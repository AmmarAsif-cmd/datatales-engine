"use client";

import { useActionState } from "react";

import { type ActionState, decideBacklog } from "@/app/actions";

const initial: ActionState = { ok: true, message: "" };

/** Accept, or reject with an optional reason. Works on a phone: one row that wraps. */
export default function BacklogActions({ itemId, status }: { itemId: string; status: string }) {
  const [state, action, pending] = useActionState(decideBacklog, initial);
  return (
    <form action={action} className="row backlog-actions">
      <input type="hidden" name="item_id" value={itemId} />
      {status !== "accepted" && (
        <button type="submit" name="decision" value="accepted" disabled={pending}>
          Accept
        </button>
      )}
      {status !== "rejected" && (
        <>
          <input type="text" name="reason" placeholder="Reason (optional)" maxLength={500} />
          <button type="submit" name="decision" value="rejected" className="danger" disabled={pending}>
            Reject
          </button>
        </>
      )}
      {state.message && <span className={`msg ${state.ok ? "ok" : "bad"}`}>{state.message}</span>}
    </form>
  );
}
