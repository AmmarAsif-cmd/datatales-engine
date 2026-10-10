import Link from "next/link";

import { createStory } from "@/app/actions";
import MiniChart from "@/components/MiniChart";
import { db, must } from "@/lib/db";
import { short, when } from "@/lib/format";
import type { Candidate, Finding } from "@/lib/types";
import { runWorker } from "@/lib/worker";

export const dynamic = "force-dynamic";

type CleanTable = {
  id: string;
  row_count: number;
  checks_passed: boolean;
  created_at: string;
  recipes: { version: number } | null;
  datasets: { fetched_at: string; sources: { slug: string; name: string } | null } | null;
};

export default async function FindingsPage({
  searchParams,
}: {
  searchParams: Promise<{ ct?: string }>;
}) {
  const { ct } = await searchParams;
  const tables = await must<CleanTable[]>(
    db()
      .from("clean_tables")
      .select("id, row_count, checks_passed, created_at, recipes(version), datasets(fetched_at, sources(slug, name))")
      .eq("checks_passed", true)
      .order("created_at", { ascending: false }),
  );
  if (!tables.length) {
    return (
      <>
        <h1>Findings</h1>
        <p className="muted">No clean tables yet. Run ingest, approve a recipe, then clean.</p>
      </>
    );
  }
  const current = tables.find((t) => t.id === ct) ?? tables[0];
  const [findings, cands] = await Promise.all([
    must<Finding[]>(
      db().from("findings").select("*").eq("clean_table_id", current.id).order("score", { ascending: false }),
    ),
    runWorker<Candidate[]>("candidates", { clean_table_id: current.id }),
  ]);

  return (
    <>
      <h1>Findings</h1>
      <div className="panel">
        <form className="row">
          <label htmlFor="ct" style={{ margin: 0 }}>
            Clean table
          </label>
          <select id="ct" name="ct" defaultValue={current.id} style={{ maxWidth: "36rem" }}>
            {tables.map((t) => (
              <option key={t.id} value={t.id}>
                {t.datasets?.sources?.slug} · recipe v{t.recipes?.version} · {t.row_count.toLocaleString("en-GB")} rows ·{" "}
                {when(t.created_at)}
              </option>
            ))}
          </select>
          <button type="submit" className="secondary">
            Show
          </button>
        </form>
      </div>

      <h2>Story shortlist</h2>
      <div className="panel">
        {!cands.ok ? (
          <p className="msg bad">{cands.error}</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th className="num">Score</th>
                <th>Candidate</th>
                <th>Findings</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {cands.data.map((c) => (
                <tr key={c.index}>
                  <td>{c.index}</td>
                  <td className="num">{c.score.toFixed(3)}</td>
                  <td>
                    <b>{c.geography}</b> <span className="muted small">({c.geo_level})</span>{" "}
                    <span className={`badge ${c.good_news ? "ok" : "bad"}`}>
                      {c.good_news ? "good news" : "bad news"}
                    </span>
                    <div className="small muted">{c.measures.join(", ")}</div>
                  </td>
                  <td>{c.finding_ids.length}</td>
                  <td>
                    <form action={createStory}>
                      <input type="hidden" name="clean_table_id" value={current.id} />
                      <input type="hidden" name="candidate" value={c.index} />
                      <button type="submit" className="secondary">
                        Create story
                      </button>
                    </form>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <h2>All findings ({findings.length}), by score</h2>
      <div className="panel">
        <table>
          <thead>
            <tr>
              <th className="num">Score</th>
              <th>Detector</th>
              <th>Finding</th>
              <th>Start → end (with CIs)</th>
              <th>Numbers</th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f) => (
              <tr key={f.id}>
                <td className="num">{f.score.toFixed(3)}</td>
                <td>
                  <span className="badge plain">{f.detector}</span>
                </td>
                <td>
                  {f.title_hint}
                  <div className="small muted">
                    {String(f.numbers.unit ?? "")} ·{" "}
                    <span className={f.numbers.good_news ? "" : ""}>
                      {f.numbers.good_news ? "good news" : "bad news"}
                    </span>{" "}
                    · {short(f.id)}
                  </div>
                </td>
                <td>
                  <MiniChart finding={f} />
                  <div className="small muted">
                    {f.detector === "outlier"
                      ? `${f.numbers.value} vs median ${f.numbers.median}`
                      : `${f.numbers.start_value} → ${f.numbers.end_value}`}
                  </div>
                </td>
                <td>
                  <details>
                    <summary className="small">JSON</summary>
                    <pre className="box small">{JSON.stringify(f.numbers, null, 1)}</pre>
                  </details>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small">
        <Link href="/stories">Go to stories →</Link>
      </p>
    </>
  );
}
