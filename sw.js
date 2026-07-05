/* Rinkari service worker — cache-first shell so the app installs and
   yesterday's visit still opens on a train with no signal, but network-first
   for puzzle data so the daily puzzle actually changes daily instead of
   being served stale from cache. */
const CACHE = "rinkari-v4";
const SHELL = ["./index.html", "./manifest.webmanifest", "./rinkari_logo.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  const isPuzzleData = url.origin === self.location.origin && url.pathname.includes("/puzzles/");

  if (isPuzzleData) {
    /* Always try the network first so today's date is picked up as soon as
       it arrives; only fall back to whatever was last cached if offline. */
    e.respondWith(
      fetch(e.request).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
        return res;
      }).catch(() => caches.match(e.request))
    );
    return;
  }

  e.respondWith(
    caches.match(e.request).then(hit => hit ||
      fetch(e.request).then(res => {
        if (res.ok && e.request.url.startsWith(self.location.origin)) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => caches.match("./index.html"))
    )
  );
});
