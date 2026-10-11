"""Automatic story drafting with a fake Claude (no network), on MemRepo with FAKE data."""

import json
from types import SimpleNamespace
from typing import Any

from datatales import autodraft, stories
from datatales.llm import LLMClient, load_llm_config
from tests.memrepo import MemRepo
from tests.test_stories import repo_ct, riser_reply  # noqa: F401  (fixture re-export)


def sdk_reply(payload: dict[str, Any] | str) -> SimpleNamespace:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(
            input_tokens=900, output_tokens=1500, cache_creation_input_tokens=0,
            cache_read_input_tokens=4000,
        ),
        stop_reason="end_turn",
    )  # fmt: skip


class FakeSDK:
    def __init__(self, *replies: Any) -> None:
        self.replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        r = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return r(self.requests) if callable(r) else r


def llm(repo: MemRepo, sdk: FakeSDK, budget: float = 5.0) -> LLMClient:
    cfg = load_llm_config().model_copy(update={"monthly_budget_gbp": budget})
    return LLMClient(repo, cfg, client=sdk, api_key="test")


def bad(reply: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(reply).replace("6.9 in 2014-15", "7.1 in 2014-15"))


def test_draft_passes_first_time(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    sdk = FakeSDK(sdk_reply(riser_reply(story)))
    out = autodraft.draft_story(repo, llm(repo, sdk), story["id"], lambda _m: None)
    assert (out.status, out.attempts) == ("passed", 1)
    saved = repo.get_story(story["id"])
    assert saved["drafted_by"] == "claude" and saved["verify_status"] == "passed"
    assert saved["status"] == "draft" and saved["draft_note"] is None
    req = sdk.requests[0]
    assert req["model"] == "claude-opus-5-5"
    assert "Rules (follow every one)" in req["system"][0]["text"]  # cached fixed part
    assert req["messages"][0]["content"].startswith('<data name="story_data">')
    assert "## CHART DATA" in req["messages"][0]["content"]
    assert req["output_config"]["format"]["schema"]["required"][0] == "headline"
    (call,) = repo.llm_calls.values()
    assert call["status"] == "ok" and call["related_id"] == story["id"]


def test_failed_verification_retries_once_with_the_report(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
) -> None:
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    sdk = FakeSDK(sdk_reply(bad(riser_reply(story))), sdk_reply(riser_reply(story)))
    out = autodraft.draft_story(repo, llm(repo, sdk), story["id"], lambda _m: None)
    assert (out.status, out.attempts) == ("passed", 2)
    retry = sdk.requests[1]["messages"][0]["content"]
    assert '<data name="verify_report">' in retry and "7.1" in retry
    assert len(repo.llm_calls) == 2


def test_two_failures_mark_the_story_failed_with_its_report(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
) -> None:
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    sdk = FakeSDK(sdk_reply(bad(riser_reply(story))))
    out = autodraft.draft_story(repo, llm(repo, sdk), story["id"], lambda _m: None)
    assert out.status == "failed"
    saved = repo.get_story(story["id"])
    assert saved["status"] == "failed" and saved["verify_status"] == "failed"
    assert saved["verify_report"]["unmatched"] == [] or saved["verify_report"]["claims"]
    assert saved["draft_note"] == autodraft.NOTE_FAILED
    # a failed story can still be fixed by copy-paste
    fixed, report = stories.paste_narration(repo, story["id"], json.dumps(riser_reply(story)))
    assert report.passed and fixed["status"] == "draft" and fixed["drafted_by"] == "manual"


def test_invalid_reply_is_retried_with_the_reason(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    too_short = {**riser_reply(story), "body_md": "Too short. " * 20}
    sdk = FakeSDK(sdk_reply(too_short), sdk_reply(riser_reply(story)))
    out = autodraft.draft_story(repo, llm(repo, sdk), story["id"], lambda _m: None)
    assert out.status == "passed"
    assert '<data name="rejection">' in sdk.requests[1]["messages"][0]["content"]
    assert [c["status"] for c in repo.llm_calls.values()] == ["invalid_output", "ok"]


def test_budget_reached_leaves_the_draft_for_copy_paste(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
) -> None:
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    sdk = FakeSDK(sdk_reply(riser_reply(story)))
    out = autodraft.draft_story(repo, llm(repo, sdk, budget=0.0001), story["id"], lambda _m: None)
    assert out.status == "budget" and sdk.requests == []
    saved = repo.get_story(story["id"])
    assert saved["draft_note"] == autodraft.NOTE_BUDGET and saved["verify_status"] == "pending"


def test_auto_draft_shortlist_then_skip_unchanged(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    picks = stories.candidates_for(repo, ct)
    probe = stories.create_story(repo, ct, 1)  # same candidate -> its reply keys
    good = riser_reply(probe)
    repo.stories.pop(probe["id"])

    sdk = FakeSDK(sdk_reply(good))
    first = autodraft.auto_draft_clean_table(repo, ct, lambda _m: None, llm(repo, sdk))
    assert len(first.outcomes) == len(picks)
    assert first.outcomes[0].status == "passed"  # Riser
    made = repo.list_stories()
    assert len(made) == len(picks)
    assert all(s["data_version"] == ct and s["candidate_key"] for s in made)

    calls = len(sdk.requests)
    again = autodraft.auto_draft_clean_table(repo, ct, lambda _m: None, llm(repo, sdk))
    assert {o.status for o in again.outcomes} == {"skipped"}
    assert len(sdk.requests) == calls and len(repo.list_stories()) == len(picks)


def test_no_key_creates_drafts_for_copy_paste(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    summary = autodraft.auto_draft_clean_table(repo, ct, lambda _m: None, None)
    assert {o.status for o in summary.outcomes} == {"error"}
    assert all(s["draft_note"] == autodraft.NOTE_NO_KEY for s in repo.list_stories())


def test_changed_data_refreshes_and_redrafts(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    good = riser_reply(story)
    stories.paste_narration(repo, story["id"], json.dumps(good))
    # pretend the story was built from an older clean table with other findings
    other = [f["id"] for f in repo.list_findings(ct) if f["id"] not in story["finding_ids"]][:1]
    repo.update_story(story["id"], {"data_version": "old-clean-table", "finding_ids": other})

    sdk = FakeSDK(sdk_reply(good))
    summary = autodraft.auto_draft_clean_table(repo, ct, lambda _m: None, llm(repo, sdk))
    riser = next(o for o in summary.outcomes if o.story_id == story["id"])
    assert riser.status == "passed"
    saved = repo.get_story(story["id"])
    assert saved["data_version"] == ct and saved["drafted_by"] == "claude"
    assert saved["slug"] == story["slug"] or saved["slug"].startswith("riser")


def test_rejected_story_is_not_redrafted(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    stories.set_status(repo, story["id"], "rejected")
    other = [f["id"] for f in repo.list_findings(ct) if f["id"] not in story["finding_ids"]][:1]
    repo.update_story(story["id"], {"data_version": "old", "finding_ids": other})
    sdk = FakeSDK(sdk_reply(riser_reply(story)))
    summary = autodraft.auto_draft_clean_table(repo, ct, lambda _m: None, llm(repo, sdk))
    mine = next(o for o in summary.outcomes if o.story_id == story["id"])
    assert mine.status == "skipped" and "rejected" in mine.detail


def test_two_rejected_replies_change_nothing(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    good = riser_reply(story)
    stories.paste_narration(repo, story["id"], json.dumps(good))  # verified manual text
    empty = {**good, "summary": "", "video_script": ""}
    sdk = FakeSDK(sdk_reply(empty))
    out = autodraft.draft_story(repo, llm(repo, sdk), story["id"], lambda _m: None)
    assert out.status == "failed" and out.detail == autodraft.NOTE_REJECTED
    saved = repo.get_story(story["id"])
    assert saved["status"] == "draft" and saved["verify_status"] == "passed"  # untouched
    assert saved["drafted_by"] == "manual" and saved["summary"] == good["summary"]
    assert saved["draft_note"] == autodraft.NOTE_REJECTED
    # the start of each rejected reply is logged so the failure can be diagnosed
    errors = [c["error"] for c in repo.llm_calls.values()]
    assert all("--- reply (start) ---" in e and '"summary": ""' in e for e in errors)


def test_the_user_turn_asks_for_the_story(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    from datatales.narrate import STORY_REQUEST

    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    sdk = FakeSDK(sdk_reply(riser_reply(story)))
    autodraft.draft_story(repo, llm(repo, sdk), story["id"], lambda _m: None)
    content = sdk.requests[0]["messages"][0]["content"]
    assert content.endswith(STORY_REQUEST) and content.index("</data>") < content.index("Write the")
    props = sdk.requests[0]["output_config"]["format"]["schema"]["properties"]
    assert "strongest finding" in props["headline"]["description"]


def _count_unions(node: Any) -> int:
    if isinstance(node, dict):
        here = 1 if ("anyOf" in node or isinstance(node.get("type"), list)) else 0
        return here + sum(_count_unions(v) for v in node.values())
    if isinstance(node, list):
        return sum(_count_unions(v) for v in node)
    return 0


def test_schema_requires_every_field_and_has_no_unions() -> None:
    from datatales.narrate import narration_json_schema, normalise_api_reply, parse_narration

    schema = narration_json_schema()
    assert _count_unions(schema) == 0  # the API allows at most 16 union-typed fields
    spec = schema["properties"]["more_charts"]["items"]
    assert set(spec["required"]) == set(spec["properties"])  # series can never be left out
    check = schema["properties"]["claims"]["items"]["properties"]["checks"]["items"]
    assert set(check["required"]) == {"kind", "group", "period", "start", "end"}

    blank = {"annotation": "", "title": "", "yLabel": "", "start": "", "end": "", "period": ""}
    reply = {
        "headline": "North rose the most of all areas", "hook": "North rose from 7.0 to 7.4.",
        "summary": "North rose from 7.0 to 7.4 between 2011-12 and 2012-13.",
        "body_md": "## How it compares\n\nx\n\n## What the data can't tell us\n\n" + "word " * 500,
        "video_script": "North rose.",
        "chart_spec": {"type": "line", "x": "period", "y": "value", "series": "geography",
                       "highlight": ["North"], **blank},
        "more_charts": [{"type": "slope", "x": "period", "y": "value", "series": "geography",
                         "highlight": [], **blank}],
        "claims": [{"sentence": "North rose from 7.0 to 7.4.", "keys": ["a"],
                    "checks": [{"kind": "all_rise", "group": "", "period": "",
                                "start": "2011-12", "end": "2012-13"}]}],
    }  # fmt: skip
    chart = [{"period": "2011-12", "geography": "North", "value": 7.0},
             {"period": "2012-13", "geography": "North", "value": 7.4}]  # fmt: skip
    norm = normalise_api_reply(reply)
    assert norm["chart_spec"] == {"type": "line", "x": "period", "y": "value",
                                  "series": "geography", "highlight": "North"}  # fmt: skip
    assert "highlight" not in norm["more_charts"][0]
    assert norm["claims"][0]["checks"][0] == {
        "kind": "all_rise",
        "start": "2011-12",
        "end": "2012-13",
    }
    n = parse_narration(json.dumps(norm), chart)
    assert n.claims[0].checks[0].group is None and n.more_charts[0].series == "geography"


ORDER = [
    "headline", "hook", "summary", "body_md", "video_script", "chart_spec", "more_charts", "claims",
]  # fmt: skip

# JSON Schema keywords structured output accepts (anything else is rejected by the API)
ALLOWED_KEYWORDS = {
    "type", "properties", "required", "additionalProperties", "items", "enum", "description",
    "anyOf", "allOf", "const", "minItems", "$ref", "$defs", "format",
}  # fmt: skip


def _keywords(node: Any, inside_properties: bool = False) -> set[str]:
    out: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if not inside_properties:
                out.add(k)
            out |= _keywords(v, inside_properties=(k == "properties" and not inside_properties))
    elif isinstance(node, list):
        for v in node:
            out |= _keywords(v)
    return out


def test_schema_order_claims_last_and_dashboard_copy_identical() -> None:
    from datatales.llm import DASHBOARD_SCHEMA
    from datatales.narrate import narration_json_schema

    schema = narration_json_schema()
    # structured output writes fields in schema order: claims copy sentences from the text
    # fields, so they must come last (an alphabetical order once put claims before headline)
    assert list(schema["properties"]) == ORDER and schema["required"] == ORDER
    synced = json.loads(DASHBOARD_SCHEMA.read_text(encoding="utf-8"))
    assert synced == schema and list(synced["properties"]) == ORDER


def test_schema_uses_only_supported_keywords() -> None:
    from datatales.narrate import narration_json_schema

    schema = narration_json_schema()
    assert _keywords(schema) <= ALLOWED_KEYWORDS, _keywords(schema) - ALLOWED_KEYWORDS
    assert _count_unions(schema) <= 16
    min_items = [n["minItems"] for n in _walk(schema) if "minItems" in n]
    assert set(min_items) <= {0, 1}  # the API accepts only 0 or 1


def _walk(node: Any) -> list[dict[str, Any]]:
    if isinstance(node, dict):
        return [node, *[x for v in node.values() for x in _walk(v)]]
    if isinstance(node, list):
        return [x for v in node for x in _walk(v)]
    return []


def test_failing_redraft_never_overwrites_verified_text(
    repo_ct: tuple[MemRepo, str],  # noqa: F811
) -> None:
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    good = riser_reply(story)
    stories.paste_narration(repo, story["id"], json.dumps(good))  # verified manual text
    one_claim = {**good, "claims": good["claims"][:1]}  # what the sorted schema produced
    sdk = FakeSDK(sdk_reply(one_claim))
    out = autodraft.draft_story(repo, llm(repo, sdk), story["id"], lambda _m: None)
    assert out.status == "failed" and out.detail == autodraft.NOTE_KEPT
    saved = repo.get_story(story["id"])
    assert saved["status"] == "draft" and saved["verify_status"] == "passed"
    assert saved["drafted_by"] == "manual" and saved["body_md"] == good["body_md"].strip()
    retry = sdk.requests[1]["messages"][0]["content"]
    assert "have no claim, but you gave only 1 claim(s)" in retry


def test_good_redraft_replaces_verified_text(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    good = riser_reply(story)
    stories.paste_narration(repo, story["id"], json.dumps(good))
    better = {**good, "hook": "Life satisfaction in Riser rose from 6.0 to 6.9."}
    out = autodraft.draft_story(
        repo, llm(repo, FakeSDK(sdk_reply(better))), story["id"], lambda _m: None
    )
    assert out.status == "passed" and repo.get_story(story["id"])["drafted_by"] == "claude"
