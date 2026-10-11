"""P2.5: catalogue file resolver, generated sources, detector drafting and the weekly
new-dataset step. All network calls go to an httpx.MockTransport; all data is FAKE."""

import json
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest
import yaml

from datatales import pipeline
from datatales.detect.prepare import prepare
from datatales.detectdraft import check_config, describe_columns, draft_detect, trial_run
from datatales.discovery import load_config
from datatales.ingest import catalogue
from datatales.ingest.catalogue import CatalogueError, FileRef, match_file, stable_name
from datatales.newsource import add_next_datasets, file_match_for, heuristic_pick, make_slug
from datatales.sources import DetectConfig, SourceDef, load_sources, set_detect, write_source_file
from tests.memrepo import MemRepo
from tests.test_recipedraft import FakeSDK, client, reply

PAGE = "https://www.gov.uk/government/statistical-data-sets/fake-vehicle-tables"
ASSET = "https://assets.publishing.service.gov.uk/media/abc/veh9999_2026-07.csv"
AREAS = [("E0001", "Avon"), ("E0002", "Brook"), ("E0003", "Cray"), ("E0004", "Dee"),
         ("E0005", "Esk"), ("E0006", "Fal")]  # fmt: skip


def noop(_msg: str) -> None:
    pass


def fake_table() -> pd.DataFrame:
    """FAKE licensed-vehicle counts: 6 areas x 6 years x 2 vehicle types; Fal's cars jump."""
    rows = []
    for i, (code, name) in enumerate(AREAS):
        for year in range(2019, 2025):
            for j, vehicle in enumerate(["Cars", "Vans"]):
                value = 1000 + 150 * i + 40 * j + 10 * (year - 2019) + (7 * i * year) % 13
                if name == "Fal" and vehicle == "Cars" and year == 2024:
                    value *= 1.6
                rows.append([code, name, year, vehicle, round(value)])
    return pd.DataFrame(rows, columns=["area_code", "area", "year", "vehicle", "count"])


def fake_csv() -> bytes:
    return fake_table().to_csv(index=False).encode()


def good_detect() -> dict[str, Any]:
    return {
        "group": "area",
        "group_code": "area_code",
        "period": "year",
        "value": "count",
        "precision_pct": 2,
        "slice_by": ["vehicle"],
        "units": [{"when": {"vehicle": ["Cars", "Vans"]}, "unit": "vehicles"}],
        "labels": [{"when": {"vehicle": ["Cars"]}, "label": "Licensed cars"}],
        "top_n": 20,
    }


# ---- catalogue resolver ----


def test_stable_name_drops_release_dates() -> None:
    assert stable_name("evci5001_2026-07_orcs_uk.ods") == "evci5001_orcs_uk"
    assert stable_name("veh0105.ods") == "veh0105"
    assert stable_name("VEH9999_2026-07.csv") == "veh9999"


def test_match_file_prefers_stable_name_then_title() -> None:
    files = [
        FileRef("Notes", "https://x.gov.uk/notes.csv", "notes.csv", "CSV"),
        FileRef(
            "Vehicles by area", "https://x.gov.uk/veh9999_2026-10.csv", "veh9999_2026-10.csv", "CSV"
        ),  # fmt: skip
    ]
    assert match_file(files, "veh9999", "CSV").filename == "veh9999_2026-10.csv"
    assert match_file(files, "vehicles by area", "CSV").title == "Vehicles by area"
    with pytest.raises(CatalogueError, match="no file matching"):
        match_file(files, "veh0001", "CSV")


def test_only_https_government_urls_are_fetched() -> None:
    for bad in ("http://www.gov.uk/x", "https://evil.example.com/x.csv", "https://gov.uk.evil.io/"):
        with pytest.raises(CatalogueError, match="refusing"):
            catalogue.check_url(bad)
    assert catalogue.check_url("https://www.ons.gov.uk/file?uri=/a/b.xlsx")


