"""Outlier: a group far from the rest in the latest period (robust z-score).

Reported only if the group's confidence interval is clear of the interval of the nearest
group on the side towards the median, i.e. there is a real gap, not just a noisy estimate.
"""

import numpy as np
import pandas as pd

from datatales.detect.base import (
    DetectMeta,
    Finding,
    ci_of,
    cis_separate,
    iter_slices,
    r,
    register,
)


@register("outlier")
def outlier(df: pd.DataFrame, meta: DetectMeta) -> list[Finding]:
    findings: list[Finding] = []
    for key, sub in iter_slices(df, meta.slice_by):
        latest = sub[sub.period == sub.period.max()].reset_index(drop=True)
        n = len(latest)
        if n < meta.min_groups_outlier:
            continue
        values = latest.value.to_numpy(dtype=float)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))
        if mad == 0:
            continue
        latest["z"] = (latest.value - median) / (1.4826 * mad)
        latest["ci"] = [ci_of(lo, hi) for lo, hi in zip(latest.lower, latest.upper, strict=True)]
        candidates = latest[latest.z.abs() >= meta.outlier_z]
        candidates = candidates.reindex(candidates.z.abs().sort_values(ascending=False).index)
        info = meta.info(key)
        for row in candidates.itertuples(index=False):
            others = latest[latest.group != row.group]
            towards_median = (
                others[others.value <= row.value]
                if row.z > 0
                else others[others.value >= row.value]
            )
            if towards_median.empty:
                continue
            nearest = towards_median.loc[(towards_median.value - row.value).abs().idxmin()]
            if not cis_separate(row.ci, nearest.ci):
                continue
            direction = "above" if row.z > 0 else "below"
            what = ", ".join(str(v) for v in key.values())
            findings.append(
                Finding(
                    detector="outlier",
                    slice=key,
                    title_hint=f"{row.group} stands out ({direction} the rest) in {what}",
                    numbers={
                        **key,
                        "group": row.group,
                        "group_code": row.group_code,
                        "period": row.period_label,
                        "value": r(row.value),
                        "ci": row.ci,
                        "median": r(median),
                        "robust_z": r(row.z, 2),
                        "direction": direction,
                        "good_news": (row.z > 0) == info.higher_is_better,
                        "groups_compared": n,
                        "nearest_group": nearest.group,
                        "nearest_value": r(nearest.value),
                        "nearest_ci": nearest.ci,
                        "gap_to_nearest": r(abs(row.value - nearest.value)),
                        "gap_to_median": r(row.value - median),
                        "unit": info.unit,
                        "higher_is_better": info.higher_is_better,
                    },
                    effect=abs(float(row.z)),
                    surprise=max(0.5, min(1.0, abs(float(row.z)) / 5)),
                )
            )
            break  # one outlier per slice: the most extreme one with a real gap
    return findings
