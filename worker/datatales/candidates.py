"""Group stored findings into story candidates and build a diversified shortlist.

A candidate is one geography, at one geography level, with findings that all point the
same way for people (all good news or all bad news), across related measures. Findings
for the same place that point in opposite directions become separate candidates.
"""

from dataclasses import dataclass, field
from typing import Any

SHORTLIST_SIZE = 5
MAX_PER_GEOGRAPHY = 2
CORROBORATION_BONUS = 0.15  # per extra distinct measure, multiplicative


def measure_of(numbers: dict[str, Any]) -> str:
    """The finding's series: its `measure`, or (for tables without one) its slice values
    apart from the geography level, e.g. "Cars, Diesel"."""
    if "measure" in numbers:
        return str(numbers["measure"])
    cols = [c for c in numbers.get("slice_by") or [] if c != "geo_level"]
    return "/".join(str(numbers.get(c)) for c in cols) if cols else "None"


@dataclass
class Candidate:
    geography: str
    geo_level: str | None
    good_news: bool
    findings: list[dict[str, Any]] = field(default_factory=list)

    @property
    def lead(self) -> dict[str, Any]:
        return self.findings[0]

    @property
    def measures(self) -> list[str]:
        return sorted({measure_of(f["numbers"]) for f in self.findings})

    @property
    def finding_ids(self) -> list[str]:
        return [f["id"] for f in self.findings]

    @property
    def score(self) -> float:
        """Best finding's score, raised a little when other measures agree. Max 1."""
        bonus = 1 + CORROBORATION_BONUS * (len(self.measures) - 1)
        return round(min(1.0, float(self.lead["score"]) * bonus), 4)

    @property
    def title(self) -> str:
        news = "good news" if self.good_news else "bad news"
        return f"{self.geography} ({self.geo_level}): {news} on {', '.join(self.measures)}"


def group_findings(findings: list[dict[str, Any]]) -> list[Candidate]:
    groups: dict[tuple[str, str | None, bool], Candidate] = {}
    for f in findings:
        n = f["numbers"]
        key = (str(n.get("group")), n.get("geo_level"), bool(n.get("good_news")))
        if key not in groups:
            groups[key] = Candidate(*key)
        groups[key].findings.append(f)
    for c in groups.values():
        c.findings.sort(key=lambda f: (-float(f["score"]), f["detector"], f["id"]))
    return sorted(groups.values(), key=lambda c: (-c.score, c.geography, not c.good_news))


def shortlist(
    findings: list[dict[str, Any]],
    size: int = SHORTLIST_SIZE,
    max_per_geography: int = MAX_PER_GEOGRAPHY,
) -> list[Candidate]:
    picked: list[Candidate] = []
    per_geo: dict[str, int] = {}
    for c in group_findings(findings):
        if per_geo.get(c.geography, 0) >= max_per_geography:
            continue
        picked.append(c)
        per_geo[c.geography] = per_geo.get(c.geography, 0) + 1
        if len(picked) == size:
            break
    return picked
