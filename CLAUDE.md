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
# M4: detect <clean_table_id> [--dry-run|--replace] | findings <clean_table_id> [--numbers]
# M7: publish <story_id> [--mark] | run-pipeline
# M5: candidates <ct> | story-new <ct> --candidate N | story-prompt <id> | story-paste <id> <file> | story-verify <id> | story-refresh <id> | stories
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
- **Story front matter is the publish contract** (schema in `site/src/content.config.ts`): `title, description, hook, date, updated?, source{name,publisher?,url,licence?}, fetchedAt, recipeVersion, datasetChecksum?, period?, keyNumbers[1-5]{label,value,note?}, chart_spec{type: line|bar|dot|slope|map, x, y, series?, highlight?, annotation?, title?, yLabel?, start?, end?, period?}, more_charts[0-2], chart_data[] (rows may carry `code`), numbers{} (incl. `cover`, `chart_facts`)`. `publish.py` (M7) must write exactly this.
- `sample: true` = fake data, dev only. `scripts/check-dist.mjs` fails the build if sample content, a Supabase URL or a key reaches `dist/`.
- Story page: byline, "Data covers X to Y" (from chart_data periods), chart, pivoted table (periods x groups, highlighted group first, plus its 95% CI), Download CSV (`/stories/<slug>.csv`, static endpoint), build-time OG image (`/stories/<slug>.png`, text-free SVG -> PNG via `sharp`, explicit dependency, no fonts needed), related links (stories with the same `source.url`, posts whose `sources:` list it), checksum and recipe under "Technical details". Display periods use en dashes (`enDash` in `lib/chart.ts`). `check-dist` fails if a story lacks its CSV or PNG.
- Charts: `Chart.tsx` (Observable Plot, `client:visible`) inside `ChartFigure.astro` (caption, legend, data table). Palette = validated dataviz default via CSS vars `--series-1..8` (light/dark); highlighted series coloured, others grey; line y-axis not zero-based; ≥2 series ⇒ legend.
- Deploy: Cloudflare Workers **static assets only** via `site/wrangler.jsonc` (no `main`, no bindings, pinned `wrangler` devDependency). Never add an Astro adapter or run `astro add cloudflare`; keep `output: 'static'`. `check-dist.mjs` fails on `_worker.js`/adapter output. `_redirects`: static rules above splat rules.
- No analytics, no external fonts, no third-party scripts (migrated posts embed public Power BI iframes only).

## Story graphics

- Shared, DOM-free modules in `site/src/lib/graphics/` (canonical): `font.ts` (TrueType reader: cmap 4/12, glyf incl. composites, GPOS pair kerning; text becomes SVG outline paths), `alt.ts` (alt text from chart_data and verified `chart_facts`), `cover.ts` (branded cover SVG: landscape 1200x630, portrait 1080x1350). The dashboard keeps byte-identical copies in `dashboard/lib/graphics/`: change the site files, then `node scripts/sync-graphics.mjs` (dashboard test fails otherwise). Use explicit `.ts` import extensions and no parameter properties (node type stripping).
- Fonts: Inter Regular/Bold (SIL OFL, `site/src/data/fonts/`, copy in `dashboard/public/fonts/`). Never rely on system fonts for images.
- Site build: `/stories/<slug>.png` (cover: hero + OG/Twitter), `-portrait.png`, `-thumb.webp` (home/archive), via `sharp`. Fonts are loaded with Vite `?inline` (the site has no @types/node; keep node APIs out of `src/`).
- Cover facts come from Python: `numbers.cover` (`storydata.cover_facts`: value, label, change, badge = rank change from a rank_shift finding for the charted slice, else a verified only/highest/biggest framing).
- Chart types: line/bar/dot (Plot island; line charts label every series up to 8, highlighted bold, labels spread by `dodge`), slope and map (static SVG at build time in `site/src/lib/charts/static.ts`, CSS-variable colours, `<title>` tooltips). A story has `chart_spec` plus up to 2 `more_charts` (stored inside `stories.chart_spec.more_charts`; publish writes front matter `more_charts`).
- Maps: boundaries in `site/src/data/geo/` (ONS BUC, OGL, BNG; see README there; refetch with `node scripts/fetch-boundaries.mjs`). chart_data rows carry `code`; the map uses the smallest boundary file holding every code and fails the build on unknown codes. `datatales/geo.py` checks the same files when suggesting a map and at publish.
- Layout rules: cover text sits in a fixed-width column (`fitText` shrinks, then ellipsises; a clipPath guarantees it), line x labels are thinned by `pickTicks` (every 2nd+ above 8 periods, last always shown), slope labels are name over value on both sides spread by `dodge`, maps use `--seq-N` with `--seq-ink-N` label colours (>= 4.5:1; higher = stronger in both themes), key number cards are 1-4 per row (2x2 on mobile, odd counts never orphan) with a `kind: rank` card from `numbers.cover.rank`.
- Before pushing chart or layout changes, check the story page at 375px and 1280px in light and dark: build, `npx astro preview`, then `node scripts/screenshot.mjs <url> <out-prefix>` (prints any horizontal overflow).
- Review a story's graphics locally: export `{headline, chart_spec, chart_data, numbers}` to JSON, then `node --experimental-strip-types scripts/render-graphics.mjs story.json out/` (from site/).

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
- Data: ONS paused the annual (local authority) series after 2022-23 (APS quality; now 'official statistics in development'). Quarterly UK/country/region tables continue but have quality grades ([cv1]) instead of CIs, one decimal, and countries/regions for the latest quarter only. Not ingested (user to decide).
- Scope: detectors run on **UK, country and region** only (`detect.filters.geo_level` in `sources.yaml`). Add `local_authority` only after the user has reviewed the first batch.

