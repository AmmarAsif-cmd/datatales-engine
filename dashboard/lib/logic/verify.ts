/**
 * TypeScript port of worker/datatales/verify.py (the dashboard runs on Cloudflare Workers,
 * where Python is not available). Behaviour must match Python exactly: every case in
 * worker/tests/golden/cases.json is checked by dashboard/tests/logic.test.ts.
 * Change verify.py first, regenerate the golden file, then mirror the change here.
 */
import { type CheckInput, evaluate } from "./chartfacts.ts";
import { type Dec, decAbs, decFromNumber, decKey, decToString, parseDec, roundsTo } from "./decimal.ts";

export const TEXT_FIELDS = ["headline", "hook", "summary", "body_md", "video_script", "chart_text"] as const;
/** chart_text: every chart title and annotation, one per line (see chartText()). */
export const PERCENT_DECIMALS = 2; // percentages are always written with 2 decimals: 38.50%
export type TextField = (typeof TEXT_FIELDS)[number];

const WORD_NUMBERS: Record<string, number> = {
  two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  seventeen: 17, eighteen: 18, nineteen: 19, twenty: 20, twice: 2, double: 2,
  doubled: 2, treble: 3, tripled: 3,
}; // prettier-ignore

const TOKEN_SOURCE =
  String.raw`(?<![\w.])(?<fy>(?:19|20)\d{2})\s*[-–/]\s*(?<fy2>\d{2})(?!\d)` +
  String.raw`|(?<money>£)?(?<![\w.])(?<num>-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(?<suffix>\s?%|(?:st|nd|rd|th)\b|\s?(?:times|x)\b)?` +
  String.raw`|\b(?<word>${Object.keys(WORD_NUMBERS).join("|")})\b`;
const YEAR_PERIOD = /((?:19|20)\d{2})\s*[-–/]\s*(\d{2})(?!\d)/g;
const OUT_OF = /out of (\d+)/g;
const YEAR_KINDS = new Set(["year", "financial_year"]);

export type Token = {
  field: string;
  text: string;
  value: Dec;
  decimals: number;
  kind: string;
  start: number;
  end: number;
};

const PLAIN_YEAR = /(?<![\p{L}\p{N}_])((?:19|20)\d{2})(?![\p{L}\p{N}_])/gu;

/** Rank / exclusivity words and the chart_data checks that can prove them (chartfacts.ts). */
export const RANK_WORDS: Record<string, string[]> = {
  only: ["only_rise", "only_fall"],
  all: ["all_rise", "all_fall"],
  highest: ["highest"],
  lowest: ["lowest"],
  biggest: ["biggest_rise", "biggest_fall"],
  largest: ["biggest_rise", "biggest_fall"],
};
const RANK_SOURCE = `(?<![\\p{L}\\p{N}_])(${Object.keys(RANK_WORDS).join("|")})(?![\\p{L}\\p{N}_])`;
const CHECK_FIELDS = ["kind", "group", "period", "start", "end"] as const;

export type Claim = { sentence: string; keys?: string[]; checks?: CheckInput[] };

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
  numbers: { text: string; key: string | null }[];
  checks: CheckResult[];
  status: "ok" | "sentence_not_found" | "unknown_keys" | "mismatch" | "assertion_missing" | "assertion_failed";
  unknown_keys?: string[];
  missing_checks?: string[];
  key_values?: Record<string, string>;
};

export type Report = {
  status: "passed" | "failed";
  checked: number;
  unmatched: { field: string; text: string; kind: string; value: string }[];
  years_out_of_range: { field: string; text: string; allowed: [number | null, number | null] }[];
  data_years: number[];
  allowed_values: number;
  claims_checked: boolean;
  claims: ClaimResult[];
  uncovered: { field: string; text: string; sentence: string }[];
  format_issues: { field: string; text: string; problem: string }[];
};

// ---- tokens ----

export function extractTokens(field: string, text: string): Token[] {
  const tokens: Token[] = [];
  for (const m of text.matchAll(new RegExp(TOKEN_SOURCE, "gi"))) {
    const g = m.groups ?? {};
    const start = m.index ?? 0;
    const end = start + m[0].length;
    if (g.fy) {
      tokens.push({ field, text: m[0], value: parseDec(g.fy), decimals: 0, kind: "financial_year", start, end });
      continue;
    }
    if (g.word) {
      const value = parseDec(String(WORD_NUMBERS[g.word.toLowerCase()]));
      tokens.push({ field, text: m[0], value, decimals: 0, kind: "word", start, end });
      continue;
    }
    const raw = g.num.replaceAll(",", "");
    const suffix = (g.suffix ?? "").trim().toLowerCase();
    const decimals = raw.includes(".") ? raw.split(".")[1].length : 0;
    const value = parseDec(raw);
    let kind: string;
    if (g.money) kind = "money";
    else if (suffix === "%") kind = "percent";
    else if (["st", "nd", "rd", "th"].includes(suffix)) kind = "ordinal";
    else if (suffix === "times" || suffix === "x") kind = "times";
    else if (decimals === 0 && !g.num.includes(",") && value.int >= 1900n && value.int <= 2099n) kind = "year";
    else kind = "number";
    tokens.push({ field, text: m[0].trim(), value, decimals, kind, start, end });
  }
  return tokens;
}

