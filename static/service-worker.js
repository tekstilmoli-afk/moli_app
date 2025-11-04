// ✅ MoliApp Service Worker (v1)
// İnternet bağlantısı varsa online çalışır, bağlantı yoksa önbellekten yükler.

const CACHE_NAME = "moliapp-cache-v1";
const urlsToCache = [
  "/", // ana sayfa
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/manifest.json"
];

// 🔹 INSTALL — İlk yüklemede temel dosyaları önbelleğe al
self.addEventListener("install", event => {
  console.log("[Service Worker] Installing...");
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log("[Service Worker] Dosyalar önbelleğe alınıyor...");
        return cache.addAll(urlsToCache);
      })
      .catch(err => console.error("[Service Worker] Önbelleğe alma hatası:", err))
  );
  self.skipWaiting();
});

// 🔹 FETCH — Önce cache kontrol et, yoksa internetten getir
self.addEventListener("fetch", event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      // Cache'de varsa onu döndür, yoksa fetch et
      return response || fetch(event.request).catch(() => {
        // Eğer çevrimdışıysa ve isteğe karşılık yoksa basit bir fallback dönebiliriz
        return new Response("Offline mod: içerik yüklenemedi.", {
          headers: { "Content-Type": "text/plain; charset=utf-8" }
        });
      });
    })
  );
});

// 🔹 ACTIVATE — Eski cache'leri temizle
self.addEventListener("activate", event => {
  console.log("[Service Worker] Aktif edildi, eski cache'ler temizleniyor...");
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      );
    })
  );
  return self.clients.claim();
});
