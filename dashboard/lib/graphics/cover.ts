/**
 * Branded story cover: headline, key number and badge, and a mini line chart (highlighted
 * group in colour, others grey). Pure SVG with all text as outline paths (font.ts), so it
 * renders the same on the build machine (sharp -> PNG) and in the browser (dashboard).
 *
 * Shared file: the dashboard keeps an identical copy (scripts/sync-graphics.mjs).
 */
import {
  enDash,
  formatValue,
  groupsOf,
  highlights,
  isPercent,
  periodsOf,
  valueAt,
  type Cover,
  type Row,
  type Spec,
} from './alt.ts';
import { measure, textPath, wrap, type Font } from './font.ts';

export type CoverFormat = 'landscape' | 'portrait';
export const COVER_SIZE: Record<CoverFormat, { w: number; h: number }> = {
  landscape: { w: 1200, h: 630 },
  portrait: { w: 1080, h: 1350 },
};

export type CoverInput = {
  headline: string;
  cover: Cover;
  spec: Spec;
  data: Row[];
  /** e.g. "Office for National Statistics" */
  source?: string;
  /** e.g. "UK nations", for the legend */
  groupNoun?: string;
};

// Light theme of the site (global.css) and the validated chart palette.
const C = {
  bg: '#fcfcfb',
  ink: '#111110',
  ink2: '#52514e',
  muted: '#6f6e69',
  rule: '#e1e0d9',
  accent: '#5a3fe0',
  accent2: '#c2452f',
  badgeBg: '#ece8fc',
  series: '#2a78d6',
  other: '#b9b8b1',
};

type Fonts = { regular: Font; bold: Font };

const text = (font: Font, s: string, x: number, y: number, size: number, fill: string) =>
  `<path fill="${fill}" d="${textPath(font, s, x, y, size)}"/>`;

const n1 = (v: number) => Math.round(v * 10) / 10;

/** Landscape: the mini chart starts here; the text column ends COLUMN_GAP before it. */
export const CHART_X = 712;
const COLUMN_GAP = 48;

/**
 * The largest size (from `max` down to `min`, in steps of 2) at which `text` fits `width` in at
 * most `maxLines` lines without cutting. At `min`, lines are cut with "…" (and a single word
 * that is still too wide is shortened), so the result always fits.
 */
export function fitText(
  font: Font,
  s: string,
  max: number,
  min: number,
  width: number,
  maxLines: number,
): { size: number; lines: string[] } {
  const fits = (lines: string[], size: number) =>
    lines.every((l) => measure(font, l, size) <= width) && !lines.at(-1)?.endsWith('…');
  for (let size = max; size >= min; size -= 2) {
    const lines = wrap(font, s, size, width, maxLines);
    if (fits(lines, size)) return { size, lines };
  }
  const lines = wrap(font, s, min, width, maxLines).map((line) => {
    let l = line;
    while (l.length > 1 && measure(font, l, min) > width) l = `${l.slice(0, -2)}…`;
    return l;
  });
  return { size: min, lines };
}

/** Layout sizes per format. Headline shrinks until the text block fits above the chart. */
const LAYOUT = {
  landscape: {
    pad: 64,
    word: 30,
    head: [52, 46, 40, 36],
    headLines: 4,
    textW: 600,
    value: 76,
    label: 24,
    change: 22,
    badge: 22,
    footer: 20,
  },
  portrait: {
    pad: 72,
    word: 40,
    head: [68, 60, 54, 48],
    headLines: 5,
    textW: 936,
    value: 112,
    label: 32,
    change: 28,
    badge: 30,
    footer: 28,
  },
};

