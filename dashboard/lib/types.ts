export type Json = string | number | boolean | null | Json[] | { [key: string]: Json };

export type Finding = {
  id: string;
  clean_table_id: string;
  detector: string;
  title_hint: string;
  score: number;
  numbers: Record<string, Json>;
  created_at: string;
};

export type CheckResult = {
  kind?: string;
  group?: string;
  period?: string;
  start?: string;
  end?: string;
  ok: boolean;
  detail: string;
};

export type ClaimResult = {
  sentence: string;
  keys: string[];
  fields: string[];
  status: "ok" | "sentence_not_found" | "unknown_keys" | "mismatch" | "assertion_missing" | "assertion_failed";
  numbers: { text: string; key: string | null }[];
  checks?: CheckResult[];
  unknown_keys?: string[];
  missing_checks?: string[];
  key_values?: Record<string, string>;
};

export type VerifyReport = {
  status: "passed" | "failed";
  checked: number;
  unmatched: { field: string; text: string; kind: string; value: string }[];
  years_out_of_range: { field: string; text: string; allowed: [number, number] }[];
  data_years: number[];
  claims_checked: boolean;
  claims: ClaimResult[];
  uncovered: { field: string; text: string; sentence: string }[];
};

export type Story = {
  id: string;
  finding_ids: string[];
  slug: string;
  headline: string | null;
  hook: string | null;
  summary: string | null;
  body_md: string | null;
  video_script: string | null;
  chart_spec: Record<string, Json> | null;
  chart_data: Record<string, string | number | null>[] | null;
  numbers: Record<string, Json> | null;
  verify_status: "pending" | "passed" | "failed";
  verify_report: VerifyReport | null;
  status: "draft" | "approved" | "rejected" | "published";
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

export type Candidate = {
  index: number;
  title: string;
  score: number;
  geography: string;
  geo_level: string;
  good_news: boolean;
  measures: string[];
  finding_ids: string[];
};
