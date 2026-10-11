"""Guard: committed example env files must only ever hold empty placeholders."""

from pathlib import Path

import pytest

from datatales.config import parse_env_file

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_FILES = sorted([*REPO_ROOT.glob("*/.env.example"), *REPO_ROOT.glob("*/.dev.vars.example")])

# Public, non-secret settings that may be pre-filled in examples.
NON_SECRET = {"GITHUB_REPO"}


def test_example_files_found() -> None:
    assert EXAMPLE_FILES, "expected at least one .env.example in the repo"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_env_example_has_no_values(path: Path) -> None:
    filled = [
        k
        for k, v in parse_env_file(path.read_text(encoding="utf-8-sig")).items()
        if v and k not in NON_SECRET
    ]
    assert not filled, f"{path.name} must not contain values; found values for: {filled}"


SKIP_DIRS = {".git", "node_modules", ".venv", "dist", ".open-next", ".wrangler", ".next", ".astro"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".mjs", ".js", ".json", ".yaml", ".yml", ".md", ".toml",
                 ".sql", ".astro", ".css", ".txt", ".example", ".jsonc", ".html"}  # fmt: skip


def test_no_anthropic_key_anywhere_in_the_repo() -> None:
    """An Anthropic API key (sk-ant-...) must never be committed in any text file."""
    from datatales.llm import KEY_PATTERN

    hits = []
    for path in REPO_ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        if KEY_PATTERN.search(path.read_text(encoding="utf-8", errors="ignore")):
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert not hits, f"possible Anthropic API key in: {hits}"
