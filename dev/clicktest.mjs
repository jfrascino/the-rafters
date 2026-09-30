// Real mouse clicks over CDP: flip the first card on #/players, then click its Career button; report where we end up.
import { spawn } from 'node:child_process';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9800 + Math.floor(Math.random() * 100);
const base = process.argv[2] || 'http://localhost:8786/';
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'ct-'))}`, '--window-size=1440,900', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws, id = 0; const pend = new Map();
for (let i = 0; i < 60 && !ws; i++) { try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const p = l.find((t) => t.type === 'page'); if (p) ws = new WebSocket(p.webSocketDebuggerUrl); } catch {} await sleep(250); }
await new Promise((r) => ws.addEventListener('open', r));
ws.addEventListener('message', (m) => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); } });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.result.value;
const click = async (x, y) => { for (const type of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 }); };
setTimeout(() => { console.log("TIMEOUT"); chrome.kill("SIGKILL"); process.exit(1); }, 45000);
try {
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: base + '#/players' }); await sleep(4000);
  const r1 = await ev(`(() => { const c = document.querySelector('.pcard'); const b = c.getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height * .35, c.querySelector('.pcard-back .go')?.textContent]; })()`);
  console.log('card center', r1);
  await click(r1[0], r1[1]); await sleep(900);
  const r2 = await ev(`(() => { const g = document.querySelector('.pcard.flip .go'); if (!g) return null; const b = g.getBoundingClientRect(); return [b.x + b.width / 2, b.y + b.height / 2, g.tagName, g.getAttribute('href'), document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2)?.outerHTML.slice(0, 120)]; })()`);
  console.log('flipped; career button', r2);
  if (r2) { await click(r2[0], r2[1]); await sleep(1500); }
  console.log('after click, hash =', await ev('location.hash'), '| flipped cards:', await ev(`document.querySelectorAll('.pcard.flip').length`));
} finally { chrome.kill('SIGKILL'); process.exit(0); }
