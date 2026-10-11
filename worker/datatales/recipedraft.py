"""Automatic cleaning-recipe drafting with the Claude API, plus the sandbox test run.

When a dataset is ingested and profiled and its source has no approved recipe, Claude drafts
one from the profile (untrusted data: column names, sample values) and the recipe schema with
its whitelist of steps. The reply is parsed with json.loads and validated by the Recipe model:
only whitelisted steps, no unknown keys, never executed as code.

The draft is then test-run in a sandbox: cleaning and every check run in memory against the
raw file; nothing is written to `clean` or `clean_tables`. Checks failed -> one retry with the
failures -> else the recipe is stored as `failed` with its report. A passing draft is stored
as `ready`: you approve or reject it in the dashboard. Only approved recipes ever run.

For a source with no `detect` block yet (added from the backlog), Claude then drafts the
detector settings from the cleaned table and they are trial-run too (detectdraft.py); they
are stored on the recipe and written into the source file when you approve it.
"""

import json
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from datatales.clean.checks import all_passed, results_to_json, run_checks
from datatales.clean.runner import run_recipe
from datatales.clean.schema import Recipe as RecipeSpec
from datatales.clean.schema import RecipeError, parse_recipe_text
from datatales.errors import UserError
from datatales.llm import BudgetReached, InvalidOutput, LLMClient, LLMError, untrusted
from datatales.recipe_prompt import EXAMPLE, RULES
from datatales.repo import Recipe, Repo
from datatales.sources import get_source

PREVIEW_ROWS = 20
MAX_ATTEMPTS = 2

RECIPE_INSTRUCTIONS = "\n".join(
    [
        "You are writing a declarative data-cleaning recipe for the DataTales pipeline.",
        "The pipeline applies the recipe's whitelisted steps to the raw file, then runs its",
        "checks. A failing check stops publication, so make the checks honest.",
        "",
        RULES.replace("`source` must be \"{slug}\". `version` must be {version}.",
                      "`source` and `version` must be exactly the values given under TARGET.")
        .replace("Reply with ONLY the recipe as YAML: no prose, no code fences.",
                 "Reply with ONLY the recipe: no prose, no code fences."),
        "## Recipe JSON Schema",
        json.dumps(RecipeSpec.model_json_schema(), separators=(",", ":")),
        "",
        "## Example recipe (different dataset; for format only)",
        EXAMPLE,
    ]
)  # fmt: skip

RECIPE_REQUEST = (
    "Write the cleaning recipe for the dataset above now, following every rule. Reply with "
    "ONLY the recipe as one JSON object (source, version, description, steps, checks): no "
    "prose and no code fences. Use only the step ops in the schema."
)


class RecipeDraftError(UserError):
    pass


# ---- plain-English summary (from the recipe itself, so it always matches) ----


def _cols(cols: list[str], limit: int = 6) -> str:
    shown = ", ".join(f"'{c}'" for c in cols[:limit])
    return shown + (f" and {len(cols) - limit} more" if len(cols) > limit else "")


def _cond(c: dict[str, Any]) -> str:
    words = {
        "eq": "is", "ne": "is not", "in": "is one of", "not_in": "is not one of",
        "is_null": "is empty", "not_null": "is not empty", "startswith": "starts with",
        "contains": "contains", "gt": ">", "ge": ">=", "lt": "<", "le": "<=",
    }  # fmt: skip
    value = c.get("value")
    if isinstance(value, list):
        value = ", ".join(map(str, value[:5])) + ("…" if len(value) > 5 else "")
    tail = "" if c["op"] in ("is_null", "not_null") else f" {value}"
    return f"'{c['column']}' {words[c['op']]}{tail}"


