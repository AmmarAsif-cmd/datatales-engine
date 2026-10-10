"""The golden vectors file must match the Python implementation (see tests/golden_cases.py)."""

from tests.golden_cases import CASES, render


def test_golden_file_is_up_to_date() -> None:
    assert CASES.exists(), "run: uv run python -m tests.golden_cases --write"
    assert CASES.read_text(encoding="utf-8") == render(), (
        "golden vectors are stale; run: uv run python -m tests.golden_cases --write "
        "and make the dashboard's TypeScript tests pass"
    )
