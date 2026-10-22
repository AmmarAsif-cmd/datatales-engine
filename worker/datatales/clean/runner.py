"""Apply a validated recipe to raw bytes. Each op maps to one fixed function below."""

import io
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from datatales.clean import schema as s
from datatales.profile import FOOTNOTE_START, NOTE_MARKER, clean_number_text
from datatales.rawio import read_grid


class StepError(ValueError):
    def __init__(self, index: int, op: str, message: str) -> None:
        super().__init__(f"step {index + 1} ({op}): {message}")


def _require(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"unknown column(s) {missing}; available: {list(df.columns)}")


def _apply_header(grid: pd.DataFrame, row: int, rows: int) -> pd.DataFrame:
    if row + rows > len(grid):
        raise ValueError(f"header row {row} is beyond the end of the data ({len(grid)} rows)")
    header_block = grid.iloc[row : row + rows]
    names: list[str] = []
    carry = [""] * grid.shape[1]
    for col in range(grid.shape[1]):
        parts = []
        for r in range(rows):
            v = header_block.iat[r, col]
            if r < rows - 1:  # merged cells in upper header rows apply to the right
                carry[col] = v or (carry[col - 1] if col else "")
                v = carry[col]
            if v:
                parts.append(v)
        base = " ".join(parts) or f"column_{col + 1}"
        name, n = base, 2
        while name in names:
            name, n = f"{base}_{n}", n + 1
        names.append(name)
    body = grid.iloc[row + rows :].reset_index(drop=True)
    body.columns = names
    return body


def _is_missing(v: Any) -> bool:
    return v is None or v is pd.NA or (isinstance(v, float) and np.isnan(v))


def _text(series: pd.Series) -> pd.Series:
    """Values as plain text, with missing values as "" (pandas 3 keeps NaN in astype(str))."""
    return series.map(lambda v: "" if _is_missing(v) else str(v)).astype(object)


def _mask(df: pd.DataFrame, cond: s.Condition) -> pd.Series:
    _require(df, [cond.column])
    col = df[cond.column]
    is_null = _text(col).eq("")
    if cond.op == "is_null":
        return is_null
    if cond.op == "not_null":
        return ~is_null
    v = cond.value
    if cond.op in ("in", "not_in"):
        values = v if isinstance(v, list) else [v]
        hit = col.isin(values) | _text(col).isin([str(x) for x in values])
        return hit if cond.op == "in" else ~hit
    if cond.op == "startswith":
        return _text(col).str.startswith(str(v)).astype(bool)
    if cond.op == "contains":
        return _text(col).str.contains(str(v), regex=False).astype(bool)
    if isinstance(v, int | float) and not isinstance(v, bool):
        num = pd.to_numeric(col, errors="coerce")
        ops: dict[str, Callable[[pd.Series], pd.Series]] = {
            "eq": lambda x: x == v, "ne": lambda x: x != v, "gt": lambda x: x > v,
            "ge": lambda x: x >= v, "lt": lambda x: x < v, "le": lambda x: x <= v,
        }  # fmt: skip
        return ops[cond.op](num).fillna(False).astype(bool)
    text = _text(col)
    if cond.op == "eq":
        return text == str(v)
    if cond.op == "ne":
        return text != str(v)
    raise ValueError(f"'{cond.op}' needs a numeric value")


def _parse_number(series: pd.Series, markers: set[str], on_error: str) -> pd.Series:
    bad: list[str] = []

    def one(v: Any) -> float:
        if _is_missing(v):
            return np.nan
        if isinstance(v, int | float):
            return float(v)
        text = str(v).strip()
        if text == "" or text in markers:
            return np.nan
        cleaned, _ = clean_number_text(text)
        try:
            return float(cleaned)
        except ValueError:
            bad.append(text)
            return np.nan

    out = series.map(one).astype("float64")
    if bad and on_error == "fail":
        examples = list(dict.fromkeys(bad))[:5]
        raise ValueError(
            f"{len(bad)} value(s) are not numbers or known markers, e.g. {examples}. "
            "Add them to `markers` or set on_error: null"
        )
    return out


