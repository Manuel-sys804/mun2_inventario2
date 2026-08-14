// Service worker mínimo: solo habilita que el navegador ofrezca
// "Instalar app" / "Agregar a pantalla de inicio". No guarda en
// caché las páginas de inventario/ventas a propósito, para que
// SIEMPRE se vean los datos más recientes del servidor local.

const CACHE_NAME = "mun2-shell-v1";
const SHELL_ASSETS = [
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// Estrategia: siempre ir a la red primero (datos frescos del
// servidor local). Solo si la red falla, intenta caché (para que
// al menos el ícono/manifest no rompan la app).
self.addEventListener("fetch", (event) => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
