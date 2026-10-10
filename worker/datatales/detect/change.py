"""Biggest change: largest rise and largest fall between the first and last period."""

import numpy as np
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
    robust_sd,
    yoy_diffs,
)


def _describe(slice_key: dict, group: str, direction: str) -> str:
    what = ", ".join(str(v) for v in slice_key.values())
    return f"{group}: biggest {direction} in {what}"


@register("biggest_change")
def biggest_change(df: pd.DataFrame, meta: DetectMeta) -> list[Finding]:
    findings: list[Finding] = []
    for key, sub in iter_slices(df, meta.slice_by):
        periods = sorted(sub.period.unique())
        if len(periods) < 2:
            continue
        p0, p1 = periods[0], periods[-1]
        both = panel(sub, p0, p1)  # only groups present in both periods
        if both.empty:
            continue
        both["change"] = both.value_1 - both.value_0
        both["ci_0"] = [ci_of(lo, hi) for lo, hi in zip(both.lower_0, both.upper_0, strict=True)]
        both["ci_1"] = [ci_of(lo, hi) for lo, hi in zip(both.lower_1, both.upper_1, strict=True)]
        both["significant"] = [
            cis_separate(a, b) for a, b in zip(both.ci_0, both.ci_1, strict=True)
        ]
        sig = both[both.significant]
        if sig.empty:
            continue
        variation = robust_sd(yoy_diffs(sub))
        median_change = float(np.median(both.change))
        info = meta.info(key)
        ranked = both.assign(abs_change=both.change.abs()).sort_values(
            "abs_change", ascending=False
        )
        ranks = {g: i + 1 for i, g in enumerate(ranked.group)}

        picks = []
        rises, falls = sig[sig.change > 0], sig[sig.change < 0]
        if not rises.empty:
            picks.append(rises.loc[rises.change.idxmax()])
        if not falls.empty:
            picks.append(falls.loc[falls.change.idxmin()])
        for row in picks:
            change = float(row.change)
            direction = "rise" if change > 0 else "fall"
            bucks_trend = (
                len(both) > 1 and np.sign(change) != np.sign(median_change) and median_change != 0
            )
            pct = None if row.value_0 == 0 else r(100 * change / float(row.value_0), 2)
            numbers = {
                **key,
                "group": row.group,
                "group_code": row.group_code_0,
                "start_period": row.period_label_0,
                "end_period": row.period_label_1,
                "start_value": r(row.value_0),
                "end_value": r(row.value_1),
                "start_ci": row.ci_0,
                "end_ci": row.ci_1,
                "change": r(change),
                # For values that are themselves percentages, `change` is in percentage
                # points; `pct_change` is the relative change and must not be called "points".
                "change_unit": "percentage points" if info.unit.startswith("%") else info.unit,
                "pct_change": pct,
                "direction": direction,
                "change_rank": ranks[row.group],
                "groups_compared": len(both),
                "median_change": r(median_change),
                "typical_yearly_change": r(variation),
                "unit": info.unit,
                "higher_is_better": info.higher_is_better,
                "improved": (change > 0) == info.higher_is_better,
            }
            findings.append(
                Finding(
                    detector="biggest_change",
                    slice=key,
                    title_hint=_describe(key, row.group, direction),
                    numbers=numbers,
                    effect=abs(change) / variation,
                    surprise=1.0 if bucks_trend else 0.6,
                )
            )
    return findings
