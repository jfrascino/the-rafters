// Storrs Lore service worker: installable app + offline reading, without ever serving stale pages or data online.
//   pages and data (index.html, data/*.json): network first, cache as the offline fallback
//   versioned code (js/css with ?v=hash): cache first (a new deploy changes the URL)
//   images on this site: stale-while-revalidate
// Other sites (ESPN, YouTube, fonts) are left to the browser.
const CACHE = 'storrs-lore-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
  await self.clients.claim();
})()));

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  const path = url.pathname;
  if (req.mode === 'navigate' || path.endsWith('.json') || path.endsWith('/')) e.respondWith(networkFirst(req));
  else if (/\.(js|css)$/.test(path) && url.searchParams.has('v')) e.respondWith(cacheFirst(req));
  else if (/\.(png|jpe?g|webp|svg|gif)$/.test(path)) e.respondWith(staleWhileRevalidate(req, e));
});

async function networkFirst(req) {
  const c = await caches.open(CACHE);
  try {
    const res = await fetch(req);
    if (res.ok) c.put(req, res.clone());
    return res;
  } catch (err) {
    return (await c.match(req, { ignoreSearch: req.mode === 'navigate' })) || (await c.match('./')) || Response.error();
  }
}
async function cacheFirst(req) {
  const c = await caches.open(CACHE);
  const hit = await c.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) c.put(req, res.clone());
  return res;
}
async function staleWhileRevalidate(req, e) {
  const c = await caches.open(CACHE);
  const hit = await c.match(req);
  const net = fetch(req).then((res) => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => hit);
  if (hit) { e.waitUntil(net); return hit; }
  return net;
}
