"""Publishing approved stories and the scheduled pipeline, on MemRepo with FAKE data."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from datatales import pipeline, publish, stories
from datatales.sources import DetectConfig, get_source
from tests.memrepo import MemRepo
from tests.test_stories import repo_ct, riser_reply  # noqa: F401  (fixture re-export)

WHEN = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)


def approved_story(repo: MemRepo, ct: str) -> dict:
    story = stories.create_story(repo, ct, 1)
    stories.paste_narration(repo, story["id"], json.dumps(riser_reply(story)))
    return stories.set_status(repo, story["id"], "approved")


def read_front_matter(path: Path) -> tuple[dict, str]:
    _, head, body = path.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(head), body


def test_write_story_file_matches_site_schema(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
    tmp_path: Path,
) -> None:
    repo, ct = repo_ct
    story = approved_story(repo, ct)
    path = publish.write_story_file(repo, story["id"], tmp_path, WHEN)
    assert path.name == f"{story['slug']}.md"
    fm, body = read_front_matter(path)
    assert fm["title"] == story["headline"] and fm["hook"] == story["hook"]
    assert fm["date"] == "2026-10-10"
    assert fm["recipeVersion"] == "ons-wellbeing-local-authority.v1"
    assert fm["source"]["name"] == "Personal well-being estimates by local authority"
    assert fm["datasetChecksum"] == "c" * 64
    assert fm["period"] == "2011–12 to 2014–15"
    assert 1 <= len(fm["keyNumbers"]) <= 5
    assert {
        "label": "Average life satisfaction score, 2014–15",
        "value": "6.9",
        "note": "From 6 in 2011–12 (average score out of 10)",
    } in fm["keyNumbers"]
    assert {
        "label": "Share with low life satisfaction, 2014–15",
        "value": "20.00%",
        "note": "From 30.00% in 2011–12",
    } in fm["keyNumbers"]
    assert fm["chart_data"] == story["chart_data"] and fm["numbers"] == story["numbers"]
    assert body.strip() == publish.en_dash(story["body_md"].strip())
    # writing the file does not publish: that happens only after the push
    assert repo.get_story(story["id"])["status"] == "approved"


def test_mark_published_sets_status_and_time(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = approved_story(repo, ct)
    done = publish.mark_published(repo, story["id"], WHEN)
    assert done["status"] == "published" and done["published_at"].startswith("2026-10-10T09:00")
    with pytest.raises(publish.PublishError, match="only approved"):
        publish.mark_published(repo, story["id"], WHEN)


def test_only_approved_verified_stories_can_be_written(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
    tmp_path: Path,
) -> None:
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    with pytest.raises(publish.PublishError, match="only approved"):
        publish.write_story_file(repo, story["id"], tmp_path, WHEN)


def test_labels_respect_anxiety_polarity() -> None:
    config = get_source("ons-wellbeing-local-authority").detect
    assert config is not None
    label = publish.label_for
    assert label(config, {"measure": "Anxiety", "estimate": "Very good"}) == (
        "Share with very low anxiety"
    )
    assert label(config, {"measure": "Anxiety", "estimate": "Poor"}) == "Share with high anxiety"
    assert label(config, {"measure": "Happiness", "estimate": "Poor"}) == "Share with low happiness"
    assert label(config, {"measure": "Worthwhile", "estimate": "Average (mean)"}) == (
        "Average worthwhile score"
    )


def test_key_numbers_from_a_place_that_stands_out() -> None:
    config = DetectConfig.model_validate(
        {
            "group": "geography", "period": "quarter_start", "value": "fuel_share_pct",
            "precision_pct": 2, "slice_by": ["fuel_type"],
            "labels": [{"when": {"fuel_type": ["Hybrid electric (petrol)"]},
                        "label": "Share of private cars: petrol hybrids"}],
        }
    )  # fmt: skip
    standout = {  # FAKE outlier finding (shape of detect/outlier.py)
        "body_type": "Cars", "fuel_type": "Hybrid electric (petrol)", "geo_level": "region",
        "group": "Fakeshire", "period": "2026 Q2", "value": 11.07, "direction": "above",
        "nearest_group": "Otherland", "nearest_value": 8.4, "unit": "% of privately kept cars",
    }  # fmt: skip
    cards = publish.key_numbers({"findings": [standout]}, config)
    assert cards == [
        {
            "label": "Share of private cars: petrol hybrids, 2026 Q2",
            "value": "11.07%",
            "note": "Next highest: Otherland, 8.40%",
        }
    ]
    below = {**standout, "direction": "below"}
    assert publish.key_numbers({"findings": [below]}, config)[0]["note"].startswith("Next lowest")
    with pytest.raises(publish.PublishError, match="no findings with values"):
        publish.key_numbers({"findings": [{"group": "Fakeshire"}]}, config)


def test_format_value_and_first_sentence() -> None:
    assert publish.format_value(39.53, "% of people") == "39.53%"
    assert publish.format_value(2.9, "average score out of 10") == "2.9"
    assert publish.format_value(1234.5, "") == "1,234.5"
    assert publish.first_sentence("One. Two.") == "One."
    assert len(publish.first_sentence("x" * 300)) == 200


def test_scheduled_run_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, ons_csv: bytes, tmp_path: Path
) -> None:
    from datatales.ingest.common import RawFile

    repo = MemRepo()
    pipeline.sync_sources(repo)
    draft = Path(
        pipeline.WORKER_DIR / "recipes" / "drafts" / "ons-wellbeing-local-authority.v1.yaml"
    )
    text = draft.read_text(encoding="utf-8").replace(
        "row_count: {min: 90288, max: 110352}", "row_count: {min: 27, max: 33}"
    )
    monkeypatch.setattr(
        pipeline, "fetch_raw", lambda _source, *_a, **_k: RawFile("fake.csv", ons_csv, "x")
    )
    log: list[str] = []
    assert pipeline.run_scheduled(repo, log.append) is True
    assert any("no approved recipe" in m for m in log)

    pipeline.import_recipe(repo, text)
    pipeline.approve_recipe(repo, "ons-wellbeing-local-authority", 1, "Tester", tmp_path)
    log.clear()
    assert pipeline.run_scheduled(repo, log.append) is True
    assert len(repo.clean_tables) == 1  # cleaned once

    log.clear()
    assert pipeline.run_scheduled(repo, log.append) is True
    assert any("Skipped: identical file" in m for m in log)
    assert len(repo.clean_tables) == 1 and len(repo.datasets) == 1
