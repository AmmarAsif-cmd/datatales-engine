// After a Cloudflare build: fail if any secret name or local secret value made it into the
// bundle. Worker secrets are the only place production secrets may live.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const SECRET_NAMES = ["SUPABASE_SERVICE_ROLE_KEY", "GITHUB_DISPATCH_TOKEN", "CF_ACCESS_AUD", "ANTHROPIC_API_KEY"];
// Any Anthropic key, even one not in .dev.vars, must never be in the bundle.
const KEY_PATTERNS = [/sk-ant-[A-Za-z0-9_-]{8,}/];
const values = [];
if (existsSync(".dev.vars")) {
  for (const line of readFileSync(".dev.vars", "utf8").split(/\r?\n/)) {
    const [k, ...rest] = line.split("=");
    const v = rest.join("=").trim();
    if (SECRET_NAMES.includes(k.trim()) && v.length >= 12) values.push(v);
  }
}
const problems = [];
const env = ".open-next/cloudflare/next-env.mjs";
if (existsSync(env)) {
  const text = readFileSync(env, "utf8");
  for (const name of [...SECRET_NAMES, "SUPABASE_URL"]) if (text.includes(name)) problems.push(`${env} defines ${name}`);
}
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(m?js|json|html|txt|map)$/.test(name)) {
      const text = readFileSync(p, "utf8");
      for (const v of values) if (text.includes(v)) problems.push(`secret value found in ${p}`);
      for (const re of KEY_PATTERNS) if (re.test(text)) problems.push(`API key pattern ${re} found in ${p}`);
    }
  }
};
if (existsSync(".open-next")) walk(".open-next");
if (problems.length) {
  console.error("Bundle check FAILED:\n - " + problems.join("\n - "));
  process.exit(1);
}
console.log(`Bundle check OK (${values.length} local secret value(s) checked).`);