## Detectors (M4)

- `datatales/detect/`: `base.py` (Finding, DetectMeta, helpers, `REGISTRY` + `@register`), `prepare.py` (clean table → standard frame via `sources.yaml` `detect:` config), one module per detector (`change.py`, `rank.py`, `outlier.py`), `scoring.py`, `run.py`.
- A detector is a pure function `(frame, meta) -> list[Finding]` decorated with `@register("name")`, imported in `detect/__init__.py`. Phase 2 (record high/low, crossover, group gap, turning point) adds modules the same way, with tests.
- Standard frame columns: `group, group_code, period, period_label, value, lower, upper` + slice columns. Rows are already reliable and non-null; iterate with `iter_slices`, pair periods with `panel()` (inner join = present in both), test CIs with `cis_separate()` (unknown CI ⇒ not significant).
- Output must not depend on input row order (frames are sorted in `prepare`; ties broken explicitly).
- Score = effect_norm(effect / normal variation) × surprise × relatability/5 × freshness (release date, −0.2/year, floor 0.2). Top `detect.top_n` (5) per clean table; findings for the same slice+group merge, extras under `numbers.related`.
- Findings store every number a story may use: values, CIs, periods, ranks, `unit`, `change_unit` ("percentage points" for % values), `higher_is_better`, `improved`, `score_parts`.
- `detect --replace` refuses if any story uses the existing findings.

## Stories (M5)

- `candidates.py`: findings grouped by (geography, geo_level, good_news) across measures; candidate score = best finding x (1 + 0.15 per extra measure); shortlist top 5, max 2 per geography. Detectors keep 20 findings per clean table (`detect.top_n`) so grouping has material.
- `storydata.py`: chart_data = the full yearly series of every geography in the chart slice (the candidate finding with the most geographies, then years, then score); `numbers.series[]` = the candidate geography's yearly points per measure + `notable_moves` (CI-clear and >= 2x typical yearly change; fall-then-rise = dip) + `moves_shared_by_most_geographies`.
- `storydata.py` also adds `series[].peak` (peak/low/latest; `latest_well_below_peak` = CIs apart and gap >= 2x typical yearly change), `numbers.caveats` (from `sources.yaml` `caveats:`, e.g. the ONS pause after 2022-23) and `numbers.chart_facts` (`chartfacts.facts_for`: which only/all/highest/lowest/biggest framings the chart data clearly supports).
- `narrate.py`: prompt + strict reply schema (json.loads only). Rules: headline states the single strongest finding (never a topic label); prefer only/first/rank-change framing when `chart_facts` supports it; say when the latest value is well below the peak; body 500-700 words (validator accepts 450-750) with `## How it compares` and `## What the data can't tell us`; mention every caveat; en dashes in financial years; polarity, percentage points.
- `chartfacts.py`: `evaluate(check, chart_data)` for kinds highest, lowest, only_rise/fall, all_rise/fall, biggest_rise/fall. highest/lowest need the group's CI clear of the runner-up; only/biggest need the group's own change CI-clear; all_* is direction only.
- `verify.py`: every number in headline/hook/summary/body_md/video_script must equal a number anywhere in `stories.numbers` after rounding to the written decimals (sign ignored); years and financial years must be inside `data_period`. Word numbers two-twenty/twice are checked; "one"/"first"/"half" are not (too idiomatic). Limitation: it checks that a number exists in the data, not that it is attached to the right claim; human review covers that.
- `stories.py`: `create_story` (draft, provisional slug) -> `story_prompt` -> `paste_narration` (parse, verify, slug from headline, unique) -> `reverify` (after edits). Approved/published stories are locked. DB constraint blocks approving a story whose verify_status is not `passed`.
- Claims: the narration reply must include `claims: [{sentence, keys, checks}]`; keys come from `verify.flatten_numbers` (f1.end_value, s1.points.2020-21.value, ...), listed in the prompt's KEYS table. The verifier checks each sentence exists, each key exists, each number matches one of ITS keys, and no number sits outside a claim. Rank words (only, all, highest, lowest, biggest, largest) must sit in a claim with a matching check (`assertion_missing` otherwise) and every check must hold against chart_data (`assertion_failed`); rank words outside claims are `uncovered`. Years quoted in `numbers.caveats` are allowed. Results live in `verify_report.claims` / `.uncovered`.
- CLI: `candidates <ct>`, `story-new <ct> --candidate N`, `story-prompt <id> [--out]`, `story-paste <id> <file>`, `story-verify <id>`, `story-refresh <id>` (rebuild numbers/chart data from findings with current logic; back to draft, verify pending; keeps the slug), `stories`.
- Slugs are set once from the first headline and never change afterwards, so a revised story republishes at the same URL. `publish.py` keeps the original `date` from the existing file and sets `updated`; it writes en dashes into displayed periods (data labels keep hyphens).

