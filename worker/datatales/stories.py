"""Story drafts: candidate -> draft (numbers + chart data) -> prompt -> pasted reply -> verify."""

import re
import unicodedata
import uuid
from typing import Any

from datatales.candidates import Candidate, shortlist
from datatales.errors import UserError
from datatales.narrate import Claim, Narration, build_prompt, parse_narration
from datatales.repo import Repo
from datatales.sources import get_source
from datatales.storydata import build_story_data
from datatales.verify import TEXT_FIELDS, Report, chart_text, verify_text

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

    picks = candidates_for(repo, clean_table_id)
    if not 1 <= index <= len(picks):
        raise StoryError(f"candidate must be 1 to {len(picks)}")
    return create_story_from_candidate(repo, clean_table_id, picks[index - 1])


def candidate_key(source_slug: str, cand: Candidate) -> str:
    """What a story is about: one place, at one level, in one direction, from one source.
    Used to avoid drafting the same story twice."""
    direction = "good" if cand.good_news else "bad"
    return f"{source_slug}|{cand.geo_level}|{cand.geography}|{direction}"


def create_story_from_candidate(repo: Repo, clean_table_id: str, cand: Candidate) -> dict[str, Any]:
    from datatales.pipeline import read_parquet

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
            "candidate_key": candidate_key(source.slug, cand),
            "data_version": clean_table_id,
        }
    )


def story_slug(repo: Repo, story: dict[str, Any], headline: str) -> str:
    """Set once from the first headline, then fixed, so a published URL never changes when
    a story is revised and republished."""
    if not story["slug"].startswith("draft-"):
        return story["slug"]
    return unique_slug(repo, slugify(headline), story["id"])


def refresh_story(repo: Repo, story_id: str) -> dict[str, Any]:
    """Rebuild a story's numbers and chart data from its findings with the current logic
    (e.g. after improving story data). Text is kept but must be re-verified: the story goes
    back to draft with verification pending."""
    from datatales.candidates import Candidate
    from datatales.pipeline import read_parquet

    story = repo.get_story(story_id)
    if story["status"] == "approved":
        raise StoryError("story is approved; move it back to draft first")
    findings = repo.get_findings(story["finding_ids"])
    if len(findings) != len(story["finding_ids"]):
        raise StoryError("some of the story's findings no longer exist")
    findings.sort(key=lambda f: (-float(f["score"]), f["detector"], f["id"]))
    first = findings[0]["numbers"]
    cand = Candidate(
        str(first.get("group")), first.get("geo_level"), bool(first.get("good_news")), findings
    )
    ct = repo.get_clean_table(findings[0]["clean_table_id"])
    source = get_source(repo.get_dataset(ct.dataset_id).source_slug)
    if source.detect is None:
        raise StoryError(f"source {source.slug} has no detect config")
    clean = read_parquet(repo.get_object("clean", ct.parquet_path))
    chart_data, chart_spec, numbers = build_story_data(clean, source, source.detect, cand)
    fields: dict[str, Any] = {
        "numbers": numbers,
        "chart_data": chart_data,
        "chart_spec": {
            **chart_spec,
            **{
                k: v
                for k, v in (story.get("chart_spec") or {}).items()
                if k in ("title", "annotation", "more_charts")
            },
        },
        "status": "draft",
        "verify_status": "pending",
        "verify_report": None,
    }
    if story["status"] == "published":
        fields["published_at"] = None
    return repo.update_story(story_id, fields)


def story_prompt(repo: Repo, story_id: str) -> str:
    s = repo.get_story(story_id)
    return build_prompt(s["numbers"], s["chart_data"], s["chart_spec"])


def _editable(story: dict[str, Any]) -> None:
    if story["status"] in LOCKED:
        raise StoryError(f"story is {story['status']}; it can no longer be edited")


def story_fields(story: dict[str, Any], **override: Any) -> dict[str, str | None]:
    """The verified text fields of a story, including all chart titles and annotations."""
    fields = {k: story.get(k) for k in TEXT_FIELDS if k != "chart_text"}
    fields["chart_text"] = chart_text(story.get("chart_spec"))
    fields.update(override)
    return fields


