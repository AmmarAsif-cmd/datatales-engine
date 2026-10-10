"""Candidates, story data, narration parsing and the story flow, on FAKE data."""

import json
from datetime import date

import pandas as pd
import pytest

from datatales import pipeline, stories
from datatales.candidates import group_findings, shortlist
from datatales.clean.runner import to_parquet_bytes
from datatales.narrate import NarrationError, build_prompt, parse_narration
from datatales.repo import now_utc
from datatales.sources import get_source
from datatales.storydata import common_moves, notable_moves
from tests.memrepo import MemRepo
from tests.test_detect import row, series

SLUG = "ons-wellbeing-local-authority"


def finding(fid: str, group: str, score: float, good: bool, measure: str = "Happiness") -> dict:
    return {
        "id": fid,
        "detector": "biggest_change",
        "title_hint": f"{group} {measure}",
        "score": score,
        "numbers": {"group": group, "geo_level": "region", "good_news": good, "measure": measure},
    }


# ---- candidates ----


def test_grouping_by_place_level_and_direction_across_measures() -> None:
    fs = [
        finding("a", "North", 0.30, True, "Happiness"),
        finding("b", "North", 0.20, True, "Anxiety"),
        finding("c", "North", 0.25, False, "Worthwhile"),
        finding("d", "South", 0.28, True),
    ]
    cands = group_findings(fs)
    north_good = next(c for c in cands if c.geography == "North" and c.good_news)
    assert north_good.finding_ids == ["a", "b"]
    assert north_good.measures == ["Anxiety", "Happiness"]
    assert north_good.score == pytest.approx(0.30 * 1.15)  # corroborated by a second measure
    assert {(c.geography, c.good_news) for c in cands} == {
        ("North", True),
        ("North", False),
        ("South", True),
    }


def test_shortlist_max_two_per_geography_and_five_total() -> None:
    fs = [finding(f"n{i}", "North", 0.9 - i / 100, i % 2 == 0, f"M{i}") for i in range(6)]
    fs += [finding(f"x{i}", f"Place{i}", 0.5 - i / 100, True) for i in range(6)]
    picks = shortlist(fs)
    assert len(picks) == 5
    assert sum(c.geography == "North" for c in picks) == 2
    assert [c.score for c in picks] == sorted((c.score for c in picks), reverse=True)


# ---- story data ----


def pts(values: list[float], half: float = 0.05) -> list[dict]:
    return [
        {"period": f"{2011 + i}-{str(2012 + i)[-2:]}", "value": v, "ci": [v - half, v + half]}
        for i, v in enumerate(values)
    ]


def test_notable_dip_is_detected_with_recovery() -> None:
    moves = notable_moves(pts([7.5, 7.5, 7.1, 7.4]), typical=0.05)
    assert moves[0]["kind"] == "dip" and moves[0]["period"] == "2013-14"
    assert moves[0]["change"] == -0.4 and moves[0]["next_value"] == 7.4


def test_small_or_noisy_moves_are_not_notable() -> None:
    assert notable_moves(pts([7.5, 7.45, 7.5]), typical=0.05) == []  # too small
    assert notable_moves(pts([7.5, 7.1, 7.5], half=0.5), typical=0.05) == []  # CIs overlap


def test_common_moves_need_most_geographies() -> None:
    rows = series("A", [7.5, 7.0]) + series("B", [7.5, 7.0]) + series("C", [7.5, 7.5])
    from datatales.detect.prepare import prepare

    frame, _ = prepare(pd.DataFrame(rows), get_source(SLUG).detect)
    assert common_moves(frame) == [{"period": "2012-13", "direction": "fall", "groups": 2, "of": 3}]


# ---- narration parsing ----

CHART = [
    {"period": "2011-12", "geography": "North", "value": 7.0},
    {"period": "2012-13", "geography": "North", "value": 7.4},
]


