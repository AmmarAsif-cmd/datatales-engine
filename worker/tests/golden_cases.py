"""Golden test vectors shared by the Python and TypeScript implementations.

The dashboard (Cloudflare Workers, no Python) re-implements the pure text logic in
TypeScript: number extraction, the KEYS table, claim verification, reply validation,
slugs, the story shortlist and the prompt. This module generates expected outputs from the
Python implementation into tests/golden/cases.json. pytest checks the file is current;
dashboard/tests/logic.test.ts checks TypeScript reproduces every case.

Regenerate after changing the logic:  uv run python -m tests.golden_cases --write
Inputs are FAKE except `real_ni_story.json` (a real, published-data story, labelled).
"""

import json
import sys
from pathlib import Path
from typing import Any

from datatales.candidates import shortlist
from datatales.chartfacts import evaluate, facts_for
from datatales.narrate import (
    STORY_REQUEST,
    NarrationError,
    build_prompt,
    narration_data,
    narration_instructions,
    normalise_api_reply,
    parse_narration,
    word_count,
)
from datatales.stories import slugify
from datatales.verify import chart_keys, chart_text, extract_tokens, flatten_numbers, verify_text
from tests.textkit import padded_body

GOLDEN = Path(__file__).parent / "golden"
CASES = GOLDEN / "cases.json"

FAKE_NUMBERS: dict[str, Any] = {
    "data_period": {"first": "2011-12", "last": "2022-23"},
    "findings": [
        {
            "group": "Fakeshire",
            "start_period": "2011-12",
            "end_period": "2022-23",
            "start_value": 34.11,
            "end_value": 39.53,
            "start_ci": [31.96, 36.27],
            "change": 5.42,
            "pct_change": 15.89,
            "start_rank": 4,
            "end_rank": 1,
            "groups_compared": 4,
            "unit": "average score out of 10",
            "median_change": -0.24,
            "good_news": True,
            "tiny": 0.00001,
            "whole": 7.0,
            "half": 34.25,
        }
    ],
    "series": [
        {
            "points": [
                {"period": "2019-20", "value": 40.54, "ci": [39.0, 42.08]},
                {"period": "2020-21", "value": 35.94, "ci": [34.0, 37.88]},
            ],
            "notable_moves": [{"period": "2020-21", "change": -4.6, "kind": "dip"}],
        }
    ],
}

TOKEN_TEXTS = [
    "Northern Ireland rose from 34.11% to 39.5% between 2011-12 and 2022–23.",
    "It climbed from 4th to 1st of four countries, £1,200 and 2.5 times, in 2020 and 2031.",
    "Scores out of 10 fell twice; 1,234.5 people; -0.24; 3x faster; Q1 2026.",
    "A 2011/12 label, 12th place, 99.99%, 0.5 and .5 and 5. Done.",
    "Twelve regions, TWENTY areas, doubled, tripled, treble.",
]

CLAIMED = "The share rose from 34.11% to 39.5%, the most of four areas."
KEYS3 = ["f1.start_value", "f1.end_value", "f1.groups_compared"]

