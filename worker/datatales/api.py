"""JSON bridge for the local dashboard: `python -m datatales api <action>`.

Reads one JSON object on stdin, writes one JSON object on stdout:
  {"ok": true, "data": ...}  or  {"ok": false, "error": "..."}
The dashboard calls this (without a shell) so every rule, prompt and check has exactly
one implementation: the Python one.
"""

import json
import sys
import uuid
from collections.abc import Callable
from typing import Any

from datatales.errors import UserError
from datatales.repo import Repo


def _candidates(repo: Repo, p: dict[str, Any]) -> Any:
    from datatales.stories import candidates_for

    return [
        {
            "index": i,
            "title": c.title,
            "score": c.score,
            "geography": c.geography,
            "geo_level": c.geo_level,
            "good_news": c.good_news,
            "measures": c.measures,
            "finding_ids": c.finding_ids,
        }
        for i, c in enumerate(candidates_for(repo, p["clean_table_id"]), start=1)
    ]


def _story_new(repo: Repo, p: dict[str, Any]) -> Any:
    from datatales.stories import create_story

    return create_story(repo, p["clean_table_id"], int(p["candidate"]))


def _story_prompt(repo: Repo, p: dict[str, Any]) -> Any:
    from datatales.stories import story_prompt

    return {"prompt": story_prompt(repo, p["story_id"])}


def _story_paste(repo: Repo, p: dict[str, Any]) -> Any:
    from datatales.stories import paste_narration

    story, report = paste_narration(repo, p["story_id"], p["reply"])
    return {"story": story, "report": report.to_json()}


def _story_reverify(repo: Repo, p: dict[str, Any]) -> Any:
    from datatales.stories import reverify

    story, report = reverify(repo, p["story_id"], p.get("edits"), p.get("claims"))
    return {"story": story, "report": report.to_json()}


def _story_status(repo: Repo, p: dict[str, Any]) -> Any:
    from datatales.stories import set_status

    return set_status(repo, p["story_id"], p["status"])


def _recipe_approve(repo: Repo, p: dict[str, Any]) -> Any:
    from datatales.pipeline import approve_recipe

    recipe, path = approve_recipe(repo, p["source"], int(p["version"]), str(p["by"]))
    return {"version": recipe.version, "approved_by": recipe.approved_by, "file": str(path)}


ACTIONS: dict[str, Callable[[Repo, dict[str, Any]], Any]] = {
    "candidates": _candidates,
    "story-new": _story_new,
    "story-prompt": _story_prompt,
    "story-paste": _story_paste,
    "story-reverify": _story_reverify,
    "story-status": _story_status,
    "recipe-approve": _recipe_approve,
}


ID_FIELDS = ("story_id", "clean_table_id")


def handle(action: str, payload: dict[str, Any], repo: Repo) -> dict[str, Any]:
    if action not in ACTIONS:
        return {"ok": False, "error": f"unknown action '{action}'"}
    for name in ID_FIELDS:
        if name in payload:
            try:
                uuid.UUID(str(payload[name]))
            except ValueError:
                return {"ok": False, "error": f"{name} is not a valid id"}
    try:
        return {"ok": True, "data": ACTIONS[action](repo, payload)}
    except (UserError, ValueError, KeyError) as exc:
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else str(exc)
        return {"ok": False, "error": str(message)}
    except Exception as exc:  # noqa: BLE001 - the bridge must always answer in JSON
        return {"ok": False, "error": f"unexpected {type(exc).__name__}: {exc}"}


def main(action: str, repo_factory: Callable[[], Repo]) -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        if not isinstance(payload, dict):
            raise ValueError("request must be a JSON object")
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": f"bad request: {exc}"}))
        return 1
    result = handle(action, payload, repo_factory())
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result["ok"] else 1
