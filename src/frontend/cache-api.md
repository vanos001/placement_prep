# Cache API

The Cache API is a browser API for storing HTTP responses (Request/Response pairs) in a cache that survives page reloads. Originally designed for Service Workers (offline web apps), it can also be used by any web page for HTTP caching. This page covers the API, the storage model, the cache eviction, and the production patterns.

## The API

The Cache API stores Request/Response pairs:

```js
// Open a cache
const cache = await caches.open('my-cache-v1');

// Put a response in the cache
const request = new Request('https://api.example.com/data');
const response = await fetch(request);
await cache.put(request, response);

// Get a response from the cache
const cachedResponse = await cache.match(request);
if (cachedResponse) {
  const data = await cachedResponse.json();
}

// Delete a response
await cache.delete(request);

// List all keys
const keys = await cache.keys();
```

The Cache API is async (Promise-based), unlike localStorage's sync API.

## The Storage Model

```text
Browser Cache Storage (per-origin):
  Cache "my-cache-v1":
    Entry: Request "https://api.example.com/data" → Response
    Entry: Request "https://api.example.com/other" → Response
  Cache "my-cache-v2":
    ...
```

Each cache is a name → entries mapping. An entry is a Request/Response pair.

To list all caches:
```js
const names = await caches.keys();
// ['my-cache-v1', 'my-cache-v2', ...]
```

To delete a whole cache:
```js
await caches.delete('my-cache-v1');
```

## The Service Worker Pattern

The canonical use: a Service Worker caches assets for offline use:

```js
// service-worker.js
const CACHE_NAME = 'app-v1';
const ASSETS = [
  '/',
  '/index.html',
  '/styles.css',
  '/app.js',
  '/images/logo.png',
];

// Install: pre-cache assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(names.map((name) => name !== CACHE_NAME && caches.delete(name)))
    )
  );
});

// Fetch: cache-first, fallback to network
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;  // serve from cache
      return fetch(event.request);  // fallback to network
    })
  );
});
```

This is the standard "cache-first" pattern: serve cached responses; fall back to the network on cache miss.

## Cache Strategies

### Cache-First

```js
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  return fetch(request);
}
```

Best for: static assets (CSS, JS, images). Once cached, always served from cache.

### Network-First

```js
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    const cache = await caches.open('dynamic-v1');
    cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    if (cached) return cached;
    throw error;
  }
}
```

Best for: dynamic content (API responses, fresh data). Network is tried first; cache is fallback.

### Stale-While-Revalidate

```js
async function staleWhileRevalidate(request) {
  const cache = await caches.open('dynamic-v1');
  const cached = await cache.match(request);
  
  const fetchPromise = fetch(request).then((response) => {
    cache.put(request, response.clone());
    return response;
  });
  
  return cached || fetchPromise;  // return cached if available, else wait for fetch
}
```

Best for: content that can be slightly stale (e.g., images, fonts). Serves cached; refreshes in the background.

### Cache-Only

```js
async function cacheOnly(request) {
  return caches.match(request);
}
```

Best for: offline-only content (e.g., a static page that must work offline).

## Storage Limits and Eviction

Browsers limit Cache API storage:
- Chrome: ~60% of free disk space, with best-effort eviction.
- Firefox: 2 GB per origin (default).
- Safari: 1 GB per origin.

When the browser is low on disk, it evicts cache entries. To prevent eviction, request persistent storage:

```js
if (await navigator.storage.persist()) {
  // Storage won't be evicted (except under extreme pressure)
}
```

## Production Use Cases

### PWA (Progressive Web App)

The standard pattern: cache the app shell (HTML, CSS, JS) for offline use, and use the network for dynamic content.

```js
// Cache app shell
const SHELL_CACHE = 'shell-v1';
const ASSETS = ['/', '/index.html', '/app.js', '/styles.css'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      caches.match('/index.html').then((cached) => cached || fetch(event.request))
    );
  } else {
    event.respondWith(
      caches.match(event.request).then((cached) => cached || fetch(event.request))
    );
  }
});
```

### Image Caching

For images that don't change often:

```js
// On page load, cache all images
document.querySelectorAll('img').forEach(async (img) => {
  const request = new Request(img.src);
  const cache = await caches.open('images-v1');
  const response = await fetch(request);
  await cache.put(request, response);
});
```

### API Response Caching

For APIs that are expensive to compute:

```js
// In a Service Worker
self.addEventListener('fetch', (event) => {
  if (event.request.url.startsWith('https://api.example.com/expensive')) {
    event.respondWith(staleWhileRevalidate(event.request));
  }
});
```

## Production Performance

Cache API performance:
- Cache hit latency: ~1-5 ms (in-memory cache).
- Cache size: limited by browser (typically 50+ MB per origin).
- Response time: matches HTTP cache; faster than re-fetching from network.

For most web apps, the Cache API + Service Worker pattern is the standard for offline support.

## Comparison to Other Caches

| Aspect | Cache API | HTTP Cache | localStorage | IndexedDB |
|--------|-----------|-----------|--------------|-----------|
| Layer | Application-controlled | Browser-controlled | App-controlled | App-controlled |
| Cache control | Programmatic | HTTP headers (Cache-Control, etc.) | Programmatic | Programmatic |
| Capacity | 50+ MB | Disk size | 5-10 MB | 50+ MB |
| Data type | HTTP responses | HTTP responses | Strings | Objects |
| Best for | Service Workers, offline | Standard HTTP caching | Small key-value | Large structured data |

Cache API complements (not replaces) the HTTP cache. The HTTP cache is browser-controlled; Cache API is app-controlled (more flexible).

## Common Pitfalls

1. **Forgetting that cache.put consumes the response.** A Response can only be read once; you must clone it (`response.clone()`) before consuming.

2. **Forgetting that responses with Vary headers may cache incorrectly.** A response with `Vary: Accept-Encoding` should match the request's Accept-Encoding; the Cache API handles this, but inspect the cache.

3. **Forgetting that the Cache API is per-origin.** You can't cache cross-origin responses (except for opaque responses from CORS-enabled requests).

4. **Forgetting that cache keys are Requests, not strings.** Two Requests with the same URL but different headers are different keys.

5. **Forgetting that cache eviction is not deterministic.** The browser may evict entries at any time. Don't rely on the cache for critical data.

6. **Forgetting that service worker updates may invalidate caches.** When the Service Worker file changes, the new worker activates; the old caches may need to be deleted in the `activate` event.

## References

- [MDN: Cache API](https://developer.mozilla.org/en-US/docs/Web/API/Cache)
- [Service Workers: An Introduction (web.dev)](https://web.dev/articles/service-workers-cache-storage)
- [Workbox: Google's Service Worker library](https://developer.chrome.com/docs/workbox/)
- [Cache API cookbook (web.dev)](https://web.dev/articles/cache-api-quick-guide)
- [PWA: Build a Service Worker](https://web.dev/articles/service-workers-cache-storage)
- [Cache Storage Limits and Eviction](https://developer.chrome.com/blog/eviction-policy/)
- [LWN: Cache API overview (2020)](https://lwn.net/Articles/815575/)
