/**
 * Build-time charts and boundaries. Run: npm test (node's test runner, no extra deps).
 */
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { dodge } from '../src/lib/chart.ts';
import { boundariesFor, renderStaticChart } from '../src/lib/charts/static.ts';
import lads from '../src/data/geo/local-authorities.json' with { type: 'json' };
import nations from '../src/data/geo/nations.json' with { type: 'json' };
import regions from '../src/data/geo/regions.json' with { type: 'json' };

test('boundary files: unique codes, expected coverage, OGL attribution', () => {
  for (const [file, n] of [
    [nations, 4],
    [regions, 12],
    [lads, 374],
  ] as const) {
    const codes = file.features.map((f) => f.code);
    assert.equal(new Set(codes).size, codes.length);
    assert.equal(codes.length, n);
    assert.match(file.attribution, /Open Government Licence/);
  }
  assert.ok(
    regions.features.some((f) => f.code === 'N92000002'),
    'regions map draws the whole UK',
  );
});

test('dodge keeps labels apart and inside the range', () => {
  const ys = dodge([100, 101, 102, 300], 15, 0, 310);
  const sorted = [...ys].sort((a, b) => a - b);
  for (let i = 1; i < sorted.length; i++) assert.ok(sorted[i] - sorted[i - 1] >= 15 - 1e-9);
  assert.ok(Math.max(...ys) <= 310 && Math.min(...ys) >= 0);
  assert.deepEqual(dodge([5], 15, 0, 10), [5]);
});

const spec = {
  type: 'map' as const,
  x: 'period',
  y: 'value',
  series: 'geography',
  highlight: 'Wales',
};

test('map: picks the smallest boundary set and draws every area', () => {
  const rows = nations.features.map((f, i) => ({
    period: '2022-23',
    geography: f.name,
    code: f.code,
    value: 30 + i,
  }));
  assert.equal(boundariesFor(rows.map((r) => r.code)), nations);
  const svg = renderStaticChart(spec, rows, { title: 'T' })!;
  assert.equal((svg.match(/<title>/g) ?? []).length, 4);
  assert.match(svg, /<title>Wales: 33<\/title>/);
  assert.match(svg, /Outlined: Wales\./);
  assert.match(svg, /Open Government Licence/);
});

test('map: all local authorities, compact output; unknown codes fail loudly', () => {
  const rows = lads.features.map((f, i) => ({
    period: '2022-23',
    geography: f.name,
    code: f.code,
    value: i % 10,
  }));
  const svg = renderStaticChart({ ...spec, highlight: rows[0].geography }, rows, { title: 'T' })!;
  assert.equal((svg.match(/<title>/g) ?? []).length, lads.features.length);
  assert.ok(svg.length < 400_000, `map is ${svg.length} bytes`);
  assert.throws(
    () =>
      renderStaticChart(
        spec,
        [...rows, { period: '2022-23', geography: 'X', code: 'E99999999', value: 1 }],
        { title: 'T' },
      ),
    /no boundary for E99999999/,
  );
});

test('regions map shows nations without data in grey', () => {
  const rows = regions.features
    .filter((f) => f.code.startsWith('E12'))
    .map((f, i) => ({ period: '2022-23', geography: f.name, code: f.code, value: i }));
  const svg = renderStaticChart({ ...spec, highlight: 'London' }, rows, { title: 'T' })!;
  assert.match(svg, /Scotland: no data/);
  assert.match(svg, /Grey: no data\./);
});

test('slope: every group labelled at both ends, highlighted drawn in colour', () => {
  const data = ['2011-12', '2022-23'].flatMap((period, i) =>
    ['A', 'B', 'C'].map((g, j) => ({
      period,
      geography: g,
      value: 10 + j + (g === 'A' ? i * 5 : -i),
    })),
  );
  const svg = renderStaticChart({ ...spec, type: 'slope', highlight: 'A', yLabel: '%' }, data, {
    title: 'T',
  })!;
  assert.match(svg, /15%  A/);
  assert.match(svg, />10%</);
  assert.match(svg, /var\(--series-1/);
  assert.equal((svg.match(/<title>/g) ?? []).length, 3);
  assert.equal(renderStaticChart({ ...spec, type: 'line' }, data, { title: 'T' }), null);
});
