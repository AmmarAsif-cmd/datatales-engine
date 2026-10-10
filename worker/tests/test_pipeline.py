"""End-to-end pipeline tests on MemRepo with FAKE data: ingest -> profile -> recipe -> clean."""

from pathlib import Path

import pytest

from datatales import pipeline
from datatales.clean.schema import parse_recipe_text
from datatales.config import WORKER_DIR
from datatales.ingest.common import RawFile
from datatales.recipe_prompt import build_recipe_prompt
from datatales.sources import SourceDef, get_source
from tests.memrepo import MemRepo

SLUG = "ons-wellbeing-local-authority"
DRAFT = WORKER_DIR / "recipes" / "drafts" / f"{SLUG}.v1.yaml"


def noop(_msg: str) -> None:
    pass


@pytest.fixture
def repo_with_dataset(ons_csv: bytes) -> tuple[MemRepo, str]:
    repo = MemRepo()
    pipeline.sync_sources(repo)
    raw = RawFile("fake-wellbeing-v4.csv", ons_csv, "https://example.invalid/fake.csv")
    result = pipeline.ingest(repo, get_source(SLUG), raw, noop)
    pipeline.profile_dataset(repo, result.dataset.id, noop)
    return repo, result.dataset.id


def recipe_text(**overrides: object) -> str:
    text = DRAFT.read_text(encoding="utf-8")
    for key, value in overrides.items():
        text = text.replace(f"{key}: ", f"{key}: {value}  # was: ", 1)
    return text


def test_profile_is_stored(repo_with_dataset: tuple[MemRepo, str]) -> None:
    repo, ds_id = repo_with_dataset
    profile = repo.get_dataset(ds_id).profile
    assert profile and profile["sheets"][0]["rows"] == 30


def test_full_flow_import_approve_clean(
    repo_with_dataset: tuple[MemRepo, str], tmp_path: Path
) -> None:
    repo, ds_id = repo_with_dataset
    # The fake file is tiny, so relax the row-count check the real recipe uses.
    text = DRAFT.read_text(encoding="utf-8").replace(
        "row_count: {min: 90288, max: 110352}", "row_count: {min: 27, max: 33}"
    )
    recipe = pipeline.import_recipe(repo, text)
    assert not recipe.approved

    with pytest.raises(pipeline.PipelineError, match="no approved recipe"):
        pipeline.clean_dataset(repo, ds_id, noop)

    approved, path = pipeline.approve_recipe(repo, SLUG, 1, "Test Person", tmp_path)
    assert approved.approved_by == "Test Person"
    assert path == tmp_path / f"{SLUG}.v1.yaml"
    assert "Approved by Test Person" in path.read_text(encoding="utf-8")
    assert parse_recipe_text(path.read_text(encoding="utf-8")).version == 1

    outcome = pipeline.clean_dataset(repo, ds_id, noop)
    assert outcome.passed and outcome.row_count == 30
    df = pipeline.read_parquet(repo.get_object("clean", outcome.parquet_path))
    assert len(df) == 30 and "geo_level" in df.columns
    row = next(iter(repo.clean_tables.values()))
    assert row["checks_passed"] is True and row["row_count"] == 30


def test_failing_checks_write_no_parquet(
    repo_with_dataset: tuple[MemRepo, str], tmp_path: Path
) -> None:
    repo, ds_id = repo_with_dataset
    pipeline.import_recipe(repo, DRAFT.read_text(encoding="utf-8"))  # expects ~100k rows
    pipeline.approve_recipe(repo, SLUG, 1, "Tester", tmp_path)
    outcome = pipeline.clean_dataset(repo, ds_id, noop)
    assert not outcome.passed and outcome.parquet_path is None
    assert not any(bucket == "clean" for bucket, _ in repo.objects)
    row = next(iter(repo.clean_tables.values()))
    assert row["checks_passed"] is False
    failed = [c for c in row["checks"] if not c["passed"]]
    assert [c["name"] for c in failed] == ["row_count"]


def test_recipe_versions_are_immutable(repo_with_dataset: tuple[MemRepo, str]) -> None:
    repo, _ = repo_with_dataset
    text = DRAFT.read_text(encoding="utf-8")
    pipeline.import_recipe(repo, text)
    with pytest.raises(pipeline.PipelineError, match="set version: 2"):
        pipeline.import_recipe(repo, text)


