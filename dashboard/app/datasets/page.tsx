import { db, must } from "@/lib/db";
import { pageGate } from "@/lib/gate";
import { short, when } from "@/lib/format";
import type { Json } from "@/lib/types";

export const dynamic = "force-dynamic";

type Dataset = {
  id: string;
  raw_path: string;
  fetched_at: string;
  checksum: string;
  profile: { sheets?: { sheet: string | null; rows: number; flags?: Record<string, Json> }[] } | null;
  sources: { slug: string; name: string } | null;
};

type CleanTable = {
  id: string;
  dataset_id: string;
  row_count: number;
  checks_passed: boolean;
  checks: { name: string; passed: boolean; detail: string }[];
  created_at: string;
  recipes: { version: number } | null;
};

type Job = {
  id: string;
  type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  log: string | null;
  error: string | null;
};

export default async function DatasetsPage() {
  const gate = await pageGate();
  if (gate) return gate;
  const [datasets, tables, jobs] = await Promise.all([
    must<Dataset[]>(
      db()
        .from("datasets")
        .select("id, raw_path, fetched_at, checksum, profile, sources(slug, name)")
        .order("fetched_at", { ascending: false }),
    ),
    must<CleanTable[]>(
      db()
        .from("clean_tables")
        .select("id, dataset_id, row_count, checks_passed, checks, created_at, recipes(version)")
        .order("created_at", { ascending: false }),
    ),
    must<Job[]>(db().from("jobs").select("*").order("started_at", { ascending: false }).limit(50)),
  ]);

  return (
    <>
      <h1>Datasets &amp; jobs</h1>

      <h2>Datasets</h2>
      <div className="panel table-scroll">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Fetched</th>
              <th>Checksum</th>
              <th>Profile</th>
              <th>Clean tables</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => {
              const sheets = d.profile?.sheets ?? [];
              const cts = tables.filter((t) => t.dataset_id === d.id);
              return (
                <tr key={d.id}>
                  <td>
                    <b>{d.sources?.slug}</b>
                    <div className="small muted">{d.raw_path}</div>
                  </td>
                  <td className="small">{when(d.fetched_at)}</td>
                  <td>
                    <code title={d.checksum}>{d.checksum.slice(0, 12)}</code>
                  </td>
                  <td className="small">
                    {sheets.length === 0
                      ? "not profiled"
                      : sheets.map((s, i) => (
                          <div key={i}>
                            {s.sheet ?? "(csv)"}: {s.rows.toLocaleString("en-GB")} rows
                            {s.flags && Object.keys(s.flags).length > 0 && (
                              <span className="muted"> · flags: {Object.keys(s.flags).join(", ")}</span>
                            )}
                          </div>
                        ))}
                  </td>
                  <td>
                    {cts.map((t) => (
                      <div key={t.id} className="small">
                        <span className={`badge ${t.checks_passed ? "ok" : "bad"}`}>
                          {t.checks_passed ? "checks passed" : "checks FAILED"}
                        </span>{" "}
                        recipe v{t.recipes?.version} · {t.row_count.toLocaleString("en-GB")} rows ·{" "}
                        {short(t.id)}
                        {t.checks.filter((c) => !c.passed).length > 0 && (
                          <ul>
                            {t.checks
                              .filter((c) => !c.passed)
                              .map((c) => (
                                <li key={c.name}>
                                  <b>{c.name}</b>: {c.detail}
                                </li>
                              ))}
                          </ul>
                        )}
                        <details>
                          <summary>All {t.checks.length} checks</summary>
                          <ul>
                            {t.checks.map((c) => (
                              <li key={c.name}>
                                {c.passed ? "✓" : "✗"} <b>{c.name}</b>: {c.detail}
                              </li>
                            ))}
                          </ul>
                        </details>
                      </div>
                    ))}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h2>Jobs (latest 50)</h2>
      <div className="panel table-scroll">
        <table>
          <thead>
            <tr>
              <th>Started</th>
              <th>Type</th>
              <th>Status</th>
              <th>Error / log</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id}>
                <td className="small">{when(j.started_at)}</td>
                <td>{j.type}</td>
                <td>
                  <span
                    className={`badge ${j.status === "succeeded" ? "ok" : j.status === "failed" ? "bad" : "warn"}`}
                  >
                    {j.status}
                  </span>
                </td>
                <td>
                  {j.error && <div className="msg bad small">{j.error}</div>}
                  {j.log && (
                    <details>
                      <summary className="small">Log</summary>
                      <pre className="box small">{j.log}</pre>
                    </details>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
