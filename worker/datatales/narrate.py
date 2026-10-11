"""Narration by copy-paste: build the prompt; parse and validate the pasted JSON reply.

The reply is parsed with json.loads only (never eval), validated against a strict schema
with length limits, and the chart spec is checked against the story's chart data.
"""

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from datatales.chartfacts import CHECK_KINDS
from datatales.errors import UserError
from datatales.verify import flatten_numbers

HEADLINE_MAX_CHARS = 70
SUMMARY_MAX_WORDS = 120
BODY_MIN_WORDS = 450  # the prompt asks for 500-700; a little slack either side
BODY_MAX_WORDS = 750
VIDEO_MAX_WORDS = 90
REQUIRED_SECTIONS = ("How it compares", "What the data can't tell us")


class NarrationError(UserError):
    pass


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


def has_section(body: str, title: str) -> bool:
    """A '## Title' (or ###) heading; straight or curly apostrophes both count."""
    norm = title.lower().replace("'", "['’]")
    return re.search(rf"^#{{2,3}}\s*{norm}\s*$", body, re.I | re.M) is not None


MAX_CHARTS = 3  # the main chart plus up to two more
CHART_TYPES = ("line", "bar", "dot", "slope", "map")


class ChartSpecOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["line", "bar", "dot", "slope", "map"]
    x: str
    y: str
    series: str | None = None
    highlight: str | list[str] | None = None
    annotation: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=120)
    yLabel: str | None = Field(default=None, max_length=80)  # noqa: N815 - matches the site schema
    start: str | None = None  # slope: first period (default: the first in chart_data)
    end: str | None = None  # slope: last period (default: the last)
    period: str | None = None  # map: the period shown (default: the last)


