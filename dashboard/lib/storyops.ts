import "server-only";

import { db } from "./db";
import { claude } from "./llm";
import { BudgetReached, InvalidOutput, untrusted } from "./logic/llm.ts";
import {
  NarrationError,
  narrationData,
  narrationInstructions,
  normaliseApiReply,
  parseChecks,
  parseNarration,
  STORY_REQUEST,
} from "./logic/narrate.ts";
import NARRATION_SCHEMA from "./narration-schema.json" with { type: "json" };
import { slugify } from "./logic/stories.ts";
import { chartText, type Claim, type Report, TEXT_FIELDS, type TextField, verifyText } from "./logic/verify.ts";
import type { Story } from "./types";

/**
 * Story operations for the deployed dashboard (no Python on Workers). The text logic is the
 * golden-tested TypeScript port; the database enforces the approval rule as well
 * (constraint stories_verified_before_approval).
 */

export class StoryOpError extends Error {}

const LOCKED = new Set(["approved", "published"]);

export async function loadStory(id: string): Promise<Story> {
  const { data, error } = await db().from("stories").select("*").eq("id", id).maybeSingle<Story>();
  if (error) throw new StoryOpError(error.message);
  if (!data) throw new StoryOpError("story not found");
  return data;
}

async function uniqueSlug(base: string, storyId: string): Promise<string> {
  let slug = base;
  for (let n = 2; n < 100; n++) {
    const { data, error } = await db().from("stories").select("id").eq("slug", slug).limit(1);
    if (error) throw new StoryOpError(error.message);
    if (!data.length || data[0].id === storyId) return slug;
    slug = `${base.slice(0, 75)}-${n}`;
  }
  throw new StoryOpError("could not find a free slug");
}

async function save(id: string, fields: Record<string, unknown>): Promise<Story> {
  const { data, error } = await db().from("stories").update(fields).eq("id", id).select("*").single<Story>();
  if (error) throw new StoryOpError(error.message);
  return data;
}

type Narration = ReturnType<typeof parseNarration>;

/** Text fields that are verified, including every chart title and annotation. */
function storyFields(story: Story, override: Partial<Record<TextField, string>> = {}): Record<TextField, string> {
  const base = Object.fromEntries(
    TEXT_FIELDS.map((f) => [f, f === "chart_text" ? chartText(story.chart_spec) : ((story[f as keyof Story] as string | null) ?? "")]),
  ) as Record<TextField, string>;
  return { ...base, ...override };
}

/** Save a validated narration and verify it. Shared by copy-paste and Claude drafting. */
/** Verify a validated narration against a story's data without saving anything. */
function checkNarration(story: Story, narration: Narration) {
  const fields = {
    headline: narration.headline,
    hook: narration.hook,
    summary: narration.summary,
    body_md: narration.body_md,
    video_script: narration.video_script,
  };
  const clean = (c: object) => Object.fromEntries(Object.entries(c).filter(([, v]) => v !== null && v !== undefined));
  const spec: Record<string, unknown> = clean(narration.chart_spec);
  if (narration.more_charts.length) spec.more_charts = narration.more_charts.map(clean);
  const report = verifyText(
    storyFields(story, { ...fields, chart_text: chartText(spec) }),
    story.numbers as never,
    narration.claims,
    story.chart_data ?? [],
  );
  return { fields, spec, report };
}

/** Verify and save. Shared by copy-paste and Claude drafting. */
async function applyNarration(
  story: Story,
  narration: Narration,
  draftedBy: "manual" | "claude",
): Promise<{ story: Story; report: Report }> {
  if (LOCKED.has(story.status)) throw new StoryOpError(`story is ${story.status}; it can no longer be edited`);
  const { fields, spec, report } = checkNarration(story, narration);
  const saved = await save(story.id, {
    ...fields,
    // set once from the first headline, then fixed: a published URL never changes
    slug: story.slug.startsWith("draft-") ? await uniqueSlug(slugify(narration.headline), story.id) : story.slug,
    chart_spec: spec,
    verify_status: report.status,
    verify_report: report,
    status: "draft",
    drafted_by: draftedBy,
    draft_note: null,
  });
  return { story: saved, report };
}

