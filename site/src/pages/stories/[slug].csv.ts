import type { APIRoute } from 'astro';

import type { Row } from '../../lib/chart';
import { getStories, type Story } from '../../lib/content';
import { toCsv } from '../../lib/story';

/** The data behind each story's chart, as a static CSV file. */
export async function getStaticPaths() {
  const stories = await getStories();
  return stories.map((story) => ({ params: { slug: story.id }, props: { story } }));
}

export const GET: APIRoute = ({ props }) => {
  const { story } = props as { story: Story };
  return new Response(toCsv(story.data.chart_data as Row[]), {
    headers: { 'Content-Type': 'text/csv; charset=utf-8' },
  });
};
