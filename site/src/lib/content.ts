import { getCollection, type CollectionEntry } from 'astro:content';

import { coverPaths, storyCoverAlt } from './storygraphics';

export type Post = CollectionEntry<'posts'>;
export type Story = CollectionEntry<'stories'>;

type NodeGlobal = { process?: { env: Record<string, string | undefined> } };

/**
 * Sample stories (fake data) are shown in `astro dev` only. A production build never
 * includes them, unless SHOW_SAMPLES=true is set for a local preview build.
 */
export const showSamples =
  import.meta.env.DEV || (globalThis as NodeGlobal).process?.env.SHOW_SAMPLES === 'true';

export async function getPosts(): Promise<Post[]> {
  const posts = await getCollection('posts');
  return posts.sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
}

export async function getStories(): Promise<Story[]> {
  const stories = await getCollection('stories', ({ data }) => showSamples || !data.sample);
  return stories.sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
}

export type FeedItem = {
  kind: 'story' | 'post';
  title: string;
  description: string;
  date: Date;
  url: string;
  sample?: boolean;
  /** Story cover thumbnail (600×315). */
  image?: { src: string; alt: string };
};

export async function getFeed(): Promise<FeedItem[]> {
  const [posts, stories] = await Promise.all([getPosts(), getStories()]);
  const items: FeedItem[] = [
    ...stories.map((s) => ({
      kind: 'story' as const,
      title: s.data.title,
      description: s.data.hook,
      date: s.data.date,
      url: `/stories/${s.id}`,
      sample: s.data.sample,
      image: { src: coverPaths(s.id).thumb, alt: storyCoverAlt(s) },
    })),
    ...posts.map((p) => ({
      kind: 'post' as const,
      title: p.data.title,
      description: p.data.description,
      date: p.data.date,
      url: `/${p.id}`,
    })),
  ];
  return items.sort((a, b) => b.date.valueOf() - a.date.valueOf());
}

const dateFmt = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'Europe/London',
});

export function formatDate(d: Date): string {
  return dateFmt.format(d);
}