export async function pasteNarration(id: string, reply: string): Promise<{ story: Story; report: Report }> {
  const story = await loadStory(id);
  if (LOCKED.has(story.status)) throw new StoryOpError(`story is ${story.status}; it can no longer be edited`);
  let narration;
  try {
    narration = parseNarration(reply, story.chart_data ?? []);
  } catch (e) {
    if (e instanceof NarrationError) throw new StoryOpError(e.message);
    throw e;
  }
  return applyNarration(story, narration, "manual");
}

// ---- Claude drafting (same flow as worker/datatales/autodraft.py) ----

export const NOTE_BUDGET = "Claude budget reached this month: use Copy prompt / Paste result.";
export const NOTE_REJECTED =
  "Claude's replies were rejected twice (incomplete or malformed), so nothing was changed. Try Regenerate with Claude again, or use Copy prompt / Paste result.";
export const NOTE_KEPT =
  "Claude's new draft failed verification twice, so your verified text was kept unchanged. Try Regenerate with Claude again, or edit by hand.";
export const NOTE_FAILED =
  "Claude's draft failed verification twice. The report shows what to fix; edit and re-verify, regenerate, or use Copy prompt / Paste result.";
const MAX_ATTEMPTS = 2;

function reportFeedback(report: Report): string {
  const lines: string[] = [];
  if (report.uncovered.length) {
    const sentences = new Set(report.uncovered.map((u) => u.sentence));
    lines.push(
      `${report.uncovered.length} number(s) or rank word(s) in ${sentences.size} sentence(s) have no claim, but you gave only ${report.claims.length} claim(s). Add one claim for EVERY sentence that contains a number or a rank word, copied exactly, in every field (headline, hook, summary, body_md, video_script, chart titles).`,
    );
  }
  const keep: Record<string, unknown> = {
    unmatched: report.unmatched,
    years_out_of_range: report.years_out_of_range,
    uncovered: report.uncovered,
    format_issues: report.format_issues,
    failed_claims: report.claims.filter((c) => c.status !== "ok"),
  };
  lines.push(JSON.stringify(Object.fromEntries(Object.entries(keep).filter(([, v]) => (v as unknown[]).length))));
  return lines.join("\n");
}

export type DraftOutcome = { status: "passed" | "failed" | "budget" | "error"; message: string; story?: Story };

export async function draftWithClaude(id: string): Promise<DraftOutcome> {
  let story = await loadStory(id);
  if (LOCKED.has(story.status)) throw new StoryOpError(`story is ${story.status}; it can no longer be edited`);
  const chartData = story.chart_data ?? [];
  const base = untrusted("story_data", narrationData(story.numbers ?? {}, chartData, story.chart_spec ?? {}));
  let feedback = "";
  let savedText = false; // did Claude's narration get saved on the story in this run?
  // A redraft must never make a story worse: verified text stays unless the new draft passes.
  const protect = story.verify_status === "passed" && !!story.body_md;
  let checked = false;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    let narration: Narration;
    try {
      const res = await claude({
        task: "story",
        instructions: narrationInstructions(),
        data: feedback ? `${base}\n\n${feedback}` : base,
        schema: NARRATION_SCHEMA as Record<string, unknown>,
        validate: (value) => parseNarration(JSON.stringify(normaliseApiReply(value)), chartData),
        relatedId: id,
        request: STORY_REQUEST,
      });
      narration = res.value;
    } catch (e) {
      if (e instanceof BudgetReached) {
        await save(id, { draft_note: NOTE_BUDGET });
        return { status: "budget", message: e.message };
      }
      if (e instanceof InvalidOutput) {
        feedback = `Your previous reply was rejected for this reason; return the whole reply again, fixed:\n${untrusted("rejection", e.message)}`;
        continue;
      }
      const message = (e as Error).message;
      await save(id, { draft_note: `Claude error: ${message}`.slice(0, 500) });
      return { status: "error", message };
    }
    let { report } = checkNarration(story, narration);
    checked = true;
    if (report.status === "passed" || !protect) {
      const applied = await applyNarration(story, narration, "claude");
      story = applied.story;
      report = applied.report;
      savedText = true;
    }
    if (report.status === "passed") return { status: "passed", message: `Verified (${report.checked} numbers checked).`, story };
    feedback =
      "Your previous draft failed verification. Fix every problem in this report and return the whole reply again (all fields, all claims):\n" +
      untrusted("verify_report", reportFeedback(report));
  }
  if (protect && checked) {
    const saved = await save(id, { draft_note: NOTE_KEPT });
    return { status: "failed", message: NOTE_KEPT, story: saved };
  }
  if (savedText) {
    const saved = await save(id, { status: "failed", draft_note: NOTE_FAILED });
    return { status: "failed", message: NOTE_FAILED, story: saved };
  }
  // Both replies were rejected before verification: the story keeps whatever it had.
  const saved = await save(id, { draft_note: NOTE_REJECTED });
  return { status: "failed", message: NOTE_REJECTED, story: saved };
}

