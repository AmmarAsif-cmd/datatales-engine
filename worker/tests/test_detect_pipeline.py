"""`detect` step on MemRepo with a FAKE clean table."""

import json
from datetime import date

import pandas as pd
import pytest

from datatales import pipeline
from datatales.clean.runner import to_parquet_bytes
from datatales.repo import now_utc
from datatales.sources import get_source
from tests.memrepo import MemRepo
from tests.test_detect import series

SLUG = "ons-wellbeing-local-authority"


def noop(_msg: str) -> None:
    pass


def make_repo(passed: bool = True) -> tuple[MemRepo, str]:
    repo = MemRepo()
    source_id = repo.upsert_source(get_source(SLUG))
    ds = repo.insert_dataset(source_id, "ons/folder/raw.csv", "a" * 64, now_utc())
    repo.put_object(
        "raw",
        "ons/folder/fetch.json",
        json.dumps({"release_date": "2025-01-01T00:00:00.000Z"}).encode(),
        "application/json",
    )
    clean = pd.DataFrame(
        series("Climber", [6.0, 7.6])
        + series("Steady", [7.0, 7.0])
        + series("Top", [7.8, 7.8])
        + series("Faller", [7.5, 7.3])
    )
    repo.put_object("clean", "c.parquet", to_parquet_bytes(clean), "application/vnd.apache.parquet")
    ct_id = repo.upsert_clean_table(ds.id, "recipe-1", "c.parquet", len(clean), [], passed)
    return repo, ct_id


def test_detect_stores_top_findings_with_numbers() -> None:
    repo, ct_id = make_repo()
    stored = pipeline.detect_clean_table(repo, ct_id, noop, today=date(2026, 1, 1))
    assert 1 <= len(stored) <= 5
    rows = repo.list_findings(ct_id)
    assert [r["id"] for r in rows] == [s["id"] for s in sorted(stored, key=lambda s: -s["score"])]
    top = rows[0]
    assert 0 < top["score"] <= 1
    assert top["numbers"]["score_parts"]["freshness"] == pytest.approx(0.8, abs=0.01)
    assert top["numbers"]["group"] in {"Climber", "Faller"}
    assert "start_value" in top["numbers"] and "end_ci" in top["numbers"]


def test_rerun_needs_replace_and_replaces() -> None:
    repo, ct_id = make_repo()
    first = pipeline.detect_clean_table(repo, ct_id, noop)
    with pytest.raises(pipeline.PipelineError, match="--replace"):
        pipeline.detect_clean_table(repo, ct_id, noop)
    second = pipeline.detect_clean_table(repo, ct_id, noop, replace=True)
    assert len(repo.list_findings(ct_id)) == len(second) == len(first)
    assert {s["id"] for s in second}.isdisjoint({f["id"] for f in first})


def test_findings_used_by_a_story_cannot_be_replaced() -> None:
    repo, ct_id = make_repo()
    stored = pipeline.detect_clean_table(repo, ct_id, noop)
    repo.stories["s1"] = {"finding_ids": [stored[0]["id"]]}
    with pytest.raises(pipeline.PipelineError, match="story"):
        pipeline.detect_clean_table(repo, ct_id, noop, replace=True)


def test_failed_clean_table_is_refused() -> None:
    repo, ct_id = make_repo(passed=False)
    with pytest.raises(pipeline.PipelineError, match="failed its checks"):
        pipeline.detect_clean_table(repo, ct_id, noop)


def test_dry_run_stores_nothing() -> None:
    repo, ct_id = make_repo()
    records = pipeline.detect_clean_table(repo, ct_id, noop, dry_run=True)
    assert records and repo.list_findings(ct_id) == []


def test_release_date_falls_back_to_fetch_date() -> None:
    repo = MemRepo()
    assert pipeline.release_date(repo, "x/raw.csv", "2026-03-04T10:00:00+00:00") == date(2026, 3, 4)