VERIFY_CASES: list[dict[str, Any]] = [
    # rounding boundaries: |value - text| exactly at and just past half a unit
    {"name": "boundary_exact_half_down", "fields": {"body_md": "It was 34.2 then."}},
    {"name": "boundary_exact_half_up", "fields": {"body_md": "It was 34.3 then."}},
    {"name": "boundary_just_past", "fields": {"body_md": "It was 36.0 then."}},
    {"name": "boundary_two_dp", "fields": {"body_md": "Exactly 34.255 or 34.245 or 34.256."}},
    # normalisation used to find claimed sentences
    {
        "name": "markdown_underscores",
        "fields": {"body_md": "The __share__ rose from 34.11% to 39.5%, the most of four areas."},
        "claims": [
            {"sentence": CLAIMED, "keys": ["f1.start_value", "f1.end_value", "f1.groups_compared"]}
        ],
    },
    {
        "name": "smart_quotes_dashes",
        "fields": {"body_md": "Fakeshire’s share – it rose from 34.11% to 39.5%."},
        "claims": [
            {
                "sentence": "Fakeshire's share - it rose from 34.11% to 39.5%.",
                "keys": ["f1.start_value", "f1.end_value"],
            }
        ],
    },  # fmt: skip
    {
        "name": "heading_and_quote_marks",
        "fields": {"body_md": "## Up 5.42 points\n\n> Up 5.42 points"},
        "claims": [{"sentence": "Up 5.42 points", "keys": ["f1.change"]}],
    },
    {"name": "plain_pass", "fields": {"body_md": "Up from 34.1% to 39.5% since 2011."}},
    {"name": "made_up", "fields": {"hook": "The share rose to 41.2% in Fakeshire."}},
    {"name": "misrounded", "fields": {"body_md": "Scores rose by 5.5 points."}},
    {"name": "year_out", "fields": {"body_md": "Back in 2009 it was lower; 2023-24 next."}},
    {"name": "scale_and_tiny", "fields": {"summary": "Out of 10, a 0.00001 change; 7 or 7.0."}},
    {
        "name": "claim_ok",
        "fields": {"body_md": CLAIMED},
        "claims": [{"sentence": CLAIMED, "keys": KEYS3}],
    },
    {
        "name": "claim_mismatch",
        "fields": {"body_md": CLAIMED},
        "claims": [{"sentence": CLAIMED, "keys": ["f1.start_value", "f1.groups_compared"]}],
    },
    {
        "name": "claim_not_found",
        "fields": {"body_md": CLAIMED},
        "claims": [{"sentence": "Something else with 34.11.", "keys": ["f1.start_value"]}],
    },
    {
        "name": "claim_unknown_key",
        "fields": {"body_md": CLAIMED},
        "claims": [{"sentence": CLAIMED, "keys": ["f9.made_up"]}],
    },
    {
        "name": "uncovered",
        "fields": {"body_md": CLAIMED + " It dipped to 35.9 in 2020-21."},
        "claims": [{"sentence": CLAIMED, "keys": KEYS3}],
    },
    {
        "name": "markdown_spacing",
        "fields": {"body_md": "The **share** rose from 34.11%\nto  39.5%, the most of four areas."},
        "claims": [{"sentence": CLAIMED, "keys": KEYS3}],
    },
    {
        "name": "two_fields",
        "fields": {"summary": CLAIMED, "body_md": CLAIMED},
        "claims": [{"sentence": CLAIMED, "keys": KEYS3}],
    },
    {
        "name": "series_keys",
        "fields": {"body_md": "It dipped to 35.94% in 2020-21, a fall of 4.6 points."},
        "claims": [
            {
                "sentence": "It dipped to 35.94% in 2020-21, a fall of 4.6 points.",
                "keys": ["s1.points.2020-21.value", "s1.notable_moves.2020-21.change"],
            }
        ],
    },
]


def _pt(period: str, geo: str, value: float | None, half: float | None = 1.0) -> dict[str, Any]:
    lo = None if value is None or half is None else value - half
    hi = None if value is None or half is None else value + half
    return {"period": period, "geography": geo, "value": value, "lower": lo, "upper": hi}


FAKE_CHART: list[dict[str, Any]] = [
    _pt("2011-12", "North", 30.0),
    _pt("2011-12", "East", 35.0),
    _pt("2011-12", "South", 32.0),
    _pt("2011-12", "West", 28.0),
    _pt("2019-20", "North", 33.0),
    _pt("2020-21", "North", 25.0),
    _pt("2020-21", "East", None),
    _pt("2020-21", "South", 30.0),
    _pt("2020-21", "West", 26.0),
    _pt("2021-22", "North", 40.0, None),
    _pt("2021-22", "East", 30.0),
    _pt("2022-23", "North", 40.0),
    _pt("2022-23", "East", 34.0),
    _pt("2022-23", "South", 31.0),
    _pt("2022-23", "West", 27.5),
]

