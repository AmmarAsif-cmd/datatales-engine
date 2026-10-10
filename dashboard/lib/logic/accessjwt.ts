/**
 * Cloudflare Access JWT verification (pure: no Next.js imports, so it can be unit-tested).
 * Checks the RS256 signature against the team's published keys, the issuer (team domain),
 * the audience (this app's AUD tag), expiry and not-before.
 */
export class AccessDenied extends Error {}

type Jwk = { kid: string; kty: string; n: string; e: string; alg?: string };
let jwksCache: { url: string; keys: Jwk[]; at: number } | null = null;
const JWKS_TTL_MS = 10 * 60 * 1000;
const CLOCK_SKEW_S = 60;

function b64urlToBytes(s: string): Uint8Array<ArrayBuffer> {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function b64urlJson<T>(s: string): T {
  return JSON.parse(new TextDecoder().decode(b64urlToBytes(s))) as T;
}

export function resetKeyCache(): void {
  jwksCache = null;
}

async function signingKeys(teamDomain: string, refresh = false): Promise<Jwk[]> {
  const url = `${teamDomain}/cdn-cgi/access/certs`;
  if (!refresh && jwksCache && jwksCache.url === url && Date.now() - jwksCache.at < JWKS_TTL_MS) {
    return jwksCache.keys;
  }
  const res = await fetch(url);
  if (!res.ok) throw new AccessDenied(`could not fetch Access signing keys (${res.status})`);
  const body = (await res.json()) as { keys?: Jwk[] };
  const keys = (body.keys ?? []).filter((k) => k.kty === "RSA");
  jwksCache = { url, keys, at: Date.now() };
  return keys;
}

export type AccessUser = { email: string; local: boolean };

export async function verifyAccessJwt(token: string, teamDomain: string, aud: string): Promise<AccessUser> {
  const parts = token.split(".");
  if (parts.length !== 3) throw new AccessDenied("malformed token");
  const [h, p, sig] = parts;
  const header = b64urlJson<{ alg?: string; kid?: string }>(h);
  if (header.alg !== "RS256" || !header.kid) throw new AccessDenied("unexpected token algorithm");

  let jwk = (await signingKeys(teamDomain)).find((k) => k.kid === header.kid);
  if (!jwk) jwk = (await signingKeys(teamDomain, true)).find((k) => k.kid === header.kid);
  if (!jwk) throw new AccessDenied("unknown signing key");

  const key = await crypto.subtle.importKey(
    "jwk",
    { kty: "RSA", n: jwk.n, e: jwk.e, alg: "RS256", ext: true },
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"],
  );
  const ok = await crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    key,
    b64urlToBytes(sig),
    new TextEncoder().encode(`${h}.${p}`),
  );
  if (!ok) throw new AccessDenied("bad signature");

  const claims = b64urlJson<{ aud?: string | string[]; iss?: string; exp?: number; nbf?: number; email?: string }>(p);
  const now = Math.floor(Date.now() / 1000);
  const auds = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
  if (!auds.includes(aud)) throw new AccessDenied("token is for a different application");
  if (claims.iss !== teamDomain) throw new AccessDenied("token from a different team");
  if (!claims.exp || claims.exp < now - CLOCK_SKEW_S) throw new AccessDenied("token expired");
  if (claims.nbf && claims.nbf > now + CLOCK_SKEW_S) throw new AccessDenied("token not yet valid");
  if (!claims.email) throw new AccessDenied("token has no email");
  return { email: claims.email, local: false };
}

