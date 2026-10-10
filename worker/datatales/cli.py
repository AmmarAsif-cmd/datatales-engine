"""Command-line entry point: `python -m datatales <command>`."""

import argparse
import json
import sys
from pathlib import Path

from datatales import __version__
from datatales.config import ConfigError, load_settings
from datatales.errors import UserError
from datatales.repo import Repo


def _repo() -> Repo:
    from datatales.db import get_client
    from datatales.repo import SupabaseRepo

    return SupabaseRepo(get_client(load_settings()))


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


# ---- commands ----


def cmd_db_check(_args: argparse.Namespace) -> int:
    from datatales.db import get_client, run_db_check

    settings = load_settings()
    print(f"Checking {settings.supabase_url} ...")
    report = run_db_check(get_client(settings))
    for line in report.ok_lines:
        print(f"OK    {line}")
    for line in report.problems:
        print(f"FAIL  {line}")
    print("\nDatabase check passed." if report.passed else "\nDatabase check FAILED.")
    return 0 if report.passed else 1


def cmd_sources_sync(_args: argparse.Namespace) -> int:
    from datatales.pipeline import sync_sources

    for slug, source_id in sync_sources(_repo()).items():
        print(f"OK    {slug}  ({source_id})")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    from datatales.pipeline import fetch_raw, ingest, profile_dataset, run_job
    from datatales.sources import get_source

    repo = _repo()
    source = get_source(args.source)

    def job(log):  # noqa: ANN001, ANN202
        result = ingest(repo, source, fetch_raw(source, args.file), log)
        if not result.skipped and not args.no_profile:
            profile_dataset(repo, result.dataset.id, log)
        return result

    result = run_job(repo, f"ingest:{source.slug}", job)
    print(f"\ndataset_id: {result.dataset.id}")
    return 0


def cmd_datasets(args: argparse.Namespace) -> int:
    repo = _repo()
    source_id = repo.get_source_id(args.source) if args.source else None
    for ds in repo.list_datasets(source_id, args.limit):
        profiled = "profiled" if ds.profile else "not profiled"
        print(f"{ds.id}  {ds.fetched_at[:19]}  {ds.source_slug}  {ds.checksum[:12]}  {profiled}")
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    from datatales.pipeline import profile_dataset, run_job

    repo = _repo()
    profile = run_job(repo, "profile", lambda log: profile_dataset(repo, args.dataset_id, log))
    if args.json:
        print(json.dumps(profile, indent=2, ensure_ascii=False))
    return 0


def cmd_recipe_prompt(args: argparse.Namespace) -> int:
    from datatales.pipeline import profile_dataset
    from datatales.recipe_prompt import build_recipe_prompt
    from datatales.sources import get_source

    repo = _repo()
    ds = repo.get_dataset(args.dataset_id)
    profile = ds.profile or profile_dataset(repo, ds.id, lambda _m: None)
    source_id = repo.get_source_id(ds.source_slug) or ds.source_id
    versions = [r.version for r in repo.list_recipes(source_id)]
    prompt = build_recipe_prompt(
        get_source(ds.source_slug), profile, max(versions, default=0) + 1, ds.id
    )
    if args.out:
        Path(args.out).write_text(prompt, encoding="utf-8")
        print(f"Prompt written to {args.out} ({len(prompt):,} characters)")
    else:
        print(prompt)
    return 0


def cmd_recipe_test(args: argparse.Namespace) -> int:
    from datatales.pipeline import dry_run_recipe

    df, results = dry_run_recipe(_repo(), _read_text(args.file), args.dataset_id)
    print(df.head(args.rows).to_string(max_colwidth=30))
    print(f"\n{len(df):,} rows x {df.shape[1]} columns\n")
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.name}: {r.detail}")
    ok = all(r.passed for r in results)
    print("\nAll checks passed (dry run, nothing written)." if ok else "\nSome checks FAILED.")
    return 0 if ok else 1


def cmd_recipe_import(args: argparse.Namespace) -> int:
    from datatales.pipeline import import_recipe

    recipe = import_recipe(_repo(), _read_text(args.file))
    print(f"Imported recipe v{recipe.version} ({recipe.id}). Not approved yet.")
    print("Next: test it with `recipe-test`, then `recipe-approve <source> <version> --by <name>`.")
    return 0


def cmd_recipe_approve(args: argparse.Namespace) -> int:
    from datatales.pipeline import approve_recipe

    recipe, path = approve_recipe(_repo(), args.source, args.version, args.by)
    print(f"Approved {args.source} v{recipe.version} by {recipe.approved_by}.")
    print(f"Wrote {path}. Commit it so the approved recipe is versioned in git.")
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    from datatales.pipeline import clean_dataset, run_job

    repo = _repo()
    outcome = run_job(
        repo, "clean", lambda log: clean_dataset(repo, args.dataset_id, log, args.version)
    )
    print(f"\nclean_table_id: {outcome.clean_table_id}  checks_passed: {outcome.passed}")
    return 0 if outcome.passed else 1


# ---- parser ----


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datatales",
        description="DataTales Story Engine worker. Commands are added milestone by milestone.",
    )
    parser.add_argument("--version", action="version", version=f"datatales {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    def add(name: str, func, help_text: str) -> argparse.ArgumentParser:  # noqa: ANN001
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.set_defaults(func=func)
        return p

    add("db-check", cmd_db_check, "Confirm Supabase connection, tables, RLS and storage buckets.")
    add("sources-sync", cmd_sources_sync, "Upsert worker/sources.yaml into the sources table.")

    p = add("ingest", cmd_ingest, "Fetch a source's raw file, store it untouched, then profile it.")
    p.add_argument("source", help="source slug from sources.yaml")
    p.add_argument("--file", help="file name in worker/data/inbox/ (upload sources only)")
    p.add_argument("--no-profile", action="store_true", help="skip profiling after ingest")

    p = add("datasets", cmd_datasets, "List recently ingested datasets.")
    p.add_argument("--source", help="only this source slug")
    p.add_argument("--limit", type=int, default=20)

    p = add("profile", cmd_profile, "(Re)profile a dataset and store the profile.")
    p.add_argument("dataset_id")
    p.add_argument("--json", action="store_true", help="print the full profile JSON")

    p = add("recipe-prompt", cmd_recipe_prompt, "Print a prompt to paste into Claude chat.")
    p.add_argument("dataset_id")
    p.add_argument("--out", help="write the prompt to this file instead of printing")

    p = add("recipe-test", cmd_recipe_test, "Dry-run a recipe file on a dataset (writes nothing).")
    p.add_argument("file")
    p.add_argument("dataset_id")
    p.add_argument("--rows", type=int, default=8)

    p = add("recipe-import", cmd_recipe_import, "Validate a recipe file and store it (unapproved).")
    p.add_argument("file")

    p = add(
        "recipe-approve", cmd_recipe_approve, "Approve a recipe version and save it to recipes/."
    )
    p.add_argument("source")
    p.add_argument("version", type=int)
    p.add_argument("--by", required=True, help="your name, recorded as approved_by")

    p = add("clean", cmd_clean, "Clean a dataset with its latest approved recipe, then run checks.")
    p.add_argument("dataset_id")
    p.add_argument("--version", type=int, help="use this approved recipe version")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    except (UserError, ValueError, KeyError, FileNotFoundError) as exc:
        # Expected problems (bad recipe, unknown id, failed step): message only, no traceback.
        message = exc.args[0] if isinstance(exc, KeyError) and exc.args else exc
        print(f"FAIL  {message}", file=sys.stderr)
        return 1
