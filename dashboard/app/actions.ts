"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import type { Story, VerifyReport } from "@/lib/types";
import { runWorker } from "@/lib/worker";

export type ActionState = { ok: boolean; message: string; report?: VerifyReport | null };

const TEXT_FIELDS = ["headline", "hook", "summary", "body_md", "video_script"] as const;

function str(form: FormData, name: string): string {
  const v = form.get(name);
  return typeof v === "string" ? v : "";
}

export async function createStory(form: FormData): Promise<void> {
  const res = await runWorker<Story>("story-new", {
    clean_table_id: str(form, "clean_table_id"),
    candidate: Number(str(form, "candidate")),
  });
  if (!res.ok) throw new Error(res.error);
  revalidatePath("/stories");
  redirect(`/stories/${res.data.id}`);
}

export async function pasteReply(_prev: ActionState, form: FormData): Promise<ActionState> {
  const storyId = str(form, "story_id");
  const reply = str(form, "reply").trim();
  if (!reply) return { ok: false, message: "Paste Claude's JSON reply first." };
  const res = await runWorker<{ story: Story; report: VerifyReport }>("story-paste", {
    story_id: storyId,
    reply,
  });
  revalidatePath(`/stories/${storyId}`);
  if (!res.ok) return { ok: false, message: res.error };
  const passed = res.data.report.status === "passed";
  return {
    ok: passed,
    message: passed
      ? "Saved. Verification passed."
      : "Saved, but verification FAILED. See the report below.",
    report: res.data.report,
  };
}

export async function saveEdits(_prev: ActionState, form: FormData): Promise<ActionState> {
  const storyId = str(form, "story_id");
  const edits: Record<string, string> = {};
  for (const f of TEXT_FIELDS) edits[f] = str(form, f);
  let claims: unknown;
  try {
    claims = JSON.parse(str(form, "claims") || "[]");
  } catch (e) {
    return { ok: false, message: `Claims are not valid JSON: ${(e as Error).message}` };
  }
  if (!Array.isArray(claims)) return { ok: false, message: "Claims must be a JSON list." };
  const res = await runWorker<{ story: Story; report: VerifyReport }>("story-reverify", {
    story_id: storyId,
    edits,
    claims,
  });
  revalidatePath(`/stories/${storyId}`);
  if (!res.ok) return { ok: false, message: res.error };
  const passed = res.data.report.status === "passed";
  return {
    ok: passed,
    message: passed ? "Saved and re-verified: passed." : "Saved, but verification FAILED.",
    report: res.data.report,
  };
}

export async function setStatus(_prev: ActionState, form: FormData): Promise<ActionState> {
  const storyId = str(form, "story_id");
  const status = str(form, "status");
  const res = await runWorker<Story>("story-status", { story_id: storyId, status });
  revalidatePath(`/stories/${storyId}`);
  revalidatePath("/stories");
  if (!res.ok) return { ok: false, message: res.error };
  return { ok: true, message: `Story is now ${res.data.status}.` };
}

export async function approveRecipe(_prev: ActionState, form: FormData): Promise<ActionState> {
  const by = str(form, "by").trim();
  if (!by) return { ok: false, message: "Enter your name to approve." };
  const res = await runWorker<{ version: number; file: string }>("recipe-approve", {
    source: str(form, "source"),
    version: Number(str(form, "version")),
    by,
  });
  revalidatePath("/recipes");
  if (!res.ok) return { ok: false, message: res.error };
  return { ok: true, message: `Approved v${res.data.version}. Commit ${res.data.file}.` };
}
