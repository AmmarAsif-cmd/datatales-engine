"use client";

import { useActionState } from "react";

import { type ActionState, createStory, runDiscovery, runPipeline } from "@/app/actions";

const initial: ActionState = { ok: true, message: "" };

function Msg({ s }: { s: ActionState }) {
  return s.message ? <p className={`msg ${s.ok ? "ok" : "bad"}`}>{s.message}</p> : null;
}

export function CreateStoryButton({ cleanTableId, candidate }: { cleanTableId: string; candidate: number }) {
  const [state, action, pending] = useActionState(createStory, initial);
  return (
    <form action={action}>
      <input type="hidden" name="clean_table_id" value={cleanTableId} />
      <input type="hidden" name="candidate" value={candidate} />
      <button type="submit" className="secondary" disabled={pending}>
        {pending ? "Queuing…" : "Create story"}
      </button>
      <Msg s={state} />
    </form>
  );
}

export function RunDiscoveryButton() {
  const [state, action, pending] = useActionState(runDiscovery, initial);
  return (
    <form action={action}>
      <button type="submit" className="secondary" disabled={pending}>
        {pending ? "Starting…" : "Find new datasets now"}
      </button>
      <Msg s={state} />
    </form>
  );
}

export function RunPipelineButton() {
  const [state, action, pending] = useActionState(runPipeline, initial);
  return (
    <form action={action}>
      <button type="submit" disabled={pending}>
        {pending ? "Starting…" : "Run pipeline now"}
      </button>
      <Msg s={state} />
    </form>
  );
}
