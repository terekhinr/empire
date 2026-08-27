const CACHE = "empire-heal-v3";
const ASSETS = ["./index.html", "./styles.css", "./app.js", "./manifest.json", "./icon-192.png", "./icon-512.png"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    (async () => {
      const c = await caches.open(CACHE);
      for (const a of ASSETS) {
        try {
          await c.add(a);
        } catch (_) {}
      }
      await self.skipWaiting();
    })()
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (
    url.pathname.includes("empire-api") ||
    url.pathname.includes("cgi-bin") ||
    url.pathname.includes("/home-ops/api") ||
    /\/api\/?$/.test(url.pathname) ||
    url.searchParams.has("action")
  ) {
    e.respondWith(fetch(e.request));
    return;
  }
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request).catch(() => caches.match("./index.html")))
  );
});
