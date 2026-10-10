/**
 * Minimal TrueType reader: text -> SVG outline paths, so story graphics render identically on
 * any machine (build server, browser) without installed fonts. Reads cmap (formats 4 and 12),
 * hmtx, glyf (simple and composite glyphs) and GPOS pair kerning (formats 1 and 2).
 * No shaping or ligatures: fine for Latin headlines.
 *
 * Shared file: the dashboard keeps an identical copy (scripts/sync-graphics.mjs).
 */

type Point = { x: number; y: number; on: boolean };
type Contour = Point[];

export type Font = {
  unitsPerEm: number;
  ascender: number;
  descender: number;
  glyphId(codePoint: number): number;
  advance(glyph: number): number;
  kern(left: number, right: number): number;
  contours(glyph: number): Contour[];
};

class Reader {
  readonly view: DataView;
  readonly base: number;
  constructor(view: DataView, base = 0) {
    this.view = view;
    this.base = base;
  }
  u8 = (o: number) => this.view.getUint8(this.base + o);
  i8 = (o: number) => this.view.getInt8(this.base + o);
  u16 = (o: number) => this.view.getUint16(this.base + o);
  i16 = (o: number) => this.view.getInt16(this.base + o);
  u32 = (o: number) => this.view.getUint32(this.base + o);
  at = (offset: number) => new Reader(this.view, this.base + offset);
  tag = (o: number) =>
    String.fromCharCode(this.u8(o), this.u8(o + 1), this.u8(o + 2), this.u8(o + 3));
}

export function parseFont(data: ArrayBuffer | Uint8Array): Font {
  const bytes = data instanceof Uint8Array ? data : new Uint8Array(data);
  const file = new Reader(new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength));
  const tables = new Map<string, Reader>();
  for (let i = 0; i < file.u16(4); i++) {
    const rec = 12 + i * 16;
    tables.set(file.tag(rec), file.at(file.u32(rec + 8)));
  }
  const table = (tag: string) => {
    const t = tables.get(tag);
    if (!t) throw new Error(`font has no ${tag} table`);
    return t;
  };

  const head = table('head');
  const hhea = table('hhea');
  const unitsPerEm = head.u16(18);
  const longLoca = head.i16(50) === 1;
  const numGlyphs = table('maxp').u16(4);
  const numHMetrics = hhea.u16(34);
  const hmtx = table('hmtx');
  const loca = table('loca');
  const glyf = table('glyf');

  const glyphId = cmapLookup(table('cmap'));
  const advance = (g: number) => hmtx.u16(4 * Math.min(g, numHMetrics - 1));
  const glyphOffset = (g: number) => (longLoca ? loca.u32(g * 4) : loca.u16(g * 2) * 2);

  const cache = new Map<number, Contour[]>();
  const contours = (g: number): Contour[] => {
    if (g < 0 || g >= numGlyphs) return [];
    const hit = cache.get(g);
    if (hit) return hit;
    const start = glyphOffset(g);
    const out = start === glyphOffset(g + 1) ? [] : readGlyph(glyf.at(start), contours);
    cache.set(g, out);
    return out;
  };

  const kerning = tables.has('GPOS') ? gposKerning(table('GPOS')) : () => 0;
  return {
    unitsPerEm,
    ascender: hhea.i16(4),
    descender: hhea.i16(6),
    glyphId,
    advance,
    kern: kerning,
    contours,
  };
}

