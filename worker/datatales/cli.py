"""Command-line entry point: `python -m datatales <command>`."""

import argparse

from datatales import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datatales",
        description="DataTales Story Engine worker. Commands are added milestone by milestone.",
    )
    parser.add_argument("--version", action="version", version=f"datatales {__version__}")
    parser.add_subparsers(dest="command", metavar="<command>")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
    return 0
