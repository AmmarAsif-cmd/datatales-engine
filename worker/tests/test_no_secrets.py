"""Guard: committed .env.example files must only ever hold empty placeholders."""

from pathlib import Path

import pytest

from datatales.config import parse_env_file

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_FILES = sorted(REPO_ROOT.glob("*/.env.example"))


def test_example_files_found() -> None:
    assert EXAMPLE_FILES, "expected at least one .env.example in the repo"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_env_example_has_no_values(path: Path) -> None:
    filled = [k for k, v in parse_env_file(path.read_text(encoding="utf-8-sig")).items() if v]
    assert not filled, f"{path.name} must not contain values; found values for: {filled}"
