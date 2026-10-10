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

  // text block: headline, key number, label, change, badge
  const c = input.cover;
  const block = (size: number) => {
    const lines = wrap(bold, enDash(input.headline), size, L.textW, L.headLines);
    const lh = Math.round(size * 1.14);
    let y = wordY + Math.round(L.word * 1.6) + size;
    const parts: string[] = lines.map((line, i) =>
      text(bold, line, L.pad, y + i * lh, size, C.ink),
    );
    y += (lines.length - 1) * lh;
    if (c.value) {
      y += Math.round(L.value * 1.25);
      parts.push(text(bold, c.value, L.pad, y, L.value, C.ink));
      y += Math.round(L.label * 0.45);
    }
    for (const [s, size2, font, fill] of [
      [c.label, L.label, regular, C.ink2],
      [c.change, L.change, regular, C.muted],
    ] as const) {
      if (!s) continue;
      for (const line of wrap(font, enDash(s), size2, L.textW, 2)) {
        y += Math.round(size2 * 1.4);
        parts.push(text(font, line, L.pad, y, size2, fill));
      }
    }
    if (c.badge) {
      const label = enDash(c.badge);
      const bw = measure(bold, label, L.badge) + L.badge * 1.4;
      const bh = Math.round(L.badge * 1.9);
      const top = y + Math.round(L.badge * 0.9);
      parts.push(
        `<rect x="${L.pad}" y="${top}" width="${n1(bw)}" height="${bh}" rx="${bh / 2}" fill="${C.badgeBg}"/>`,
        text(bold, label, L.pad + L.badge * 0.7, top + bh / 2 + L.badge * 0.36, L.badge, C.accent),
      );
      y = top + bh;
    }
    return { parts, bottom: y };
  };

  // chart box
  const footerY = h - L.pad + L.footer * 0.4;
  let chosen = block(L.head[0]);
  let box: { x: number; y: number; w: number; h: number };
  if (format === 'landscape') {
    for (const size of L.head.slice(1)) {
      if (chosen.bottom <= footerY - L.footer * 2.5) break;
      chosen = block(size);
    }
    box = { x: 712, y: 150, w: w - 712 - L.pad, h: footerY - 150 - L.footer * 3 };
  } else {
    for (const size of L.head.slice(1)) {
      if (chosen.bottom <= h * 0.55) break;
      chosen = block(size);
    }
    const top = chosen.bottom + 64;
    box = { x: L.pad, y: top, w: w - 2 * L.pad, h: footerY - top - L.footer * 3 };
  }
  out.push(...chosen.parts);
  out.push(miniChart(input, fonts, box, format === 'portrait' ? 26 : 20));

  // footer
  out.push(
    `<rect x="${L.pad}" y="${footerY - L.footer * 1.8}" width="${w - 2 * L.pad}" height="2" fill="${C.rule}"/>`,
  );
  out.push(text(bold, 'datatales.co.uk', L.pad, footerY, L.footer, C.accent));
  if (input.source) {
    const s = `Source: ${input.source}`;
    out.push(
      text(regular, s, w - L.pad - measure(regular, s, L.footer), footerY, L.footer, C.muted),
    );
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
