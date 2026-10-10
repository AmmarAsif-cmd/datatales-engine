"""Number checker for story text.

Two levels:

1. Data-level (always): every number in the text equals some number in the story's
   `numbers` (sign ignored) after rounding that number to the decimals written. Years and
   financial years (2011-12) must fall within the data period.
2. Claim-level (when the narration supplies `claims`): each claim is
   {sentence, keys}. The sentence must appear in the text; every key must exist in the
   story's key table (`flatten_numbers`); every number in the sentence must match one of
   ITS keys; and every number in the text must sit inside a claimed sentence. This catches
   a real number attached to the wrong thing (e.g. a happiness score called "worthwhile").

A failed story cannot be approved (enforced in the database too).
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
YEAR_KINDS = ("year", "financial_year")
PLAIN_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")

# Rank / exclusivity words and the chart_data checks that can prove them (chartfacts.py).
RANK_WORDS: dict[str, tuple[str, ...]] = {
    "only": ("only_rise", "only_fall"),
    "all": ("all_rise", "all_fall"),
    "highest": ("highest",),
    "lowest": ("lowest",),
    "biggest": ("biggest_rise", "biggest_fall"),
    "largest": ("biggest_rise", "biggest_fall"),
}
RANK_RE = re.compile(r"\b(" + "|".join(RANK_WORDS) + r")\b", re.I)


@dataclass(frozen=True)
class Token:
    field: str
    text: str
    value: Decimal
    decimals: int
    kind: str  # number | percent | money | ordinal | times | word | year | financial_year
    start: int = 0
    end: int = 0


@dataclass
class Report:
    status: str
    checked: int
    unmatched: list[dict[str, Any]] = field(default_factory=list)
    years_out_of_range: list[dict[str, Any]] = field(default_factory=list)
    data_years: list[int] = field(default_factory=list)
    allowed_values: int = 0
    claims_checked: bool = False
    claims: list[dict[str, Any]] = field(default_factory=list)
    uncovered: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


# ---- tokens ----


def extract_tokens(field_name: str, text: str) -> list[Token]:
    tokens: list[Token] = []
    for m in TOKEN.finditer(text):
        span = (m.start(), m.end())
        if m.group("fy"):
            value = Decimal(int(m.group("fy")))
            tokens.append(Token(field_name, m.group(0), value, 0, "financial_year", *span))
            continue
        if m.group("word"):
            value = Decimal(WORD_NUMBERS[m.group("word").lower()])
            tokens.append(Token(field_name, m.group(0), value, 0, "word", *span))
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
        tokens.append(Token(field_name, m.group(0).strip(), value, decimals, kind, *span))
    return tokens


def matches(token: Token, allowed: set[Decimal] | list[Decimal]) -> bool:
    target = abs(token.value)
    half_step = Decimal(5) * Decimal(10) ** -(token.decimals + 1)
    return any(abs(a - target) <= half_step for a in allowed)


# ---- the numbers a story may use ----


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


def flatten_numbers(numbers: dict[str, Any]) -> dict[str, Decimal]:
    """Readable key -> value for every number in `numbers`.

    findings[i] -> f{i+1}, series[i] -> s{i+1}; list items with a `period` are keyed by
    that period (s1.points.2020-21.value); confidence intervals are `.ci.lower`/`.ci.upper`.
    `unit` strings like "out of 10" give `{path}.scale_max`.
    """
    out: dict[str, Decimal] = {}

    def seg_for(index: int, item: Any) -> str:
        if isinstance(item, dict) and isinstance(item.get("period"), str):
            return item["period"]
        if isinstance(item, dict) and isinstance(item.get("group"), str):
            return item["group"]
        return str(index + 1)

    def walk(obj: Any, path: list[str]) -> None:
        if isinstance(obj, bool) or obj is None:
            return
        if isinstance(obj, int | float):
            out[".".join(path)] = Decimal(str(obj))
        elif isinstance(obj, str):
            for n in OUT_OF.findall(obj):
                out[".".join([*path[:-1], "scale_max"])] = Decimal(n)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k == "source":
                    continue
                walk(v, [*path, k])
        elif isinstance(obj, list | tuple):
            parent = path[-1] if path else ""
            if (
                path
                and path[-1].endswith("ci")
                and len(obj) == 2
                and all(isinstance(x, int | float) for x in obj)
            ):
                walk(obj[0], [*path, "lower"])
                walk(obj[1], [*path, "upper"])
                return
            top_level = len(path) == 1 and parent in ("findings", "series")
            for i, item in enumerate(obj):
                if top_level:
                    walk(item, [("f" if parent == "findings" else "s") + str(i + 1)])
                else:
                    walk(item, [*path, seg_for(i, item)])

    walk(numbers, [])
    return out


# ---- text positions (claims are matched ignoring Markdown and whitespace) ----


def _normalise(text: str) -> tuple[str, list[int]]:
    """Lowercased text without Markdown emphasis and with collapsed whitespace, plus a map
    from each normalised character back to its index in the original."""
    chars: list[str] = []
    index: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        if ch in "*_`#>":
            continue
        ch = {"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"}.get(ch, ch)
        if ch.isspace():
            if prev_space:
                continue
            ch = " "
            prev_space = True
        else:
            prev_space = False
        chars.append(ch.lower())
        index.append(i)
    while chars and chars[-1] == " ":
        chars.pop()
        index.pop()
    return "".join(chars), index


def _find_spans(text: str, sentence: str) -> list[tuple[int, int]]:
    norm_text, mapping = _normalise(text)
    norm_sentence, _ = _normalise(sentence)
    norm_sentence = norm_sentence.strip()
    spans: list[tuple[int, int]] = []
    if not norm_sentence:
        return spans
    start = norm_text.find(norm_sentence)
    while start != -1:
        end = start + len(norm_sentence) - 1
        spans.append((mapping[start], mapping[end] + 1))
        start = norm_text.find(norm_sentence, start + 1)
    return spans


def _sentence_around(text: str, pos: int) -> str:
    start = max(text.rfind(". ", 0, pos), text.rfind("\n", 0, pos))
    end_candidates = [i for i in (text.find(". ", pos), text.find("\n", pos)) if i != -1]
    end = min(end_candidates) + 1 if end_candidates else len(text)
    return text[start + 1 : end].strip()


# ---- main entry ----


def _data_years(numbers: dict[str, Any], fallback: set[int]) -> tuple[int | None, int | None]:
    period = numbers.get("data_period") or {}
    years: set[int] = set()
    for label in (period.get("first"), period.get("last")):
        for a, b in YEAR_PERIOD.findall(str(label or "")):
            years.update({int(a), int(a[:2] + b)})
    years = years or fallback
    return (min(years), max(years)) if years else (None, None)


def caveat_years(numbers: dict[str, Any]) -> set[int]:
    """Years quoted in the source's caveats (e.g. when a release was paused) are allowed."""
    years: set[int] = set()
    for text in numbers.get("caveats") or []:
        for a, b in YEAR_PERIOD.findall(str(text)):
            years.update({int(a), int(a[:2] + b)})
        years.update(int(y) for y in PLAIN_YEAR.findall(str(text)))
    return years