class Check(BaseModel):
    """A rank/exclusivity claim checked against chart_data (see chartfacts.py)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: Literal[
        "highest", "lowest", "only_rise", "only_fall",
        "all_rise", "all_fall", "biggest_rise", "biggest_fall",
    ]  # fmt: skip
    group: str | None = None
    period: str | None = None
    start: str | None = None
    end: str | None = None

    @model_validator(mode="after")
    def _fields_for_kind(self) -> "Check":
        needs = ["period"] if self.kind in ("highest", "lowest") else ["start", "end"]
        if self.kind != "all_rise" and self.kind != "all_fall":
            needs.append("group")
        missing = [f for f in needs if not getattr(self, f)]
        if missing:
            raise ValueError(f"{self.kind} needs {', '.join(missing)}")
        return self


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    sentence: str = Field(min_length=5, max_length=600)
    keys: list[str] = Field(default_factory=list, max_length=12)
    checks: list[Check] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def _keys_or_checks(self) -> "Claim":
        if not self.keys and not self.checks:
            raise ValueError("needs at least one key or check")
        return self


class Narration(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    headline: str = Field(min_length=10, max_length=HEADLINE_MAX_CHARS)
    hook: str = Field(min_length=10, max_length=300)
    summary: str = Field(min_length=20)
    body_md: str = Field(min_length=50)
    video_script: str = Field(min_length=10)
    chart_spec: ChartSpecOut
    more_charts: list[ChartSpecOut] = Field(default_factory=list, max_length=MAX_CHARTS - 1)
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
        n = word_count(v)
        if n > BODY_MAX_WORDS or n < BODY_MIN_WORDS:
            raise ValueError(f"is {n} words; must be {BODY_MIN_WORDS} to {BODY_MAX_WORDS}")
        if re.search(r"<\s*(script|iframe|style)|javascript:", v, re.I):
            raise ValueError("must be plain Markdown (no scripts, iframes or styles)")
        missing = [s for s in REQUIRED_SECTIONS if not has_section(v, s)]
        if missing:
            raise ValueError(f"needs '## ' sections: {', '.join(missing)}")
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

    columns = set().union(*(row.keys() for row in chart_data)) if chart_data else set()
    for i, spec in enumerate([narration.chart_spec, *narration.more_charts]):
        check_chart(spec, chart_data, columns, "chart_spec" if i == 0 else f"more_charts.{i - 1}")
    return narration


def check_chart(
    spec: ChartSpecOut, chart_data: list[dict[str, Any]], columns: set[str], name: str
) -> None:
    for field_name in ("x", "y", "series"):
        col = getattr(spec, field_name)
        if col is not None and col not in columns:
            raise NarrationError(
                f"{name}.{field_name} '{col}' is not a chart_data column {sorted(columns)}"
            )
    if spec.highlight is not None:
        wanted = spec.highlight if isinstance(spec.highlight, list) else [spec.highlight]
        key = spec.series or spec.x
        present = {str(row.get(key)) for row in chart_data}
        missing = [h for h in wanted if h not in present]
        if missing:
            raise NarrationError(f"{name}.highlight {missing} not found in chart_data['{key}']")
    if spec.type in ("slope", "map") and not spec.series:
        raise NarrationError(f"{name}: a {spec.type} chart needs `series` (the geography column)")
    if spec.type == "map" and "code" not in columns:
        raise NarrationError(f"{name}: a map needs geography codes (chart_data has no 'code')")
    periods = {str(row.get(spec.x)) for row in chart_data}
    for field_name in ("start", "end", "period"):
        value = getattr(spec, field_name)
        if value is not None and value not in periods:
            raise NarrationError(f"{name}.{field_name} '{value}' is not a value of '{spec.x}'")
    if spec.start is not None and spec.end is not None and not spec.start < spec.end:
        raise NarrationError(f"{name}: start must come before end")


OUTPUT_SCHEMA = {
    "headline": f"string, at most {HEADLINE_MAX_CHARS} characters: the single strongest finding "
    'as a statement, e.g. "Northern Ireland is the only UK nation where low anxiety rose"',
    "hook": "string, exactly one sentence",
    "summary": f"string, at most {SUMMARY_MAX_WORDS} words",
    "body_md": "string, Markdown, 500 to 700 words, with the sections "
    '"## How it compares" and "## What the data can\'t tell us"; no headings above ##',
    "video_script": f"string, at most {VIDEO_MAX_WORDS} words, to be read aloud",
    "chart_spec": {
        "type": "line | bar | dot | slope | map",
        "x": "column name in chart_data",
        "y": "column name in chart_data",
        "series": "column name in chart_data (optional)",
        "highlight": "a value (or list of values) of the series column to highlight",
        "annotation": "short note under the chart, at most 200 characters (optional)",
        "title": "chart title, at most 120 characters (optional)",
        "yLabel": "label for the values, e.g. the unit (optional)",
        "start": "slope only: first period to compare (optional, default first)",
        "end": "slope only: last period to compare (optional, default last)",
        "period": "map only: the period to map (optional, default last)",
    },
    "more_charts": ["up to 2 more chart_spec objects (optional), e.g. a slope and a map"],
    "claims": [
        {
            "sentence": "a sentence copied EXACTLY from headline/hook/summary/body_md/"
            "video_script that contains a number (other than a year) or a rank word",
            "keys": ["the KEYS (from the KEYS table) that each number in it comes from"],
            "checks": [
                {
                    "kind": "only_rise | only_fall | all_rise | all_fall | highest | lowest "
                    "| biggest_rise | biggest_fall",
                    "group": "geography (not for all_rise/all_fall)",
                    "start": "first period (rise/fall kinds)",
                    "end": "last period (rise/fall kinds)",
                    "period": "period (highest/lowest)",
                }
            ],
        }
    ],
}

RULES = """\
Rules (follow every one):
1. Use ONLY numbers that appear in NUMBERS or CHART DATA below. Do not calculate new
   numbers (no new differences, ratios, averages or percentages) and do not round to a
   different figure than one you could get by rounding a number given. Years must be within
   the data period (years mentioned in `caveats` are also allowed).
2. UK English. Plain, calm language for a general reader. No hype words ("shocking",
   "soaring", "plummeting", "crisis"). Write financial years with an en dash: 2011–12.
3. HEADLINE: state the single strongest finding as a statement with its key fact, e.g.
   "Northern Ireland is the only UK nation where low anxiety rose". Never a topic label
   such as "Wellbeing in Northern Ireland 2011–2023".
