import pytest

from datatales.clean.schema import RecipeError, parse_recipe_text, recipe_to_yaml
from datatales.config import WORKER_DIR

BASE = """
source: some-source
version: 1
description: test
checks:
  expected_columns: [a]
"""


def recipe(steps: str) -> str:
    return BASE + "steps:\n" + steps


def test_valid_recipe_parses_and_round_trips() -> None:
    r = parse_recipe_text(recipe("  - op: rename_columns\n    mapping: {x: a}\n"))
    assert r.steps[0].op == "rename_columns"
    assert parse_recipe_text(recipe_to_yaml(r)) == r


def test_json_is_accepted() -> None:
    text = (
        '{"source": "s", "version": 2, "description": "d", "checks": {"expected_columns": ["a"]},'
        ' "steps": [{"op": "sort", "by": ["a"]}]}'
    )
    assert parse_recipe_text(text).version == 2


@pytest.mark.parametrize(
    ("steps", "message"),
    [
        ("  - op: run_python\n    code: print(1)\n", "does not match any of the expected tags"),
        ("  - op: sort\n    by: [a]\n    sql: drop table x\n", "Extra inputs are not permitted"),
        ("  - op: sort\n    by: [a]\n  - op: skip_rows\n    count: 1\n", "must come before"),
        (
            "  - op: use_header_row\n  - op: skip_rows\n    count: 1\n",
            "at most once, in order",
        ),
        ("  - op: filter\n    where: {column: a, op: in, value: x}\n", "non-empty list"),
        ("  - op: filter\n    where: {column: a, op: is_null, value: 1}\n", "takes no value"),
        ("  - op: filter\n    where: {column: a, op: contains, value: 3}\n", "text value"),
        ("  - op: skip_rows\n    count: -1\n", "greater than or equal to 0"),
    ],
)
def test_invalid_recipes_are_rejected(steps: str, message: str) -> None:
    with pytest.raises(RecipeError, match=message):
        parse_recipe_text(recipe(steps))


def test_yaml_python_tags_cannot_build_objects() -> None:
    with pytest.raises(RecipeError, match="not valid YAML"):
        parse_recipe_text("!!python/object/apply:os.system ['echo hacked']")


def test_non_mapping_rejected() -> None:
    with pytest.raises(RecipeError, match="must be a mapping"):
        parse_recipe_text("- just a list")


def test_bad_source_slug_rejected() -> None:
    with pytest.raises(RecipeError, match="source"):
        parse_recipe_text(
            BASE.replace("some-source", "Bad Slug!") + "steps:\n  - op: strip_footnotes\n"
        )


def test_every_committed_recipe_is_valid() -> None:
    files = sorted((WORKER_DIR / "recipes").rglob("*.yaml"))
    assert files, "expected at least one recipe file"
    for f in files:
        parse_recipe_text(f.read_text(encoding="utf-8"))
