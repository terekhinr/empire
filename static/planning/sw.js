/* Kill-switch SW v30: без fetch-перехвата.
   Старый SW с кэшем мог вечно держать нативный splash.
   Этот скрипт: чистит Cache Storage, claim, unregister — и всё. */
const KILL = "empire-tasks-kill-v30";

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    (async () => {
      try {
        const keys = await caches.keys();
        await Promise.all(keys.map((k) => caches.delete(k)));
      } catch (_) {}
      try {
        await self.clients.claim();
      } catch (_) {}
      try {
        await self.registration.unregister();
      } catch (_) {}
    })()
  );
});

// Намеренно НЕТ fetch listener — не перехватываем навигацию/ассеты.
