import pandas as pd

from datatales.clean.checks import CheckResult, all_passed, results_to_json, run_checks
from datatales.clean.schema import Checks


def df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "g": ["A", "A", "A", "B", "B", "B"],
            "band": ["low", "mid", "high", "low", "mid", "high"],
            "pct": [20.0, 30.0, 50.0, 10.0, None, 60.0],
        }
    )


def checks(**kw: object) -> Checks:
    return Checks.model_validate({"expected_columns": ["g", "band", "pct"], **kw})


def by_name(results: list[CheckResult]) -> dict[str, CheckResult]:
    return {r.name: r for r in results}


BANDS = {
    "name": "bands",
    "value": "pct",
    "group_by": ["g"],
    "where": {"band": ["low", "mid", "high"]},
    "group_size": 3,
    "target": 100,
}


def test_all_pass() -> None:
    results = run_checks(
        df(),
        checks(
            row_count={"min": 6, "max": 6},
            not_null=["g", "band"],
            unique=["g", "band"],
            ranges={"pct": {"min": 0, "max": 100}},
            sums=[BANDS],
        ),
    )
    assert all_passed(results), [r for r in results if not r.passed]
    # Group B has a null, so only group A is complete and checked.
    detail = by_name(results)["sum:bands"].detail
    assert "1 complete group(s) checked, 1 skipped" in detail and "max |sum-100| = 0" in detail


def test_failures_are_reported() -> None:
    bad = df().drop(columns=["band"])
    results = by_name(
        run_checks(
            bad,
            checks(
                row_count={"min": 10},
                not_null=["pct"],
                unique=["g"],
                ranges={"pct": {"max": 55}},
            ),
        )
    )
    assert not results["expected_columns"].passed
    assert "band" in results["expected_columns"].detail
    assert not results["row_count"].passed
    assert results["not_null:pct"].detail == "1 null(s)"
    assert not results["unique"].passed
    assert "1 above 55" in results["range:pct"].detail


def test_sum_off_target_fails() -> None:
    d = df()
    d.loc[0, "pct"] = 25.0
    r = run_checks(d, checks(sums=[{**BANDS, "tolerance": 1}]))
    assert not by_name(r)["sum:bands"].passed


def test_sum_with_no_complete_groups_fails() -> None:
    d = df()
    d.loc[0, "pct"] = None
    r = run_checks(d, checks(sums=[BANDS]))
    assert not by_name(r)["sum:bands"].passed


def test_results_serialise() -> None:
    out = results_to_json(run_checks(df(), checks()))
    assert out[0] == {"name": "expected_columns", "passed": True, "detail": "all 3 present"}


def test_partial_groups_are_skipped_not_failed() -> None:
    d = df()[df().index != 4]  # group B now has only 2 of 3 bands
    r = by_name(run_checks(d, checks(sums=[BANDS])))["sum:bands"]
    assert r.passed and "1 skipped" in r.detail


def test_sum_where_on_two_columns() -> None:
    d = pd.concat([df().assign(m="x"), df().assign(m="y", pct=[1.0] * 6)])
    ok = {**BANDS, "where": {"band": ["low", "mid", "high"], "m": ["x"]}, "group_by": ["g", "m"]}
    assert by_name(run_checks(d, checks(sums=[ok])))["sum:bands"].passed
    bad = {**ok, "where": {"band": ["low", "mid", "high"], "m": ["y"]}}
    assert not by_name(run_checks(d, checks(sums=[bad])))["sum:bands"].passed


def test_ranges_where_split_by_category() -> None:
    d = pd.DataFrame({"est": ["mean", "band", "band"], "v": [7.5, 60.0, 30.0]})
    c = Checks.model_validate(
        {
            "expected_columns": ["est", "v"],
            "ranges_where": [
                {"name": "mean", "column": "v", "where": {"est": ["mean"]}, "min": 0, "max": 10},
                {"name": "band", "column": "v", "where": {"est": ["band"]}, "min": 0, "max": 100},
            ],
        }
    )
    assert all_passed(run_checks(d, c))
    d.loc[0, "v"] = 11.0
    results = by_name(run_checks(d, c))
    assert not results["range:mean"].passed and results["range:band"].passed


def test_ranges_where_with_no_matching_rows_fails() -> None:
    c = Checks.model_validate(
        {
            "expected_columns": ["g", "band", "pct"],
            "ranges_where": [{"name": "r", "column": "pct", "where": {"band": ["nope"]}, "max": 1}],
        }
    )
    assert not by_name(run_checks(df(), c))["range:r"].passed
