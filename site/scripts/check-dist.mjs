// Post-build checks for the production site in dist/. Exits 1 on any failure.
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const DIST = new URL('../dist/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const problems = [];
const must = (cond, msg) => cond || problems.push(msg);

// 1. Every migrated Hashnode URL must still exist (served without trailing slash).
const LEGACY = [
  'welcome-to-datatales-where-your-data-speaks',
  'are-petrol-cars-still-king-in-uk',
  'uk-laptop-imports-vs-exports',
  'wellbeing-in-the-uk',
];
for (const slug of LEGACY)
  must(existsSync(join(DIST, `${slug}.html`)), `missing legacy post /${slug}`);

// 2. Required site files.
for (const f of [
  'index.html',
  '404.html',
  'archive.html',
  'about.html',
  'contact.html',
  'rss.xml',
  'sitemap.xml',
  'robots.txt',
  '_redirects',
  '_headers',
  'favicon.svg',
]) {
  must(existsSync(join(DIST, f)), `missing ${f}`);
}

// 3. Walk every built file.
const files = [];
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else files.push(p);
  }
};
walk(DIST);

const SECRET_PATTERNS = [
  /sb_secret_[A-Za-z0-9_-]{10,}/,
  /SUPABASE_SERVICE_ROLE_KEY/,
  /service_role/,
  /eyJhbGciOi[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/, // JWT
  /\.supabase\.co/,
  /sk-ant-[A-Za-z0-9_-]{8,}/, // Anthropic API key
  /ANTHROPIC_API_KEY/,
];
for (const f of files.filter((p) => /\.(html|js|xml|txt|json|css)$/.test(p))) {
  const text = readFileSync(f, 'utf8');
  const rel = f.slice(DIST.length);
  // 4. Sample stories must never reach production.
  must(
    !/SAMPLE STORY|sample-fake-data-demo|"sample":\s*true/.test(text),
    `sample content found in ${rel}`,
  );
  for (const re of SECRET_PATTERNS)
    must(!re.test(text), `possible secret/Supabase reference (${re}) in ${rel}`);
}
must(
  !existsSync(join(DIST, 'stories', 'sample-fake-data-demo.html')),
  'sample story page was built',
);

// 5. Every story page ships its data download and its social card image.
const storyDir = join(DIST, 'stories');
for (const page of existsSync(storyDir)
  ? readdirSync(storyDir).filter((f) => f.endsWith('.html'))
  : []) {
  const slug = page.slice(0, -'.html'.length);
  const csv = join(storyDir, `${slug}.csv`);
  const png = join(storyDir, `${slug}.png`);
  must(existsSync(csv) && statSync(csv).size > 20, `story ${slug} has no CSV download`);
  must(
    existsSync(png) && readFileSync(png).subarray(1, 4).toString() === 'PNG',
    `story ${slug} has no OG image`,
  );
  const portrait = join(storyDir, `${slug}-portrait.png`);
  const thumb = join(storyDir, `${slug}-thumb.webp`);
  must(
    existsSync(portrait) && readFileSync(portrait).subarray(1, 4).toString() === 'PNG',
    `story ${slug} has no portrait image`,
  );
  must(
    existsSync(thumb) && readFileSync(thumb).subarray(8, 12).toString() === 'WEBP',
    `story ${slug} has no thumbnail`,
  );
  const html = readFileSync(join(storyDir, page), 'utf8');
  must(
    /<img[^>]+class="hero"[^>]+alt="[^"]{40,}"/.test(html),
    `story ${slug} hero image lacks alt text`,
  );
  must(!/<img(?![^>]*\salt=)[^>]*>/.test(html), `story ${slug} has an image without alt`);
  must(html.includes(`/stories/${slug}.png`), `story ${slug} does not use its OG image`);
  must(html.includes(`/stories/${slug}.csv`), `story ${slug} does not link its CSV`);
}

// 6. Pure static output: no Worker script or adapter artefacts.
for (const f of ['_worker.js', '_routes.json', 'server']) {
  must(!existsSync(join(DIST, f)), `unexpected server/adapter output: ${f}`);
}

if (problems.length) {
  console.error(`check-dist: ${problems.length} problem(s)\n - ` + problems.join('\n - '));
  process.exit(1);
}
console.log(`check-dist: OK (${files.length} files)`);
