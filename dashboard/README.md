# DataTales review dashboard (local only)

> **Do not deploy this app.** It holds the Supabase service-role key and has no login.
> It binds to `127.0.0.1` and refuses requests addressed to any other host.

Next.js (App Router, TypeScript). Pages read Supabase on the server. Every action (create a
story, build the prompt, paste a reply, verify, approve) runs the Python worker through one
bridge, `python -m datatales api <action>`, so each rule and check has a single implementation.

## Setup

```sh
cd dashboard
cp .env.example .env.local    # fill in SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (server-only)
npm install
cd ../worker && uv sync       # the dashboard runs worker/.venv's Python
cd ../dashboard
npm run dev                   # http://127.0.0.1:4317
```

The worker's Python is found at `worker/.venv`. Set `DATATALES_PYTHON` to use a different
interpreter. The dashboard passes its own Supabase settings to the worker, so both always use
the same project.

## Pages

| Page | What you do there |
|---|---|
| **Findings** | Pick a clean table; see the story shortlist (max 2 per place) and every finding with a mini chart of start → end and its confidence intervals. "Create story" drafts one. |
| **Stories** | All stories with status and verification. |
| **Story editor** | 1) Copy the prompt into Claude chat. 2) Paste the JSON reply. The verification report shows unmatched numbers, out-of-range years, numbers outside any claim and every claim with its numbers mapped to keys (mismatches in red). 3) Edit text and claims, then re-verify. Approve (only when verification passed) or reject. Chart preview included. |
| **Datasets & jobs** | Raw files, profiles, clean tables with failing checks, and job logs. |
| **Recipes** | Recipe specs and approval (writes `worker/recipes/<source>.v<N>.yaml`; commit it). |

## Checks

```sh
npm run lint
npm run typecheck
```
