/* NexusIQ Service Worker — Web Push bildirişləri.
   Sayt bağlı olsa belə bu skript arxa planda işləyir. */

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

/**
 * Bildiriş URL-ini SAYT DAXİLİ yola məhdudlaşdırır.
 *
 * Payload-a yalnız NexusIQ backend-i yaza bilər (Web Push mesajı abunənin
 * açarlarına şifrələnir və VAPID ilə imzalanır), ona görə bu bu gün hücumçuya
 * açıq deyil. Amma `client.navigate(url)` / `openWindow(url)` xam payload
 * dəyərini alırdı — yəni backend-də bir səhv (məs. gələcəkdə xəbər URL-inin
 * payload-a düşməsi) dərhal açıq-yönləndirməyə çevrilərdi. Müdafiə dərinliyi:
 * yalnız `/` ilə başlayan, `//` OLMAYAN nisbi yol qəbul edilir
 * (`//evil.com` protokol-nisbi mütləq URL-dir).
 */
function safePath(u) {
  if (typeof u !== "string" || !u.startsWith("/") || u.startsWith("//")) return "/";
  return u;
}

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
    data: { url: safePath(data.url) },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  // Köhnə (düzəlişdən əvvəl göstərilmiş) bildirişlər hələ də xam URL daşıya
  // bilər → oxuyanda da yoxla.
  const url = safePath(event.notification.data && event.notification.data.url);

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
