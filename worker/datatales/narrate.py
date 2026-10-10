"""Narration by copy-paste: build the prompt; parse and validate the pasted JSON reply.

The reply is parsed with json.loads only (never eval), validated against a strict schema
with length limits, and the chart spec is checked against the story's chart data.
"""

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from datatales.errors import UserError
from datatales.verify import flatten_numbers

HEADLINE_MAX_CHARS = 70
SUMMARY_MAX_WORDS = 120
BODY_MAX_WORDS = 400
VIDEO_MAX_WORDS = 90


class NarrationError(UserError):
    pass


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


class ChartSpecOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["line", "bar", "dot"]
    x: str
    y: str
    series: str | None = None
    highlight: str | list[str] | None = None
    annotation: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=120)
    yLabel: str | None = Field(default=None, max_length=80)  # noqa: N815 - matches the site schema


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sentence: str = Field(min_length=5, max_length=600)
    keys: list[str] = Field(min_length=1, max_length=12)


class Narration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    headline: str = Field(min_length=10, max_length=HEADLINE_MAX_CHARS)
    hook: str = Field(min_length=10, max_length=300)
    summary: str = Field(min_length=20)
    body_md: str = Field(min_length=50)
    video_script: str = Field(min_length=10)
    chart_spec: ChartSpecOut
    claims: list[Claim] = Field(min_length=1, max_length=80)

    @field_validator("hook")
    @classmethod
    def _one_sentence(cls, v: str) -> str:
        if len(re.findall(r"[.!?](\s|$)", v.strip())) > 1:
            raise ValueError("must be one sentence")
        return v

    @field_validator("summary")
    @classmethod
    def _summary_len(cls, v: str) -> str:
        if word_count(v) > SUMMARY_MAX_WORDS:
            raise ValueError(f"is {word_count(v)} words; max {SUMMARY_MAX_WORDS}")
        return v

    @field_validator("body_md")
    @classmethod
    def _body_len(cls, v: str) -> str:
        if word_count(v) > BODY_MAX_WORDS:
            raise ValueError(f"is {word_count(v)} words; max {BODY_MAX_WORDS}")
        if re.search(r"<\s*(script|iframe|style)|javascript:", v, re.I):
            raise ValueError("must be plain Markdown (no scripts, iframes or styles)")
        return v

    @field_validator("video_script")
    @classmethod
    def _video_len(cls, v: str) -> str:
        if word_count(v) > VIDEO_MAX_WORDS:
            raise ValueError(f"is {word_count(v)} words; max {VIDEO_MAX_WORDS}")
        return v


