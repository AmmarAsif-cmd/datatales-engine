"""Command-line entry point: `python -m datatales <command>`."""

import argparse
import sys

from datatales import __version__
from datatales.config import ConfigError, load_settings


def cmd_db_check(_args: argparse.Namespace) -> int:
    from datatales.db import get_client, run_db_check

    try:
        settings = load_settings()
    except ConfigError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1

    print(f"Checking {settings.supabase_url} ...")
    report = run_db_check(get_client(settings))
    for line in report.ok_lines:
        print(f"OK    {line}")
    for line in report.problems:
        print(f"FAIL  {line}")
    print("\nDatabase check passed." if report.passed else "\nDatabase check FAILED.")
    return 0 if report.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datatales",
        description="DataTales Story Engine worker. Commands are added milestone by milestone.",
    )
    parser.add_argument("--version", action="version", version=f"datatales {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    db_check = sub.add_parser(
        "db-check", help="Confirm Supabase connection, tables, RLS and storage buckets."
    )
    db_check.set_defaults(func=cmd_db_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)