SPAN = {"start": "2011-12", "end": "2022-23"}
CHART_CHECKS: list[dict[str, Any]] = [
    {"kind": "highest", "group": "North", "period": "2022-23"},
    {"kind": "highest", "group": "East", "period": "2011-12"},
    {"kind": "highest", "group": "North", "period": "2011-12"},
    {"kind": "highest", "group": "North", "period": "2019-20"},
    {"kind": "highest", "group": "North", "period": "2021-22"},
    {"kind": "lowest", "group": "West", "period": "2022-23"},
    {"kind": "lowest", "group": "West", "period": "2011-12"},
    {"kind": "lowest", "group": "North", "period": "2020-21"},
    {"kind": "lowest", "group": "East", "period": "2020-21"},
    {"kind": "only_rise", "group": "North", **SPAN},
    {"kind": "only_fall", "group": "East", **SPAN},
    {"kind": "only_fall", "group": "North", **SPAN},
    {"kind": "only_rise", "group": "North", "start": "2019-20", "end": "2022-23"},
    {"kind": "only_rise", "group": "North", "start": "2020-21", "end": "2022-23"},
    {"kind": "all_fall", "start": "2011-12", "end": "2020-21"},
    {"kind": "all_rise", **SPAN},
    {"kind": "all_fall", **SPAN},
    {"kind": "biggest_rise", "group": "North", **SPAN},
    {"kind": "biggest_fall", "group": "East", **SPAN},
    {"kind": "biggest_fall", "group": "West", **SPAN},
    {"kind": "biggest_fall", "group": "North", "start": "2011-12", "end": "2020-21"},
    {"kind": "biggest_fall", "group": "South", "start": "2011-12", "end": "2020-21"},
    {"kind": "middle", "group": "North"},
    {"kind": "highest", "group": "Nowhere", "period": "2022-23"},
]

_BLANK = {"annotation": "", "title": "T", "yLabel": "", "start": "", "end": "", "period": ""}
NORMALISE_CASES: list[Any] = [
    {
        "headline": "H",
        "chart_spec": {"type": "line", "x": "period", "highlight": ["North"], **_BLANK},
        "more_charts": [
            {"type": "map", "highlight": [], **_BLANK},
            {"type": "slope", "highlight": ["A", "B"], **_BLANK, "start": "2011-12"},
        ],
        "claims": [
            {"sentence": "S", "keys": [], "checks": [
                {"kind": "all_rise", "group": "", "period": "", "start": "a", "end": "b"}]},
            {"sentence": "S2", "keys": ["k"], "checks": []},
        ],
    },
    {"headline": "no charts or claims"},
    ["not", "an", "object"],
]  # fmt: skip

# More rows than CHART_ROWS_MAX: the prompt lists first/last period and the highlight only.
BIG_CHART = [
    {"period": f"20{10 + y}-{11 + y}", "geography": f"Area {a}", "value": 10.0 + a + y / 10,
     "lower": None, "upper": None}
    for a in range(30) for y in range(10)
]  # fmt: skip

CAVEAT_NUMBERS: dict[str, Any] = {
    "data_period": {"first": "2011-12", "last": "2022-23"},
    "caveats": ["Paused after April 2022 to March 2023; a review is due in 2026."],
    "findings": [{"start_value": 30.0, "end_value": 40.0, "change": 10.0, "groups_compared": 4}],
}
ONLY = "North had the only rise, from 30 to 40."
ONLY_CHECK = {"kind": "only_rise", "group": "North", **SPAN}
UP = ["f1.start_value", "f1.end_value"]

