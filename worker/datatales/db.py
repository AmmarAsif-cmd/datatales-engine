"""Supabase client helpers and the database self-check."""

from dataclasses import dataclass, field
from typing import Any

from supabase import Client, create_client

from datatales.config import Settings

EXPECTED_TABLES = (
    "sources",
    "datasets",
    "recipes",
    "clean_tables",
    "findings",
    "stories",
    "jobs",
    "llm_calls",
    "dataset_backlog",
    "llm_budget_topups",
)
EXPECTED_BUCKETS = ("raw", "clean")


def get_client(settings: Settings) -> Client:
    return create_client(
        settings.supabase_url, settings.supabase_service_role_key.get_secret_value()
    )


@dataclass
class CheckReport:
    ok_lines: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.problems


def evaluate_security(rows: list[dict[str, Any]], report: CheckReport) -> None:
    """Check rows from public.dt_security_status(): tables exist, RLS on, nothing exposed."""
    by_name = {row["table_name"]: row for row in rows}
    for name in EXPECTED_TABLES:
        if name not in by_name:
            report.problems.append(f"table '{name}' is missing")
    for name, row in sorted(by_name.items()):
        issues = []
        if not row["rls_enabled"]:
            issues.append("RLS is OFF")
        if row["policy_count"]:
            issues.append(f"{row['policy_count']} policy(ies) exist (expected none)")
        if row["anon_select"]:
            issues.append("anon can SELECT")
        if row["auth_select"]:
            issues.append("authenticated can SELECT")
        if issues:
            report.problems.append(f"table '{name}': " + ", ".join(issues))
        elif name in EXPECTED_TABLES:
            report.ok_lines.append(f"table '{name}': RLS on, no policies, not exposed")
        else:
            report.ok_lines.append(f"table '{name}' (extra): RLS on, not exposed")


def evaluate_buckets(buckets: dict[str, bool], report: CheckReport) -> None:
    """`buckets` maps bucket name -> is_public."""
    for name in EXPECTED_BUCKETS:
        if name not in buckets:
            report.problems.append(f"storage bucket '{name}' is missing")
        elif buckets[name]:
            report.problems.append(f"storage bucket '{name}' is PUBLIC (must be private)")
        else:
            report.ok_lines.append(f"storage bucket '{name}': private")


def run_db_check(client: Client) -> CheckReport:
    report = CheckReport()

    try:
        rows = client.rpc("dt_security_status").execute().data or []
    except Exception as exc:  # network/auth/missing-migration errors all land here
        if "PGRST202" in str(exc):
            report.ok_lines.append("connected to Supabase with the service role")
            report.problems.append(
                "dt_security_status() not found: run supabase/migrations/0001_init.sql first"
            )
            return report
        report.problems.append(
            f"could not query the database ({type(exc).__name__}: {exc}). "
            "Check SUPABASE_URL / key, and that migration 0001_init.sql has been run."
        )
        return report
    report.ok_lines.append("connected to Supabase with the service role")
    evaluate_security(rows, report)

    for name in EXPECTED_TABLES:
        try:
            result = client.table(name).select("id", count="exact").limit(0).execute()
            report.ok_lines.append(f"table '{name}': reachable via API ({result.count} rows)")
        except Exception as exc:
            report.problems.append(f"table '{name}' not reachable via API: {exc}")

    try:
        buckets = {b.name: b.public for b in client.storage.list_buckets()}
    except Exception as exc:
        report.problems.append(f"could not list storage buckets: {exc}")
    else:
        evaluate_buckets(buckets, report)

    return report
