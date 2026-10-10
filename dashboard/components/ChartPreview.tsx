"use client";

import * as Plot from "@observablehq/plot";
import { useEffect, useRef } from "react";

type Row = Record<string, string | number | null>;
type Spec = {
  type?: string;
  x?: string;
  y?: string;
  series?: string;
  highlight?: string | string[];
  title?: string;
  yLabel?: string;
  annotation?: string;
};

const HIGHLIGHT = "#2a78d6";
const OTHER = "#b9b8b1";

/** Preview of the story chart, styled like the public site: highlighted series in blue. */
export default function ChartPreview({ data, spec }: { data: Row[]; spec: Spec }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !spec.x || !spec.y) return;
    const highlights = new Set(
      spec.highlight === undefined ? [] : Array.isArray(spec.highlight) ? spec.highlight : [spec.highlight],
    );
    const seriesKey = spec.series;
    const isHl = (r: Row) => !seriesKey || highlights.has(String(r[seriesKey]));
    const ordered = [...data.filter((r) => !isHl(r)), ...data.filter(isHl)];
    const marks =
      spec.type === "bar"
        ? [Plot.barY(ordered, { x: spec.x, y: spec.y, fill: (r: Row) => (isHl(r) ? HIGHLIGHT : OTHER) })]
        : spec.type === "dot"
          ? [Plot.dot(ordered, { x: spec.x, y: spec.y, fill: (r: Row) => (isHl(r) ? HIGHLIGHT : OTHER), r: 4 })]
          : [
              Plot.lineY(ordered, {
                x: spec.x,
                y: spec.y,
                z: seriesKey,
                stroke: (r: Row) => (isHl(r) ? HIGHLIGHT : OTHER),
                strokeWidth: (r: Row) => (isHl(r) ? 2.5 : 1.25),
              }),
              Plot.dot(ordered.filter(isHl), { x: spec.x, y: spec.y, fill: HIGHLIGHT, r: 3 }),
              Plot.tip(ordered, Plot.pointer({ x: spec.x, y: spec.y, channels: seriesKey ? { [seriesKey]: seriesKey } : {} })),
            ];
    const chart = Plot.plot({
      width: Math.max(320, el.clientWidth),
      height: 300,
      marginLeft: 48,
      x: { type: "point", label: null },
      y: { grid: true, label: spec.yLabel ?? spec.y, zero: false, nice: true },
      marks,
    });
    el.replaceChildren(chart);
    return () => chart.remove();
  }, [data, spec]);

  return (
    <figure style={{ margin: 0 }}>
      {spec.title && <figcaption style={{ fontWeight: 700 }}>{spec.title}</figcaption>}
      <div ref={ref} />
      {spec.annotation && <p className="small muted">{spec.annotation}</p>}
    </figure>
  );
}