RANK_CASES: list[dict[str, Any]] = [
    {
        "name": "rank_ok",
        "fields": {"body_md": ONLY},
        "claims": [{"sentence": ONLY, "keys": UP, "checks": [ONLY_CHECK]}],
    },
    {
        "name": "rank_missing_check",
        "fields": {"body_md": ONLY},
        "claims": [{"sentence": ONLY, "keys": UP}],
    },
    {
        "name": "rank_wrong_kind",
        "fields": {"body_md": "North had the highest rise."},
        "claims": [
            {
                "sentence": "North had the highest rise.",
                "keys": [],
                "checks": [{"kind": "biggest_rise", "group": "North", **SPAN}],
            }
        ],
    },
    {
        "name": "rank_failed",
        "fields": {"headline": "East saw the only fall"},
        "claims": [
            {
                "sentence": "East saw the only fall",
                "checks": [{"kind": "only_fall", "group": "East", **SPAN}],
            }
        ],
    },
    {
        "name": "rank_mismatch_first",
        "fields": {"body_md": "North had the only rise, to 41."},
        "claims": [
            {"sentence": "North had the only rise, to 41.", "keys": UP, "checks": [ONLY_CHECK]}
        ],
    },
    {
        "name": "rank_uncovered",
        "fields": {"body_md": "All areas fell in 2020-21. Overall it was small."},
        "claims": [],
    },
    {
        "name": "rank_words_mixed_case",
        "fields": {"summary": "The LARGEST rise and the Lowest score."},
        "claims": [
            {
                "sentence": "The LARGEST rise and the Lowest score.",
                "checks": [
                    {"kind": "biggest_rise", "group": "North", **SPAN},
                    {"kind": "lowest", "group": "West", "period": "2022-23"},
                ],
            }
        ],
    },
    {
        "name": "caveat_years",
        "fields": {"body_md": "Paused after 2022-23; a review is due in 2026, not 2027."},
        "claims": [],
    },
    {
        "name": "chart_key_ok",
        "fields": {"body_md": "In 2022-23 East was 34.00% (33.00% to 35.00%)."},
        "claims": [
            {
                "sentence": "In 2022-23 East was 34.00% (33.00% to 35.00%).",
                "keys": [
                    "chart.East.2022-23.value",
                    "chart.East.2022-23.lower",
                    "chart.East.2022-23.upper",
                ],
            }
        ],
    },
    {
        "name": "chart_value_wrong_key",
        "fields": {"body_md": "In 2022-23 East was 34.00%."},
        "claims": [
            {"sentence": "In 2022-23 East was 34.00%.", "keys": ["chart.West.2022-23.value"]}
        ],
    },
    {
        "name": "percent_decimals",
        "fields": {"body_md": "North 40% and 40.0% and 40.00%; East 34.000%."},
        "claims": [],
    },
    {
        "name": "chart_text_checked",
        "fields": {"chart_text": "The only area to rise\nScores 0 to 10, North 40.00%"},
        "claims": [
            {
                "sentence": "Scores 0 to 10, North 40.00%",
                "keys": ["chart.North.2022-23.value"],
            }
        ],
    },
]

CHART = [
    {"period": "2011-12", "geography": "North", "value": 7.0},
    {"period": "2012-13", "geography": "North", "value": 7.4},
]


def _reply(**over: Any) -> str:
    base: dict[str, Any] = {
        "headline": "North wellbeing 2011–2013",
        "hook": "People in North reported higher wellbeing.",
        "summary": "Average scores rose from 7.0 to 7.4 between 2011-12 and 2012-13.",
        "body_md": padded_body(
            "Average scores in North rose from 7.0 to 7.4 between 2011-12 and 2012-13. "
            "The data comes from the ONS."
        ),
        "video_script": "North felt better: up from 7.0 to 7.4.",
        "chart_spec": {"type": "line", "x": "period", "y": "value", "series": "geography",
                       "highlight": "North"},
        "claims": [{"sentence": "North felt better: up from 7.0 to 7.4.", "keys": ["a"]}],
    }  # fmt: skip
    base.update(over)
    return json.dumps(base, ensure_ascii=False)


