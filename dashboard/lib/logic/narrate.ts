/**
 * TypeScript port of worker/datatales/narrate.py: reply validation and the prompt.
 * Must match Python (checked against worker/tests/golden/cases.json). The reply is parsed
 * with JSON.parse only; nothing in it is ever executed.
 */
import { CHECK_KINDS, type CheckKind } from "./chartfacts.ts";
import { decToString } from "./decimal.ts";
import { flattenNumbers } from "./verify.ts";

export const HEADLINE_MAX_CHARS = 70;
export const SUMMARY_MAX_WORDS = 120;
export const BODY_MIN_WORDS = 450; // the prompt asks for 500-700; a little slack either side
export const BODY_MAX_WORDS = 750;
export const VIDEO_MAX_WORDS = 90;
export const REQUIRED_SECTIONS = ["How it compares", "What the data can't tell us"];
export type Check = { kind: CheckKind; group?: string; period?: string; start?: string; end?: string };

export class NarrationError extends Error {}

type Row = Record<string, string | number | null>;

export const MAX_CHARTS = 3; // the main chart plus up to two more
export const CHART_TYPES = ["line", "bar", "dot", "slope", "map"] as const;
export type ChartType = (typeof CHART_TYPES)[number];
const SPEC_FIELDS = [
  "type", "x", "y", "series", "highlight", "annotation", "title", "yLabel", "start", "end", "period",
]; // prettier-ignore

export type ChartSpec = {
  type: ChartType;
  x: string;
  y: string;
  series?: string | null;
  highlight?: string | string[] | null;
  annotation?: string | null;
  title?: string | null;
  yLabel?: string | null;
  start?: string | null;
  end?: string | null;
  period?: string | null;
};

export type Narration = {
  headline: string;
  hook: string;
  summary: string;
  body_md: string;
  video_script: string;
  chart_spec: ChartSpec;
  more_charts: ChartSpec[];
  claims: { sentence: string; keys: string[]; checks: Check[] }[];
};

const chars = (s: string) => [...s].length;

