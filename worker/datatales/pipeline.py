"""Pipeline operations used by the CLI and the scheduled workflow.

All persistence goes through `Repo`, so every function here is testable with MemRepo.
"""

import io
import json
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from datatales.clean.checks import CheckResult, all_passed, results_to_json, run_checks
from datatales.clean.runner import run_recipe, to_parquet_bytes
from datatales.clean.schema import Recipe as RecipeSpec
from datatales.clean.schema import parse_recipe_text, recipe_to_yaml
from datatales.config import WORKER_DIR
from datatales.errors import UserError
from datatales.ingest import ons, upload
from datatales.ingest.common import IngestResult, RawFile, ingest_raw
from datatales.profile import profile_file
from datatales.repo import Recipe, Repo
from datatales.sources import SourceDef, get_source, load_sources

RECIPES_DIR = WORKER_DIR / "recipes"


class PipelineError(UserError):
    pass


class JobLog:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, message: str) -> None:
        self.lines.append(message)
        print(message)

    def text(self) -> str:
        return "\n".join(self.lines)


def run_job[T](repo: Repo, job_type: str, fn: Callable[[JobLog], T]) -> T:
    """Run `fn`, recording a `jobs` row with its log and any error."""
    log = JobLog()
    job_id = repo.start_job(job_type)
    try:
        result = fn(log)
    except Exception as exc:
        repo.finish_job(job_id, "failed", log.text(), f"{type(exc).__name__}: {exc}")
        if not isinstance(exc, UserError | ValueError | KeyError):
            traceback.print_exc()
        raise
    repo.finish_job(job_id, "succeeded", log.text(), None)
    return result


# ---- sources & ingest ----


def sync_sources(repo: Repo, sources: dict[str, SourceDef] | None = None) -> dict[str, str]:
    sources = sources or load_sources()
    return {slug: repo.upsert_source(src) for slug, src in sources.items()}


def fetch_raw(
    source: SourceDef, file: str | None = None, client: httpx.Client | None = None
) -> RawFile:
    if source.fetch.type == "ons_api":
        if file:
            raise PipelineError(f"{source.slug} is fetched from the ONS API; don't pass --file")
        return ons.fetch_latest(source.fetch.dataset_id, source.fetch.edition, client)
    if not file:
        raise PipelineError(f"{source.slug} is an upload source; pass --file <name in data/inbox>")
    return upload.read_inbox_file(file)


def ingest(repo: Repo, source: SourceDef, raw: RawFile, log: Callable[[str], None]) -> IngestResult:
    log(f"Fetched {raw.filename} ({len(raw.content):,} bytes) from {raw.source_url}")
    result = ingest_raw(repo, source, raw)
    if result.skipped:
        log(f"Skipped: identical file already ingested as dataset {result.dataset.id}")
    else:
        log(f"Stored raw/{result.dataset.raw_path} as dataset {result.dataset.id}")
    return result


# ---- profile ----


def raw_filename(raw_path: str) -> str:
    return raw_path.rsplit("/", 1)[-1]


def profile_dataset(repo: Repo, dataset_id: str, log: Callable[[str], None]) -> dict[str, Any]:
    ds = repo.get_dataset(dataset_id)
    content = repo.get_object("raw", ds.raw_path)
    profile = profile_file(content, raw_filename(ds.raw_path))
    repo.set_profile(ds.id, profile)
    sheets = profile["sheets"]
    log(f"Profiled {raw_filename(ds.raw_path)}: {len(sheets)} sheet(s)")
    for sh in sheets:
        flags = ", ".join(sh.get("flags", {})) or "none"
        name = sh["sheet"] or "(csv)"
        log(f"  {name}: {sh['rows']:,} rows, {len(sh['columns'])} columns; flags: {flags}")
    return profile


# ---- recipes ----


def _source_id(repo: Repo, slug: str) -> str:
    get_source(slug)  # must be a known source
    source_id = repo.get_source_id(slug)
    if not source_id:
        raise PipelineError(f"source '{slug}' is not in the database yet; run sources-sync")
    return source_id


def import_recipe(repo: Repo, text: str, replace: bool = False) -> Recipe:
    """Store a recipe unapproved. `replace` overwrites an existing *unapproved* version
    (it has never run); approved versions are immutable."""
    spec = parse_recipe_text(text)
    source_id = _source_id(repo, spec.source)
    existing = {r.version: r for r in repo.list_recipes(source_id)}
    current = existing.get(spec.version)
    if current is None:
        return repo.insert_recipe(source_id, spec.version, spec.model_dump(mode="json"))
    if current.approved:
        raise PipelineError(
            f"{spec.source} v{spec.version} is approved and immutable; "
            f"set version: {max(existing) + 1}"
        )
    if not replace:
        raise PipelineError(
            f"{spec.source} v{spec.version} already exists (unapproved). Use --replace to "
            f"overwrite it, or set version: {max(existing) + 1}"
        )
    return repo.replace_unapproved_spec(current.id, spec.model_dump(mode="json"))