function cmapLookup(cmap: Reader): (cp: number) => number {
  let best: Reader | null = null;
  let bestScore = -1;
  for (let i = 0; i < cmap.u16(2); i++) {
    const rec = 4 + i * 8;
    const platform = cmap.u16(rec);
    const encoding = cmap.u16(rec + 2);
    const sub = cmap.at(cmap.u32(rec + 4));
    const format = sub.u16(0);
    const score =
      format === 12 && (platform === 3 || platform === 0)
        ? 3
        : format === 4 && platform === 3 && encoding === 1
          ? 2
          : format === 4 && platform === 0
            ? 1
            : -1;
    if (score > bestScore) [best, bestScore] = [sub, score];
  }
  if (!best) throw new Error('font has no usable cmap');
  const sub = best;
  if (sub.u16(0) === 12) {
    const groups = sub.u32(12);
    return (cp) => {
      let lo = 0;
      let hi = groups - 1;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        const g = 16 + mid * 12;
        if (cp < sub.u32(g)) hi = mid - 1;
        else if (cp > sub.u32(g + 4)) lo = mid + 1;
        else return sub.u32(g + 8) + cp - sub.u32(g);
      }
      return 0;
    };
  }
  const segX2 = sub.u16(6);
  const ends = 14;
  const starts = ends + segX2 + 2;
  const deltas = starts + segX2;
  const ranges = deltas + segX2;
  return (cp) => {
    if (cp > 0xffff) return 0;
    for (let s = 0; s < segX2; s += 2) {
      if (cp > sub.u16(ends + s)) continue;
      const first = sub.u16(starts + s);
      if (cp < first) return 0;
      const rangeOffset = sub.u16(ranges + s);
      if (rangeOffset === 0) return (cp + sub.i16(deltas + s)) & 0xffff;
      const g = sub.u16(ranges + s + rangeOffset + 2 * (cp - first));
      return g === 0 ? 0 : (g + sub.i16(deltas + s)) & 0xffff;
    }
    return 0;
  };
}

function readGlyph(g: Reader, contoursOf: (glyph: number) => Contour[]): Contour[] {
  const n = g.i16(0);
  if (n >= 0) return readSimple(g, n);
  const out: Contour[] = [];
  let o = 10;
  for (;;) {
    const flags = g.u16(o);
    const child = g.u16(o + 2);
    o += 4;
    let dx = 0;
    let dy = 0;
    if (flags & 1) {
      dx = g.i16(o);
      dy = g.i16(o + 2);
      o += 4;
    } else {
      dx = g.i8(o);
      dy = g.i8(o + 1);
      o += 2;
    }
    if (!(flags & 2)) [dx, dy] = [0, 0]; // point-matched offsets: not used by Latin fonts
    let [a, b, c, d] = [1, 0, 0, 1];
    const f2 = (off: number) => g.i16(off) / 16384;
    if (flags & 8) {
      a = d = f2(o);
      o += 2;
    } else if (flags & 0x40) {
      a = f2(o);
      d = f2(o + 2);
      o += 4;
    } else if (flags & 0x80) {
      [a, b, c, d] = [f2(o), f2(o + 2), f2(o + 4), f2(o + 6)];
      o += 8;
    }
    for (const contour of contoursOf(child)) {
      out.push(
        contour.map((p) => ({ x: a * p.x + c * p.y + dx, y: b * p.x + d * p.y + dy, on: p.on })),
      );
    }
    if (!(flags & 0x20)) return out;
  }
}

function readSimple(g: Reader, n: number): Contour[] {
  const endPts: number[] = [];
  for (let i = 0; i < n; i++) endPts.push(g.u16(10 + i * 2));
  const count = n ? endPts[n - 1] + 1 : 0;
  let o = 10 + n * 2;
  o += 2 + g.u16(o); // skip instructions
  const flags: number[] = [];
  while (flags.length < count) {
    const f = g.u8(o++);
    flags.push(f);
    if (f & 8) for (let r = g.u8(o++); r > 0; r--) flags.push(f);
  }
  const coords = (short: number, same: number) => {
    const out: number[] = [];
    let v = 0;
    for (const f of flags) {
      if (f & short) {
        const d = g.u8(o++);
        v += f & same ? d : -d;
      } else if (!(f & same)) {
        v += g.i16(o);
        o += 2;
      }
      out.push(v);
    }
    return out;
  };
  const xs = coords(2, 16);
  const ys = coords(4, 32);
  const out: Contour[] = [];
  let start = 0;
  for (const end of endPts) {
    const contour: Contour = [];
    for (let i = start; i <= end; i++)
      contour.push({ x: xs[i], y: ys[i], on: (flags[i] & 1) === 1 });
    out.push(contour);
    start = end + 1;
  }
  return out;
}

// ---- GPOS pair kerning ----