/** Matches Python `\b[\w'’-]+\b` with Unicode \w. */
export function wordCount(text: string): number {
  let n = 0;
  for (const m of text.matchAll(/[\p{L}\p{N}\p{M}_'’-]+/gu)) {
    if (m[0].replace(/^['’-]+|['’-]+$/g, "")) n += 1;
  }
  return n;
}

/** A '## Title' (or ###) heading; straight or curly apostrophes both count. */
export function hasSection(body: string, title: string): boolean {
  const norm = title.toLowerCase().replace(/'/g, "['’]");
  return new RegExp(`^#{2,3}\\s*${norm}\\s*$`, "im").test(body);
}

function stripFences(text: string): string {
  const t = text.trim();
  const m = /^```(?:json)?\s*\n([\s\S]*)\n```\s*$/.exec(t);
  return m ? m[1] : t;
}

type Problem = [string, string];

function checkExtra(obj: Record<string, unknown>, allowed: string[], prefix: string, out: Problem[]) {
  for (const k of Object.keys(obj)) if (!allowed.includes(k)) out.push([prefix + k, "Extra inputs are not permitted"]);
}

function strField(
  obj: Record<string, unknown>,
  key: string,
  loc: string,
  out: Problem[],
  opts: { strip?: boolean; min?: number; max?: number; optional?: boolean } = {},
): string | undefined {
  const v = obj[key];
  if (v === undefined || (opts.optional && v === null)) {
    if (!opts.optional) out.push([loc, "Field required"]);
    return undefined;
  }
  if (typeof v !== "string") {
    out.push([loc, "Input should be a valid string"]);
    return undefined;
  }
  const s = opts.strip ? v.trim() : v;
  if (opts.min !== undefined && chars(s) < opts.min) {
    out.push([loc, `String should have at least ${opts.min} characters`]);
    return undefined;
  }
  if (opts.max !== undefined && chars(s) > opts.max) {
    out.push([loc, `String should have at most ${opts.max} characters`]);
    return undefined;
  }
  return s;
}

export function parseNarration(text: string, chartData: Row[]): Narration {
  let data: unknown;
  try {
    data = JSON.parse(stripFences(text));
  } catch (e) {
    throw new NarrationError(`not valid JSON: ${(e as Error).message}`);
  }
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    throw new NarrationError("reply must be a JSON object");
  }
  const obj = data as Record<string, unknown>;
  const p: Problem[] = [];
  checkExtra(obj, ["headline", "hook", "summary", "body_md", "video_script", "chart_spec", "more_charts", "claims"], "", p);

  const headline = strField(obj, "headline", "headline", p, { strip: true, min: 10, max: HEADLINE_MAX_CHARS });
  let hook = strField(obj, "hook", "hook", p, { strip: true, min: 10, max: 300 });
  if (hook !== undefined && (hook.trim().match(/[.!?](\s|$)/g) ?? []).length > 1) {
    p.push(["hook", "Value error, must be one sentence"]);
    hook = undefined;
  }
  const summary = strField(obj, "summary", "summary", p, { strip: true, min: 20 });
  if (summary !== undefined && wordCount(summary) > SUMMARY_MAX_WORDS) {
    p.push(["summary", `Value error, is ${wordCount(summary)} words; max ${SUMMARY_MAX_WORDS}`]);
  }
  const body = strField(obj, "body_md", "body_md", p, { strip: true, min: 50 });
  if (body !== undefined) {
    const n = wordCount(body);
    const missing = REQUIRED_SECTIONS.filter((t) => !hasSection(body, t));
    if (n > BODY_MAX_WORDS || n < BODY_MIN_WORDS) {
      p.push(["body_md", `Value error, is ${n} words; must be ${BODY_MIN_WORDS} to ${BODY_MAX_WORDS}`]);
    } else if (/<\s*(script|iframe|style)|javascript:/i.test(body)) {
      p.push(["body_md", "Value error, must be plain Markdown (no scripts, iframes or styles)"]);
    } else if (missing.length) {
      p.push(["body_md", `Value error, needs '## ' sections: ${missing.join(", ")}`]);
    }
  }
  const video = strField(obj, "video_script", "video_script", p, { strip: true, min: 10 });
  if (video !== undefined && wordCount(video) > VIDEO_MAX_WORDS) {
    p.push(["video_script", `Value error, is ${wordCount(video)} words; max ${VIDEO_MAX_WORDS}`]);
  }

  const spec = obj.chart_spec === undefined ? (p.push(["chart_spec", "Field required"]), undefined) : parseSpec(obj.chart_spec, "chart_spec", p);
  const more: ChartSpec[] = [];
  const rawMore = obj.more_charts ?? [];
  if (!Array.isArray(rawMore)) p.push(["more_charts", "Input should be a valid list"]);
  else if (rawMore.length > MAX_CHARTS - 1) {
    p.push(["more_charts", `List should have at most ${MAX_CHARTS - 1} items after validation, not ${rawMore.length}`]);
  } else {
    rawMore.forEach((m, i) => {
      const parsed = parseSpec(m, `more_charts.${i}`, p);
      if (parsed) more.push(parsed);
    });
  }

  const claims: Narration["claims"] = [];
  const rawClaims = obj.claims;
  if (rawClaims === undefined) p.push(["claims", "Field required"]);
  else if (!Array.isArray(rawClaims)) p.push(["claims", "Input should be a valid list"]);
  else if (rawClaims.length < 1) p.push(["claims", "List should have at least 1 item after validation, not 0"]);
  else if (rawClaims.length > 80) p.push(["claims", "List should have at most 80 items after validation"]);
  else {
    rawClaims.forEach((c, i) => {
      const loc = `claims.${i}`;
      if (!c || typeof c !== "object" || Array.isArray(c)) {
        p.push([loc, "Input should be a valid dictionary"]);
        return;
      }
      const co = c as Record<string, unknown>;
      checkExtra(co, ["sentence", "keys", "checks"], `${loc}.`, p);
      const before = p.length;
      const sentence = strField(co, "sentence", `${loc}.sentence`, p, { strip: true, min: 5, max: 600 });
      const keys = co.keys ?? [];
      if (!Array.isArray(keys) || !keys.every((k) => typeof k === "string")) {
        p.push([`${loc}.keys`, "Input should be a valid list of strings"]);
      } else if (keys.length > 12) p.push([`${loc}.keys`, "List should have at most 12 items after validation"]);
      const checks = parseChecks(co.checks ?? [], `${loc}.checks`, p);
      if (p.length !== before || sentence === undefined) return;
      if (!(keys as string[]).length && !checks.length) {
        p.push([loc, "Value error, needs at least one key or check"]);
        return;
      }
      claims.push({ sentence, keys: (keys as string[]).map((k) => k.trim()), checks });
    });
  }

  if (p.length) {
    throw new NarrationError(`reply does not match the schema: ${p.map(([l, m]) => `${l}: ${m}`).join("; ")}`);
  }

  const narration: Narration = {
    headline: headline as string,
    hook: hook as string,
    summary: summary as string,
    body_md: body as string,
    video_script: video as string,
    chart_spec: spec as ChartSpec,
    more_charts: more,
    claims,
  };
  [narration.chart_spec, ...more].forEach((c, i) => checkChart(c, chartData, i === 0 ? "chart_spec" : `more_charts.${i - 1}`));
  return narration;
}

export function parseChecks(raw: unknown, loc: string, p: [string, string][]): Check[] {
  if (!Array.isArray(raw)) {
    p.push([loc, "Input should be a valid list"]);
    return [];
  }
  if (raw.length > 6) {
    p.push([loc, "List should have at most 6 items after validation"]);
    return [];
  }
  const out: Check[] = [];
  raw.forEach((c, j) => {
    const at = `${loc}.${j}`;
    if (!c || typeof c !== "object" || Array.isArray(c)) {
      p.push([at, "Input should be a valid dictionary"]);
      return;
    }
    const co = c as Record<string, unknown>;
    const before = p.length;
    checkExtra(co, ["kind", "group", "period", "start", "end"], `${at}.`, p);
    if (!CHECK_KINDS.includes(co.kind as CheckKind)) {
      p.push([`${at}.kind`, `Input should be ${CHECK_KINDS.slice(0, -1).map((k) => `'${k}'`).join(", ")} or '${CHECK_KINDS.at(-1)}'`]);
    }
    const fields: Record<string, string | undefined> = {};
    for (const f of ["group", "period", "start", "end"]) {
      fields[f] = strField(co, f, `${at}.${f}`, p, { strip: true, optional: true });
    }
    if (p.length !== before) return;
    const kind = co.kind as CheckKind;
    const needs = kind === "highest" || kind === "lowest" ? ["period"] : ["start", "end"];
    if (kind !== "all_rise" && kind !== "all_fall") needs.push("group");
    const missing = needs.filter((f) => !fields[f]);
    if (missing.length) {
      p.push([at, `Value error, ${kind} needs ${missing.join(", ")}`]);
      return;
    }
    const check: Check = { kind };
    for (const f of ["group", "period", "start", "end"] as const) if (fields[f] !== undefined) check[f] = fields[f];
    out.push(check);
  });
  return out;
}

function parseSpec(raw: unknown, loc: string, p: Problem[]): ChartSpec | undefined {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    p.push([loc, "Input should be a valid dictionary"]);
    return undefined;
  }
  const s = raw as Record<string, unknown>;
  const before = p.length;
  checkExtra(s, SPEC_FIELDS, `${loc}.`, p);
  if (!CHART_TYPES.includes(s.type as ChartType)) {
    p.push([`${loc}.type`, `Input should be ${CHART_TYPES.slice(0, -1).map((t) => `'${t}'`).join(", ")} or '${CHART_TYPES.at(-1)}'`]);
  }
  const x = strField(s, "x", `${loc}.x`, p);
  const y = strField(s, "y", `${loc}.y`, p);
  const opt: Record<string, string | undefined> = {};
  const limits: Record<string, number | undefined> = { annotation: 200, title: 120, yLabel: 80 };
  for (const f of ["series", "annotation", "title", "yLabel", "start", "end", "period"]) {
    opt[f] = strField(s, f, `${loc}.${f}`, p, { optional: true, max: limits[f] });
  }
  const h = s.highlight;
  const hOk = h === undefined || h === null || typeof h === "string" || (Array.isArray(h) && h.every((v) => typeof v === "string"));
  if (!hOk) p.push([`${loc}.highlight`, "Input should be a valid string or list of strings"]);
  if (p.length !== before) return undefined;
  const spec: ChartSpec = { type: s.type as ChartType, x: x as string, y: y as string };
  if (opt.series !== undefined) spec.series = opt.series;
  if (h !== undefined && h !== null) spec.highlight = h as string | string[];
  for (const f of ["annotation", "title", "yLabel", "start", "end", "period"] as const) {
    if (opt[f] !== undefined) spec[f] = opt[f];
  }
  return spec;
}

