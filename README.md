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
- **£0 running cost:** Supabase free tier, GitHub Actions and Cloudflare Pages.

## Repository layout

| Folder | What it is | Runs where |
|---|---|---|
| `worker/` | Python 3.12 pipeline (DuckDB, pandas, pydantic) | Your machine + GitHub Actions |
| `site/` | Astro public site | Built by Cloudflare Pages |
| `dashboard/` | Next.js review app | **Your machine only** |
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
2. Paste the whole of `supabase/migrations/0001_init.sql` and click **Run**.
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

Cloudflare Pages builds it from `site/` using only committed files. See [site/README.md](site/README.md)
for the Pages settings, content folders and how sample stories are kept out of production.

## Review dashboard

Arrives in Milestone 6.

> ⚠️ **Never deploy the dashboard.** It holds the Supabase service-role key, has no login,
> and is meant to run only on `127.0.0.1`.

## Secrets

| Secret | Where it lives |
|---|---|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | `worker/.env` (local), GitHub Actions secrets, `dashboard/.env.local` |
| *(none)* | `site/` never holds or reads any key |

Only `.env.example` files (placeholder names, no values) are committed.

## Milestones

- [x] M0 Scaffold
- [x] M1 Database (migrations, RLS, buckets, `db-check`)
- [x] M2 Public site + Hashnode migration
- [ ] M3 Ingest, profile, clean
- [ ] M4 Detect
- [ ] M5 Narrate + verify
- [ ] M6 Review dashboard
- [ ] M7 Publish + weekly pipeline
