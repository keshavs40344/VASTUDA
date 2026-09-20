const CACHE_NAME = "staunt-search-v1";
const ASSETS_TO_CACHE = [
  "/",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/icons/icon.svg",
  "/static/manifest.json"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE).catch(() => {});
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((k) => {
          if (k !== CACHE_NAME) return caches.delete(k);
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  // Only cache GET navigation / static assets, do not cache API calls
  if (e.request.url.includes("/api/")) {
    return;
  }

  e.respondWith(
    caches.match(e.request).then((cached) => {
      return (
        cached ||
        fetch(e.request).catch(() => {
          if (e.request.mode === "navigate") {
            return caches.match("/");
          }
        })
      );
    })
  );
});
