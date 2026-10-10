"""Publish an approved story as Markdown for the static site.

Writes site/src/content/stories/<slug>.md with the front matter defined in
site/src/content.config.ts. Every number on the page comes from the story's stored,
verified `numbers`; nothing is recalculated here.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from datatales.config import WORKER_DIR
from datatales.errors import UserError
from datatales.geo import mappable
from datatales.repo import Repo, now_utc
from datatales.sources import DetectConfig, SourceDef, get_source

SITE_STORIES = WORKER_DIR.parent / "site" / "src" / "content" / "stories"
MAX_KEY_NUMBERS = 4
DESCRIPTION_MAX = 200


class PublishError(UserError):
    pass


def _matches(when: dict[str, list[Any]], key: dict[str, Any]) -> bool:
    return all(key.get(col) in allowed for col, allowed in when.items())


def label_for(config: DetectConfig, numbers: dict[str, Any]) -> str:
    for rule in config.labels:
        if _matches(rule.when, numbers):
            return rule.label.replace("{measure}", str(numbers.get("measure", "")).lower())
    parts = [str(numbers[c]) for c in config.slice_by if c in numbers]
    return ", ".join(parts)


def format_value(value: float, unit: str) -> str:
    text = f"{value:,.2f}".rstrip("0").rstrip(".")
    return f"{text}%" if unit.startswith("%") else text


def key_numbers(numbers: dict[str, Any], config: DetectConfig) -> list[dict[str, str]]:
    """Cards from the story's findings: latest value, with where it started as the note."""
    cards: list[dict[str, str]] = []
    seen: set[str] = set()
    for f in numbers.get("findings", []):
        if "end_value" not in f or len(cards) == MAX_KEY_NUMBERS:
            continue
        label = f"{label_for(config, f)}, {f['end_period']}"
        if label in seen:
            continue
        seen.add(label)
        unit = str(f.get("unit", ""))
        note = f"From {format_value(f['start_value'], unit)} in {f['start_period']}"
        if unit and not unit.startswith("%"):
            note += f" ({unit})"
        cards.append({"label": label, "value": format_value(f["end_value"], unit), "note": note})
    if not cards:
        raise PublishError("story has no findings with start and end values for key numbers")
    return cards


def first_sentence(text: str, limit: int = DESCRIPTION_MAX) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text.strip(), re.S)
    sentence = (m.group(1) if m else text).strip()
    return sentence if len(sentence) <= limit else sentence[: limit - 1].rstrip() + "…"


def provenance(repo: Repo, story: dict[str, Any]) -> tuple[SourceDef, dict[str, Any]]:
    findings = repo.get_findings(story["finding_ids"])
    if not findings:
        raise PublishError("story's findings were not found")
    clean_ids = {f["clean_table_id"] for f in findings}
    if len(clean_ids) != 1:
        raise PublishError("story's findings come from more than one clean table")
    ct = repo.get_clean_table(clean_ids.pop())
    ds = repo.get_dataset(ct.dataset_id)
    source = get_source(ds.source_slug)
    recipe = next((r for r in repo.list_recipes(ds.source_id) if r.id == ct.recipe_id), None)
    if recipe is None:
        raise PublishError("recipe for the story's clean table was not found")
    return source, {
        "fetchedAt": ds.fetched_at,
        "datasetChecksum": ds.checksum,
        "recipeVersion": f"{source.slug}.v{recipe.version}",
    }


FIN_YEAR_HYPHEN = re.compile(r"(?<![\w.])((?:19|20)\d{2})-(\d{2})(?!\d)")


def en_dash(text: str) -> str:
    """Financial years read 2011–12, not 2011-12 (display only; data keeps its labels)."""
    return FIN_YEAR_HYPHEN.sub("\\1\u2013\\2", text)


def display_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """A chart spec for the site: en dashes in its text, extra charts listed separately."""
    return {
        k: en_dash(v) if k in ("title", "annotation") and isinstance(v, str) else v
        for k, v in spec.items()
        if k != "more_charts"
    }


