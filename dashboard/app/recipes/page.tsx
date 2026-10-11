import { RecipeDraftButton, RecipeReject } from "@/components/RecipeActions";
import RecipeApprove from "@/components/RecipeApprove";
import { db, must } from "@/lib/db";
import { when } from "@/lib/format";
import { pageGate } from "@/lib/gate";
import type { Json } from "@/lib/types";

export const dynamic = "force-dynamic";

type CheckRow = { name: string; passed: boolean; detail: string };
type DetectTrial = {
  passed: boolean;
  drafted: boolean;
  error?: string;
  candidates?: number;
  findings?: string[];
  series?: number;
  groups?: number;
  periods?: number;
};
type TestReport = {
  passed: boolean;
  error?: string;
  row_count?: number;
  columns?: string[];
  checks?: CheckRow[];
  preview?: Record<string, Json>[];
  summary?: string[];
  detect?: DetectTrial;
};
type Recipe = {
  id: string;
  version: number;
  spec: { description?: string; steps?: { op: string }[] };
  status: "draft" | "ready" | "failed" | "rejected";
  drafted_by: "claude" | "manual" | null;
  dataset_id: string | null;
  test_report: TestReport | null;
  detect_spec: Record<string, Json> | null;
  reject_note: string | null;
  approved_at: string | null;
  approved_by: string | null;
  created_at: string;
  sources: { slug: string } | null;
};

const cell = (v: Json | undefined) =>
  v === null || v === undefined ? "–" : typeof v === "object" ? JSON.stringify(v) : String(v);

