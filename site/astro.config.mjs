// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// Static site. URLs have no trailing slash, matching the old Hashnode URLs
// (e.g. /wellbeing-in-the-uk). `build.format: 'file'` emits wellbeing-in-the-uk.html,
// which Cloudflare Pages serves at /wellbeing-in-the-uk without a redirect.
export default defineConfig({
  site: 'https://datatales.co.uk',
  output: 'static',
  trailingSlash: 'never',
  build: { format: 'file' },
  integrations: [react()],
});
