/**
 * TypeScript port of worker/datatales/narrate.py: reply validation and the prompt.
 * Must match Python (checked against worker/tests/golden/cases.json). The reply is parsed
 * with JSON.parse only; nothing in it is ever executed.
 */
import { decToString } from "./decimal.ts";
import { flattenNumbers } from "./verify.ts";

export const HEADLINE_MAX_CHARS = 70;
export const SUMMARY_MAX_WORDS = 120;
export const BODY_MAX_WORDS = 400;
export const VIDEO_MAX_WORDS = 90;

export class NarrationError extends Error {}

type Row = Record<string, string | number | null>;

export type Narration = {
  headline: string;
  hook: string;
  summary: string;
  body_md: string;
  video_script: string;
  chart_spec: {
    type: "line" | "bar" | "dot";
    x: string;
    y: string;
    series?: string | null;
    highlight?: string | string[] | null;
    annotation?: string | null;
    title?: string | null;
    yLabel?: string | null;
  };
  claims: { sentence: string; keys: string[] }[];
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
  checkExtra(obj, ["headline", "hook", "summary", "body_md", "video_script", "chart_spec", "claims"], "", p);

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
    if (wordCount(body) > BODY_MAX_WORDS) {
      p.push(["body_md", `Value error, is ${wordCount(body)} words; max ${BODY_MAX_WORDS}`]);
    } else if (/<\s*(script|iframe|style)|javascript:/i.test(body)) {
      p.push(["body_md", "Value error, must be plain Markdown (no scripts, iframes or styles)"]);
    }
  }
  const video = strField(obj, "video_script", "video_script", p, { strip: true, min: 10 });
  if (video !== undefined && wordCount(video) > VIDEO_MAX_WORDS) {
    p.push(["video_script", `Value error, is ${wordCount(video)} words; max ${VIDEO_MAX_WORDS}`]);
  }

  let spec: Narration["chart_spec"] | undefined;
  const rawSpec = obj.chart_spec;
  if (rawSpec === undefined) p.push(["chart_spec", "Field required"]);
  else if (!rawSpec || typeof rawSpec !== "object" || Array.isArray(rawSpec)) {
    p.push(["chart_spec", "Input should be a valid dictionary"]);
  } else {
    const s = rawSpec as Record<string, unknown>;
    const before = p.length;
    checkExtra(s, ["type", "x", "y", "series", "highlight", "annotation", "title", "yLabel"], "chart_spec.", p);
    if (!["line", "bar", "dot"].includes(s.type as string)) {
      p.push(["chart_spec.type", "Input should be 'line', 'bar' or 'dot'"]);
    }
    const x = strField(s, "x", "chart_spec.x", p);
    const y = strField(s, "y", "chart_spec.y", p);
    const series = strField(s, "series", "chart_spec.series", p, { optional: true });
    const annotation = strField(s, "annotation", "chart_spec.annotation", p, { optional: true, max: 200 });
    const title = strField(s, "title", "chart_spec.title", p, { optional: true, max: 120 });
    const yLabel = strField(s, "yLabel", "chart_spec.yLabel", p, { optional: true, max: 80 });
    const h = s.highlight;
    const hOk = h === undefined || h === null || typeof h === "string" || (Array.isArray(h) && h.every((x) => typeof x === "string"));
    if (!hOk) p.push(["chart_spec.highlight", "Input should be a valid string or list of strings"]);
    if (p.length === before) {
      spec = {
        type: s.type as "line" | "bar" | "dot",
        x: x as string,
        y: y as string,
        ...(series !== undefined ? { series } : {}),
        ...(h !== undefined && h !== null ? { highlight: h as string | string[] } : {}),
        ...(annotation !== undefined ? { annotation } : {}),
        ...(title !== undefined ? { title } : {}),
        ...(yLabel !== undefined ? { yLabel } : {}),
      };
    }
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
      checkExtra(co, ["sentence", "keys"], `${loc}.`, p);
      const sentence = strField(co, "sentence", `${loc}.sentence`, p, { strip: true, min: 5, max: 600 });
      const keys = co.keys;
      if (keys === undefined) p.push([`${loc}.keys`, "Field required"]);
      else if (!Array.isArray(keys) || !keys.every((k) => typeof k === "string")) {
        p.push([`${loc}.keys`, "Input should be a valid list of strings"]);
      } else if (keys.length < 1) p.push([`${loc}.keys`, "List should have at least 1 item after validation, not 0"]);
      else if (keys.length > 12) p.push([`${loc}.keys`, "List should have at most 12 items after validation"]);
      else if (sentence !== undefined) claims.push({ sentence, keys: keys.map((k) => (k as string).trim()) });
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
    chart_spec: spec as Narration["chart_spec"],
    claims,
  };
  checkChart(narration.chart_spec, chartData);
  return narration;
}

