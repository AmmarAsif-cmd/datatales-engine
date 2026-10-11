import { claudeBudget, claudeConfigured } from "@/lib/llm";

/** This month's Claude API spend vs budget (from llm_calls), with a banner when reached. */
export default async function ClaudeUsage({ compact = false }: { compact?: boolean }) {
  let status;
  try {
    status = await claudeBudget();
  } catch (e) {
    const missing = /llm_calls/.test((e as Error).message);
    return (
      <div className="panel">
        <h2 className="first">Claude API</h2>
        <p className="msg bad">
          {missing
            ? "The llm_calls table is missing: run supabase/migrations/0002_llm_calls.sql in the Supabase SQL Editor."
            : `Could not read Claude usage: ${(e as Error).message}`}
        </p>
      </div>
    );
  }
  const pct = status.budget ? Math.min(100, (status.spent / status.budget) * 100) : 100;
  if (compact) {
    // story pages: only speak up when Claude cannot draft
    if (status.reached) {
      return (
        <p className="msg bad" role="alert">
          Monthly Claude budget reached (£{status.spent.toFixed(2)} of £{status.budget.toFixed(2)}). Use Copy prompt /
          Paste result until next month.
        </p>
      );
    }
    return claudeConfigured() ? null : (
      <p className="msg bad">ANTHROPIC_API_KEY is not set on this Worker: use Copy prompt / Paste result.</p>
    );
  }
  return (
    <div className="panel">
      <h2 className="first">Claude API</h2>
      {status.reached && (
        <p className="msg bad" role="alert">
          Monthly budget reached. Automatic drafting is paused until next month; use Copy prompt / Paste
          result instead (or raise <code>monthly_budget_gbp</code> in worker/config/llm.yaml).
        </p>
      )}
      {!claudeConfigured() && (
        <p className="msg bad">ANTHROPIC_API_KEY is not set on this Worker: Claude buttons will fall back to copy-paste.</p>
      )}
      <p>
        <b>£{status.spent.toFixed(2)}</b> of £{status.budget.toFixed(2)} this month · {status.calls} call
        {status.calls === 1 ? "" : "s"}
      </p>
      <div className="meter" aria-label={`${pct.toFixed(0)}% of the monthly budget used`}>
        <span style={{ width: `${pct}%` }} className={status.reached ? "full" : pct > 80 ? "high" : ""} />
      </div>
      <p className="small muted">Estimated from token usage logged in llm_calls (UTC calendar month).</p>
    </div>
  );
}