export function coverSvg(input: CoverInput, fonts: Fonts, format: CoverFormat): string {
  const { w, h } = COVER_SIZE[format];
  const L = LAYOUT[format];
  const { regular, bold } = fonts;
  const out: string[] = [];

  // frame
  out.push(`<rect width="${w}" height="${h}" fill="${C.bg}"/>`);
  out.push(`<rect width="${w}" height="12" fill="${C.accent}"/>`);

  // wordmark
  const wordY = L.pad + L.word;
  out.push(text(bold, 'Data', L.pad, wordY, L.word, C.accent));
  out.push(text(bold, 'Tales', L.pad + measure(bold, 'Data', L.word), wordY, L.word, C.accent2));

  // Text column: a fixed width left of (landscape) or above (portrait) the chart. Every line
  // is fitted to it, so text can never run into the chart.
  const col = format === 'landscape' ? CHART_X - COLUMN_GAP - L.pad : w - 2 * L.pad;
  const footerY = h - L.pad + L.footer * 0.4;
  const limit = format === 'landscape' ? footerY - L.footer * 2.5 : h * 0.55;
  const c = input.cover;
  const block = (headSize: number) => {
    const head = fitText(bold, enDash(input.headline), headSize, L.head.at(-1)!, col, L.headLines);
    const lh = Math.round(head.size * 1.14);
    let y = wordY + Math.round(L.word * 1.6) + head.size;
    const parts: string[] = head.lines.map((line, i) =>
      text(bold, line, L.pad, y + i * lh, head.size, C.ink),
    );
    y += (head.lines.length - 1) * lh;
    if (c.value) {
      const v = fitText(bold, c.value, L.value, L.value * 0.5, col, 1);
      y += Math.round(v.size * 1.25);
      parts.push(text(bold, v.lines[0], L.pad, y, v.size, C.ink));
      y += Math.round(L.label * 0.45);
    }
    for (const [s, size2, font, fill] of [
      [c.label, L.label, regular, C.ink2],
      [c.change, L.change, regular, C.muted],
    ] as const) {
      if (!s) continue;
      const f = fitText(font, enDash(s), size2, size2 * 0.75, col, 2);
      for (const line of f.lines) {
        y += Math.round(f.size * 1.4);
        parts.push(text(font, line, L.pad, y, f.size, fill));
      }
    }
    if (c.badge) {
      const inner = col - L.badge * 1.4;
      const f = fitText(bold, enDash(c.badge), L.badge, L.badge * 0.6, inner, 1);
      const bw = measure(bold, f.lines[0], f.size) + L.badge * 1.4;
      const bh = Math.round(L.badge * 1.9);
      const top = y + Math.round(L.badge * 0.9);
      parts.push(
        `<rect x="${L.pad}" y="${top}" width="${n1(bw)}" height="${bh}" rx="${bh / 2}" fill="${C.badgeBg}"/>`,
        text(
          bold,
          f.lines[0],
          L.pad + L.badge * 0.7,
          top + bh / 2 + f.size * 0.36,
          f.size,
          C.accent,
        ),
      );
      y = top + bh;
    }
    return { parts, bottom: y };
  };

  // Largest headline size whose whole block still fits above the footer / chart.
  let chosen = block(L.head[0]);
  for (let size = L.head[0] - 2; size >= L.head.at(-1)! && chosen.bottom > limit; size -= 2) {
    chosen = block(size);
  }
  let box: { x: number; y: number; w: number; h: number };
  if (format === 'landscape') {
    box = { x: CHART_X, y: 150, w: w - CHART_X - L.pad, h: footerY - 150 - L.footer * 3 };
  } else {
    const top = chosen.bottom + 64;
    box = { x: L.pad, y: top, w: w - 2 * L.pad, h: footerY - top - L.footer * 3 };
  }
  // Hard guarantee on top of the fitting: nothing in the column can paint outside it.
  out.push(
    `<clipPath id="col"><rect x="${L.pad - 4}" y="0" width="${col + 8}" height="${h}"/></clipPath>`,
  );
  out.push(`<g clip-path="url(#col)">`, ...chosen.parts, '</g>');

  out.push(miniChart(input, fonts, box, format === 'portrait' ? 26 : 20));

  // footer
  out.push(
    `<rect x="${L.pad}" y="${footerY - L.footer * 1.8}" width="${w - 2 * L.pad}" height="2" fill="${C.rule}"/>`,
  );
  out.push(text(bold, 'datatales.co.uk', L.pad, footerY, L.footer, C.accent));
  if (input.source) {
    const room = w - 2 * L.pad - measure(bold, 'datatales.co.uk', L.footer) - L.footer * 2;
    const f = fitText(regular, `Source: ${input.source}`, L.footer, L.footer * 0.7, room, 1);
    const sw = measure(regular, f.lines[0], f.size);
    out.push(text(regular, f.lines[0], w - L.pad - sw, footerY, f.size, C.muted));
  }

  return (
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">` +
    out.join('') +
    '</svg>'
  );
}

