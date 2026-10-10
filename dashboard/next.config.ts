import path from "node:path";

import type { NextConfig } from "next";

// Local-only review app. Never deploy it: it holds the Supabase service-role key.
const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactCompiler: true,
  // Pin the project root (a stray lockfile higher up the tree must not be picked up).
  turbopack: { root: path.resolve(__dirname) },
};

export default nextConfig;