export function validateClaims(raw: unknown): Claim[] {
  if (!Array.isArray(raw)) throw new StoryOpError("claims must be a JSON list");
  return raw.map((c, i) => {
    if (!c || typeof c !== "object") throw new StoryOpError(`claim ${i + 1} must be an object`);
    const { sentence, keys = [], checks = [], ...extra } = c as Record<string, unknown>;
    if (Object.keys(extra).length) throw new StoryOpError(`claim ${i + 1} has unknown fields`);
    if (typeof sentence !== "string" || sentence.trim().length < 5) {
      throw new StoryOpError(`claim ${i + 1} needs a sentence`);
    }
    if (!Array.isArray(keys) || !keys.every((k) => typeof k === "string")) {
      throw new StoryOpError(`claim ${i + 1}: keys must be a list of strings`);
    }
    const problems: [string, string][] = [];
    const parsed = parseChecks(checks, "checks", problems);
    if (problems.length) {
      throw new StoryOpError(`claim ${i + 1}: ${problems.map(([l, m]) => `${l}: ${m}`).join("; ")}`);
    }
    if (!keys.length && !parsed.length) throw new StoryOpError(`claim ${i + 1} needs keys or checks`);
    return { sentence: sentence.trim(), keys: keys.map((k) => (k as string).trim()), checks: parsed };
  });
}

export async function reverifyStory(
  id: string,
  edits: Partial<Record<TextField, string>>,
  claims: Claim[],
): Promise<{ story: Story; report: Report }> {
  const story = await loadStory(id);
  if (LOCKED.has(story.status)) throw new StoryOpError(`story is ${story.status}; it can no longer be edited`);
  const clean = Object.fromEntries(
    TEXT_FIELDS.filter((f) => f !== "chart_text" && f in edits).map((f) => [f, edits[f]!.trim()]),
  );
  const report = verifyText(storyFields(story, clean), story.numbers as never, claims, story.chart_data ?? []);
  const saved = await save(id, { ...clean, verify_status: report.status, verify_report: report });
  return { story: saved, report };
}

const TRANSITIONS: Record<string, string[]> = {
  draft: ["approved", "rejected"],
  failed: ["draft", "rejected"], // Claude's draft failed verification; fix by hand
  rejected: ["draft"],
  approved: ["draft"],
  published: ["draft"], // "Revise": the live page stays up until the story is republished
};

export async function setStoryStatus(id: string, status: string): Promise<Story> {
  const story = await loadStory(id);
  if (!(TRANSITIONS[story.status] ?? []).includes(status)) {
    throw new StoryOpError(`cannot move a ${story.status} story to ${status}`);
  }
  if (status === "approved" && story.verify_status !== "passed") {
    throw new StoryOpError("only stories that passed verification can be approved");
  }
  // DB rule stories_published_at_set: published_at only while published
  return save(id, story.status === "published" ? { status, published_at: null } : { status });
}
