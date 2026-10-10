export type Row = Record<string, string | number | null>;

export type ChartSpec = {
  type: 'line' | 'bar' | 'dot' | 'slope' | 'map';
  x: string;
  y: string;
  series?: string;
  highlight?: string | string[];
  annotation?: string;
  title?: string;
  yLabel?: string;
  start?: string;
  end?: string;
  period?: string;
};

export const MAX_COLOURED = 8;

/** Financial years read 2011–12, not 2011-12 (display only; data keeps its labels). */
export function enDash(text: string): string {
  return text.replace(/(?<![\w.])((?:19|20)\d{2})-(\d{2})(?!\d)/g, '$1–$2');
}

export function highlightList(spec: ChartSpec): string[] {
  if (!spec.highlight) return [];
  return Array.isArray(spec.highlight) ? spec.highlight : [spec.highlight];
}

/** Series in first-appearance order: colour follows the entity, never its rank. */
export function seriesOrder(data: Row[], key: string): string[] {
  const seen: string[] = [];
  for (const row of data) {
    const s = String(row[key]);
    if (!seen.includes(s)) seen.push(s);
  }
  return seen;
}

/** Series that get a palette colour (slot = index). Others are drawn in muted grey. */
export function colouredSeries(spec: ChartSpec, data: Row[]): string[] {
  if (!spec.series) return [];
  const hl = highlightList(spec);
  return (hl.length ? hl : seriesOrder(data, spec.series)).slice(0, MAX_COLOURED);
}

/** Spread label positions so none are closer than `gap`, keeping them inside [lo, hi]. */
export function dodge(ys: number[], gap: number, lo: number, hi: number): number[] {
  const order = ys.map((y, i) => [y, i] as const).sort((a, b) => a[0] - b[0]);
  const out = order.map(([y]) => y);
  for (let i = 1; i < out.length; i++) out[i] = Math.max(out[i], out[i - 1] + gap);
  const over = out.at(-1)! - hi;
  if (over > 0)
    for (let i = out.length - 1; i >= 0; i--)
      out[i] = Math.min(out[i], i === out.length - 1 ? hi : out[i + 1] - gap);
  for (let i = 0; i < out.length; i++) out[i] = Math.max(out[i], lo);
  const result: number[] = new Array(ys.length);
  order.forEach(([, idx], k) => (result[idx] = out[k]));
  return result;
}

/**
 * Which x labels to show so none overlap: at most one per `labelWidth` px of plot, and at
 * most every 2nd period when there are more than 8. Counts back from the last period so the
 * latest one is always labelled.
 */
export function pickTicks<T>(values: T[], plotWidth: number, labelWidth: number): T[] {
  const n = values.length;
  if (n === 0) return [];
  const fit = Math.max(2, Math.floor(plotWidth / labelWidth));
  const step = Math.max(n > 8 ? 2 : 1, Math.ceil(n / fit));
  return values.filter((_, i) => (n - 1 - i) % step === 0);
}
