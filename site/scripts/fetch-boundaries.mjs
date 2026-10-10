// One-off: download ONS Open Geography boundaries (ultra generalised, BUC) and write compact
// JSON for the map charts to src/data/geo/. Run from site/: node scripts/fetch-boundaries.mjs
// Output is committed; the build never downloads anything.
//
// Coordinates are British National Grid (EPSG:27700) in units of 100 m, rings as flat
// [x0, y0, x1, y1, ...] arrays. Licence: Open Government Licence v3.0 (see README.md there).
import { mkdirSync, writeFileSync } from 'node:fs';

const BASE = 'https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services';
const LAYERS = {
  countries: 'Countries_December_2023_Boundaries_UK_BUC',
  regions: 'Regions_December_2023_Boundaries_EN_BUC',
  lads: 'Local_Authority_Districts_December_2022_UK_BUC_V2',
};
const UNIT = 100; // metres per stored unit

async function features(service) {
  const out = [];
  for (let offset = 0; ; offset += 1000) {
    const q = new URLSearchParams({
      where: '1=1',
      outFields: '*',
      outSR: '27700',
      returnGeometry: 'true',
      maxAllowableOffset: '150',
      resultOffset: String(offset),
      resultRecordCount: '1000',
      f: 'json',
    });
    const res = await fetch(`${BASE}/${service}/FeatureServer/0/query?${q}`);
    if (!res.ok) throw new Error(`${service}: HTTP ${res.status}`);
    const body = await res.json();
    if (!body.features) throw new Error(`${service}: ${JSON.stringify(body).slice(0, 200)}`);
    out.push(...body.features);
    if (!body.exceededTransferLimit) return out;
  }
}

function compact(feature) {
  const attrs = feature.attributes;
  const codeKey = Object.keys(attrs).find((k) => /^[A-Z]+\d{2}CD$/.test(k));
  const nameKey = Object.keys(attrs).find((k) => /^[A-Z]+\d{2}NM$/.test(k));
  const rings = [];
  for (const ring of feature.geometry.rings) {
    const flat = [];
    for (const [x, y] of ring) {
      const px = Math.round(x / UNIT);
      const py = Math.round(y / UNIT);
      if (flat.length && flat.at(-2) === px && flat.at(-1) === py) continue;
      flat.push(px, py);
    }
    if (flat.length >= 8) rings.push(flat); // 4+ points; drops slivers that round away
  }
  return { code: attrs[codeKey], name: attrs[nameKey], rings };
}

const meta = (layers) => ({
  source: 'Office for National Statistics, Open Geography Portal',
  layers: layers.map((l) => `${BASE}/${l}`),
  licence: 'Open Government Licence v3.0',
  attribution:
    'Source: Office for National Statistics licensed under the Open Government Licence v.3.0. ' +
    'Contains OS data © Crown copyright and database right 2024.',
  crs: 'EPSG:27700',
  unit: UNIT,
});

const countries = (await features(LAYERS.countries)).map(compact);
const regions = (await features(LAYERS.regions)).map(compact);
const lads = (await features(LAYERS.lads)).map(compact);
const sort = (list) => list.sort((a, b) => a.code.localeCompare(b.code));

const dir = new URL('../src/data/geo/', import.meta.url);
mkdirSync(dir, { recursive: true });
const files = {
  'nations.json': { ...meta([LAYERS.countries]), features: sort(countries) },
  // English regions plus Wales, Scotland and Northern Ireland, so the whole UK is drawn.
  'regions.json': {
    ...meta([LAYERS.regions, LAYERS.countries]),
    features: sort([...regions, ...countries.filter((c) => !c.code.startsWith('E'))]),
  },
  'local-authorities.json': { ...meta([LAYERS.lads]), features: sort(lads) },
};
for (const [name, data] of Object.entries(files)) {
  const text = JSON.stringify(data);
  writeFileSync(new URL(name, dir), text + '\n');
  console.log(`${name}: ${data.features.length} areas, ${(text.length / 1024).toFixed(0)} KB`);
}