def test_approve_twice_and_without_name(
    repo_with_dataset: tuple[MemRepo, str], tmp_path: Path
) -> None:
    repo, _ = repo_with_dataset
    pipeline.import_recipe(repo, DRAFT.read_text(encoding="utf-8"))
    with pytest.raises(pipeline.PipelineError, match="--by"):
        pipeline.approve_recipe(repo, SLUG, 1, "  ", tmp_path)
    pipeline.approve_recipe(repo, SLUG, 1, "A", tmp_path)
    with pytest.raises(pipeline.PipelineError, match="already approved"):
        pipeline.approve_recipe(repo, SLUG, 1, "B", tmp_path)


def test_recipe_for_unknown_source_rejected(repo_with_dataset: tuple[MemRepo, str]) -> None:
    repo, _ = repo_with_dataset
    text = DRAFT.read_text(encoding="utf-8").replace(f"source: {SLUG}", "source: not-a-source")
    with pytest.raises(KeyError, match="unknown source"):
        pipeline.import_recipe(repo, text)


def test_dry_run_writes_nothing(repo_with_dataset: tuple[MemRepo, str]) -> None:
    repo, ds_id = repo_with_dataset
    before = (dict(repo.objects), dict(repo.recipes), dict(repo.clean_tables))
    df, results = pipeline.dry_run_recipe(repo, DRAFT.read_text(encoding="utf-8"), ds_id)
    assert len(df) == 30 and results
    assert (repo.objects, repo.recipes, repo.clean_tables) == before


def test_upload_source_requires_file() -> None:
    data = get_source(SLUG).model_dump(mode="json") | {"fetch": {"type": "upload"}}
    upload_source = SourceDef.model_validate(data)
    with pytest.raises(pipeline.PipelineError, match="--file"):
        pipeline.fetch_raw(upload_source)
    with pytest.raises(pipeline.PipelineError, match="don't pass --file"):
        pipeline.fetch_raw(get_source(SLUG), "x.csv")


def test_run_job_records_success_and_failure() -> None:
    repo = MemRepo()

    def ok(log: pipeline.JobLog) -> int:
        log("hello")
        return 1

    assert pipeline.run_job(repo, "t", ok) == 1

    def boom(_log: pipeline.JobLog) -> None:
        raise pipeline.PipelineError("nope")

    with pytest.raises(pipeline.PipelineError):
        pipeline.run_job(repo, "t", boom)
    statuses = [(j["status"], j["log"], j["error"]) for j in repo.jobs.values()]
    assert statuses == [("succeeded", "hello", None), ("failed", "", "PipelineError: nope")]


def test_recipe_prompt_contains_everything_needed(repo_with_dataset: tuple[MemRepo, str]) -> None:
    repo, ds_id = repo_with_dataset
    ds = repo.get_dataset(ds_id)
    prompt = build_recipe_prompt(get_source(SLUG), ds.profile or {}, 3, ds_id)
    assert f'`source` must be "{SLUG}". `version` must be 3.' in prompt
    assert "Reply with ONLY the recipe as YAML" in prompt
    assert '"v4_3"' in prompt  # profile included
    assert '"parse_number"' in prompt  # schema included
    assert ds_id in prompt


def test_replace_only_works_on_unapproved(
    repo_with_dataset: tuple[MemRepo, str], tmp_path: Path
) -> None:
    repo, _ = repo_with_dataset
    text = DRAFT.read_text(encoding="utf-8")
    first = pipeline.import_recipe(repo, text)
    changed = text.replace("tolerance: 0.05", "tolerance: 0.04")
    replaced = pipeline.import_recipe(repo, changed, replace=True)
    assert replaced.id == first.id and replaced.version == 1
    assert replaced.spec["checks"]["sums"][0]["tolerance"] == 0.04
    pipeline.approve_recipe(repo, SLUG, 1, "A", tmp_path)
    with pytest.raises(pipeline.PipelineError, match="approved and immutable"):
        pipeline.import_recipe(repo, text, replace=True)