function miniChart(
  input: CoverInput,
  fonts: Fonts,
  box: { x: number; y: number; w: number; h: number },
  size: number,
): string {
  const { spec, data } = input;
  const line = { ...spec, type: 'line' as const };
  const periods = periodsOf(line, data);
  const groups = groupsOf(line, data);
  const hl = highlights(spec)
    .filter((g) => groups.includes(g))
    .slice(0, 1);
  if (periods.length < 2 || !groups.length) return '';
  const pct = isPercent(spec);
  const out: string[] = [];

  // legend row
  let lx = box.x;
  const ly = box.y + size;
  const swatch = (x: number, colour: string) =>
    `<rect x="${n1(x)}" y="${n1(ly - size * 0.42)}" width="${size * 1.2}" height="${Math.max(3, size * 0.2)}" rx="2" fill="${colour}"/>`;
  for (const [label, colour, font] of [
    [hl[0], C.series, fonts.bold],
    [
      groups.length > hl.length ? `Other ${input.groupNoun ?? 'areas'}` : '',
      C.other,
      fonts.regular,
    ],
  ] as const) {
    if (!label) continue;
    out.push(swatch(lx, colour), text(font, label, lx + size * 1.6, ly, size, C.ink2));
    lx += size * 1.6 + measure(font, label, size) + size * 1.4;
  }

  // plot area
  const values = data.map((r) => r[spec.y]).filter((v): v is number => typeof v === 'number');
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = (hi - lo || 1) * 0.08;
  const endLabel = hl[0] ? formatValue(valueAt(line, data, hl[0], periods.at(-1)!) ?? 0, pct) : '';
  const right = endLabel ? measure(fonts.bold, endLabel, size) + size * 0.9 : 0;
  const top = ly + size * 1.4;
  const bottom = box.y + box.h - size * 1.8;
  const x0 = box.x + 6;
  const x1 = box.x + box.w - right;
  const px = (p: string) => x0 + (periods.indexOf(p) / (periods.length - 1)) * (x1 - x0);
  const py = (v: number) => top + (1 - (v - (lo - pad)) / (hi - lo + 2 * pad)) * (bottom - top);

  for (const f of [0, 0.5, 1]) {
    const y = n1(top + f * (bottom - top));
    out.push(`<rect x="${n1(x0)}" y="${y}" width="${n1(x1 - x0)}" height="1.5" fill="${C.rule}"/>`);
  }
  const path = (g: string) => {
    const pts = periods
      .map((p) => [p, valueAt(line, data, g, p)] as const)
      .filter((x): x is readonly [string, number] => x[1] !== null);
    return pts.map(([p, v], i) => `${i ? 'L' : 'M'}${n1(px(p))} ${n1(py(v))}`).join('');
  };
  const stroke = Math.max(3, size * 0.16);
  for (const g of groups.filter((x) => !hl.includes(x))) {
    out.push(
      `<path d="${path(g)}" fill="none" stroke="${C.other}" stroke-width="${n1(stroke * 0.7)}" stroke-linejoin="round" stroke-linecap="round"/>`,
    );
  }
  for (const g of hl) {
    out.push(
      `<path d="${path(g)}" fill="none" stroke="${C.series}" stroke-width="${n1(stroke * 1.6)}" stroke-linejoin="round" stroke-linecap="round"/>`,
    );
    const v = valueAt(line, data, g, periods.at(-1)!);
    if (v !== null) {
      const cx = px(periods.at(-1)!);
      const cy = py(v);
      out.push(
        `<circle cx="${n1(cx)}" cy="${n1(cy)}" r="${n1(stroke * 2.4)}" fill="${C.series}" stroke="${C.bg}" stroke-width="${n1(stroke)}"/>`,
      );
      out.push(text(fonts.bold, endLabel, cx + size * 0.8, cy + size * 0.36, size, C.ink));
    }
  }

  // first and last period under the axis
  const first = enDash(periods[0]);
  const last = enDash(periods.at(-1)!);
  const by = box.y + box.h;
  out.push(text(fonts.regular, first, x0, by, size * 0.9, C.muted));
  out.push(
    text(
      fonts.regular,
      last,
      x1 - measure(fonts.regular, last, size * 0.9),
      by,
      size * 0.9,
      C.muted,
    ),
  );
  return out.join('');
}
