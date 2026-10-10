import Link from "next/link";

import { db, must } from "@/lib/db";

export const dynamic = "force-dynamic";

async function count(table: string, filter?: [string, string]): Promise<number> {
  let q = db().from(table).select("id", { count: "exact", head: true });
  if (filter) q = q.eq(filter[0], filter[1]);
  const { count: n, error } = await q;
  if (error) throw new Error(error.message);
  return n ?? 0;
}

export default async function Home() {
  const [datasets, findings, drafts, approved, published, failedJobs] = await Promise.all([
    count("datasets"),
    count("findings"),
    count("stories", ["status", "draft"]),
    count("stories", ["status", "approved"]),
    count("stories", ["status", "published"]),
    count("jobs", ["status", "failed"]),
  ]);
  const jobs = await must<{ type: string; status: string; started_at: string }[]>(
    db().from("jobs").select("type, status, started_at").order("started_at", { ascending: false }).limit(5),
  );
  return (
    <>
      <h1>Overview</h1>
      <div className="grid2">
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Pipeline</h2>
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
        </div>
        <div className="panel">
          <h2 style={{ marginTop: 0 }}>Latest jobs</h2>
          <table>
            <tbody>
              {jobs.map((j, i) => (
                <tr key={i}>
                  <td>{j.type}</td>
                  <td>
                    <span className={`badge ${j.status === "succeeded" ? "ok" : j.status === "failed" ? "bad" : "warn"}`}>
                      {j.status}
                    </span>
                  </td>
                  <td className="small muted">{new Date(j.started_at).toLocaleString("en-GB")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="small muted">
        Local review app. Reads and writes Supabase on the server only; every rule and check runs in
        the Python worker.
      </p>
    </>
  );
}
