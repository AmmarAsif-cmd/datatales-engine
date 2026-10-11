"""Shared fixtures. All data is FAKE (see tests/fixtures/README.md)."""

import io
from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def ons_csv() -> bytes:
    return (FIXTURES / "fake_ons_wellbeing.csv").read_bytes()


@pytest.fixture
def messy_csv() -> bytes:
    return (FIXTURES / "fake_messy.csv").read_bytes()


@pytest.fixture
def messy_xlsx() -> bytes:
    """FAKE workbook: cover sheet, then a table with a title, two header rows and a footnote."""
    wb = Workbook()
    cover = wb.active
    cover.title = "Cover"
    cover.append(["FAKE workbook for tests"])
    ws = wb.create_sheet("Table 1")
    ws.append(["Table 1: Invented counts by area [note 1]"])
    ws.append([])
    ws.append(["Area", "Count", None, "Released"])
    ws.append([None, "2022", "2023", None])
    ws.append(["Alpha", 10, 12.5, date(2024, 1, 31)])
    ws.append(["Beta", "[c]", 7, date(2024, 1, 31)])
    ws.append(["Source: made up for testing only"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def isolated_sources_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Generated sources (worker/sources.d) are left out of every test, so tests never see
    (or fetch) real backlog sources; tests that need some write them here."""
    folder = tmp_path / "sources.d"
    monkeypatch.setattr("datatales.sources.SOURCES_DIR", folder)
    return folder