def describe_step(step: dict[str, Any]) -> str:
    op = step["op"]
    if op == "select_sheet":
        return f"Uses the sheet '{step['sheet']}'"
    if op == "skip_rows":
        return f"Skips the first {step['count']} row(s)"
    if op == "use_header_row":
        rows = step.get("rows", 1)
        joined = f", joining {rows} stacked header rows" if rows > 1 else ""
        return f"Takes column names from row {step.get('row', 0)}{joined}"
    if op == "rename_columns":
        pairs = list(step["mapping"].items())
        shown = ", ".join(f"'{a}' to '{b}'" for a, b in pairs[:4])
        more = f" and {len(pairs) - 4} more" if len(pairs) > 4 else ""
        return f"Renames {shown}{more}"
    if op == "drop_columns":
        return f"Drops {_cols(step['columns'])}"
    if op == "select_columns":
        return f"Keeps only {_cols(step['columns'])}"
    if op == "drop_rows_where":
        return f"Drops rows where {_cond(step['where'])}"
    if op == "filter":
        return f"Keeps only rows where {_cond(step['where'])}"
    if op == "strip_footnotes":
        return "Removes footnote markers and note rows"
    if op == "parse_number":
        mode = "empty" if step.get("on_error") == "null" else "a failure"
        cols = _cols(step["columns"])
        return f"Reads {cols} as numbers (markers become empty; other text is {mode})"
    if op == "parse_date":
        into = f" into '{step['into']}'" if step.get("into") else ""
        return f"Reads '{step['column']}' as a date ({step['format']}){into}"
    if op == "melt":
        return (
            f"Turns wide columns into rows, keeping {_cols(step['id_columns'])} "
            f"('{step.get('var_name', 'variable')}' / '{step.get('value_name', 'value')}')"
        )
    if op == "cast":
        return "Sets types: " + ", ".join(f"'{c}' {t}" for c, t in step["columns"].items())
    if op == "dedupe":
        on = f" on {_cols(step['columns'])}" if step.get("columns") else ""
        return f"Removes duplicate rows{on}"
    if op == "sort":
        return f"Sorts by {_cols(step['by'])}" + (" (descending)" if step.get("descending") else "")
    if op == "classify_prefix":
        n = len(step["mapping"])
        return f"Adds '{step['into']}' from the start of '{step['column']}' ({n} codes)"
    if op == "derive_flag":
        return f"Adds true/false '{step['into']}' where {_cond(step['where'])}"
    return op


def describe_recipe(spec: dict[str, Any]) -> list[str]:
    """One plain-English line per step, then the checks."""
    lines = [describe_step(s) for s in spec.get("steps", [])]
    checks = spec.get("checks", {})
    parts = [f"{len(checks.get('expected_columns', []))} expected columns"]
    rc = checks.get("row_count") or {}
    if rc:
        parts.append(f"{rc.get('min', 1):,} to {rc['max']:,} rows" if rc.get("max") else
                     f"at least {rc.get('min', 1):,} rows")  # fmt: skip
    for key, label in (("not_null", "never empty"), ("unique", "unique")):
        if checks.get(key):
            parts.append(f"{_cols(checks[key], 3)} {label}")
    if checks.get("ranges") or checks.get("ranges_where"):
        parts.append("value ranges")
    if checks.get("sums"):
        parts.append(f"{len(checks['sums'])} sum check(s)")
    lines.append("Checks: " + "; ".join(parts))
    return lines


# ---- sandbox test run ----


def _jsonable(v: Any) -> Any:
    if v is None or isinstance(v, bool | str | int):
        return v
    if isinstance(v, float):
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(v, datetime | date):
        return v.isoformat()
    try:
        import pandas as pd

        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(v, "item"):  # numpy scalars
        return _jsonable(v.item())
    return str(v)


def test_recipe(repo: Repo, dataset_id: str, spec: RecipeSpec) -> dict[str, Any]:
    """Run cleaning and checks in memory. Returns a JSON-safe report; writes nothing."""
    return test_recipe_frame(repo, dataset_id, spec)[0]


def test_recipe_frame(repo: Repo, dataset_id: str, spec: RecipeSpec) -> tuple[dict[str, Any], Any]:
    """test_recipe plus the cleaned DataFrame (None when the recipe did not run)."""
    ds = repo.get_dataset(dataset_id)
    summary = describe_recipe(spec.model_dump(mode="json"))
    if spec.source != ds.source_slug:
        return {"passed": False, "error": f"recipe is for {spec.source}, dataset is "
                f"{ds.source_slug}", "summary": summary, "checks": []}, None  # fmt: skip
    try:
        content = repo.get_object("raw", ds.raw_path)
        df = run_recipe(spec, content, ds.raw_path.rsplit("/", 1)[-1])
    except Exception as exc:  # noqa: BLE001 - a step error is a test result, not a crash
        return {"passed": False, "error": f"{type(exc).__name__}: {exc}"[:1000],
                "summary": summary, "checks": []}, None  # fmt: skip
    results = run_checks(df, spec.checks)
    preview = [
        {str(k): _jsonable(v) for k, v in row.items()}
        for row in df.head(PREVIEW_ROWS).to_dict(orient="records")
    ]
    report = {
        "passed": all_passed(results),
        "row_count": int(len(df)),
        "columns": [str(c) for c in df.columns],
        "checks": results_to_json(results),
        "preview": preview,
        "summary": summary,
        "dataset_id": dataset_id,
    }
    return report, df


