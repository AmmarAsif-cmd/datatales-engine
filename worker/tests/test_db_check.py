from datatales.db import EXPECTED_TABLES, CheckReport, evaluate_buckets, evaluate_security


def secure_row(name: str) -> dict:
    return {
        "table_name": name,
        "rls_enabled": True,
        "policy_count": 0,
        "anon_select": False,
        "auth_select": False,
    }


def test_all_tables_secure_passes() -> None:
    report = CheckReport()
    evaluate_security([secure_row(t) for t in EXPECTED_TABLES], report)
    assert report.passed
    assert len(report.ok_lines) == len(EXPECTED_TABLES)


def test_missing_table_fails() -> None:
    report = CheckReport()
    evaluate_security([secure_row(t) for t in EXPECTED_TABLES if t != "stories"], report)
    assert report.problems == ["table 'stories' is missing"]


def test_rls_off_policy_and_grants_all_reported() -> None:
    rows = [secure_row(t) for t in EXPECTED_TABLES]
    rows[0] |= {"rls_enabled": False, "policy_count": 1, "anon_select": True}
    report = CheckReport()
    evaluate_security(rows, report)
    assert len(report.problems) == 1
    problem = report.problems[0]
    assert "RLS is OFF" in problem and "policy" in problem and "anon can SELECT" in problem


def test_extra_table_without_rls_fails() -> None:
    rows = [secure_row(t) for t in EXPECTED_TABLES]
    rows.append(secure_row("scratch") | {"rls_enabled": False})
    report = CheckReport()
    evaluate_security(rows, report)
    assert report.problems == ["table 'scratch': RLS is OFF"]


def test_buckets_private_pass_and_public_or_missing_fail() -> None:
    report = CheckReport()
    evaluate_buckets({"raw": False, "clean": False}, report)
    assert report.passed

    report = CheckReport()
    evaluate_buckets({"raw": True}, report)
    assert report.problems == [
        "storage bucket 'raw' is PUBLIC (must be private)",
        "storage bucket 'clean' is missing",
    ]
