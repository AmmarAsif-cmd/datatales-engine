/**
 * Cloudflare Access JWT verification, with a locally generated RSA key pair and a fake
 * key endpoint. Nothing here talks to Cloudflare.
 */
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { AccessDenied, resetKeyCache, verifyAccessJwt } from "../lib/logic/accessjwt.ts";

const TEAM = "https://datatales.cloudflareaccess.com";
const AUD = "a".repeat(64);

const pair = (await crypto.subtle.generateKey(
  { name: "RSASSA-PKCS1-v1_5", modulusLength: 2048, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" },
  true,
  ["sign", "verify"],
)) as CryptoKeyPair;
const publicJwk = await crypto.subtle.exportKey("jwk", pair.publicKey);

const b64url = (bytes: Uint8Array) =>
  Buffer.from(bytes).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const enc = (obj: unknown) => b64url(new TextEncoder().encode(JSON.stringify(obj)));

async function token(claims: Record<string, unknown>, header: Record<string, unknown> = {}): Promise<string> {
  const h = enc({ alg: "RS256", kid: "k1", typ: "JWT", ...header });
  const p = enc(claims);
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", pair.privateKey, new TextEncoder().encode(`${h}.${p}`));
  return `${h}.${p}.${b64url(new Uint8Array(sig))}`;
}

const now = () => Math.floor(Date.now() / 1000);
const good = () => ({ aud: [AUD], iss: TEAM, email: "ammar@example.com", exp: now() + 600, nbf: now() - 5 });

beforeEach(() => {
  resetKeyCache();
  globalThis.fetch = (async (url: string) => {
    assert.equal(url, `${TEAM}/cdn-cgi/access/certs`);
    return new Response(JSON.stringify({ keys: [{ ...publicJwk, kid: "k1", alg: "RS256" }] }));
  }) as typeof fetch;
});

async function rejects(tok: string, reason: RegExp) {
  await assert.rejects(verifyAccessJwt(tok, TEAM, AUD), (e: unknown) => e instanceof AccessDenied && reason.test(e.message));
}

test("valid token gives the email", async () => {
  assert.deepEqual(await verifyAccessJwt(await token(good()), TEAM, AUD), { email: "ammar@example.com", local: false });
});

test("wrong audience (another Access app) is refused", async () => {
  await rejects(await token({ ...good(), aud: ["b".repeat(64)] }), /different application/);
});

test("wrong team is refused", async () => {
  await rejects(await token({ ...good(), iss: "https://evil.cloudflareaccess.com" }), /different team/);
});

test("expired and not-yet-valid tokens are refused", async () => {
  await rejects(await token({ ...good(), exp: now() - 3600 }), /expired/);
  await rejects(await token({ ...good(), nbf: now() + 3600 }), /not yet valid/);
});

test("tampered payload fails the signature", async () => {
  const [h, , s] = (await token(good())).split(".");
  await rejects(`${h}.${enc({ ...good(), email: "attacker@example.com" })}.${s}`, /bad signature/);
});

test("unknown key, wrong algorithm and junk are refused", async () => {
  await rejects(await token(good(), { kid: "other" }), /unknown signing key/);
  await rejects(await token(good(), { alg: "HS256" }), /algorithm/);
  await rejects("not.a.jwt.at.all", /malformed/);
});

test("token without an email is refused", async () => {
  const { email: _drop, ...rest } = good();
  void _drop;
  await rejects(await token(rest), /no email/);
});
