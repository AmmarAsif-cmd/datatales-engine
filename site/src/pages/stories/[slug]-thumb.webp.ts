import type { APIRoute } from 'astro';
import sharp from 'sharp';

import { getStories, type Story } from '../../lib/content';
import { storyCoverSvg } from '../../lib/storygraphics';

/** Small cover for the home and archive lists (600×315, WebP). */
export async function getStaticPaths() {
  const stories = await getStories();
  return stories.map((story) => ({ params: { slug: story.id }, props: { story } }));
}

export const GET: APIRoute = async ({ props }) => {
  const { story } = props as { story: Story };
  const svg = new TextEncoder().encode(storyCoverSvg(story, 'landscape'));
  const webp = await sharp(svg, { density: 72 }).resize(600, 315).webp({ quality: 82 }).toBuffer();
  return new Response(new Uint8Array(webp), { headers: { 'Content-Type': 'image/webp' } });
};