_DATE_FORMATS = {
    "yyyy-mm-dd": "%Y-%m-%d",
    "dd/mm/yyyy": "%d/%m/%Y",
    "d mon yyyy": "%d %b %Y",
    "mon yyyy": "%b %Y",
    "yyyy-mm": "%Y-%m",
    "yyyy": "%Y",
}


def _parse_date(series: pd.Series, fmt: str) -> pd.Series:
    text = _text(series).str.strip()
    blank = text.eq("")
    if fmt == "financial_year_start":
        years = text.str.extract(r"^((?:19|20)\d{2})[-/]\d{2}$")[0]
        bad = text[years.isna() & ~blank]
        if not bad.empty:
            raise ValueError(f"not financial years like 2011-12: {bad.head(3).tolist()}")
        return pd.to_numeric(years).astype("Int64")
    if fmt == "quarter_start":
        parts = text.str.upper().str.extract(r"^((?:19|20)\d{2})\s*Q([1-4])$")
        bad = text[parts[0].isna() & ~blank]
        if not bad.empty:
            raise ValueError(f"not quarters like 2023 Q1: {bad.head(3).tolist()}")
        month = (pd.to_numeric(parts[1]) - 1) * 3 + 1
        return pd.to_datetime(
            {"year": pd.to_numeric(parts[0]), "month": month, "day": 1}, errors="coerce"
        )
    if fmt in ("mon yyyy", "d mon yyyy"):
        text = text.str.replace(r"^(\d{1,2} )?([A-Za-z]{3})[A-Za-z]*", r"\1\2", regex=True)
    parsed = pd.to_datetime(text, format=_DATE_FORMATS[fmt], errors="coerce")
    bad = text[parsed.isna() & text.ne("")]
    if not bad.empty:
        raise ValueError(f"{len(bad)} value(s) don't match {fmt}, e.g. {bad.head(3).tolist()}")
    return parsed


def _cast(series: pd.Series, kind: str) -> pd.Series:
    if kind == "str":
        return series.map(lambda v: None if v is None or v == "" or v is pd.NA else str(v)).astype(
            "string"
        )
    if kind == "float":
        return pd.to_numeric(series.replace("", np.nan), errors="raise").astype("float64")
    if kind == "int":
        num = pd.to_numeric(series.replace("", np.nan), errors="raise")
        if (num.dropna() % 1 != 0).any():
            raise ValueError("non-integer values present")
        return num.astype("Int64")
    if kind == "bool":
        mapping = {"true": True, "false": False, "yes": True, "no": False, "1": True, "0": False}
        lowered = _text(series).str.strip().str.lower()
        unknown = lowered[~lowered.isin([*mapping, "", "nan", "none"])]
        if not unknown.empty:
            raise ValueError(f"not booleans: {unknown.head(3).tolist()}")
        return lowered.map(mapping).astype("boolean")
    return pd.to_datetime(series.replace("", np.nan), errors="raise")


def _strip_footnotes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: NOTE_MARKER.sub("", str(c)).strip())
    text_cols = [
        c for c in df.columns if df[c].dtype == object or pd.api.types.is_string_dtype(df[c])
    ]
    for c in text_cols:
        df[c] = df[c].map(lambda v: NOTE_MARKER.sub("", v).strip() if isinstance(v, str) else v)
    as_text = df.apply(_text)
    filled = as_text.ne("").sum(axis=1)
    first = as_text.apply(lambda r: next((v for v in r if v), ""), axis=1)
    is_note = (filled == 1) & first.map(lambda t: bool(FOOTNOTE_START.match(t)) or len(t) > 60)
    return df[~is_note].reset_index(drop=True)