def _strip_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*\n(.*)\n```\s*$", text, re.S)
    return m.group(1) if m else text


def parse_narration(text: str, chart_data: list[dict[str, Any]]) -> Narration:
    try:
        data = json.loads(_strip_fences(text))
    except json.JSONDecodeError as exc:
        raise NarrationError(
            f"not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})"
        ) from None
    if not isinstance(data, dict):
        raise NarrationError("reply must be a JSON object")
    try:
        narration = Narration.model_validate(data)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or 'reply'}: {e['msg']}" for e in exc.errors()
        )
        raise NarrationError(f"reply does not match the schema: {problems}") from None

    spec = narration.chart_spec
    columns = set().union(*(row.keys() for row in chart_data)) if chart_data else set()
    for field_name in ("x", "y", "series"):
        col = getattr(spec, field_name)
        if col is not None and col not in columns:
            raise NarrationError(
                f"chart_spec.{field_name} '{col}' is not a chart_data column {sorted(columns)}"
            )
    if spec.highlight is not None:
        wanted = spec.highlight if isinstance(spec.highlight, list) else [spec.highlight]
        key = spec.series or spec.x
        present = {str(row.get(key)) for row in chart_data}
        missing = [h for h in wanted if h not in present]
        if missing:
            raise NarrationError(f"chart_spec.highlight {missing} not found in chart_data['{key}']")
    return narration


OUTPUT_SCHEMA = {
    "headline": f"string, at most {HEADLINE_MAX_CHARS} characters, search-friendly, e.g. "
    '"UK wellbeing by region 2011–2023"',
    "hook": "string, exactly one sentence",
    "summary": f"string, at most {SUMMARY_MAX_WORDS} words",
    "body_md": f"string, Markdown, at most {BODY_MAX_WORDS} words, no headings above ##",
    "video_script": f"string, at most {VIDEO_MAX_WORDS} words, to be read aloud",
    "chart_spec": {
        "type": "line | bar | dot",
        "x": "column name in chart_data",
        "y": "column name in chart_data",
        "series": "column name in chart_data (optional)",
        "highlight": "a value (or list of values) of the series column to highlight",
        "annotation": "short note under the chart, at most 200 characters (optional)",
        "title": "chart title, at most 120 characters (optional)",
        "yLabel": "label for the values, e.g. the unit (optional)",
    },
    "claims": [
        {
            "sentence": "a sentence copied EXACTLY from headline/hook/summary/body_md/"
            "video_script that contains a number (other than a year)",
            "keys": ["the KEYS (from the KEYS table) that each number in it comes from"],
        }
    ],
}

RULES = """\
Rules (follow every one):
1. Use ONLY numbers that appear in NUMBERS below. Do not calculate new numbers (no new
   differences, ratios, averages or percentages) and do not round to a different figure
   than one you could get by rounding a number given. Years must be within the data period.
2. UK English. Plain, calm language for a general reader. No hype words ("shocking",
   "soaring", "plummeting", "crisis").
3. Every change or gap in NUMBERS is statistically clear (confidence intervals do not
   overlap). Say "clearly higher/lower" if useful; never say "significant".
4. Respect polarity: `higher_is_better` and `good_news` say whether a rise is good. For
   anxiety, a LOWER score is better. Band labels for anxiety mean: Poor = high anxiety,
   Fair = medium, Good = low, Very good = very low anxiety. Never write "very good anxiety";
   write "very low anxiety".
5. When `unit` starts with "%", a change in `change` is in percentage points: write
   "5.4 percentage points", never "5.4%". `pct_change` is a relative change.
6. Look at `series[].notable_moves` and `moves_shared_by_most_geographies`. If they show a
   notable dip or rise (for example around 2020-21), mention it briefly with its numbers.
   If they are empty, do not invent one.
7. Describe the shape honestly. The findings compare the first and last year; `series[].points`
   has every year. If the series peaked or bottomed out in between (for example rose, then
   fell back), say so with those numbers instead of implying a steady trend.
8. Say where the data comes from (source name) and the period covered.
9. CLAIMS: for EVERY sentence in any field that contains a number other than a year, add
   one claim {"sentence": <the sentence copied exactly>, "keys": [<KEYS it uses>]}. Each
   number in the sentence must equal (after rounding) one of its keys. If the same sentence
   is used in two fields, one claim covers both. Count words like "four" as numbers.
10. Return ONLY a JSON object with exactly these keys, no Markdown fences, no comments.
"""


def build_prompt(
    numbers: dict[str, Any], chart_data: list[dict[str, Any]], chart_spec: dict[str, Any]
) -> str:
    columns = sorted(set().union(*(row.keys() for row in chart_data))) if chart_data else []
    series_values = sorted({str(row.get("geography")) for row in chart_data})
    return "\n".join(
        [
            "You are writing a short data story for DataTales (datatales.co.uk), a UK site",
            "that turns public data into plain, accurate stories. Python has already done all",
            "the maths; your job is only the words around the numbers below.",
            "",
            RULES,
            "## Output JSON shape",
            json.dumps(OUTPUT_SCHEMA, indent=1, ensure_ascii=False),
            "",
            "## Chart",
            f"chart_data columns: {columns}",
            f"geography values: {series_values}",
            "Suggested chart_spec (adjust only if a different chart is clearer):",
            json.dumps(chart_spec, ensure_ascii=False),
            "",
            "## NUMBERS (context and meaning)",
            json.dumps(numbers, indent=1, ensure_ascii=False),
            "",
            "## KEYS (use these names in claims[].keys)",
            *(f"{k} = {v}" for k, v in flatten_numbers(numbers).items()),
        ]
    )
