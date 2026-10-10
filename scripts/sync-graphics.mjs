// Copy the shared story-graphics modules from the site (canonical) to the dashboard.
// Run from the repo root after changing site/src/lib/graphics/: node scripts/sync-graphics.mjs
// dashboard/tests/graphics.test.ts fails if the copies differ.
import { copyFileSync, mkdirSync } from 'node:fs';

export const SHARED = ['font.ts', 'alt.ts', 'cover.ts'];
const from = new URL('../site/src/lib/graphics/', import.meta.url);
const to = new URL('../dashboard/lib/graphics/', import.meta.url);
mkdirSync(to, { recursive: true });
for (const f of SHARED) copyFileSync(new URL(f, from), new URL(f, to));
for (const f of ['Inter-Regular.ttf', 'Inter-Bold.ttf', 'OFL.txt']) {
  copyFileSync(new URL(`../site/src/data/fonts/${f}`, import.meta.url), new URL(`../dashboard/public/fonts/${f}`, import.meta.url));
}
console.log(`synced ${SHARED.join(', ')} and fonts`);
