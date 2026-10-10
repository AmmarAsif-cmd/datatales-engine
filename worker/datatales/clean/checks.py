"""Validation checks run after every clean. Any failure stops the pipeline for that dataset."""

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from datatales.clean.schema import Checks


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _where(df: pd.DataFrame, where: dict[str, list[Any]] | None) -> pd.DataFrame:
    """Rows where every listed column's value is one of its allowed values."""
    if not where:
        return df
    mask = pd.Series(True, index=df.index)
    for col, allowed in where.items():
        mask &= df[col].isin(allowed)
    return df[mask]


def run_checks(df: pd.DataFrame, checks: Checks) -> list[CheckResult]:
    results: list[CheckResult] = []

    def add(name: str, passed: bool, detail: str) -> None:
        results.append(CheckResult(name, bool(passed), detail))

    missing = [c for c in checks.expected_columns if c not in df.columns]
    extra = [c for c in df.columns if c not in checks.expected_columns]
    add(
        "expected_columns",
        not missing,
        f"missing {missing}"
        if missing
        else f"all {len(checks.expected_columns)} present" + (f"; extra {extra}" if extra else ""),
    )

    n = len(df)
    lo, hi = checks.row_count.min, checks.row_count.max
    ok = n >= lo and (hi is None or n <= hi)
    add("row_count", ok, f"{n:,} rows (expected {lo:,} to {'∞' if hi is None else f'{hi:,}'})")

    for col in checks.not_null:
        if col not in df.columns:
            add(f"not_null:{col}", False, "column missing")
            continue
        nulls = int(df[col].isna().sum())
        add(f"not_null:{col}", nulls == 0, f"{nulls:,} null(s)")

    if checks.unique:
        cols = [c for c in checks.unique if c in df.columns]
        if len(cols) != len(checks.unique):
            add("unique", False, f"columns missing: {set(checks.unique) - set(cols)}")
        else:
            dupes = int(df.duplicated(subset=cols).sum())
            add("unique", dupes == 0, f"{dupes:,} duplicate key row(s) on {cols}")

    for col, rng in checks.ranges.items():
        if col not in df.columns:
            add(f"range:{col}", False, "column missing")
            continue
        values = _numeric(df[col]).dropna()
        if values.empty:
            add(f"range:{col}", False, "no numeric values")
            continue
        below = int((values < rng.min).sum()) if rng.min is not None else 0
        above = int((values > rng.max).sum()) if rng.max is not None else 0
        add(
            f"range:{col}",
            below == 0 and above == 0,
            f"min {values.min():g}, max {values.max():g}; "
            f"{below} below {rng.min}, {above} above {rng.max}",
        )

    for rw in checks.ranges_where:
        name = f"range:{rw.name}"
        needed = [rw.column, *rw.where]
        if any(c not in df.columns for c in needed):
            add(name, False, f"columns missing from {needed}")
            continue
        values = _numeric(_where(df, rw.where)[rw.column]).dropna()
        if values.empty:
            add(name, False, "no rows match `where`, or no numeric values")
            continue
        below = int((values < rw.min).sum()) if rw.min is not None else 0
        above = int((values > rw.max).sum()) if rw.max is not None else 0
        add(
            name,
            below == 0 and above == 0,
            f"{len(values):,} values, min {values.min():g}, max {values.max():g}; "
            f"{below} below {rw.min}, {above} above {rw.max}",
        )

    for sc in checks.sums:
        name = f"sum:{sc.name}"
        needed = [sc.value, *sc.group_by, *(sc.where or {})]
        if any(c not in df.columns for c in needed):
            add(name, False, f"columns missing from {needed}")
            continue
        part = _where(df, sc.where)
        vals = part.assign(_v=_numeric(part[sc.value]))
        grouped = vals.groupby(sc.group_by, dropna=False)["_v"]
        sizes, nulls, sums = grouped.size(), grouped.apply(lambda x: x.isna().sum()), grouped.sum()
        usable = nulls == 0
        if sc.group_size is not None:
            usable &= sizes == sc.group_size
        n_usable, n_skipped = int(usable.sum()), int((~usable).sum())
        deviation = (sums[usable] - sc.target).abs()
        off = deviation > sc.tolerance
        worst = f"{deviation.max():.4g}" if n_usable else "n/a"
        add(
            name,
            n_usable > 0 and not off.any(),
            f"{n_usable:,} complete group(s) checked, {n_skipped:,} skipped (null or partial); "
            f"max |sum-{sc.target:g}| = {worst}; {int(off.sum())} beyond ±{sc.tolerance:g}",
        )
    return results


def results_to_json(results: list[CheckResult]) -> list[dict[str, Any]]:
    return [asdict(r) for r in results]


def all_passed(results: list[CheckResult]) -> bool:
    return all(r.passed for r in results)
