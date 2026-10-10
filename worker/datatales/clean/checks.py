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

    for sc in checks.sums:
        needed = [sc.value, *sc.group_by] + ([sc.where_column] if sc.where_column else [])
        if any(c not in df.columns for c in needed):
            add(f"sum:{sc.name}", False, f"columns missing from {needed}")
            continue
        part = df
        if sc.where_column and sc.where_in is not None:
            part = df[df[sc.where_column].isin(sc.where_in)]
        vals = part.assign(_v=_numeric(part[sc.value]))
        grouped = vals.groupby(sc.group_by, dropna=False)["_v"]
        sizes, nulls, sums = grouped.size(), grouped.apply(lambda x: x.isna().sum()), grouped.sum()
        expected_size = len(sc.where_in) if sc.where_in else None
        usable = nulls == 0
        if sc.complete_groups_only and expected_size:
            usable &= sizes == expected_size
        off = (sums[usable] - sc.target).abs() > sc.tolerance
        add(
            f"sum:{sc.name}",
            int(usable.sum()) > 0 and not off.any(),
            f"{int(usable.sum()):,} complete group(s) checked, {int(off.sum())} off target "
            f"{sc.target}±{sc.tolerance}",
        )
    return results


def results_to_json(results: list[CheckResult]) -> list[dict[str, Any]]:
    return [asdict(r) for r in results]


def all_passed(results: list[CheckResult]) -> bool:
    return all(r.passed for r in results)
