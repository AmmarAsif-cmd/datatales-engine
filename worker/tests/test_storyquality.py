"""Story quality: chart facts, peaks, rank-word checks, refresh/revise, display dashes."""

import json
from pathlib import Path

import pytest

from datatales import publish, stories
from datatales.chartfacts import evaluate, facts_for
from datatales.narrate import NarrationError, parse_narration
from datatales.storydata import peak_info
from datatales.verify import verify_text
from tests.golden_cases import CHART as GOLDEN_CHART
from tests.golden_cases import _reply
from tests.memrepo import MemRepo
from tests.test_publish import WHEN, approved_story, read_front_matter
from tests.test_stories import repo_ct, riser_reply  # noqa: F401  (fixture re-export)
from tests.textkit import padded_body

CHART = [
    {"period": p, "geography": g, "value": v, "lower": v - 0.5, "upper": v + 0.5}
    for p, vals in {"2011-12": (5.0, 7.0, 6.2), "2014-15": (8.0, 6.2, 5.0)}.items()
    for g, v in zip(("A", "B", "C"), vals, strict=True)
]
SPAN = {"start": "2011-12", "end": "2014-15"}


# ---- chart facts ----


@pytest.mark.parametrize(
    ("check", "ok"),
    [
        ({"kind": "only_rise", "group": "A", **SPAN}, True),
        ({"kind": "biggest_rise", "group": "A", **SPAN}, True),
        ({"kind": "only_fall", "group": "B", **SPAN}, False),  # C fell too
        ({"kind": "biggest_fall", "group": "B", **SPAN}, False),  # tie with C: not biggest
        ({"kind": "highest", "group": "A", "period": "2014-15"}, True),
        ({"kind": "lowest", "group": "A", "period": "2011-12"}, True),
        ({"kind": "lowest", "group": "C", "period": "2014-15"}, True),
        ({"kind": "all_fall", **SPAN}, False),
    ],
)
def test_evaluate(check: dict, ok: bool) -> None:
    assert evaluate(check, CHART)[0] is ok


def test_overlapping_cis_do_not_support_highest() -> None:
    close = [dict(r, upper=r["value"] + 2, lower=r["value"] - 2) for r in CHART]
    ok, detail = evaluate({"kind": "highest", "group": "A", "period": "2014-15"}, close)
    assert not ok and "not clearly apart" in detail


def test_facts_for_lists_supported_framings() -> None:
    facts = facts_for(CHART, "A")
    assert (facts["start"], facts["end"], facts["groups_compared"]) == ("2011-12", "2014-15", 3)
    assert (facts["groups_rising"], facts["groups_falling"]) == (1, 2)
    kinds = [c["kind"] for c in facts["supported_checks"]]
    assert kinds == ["highest", "only_rise", "biggest_rise"]
    assert facts_for(CHART[:3], "A") == {}  # one period: nothing to compare


# ---- peaks ----


def _pts(values: list[float], half: float = 0.5) -> list[dict]:
    return [
        {"period": f"{2011 + i}-{12 + i}", "value": v, "ci": [v - half, v + half]}
        for i, v in enumerate(values)
    ]


def test_peak_info_flags_latest_well_below_peak() -> None:
    info = peak_info(_pts([34.1, 47.0, 39.5]), typical=1.5)
    assert info["peak_period"] == "2012-13" and info["peak_value"] == 47.0
    assert info["latest_below_peak_by"] == 7.5 and info["latest_well_below_peak"] is True
    assert info["low_value"] == 34.1 and info["latest_is_peak"] is False


def test_peak_info_needs_clear_and_large_gap() -> None:
    assert peak_info(_pts([5.0, 6.0, 5.8]), typical=1.0)["latest_well_below_peak"] is False
    assert peak_info(_pts([5.0, 9.0, 6.0], half=2.0), 1.0)["latest_well_below_peak"] is False
    assert peak_info(_pts([5.0, 6.0]), typical=0.1)["latest_is_peak"] is True
    assert peak_info([], 1.0) == {}


# ---- rank words in stories ----