def apply_step(df: pd.DataFrame, step: Any) -> pd.DataFrame:
    match step:
        case s.RenameColumns(mapping=m):
            _require(df, list(m))
            return df.rename(columns=m)
        case s.DropColumns(columns=cols):
            _require(df, cols)
            return df.drop(columns=cols)
        case s.SelectColumns(columns=cols):
            _require(df, cols)
            return df[cols].copy()
        case s.DropRowsWhere(where=cond):
            return df[~_mask(df, cond)].reset_index(drop=True)
        case s.Filter(where=cond):
            return df[_mask(df, cond)].reset_index(drop=True)
        case s.StripFootnotes():
            return _strip_footnotes(df)
        case s.ParseNumber(columns=cols, markers=markers, on_error=on_error):
            _require(df, cols)
            out = df.copy()
            for c in cols:
                try:
                    out[c] = _parse_number(out[c], set(markers), on_error)
                except ValueError as exc:
                    raise ValueError(f"column '{c}': {exc}") from None
            return out
        case s.ParseDate(column=c, format=fmt, into=into):
            _require(df, [c])
            out = df.copy()
            out[into or c] = _parse_date(out[c], fmt)
            return out
        case s.Melt(id_columns=ids, var_name=var, value_name=val):
            _require(df, ids)
            return df.melt(id_vars=ids, var_name=var, value_name=val)
        case s.Cast(columns=kinds):
            _require(df, list(kinds))
            out = df.copy()
            for c, kind in kinds.items():
                try:
                    out[c] = _cast(out[c], kind)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"column '{c}' -> {kind}: {exc}") from None
            return out
        case s.Dedupe(columns=cols, keep=keep):
            if cols:
                _require(df, cols)
            return df.drop_duplicates(subset=cols, keep=keep).reset_index(drop=True)
        case s.Sort(by=by, descending=desc):
            _require(df, by)
            return df.sort_values(by, ascending=not desc, kind="stable").reset_index(drop=True)
        case s.ClassifyPrefix(column=c, into=into, mapping=m, default=default):
            _require(df, [c])
            prefixes = sorted(m, key=len, reverse=True)  # longest prefix wins

            def label(v: Any) -> str | None:
                text = "" if v is None else str(v)
                return next((m[p] for p in prefixes if text.startswith(p)), default)

            out = df.copy()
            out[into] = df[c].map(label)
            return out
        case s.DeriveFlag(into=into, where=cond):
            out = df.copy()
            out[into] = _mask(df, cond).astype(bool)
            return out
        case s.ShareOfTotal(value=val, of=of, total=total, into=into, keys=keys):
            _require(df, [val, of, *keys])
            is_total = _text(df[of]) == str(total)
            totals = df.loc[is_total, [*keys, val]].rename(columns={val: "__total"})
            if totals.duplicated(keys).any():
                raise ValueError(f"more than one '{total}' row for the same {keys}")
            merged = df.merge(totals, on=keys, how="left", validate="many_to_one")
            num = pd.to_numeric(merged[val], errors="coerce")
            den = pd.to_numeric(merged["__total"], errors="coerce")
            out = df.copy()
            out[into] = (num / den.where(den != 0) * 100).round(6).to_numpy()
            return out
    raise ValueError(f"unsupported step {step!r}")  # pragma: no cover - schema prevents this


def run_recipe(recipe: s.Recipe, content: bytes, filename: str) -> pd.DataFrame:
    steps = list(recipe.steps)
    sheet: str | int | None = None
    skip, header_row, header_rows = 0, 0, 1
    while steps and steps[0].op in s.STRUCTURAL_ORDER:
        st = steps.pop(0)
        if isinstance(st, s.SelectSheet):
            sheet = st.sheet
        elif isinstance(st, s.SkipRows):
            skip = st.count
        elif isinstance(st, s.UseHeaderRow):
            header_row, header_rows = st.row, st.rows

    n_structural = len(recipe.steps) - len(steps)
    try:
        grid = read_grid(content, filename, sheet)
    except (ValueError, KeyError) as exc:
        raise StepError(0, "read", str(exc)) from None
    grid = grid.iloc[skip:].reset_index(drop=True)
    try:
        df = _apply_header(grid, header_row, header_rows)
    except ValueError as exc:
        raise StepError(max(n_structural - 1, 0), "use_header_row", str(exc)) from None
    df = df.replace({"": None})

    for i, step in enumerate(steps, start=n_structural):
        try:
            df = apply_step(df, step)
        except (ValueError, KeyError, TypeError) as exc:
            raise StepError(i, step.op, str(exc)) from None
    return df


def to_parquet_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False, engine="pyarrow")
    return buf.getvalue()
