"use client";

import { useActionState } from "react";

import { type ActionState, draftRecipe, rejectRecipe } from "@/app/actions";

const initial: ActionState = { ok: true, message: "" };

export function RecipeReject({ recipeId }: { recipeId: string }) {
  const [state, action, pending] = useActionState(rejectRecipe, initial);
  return (
    <form action={action} className="row">
      <input type="hidden" name="recipe_id" value={recipeId} />
      <input type="text" name="note" placeholder="Why? (optional)" maxLength={500} style={{ maxWidth: "20rem" }} />
      <button type="submit" className="danger" disabled={pending}>
        {pending ? "Rejecting…" : "Reject"}
      </button>
      {state.message && <span className={`msg ${state.ok ? "ok" : "bad"}`}>{state.message}</span>}
    </form>
  );
}

export function RecipeDraftButton({ datasetId, label = "Draft with Claude" }: { datasetId: string; label?: string }) {
  const [state, action, pending] = useActionState(draftRecipe, initial);
  return (
    <form action={action} className="row">
      <input type="hidden" name="dataset_id" value={datasetId} />
      <button type="submit" className="secondary" disabled={pending}>
        {pending ? "Starting…" : label}
      </button>
      {state.message && <span className={`msg ${state.ok ? "ok" : "bad"}`}>{state.message}</span>}
    </form>
  );
}
