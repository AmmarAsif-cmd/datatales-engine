from datatales.profile import guess_header_row, profile_file
from datatales.rawio import read_grid


def _cols(profile: dict) -> dict:
    return {c["name"]: c for c in profile["sheets"][0]["columns"]}


def test_ons_like_csv_profile(ons_csv: bytes) -> None:
    p = profile_file(ons_csv, "fake.csv")
    sheet = p["sheets"][0]
    assert sheet["header_row"] == 0 and sheet["rows"] == 30
    cols = _cols(p)
    assert cols["v4_3"]["inferred_type"] == "number"
    assert cols["v4_3"]["null_pct"] == 40.0
    assert cols["Lower limit"]["inferred_type"] == "number_text"
    assert cols["Lower limit"]["flags"]["suppression_markers"] == {"[x]": 5, "[u]": 5, "[c]": 2}
    assert cols["Time"]["inferred_type"] == "date"
    assert cols["Geography"]["inferred_type"] == "text"
    assert cols["Geography"]["distinct"] == 2


def test_messy_csv_flags(messy_csv: bytes) -> None:
    p = profile_file(messy_csv, "fake_messy.csv")
    sheet = p["sheets"][0]
    flags = sheet["flags"]
    assert sheet["header_row"] == 1
    assert flags["title_rows_above_header"]["count"] == 1
    assert flags["header_rows_inside_data"]["count"] == 1
    assert flags["footnote_rows"]["count"] == 1
    assert flags["wide_year_columns"] == ["2019", "2020", "2021"]
    cols = _cols(p)
    assert cols["2019"]["flags"]["numbers_stored_as_text"] == ["currency", "thousands_separator"]
    assert cols["2021"]["flags"]["suppression_markers"] == {"..": 1, "[x]": 1}
    assert cols["Share"]["flags"]["numbers_stored_as_text"] == ["percent"]
    assert cols["Share"]["min"] == 7.0 and cols["Share"]["max"] == 12.5
    assert cols["Updated"]["flags"]["mixed_date_formats"] == {"yyyy-mm-dd": 2, "dd/mm/yyyy": 1}
    # The repeated header row and footnote are excluded from column stats.
    assert sheet["rows"] == 3


def test_xlsx_profile_per_sheet(messy_xlsx: bytes) -> None:
    p = profile_file(messy_xlsx, "fake.xlsx")
    assert p["format"] == "xlsx" and p["sheet_names"] == ["Cover", "Table 1"]
    table = p["sheets"][1]
    assert table["header_row"] == 2
    assert table["flags"]["title_rows_above_header"]["count"] == 2
    assert table["flags"]["multi_row_header"] == {"rows": [2, 3]}
    assert table["flags"]["footnote_rows"]["count"] == 1


def test_header_guess_skips_sparse_title_rows(messy_xlsx: bytes) -> None:
    assert guess_header_row(read_grid(messy_xlsx, "x.xlsx", "Table 1")) == 2


def test_samples_are_truncated() -> None:
    long = "x" * 200
    p = profile_file(f"a,b\n{long},1\nshort,2\n".encode(), "x.csv")
    assert max(len(s) for s in _cols(p)["a"]["samples"]) <= 60