4. FRAMING: `chart_facts.supported_checks` lists what the chart data clearly supports
   (only_rise, only_fall, all_rise, all_fall, highest, lowest, biggest_rise, biggest_fall).
   When one is supported, prefer that framing ("the only nation where…", "the biggest rise
   of the four…"), or rank-change framing from `rank_change`/`overtook` in the findings.
5. Every change or gap in NUMBERS is statistically clear (confidence intervals do not
   overlap). Say "clearly higher/lower" if useful; never say "significant".
6. Respect polarity: `higher_is_better` and `good_news` say whether a rise is good. For
   anxiety, a LOWER score is better. Band labels for anxiety mean: Poor = high anxiety,
   Fair = medium, Good = low, Very good = very low anxiety. Never write "very good anxiety";
   write "very low anxiety".
7. When `unit` starts with "%", a change in `change` is in percentage points: write
   "5.42 percentage points", never "5.42%". `pct_change` is a relative change. Write every
   percentage with exactly 2 decimals: 38.50%, 5.00% (never 38.5% or 39%).
8. SHAPE: `series[].points` has every year and `series[].peak` the peak and low point. If
   `latest_well_below_peak` is true, say plainly that the latest value is well below the
   peak, with both numbers and years. Mention notable dips or rises from `notable_moves` and
   `moves_shared_by_most_geographies` (for example 2020–21) briefly, with their numbers. If
   they are empty, do not invent one.
9. STRUCTURE of body_md (500 to 700 words): first the main finding and its shape; then
   "## How it compares" (the other geographies and the other measures in NUMBERS); then
   "## What the data can't tell us" (these are survey estimates with confidence intervals;
   the data does not explain causes; and every point in `caveats`, such as the paused annual
   release). Say where the data comes from (source name) and the period covered.
10. RANK WORDS: use "only", "all", "highest", "lowest", "biggest" or "largest" only for the
   charted measure, and only when a check proves it (rule 11). Otherwise avoid these words.
11. CLAIMS: for EVERY sentence in any field that contains a number other than a year, or any
   of the rank words above, add one claim:
   {"sentence": <copied exactly>, "keys": [<KEYS used>], "checks": [<checks>]}.
   Each number must equal (after rounding) one of its keys. Each rank word needs a check of
   the matching kind: only -> only_rise/only_fall; all -> all_rise/all_fall; highest ->
   highest; lowest -> lowest; biggest/largest -> biggest_rise/biggest_fall. Copy checks from
   `chart_facts.supported_checks` (without "detail"), or write one with other periods; every
   check is re-tested against chart_data. If the same sentence is used in two fields, one
   claim covers both. Count words like "four" as numbers. For a value from CHART DATA use
   the key chart.<geography>.<period>.value (or .lower / .upper for its confidence interval).
   Chart titles and annotations are checked like the other text: keep numbers out of them
   unless they come from the data, and give any such sentence a claim.
12. CHARTS: chart_spec is the main chart (a line chart of every year suits most stories).
   `more_charts` may add up to 2 more from the same chart_data: "slope" (first vs last period,
   good for showing who rose and who fell) and "map" (one period by area; only for nations,
   regions or local authorities, and only when chart_data has a `code` column). Give each a
   short title. Do not repeat the same chart twice.
13. Return ONLY a JSON object with exactly these keys, no Markdown fences, no comments.
"""


INTRO = (
    "You are writing a short data story for DataTales (datatales.co.uk), a UK site\n"
    "that turns public data into plain, accurate stories. Python has already done all\n"
    "the maths; your job is only the words around the numbers below."
)
CHART_ROWS_MAX = 240  # chart rows listed in the prompt; larger charts list the key rows only


# The explicit task, sent after the data in the user turn (API drafting). Without it the user
# turn holds only data, which the model is told to treat as inert.
STORY_REQUEST = (
    "Write the DataTales story for the data above now, following every rule. Fill every "
    "field completely: headline (10 to 70 characters, stating the strongest finding), hook "
    "(one full sentence), summary (2 to 4 sentences, at most 120 words), body_md (500 to 700 "
    "words, with the sections ## How it compares and ## What the data can't tell us), "
    "video_script (at most 90 words), chart_spec, more_charts (may be empty) and claims (one "
    "per sentence that has a number or a rank word, copied exactly). Every check needs all "
    "the fields its kind uses: group plus start and end for rise/fall kinds, group plus "
    "period for highest/lowest, start and end for all_rise/all_fall."
)


def narration_instructions() -> str:
    """The fixed part of the prompt (cached by the API): intro, rules and output shape."""
    return "\n".join(
        [
            INTRO,
            "",
            RULES,
            "## Output JSON shape",
            json.dumps(OUTPUT_SCHEMA, indent=1, ensure_ascii=False),
        ]
    )


def _num(v: Any) -> str:
    return "" if v is None else str(v)


def chart_rows_for_prompt(
    chart_data: list[dict[str, Any]], highlight: Any
) -> tuple[list[dict[str, Any]], bool]:
    """Every chart row, or (for big charts) the first and last period plus the highlighted
    group's rows. Returns (rows, cut)."""
    if len(chart_data) <= CHART_ROWS_MAX:
        return chart_data, False
    periods = sorted({str(r.get("period")) for r in chart_data})
    keep = {periods[0], periods[-1]}
    wanted = set(highlight if isinstance(highlight, list) else [highlight] if highlight else [])
    rows = [r for r in chart_data if str(r.get("period")) in keep or r.get("geography") in wanted]
    return rows, True


def narration_data(
    numbers: dict[str, Any], chart_data: list[dict[str, Any]], chart_spec: dict[str, Any]
) -> str:
    """The per-story part of the prompt: chart, numbers, keys and chart data."""
    columns = sorted(set().union(*(row.keys() for row in chart_data))) if chart_data else []
    main = {k: v for k, v in chart_spec.items() if k != "more_charts"}
    more = chart_spec.get("more_charts") or []
    series_values = sorted({str(row.get("geography")) for row in chart_data})
    rows, cut = chart_rows_for_prompt(chart_data, chart_spec.get("highlight"))
    return "\n".join(
        [
            "## Chart",
            f"chart_data columns: {columns}",
            f"geography values: {series_values}",
            "Suggested chart_spec (adjust only if a different chart is clearer):",
            json.dumps(main, ensure_ascii=False),
            *(
                ["Suggested more_charts (optional):", json.dumps(more, ensure_ascii=False)]
                if more
                else []
            ),
            "",
            "## NUMBERS (context and meaning)",
            json.dumps(numbers, indent=1, ensure_ascii=False),
            "",
            "## KEYS (use these names in claims[].keys)",
            *(f"{k} = {v}" for k, v in flatten_numbers(numbers).items()),
            "",
            "## CHART DATA (keys: chart.<geography>.<period>.value, .lower, .upper)",
            *(
                ["(large chart: first and last period and the highlighted rows only)"]
                if cut
                else []
            ),
            "geography,period,value,lower,upper",
            *(
                f"{r.get('geography')},{r.get('period')},{_num(r.get('value'))},"
                f"{_num(r.get('lower'))},{_num(r.get('upper'))}"
                for r in rows
            ),
        ]
    )


def build_prompt(
    numbers: dict[str, Any], chart_data: list[dict[str, Any]], chart_spec: dict[str, Any]
) -> str:
    """The whole prompt, for the copy-paste flow."""
    return narration_instructions() + "\n\n" + narration_data(numbers, chart_data, chart_spec)


def _nullable(description: str) -> dict[str, Any]:
    return {"anyOf": [{"type": "string"}, {"type": "null"}], "description": description}


def _spec_schema() -> dict[str, Any]:
    """Every field is required (null where it does not apply), so a chart can never come back
    without, say, its series column: structured output then guarantees the shape."""
    text = {"type": "string"}
    return {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": list(CHART_TYPES)},
            "x": {"type": "string", "description": "period column, normally 'period'"},
            "y": {"type": "string", "description": "value column, normally 'value'"},
            "series": {"type": "string", "description": "geography column: 'geography'"},
            "highlight": {
                "anyOf": [text, {"type": "array", "items": text}, {"type": "null"}],
                "description": "the geography (or list) to highlight",
            },
            "annotation": _nullable("short note under the chart, or null"),
            "title": _nullable("short chart title"),
            "yLabel": _nullable("unit label, e.g. '% of people'"),
            "start": _nullable("slope only: first period; otherwise null"),
            "end": _nullable("slope only: last period; otherwise null"),
            "period": _nullable("map only: the period shown; otherwise null"),
        },
        "required": [
            "type", "x", "y", "series", "highlight", "annotation", "title", "yLabel",
            "start", "end", "period",
        ],
        "additionalProperties": False,
    }  # fmt: skip


