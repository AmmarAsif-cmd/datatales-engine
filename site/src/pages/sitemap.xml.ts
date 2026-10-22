import { getPosts, getStories } from '../lib/content';
import { SITE } from '../lib/site';

const STATIC_PAGES = ['', '/archive', '/about', '/contact', '/privacy'];

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');

export async function GET() {
  const [posts, stories] = await Promise.all([getPosts(), getStories()]);
  const entries: { loc: string; lastmod?: Date }[] = [
    ...STATIC_PAGES.map((p) => ({ loc: SITE.url + p })),
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
