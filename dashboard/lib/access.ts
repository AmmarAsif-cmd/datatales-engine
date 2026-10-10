import "server-only";

import { headers } from "next/headers";

/**
 * Cloudflare Access check, run by every page and every server action.
 *
 * Cloudflare Access sits in front of admin.datatales.co.uk and adds a signed JWT
 * (`Cf-Access-Jwt-Assertion`) to every request it lets through. We verify that JWT here as
 * well (signature against the team's public keys, issuer, audience = this app's AUD tag,
 * expiry), so a request that somehow skipped Access is still refused. Fails closed: in
 * production, missing settings mean every request is refused.
 *
 * Local development (`npm run dev` on 127.0.0.1) has no Access in front, so it is allowed
 * only when NODE_ENV is "development" and the Host is local.
 */

import { AccessDenied, type AccessUser, verifyAccessJwt } from "./logic/accessjwt.ts";

export { AccessDenied, type AccessUser };

const LOCAL_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]"]);

/** The signed-in user. Throws AccessDenied unless the request is properly authenticated. */
export async function requireUser(): Promise<AccessUser> {
  const h = await headers();
  const teamDomain = process.env.CF_ACCESS_TEAM_DOMAIN?.trim().replace(/\/$/, "");
  const aud = process.env.CF_ACCESS_AUD?.trim();
  const token = h.get("cf-access-jwt-assertion");

  if (token && teamDomain && aud) return verifyAccessJwt(token, teamDomain, aud);

  const host = (h.get("host") ?? "").replace(/:\d+$/, "").toLowerCase();
  if (process.env.NODE_ENV === "development" && LOCAL_HOSTS.has(host) && !token) {
    return { email: "local developer", local: true };
  }
  if (!teamDomain || !aud) throw new AccessDenied("Access is not configured (CF_ACCESS_TEAM_DOMAIN / CF_ACCESS_AUD)");
  throw new AccessDenied("no Cloudflare Access token");
}
