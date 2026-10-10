import "server-only";

import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

import { supabaseEnv } from "./env";

const WORKER_DIR = path.resolve(process.cwd(), "..", "worker");
const TIMEOUT_MS = 180_000;

function pythonPath(): string {
  if (process.env.DATATALES_PYTHON) return process.env.DATATALES_PYTHON;
  const venv =
    process.platform === "win32"
      ? path.join(WORKER_DIR, ".venv", "Scripts", "python.exe")
      : path.join(WORKER_DIR, ".venv", "bin", "python");
  if (!existsSync(venv)) {
    throw new Error(`Python worker not set up: run \`uv sync\` in ${WORKER_DIR}`);
  }
  return venv;
}

export type WorkerResult<T> = { ok: true; data: T } | { ok: false; error: string };

/**
 * Run `python -m datatales api <action>` with a JSON payload on stdin. No shell is used,
 * and the dashboard's own Supabase settings are passed so both talk to the same project.
 */
export function runWorker<T>(action: string, payload: Record<string, unknown>): Promise<WorkerResult<T>> {
  const { url, key } = supabaseEnv();
  return new Promise((resolve) => {
    const child = spawn(pythonPath(), ["-m", "datatales", "api", action], {
      cwd: WORKER_DIR,
      env: { ...process.env, SUPABASE_URL: url, SUPABASE_SERVICE_ROLE_KEY: key, PYTHONIOENCODING: "utf-8" },
      shell: false,
      windowsHide: true,
    });
    let out = "";
    let err = "";
    const timer = setTimeout(() => {
      child.kill();
      resolve({ ok: false, error: `worker timed out after ${TIMEOUT_MS / 1000}s` });
    }, TIMEOUT_MS);
    child.stdout.setEncoding("utf8").on("data", (d: string) => (out += d));
    child.stderr.setEncoding("utf8").on("data", (d: string) => (err += d));
    child.on("error", (e) => {
      clearTimeout(timer);
      resolve({ ok: false, error: `could not start Python: ${e.message}` });
    });
    child.on("close", () => {
      clearTimeout(timer);
      const last = out.trim().split("\n").pop() ?? "";
      try {
        resolve(JSON.parse(last) as WorkerResult<T>);
      } catch {
        resolve({ ok: false, error: (err || out || "worker returned no output").slice(-2000) });
      }
    });
    child.stdin.end(JSON.stringify(payload));
  });
}
