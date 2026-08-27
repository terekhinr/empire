const CACHE = "empire-tasks-v26";
const API_CACHE_PATHS = [
  "/tasks/api/planning/tasks",
  "/tasks/api/planning/summary",
  "/tasks/api/planning/projects",
  "/tasks/api/planning/checklists",
  "/tasks/api/planning/measurements",
  "/tasks/api/planning/workouts",
  "/tasks/api/planning/body/summary",
];

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

function isApiCacheable(url) {
  if (url.search && url.search.length > 1) return false;
  return API_CACHE_PATHS.some((p) => url.pathname === p || url.pathname.startsWith(p + "?"));
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  const network = fetch(request)
    .then((res) => {
      if (res.ok) cache.put(request, res.clone());
      return res;
    })
    .catch(() => null);
  if (cached) {
    network.catch(() => {});
    return cached;
  }
  const res = await network;
  if (res) return res;
  return new Response(JSON.stringify({ offline: true, tasks: [] }), {
    status: 503,
    headers: { "Content-Type": "application/json" },
  });
}

function networkFirst(request) {
  return fetch(request)
    .then((res) => {
      if (res.ok && request.method === "GET") {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(request, copy));
      }
      return res;
    })
    .catch(() => caches.match(request));
}

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.pathname.startsWith("/tasks/api/planning/")) {
    if (isApiCacheable(url)) {
      e.respondWith(staleWhileRevalidate(e.request));
    }
    return;
  }
  if (!url.pathname.startsWith("/tasks/")) return;
  const isAppShell =
    url.pathname === "/tasks/" ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".html") ||
    url.pathname.endsWith(".json") ||
    url.pathname.endsWith(".png");
  if (isAppShell) {
    e.respondWith(networkFirst(e.request));
    return;
  }
  e.respondWith(caches.match(e.request).then((cached) => cached || fetch(e.request)));
});

self.addEventListener("push", (e) => {
  let data = {};
  try {
    data = e.data ? e.data.json() : {};
  } catch (_) {
    data = { body: e.data ? e.data.text() : "" };
  }
  const title = data.title || "Задачник";
  const options = {
    body: data.body || "",
    icon: "/tasks/assets/icon-192.png",
    badge: "/tasks/assets/icon-192.png",
    tag: data.tag || "empire-task",
    data: { url: data.url || "/tasks/", task_id: data.task_id || null },
    renotify: true,
  };
  if (data.image) options.image = data.image;
  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const raw = (e.notification.data && e.notification.data.url) || "/tasks/";
  const target = raw.startsWith("http") ? raw : `${self.location.origin}${raw}`;
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if (client.url.includes("/tasks/") && "focus" in client) {
          if ("navigate" in client) {
            return client.navigate(target).then(() => client.focus());
          }
          return client.focus();
        }
      }
      return clients.openWindow(target);
    })
  );
});
