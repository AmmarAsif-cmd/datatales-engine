import "server-only";

import Anthropic from "@anthropic-ai/sdk";

import { db } from "./db";
import {
  budgetStatus,
  callClaude,
  LLMError,
  type BudgetStatus,
  type CallArgs,
  type CallResult,
  type LlmLog,
  type Sdk,
} from "./logic/llm.ts";

/** llm_calls in Supabase (service role, server only). */
export const supabaseLlmLog: LlmLog = {
  async insert(row) {
    const { data, error } = await db().from("llm_calls").insert(row).select("id").single<{ id: string }>();
    if (error) throw new LLMError(`could not log the Claude call: ${error.message}`);
    return data.id;
  },
  async update(id, fields) {
    const { error } = await db().from("llm_calls").update(fields).eq("id", id);
    if (error) throw new LLMError(`could not update the Claude call log: ${error.message}`);
  },
  async spendSince(since) {
    const { data, error } = await db()
      .from("llm_calls")
      .select("estimated_cost, status")
      .gte("created_at", since.toISOString());
    if (error) throw new LLMError(error.message);
    const rows = (data ?? []) as { estimated_cost: number | string | null; status: string }[];
    return {
      spent: rows.reduce((sum, r) => sum + Number(r.estimated_cost ?? 0), 0),
      calls: rows.filter((r) => r.status === "ok" || r.status === "invalid_output").length,
    };
  },
  async topupsSince(since) {
    const { data, error } = await db()
      .from("llm_budget_topups")
      .select("amount_gbp")
      .gte("month", since.toISOString().slice(0, 10));
    if (error) {
      if (/llm_budget_topups/.test(error.message)) return 0; // migration 0007 not run yet
      throw new LLMError(error.message);
    }
    return ((data ?? []) as { amount_gbp: number | string }[]).reduce((s, r) => s + Number(r.amount_gbp), 0);
  },
};

/** The key lives only in the Worker secret (or .dev.vars locally) and in this module. */
function apiKey(): string | null {
  return process.env.ANTHROPIC_API_KEY?.trim() || null;
}

export function claudeConfigured(): boolean {
  return apiKey() !== null;
}

let client: Sdk | null = null;
function sdk(): Sdk {
  const key = apiKey();
  if (!key) throw new LLMError("ANTHROPIC_API_KEY is not set on the Worker; use the copy-paste flow.");
  client ??= new Anthropic({ apiKey: key, maxRetries: 3 }) as unknown as Sdk;
  return client;
}

export function claude<T>(args: CallArgs<T>): Promise<CallResult<T>> {
  return callClaude({ log: supabaseLlmLog, sdk, key: apiKey() }, args);
}

export function claudeBudget(): Promise<BudgetStatus> {
  return budgetStatus(supabaseLlmLog, new Date());
}
