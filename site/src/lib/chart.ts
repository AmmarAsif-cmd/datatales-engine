export type Row = Record<string, string | number | null>;

export type ChartSpec = {
  type: 'line' | 'bar' | 'dot';
  x: string;
  y: string;
  series?: string;
  highlight?: string | string[];
  annotation?: string;
  title?: string;
  yLabel?: string;
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