def narration_json_schema() -> dict[str, Any]:
    """JSON schema for structured output. Length limits are not expressible there; the
    Narration model (parse_narration) still enforces every rule after the reply arrives."""
    text = {"type": "string"}

    def desc(d: str) -> dict[str, str]:
        return {"type": "string", "description": d}

    check = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": list(CHECK_KINDS)},
            "group": _nullable("geography; null only for all_rise/all_fall"),
            "period": _nullable("highest/lowest: the period; otherwise null"),
            "start": _nullable("rise/fall kinds: first period; otherwise null"),
            "end": _nullable("rise/fall kinds: last period; otherwise null"),
        },
        "required": ["kind", "group", "period", "start", "end"],
        "additionalProperties": False,
    }
    claim = {
        "type": "object",
        "properties": {
            "sentence": desc("a sentence copied exactly from the text fields"),
            "keys": {"type": "array", "items": text},
            "checks": {"type": "array", "items": check},
        },
        "required": ["sentence", "keys", "checks"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "headline": desc("10 to 70 characters: the single strongest finding as a statement"),
            "hook": desc("exactly one full sentence"),
            "summary": desc("2 to 4 sentences, at most 120 words"),
            "body_md": desc(
                "Markdown, 500 to 700 words, with '## How it compares' and "
                "'## What the data can't tell us'"
            ),
            "video_script": desc("at most 90 words, to be read aloud"),
            "chart_spec": _spec_schema(),
            "more_charts": {"type": "array", "items": _spec_schema()},
            "claims": {"type": "array", "items": claim, "minItems": 1},
        },
        "required": [
            "headline", "hook", "summary", "body_md", "video_script", "chart_spec",
            "more_charts", "claims",
        ],
        "additionalProperties": False,
    }  # fmt: skip
