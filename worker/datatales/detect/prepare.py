"""Turn a clean table into the standard detector frame, using a source's DetectConfig."""

from typing import Any

import numpy as np
import pandas as pd

from datatales.detect.base import DetectMeta, SliceInfo
from datatales.sources import DetectConfig


def _matches(when: dict[str, list[Any]], slice_key: dict[str, Any]) -> bool:
    return all(slice_key.get(col) in allowed for col, allowed in when.items())


def slice_info_fn(config: DetectConfig):  # noqa: ANN201 - Callable[[dict], SliceInfo]
    def info(slice_key: dict[str, Any]) -> SliceInfo:
        unit = next(
            (u.unit for u in config.units if _matches(u.when, slice_key)), config.default_unit
        )
        better = next(
            (p.higher_is_better for p in config.polarity if _matches(p.when, slice_key)),
            config.default_higher_is_better,
        )
        return SliceInfo(unit=unit, higher_is_better=better)

    return info


def prepare(clean: pd.DataFrame, config: DetectConfig) -> tuple[pd.DataFrame, DetectMeta]:
    needed = [config.group, config.period, config.value, *config.slice_by, *config.filters]
    needed += [c for c in (config.group_code, config.period_label, config.lower, config.upper) if c]
    missing = sorted({c for c in needed if c not in clean.columns})
    if missing:
        raise ValueError(f"clean table lacks detect columns {missing}")
    rule_cols = {c for rule in [*config.units, *config.polarity] for c in rule.when}
    stray = rule_cols - set(config.slice_by)
    if stray:
        raise ValueError(f"unit/polarity rules may only use slice_by columns, not {sorted(stray)}")

    df = clean
    for col, allowed in config.filters.items():
        df = df[df[col].isin(allowed)]

    out = pd.DataFrame(
        {
            "group": df[config.group].astype(str),
            "group_code": df[config.group_code].astype(str)
            if config.group_code
            else df[config.group].astype(str),
            "period": df[config.period],
            "period_label": df[config.period_label].astype(str)
            if config.period_label
            else df[config.period].astype(str),
            "value": pd.to_numeric(df[config.value], errors="coerce"),
            "lower": pd.to_numeric(df[config.lower], errors="coerce") if config.lower else np.nan,
            "upper": pd.to_numeric(df[config.upper], errors="coerce") if config.upper else np.nan,
        }
    )
    for col in config.slice_by:
        out[col] = (
            df[col].astype(object).map(lambda v: v.item() if isinstance(v, np.generic) else v)
        )
    out = out[out["value"].notna()]
    # Stable order so results never depend on the input row order.
    out = out.sort_values([*config.slice_by, "period", "group"], kind="stable").reset_index(
        drop=True
    )

    meta = DetectMeta(
        slice_by=tuple(config.slice_by),
        info=slice_info_fn(config),
        min_groups_rank=config.min_groups_rank,
        min_groups_outlier=config.min_groups_outlier,
        outlier_z=config.outlier_z,
    )
    return out, meta
