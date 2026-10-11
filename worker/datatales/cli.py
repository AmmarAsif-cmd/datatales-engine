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


CHECK_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


def _check_reply(data: object) -> dict[str, bool]:
    if not isinstance(data, dict) or data.get("ok") is not True:
        raise ValueError('expected {"ok": true}')
    return {"ok": True}


def cmd_llm_check(_args: argparse.Namespace) -> int:
    """One tiny Claude API call, logged to llm_calls, to confirm the key and the budget guard."""
    from datatales.llm import LLMClient, untrusted

    client = LLMClient(_repo())
    cfg = client.config.task("check")
    before = client.budget()
    print(f"Model: {cfg.model} (task 'check')")
    print(
        f"This month: £{before.spent_gbp:.4f} of £{before.budget_gbp:.2f}, {before.calls} call(s)"
    )
    result = client.call(
        "check",
        instructions='Health check for an API integration. Reply with the JSON {"ok": true}.',
        data=untrusted("ping", "ping"),
        schema=CHECK_SCHEMA,
        validate=_check_reply,
    )
    u = result.usage
    print(
        f"OK: reply valid. Tokens in {u.input_tokens}, out {u.output_tokens}, "
        f"cache read {u.cache_read_tokens}, cache write {u.cache_write_tokens}."
    )
    after = client.budget()
    print(f"Cost: £{result.cost_gbp:.6f}.")
    print(f"This month now: £{after.spent_gbp:.4f}, {after.calls} call(s).")
    print(f"Logged as llm_calls {result.call_id}.")
    return 0


def cmd_llm_config_sync(_args: argparse.Namespace) -> int:
    from datatales.llm import DASHBOARD_CONFIG, dashboard_config_json

    DASHBOARD_CONFIG.write_text(dashboard_config_json(), encoding="utf-8", newline="\n")
    print(f"Wrote {DASHBOARD_CONFIG}")
    return 0


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

    recipe = import_recipe(_repo(), _read_text(args.file), replace=args.replace)
    verb = "Replaced" if args.replace else "Imported"
    print(f"{verb} recipe v{recipe.version} ({recipe.id}). Not approved yet.")
    print("Next: test it with `recipe-test`, then `recipe-approve <source> <version> --by <name>`.")
    return 0


def cmd_recipe_approve(args: argparse.Namespace) -> int:
    from datatales.pipeline import approve_recipe, run_job

    repo = _repo()

    def job(log):  # noqa: ANN001, ANN202
        result = approve_recipe(repo, args.source, args.version, args.by)
        log(f"Approved {args.source} v{args.version} by {args.by}")
        return result

    recipe, path = run_job(repo, f"recipe-approve:{args.source}", job)
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


def cmd_detect(args: argparse.Namespace) -> int:
    from datatales.pipeline import detect_clean_table, run_job

    repo = _repo()
    run_job(
        repo,
        "detect",
        lambda log: detect_clean_table(
            repo, args.clean_table_id, log, replace=args.replace, dry_run=args.dry_run
        ),
    )
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    rows = _repo().list_findings(args.clean_table_id)
    if not rows:
        print("No findings for this clean table. Run `detect` first.")
    for row in rows:
        print(f"{row['score']:.4f}  {row['detector']:<15} {row['title_hint']}  ({row['id']})")
        if args.numbers:
            print(json.dumps(row["numbers"], indent=2, ensure_ascii=False))
    return 0


def cmd_candidates(args: argparse.Namespace) -> int:
    from datatales.stories import candidates_for

    for i, c in enumerate(candidates_for(_repo(), args.clean_table_id), start=1):
        print(f"{i}. [{c.score:.4f}] {c.title}")
        for f in c.findings:
            print(f"     {f['score']:.4f}  {f['detector']:<15} {f['title_hint']}")
    return 0


def cmd_story_new(args: argparse.Namespace) -> int:
    from datatales.pipeline import run_job
    from datatales.stories import create_story

    repo = _repo()

    def job(log):  # noqa: ANN001, ANN202
        s = create_story(repo, args.clean_table_id, args.candidate)
        log(f"Draft story {s['id']} from candidate {args.candidate}: {s['headline']}")
        return s

    story = run_job(repo, "story-new", job)
    rows, n = len(story["chart_data"]), len(story["finding_ids"])
    print(f"Draft story {story['id']}: {n} finding(s), {rows} chart rows.")
    print(f"Next: story-prompt {story['id']} --out prompt.txt")
    return 0


def cmd_story_refresh(args: argparse.Namespace) -> int:
    from datatales.stories import refresh_story

    story = refresh_story(_repo(), args.story_id)
    print(f"Refreshed {story['slug']}: numbers and chart data rebuilt; status draft,")
    print("verification pending. Next: story-prompt, then story-paste the new reply.")
    return 0


def cmd_story_prompt(args: argparse.Namespace) -> int:
    from datatales.stories import story_prompt

    prompt = story_prompt(_repo(), args.story_id)
    if args.out:
        Path(args.out).write_text(prompt, encoding="utf-8")
        print(f"Prompt written to {args.out} ({len(prompt):,} characters)")
    else:
        print(prompt)
    return 0