def verify_text(
    fields: dict[str, str | None],
    numbers: dict[str, Any],
    claims: list[dict[str, Any]] | None = None,
    chart_data: list[dict[str, Any]] | None = None,
) -> Report:
    allowed, years = allowed_from_numbers(numbers)
    lo, hi = _data_years(numbers, years)
    extra_years = caveat_years(numbers)
    report = Report(status="passed", checked=0, data_years=[lo, hi] if lo else [])
    report.allowed_values = len(allowed)

    texts = {name: fields.get(name) or "" for name in TEXT_FIELDS}
    tokens = {name: extract_tokens(name, text) for name, text in texts.items()}

    for name, toks in tokens.items():
        for tok in toks:
            report.checked += 1
            if tok.kind in YEAR_KINDS:
                ys = [int(tok.value)]
                if tok.kind == "financial_year":
                    m = YEAR_PERIOD.search(tok.text)
                    if m:
                        ys.append(int(m.group(1)[:2] + m.group(2)))
                outside = [
                    y for y in ys if y not in extra_years and (lo is None or not lo <= y <= hi)
                ]
                if outside:
                    report.years_out_of_range.append(
                        {"field": name, "text": tok.text, "allowed": [lo, hi]}
                    )
            elif not matches(tok, allowed):
                report.unmatched.append(
                    {"field": name, "text": tok.text, "kind": tok.kind, "value": str(tok.value)}
                )

    if claims is not None:
        _check_claims(report, texts, tokens, numbers, claims, chart_data or [])

    failed = report.unmatched or report.years_out_of_range or report.uncovered
    failed = failed or any(c["status"] != "ok" for c in report.claims)
    report.status = "failed" if failed else "passed"
    return report


