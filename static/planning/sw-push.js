/* Push-only SW: не трогает fetch/навигацию. Регистрируется только из настроек. */
self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (_) {
    try {
      data = { body: event.data ? event.data.text() : "" };
    } catch (_) {}
  }
  const title = data.title || "Задачник";
  const opts = {
    body: data.body || "",
    icon: "/tasks/assets/icon-192.png",
    badge: "/tasks/assets/icon-192.png",
    data: data.data || {},
    tag: data.tag || "empire-planning",
  };
  event.waitUntil(self.registration.showNotification(title, opts));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/tasks/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        if ("focus" in c) return c.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
