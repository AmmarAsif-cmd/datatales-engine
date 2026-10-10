// Runtime smoke test: run the built Worker in workerd (`opennextjs-cloudflare preview`) and
// request real pages. Fails on a 5xx, a Worker exception (Cloudflare error 1101) or any
// "Unexpected loadManifest" style crash. Run after `npm run build:cf`.
//
// Each scenario runs from a temporary folder holding a copy of wrangler.jsonc (pointing at the
// real build) and its own .dev.vars with dummy values, because Wrangler reads .dev.vars next to
// the config file. The developer's real dashboard/.dev.vars is never read or touched.
import { spawn } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

const UUID = "00000000-0000-0000-0000-000000000000";
const CRASH = /Unexpected loadManifest|Error 1101|Worker threw exception|Internal Server Error/i;

const SCENARIOS = [
  {
    name: "configured (dummy values, no Access token)",
    port: 8791,
    env: {
      SUPABASE_URL: "https://smoke.invalid",
      SUPABASE_SERVICE_ROLE_KEY: "smoke-test-not-a-real-key-0123456789",
      CF_ACCESS_TEAM_DOMAIN: "https://ci-smoke.cloudflareaccess.com",
      CF_ACCESS_AUD: "0".repeat(64),
      GITHUB_REPO: "AmmarAsif-cmd/datatales-engine",
    },
    expect: "Not signed in",
    paths: ["/", "/findings", "/stories", `/stories/${UUID}`, "/datasets", "/recipes"],
  },
  {
    name: "missing configuration",
    port: 8792,
    env: { GITHUB_REPO: "AmmarAsif-cmd/datatales-engine" },
    expect: "Configuration problem",
    paths: ["/", "/stories"],
  },
];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** wrangler.jsonc -> plain object with absolute paths, so it works from another folder. */
function loadConfig() {
  const text = readFileSync("wrangler.jsonc", "utf8")
    .split("\n")
    .filter((line) => !line.trim().startsWith("//"))
    .join("\n")
    .replace(/,(\s*[}\]])/g, "$1");
  const config = JSON.parse(text);
  delete config.$schema;
  config.main = resolve(config.main);
  config.assets.directory = resolve(config.assets.directory);
  return config;
}

async function waitUp(url, child, seconds = 120) {
  for (let i = 0; i < seconds; i++) {
    if (child.exitCode !== null) throw new Error(`preview exited early (code ${child.exitCode})`);
    try {
      await fetch(url, { signal: AbortSignal.timeout(2000) });
      return;
    } catch {
      await sleep(1000);
    }
  }
  throw new Error(`preview did not start within ${seconds}s`);
}

function stop(child) {
  if (child.exitCode !== null) return;
  if (process.platform === "win32") spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"]);
  else process.kill(-child.pid, "SIGTERM");
}

const config = loadConfig();
const root = mkdtempSync(join(tmpdir(), "dt-smoke-"));
let failures = 0;

for (const s of SCENARIOS) {
  const dir = mkdtempSync(join(root, "s-"));
  const configFile = join(dir, "wrangler.json");
  writeFileSync(configFile, JSON.stringify(config, null, 2));
  writeFileSync(
    join(dir, ".dev.vars"),
    Object.entries(s.env)
      .map(([k, v]) => `${k}=${v}`)
      .join("\n") + "\n",
  );

  console.log(`\n== ${s.name}`);
  const child = spawn(
    "npx",
    ["opennextjs-cloudflare", "preview", "--config", configFile, "--port", String(s.port), "--ip", "127.0.0.1"],
    { shell: process.platform === "win32", detached: process.platform !== "win32", stdio: ["ignore", "pipe", "pipe"] },
  );
  let log = "";
  child.stdout.on("data", (d) => (log += d));
  child.stderr.on("data", (d) => (log += d));
  const base = `http://127.0.0.1:${s.port}`;
  try {
    await waitUp(base, child);
    for (const p of s.paths) {
      const res = await fetch(base + p, { signal: AbortSignal.timeout(60000) });
      const body = await res.text();
      const ok = res.status < 500 && body.includes(s.expect) && !CRASH.test(body);
      const h1 = /<h1[^>]*>([^<]*)<\/h1>/.exec(body)?.[1] ?? "(no h1)";
      console.log(`${ok ? "PASS" : "FAIL"}  ${res.status}  ${p}  [${h1}]`);
      if (!ok) {
        failures++;
        const items = (body.match(/<li>.*?<\/li>/g) ?? []).join(" ").replace(/<[^>]+>/g, "");
        console.log(items.slice(0, 400) || body.slice(0, 400));
      }
    }
    if (CRASH.test(log)) {
      failures++;
      const lines = log.split("\n").filter((l) => CRASH.test(l));
      console.log("FAIL  worker log shows a crash:\n" + lines.join("\n"));
    }
  } catch (e) {
    failures++;
    console.log(`FAIL  ${e.message}\n${log.slice(-2000)}`);
  } finally {
    stop(child);
    await sleep(2000);
  }
}

console.log(failures ? `\nSmoke test FAILED (${failures})` : "\nSmoke test passed");
process.exit(failures ? 1 : 0);
