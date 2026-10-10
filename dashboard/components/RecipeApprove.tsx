"use client";

import { useActionState } from "react";

import { type ActionState, approveRecipe } from "@/app/actions";

const initial: ActionState = { ok: true, message: "" };

export default function RecipeApprove({ source, version }: { source: string; version: number }) {
  const [state, action, pending] = useActionState(approveRecipe, initial);
  return (
    <form action={action} className="row">
      <input type="hidden" name="source" value={source} />
      <input type="hidden" name="version" value={version} />
      <input type="text" name="by" placeholder="Your name" style={{ maxWidth: "14rem" }} />
      <button type="submit" disabled={pending}>
        {pending ? "Approving…" : `Approve v${version}`}
      </button>
      {state.message && <span className={`msg ${state.ok ? "ok" : "bad"}`}>{state.message}</span>}
    </form>
  );
}