# ---- drafting ----


@dataclass
class RecipeOutcome:
    status: str  # ready | failed | budget | error | skipped
    detail: str = ""
    recipe_id: str | None = None
    version: int | None = None


def recipe_data(source_slug: str, version: int, dataset_id: str, profile: dict[str, Any]) -> str:
    source = get_source(source_slug)
    return "\n".join(
        [
            "## TARGET",
            f"source: {source_slug}",
            f"version: {version}",
            "",
            f"## Source\n{source.name} ({source.publisher})\n{source.url}",
            f"Dataset id: {dataset_id}",
            "",
            "## Profile of the raw file (JSON)",
            json.dumps(profile, ensure_ascii=False, indent=1),
        ]
    )


def _validator(slug: str, version: int) -> Callable[[Any], RecipeSpec]:
    def validate(value: Any) -> RecipeSpec:
        if not isinstance(value, dict):
            raise RecipeError("the reply must be one JSON object (the recipe)")
        spec = parse_recipe_text(json.dumps(value))
        if spec.source != slug or spec.version != version:
            raise RecipeError(f"source/version must be {slug} / {version}")
        return spec

    return validate


def _failure_feedback(report: dict[str, Any]) -> str:
    if report.get("error"):
        return f"Running the recipe failed: {report['error']}"
    failed = [c for c in report.get("checks", []) if not c["passed"]]
    head = (
        f"The recipe ran ({report.get('row_count', 0):,} rows; columns "
        f"{report.get('columns', [])}) but {len(failed)} check(s) failed:"
    )
    rows = "\n".join(f"- {c['name']}: {c['detail']}" for c in failed)
    sample = json.dumps(report.get("preview", [])[:5], ensure_ascii=False)
    return f"{head}\n{rows}\nFirst rows of the cleaned table: {sample}"


def _target_version(repo: Repo, source_id: str) -> tuple[int, Recipe | None]:
    """The version to draft: reuse the latest unapproved, non-rejected draft; else max+1."""
    recipes = repo.list_recipes(source_id)
    open_drafts = [r for r in recipes if not r.approved and r.status != "rejected"]
    if open_drafts:
        return open_drafts[-1].version, open_drafts[-1]
    return (max((r.version for r in recipes), default=0) + 1), None


