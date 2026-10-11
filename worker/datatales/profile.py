"""Profile a raw file: per-column stats plus flags for common spreadsheet mess.

The profile is stored on `datasets.profile` and pasted into the recipe prompt, so it is
kept compact (samples are truncated, lists are capped).
"""

import re
from collections import Counter
from typing import Any

import pandas as pd

from datatales.ingest.common import extension
from datatales.rawio import SPREADSHEET_ENGINES, list_sheets, read_grid, read_grids

PROFILE_VERSION = 1
MAX_SHEETS = 25
HEADER_SCAN_ROWS = 30
SAMPLE_COUNT = 5
SAMPLE_CHARS = 60

# Suppression / missing markers used by ONS and other UK publishers.
MARKERS = frozenset(
    {"[x]", "[c]", "[u]", "[w]", "[z]", "[low]", "[d]", "..", ":", "-", "–", "*", "x", "c", "z"}
)
FOOTNOTE_START = re.compile(r"^\s*(\[?note|notes?\b|source\b|footnote|\*|†|\d+\s*[\.)]\s)", re.I)
NOTE_MARKER = re.compile(r"\s*\[note\s*\d+\]", re.I)
NUMBER_RE = re.compile(r"^[-+]?\d+(\.\d+)?$")
YEAR_COL_RE = re.compile(r"^(19|20)\d{2}([-/](\d{2}|\d{4}))?$")

DATE_PATTERNS: dict[str, re.Pattern[str]] = {
    "yyyy-mm-dd": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "dd/mm/yyyy": re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$"),
    "d mon yyyy": re.compile(r"^\d{1,2} [A-Za-z]{3,9} \d{4}$"),
    "mon yyyy": re.compile(r"^[A-Za-z]{3,9} \d{4}$"),
    "yyyy-mm": re.compile(r"^\d{4}-\d{2}$"),
    "yyyy": re.compile(r"^(19|20)\d{2}$"),
    "financial year yyyy-yy": re.compile(r"^(19|20)\d{2}[-/]\d{2}$"),
    "quarter yyyy qn": re.compile(r"^(19|20)\d{2}\s*Q[1-4]$", re.I),
}


def clean_number_text(value: str) -> tuple[str, set[str]]:
    """Strip currency, percent, thousands separators. Returns (text, symbols found)."""
    found: set[str] = set()
    v = value.strip()
    for sym, name in (("£", "currency"), ("$", "currency"), ("€", "currency"), ("%", "percent")):
        if sym in v:
            found.add(name)
            v = v.replace(sym, "")
    if re.search(r"\d,\d{3}", v):
        found.add("thousands_separator")
        v = v.replace(",", "")
    return v.strip(), found


def _shorten(v: str) -> str:
    return v if len(v) <= SAMPLE_CHARS else v[: SAMPLE_CHARS - 1] + "…"


def profile_column(name: str, values: list[str]) -> dict[str, Any]:
    total = len(values)
    nulls = sum(1 for v in values if v == "")
    present = [v for v in values if v != ""]
    markers = Counter(v for v in present if v in MARKERS)
    real = [v for v in present if v not in MARKERS]

    numeric: list[float] = []
    symbols: Counter[str] = Counter()
    for v in real:
        text, found = clean_number_text(v)
        if NUMBER_RE.match(text):
            numeric.append(float(text))
            symbols.update(found)
    numeric_share = len(numeric) / len(real) if real else 0.0

    date_hits: Counter[str] = Counter()
    for v in real:
        for label, pattern in DATE_PATTERNS.items():
            if pattern.match(v):
                date_hits[label] += 1
                break
    date_share = sum(date_hits.values()) / len(real) if real else 0.0

    if not real:
        inferred = "empty" if not markers else "markers_only"
    elif date_share >= 0.9 and not (numeric_share == 1 and set(date_hits) == {"yyyy"}):
        inferred = "date"
    elif numeric_share >= 0.95:
        all_int = all(x.is_integer() for x in numeric)
        if symbols or markers or numeric_share < 1:
            inferred = "number_text"
        else:
            inferred = "integer" if all_int else "number"
    elif date_share >= 0.9:
        inferred = "date"
    else:
        inferred = "text"

    col: dict[str, Any] = {
        "name": name,
        "inferred_type": inferred,
        "null_pct": round(100 * nulls / total, 2) if total else 0.0,
        "distinct": len(set(present)),
        "samples": [_shorten(v) for v in list(dict.fromkeys(real))[:SAMPLE_COUNT]],
    }
    if numeric:
        col["min"], col["max"] = min(numeric), max(numeric)
    flags: dict[str, Any] = {}
    if markers:
        flags["suppression_markers"] = dict(markers.most_common())
    if inferred in ("number_text",) or symbols:
        flags["numbers_stored_as_text"] = sorted(symbols) or ["plain"]
    if 0.5 <= numeric_share < 0.95:
        flags["mostly_numeric_with_text"] = round(numeric_share, 3)
    if inferred == "date" and len(date_hits) > 1:
        flags["mixed_date_formats"] = dict(date_hits.most_common())
    if flags:
        col["flags"] = flags
    return col


