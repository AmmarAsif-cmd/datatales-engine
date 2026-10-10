import Link from "next/link";

import { CreateStoryButton } from "@/components/Buttons";
import MiniChart from "@/components/MiniChart";
import { db, must } from "@/lib/db";
import { short, when } from "@/lib/format";
import { pageGate } from "@/lib/gate";
import { type FindingRow, shortlist } from "@/lib/logic/stories.ts";
import type { Finding } from "@/lib/types";

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
  const gate = await pageGate();
  if (gate) return gate;
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
        <p className="muted">No clean tables yet. Run the pipeline from the overview.</p>
      </>
    );
  }
  const current = tables.find((t) => t.id === ct) ?? tables[0];
  const findings = await must<Finding[]>(
    db().from("findings").select("*").eq("clean_table_id", current.id).order("score", { ascending: false }),
  );
  const cands = shortlist(findings as unknown as FindingRow[]);

  return (
    <>
      <h1>Findings</h1>
      <div className="panel">
        <form className="row">
          <label htmlFor="ct" className="inline">
            Clean table
          </label>
          <select id="ct" name="ct" defaultValue={current.id}>
            {tables.map((t) => (
              <option key={t.id} value={t.id}>
                {t.datasets?.sources?.slug} · v{t.recipes?.version} ·{" "}
                {t.row_count.toLocaleString("en-GB")} rows · {when(t.created_at)}
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
        {cands.length === 0 && <p className="muted">No findings yet for this table.</p>}
        <table className="stack">
          <thead>
            <tr>
              <th>#</th>
              <th className="num">Score</th>
              <th>Candidate</th>
              <th className="num">Findings</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cands.map((c, i) => (
              <tr key={c.finding_ids.join()}>
                <td data-label="#">{i + 1}</td>
                <td data-label="Score" className="num">
                  {c.score.toFixed(3)}
                </td>
                <td data-label="Candidate">
                  <b>{c.geography}</b> <span className="muted small">({c.geo_level})</span>{" "}
                  <span className={`badge ${c.good_news ? "ok" : "bad"}`}>
                    {c.good_news ? "good news" : "bad news"}
                  </span>
                  <div className="small muted">{c.measures.join(", ")}</div>
                </td>
                <td data-label="Findings" className="num">
                  {c.finding_ids.length}
                </td>
                <td data-label="">
                  <CreateStoryButton cleanTableId={current.id} candidate={i + 1} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>All findings ({findings.length}), by score</h2>
      <div className="panel">
        <table className="stack">
          <thead>
            <tr>
              <th className="num">Score</th>
              <th>Finding</th>
              <th>Start → end (with CIs)</th>
              <th>Numbers</th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f) => (
              <tr key={f.id}>
                <td data-label="Score" className="num">
                  {f.score.toFixed(3)}
                </td>
                <td data-label="Finding">
                  {f.title_hint}
                  <div className="small muted">
                    <span className="badge plain">{f.detector}</span> {String(f.numbers.unit ?? "")} ·{" "}
                    {f.numbers.good_news ? "good news" : "bad news"} · {short(f.id)}
                  </div>
                </td>
                <td data-label="Change">
                  <MiniChart finding={f} />
                  <div className="small muted">
                    {f.detector === "outlier"
                      ? `${f.numbers.value} vs median ${f.numbers.median}`
                      : `${f.numbers.start_value} → ${f.numbers.end_value}`}
                  </div>
                </td>
                <td data-label="Numbers">
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
