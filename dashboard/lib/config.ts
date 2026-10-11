/**
 * Configuration check. Reports problems by setting NAME only (never values), so the page that
 * shows them cannot leak a secret. Pure (reads an env object), so it can be unit-tested.
 */

export type ConfigProblem = { name: string; problem: string; fatal: boolean };

type Env = Record<string, string | undefined>;

const TEAM_DOMAIN = /^https:\/\/[a-z0-9-]+\.cloudflareaccess\.com\/?$/;
const AUD_TAG = /^[0-9a-f]{64}$/;

export function configProblems(env: Env = process.env): ConfigProblem[] {
  const out: ConfigProblem[] = [];
  const get = (k: string) => env[k]?.trim() ?? "";
  const fatal = (name: string, problem: string) => out.push({ name, problem, fatal: true });
  const warn = (name: string, problem: string) => out.push({ name, problem, fatal: false });

  const url = get("SUPABASE_URL");
  if (!url) fatal("SUPABASE_URL", "is not set");
  else if (!/^https:\/\/[^\s/]+/.test(url)) fatal("SUPABASE_URL", "must start with https://");

  const key = get("SUPABASE_SERVICE_ROLE_KEY");
  if (!key) fatal("SUPABASE_SERVICE_ROLE_KEY", "is not set");
  else if (key.length < 20) fatal("SUPABASE_SERVICE_ROLE_KEY", "looks too short to be a Supabase key");

  if (env.NODE_ENV === "production") {
    const team = get("CF_ACCESS_TEAM_DOMAIN");
    if (!team) fatal("CF_ACCESS_TEAM_DOMAIN", "is not set");
    else if (!TEAM_DOMAIN.test(team)) {
      fatal("CF_ACCESS_TEAM_DOMAIN", "must look like https://<team>.cloudflareaccess.com");
    }
    const aud = get("CF_ACCESS_AUD");
    if (!aud) fatal("CF_ACCESS_AUD", "is not set");
    else if (!AUD_TAG.test(aud)) {
      fatal("CF_ACCESS_AUD", "must be the 64-character Application Audience (AUD) tag");
    }
  }

  const anthropic = get("ANTHROPIC_API_KEY");
  if (!anthropic) warn("ANTHROPIC_API_KEY", "is not set: Claude drafting falls back to copy-paste");
  else if (!anthropic.startsWith("sk-ant-")) warn("ANTHROPIC_API_KEY", "does not look like an Anthropic API key");
  if (!get("GITHUB_DISPATCH_TOKEN")) warn("GITHUB_DISPATCH_TOKEN", "is not set: publish and run buttons won't work");
  const repo = get("GITHUB_REPO");
  if (!repo) warn("GITHUB_REPO", "is not set");
  else if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) warn("GITHUB_REPO", "must look like owner/name");
  return out;
}
