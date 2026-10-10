from datatales.rawio import list_sheets, read_grid


def test_csv_cells_stay_text(ons_csv: bytes) -> None:
    grid = read_grid(ons_csv, "x.csv")
    assert grid.shape == (31, 12)
    assert grid.iat[0, 0] == "v4_3"
    assert grid.iat[1, 0] == "7.10"  # not converted to float
    assert grid.iat[12, 1] == "[c]"
    assert grid.iat[12, 0] == ""


def test_semicolon_csv_is_sniffed() -> None:
    grid = read_grid(b"a;b\n1;2\n", "x.csv")
    assert grid.values.tolist() == [["a", "b"], ["1", "2"]]


def test_cp1252_csv_decodes() -> None:
    grid = read_grid("name,price\nTea,£2\n".encode("cp1252"), "x.csv")
    assert grid.iat[1, 1] == "£2"


def test_xlsx_sheets_and_cell_conversion(messy_xlsx: bytes) -> None:
    assert list_sheets(messy_xlsx, "x.xlsx") == ["Cover", "Table 1"]
    grid = read_grid(messy_xlsx, "x.xlsx", "Table 1")
    assert grid.iat[4, 1] == "10"  # int stays integer-looking
    assert grid.iat[4, 2] == "12.5"
    assert grid.iat[4, 3] == "2024-01-31"  # date -> ISO text
    assert grid.iat[1, 0] == ""  # blank row kept as empty strings


def test_empty_file_gives_empty_grid() -> None:
    assert read_grid(b"\n\n", "x.csv").empty
