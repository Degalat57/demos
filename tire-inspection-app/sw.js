/* Service worker: cache-first for same-origin GET, versioned cache. */
var CACHE_VERSION = 'dvi-demo-v1';
var APP_FILES = [
  './',
  './index.html',
  './config.js',
  './seed.js',
  './app.js',
  './styles.css',
  './manifest.webmanifest',
  './icon.svg',
  './icon-maskable.svg'
];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE_VERSION).then(function (cache) {
    return cache.addAll(APP_FILES);
  }).then(function () {
    return self.skipWaiting();
  }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) {
      return k !== CACHE_VERSION;
    }).map(function (k) { return caches.delete(k); }));
  }).then(function () {
    return self.clients.claim();
  }));
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  e.respondWith(caches.match(req).then(function (hit) {
    if (hit) return hit;
    return fetch(req).then(function (res) {
      var copy = res.clone();
      caches.open(CACHE_VERSION).then(function (cache) { cache.put(req, copy); });
      return res;
    }).catch(function () {
      return caches.match('./index.html');
    });
  }));
});