function checkChart(spec: ChartSpec, chartData: Row[], name: string): void {
  const columns = new Set(chartData.flatMap((r) => Object.keys(r)));
  for (const field of ["x", "y", "series"] as const) {
    const col = spec[field];
    if (col !== undefined && col !== null && !columns.has(col)) {
      throw new NarrationError(`${name}.${field} '${col}' is not a chart_data column ${pyList([...columns].sort())}`);
    }
  }
  if (spec.highlight !== undefined && spec.highlight !== null) {
    const wanted = Array.isArray(spec.highlight) ? spec.highlight : [spec.highlight];
    const key = spec.series ?? spec.x;
    const present = new Set(chartData.map((r) => pyStr(r[key])));
    const missing = wanted.filter((h) => !present.has(h));
    if (missing.length) {
      throw new NarrationError(`${name}.highlight ${pyList(missing)} not found in chart_data['${key}']`);
    }
  }
  if ((spec.type === "slope" || spec.type === "map") && !spec.series) {
    throw new NarrationError(`${name}: a ${spec.type} chart needs \`series\` (the geography column)`);
  }
  if (spec.type === "map" && !columns.has("code")) {
    throw new NarrationError(`${name}: a map needs geography codes (chart_data has no 'code')`);
  }
  const periods = new Set(chartData.map((r) => pyStr(r[spec.x])));
  for (const field of ["start", "end", "period"] as const) {
    const value = spec[field];
    if (value !== undefined && value !== null && !periods.has(value)) {
      throw new NarrationError(`${name}.${field} '${value}' is not a value of '${spec.x}'`);
    }
  }
  if (spec.start && spec.end && !(spec.start < spec.end)) {
    throw new NarrationError(`${name}: start must come before end`);
  }
}

