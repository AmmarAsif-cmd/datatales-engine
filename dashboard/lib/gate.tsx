import "server-only";

import type { ReactElement } from "react";

import { type AccessUser, AccessDenied, requireUser } from "./access";
import { type ConfigProblem, configProblems } from "./config.ts";

/** Signed-in user or null. Never throws (used by the layout for the top bar). */
export async function pageUser(): Promise<AccessUser | null> {
  try {
    if (configProblems().some((p) => p.fatal)) return null;
    return await requireUser();
  } catch {
    return null;
  }
}

/**
 * Run at the top of every page, before any data is loaded. Returns a page to render
 * instead (configuration problem, or not signed in), or null to carry on.
 */
export async function pageGate(): Promise<ReactElement | null> {
  const fatal = configProblems().filter((p) => p.fatal);
  if (fatal.length) return <ConfigError problems={fatal} />;
  try {
    await requireUser();
    return null;
  } catch (e) {
    if (e instanceof AccessDenied) return <Denied reason={e.message} />;
    return <ConfigError problems={[{ name: "Cloudflare Access", problem: (e as Error).message, fatal: true }]} />;
  }
}

export function ConfigError({ problems }: { problems: ConfigProblem[] }) {
  return (
    <div className="panel">
      <h1>Configuration problem</h1>
      <p>The dashboard is running, but these settings need fixing before it can load data:</p>
      <ul>
        {problems.map((p) => (
          <li key={p.name}>
            <code>{p.name}</code> {p.problem}
          </li>
        ))}
      </ul>
      <p className="small muted">
        On Cloudflare: Workers &amp; Pages → datatales-admin → Settings → Variables and Secrets (or{" "}
        <code>npx wrangler secret put NAME</code>), then redeploy. Locally: <code>dashboard/.dev.vars</code>.
        See dashboard/README.md.
      </p>
    </div>
  );
}

export function Denied({ reason }: { reason?: string }) {
  return (
    <div className="panel">
      <h1>Not signed in</h1>
      <p>This dashboard is only available through Cloudflare Access at admin.datatales.co.uk.</p>
      {reason && <p className="small muted">Reason: {reason}</p>}
    </div>
  );
}
