import * as Plot from '@observablehq/plot';
import { useEffect, useRef, useState } from 'react';

import { colouredSeries, highlightList, type ChartSpec, type Row } from '../lib/chart';

type Props = { spec: ChartSpec; data: Row[]; label: string };

const SERIES_VARS = Array.from({ length: 8 }, (_, i) => `--series-${i + 1}`);
const MAX_LABELLED = 4;

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
    const lastByS = sKey
      ? coloured.slice(0, MAX_LABELLED).map((s) => {
          const rows = data.filter((r) => String(r[sKey]) === s && r[spec.y] != null);
          return rows[rows.length - 1];
        })
      : [data.filter((r) => r[spec.y] != null).at(-1)];
    const labelled = lastByS.filter(Boolean) as Row[];
    const rightRoom = sKey && coloured.length <= MAX_LABELLED ? 120 : 16;

    return Plot.plot({
      ...common,
      height: Math.max(260, Math.min(420, width * 0.6)),
      marginRight: rightRoom,
      x: years
        ? { tickFormat: 'd', label: null, ticks: Math.min(8, Math.floor(width / 70)) }
        : { type: 'point', label: null },
      // Lines need no zero baseline: fit the axis to the data. The unit is in the caption.
      y: { grid: true, label: null, nice: true, zero: false },
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
        Plot.dot(labelled, {
          x: spec.x,
          y: spec.y,
          r: 4,
          fill: sKey ? (r: Row) => strokeFor(String(r[sKey])) : t.series[0],
          stroke: t.surface,
          strokeWidth: 2,
        }),
        ...(sKey && coloured.length <= MAX_LABELLED
          ? [
              Plot.text(labelled, {
                x: spec.x,
                y: spec.y,
                text: (r: Row) => `${r[sKey]} ${numFmt.format(Number(r[spec.y]))}`,
                dx: 8,
                textAnchor: 'start',
                fill: t.ink2,
                fontWeight: 600,
              }),
            ]
          : []),
        Plot.ruleX(data, Plot.pointerX({ x: spec.x, stroke: t.muted, strokeOpacity: 0.6 })),
        Plot.tip(
          data,
          Plot.pointer({
            x: spec.x,
            y: spec.y,
            ...tipStyle,
            channels: sKey ? { [sKey]: sKey } : {},
            format: {
              x: years ? (v: number) => String(v) : true,
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

export default function Chart({ spec, data, label }: Props) {
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
    el.replaceChildren(svg);
  }, [spec, data, label, tick, width]);

  return <div ref={ref} className="chart-canvas" />;
}
