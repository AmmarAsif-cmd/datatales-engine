/**
 * Alt text for every chart and cover image, written from the story's chart_data (the
 * code-computed values the story was verified against) and its verified chart facts.
 * Nothing here is free text from the narration except chart titles.
 *
 * Shared file: the dashboard keeps an identical copy (scripts/sync-graphics.mjs).
 */

export type Row = Record<string, string | number | null | undefined>;
export type Spec = {
  type: 'line' | 'bar' | 'dot' | 'slope' | 'map';
  x: string;
  y: string;
  series?: string | null;
  highlight?: string | string[] | null;
  title?: string | null;
  yLabel?: string | null;
  start?: string | null;
  end?: string | null;
  period?: string | null;
};
export type ChartFacts = {
  groups_compared?: number;
  supported_checks?: {
    kind: string;
    group?: string;
    period?: string;
    start?: string;
    end?: string;
  }[];
};
export type Cover = {
  group?: string;
  value?: string;
  label?: string;
  change?: string;
  badge?: string;
};

/** Financial years read 2011–12, not 2011-12 (display only; data keeps its labels). */
export function enDash(text: string): string {
  return text.replace(/(?<![\w.])((?:19|20)\d{2})-(\d{2})(?!\d)/g, '$1–$2');
}

export const isPercent = (spec: Spec) => (spec.yLabel ?? '').trim().startsWith('%');

/** Like the worker's format_value: up to 2 decimals, "%" for percentage units. */
export function formatValue(v: number, percent: boolean): string {
  const text = (Math.round(v * 100) / 100).toLocaleString('en-GB', { maximumFractionDigits: 2 });
  return percent ? `${text}%` : text;
}

export function highlights(spec: Spec): string[] {
  if (!spec.highlight) return [];
  return Array.isArray(spec.highlight) ? spec.highlight : [spec.highlight];
}

export function periodsOf(spec: Spec, data: Row[]): string[] {
  return [
    ...new Set(data.filter((r) => typeof r[spec.y] === 'number').map((r) => String(r[spec.x]))),
  ].sort();
}

export function groupsOf(spec: Spec, data: Row[]): string[] {
  const key = spec.series ?? spec.x;
  return [...new Set(data.map((r) => String(r[key])))];
}

export function valueAt(spec: Spec, data: Row[], group: string, period: string): number | null {
  const key = spec.series ?? spec.x;
  const row = data.find((r) => String(r[key]) === group && String(r[spec.x]) === period);
  const v = row?.[spec.y];
  return typeof v === 'number' ? v : null;
}

const listJoin = (items: string[]) =>
  items.length <= 1 ? (items[0] ?? '') : `${items.slice(0, -1).join(', ')} and ${items.at(-1)}`;

function movement(spec: Spec, data: Row[], group: string, a: string, b: string, pct: boolean) {
  const v0 = valueAt(spec, data, group, a);
  const v1 = valueAt(spec, data, group, b);
  if (v0 === null || v1 === null) return null;
  const f = (v: number) => formatValue(v, pct);
  const verb = v1 > v0 ? 'rose' : v1 < v0 ? 'fell' : 'was unchanged';
  return verb === 'was unchanged'
    ? `${group} was unchanged at ${f(v0)}`
    : `${group} ${verb} from ${f(v0)} in ${enDash(a)} to ${f(v1)} in ${enDash(b)}`;
}

function factSentences(facts: ChartFacts | undefined, group: string, n: number): string[] {
  const out: string[] = [];
  for (const c of facts?.supported_checks ?? []) {
    if (c.group && c.group !== group) continue;
    const span = c.start && c.end ? ` between ${enDash(c.start)} and ${enDash(c.end)}` : '';
    if (c.kind === 'only_rise') out.push(`It was the only one of the ${n} to rise${span}.`);
    if (c.kind === 'only_fall') out.push(`It was the only one of the ${n} to fall${span}.`);
    if (c.kind === 'highest' && c.period)
      out.push(`In ${enDash(c.period)} it was the highest of the ${n}.`);
    if (c.kind === 'lowest' && c.period)
      out.push(`In ${enDash(c.period)} it was the lowest of the ${n}.`);
  }
  return out;
}

const KIND: Record<Spec['type'], string> = {
  line: 'Line chart',
  bar: 'Bar chart',
  dot: 'Dot chart',
  slope: 'Slope chart',
  map: 'Map',
};

