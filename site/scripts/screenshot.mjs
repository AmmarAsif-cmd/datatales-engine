// Exact-viewport screenshots (375px and 1280px, light and dark) via the Chrome DevTools Protocol.
// Headless Chrome otherwise enforces a 500px minimum window. No dependencies (Node 22 WebSocket).
// Usage (from site/, with a preview server running): node scripts/screenshot.mjs <url> <outPrefix> [widths=375,1280] [schemes=light,dark]
// Writes <outPrefix>-<width>-<scheme>.png (full page) and prints horizontal overflow per shot.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [url, prefix, widthsArg = '375,1280', schemesArg = 'light,dark'] = process.argv.slice(2);
const CHROME = process.env.CHROME ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const port = 9300 + Math.floor(Math.random() * 500);
const profile = mkdtempSync(join(tmpdir(), 'cdp-'));
const chrome = spawn(
  CHROME,
  [
    '--headless=new',
    '--disable-gpu',
    '--hide-scrollbars',
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    'about:blank',
  ],
  { stdio: 'ignore' },
);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    target = list.find((t) => t.type === 'page');
  } catch {
    await sleep(200);
  }
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let id = 0;
const pending = new Map();
ws.addEventListener('message', (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id && pending.has(msg.id)) {
    pending.get(msg.id)(msg);
    pending.delete(msg.id);
  }
});
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const n = ++id;
    pending.set(n, (m) => (m.error ? reject(new Error(m.error.message)) : resolve(m.result)));
    ws.send(JSON.stringify({ id: n, method, params }));
  });

await send('Page.enable');
for (const scheme of schemesArg.split(',')) {
  for (const width of widthsArg.split(',').map(Number)) {
    await send('Emulation.setDeviceMetricsOverride', {
      width,
      height: 900,
      deviceScaleFactor: 1,
      mobile: width < 600,
    });
    await send('Emulation.setEmulatedMedia', {
      features: [{ name: 'prefers-color-scheme', value: scheme }],
    });
    await send('Page.navigate', { url });
    await sleep(2500);
    // scroll through so client:visible islands hydrate, then back to top
    const { result: h } = await send('Runtime.evaluate', {
      expression: 'document.documentElement.scrollHeight',
      returnByValue: true,
    });
    for (let y = 0; y < h.value; y += 600) {
      await send('Runtime.evaluate', { expression: `scrollTo(0, ${y})` });
      await sleep(120);
    }
    await send('Runtime.evaluate', { expression: 'scrollTo(0, 0)' });
    await sleep(1200);
    const { result: o } = await send('Runtime.evaluate', {
      expression: `JSON.stringify({vw: innerWidth, sw: document.documentElement.scrollWidth,
        wide: [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1 && !e.closest('.table-scroll')).map(e => e.tagName + '.' + e.className).slice(0, 5)})`,
      returnByValue: true,
    });
    const { result: hh } = await send('Runtime.evaluate', {
      expression: 'document.documentElement.scrollHeight',
      returnByValue: true,
    });
    await send('Emulation.setDeviceMetricsOverride', {
      width,
      height: hh.value,
      deviceScaleFactor: 1,
      mobile: width < 600,
    });
    await sleep(800);
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    const file = `${prefix}-${width}-${scheme}.png`;
    writeFileSync(file, Buffer.from(shot.data, 'base64'));
    console.log(file, o.value);
  }
}
ws.close();
chrome.kill();
