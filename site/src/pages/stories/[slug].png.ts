import type { APIRoute } from 'astro';
import sharp from 'sharp';

import type { ChartSpec, Row } from '../../lib/chart';
import { getStories, type Story } from '../../lib/content';
import { OG_SIZE, ogSvg } from '../../lib/story';

/** Build-time social card per story: the chart (no text) with the DataTales logo. */
export async function getStaticPaths() {
  const stories = await getStories();
  return stories.map((story) => ({ params: { slug: story.id }, props: { story } }));
}

const LOGO_HEIGHT = 64;
/** Builds run from site/ (npm run build). */
const LOGO = 'public/images/logo.png';

export const GET: APIRoute = async ({ props }) => {
  const { story } = props as { story: Story };
  const svg = ogSvg(story.data.chart_spec as ChartSpec, story.data.chart_data as Row[]);
  const logo = await sharp(LOGO).resize({ height: LOGO_HEIGHT }).png().toBuffer();
  const png = await sharp(new TextEncoder().encode(svg))
    .resize(OG_SIZE.w, OG_SIZE.h)
    .composite([{ input: logo, top: 40, left: 90 }])
    .png({ compressionLevel: 9 })
    .toBuffer();
  return new Response(new Uint8Array(png), { headers: { 'Content-Type': 'image/png' } });
};