def first_published(path: Path) -> str | None:
    """`date` of an existing story file, so republishing keeps the original publish date."""
    if not path.exists():
        return None
    parts = path.read_text(encoding="utf-8").split("---\n", 2)
    if len(parts) < 3:
        return None
    head = yaml.safe_load(parts[1]) or {}
    return str(head["date"]) if head.get("date") else None


def front_matter(
    story: dict[str, Any],
    source: SourceDef,
    prov: dict[str, Any],
    when: datetime,
    first_date: str | None = None,
) -> dict[str, Any]:
    numbers = story["numbers"]
    if source.detect is None:
        raise PublishError(f"source {source.slug} has no detect config")
    period = numbers.get("data_period") or {}
    src = numbers.get("source") or {}
    fm: dict[str, Any] = {
        "title": en_dash(story["headline"]),
        "description": en_dash(first_sentence(story["summary"] or story["hook"])),
        "hook": en_dash(story["hook"]),
        "date": first_date or when.date().isoformat(),
        "updated": when.date().isoformat(),
        "source": {
            "name": src.get("name", source.name),
            "publisher": src.get("publisher", source.publisher),
            "url": src.get("url", str(source.url)),
            **({"licence": src["licence"]} if src.get("licence") else {}),
        },
        "fetchedAt": prov["fetchedAt"][:10],
        "recipeVersion": prov["recipeVersion"],
        "datasetChecksum": prov["datasetChecksum"],
        "keyNumbers": [
            {k: en_dash(v) for k, v in card.items()} for card in key_numbers(numbers, source.detect)
        ],
        "chart_spec": display_spec(story["chart_spec"]),
        "chart_data": story["chart_data"],
        "numbers": numbers,
    }
    more = story["chart_spec"].get("more_charts") or []
    if any(c.get("type") == "map" for c in [story["chart_spec"], *more]):
        codes = {str(r.get("code")) for r in story["chart_data"]}
        if not mappable(codes):
            raise PublishError("a map chart needs geography codes that the site has boundaries for")
    if more:
        fm["more_charts"] = [display_spec(m) for m in more]
    if period.get("first") and period.get("last"):
        fm["period"] = en_dash(f"{period['first']} to {period['last']}")
    return fm


def render(story: dict[str, Any], fm: dict[str, Any]) -> str:
    head = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=100)
    note = (
        "# Written by worker/datatales/publish.py from the approved, verified story. Do not edit.\n"
    )
    return f"---\n{note}{head}---\n\n{en_dash(story['body_md'].strip())}\n"


def write_story_file(
    repo: Repo, story_id: str, out_dir: Path = SITE_STORIES, when: datetime | None = None
) -> Path:
    """Write the site file for an approved story. Does NOT change its status: call
    `mark_published` only after the file has been committed and pushed."""
    story = repo.get_story(story_id)
    if story["status"] != "approved":
        raise PublishError(
            f"only approved stories can be published (this one is {story['status']})"
        )
    if story["verify_status"] != "passed":
        raise PublishError("story has not passed verification")
    for field in ("headline", "hook", "summary", "body_md"):
        if not (story.get(field) or "").strip():
            raise PublishError(f"story has no {field}")
    when = when or now_utc()
    source, prov = provenance(repo, story)
    path = out_dir / f"{story['slug']}.md"
    text = render(story, front_matter(story, source, prov, when, first_published(path)))
    out_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def mark_published(repo: Repo, story_id: str, when: datetime | None = None) -> dict[str, Any]:
    story = repo.get_story(story_id)
    if story["status"] != "approved":
        raise PublishError(
            f"only approved stories can be marked published (it is {story['status']})"
        )
    stamp = (when or now_utc()).astimezone(UTC).isoformat()
    return repo.update_story(story_id, {"status": "published", "published_at": stamp})
