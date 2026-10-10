# DataTales review dashboard

Next.js 16 (App Router) deployed to **Cloudflare Workers** with the OpenNext adapter at
**https://admin.datatales.co.uk**, behind **Cloudflare Access**. It can also run locally.

## How it works

| What | Where it runs |
|---|---|
| Pages (findings, stories, datasets & jobs, recipes) | Server-rendered on the Worker; Supabase read with the service key (Worker secret) |
| Paste reply → validate → **verify claims** → edit → re-verify | Instantly, in TypeScript (`lib/logic/`), a port of the Python verifier |
| Approve / reject | Supabase update (the database also refuses approval unless verification passed) |
| Approve → **publish** | `publish.yml` (GitHub Actions): write story file → build site → commit → push → mark published |
| Create story, approve recipe, **Run pipeline now** | `story-new.yml`, `recipe-approve.yml`, `pipeline.yml` (GitHub Actions) |

The TypeScript port must match Python exactly: `npm test` replays every case in
`worker/tests/golden/cases.json` (generated from Python), including a real story and a broken
version of it. CI fails if they ever disagree.

Workflows are started with **workflow_dispatch**, which needs a token with only
**Actions: Read and write** on this repository. (repository_dispatch would need
Contents: write, a token that could also push code.)

## Security

- **Cloudflare Access** in front of the custom domain. `workers_dev` and preview URLs are off,
  so there is no other way in.
- **The app verifies the Access JWT itself** on every page and server action (`lib/access.ts`:
  RS256 signature against your team's keys, issuer, audience = this app's AUD tag, expiry).
  It **fails closed**: if the settings are missing, every request is refused. Next 16's `proxy`
  is not used: OpenNext calls Node middleware on Workers experimental.
- **Secrets are Worker secrets only.** Never put them in `.env*` files here: OpenNext bundles
  every `.env*` file into the Worker. `npm run build:cf` refuses to build if one exists, and
  checks the finished bundle for secret names and values.

## 1. One-time Cloudflare Access setup (you)

Prerequisite: the `datatales.co.uk` DNS zone is on Cloudflare (needed for the custom domain).

1. **Zero Trust** dashboard (one.dash.cloudflare.com). The Free plan is fine (up to 50 users).
   On first visit, choose a **team name**; your team domain is `https://<team>.cloudflareaccess.com`.
2. **Settings → Authentication → Login methods → Add new → One-time PIN.** (Optionally add
   Google. With only one method, you can turn on "Instant Auth" on the app.)
3. **Access → Applications → Add an application → Self-hosted:**
   - **Application name:** `DataTales admin`
   - **Session duration:** `24 hours`
   - **Application domain:** subdomain `admin`, domain `datatales.co.uk`, path *empty* (the whole site)
   - **Identity providers:** One-time PIN (and Google if added)
   - **Policy:** name `Owner`, **Action: Allow**, **Include → Emails →** your email address.
     Don't use "Everyone" and don't add any Bypass policy.
   - **Cookie settings:** SameSite `Lax`, HTTP Only **on**, Binding Cookie **on**
   - Leave CORS settings empty. Save.
4. Open the application's **Overview** and copy the **Application Audience (AUD) Tag**.
5. Set the two Access secrets on the Worker (step 3 below):
   `CF_ACCESS_TEAM_DOMAIN` = `https://<team>.cloudflareaccess.com` (no trailing slash) and
   `CF_ACCESS_AUD` = the AUD tag.

## 2. GitHub setup (you)

1. **Repository secrets** (repo → Settings → Secrets and variables → Actions → New repository
   secret): `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`, used by the workflows.
2. **Fine-grained token for the dashboard** (your profile → Settings → Developer settings →
   Personal access tokens → Fine-grained tokens → Generate new token):
   - **Resource owner:** you. **Expiration:** 90 days (put a renewal reminder in your calendar).
   - **Repository access:** *Only select repositories* → `datatales-engine`
   - **Permissions → Repository permissions → Actions: Read and write.** Nothing else (Metadata:
     read is added automatically).
   - Save it as the Worker secret `GITHUB_DISPATCH_TOKEN`.
3. If you ever add branch protection to `main`, allow GitHub Actions to push, because the publish
   and recipe-approve workflows commit to `main`.

## 3. Deploy

**Recommended: Cloudflare Workers Builds.** Workers & Pages → Create → Import a repository →
`datatales-engine`:

| Setting | Value |
|---|---|
| Project name | `datatales-admin` |
| Root directory | `dashboard` |
| Build command | `npm run build:cf` |
| Deploy command | `npx opennextjs-cloudflare deploy` |
| Build variable | `NODE_VERSION` = `22` |

Then set the Worker secrets, either in the dashboard (Worker → Settings → Variables and
Secrets → Add → type *Secret*) or from this folder:

```sh
npx wrangler secret put SUPABASE_URL
npx wrangler secret put SUPABASE_SERVICE_ROLE_KEY
npx wrangler secret put GITHUB_DISPATCH_TOKEN
npx wrangler secret put CF_ACCESS_TEAM_DOMAIN
npx wrangler secret put CF_ACCESS_AUD
```

Check: open `https://admin.datatales.co.uk`. You should see the Access login, then the
dashboard with your email in the top bar.

## Local development

```sh
cd dashboard
cp .dev.vars.example .dev.vars    # fill in SUPABASE_*, GITHUB_DISPATCH_TOKEN (not .env.local!)
npm install
npm run dev                       # http://127.0.0.1:4317 (shows LOCAL DEV, no Access needed)
```

Locally, sign-in is skipped only in `next dev` with a localhost Host header. Production builds
always require a valid Access token.

## Checks

```sh
npm run lint
npm run typecheck
npm test          # golden vectors (TS == Python) + Access JWT tests
npm run build:cf  # Cloudflare build with the env-file guard and bundle secret scan
```