function checkChart(spec: Narration["chart_spec"], chartData: Row[]): void {
  const columns = new Set(chartData.flatMap((r) => Object.keys(r)));
  for (const field of ["x", "y", "series"] as const) {
    const col = spec[field];
    if (col !== undefined && col !== null && !columns.has(col)) {
      throw new NarrationError(
        `chart_spec.${field} '${col}' is not a chart_data column ${pyList([...columns].sort())}`,
      );
    }
  }
  if (spec.highlight !== undefined && spec.highlight !== null) {
    const wanted = Array.isArray(spec.highlight) ? spec.highlight : [spec.highlight];
    const key = spec.series ?? spec.x;
    const present = new Set(chartData.map((r) => pyStr(r[key])));
    const missing = wanted.filter((h) => !present.has(h));
    if (missing.length) {
      throw new NarrationError(`chart_spec.highlight ${pyList(missing)} not found in chart_data['${key}']`);
    }
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

export const OUTPUT_SCHEMA = {
  headline: `string, at most ${HEADLINE_MAX_CHARS} characters, search-friendly, e.g. "UK wellbeing by region 2011–2023"`,
  hook: "string, exactly one sentence",
  summary: `string, at most ${SUMMARY_MAX_WORDS} words`,
  body_md: `string, Markdown, at most ${BODY_MAX_WORDS} words, no headings above ##`,
  video_script: `string, at most ${VIDEO_MAX_WORDS} words, to be read aloud`,
  chart_spec: {
    type: "line | bar | dot",
    x: "column name in chart_data",
    y: "column name in chart_data",
    series: "column name in chart_data (optional)",
    highlight: "a value (or list of values) of the series column to highlight",
    annotation: "short note under the chart, at most 200 characters (optional)",
    title: "chart title, at most 120 characters (optional)",
    yLabel: "label for the values, e.g. the unit (optional)",
  },
  claims: [
    {
      sentence:
        "a sentence copied EXACTLY from headline/hook/summary/body_md/video_script that contains a number (other than a year)",
      keys: ["the KEYS (from the KEYS table) that each number in it comes from"],
    },
  ],
};

export const RULES = `Rules (follow every one):
1. Use ONLY numbers that appear in NUMBERS below. Do not calculate new numbers (no new
   differences, ratios, averages or percentages) and do not round to a different figure
   than one you could get by rounding a number given. Years must be within the data period.
2. UK English. Plain, calm language for a general reader. No hype words ("shocking",
   "soaring", "plummeting", "crisis").
3. Every change or gap in NUMBERS is statistically clear (confidence intervals do not
   overlap). Say "clearly higher/lower" if useful; never say "significant".
4. Respect polarity: \`higher_is_better\` and \`good_news\` say whether a rise is good. For
   anxiety, a LOWER score is better. Band labels for anxiety mean: Poor = high anxiety,
   Fair = medium, Good = low, Very good = very low anxiety. Never write "very good anxiety";
   write "very low anxiety".
5. When \`unit\` starts with "%", a change in \`change\` is in percentage points: write
   "5.4 percentage points", never "5.4%". \`pct_change\` is a relative change.
6. Look at \`series[].notable_moves\` and \`moves_shared_by_most_geographies\`. If they show a
   notable dip or rise (for example around 2020-21), mention it briefly with its numbers.
   If they are empty, do not invent one.
7. Describe the shape honestly. The findings compare the first and last year; \`series[].points\`
   has every year. If the series peaked or bottomed out in between (for example rose, then
   fell back), say so with those numbers instead of implying a steady trend.
8. Say where the data comes from (source name) and the period covered.
9. CLAIMS: for EVERY sentence in any field that contains a number other than a year, add
   one claim {"sentence": <the sentence copied exactly>, "keys": [<KEYS it uses>]}. Each
   number in the sentence must equal (after rounding) one of its keys. If the same sentence
   is used in two fields, one claim covers both. Count words like "four" as numbers.
10. Return ONLY a JSON object with exactly these keys, no Markdown fences, no comments.
`;

export function buildPrompt(
  numbers: Record<string, unknown>,
  chartData: Row[],
  chartSpec: Record<string, unknown>,
): string {
  const columns = [...new Set(chartData.flatMap((r) => Object.keys(r)))].sort();
  const seriesValues = [...new Set(chartData.map((r) => pyStr(r.geography)))].sort();
  const keys = flattenNumbers(numbers as never);
  return [
    "You are writing a short data story for DataTales (datatales.co.uk), a UK site",
    "that turns public data into plain, accurate stories. Python has already done all",
    "the maths; your job is only the words around the numbers below.",
    "",
    RULES,
    "## Output JSON shape",
    pyDumps(OUTPUT_SCHEMA, 1),
    "",
    "## Chart",
    `chart_data columns: ${pyList(columns)}`,
    `geography values: ${pyList(seriesValues)}`,
    "Suggested chart_spec (adjust only if a different chart is clearer):",
    pyDumps(chartSpec),
    "",
    "## NUMBERS (context and meaning)",
    pyDumps(numbers, 1),
    "",
    "## KEYS (use these names in claims[].keys)",
    ...[...keys.entries()].map(([k, v]) => `${k} = ${decToString(v)}`),
  ].join("\n");
}
