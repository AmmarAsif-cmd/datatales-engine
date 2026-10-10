import type { Finding, Json } from "@/lib/types";

type Pt = { v: number; ci: [number, number] | null; label: string; strong?: boolean };

const W = 180;
const H = 34;

function ci(x: Json | undefined): [number, number] | null {
  return Array.isArray(x) && x.length === 2 ? [Number(x[0]), Number(x[1])] : null;
}

/** Tiny SVG: start and end (with CIs) for changes and ranks; value vs median for outliers. */
export default function MiniChart({ finding }: { finding: Finding }) {
  const n = finding.numbers;
  let pts: Pt[] = [];
  let median: number | null = null;
  if (finding.detector === "outlier") {
    pts = [
      { v: Number(n.value), ci: ci(n.ci), label: String(n.group ?? ""), strong: true },
      { v: Number(n.nearest_value), ci: ci(n.nearest_ci), label: String(n.nearest_group ?? "") },
    ];
    median = Number(n.median);
  } else if (n.start_value !== undefined && n.end_value !== undefined) {
    pts = [
      { v: Number(n.start_value), ci: ci(n.start_ci), label: String(n.start_period ?? "start") },
      {
        v: Number(n.end_value),
        ci: ci(n.end_ci),
        label: String(n.end_period ?? "end"),
        strong: true,
      },
    ];
  }
  if (!pts.length) return null;
  const all = pts.flatMap((p) => (p.ci ? [...p.ci, p.v] : [p.v])).concat(median ?? []);
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const pad = (hi - lo || 1) * 0.08;
  const x = (v: number) => 6 + ((v - lo + pad) / (hi - lo + 2 * pad)) * (W - 12);
  const colour = n.good_news === true ? "#0f7b3e" : "#b3261e";
  const label = pts.map((p) => `${p.label} ${p.v}`).join(", ");
  return (
    <svg width={W} height={H} role="img" aria-label={label}>
      <line x1={6} x2={W - 6} y1={H / 2} y2={H / 2} stroke="#e2e1da" />
      {median !== null && (
        <line
          x1={x(median)}
          x2={x(median)}
          y1={4}
          y2={H - 4}
          stroke="#84837d"
          strokeDasharray="2 2"
        />
      )}
      {pts.length === 2 && finding.detector !== "outlier" && (
        <line
          x1={x(pts[0].v)}
          x2={x(pts[1].v)}
          y1={H / 2}
          y2={H / 2}
          stroke={colour}
          strokeWidth={2}
        />
      )}
      {pts.map((p, i) => (
        <g key={i}>
          {p.ci && (
            <line
              x1={x(p.ci[0])}
              x2={x(p.ci[1])}
              y1={H / 2}
              y2={H / 2}
              stroke={p.strong ? colour : "#84837d"}
              strokeWidth={6}
              strokeOpacity={0.25}
            />
          )}
          <circle
            cx={x(p.v)}
            cy={H / 2}
            r={4}
            fill={p.strong ? colour : "#84837d"}
            stroke="#fff"
            strokeWidth={1.5}
          >
            <title>{`${p.label}: ${p.v}${p.ci ? ` (CI ${p.ci[0]}–${p.ci[1]})` : ""}`}</title>
          </circle>
        </g>
      ))}
    </svg>
  );
}
