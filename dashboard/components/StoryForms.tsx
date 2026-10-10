"use client";

import { useActionState } from "react";

import { type ActionState, pasteReply, saveEdits, setStatus } from "@/app/actions";
import type { Story } from "@/lib/types";

const initial: ActionState = { ok: true, message: "" };

function Message({ state }: { state: ActionState }) {
  if (!state.message) return null;
  return <p className={`msg ${state.ok ? "ok" : "bad"}`}>{state.message}</p>;
}

export function PasteForm({ storyId, locked }: { storyId: string; locked: boolean }) {
  const [state, action, pending] = useActionState(pasteReply, initial);
  return (
    <form action={action}>
      <input type="hidden" name="story_id" value={storyId} />
      <label htmlFor="reply">Paste Claude&apos;s JSON reply</label>
      <textarea
        id="reply"
        name="reply"
        className="mono"
        rows={10}
        placeholder='{"headline": "...", "claims": [...]}'
        disabled={locked}
      />
      <div className="row" style={{ marginTop: "0.5rem" }}>
        <button type="submit" disabled={pending || locked}>
          {pending ? "Validating and verifying…" : "Save and verify"}
        </button>
        {locked && <span className="small muted">Approved or published stories are locked.</span>}
      </div>
      <Message state={state} />
    </form>
  );
}

const FIELDS: { name: keyof Story; label: string; rows: number }[] = [
  { name: "headline", label: "Headline (max 70 characters)", rows: 1 },
  { name: "hook", label: "Hook (one sentence)", rows: 2 },
  { name: "summary", label: "Summary (max 120 words)", rows: 5 },
  { name: "body_md", label: "Body, Markdown (max 400 words)", rows: 14 },
  { name: "video_script", label: "Video script (max 90 words)", rows: 4 },
];

export function EditForm({ story, claimsJson }: { story: Story; claimsJson: string }) {
  const [state, action, pending] = useActionState(saveEdits, initial);
  const locked = story.status === "approved" || story.status === "published";
  return (
    <form action={action}>
      <input type="hidden" name="story_id" value={story.id} />
      {FIELDS.map((f) => (
        <div key={f.name}>
          <label htmlFor={f.name}>{f.label}</label>
          <textarea
            id={f.name}
            name={f.name}
            rows={f.rows}
            defaultValue={(story[f.name] as string | null) ?? ""}
            disabled={locked}
            style={f.rows === 1 ? { minHeight: "auto" } : undefined}
          />
        </div>
      ))}
      <label htmlFor="claims">
        Claims (JSON). If you change a sentence above, change it here too.
      </label>
      <textarea
        id="claims"
        name="claims"
        className="mono"
        rows={12}
        defaultValue={claimsJson}
        disabled={locked}
      />
      <div className="row" style={{ marginTop: "0.5rem" }}>
        <button type="submit" disabled={pending || locked}>
          {pending ? "Re-verifying…" : "Save edits and re-verify"}
        </button>
      </div>
      <Message state={state} />
    </form>
  );
}

export function StatusButtons({ story }: { story: Story }) {
  const [state, action, pending] = useActionState(setStatus, initial);
  const canApprove = story.status === "draft" && story.verify_status === "passed";
  return (
    <form action={action}>
      <input type="hidden" name="story_id" value={story.id} />
      <div className="row">
        {story.status === "draft" && (
          <>
            <button
              type="submit"
              name="status"
              value="approved"
              disabled={pending || !canApprove}
              title={canApprove ? "" : "Only stories that passed verification can be approved"}
            >
              Approve
            </button>
            <button type="submit" name="status" value="rejected" className="danger" disabled={pending}>
              Reject
            </button>
          </>
        )}
        {(story.status === "approved" || story.status === "rejected") && (
          <button type="submit" name="status" value="draft" className="secondary" disabled={pending}>
            Back to draft
          </button>
        )}
        {story.status === "draft" && !canApprove && (
          <span className="small muted">Approval needs a passed verification.</span>
        )}
      </div>
      <Message state={state} />
    </form>
  );
}
