import "server-only";

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

import { supabaseEnv } from "./env";

let client: SupabaseClient | null = null;

/** Service-role client. Server-only: imported only by server components and actions. */
export function db(): SupabaseClient {
  if (!client) {
    const { url, key } = supabaseEnv();
    client = createClient(url, key, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
  }
  return client;
}

export async function must<T>(
  // Supabase infers joined rows as arrays without generated types; callers declare the real shape.
  query: PromiseLike<{ data: unknown; error: { message: string } | null }>,
): Promise<T> {
  const { data, error } = await query;
  if (error) throw new Error(error.message);
  return data as T;
}
