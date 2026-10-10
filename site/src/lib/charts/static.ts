/**
 * Slope charts and UK choropleth maps, rendered to SVG at build time (no client JS).
 * Colours come from the site's CSS variables (with light-theme fallbacks, so a standalone
 * SVG still renders), which makes them follow the light/dark theme like the Plot charts.
 * Every line or area has a <title> tooltip.
 */
import {
  enDash,
  formatValue,
  groupsOf,
  highlights,
  isPercent,
  periodsOf,
  valueAt,
  type Row,
  type Spec,
} from '../graphics/alt.ts';
import { dodge } from '../chart.ts';
import nations from '../../data/geo/nations.json' with { type: 'json' };
import regions from '../../data/geo/regions.json' with { type: 'json' };
import lads from '../../data/geo/local-authorities.json' with { type: 'json' };

type GeoFile = {
  attribution: string;
  unit: number;
  features: { code: string; name: string; rings: number[][] }[];
};

const V = {
  ink: 'var(--ink, #111110)',
  ink2: 'var(--ink-2, #52514e)',
  muted: 'var(--muted, #6f6e69)',
  grid: 'var(--chart-grid, #e1e0d9)',
  other: 'var(--chart-muted, #b9b8b1)',
  surface: 'var(--chart-surface, #fcfcfb)',
  empty: 'var(--surface-2, #f4f3ef)',
  series: (i: number) =>
    `var(--series-${i + 1}, ${['#2a78d6', '#eb6834', '#1baf7a', '#eda100'][i] ?? '#2a78d6'})`,
  seq: (i: number) =>
    `var(--seq-${i + 1}, ${['#c9dcf4', '#9cc0ec', '#6399dc', '#2b66ad', '#1b4f91'][i]})`,
  /** Label colour with at least 4.5:1 contrast on --seq-N, in either theme. */
  seqInk: (i: number) => `var(--seq-ink-${i + 1}, ${i >= 3 ? '#ffffff' : '#111110'})`,
};

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const n1 = (v: number) => Math.round(v * 10) / 10;
const FONT = `font-family="system-ui, -apple-system, 'Segoe UI', sans-serif"`;

export type StaticOpts = { title: string; standalone?: boolean; describedBy?: string };

/** SVG for slope and map charts; null for the types drawn by the Plot island. */
export function renderStaticChart(spec: Spec, data: Row[], opts: StaticOpts): string | null {
  if (spec.type === 'slope') return slope(spec, data, opts);
  if (spec.type === 'map') return map(spec, data, opts);
  return null;
}

function svgOpen(w: number, h: number, opts: StaticOpts, label: string) {
  const ns = opts.standalone ? ' xmlns="http://www.w3.org/2000/svg"' : '';
  const bg = opts.standalone ? `<rect width="${w}" height="${h}" fill="#fcfcfb"/>` : '';
  const desc = opts.describedBy ? ` aria-describedby="${esc(opts.describedBy)}"` : '';
  return `<svg${ns} viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${esc(label)}"${desc} class="static-chart" style="max-width: ${w}px" ${FONT}>${bg}`;
}

/** Rough text width for the system UI font (static SVG text is laid out by the browser). */
const textWidth = (s: string, size: number, bold = false) => s.length * size * (bold ? 0.6 : 0.56);

