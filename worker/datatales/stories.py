"""Story drafts: candidate -> draft (numbers + chart data) -> prompt -> pasted reply -> verify."""

import re
import unicodedata
import uuid
from typing import Any

from datatales.candidates import Candidate, shortlist
from datatales.errors import UserError
from datatales.narrate import build_prompt, parse_narration
from datatales.repo import Repo
from datatales.sources import get_source
from datatales.storydata import build_story_data
from datatales.verify import TEXT_FIELDS, Report, verify_text

LOCKED = ("approved", "published")


class StoryError(UserError):
    pass


def slugify(text: str, max_len: int = 80) -> str:
    text = re.sub(r"[‐-―−/]", " ", text)  # en/em dashes and slashes separate words
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "story"


def unique_slug(repo: Repo, base: str, story_id: str) -> str:
    slug, n = base, 2
    while (owner := repo.story_id_for_slug(slug)) and owner != story_id:
        slug, n = f"{base[:75]}-{n}", n + 1
    return slug


def candidates_for(repo: Repo, clean_table_id: str) -> list[Candidate]:
    findings = repo.list_findings(clean_table_id)
    if not findings:
        raise StoryError(f"no findings for clean table {clean_table_id}; run `detect` first")
    return shortlist(findings)


def create_story(repo: Repo, clean_table_id: str, index: int) -> dict[str, Any]:
    """Draft a story from shortlist candidate number `index` (1-based)."""
    from datatales.pipeline import read_parquet

    picks = candidates_for(repo, clean_table_id)
    if not 1 <= index <= len(picks):
        raise StoryError(f"candidate must be 1 to {len(picks)}")
    cand = picks[index - 1]
    ct = repo.get_clean_table(clean_table_id)
    source = get_source(repo.get_dataset(ct.dataset_id).source_slug)
    if source.detect is None:
        raise StoryError(f"source {source.slug} has no detect config")
    clean = read_parquet(repo.get_object("clean", ct.parquet_path))
    chart_data, chart_spec, numbers = build_story_data(clean, source, source.detect, cand)
    draft_slug = f"draft-{slugify(cand.geography, 40)}-{uuid.uuid4().hex[:8]}"
    return repo.insert_story(
        {
            "finding_ids": cand.finding_ids,
            "slug": draft_slug,
            "headline": cand.title,
            "numbers": numbers,
            "chart_spec": chart_spec,
            "chart_data": chart_data,
            "status": "draft",
            "verify_status": "pending",
        }
    )


def story_prompt(repo: Repo, story_id: str) -> str:
    s = repo.get_story(story_id)
    return build_prompt(s["numbers"], s["chart_data"], s["chart_spec"])


def _editable(story: dict[str, Any]) -> None:
    if story["status"] in LOCKED:
        raise StoryError(f"story is {story['status']}; it can no longer be edited")


def paste_narration(repo: Repo, story_id: str, reply: str) -> tuple[dict[str, Any], Report]:
    story = repo.get_story(story_id)
    _editable(story)
    narration = parse_narration(reply, story["chart_data"])
    fields = {
        "headline": narration.headline,
        "hook": narration.hook,
        "summary": narration.summary,
        "body_md": narration.body_md,
        "video_script": narration.video_script,
    }
    report = verify_text(fields, story["numbers"])
    spec = narration.chart_spec.model_dump(exclude_none=True)
    updated = repo.update_story(
        story_id,
        {
            **fields,
            "slug": unique_slug(repo, slugify(narration.headline), story_id),
            "chart_spec": spec,
            "verify_status": report.status,
            "verify_report": report.to_json(),
            "status": "draft",
        },
    )
    return updated, report


def reverify(
    repo: Repo, story_id: str, edits: dict[str, str] | None = None
) -> tuple[dict[str, Any], Report]:
    """Re-run verification, optionally after editing text fields (dashboard edits)."""
    story = repo.get_story(story_id)
    _editable(story)
    edits = {k: v for k, v in (edits or {}).items() if k in TEXT_FIELDS}
    fields = {k: edits.get(k, story.get(k)) for k in TEXT_FIELDS}
    report = verify_text(fields, story["numbers"])
    updated = repo.update_story(
        story_id, {**edits, "verify_status": report.status, "verify_report": report.to_json()}
    )
    return updated, report
