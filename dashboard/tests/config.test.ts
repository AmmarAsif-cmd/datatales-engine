import assert from "node:assert/strict";
import { test } from "node:test";

import { configProblems } from "../lib/config.ts";

const GOOD = {
  // built at runtime so no key-shaped string sits in the source (the repo key scan)
  ANTHROPIC_API_KEY: "sk-ant-" + "x".repeat(12),
  NODE_ENV: "production",
  SUPABASE_URL: "https://abc.supabase.co",
  SUPABASE_SERVICE_ROLE_KEY: "x".repeat(40),
  CF_ACCESS_TEAM_DOMAIN: "https://datatales.cloudflareaccess.com",
  CF_ACCESS_AUD: "a".repeat(64),
  GITHUB_DISPATCH_TOKEN: "github_pat_xxx",
  GITHUB_REPO: "AmmarAsif-cmd/datatales-engine",
};

const names = (env: Record<string, string | undefined>, fatal = true) =>
  configProblems(env).filter((p) => p.fatal === fatal).map((p) => p.name);

test("complete production config has no problems", () => {
  assert.deepEqual(configProblems(GOOD), []);
});

test("missing and malformed settings are fatal, by name", () => {
  assert.deepEqual(names({ NODE_ENV: "production" }), [
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "CF_ACCESS_TEAM_DOMAIN",
    "CF_ACCESS_AUD",
  ]);
  assert.deepEqual(names({ ...GOOD, SUPABASE_URL: "http://abc.supabase.co" }), ["SUPABASE_URL"]);
  assert.deepEqual(names({ ...GOOD, CF_ACCESS_TEAM_DOMAIN: "datatales.cloudflareaccess.com" }), [
    "CF_ACCESS_TEAM_DOMAIN",
  ]);
  assert.deepEqual(names({ ...GOOD, CF_ACCESS_AUD: "not-a-tag" }), ["CF_ACCESS_AUD"]);
});

test("trailing slash on the team domain is accepted", () => {
  assert.deepEqual(names({ ...GOOD, CF_ACCESS_TEAM_DOMAIN: "https://datatales.cloudflareaccess.com/" }), []);
});

test("Access settings are not required in development", () => {
  assert.deepEqual(names({ ...GOOD, NODE_ENV: "development", CF_ACCESS_AUD: "", CF_ACCESS_TEAM_DOMAIN: "" }), []);
});

test("GitHub settings missing is a warning, not fatal", () => {
  const env = { ...GOOD, GITHUB_DISPATCH_TOKEN: "", GITHUB_REPO: "" };
  assert.deepEqual(names(env), []);
  assert.deepEqual(names(env, false), ["GITHUB_DISPATCH_TOKEN", "GITHUB_REPO"]);
});

test("problems never include values", () => {
  const secret = "super-secret-value-123";
  const out = JSON.stringify(configProblems({ NODE_ENV: "production", SUPABASE_SERVICE_ROLE_KEY: "short", SUPABASE_URL: secret }));
  assert.ok(!out.includes(secret) && !out.includes("short\""));
});

test("Claude key missing or malformed is a warning, not fatal", () => {
  assert.deepEqual(names({ ...GOOD, ANTHROPIC_API_KEY: "" }), []);
  assert.deepEqual(names({ ...GOOD, ANTHROPIC_API_KEY: "" }, false), ["ANTHROPIC_API_KEY"]);
  assert.deepEqual(names({ ...GOOD, ANTHROPIC_API_KEY: "abc" }, false), ["ANTHROPIC_API_KEY"]);
});
