"""Automatic story drafting with the Claude API.

After `detect`, each shortlisted candidate (top 5, max 2 per place) gets a story draft:

* A candidate that already has a story is skipped, unless the data behind it changed (a new
  clean table): then that story is refreshed with the new data and redrafted. Rejected
  stories stay rejected; approved ones are left for you.
* Claude writes the narration from the same prompt as the copy-paste flow (fixed rules
  cached; numbers and chart data as untrusted data). The reply is validated strictly and the
  full verifier runs (numbers, claims, rank words, chart titles).
* Verification failed -> one retry with the verify report -> else status `failed`, with the
  report on the story. Budget reached or no key -> the draft waits for copy-paste.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from datatales.llm import BudgetReached, InvalidOutput, LLMClient, LLMError, untrusted
from datatales.narrate import (
    narration_data,
    narration_instructions,
    narration_json_schema,
    parse_narration,
)
from datatales.repo import Repo
from datatales.stories import (
    StoryError,
    apply_narration,
    candidate_key,
    candidates_for,
    create_story_from_candidate,
    refresh_story,
)
from datatales.verify import Report

MAX_ATTEMPTS = 2  # first draft + one retry with the verify report / rejection reason

NOTE_BUDGET = "Claude budget reached this month: use Copy prompt / Paste result."
NOTE_NO_KEY = "Claude is not configured (ANTHROPIC_API_KEY): use Copy prompt / Paste result."
NOTE_FAILED = (
    "Claude's draft failed verification twice. The report shows what to fix; edit and "
    "re-verify, regenerate, or use Copy prompt / Paste result."
)


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
    """The parts of a verify report the model needs to fix its draft (compact JSON)."""
    data = report.to_json()
    bad_claims = [c for c in data["claims"] if c["status"] != "ok"]
    keep = {
        "unmatched": data["unmatched"],
        "years_out_of_range": data["years_out_of_range"],
        "uncovered": data["uncovered"],
        "format_issues": data["format_issues"],
        "failed_claims": bad_claims,
    }
    return json.dumps({k: v for k, v in keep.items() if v}, ensure_ascii=False)


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
    for attempt in range(1, MAX_ATTEMPTS + 1):
        data = base + (f"\n\n{feedback}" if feedback else "")
        try:
            result = llm.call(
                "story",
                instructions=instructions,
                data=data,
                schema=narration_json_schema(),
                validate=lambda d: parse_narration(json.dumps(d), story["chart_data"]),
                related_id=story_id,
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

        _, report = apply_narration(repo, story_id, result.value, drafted_by="claude")
        if report.passed:
            log(f"  attempt {attempt}: verified ({report.checked} numbers checked)")
            return DraftOutcome(story_id, "passed", "", attempt)
        log(f"  attempt {attempt}: verification failed")
        feedback = (
            "Your previous draft failed verification. Fix every problem in this report and "
            "return the whole reply again (all fields, all claims):\n"
            + untrusted("verify_report", _report_feedback(report))
        )

    current = repo.get_story(story_id)
    fields: dict[str, Any] = {"draft_note": NOTE_FAILED}
    if current.get("verify_report"):  # a narration was saved: keep it, mark the story failed
        fields["status"] = "failed"
    repo.update_story(story_id, fields)
    return DraftOutcome(story_id, "failed", NOTE_FAILED, MAX_ATTEMPTS)


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
) -> AutoDraftSummary:
    """Create and draft stories for the shortlist of one clean table (see module docstring)."""
    summary = AutoDraftSummary()
    ct = repo.get_clean_table(clean_table_id)
    slug = repo.get_dataset(ct.dataset_id).source_slug
    existing: dict[str, dict[str, Any]] = {}
    for s in repo.list_stories(limit=500):
        key = _story_key(repo, s)
        if key and key not in existing:  # list is newest first
            existing[key] = s

    budget_hit = False
    for i, cand in enumerate(candidates_for(repo, clean_table_id), 1):
        key = candidate_key(slug, cand)
        label = f"[{i}] {cand.title}"
        story = existing.get(key)
        if story is not None:
            same_data = story.get("data_version") == clean_table_id or bool(
                set(story["finding_ids"]) & set(cand.finding_ids)
            )
            if same_data or story["status"] in ("rejected", "approved"):
                why = "same data" if same_data else f"story is {story['status']}"
                log(f"{label}: skipped ({why}; story {story['id']})")
                summary.outcomes.append(DraftOutcome(story["id"], "skipped", why))
                continue
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
        else:
            story = create_story_from_candidate(repo, clean_table_id, cand)
            log(f"{label}: new story {story['id']}")

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