CODED = [
    {"period": p, "geography": g, "code": c, "value": v}
    for p, vals in {"2011-12": (7.0, 6.0), "2012-13": (7.4, 6.1), "2013-14": (7.2, 5.9)}.items()
    for (g, c), v in zip((("North", "E12000001"), ("South", "E12000008")), vals, strict=True)
]
_LINE = {"type": "line", "x": "period", "y": "value", "series": "geography", "highlight": "North"}
SLOPE = {**_LINE, "type": "slope", "title": "First vs last", "start": "2011-12", "end": "2013-14"}
MAP = {**_LINE, "type": "map", "title": "By region", "period": "2013-14"}

NARRATION_CASES: list[dict[str, Any]] = [
    {"name": "valid", "reply": _reply(), "error": None},
    {"name": "fenced", "reply": "```json\n" + _reply() + "\n```", "error": None},
    {"name": "not_json", "reply": "__import__('os')", "error": "not valid JSON"},
    {"name": "array", "reply": "[1, 2]", "error": "JSON object"},
    {"name": "headline_long", "reply": _reply(headline="x" * 71), "error": "headline"},
    {"name": "headline_short", "reply": _reply(headline="short"), "error": "headline"},
    {"name": "hook_two", "reply": _reply(hook="One sentence. Two sentences."), "error": "hook"},
    {"name": "summary_long", "reply": _reply(summary="word " * 121), "error": "summary"},
    {"name": "body_long", "reply": _reply(body_md=padded_body("Long.", 760)), "error": "body_md"},
    {
        "name": "body_short",
        "reply": _reply(
            body_md="## How it compares\n\nx\n\n## What the data can't tell us\n\n" + "word " * 100
        ),
        "error": "body_md",
    },  # noqa: E501
    {"name": "body_no_sections", "reply": _reply(body_md="word " * 520), "error": "sections"},
    {
        "name": "curly_apostrophe_section",
        "reply": _reply(body_md=padded_body("Core.").replace("can't", "can’t")),
        "error": None,
    },  # noqa: E501
    {
        "name": "claim_with_check",
        "reply": _reply(
            claims=[
                {
                    "sentence": "Only North rose here.",
                    "checks": [
                        {
                            "kind": "only_rise",
                            "group": "North",
                            "start": "2011-12",
                            "end": "2012-13",
                        }
                    ],
                }
            ]
        ),
        "error": None,
    },  # noqa: E501
    {
        "name": "check_missing_field",
        "reply": _reply(
            claims=[
                {
                    "sentence": "North was highest here.",
                    "checks": [{"kind": "highest", "group": "North"}],
                }
            ]
        ),
        "error": "claims",
    },  # noqa: E501
    {
        "name": "check_bad_kind",
        "reply": _reply(
            claims=[
                {
                    "sentence": "North was best here.",
                    "checks": [{"kind": "best", "group": "North", "period": "2011-12"}],
                }
            ]
        ),
        "error": "claims",
    },  # noqa: E501
    {"name": "video_long", "reply": _reply(video_script="word " * 91), "error": "video_script"},
    {
        "name": "script_tag",
        "reply": _reply(body_md="Fine text <script>x</script> more words here ok."),
        "error": "body_md",
    },  # noqa: E501
    {"name": "extra_key", "reply": _reply(extra=1), "error": "extra"},
    {
        "name": "missing_key",
        "reply": json.dumps({"headline": "Only a headline here"}),
        "error": "hook",
    },
    {
        "name": "bad_type",
        "reply": _reply(chart_spec={"type": "pie", "x": "period", "y": "value"}),
        "error": "chart_spec",
    },  # noqa: E501
    {
        "name": "bad_column",
        "reply": _reply(chart_spec={"type": "line", "x": "year", "y": "value"}),
        "error": "chart_spec.x",
    },  # noqa: E501
    {
        "name": "bad_highlight",
        "reply": _reply(
            chart_spec={
                "type": "line",
                "x": "period",
                "y": "value",
                "series": "geography",
                "highlight": "South",
            }
        ),
        "error": "highlight",
    },  # noqa: E501
    {"name": "no_claims", "reply": _reply(claims=[]), "error": "claims"},
    {
        "name": "claim_no_keys",
        "reply": _reply(claims=[{"sentence": "Up to 7.4.", "keys": []}]),
        "error": "claims",
    },  # noqa: E501
    {
        "name": "claim_extra",
        "reply": _reply(claims=[{"sentence": "Up to 7.4 here.", "keys": ["a"], "x": 1}]),
        "error": "claims",
    },  # noqa: E501
    {
        "name": "spec_extra_ok_fields",
        "reply": _reply(
            chart_spec={
                "type": "bar",
                "x": "period",
                "y": "value",
                "title": "T",
                "yLabel": "Y",
                "annotation": "A",
            }
        ),
        "error": None,
    },  # noqa: E501
    {
        "name": "explicit_nulls",
        "reply": _reply(
            chart_spec={
                **_LINE,
                "annotation": None,
                "title": None,
                "yLabel": None,
                "start": None,
                "end": None,
                "period": None,
            },
            more_charts=[{**SLOPE, "annotation": None, "yLabel": None, "period": None}],
            claims=[
                {
                    "sentence": "North felt better: up from 7.0 to 7.4.",
                    "keys": ["a"],
                    "checks": [
                        {
                            "kind": "all_rise",
                            "group": None,
                            "period": None,
                            "start": "2011-12",
                            "end": "2013-14",
                        }
                    ],
                }
            ],
        ),
        "chart_data": CODED,
        "error": None,
    },  # fmt: skip
    {
        "name": "null_check_field_still_needed",
        "reply": _reply(
            claims=[
                {
                    "sentence": "North felt better: up from 7.0 to 7.4.",
                    "keys": ["a"],
                    "checks": [
                        {
                            "kind": "only_rise",
                            "group": "North",
                            "period": None,
                            "start": None,
                            "end": "2013-14",
                        }
                    ],
                }
            ],
        ),
        "chart_data": CODED,
        "error": "only_rise needs start",
    },  # fmt: skip
    {
        "name": "three_charts",
        "reply": _reply(more_charts=[SLOPE, MAP]),
        "chart_data": CODED,
        "error": None,
    },
    {
        "name": "four_charts",
        "reply": _reply(more_charts=[SLOPE, MAP, SLOPE]),
        "chart_data": CODED,
        "error": "more_charts",
    },
    {"name": "map_without_codes", "reply": _reply(more_charts=[MAP]), "error": "geography codes"},
    {
        "name": "map_as_main",
        "reply": _reply(chart_spec=MAP),
        "chart_data": CODED,
        "error": None,
    },
    {
        "name": "slope_no_series",
        "reply": _reply(more_charts=[{**SLOPE, "series": None, "highlight": None}]),
        "chart_data": CODED,
        "error": "needs `series`",
    },
    {
        "name": "slope_bad_period",
        "reply": _reply(more_charts=[{**SLOPE, "start": "2009-10"}]),
        "chart_data": CODED,
        "error": "more_charts.0.start",
    },
    {
        "name": "slope_backwards",
        "reply": _reply(more_charts=[{**SLOPE, "start": "2013-14", "end": "2011-12"}]),
        "chart_data": CODED,
        "error": "start must come before end",
    },
    {
        "name": "more_chart_bad_column",
        "reply": _reply(more_charts=[{**SLOPE, "y": "score"}]),
        "chart_data": CODED,
        "error": "more_charts.0.y",
    },
    {
        "name": "more_chart_bad_type",
        "reply": _reply(more_charts=[{**SLOPE, "type": "pie"}]),
        "chart_data": CODED,
        "error": "more_charts.0.type",
    },
]

