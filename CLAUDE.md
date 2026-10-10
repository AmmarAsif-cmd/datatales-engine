# CLAUDE.md: DataTales Story Engine

Project rules for Claude Code sessions. Keep this file updated as conventions are decided.

## What this is

A pipeline that turns UK public datasets into verified data stories for datatales.co.uk:
ingest → profile → clean → detect → narrate → verify → review → publish.
Python computes every number. The language model (Claude chat, copy-paste, **no API**) only writes words around given numbers.

## Hard rules

1. **£0 running cost.** Free tiers only (Supabase free, GitHub Actions, Cloudflare static assets). No paid APIs or packages.
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
uv run python -m datatales db-check  # Supabase connection, tables, RLS, buckets
# M3: sources-sync | ingest <source> [--file] | datasets | profile <id> | recipe-prompt <id>
#     recipe-test <file> <id> | recipe-import <file> | recipe-approve <src> <v> --by NAME | clean <id>
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

Site (run from `site/`):

```sh
npm run dev | npm run build | npm run check | npm run lint | npm run format
```

## Site

- Astro 7, static, `build.format: 'file'` + `trailingSlash: 'never'`: URLs are `/slug` with no trailing slash. Don't change this; the migrated Hashnode URLs depend on it.
- Posts: `site/src/content/posts/<slug>.md` → `/<slug>` (migrated, frozen). Stories: `site/src/content/stories/<slug>.md` → `/stories/<slug>`.
- **Story front matter is the publish contract** (schema in `site/src/content.config.ts`): `title, description, hook, date, updated?, source{name,publisher?,url,licence?}, fetchedAt, recipeVersion, datasetChecksum?, period?, keyNumbers[1-5]{label,value,note?}, chart_spec{type,x,y,series?,highlight?,annotation?,title?,yLabel?}, chart_data[], numbers{}`. `publish.py` (M7) must write exactly this.
- `sample: true` = fake data, dev only. `scripts/check-dist.mjs` fails the build if sample content, a Supabase URL or a key reaches `dist/`.
- Charts: `Chart.tsx` (Observable Plot, `client:visible`) inside `ChartFigure.astro` (caption, legend, data table). Palette = validated dataviz default via CSS vars `--series-1..8` (light/dark); highlighted series coloured, others grey; line y-axis not zero-based; ≥2 series ⇒ legend.
- Deploy: Cloudflare Workers **static assets only** via `site/wrangler.jsonc` (no `main`, no bindings, pinned `wrangler` devDependency). Never add an Astro adapter or run `astro add cloudflare`; keep `output: 'static'`. `check-dist.mjs` fails on `_worker.js`/adapter output. `_redirects`: static rules above splat rules.
- No analytics, no external fonts, no third-party scripts (migrated posts embed public Power BI iframes only).

## Worker pipeline (M3)

- Layout: `ingest/` (common, ons, upload) → `rawio.py` (any file → grid of strings, nothing inferred) → `profile.py` → `clean/` (schema, runner, checks) → `pipeline.py` (orchestration, jobs) → `cli.py`.
- All persistence goes through the `Repo` protocol (`repo.py`); tests use `tests/memrepo.py`. Never call Supabase directly from pipeline code.
- Sources live in `worker/sources.yaml`. Raw files: `raw/<slug>/<UTC timestamp>-<sha12>/<file>` + `fetch.json` (source URL, ONS version, release date). Clean: `clean/<slug>/<dataset_id>/recipe-v<N>.parquet`.
- Recipes: declarative only, `extra="forbid"` everywhere, `yaml.safe_load`. New step types must be added to `clean/schema.py` (model) and `clean/runner.py` (`apply_step`), with tests. Only approved recipes run; versions are immutable.
- ONS fetches: HTTPS + ONS hosts only (checked on every redirect), 50 MB cap.
- pandas 3: `astype(str)` keeps NaN; use the runner's `_text()` helper for string comparisons.
- Added deps (approved by user 2026-10-10): `pyyaml`, `openpyxl`.
- Unapproved recipe versions may be overwritten with `recipe-import --replace` (they never ran); approved ones never.

## Detector rules (M4, set by the user 2026-10-10)

- Ignore unreliable values: rows with `is_reliable = false` (ONS `[u]`) and null values (suppressed `[c]`/`[x]`/`[w]`).
- Only report a change (between periods) or a gap (between geographies) when the **confidence intervals do not overlap** (`lower_ci`/`upper_ci`). Store both intervals in the finding's `numbers`.
- Only compare geographies present (with reliable, non-null values) in **both** periods being compared.
- Compare like with like: same `measure`, same `estimate`, same `geo_level`.

## Wording rules (M5)

- ONS wellbeing bands use the same labels for every measure. For **anxiety**: Poor = high anxiety, Fair = medium, Good = low, Very good = **very low** anxiety (ONS metadata). A rise in anxiety's mean is bad news. Never write "very good anxiety".

## Database

- Migrations: `supabase/migrations/NNNN_name.sql`, plain SQL, wrapped in `begin; ... commit;`. The user runs them in the Supabase SQL Editor. Never edit an applied migration; add a new one.
- Every new table must: `enable row level security`, have **no** policies, `revoke all ... from anon, authenticated`, `grant all ... to service_role`. `db-check` fails on any public table that breaks this.
- Functions: `set search_path = ''` and fully qualified names; revoke execute from `public, anon, authenticated`.
- DB-level rule: a story cannot be `approved`/`published` unless `verify_status = 'passed'`.
- Config is read by `datatales.config.load_settings()` (env vars override `worker/.env`). The key is a `SecretStr`, so never call `get_secret_value()` except when creating the client.

## Conventions

- Python: small typed functions; ruff (line length 100, rules E,F,W,I,B,UP,S,SIM); tests in `worker/tests/`, fixtures in `worker/tests/fixtures/`.
- TypeScript: ESLint + Prettier.
- Line endings: LF (enforced by `.gitattributes`).
- CLI commands live in `worker/datatales/cli.py` as argparse subcommands.
- Commits: clear imperative message. Work milestone by milestone, and stop for the user's "go" after each.

## Status

- M0 Scaffold: done
- M1 Database: done (migration 0001 + `db-check`)
- M2 Public site + Hashnode migration: done (deployed as Cloudflare Workers static assets)
- M3 Ingest, profile, clean: done (ONS wellbeing v4 ingested; recipe v1 imported, awaiting user approval)
- Next: M4 Detect
