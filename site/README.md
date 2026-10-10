# DataTales public site

Static [Astro](https://astro.build) site for **datatales.co.uk**, deployed by Cloudflare Pages.

The site builds **only from files committed in this repo**. It never reads a Supabase key and never
calls Supabase.

## Commands

Run from `site/`:

| Command                           | What it does                                                       |
| --------------------------------- | ------------------------------------------------------------------ |
| `npm install`                     | Install dependencies                                               |
| `npm run dev`                     | Local dev server on http://127.0.0.1:4321 (sample stories visible) |
| `npm run build`                   | Production build to `dist/`, then `scripts/check-dist.mjs`         |
| `npm run preview`                 | Serve the production build locally                                 |
| `npm run check`                   | TypeScript + Astro type check                                      |
| `npm run lint` / `npm run format` | ESLint / Prettier                                                  |

`check-dist.mjs` fails the build if any old Hashnode URL is missing, if sample content reaches
`dist/`, or if anything that looks like a Supabase key or URL appears in the output.

## Content

| Folder                     | URL               | Written by                                           |
| -------------------------- | ----------------- | ---------------------------------------------------- |
| `src/content/posts/*.md`   | `/<slug>`         | Migrated from Hashnode (frozen; edit by hand only)   |
| `src/content/stories/*.md` | `/stories/<slug>` | The publish step (`worker/datatales/publish.py`, M7) |

Schemas are in `src/content.config.ts`. A story with `sample: true` (fake data) is shown by
`npm run dev` only. It is excluded from production builds, the sitemap and RSS.
To preview a production-like build that includes samples: `SHOW_SAMPLES=true npx astro build`.

URLs have no trailing slash (`build.format: 'file'`), matching the old Hashnode URLs.

## Deployment (Cloudflare Workers, static assets)

The site deploys as **static assets only**: `wrangler.jsonc` has no `main`, no adapter and no
bindings. Do not run `astro add cloudflare`. The site must stay `output: 'static'` with no adapter.

Cloudflare Workers Builds settings:

| Setting              | Value                 |
| -------------------- | --------------------- |
| Root directory       | `site`                |
| Build command        | `npm run build`       |
| Deploy command       | `npx wrangler deploy` |
| Environment variable | `NODE_VERSION` = `22` |

`wrangler` is a pinned devDependency, so the deploy uses the version in `package-lock.json`.
No secrets or environment variables are needed.

- `public/_redirects`: old Hashnode paths. Static rules go **above** splat (`*`) rules.
- `public/_headers`: security headers, and long-term caching for hashed `/_astro/*` files.
- `html_handling: drop-trailing-slash`: `/slug.html` and `/slug/` redirect to `/slug`.
- `not_found_handling: 404-page`: unknown URLs get `404.html` with a 404 status.

Check locally before pushing:

```sh
npm run build
npx wrangler deploy --dry-run   # no login needed; should say "No bindings found"
npx wrangler dev                # serves dist/ with redirects + headers on http://localhost:8787
```
