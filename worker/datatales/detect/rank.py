"""Rank shift: the group whose rank moved most between the first and last period.

An overtake only counts when the two groups' confidence intervals are clearly apart in
BOTH periods (behind before, ahead after), so ranking noise is not reported as news.
Rank 1 = highest value; whether that is good depends on the slice's polarity.
"""

from typing import Any

import pandas as pd

from datatales.detect.base import (
    DetectMeta,
    Finding,
    ci_of,
    cis_separate,
    iter_slices,
    panel,
    r,
    register,
)


def _clear_swap(g: Any, h: Any) -> bool:
    """g was clearly behind h in the first period and is clearly ahead in the last."""
    return (
        g.rank_0 > h.rank_0
        and g.rank_1 < h.rank_1
        and cis_separate(g.ci_0, h.ci_0)
        and cis_separate(g.ci_1, h.ci_1)
    )


def _brief(h: Any) -> dict[str, Any]:
    return {
        "group": h.group,
        "start_rank": int(h.rank_0),
        "end_rank": int(h.rank_1),
        "start_value": r(h.value_0),
        "end_value": r(h.value_1),
        "start_ci": h.ci_0,
        "end_ci": h.ci_1,
    }


@register("rank_shift")
def rank_shift(df: pd.DataFrame, meta: DetectMeta) -> list[Finding]:
    findings: list[Finding] = []
    for key, sub in iter_slices(df, meta.slice_by):
        periods = sorted(sub.period.unique())
        if len(periods) < 2:
            continue
        both = panel(sub, periods[0], periods[-1])  # only groups present in both periods
        n = len(both)
        if n < meta.min_groups_rank:
            continue
        both["rank_0"] = both.value_0.rank(ascending=False, method="min").astype(int)
        both["rank_1"] = both.value_1.rank(ascending=False, method="min").astype(int)
        both["ci_0"] = [ci_of(lo, hi) for lo, hi in zip(both.lower_0, both.upper_0, strict=True)]
        both["ci_1"] = [ci_of(lo, hi) for lo, hi in zip(both.lower_1, both.upper_1, strict=True)]
        rows = list(both.itertuples(index=False))

        best = None
        for g in rows:
            passed = [h for h in rows if h is not g and _clear_swap(g, h)]
            passed_by = [h for h in rows if h is not g and _clear_swap(h, g)]
            if not (passed or passed_by):
                continue
            shift = int(g.rank_0 - g.rank_1)  # positive = moved up
            strength = (abs(shift), len(passed) + len(passed_by))
            # ties: bigger move, then more clear overtakes, then first by name (rows are sorted)
            if best is None or strength > best[4]:
                best = (g, shift, passed, passed_by, strength)
        if best is None:
            continue

        g, shift, passed, passed_by, _ = best
        info = meta.info(key)
        numbers = {
            **key,
            **_brief(g),
            "group_code": g.group_code_0,
            "start_period": g.period_label_0,
            "end_period": g.period_label_1,
            "rank_change": shift,
            "direction": "up" if shift > 0 else "down",
            "groups_ranked": n,
            "rank_1_means": "highest value",
            "overtook": [_brief(h) for h in passed],
            "overtaken_by": [_brief(h) for h in passed_by],
            "unit": info.unit,
            "higher_is_better": info.higher_is_better,
        }
        what = ", ".join(str(v) for v in key.values())
        verb = "climbed" if shift > 0 else "dropped"
        findings.append(
            Finding(
                detector="rank_shift",
                slice=key,
                title_hint=f"{g.group} {verb} {abs(shift)} place(s) in {what}",
                numbers=numbers,
                effect=float(len(passed) + len(passed_by)) + abs(shift) / max(n - 1, 1),
                surprise=min(1.0, 0.5 + abs(shift) / n),
            )
        )
    return findings
