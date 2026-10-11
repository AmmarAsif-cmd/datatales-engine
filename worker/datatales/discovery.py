"""Weekly dataset discovery: find new UK public datasets and suggest the best few.

1. Fetch catalogue metadata from data.gov.uk (its CKAN API) and the ONS dataset API. Nothing
   is downloaded: titles, descriptions, licences, formats, update frequency and dates only.
2. Hard filters in code: Open Government Licence only; a machine-readable format; a time
   series and/or a geographic breakdown; nothing personal or individual-level; nothing already
   a source or already in the backlog (so rejected datasets are never suggested again).
3. Claude (the discovery model) scores the survivors 0-100 and writes a one-line pitch, from
   the metadata only (untrusted, delimited). Without a key, a simple heuristic scores them.
4. The top few (config: suggestions_per_week, min_score) are added as `suggested`.
"""

import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field

from datatales.config import WORKER_DIR
from datatales.errors import UserError
from datatales.llm import BudgetReached, LLMClient, LLMError, untrusted
from datatales.repo import Repo, now_utc
from datatales.sources import load_sources

CONFIG_PATH = WORKER_DIR / "config" / "discovery.yaml"
SEED_PATH = WORKER_DIR / "config" / "backlog_seed.yaml"
CKAN_API = "https://ckan.publishing.service.gov.uk/api/action/package_search"
ONS_API = "https://api.beta.ons.gov.uk/v1/datasets"
ALLOWED_HOSTS = {"ckan.publishing.service.gov.uk", "api.beta.ons.gov.uk"}
OGL = "Open Government Licence v3.0"
MAX_RESPONSE_BYTES = 20 * 1024 * 1024


class DiscoveryError(UserError):
    pass


class CkanConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rows_per_query: int = Field(50, ge=1, le=200)
    queries: list[str]


class OnsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_datasets: int = Field(400, ge=1, le=2000)


class DiscoveryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suggestions_per_week: int = Field(5, ge=1, le=20)
    min_score: int = Field(55, ge=0, le=100)
    max_to_score: int = Field(40, ge=1, le=100)
    recent_days: int = Field(180, ge=1)
    ckan: CkanConfig
    ons: OnsConfig
    machine_readable_formats: list[str]
    exclude_keywords: list[str]