export function matches(token: Token, allowed: Iterable<Dec>): boolean {
  const target = decAbs(token.value);
  for (const a of allowed) if (roundsTo(a, target, token.decimals)) return true;
  return false;
}

// ---- the numbers a story may use ----

type JsonValue = string | number | boolean | null | JsonValue[] | { [k: string]: JsonValue };

const isNum = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);

function yearsFromLabel(text: string, into: Set<number>): void {
  for (const [, a, b] of text.matchAll(YEAR_PERIOD)) {
    into.add(Number(a));
    into.add(Number(a.slice(0, 2) + b));
  }
}

export function allowedFromNumbers(numbers: JsonValue): { values: Map<string, Dec>; years: Set<number> } {
  const values = new Map<string, Dec>();
  const years = new Set<number>();
  const walk = (obj: JsonValue): void => {
    if (obj === null || typeof obj === "boolean") return;
    if (isNum(obj)) {
      const d = decAbs(decFromNumber(obj));
      values.set(decKey(d), d);
    } else if (typeof obj === "string") {
      yearsFromLabel(obj, years);
      for (const [, n] of obj.matchAll(OUT_OF)) {
        const d = parseDec(n);
        values.set(decKey(d), d);
      }
    } else if (Array.isArray(obj)) obj.forEach(walk);
    else Object.values(obj).forEach(walk);
  };
  walk(numbers);
  return { values, years };
}

/** Readable key -> value for every number (see verify.py flatten_numbers). */
type ChartRow = Record<string, string | number | null | undefined>;

/** Every value in chart_data as a claim key: chart.<geography>.<period>.value|lower|upper. */
export function chartKeys(chartData: ChartRow[] | null | undefined): Map<string, Dec> {
  const out = new Map<string, Dec>();
  for (const row of chartData ?? []) {
    for (const col of ["value", "lower", "upper"]) {
      const v = row[col];
      if (typeof v === "number") out.set(`chart.${pyStr(row.geography)}.${pyStr(row.period)}.${col}`, decFromNumber(v));
    }
  }
  return out;
}

const pyStr = (v: unknown) => (v === null || v === undefined ? "None" : String(v));

/** All chart titles and annotations (main chart, then more_charts), one per line. */
export function chartText(spec: Record<string, unknown> | null | undefined): string {
  if (!spec) return "";
  const specs = [spec, ...((spec.more_charts as Record<string, unknown>[] | undefined) ?? [])];
  return specs
    .flatMap((s) => ["title", "annotation"].map((k) => s[k]).filter((v) => v !== undefined && v !== null && v !== ""))
    .map(String)
    .join("\n");
}

export function flattenNumbers(numbers: { [k: string]: JsonValue }): Map<string, Dec> {
  const out = new Map<string, Dec>();
  const segFor = (index: number, item: JsonValue): string => {
    if (item && typeof item === "object" && !Array.isArray(item)) {
      if (typeof item.period === "string") return item.period;
      if (typeof item.group === "string") return item.group;
    }
    return String(index + 1);
  };
  const walk = (obj: JsonValue, path: string[]): void => {
    if (obj === null || typeof obj === "boolean") return;
    if (isNum(obj)) {
      out.set(path.join("."), decFromNumber(obj));
    } else if (typeof obj === "string") {
      for (const [, n] of obj.matchAll(OUT_OF)) out.set([...path.slice(0, -1), "scale_max"].join("."), parseDec(n));
    } else if (Array.isArray(obj)) {
      const parent = path.length ? path[path.length - 1] : "";
      if (path.length && parent.endsWith("ci") && obj.length === 2 && obj.every(isNum)) {
        walk(obj[0], [...path, "lower"]);
        walk(obj[1], [...path, "upper"]);
        return;
      }
      const top = path.length === 1 && (parent === "findings" || parent === "series");
      obj.forEach((item, i) => {
        if (top) walk(item, [(parent === "findings" ? "f" : "s") + String(i + 1)]);
        else walk(item, [...path, segFor(i, item)]);
      });
    } else {
      for (const [k, v] of Object.entries(obj)) {
        if (k === "source") continue;
        walk(v, [...path, k]);
      }
    }
  };
  walk(numbers, []);
  return out;
}

// ---- text positions ----

const QUOTE_MAP: Record<string, string> = { "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-" };

