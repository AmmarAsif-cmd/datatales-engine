import { enDash, highlightList, type ChartSpec, type Row } from './chart';

export { enDash };

/** First and last period in the chart data, e.g. ["2011-12", "2022-23"]. */
export function periodRange(data: Row[], key = 'period'): [string, string] | null {
  const periods = [
    ...new Set(
      data
        .map((r) => r[key])
        .filter((v) => v != null)
        .map(String),
    ),
  ].sort();
  return periods.length ? [periods[0], periods[periods.length - 1]] : null;
}

export type PivotTable = {
  rowKey: string;
  columns: string[];
  /** Group whose confidence interval is shown, if the data has lower/upper. */
  ciFor: string | null;
  rows: { label: string; values: (number | null)[]; ci: [number, number] | null }[];
};

/**
 * Periods down the side, one column per group (highlighted group first), plus the 95%
 * confidence interval for the highlighted group.
 */
export function pivot(spec: ChartSpec, data: Row[]): PivotTable {
  const rowKey = spec.x;
  const groupKey = spec.series ?? 'geography';
  const groups = [...new Set(data.map((r) => String(r[groupKey])))];
  const hl = highlightList(spec).filter((h) => groups.includes(h));
  const columns = [...hl, ...groups.filter((g) => !hl.includes(g))];
  const hasCi = data.some((r) => typeof r.lower === 'number' && typeof r.upper === 'number');
  const ciFor = hasCi ? (columns[0] ?? null) : null;
  const labels = [...new Set(data.map((r) => String(r[rowKey])))].sort();
  const at = new Map(data.map((r) => [`${r[rowKey]}\u0000${r[groupKey]}`, r]));
  return {
    rowKey,
    columns,
    ciFor,
    rows: labels.map((label) => {
      const ciRow = ciFor ? at.get(`${label}\u0000${ciFor}`) : undefined;
      return {
        label,
        values: columns.map((g) => {
          const v = at.get(`${label}\u0000${g}`)?.[spec.y];
          return typeof v === 'number' ? v : null;
        }),
        ci:
          ciRow && typeof ciRow.lower === 'number' && typeof ciRow.upper === 'number'
            ? [ciRow.lower, ciRow.upper]
            : null,
      };
    }),
  };
}

const csvCell = (v: unknown) => {
  const s = v === null || v === undefined ? '' : String(v);
  // Quote when needed; prefix formula-like text so spreadsheets never evaluate it.
  const safe = /^[=+\-@\t\r]/.test(s) && Number.isNaN(Number(s)) ? `'${s}` : s;
  return /[",\n\r]/.test(safe) ? `"${safe.replace(/"/g, '""')}"` : safe;
};

const CSV_FIRST = ['period', 'geography', 'value', 'lower', 'upper'];

/** The chart data as CSV: period, geography, value, lower, upper, then any other columns. */
export function toCsv(data: Row[]): string {
  const seen = new Set(data.flatMap((r) => Object.keys(r)));
  const columns = [
    ...CSV_FIRST.filter((c) => seen.has(c)),
    ...[...seen].filter((c) => !CSV_FIRST.includes(c)),
  ];
  const lines = [columns.map(csvCell).join(',')];
  for (const r of data) lines.push(columns.map((c) => csvCell(r[c])).join(','));
  return lines.join('\r\n') + '\r\n';
}

const OG = { w: 1200, h: 630 };
const PALETTE = {
  bg: '#fcfcfb',
  grid: '#e1e0d9',
  other: '#b9b8b1',
  accent: '#5a3fe0',
  series: ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948'],
};

/**
 * A text-free SVG of the story's chart for the social card (no fonts needed, so it renders
 * the same on any build machine). Highlighted groups in palette colours, others grey.
 */
export function ogSvg(spec: ChartSpec, data: Row[]): string {
  const groupKey = spec.series ?? 'geography';
  const xs = [...new Set(data.map((r) => String(r[spec.x])))].sort();
  const values = data.map((r) => r[spec.y]).filter((v): v is number => typeof v === 'number');
  const pad = { l: 90, r: 90, t: 130, b: 80 };
  const plotW = OG.w - pad.l - pad.r;
  const plotH = OG.h - pad.t - pad.b;
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const yMin = lo - span * 0.1;
  const yMax = hi + span * 0.1;
  const x = (label: string) =>
    pad.l + (xs.length < 2 ? plotW / 2 : (xs.indexOf(label) / (xs.length - 1)) * plotW);
  const y = (v: number) => pad.t + (1 - (v - yMin) / (yMax - yMin)) * plotH;
  const groups = [...new Set(data.map((r) => String(r[groupKey])))];
  const hl = highlightList(spec);
  const coloured = (hl.length ? hl : groups).slice(0, PALETTE.series.length);
  const line = (g: string) => {
    const pts = data
      .filter((r) => String(r[groupKey]) === g && typeof r[spec.y] === 'number')
      .sort((a, b) => xs.indexOf(String(a[spec.x])) - xs.indexOf(String(b[spec.x])))
      .map((r) => [x(String(r[spec.x])), y(r[spec.y] as number)] as const);
    return pts;
  };
  const path = (pts: readonly (readonly [number, number])[]) =>
    pts.map(([px, py], i) => `${i ? 'L' : 'M'}${px.toFixed(1)},${py.toFixed(1)}`).join('');
  const grid = [0, 0.25, 0.5, 0.75, 1]
    .map((f) => pad.t + f * plotH)
    .map(
      (gy) =>
        `<line x1="${pad.l}" x2="${OG.w - pad.r}" y1="${gy}" y2="${gy}" stroke="${PALETTE.grid}" stroke-width="2"/>`,
    )
    .join('');
  const others = groups
    .filter((g) => !coloured.includes(g))
    .map(
      (g) =>
        `<path d="${path(line(g))}" fill="none" stroke="${PALETTE.other}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>`,
    )
    .join('');
  const main = coloured
    .map((g, i) => {
      const pts = line(g);
      const colour = PALETTE.series[i];
      const last = pts[pts.length - 1];
      return (
        `<path d="${path(pts)}" fill="none" stroke="${colour}" stroke-width="9" stroke-linejoin="round" stroke-linecap="round"/>` +
        (last
          ? `<circle cx="${last[0]}" cy="${last[1]}" r="14" fill="${colour}" stroke="${PALETTE.bg}" stroke-width="6"/>`
          : '')
      );
    })
    .join('');
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${OG.w}" height="${OG.h}" viewBox="0 0 ${OG.w} ${OG.h}">` +
    `<rect width="100%" height="100%" fill="${PALETTE.bg}"/>` +
    `<rect width="100%" height="14" fill="${PALETTE.accent}"/>` +
    grid +
    others +
    main +
    `</svg>`
  );
}

export const OG_SIZE = OG;