function coverageIndex(cov: Reader, glyph: number): number {
  if (cov.u16(0) === 1) {
    let lo = 0;
    let hi = cov.u16(2) - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const g = cov.u16(4 + mid * 2);
      if (glyph < g) hi = mid - 1;
      else if (glyph > g) lo = mid + 1;
      else return mid;
    }
    return -1;
  }
  for (let i = 0; i < cov.u16(2); i++) {
    const r = 4 + i * 6;
    if (glyph >= cov.u16(r) && glyph <= cov.u16(r + 2)) return cov.u16(r + 4) + glyph - cov.u16(r);
  }
  return -1;
}

function classOf(cd: Reader, glyph: number): number {
  if (cd.u16(0) === 1) {
    const first = cd.u16(2);
    return glyph >= first && glyph < first + cd.u16(4) ? cd.u16(6 + (glyph - first) * 2) : 0;
  }
  let lo = 0;
  let hi = cd.u16(2) - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const r = 4 + mid * 6;
    if (glyph < cd.u16(r)) hi = mid - 1;
    else if (glyph > cd.u16(r + 2)) lo = mid + 1;
    else return cd.u16(r + 4);
  }
  return 0;
}

const bits = (v: number) => {
  let n = 0;
  for (; v; v &= v - 1) n++;
  return n;
};

function pairAdjust(sub: Reader, left: number, right: number): number | null {
  const ci = coverageIndex(sub.at(sub.u16(2)), left);
  if (ci < 0) return null;
  const vf1 = sub.u16(4);
  const vf2 = sub.u16(6);
  const size1 = bits(vf1) * 2;
  const size2 = bits(vf2) * 2;
  // XAdvance sits after XPlacement and YPlacement, if those are present.
  const xAdv = (rec: Reader, off: number) => (vf1 & 4 ? rec.i16(off + bits(vf1 & 3) * 2) : 0);
  if (sub.u16(0) === 1) {
    const set = sub.at(sub.u16(10 + ci * 2));
    const recSize = 2 + size1 + size2;
    let lo = 0;
    let hi = set.u16(0) - 1;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      const r = 2 + mid * recSize;
      const g = set.u16(r);
      if (right < g) hi = mid - 1;
      else if (right > g) lo = mid + 1;
      else return xAdv(set, r + 2);
    }
    return null;
  }
  const c1 = classOf(sub.at(sub.u16(8)), left);
  const c2 = classOf(sub.at(sub.u16(10)), right);
  const class2Count = sub.u16(14);
  const r = 16 + (c1 * class2Count + c2) * (size1 + size2);
  return xAdv(sub, r);
}

function gposKerning(gpos: Reader): (left: number, right: number) => number {
  const features = gpos.at(gpos.u16(6));
  const lookups = gpos.at(gpos.u16(8));
  const indices = new Set<number>();
  for (let i = 0; i < features.u16(0); i++) {
    const rec = 2 + i * 6;
    if (features.tag(rec) !== 'kern') continue;
    const feature = features.at(features.u16(rec + 4));
    for (let j = 0; j < feature.u16(2); j++) indices.add(feature.u16(4 + j * 2));
  }
  const subtables: Reader[][] = [];
  for (const li of [...indices].sort((a, b) => a - b)) {
    const lookup = lookups.at(lookups.u16(2 + li * 2));
    const type = lookup.u16(0);
    const subs: Reader[] = [];
    for (let s = 0; s < lookup.u16(4); s++) {
      let sub = lookup.at(lookup.u16(6 + s * 2));
      let subType = type;
      if (type === 9) {
        subType = sub.u16(2);
        sub = sub.at(sub.u32(4));
      }
      if (subType === 2) subs.push(sub);
    }
    if (subs.length) subtables.push(subs);
  }
  const cache = new Map<number, number>();
  return (left, right) => {
    const key = left * 65536 + right;
    const hit = cache.get(key);
    if (hit !== undefined) return hit;
    let total = 0;
    for (const subs of subtables) {
      for (const sub of subs) {
        const v = pairAdjust(sub, left, right);
        if (v !== null) {
          total += v;
          break;
        }
      }
    }
    cache.set(key, total);
    return total;
  };
}

