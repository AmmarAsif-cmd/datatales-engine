"""Read raw CSV/XLSX/ODS bytes into a header-less grid of strings.

Nothing is inferred here: every cell is text ("" for empty), so suppression markers such
as "[c]" or ".." survive for the profiler and the recipe steps to deal with explicitly.
"""

import io
import math
from datetime import date, datetime, time
from typing import Any

import pandas as pd

from datatales.ingest.common import extension

CSV_ENCODINGS = ("utf-8-sig", "cp1252")
# Spreadsheet engines: openpyxl for Excel; calamine (python-calamine, Rust) for OpenDocument,
# which much of UK government statistics uses (DfT, DESNZ, MHCLG). Calamine reads a 17.6 MB
# DfT ODS in ~3 s where odfpy took ~8.5 minutes. Neither evaluates formulas or macros.
SPREADSHEET_ENGINES = {".xlsx": "openpyxl", ".ods": "calamine"}


def list_sheets(content: bytes, filename: str) -> list[str]:
    engine = SPREADSHEET_ENGINES.get(extension(filename))
    if engine is None:
        return []
    with pd.ExcelFile(io.BytesIO(content), engine=engine) as book:
        return [str(s) for s in book.sheet_names]


def _cell_to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time(0) else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _sniff_delimiter(first_line: str) -> str:
    counts = {d: first_line.count(d) for d in (",", ";", "\t", "|")}
    return max(counts, key=lambda d: counts[d]) if max(counts.values()) > 0 else ","


def _tidy(grid: pd.DataFrame) -> pd.DataFrame:
    grid = grid.astype(object).fillna("").map(lambda v: str(v).strip())
    # Drop trailing fully-empty rows and columns (common in spreadsheets).
    non_empty_rows = grid.ne("").any(axis=1)
    non_empty_cols = grid.ne("").any(axis=0)
    if not non_empty_rows.any():
        return pd.DataFrame()
    last_row = non_empty_rows[non_empty_rows].index[-1]
    last_col = non_empty_cols[non_empty_cols].index[-1]
    grid = grid.loc[:last_row, :last_col]
    grid.columns = range(grid.shape[1])
    return grid.reset_index(drop=True)


def read_grids(content: bytes, filename: str, sheets: list[str]) -> dict[str, pd.DataFrame]:
    """Several sheets of one spreadsheet, parsed once (ODS parsing is slow)."""
    engine = SPREADSHEET_ENGINES[extension(filename)]
    raw = pd.read_excel(
        io.BytesIO(content), sheet_name=sheets, header=None, dtype=object, engine=engine
    )
    return {str(name): _tidy(grid.map(_cell_to_str)) for name, grid in raw.items()}


def read_grid(content: bytes, filename: str, sheet: str | int | None = None) -> pd.DataFrame:
    ext = extension(filename)
    if ext == ".csv":
        if sheet not in (None, 0):
            raise ValueError("CSV files have no sheets")
        for enc in CSV_ENCODINGS:
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:  # pragma: no cover - cp1252 decodes almost anything
            raise ValueError("could not decode CSV as UTF-8 or Windows-1252")
        if not text.strip():
            return pd.DataFrame()
        first_line = text.split("\n", 1)[0]
        grid = pd.read_csv(
            io.StringIO(text),
            header=None,
            dtype=str,
            keep_default_na=False,
            sep=_sniff_delimiter(first_line),
            skip_blank_lines=False,
        )
    elif ext in SPREADSHEET_ENGINES:
        grid = pd.read_excel(
            io.BytesIO(content),
            sheet_name=0 if sheet is None else sheet,
            header=None,
            dtype=object,
            engine=SPREADSHEET_ENGINES[ext],
        )
        grid = grid.map(_cell_to_str)
    else:
        raise ValueError(f"unsupported file type: {filename}")

    return _tidy(grid)
