import Link from "next/link";

import { db, must } from "@/lib/db";
import { claudeBudget, supabaseLlmLog } from "@/lib/llm";
import {
  buildSummary,
  type BacklogRow,
  type JobRow,
  type Line,
  type RecipeRow,
  type StoryRow,
  windowStart,
} from "@/lib/logic/summary.ts";

async function count(table: string, since: Date): Promise<number> {
  const { count: n, error } = await db()
    .from(table)
    .select("id", { count: "exact", head: true })
    .gte("created_at", since.toISOString());
  if (error) throw new Error(error.message);
  return n ?? 0;
}

function Lines({ lines }: { lines: Line[] }) {
  return (
    <ul className="summary">
      {lines.map((l, i) => (
        <li key={i}>
          <Link href={l.href}>
            {l.tone === "plain" ? l.text : <span className={`badge ${l.tone}`}>{l.text}</span>}
          </Link>
          {l.examples.length > 0 && <span className="small muted"> · {l.examples.join(" · ")}</span>}
        </li>
      ))}
    </ul>
  );
}

/** Top of the overview: what needs you now, and what happened in the last 7 days. */
export default async function WeeklySummary() {
  const now = new Date();
  const since = windowStart(now);
  let summary;
  try {
    const [stories, recipes, backlog, jobs, newDatasets, newFindings, week, month] = await Promise.all([
      must<StoryRow[]>(
        db()
          .from("stories")
          .select("slug, headline, status, verify_status, created_at, published_at")
          .or(`status.in.(draft,approved,failed),created_at.gte.${since.toISOString()},published_at.gte.${since.toISOString()}`)
          .limit(500),
      ),
      must<(Omit<RecipeRow, "slug"> & { sources: { slug: string } | null })[]>(
        db()
          .from("recipes")
          .select("status, approved_at, created_at, sources(slug)")
          .or(`approved_at.is.null,created_at.gte.${since.toISOString()}`)
          .limit(500),
      ),
      must<BacklogRow[]>(
        db()
          .from("dataset_backlog")
          .select("title, status, error, source_slug, created_at, updated_at")
          .or(`status.in.(suggested,accepted),updated_at.gte.${since.toISOString()}`)
          .order("score", { ascending: false, nullsFirst: false })
          .limit(500),
      ),
      must<JobRow[]>(db().from("jobs").select("type, status, started_at").gte("started_at", since.toISOString())),
      count("datasets", since),
      count("findings", since),
      supabaseLlmLog.spendSince(since),
      claudeBudget(),
    ]);
    summary = buildSummary(
      {
        stories,
        recipes: recipes.map((r) => ({ ...r, slug: r.sources?.slug ?? "?" })),
        backlog,
        jobs,
        newDatasets,
        newFindings,
        weekSpend: week.spent,
        monthSpend: month.spent,
        budget: month.budget,
      },
      now,
    );
  } catch (e) {
    return (
      <div className="panel">
        <h2 className="first">This week</h2>
        <p className="msg bad">Could not build the weekly summary: {(e as Error).message}</p>
      </div>
    );
  }
  return (
    <div className="panel">
      <h2 className="first">This week</h2>
      <h3>Waiting for you</h3>
      {summary.allClear ? <p className="msg ok">Nothing waiting: all clear.</p> : <Lines lines={summary.todo} />}
      <h3>Last 7 days</h3>
      <Lines lines={summary.week} />
    </div>
  );
}