def load_config() -> DiscoveryConfig:
    return DiscoveryConfig.model_validate(yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")))


@dataclass
class Item:
    """One catalogue dataset, normalised (metadata only)."""

    title: str
    publisher: str
    source_url: str
    catalogue: str  # data_gov_uk | ons
    catalogue_id: str
    licence: str
    formats: list[str]
    update_frequency: str | None
    description: str = ""
    last_updated: str | None = None
    geography_levels: list[str] = field(default_factory=list)
    has_time_series: bool | None = None


# ---- fetching (metadata only) ----


def _get_json(client: httpx.Client, url: str, params: dict[str, Any]) -> Any:
    host = httpx.URL(url).host
    if host not in ALLOWED_HOSTS:
        raise DiscoveryError(f"refusing to fetch from {host}")
    res = client.get(url, params=params)
    res.raise_for_status()
    if len(res.content) > MAX_RESPONSE_BYTES:
        raise DiscoveryError(f"{host} returned more than {MAX_RESPONSE_BYTES} bytes")
    return res.json()


def _ckan_item(p: dict[str, Any]) -> Item:
    extras = {e.get("key"): e.get("value") for e in p.get("extras") or []}
    formats = sorted(
        {(r.get("format") or "").strip(" .").upper() for r in p.get("resources") or []} - {""}
    )
    licence = p.get("license_title") or p.get("license_id") or ""
    return Item(
        title=(p.get("title") or "").strip(),
        publisher=((p.get("organization") or {}).get("title") or "").strip(),
        source_url=f"https://www.data.gov.uk/dataset/{p['id']}/{p.get('name', '')}",
        catalogue="data_gov_uk",
        catalogue_id=str(p["id"]),
        licence=licence,
        formats=formats,
        update_frequency=extras.get("update_frequency") or extras.get("frequency-of-update"),
        description=(p.get("notes") or "")[:1200],
        last_updated=p.get("metadata_modified"),
    )


def fetch_ckan(client: httpx.Client, cfg: DiscoveryConfig) -> list[Item]:
    since = (datetime.now(UTC) - timedelta(days=cfg.recent_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fq = (
        "license_id:uk-ogl AND (res_format:CSV OR res_format:XLSX OR res_format:ODS "
        f"OR res_format:XLS) AND metadata_modified:[{since} TO NOW]"
    )
    items: dict[str, Item] = {}
    for q in cfg.ckan.queries:
        data = _get_json(
            client,
            CKAN_API,
            {"q": q, "fq": fq, "rows": cfg.ckan.rows_per_query, "sort": "metadata_modified desc"},
        )
        for p in (data.get("result") or {}).get("results", []):
            item = _ckan_item(p)
            items.setdefault(item.catalogue_id, item)
    return list(items.values())


def fetch_ons(client: httpx.Client, cfg: DiscoveryConfig) -> list[Item]:
    items: list[Item] = []
    offset = 0
    while offset < cfg.ons.max_datasets:
        data = _get_json(client, ONS_API, {"limit": 100, "offset": offset})
        page = data.get("items") or []
        for d in page:
            if d.get("state") != "published":
                continue
            text = " ".join([d.get("description") or "", " ".join(d.get("keywords") or [])])
            items.append(
                Item(
                    title=(d.get("title") or "").strip(),
                    publisher="Office for National Statistics",
                    source_url=f"https://www.ons.gov.uk/datasets/{d['id']}",
                    catalogue="ons",
                    catalogue_id=str(d["id"]),
                    licence=OGL,  # ONS publishes all datasets under the OGL
                    formats=["CSV", "XLSX", "API"],
                    update_frequency=d.get("release_frequency"),
                    description=text[:1200],
                    last_updated=d.get("last_updated"),
                )
            )
        offset += 100
        if len(page) < 100:
            break
    return items


# ---- hard filters (code, before any model) ----

GEO_WORDS = {
    "local_authority": ["local authority", "local authorities", "council", "district", "borough",
                        "lsoa", "msoa", "ward", "county", "unitary"],
    "region": ["region", "regional", "itl1", "nuts1"],
    "country": ["england", "wales", "scotland", "northern ireland", "by country", "uk countries"],
}  # fmt: skip
TIME_WORDS = ["time series", "monthly", "quarterly", "annual", "weekly", "trend", "since",
              "historic", "over time"]  # fmt: skip
YEAR = re.compile(r"\b(19|20)\d{2}\b")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def annotate(item: Item) -> Item:
    """Geography levels and time-series flag from the metadata text (heuristic)."""
    text = f"{item.title} {item.description}".lower()
    item.geography_levels = [
        lvl for lvl, words in GEO_WORDS.items() if any(w in text for w in words)
    ]
    freq = (item.update_frequency or "").lower()
    item.has_time_series = bool(
        any(w in text or w in freq for w in TIME_WORDS) or len(set(YEAR.findall(text))) >= 2
    )
    return item


def is_ogl(licence: str) -> bool:
    lic = licence.lower()
    return "uk-ogl" in lic or "open government licence" in lic or lic in ("ogl", "ogl-uk-3.0")


def hard_filter(
    item: Item, cfg: DiscoveryConfig, known_urls: set[str], known_titles: set[str]
) -> str | None:
    """None if the item may be suggested; otherwise the reason it was dropped."""
    text = f"{item.title} {item.description}".lower()
    if not item.title:
        return "no title"
    if not is_ogl(item.licence):
        return "not Open Government Licence"
    allowed = {f.upper() for f in cfg.machine_readable_formats}
    if not set(item.formats) & allowed:
        return "no machine-readable format"
    if any(k in text for k in cfg.exclude_keywords):
        return "personal, individual-level or administrative data"
    if not (item.geography_levels or item.has_time_series):
        return "no time series or geographic breakdown"
    if item.source_url in known_urls:
        return "already a source or in the backlog"
    if _norm(item.title) in known_titles:
        return "same title as a source or backlog item"
    return None


def known(repo: Repo) -> tuple[set[str], set[str]]:
    """URLs and normalised titles of every source and backlog item (any status)."""
    urls = set()
    titles = set()
    for s in load_sources().values():
        urls.add(str(s.url))
        titles.add(_norm(s.name))
    for b in repo.list_backlog():
        urls.add(b["source_url"])
        titles.add(_norm(b["title"]))
    return urls, titles


# ---- scoring ----

SCORING_INSTRUCTIONS = """\
You help DataTales (datatales.co.uk) choose UK public datasets to turn into short, plain,
verified data stories. Stories compare places or groups over time ("which areas rose fastest",
"the only region where ... fell") using numbers computed by code.

Score each candidate dataset 0-100 from its catalogue metadata only:
- update frequency (monthly or quarterly beats annual; one-off or ceased scores low),
- comparisons across places or groups (local authority, region, nation, age, sex, sector),
- public interest (housing, health, transport, jobs, money, environment, education, crime),
- fit with DataTales (clean numeric tables that support clear, verifiable comparisons).
Score low: internal admin lists, geospatial layers without statistics, documents, one-off
surveys, anything personal or individual-level, anything that looks withdrawn.

For each candidate write a one-line pitch (at most 25 words, plain UK English, no hype): the
story the data could tell. Do not invent numbers. Also say whether it is a time series and
which geography levels it has (local_authority, region, country), from the metadata."""

GEO_LEVELS = ["local_authority", "region", "country"]

SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "ratings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "the candidate id, copied"},
                    "score": {"type": "integer", "description": "0 to 100"},
                    "pitch": {"type": "string", "description": "one line, at most 25 words"},
                    "has_time_series": {"type": "boolean"},
                    "geography_levels": {
                        "type": "array",
                        "items": {"type": "string", "enum": GEO_LEVELS},
                    },
                },
                "required": ["id", "score", "pitch", "has_time_series", "geography_levels"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ratings"],
    "additionalProperties": False,
}  # fmt: skip


class Rating(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    score: int = Field(ge=0, le=100)
    pitch: str = Field(min_length=10, max_length=240)
    has_time_series: bool
    geography_levels: list[str]


def _validate_ratings(ids: set[str]) -> Callable[[Any], list[Rating]]:
    def validate(value: Any) -> list[Rating]:
        if not isinstance(value, dict):
            raise ValueError("reply must be a JSON object")
        ratings = [Rating.model_validate(r) for r in value.get("ratings", [])]
        unknown = {r.id for r in ratings} - ids
        if unknown:
            raise ValueError(f"unknown candidate ids: {sorted(unknown)[:5]}")
        return ratings

    return validate


FREQ_POINTS = {"weekly": 30, "monthly": 30, "quarterly": 25, "annual": 15, "annually": 15,
               "yearly": 15}  # fmt: skip


def heuristic_score(item: Item) -> int:
    """Fallback when Claude is unavailable: frequency, geography and time series only."""
    freq = (item.update_frequency or "").lower()
    points = next((v for k, v in FREQ_POINTS.items() if k in freq), 5)
    points += 15 * len(item.geography_levels) + (15 if item.has_time_series else 0)
    return min(100, 20 + points)


def candidate_payload(items: list[Item]) -> str:
    rows = [
        {
            "id": str(i),
            "title": it.title,
            "publisher": it.publisher,
            "update_frequency": it.update_frequency,
            "formats": it.formats,
            "last_updated": (it.last_updated or "")[:10],
            "description": it.description[:500],
        }
        for i, it in enumerate(items)
    ]
    return json.dumps(rows, ensure_ascii=False)


@dataclass
class DiscoverySummary:
    fetched: int = 0
    passed_filters: int = 0
    scored_by: str = "heuristic"
    added: list[dict[str, Any]] = field(default_factory=list)
    dropped: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def score_items(
    items: list[Item], llm: LLMClient | None, log: Callable[[str], None]
) -> tuple[list[tuple[Item, int, str]], str]:
    """[(item, score, pitch)], scored by Claude when possible, else by the heuristic."""
    if llm is not None and items:
        try:
            result = llm.call(
                "discovery",
                instructions=SCORING_INSTRUCTIONS,
                data=untrusted("candidates", candidate_payload(items)),
                schema=SCORE_SCHEMA,
                validate=_validate_ratings({str(i) for i in range(len(items))}),
                request="Score every candidate above. Return one rating per candidate id.",
            )
            out = []
            for r in result.value:
                it = items[int(r.id)]
                it.has_time_series = r.has_time_series
                it.geography_levels = sorted(set(it.geography_levels) | set(r.geography_levels))
                out.append((it, r.score, r.pitch.strip()))
            return out, "claude"
        except BudgetReached as exc:
            log(f"Claude budget reached ({exc}); using the heuristic score")
        except LLMError as exc:
            log(f"Claude scoring failed ({exc}); using the heuristic score")
    return [(it, heuristic_score(it), _first_sentence(it.description)) for it in items], "heuristic"


def _first_sentence(text: str) -> str:
    m = re.match(r"(.{10,200}?[.!?])(\s|$)", text.strip(), re.S)
    return (m.group(1) if m else text.strip()[:200]).replace("\n", " ")


def _row(item: Item, score: int, pitch: str) -> dict[str, Any]:
    return {
        "title": item.title[:300],
        "publisher": item.publisher[:200] or "Unknown",
        "source_url": item.source_url,
        "catalogue": item.catalogue,
        "catalogue_id": item.catalogue_id,
        "licence": OGL if is_ogl(item.licence) else item.licence,
        "formats": item.formats,
        "update_frequency": item.update_frequency,
        "geography_levels": item.geography_levels,
        "has_time_series": item.has_time_series,
        "score": score,
        "pitch": pitch[:300],
        "status": "suggested",
        "last_updated": item.last_updated,
    }


Fetcher = Callable[[httpx.Client, DiscoveryConfig], list[Item]]


def run_discovery(
    repo: Repo,
    log: Callable[[str], None] = print,
    llm: LLMClient | None = None,
    fetchers: dict[str, Fetcher] | None = None,
    cfg: DiscoveryConfig | None = None,
) -> DiscoverySummary:
    cfg = cfg or load_config()
    fetchers = fetchers or {"data.gov.uk": fetch_ckan, "ONS": fetch_ons}
    summary = DiscoverySummary()
    items: list[Item] = []
    headers = {"User-Agent": "DataTales discovery (datatales.co.uk)"}
    with httpx.Client(timeout=60, follow_redirects=False, headers=headers) as client:
        for name, fetch in fetchers.items():
            try:
                got = fetch(client, cfg)
                log(f"{name}: {len(got)} dataset(s)")
                items.extend(got)
            except Exception as exc:  # noqa: BLE001 - one catalogue failing must not stop the other
                summary.errors.append(f"{name}: {type(exc).__name__}: {exc}"[:300])
                log(f"{name}: FAILED ({exc})")
    summary.fetched = len(items)

    urls, titles = known(repo)
    passed: list[Item] = []
    for it in items:
        reason = hard_filter(annotate(it), cfg, urls, titles)
        if reason:
            summary.dropped[reason] = summary.dropped.get(reason, 0) + 1
            continue
        urls.add(it.source_url)  # also de-duplicates within this run
        titles.add(_norm(it.title))
        passed.append(it)
    summary.passed_filters = len(passed)
    # most promising first (frequency, geography, time series), then most recently updated
    passed.sort(key=lambda i: (heuristic_score(i), i.last_updated or ""), reverse=True)
    scored, summary.scored_by = score_items(passed[: cfg.max_to_score], llm, log)

    best = sorted(scored, key=lambda t: t[1], reverse=True)
    picks = [t for t in best if t[1] >= cfg.min_score][: cfg.suggestions_per_week]
    for it, score, pitch in picks:
        row = _row(it, score, pitch)
        repo.insert_backlog([row])
        summary.added.append(row)
        log(f"  suggested ({score}): {it.title} [{it.publisher}]")
    return summary


def seed_backlog(repo: Repo, path: Any = SEED_PATH) -> int:
    """Add the curated seed list (idempotent: existing source_urls are skipped)."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    existing = {b["source_url"] for b in repo.list_backlog()}
    rows = [
        {
            **{
                k: d[k]
                for k in (
                    "title",
                    "publisher",
                    "source_url",
                    "formats",
                    "update_frequency",
                    "geography_levels",
                    "has_time_series",
                    "score",
                    "pitch",
                )
            },
            "catalogue": "seed",
            "licence": data["licence"],
            "status": "suggested",
        }  # fmt: skip
        for d in data["datasets"]
        if d["source_url"] not in existing
    ]
    if rows:
        repo.insert_backlog(rows)
    return len(rows)


def summary_json(summary: DiscoverySummary) -> dict[str, Any]:
    return {**asdict(summary), "at": now_utc().isoformat()}
