"""Build a story's chart data and supporting numbers from the clean table.

Everything here comes from the clean Parquet (reliable, non-null rows only), so every
number a story can mention is computed, stored in `stories.numbers`, and verifiable.
"""

from typing import Any

import pandas as pd

from datatales.candidates import Candidate
from datatales.chartfacts import facts_for
from datatales.detect.base import ci_of, cis_separate, r, robust_sd, yoy_diffs
from datatales.detect.prepare import prepare
from datatales.sources import DetectConfig, SourceDef

NOTABLE_MULTIPLIER = 2.0  # a year-on-year move is notable at >= 2x the typical yearly change


def _slice_key(numbers: dict[str, Any], slice_by: tuple[str, ...]) -> dict[str, Any]:
    return {c: numbers[c] for c in slice_by}


def _in_slice(frame: pd.DataFrame, key: dict[str, Any]) -> pd.DataFrame:
    mask = pd.Series(True, index=frame.index)
    for col, value in key.items():
        mask &= frame[col] == value
    return frame[mask]


def series_points(sub: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {"period": row.period_label, "value": r(row.value), "ci": ci_of(row.lower, row.upper)}
        for row in sub.sort_values("period").itertuples(index=False)
    ]


def notable_moves(points: list[dict[str, Any]], typical: float) -> list[dict[str, Any]]:
    """Year-on-year moves that are clear (CIs apart) and large (>= 2x typical change)."""
    moves: list[dict[str, Any]] = []
    for i in range(1, len(points)):
        prev, cur = points[i - 1], points[i]
        change = cur["value"] - prev["value"]
        if abs(change) < NOTABLE_MULTIPLIER * typical or not cis_separate(prev["ci"], cur["ci"]):
            continue
        move: dict[str, Any] = {
            "period": cur["period"],
            "previous_period": prev["period"],
            "value": cur["value"],
            "previous_value": prev["value"],
            "change": r(change),
            "kind": "rise" if change > 0 else "fall",
        }
        if i + 1 < len(points):
            nxt = points[i + 1]
            rebound = nxt["value"] - cur["value"]
            if rebound != 0 and (rebound > 0) != (change > 0):
                move["kind"] = "dip" if change < 0 else "spike"
                move["next_period"] = nxt["period"]
                move["next_value"] = nxt["value"]
        moves.append(move)
    return moves


def common_moves(sub: pd.DataFrame) -> list[dict[str, Any]]:
    """Periods where at least half the geographies moved clearly in the same direction."""
    out = []
    groups = sub.group.nunique()
    if groups < 2:
        return out
    periods = sorted(sub.period.unique())
    for p_prev, p in zip(periods, periods[1:], strict=False):
        a = sub[sub.period == p_prev].set_index("group")
        b = sub[sub.period == p].set_index("group")
        both = a.join(b, how="inner", lsuffix="_0", rsuffix="_1")
        falls = rises = 0
        for row in both.itertuples():
            if cis_separate(ci_of(row.lower_0, row.upper_0), ci_of(row.lower_1, row.upper_1)):
                falls += row.value_1 < row.value_0
                rises += row.value_1 > row.value_0
        for direction, count in (("fall", falls), ("rise", rises)):
            if count >= 2 and count * 2 >= len(both):
                label = b.period_label.iloc[0]
                out.append(
                    {"period": label, "direction": direction, "groups": int(count), "of": len(both)}
                )
    return out


def peak_info(points: list[dict[str, Any]], typical: float) -> dict[str, Any]:
    """Peak and low point of a series, and whether the latest value is well below the peak
    (confidence intervals apart AND at least 2x the typical yearly change)."""
    if not points:
        return {}
    peak = max(points, key=lambda p: p["value"])
    low = min(points, key=lambda p: p["value"])
    latest = points[-1]
    gap = r(peak["value"] - latest["value"])
    well_below = (
        latest is not peak
        and gap >= NOTABLE_MULTIPLIER * typical
        and cis_separate(peak["ci"], latest["ci"])
    )
    return {
        "peak_period": peak["period"],
        "peak_value": peak["value"],
        "low_period": low["period"],
        "low_value": low["value"],
        "latest_period": latest["period"],
        "latest_value": latest["value"],
        "latest_below_peak_by": gap,
        "latest_well_below_peak": bool(well_below),
        "latest_is_peak": latest is peak,
    }


def build_story_data(
    clean: pd.DataFrame, source: SourceDef, config: DetectConfig, candidate: Candidate
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Returns (chart_data, suggested chart_spec, numbers)."""
    frame, meta = prepare(clean, config)

    # Chart the finding whose slice gives the most context: most geographies to compare
    # against, then most years, then the highest score.
    def context(f: dict[str, Any]) -> tuple[int, int, float]:
        sub = _in_slice(frame, _slice_key(f["numbers"], meta.slice_by))
        return (sub.group.nunique(), sub.period.nunique(), float(f["score"]))

    chart_finding = max(candidate.findings, key=context)
    lead_key = _slice_key(chart_finding["numbers"], meta.slice_by)
    lead_slice = _in_slice(frame, lead_key)

    chart_data = [
        {
            "period": row.period_label,
            "geography": row.group,
            "value": r(row.value),
            "lower": None if pd.isna(row.lower) else r(row.lower),
            "upper": None if pd.isna(row.upper) else r(row.upper),
        }
        for row in lead_slice.sort_values(["group", "period"]).itertuples(index=False)
    ]
    info = meta.info(lead_key)
    chart_spec = {
        "type": "line",
        "x": "period",
        "y": "value",
        "series": "geography",
        "highlight": candidate.geography,
        "yLabel": info.unit,
    }

    series: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for f in candidate.findings:
        key = _slice_key(f["numbers"], meta.slice_by)
        marker = tuple(key.items())
        if marker in seen:
            continue
        seen.add(marker)
        sub = _in_slice(frame, key)
        typical = robust_sd(yoy_diffs(sub))
        points = series_points(sub[sub.group == candidate.geography])
        series.append(
            {
                **key,
                "geography": candidate.geography,
                "unit": meta.info(key).unit,
                "typical_yearly_change": r(typical),
                "points": points,
                "notable_moves": notable_moves(points, typical),
                "peak": peak_info(points, typical),
                "moves_shared_by_most_geographies": common_moves(sub),
            }
        )

    periods = sorted(frame.period_label.unique())
    numbers = {
        "source": {
            "name": source.name,
            "publisher": source.publisher,
            "url": str(source.url),
            "licence": source.licence,
        },
        "caveats": list(source.caveats),
        "geography": candidate.geography,
        "geo_level": candidate.geo_level,
        "good_news": candidate.good_news,
        "data_period": {"first": periods[0], "last": periods[-1]} if periods else {},
        "findings": [
            {
                "id": f["id"],
                "detector": f["detector"],
                "title_hint": f["title_hint"],
                **f["numbers"],
            }
            for f in candidate.findings
        ],
        "series": series,
        "chart_facts": facts_for(chart_data, candidate.geography),
    }
    return chart_data, chart_spec, numbers