def _check_claims(
    report: Report,
    texts: dict[str, str],
    tokens: dict[str, list[Token]],
    numbers: dict[str, Any],
    claims: list[dict[str, Any]],
    chart_data: list[dict[str, Any]],
) -> None:
    from datatales.chartfacts import evaluate

    report.claims_checked = True
    key_table = flatten_numbers(numbers)
    covered: dict[str, list[tuple[int, int]]] = {name: [] for name in texts}

    for claim in claims:
        sentence = str(claim.get("sentence", ""))
        keys = [str(k) for k in claim.get("keys", [])]
        checks = [dict(c) for c in claim.get("checks", [])]
        result: dict[str, Any] = {
            "sentence": sentence,
            "keys": keys,
            "fields": [],
            "numbers": [],
            "checks": [],
        }
        unknown = [k for k in keys if k not in key_table]
        found_in: list[tuple[str, tuple[int, int]]] = []
        for name, text in texts.items():
            for span in _find_spans(text, sentence):
                found_in.append((name, span))
                covered[name].append(span)
        result["fields"] = sorted({name for name, _ in found_in})

        if not found_in:
            result["status"] = "sentence_not_found"
        elif unknown:
            result["status"] = "unknown_keys"
            result["unknown_keys"] = unknown
        else:
            name, (start, end) = found_in[0]
            mismatched = False
            for tok in tokens[name]:
                if not (start <= tok.start < end) or tok.kind in YEAR_KINDS:
                    continue
                hit = next((k for k in keys if matches(tok, [abs(key_table[k])])), None)
                result["numbers"].append({"text": tok.text, "key": hit})
                mismatched = mismatched or hit is None
            kinds = {c.get("kind") for c in checks}
            words = sorted({w.lower() for w in RANK_RE.findall(sentence)})
            missing = [w for w in words if not kinds & set(RANK_WORDS[w])]
            for c in checks:
                ok, detail = evaluate(c, chart_data)
                result["checks"].append({**_check_input(c), "ok": ok, "detail": detail})
            if mismatched:
                result["status"] = "mismatch"
                result["key_values"] = {k: str(key_table[k]) for k in keys}
            elif missing:
                result["status"] = "assertion_missing"
                result["missing_checks"] = missing
            elif not all(c["ok"] for c in result["checks"]):
                result["status"] = "assertion_failed"
            else:
                result["status"] = "ok"
        report.claims.append(result)

    for name, text in texts.items():
        for m in RANK_RE.finditer(text):
            if not any(s <= m.start() < e for s, e in covered[name]):
                report.uncovered.append(
                    {
                        "field": name,
                        "text": m.group(0),
                        "sentence": _sentence_around(text, m.start()),
                    }
                )

    for name, toks in tokens.items():
        for tok in toks:
            if tok.kind in YEAR_KINDS:
                continue
            if not any(s <= tok.start < e for s, e in covered[name]):
                report.uncovered.append(
                    {
                        "field": name,
                        "text": tok.text,
                        "sentence": _sentence_around(texts[name], tok.start),
                    }
                )


CHECK_FIELDS = ("kind", "group", "period", "start", "end")


def _check_input(check: dict[str, Any]) -> dict[str, Any]:
    return {k: check[k] for k in CHECK_FIELDS if check.get(k) is not None}
