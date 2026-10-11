# DataTales Story Engine

Turns raw UK public datasets into verified, publish-ready data stories for
[datatales.co.uk](https://datatales.co.uk).

```
ingest → profile → clean → detect → narrate → verify → review → publish
```

- **Python does all the maths.** Every number in a story is computed by code and stored with the story.
- **Claude only writes words** around numbers it is given. In this phase there is no Claude API: prompts are copied into Claude chat and the JSON reply is pasted back.
- **Nothing is published until it is approved** in the local review dashboard.
- **The public site is fully static** and holds no secrets.
- **£0 running cost:** Supabase free tier, GitHub Actions and Cloudflare (free static assets).

## Repository layout

| Folder | What it is | Runs where |
|---|---|---|
| `worker/` | Python 3.12 pipeline (DuckDB, pandas, pydantic) | Your machine + GitHub Actions |
| `site/` | Astro public site | Cloudflare Workers (static assets) |
| `dashboard/` | Next.js review app | Cloudflare Workers at admin.datatales.co.uk, behind Cloudflare Access |
| `supabase/migrations/` | Plain SQL migrations | Run by you against Supabase |
| `.github/` | CI, weekly pipeline, Dependabot | GitHub |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python env and dependency manager). On Windows:
  `winget install astral-sh.uv`. uv installs Python 3.12 for you.
- Node.js 22+ and npm (for `site/` and `dashboard/`)
- Git

## Worker

```sh
cd worker
cp .env.example .env      # then fill in values (never commit .env)
uv sync                   # creates .venv with Python 3.12 + deps
uv run python -m datatales --help
```

Checks (the same ones CI runs):

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Database setup (Supabase)

One-time, per Supabase project. Migrations live in `supabase/migrations/` and are run by hand,
in number order, in the Supabase **SQL Editor**.