// ---- layout ----

const FALLBACK: Record<string, string> = { ' ': ' ', ' ': ' ', ' ': ' ' };

function glyphs(font: Font, text: string): number[] {
  const out: number[] = [];
  for (const ch of text) {
    let g = font.glyphId((FALLBACK[ch] ?? ch).codePointAt(0)!);
    if (g === 0) g = font.glyphId(0x3f); // "?" rather than an empty box
    out.push(g);
  }
  return out;
}

/** Width of `text` at `size` px. */
export function measure(font: Font, text: string, size: number): number {
  const gs = glyphs(font, text);
  let w = 0;
  gs.forEach((g, i) => {
    w += font.advance(g) + (i + 1 < gs.length ? font.kern(g, gs[i + 1]) : 0);
  });
  return (w * size) / font.unitsPerEm;
}

const fmt = (v: number) => {
  const r = Math.round(v * 10) / 10;
  return Object.is(r, -0) ? '0' : String(r);
};

function contourPath(c: Contour, tx: (p: Point) => [number, number]): string {
  if (!c.length) return '';
  const pts = c.map((p) => ({ p, xy: tx(p) }));
  const mid = (a: [number, number], b: [number, number]): [number, number] => [
    (a[0] + b[0]) / 2,
    (a[1] + b[1]) / 2,
  ];
  // Start on an on-curve point (or the midpoint of two off-curve points).
  let startIdx = pts.findIndex((q) => q.p.on);
  let start: [number, number];
  if (startIdx < 0) {
    start = mid(pts[0].xy, pts[1 % pts.length].xy);
    startIdx = 0;
  } else start = pts[startIdx].xy;
  let d = `M${fmt(start[0])} ${fmt(start[1])}`;
  let ctrl: [number, number] | null = null;
  for (let k = 1; k <= pts.length; k++) {
    const q = pts[(startIdx + k) % pts.length];
    const isStartAgain = k === pts.length;
    const target = isStartAgain ? start : q.xy;
    if (!isStartAgain && !q.p.on) {
      if (ctrl) {
        const m = mid(ctrl, q.xy);
        d += `Q${fmt(ctrl[0])} ${fmt(ctrl[1])} ${fmt(m[0])} ${fmt(m[1])}`;
      }
      ctrl = q.xy;
      continue;
    }
    if (ctrl) d += `Q${fmt(ctrl[0])} ${fmt(ctrl[1])} ${fmt(target[0])} ${fmt(target[1])}`;
    else if (!isStartAgain) d += `L${fmt(target[0])} ${fmt(target[1])}`;
    ctrl = null;
  }
  return d + 'Z';
}

/** SVG path data for `text` with its baseline starting at (x, y). */
export function textPath(font: Font, text: string, x: number, y: number, size: number): string {
  const scale = size / font.unitsPerEm;
  const gs = glyphs(font, text);
  let pen = 0;
  let d = '';
  gs.forEach((g, i) => {
    const ox = x + pen * scale;
    for (const c of font.contours(g)) {
      d += contourPath(c, (p) => [ox + p.x * scale, y - p.y * scale]);
    }
    pen += font.advance(g) + (i + 1 < gs.length ? font.kern(g, gs[i + 1]) : 0);
  });
  return d;
}

/** Greedy word wrap to `maxWidth`; the last allowed line ends with "…" if text was cut. */
export function wrap(
  font: Font,
  text: string,
  size: number,
  maxWidth: number,
  maxLines = 99,
): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = '';
  for (let i = 0; i < words.length; i++) {
    const next = line ? `${line} ${words[i]}` : words[i];
    if (!line || measure(font, next, size) <= maxWidth) {
      line = next;
      continue;
    }
    lines.push(line);
    line = words[i];
    if (lines.length === maxLines) {
      let last = lines[maxLines - 1];
      while (last.includes(' ') && measure(font, `${last}…`, size) > maxWidth) {
        last = last.slice(0, last.lastIndexOf(' '));
      }
      lines[maxLines - 1] = `${last}…`;
      return lines;
    }
  }
  if (line) lines.push(line);
  return lines;
}
