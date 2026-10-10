"""The dashboard's JSON bridge and story status rules, on MemRepo with FAKE data."""

import json

import pytest

from datatales import api, stories
from tests.memrepo import MemRepo
from tests.test_stories import repo_ct, riser_reply  # noqa: F401  (fixture re-export)


def call(repo: MemRepo, action: str, **payload: object) -> dict:
    return api.handle(action, payload, repo)


def test_unknown_action_and_bad_ids_answer_in_json() -> None:
    repo = MemRepo()
    assert call(repo, "drop-tables") == {"ok": False, "error": "unknown action 'drop-tables'"}
    assert call(repo, "story-prompt", story_id="nope")["error"] == "story_id is not a valid id"
    missing = call(repo, "story-prompt", story_id="00000000-0000-0000-0000-000000000000")
    assert missing["ok"] is False and "not found" in missing["error"]


def test_unexpected_errors_are_still_json(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_repo: object, _p: object) -> None:
        raise RuntimeError("disk on fire")

    monkeypatch.setitem(api.ACTIONS, "story-prompt", boom)
    out = call(MemRepo(), "story-prompt", story_id="00000000-0000-0000-0000-000000000000")
    assert out == {"ok": False, "error": "unexpected RuntimeError: disk on fire"}


def test_full_flow_through_the_bridge(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    cands = call(repo, "candidates", clean_table_id=ct)
    assert cands["ok"] and cands["data"][0]["geography"] == "Riser"

    story = call(repo, "story-new", clean_table_id=ct, candidate=1)["data"]
    assert "## KEYS" in call(repo, "story-prompt", story_id=story["id"])["data"]["prompt"]

    pasted = call(repo, "story-paste", story_id=story["id"], reply=json.dumps(riser_reply(story)))
    assert pasted["ok"] and pasted["data"]["report"]["status"] == "passed"

    edited = call(
        repo,
        "story-reverify",
        story_id=story["id"],
        edits={"hook": "Life satisfaction in Riser rose from 6.0 to 7.0."},
    )
    report = edited["data"]["report"]
    assert report["status"] == "failed"  # 7.0 is not in the data, and the claim no longer matches

    refused = call(repo, "story-status", story_id=story["id"], status="approved")
    assert refused == {
        "ok": False,
        "error": "only stories that passed verification can be approved",
    }


def test_status_transitions(repo_ct: tuple[MemRepo, str]) -> None:  # noqa: F811
    repo, ct = repo_ct
    story = stories.create_story(repo, ct, 1)
    stories.paste_narration(repo, story["id"], json.dumps(riser_reply(story)))
    assert stories.set_status(repo, story["id"], "approved")["status"] == "approved"
    with pytest.raises(stories.StoryError, match="cannot move a approved story to rejected"):
        stories.set_status(repo, story["id"], "rejected")
    assert stories.set_status(repo, story["id"], "draft")["status"] == "draft"
    assert stories.set_status(repo, story["id"], "rejected")["status"] == "rejected"
    with pytest.raises(stories.StoryError, match="cannot move"):
        stories.set_status(repo, story["id"], "published")
