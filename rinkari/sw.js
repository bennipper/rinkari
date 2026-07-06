/* Rinkari service worker — cache-first shell so the app installs and
   yesterday's visit still opens on a train with no signal. Puzzle data now
   comes from Sanity (cross-origin), which this worker never caches — every
   request to a different origin than this page falls straight through to
   the network, so the daily puzzle always reflects what's actually in the
   CMS rather than a stale cached copy. */
const CACHE = "rinkari-v7";
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
  const sameOrigin = e.request.url.startsWith(self.location.origin);
  e.respondWith(
    caches.match(e.request).then(hit => hit ||
      fetch(e.request).then(res => {
        if (res.ok && sameOrigin) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, copy));
        }
        return res;
      }).catch(() => {
        /* Only fall back to the cached shell for same-origin requests (e.g.
           opening the app itself while offline). A failed cross-origin call
           (the Sanity API) must propagate as a real error so the app's own
           error handling shows a proper message, instead of silently
           swapping in index.html for what was supposed to be a JSON
           response. */
        if (sameOrigin) return caches.match("./index.html");
        throw new Error("network request failed: " + e.request.url);
      })
    )
  );
});