def reply(**over: object) -> str:
    base = {
        "headline": "North wellbeing 2011–2013",
        "hook": "People in North reported higher wellbeing.",
        "summary": "Average scores rose from 7.0 to 7.4 between 2011-12 and 2012-13.",
        "body_md": "Average scores in North rose from 7.0 to 7.4 between 2011-12 and 2012-13. "
        "The data comes from the ONS.",
        "video_script": "North felt better: up from 7.0 to 7.4.",
        "chart_spec": {"type": "line", "x": "period", "y": "value", "series": "geography",
                       "highlight": "North"},
    }  # fmt: skip
    base.update(over)
    return json.dumps(base)


def test_valid_reply_parses_even_inside_code_fences() -> None:
    n = parse_narration("```json\n" + reply() + "\n```", CHART)
    assert n.chart_spec.highlight == "North"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"headline": "x" * 71}, "headline"),
        ({"hook": "One sentence. Two sentences."}, "one sentence"),
        ({"summary": "word " * 121}, "max 120"),
        ({"body_md": "word " * 401}, "max 400"),
        ({"video_script": "word " * 91}, "max 90"),
        ({"body_md": "Fine text <script>alert(1)</script> and more words."}, "plain Markdown"),
        ({"extra": 1}, "Extra inputs"),
        ({"chart_spec": {"type": "pie", "x": "period", "y": "value"}}, "chart_spec.type"),
        ({"chart_spec": {"type": "line", "x": "year", "y": "value"}}, "not a chart_data column"),
        ({"chart_spec": {"type": "line", "x": "period", "y": "value", "series": "geography",
                         "highlight": "South"}}, "highlight"),
    ],
)  # fmt: skip
def test_bad_replies_give_clear_errors(override: dict, message: str) -> None:
    with pytest.raises(NarrationError, match=message):
        parse_narration(reply(**override), CHART)


def test_non_json_reply_is_rejected_without_eval() -> None:
    with pytest.raises(NarrationError, match="not valid JSON"):
        parse_narration("__import__('os').system('echo hacked')", CHART)


def test_prompt_contains_rules_numbers_and_chart() -> None:
    prompt = build_prompt({"x": 1.23}, CHART, {"type": "line"})
    assert "Use ONLY numbers that appear in NUMBERS" in prompt
    assert "very low anxiety" in prompt and "percentage points" in prompt
    assert "2020-21" in prompt and '"x": 1.23' in prompt and "['North']" in prompt


# ---- full story flow on MemRepo ----


@pytest.fixture
def repo_ct() -> tuple[MemRepo, str]:
    repo = MemRepo()
    sid = repo.upsert_source(get_source(SLUG))
    ds = repo.insert_dataset(sid, "f/raw.csv", "c" * 64, now_utc())
    repo.put_object(
        "raw",
        "f/fetch.json",
        json.dumps({"release_date": "2025-06-01T00:00:00Z"}).encode(),
        "application/json",
    )
    rows = (
        series("Riser", [6.0, 6.4, 6.2, 6.9])
        + series("Steady", [7.0, 7.0, 7.0, 7.0])
        + series("Top", [7.8, 7.8, 7.8, 7.8])
        + series("Faller", [7.5, 7.4, 7.3, 7.2])
        + [row("Riser", 2011, 30.0, half_ci=1.0, estimate="Poor")]
        + [row("Riser", 2014, 20.0, half_ci=1.0, estimate="Poor")]
    )
    df = pd.DataFrame(rows)
    repo.put_object("clean", "c.parquet", to_parquet_bytes(df), "application/vnd.apache.parquet")
    ct = repo.upsert_clean_table(ds.id, "r1", "c.parquet", len(df), [], True)
    pipeline.detect_clean_table(repo, ct, lambda _m: None, today=date(2026, 1, 1))
    return repo, ct


