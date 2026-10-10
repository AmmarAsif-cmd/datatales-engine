"""Detector tests on small hand-made FAKE frames shaped like the clean wellbeing table."""

from datetime import date

import pandas as pd
import pytest

from datatales.detect import REGISTRY
from datatales.detect.change import biggest_change
from datatales.detect.outlier import outlier
from datatales.detect.prepare import prepare
from datatales.detect.rank import rank_shift
from datatales.detect.run import run_detectors
from datatales.detect.scoring import effect_norm, freshness
from datatales.sources import DetectConfig, get_source

CONFIG = get_source("ons-wellbeing-local-authority").detect
assert CONFIG is not None

LS, MEAN = "Life satisfaction", "Average (mean)"


def row(
    geo: str,
    year: int,
    value: float | None,
    half_ci: float | None = 0.05,
    level: str = "region",
    measure: str = LS,
    estimate: str = MEAN,
    reliable: bool = True,
) -> dict:
    return {
        "geography": geo,
        "geo_code": f"FAKE-{geo}",
        "year_start": year,
        "period": f"{year}-{str(year + 1)[-2:]}",
        "value": value,
        "lower_ci": None if value is None or half_ci is None else value - half_ci,
        "upper_ci": None if value is None or half_ci is None else value + half_ci,
        "measure": measure,
        "estimate": estimate,
        "geo_level": level,
        "is_reliable": reliable,
    }