function Report({ report }: { report: TestReport }) {
  const failed = (report.checks ?? []).filter((c) => !c.passed);
  const columns = report.columns ?? Object.keys(report.preview?.[0] ?? {});
  return (
    <>
      {report.summary && report.summary.length > 0 && (
        <>
          <h3>What it does</h3>
          <ul className="small">
            {report.summary.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </>
      )}
      {report.error && <p className="msg bad">Test run failed: {report.error}</p>}
      {report.row_count !== undefined && (
        <p className="small">
          Test run: <b>{report.row_count.toLocaleString("en-GB")}</b> rows · {columns.length} columns ·{" "}
          {failed.length ? (
            <span className="badge bad">{failed.length} check(s) failed</span>
          ) : (
            <span className="badge ok">all {report.checks?.length ?? 0} checks passed</span>
          )}
        </p>
      )}
      {(report.checks ?? []).length > 0 && (
        <details open={failed.length > 0}>
          <summary className="small">Check results</summary>
          <table className="stack small">
            <tbody>
              {(report.checks ?? []).map((c, i) => (
                <tr key={i} className={c.passed ? undefined : "claim-bad"}>
                  <td data-label="Result">
                    <span className={`badge ${c.passed ? "ok" : "bad"}`}>{c.passed ? "pass" : "fail"}</span>
                  </td>
                  <td data-label="Check">{c.name}</td>
                  <td data-label="Detail">{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
      {(report.preview ?? []).length > 0 && (
        <details>
          <summary className="small">First {report.preview!.length} cleaned rows</summary>
          <div className="table-scroll">
            <table className="small preview">
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {report.preview!.map((row, i) => (
                  <tr key={i}>
                    {columns.map((c) => (
                      <td key={c}>{cell(row[c])}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </>
  );
}

const n = (v: number | undefined) => (v ?? 0).toLocaleString("en-GB");

/** A new source's detector settings (drafted by Claude, trial-run on the cleaned table). */
function Detect({ trial, spec }: { trial: DetectTrial; spec: Record<string, Json> | null }) {
  return (
    <>
      <h3>Story detectors</h3>
      {trial.passed ? (
        <p className="small">
          Trial run: <span className="badge ok">{n(trial.candidates)} possible finding(s)</span> across{" "}
          {n(trial.groups)} places, {n(trial.periods)} periods and {n(trial.series)} series. Approving the recipe
          also saves these settings, so the source joins the weekly pipeline.
        </p>
      ) : (
        <p className="msg bad">
          {trial.drafted ? "The detector settings did not pass their trial run" : "No detector settings were drafted"}
          {trial.error ? `: ${trial.error}` : ""}. You can still approve the recipe; the data is then cleaned each
          week, but no stories are found until a <code>detect</code> block is added to the source file.
        </p>
      )}
      {(trial.findings ?? []).length > 0 && (
        <ul className="small">
          {trial.findings!.map((f, i) => (
            <li key={i}>{f}</li>
          ))}
        </ul>
      )}
      {spec && (
        <details>
          <summary className="small">Settings</summary>
          <pre className="small">{JSON.stringify(spec, null, 2)}</pre>
        </details>
      )}
    </>
  );
}

function RecipeCard({ r }: { r: Recipe }) {
  const slug = r.sources?.slug ?? "?";
  const badge = r.approved_at
    ? { cls: "ok", text: `approved by ${r.approved_by}, ${when(r.approved_at)}` }
    : { ready: { cls: "ok", text: "ready to approve" }, failed: { cls: "bad", text: "test run failed" },
        draft: { cls: "warn", text: "not test-run yet" }, rejected: { cls: "plain", text: "rejected" } }[r.status]; // prettier-ignore
  return (
    <div className="panel">
      <div className="row">
        <h2 style={{ margin: 0 }}>
          {slug} v{r.version}
        </h2>
        <span className={`badge ${badge.cls}`}>{badge.text}</span>
        {r.drafted_by === "claude" && <span className="badge claude">Drafted by Claude</span>}
        <span className="small muted">{when(r.created_at)}</span>
      </div>
      {r.spec.description && <p>{r.spec.description}</p>}
      {r.reject_note && <p className="small">Rejected: {r.reject_note}</p>}
      {r.test_report ? (
        <>
          <Report report={r.test_report} />
          {r.test_report.detect && <Detect trial={r.test_report.detect} spec={r.detect_spec} />}
        </>
      ) : (
        <p className="small">Steps: {(r.spec.steps ?? []).map((s) => s.op).join(" → ")}</p>
      )}
      {!r.approved_at && r.status !== "rejected" && (
        <div className="row" style={{ marginTop: "0.75rem", gap: "1.5rem" }}>
          {(r.status === "ready" || r.status === "draft") && <RecipeApprove source={slug} version={r.version} />}
          <RecipeReject recipeId={r.id} />
          {r.status === "failed" && r.dataset_id && <RecipeDraftButton datasetId={r.dataset_id} label="Draft again with Claude" />}
        </div>
      )}
      {r.status === "draft" && !r.approved_at && (
        <p className="small muted">Approving test-runs it first; it is only approved if every check passes.</p>
      )}
      <details>
        <summary className="small">Full recipe</summary>
        <pre className="box small">{JSON.stringify(r.spec, null, 2)}</pre>
      </details>
    </div>
  );
}

export default async function RecipesPage() {
  const gate = await pageGate();
  if (gate) return gate;
  const recipes = await must<Recipe[]>(
    db()
      .from("recipes")
      .select(
        "id, version, spec, status, drafted_by, dataset_id, test_report, detect_spec, reject_note, approved_at, approved_by, created_at, sources(slug)",
      )
      .order("created_at", { ascending: false }),
  );
  const groups: [string, Recipe[], string][] = [
    ["Ready to approve", recipes.filter((r) => !r.approved_at && r.status === "ready"), "Passed every check in a test run on real data. Approve to let it run in the pipeline."],
    ["Needs attention", recipes.filter((r) => !r.approved_at && (r.status === "failed" || r.status === "draft")), "Failed its test run, or not test-run yet."],
    ["Approved", recipes.filter((r) => r.approved_at), "These run in the weekly pipeline. Approved versions never change."],
    ["Rejected", recipes.filter((r) => !r.approved_at && r.status === "rejected"), ""],
  ]; // prettier-ignore

  return (
    <>
      <h1>Recipes</h1>
      <p className="small muted">
        Recipes are declarative cleaning steps from a fixed whitelist; Claude drafts them, a test run checks them, and
        only recipes you approve ever run. Approving commits{" "}
        <code>worker/recipes/&lt;source&gt;.v&lt;N&gt;.yaml</code>.
      </p>
      {groups.map(([title, list, help]) =>
        list.length ? (
          <section key={title}>
            <h2>
              {title} <span className="small muted">({list.length})</span>
            </h2>
            {help && <p className="small muted">{help}</p>}
            {list.map((r) => (
              <RecipeCard key={r.id} r={r} />
            ))}
          </section>
        ) : null,
      )}
      {!recipes.length && <p>No recipes yet.</p>}
    </>
  );
}