function normalise(text: string): { norm: string; index: number[] } {
  const chars: string[] = [];
  const index: number[] = [];
  let prevSpace = true;
  for (let i = 0; i < text.length; i++) {
    let ch = text[i];
    if ("*_`#>".includes(ch)) continue;
    ch = QUOTE_MAP[ch] ?? ch;
    if (/\s/.test(ch)) {
      if (prevSpace) continue;
      ch = " ";
      prevSpace = true;
    } else {
      prevSpace = false;
    }
    chars.push(ch.toLowerCase());
    index.push(i);
  }
  while (chars.length && chars[chars.length - 1] === " ") {
    chars.pop();
    index.pop();
  }
  return { norm: chars.join(""), index };
}

function findSpans(text: string, sentence: string): [number, number][] {
  const { norm, index } = normalise(text);
  const needle = normalise(sentence).norm.trim();
  const spans: [number, number][] = [];
  if (!needle) return spans;
  let start = norm.indexOf(needle);
  while (start !== -1) {
    const end = start + needle.length - 1;
    spans.push([index[start], index[end] + 1]);
    start = norm.indexOf(needle, start + 1);
  }
  return spans;
}

function rfindBefore(text: string, sub: string, pos: number): number {
  // Python text.rfind(sub, 0, pos): the whole match must end at or before pos.
  return pos - sub.length < 0 ? -1 : text.lastIndexOf(sub, pos - sub.length);
}

function sentenceAround(text: string, pos: number): string {
  const start = Math.max(rfindBefore(text, ". ", pos), rfindBefore(text, "\n", pos));
  const ends = [text.indexOf(". ", pos), text.indexOf("\n", pos)].filter((i) => i !== -1);
  const end = ends.length ? Math.min(...ends) + 1 : text.length;
  return text.slice(start + 1, end).trim();
}

// ---- main entry ----

function dataYears(numbers: { [k: string]: JsonValue }, fallback: Set<number>): [number | null, number | null] {
  const period = (numbers.data_period ?? {}) as { [k: string]: JsonValue };
  const years = new Set<number>();
  for (const label of [period.first, period.last]) {
    const text = String(label ?? "");
    if ([...text.matchAll(YEAR_PERIOD)].length) yearsFromLabel(text, years);
    else {
      // a plain year or a quarter/month label: 2023, 2026 Q2, 2024-01-01
      const first = [...text.matchAll(PLAIN_YEAR)][0];
      if (first) years.add(Number(first[1]));
    }
  }
  const use = years.size ? years : fallback;
  return use.size ? [Math.min(...use), Math.max(...use)] : [null, null];
}

/** Years quoted in the source's caveats (e.g. when a release was paused) are allowed. */
export function caveatYears(numbers: { [k: string]: JsonValue }): Set<number> {
  const years = new Set<number>();
  const caveats = Array.isArray(numbers.caveats) ? numbers.caveats : [];
  for (const text of caveats) {
    yearsFromLabel(String(text), years);
    for (const m of String(text).matchAll(PLAIN_YEAR)) years.add(Number(m[1]));
  }
  return years;
}

export function verifyText(
  fields: Partial<Record<TextField, string | null>>,
  numbers: { [k: string]: JsonValue },
  claims: Claim[] | null = null,
  chartData: Record<string, string | number | null>[] | null = null,
): Report {
  const { values, years } = allowedFromNumbers(numbers);
  for (const v of chartKeys(chartData).values()) {
    const a = decAbs(v);
    values.set(decKey(a), a);
  }
  const allowed = [...values.values()];
  const [lo, hi] = dataYears(numbers, years);
  const extraYears = caveatYears(numbers);
  const report: Report = {
    status: "passed",
    checked: 0,
    unmatched: [],
    years_out_of_range: [],
    data_years: lo !== null && lo ? [lo, hi as number] : [],
    allowed_values: values.size,
    claims_checked: false,
    claims: [],
    uncovered: [],
    format_issues: [],
  };
  const texts = Object.fromEntries(TEXT_FIELDS.map((f) => [f, fields[f] ?? ""])) as Record<TextField, string>;
  const tokens = Object.fromEntries(TEXT_FIELDS.map((f) => [f, extractTokens(f, texts[f])])) as Record<TextField, Token[]>;

  for (const name of TEXT_FIELDS) {
    for (const tok of tokens[name]) {
      report.checked += 1;
      if (YEAR_KINDS.has(tok.kind)) {
        const ys = [Number(tok.value.int)];
        if (tok.kind === "financial_year") {
          const m = /((?:19|20)\d{2})\s*[-–/]\s*(\d{2})(?!\d)/.exec(tok.text);
          if (m) ys.push(Number(m[1].slice(0, 2) + m[2]));
        }
        const outside = ys.filter((y) => !extraYears.has(y) && (lo === null || y < lo || y > (hi as number)));
        if (outside.length) {
          report.years_out_of_range.push({ field: name, text: tok.text, allowed: [lo, hi] });
        }
      } else if (tok.kind === "percent" && tok.decimals !== PERCENT_DECIMALS) {
        report.format_issues.push({ field: name, text: tok.text, problem: "percentages need 2 decimals" });
        if (!matches(tok, allowed)) {
          report.unmatched.push({ field: name, text: tok.text, kind: tok.kind, value: decToString(tok.value) });
        }
      } else if (!matches(tok, allowed)) {
        report.unmatched.push({ field: name, text: tok.text, kind: tok.kind, value: decToString(tok.value) });
      }
    }
  }

  if (claims !== null) checkClaims(report, texts, tokens, numbers, claims, chartData ?? []);

  const failed =
    report.unmatched.length > 0 ||
    report.years_out_of_range.length > 0 ||
    report.uncovered.length > 0 ||
    report.format_issues.length > 0 ||
    report.claims.some((c) => c.status !== "ok");
  report.status = failed ? "failed" : "passed";
  return report;
}

