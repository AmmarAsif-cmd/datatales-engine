# DataTales worker

Python pipeline: **ingest → profile → clean** → detect → narrate → verify → publish.
See the root [README](../README.md) for setup.

```sh
uv sync
uv run python -m datatales --help
uv run ruff check . && uv run ruff format --check . && uv run pytest
```

## Commands (M1–M3)

| Command | What it does |
|---|---|
| `db-check` | Confirm Supabase connection, tables, RLS and private buckets |
| `sources-sync` | Upsert `sources.yaml` into the `sources` table |
| `ingest <source> [--file NAME]` | Fetch the raw file (ONS API, or `data/inbox/NAME` for upload sources), store it untouched in the `raw` bucket with a `fetch.json` record, skip if the checksum is already known, then profile it |
| `datasets [--source S]` | List recent datasets and their ids |
| `profile <dataset_id> [--json]` | Re-profile a dataset |
| `recipe-prompt <dataset_id> [--out F]` | Prompt to paste into Claude chat; the reply is a recipe |
| `recipe-test <file> <dataset_id>` | Dry-run a recipe file: shows the result and checks, writes nothing |
| `recipe-import <file> [--replace]` | Validate a recipe and store it, **unapproved**. `--replace` overwrites an existing unapproved version |
| `recipe-approve <source> <version> --by NAME` | Approve it and write `recipes/<source>.v<N>.yaml` (commit this) |
| `clean <dataset_id> [--version N]` | Run the latest approved recipe, run checks, write Parquet to `clean` only if all checks pass |
| `detect <clean_table_id> [--dry-run] [--replace]` | Run all registered detectors (biggest change, rank shift, outlier), score, store the top 5 findings |
| `findings <clean_table_id> [--numbers]` | List stored findings (and their exact numbers) |
| `candidates <clean_table_id>` | Story shortlist: findings grouped by place, level and good/bad news; max 2 per place, top 5 |
| `story-new <clean_table_id> --candidate N` | Draft a story: numbers, full yearly chart data, notable moves (e.g. a 2020–21 dip) |
| `story-prompt <story_id> [--out F]` | Narration prompt to paste into Claude chat |
| `story-paste <story_id> <reply.json>` | Validate the JSON reply, verify every number and every rank word ("only", "highest"...) against the data, save (fails loudly on anything unsupported) |
| `story-verify <story_id>` | Re-run verification |
| `story-refresh <story_id>` | Rebuild a story's numbers and chart data with the current logic; back to draft for a new narration (same slug, so the URL is kept) |
| `stories` | List stories |

Every `ingest`, `profile`, `clean` and `detect` run writes a row to the `jobs` table.

## Detectors

Configured per source in `sources.yaml` under `detect:` (which columns are the group, period,
value and confidence interval; how to slice; filters; units; polarity). Rules:
unreliable/suppressed values are ignored; a change or gap is only reported when the confidence
intervals don't overlap; changes only compare groups present in both periods; comparisons
stay within one slice (same measure, estimate and geography level).

## Adding a dataset

1. Add the source to `sources.yaml` (`fetch.type: ons_api` or `upload`), then `sources-sync`.
2. Upload sources: put the CSV/XLSX in `data/inbox/` and run `ingest <source> --file <name>`.
3. `recipe-prompt <dataset_id> --out prompt.txt` → paste into Claude chat → save the YAML reply.
4. `recipe-test reply.yaml <dataset_id>` until every check passes.
5. `recipe-import reply.yaml`, review it, `recipe-approve <source> <version> --by "Your Name"`.
6. `clean <dataset_id>`.

## Recipes

Recipes are **declarative YAML**: a list of whitelisted steps (`select_sheet`, `skip_rows`,
`use_header_row`, `rename_columns`, `drop_columns`, `select_columns`, `drop_rows_where`, `filter`,
`strip_footnotes`, `parse_number`, `parse_date`, `melt`, `cast`, `dedupe`, `sort`,
`classify_prefix`, `derive_flag`) plus `checks` (expected columns, row count, not-null, unique,
`ranges`, `ranges_where` for per-category ranges, and `sums` with a multi-column `where` filter). The schema is in `datatales/clean/schema.py`. They're loaded with
`yaml.safe_load` and never executed as code.

- `recipes/drafts/` holds drafts (not approved, not used by the pipeline).
- `recipes/<source>.v<N>.yaml` files are written by `recipe-approve` and are immutable; change a
  recipe by importing a new version.

Test fixtures in `tests/fixtures/` are small, hand-made and **fake**.