def _print_report(report) -> None:  # noqa: ANN001
    print(f"Verification: {report.status.upper()} ({report.checked} number(s) checked)")
    for u in report.unmatched:
        print(f"  NOT IN DATA  {u['field']}: {u['text']!r}")
    for y in report.years_out_of_range:
        print(f"  BAD YEAR     {y['field']}: {y['text']!r} (data covers {y['allowed']})")


def cmd_story_paste(args: argparse.Namespace) -> int:
    from datatales.stories import paste_narration

    story, report = paste_narration(_repo(), args.story_id, _read_text(args.file))
    print(f"Saved: {story['headline']}  (slug: {story['slug']})")
    _print_report(report)
    return 0 if report.passed else 1


def cmd_story_verify(args: argparse.Namespace) -> int:
    from datatales.stories import reverify

    _, report = reverify(_repo(), args.story_id)
    _print_report(report)
    return 0 if report.passed else 1


def cmd_stories(_args: argparse.Namespace) -> int:
    for s in _repo().list_stories():
        print(f"{s['id']}  {s['status']:<9} verify:{s['verify_status']:<8} {s['headline']}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    from datatales.pipeline import run_job
    from datatales.publish import mark_published, write_story_file

    repo = _repo()
    if args.mark:

        def mark(log):  # noqa: ANN001, ANN202
            s = mark_published(repo, args.story_id)
            log(f"Marked published at {s['published_at']}: {s['slug']}")
            return s

        run_job(repo, "publish:mark", mark)
        return 0

    def write(log):  # noqa: ANN001, ANN202
        out = write_story_file(repo, args.story_id)
        log(f"Wrote {out.name}")
        return out

    path = run_job(repo, "publish:write", write)
    print(f"Wrote {path}")
    print("Next: build the site, commit and push, then `publish <id> --mark`.")
    return 0


def cmd_run_pipeline(_args: argparse.Namespace) -> int:
    from datatales.pipeline import run_job, run_scheduled

    repo = _repo()
    ok = run_job(repo, "pipeline", lambda log: run_scheduled(repo, log))
    return 0 if ok else 1


def cmd_api(args: argparse.Namespace) -> int:
    from datatales.api import main as api_main

    return api_main(args.action, _repo)


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
    add(
        "llm-check",
        cmd_llm_check,
        "Make one tiny Claude API call (logged) to confirm the key works.",
    )
    add("llm-config-sync", cmd_llm_config_sync, "Copy config/llm.yaml to the dashboard as JSON.")
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
    p.add_argument(
        "--replace", action="store_true", help="update this version if it exists and is unapproved"
    )

    p = add(
        "recipe-approve", cmd_recipe_approve, "Approve a recipe version and save it to recipes/."
    )
    p.add_argument("source")
    p.add_argument("version", type=int)
    p.add_argument("--by", required=True, help="your name, recorded as approved_by")

    p = add("clean", cmd_clean, "Clean a dataset with its latest approved recipe, then run checks.")
    p.add_argument("dataset_id")
    p.add_argument("--version", type=int, help="use this approved recipe version")

    p = add("detect", cmd_detect, "Run detectors on a clean table and store the top findings.")
    p.add_argument("clean_table_id")
    p.add_argument("--replace", action="store_true", help="recompute existing findings")
    p.add_argument("--dry-run", action="store_true", help="show findings without storing them")

    p = add("findings", cmd_findings, "List stored findings for a clean table.")
    p.add_argument("clean_table_id")
    p.add_argument("--numbers", action="store_true", help="also print each finding's numbers")

    p = add("candidates", cmd_candidates, "Story shortlist: findings grouped by place and news.")
    p.add_argument("clean_table_id")

    p = add("story-new", cmd_story_new, "Create a draft story from a shortlist candidate.")
    p.add_argument("clean_table_id")
    p.add_argument("--candidate", type=int, required=True, help="number from `candidates`")

    p = add("story-prompt", cmd_story_prompt, "Print the narration prompt for Claude chat.")
    p.add_argument("story_id")
    p.add_argument("--out", help="write the prompt to this file instead of printing")

    p = add("story-paste", cmd_story_paste, "Validate a pasted JSON reply, verify numbers, save.")
    p.add_argument("story_id")
    p.add_argument("file", help="file containing the JSON reply from Claude")

    p = add("story-refresh", cmd_story_refresh, "Rebuild a story's numbers/chart data; URL kept.")
    p.add_argument("story_id")

    p = add("story-verify", cmd_story_verify, "Re-run number verification on a story.")
    p.add_argument("story_id")

    add("stories", cmd_stories, "List stories.")

    p = add("publish", cmd_publish, "Write an approved story's site file (or --mark it published).")
    p.add_argument("story_id")
    p.add_argument("--mark", action="store_true", help="mark published (after commit + push)")

    add("run-pipeline", cmd_run_pipeline, "Scheduled run: ingest, profile, clean, detect.")

    p = add("api", cmd_api, "JSON bridge for the local dashboard (stdin -> stdout).")
    p.add_argument("action")
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
