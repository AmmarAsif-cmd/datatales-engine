/** Weekly summary logic (P2.6). FAKE rows, fixed clock. */
import assert from "node:assert/strict";
import { test } from "node:test";

import { buildSummary, summaryText, type SummaryInput } from "../lib/logic/summary.ts";

const NOW = new Date("2026-10-12T09:00:00Z");
const RECENT = "2026-10-10T08:00:00Z";
const OLD = "2026-09-01T08:00:00Z";

const empty: SummaryInput = {
  stories: [],
  recipes: [],
  backlog: [],
  jobs: [],
  newDatasets: 0,
  newFindings: 0,
  weekSpend: 0,
  monthSpend: 0,
  budget: 5,
};

const story = (over: Partial<SummaryInput["stories"][number]>) => ({
  slug: "fake-story",
  headline: "Fake headline",
  status: "draft" as const,
  verify_status: "passed" as const,
  created_at: OLD,
  published_at: null,
  ...over,
});

test("nothing waiting is all clear, and spend is always shown", () => {
  const s = buildSummary(empty, NOW);
  assert.equal(s.allClear, true);
  assert.equal(s.week.length, 1);
  assert.match(s.week[0].text, /£0\.00 this week · £0\.00 of £5\.00 this month \(0%\)/);
  assert.match(summaryText(s), /Nothing: all clear\./);
});

test("waiting items: stories, recipes and backlog, with plurals and examples", () => {
  const s = buildSummary(
    {
      ...empty,
      stories: [
        story({ headline: "A" }),
        story({ headline: "B" }),
        story({ headline: null, slug: "c-slug", verify_status: "failed" }),
        story({ status: "approved", headline: "D" }),
      ],
      recipes: [
        { status: "ready", approved_at: null, created_at: OLD, slug: "veh" },
        { status: "failed", approved_at: null, created_at: OLD, slug: "rents" },
        { status: "ready", approved_at: OLD, created_at: OLD, slug: "done" },
      ],
      backlog: [
        { title: "Suggested one", status: "suggested", error: null, source_slug: null, created_at: OLD, updated_at: OLD },
        { title: "Broken", status: "accepted", error: "no CSV", source_slug: null, created_at: OLD, updated_at: OLD },
        { title: "Waiting", status: "accepted", error: null, source_slug: null, created_at: OLD, updated_at: OLD },
      ],
    },
    NOW,
  );
  const texts = s.todo.map((l) => l.text);
  assert.deepEqual(texts, [
    "2 verified stories to review",
    "1 approved story waiting to be published",
    "1 recipe ready to approve",
    "1 suggested dataset to accept or reject",
    "1 story failed verification or drafting",
    "1 recipe failed its test run",
    "1 accepted dataset could not be added",
  ]);
  assert.deepEqual(s.todo[0].examples, ["A", "B"]);
  assert.deepEqual(s.todo[4].examples, ["c-slug"]); // falls back to the slug
  assert.equal(s.todo[6].tone, "bad");
});

test("the last 7 days: only recent rows count", () => {
  const s = buildSummary(
    {
      ...empty,
      stories: [
        story({ status: "published", published_at: RECENT, created_at: RECENT, headline: "New" }),
        story({ status: "published", published_at: OLD, headline: "Old" }),
      ],
      backlog: [
        { title: "Added", status: "ingested", error: null, source_slug: "veh", created_at: OLD, updated_at: RECENT },
        { title: "Found", status: "suggested", error: null, source_slug: null, created_at: RECENT, updated_at: RECENT },
      ],
      jobs: [
        { type: "pipeline", status: "failed", started_at: RECENT },
        { type: "pipeline", status: "failed", started_at: RECENT },
        { type: "discover", status: "succeeded", started_at: RECENT },
      ],
      newFindings: 12,
      weekSpend: 0.4,
      monthSpend: 4.5,
    },
    NOW,
  );
  const byText = Object.fromEntries(s.week.map((l) => [l.text, l]));
  assert.deepEqual(byText["1 story published"].examples, ["New"]);
  assert.ok(byText["1 new story draft"]);
  assert.ok(byText["12 new findings"]);
  assert.deepEqual(byText["1 dataset added to the pipeline"].examples, ["veh"]);
  assert.deepEqual(byText["1 dataset found by discovery"].examples, ["Found"]);
  assert.deepEqual(byText["2 jobs failed"].examples, ["pipeline"]);
  const spend = s.week.at(-1)!;
  assert.match(spend.text, /£0\.40 this week · £4\.50 of £5\.00 this month \(90%\)/);
  assert.equal(spend.tone, "warn");
});

test("examples are capped at three and the text form links to the dashboard", () => {
  const stories = ["A", "B", "C", "D"].map((h) => story({ headline: h }));
  const s = buildSummary({ ...empty, stories, monthSpend: 5 }, NOW);
  assert.deepEqual(s.todo[0].examples, ["A", "B", "C"]);
  assert.equal(s.week.at(-1)!.tone, "bad");
  const text = summaryText(s, "https://admin.datatales.co.uk");
  assert.match(text, /- 4 verified stories to review \(A; B; C\): https:\/\/admin\.datatales\.co\.uk\/stories/);
  assert.match(text, /Since 5 October:/);
});
