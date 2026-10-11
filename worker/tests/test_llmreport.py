"""llm-report: actual Claude cost from llm_calls rows (FAKE rows)."""

from datatales.llmreport import build_report, format_report


def row(task: str, status: str, cost: float, model: str = "claude-sonnet-5-5") -> dict:
    return {"task": task, "model": model, "status": status, "input_tokens": 1000,
            "output_tokens": 200, "cached_tokens": 500, "cache_write_tokens": 0,
            "estimated_cost": cost}  # fmt: skip


def test_report_groups_by_task_and_model() -> None:
    rows = [
        row("recipe", "ok", 0.05),
        row("recipe", "invalid_output", 0.04),
        row("story", "ok", 0.30, "claude-opus-5-5"),
        row("story", "budget_blocked", 0),
        row("discovery", "reserved", 0.01, "claude-haiku-5-5"),
    ]
    r = build_report(rows)
    recipe = r.groups[("recipe", "claude-sonnet-5-5")]
    assert (recipe.calls, recipe.failed, recipe.input_tokens) == (2, 1, 2000)
    assert round(r.total, 4) == 0.40 and r.blocked == 1 and r.reserved == 1
    text = format_report(r, "October 2026 so far", 5.0)
    assert "Total: £0.4000 of £5.00 monthly budget (8%)" in text
    assert "1 call(s) were blocked" in text and "still 'reserved'" in text


def test_empty_report() -> None:
    assert "No Claude calls." in format_report(build_report([]), "last 7 day(s)")