def _is_textish(v: str) -> bool:
    return v != "" and not NUMBER_RE.match(clean_number_text(v)[0]) and v not in MARKERS


def _is_headerish(v: str) -> bool:
    """Text, or a year-like heading (wide tables use years as column names)."""
    return _is_textish(v) or bool(YEAR_COL_RE.match(v))


def guess_header_row(grid: pd.DataFrame) -> int:
    """First row (within the first rows) that looks like column headings."""
    scan = grid.head(HEADER_SCAN_ROWS)
    widest = max((int(r.ne("").sum()) for _, r in scan.iterrows()), default=0)
    for i, row in scan.iterrows():
        filled = [v for v in row.tolist() if v != ""]
        if len(filled) < max(2, 0.5 * widest):
            continue
        if sum(_is_headerish(v) for v in filled) / len(filled) >= 0.6:
            return int(i)  # type: ignore[arg-type]
    return 0


def _header_names(row: list[str]) -> list[str]:
    names: list[str] = []
    for i, raw in enumerate(row):
        base = raw or f"column_{i + 1}"
        name, n = base, 2
        while name in names:
            name, n = f"{base}_{n}", n + 1
        names.append(name)
    return names


def profile_grid(grid: pd.DataFrame) -> dict[str, Any]:
    if grid.empty:
        return {"rows": 0, "columns": [], "flags": {"empty": True}}
    header_idx = guess_header_row(grid)
    header = grid.iloc[header_idx].tolist()
    names = _header_names(header)
    data = grid.iloc[header_idx + 1 :].reset_index(drop=True)

    flags: dict[str, Any] = {}
    if header_idx > 0:
        flags["title_rows_above_header"] = {
            "count": header_idx,
            "text": [
                _shorten(" ".join(v for v in grid.iloc[i].tolist() if v))
                for i in range(min(header_idx, 5))
            ],
        }
    # Two stacked header rows: next row is also mostly text and the header has gaps.
    if len(data) > 1:
        nxt = [v for v in data.iloc[0].tolist() if v != ""]
        if nxt and sum(_is_headerish(v) for v in nxt) / len(nxt) >= 0.8 and "" in header:
            flags["multi_row_header"] = {"rows": [header_idx, header_idx + 1]}

    lowered = data.apply(lambda col: col.str.lower())
    is_repeat = lowered.eq([h.strip().lower() for h in header]).all(axis=1)
    repeats = [int(i) for i in is_repeat[is_repeat].index]
    if repeats:
        flags["header_rows_inside_data"] = {"count": len(repeats), "data_rows": repeats[:10]}

    footnotes = []
    single = data.ne("").sum(axis=1) == 1
    for i in single[single].index:
        text = next(v for v in data.iloc[int(i)].tolist() if v != "")
        if FOOTNOTE_START.match(text) or len(text) > 60:
            footnotes.append(int(i))
    if footnotes:
        flags["footnote_rows"] = {"count": len(footnotes), "data_rows": footnotes[:10]}

    year_cols = [h for h in header if YEAR_COL_RE.match(h)]
    if len(year_cols) >= 3:
        flags["wide_year_columns"] = year_cols[:40]
    note_cols = [h for h in header if NOTE_MARKER.search(h)]
    if note_cols:
        flags["note_markers_in_headers"] = note_cols[:20]

    skip = set(repeats) | set(footnotes)
    keep = [i for i in range(len(data)) if i not in skip]
    body = data.iloc[keep] if skip else data
    columns = [
        profile_column(n, body[c].tolist()) for c, n in zip(data.columns, names, strict=True)
    ]
    return {
        "header_row": header_idx,
        "rows": len(body),
        "column_count": len(names),
        "columns": columns,
        "flags": flags,
    }


def profile_file(content: bytes, filename: str) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "profile_version": PROFILE_VERSION,
        "filename": filename,
        "format": extension(filename).lstrip("."),
        "bytes": len(content),
    }
    if f".{profile['format']}" in SPREADSHEET_ENGINES:
        sheets = list_sheets(content, filename)
        profile["sheet_names"] = sheets
        grids = read_grids(content, filename, sheets[:MAX_SHEETS])
        profile["sheets"] = [{"sheet": s, **profile_grid(grids[s])} for s in sheets[:MAX_SHEETS]]
        if len(sheets) > MAX_SHEETS:
            profile["sheets_truncated"] = len(sheets) - MAX_SHEETS
    else:
        profile["sheets"] = [{"sheet": None, **profile_grid(read_grid(content, filename))}]
    return profile
