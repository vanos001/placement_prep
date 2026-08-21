# Progressive Web Apps (PWA)

## Table of Contents

- [What a PWA Actually Is](#what-a-pwa-actually-is)
- [The Web App Manifest](#the-web-app-manifest)
- [Service Workers](#service-workers)
- [Offline, Background Sync, and Push Notifications](#offline-background-sync-and-push-notifications)
- [The Install Prompt (beforeinstallprompt)](#the-install-prompt-beforeinstallprompt)
- [Web App Bundles and Bundled Exchanges](#web-app-bundles-and-bundled-exchanges)
- [App Store Distribution](#app-store-distribution)
- [PWA vs Native](#pwa-vs-native)
- [Limitations and Platform Reality](#limitations-and-platform-reality)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## What a PWA Actually Is

A **Progressive Web App** is not a single API — it's the marketing label for
the combination of three web platform features:

1. A **Web App Manifest** describing the app's name, icons, theme, display
   mode, and start URL.
2. A **Service Worker** — a JavaScript worker that the browser installs in
   the origin's scope and that sits between the page and the network, able to
   serve cached responses, handle push, and run sync work in the background.
3. **HTTPS** — required, because service workers can rewrite responses.

If a site meets all three, browsers offer the user an install prompt that
turns the page into a launchable app: an icon on the home screen / launcher,
an app-window experience (no browser chrome), and a launch that doesn't go
through the address bar.

The promise: write one web app, run it on every device, ship updates without
an app store review, and have it work offline. The catch: capabilities lag
native on iOS in particular, and the install funnel is weaker than app
stores.

## The Web App Manifest

The manifest is a JSON file linked from the page:

```html
<link rel="manifest" href="/manifest.webmanifest">
```

A realistic example:

```json
{
  "name": "Recipe Book",
  "short_name": "Recipes",
  "description": "Plan your week's meals and shopping list.",
  "start_url": "/?source=pwa",
  "scope": "/",
  "display": "standalone",
  "display_override": ["window-controls-overlay", "standalone", "minimal-ui"],
  "orientation": "any",
  "background_color": "#ffffff",
  "theme_color": "#ff7043",
  "lang": "en",
  "dir": "ltr",
  "categories": ["food", "lifestyle", "productivity"],
  "icons": [
    { "src": "/icons/192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/maskable.png", "sizes": "512x512", "type": "image/png",
      "purpose": "maskable" }
  ],
  "shortcuts": [
    { "name": "Add recipe", "url": "/recipes/new",
      "icons": [{ "src": "/icons/add-96.png", "sizes": "96x96" }] }
  ],
  "screenshots": [
    { "src": "/shots/home-wide.png", "sizes": "1280x720",
      "type": "image/png", "form_factor": "wide" },
    { "src": "/shots/home-narrow.png", "sizes": "720x1280",
      "type": "image/png", "form_factor": "narrow" }
  ],
  "share_target": {
    "action": "/share",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "text": "text",
      "url": "url",
      "files": [
        { "name": "image", "accept": ["image/png", "image/jpeg"] }
      ]
    }
  }
}
```

Key fields:

- **`display`**: `fullscreen`, `standalone` (no browser UI), `minimal-ui`,
  `browser`. `standalone` is what most PWAs want.
- **`display_override`**: lets you list preferred display modes; the browser
  picks the first one it supports. `window-controls-overlay` (desktop) lets
  your app draw into the title bar.
- **`scope`**: which URLs the PWA can navigate to without falling out of app
  context. Cross-origin navigations break out of the PWA window.
- **`icons`** with `purpose: "maskable"`: Android adaptive icon support —
  the OS can mask the icon into a circle, squircle, etc. Without a maskable
  icon your installed PWA on Android gets a white-bordered icon.
- **`shortcuts`**: appear in the OS launcher's long-press menu.
- **`screenshots`**: shown in the install prompt on Chrome / Edge.
- **`share_target`**: lets the PWA receive content from native share sheets
  ("share to…").

Manifest spec: W3C — see [Web Application Manifest](https://www.w3.org/TR/appmanifest/).

## Service Workers

A service worker is a special JavaScript worker. Unlike a normal worker, it
is:

- **Registered against an origin + scope**: `navigator.serviceWorker.register('/sw.js', { scope: '/app/' })`.
- **Event-driven**: the browser wakes it up to deliver events; the SW exits
  between events when idle.
- **Network-intercepting**: every `fetch` from a controlled page passes
  through `self.addEventListener('fetch', ...)` if installed.
- **No DOM access**: it runs in its own global scope (`ServiceWorkerGlobalScope`),
  cannot touch `window` or `document`.
- **API surface**: `install`, `activate`, `fetch`, `push`, `sync`,
  `periodicsync`, `notificationclick`, `message`.

A minimal "cache-first" service worker:

```js
// sw.js
const CACHE = 'recipe-cache-v1';
const ASSETS = ['/', '/index.html', '/app.js', '/styles.css',
                '/icons/192.png', '/offline.html'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(ASSETS))
  );
  self.skipWaiting(); // activate this SW on next navigation immediately
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim(); // take control of existing open tabs
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return; // don't cache writes
  event.respondWith(
    caches.match(request).then((cached) =>
      cached || fetch(request).then((res) => {
        // optionally cache new GETs
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(request, copy));
        return res;
      }).catch(() => caches.match('/offline.html'))
    )
  );
});
```

The Cache API (`caches`) is a separate persistent store from HTTP cache. It
lives across browser restarts, is per-origin, and stores `Response`
objects. SWs combine it with the IndexedDB (`indexedDB`) for structured data
and the Storage API quota.

Lifecycle states:

```
  registering ──► installing ──► installed ──► activating ──► activated
                       │                                              │
                       │  (failure)                                  │
                       ▼                                              ▼
                    redundant                              waiting, then activated
                                                                 on next navigation
```

## Offline, Background Sync, and Push Notifications

**Offline** is the simplest use case — cache the app shell (`/`,
`/app.js`, `/styles.css`) and the most-recent data; serve from cache when
network fails. The "app shell" model: cache the static front-end on install,
runtime-cache dynamic data with a strategy (network-first, cache-first,
stale-while-revalidate).

```js
// Stale-while-revalidate for API responses
self.addEventListener('fetch', (e) => {
  if (e.request.url.includes('/api/recipes')) {
    e.respondWith(async () => {
      const cache = await caches.open('api-v1');
      const cached = await cache.match(e.request);
      const network = fetch(e.request).then((res) => {
        cache.put(e.request, res.clone());
        return res;
      });
      return cached || network;
    })();
  }
});
```

**Background Sync** lets you defer work until the device has connectivity.
The page calls `serviceWorkerRegistration.sync.register('sync-tag')`; when
the browser decides the device is online and the SW is allowed to run,
it fires a `sync` event in the SW.

```js
// page
const reg = await navigator.serviceWorker.ready;
await reg.sync.register('send-outbox');

// sw.js
self.addEventListener('sync', (event) => {
  if (event.tag === 'send-outbox') {
    event.waitUntil(flushOutbox()); // returns Promise; retry until fulfilled
  }
});

async function flushOutbox() {
  const outbox = await idbGetAll('outbox');
  for (const item of outbox) {
    const res = await fetch('/api/recipes', { method: 'POST',
      body: JSON.stringify(item) });
    if (res.ok) await idbDelete('outbox', item.id);
    else throw 'will retry on next sync';
  }
}
```

If `flushOutbox` rejects, the browser will retry later (with backoff).

**Periodic Background Sync** is a separate API that runs without user
interaction at intervals the browser deems appropriate (e.g. daily news
update). Requires permission and the site must be installed.

**Push notifications** use the Web Push API + VAPID keys. The page registers
a `PushSubscription` with a push service (e.g. Mozilla's autopush,
Firebase Cloud Messaging for Chrome). Your server sends a JWT-signed push
message to the subscription endpoint; the push service wakes the SW and
fires a `push` event:

```js
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  event.waitUntil(
    self.registration.showNotification(data.title || 'Update', {
      body: data.body, icon: '/icons/192.png',
      badge: '/icons/badge-72.png',
      tag: data.tag, // collapse same-tag notifications
      data: { url: data.url } // attach for click handler
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});
```

On Android (Chrome), Web Push uses FCM and feels exactly like native push.
On desktop Chrome/Edge/Firefox, it works similarly. On iOS Safari, Web
Push works only when the PWA is installed to the home screen, since iOS 16.4.

## The Install Prompt (beforeinstallprompt)

Browsers trigger an install prompt when the site meets the installability
criteria:

1. Served over HTTPS
2. Has a manifest with `name`/`short_name`, `start_url`, `display: standalone
   | fullscreen | minimal-ui`, `icons` including 192px + 512px PNG.
3. Has a registered service worker with a `fetch` handler (Chrome relaxed
   this requirement in 2024 for desktop, but historically required).
4. Has reasonable engagement (user spent 30+ seconds on the page, or
   interacted with it).

You cannot show the prompt at any time. Instead, capture the
`beforeinstallprompt` event, prevent it, store it, and trigger it on a
user gesture:

```js
let deferredPrompt = null;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();               // suppress the browser's own banner
  deferredPrompt = e;
  document.querySelector('#install-btn').hidden = false;
});

document.querySelector('#install-btn').addEventListener('click', async () => {
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  console.log('install outcome:', outcome); // "accepted" | "dismissed"
  deferredPrompt = null;
});

window.addEventListener('appinstalled', () => {
  console.log('PWA installed');
});
```

iOS Safari does *not* fire `beforeinstallprompt`. On iOS you must train
users to use the Share → "Add to Home Screen" menu item, since Apple does
not expose a programmatic install API for the web.

## Web App Bundles and Bundled Exchanges

**Web Bundles** (`application/webbundle`) are a serialization format for a
set of HTTP responses (and their request URLs) as a single file. They are
related to Web Packaging. A Web Bundle contains the HTML, JS, CSS, images
that make up a site, signed for content integrity, so it can be served from
anywhere (e.g. a USB stick, an alternate CDN) without losing the origin's
authority.

Use cases:

- Distribute a PWA through an app store as a single file instead of a zip.
- Pre-load a PWA on a kiosk device.
- Sign content with the origin's certificate (Bundled Exchanges — `BXSI`
  experimental) so it can be loaded from a third party with cryptographic
  proof of origin.

Web Bundles are specified in the W3C Web Packaging WG. Bubbles / Trusted
Web Activity on Android can install from a Web Bundle, though most
Play-Store-distributed PWAs still pull from the live origin.

```bash
# Build a Web Bundle from a directory of files
go install github.com/WICG/webpackage/go/webbundle/cmd/wb@latest
wb gen ./public -baseURL https://recipes.example/ \
       -output recipes.wbn \
       -manifestURL https://recipes.example/manifest.webmanifest
```

The browser can then load `recipes.wbn` as if its contents were being served
from `https://recipes.example/`.

## App Store Distribution

**Google Play** accepts PWAs through **Trusted Web Activity (TWA)**. A TWA is
essentially a Chrome Custom Tab running in full-screen with no URL bar; the
Android app declares a `provider` pointing at the origin and is digitally
linked to that origin via a `assetlinks.json` file with the app's signing
key fingerprint. The PWA behaves as a full-screen Chrome inside the APK.

Build with Bubblewrap (CLI generator):

```bash
npx @bubblewrap/cli init --manifest=https://recipes.example/manifest.webmanifest
npx @bubblewrap/cli build
npx @bubblewrap/cli deploy   # uploads to Play Console
```

Bubblewrap generates an Android Studio project with a TWA wrapper. You ship
the APK to Play, and updates to the PWA (HTML/JS) take effect instantly
without Play review — only changes to the TWA config need store review.

**Microsoft Store** accepts PWAs directly: Microsoft's Edge crawler detects
manifests on the web; you can also self-publish via Partner Center with a
URL. The PWA is wrapped in an Edge-based host and ships as a Store app.

**Apple App Store** does not directly accept PWAs. The only path is to
wrap the PWA in a WKWebView inside a native app — which Apple reviews for
"app-like" behavior and historically rejects apps that are "merely a
website repackaged". This is the strictest constraint in the PWA story.

## PWA vs Native

| Capability | PWA | Native (Android/iOS) |
|---|---|---|
| Install on home screen | Yes (Chrome/Edge on desktop+Android, Safari on iOS) | Yes |
| Run offline | Yes (Service Worker + Cache API) | Yes |
| Push notifications | Android yes (FCM); iOS yes only if installed to home (iOS 16.4+) | Yes (FCM / APNs) |
| Background sync | Yes (limited by browser policy) | Yes |
| Camera / microphone | getUserMedia; in-browser only | Yes, full |
| Bluetooth | Web Bluetooth (limited GATT) | Full |
| File system access | File System Access API (Chrome/Edge) | Full |
| Background location | No | Yes (with permission) |
| Contacts / Calendar | Limited; via web share / pickers | Full |
| Native UI components | None (you build with HTML/CSS) | Full |
| Performance | Browser overhead; 60 fps is achievable | Native |
| Distribution | Web (any URL), Play Store (TWA), MS Store | Store only |
| Updates | Instant (server-side) | Store review queue |
| Discovery | URL-shareable; can be indexed | Store search |

PWAs are best when: the app's purpose is light, content-centric, shareable
by URL, and the platform gap doesn't kill you (e.g. e-commerce, news,
event sites, dashboards). Native is best when: you need deep hardware
integration, complex background processing, native UI polish, or store
monetization (in-app purchases especially — web payment APIs exist but
gating is harder).

## Limitations and Platform Reality

### iOS limitations

Safari on iOS supports Web App Manifest and Add to Home Screen, but the
support is shallower than Chrome on Android:

- No `beforeinstallprompt` event — the install path is manual.
- Service workers exist since iOS 11.3 but were capped at 50 MB cache and
  had a 7-day eviction policy: if the user doesn't use the PWA within 14
  days, iOS purges the service worker, all caches, and IndexedDB.
- Web Push arrived in iOS 16.4 but only for installed PWAs — not Safari
  tabs. The notification UI is web-style (served by the OS), not as rich as
  APNs.
- No Background Sync, no Periodic Background Sync, no Web Bluetooth, no
  File System Access API, no Web NFC, no Web Serial.
- WebRTC works (camera/mic), but background audio playback and capture
  have restrictions.

These constraints are deliberate. Apple's positioning is that the web is a
sandbox and native should remain richer.

### Android limitations

Chrome on Android is far more capable, but still gated:

- Background work is throttled aggressively (Chrome's "intensive wake up"
  and "standby buckets"). Periodic sync runs at most every ~12 hours and
  only if the user has used the PWA recently.
- Storage quota is per-origin and can be evicted under pressure.
- The browser's network stack handles the fetch, so proxy / mTLS / custom
  DNS is limited.

### Desktop

On Windows, Edge installs PWAs with shortcuts in the Start menu and a
native-feeling window. On macOS, Chrome/Edge/Safari all support installable
PWAs in windows. PWAs on ChromeOS are first-class — ChromeOS installs them
like Android apps.

## Interview Questions

**Q: What three things make a site an installable PWA in Chrome?**
A: HTTPS, a Web App Manifest with the required fields (`name`/`short_name`,
`start_url`, `display`, 192+512 px icons), and a service worker with a
`fetch` handler (now optional on desktop but historically required). After
those, the browser fires `beforeinstallprompt`.

**Q: What is a service worker and how does it differ from a regular worker?**
A: A service worker is a JavaScript worker that the browser registers for an
origin + scope. It can intercept network requests, run push/sync handlers in
the background, and persist responses in the Cache API. Unlike a regular
Worker, it has no DOM access, lives between page and network, is event-
driven (the browser wakes it on demand), and persists across browser
restarts in a registry tied to the origin.

**Q: Why is HTTPS mandatory for service workers?**
A: Because the service worker sits between the page and the network and can
rewrite any response. Over HTTP, a man-in-the-middle could inject a
malicious SW into a victim's browser and serve hostile content with the
origin's authority. HTTPS guarantees integrity of the SW script and the
pages it controls.

**Q: How does Web Push work?**
A: The page requests `Notification` permission, then calls
`serviceWorkerRegistration.pushManager.subscribe({userVisibleOnly: true,
applicationServerKey: VAPID_PUBLIC_KEY})`. The browser returns a
`PushSubscription` containing an endpoint URL + keys. Your server signs a
JWT with the VAPID private key and POSTs the payload to the push service;
the service routes it to the device. The browser wakes the SW and fires a
`push` event. The SW must call `showNotification` (because
`userVisibleOnly: true`), otherwise it gets a silent push rejection on most
platforms.

**Q: What is the difference between Trusted Web Activity (TWA) and a WebView
wrapper?**
A: A TWA uses Chrome (the system Chrome on Android) to render the PWA in a
full-screen activity with no URL bar, sharing cookies, storage, and
service workers with the user's browser. A WebView wrapper uses the
in-app WebView, which has its own cookie jar, no shared service workers,
and requires you to handle `WebView.setWebViewClient`/`WebViewClient` and
back button yourself. TWAs also get Digital Asset Links verification so
they can claim the origin's authority (no URL bar even).

**Q: Why don't iOS PWAs feel as smooth as Android PWAs?**
A: Apple's WebKit support for service workers is shallower: 7-day eviction,
50 MB cache caps, no Background Sync, no Periodic Sync, no `beforeinstallprompt`.
Push only works when the PWA is installed to home screen. The result is a
PWA experience that works "the moment you use it" but degrades fast — and
Apple's intention has been to keep the web sandboxed below native.

## References

- [PWA — web.dev/learn/pwa](https://web.dev/learn/pwa)
- [Web App Manifest — MDN](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [W3C Web Application Manifest specification](https://www.w3.org/TR/appmanifest/)
- [Service Worker API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Service Worker overview — web.dev](https://web.dev/articles/service-workers-cache-storage)
- [Web Push API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)
- [Background Sync API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Background_Synchronization_API)
- [Periodic Background Sync — Chrome developers](https://developer.chrome.com/blog/periodic-background-sync/)
- [beforeinstallprompt event — MDN](https://developer.mozilla.org/en-US/docs/Web/API/BeforeInstallPromptEvent)
- [Web Bundles / Web Packaging — WICG](https://github.com/WICG/webpackage)
- [Trusted Web Activity — Android developers](https://developer.android.com/training/app-links/verify-site-associations)
- [Bubblewrap CLI — github.com/GoogleChromeLabs/bubblewrap](https://github.com/GoogleChromeLabs/bubblewrap)
- [Apple PWA / Add to Home Screen docs — developer.apple.com](https://developer.apple.com/documentation/webkitjs/add_to_home_screen)
- [iOS Web Push support — webkit.org blog](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/)
- [PWA on Microsoft Store — Microsoft docs](https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps-chromium/microsoft-store)
