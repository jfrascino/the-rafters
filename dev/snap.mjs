// Headless Chrome screenshots over CDP (works while the app pane is hidden).
// node dev/snap.mjs <outdir> <route>[@WxH][:fullpage] ...   e.g.  node dev/snap.mjs /tmp/s "/" "/season/1999@390x844"
// Also prints console errors from each page.
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [outDir, ...routes] = process.argv.slice(2);
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9300 + Math.floor(Math.random() * 500);
const prof = mkdtempSync(join(tmpdir(), 'snap-'));
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${prof}`, '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--hide-scrollbars', '--window-size=1440,1000', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let ws, id = 0;
const pending = new Map(), listeners = [];
async function connect() {
  for (let i = 0; i < 60; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const page = list.find((t) => t.type === 'page');
      if (page) { ws = new WebSocket(page.webSocketDebuggerUrl); break; }
    } catch {}
    await sleep(250);
  }
  await new Promise((r) => ws.addEventListener('open', r));
  ws.addEventListener('message', (m) => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    else listeners.forEach((f) => f(d));
  });
}
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });

try {
  await connect();
  await send('Page.enable'); await send('Runtime.enable');
  // REDUCED=1 emulates prefers-reduced-motion, so scroll-in reveals are visible in full-page captures
  if (process.env.REDUCED) await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  const errors = [];
  listeners.push((d) => {
    if (d.method === 'Runtime.exceptionThrown') errors.push(d.params.exceptionDetails?.exception?.description || d.params.exceptionDetails?.text);
    if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errors.push(d.params.args.map((a) => a.value ?? a.description).join(' '));
  });
  for (const spec of routes) {
    const full = spec.endsWith(':full');
    const s = spec.replace(/:full$/, '');
    const [route, size = '1440x1000'] = s.split('@');
    const [w, h] = size.split('x').map(Number);
    errors.length = 0;
    await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: w < 600 });
    await send('Page.navigate', { url: `http://localhost:8786/?shot=1&b=${Date.now()}#${route}` });
    await sleep(Number(process.env.WAIT || 3500));
    if (process.env.PRE_JS) { await send("Runtime.evaluate", { expression: process.env.PRE_JS, awaitPromise: true }); await sleep(Number(process.env.PRE_WAIT || 1200)); }
    let clip;
    if (full) {
      const r = await send('Runtime.evaluate', { expression: 'document.documentElement.scrollHeight', returnByValue: true });
      clip = { x: 0, y: 0, width: w, height: Math.min(r.result.result.value, 12000), scale: 1 };
    }
    const shot = await send('Page.captureScreenshot', { format: 'png', ...(clip ? { clip, captureBeyondViewport: true } : {}) });
    const name = (route.replace(/[^\w]+/g, '_') || 'home') + `_${w}${full ? '_full' : ''}.png`;
    writeFileSync(join(outDir, name), Buffer.from(shot.result.data, 'base64'));
    console.log('ok', name, errors.length ? `ERRORS: ${errors.slice(0, 5).join(' | ')}` : '');
  }
} finally {
  chrome.kill('SIGKILL');
  try { rmSync(prof, { recursive: true, force: true }); } catch {}
  process.exit(0);
}
