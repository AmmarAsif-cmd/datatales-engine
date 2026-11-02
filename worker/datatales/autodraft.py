"""Automatic story drafting with the Claude API.

After `detect`, each shortlisted candidate (top 5, max 2 per place) gets a story draft:

* A candidate that already has a story is skipped, unless the data behind it changed (a new
  clean table): then that story is refreshed with the new data and redrafted. Rejected
  stories stay rejected; approved ones are left for you.
* Claude writes the narration from the same prompt as the copy-paste flow (fixed rules
  cached; numbers and chart data as untrusted data). The reply is validated strictly and the
  full verifier runs (numbers, claims, rank words, chart titles).
* Verification failed -> one retry with the verify report -> else status `failed`, with the
  report on the story. Budget reached or no key -> the draft waits for copy-paste; a later
  run drafts it once Claude is available again.
* Quality and variety (config/stories.yaml): a table needs a trend (>= min_periods time
  points) and recent data (latest year within max_data_age_years); at most
  max_new_drafts_per_run drafts per dataset per run; no second story on an angle (same
  dataset and series) that is already published or approved.
"""

import io
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import yaml
from pydantic import BaseModel, ConfigDict, Field

from datatales.candidates import measure_of
from datatales.config import WORKER_DIR
from datatales.detect.prepare import prepare
from datatales.llm import BudgetReached, InvalidOutput, LLMClient, LLMError, untrusted
from datatales.narrate import (
    STORY_REQUEST,
    narration_data,
    narration_instructions,
    narration_json_schema,
    normalise_api_reply,
    parse_narration,
)
from datatales.repo import CleanTable, Repo
from datatales.sources import get_source
from datatales.stories import (
    StoryError,
    apply_narration,
    candidate_key,
    candidates_for,
    check_narration,
    create_story_from_candidate,
    refresh_story,
)
from datatales.verify import Report

MAX_ATTEMPTS = 2  # first draft + one retry with the verify report / rejection reason

NOTE_BUDGET = "Claude budget reached this month: use Copy prompt / Paste result."
NOTE_NO_KEY = "Claude is not configured (ANTHROPIC_API_KEY): use Copy prompt / Paste result."
NOTE_REJECTED = (
    "Claude's replies were rejected twice (incomplete or malformed), so nothing was changed. "
    "Try Regenerate with Claude again, or use Copy prompt / Paste result."
)
NOTE_KEPT = (
    "Claude's new draft failed verification twice, so your verified text was kept unchanged. "
    "Try Regenerate with Claude again, or edit by hand."
)
NOTE_FAILED = (
    "Claude's draft failed verification twice. The report shows what to fix; edit and "
    "re-verify, regenerate, or use Copy prompt / Paste result."
)


RULES_PATH = WORKER_DIR / "config" / "stories.yaml"
YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


class StoryRules(BaseModel):
    """config/stories.yaml: which candidates are worth a Claude draft."""

    model_config = ConfigDict(extra="forbid")
    min_periods: int = Field(3, ge=1)
    max_data_age_years: int = Field(3, ge=1)
    max_new_drafts_per_run: int = Field(2, ge=1, le=5)
    covered_days: int = Field(180, ge=0)
    distinct_series: bool = True  # one draft per series (angle) per dataset per run


def load_story_rules() -> StoryRules:
    return StoryRules.model_validate(yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")))


def table_gate(
    repo: Repo, ct: CleanTable, slug: str, rules: StoryRules, today: datetime | None = None
) -> str | None:
    """Why this clean table should get no drafts at all (None = fine): too few time points
    for a trend, or data too old to be news."""
    source = get_source(slug)
    if source.detect is None or not ct.parquet_path:
        return None
    clean = pd.read_parquet(io.BytesIO(repo.get_object("clean", ct.parquet_path)))
    frame, _ = prepare(clean, source.detect)
    labels = sorted({str(v) for v in frame["period_label"].unique()})
    if len(labels) < rules.min_periods:
        shown = ", ".join(labels[:3])
        return (
            f"the data has {len(labels)} time point(s) ({shown}); a story needs at least "
            f"{rules.min_periods} to show a trend"
        )
    years = [int(y) for label in labels for y in YEAR.findall(label)]
    year_now = (today or datetime.now(UTC)).year
    if years and max(years) < year_now - rules.max_data_age_years:
        return f"the latest data is from {max(years)}, too old to be news"
    return None


def _undrafted(story: dict[str, Any]) -> bool:
    """A draft that never got text (budget reached or no key at the time)."""
    return (
        story.get("status") == "draft"
        and story.get("verify_status") == "pending"
        and not story.get("drafted_by")
    )


def _series_of(story: dict[str, Any]) -> str | None:
    findings = (story.get("numbers") or {}).get("findings") or []
    return measure_of(findings[0]) if findings else None


def covered_angles(
    stories: list[dict[str, Any]],
    keys: dict[str, str],
    rules: StoryRules,
    now: datetime | None = None,
) -> dict[tuple[str, str], str]:
    """(source, series) -> id of a published/approved story on that angle, recent enough."""
    since = (now or datetime.now(UTC)) - timedelta(days=rules.covered_days)
    out: dict[tuple[str, str], str] = {}
    for s in stories:
        if s.get("status") not in ("published", "approved"):
            continue
        updated = s.get("updated_at")
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)
        if updated is not None and updated < since:
            continue
        series, key = _series_of(s), keys.get(s["id"])
        if series and key:
            out.setdefault((key.split("|", 1)[0], series), s["id"])
    return out


