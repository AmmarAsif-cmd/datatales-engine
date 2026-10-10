"""Number checker: every number in a story's text must come from the story's `numbers`.

A number in the text passes if it equals a number in `numbers` (sign ignored) after
rounding that number to the decimal places written in the text. Years (including
financial years such as 2011-12) must fall within the data period. Anything else fails
verification, and a failed story cannot be approved (enforced in the database too).
"""

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

TEXT_FIELDS = ("headline", "hook", "summary", "body_md", "video_script")

WORD_NUMBERS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "twice": 2, "double": 2, "doubled": 2, "treble": 3, "tripled": 3,
}  # fmt: skip
# "one", "first", "half" etc. are left out on purpose: they are too often idiomatic
# ("no one", "for the first time") to check reliably.

_FIN_YEAR = r"(?P<fy>(?:19|20)\d{2})\s*[-–/]\s*(?P<fy2>\d{2})(?!\d)"
_NUMBER = r"(?P<num>-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
TOKEN = re.compile(
    rf"(?<![\w.]){_FIN_YEAR}"
    rf"|(?P<money>£)?(?<![\w.]){_NUMBER}(?P<suffix>\s?%|(?:st|nd|rd|th)\b|\s?(?:times|x)\b)?"
    rf"|\b(?P<word>{'|'.join(WORD_NUMBERS)})\b",
    re.I,
)
YEAR_PERIOD = re.compile(r"((?:19|20)\d{2})\s*[-–/]\s*(\d{2})(?!\d)")
OUT_OF = re.compile(r"out of (\d+)")


@dataclass(frozen=True)
class Token:
    field: str
    text: str
    value: Decimal
    decimals: int
    kind: str  # number | percent | money | ordinal | times | word | year | financial_year


@dataclass
class Report:
    status: str
    checked: int
    unmatched: list[dict[str, Any]] = field(default_factory=list)
    years_out_of_range: list[dict[str, Any]] = field(default_factory=list)
    data_years: list[int] = field(default_factory=list)
    allowed_values: int = 0

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def extract_tokens(field_name: str, text: str) -> list[Token]:
    tokens: list[Token] = []
    for m in TOKEN.finditer(text):
        if m.group("fy"):
            start = int(m.group("fy"))
            tokens.append(Token(field_name, m.group(0), Decimal(start), 0, "financial_year"))
            continue
        if m.group("word"):
            word = m.group("word").lower()
            tokens.append(Token(field_name, m.group(0), Decimal(WORD_NUMBERS[word]), 0, "word"))
            continue
        raw = m.group("num").replace(",", "")
        suffix = (m.group("suffix") or "").strip().lower()
        decimals = len(raw.split(".")[1]) if "." in raw else 0
        value = Decimal(raw)
        if m.group("money"):
            kind = "money"
        elif suffix == "%":
            kind = "percent"
        elif suffix in ("st", "nd", "rd", "th"):
            kind = "ordinal"
        elif suffix in ("times", "x"):
            kind = "times"
        elif decimals == 0 and "," not in m.group("num") and 1900 <= value <= 2099:
            kind = "year"
        else:
            kind = "number"
        tokens.append(Token(field_name, m.group(0).strip(), value, decimals, kind))
    return tokens


def allowed_from_numbers(numbers: Any) -> tuple[set[Decimal], set[int]]:
    """All numeric values in `numbers` (recursively), plus years from period labels."""
    values: set[Decimal] = set()
    years: set[int] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, bool) or obj is None:
            return
        if isinstance(obj, int | float):
            values.add(abs(Decimal(str(obj))))
        elif isinstance(obj, str):
            for a, b in YEAR_PERIOD.findall(obj):
                years.update({int(a), int(a[:2] + b)})
            for n in OUT_OF.findall(obj):
                values.add(Decimal(n))
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list | tuple):
            for v in obj:
                walk(v)

    walk(numbers)
    return values, years


def matches(token: Token, allowed: set[Decimal]) -> bool:
    target = abs(token.value)
    half_step = Decimal(5) * Decimal(10) ** -(token.decimals + 1)
    return any(abs(a - target) <= half_step for a in allowed)


def verify_text(fields: dict[str, str | None], numbers: dict[str, Any]) -> Report:
    allowed, years = allowed_from_numbers(numbers)
    period = numbers.get("data_period") or {}
    data_years: set[int] = set()
    for label in (period.get("first"), period.get("last")):
        for a, b in YEAR_PERIOD.findall(str(label or "")):
            data_years.update({int(a), int(a[:2] + b)})
    data_years = data_years or years
    lo, hi = (min(data_years), max(data_years)) if data_years else (None, None)

    report = Report(status="passed", checked=0, data_years=[lo, hi] if lo else [])
    report.allowed_values = len(allowed)
    for name in TEXT_FIELDS:
        text = fields.get(name) or ""
        for tok in extract_tokens(name, text):
            report.checked += 1
            if tok.kind in ("year", "financial_year"):
                ys = [int(tok.value)]
                if tok.kind == "financial_year":
                    m = YEAR_PERIOD.search(tok.text)
                    if m:
                        ys.append(int(m.group(1)[:2] + m.group(2)))
                if lo is None or any(y < lo or y > hi for y in ys):
                    report.years_out_of_range.append(
                        {"field": name, "text": tok.text, "allowed": [lo, hi]}
                    )
                continue
            if not matches(tok, allowed):
                report.unmatched.append(
                    {"field": name, "text": tok.text, "kind": tok.kind, "value": str(tok.value)}
                )
    if report.unmatched or report.years_out_of_range:
        report.status = "failed"
    return report