function slope(spec: Spec, data: Row[], opts: StaticOpts): string {
  const periods = periodsOf(spec, data);
  const a = spec.start ?? periods[0];
  const b = spec.end ?? periods.at(-1)!;
  const groups = groupsOf(spec, data).filter(
    (g) => valueAt(spec, data, g, a) !== null && valueAt(spec, data, g, b) !== null,
  );
  const hl = highlights(spec).filter((g) => groups.includes(g));
  const pct = isPercent(spec);
  const labelled = groups.length <= 12 ? groups : hl;
  const FS = 14;
  const GAP = 36; // two-line labels: name over value
  // Size to the content: label widths set the margins, label count sets the height.
  const labelW = Math.max(
    60,
    ...labelled.map((g) =>
      Math.max(
        textWidth(g, FS, hl.includes(g)),
        textWidth(formatValue(valueAt(spec, data, g, b)!, pct), FS),
      ),
    ),
  );
  const xa = Math.ceil(labelW) + 14;
  const xb = xa + 96;
  const W = xb + 14 + Math.ceil(labelW) + 6;
  const top = 46;
  const bottom = top + Math.max(170, (labelled.length - 1) * GAP + 30);
  const H = bottom + (groups.length > labelled.length ? 34 : 18);
  const vals = groups.flatMap((g) => [valueAt(spec, data, g, a)!, valueAt(spec, data, g, b)!]);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = (hi - lo || 1) * 0.04;
  const y = (v: number) => top + (1 - (v - lo + pad) / (hi - lo + 2 * pad)) * (bottom - top);
  const order = [...groups.filter((g) => !hl.includes(g)), ...hl]; // highlighted drawn last
  const out = [svgOpen(W, H, opts, opts.title)];
  out.push(
    `<text x="${xa}" y="20" text-anchor="middle" font-size="${FS + 1}" font-weight="700" fill="${V.ink2}">${esc(enDash(a))}</text>`,
    `<text x="${xb}" y="20" text-anchor="middle" font-size="${FS + 1}" font-weight="700" fill="${V.ink2}">${esc(enDash(b))}</text>`,
    `<line x1="${xa}" x2="${xa}" y1="30" y2="${bottom}" stroke="${V.grid}"/>`,
    `<line x1="${xb}" x2="${xb}" y1="30" y2="${bottom}" stroke="${V.grid}"/>`,
  );
  for (const g of order) {
    const i = hl.indexOf(g);
    const colour = i >= 0 ? V.series(i) : V.other;
    const va = valueAt(spec, data, g, a)!;
    const vb = valueAt(spec, data, g, b)!;
    const tip = `${g}: ${formatValue(va, pct)} in ${enDash(a)}, ${formatValue(vb, pct)} in ${enDash(b)}`;
    out.push(
      `<g><title>${esc(tip)}</title>` +
        `<line x1="${xa}" y1="${n1(y(va))}" x2="${xb}" y2="${n1(y(vb))}" stroke="${colour}" stroke-width="${i >= 0 ? 3 : 1.75}" stroke-linecap="round"/>` +
        `<line x1="${xa}" y1="${n1(y(va))}" x2="${xb}" y2="${n1(y(vb))}" stroke="transparent" stroke-width="14"/>` +
        `<circle cx="${xa}" cy="${n1(y(va))}" r="${i >= 0 ? 5 : 4}" fill="${colour}" stroke="${V.surface}" stroke-width="2"/>` +
        `<circle cx="${xb}" cy="${n1(y(vb))}" r="${i >= 0 ? 5 : 4}" fill="${colour}" stroke="${V.surface}" stroke-width="2"/></g>`,
    );
  }
  // Both sides: name over value, spread so no two labels overlap.
  const side = (period: string, x: number, anchor: 'start' | 'end') => {
    const ys = dodge(
      labelled.map((g) => y(valueAt(spec, data, g, period)!)),
      GAP,
      top - 4,
      bottom + 4,
    );
    labelled.forEach((g, k) => {
      const strong = hl.includes(g);
      const v = formatValue(valueAt(spec, data, g, period)!, pct);
      out.push(
        `<text x="${x}" y="${n1(ys[k] - 2)}" text-anchor="${anchor}" font-size="${FS}" font-weight="${strong ? 700 : 400}" fill="${strong ? V.ink : V.ink2}">${esc(g)}</text>`,
        `<text x="${x}" y="${n1(ys[k] + FS - 1)}" text-anchor="${anchor}" font-size="${FS}" font-weight="${strong ? 700 : 400}" fill="${strong ? V.ink : V.muted}">${esc(v)}</text>`,
      );
    });
  };
  side(a, xa - 12, 'end');
  side(b, xb + 12, 'start');
  if (groups.length > labelled.length) {
    out.push(
      `<text x="${xb + 12}" y="${H - 8}" font-size="12" fill="${V.muted}">${groups.length - hl.length} other areas in grey</text>`,
    );
  }
  out.push('</svg>');
  return out.join('');
}

// ---- maps ----

export function boundariesFor(codes: string[]): GeoFile | null {
  const files = [nations, regions, lads] as GeoFile[];
  const want = new Set(codes);
  // the smallest file that has every code
  return (
    files.find((f) => codes.every((c) => f.features.some((ft) => ft.code === c))) ??
    files.find((f) => f.features.some((ft) => want.has(ft.code))) ??
    null
  );
}