@dataclass
class DraftOutcome:
    story_id: str
    status: str  # passed | failed | budget | error | skipped
    detail: str = ""
    attempts: int = 0


@dataclass
class AutoDraftSummary:
    outcomes: list[DraftOutcome] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for o in self.outcomes if o.status == status)


def _report_feedback(report: Report) -> str:
    """The parts of a verify report the model needs to fix its draft: a plain summary first,
    then compact JSON."""
    data = report.to_json()
    lines = []
    unclaimed = [u for u in data["uncovered"]]
    if unclaimed:
        sentences = sorted({u["sentence"] for u in unclaimed})
        lines.append(
            f"{len(unclaimed)} number(s) or rank word(s) in {len(sentences)} sentence(s) have no "
            f"claim, but you gave only {len(data['claims'])} claim(s). Add one claim for EVERY "
            "sentence that contains a number or a rank word, copied exactly, in every field "
            "(headline, hook, summary, body_md, video_script, chart titles)."
        )
    bad_claims = [c for c in data["claims"] if c["status"] != "ok"]
    keep = {
        "unmatched": data["unmatched"],
        "years_out_of_range": data["years_out_of_range"],
        "uncovered": data["uncovered"],
        "format_issues": data["format_issues"],
        "failed_claims": bad_claims,
    }
    lines.append(json.dumps({k: v for k, v in keep.items() if v}, ensure_ascii=False))
    return "\n".join(lines)


def draft_story(
    repo: Repo, llm: LLMClient, story_id: str, log: Callable[[str], None] = print
) -> DraftOutcome:
    """Draft (or redraft) one story with Claude and verify it. Never raises for API problems:
    the outcome says what happened and the story keeps a note for the dashboard."""
    story = repo.get_story(story_id)
    instructions = narration_instructions()
    base = untrusted(
        "story_data", narration_data(story["numbers"], story["chart_data"], story["chart_spec"])
    )
    feedback = ""
    saved_text = False  # did Claude's narration get saved on the story in this run?
    # A redraft must never make a story worse: verified text stays unless the new draft passes.
    protect = story.get("verify_status") == "passed" and bool(story.get("body_md"))
    last_report: Report | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        data = base + (f"\n\n{feedback}" if feedback else "")
        try:
            result = llm.call(
                "story",
                instructions=instructions,
                data=data,
                schema=narration_json_schema(),
                validate=lambda d: parse_narration(
                    json.dumps(normalise_api_reply(d)), story["chart_data"]
                ),
                related_id=story_id,
                request=STORY_REQUEST,
            )
        except BudgetReached as exc:
            repo.update_story(story_id, {"draft_note": NOTE_BUDGET})
            return DraftOutcome(story_id, "budget", str(exc), attempt - 1)
        except InvalidOutput as exc:
            log(f"  attempt {attempt}: reply rejected: {exc}")
            feedback = (
                "Your previous reply was rejected for this reason; return the whole reply "
                f"again, fixed:\n{untrusted('rejection', str(exc))}"
            )
            continue
        except LLMError as exc:
            note = NOTE_NO_KEY if "ANTHROPIC_API_KEY" in str(exc) else f"Claude error: {exc}"
            repo.update_story(story_id, {"draft_note": note[:500]})
            return DraftOutcome(story_id, "error", str(exc), attempt - 1)

        _, _, report = check_narration(repo.get_story(story_id), result.value)
        last_report = report
        if report.passed or not protect:
            _, report = apply_narration(repo, story_id, result.value, drafted_by="claude")
            saved_text = True
        if report.passed:
            log(f"  attempt {attempt}: verified ({report.checked} numbers checked)")
            return DraftOutcome(story_id, "passed", "", attempt)
        log(f"  attempt {attempt}: verification failed")
        feedback = (
            "Your previous draft failed verification. Fix every problem in this report and "
            "return the whole reply again (all fields, all claims):\n"
            + untrusted("verify_report", _report_feedback(report))
        )

    if protect and last_report is not None:  # verified text kept; nothing overwritten
        repo.update_story(story_id, {"draft_note": NOTE_KEPT})
        return DraftOutcome(story_id, "failed", NOTE_KEPT, MAX_ATTEMPTS)
    if saved_text:  # Claude's text is on the story but failed verification
        repo.update_story(story_id, {"status": "failed", "draft_note": NOTE_FAILED})
        return DraftOutcome(story_id, "failed", NOTE_FAILED, MAX_ATTEMPTS)
    # Both replies were rejected before verification: the story keeps whatever it had.
    repo.update_story(story_id, {"draft_note": NOTE_REJECTED})
    return DraftOutcome(story_id, "failed", NOTE_REJECTED, MAX_ATTEMPTS)