def test_story_flow_create_prompt_paste_verify(repo_ct: tuple[MemRepo, str]) -> None:
    repo, ct = repo_ct
    picks = stories.candidates_for(repo, ct)
    assert picks[0].geography == "Riser" and set(picks[0].measures) == {"Life satisfaction"}
    story = stories.create_story(repo, ct, 1)
    assert story["status"] == "draft" and story["verify_status"] == "pending"
    assert {r["geography"] for r in story["chart_data"]} == {"Riser", "Steady", "Top", "Faller"}
    assert len(story["chart_data"]) == 16  # full yearly series, not just endpoints
    s = next(x for x in story["numbers"]["series"] if x["estimate"] == "Average (mean)")
    assert [p["value"] for p in s["points"]] == [6.0, 6.4, 6.2, 6.9]
    assert "NUMBERS" in stories.story_prompt(repo, story["id"])

    good = json.dumps(
        {
            "headline": "Riser life satisfaction 2011–2015",
            "hook": "Life satisfaction in Riser rose from 6.0 to 6.9.",
            "summary": "Average life satisfaction in Riser rose from 6.0 in 2011-12 to 6.9 "
            "in 2014-15, after a dip to 6.2 in 2013-14.",
            "body_md": "Riser rose from 6.0 to 6.9 between 2011-12 and 2014-15. "
            "It dipped to 6.2 in 2013-14 before recovering. Source: ONS.",
            "video_script": "Riser is up from 6.0 to 6.9.",
            "chart_spec": {
                "type": "line",
                "x": "period",
                "y": "value",
                "series": "geography",
                "highlight": "Riser",
            },
        }  # fmt: skip
    )
    saved, report = stories.paste_narration(repo, story["id"], good)
    assert report.passed, report.unmatched
    assert saved["slug"] == "riser-life-satisfaction-2011-2015"
    assert saved["verify_status"] == "passed" and saved["hook"].startswith("Life")

    bad = good.replace("6.9 in 2014-15", "7.3 in 2014-15")
    saved, report = stories.paste_narration(repo, story["id"], bad)
    assert not report.passed and saved["verify_status"] == "failed"
    assert [u["text"] for u in report.unmatched] == ["7.3"]
    with pytest.raises(ValueError, match="verified_before_approval"):
        repo.update_story(story["id"], {"status": "approved"})

    # fix the text by editing, re-verify, then it can be approved
    fixed, report = stories.reverify(
        repo, story["id"], {"summary": saved["summary"].replace("7.3", "6.9")}
    )
    assert report.passed and fixed["verify_status"] == "passed"
    repo.update_story(story["id"], {"status": "approved"})
    with pytest.raises(stories.StoryError, match="approved"):
        stories.paste_narration(repo, story["id"], good)


def test_slugs_stay_unique(repo_ct: tuple[MemRepo, str]) -> None:
    repo, ct = repo_ct
    reply_text = json.dumps(
        {
            "headline": "Riser wellbeing story here",
            "hook": "Riser rose from 6.0 to 6.9.",
            "summary": "Riser rose from 6.0 to 6.9 over the period shown here.",
            "body_md": "Riser rose from 6.0 to 6.9 over the period in the chart. Source: ONS.",
            "video_script": "Riser rose from 6.0 to 6.9.",
            "chart_spec": {"type": "line", "x": "period", "y": "value"},
        }
    )
    a = stories.create_story(repo, ct, 1)
    b = stories.create_story(repo, ct, 1)
    sa, _ = stories.paste_narration(repo, a["id"], reply_text)
    sb, _ = stories.paste_narration(repo, b["id"], reply_text)
    assert (
        sa["slug"] == "riser-wellbeing-story-here" and sb["slug"] == "riser-wellbeing-story-here-2"
    )


def test_candidate_index_out_of_range(repo_ct: tuple[MemRepo, str]) -> None:
    repo, ct = repo_ct
    with pytest.raises(stories.StoryError, match="candidate must be"):
        stories.create_story(repo, ct, 99)
