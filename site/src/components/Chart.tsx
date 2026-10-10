import * as Plot from '@observablehq/plot';
import { useEffect, useRef, useState } from 'react';

import {
  colouredSeries,
  dodge,
  enDash,
  highlightList,
  seriesOrder,
  type ChartSpec,
  type Row,
} from '../lib/chart';

type Props = { spec: ChartSpec; data: Row[]; label: string; describedBy?: string };

const SERIES_VARS = Array.from({ length: 8 }, (_, i) => `--series-${i + 1}`);
/** Up to this many series, every line gets an end label (others only the coloured ones). */
const MAX_LABELLED = 8;
const LABEL_GAP = 15;

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function theme() {
  return {
    surface: cssVar('--chart-surface'),
    ink: cssVar('--ink'),
    ink2: cssVar('--ink-2'),
    muted: cssVar('--muted'),
    grid: cssVar('--chart-grid'),
    other: cssVar('--chart-muted'),
    series: SERIES_VARS.map(cssVar),
  };
}

const isYearLike = (values: unknown[]) =>
  values.every((v) => typeof v === 'number' && Number.isInteger(v) && v >= 1800 && v <= 2200);

const numFmt = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 2 });

function build(spec: ChartSpec, data: Row[], width: number): SVGSVGElement | HTMLElement {
  const t = theme();
  const highlight = highlightList(spec);
  const sKey = spec.series;
  const coloured = colouredSeries(spec, data);
  const colourOf = new Map(coloured.map((s, i) => [s, t.series[i]]));
  const strokeFor = (s: string) => colourOf.get(s) ?? t.other;
  const isColoured = (r: Row) => !sKey || colourOf.has(String(r[sKey]));

  const common = {
    width,
    marginLeft: 48,
    marginRight: 16,
    style: {
      background: 'transparent',
      color: t.muted,
      fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
      fontSize: '12px',
      overflow: 'visible',
    },
  } satisfies Partial<Plot.PlotOptions>;

  const tipStyle = { fill: t.surface, stroke: t.grid, textPadding: 8 } as const;

  if (spec.type === 'line') {
    const xValues = data.map((r) => r[spec.x]);
    const years = isYearLike(xValues);
    const allSeries = sKey ? seriesOrder(data, sKey) : [];
    const labelSeries = sKey ? (allSeries.length <= MAX_LABELLED ? allSeries : coloured) : [];
    const lastRow = (s: string) =>
      data.filter((r) => String(r[sKey!]) === s && r[spec.y] != null).at(-1);
    const ends = labelSeries.map(lastRow).filter(Boolean) as Row[];
    const labelText = (r: Row) => `${r[sKey!]} ${numFmt.format(Number(r[spec.y]))}`;
    const longest = Math.max(0, ...ends.map((r) => labelText(r).length));
    const rightRoom = ends.length ? Math.min(190, longest * 7 + 16) : 16;
    const height = Math.max(260, Math.min(420, width * 0.6));
    const xOpt = years
      ? { tickFormat: 'd', label: null, ticks: Math.min(8, Math.floor(width / 70)) }
      : { type: 'point' as const, label: null, tickFormat: (v: unknown) => enDash(String(v)) };
    const yOpt = { grid: true, label: null, nice: true, zero: false };

    // Pass 1 finds the y scale; labels are then spread so they never overlap.
    const probe = Plot.plot({
      ...common,
      height,
      marginRight: rightRoom,
      x: xOpt,
      y: yOpt,
      marks: [Plot.lineY(data, { x: spec.x, y: spec.y, z: sKey })],
    });
    const yScale = probe.scale('y')!;
    const [r0, r1] = (yScale.range as number[]).slice().sort((a, b) => a - b);
    const placed = dodge(
      ends.map((r) => yScale.apply(r[spec.y]) as number),
      LABEL_GAP,
      r0,
      r1,
    );
    const labels = ends.map((r, i) => ({
      ...r,
      __y: yScale.invert!(placed[i]) as number,
      __strong: colourOf.has(String(r[sKey!])),
    }));
    const dotted = ends.filter((r) => colourOf.has(String(r[sKey!])));

    return Plot.plot({
      ...common,
      height,
      marginRight: rightRoom,
      x: xOpt,
      // Lines need no zero baseline: fit the axis to the data. The unit is in the caption.
      y: { ...yOpt, domain: yScale.domain },
      color: { type: 'identity' },
      marks: [
        // muted context lines first, coloured lines on top
        ...(sKey
          ? [
              Plot.lineY(
                data.filter((r) => !isColoured(r)),
                {
                  x: spec.x,
                  y: spec.y,
                  z: sKey,
                  stroke: t.other,
                  strokeWidth: 1.25,
                },
              ),
            ]
          : []),
        Plot.lineY(data.filter(isColoured), {
          x: spec.x,
          y: spec.y,
          z: sKey,
          stroke: sKey ? (r: Row) => strokeFor(String(r[sKey])) : t.series[0],
          strokeWidth: 2,
          strokeLinejoin: 'round',
          strokeLinecap: 'round',
        }),
        Plot.dot(sKey ? dotted : (data.filter((r) => r[spec.y] != null).slice(-1) as Row[]), {
          x: spec.x,
          y: spec.y,
          r: 4,
          fill: sKey ? (r: Row) => strokeFor(String(r[sKey])) : t.series[0],
          stroke: t.surface,
          strokeWidth: 2,
        }),
        ...[true, false].map((strong) =>
          Plot.text(
            labels.filter((r) => r.__strong === strong),
            {
              x: spec.x,
              y: '__y',
              text: labelText,
              dx: 8,
              textAnchor: 'start',
              fill: strong ? t.ink : t.ink2,
              fontWeight: strong ? 700 : 400,
            },
          ),
        ),
        Plot.ruleX(data, Plot.pointerX({ x: spec.x, stroke: t.muted, strokeOpacity: 0.6 })),
        Plot.tip(
          data,
          Plot.pointer({
            x: spec.x,
            y: spec.y,
            ...tipStyle,
            channels: sKey ? { [sKey]: sKey } : {},
            format: {
              x: (v: unknown) => enDash(String(v)),
              y: (v: number) => numFmt.format(v),
            },
          }),
        ),
      ],
    });
  }

  // bar and dot: categories down the side, values along the bottom
  const rows = [...data].filter((r) => r[spec.y] != null);
  rows.sort((a, b) => Number(b[spec.y]) - Number(a[spec.y]));
  const catKey = spec.x;
  const highlighted = new Set(highlight);
  const fillFor = (r: Row) =>
    highlighted.size === 0 || highlighted.has(String(r[catKey])) ? t.series[0] : t.other;
  const height = Math.max(160, rows.length * 32 + 48);
  const longest = Math.max(...rows.map((r) => String(r[catKey]).length));
  const marginLeft = Math.min(220, Math.max(60, longest * 7 + 12));

  const valueMarks =
    spec.type === 'bar'
      ? [
          Plot.barX(rows, {
            y: catKey,
            x: spec.y,
            fill: fillFor,
            rx: 4,
            insetTop: 6,
            insetBottom: 6,
          }),
          Plot.text(rows, {
            y: catKey,
            x: spec.y,
            text: (r: Row) => numFmt.format(Number(r[spec.y])),
            dx: 6,
            textAnchor: 'start',
            fill: t.ink2,
          }),
          Plot.ruleX([0], { stroke: t.muted }),
        ]
      : [
          Plot.ruleY(rows, { y: catKey, stroke: t.grid }),
          Plot.dot(rows, {
            y: catKey,
            x: spec.y,
            r: 5,
            fill: fillFor,
            stroke: t.surface,
            strokeWidth: 2,
          }),
        ];

  return Plot.plot({
    ...common,
    height,
    marginLeft,
    marginRight: spec.type === 'bar' ? 56 : 24,
    y: { domain: rows.map((r) => String(r[catKey])), label: null, tickSize: 0 },
    x: {
      grid: true,
      label: null,
      nice: true,
      zero: spec.type === 'bar',
    },
    marks: [
      ...valueMarks,
      Plot.tip(
        rows,
        Plot.pointerY({
          y: catKey,
          x: spec.y,
          ...tipStyle,
          format: { x: (v: number) => numFmt.format(v) },
        }),
      ),
    ],
  });
}

export default function Chart({ spec, data, label, describedBy }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [tick, setTick] = useState(0);
  const [width, setWidth] = useState(0);

  // Redraw on theme change (toggle or OS) and when the available width changes.
  useEffect(() => {
    const bump = () => setTick((n) => n + 1);
    const mq = matchMedia('(prefers-color-scheme: dark)');
    window.addEventListener('themechange', bump);
    mq.addEventListener('change', bump);
    const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    if (ref.current) ro.observe(ref.current);
    return () => {
      window.removeEventListener('themechange', bump);
      mq.removeEventListener('change', bump);
      ro.disconnect();
    };
  }, []);

  useEffect(() => {
    const el = ref.current;
    if (!el || width === 0) return;
    const svg = build(spec, data, Math.max(280, width));
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', label);
    if (describedBy) svg.setAttribute('aria-describedby', describedBy);
    el.replaceChildren(svg);
  }, [spec, data, label, describedBy, tick, width]);

  return <div ref={ref} className="chart-canvas" />;
}
