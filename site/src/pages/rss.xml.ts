import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { getFeed } from '../lib/content';
import { SITE } from '../lib/site';

export async function GET(context: APIContext) {
  const feed = (await getFeed()).filter((item) => !item.sample);
  return rss({
    title: SITE.name,
    description: SITE.description,
    site: context.site ?? SITE.url,
    trailingSlash: false,
    customData: '<language>en-gb</language>',
    items: feed.map((item) => ({
      title: item.title,
      description: item.description,
      pubDate: item.date,
      link: item.url,
      categories: [item.kind === 'story' ? 'Data story' : 'Article'],
    })),
  });
}
