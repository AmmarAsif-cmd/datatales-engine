"""Actual Claude API cost from `llm_calls` (`python -m datatales llm-report`).

Costs are the estimates logged with each call (token usage x the prices in
config/llm.yaml, converted to GBP); compare with the Anthropic Console's usage page."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

COUNTED = ("ok", "invalid_output", "error")  # calls that reached the API


@dataclass
class Group:
    calls: int = 0
    failed: int = 0  # invalid_output or error
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    cost: float = 0.0


@dataclass
class Report:
    groups: dict[tuple[str, str], Group] = field(default_factory=dict)  # (task, model)
    blocked: int = 0  # budget_blocked attempts
    reserved: int = 0  # still `reserved` (a run that crashed mid-call)

    @property
    def total(self) -> float:
        return sum(g.cost for g in self.groups.values())


def build_report(rows: list[dict[str, Any]]) -> Report:
    report = Report()
    groups: dict[tuple[str, str], Group] = defaultdict(Group)
    for r in rows:
        status = r.get("status")
        if status == "budget_blocked":
            report.blocked += 1
            continue
        if status == "reserved":
            report.reserved += 1
        g = groups[(r.get("task") or "?", r.get("model") or "?")]
        if status in COUNTED:
            g.calls += 1
            g.failed += status != "ok"
        for key in ("input_tokens", "output_tokens", "cached_tokens", "cache_write_tokens"):
            setattr(g, key, getattr(g, key) + int(r.get(key) or 0))
        g.cost += float(r.get("estimated_cost") or 0)
    report.groups = dict(sorted(groups.items()))
    return report


def format_report(report: Report, period: str, budget: float | None = None) -> str:
    lines = [f"Claude API usage, {period} (estimated cost, GBP)", ""]
    if not report.groups:
        lines.append("No Claude calls.")
    header = (
        f"{'task':<10} {'model':<20} {'calls':>5} {'failed':>6} {'in':>9} {'out':>8} "
        f"{'cached':>9}  cost"
    )
    if report.groups:
        lines.append(header)
    for (task, model), g in report.groups.items():
        lines.append(
            f"{task:<10} {model:<20} {g.calls:>5} {g.failed:>6} {g.input_tokens:>9,} "
            f"{g.output_tokens:>8,} {g.cached_tokens:>9,}  £{g.cost:.4f}"
        )
    lines.append("")
    total = f"Total: £{report.total:.4f}"
    if budget:
        total += f" of £{budget:.2f} monthly budget ({report.total / budget:.0%})"
    lines.append(total)
    if report.blocked:
        lines.append(f"{report.blocked} call(s) were blocked by the budget guard.")
    if report.reserved:
        lines.append(f"{report.reserved} call(s) are still 'reserved' (worst case counted).")
    return "\n".join(lines)
