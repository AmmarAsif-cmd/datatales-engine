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
