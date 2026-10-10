// `npm run dev`: load .dev.vars into the environment, then start Next on 127.0.0.1.
// Local secrets live in .dev.vars (not .env.local) because OpenNext bundles .env* files.
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";

if (existsSync(".dev.vars")) {
  for (const raw of readFileSync(".dev.vars", "utf8").split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const i = line.indexOf("=");
    const key = line.slice(0, i).trim();
    let value = line.slice(i + 1).trim();
    if (value.length >= 2 && value[0] === value.at(-1) && `"'`.includes(value[0])) value = value.slice(1, -1);
    if (!(key in process.env)) process.env[key] = value;
  }
}
const port = process.env.DASHBOARD_PORT ?? "4317";
const child = spawn("npx", ["next", "dev", "--hostname", "127.0.0.1", "--port", port], {
  stdio: "inherit",
  shell: process.platform === "win32",
});
child.on("exit", (code) => process.exit(code ?? 0));