function checkClaims(
  report: Report,
  texts: Record<TextField, string>,
  tokens: Record<TextField, Token[]>,
  numbers: { [k: string]: JsonValue },
  claims: Claim[],
  chartData: Record<string, string | number | null>[],
): void {
  report.claims_checked = true;
  const keyTable = new Map([...flattenNumbers(numbers), ...chartKeys(chartData)]);
  const covered = Object.fromEntries(TEXT_FIELDS.map((f) => [f, [] as [number, number][]])) as Record<
    TextField,
    [number, number][]
  >;

  for (const claim of claims) {
    const sentence = String(claim.sentence ?? "");
    const keys = (claim.keys ?? []).map(String);
    const checks = (claim.checks ?? []).map((c) => ({ ...c }));
    const result: ClaimResult = { sentence, keys, fields: [], numbers: [], checks: [], status: "ok" };
    const unknown = keys.filter((k) => !keyTable.has(k));
    const foundIn: [TextField, [number, number]][] = [];
    for (const name of TEXT_FIELDS) {
      for (const span of findSpans(texts[name], sentence)) {
        foundIn.push([name, span]);
        covered[name].push(span);
      }
    }
    result.fields = [...new Set(foundIn.map(([n]) => n))].sort();

    if (!foundIn.length) {
      result.status = "sentence_not_found";
    } else if (unknown.length) {
      result.status = "unknown_keys";
      result.unknown_keys = unknown;
    } else {
      const [name, [start, end]] = foundIn[0];
      let mismatched = false;
      for (const tok of tokens[name]) {
        if (!(start <= tok.start && tok.start < end) || YEAR_KINDS.has(tok.kind)) continue;
        const hit = keys.find((k) => matches(tok, [decAbs(keyTable.get(k) as Dec)])) ?? null;
        result.numbers.push({ text: tok.text, key: hit });
        mismatched = mismatched || hit === null;
      }
      const kinds = new Set(checks.map((c) => c.kind));
      const words = [...new Set([...sentence.matchAll(new RegExp(RANK_SOURCE, "giu"))].map((m) => m[1].toLowerCase()))].sort();
      const missing = words.filter((w) => !RANK_WORDS[w].some((k) => kinds.has(k)));
      for (const c of checks) {
        const [ok, detail] = evaluate(c, chartData);
        const input = Object.fromEntries(
          CHECK_FIELDS.filter((f) => c[f] !== null && c[f] !== undefined).map((f) => [f, c[f]]),
        );
        result.checks.push({ ...input, ok, detail });
      }
      if (mismatched) {
        result.status = "mismatch";
        result.key_values = Object.fromEntries(keys.map((k) => [k, decToString(keyTable.get(k) as Dec)]));
      } else if (missing.length) {
        result.status = "assertion_missing";
        result.missing_checks = missing;
      } else if (!result.checks.every((c) => c.ok)) {
        result.status = "assertion_failed";
      } else {
        result.status = "ok";
      }
    }
    report.claims.push(result);
  }

  for (const name of TEXT_FIELDS) {
    for (const m of texts[name].matchAll(new RegExp(RANK_SOURCE, "giu"))) {
      if (!covered[name].some(([s, e]) => s <= m.index && m.index < e)) {
        report.uncovered.push({ field: name, text: m[0], sentence: sentenceAround(texts[name], m.index) });
      }
    }
  }

  for (const name of TEXT_FIELDS) {
    for (const tok of tokens[name]) {
      if (YEAR_KINDS.has(tok.kind)) continue;
      if (!covered[name].some(([s, e]) => s <= tok.start && tok.start < e)) {
        report.uncovered.push({ field: name, text: tok.text, sentence: sentenceAround(texts[name], tok.start) });
      }
    }
  }
}