def test_rank_word_needs_a_passing_check() -> None:
    nums = {"data_period": {"first": "2011-12", "last": "2014-15"}, "findings": []}
    text = "A was the only area to rise."
    no_check = verify_text({"body_md": text}, nums, [{"sentence": text}], CHART)
    assert no_check.claims[0]["status"] == "assertion_missing" and not no_check.passed
    good = [{"sentence": text, "checks": [{"kind": "only_rise", "group": "A", **SPAN}]}]
    assert verify_text({"body_md": text}, nums, good, CHART).passed
    wrong = [{"sentence": text, "checks": [{"kind": "only_rise", "group": "B", **SPAN}]}]
    report = verify_text({"body_md": text}, nums, wrong, CHART)
    assert report.claims[0]["status"] == "assertion_failed"
    assert report.claims[0]["checks"][0]["ok"] is False
    loose = verify_text({"body_md": "Highest of all."}, nums, [], CHART)
    assert [u["text"] for u in loose.uncovered] == ["Highest", "all"]


def test_years_in_caveats_are_allowed() -> None:
    nums = {"data_period": {"first": "2011-12", "last": "2014-15"}, "caveats": ["Due 2026."]}
    assert verify_text({"body_md": "A review is due in 2026."}, nums).passed
    assert not verify_text({"body_md": "A review is due in 2027."}, nums).passed


def test_narration_needs_sections_and_length() -> None:
    base = json.loads(_reply())
    with pytest.raises(NarrationError, match="must be 450 to 750"):
        parse_narration(json.dumps({**base, "body_md": "word " * 100}), GOLDEN_CHART)
    with pytest.raises(NarrationError, match="How it compares"):
        parse_narration(json.dumps({**base, "body_md": "word " * 500}), GOLDEN_CHART)
    check = {"kind": "only_rise", "group": "A"}  # no start/end
    claims = [{"sentence": "x", "checks": [check]}]
    with pytest.raises(NarrationError, match="start"):
        parse_narration(
            json.dumps({**base, "body_md": padded_body("x"), "claims": claims}), GOLDEN_CHART
        )


# ---- refresh, revise, slug ----


def test_story_numbers_carry_caveats_peaks_and_chart_facts(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
) -> None:
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    nums = story["numbers"]
    assert any("paused" in c for c in nums["caveats"])
    assert nums["chart_facts"]["group"] == "Riser"
    assert all("peak" in s for s in nums["series"])
    assert "only_rise" in stories.story_prompt(repo, story["id"])


def test_revise_published_story_keeps_slug_and_date(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
    tmp_path: Path,
) -> None:
    repo, ct = repo_ct
    story = approved_story(repo, ct)
    publish.write_story_file(repo, story["id"], tmp_path, WHEN.replace(year=2025))
    publish.mark_published(repo, story["id"], WHEN)

    with pytest.raises(stories.StoryError, match="approved"):
        stories.refresh_story(repo, approved_story(repo, ct)["id"])
    fresh = stories.refresh_story(repo, story["id"])
    assert fresh["status"] == "draft" and fresh["published_at"] is None
    assert fresh["verify_status"] == "pending" and fresh["slug"] == story["slug"]

    reply = riser_reply(fresh, headline="A completely new headline for Riser")
    saved, report = stories.paste_narration(repo, story["id"], json.dumps(reply))
    assert report.passed and saved["slug"] == story["slug"]  # URL never changes
    stories.set_status(repo, story["id"], "approved")
    path = publish.write_story_file(repo, story["id"], tmp_path, WHEN)
    fm, _ = read_front_matter(path)
    assert (fm["date"], fm["updated"]) == ("2025-10-10", "2026-10-10")
    assert fm["title"] == "A completely new headline for Riser"


def test_published_story_can_be_moved_back_to_draft(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
) -> None:
    repo, ct = repo_ct
    story = approved_story(repo, ct)
    publish.mark_published(repo, story["id"], WHEN)
    back = stories.set_status(repo, story["id"], "draft")
    assert back["status"] == "draft" and back["published_at"] is None
    with pytest.raises(stories.StoryError):
        stories.set_status(repo, story["id"], "published")


# ---- display ----


@pytest.mark.parametrize(
    ("text", "out"),
    [
        ("2011-12 to 2022-23", "2011–12 to 2022–23"),
        ("In 2020-21, scores fell.", "In 2020–21, scores fell."),
        ("s1.points.2020-21.value", "s1.points.2020-21.value"),
        ("2011-2015 and 2011-123", "2011-2015 and 2011-123"),
    ],
)
def test_en_dash(text: str, out: str) -> None:
    assert publish.en_dash(text) == out


def test_first_published_reads_existing_date(tmp_path: Path) -> None:
    path = tmp_path / "s.md"
    assert publish.first_published(path) is None
    path.write_text("---\ntitle: x\ndate: 2025-01-02\n---\n\nBody\n", encoding="utf-8")
    assert publish.first_published(path) == "2025-01-02"
