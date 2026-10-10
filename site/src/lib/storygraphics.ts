import type { Story } from './content';
import { coverAlt, type Cover, type Row, type Spec } from './graphics/alt.ts';
import { coverSvg, type CoverFormat } from './graphics/cover.ts';
import { parseFont, type Font } from './graphics/font.ts';

import interBold from '../data/fonts/Inter-Bold.ttf?inline';
import interRegular from '../data/fonts/Inter-Regular.ttf?inline';

/** Build-time story graphics. Fonts come from the repo (src/data/fonts), never the system. */
const fromDataUrl = (url: string) =>
  Uint8Array.from(atob(url.slice(url.indexOf(',') + 1)), (c) => c.charCodeAt(0));

let fonts: { regular: Font; bold: Font } | null = null;
function loadFonts() {
  fonts ??= {
    regular: parseFont(fromDataUrl(interRegular)),
    bold: parseFont(fromDataUrl(interBold)),
  };
  return fonts;
}

const NOUNS: Record<string, string> = {
  country: 'UK nations',
  region: 'regions',
  local_authority: 'local authorities',
};

export function coverInput(story: Story) {
  const d = story.data;
  const numbers = d.numbers as {
    cover?: Cover;
    geo_level?: string;
    source?: { publisher?: string };
  };
  return {
    headline: d.title,
    cover: numbers.cover ?? {},
    spec: d.chart_spec as Spec,
    data: d.chart_data as Row[],
    source: d.source.publisher ?? numbers.source?.publisher,
    groupNoun: NOUNS[numbers.geo_level ?? ''],
  };
}

export function storyCoverSvg(story: Story, format: CoverFormat): string {
  return coverSvg(coverInput(story), loadFonts(), format);
}

export function storyCoverAlt(story: Story): string {
  const i = coverInput(story);
  return coverAlt(i.headline, i.cover, i.spec, i.data);
}

export const coverPaths = (slug: string) => ({
  landscape: `/stories/${slug}.png`,
  portrait: `/stories/${slug}-portrait.png`,
  thumb: `/stories/${slug}-thumb.webp`,
});
