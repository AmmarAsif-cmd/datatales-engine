# DataTales public site

Static [Astro](https://astro.build) site for **datatales.co.uk**, deployed by Cloudflare Pages.

The site builds **only from files committed in this repo**. It never reads a Supabase key and never
calls Supabase.

## Commands

Run from `site/`:

| Command | What it does |
|---|---|
| `npm install` | Install dependencies |
| `npm run dev` | Local dev server on http://127.0.0.1:4321 (sample stories visible) |
| `npm run build` | Production build to `dist/`, then `scripts/check-dist.mjs` |
| `npm run preview` | Serve the production build locally |
| `npm run check` | TypeScript + Astro type check |
| `npm run lint` / `npm run format` | ESLint / Prettier |

`check-dist.mjs` fails the build if any old Hashnode URL is missing, if sample content reaches
`dist/`, or if anything that looks like a Supabase key or URL appears in the output.

## Content

| Folder | URL | Written by |
|---|---|---|
| `src/content/posts/*.md` | `/<slug>` | Migrated from Hashnode (frozen; edit by hand only) |
| `src/content/stories/*.md` | `/stories/<slug>` | The publish step (`worker/datatales/publish.py`, M7) |

Schemas are in `src/content.config.ts`. A story with `sample: true` (fake data) is shown by
`npm run dev` only. It is excluded from production builds, the sitemap and RSS.
To preview a production-like build that includes samples: `SHOW_SAMPLES=true npx astro build`.

URLs have no trailing slash (`build.format: 'file'`), matching the old Hashnode URLs.

## Cloudflare Pages settings

| Setting | Value |
|---|---|
| Root directory | `site` |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Environment variable | `NODE_VERSION` = `22` |

No secrets or environment variables are needed. `public/_redirects` holds old Hashnode paths.
