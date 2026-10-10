import io
import math

import pandas as pd
import pytest

from datatales.clean.runner import StepError, apply_step, run_recipe, to_parquet_bytes
from datatales.clean.schema import parse_recipe_text
from datatales.config import WORKER_DIR

HEAD = "source: s\nversion: 1\ndescription: t\nchecks:\n  expected_columns: [a]\nsteps:\n"


def run(steps: str, content: bytes, filename: str = "x.csv") -> pd.DataFrame:
    return run_recipe(parse_recipe_text(HEAD + steps), content, filename)


def step(yaml_step: str):  # noqa: ANN201
    return parse_recipe_text(HEAD + yaml_step).steps[0]


def test_wellbeing_draft_recipe_on_fake_ons_file(ons_csv: bytes) -> None:
    path = WORKER_DIR / "recipes" / "drafts" / "ons-wellbeing-local-authority.v1.yaml"
    recipe = parse_recipe_text(path.read_text(encoding="utf-8"))
    df = run_recipe(recipe, ons_csv, "fake.csv")
    assert len(df) == 30
    assert list(df.columns) == recipe.checks.expected_columns
    ne = df[
        (df.geo_code == "E12000001") & (df.year_start == 2011) & (df.measure == "Life satisfaction")
    ]
    assert ne.set_index("estimate").loc["Average (mean)", "value"] == 7.1
    # is_reliable is false exactly where ONS marked [u] (fake Fakeshire anxiety rows)
    unreliable = df[~df.is_reliable]
    assert len(unreliable) == 5 and set(unreliable.marking) == {"[u]"}
    assert df[df.marking == "[c]"].is_reliable.all() and df[df.marking.isna()].is_reliable.all()
    assert set(df.geo_level) == {"region", "local_authority"}
    poor = df[
        (df.geography == "Fakeshire")
        & (df.measure == "Life satisfaction")
        & (df.estimate == "Poor")
        & (df.year_start == 2011)
    ]
    assert math.isnan(poor.value.iloc[0]) and poor.marking.iloc[0] == "[c]"


def test_messy_csv_cleaned_end_to_end(messy_csv: bytes) -> None:
    df = run(
        """
  - op: skip_rows
    count: 1
  - op: strip_footnotes
  - op: drop_rows_where
    where: {column: Region, op: eq, value: Region}
  - op: rename_columns
    mapping: {Region: region, Code: code, Share: share, Updated: updated}
  - op: drop_columns
    columns: [updated]
  - op: melt
    id_columns: [region, code, share]
    var_name: year
    value_name: sales
  - op: parse_number
    columns: [sales, share]
  - op: cast
    columns: {year: int}
  - op: sort
    by: [code, year]
""",
        messy_csv,
    )
    assert len(df) == 9  # 3 regions x 3 years; repeated header + footnote dropped
    north = df[df.code == "R1"].set_index("year").sales
    assert north[2019] == 1200.0 and north[2020] == 900.0 and math.isnan(north[2021])
    assert df[df.code == "R3"].share.iloc[0] == 9.25
    assert str(df.year.dtype) == "Int64"


def test_xlsx_with_sheet_title_rows_stacked_header_and_footnote(messy_xlsx: bytes) -> None:
    df = run(
        """
  - op: select_sheet
    sheet: Table 1
  - op: skip_rows
    count: 2
  - op: use_header_row
    row: 0
    rows: 2
  - op: strip_footnotes
  - op: rename_columns
    mapping: {Area: area, Count 2022: c2022, Count 2023: c2023, Released: released}
  - op: parse_number
    columns: [c2022, c2023]
  - op: parse_date
    column: released
    format: yyyy-mm-dd
""",
        messy_xlsx,
        "fake.xlsx",
    )
    assert list(df.columns) == ["area", "c2022", "c2023", "released"]
    assert df.area.tolist() == ["Alpha", "Beta"]
    assert df.c2023.tolist() == [12.5, 7.0]
    assert math.isnan(df.c2022.iloc[1])
    assert df.released.iloc[0] == pd.Timestamp("2024-01-31")


def frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": ["E12000001", "E06000001", "K02000001", "X1"],
            "name": ["North East", "Fakeshire", "United Kingdom", None],
            "n": ["3", "10", "7", "1"],
            "period": ["2011-12", "2012-13", "2013-14", "2014-15"],
        }
    )


@pytest.mark.parametrize(
    ("where", "expected"),
    [
        ("{column: code, op: startswith, value: E}", ["E12000001", "E06000001"]),
        ("{column: name, op: is_null}", ["X1"]),
        ("{column: name, op: not_null}", ["E12000001", "E06000001", "K02000001"]),
        ("{column: n, op: gt, value: 5}", ["E06000001", "K02000001"]),
        ("{column: n, op: le, value: 3}", ["E12000001", "X1"]),
        ("{column: code, op: in, value: [X1, K02000001]}", ["K02000001", "X1"]),
        ("{column: code, op: not_in, value: [X1]}", ["E12000001", "E06000001", "K02000001"]),
        ("{column: name, op: contains, value: shire}", ["E06000001"]),
        ("{column: n, op: eq, value: 10}", ["E06000001"]),
        ("{column: name, op: ne, value: Fakeshire}", ["E12000001", "K02000001", "X1"]),
    ],
)
def test_filter_conditions(where: str, expected: list[str]) -> None:
    out = apply_step(frame(), step(f"  - op: filter\n    where: {where}\n"))
    assert out.code.tolist() == expected


def test_drop_rows_where_is_inverse_of_filter() -> None:
    out = apply_step(
        frame(), step("  - op: drop_rows_where\n    where: {column: name, op: is_null}\n")
    )
    assert out.code.tolist() == ["E12000001", "E06000001", "K02000001"]


def test_classify_prefix_longest_match_and_default() -> None:
    s = step(
        "  - op: classify_prefix\n    column: code\n    into: level\n"
        "    mapping: {E: england, E12: region, K02: uk}\n    default: other\n"
    )
    assert apply_step(frame(), s).level.tolist() == ["region", "england", "uk", "other"]


