"""Dataset discovery with fake catalogues and a fake Claude (no network)."""

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from datatales import discovery as d
from datatales.llm import LLMClient, load_llm_config
from tests.memrepo import MemRepo

OGL = "Open Government Licence v3.0"


def item(n: int, **over: Any) -> d.Item:
    base = {
        "title": f"Dataset {n} by local authority",
        "publisher": "Fake Office",
        "source_url": f"https://www.data.gov.uk/dataset/{n}/fake-{n}",
        "catalogue": "data_gov_uk",
        "catalogue_id": str(n),
        "licence": OGL,
        "formats": ["CSV"],
        "update_frequency": "monthly",
        "description": "Monthly counts for every local authority since 2015.",
        "last_updated": f"2026-10-0{n % 9 + 1}",
    }
    return d.Item(**{**base, **over})


def fetchers(items: list[d.Item]) -> dict[str, Any]:
    return {"fake": lambda _client, _cfg: [d.Item(**vars(i)) for i in items]}


def cfg(**over: Any) -> d.DiscoveryConfig:
    return d.load_config().model_copy(update=over)


def claude_reply(ratings: list[dict[str, Any]]) -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps({"ratings": ratings}))],
        usage=SimpleNamespace(input_tokens=3000, output_tokens=600,
                              cache_creation_input_tokens=0, cache_read_input_tokens=0),
        stop_reason="end_turn",
    )  # fmt: skip


class FakeSDK:
    def __init__(self, reply: Any) -> None:
        self.reply = reply
        self.requests: list[dict[str, Any]] = []
        self.messages = self

    def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def llm(repo: MemRepo, sdk: FakeSDK) -> LLMClient:
    return LLMClient(repo, load_llm_config(), client=sdk, api_key="test")


def rating(i: int, score: int, pitch: str = "Which places changed most, month by month.") -> dict:
    return {"id": str(i), "score": score, "pitch": pitch, "has_time_series": True,
            "geography_levels": ["local_authority"]}  # fmt: skip


@pytest.mark.parametrize(
    ("over", "reason"),
    [
        ({"licence": "Creative Commons Attribution"}, "not Open Government Licence"),
        ({"formats": ["PDF", "ZIP"]}, "no machine-readable format"),
        ({"title": "Organogram of staff roles and salaries"}, "personal"),
        ({"description": "Patient-level records for research."}, "personal"),
        ({"title": "Spend over £25,000"}, "administrative"),
        ({"title": "A map layer", "description": "Polygons.", "update_frequency": None},
         "no time series or geographic breakdown"),
    ],
)  # fmt: skip
def test_hard_filters(over: dict[str, Any], reason: str) -> None:
    it = d.annotate(item(1, **over))
    assert reason in (d.hard_filter(it, cfg(), set(), set()) or "")


def test_good_item_passes_and_known_ones_do_not() -> None:
    it = d.annotate(item(1))
    assert it.geography_levels == ["local_authority"] and it.has_time_series
    assert d.hard_filter(it, cfg(), set(), set()) is None
    assert "already" in d.hard_filter(it, cfg(), {it.source_url}, set())
    assert "same title" in d.hard_filter(it, cfg(), set(), {d._norm(it.title)})


def test_claude_scores_and_top_n_are_suggested() -> None:
    repo = MemRepo()
    items = [item(i) for i in range(6)]
    ratings = [rating(i, s) for i, s in enumerate([90, 40, 75, 60, 85, 20])]
    sdk = FakeSDK(claude_reply(ratings))
    summary = d.run_discovery(repo, lambda _m: None, llm(repo, sdk), fetchers(items),
                              cfg(suggestions_per_week=3, min_score=55))  # fmt: skip
    assert summary.scored_by == "claude" and summary.passed_filters == 6
    assert [r["score"] for r in summary.added] == [90, 85, 75]
    rows = repo.list_backlog("suggested")
    assert len(rows) == 3 and rows[0]["pitch"].startswith("Which places")
    assert rows[0]["licence"] == OGL and rows[0]["catalogue"] == "data_gov_uk"
    req = sdk.requests[0]
    assert req["model"] == "claude-haiku-5-5"
    assert req["messages"][0]["content"].startswith('<data name="candidates">')
    assert req["output_config"]["format"]["schema"] == d.SCORE_SCHEMA


