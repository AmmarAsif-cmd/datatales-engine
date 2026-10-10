// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// Pure static site: no adapter, no server output. Deployed as Cloudflare Workers static
// assets (see wrangler.jsonc). URLs have no trailing slash, matching the old Hashnode URLs
// (e.g. /wellbeing-in-the-uk): `build.format: 'file'` emits wellbeing-in-the-uk.html, which
// is served at /wellbeing-in-the-uk.
export default defineConfig({
  site: 'https://datatales.co.uk',
  output: 'static',
  trailingSlash: 'never',
  build: { format: 'file' },
  integrations: [react()],
});
