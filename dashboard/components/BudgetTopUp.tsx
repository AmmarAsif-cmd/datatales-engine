"use client";

import { useActionState } from "react";

import { type ActionState, addBudgetTopUp } from "@/app/actions";

const initial: ActionState = { ok: true, message: "" };

/** "Add £5 this month" (llm_budget_topups); the server re-checks the monthly cap. */
export default function BudgetTopUp({
  amount,
  cap,
}: {
  amount: number;
  cap: number;
}) {
  const [state, action, pending] = useActionState(addBudgetTopUp, initial);
  return (
    <form action={action} className="row">
      <button type="submit" disabled={pending}>
        {pending ? "Adding…" : `Add £${amount.toFixed(2)} this month`}
      </button>
      {state.message ? (
        <span className={`msg ${state.ok ? "ok" : "bad"}`}>
          {state.message}
        </span>
      ) : (
        <span className="small muted">
          Up to £{cap.toFixed(2)} extra a month; resets on the 1st.
        </span>
      )}
    </form>
  );
}
