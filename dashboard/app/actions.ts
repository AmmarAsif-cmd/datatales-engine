"use server";

import { revalidatePath } from "next/cache";

import { AccessDenied, requireUser } from "@/lib/access";
import { dispatch, WORKFLOWS } from "@/lib/github";
import type { VerifyReport } from "@/lib/types";
import {
  loadStory,
  pasteNarration,
  reverifyStory,
  setStoryStatus,
  StoryOpError,
  validateClaims,
} from "@/lib/storyops";

export type ActionState = { ok: boolean; message: string; report?: VerifyReport | null };

const TEXT_FIELDS = ["headline", "hook", "summary", "body_md", "video_script"] as const;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function str(form: FormData, name: string): string {
  const v = form.get(name);
  return typeof v === "string" ? v : "";
}

/** Every action: check Access first, then turn expected errors into a message. */
async function guarded(fn: () => Promise<ActionState>): Promise<ActionState> {
  try {
    await requireUser();
    return await fn();
  } catch (e) {
    if (e instanceof AccessDenied) return { ok: false, message: `Not signed in: ${e.message}` };
    if (e instanceof StoryOpError) return { ok: false, message: e.message };
    return { ok: false, message: (e as Error).message || "Something went wrong" };
  }
}

function id(form: FormData, name: string): string {
  const v = str(form, name);
  if (!UUID.test(v)) throw new StoryOpError(`${name} is not a valid id`);
  return v;
}

export async function createStory(_prev: ActionState, form: FormData): Promise<ActionState> {
  return guarded(async () => {
    const ct = id(form, "clean_table_id");
    const candidate = str(form, "candidate");
    if (!/^[1-9]$/.test(candidate)) throw new StoryOpError("bad candidate number");
    await dispatch(WORKFLOWS.storyNew, { clean_table_id: ct, candidate });
    return {
      ok: true,
      message: "Story draft queued. It appears under Stories in about a minute.",
    };
  });
}

export async function pasteReply(_prev: ActionState, form: FormData): Promise<ActionState> {
  return guarded(async () => {
    const storyId = id(form, "story_id");
    const reply = str(form, "reply").trim();
    if (!reply) return { ok: false, message: "Paste Claude's JSON reply first." };
    const { report } = await pasteNarration(storyId, reply);
    revalidatePath(`/stories/${storyId}`);
    const passed = report.status === "passed";
    return {
      ok: passed,
      message: passed ? "Saved. Verification passed." : "Saved, but verification FAILED. See the report.",
      report: report as unknown as VerifyReport,
    };
  });
}

export async function saveEdits(_prev: ActionState, form: FormData): Promise<ActionState> {
  return guarded(async () => {
    const storyId = id(form, "story_id");
    const edits: Record<string, string> = {};
    for (const f of TEXT_FIELDS) edits[f] = str(form, f);
    let raw: unknown;
    try {
      raw = JSON.parse(str(form, "claims") || "[]");
    } catch (e) {
      return { ok: false, message: `Claims are not valid JSON: ${(e as Error).message}` };
    }
    const { report } = await reverifyStory(storyId, edits, validateClaims(raw));
    revalidatePath(`/stories/${storyId}`);
    const passed = report.status === "passed";
    return {
      ok: passed,
      message: passed ? "Saved and re-verified: passed." : "Saved, but verification FAILED.",
      report: report as unknown as VerifyReport,
    };
  });
}

export async function setStatus(_prev: ActionState, form: FormData): Promise<ActionState> {
  return guarded(async () => {
    const storyId = id(form, "story_id");
    const status = str(form, "status");
    const story = await setStoryStatus(storyId, status);
    revalidatePath(`/stories/${storyId}`);
    revalidatePath("/stories");
    if (status !== "approved") return { ok: true, message: `Story is now ${story.status}.` };
    try {
      await dispatch(WORKFLOWS.publish, { story_id: storyId });
    } catch (e) {
      return {
        ok: false,
        message: `Approved, but publishing could not start: ${(e as Error).message}. Use "Publish again".`,
      };
    }
    return {
      ok: true,
      message: "Approved. Publishing started: the site updates in a few minutes.",
    };
  });
}

export async function republish(_prev: ActionState, form: FormData): Promise<ActionState> {
  return guarded(async () => {
    const storyId = id(form, "story_id");
    const story = await loadStory(storyId);
    if (story.status !== "approved") throw new StoryOpError(`story is ${story.status}, not approved`);
    await dispatch(WORKFLOWS.publish, { story_id: storyId });
    return { ok: true, message: "Publishing started again." };
  });
}

export async function approveRecipe(_prev: ActionState, form: FormData): Promise<ActionState> {
  return guarded(async () => {
    const by = str(form, "by").trim();
    if (!/^[A-Za-z][A-Za-z .-]{1,79}$/.test(by)) {
      return { ok: false, message: "Enter your name (letters, spaces, dots and hyphens)." };
    }
    const source = str(form, "source");
    const version = str(form, "version");
    if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(source) || !/^[1-9]\d{0,3}$/.test(version)) {
      throw new StoryOpError("bad recipe reference");
    }
    await dispatch(WORKFLOWS.recipeApprove, { source, version, by });
    return { ok: true, message: `Approval of v${version} queued; the recipe file is committed by the workflow.` };
  });
}

export async function runPipeline(): Promise<ActionState> {
  return guarded(async () => {
    await dispatch(WORKFLOWS.pipeline);
    return { ok: true, message: "Pipeline started. Progress shows under Jobs and Automation runs." };
  });
}