def test_nothing_known_is_ever_suggested_again() -> None:
    repo = MemRepo()
    repo.insert_backlog([{**d._row(d.annotate(item(1)), 50, "x" * 20), "status": "rejected"}])
    sdk = FakeSDK(claude_reply([rating(0, 99)]))
    summary = d.run_discovery(repo, lambda _m: None, llm(repo, sdk),
                              fetchers([item(1), item(2)]), cfg())  # fmt: skip
    assert [r["catalogue_id"] for r in summary.added] == ["2"]
    assert summary.dropped == {"already a source or in the backlog": 1}
    # existing sources (sources.yaml) are known too
    urls, _ = d.known(repo)
    assert any("ons.gov.uk" in u for u in urls)


def test_bad_scores_fall_back_to_the_heuristic() -> None:
    repo = MemRepo()
    out_of_range = claude_reply([rating(0, 140)])
    summary = d.run_discovery(repo, lambda _m: None, llm(repo, FakeSDK(out_of_range)),
                              fetchers([item(0)]), cfg(min_score=0))  # fmt: skip
    assert summary.scored_by == "heuristic" and summary.added[0]["score"] <= 100
    assert [c["status"] for c in repo.llm_calls.values()] == ["invalid_output"]


def test_unknown_ids_are_rejected() -> None:
    validate = d._validate_ratings({"0"})
    with pytest.raises(ValueError, match="unknown candidate ids"):
        validate({"ratings": [rating(5, 50)]})


def test_without_a_key_the_heuristic_scores() -> None:
    repo = MemRepo()
    summary = d.run_discovery(repo, lambda _m: None, None, fetchers([item(0)]), cfg(min_score=0))
    assert summary.scored_by == "heuristic" and len(summary.added) == 1
    assert summary.added[0]["pitch"].startswith("Monthly counts")


def test_catalogue_failure_is_reported_and_the_other_still_runs() -> None:
    repo = MemRepo()

    def broken(_c: Any, _cfg: Any) -> list[d.Item]:
        raise httpx.ConnectError("down")

    both = {"broken": broken, **fetchers([item(0)])}
    summary = d.run_discovery(repo, lambda _m: None, None, both, cfg(min_score=0))
    assert summary.errors and "broken" in summary.errors[0] and len(summary.added) == 1


def test_only_allowed_hosts_are_fetched() -> None:
    with httpx.Client() as client, pytest.raises(d.DiscoveryError, match="refusing"):
        d._get_json(client, "https://evil.example.com/api", {})


def test_ckan_and_ons_records_are_normalised() -> None:
    ckan = d._ckan_item({
        "id": "abc", "name": "road-traffic", "title": " Road traffic ", "license_id": "uk-ogl",
        "organization": {"title": "Department for Transport"},
        "resources": [{"format": "csv"}, {"format": ".XLSX"}, {"format": ""}],
        "extras": [{"key": "update_frequency", "value": "annual"}],
        "metadata_modified": "2026-09-01T10:00:00",
    })  # fmt: skip
    assert ckan.title == "Road traffic" and ckan.formats == ["CSV", "XLSX"]
    assert ckan.source_url == "https://www.data.gov.uk/dataset/abc/road-traffic"
    assert d.is_ogl(ckan.licence) and ckan.update_frequency == "annual"


def test_seed_is_idempotent_and_vehicles_top() -> None:
    repo = MemRepo()
    assert d.seed_backlog(repo) >= 25
    assert d.seed_backlog(repo) == 0
    top = repo.list_backlog("suggested")[0]
    assert "Vehicle licensing" in top["title"] and top["publisher"] == "Department for Transport"
    assert all(r["licence"] == OGL and r["catalogue"] == "seed" for r in repo.list_backlog())
