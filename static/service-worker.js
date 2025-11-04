// ✅ MoliApp Service Worker (v2) — Güncelleme bildirimi dahil
const CACHE_NAME = "moliapp-cache-v2";
const urlsToCache = [
  "/",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.json"
];

// 📦 Install
self.addEventListener("install", event => {
  console.log("[SW] Kuruluyor...");
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
  self.skipWaiting(); // anında aktifleşsin
});

// 🧹 Activate — eski cache’leri temizle
self.addEventListener("activate", event => {
  console.log("[SW] Aktif edildi");
  event.waitUntil(
    caches.keys().then(cacheNames =>
      Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME)
                  .map(name => caches.delete(name))
      )
    )
  );
  return self.clients.claim();
});

// 🌐 Fetch — önce cache, yoksa ağ
self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});

// 🔁 Güncelleme bildirimi
self.addEventListener("message", event => {
  if (event.data === "skipWaiting") {
    self.skipWaiting();
  }
});

self.addEventListener("statechange", event => {
  console.log("[SW] State değişti:", event.target.state);
});