WORD_TEXTS = [
    "One two three",
    "It's a well-known fact — really!",
    "  -- 'quoted' words’ end ",
    "café naïve 2011-12 £1,200 39.5%",
    "",
]

SLUG_TEXTS = [
    "UK wellbeing by region 2011–2023",
    "Northern Ireland: anxiety falls / happiness rises",
    "Café — naïve “quotes”",
    "   ",
    "x" * 100,
]


def _finding(
    fid: str, group: str, score: float, good: bool, measure: str, level: str = "region"
) -> dict[str, Any]:
    return {
        "id": fid,
        "detector": "biggest_change",
        "title_hint": f"{group} {measure}",
        "score": score,
        "numbers": {"group": group, "geo_level": level, "good_news": good, "measure": measure},
    }


CANDIDATE_FINDINGS = [
    *[_finding(f"n{i}", "North", round(0.9 - i / 100, 4), i % 2 == 0, f"M{i}") for i in range(6)],
    *[_finding(f"x{i}", f"Place{i}", round(0.5 - i / 100, 4), True, "Happiness") for i in range(6)],
    _finding("u1", "United Kingdom", 0.2, True, "Worthwhile", "uk"),
    _finding("u2", "United Kingdom", 0.19, True, "Happiness", "uk"),
    # a table without a `measure` column: the series comes from the slice values
    *[
        {
            **f,
            "numbers": {k: v for k, v in f["numbers"].items() if k != "measure"}
            | {
                "slice_by": ["body_type", "fuel_type", "geo_level"],
                "body_type": "Cars",
                "fuel_type": fuel,
            },
        }
        for f, fuel in (
            (_finding("v1", "Wales", 0.45, True, "x", "country"), "Diesel"),
            (_finding("v2", "Wales", 0.44, True, "x", "country"), "Petrol"),
        )
    ],  # fmt: skip
]


