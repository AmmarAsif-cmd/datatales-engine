import "server-only";

import { db } from "./db";
import { NarrationError, parseChecks, parseNarration } from "./logic/narrate.ts";
import { slugify } from "./logic/stories.ts";
import { type Claim, type Report, TEXT_FIELDS, type TextField, verifyText } from "./logic/verify.ts";
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
  const fields = {
    headline: narration.headline,
    hook: narration.hook,
    summary: narration.summary,
    body_md: narration.body_md,
    video_script: narration.video_script,
  };
  const report = verifyText(fields, story.numbers as never, narration.claims, story.chart_data ?? []);
  const spec = Object.fromEntries(Object.entries(narration.chart_spec).filter(([, v]) => v !== null && v !== undefined));
  const saved = await save(id, {
    ...fields,
    // set once from the first headline, then fixed: a published URL never changes
    slug: story.slug.startsWith("draft-") ? await uniqueSlug(slugify(narration.headline), id) : story.slug,
    chart_spec: spec,
    verify_status: report.status,
    verify_report: report,
    status: "draft",
  });
  return { story: saved, report };
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
  const clean = Object.fromEntries(TEXT_FIELDS.filter((f) => f in edits).map((f) => [f, edits[f]!.trim()]));
  const fields = Object.fromEntries(TEXT_FIELDS.map((f) => [f, (clean[f] ?? story[f] ?? "") as string]));
  const report = verifyText(fields, story.numbers as never, claims, story.chart_data ?? []);
  const saved = await save(id, { ...clean, verify_status: report.status, verify_report: report });
  return { story: saved, report };
}

const TRANSITIONS: Record<string, string[]> = {
  draft: ["approved", "rejected"],
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
