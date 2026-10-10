"""Shared detector types, helpers and the registry.

Detectors receive a *prepared* frame (see prepare.py) with standard columns:
  group, group_code, period, period_label, value, lower, upper, plus the slice columns.
Rows are already reliable and non-null. Detectors must only compare rows within one slice.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

STD_COLUMNS = ("group", "group_code", "period", "period_label", "value", "lower", "upper")


@dataclass(frozen=True)
class SliceInfo:
    unit: str
    higher_is_better: bool


@dataclass(frozen=True)
class DetectMeta:
    slice_by: tuple[str, ...]
    info: Callable[[dict[str, Any]], SliceInfo]
    min_groups_rank: int = 3
    min_groups_outlier: int = 5
    outlier_z: float = 2.5


@dataclass
class Finding:
    detector: str
    slice: dict[str, Any]
    title_hint: str
    numbers: dict[str, Any]
    effect: float  # effect size relative to the series' normal variation (>= 0)
    surprise: float  # 0..1
    score: float = 0.0
    score_parts: dict[str, float] = field(default_factory=dict)

    @property
    def key(self) -> tuple[Any, ...]:
        return (self.detector, tuple(sorted(self.slice.items())), self.numbers.get("group"))


Detector = Callable[[pd.DataFrame, DetectMeta], list[Finding]]
REGISTRY: dict[str, Detector] = {}


def register(name: str) -> Callable[[Detector], Detector]:
    def deco(fn: Detector) -> Detector:
        if name in REGISTRY:
            raise ValueError(f"detector '{name}' registered twice")
        REGISTRY[name] = fn
        return fn

    return deco


# ---- helpers ----


def iter_slices(
    df: pd.DataFrame, slice_by: tuple[str, ...]
) -> Iterator[tuple[dict[str, Any], pd.DataFrame]]:
    if not slice_by:
        yield {}, df
        return
    for key, sub in df.groupby(list(slice_by), sort=True, dropna=False):
        values = key if isinstance(key, tuple) else (key,)
        yield {c: _plain(v) for c, v in zip(slice_by, values, strict=True)}, sub


def _plain(v: Any) -> Any:
    if isinstance(v, np.generic):
        return v.item()
    return v


def ci_of(lo: Any, hi: Any) -> list[float] | None:
    """Confidence interval as [lower, upper], or None if either bound is unknown."""
    if lo is None or hi is None or pd.isna(lo) or pd.isna(hi):
        return None
    return [round(float(lo), 6), round(float(hi), 6)]


def cis_separate(a: list[float] | None, b: list[float] | None) -> bool:
    """True only if both intervals are known and do not overlap."""
    if a is None or b is None:
        return False
    return a[1] < b[0] or b[1] < a[0]


def robust_sd(values: pd.Series | np.ndarray) -> float:
    """1.4826 x MAD (robust standard deviation); falls back to std; never 0."""
    arr = np.asarray(pd.Series(values).dropna(), dtype=float)
    if arr.size == 0:
        return 1.0
    mad = float(np.median(np.abs(arr - np.median(arr))))
    sd = 1.4826 * mad if mad > 0 else float(np.std(arr))
    return sd if sd > 1e-9 else 1e-9


def yoy_diffs(sub: pd.DataFrame) -> pd.Series:
    """Consecutive-period changes for every group in a slice: the series' normal variation."""
    ordered = sub.sort_values(["group", "period"])
    return ordered.groupby("group")["value"].diff().dropna()


def panel(sub: pd.DataFrame, p0: Any, p1: Any) -> pd.DataFrame:
    """Groups with a value in both periods: one row per group, columns suffixed _0 / _1."""
    a = sub[sub.period == p0].set_index("group")
    b = sub[sub.period == p1].set_index("group")
    both = a.join(b, how="inner", lsuffix="_0", rsuffix="_1")
    return both.reset_index().sort_values("group", kind="stable").reset_index(drop=True)


def r(x: float, places: int = 4) -> float:
    return round(float(x), places)
