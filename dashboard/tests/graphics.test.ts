/**
 * Story graphics: the dashboard's copies must match the site's (canonical) modules, and a
 * cover must render with every piece of text outlined (no <text>, so no font dependency).
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { chartAlt, coverAlt } from "../lib/graphics/alt.ts";
import { coverSvg } from "../lib/graphics/cover.ts";
import { measure, parseFont, wrap } from "../lib/graphics/font.ts";

const read = (rel: string) => readFileSync(new URL(rel, import.meta.url));

test("graphics modules and fonts are in sync with the site (run scripts/sync-graphics.mjs)", () => {
  for (const f of ["font.ts", "alt.ts", "cover.ts"]) {
    assert.ok(read(`../lib/graphics/${f}`).equals(read(`../../site/src/lib/graphics/${f}`)), f);
  }
  for (const f of ["Inter-Regular.ttf", "Inter-Bold.ttf"]) {
    assert.ok(read(`../public/fonts/${f}`).equals(read(`../../site/src/data/fonts/${f}`)), f);
  }
});

const fonts = {
  regular: parseFont(read("../public/fonts/Inter-Regular.ttf")),
  bold: parseFont(read("../public/fonts/Inter-Bold.ttf")),
};

test("font: kerning, wrapping and missing glyphs", () => {
  const plain = measure(fonts.bold, "A", 100) + measure(fonts.bold, "V", 100);
  assert.ok(measure(fonts.bold, "AV", 100) < plain, "AV is kerned");
  const lines = wrap(fonts.bold, "one two three four five six seven eight nine ten", 40, 200, 2);
  assert.equal(lines.length, 2);
  assert.ok(lines[1].endsWith("…"));
  for (const l of lines) assert.ok(measure(fonts.bold, l, 40) <= 200 + 1, l);
  assert.ok(measure(fonts.regular, "\u{1F600}", 20) > 0, "unknown characters fall back to ?");
});

const data = ["2011-12", "2012-13", "2013-14"].flatMap((period, i) => [
  { period, geography: "North", value: 30 + i * 4 },
  { period, geography: "South", value: 35 - i },
]);
const spec = { type: "line" as const, x: "period", y: "value", series: "geography", highlight: "North", yLabel: "%" };
const cover = { value: "38%", label: "Share, 2013-14", change: "Up from 30% in 2011-12", badge: "2nd → 1st of 2 regions" };

test("cover renders in both formats with outlined text", () => {
  for (const format of ["landscape", "portrait"] as const) {
    const svg = coverSvg({ headline: "North overtakes South on a fake measure", cover, spec, data, source: "Fake" }, fonts, format);
    assert.match(svg, format === "landscape" ? /width="1200" height="630"/ : /width="1080" height="1350"/);
    assert.ok(!svg.includes("<text"), "no live text");
    assert.ok((svg.match(/<path /g) ?? []).length > 10);
  }
});

test("alt text is built from the data", () => {
  const alt = chartAlt(spec, data, "Share by region", {
    groups_compared: 2,
    supported_checks: [{ kind: "only_rise", group: "North", start: "2011-12", end: "2013-14" }],
  });
  assert.match(alt, /North, highlighted, rose from 30% in 2011–12 to 38% in 2013–14/);
  assert.match(alt, /only one of the 2 to rise/);
  assert.match(alt, /Shown in grey: South fell from 35% in 2011–12 to 33% in 2013–14/);
  assert.match(coverAlt("Headline", cover, spec, data), /^Headline\. 38%: Share, 2013–14\./);
  const map = chartAlt({ ...spec, type: "map" }, data, "Map title");
  assert.match(map, /Values range from 33% in South to 38% in North/);
});

test("cover text always fits its column, however long the headline", async () => {
  const { CHART_X, fitText } = await import("../lib/graphics/cover.ts");
  const long = "Northern Ireland’s extraordinarily disproportionate anxiety improvements outpaced every comparable nation across the entire decade-long measurement period";
  for (const [max, min, width, lines] of [[52, 36, 600, 4], [68, 48, 936, 5], [22, 13, 300, 1]] as const) {
    const f = fitText(fonts.bold, long, max, min, width, lines);
    assert.ok(f.lines.length <= lines);
    for (const l of f.lines) assert.ok(measure(fonts.bold, l, f.size) <= width + 0.5, `${l} @ ${f.size}`);
  }
  const short = fitText(fonts.bold, "Short headline", 52, 36, 600, 4);
  assert.deepEqual(short, { size: 52, lines: ["Short headline"] });
  const word = fitText(fonts.bold, "Supercalifragilisticexpialidocious".repeat(3), 52, 36, 300, 2);
  for (const l of word.lines) assert.ok(measure(fonts.bold, l, word.size) <= 300 + 0.5);
  assert.equal(CHART_X, 712);
});
