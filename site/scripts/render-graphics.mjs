// Render a story's graphics for review, with the same code the site build uses.
// Usage (from site/): node --experimental-strip-types scripts/render-graphics.mjs <story.json> <out-dir>
// story.json: {headline, chart_spec, chart_data, numbers} (a dashboard/worker story export).
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

import sharp from 'sharp';

import { chartAlt, coverAlt } from '../src/lib/graphics/alt.ts';
import { coverSvg } from '../src/lib/graphics/cover.ts';
import { parseFont } from '../src/lib/graphics/font.ts';
import { renderStaticChart } from '../src/lib/charts/static.ts';

const [file, outDir] = process.argv.slice(2);
const story = JSON.parse(readFileSync(file, 'utf8'));
mkdirSync(outDir, { recursive: true });

const fonts = {
  regular: parseFont(readFileSync('src/data/fonts/Inter-Regular.ttf')),
  bold: parseFont(readFileSync('src/data/fonts/Inter-Bold.ttf')),
};
const { more_charts: more = [], ...main } = story.chart_spec;
const specs = [main, ...more];
const numbers = story.numbers ?? {};
const input = {
  headline: story.headline,
  cover: numbers.cover ?? {},
  spec: specs[0],
  data: story.chart_data,
  source: numbers.source?.publisher,
  groupNoun: { country: 'UK nations', region: 'regions', local_authority: 'local authorities' }[
    numbers.geo_level
  ],
};
const alts = [`cover: ${coverAlt(story.headline, input.cover, input.spec, input.data)}`];
for (const format of ['landscape', 'portrait']) {
  const svg = coverSvg(input, fonts, format);
  writeFileSync(
    join(outDir, `cover-${format}.png`),
    await sharp(Buffer.from(svg)).png().toBuffer(),
  );
}
specs.forEach((spec, i) => {
  const title = spec.title ?? story.headline;
  alts.push(
    `chart ${i + 1} (${spec.type}): ${chartAlt(spec, story.chart_data, title, numbers.chart_facts)}`,
  );
  const svg = renderStaticChart(spec, story.chart_data, { standalone: true, title });
  if (svg) writeFileSync(join(outDir, `chart-${i + 1}-${spec.type}.svg`), svg);
});
writeFileSync(join(outDir, 'alt.txt'), alts.join('\n\n') + '\n');
console.log(alts.join('\n\n'));