def test_parse_date_financial_year_and_quarter() -> None:
    fy = apply_step(
        frame(),
        step(
            "  - op: parse_date\n    column: period\n"
            "    format: financial_year_start\n    into: y\n"
        ),
    )
    assert fy.y.tolist() == [2011, 2012, 2013, 2014]
    q = pd.DataFrame({"q": ["2023 Q1", "2023 Q4"]})
    out = apply_step(q, step("  - op: parse_date\n    column: q\n    format: quarter_start\n"))
    assert out.q.tolist() == [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-10-01")]


def test_parse_date_month_names() -> None:
    df = pd.DataFrame({"d": ["Sept 2024", "March 2023", "Jan 2022"]})
    out = apply_step(df, step("  - op: parse_date\n    column: d\n    format: mon yyyy\n"))
    assert out.d.dt.month.tolist() == [9, 3, 1]


def test_parse_date_rejects_wrong_format() -> None:
    df = pd.DataFrame({"d": ["2024-01-01", "01/02/2024"]})
    with pytest.raises(ValueError, match="don't match yyyy-mm-dd"):
        apply_step(df, step("  - op: parse_date\n    column: d\n    format: yyyy-mm-dd\n"))


def test_cast_dedupe_sort() -> None:
    df = pd.DataFrame({"k": ["b", "a", "a"], "v": ["2", "1", "1"], "f": ["yes", "no", "no"]})
    df = apply_step(df, step("  - op: cast\n    columns: {v: int, f: bool}\n"))
    df = apply_step(df, step("  - op: dedupe\n"))
    df = apply_step(df, step("  - op: sort\n    by: [v]\n    descending: true\n"))
    assert df.k.tolist() == ["b", "a"] and df.f.tolist() == [True, False]


def test_parse_number_fails_on_unknown_text_with_examples() -> None:
    df = pd.DataFrame({"v": ["1", "two", "3"]})
    with pytest.raises(ValueError, match=r"column 'v'.*\['two'\]"):
        apply_step(df, step("  - op: parse_number\n    columns: [v]\n"))
    lenient = step("  - op: parse_number\n    columns: [v]\n    on_error: 'null'\n")
    assert math.isnan(apply_step(df, lenient).v.iloc[1])


def test_parse_number_custom_marker() -> None:
    df = pd.DataFrame({"v": ["1", "n/a"]})
    out = apply_step(df, step("  - op: parse_number\n    columns: [v]\n    markers: [n/a]\n"))
    assert out.v.iloc[0] == 1.0 and math.isnan(out.v.iloc[1])


def test_unknown_column_error_names_step_and_lists_columns(ons_csv: bytes) -> None:
    with pytest.raises(StepError, match=r"step 1 \(rename_columns\).*'nope'.*available"):
        run("  - op: rename_columns\n    mapping: {nope: x}\n", ons_csv)


def test_cast_failure_is_reported() -> None:
    with pytest.raises(ValueError, match="column 'v' -> int"):
        apply_step(pd.DataFrame({"v": ["1.5"]}), step("  - op: cast\n    columns: {v: int}\n"))


def test_header_row_beyond_data() -> None:
    with pytest.raises(StepError, match="use_header_row"):
        run("  - op: use_header_row\n    row: 50\n", b"a,b\n1,2\n")


def test_parquet_round_trip(ons_csv: bytes) -> None:
    df = run("  - op: parse_number\n    columns: [v4_3]\n", ons_csv)
    back = pd.read_parquet(io.BytesIO(to_parquet_bytes(df)))
    assert back.shape == df.shape


# ---- whitelist: every allowed step is deliberate and tested ----


def test_whitelisted_ops_are_exactly_these() -> None:
    from typing import get_args

    from datatales.clean.schema import Step

    union = get_args(Step)[0]
    ops = sorted(get_args(m.model_fields["op"].annotation)[0] for m in get_args(union))
    assert ops == sorted(
        [
            "select_sheet", "skip_rows", "use_header_row", "rename_columns", "drop_columns",
            "select_columns", "drop_rows_where", "filter", "strip_footnotes", "parse_number",
            "parse_date", "melt", "cast", "dedupe", "sort", "classify_prefix", "derive_flag",
        ]
    )  # fmt: skip


def lines(*parts: str) -> str:
    return "".join(f"{p}\n" for p in parts)


def test_select_columns_keeps_only_listed_in_order() -> None:
    out = apply_step(frame(), step(lines("  - op: select_columns", "    columns: [period, code]")))
    assert list(out.columns) == ["period", "code"]
    assert out.code.tolist() == frame().code.tolist()


def test_select_columns_unknown_column_fails() -> None:
    s = step(lines("  - op: select_columns", "    columns: [code, missing]"))
    with pytest.raises(ValueError, match="unknown column"):
        apply_step(frame(), s)


def test_classify_prefix_without_default_gives_null() -> None:
    s = step(
        lines(
            "  - op: classify_prefix",
            "    column: code",
            "    into: level",
            "    mapping: {E12: region}",
        )
    )
    level = apply_step(frame(), s).level
    assert level.iloc[0] == "region" and level.iloc[1:].isna().all()


def test_classify_prefix_unknown_column_fails() -> None:
    s = step(
        lines("  - op: classify_prefix", "    column: nope", "    into: x", "    mapping: {E: e}")
    )
    with pytest.raises(ValueError, match="unknown column"):
        apply_step(frame(), s)


def test_derive_flag_true_where_condition_matches_including_nulls() -> None:
    df = pd.DataFrame({"marking": [None, "[u]", "[c]"]})
    s = step(
        lines(
            "  - op: derive_flag",
            "    into: ok",
            '    where: {column: marking, op: ne, value: "[u]"}',
        )
    )
    out = apply_step(df, s)
    assert out.ok.tolist() == [True, False, True] and out.ok.dtype == bool
