# CLAUDE.md: DataTales Story Engine

Project rules for Claude Code sessions. Keep this file updated as conventions are decided.

## What this is

A pipeline that turns UK public datasets into verified data stories for datatales.co.uk:
ingest → profile → clean → detect → narrate → verify → review → publish.
Python computes every number. The language model (Claude chat, copy-paste, **no API**) only writes words around given numbers.

## Hard rules

1. **£0 running cost.** Free tiers only (Supabase free, GitHub Actions, Cloudflare Pages). No paid APIs or packages.
2. **No secrets in git.** Only `.env.example` files with empty placeholders are committed. `.env*` is gitignored.
3. **`site/` never touches Supabase.** No keys, no client, no fetches. It builds only from committed files.
4. **Service-role key** is used only by `worker/` (local `.env` / Actions secret) and `dashboard/` (local `.env.local`, server-side only). Never `NEXT_PUBLIC_` / `PUBLIC_`, and never in a client component.
5. **RLS on every table**, with no anon/authenticated policies unless explicitly agreed.
6. **Never `eval`/`exec`** anything from a dataset or pasted AI output. Cleaning recipes are declarative, whitelisted steps validated by pydantic.
7. **Traceability.** Every story stores the source URL, fetch date, dataset checksum, recipe version and the exact computed values behind each claim.
8. **Verification gate.** Every number in story text must match a computed value. Failed stories cannot be approved.
9. **Don't invent data.** Test fixtures are small, hand-made and labelled as such.
10. **UK English** in all user-facing text.

## Ask the user before

- adding a dependency outside the agreed stack (below)
- changing the data model
- anything that could cost money
- working around a blocked website/download (ask them to download it into `worker/data/inbox/` instead)

## Stack

- **Worker:** Python 3.12, uv, DuckDB, pandas, pyarrow, httpx, pydantic, supabase-py, pytest, ruff
- **Site:** Astro (static, TypeScript, content collections), React islands only for charts, Observable Plot
- **Dashboard:** Next.js App Router, TypeScript, local only (bind 127.0.0.1)
- **DB/files:** Supabase Postgres + private Storage buckets `raw`, `clean`; migrations are plain SQL in `supabase/migrations/NNNN_name.sql`
- **CI:** GitHub Actions with actions pinned to major versions, `permissions: contents: read`, uv caching

## Commands

Worker (run from `worker/`):

```sh
uv sync                              # install
uv run python -m datatales --help    # CLI
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

## Conventions

- Python: small typed functions; ruff (line length 100, rules E,F,W,I,B,UP,S,SIM); tests in `worker/tests/`, fixtures in `worker/tests/fixtures/`.
- TypeScript: ESLint + Prettier.
- Line endings: LF (enforced by `.gitattributes`).
- CLI commands live in `worker/datatales/cli.py` as argparse subcommands.
- Commits: clear imperative message. Work milestone by milestone, and stop for the user's "go" after each.

## Status

- M0 Scaffold: done
- Next: M1 Database