def apply_narration(
    repo: Repo, story_id: str, narration: Narration, drafted_by: str = "manual"
) -> tuple[dict[str, Any], Report]:
    """Save a validated narration on a story and verify it (numbers, claims, rank words,
    chart titles). Used by the copy-paste flow and by Claude drafting alike."""
    story = repo.get_story(story_id)
    _editable(story)
    spec = narration.chart_spec.model_dump(exclude_none=True)
    if narration.more_charts:
        spec["more_charts"] = [m.model_dump(exclude_none=True) for m in narration.more_charts]
    fields = {
        "headline": narration.headline,
        "hook": narration.hook,
        "summary": narration.summary,
        "body_md": narration.body_md,
        "video_script": narration.video_script,
    }
    claims = [c.model_dump() for c in narration.claims]
    report = verify_text(
        story_fields(story, **fields, chart_text=chart_text(spec)),
        story["numbers"],
        claims,
        story["chart_data"],
    )
    updated = repo.update_story(
        story_id,
        {
            **fields,
            "slug": story_slug(repo, story, narration.headline),
            "chart_spec": spec,
            "verify_status": report.status,
            "verify_report": report.to_json(),
            "status": "draft",
            "drafted_by": drafted_by,
            "draft_note": None,
        },
    )
    return updated, report


def paste_narration(repo: Repo, story_id: str, reply: str) -> tuple[dict[str, Any], Report]:
    story = repo.get_story(story_id)
    _editable(story)
    return apply_narration(repo, story_id, parse_narration(reply, story["chart_data"]))


def stored_claims(story: dict[str, Any]) -> list[dict[str, Any]] | None:
    report = story.get("verify_report") or {}
    if not report.get("claims_checked"):
        return None
    return [
        {
            "sentence": c["sentence"],
            "keys": c["keys"],
            "checks": [
                {k: v for k, v in ch.items() if k not in ("ok", "detail")}
                for ch in c.get("checks", [])
            ],
        }
        for c in report.get("claims", [])
    ]


def reverify(
    repo: Repo,
    story_id: str,
    edits: dict[str, str] | None = None,
    claims: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], Report]:
    """Re-run verification after editing text fields and/or claims (dashboard edits)."""
    story = repo.get_story(story_id)
    _editable(story)
    edits = {k: v for k, v in (edits or {}).items() if k in TEXT_FIELDS and k != "chart_text"}
    fields = story_fields(story, **edits)
    if claims is not None:
        claims = [Claim.model_validate(c).model_dump() for c in claims]
    else:
        claims = stored_claims(story)
    if claims is None:
        raise StoryError("story has no claims; paste a narration reply that includes claims")
    report = verify_text(fields, story["numbers"], claims, story["chart_data"])
    updated = repo.update_story(
        story_id, {**edits, "verify_status": report.status, "verify_report": report.to_json()}
    )
    return updated, report


TRANSITIONS = {
    "draft": {"approved", "rejected"},
    "failed": {"draft", "rejected"},  # Claude's draft failed verification; fix by hand
    "rejected": {"draft"},
    "approved": {"draft"},
    "published": {"draft"},  # "Revise": the page stays live until it is republished
}


def set_status(repo: Repo, story_id: str, status: str) -> dict[str, Any]:
    """Review decisions. Approval needs a passed verification (the DB enforces this too)."""
    story = repo.get_story(story_id)
    allowed = TRANSITIONS.get(story["status"], set())
    if status not in allowed:
        raise StoryError(f"cannot move a {story['status']} story to {status}")
    if status == "approved" and story["verify_status"] != "passed":
        raise StoryError("only stories that passed verification can be approved")
    fields: dict[str, Any] = {"status": status}
    if story["status"] == "published":
        fields["published_at"] = None  # DB rule: published_at only while published
    return repo.update_story(story_id, fields)