1. Open your project at [supabase.com/dashboard](https://supabase.com/dashboard) → **SQL Editor** → **New query**.
2. Paste the whole of `supabase/migrations/0001_init.sql` and click **Run**. Then do the same
   for each later migration in order (`0002_llm_calls.sql`: Claude API usage log;
   `0003_story_drafting.sql`: automatic story drafting; `0004_recipe_drafting.sql`: recipe
   drafting and test runs; `0005_dataset_backlog.sql`: dataset discovery;
   `0006_new_sources.sql`: detector settings drafted for new sources).
   It should end with "Success. No rows returned". It runs in a transaction, so on error nothing is applied.
3. Check from the worker:
   ```sh
   cd worker
   uv run python -m datatales db-check
   ```
   Every line should start with `OK`, ending in "Database check passed."

What the migration creates: tables `sources`, `datasets`, `recipes`, `clean_tables`, `findings`,
`stories`, `jobs` (all with RLS on and **no** policies, so only the service role can touch them);
private storage buckets `raw` and `clean`; and a `dt_security_status()` function (service role only)
that `db-check` uses to confirm nothing is exposed.

## Public site

```sh
cd site
npm install
npm run dev      # http://127.0.0.1:4321
npm run build    # production build + checks
```

Cloudflare Workers Builds deploys it from `site/` as static assets, using only committed files.
See [site/README.md](site/README.md) for the deploy settings, content folders and how sample stories are kept out of production.

## Review dashboard

Deployed at **https://admin.datatales.co.uk** behind Cloudflare Access. See
[dashboard/README.md](dashboard/README.md) for setup: the Access settings, the fine-grained token
and Worker secrets.

**Approve publishes.** The dashboard starts `publish.yml`, which writes
`site/src/content/stories/<slug>.md`, builds the site, commits and pushes (Cloudflare rebuilds
the site), then marks the story published. **Run pipeline now** starts `pipeline.yml`, which also
runs every Monday at 06:00 UTC.

## Automation with Claude (Phase 2)

### The weekly flow

Every Monday at 06:00 UTC, `.github/workflows/pipeline.yml` runs these steps in order:

1. **Discover** (`discover`). It reads catalogue metadata from data.gov.uk and the ONS, applies
   hard filters in code (Open Government Licence, machine-readable, nothing personal), and
   Claude Haiku scores what is left. The best few appear on **Suggested** for you to accept or
   reject.
2. **Add a dataset** (`add-datasets`). The highest-scored *accepted* dataset becomes a source.
   Its data file is found on the publisher's page, then downloaded, stored untouched and
   profiled. Claude Sonnet drafts a cleaning recipe and the detector settings, and both are
   test-run in memory. If any step fails, the error is shown on the item and the next accepted
   item is tried.
3. **Pipeline** (`run-pipeline`). For every source with an approved recipe, it fetches the
   latest file, cleans it, runs the detectors, and Claude Opus drafts stories for the best new
   findings. Code checks every number in a draft against the data before you see it.
4. **Commit.** New source files (`worker/sources.d/`) are committed to the repository.

**Nothing publishes without you.** Recipes are approved on **Recipes**, and stories are
approved (which publishes them) on **Stories**. The **Overview** page starts with a weekly
summary of what is waiting for you.

To run the whole flow now: GitHub → Actions → **pipeline** → *Run workflow*, and tick
`new_datasets`. The dashboard's **Run pipeline now** button runs step 3 only.

### Settings

| File | Setting | Default |
|---|---|---|
| `worker/config/llm.yaml` | `monthly_budget_gbp` | 5 |
| | model, `max_tokens` and `effort` per task (`story`, `recipe`, `discovery`, `check`) | Opus / Sonnet / Haiku / Haiku |
| | `pricing` (USD per million tokens), `usd_to_gbp` | as published 2026-10-11 |
| `worker/config/discovery.yaml` | `suggestions_per_week`, `min_score`, `max_to_score` | 5, 55, 40 |
| | `new_datasets_per_week` (0 turns the add step off) | 1 |
| | search topics, excluded keywords | |

**Changing a model or the budget:** edit `worker/config/llm.yaml`. If you change a model, also
add its prices under `pricing`. Then run:

```sh
cd worker
uv run python -m datatales llm-config-sync   # copies the settings to the dashboard
uv run pytest                                 # a test fails if the two copies differ
```

Commit both files and redeploy the dashboard (`cd dashboard && npm run deploy`).

### Cost

```sh
cd worker
uv run python -m datatales llm-report            # this month, by task and model
uv run python -m datatales llm-report --days 7   # the last 7 days
```

Costs are estimates calculated from the token counts logged in `llm_calls`. Compare them now and
then with the usage page in the Anthropic Console. A typical week (one discovery run, one
recipe with detector settings, a few story drafts) should cost well under £1.

### When the monthly budget is reached

Before each call, the budget guard adds the worst-case cost of that call to this month's
spend. If the total would go over the budget, the call is not sent, a `budget_blocked` row is
logged, and work carries on without Claude:

- Discovery falls back to a keyword score, and the add step falls back to a keyword file choice.
- Recipes are not drafted. Use `recipe-prompt` and copy-paste instead, or wait until next month.
- Stories are still created, but wait for **Copy prompt / Paste result** on the dashboard.

The dashboard shows a red banner. You can wait for the 1st of the month (UTC), or raise
`monthly_budget_gbp` as described above. To be safe, also set a hard spending limit in the
Anthropic Console.

### Rotating `ANTHROPIC_API_KEY`

1. In the Anthropic Console → API keys, create a new key.
2. GitHub → repository Settings → Secrets and variables → Actions → `ANTHROPIC_API_KEY` →
   *Update secret*.
3. Dashboard Worker: `cd dashboard && npx wrangler secret put ANTHROPIC_API_KEY` (paste the key
   when asked), or Cloudflare dashboard → Workers → `datatales-admin` → Settings → Variables and
   Secrets.
4. Update `worker/.env` and `dashboard/.dev.vars` if you keep the key locally.
5. Check it: GitHub → Actions → **llm-check** → *Run workflow*.
6. Delete the old key in the Console.

The key is never written to code, logs, error messages, Supabase or the site bundle. The repo
scan test and `dashboard/scripts/check-bundle.mjs` both fail if a key-shaped string appears.


## Secrets

| Secret | Where it lives |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | `worker/.env` (local), GitHub Actions secrets, dashboard Worker secrets (`dashboard/.dev.vars` locally) |
| `GITHUB_DISPATCH_TOKEN` (Actions: write, this repo only), `CF_ACCESS_*` | Dashboard Worker secrets |
| `ANTHROPIC_API_KEY` | GitHub Actions secret, dashboard Worker secret (`datatales-admin`); optionally `worker/.env` / `dashboard/.dev.vars` locally. Never in code, logs, Supabase or the site |
| *(none)* | `site/` never holds or reads any key |

Only `.env.example` files (placeholder names, no values) are committed.

## Milestones

- [x] M0 Scaffold
- [x] M1 Database (migrations, RLS, buckets, `db-check`)
- [x] M2 Public site + Hashnode migration
- [x] M3 Ingest, profile, clean
- [x] M4 Detect
- [x] M5 Narrate + verify
- [x] M6 Review dashboard
- [x] M7 Publish + weekly pipeline + deployed dashboard
- [x] P2.1 Claude API foundation (`llm_calls`, budget guard, `llm-check`)
- [x] P2.2 Automatic story drafting (pipeline + "Regenerate with Claude")
- [x] P2.3 Automatic recipe drafting with sandbox test runs
- [x] P2.4 Dataset discovery and backlog (weekly, data.gov.uk + ONS)
- [x] P2.5 Weekly new-dataset step (accepted backlog item -> source -> recipe + detector drafts)
- [x] P2.6 Weekly summary on the dashboard overview (email not set up yet)
- [x] P2.7 End-to-end test, Phase 2 docs, `llm-report`