## Wording rules (M5)

- ONS wellbeing bands use the same labels for every measure. For **anxiety**: Poor = high anxiety, Fair = medium, Good = low, Very good = **very low** anxiety (ONS metadata). A rise in anxiety's mean is bad news. Never write "very good anxiety".

## Dashboard (M6, deployed in M7)

- `dashboard/`: Next.js 16 App Router on **Cloudflare Workers via OpenNext** at admin.datatales.co.uk, behind **Cloudflare Access** (user decision 2026-10-10, overriding the original "never deploy"). `workers_dev`/preview URLs off. Read `dashboard/node_modules/next/dist/docs/` before changing Next code (Next 16: `middleware` is `proxy`; params are Promises).
- Auth: every page calls `pageUser()` and every server action `requireUser()` (`lib/access.ts` verifies the Access JWT: RS256 via WebCrypto, iss, aud, exp). Fails closed. No `proxy.ts` (Node middleware on Workers is experimental in OpenNext). Local bypass only in `next dev` with a localhost Host.
- Secrets: Worker secrets only (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GITHUB_DISPATCH_TOKEN, CF_ACCESS_TEAM_DOMAIN, CF_ACCESS_AUD). **Never `.env*` in dashboard/**: OpenNext bundles them. Local dev uses `.dev.vars`. `npm run build:cf` guards both ways.
- **Next is pinned to 16.3.8**: @opennextjs/cloudflare 1.20.10 crashes on Next 16.4 at runtime (preview-props.json not inlined, error 1101). Never upgrade Next/the adapter without `npm run build:cf && npm run smoke:cf` passing (CI runs it).
- Every page starts with `const gate = await pageGate(); if (gate) return gate;` (config problems page, then Access). `app/error.tsx` and `app/global-error.tsx` catch everything else.
- No Python on Workers. Pure text logic is ported to TypeScript in `dashboard/lib/logic/` (verify, narrate/prompt, shortlist, slug). **Change Python first**, regenerate `uv run python -m tests.golden_cases --write`, then mirror in TS until `npm test` passes. Never let them diverge.
- Heavy/repo-writing work runs in GitHub Actions via **workflow_dispatch** (token: fine-grained, this repo, Actions read/write only): `story-new.yml`, `publish.yml` (write file, build site, commit, push, then `publish --mark`), `recipe-approve.yml`, `pipeline.yml`. Workflow inputs go through env vars and are validated; never interpolate `${{ inputs.* }}` into scripts.
- `datatales/api.py` (JSON bridge) remains for local scripting; the deployed dashboard doesn't use it.
- Story status transitions: draft -> approved (verify passed only) | rejected; rejected -> draft; approved -> draft; published -> draft ("Revise": clears published_at; the live page stays until republished); approved -> published only by `publish.yml`.

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
- M4 Detect: done (3 detectors; awaiting recipe approval + clean to store real findings)
- M5 Narrate + verify: done (candidates, full-series chart data, notable moves, prompt, parser, number checker)
- M6 Dashboard: done
- M7 Publish + pipeline + dashboard deployment: done in code (needs user's Cloudflare/GitHub setup; then Approve publishes)
- Next source after M7 (user, 2026-10-10): DfT vehicle licensing statistics (VEH tables), via upload ingest