// ---- Python-compatible formatting helpers (for messages and the prompt) ----

function pyStr(v: unknown): string {
  if (v === null || v === undefined) return "None";
  return String(v);
}

export function pyList(items: string[]): string {
  return `[${items.map((s) => `'${s}'`).join(", ")}]`;
}

/** json.dumps(obj, ensure_ascii=False[, indent=n]). */
export function pyDumps(obj: unknown, indent?: number, level = 0): string {
  if (obj === null || obj === undefined) return "null";
  if (typeof obj === "boolean") return obj ? "true" : "false";
  if (typeof obj === "number") return String(obj);
  if (typeof obj === "string") return JSON.stringify(obj);
  const pad = indent === undefined ? "" : "\n" + " ".repeat(indent * (level + 1));
  const end = indent === undefined ? "" : "\n" + " ".repeat(indent * level);
  const sep = indent === undefined ? ", " : ",";
  if (Array.isArray(obj)) {
    if (!obj.length) return "[]";
    return `[${obj.map((v) => pad + pyDumps(v, indent, level + 1)).join(sep)}${end}]`;
  }
  const entries = Object.entries(obj as Record<string, unknown>);
  if (!entries.length) return "{}";
  return `{${entries.map(([k, v]) => `${pad}${JSON.stringify(k)}: ${pyDumps(v, indent, level + 1)}`).join(sep)}${end}}`;
}

// ---- prompt (keep in sync with narrate.py) ----