/** Douglas-Peucker on a closed flat [x, y, ...] ring already in pixels. A closed ring starts
 * and ends on the same point, so it is split at the point farthest from the start. */
function simplify(pts: number[], tol: number): number[] {
  const n = pts.length / 2;
  if (n <= 4) return pts;
  let far = 0;
  let best = -1;
  for (let i = 1; i < n; i++) {
    const d = Math.hypot(pts[2 * i] - pts[0], pts[2 * i + 1] - pts[1]);
    if (d > best) [far, best] = [i, d];
  }
  const a = simplifyOpen(pts.slice(0, 2 * far + 2), tol);
  const b = simplifyOpen(pts.slice(2 * far), tol);
  return [...a, ...b.slice(2)];
}

function simplifyOpen(pts: number[], tol: number): number[] {
  const n = pts.length / 2;
  if (n <= 4) return pts;
  const keep = new Uint8Array(n);
  keep[0] = keep[n - 1] = 1;
  const stack: [number, number][] = [[0, n - 1]];
  while (stack.length) {
    const [s, e] = stack.pop()!;
    const [x1, y1, x2, y2] = [pts[2 * s], pts[2 * s + 1], pts[2 * e], pts[2 * e + 1]];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.hypot(dx, dy) || 1;
    let best = -1;
    let dist = tol;
    for (let i = s + 1; i < e; i++) {
      const d = Math.abs(dy * pts[2 * i] - dx * pts[2 * i + 1] + x2 * y1 - y2 * x1) / len;
      if (d > dist) [best, dist] = [i, d];
    }
    if (best >= 0) {
      keep[best] = 1;
      stack.push([s, best], [best, e]);
    }
  }
  const out: number[] = [];
  for (let i = 0; i < n; i++) if (keep[i]) out.push(pts[2 * i], pts[2 * i + 1]);
  return out;
}

function ringArea(r: number[]): number {
  let a = 0;
  for (let i = 0; i < r.length; i += 2) {
    const j = (i + 2) % r.length;
    a += r[i] * r[j + 1] - r[j] * r[i + 1];
  }
  return a / 2;
}

function centroid(r: number[]): [number, number] {
  let cx = 0;
  let cy = 0;
  let a = 0;
  for (let i = 0; i < r.length; i += 2) {
    const j = (i + 2) % r.length;
    const f = r[i] * r[j + 1] - r[j] * r[i + 1];
    cx += (r[i] + r[j]) * f;
    cy += (r[i + 1] + r[j + 1]) * f;
    a += f;
  }
  return a ? [cx / (3 * a), cy / (3 * a)] : [r[0], r[1]];
}

export const MAP_BINS = 5;