def draft_recipe(
    repo: Repo, llm: LLMClient, dataset_id: str, log: Callable[[str], None] = print
) -> RecipeOutcome:
    ds = repo.get_dataset(dataset_id)
    if ds.profile is None:
        raise RecipeDraftError(f"dataset {dataset_id} has no profile yet; run `profile` first")
    source_id = repo.get_source_id(ds.source_slug)
    if source_id is None:
        raise RecipeDraftError(f"source {ds.source_slug} is not in the database; run sources-sync")
    version, existing = _target_version(repo, source_id)
    if existing is not None and existing.drafted_by == "manual":
        return RecipeOutcome(
            "skipped", f"v{version} is a manual draft; not overwritten", existing.id, version
        )

    base = untrusted("dataset", recipe_data(ds.source_slug, version, dataset_id, ds.profile))
    feedback = ""
    spec: RecipeSpec | None = None
    report: dict[str, Any] = {}
    clean = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        data = base + (f"\n\n{feedback}" if feedback else "")
        try:
            result = llm.call(
                "recipe",
                instructions=RECIPE_INSTRUCTIONS,
                data=data,
                schema=None,
                validate=_validator(ds.source_slug, version),
                related_id=dataset_id,
                request=RECIPE_REQUEST,
            )
        except BudgetReached as exc:
            return RecipeOutcome("budget", str(exc), None, version)
        except InvalidOutput as exc:
            log(f"  attempt {attempt}: reply rejected: {exc}")
            feedback = (
                "Your previous reply was rejected for this reason; reply again with the whole "
                f"recipe, fixed:\n{untrusted('rejection', str(exc))}"
            )
            continue
        except LLMError as exc:
            return RecipeOutcome("error", str(exc), None, version)

        spec = result.value
        report, clean = test_recipe_frame(repo, dataset_id, spec)
        if report["passed"]:
            log(f"  attempt {attempt}: test run passed ({report['row_count']:,} rows)")
            break
        log(f"  attempt {attempt}: test run failed")
        feedback = (
            "Your previous recipe failed its test run. Fix it and reply with the whole recipe "
            "again:\n" + untrusted("test_report", _failure_feedback(report))
        )

    if spec is None:
        return RecipeOutcome("failed", "Claude's replies were rejected twice", None, version)
    status = "ready" if report.get("passed") else "failed"
    fields: dict[str, Any] = {
        "status": status,
        "drafted_by": "claude",
        "dataset_id": dataset_id,
        "test_report": report,
        "reject_note": None,
    }
    source = get_source(ds.source_slug)
    if status == "ready" and source.detect is None and clean is not None:
        from datatales.detectdraft import draft_detect

        log("  drafting detector settings for the new source")
        detect = draft_detect(llm, source, clean, related_id=dataset_id, log=log)
        report["detect"] = detect.report()
        fields["detect_spec"] = (
            detect.config.model_dump(mode="json", exclude_defaults=True) if detect.config else None
        )
    spec_json = spec.model_dump(mode="json")
    if existing is not None:
        repo.replace_unapproved_spec(existing.id, spec_json)
        saved = repo.update_unapproved_recipe(existing.id, fields)
    else:
        saved = repo.insert_recipe(source_id, version, spec_json, fields)
    return RecipeOutcome(status, "" if status == "ready" else "checks failed", saved.id, version)


def ensure_recipe_draft(
    repo: Repo, dataset_id: str, log: Callable[[str], None], llm: LLMClient | None
) -> RecipeOutcome:
    """Pipeline hook: draft a recipe for a profiled dataset whose source has no approved
    recipe, unless one is already waiting (ready/failed/draft) or was rejected for this data."""
    ds = repo.get_dataset(dataset_id)
    source_id = repo.get_source_id(ds.source_slug)
    recipes = repo.list_recipes(source_id) if source_id else []
    if any(r.approved for r in recipes):
        return RecipeOutcome("skipped", "source has an approved recipe")
    waiting = [r for r in recipes if r.status in ("ready", "draft")]
    if waiting:
        return RecipeOutcome("skipped", f"v{waiting[-1].version} is waiting for review")
    if any(r.dataset_id == dataset_id and r.status in ("failed", "rejected") for r in recipes):
        return RecipeOutcome("skipped", "a draft for this dataset failed or was rejected")
    if llm is None:
        log(f"[{ds.source_slug}] no approved recipe; Claude key not set: use recipe-prompt")
        return RecipeOutcome("error", "Claude is not configured")
    log(f"[{ds.source_slug}] no approved recipe: drafting one with Claude")
    return draft_recipe(repo, llm, dataset_id, log)


def approve_ready_check(repo: Repo, recipe: Recipe) -> Recipe:
    """Before approval: a recipe that has not passed a test run (e.g. imported by hand) is
    test-run now against its dataset or the source's latest one. Returns the ready recipe."""
    if recipe.status == "ready":
        return recipe
    if recipe.status == "rejected":
        raise RecipeDraftError("this recipe was rejected; import or draft a new version")
    dataset_id = recipe.dataset_id
    if dataset_id is None:
        datasets = repo.list_datasets(recipe.source_id, limit=1)
        if not datasets:
            raise RecipeDraftError("no dataset to test the recipe on; ingest one first")
        dataset_id = datasets[0].id
    report = test_recipe(repo, dataset_id, RecipeSpec.model_validate(recipe.spec))
    status = "ready" if report["passed"] else "failed"
    updated = repo.update_unapproved_recipe(
        recipe.id, {"status": status, "test_report": report, "dataset_id": dataset_id}
    )
    if status != "ready":
        failed = [c["name"] for c in report.get("checks", []) if not c["passed"]]
        why = report.get("error") or f"failed checks: {', '.join(failed)}"
        raise RecipeDraftError(f"the recipe failed its test run ({why}); it cannot be approved")
    return updated