/** Generated from narrate.py OUTPUT_SCHEMA (golden-tested). */
/** Generated from narrate.py OUTPUT_SCHEMA (golden-tested). */
/** Generated from narrate.py OUTPUT_SCHEMA (golden-tested). */
/** Generated from narrate.py OUTPUT_SCHEMA (golden-tested). */
export const OUTPUT_SCHEMA = {
  "headline": "string, at most 70 characters: the single strongest finding as a statement, e.g. \"Northern Ireland is the only UK nation where low anxiety rose\"",
  "hook": "string, exactly one sentence",
  "summary": "string, at most 120 words",
  "body_md": "string, Markdown, 500 to 700 words, with the sections \"## How it compares\" and \"## What the data can't tell us\"; no headings above ##",
  "video_script": "string, at most 90 words, to be read aloud",
  "chart_spec": {
    "type": "line | bar | dot | slope | map",
    "x": "column name in chart_data",
    "y": "column name in chart_data",
    "series": "column name in chart_data (optional)",
    "highlight": "a value (or list of values) of the series column to highlight",
    "annotation": "short note under the chart, at most 200 characters (optional)",
    "title": "chart title, at most 120 characters (optional)",
    "yLabel": "label for the values, e.g. the unit (optional)",
    "start": "slope only: first period to compare (optional, default first)",
    "end": "slope only: last period to compare (optional, default last)",
    "period": "map only: the period to map (optional, default last)"
  },
  "more_charts": [
    "up to 2 more chart_spec objects (optional), e.g. a slope and a map"
  ],
  "claims": [
    {
      "sentence": "a sentence copied EXACTLY from headline/hook/summary/body_md/video_script that contains a number (other than a year) or a rank word",
      "keys": [
        "the KEYS (from the KEYS table) that each number in it comes from"
      ],
      "checks": [
        {
          "kind": "only_rise | only_fall | all_rise | all_fall | highest | lowest | biggest_rise | biggest_fall",
          "group": "geography (not for all_rise/all_fall)",
          "start": "first period (rise/fall kinds)",
          "end": "last period (rise/fall kinds)",
          "period": "period (highest/lowest)"
        }
      ]
    }
  ]
};