def _jsonable(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=str))


def build() -> dict[str, Any]:
    real = json.loads((GOLDEN / "real_ni_story.json").read_text(encoding="utf-8"))
    real_fields = {
        k: real["reply"][k] for k in ("headline", "hook", "summary", "body_md", "video_script")
    }
    broken_claims = [dict(c) for c in real["reply"]["claims"]]
    for c in broken_claims:
        if c["sentence"].startswith("Average happiness"):
            c["keys"] = ["f3.start_value", "f3.end_value", "f3.scale_max"]  # wrong measure
        if c["sentence"].startswith("Northern Ireland's rise was the biggest"):
            c["checks"] = [{"kind": "biggest_fall", "group": "Northern Ireland", **SPAN}]
    broken_fields = dict(
        real_fields, body_md=real_fields["body_md"] + "\n\nThat is 4.6 points below its peak."
    )

    verify_cases = (
        [{**c, "numbers": FAKE_NUMBERS, "claims": c.get("claims")} for c in VERIFY_CASES]
        + [{**c, "numbers": CAVEAT_NUMBERS, "chart_data": FAKE_CHART} for c in RANK_CASES]
        + [
            {
                "name": "real_ni_story",
                "fields": real_fields,
                "numbers": real["numbers"],
                "claims": real["reply"]["claims"],
                "chart_data": real["chart_data"],
            },
            {
                "name": "real_ni_story_broken",
                "fields": broken_fields,
                "numbers": real["numbers"],
                "claims": broken_claims,
                "chart_data": real["chart_data"],
            },
        ]
    )
    for c in verify_cases:
        c["report"] = verify_text(
            c["fields"], c["numbers"], c["claims"], c.get("chart_data")
        ).to_json()

    narration = []
    for c in NARRATION_CASES:
        try:
            parse_narration(c["reply"], c.get("chart_data", CHART))
            outcome = None
        except NarrationError as exc:
            outcome = str(exc)
        if (outcome is None) != (c["error"] is None) or (outcome and c["error"] not in outcome):
            raise AssertionError(f"narration case {c['name']}: got {outcome!r}")
        narration.append({**c, "chart_data": c.get("chart_data", CHART)})

    picks = shortlist(CANDIDATE_FINDINGS)
    return _jsonable(
        {
            "tokens": [
                {
                    "text": t,
                    "tokens": [
                        {
                            "text": k.text,
                            "value": str(k.value),
                            "decimals": k.decimals,
                            "kind": k.kind,
                            "start": k.start,
                            "end": k.end,
                        }
                        for k in extract_tokens("f", t)
                    ],
                }  # fmt: skip
                for t in TOKEN_TEXTS
            ],
            "flatten": [
                {"numbers": n, "keys": {k: str(v) for k, v in flatten_numbers(n).items()}}
                for n in (FAKE_NUMBERS, real["numbers"])
            ],
            "verify": verify_cases,
            "chartfacts": {
                "chart_data": FAKE_CHART,
                "evaluate": [
                    {"check": c, "result": list(evaluate(c, FAKE_CHART))} for c in CHART_CHECKS
                ],
                "facts_for": {g: facts_for(FAKE_CHART, g) for g in ("North", "East", "Nowhere")},
            },
            "narration": narration,
            "word_count": [{"text": t, "count": word_count(t)} for t in WORD_TEXTS],
            "slugify": [{"text": t, "slug": slugify(t)} for t in SLUG_TEXTS],
            "candidates": {
                "findings": CANDIDATE_FINDINGS,
                "shortlist": [
                    {
                        "geography": c.geography,
                        "geo_level": c.geo_level,
                        "good_news": c.good_news,
                        "finding_ids": c.finding_ids,
                        "measures": c.measures,
                        "score": c.score,
                        "title": c.title,
                    }
                    for c in picks
                ],
            },  # fmt: skip
            "prompt": [
                {
                    "numbers": real["numbers"],
                    "chart_data": real["chart_data"],
                    "chart_spec": real["chart_spec"],
                    "prompt": build_prompt(real["numbers"], real["chart_data"], real["chart_spec"]),
                    "instructions": narration_instructions(),
                    "request": STORY_REQUEST,
                    "data": narration_data(real["numbers"], real["chart_data"], real["chart_spec"]),
                },
                {
                    "numbers": CAVEAT_NUMBERS,
                    "chart_data": BIG_CHART,
                    "chart_spec": {
                        "type": "line",
                        "x": "period",
                        "y": "value",
                        "series": "geography",
                        "highlight": "Area 7",
                    },
                    "prompt": build_prompt(
                        CAVEAT_NUMBERS,
                        BIG_CHART,
                        {
                            "type": "line",
                            "x": "period",
                            "y": "value",
                            "series": "geography",
                            "highlight": "Area 7",
                        },
                    ),
                    "instructions": narration_instructions(),
                    "request": STORY_REQUEST,
                    "data": narration_data(
                        CAVEAT_NUMBERS,
                        BIG_CHART,
                        {
                            "type": "line",
                            "x": "period",
                            "y": "value",
                            "series": "geography",
                            "highlight": "Area 7",
                        },
                    ),
                },
            ],  # fmt: skip
            "normalise": [{"reply": r, "out": normalise_api_reply(r)} for r in NORMALISE_CASES],
            "chart_keys": {k: str(v) for k, v in chart_keys(FAKE_CHART).items()},
            "chart_text": [
                {"spec": spec, "text": chart_text(spec)}
                for spec in (
                    {"title": "A", "annotation": "B", "more_charts": [{"title": "C"}, {}]},
                    {"type": "line"},
                    {},
                )
            ],
        }
    )


def render() -> str:
    return json.dumps(build(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    if "--write" in sys.argv:
        CASES.write_text(render(), encoding="utf-8", newline="\n")
        print(f"wrote {CASES}")
    else:
        print(render())