def _story_key(repo: Repo, story: dict[str, Any]) -> str | None:
    """candidate_key for stories created before it was stored (worked out from the story)."""
    if story.get("candidate_key"):
        return str(story["candidate_key"])
    findings = repo.get_findings(story["finding_ids"][:1])
    if not findings:
        return None
    ct = repo.get_clean_table(findings[0]["clean_table_id"])
    slug = repo.get_dataset(ct.dataset_id).source_slug
    n = story.get("numbers") or {}
    direction = "good" if n.get("good_news") else "bad"
    return f"{slug}|{n.get('geo_level')}|{n.get('geography')}|{direction}"


def auto_draft_clean_table(
    repo: Repo,
    clean_table_id: str,
    log: Callable[[str], None] = print,
    llm: LLMClient | None = None,
    rules: StoryRules | None = None,
) -> AutoDraftSummary:
    """Create and draft stories for the shortlist of one clean table (see module docstring)."""
    summary = AutoDraftSummary()
    rules = rules or load_story_rules()
    ct = repo.get_clean_table(clean_table_id)
    slug = repo.get_dataset(ct.dataset_id).source_slug
    gate = table_gate(repo, ct, slug, rules)
    if gate:
        log(f"No story drafts for {slug}: {gate}")
        return summary
    stories_list = repo.list_stories(limit=500)
    keys: dict[str, str] = {}
    existing: dict[str, dict[str, Any]] = {}
    for s in stories_list:
        key = _story_key(repo, s)
        if key:
            keys[s["id"]] = key
            existing.setdefault(key, s)  # list is newest first
    covered = covered_angles(stories_list, keys, rules)

    budget_hit = False
    drafted = 0
    angles_this_run: set[tuple[str, str]] = set()
    for i, cand in enumerate(candidates_for(repo, clean_table_id), 1):
        key = candidate_key(slug, cand)
        label = f"[{i}] {cand.title}"
        story = existing.get(key)
        angle = (slug, measure_of(cand.lead["numbers"]))
        cover_id = covered.get(angle)
        skip = ""
        if cover_id and (story is None or story["id"] != cover_id):
            skip = f"angle already covered by story {cover_id}"
        elif rules.distinct_series and angle in angles_this_run:
            skip = "same angle as another draft in this run"
        elif drafted >= rules.max_new_drafts_per_run:
            skip = f"{rules.max_new_drafts_per_run} drafts already made for this dataset this run"
        if skip:
            log(f"{label}: skipped ({skip})")
            summary.outcomes.append(DraftOutcome(story["id"] if story else "", "skipped", skip))
            continue
        retry = False
        if story is not None:
            same_data = story.get("data_version") == clean_table_id or bool(
                set(story["finding_ids"]) & set(cand.finding_ids)
            )
            retry = same_data and _undrafted(story) and llm is not None and not budget_hit
            if retry:
                log(f"{label}: drafting story {story['id']} (never drafted)")
            elif same_data or story["status"] in ("rejected", "approved", "published"):
                why = "same data" if same_data else f"story is {story['status']}"
                log(f"{label}: skipped ({why}; story {story['id']})")
                summary.outcomes.append(DraftOutcome(story["id"], "skipped", why))
                continue
        if story is not None and not retry:
            log(f"{label}: data changed: refreshing story {story['id']}")
            repo.update_story(
                story["id"],
                {
                    "finding_ids": cand.finding_ids,
                    "data_version": clean_table_id,
                    "candidate_key": key,
                },
            )
            try:
                story = refresh_story(repo, story["id"])
            except StoryError as exc:
                log(f"{label}: could not refresh: {exc}")
                summary.outcomes.append(DraftOutcome(story["id"], "skipped", str(exc)))
                continue
        elif story is None:
            story = create_story_from_candidate(repo, clean_table_id, cand)
            log(f"{label}: new story {story['id']}")

        drafted += 1
        angles_this_run.add(angle)
        if llm is None or budget_hit:
            note = NOTE_BUDGET if budget_hit else NOTE_NO_KEY
            repo.update_story(story["id"], {"draft_note": note})
            summary.outcomes.append(
                DraftOutcome(story["id"], "budget" if budget_hit else "error", note)
            )
            continue
        outcome = draft_story(repo, llm, story["id"], log)
        log(f"{label}: {outcome.status}")
        summary.outcomes.append(outcome)
        budget_hit = outcome.status == "budget"
    return summary