export const RULES = `Rules (follow every one):
1. Use ONLY numbers that appear in NUMBERS or CHART DATA below. Do not calculate new
   numbers (no new differences, ratios, averages or percentages) and do not round to a
   different figure than one you could get by rounding a number given. Years must be within
   the data period (years mentioned in \`caveats\` are also allowed).
2. UK English. Plain, calm language for a general reader. No hype words ("shocking",
   "soaring", "plummeting", "crisis"). Write financial years with an en dash: 2011–12.
3. HEADLINE: state the single strongest finding as a statement with its key fact, e.g.
   "Northern Ireland is the only UK nation where low anxiety rose". Never a topic label
   such as "Wellbeing in Northern Ireland 2011–2023".
4. FRAMING: \`chart_facts.supported_checks\` lists what the chart data clearly supports
   (only_rise, only_fall, all_rise, all_fall, highest, lowest, biggest_rise, biggest_fall).
   When one is supported, prefer that framing ("the only nation where…", "the biggest rise
   of the four…"), or rank-change framing from \`rank_change\`/\`overtook\` in the findings.
5. Every change or gap in NUMBERS is statistically clear (confidence intervals do not
   overlap). Say "clearly higher/lower" if useful; never say "significant". If
   \`exact_counts\` is true the data are administrative counts with no margin of error:
   never mention confidence intervals or survey estimates for them.
6. Respect polarity: \`higher_is_better\` and \`good_news\` say whether a rise is good. For
   anxiety, a LOWER score is better. Band labels for anxiety mean: Poor = high anxiety,
   Fair = medium, Good = low, Very good = very low anxiety. Never write "very good anxiety";
   write "very low anxiety".
7. When \`unit\` starts with "%", a change in \`change\` is in percentage points: write
   "5.42 percentage points", never "5.42%". \`pct_change\` is a relative change. Write every
   percentage with exactly 2 decimals: 38.50%, 5.00% (never 38.5% or 39%).
8. SHAPE: \`series[].points\` has every year and \`series[].peak\` the peak and low point. If
   \`latest_well_below_peak\` is true, say plainly that the latest value is well below the
   peak, with both numbers and years. Mention notable dips or rises from \`notable_moves\` and
   \`moves_shared_by_most_geographies\` (for example 2020–21) briefly, with their numbers. If
   they are empty, do not invent one.
9. STRUCTURE of body_md (500 to 700 words): first the main finding and its shape; then
   "## How it compares" (the other geographies and the other measures in NUMBERS); then
   "## What the data can't tell us" (these are survey estimates with confidence intervals;
   the data does not explain causes; and every point in \`caveats\`, such as the paused annual
   release). Say where the data comes from (source name) and the period covered.
10. RANK WORDS: use "only", "all", "highest", "lowest", "biggest" or "largest" only for the
   charted measure, and only when a check proves it (rule 11). Otherwise avoid these words.
11. CLAIMS: for EVERY sentence in any field that contains a number other than a year, or any
   of the rank words above, add one claim:
   {"sentence": <copied exactly>, "keys": [<KEYS used>], "checks": [<checks>]}.
   Each number must equal (after rounding) one of its keys. Each rank word needs a check of
   the matching kind: only -> only_rise/only_fall; all -> all_rise/all_fall; highest ->
   highest; lowest -> lowest; biggest/largest -> biggest_rise/biggest_fall. Copy checks from
   \`chart_facts.supported_checks\` (without "detail"), or write one with other periods; every
   check is re-tested against chart_data. If the same sentence is used in two fields, one
   claim covers both. Count words like "four" as numbers. For a value from CHART DATA use
   the key chart.<geography>.<period>.value (or .lower / .upper for its confidence interval).
   Chart titles and annotations are checked like the other text: keep numbers out of them
   unless they come from the data, and give any such sentence a claim.
12. CHARTS: chart_spec is the main chart (a line chart of every year suits most stories).
   \`more_charts\` may add up to 2 more from the same chart_data: "slope" (first vs last period,
   good for showing who rose and who fell) and "map" (one period by area; only for nations,
   regions or local authorities, and only when chart_data has a \`code\` column). Give each a
   short title. Do not repeat the same chart twice.
13. Return ONLY a JSON object with exactly these keys, no Markdown fences, no comments.
`;

const INTRO = [
  "You are writing a short data story for DataTales (datatales.co.uk), a UK site",
  "that turns public data into plain, accurate stories. Python has already done all",
  "the maths; your job is only the words around the numbers below.",
].join("\n");
export const CHART_ROWS_MAX = 240; // chart rows listed in the prompt; larger charts list key rows only

/** The explicit task, sent after the data in the user turn (API drafting). Same as narrate.py. */
export const STORY_REQUEST =
  "Write the DataTales story for the data above now, following every rule. Fill every " +
  "field completely: headline (10 to 70 characters, stating the strongest finding), hook " +
  "(one full sentence), summary (2 to 4 sentences, at most 120 words), body_md (500 to 700 " +
  "words, with the sections ## How it compares and ## What the data can't tell us), " +
  "video_script (at most 90 words), chart_spec, more_charts (may be empty) and claims (one " +
  "per sentence that has a number or a rank word, copied exactly: usually 20 to 40). " +
  "Every check needs all " +
  "the fields its kind uses: group plus start and end for rise/fall kinds, group plus " +
  "period for highest/lowest, start and end for all_rise/all_fall.";

const isEmpty = (v: unknown) => v === "" || v === null || v === undefined || (Array.isArray(v) && v.length === 0);

/**
 * Structured-output replies use "" / [] for "not used" (the schema has no union types: the
 * API allows at most 16). Drop those so the reply means the same as a hand-pasted one; a
 * one-item highlight list becomes a string. Same as narrate.py normalise_api_reply.
 */
