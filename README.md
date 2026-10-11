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
   drafting and test runs).
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
