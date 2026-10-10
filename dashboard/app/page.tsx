import Link from "next/link";

import { RunPipelineButton } from "@/components/Buttons";
import { db, must } from "@/lib/db";
import { when } from "@/lib/format";
import { Denied, pageUser } from "@/lib/gate";
import { recentRuns, type WorkflowRun } from "@/lib/github";

export const dynamic = "force-dynamic";

async function count(table: string, filter?: [string, string]): Promise<number> {
  let q = db().from(table).select("id", { count: "exact", head: true });
  if (filter) q = q.eq(filter[0], filter[1]);
  const { count: n, error } = await q;
  if (error) throw new Error(error.message);
  return n ?? 0;
}

function runBadge(r: WorkflowRun): string {
  if (r.status !== "completed") return "warn";
  return r.conclusion === "success" ? "ok" : "bad";
}

export default async function Home() {
  if (!(await pageUser())) return <Denied />;
  const [datasets, findings, drafts, approved, published, failedJobs] = await Promise.all([
    count("datasets"),
    count("findings"),
    count("stories", ["status", "draft"]),
    count("stories", ["status", "approved"]),
    count("stories", ["status", "published"]),
    count("jobs", ["status", "failed"]),
  ]);
  const jobs = await must<{ type: string; status: string; started_at: string }[]>(
    db().from("jobs").select("type, status, started_at").order("started_at", { ascending: false }).limit(6),
  );
  let runs: WorkflowRun[] = [];
  let runsError = "";
  try {
    runs = await recentRuns(6);
  } catch (e) {
    runsError = (e as Error).message;
  }

  return (
    <>
      <h1>Overview</h1>
      <div className="grid2">
        <div className="panel">
          <h2 className="first">Pipeline</h2>
          <p>
            {datasets} dataset(s) · <Link href="/findings">{findings} finding(s)</Link>
          </p>
          <p>
            <Link href="/stories">Stories</Link>: {drafts} draft · {approved} approved · {published}{" "}
            published
          </p>
          <p>
            <Link href="/datasets">Jobs</Link>:{" "}
            {failedJobs ? <span className="badge bad">{failedJobs} failed</span> : "none failed"}
          </p>
          <RunPipelineButton />
          <p className="small muted">
            Runs ingest → profile → clean → detect in GitHub Actions (also every Monday 06:00 UTC).
          </p>
        </div>
        <div className="panel">
          <h2 className="first">Automation runs</h2>
          {runsError ? (
            <p className="small muted">{runsError}</p>
          ) : (
            <table className="stack">
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td data-label="Workflow">
                      <a href={r.html_url} target="_blank" rel="noreferrer">
                        {r.name}
                      </a>
                    </td>
                    <td data-label="Status">
                      <span className={`badge ${runBadge(r)}`}>{r.conclusion ?? r.status}</span>
                    </td>
                    <td data-label="Started" className="small muted">
                      {when(r.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <h2>Latest jobs</h2>
          <table className="stack">
            <tbody>
              {jobs.map((j, i) => (
                <tr key={i}>
                  <td data-label="Job">{j.type}</td>
                  <td data-label="Status">
                    <span
                      className={`badge ${j.status === "succeeded" ? "ok" : j.status === "failed" ? "bad" : "warn"}`}
                    >
                      {j.status}
                    </span>
                  </td>
                  <td data-label="Started" className="small muted">
                    {when(j.started_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
