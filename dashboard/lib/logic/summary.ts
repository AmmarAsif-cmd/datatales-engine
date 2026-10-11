/**
 * Weekly summary (P2.6): what needs you now, and what happened in the last 7 days.
 * Pure: the overview page passes in rows it read; `summaryText` gives the same content as
 * plain text (ready for an email once a sending method is chosen).
 */

export const WINDOW_DAYS = 7;

export type StoryRow = {
  slug: string;
  headline: string | null;
  status: "draft" | "approved" | "rejected" | "published" | "failed";
  verify_status: "pending" | "passed" | "failed";
  created_at: string;
  published_at: string | null;
};
export type RecipeRow = {
  status: "draft" | "ready" | "failed" | "rejected";
  approved_at: string | null;
  created_at: string;
  slug: string;
};
export type BacklogRow = {
  title: string;
  status: "suggested" | "accepted" | "rejected" | "ingested";
  error: string | null;
  source_slug: string | null;
  created_at: string;
  updated_at: string;
};
export type JobRow = { type: string; status: string; started_at: string };

export type SummaryInput = {
  stories: StoryRow[];
  recipes: RecipeRow[];
  backlog: BacklogRow[];
  jobs: JobRow[]; // jobs started in the window
  newDatasets: number; // raw files ingested in the window
  newFindings: number; // findings created in the window
  weekSpend: number; // GBP, llm_calls in the window
  monthSpend: number;
  budget: number;
};

export type Tone = "ok" | "warn" | "bad" | "plain";
export type Line = { text: string; href: string; tone: Tone; examples: string[] };
export type Summary = { since: Date; todo: Line[]; week: Line[]; allClear: boolean };

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const after = (iso: string | null, since: Date) => !!iso && new Date(iso).getTime() >= since.getTime();
const titles = (xs: string[], max = 3) => xs.slice(0, max);
const storyName = (s: StoryRow) => s.headline?.trim() || s.slug;

export function windowStart(now: Date, days = WINDOW_DAYS): Date {
  return new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
}

export function buildSummary(input: SummaryInput, now: Date): Summary {
  const since = windowStart(now);
  const todo: Line[] = [];
  const week: Line[] = [];
  const add = (list: Line[], n: number, text: string, href: string, tone: Tone, examples: string[] = []) => {
    if (n > 0) list.push({ text, href, tone, examples: titles(examples) });
  };

  // ---- waiting for you (current state) ----
  const drafts = input.stories.filter((s) => s.status === "draft");
  const toReview = drafts.filter((s) => s.verify_status === "passed");
  const needWork = [...drafts.filter((s) => s.verify_status !== "passed"), ...input.stories.filter((s) => s.status === "failed")];
  const toPublish = input.stories.filter((s) => s.status === "approved");
  const open = input.recipes.filter((r) => !r.approved_at);
  const recipesReady = open.filter((r) => r.status === "ready");
  const recipesFailed = open.filter((r) => r.status === "failed");
  const suggested = input.backlog.filter((b) => b.status === "suggested");
  const stuck = input.backlog.filter((b) => b.status === "accepted" && b.error);

  add(todo, toReview.length, `${plural(toReview.length, "verified story", "verified stories")} to review`, "/stories", "warn", toReview.map(storyName));
  add(todo, toPublish.length, `${plural(toPublish.length, "approved story", "approved stories")} waiting to be published`, "/stories", "warn", toPublish.map(storyName));
  add(todo, recipesReady.length, `${plural(recipesReady.length, "recipe")} ready to approve`, "/recipes", "warn", recipesReady.map((r) => r.slug));
  add(todo, suggested.length, `${plural(suggested.length, "suggested dataset")} to accept or reject`, "/datasets/suggested", "warn", suggested.map((b) => b.title));
  add(todo, needWork.length, `${plural(needWork.length, "story", "stories")} failed verification or drafting`, "/stories", "bad", needWork.map(storyName));
  add(todo, recipesFailed.length, `${plural(recipesFailed.length, "recipe")} failed its test run`, "/recipes", "bad", recipesFailed.map((r) => r.slug));
  add(todo, stuck.length, `${plural(stuck.length, "accepted dataset")} could not be added`, "/datasets/suggested", "bad", stuck.map((b) => b.title));

  // ---- the last 7 days ----
  const published = input.stories.filter((s) => s.status === "published" && after(s.published_at, since));
  const drafted = input.stories.filter((s) => after(s.created_at, since));
  const added = input.backlog.filter((b) => b.status === "ingested" && after(b.updated_at, since));
  const found = input.backlog.filter((b) => after(b.created_at, since) && b.status !== "ingested");
  const newRecipes = input.recipes.filter((r) => after(r.created_at, since));
  const failedJobs = input.jobs.filter((j) => j.status === "failed");

  add(week, published.length, `${plural(published.length, "story", "stories")} published`, "/stories", "ok", published.map(storyName));
  add(week, drafted.length, `${plural(drafted.length, "new story draft")}`, "/stories", "plain", drafted.map(storyName));
  add(week, input.newFindings, `${plural(input.newFindings, "new finding")}`, "/findings", "plain");
  add(week, added.length, `${plural(added.length, "dataset")} added to the pipeline`, "/datasets/suggested", "ok", added.map((b) => b.source_slug ?? b.title));
  add(week, found.length, `${plural(found.length, "dataset")} found by discovery`, "/datasets/suggested", "plain", found.map((b) => b.title));
  add(week, newRecipes.length, `${plural(newRecipes.length, "recipe")} drafted`, "/recipes", "plain", newRecipes.map((r) => r.slug));
  add(week, input.newDatasets, `${plural(input.newDatasets, "new data file")} ingested`, "/datasets", "plain");
  add(week, failedJobs.length, `${plural(failedJobs.length, "job")} failed`, "/datasets", "bad", [...new Set(failedJobs.map((j) => j.type))]);
  const pct = input.budget > 0 ? Math.round((input.monthSpend / input.budget) * 100) : 100;
  week.push({
    text: `Claude: £${input.weekSpend.toFixed(2)} this week · £${input.monthSpend.toFixed(2)} of £${input.budget.toFixed(2)} this month (${pct}%)`,
    href: "/",
    tone: pct >= 100 ? "bad" : pct > 80 ? "warn" : "plain",
    examples: [],
  });

  return { since, todo, week, allClear: todo.length === 0 };
}

/** The same summary as plain text (UK English), e.g. for an email body. */
export function summaryText(s: Summary, baseUrl = ""): string {
  const fmt = (l: Line) => {
    const ex = l.examples.length ? ` (${l.examples.join("; ")})` : "";
    return `- ${l.text}${ex}${baseUrl ? `: ${baseUrl}${l.href}` : ""}`;
  };
  const since = s.since.toLocaleDateString("en-GB", { day: "numeric", month: "long", timeZone: "UTC" });
  return [
    "DataTales weekly summary",
    "",
    "Waiting for you:",
    ...(s.allClear ? ["- Nothing: all clear."] : s.todo.map(fmt)),
    "",
    `Since ${since}:`,
    ...s.week.map(fmt),
  ].join("\n");
}