def find_recipe(repo: Repo, slug: str, version: int | None, approved_only: bool) -> Recipe:
    recipes = repo.list_recipes(_source_id(repo, slug))
    if approved_only:
        recipes = [r for r in recipes if r.approved]
    if version is not None:
        recipes = [r for r in recipes if r.version == version]
    if not recipes:
        what = f"v{version}" if version else "any version"
        kind = "approved recipe" if approved_only else "recipe"
        raise PipelineError(f"no {kind} for {slug} ({what})")
    return recipes[-1]


def recipe_file(slug: str, version: int, recipes_dir: Path = RECIPES_DIR) -> Path:
    return recipes_dir / f"{slug}.v{version}.yaml"


def approve_recipe(
    repo: Repo, slug: str, version: int, approved_by: str, recipes_dir: Path = RECIPES_DIR
) -> tuple[Recipe, Path]:
    if not approved_by.strip():
        raise PipelineError("--by is required (who approved it)")
    recipe = find_recipe(repo, slug, version, approved_only=False)
    if recipe.approved:
        raise PipelineError(f"{slug} v{version} was already approved by {recipe.approved_by}")
    spec = RecipeSpec.model_validate(recipe.spec)
    approved = repo.approve_recipe(recipe.id, approved_by.strip())
    path = recipe_file(slug, version, recipes_dir)
    header = (
        f"# Approved by {approved.approved_by} at {approved.approved_at}.\n"
        "# Do not edit: approved recipes are immutable. Import a new version instead.\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + recipe_to_yaml(spec), encoding="utf-8", newline="\n")
    return approved, path


# ---- clean ----


@dataclass(frozen=True)
class CleanOutcome:
    clean_table_id: str | None
    parquet_path: str | None
    row_count: int
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all_passed(self.checks)


def _run(repo: Repo, dataset_id: str, spec: RecipeSpec):  # noqa: ANN202 - (DataFrame, checks)
    ds = repo.get_dataset(dataset_id)
    if spec.source != ds.source_slug:
        raise PipelineError(f"recipe is for {spec.source} but dataset is {ds.source_slug}")
    content = repo.get_object("raw", ds.raw_path)
    df = run_recipe(spec, content, raw_filename(ds.raw_path))
    return ds, df, run_checks(df, spec.checks)


def dry_run_recipe(repo: Repo, text: str, dataset_id: str) -> tuple[Any, list[CheckResult]]:
    """Dry run of an unapproved recipe: nothing is written."""
    _, df, results = _run(repo, dataset_id, parse_recipe_text(text))
    return df, results


def clean_dataset(
    repo: Repo, dataset_id: str, log: Callable[[str], None], version: int | None = None
) -> CleanOutcome:
    ds = repo.get_dataset(dataset_id)
    recipe = find_recipe(repo, ds.source_slug, version, approved_only=True)
    spec = RecipeSpec.model_validate(recipe.spec)
    log(f"Cleaning dataset {ds.id} with {ds.source_slug} recipe v{recipe.version}")
    _, df, results = _run(repo, dataset_id, spec)
    for r in results:
        log(f"  {'PASS' if r.passed else 'FAIL'}  {r.name}: {r.detail}")
    passed = all_passed(results)
    path = f"{ds.source_slug}/{ds.id}/recipe-v{recipe.version}.parquet"
    if passed:
        repo.put_object(
            "clean", path, to_parquet_bytes(df), "application/vnd.apache.parquet", upsert=True
        )
        log(f"Wrote clean/{path} ({len(df):,} rows)")
    else:
        log("Checks failed: no Parquet written; pipeline stops for this dataset")
    table_id = repo.upsert_clean_table(
        ds.id, recipe.id, path if passed else "", len(df), results_to_json(results), passed
    )
    return CleanOutcome(table_id, path if passed else None, len(df), results)


# ---- detect ----


def release_date(repo: Repo, raw_path: str, fetched_at: str) -> date:
    """Publisher release date from the raw file's fetch.json, else the fetch date."""
    folder = raw_path.rsplit("/", 1)[0]
    try:
        record = json.loads(repo.get_object("raw", f"{folder}/fetch.json"))
        if record.get("release_date"):
            return datetime.fromisoformat(record["release_date"].replace("Z", "+00:00")).date()
    except Exception:  # noqa: BLE001, S110 - missing/old fetch.json: fall back to the fetch date
        pass
    return datetime.fromisoformat(fetched_at.replace("Z", "+00:00")).date()


def detect_clean_table(
    repo: Repo,
    clean_table_id: str,
    log: Callable[[str], None],
    replace: bool = False,
    dry_run: bool = False,
    today: date | None = None,
) -> list[dict[str, Any]]:
    from datatales.detect.run import finding_record, run_detectors

    ct = repo.get_clean_table(clean_table_id)
    if not ct.checks_passed:
        raise PipelineError(f"clean table {ct.id} failed its checks; detectors will not run")
    ds = repo.get_dataset(ct.dataset_id)
    source = get_source(ds.source_slug)
    if source.detect is None:
        raise PipelineError(f"source {source.slug} has no `detect` config in sources.yaml")

    existing = repo.list_findings(ct.id)
    if existing and not dry_run:
        if not replace:
            raise PipelineError(
                f"clean table {ct.id} already has {len(existing)} finding(s); "
                "use --replace to recompute them"
            )
        used = repo.count_stories_using([f["id"] for f in existing])
        if used:
            raise PipelineError(f"{used} story(ies) use these findings; they cannot be replaced")

    clean = read_parquet(repo.get_object("clean", ct.parquet_path))
    released = release_date(repo, ds.raw_path, ds.fetched_at)
    top, total = run_detectors(
        clean, source.detect, source.relatability, released, today or date.today()
    )
    records = [finding_record(f) for f in top]
    log(
        f"{total} candidate finding(s) passed the detector rules; keeping top {len(records)} "
        f"(data released {released})"
    )
    for rec in records:
        log(f"  {rec['score']:.4f}  {rec['detector']:<15} {rec['title_hint']}")
    if dry_run:
        log("Dry run: nothing stored")
        return records
    if existing:
        log(f"Replacing {repo.delete_findings(ct.id)} old finding(s)")
    ids = repo.insert_findings(ct.id, records)
    return [{**rec, "id": fid} for rec, fid in zip(records, ids, strict=True)]


# ---- scheduled run ----


def run_scheduled(repo: Repo, log: Callable[[str], None]) -> bool:
    """ingest -> profile -> clean -> detect for every ONS API source with an approved recipe.

    Idempotent: an unchanged raw file is skipped, and clean/detect only run for a dataset
    that has no clean table (or no findings) for the latest approved recipe yet.
    Returns True if every source succeeded.
    """
    ok = True
    sync_sources(repo)
    for slug, source in load_sources().items():
        if source.fetch.type != "ons_api":
            log(f"[{slug}] upload source: skipped (ingest with --file)")
            continue
        try:
            recipe = find_recipe(repo, slug, None, approved_only=True)
        except PipelineError:
            log(f"[{slug}] no approved recipe: skipped")
            continue
        try:
            result = ingest(repo, source, fetch_raw(source), log)
            ds = result.dataset
            if ds.profile is None:
                profile_dataset(repo, ds.id, log)
            ct = repo.find_clean_table(ds.id, recipe.id)
            if ct is None:
                outcome = clean_dataset(repo, ds.id, log, recipe.version)
                if not outcome.passed or outcome.clean_table_id is None:
                    log(f"[{slug}] checks failed: stopping this source")
                    ok = False
                    continue
                ct = repo.get_clean_table(outcome.clean_table_id)
            if not ct.checks_passed:
                log(f"[{slug}] latest clean table failed its checks: nothing to detect")
                continue
            if repo.list_findings(ct.id):
                log(f"[{slug}] findings already exist for clean table {ct.id}")
            else:
                detect_clean_table(repo, ct.id, log)
                draft_new_stories(repo, ct.id, log)
        except Exception as exc:  # noqa: BLE001 - one source failing must not stop the others
            log(f"[{slug}] FAILED: {type(exc).__name__}: {exc}")
            ok = False
    return ok


def draft_new_stories(repo: Repo, clean_table_id: str, log: Callable[[str], None]) -> None:
    """Auto-draft stories for the new findings (Claude API). Without a key, or once the
    monthly budget is reached, drafts are still created and wait for copy-paste. A drafting
    problem never fails the pipeline run."""
    from datatales.autodraft import auto_draft_clean_table
    from datatales.llm import LLMClient, load_api_key

    try:
        llm = LLMClient(repo) if load_api_key() else None
        if llm is None:
            log("Claude key not set: story drafts are created for copy-paste only")
        summary = auto_draft_clean_table(repo, clean_table_id, log, llm)
        log(
            f"Story drafting: {summary.count('passed')} verified, {summary.count('failed')} "
            f"failed, {summary.count('skipped')} skipped, {summary.count('budget')} waiting "
            "(budget)"
        )
    except Exception as exc:  # noqa: BLE001
        log(f"Story drafting stopped: {type(exc).__name__}: {exc}")


def read_parquet(data: bytes):  # noqa: ANN201 - pandas DataFrame
    import pandas as pd

    return pd.read_parquet(io.BytesIO(data))