function map(spec: Spec, data: Row[], opts: StaticOpts): string {
  const key = spec.series ?? 'geography';
  const periods = periodsOf(spec, data);
  const period = spec.period ?? periods.at(-1)!;
  const rows = data.filter((r) => String(r[spec.x]) === period && typeof r[spec.y] === 'number');
  const byCode = new Map(rows.map((r) => [String(r.code), r]));
  const geo = boundariesFor([...byCode.keys()]);
  if (!geo)
    throw new Error(`map: no boundaries for codes ${[...byCode.keys()].slice(0, 5).join(', ')}`);
  const missing = [...byCode.keys()].filter((c) => !geo.features.some((f) => f.code === c));
  if (missing.length) throw new Error(`map: no boundary for ${missing.join(', ')}`);

  const pct = isPercent(spec);
  const hl = new Set(highlights(spec));
  const vals = rows.map((r) => r[spec.y] as number);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const bin = (v: number) =>
    hi === lo
      ? MAP_BINS - 1
      : Math.min(MAP_BINS - 1, Math.floor(((v - lo) / (hi - lo)) * MAP_BINS));

  let [minX, minY, maxX, maxY] = [Infinity, Infinity, -Infinity, -Infinity];
  for (const f of geo.features)
    for (const r of f.rings)
      for (let i = 0; i < r.length; i += 2) {
        minX = Math.min(minX, r[i]);
        maxX = Math.max(maxX, r[i]);
        minY = Math.min(minY, r[i + 1]);
        maxY = Math.max(maxY, r[i + 1]);
      }
  const W = 320; // drawn close to 1:1 on a phone, so legend text stays readable
  const mapH = Math.round((W - 20) * ((maxY - minY) / (maxX - minX)));
  const legendH = 26 + MAP_BINS * 21 + 24 + 34;
  const H = mapH + 20 + legendH;
  const k = (W - 20) / (maxX - minX);
  const tx = (x: number) => 10 + (x - minX) * k;
  const ty = (y: number) => 10 + (maxY - y) * k;
  const project = (r: number[]) => {
    const p: number[] = [];
    for (let i = 0; i < r.length; i += 2) p.push(tx(r[i]), ty(r[i + 1]));
    return simplify(p, 0.35);
  };
  const d = (rings: number[][]) =>
    rings
      .map(project)
      .filter((p) => p.length >= 6 && Math.abs(ringArea(p)) > 0.4)
      .map(
        (p) =>
          `M${p
            .map((v, i) => (i % 2 ? n1(v) : `${i ? 'L' : ''}${n1(v)}`))
            .join(' ')
            .replace(/ L/g, 'L')}Z`,
      )
      .join('');

  const out = [svgOpen(W, H, opts, opts.title)];
  const outlines: string[] = [];
  const labels: string[] = [];
  for (const f of geo.features) {
    const row = byCode.get(f.code);
    const v = row ? (row[spec.y] as number) : null;
    const name = row ? String(row[key]) : f.name;
    const fill = v === null ? V.empty : V.seq(bin(v));
    const tip = v === null ? `${f.name}: no data` : `${name}: ${formatValue(v, pct)}`;
    const path = d(f.rings);
    out.push(
      `<path d="${path}" fill="${fill}" stroke="${V.surface}" stroke-width="0.6" fill-rule="evenodd"><title>${esc(tip)}</title></path>`,
    );
    if (row && hl.has(name))
      outlines.push(
        `<path d="${path}" fill="none" stroke="${V.ink}" stroke-width="2.25" stroke-linejoin="round" pointer-events="none"/>`,
      );
    if (v !== null && rows.length <= 4) {
      const big = f.rings.reduce(
        (m, r) => (Math.abs(ringArea(r)) > Math.abs(ringArea(m)) ? r : m),
        f.rings[0],
      );
      const [cx, cy] = centroid(big);
      labels.push(
        `<text x="${n1(tx(cx))}" y="${n1(ty(cy))}" text-anchor="middle" font-size="14" font-weight="${hl.has(name) ? 700 : 600}" fill="${V.seqInk(bin(v))}" stroke="${V.seq(bin(v))}" stroke-width="3" paint-order="stroke" pointer-events="none">${esc(formatValue(v, pct))}</text>`,
      );
    }
  }
  out.push(...outlines, ...labels);

  // legend: equal-interval bins, one per row, highest first ("stronger = higher" on top)
  let ly = mapH + 34;
  out.push(
    `<text x="10" y="${ly}" font-size="13" font-weight="700" fill="${V.ink2}">${esc(`${enDash(period)}${spec.yLabel ? `, ${spec.yLabel}` : ''}`)}</text>`,
  );
  ly += 10;
  for (let i = MAP_BINS - 1; i >= 0; i--) {
    const a = lo + ((hi - lo) * i) / MAP_BINS;
    const b = lo + ((hi - lo) * (i + 1)) / MAP_BINS;
    out.push(
      `<rect x="10" y="${ly}" width="22" height="14" rx="2" fill="${V.seq(i)}"/>`,
      `<text x="40" y="${ly + 11.5}" font-size="13" fill="${V.ink2}">${esc(`${formatValue(a, false)} to ${formatValue(b, pct)}`)}</text>`,
    );
    ly += 21;
  }
  const hlNames = [...hl].filter((h) => rows.some((r) => String(r[key]) === h));
  const note = [
    hlNames.length ? `Outlined: ${hlNames.join(', ')}.` : '',
    geo.features.length > byCode.size ? 'Grey: no data.' : '',
  ]
    .filter(Boolean)
    .join(' ');
  ly += 12;
  if (note) out.push(`<text x="10" y="${ly}" font-size="12" fill="${V.muted}">${esc(note)}</text>`);
  out.push(
    `<text x="10" y="${ly + 20}" font-size="11" fill="${V.muted}">${esc('Boundaries: ONS, Open Government Licence v3.0.')}</text>`,
    `<text x="10" y="${ly + 35}" font-size="11" fill="${V.muted}">${esc('Contains OS data © Crown copyright 2024.')}</text>`,
  );
  out.push('</svg>');
  return out.join('');
}