def handler(pages: dict[str, Any]):  # noqa: ANN201 - MockTransport handler
    def handle(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url not in pages:
            return httpx.Response(404)
        body = pages[url]
        if isinstance(body, httpx.Response):
            return body
        if isinstance(body, bytes):
            return httpx.Response(200, content=body)
        return httpx.Response(200, json=body)

    return handle


def govuk_pages(attachments: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    api = "https://www.gov.uk/api/content/government/statistical-data-sets/fake-vehicle-tables"
    return {
        api: {
            "details": {
                "attachments": attachments
                if attachments is not None
                else [
                    {
                        "title": "Notes and definitions",
                        "url": "https://assets.publishing.service.gov.uk/n.pdf",
                        "filename": "n.pdf",
                    },
                    {
                        "title": "VEH9999: Licensed vehicles by area (FAKE)",
                        "url": ASSET,
                        "filename": "veh9999_2026-07.csv",
                        "file_size": 4000,
                    },
                ]
            }
        },  # fmt: skip
        ASSET: fake_csv(),
    }


def mock_client(pages: dict[str, Any]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler(pages)))


def test_govuk_page_lists_attachments_and_downloads_the_match() -> None:
    with mock_client(govuk_pages()) as c:
        files = catalogue.list_files("govuk", PAGE, c)
        assert [f.filename for f in files] == ["veh9999_2026-07.csv"]  # the PDF is not data
        raw = catalogue.fetch_catalogue_file("govuk", PAGE, "veh9999", "CSV", c)
    assert raw.content == fake_csv() and raw.filename == "veh9999_2026-07.csv"
    assert raw.meta["page_url"] == PAGE


def test_redirect_off_government_hosts_is_refused() -> None:
    pages = govuk_pages()
    pages[ASSET] = httpx.Response(302, headers={"location": "https://evil.example.com/x.csv"})
    with mock_client(pages) as c, pytest.raises(CatalogueError, match="refusing"):
        catalogue.fetch_catalogue_file("govuk", PAGE, "veh9999", "CSV", c)


# ---- generated source files ----


def test_generated_sources_merge_and_set_detect(isolated_sources_dir: Path) -> None:
    source = SourceDef.model_validate({
        "slug": "fake-vehicles", "name": "Fake", "publisher": "DfT", "url": PAGE,
        "fetch": {"type": "catalogue_file", "kind": "govuk", "page_url": PAGE,
                  "file_match": "veh9999", "format": "CSV"},
    })  # fmt: skip
    write_source_file(source)
    sources = load_sources()
    assert "fake-vehicles" in sources and "ons-wellbeing-local-authority" in sources
    assert sources["fake-vehicles"].detect is None

    assert set_detect("fake-vehicles", good_detect()) is not None
    assert load_sources()["fake-vehicles"].detect.precision_pct == 2
    # never overwritten once set, and hand-made sources are left alone
    assert set_detect("fake-vehicles", good_detect()) is None
    assert set_detect("ons-wellbeing-local-authority", good_detect()) is None

    write_source_file(source.model_copy(update={"slug": "ons-wellbeing-local-authority"}))
    with pytest.raises(ValueError, match="duplicate"):
        load_sources()


# ---- detector settings ----


def test_precision_band_for_exact_counts() -> None:
    frame, _ = prepare(fake_table(), DetectConfig.model_validate(good_detect()))
    row = frame.iloc[0]
    assert row["lower"] == pytest.approx(row["value"] * 0.99)
    assert row["upper"] == pytest.approx(row["value"] * 1.01)


def test_check_config_rejects_bad_settings() -> None:
    table = fake_table()
    no_band = {k: v for k, v in good_detect().items() if k != "precision_pct"}
    cases = [
        (no_band, "precision_pct"),
        # Cars and Vans collide without slice_by
        ({**good_detect(), "slice_by": [], "units": [], "labels": []}, "share the same"),
        ({**good_detect(), "filters": {"vehicle": ["Lorries"]}}, "filter values"),
        ({**good_detect(), "value": "nope"}, "lacks detect columns"),
        (
            {
                **good_detect(),
                "group": "vehicle",
                "group_code": None,
                "slice_by": ["area", "area_code"],
                "units": [],
                "labels": [],
            },
            "at most 2 group",
        ),  # fmt: skip
    ]
    for spec, message in cases:
        with pytest.raises(ValueError, match=message):
            check_config(table, DetectConfig.model_validate(spec))


def test_trial_run_finds_the_jump() -> None:
    trial = trial_run(fake_table(), DetectConfig.model_validate(good_detect()), 3)
    assert trial.passed and trial.candidates > 0
    assert (trial.groups, trial.periods, trial.series) == (6, 6, 2)
    assert any("Fal" in f for f in trial.findings)


def test_describe_columns_lists_values_for_the_prompt() -> None:
    cols = {c["column"]: c for c in describe_columns(fake_table())}
    assert cols["vehicle"]["values"] == ["Cars", "Vans"]
    assert cols["count"]["min"] > 0 and "values" not in cols["count"]


def source_def() -> SourceDef:
    return SourceDef.model_validate({
        "slug": "fake-vehicles", "name": "Fake vehicles", "publisher": "DfT", "url": PAGE,
        "fetch": {"type": "upload"},
    })  # fmt: skip


def test_draft_detect_retries_with_the_reason() -> None:
    repo = MemRepo()
    bad = {**good_detect(), "slice_by": [], "units": [], "labels": []}
    sdk = FakeSDK(reply(bad), reply(good_detect()))
    out = draft_detect(client(repo, sdk), source_def(), fake_table(), log=noop)
    assert out.trial.passed and out.config is not None
    second = sdk.requests[1]["messages"][0]["content"]
    text = json.dumps(second)
    assert "share the same" in text and "<data" in text


def test_draft_detect_rejects_unknown_keys() -> None:
    repo = MemRepo()
    sdk = FakeSDK(reply({**good_detect(), "run": "rm -rf /"}))
    out = draft_detect(client(repo, sdk), source_def(), fake_table(), log=noop)
    assert out.config is None and not out.trial.passed
    assert out.report()["drafted"] is False


# ---- the weekly step ----


def item(**kw: Any) -> dict[str, Any]:
    return {
        "title": "Vehicle licensing statistics (FAKE)",
        "publisher": "Department for Transport",
        "source_url": PAGE,
        "catalogue": "seed",
        "licence": "Open Government Licence v3.0",
        "update_frequency": "quarterly",
        "score": 90,
        "pitch": "Licensed vehicles by area.",
        "status": "accepted",
        "error": None,
        **kw,
    }


def fake_recipe(slug: str) -> dict[str, Any]:
    return {
        "source": slug,
        "version": 1,
        "description": "FAKE vehicle counts, already tidy.",
        "steps": [{"op": "parse_number", "columns": ["count"]}],
        "checks": {
            "expected_columns": ["area_code", "area", "year", "vehicle", "count"],
            "row_count": {"min": 60, "max": 100},
            "not_null": ["area", "count"],
        },
    }


def test_slug_and_file_match() -> None:
    assert make_slug("Vehicle licensing statistics (VEH tables)", set()) == (
        "vehicle-licensing-statistics-veh-tables"
    )
    assert make_slug("A b", {"a-b"}) == "a-b-2"
    ref = FileRef("VEH9999", ASSET, "veh9999_2026-07.csv", "CSV")
    assert file_match_for([ref], ref) == "veh9999"
    files = [FileRef("Notes", "u1", "notes.csv", "CSV"),
             FileRef("Licensed vehicles by local authority", "u2", "t2.csv", "CSV")]  # fmt: skip
    assert heuristic_pick(files, item()) == 1


def test_add_next_dataset_end_to_end(isolated_sources_dir: Path) -> None:
    repo = MemRepo()
    repo.insert_backlog([item(), item(source_url=PAGE + "-two", score=50)])
    for b in repo.list_backlog():
        repo.update_backlog(b["id"], {"status": "accepted"})
    first = repo.list_backlog()[0]["id"]
    slug = "vehicle-licensing-statistics-fake"
    sdk = FakeSDK(reply(fake_recipe(slug)), reply(good_detect()))
    with mock_client(govuk_pages()) as c:
        summary = add_next_datasets(repo, noop, client(repo, sdk), load_config(), client=c)

    assert summary.added == [slug] and summary.failed == []  # only one per week
    path = isolated_sources_dir / f"{slug}.yaml"
    source = load_sources()[slug]
    assert source.fetch.file_match == "veh9999" and source.backlog_id == first
    assert source.detect is None and "Generated by" in path.read_text(encoding="utf-8")
    done = next(b for b in repo.list_backlog() if b["id"] == first)
    assert (done["status"], done["source_slug"]) == ("ingested", slug)

    (recipe,) = repo.recipes.values()
    assert recipe.status == "ready" and recipe.test_report["detect"]["passed"]
    assert recipe.detect_spec["precision_pct"] == 2

    # approval writes the detector settings into the generated file
    pipeline.approve_recipe(repo, slug, 1, "Test Person", isolated_sources_dir / "recipes")
    assert load_sources()[slug].detect.group == "area"
    assert "detect:" in path.read_text(encoding="utf-8")


def test_failed_item_keeps_its_error_and_the_next_is_tried(isolated_sources_dir: Path) -> None:
    repo = MemRepo()
    two = PAGE + "-two"
    repo.insert_backlog([item(score=95), item(source_url=two, score=60)])
    for b in repo.list_backlog():
        repo.update_backlog(b["id"], {"status": "accepted"})
    pages = govuk_pages(attachments=[])  # first page has no data files
    two_api = (
        "https://www.gov.uk/api/content/government/statistical-data-sets/fake-vehicle-tables-two"
    )
    pages[two_api] = govuk_pages()[next(iter(govuk_pages()))]
    with mock_client(pages) as c:
        summary = add_next_datasets(repo, noop, None, load_config(), client=c)

    assert len(summary.added) == 1 and len(summary.failed) == 1
    items = {b["source_url"]: b for b in repo.list_backlog()}
    assert "no CSV, XLSX or ODS" in items[PAGE]["error"] and items[PAGE]["status"] == "accepted"
    assert items[two]["status"] == "ingested"
    assert [p.name for p in isolated_sources_dir.glob("*.yaml")] == [f"{summary.added[0]}.yaml"]
    # nothing is retried while the error stands
    with mock_client(pages) as c:
        again = add_next_datasets(repo, noop, None, load_config(), client=c)
    assert again.added == [] and again.failed == []


def test_zero_per_week_turns_it_off() -> None:
    repo = MemRepo()
    repo.insert_backlog([item()])
    repo.update_backlog(repo.list_backlog()[0]["id"], {"status": "accepted"})
    cfg = load_config().model_copy(update={"new_datasets_per_week": 0})
    assert add_next_datasets(repo, noop, None, cfg).added == []


def test_sources_dir_yaml_is_plain(isolated_sources_dir: Path) -> None:
    write_source_file(source_def())
    data = yaml.safe_load((isolated_sources_dir / "fake-vehicles.yaml").read_text("utf-8"))
    assert data["fetch"] == {"type": "upload"} and "detect" not in data
