"""Cleaning recipe schema: declarative, whitelisted steps only.

A recipe is data, never code. Every step is one of the models below (selected by `op`),
unknown keys are rejected, and the runner maps each op to a fixed pandas function.
Recipes are loaded with yaml.safe_load, so YAML tags cannot construct Python objects.
"""

from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from datatales.errors import UserError
from datatales.sources import Slug

Col = Annotated[str, Field(min_length=1, max_length=200)]
Cols = Annotated[list[Col], Field(min_length=1, max_length=200)]
Scalar = str | int | float
ONS_MARKERS = ["[x]", "[c]", "[u]", "[w]", "[z]", "[low]", "[d]", "..", ":"]


class _Step(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- structural steps (must come first, in this order) ----


class SelectSheet(_Step):
    op: Literal["select_sheet"]
    sheet: str | Annotated[int, Field(ge=0)]


class SkipRows(_Step):
    op: Literal["skip_rows"]
    count: Annotated[int, Field(ge=0, le=10_000)]


class UseHeaderRow(_Step):
    """Row (0-based, after skip_rows) holding column names. `rows` > 1 joins stacked headers."""

    op: Literal["use_header_row"]
    row: Annotated[int, Field(ge=0, le=1_000)] = 0
    rows: Annotated[int, Field(ge=1, le=3)] = 1


# ---- row/column steps ----


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    column: Col
    op: Literal[
        "eq", "ne", "in", "not_in", "is_null", "not_null",
        "startswith", "contains", "gt", "ge", "lt", "le",
    ]  # fmt: skip
    value: Scalar | list[Scalar] | None = None

    @model_validator(mode="after")
    def _value_matches_op(self) -> "Condition":
        if self.op in ("is_null", "not_null"):
            if self.value is not None:
                raise ValueError(f"'{self.op}' takes no value")
        elif self.op in ("in", "not_in"):
            if not isinstance(self.value, list) or not self.value:
                raise ValueError(f"'{self.op}' needs a non-empty list value")
        elif self.value is None or isinstance(self.value, list):
            raise ValueError(f"'{self.op}' needs a single value")
        if self.op in ("startswith", "contains") and not isinstance(self.value, str):
            raise ValueError(f"'{self.op}' needs a text value")
        return self


class RenameColumns(_Step):
    op: Literal["rename_columns"]
    mapping: Annotated[dict[Col, Col], Field(min_length=1)]


class DropColumns(_Step):
    op: Literal["drop_columns"]
    columns: Cols


class SelectColumns(_Step):
    op: Literal["select_columns"]
    columns: Cols


class DropRowsWhere(_Step):
    op: Literal["drop_rows_where"]
    where: Condition


class Filter(_Step):
    """Keep only rows matching the condition."""

    op: Literal["filter"]
    where: Condition


class StripFootnotes(_Step):
    """Remove '[note N]' markers from names/cells and drop note/source rows."""

    op: Literal["strip_footnotes"]


class ParseNumber(_Step):
    """'£1,200' -> 1200, '12.5%' -> 12.5, markers -> null. Unparseable text fails by default."""

    op: Literal["parse_number"]
    columns: Cols
    markers: list[str] = Field(default_factory=lambda: list(ONS_MARKERS), max_length=50)
    on_error: Literal["fail", "null"] = "fail"


class ParseDate(_Step):
    op: Literal["parse_date"]
    column: Col
    format: Literal[
        "yyyy-mm-dd", "dd/mm/yyyy", "d mon yyyy", "mon yyyy", "yyyy-mm", "yyyy",
        "financial_year_start", "quarter_start",
    ]  # fmt: skip
    into: Col | None = None


class Melt(_Step):
    """Wide -> long: columns not in id_columns become (var_name, value_name) rows."""

    op: Literal["melt"]
    id_columns: Cols
    var_name: Col = "variable"
    value_name: Col = "value"


class Cast(_Step):
    op: Literal["cast"]
    columns: Annotated[
        dict[Col, Literal["str", "int", "float", "bool", "date"]], Field(min_length=1)
    ]


class Dedupe(_Step):
    op: Literal["dedupe"]
    columns: Cols | None = None
    keep: Literal["first", "last"] = "first"


class Sort(_Step):
    op: Literal["sort"]
    by: Cols
    descending: bool = False


class ClassifyPrefix(_Step):
    """New column from the start of a code, e.g. ONS geography E12 -> 'region'."""

    op: Literal["classify_prefix"]
    column: Col
    into: Col
    mapping: Annotated[
        dict[Annotated[str, Field(min_length=1, max_length=20)], str], Field(min_length=1)
    ]
    default: str | None = None


Step = Annotated[
    SelectSheet | SkipRows | UseHeaderRow | RenameColumns | DropColumns | SelectColumns
    | DropRowsWhere | Filter | StripFootnotes | ParseNumber | ParseDate | Melt | Cast
    | Dedupe | Sort | ClassifyPrefix,
    Field(discriminator="op"),
]  # fmt: skip

STRUCTURAL_ORDER = ("select_sheet", "skip_rows", "use_header_row")


# ---- validation checks ----


class Range(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: float | None = None
    max: float | None = None


class RowCount(BaseModel):
    model_config = ConfigDict(extra="forbid")
    min: Annotated[int, Field(ge=0)] = 1
    max: Annotated[int, Field(ge=1)] | None = None


class SumCheck(BaseModel):
    """Within each group, values (optionally only where column in values) sum to target."""

    model_config = ConfigDict(extra="forbid")
    name: str
    value: Col
    group_by: Cols
    where_column: Col | None = None
    where_in: list[Scalar] | None = None
    target: float
    tolerance: Annotated[float, Field(ge=0)] = 0.5
    complete_groups_only: bool = True


class Checks(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_columns: Cols
    row_count: RowCount = Field(default_factory=RowCount)
    not_null: list[Col] = Field(default_factory=list)
    unique: list[Col] = Field(default_factory=list)
    ranges: dict[Col, Range] = Field(default_factory=dict)
    sums: list[SumCheck] = Field(default_factory=list)


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: Slug
    version: Annotated[int, Field(ge=1)]
    description: Annotated[str, Field(max_length=2_000)]
    steps: Annotated[list[Step], Field(min_length=1, max_length=100)]
    checks: Checks

    @model_validator(mode="after")
    def _structural_steps_first(self) -> "Recipe":
        ops = [s.op for s in self.steps]
        structural = [op for op in ops if op in STRUCTURAL_ORDER]
        if ops[: len(structural)] != structural:
            raise ValueError(f"{', '.join(STRUCTURAL_ORDER)} must come before all other steps")
        if structural != sorted(structural, key=STRUCTURAL_ORDER.index) or len(
            set(structural)
        ) != len(structural):
            raise ValueError(
                f"structural steps must appear at most once, in order: {STRUCTURAL_ORDER}"
            )
        return self


class RecipeError(UserError, ValueError):
    pass


def parse_recipe_text(text: str) -> Recipe:
    """Parse YAML or JSON (JSON is valid YAML) safely and validate."""
    try:
        data: Any = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RecipeError(f"not valid YAML/JSON: {exc}") from None
    if not isinstance(data, dict):
        raise RecipeError(
            "recipe must be a mapping with source, version, description, steps, checks"
        )
    try:
        return Recipe.model_validate(data)
    except ValueError as exc:
        raise RecipeError(str(exc)) from None


def recipe_to_yaml(recipe: Recipe) -> str:
    data = recipe.model_dump(mode="json", exclude_defaults=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)
