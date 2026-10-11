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
from datatales.geo import mappable
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


GROUP_NOUNS = {
    "country": "UK nations",
    "region": "English regions",
    "local_authority": "local authorities",
}


def is_exact(config: DetectConfig) -> bool:
    """Administrative counts (no sampling error): precision band instead of CIs."""
    return bool(config.precision_pct) and not (config.lower or config.upper)


def exact_count_caveat(config: DetectConfig) -> list[str]:
    if not is_exact(config):
        return []
    return [
        "These are administrative counts, not survey estimates, so they have no margin of error; "
        f"changes smaller than {config.precision_pct:g}% are treated as no real change."
    ]


def ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def rank_shift_for(
    findings: list[dict[str, Any]], key: dict[str, Any], group: str | None = None
) -> dict[str, Any] | None:
    """A rank_shift result (a finding, or merged under `related`) for the charted slice and,
    when given, the story's own place."""
    for f in findings:
        if any(f["numbers"].get(k) != v for k, v in key.items()):
            continue  # another measure: its ranks say nothing about the charted one
        # Related results were merged from findings for the same place and slice.
        entries = [{"detector": f["detector"], "numbers": f["numbers"]}]
        entries += f["numbers"].get("related") or []
        for e in entries:
            n = e.get("numbers") or {}
            if e.get("detector") != "rank_shift" or "start_rank" not in n or "end_rank" not in n:
                continue
            if group is None or n.get("group", f["numbers"].get("group")) == group:
                return n
    return None


def cover_facts(
    chart_data: list[dict[str, Any]],
    group: str,
    geo_level: str | None,
    label: str,
    unit: str,
    rank: dict[str, Any] | None,
    facts: dict[str, Any],
) -> dict[str, Any]:
    """The headline number and badge for a story's cover image, from code-computed values.
    Text only: every number here also appears in chart_data or the findings."""
    from datatales.publish import format_value

    points = sorted(
        (str(r["period"]), r["value"])
        for r in chart_data
        if r.get("geography") == group and r.get("value") is not None
    )
    if not points:
        return {}
    (p0, v0), (p1, v1) = points[0], points[-1]
    noun = GROUP_NOUNS.get(geo_level or "", "areas")
    cover: dict[str, Any] = {
        "group": group,
        "value": format_value(v1, unit),
        "label": f"{label}, {p1}",
        "measure_label": label,
    }
    if len(points) > 1 and v1 != v0:
        word = "Up" if v1 > v0 else "Down"
        cover["change"] = f"{word} from {format_value(v0, unit)} in {p0}"
    n = facts.get("groups_compared")
    kinds = {c["kind"]: c for c in facts.get("supported_checks", [])}
    if rank and rank.get("start_rank") != rank.get("end_rank"):
        total = rank.get("groups_ranked") or n
        cover["rank"] = {
            "start_rank": rank["start_rank"],
            "end_rank": rank["end_rank"],
            "groups": total,
            "noun": noun,
            "start_period": rank.get("start_period", p0),
            "end_period": rank.get("end_period", p1),
            "first_means": "highest",  # rank_shift ranks by value, 1st = highest
        }
        cover["badge"] = (
            f"{ordinal(rank['start_rank'])} → {ordinal(rank['end_rank'])} of {total} {noun}"
        )
    elif "only_rise" in kinds or "only_fall" in kinds:
        verb = "rise" if "only_rise" in kinds else "fall"
        cover["badge"] = f"The only one of the {n} {noun} to {verb}"
    elif "highest" in kinds or "lowest" in kinds:
        cover["badge"] = f"{'Highest' if 'highest' in kinds else 'Lowest'} of the {n} {noun}"
    elif "biggest_rise" in kinds or "biggest_fall" in kinds:
        cover["badge"] = (
            f"Biggest {'rise' if 'biggest_rise' in kinds else 'fall'} of the {n} {noun}"
        )
    return cover


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
            **({"code": row.group_code} if config.group_code else {}),
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
    more: list[dict[str, Any]] = []
    if lead_slice.period.nunique() >= 3 and lead_slice.group.nunique() >= 2:
        more.append({**chart_spec, "type": "slope"})
    if config.group_code and mappable({str(r["code"]) for r in chart_data}):
        more.append({**chart_spec, "type": "map"})
    if more:
        chart_spec["more_charts"] = more

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
        "caveats": list(source.caveats) + exact_count_caveat(config),
        **(
            {"exact_counts": True, "precision_pct": config.precision_pct}
            if is_exact(config)
            else {}
        ),  # fmt: skip
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
    from datatales.publish import label_for

    numbers["cover"] = cover_facts(
        chart_data,
        candidate.geography,
        candidate.geo_level,
        label_for(config, lead_key),
        info.unit,
        rank_shift_for(candidate.findings, lead_key, candidate.geography),
        numbers["chart_facts"],
    )
    return chart_data, chart_spec, numbers
