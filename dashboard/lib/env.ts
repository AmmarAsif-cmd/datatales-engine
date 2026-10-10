import "server-only";

/** Server-only settings. Never prefix these with NEXT_PUBLIC_: they must not reach the browser. */
export function supabaseEnv(): { url: string; key: string } {
  const url = process.env.SUPABASE_URL?.trim();
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY?.trim();
  if (!url || !key) {
    throw new Error(
      "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in dashboard/.env.local (see .env.example).",
    );
  }
  if (!url.startsWith("https://")) throw new Error("SUPABASE_URL must start with https://");
  return { url, key };
}
