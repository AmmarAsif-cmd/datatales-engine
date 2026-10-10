import type { APIRoute } from 'astro';
import sharp from 'sharp';

import { getStories, type Story } from '../../lib/content';
import { storyCoverSvg } from '../../lib/storygraphics';

/** Build-time portrait cover (1080×1350) for Instagram and LinkedIn. */
export async function getStaticPaths() {
  const stories = await getStories();
  return stories.map((story) => ({ params: { slug: story.id }, props: { story } }));
}

export const GET: APIRoute = async ({ props }) => {
  const { story } = props as { story: Story };
  const svg = new TextEncoder().encode(storyCoverSvg(story, 'portrait'));
  const png = await sharp(svg).png({ compressionLevel: 9 }).toBuffer();
  return new Response(new Uint8Array(png), { headers: { 'Content-Type': 'image/png' } });
};