/** Alt text for one chart. */
export function chartAlt(spec: Spec, data: Row[], title: string, facts?: ChartFacts): string {
  const pct = isPercent(spec);
  const f = (v: number) => formatValue(v, pct);
  const periods = periodsOf(spec, data);
  const groups = groupsOf(spec, data);
  const hl = highlights(spec).filter((h) => groups.includes(h));
  const others = groups.filter((g) => !hl.includes(g));
  const unit = spec.yLabel ? ` (${spec.yLabel})` : '';
  const parts = [`${KIND[spec.type]}: ${enDash(title)}${unit}.`];

  if (spec.type === 'line' || spec.type === 'slope') {
    const a = spec.type === 'slope' && spec.start ? spec.start : periods[0];
    const b = spec.type === 'slope' && spec.end ? spec.end : periods.at(-1)!;
    if (!a || !b) return parts[0];
    parts.push(
      spec.type === 'slope'
        ? `It compares ${enDash(a)} with ${enDash(b)} for ${groups.length} areas.`
        : `It shows ${groups.length} ${groups.length === 1 ? 'series' : 'areas'} from ${enDash(a)} to ${enDash(b)}.`,
    );
    for (const g of hl) {
      const move = movement(spec, data, g, a, b, pct);
      if (move) parts.push(`${move.replace(g, `${g}, highlighted,`)}.`);
      if (spec.type === 'line') {
        const pts = periods
          .map((p) => [p, valueAt(spec, data, g, p)] as const)
          .filter((x): x is readonly [string, number] => x[1] !== null);
        const peak = pts.reduce((m, x) => (x[1] > m[1] ? x : m), pts[0]);
        if (peak && peak[0] !== a && peak[0] !== b)
          parts.push(`It peaked at ${f(peak[1])} in ${enDash(peak[0])}.`);
      }
      parts.push(...factSentences(facts, g, groups.length));
    }
    if (others.length && others.length <= 6) {
      const moves = others
        .map((g) => movement(spec, data, g, a, b, pct))
        .filter(Boolean) as string[];
      if (moves.length) parts.push(`Shown in grey: ${listJoin(moves)}.`);
    } else if (others.length) {
      const last = others
        .map((g) => valueAt(spec, data, g, b))
        .filter((v): v is number => v !== null);
      if (last.length) {
        parts.push(
          `The other ${others.length} areas are shown in grey; in ${enDash(b)} they ranged from ${f(Math.min(...last))} to ${f(Math.max(...last))}.`,
        );
      }
    }
    return parts.join(' ');
  }

  if (spec.type === 'map') {
    const period = spec.period ?? periods.at(-1);
    if (!period) return parts[0];
    const vals = groups
      .map((g) => [g, valueAt(spec, data, g, period)] as const)
      .filter((x): x is readonly [string, number] => x[1] !== null)
      .sort((x, y) => x[1] - y[1]);
    parts[0] = `Map: ${enDash(title)}${unit}, ${enDash(period)}.`;
    for (const g of hl) {
      const v = valueAt(spec, data, g, period);
      if (v !== null) parts.push(`${g}, outlined, ${f(v)}.`);
    }
    if (vals.length > 1) {
      const lo = vals[0];
      const hi = vals.at(-1)!;
      parts.push(
        `Values range from ${f(lo[1])} in ${lo[0]} to ${f(hi[1])} in ${hi[0]}; a stronger colour means a higher value.`,
      );
    }
    if (vals.length <= 6) parts.push(`${listJoin(vals.map(([g, v]) => `${g} ${f(v)}`))}.`);
    parts.push('Areas without data are grey.');
    return parts.join(' ');
  }

  // bar / dot: one value per category
  const key = spec.series ?? spec.x;
  const rows = data
    .filter((r) => typeof r[spec.y] === 'number')
    .map((r) => [String(r[key]), r[spec.y] as number] as const)
    .sort((x, y) => y[1] - x[1]);
  const shown = rows
    .slice(0, 12)
    .map(([g, v]) => `${g} ${f(v)}${hl.includes(g) ? ' (highlighted)' : ''}`);
  parts.push(`${listJoin(shown)}${rows.length > 12 ? `, and ${rows.length - 12} more` : ''}.`);
  return parts.join(' ');
}

/** Alt text for the cover image (headline, key number, badge, and what the chart shows). */
export function coverAlt(headline: string, cover: Cover, spec: Spec, data: Row[]): string {
  const parts = [`${enDash(headline)}.`];
  if (cover.value && cover.label) parts.push(`${cover.value}: ${enDash(cover.label)}.`);
  if (cover.change) parts.push(`${enDash(cover.change)}.`);
  if (cover.badge) parts.push(`${enDash(cover.badge)}.`);
  const periods = periodsOf(spec, data);
  const hl = highlights(spec)[0];
  if (hl && periods.length > 1) {
    parts.push(
      `Small line chart from ${enDash(periods[0])} to ${enDash(periods.at(-1)!)} with ${hl} in colour and the others in grey.`,
    );
  }
  return parts.join(' ');
}
