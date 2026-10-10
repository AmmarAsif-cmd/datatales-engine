"""Build the copy-paste prompt that asks Claude chat for a cleaning recipe."""

import json
from typing import Any

from datatales.clean.schema import Recipe
from datatales.sources import SourceDef

EXAMPLE = """\
source: example-source
version: 1
description: Regional table, one header row under a title, wide year columns.
steps:
  - op: select_sheet
    sheet: Table 1
  - op: skip_rows
    count: 3
  - op: use_header_row
    row: 0
  - op: strip_footnotes
  - op: rename_columns
    mapping: {Area code: area_code, Area name: area}
  - op: melt
    id_columns: [area_code, area]
    var_name: year
    value_name: value
  - op: parse_number
    columns: [value]
  - op: cast
    columns: {year: int}
checks:
  expected_columns: [area_code, area, year, value]
  row_count: {min: 100, max: 1000}
  not_null: [area_code, area, year]
  unique: [area_code, year]
  ranges:
    value: {min: 0}
"""

RULES = """\
Rules:
1. Reply with ONLY the recipe as YAML: no prose, no code fences.
2. Use only the step `op`s defined in the schema. Never include code, SQL, regexes or formulas.
3. `source` must be "{slug}". `version` must be {version}.
4. Aim for a tidy long table: one row per observation, short snake_case column names,
   human-readable labels kept (drop duplicate slug/code columns only if a label column exists).
5. Structural steps (select_sheet, skip_rows, use_header_row) come first, in that order.
   Without use_header_row, the first remaining row is the header.
6. Convert numbers stored as text with parse_number; suppression markers such as
   [c], [x], [u], [w], "..", ":" become null. Add any other marker seen in the profile to `markers`.
7. Use the profile's flags: skip title rows, strip footnote rows, drop repeated header rows,
   melt wide year columns, join stacked header rows with use_header_row.rows.
8. Checks must describe the FINAL table: expected_columns (all final columns, in order),
   a realistic row_count range, not_null and unique for the key columns, ranges for numeric
   columns, and a sums check where categories should add up to a total (e.g. 100%).
9. Do not invent columns or values that are not in the profile.
"""


def build_recipe_prompt(
    source: SourceDef, profile: dict[str, Any], next_version: int, dataset_id: str
) -> str:
    schema = json.dumps(Recipe.model_json_schema(), separators=(",", ":"))
    return "\n".join(
        [
            "You are writing a declarative data-cleaning recipe for the DataTales pipeline.",
            "The pipeline applies the recipe's whitelisted steps to the raw file, then runs its",
            "checks. A failing check stops publication, so make the checks honest.",
            "",
            RULES.format(slug=source.slug, version=next_version),
            f"## Source\n{source.name} ({source.publisher})\n{source.url}",
            f"Dataset id: {dataset_id}",
            "",
            "## Profile of the raw file (JSON)",
            json.dumps(profile, ensure_ascii=False, indent=1),
            "",
            "## Recipe JSON Schema",
            schema,
            "",
            "## Example recipe (different dataset; for format only)",
            EXAMPLE,
            "Now write the recipe for this dataset.",
        ]
    )
