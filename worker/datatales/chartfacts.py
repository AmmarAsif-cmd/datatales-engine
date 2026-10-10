"""Rank and exclusivity facts ("only", "all", "highest", "lowest", "biggest") over chart_data.

Used twice, with the same rules: storydata lists which framings the data supports (so the
narrator can use them), and the verifier checks every such claim in a story against
chart_data. chart_data rows are {period, geography, value, lower, upper}.

A fact only holds when it is clear:
- highest/lowest: the group's confidence interval does not overlap the runner-up's.
- only/biggest rise or fall: the group's own change is clear (start and end CIs apart).
- all rise/fall: every group moved that way (direction only; reported with the count).
"""

from typing import Any

CHECK_KINDS = (
    "highest",
    "lowest",
    "only_rise",
    "only_fall",
    "all_rise",
    "all_fall",
    "biggest_rise",
    "biggest_fall",
)
NEEDS_PERIOD = ("highest", "lowest")
NEEDS_GROUP = ("highest", "lowest", "only_rise", "only_fall", "biggest_rise", "biggest_fall")

Point = tuple[float, float | None, float | None]  # value, lower, upper


def by_group(chart_data: list[dict[str, Any]]) -> dict[str, dict[str, Point]]:
    out: dict[str, dict[str, Point]] = {}
    for row in chart_data:
        if row.get("value") is None:
            continue
        out.setdefault(str(row.get("geography")), {})[str(row.get("period"))] = (
            float(row["value"]),
            None if row.get("lower") is None else float(row["lower"]),
            None if row.get("upper") is None else float(row["upper"]),
        )
    return out


def _clear_change(a: Point, b: Point) -> bool:
    if None in (a[1], a[2], b[1], b[2]):
        return False
    return a[2] < b[1] or b[2] < a[1]  # type: ignore[operator]


def _fmt(x: float) -> str:
    return f"{x:g}"


def evaluate(check: dict[str, Any], chart_data: list[dict[str, Any]]) -> tuple[bool, str]:
    """(holds, explanation) for one check against chart_data."""
    kind = check.get("kind")
    if kind not in CHECK_KINDS:
        return False, f"unknown check kind {kind!r}"
    groups = by_group(chart_data)
    group = check.get("group")
    if kind in NEEDS_GROUP and group not in groups:
        return False, f"group {group!r} is not in the chart data"

    if kind in NEEDS_PERIOD:
        period = check.get("period")
        at = {g: pts[period] for g, pts in groups.items() if period in pts}
        if group not in at:
            return False, f"no value for {group} in {period}"
        if len(at) < 2:
            return False, f"fewer than two groups have a value in {period}"
        ranked = sorted(at.items(), key=lambda kv: kv[1][0], reverse=(kind == "highest"))
        top, (runner, rv) = ranked[0], ranked[1]
        if top[0] != group:
            return False, f"{top[0]} ({_fmt(top[1][0])}) is {kind} in {period}, not {group}"
        gv = at[group]
        if None in (gv[1], gv[2], rv[1], rv[2]):
            return False, "confidence intervals unknown"
        clear = gv[1] > rv[2] if kind == "highest" else gv[2] < rv[1]  # type: ignore[operator]
        if not clear:
            return (
                False,
                f"{group} ({_fmt(gv[0])}) is not clearly apart from {runner} ({_fmt(rv[0])})",
            )
        return True, f"{group} {_fmt(gv[0])} vs next {runner} {_fmt(rv[0])} in {period}, clear"

    start, end = check.get("start"), check.get("end")
    both = {g: (pts[start], pts[end]) for g, pts in groups.items() if start in pts and end in pts}
    if len(both) < 2:
        return False, f"fewer than two groups have values for both {start} and {end}"
    change = {g: e[0] - s[0] for g, (s, e) in both.items()}
    rising = kind.endswith("rise")

    if kind in ("all_rise", "all_fall"):
        moved = [g for g, c in change.items() if (c > 0 if rising else c < 0)]
        ok = len(moved) == len(change)
        return ok, f"{len(moved)} of {len(change)} groups {'rose' if rising else 'fell'}"

    if group not in both:
        return False, f"{group} has no values for both {start} and {end}"
    own = change[group]
    if (own <= 0) if rising else (own >= 0):
        return (
            False,
            f"{group} {'did not rise' if rising else 'did not fall'} ({_fmt(round(own, 4))})",
        )
    if not _clear_change(*both[group]):
        return False, f"{group}'s change ({_fmt(round(own, 4))}) is within the confidence intervals"
    others = {g: c for g, c in change.items() if g != group}
    if kind.startswith("only"):
        same = [g for g, c in others.items() if (c > 0 if rising else c < 0)]
        if same:
            return False, f"{', '.join(sorted(same))} also {'rose' if rising else 'fell'}"
        return True, f"{group} {_fmt(round(own, 4))}; all {len(others)} others did not"
    best = max(others.values()) if rising else min(others.values())
    if (own <= best) if rising else (own >= best):
        return False, f"{group} ({_fmt(round(own, 4))}) is not the biggest change"
    return True, f"{group} {_fmt(round(own, 4))}, next {_fmt(round(best, 4))}"


def facts_for(chart_data: list[dict[str, Any]], group: str) -> dict[str, Any]:
    """What the chart data supports for `group` (first vs last period, and the last period)."""
    periods = sorted({str(r["period"]) for r in chart_data if r.get("value") is not None})
    if len(periods) < 2:
        return {}
    start, end = periods[0], periods[-1]
    groups = by_group(chart_data)
    both = {g: (p[start], p[end]) for g, p in groups.items() if start in p and end in p}
    supported = []
    for kind in CHECK_KINDS:
        check: dict[str, Any] = {"kind": kind}
        if kind in NEEDS_GROUP:
            check["group"] = group
        if kind in NEEDS_PERIOD:
            check["period"] = end
        else:
            check |= {"start": start, "end": end}
        ok, detail = evaluate(check, chart_data)
        if ok:
            supported.append({**check, "detail": detail})
    return {
        "group": group,
        "start": start,
        "end": end,
        "groups_compared": len(both),
        "groups_rising": sum(1 for s, e in both.values() if e[0] > s[0]),
        "groups_falling": sum(1 for s, e in both.values() if e[0] < s[0]),
        "supported_checks": supported,
    }