def frame(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def prepared(rows: list[dict], config: DetectConfig = CONFIG):  # noqa: ANN201
    return prepare(frame(rows), config)


def series(geo: str, values: list[float], start: int = 2011, **kw: object) -> list[dict]:
    return [row(geo, start + i, v, **kw) for i, v in enumerate(values)]  # type: ignore[arg-type]


# ---- registry & prepare ----


def test_registry_has_the_three_phase_one_detectors() -> None:
    assert sorted(REGISTRY) == ["biggest_change", "outlier", "rank_shift"]


def test_prepare_applies_filters_and_drops_nulls() -> None:
    rows = [
        row("A", 2011, 7.0),
        row("B", 2011, 7.0, reliable=False),  # unreliable
        row("C", 2011, None),  # suppressed
        row("D", 2011, 7.0, level="local_authority"),  # out of scope for batch 1
        row("E", 2011, 30.0, estimate="Fair"),  # band not in scope
    ]
    df, meta = prepared(rows)
    assert df.group.tolist() == ["A"]
    assert meta.slice_by == ("measure", "estimate", "geo_level")


def test_polarity_and_units() -> None:
    _, meta = prepared([row("A", 2011, 7.0)])
    anx_mean = meta.info({"measure": "Anxiety", "estimate": MEAN, "geo_level": "uk"})
    assert not anx_mean.higher_is_better and anx_mean.unit == "average score out of 10"
    poor = meta.info({"measure": LS, "estimate": "Poor", "geo_level": "uk"})
    assert not poor.higher_is_better and poor.unit == "% of people"
    assert meta.info({"measure": LS, "estimate": "Very good", "geo_level": "uk"}).higher_is_better


def test_prepare_rejects_missing_columns() -> None:
    with pytest.raises(ValueError, match="lacks detect columns"):
        prepare(frame([row("A", 2011, 7.0)]).drop(columns=["lower_ci"]), CONFIG)


def test_rules_must_use_slice_columns() -> None:
    bad = CONFIG.model_copy(update={"slice_by": ["measure"]})
    with pytest.raises(ValueError, match="slice_by"):
        prepare(frame([row("A", 2011, 7.0)]), bad)


# ---- biggest change ----


def test_biggest_change_picks_largest_significant_rise_and_fall() -> None:
    rows = (
        series("Rise", [7.0, 7.1, 7.5])
        + series("SmallRise", [7.0, 7.05, 7.2])
        + series("Fall", [7.4, 7.3, 7.0])
        + series("WideCI", [6.0, 6.5, 7.0], half_ci=0.6)  # biggest change, but CIs overlap
    )
    found = biggest_change(*prepared(rows))
    by_dir = {f.numbers["direction"]: f.numbers for f in found}
    assert by_dir["rise"]["group"] == "Rise"
    assert by_dir["rise"]["start_value"] == 7.0 and by_dir["rise"]["end_value"] == 7.5
    assert by_dir["rise"]["change"] == 0.5 and by_dir["rise"]["pct_change"] == 7.14
    assert by_dir["rise"]["start_period"] == "2011-12" and by_dir["rise"]["end_period"] == "2013-14"
    assert by_dir["rise"]["start_ci"] == [6.95, 7.05]
    assert by_dir["fall"]["group"] == "Fall" and by_dir["fall"]["change"] == -0.4
    assert all(f.numbers["group"] != "WideCI" for f in found)


def test_change_ignores_groups_missing_a_period() -> None:
    rows = series("Steady", [7.0, 7.0, 7.2]) + [row("Late", 2013, 9.0)]  # no 2011 value
    found = biggest_change(*prepared(rows))
    assert [f.numbers["group"] for f in found] == ["Steady"]
    assert found[0].numbers["groups_compared"] == 1


def test_change_ignores_unreliable_values() -> None:
    rows = series("A", [7.0, 7.1, 7.15]) + [
        row("Shaky", 2011, 5.0, reliable=False),
        row("Shaky", 2013, 9.0, reliable=False),
    ]
    assert all(f.numbers["group"] != "Shaky" for f in biggest_change(*prepared(rows)))


def test_change_without_ci_is_never_significant() -> None:
    rows = series("NoCI", [6.0, 8.0], half_ci=None)
    assert biggest_change(*prepared(rows)) == []


def test_bucking_the_trend_is_more_surprising() -> None:
    rows = series("Up1", [7.0, 7.3]) + series("Up2", [7.0, 7.3]) + series("Down", [7.4, 7.0])
    found = {f.numbers["group"]: f for f in biggest_change(*prepared(rows))}
    assert found["Down"].surprise == 1.0 and found["Up1"].surprise == 0.6


def test_improved_flag_and_points_for_percentage_bands() -> None:
    rows = series("A", [20.0, 15.0], half_ci=1.0, estimate="Poor", measure="Anxiety")
    (f,) = biggest_change(*prepared(rows))
    assert f.numbers["direction"] == "fall" and f.numbers["improved"] is True
    assert f.numbers["change"] == -5.0 and f.numbers["change_unit"] == "percentage points"


# ---- rank shift ----


def test_rank_shift_reports_clear_overtakes() -> None:
    rows = series("Climber", [6.0, 7.6]) + series("Steady", [7.0, 7.0]) + series("Top", [7.8, 7.8])
    (f,) = rank_shift(*prepared(rows))
    n = f.numbers
    assert (n["group"], n["start_rank"], n["end_rank"], n["rank_change"]) == ("Climber", 3, 2, 1)
    assert [o["group"] for o in n["overtook"]] == ["Steady"] and n["overtaken_by"] == []
    assert n["overtook"][0]["start_value"] == 7.0 and n["groups_ranked"] == 3


def test_rank_shift_ignores_overtakes_within_the_noise() -> None:
    rows = series("A", [7.00, 7.06]) + series("B", [7.04, 7.02]) + series("C", [8.0, 8.0])
    assert rank_shift(*prepared(rows)) == []


def test_rank_shift_needs_three_groups_in_both_periods() -> None:
    rows = series("A", [6.0, 8.0]) + series("B", [7.0, 7.0]) + [row("C", 2012, 9.0)]
    assert rank_shift(*prepared(rows)) == []


# ---- outlier ----


def regions(latest: dict[str, float], half_ci: float = 0.05) -> list[dict]:
    return [row(g, 2022, v, half_ci=half_ci) for g, v in latest.items()]


def test_outlier_with_real_gap_is_reported() -> None:
    rows = regions({"A": 7.40, "B": 7.45, "C": 7.50, "D": 7.48, "E": 7.43, "Low": 6.80})
    (f,) = outlier(*prepared(rows))
    n = f.numbers
    assert (n["group"], n["direction"], n["value"], n["nearest_group"]) == (
        "Low",
        "below",
        6.8,
        "A",
    )
    assert n["gap_to_nearest"] == 0.6 and n["groups_compared"] == 6 and n["robust_z"] < -2.5


def test_outlier_overlapping_nearest_is_not_reported() -> None:
    rows = regions({"A": 7.40, "B": 7.45, "C": 7.50, "D": 7.48, "E": 7.43, "Low": 6.80}, 0.4)
    assert outlier(*prepared(rows)) == []


def test_outlier_needs_enough_groups_and_spread() -> None:
    assert outlier(*prepared(regions({"A": 7.0, "B": 7.1, "C": 7.2, "Low": 5.0}))) == []
    assert outlier(*prepared(regions({g: 7.0 for g in "ABCDEF"}))) == []


def test_outlier_uses_latest_period_only() -> None:
    old = [row("Low", 2011, 3.0)]
    rows = old + regions({"A": 7.40, "B": 7.45, "C": 7.50, "D": 7.48, "E": 7.43, "Low": 7.42})
    assert outlier(*prepared(rows)) == []


# ---- slices, scoring, run ----


def test_levels_are_never_compared_with_each_other() -> None:
    rows = regions({"A": 7.40, "B": 7.45, "C": 7.50, "D": 7.48, "E": 7.43})
    rows.append(row("Wales", 2022, 6.0, level="country"))  # would be an outlier among regions
    assert outlier(*prepared(rows)) == []


def test_effect_norm_and_freshness() -> None:
    assert effect_norm(0) == 0 and effect_norm(1) == 0.5 and effect_norm(3) == 0.75
    today = date(2026, 1, 1)
    assert freshness(today, today) == 1.0
    assert freshness(date(2025, 1, 1), today) == pytest.approx(0.8, abs=0.01)
    assert freshness(date(2000, 1, 1), today) == 0.2
    assert freshness(None, today) == 0.5


def test_run_scores_ranks_merges_and_limits() -> None:
    rows = (
        series("Climber", [6.0, 7.6])
        + series("Steady", [7.0, 7.0])
        + series("Top", [7.8, 7.8])
        + series("Faller", [7.5, 7.3])
    )
    config = CONFIG.model_copy(update={"top_n": 2})
    top, total = run_detectors(frame(rows), config, 5, date(2026, 1, 1), date(2026, 1, 1))
    assert total >= 3 and len(top) == 2
    assert top[0].score >= top[1].score
    for f in top:
        parts = f.score_parts
        assert 0 <= f.score <= 1
        expected = parts["effect"] * parts["surprise"] * parts["relatability"] * parts["freshness"]
        assert f.score == pytest.approx(expected, abs=1e-4)
    climber = next(f for f in top if f.numbers["group"] == "Climber")
    related = {r["detector"] for r in climber.numbers.get("related", [])}
    assert {climber.detector} | related == {"biggest_change", "rank_shift"}


def test_run_is_deterministic() -> None:
    rows = series("A", [7.0, 7.5]) + series("B", [7.4, 7.0]) + series("C", [7.2, 7.2])
    a = run_detectors(frame(rows), CONFIG, 5, None, date(2026, 1, 1))[0]
    b = run_detectors(
        frame(rows).sample(frac=1, random_state=1), CONFIG, 5, None, date(2026, 1, 1)
    )[0]
    assert [(f.detector, f.numbers["group"], f.score) for f in a] == [
        (f.detector, f.numbers["group"], f.score) for f in b
    ]
