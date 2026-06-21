/* NexusIQ Service Worker — Web Push bildirişləri.
   Sayt bağlı olsa belə bu skript arxa planda işləyir. */

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: "NexusIQ", body: event.data ? event.data.text() : "" };
  }

  const title = data.title || "NexusIQ";
  const options = {
    body: data.body || "Yeni xəbər var.",
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    tag: data.tag || "nexusiq",
    renotify: true,
    data: { url: data.url || "/" },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";

  event.waitUntil(
    self.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if ("focus" in client) {
            client.navigate(url);
            return client.focus();
          }
        }
        if (self.clients.openWindow) {
          return self.clients.openWindow(url);
        }
      })
  );
});
