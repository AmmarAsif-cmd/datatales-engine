/**
 * TypeScript port of worker/datatales/chartfacts.py `evaluate`: rank and exclusivity checks
 * ("only", "all", "highest", "lowest", "biggest") against a story's chart_data.
 * Must match Python (golden cases in worker/tests/golden/cases.json, `chartfacts`).
 */
export const CHECK_KINDS = [
  "highest", "lowest", "only_rise", "only_fall",
  "all_rise", "all_fall", "biggest_rise", "biggest_fall",
] as const; // prettier-ignore
export type CheckKind = (typeof CHECK_KINDS)[number];

type Row = Record<string, string | number | null | undefined>;
type Point = [number, number | null, number | null]; // value, lower, upper
export type CheckInput = { kind?: unknown; group?: unknown; period?: unknown; start?: unknown; end?: unknown };

const NEEDS_PERIOD = ["highest", "lowest"];
const NEEDS_GROUP = ["highest", "lowest", "only_rise", "only_fall", "biggest_rise", "biggest_fall"];

const pyStr = (v: unknown) => (v === null || v === undefined ? "None" : String(v));

/** Python repr() of a str or None. */
function pyRepr(v: unknown): string {
  if (v === null || v === undefined) return "None";
  if (typeof v !== "string") return String(v);
  const quote = v.includes("'") && !v.includes('"') ? '"' : "'";
  const body = v.replace(/\\/g, "\\\\").replace(quote === "'" ? /'/g : /"/g, `\\${quote}`);
  return quote + body + quote;
}

/** Python f"{x:g}". */
export function fmtG(x: number): string {
  if (x === 0) return Object.is(x, -0) ? "-0" : "0";
  const [mant, expStr] = x.toExponential(5).split("e");
  const exp = Number(expStr);
  const strip = (s: string) => (s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s);
  if (exp < -4 || exp >= 6) {
    return `${strip(mant)}e${exp < 0 ? "-" : "+"}${String(Math.abs(exp)).padStart(2, "0")}`;
  }
  return strip(x.toFixed(Math.max(0, 5 - exp)));
}

/** Python round(x, 4) (ties are vanishingly rare in practice). */
const round4 = (x: number) => Number(x.toFixed(4));

export function byGroup(chartData: Row[]): Map<string, Map<string, Point>> {
  const out = new Map<string, Map<string, Point>>();
  for (const row of chartData) {
    if (row.value === null || row.value === undefined) continue;
    const g = pyStr(row.geography);
    if (!out.has(g)) out.set(g, new Map());
    out.get(g)!.set(pyStr(row.period), [
      Number(row.value),
      row.lower === null || row.lower === undefined ? null : Number(row.lower),
      row.upper === null || row.upper === undefined ? null : Number(row.upper),
    ]);
  }
  return out;
}

function clearChange(a: Point, b: Point): boolean {
  if (a[1] === null || a[2] === null || b[1] === null || b[2] === null) return false;
  return a[2] < b[1] || b[2] < a[1];
}

export function evaluate(check: CheckInput, chartData: Row[]): [boolean, string] {
  const kind = check.kind as CheckKind;
  if (!CHECK_KINDS.includes(kind)) return [false, `unknown check kind ${pyRepr(check.kind)}`];
  const groups = byGroup(chartData);
  const group = check.group as string;
  if (NEEDS_GROUP.includes(kind) && !(typeof group === "string" && groups.has(group))) {
    return [false, `group ${pyRepr(check.group)} is not in the chart data`];
  }

  if (NEEDS_PERIOD.includes(kind)) {
    const period = pyStr(check.period);
    const has = typeof check.period === "string";
    const at = new Map<string, Point>();
    for (const [g, pts] of groups) if (has && pts.has(period)) at.set(g, pts.get(period)!);
    if (!at.has(group)) return [false, `no value for ${pyStr(group)} in ${period}`];
    if (at.size < 2) return [false, `fewer than two groups have a value in ${period}`];
    const ranked = [...at.entries()].sort((a, b) => (kind === "highest" ? b[1][0] - a[1][0] : a[1][0] - b[1][0]));
    const [top, [runner, rv]] = ranked;
    if (top[0] !== group) return [false, `${top[0]} (${fmtG(top[1][0])}) is ${kind} in ${period}, not ${group}`];
    const gv = at.get(group)!;
    if (gv[1] === null || gv[2] === null || rv[1] === null || rv[2] === null) {
      return [false, "confidence intervals unknown"];
    }
    const clear = kind === "highest" ? gv[1] > rv[2] : gv[2] < rv[1];
    if (!clear) return [false, `${group} (${fmtG(gv[0])}) is not clearly apart from ${runner} (${fmtG(rv[0])})`];
    return [true, `${group} ${fmtG(gv[0])} vs next ${runner} ${fmtG(rv[0])} in ${period}, clear`];
  }

  const start = pyStr(check.start);
  const end = pyStr(check.end);
  const ok = typeof check.start === "string" && typeof check.end === "string";
  const both = new Map<string, [Point, Point]>();
  for (const [g, pts] of groups) if (ok && pts.has(start) && pts.has(end)) both.set(g, [pts.get(start)!, pts.get(end)!]);
  if (both.size < 2) return [false, `fewer than two groups have values for both ${start} and ${end}`];
  const change = new Map([...both].map(([g, [s, e]]) => [g, e[0] - s[0]]));
  const rising = kind.endsWith("rise");

  if (kind === "all_rise" || kind === "all_fall") {
    const moved = [...change.values()].filter((c) => (rising ? c > 0 : c < 0)).length;
    return [moved === change.size, `${moved} of ${change.size} groups ${rising ? "rose" : "fell"}`];
  }

  if (!both.has(group)) return [false, `${group} has no values for both ${start} and ${end}`];
  const own = change.get(group)!;
  if (rising ? own <= 0 : own >= 0) {
    return [false, `${group} ${rising ? "did not rise" : "did not fall"} (${fmtG(round4(own))})`];
  }
  if (!clearChange(...both.get(group)!)) {
    return [false, `${group}'s change (${fmtG(round4(own))}) is within the confidence intervals`];
  }
  const others = [...change].filter(([g]) => g !== group);
  if (kind.startsWith("only")) {
    const same = others.filter(([, c]) => (rising ? c > 0 : c < 0)).map(([g]) => g).sort();
    if (same.length) return [false, `${same.join(", ")} also ${rising ? "rose" : "fell"}`];
    return [true, `${group} ${fmtG(round4(own))}; all ${others.length} others did not`];
  }
  const values = others.map(([, c]) => c);
  const best = rising ? Math.max(...values) : Math.min(...values);
  if (rising ? own <= best : own >= best) return [false, `${group} (${fmtG(round4(own))}) is not the biggest change`];
  return [true, `${group} ${fmtG(round4(own))}, next ${fmtG(round4(best))}`];
}
