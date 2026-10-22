import { getPosts, getStories } from '../lib/content';
import { SITE } from '../lib/site';

const STATIC_PAGES = ['', '/archive', '/about', '/contact', '/privacy'];

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

export async function GET() {
  const [posts, stories] = await Promise.all([getPosts(), getStories()]);
  const live = stories.filter((s) => !s.data.sample);
  // The home page and archive change whenever a post or story is added or updated.
  const newest = [...posts, ...live]
    .map((e) => e.data.updated ?? e.data.date)
    .reduce<Date | undefined>((a, b) => (a && a > b ? a : b), undefined);
  const LISTING_PAGES = new Set(['', '/archive']);
  const entries: { loc: string; lastmod?: Date }[] = [
    ...STATIC_PAGES.map((p) => ({
      loc: SITE.url + p,
      ...(LISTING_PAGES.has(p) && newest ? { lastmod: newest } : {}),
    })),
    ...posts.map((p) => ({ loc: `${SITE.url}/${p.id}`, lastmod: p.data.updated ?? p.data.date })),
    ...stories
      .filter((s) => !s.data.sample)
      .map((s) => ({ loc: `${SITE.url}/stories/${s.id}`, lastmod: s.data.updated ?? s.data.date })),
  ];
  const body = entries
    .map(
      (e) =>
        `  <url><loc>${esc(e.loc)}</loc>${e.lastmod ? `<lastmod>${e.lastmod.toISOString()}</lastmod>` : ''}</url>`,
    )
    .join('\n');
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`,
    { headers: { 'Content-Type': 'application/xml; charset=utf-8' } },
  );
}