export function normaliseApiReply(reply: unknown): unknown {
  if (!reply || typeof reply !== "object" || Array.isArray(reply)) return reply;
  const spec = (s: unknown) => {
    if (!s || typeof s !== "object" || Array.isArray(s)) return s;
    const out = Object.fromEntries(Object.entries(s).filter(([, v]) => !isEmpty(v)));
    if (Array.isArray(out.highlight) && out.highlight.length === 1) out.highlight = out.highlight[0];
    return out;
  };
  const out: Record<string, unknown> = { ...(reply as Record<string, unknown>) };
  if ("chart_spec" in out) out.chart_spec = spec(out.chart_spec);
  if (Array.isArray(out.more_charts)) out.more_charts = out.more_charts.map(spec);
  if (Array.isArray(out.claims)) {
    out.claims = out.claims.map((c) => {
      if (!c || typeof c !== "object" || !Array.isArray((c as { checks?: unknown }).checks)) return c;
      const claim = c as { checks: unknown[] };
      return {
        ...claim,
        checks: claim.checks.map((ch) =>
          ch && typeof ch === "object" && !Array.isArray(ch)
            ? Object.fromEntries(Object.entries(ch).filter(([, v]) => v !== "" && v !== null))
            : ch,
        ),
      };
    });
  }
  return out;
}

/** The fixed part of the prompt (cached by the API): intro, rules and output shape. */
export function narrationInstructions(): string {
  return [INTRO, "", RULES, "## Output JSON shape", pyDumps(OUTPUT_SCHEMA, 1)].join("\n");
}

const num = (v: unknown) => (v === null || v === undefined ? "" : String(v));

export function chartRowsForPrompt(chartData: Row[], highlight: unknown): { rows: Row[]; cut: boolean } {
  if (chartData.length <= CHART_ROWS_MAX) return { rows: chartData, cut: false };
  const periods = [...new Set(chartData.map((r) => pyStr(r.period)))].sort();
  const keep = new Set([periods[0], periods[periods.length - 1]]);
  const wanted = new Set(Array.isArray(highlight) ? highlight : highlight ? [highlight] : []);
  return { rows: chartData.filter((r) => keep.has(pyStr(r.period)) || wanted.has(r.geography)), cut: true };
}

/** The per-story part of the prompt: chart, numbers, keys and chart data. */
export function narrationData(
  numbers: Record<string, unknown>,
  chartData: Row[],
  chartSpec: Record<string, unknown>,
): string {
  const columns = [...new Set(chartData.flatMap((r) => Object.keys(r)))].sort();
  const seriesValues = [...new Set(chartData.map((r) => pyStr(r.geography)))].sort();
  const keys = flattenNumbers(numbers as never);
  const { rows, cut } = chartRowsForPrompt(chartData, chartSpec.highlight);
  return [
    "## Chart",
    `chart_data columns: ${pyList(columns)}`,
    `geography values: ${pyList(seriesValues)}`,
    "Suggested chart_spec (adjust only if a different chart is clearer):",
    pyDumps(Object.fromEntries(Object.entries(chartSpec).filter(([k]) => k !== "more_charts"))),
    ...(Array.isArray(chartSpec.more_charts) && chartSpec.more_charts.length
      ? ["Suggested more_charts (optional):", pyDumps(chartSpec.more_charts)]
      : []),
    "",
    "## NUMBERS (context and meaning)",
    pyDumps(numbers, 1),
    "",
    "## KEYS (use these names in claims[].keys)",
    ...[...keys.entries()].map(([k, v]) => `${k} = ${decToString(v)}`),
    "",
    "## CHART DATA (keys: chart.<geography>.<period>.value, .lower, .upper)",
    ...(cut ? ["(large chart: first and last period and the highlighted rows only)"] : []),
    "geography,period,value,lower,upper",
    ...rows.map((r) => `${pyStr(r.geography)},${pyStr(r.period)},${num(r.value)},${num(r.lower)},${num(r.upper)}`),
  ].join("\n");
}

/** The whole prompt, for the copy-paste flow. */
export function buildPrompt(
  numbers: Record<string, unknown>,
  chartData: Row[],
  chartSpec: Record<string, unknown>,
): string {
  return `${narrationInstructions()}\n\n${narrationData(numbers, chartData, chartSpec)}`;
}
