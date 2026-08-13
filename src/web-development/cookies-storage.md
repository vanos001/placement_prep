# Cookies & Client-Side Storage

Modern web applications need to store data on the client. Browsers offer several storage mechanisms, each with different capacities, lifetimes, and use cases. Understanding when to use each is essential for building robust web applications.

## Cookies

Cookies are small pieces of data that the server sends to the browser, which the browser stores and includes in subsequent requests to the same server.

### How Cookies Work

1. Server sends a `Set-Cookie` header in the HTTP response
2. Browser stores the cookie
3. Browser includes the cookie in the `Cookie` header of subsequent requests to the same origin

```
# Server response
HTTP/1.1 200 OK
Set-Cookie: session_id=abc123; Path=/; HttpOnly; Secure; SameSite=Lax

# Subsequent request
GET /api/data HTTP/1.1
Cookie: session_id=abc123
```

### Cookie Attributes

#### Domain and Path

```
Set-Cookie: name=value; Domain=.example.com; Path=/
```

- **Domain** — determines which hosts can receive the cookie. If set to `.example.com`, the cookie is sent to both `example.com` and `sub.example.com`. If omitted, defaults to the exact host
- **Path** — the cookie is only sent to URLs that match this path prefix. `/` means all paths

#### Secure

```
Set-Cookie: name=value; Secure
```

The cookie is only sent over HTTPS connections. Never transmitted over unencrypted HTTP. This should be used for any cookie containing sensitive data.

#### HttpOnly

```
Set-Cookie: name=value; HttpOnly
```

The cookie is not accessible to JavaScript via `document.cookie`. This is a critical security measure against XSS (Cross-Site Scripting) attacks — even if an attacker can inject script, they can't steal HttpOnly cookies.

#### SameSite

Controls when cookies are sent in cross-site requests:

```
Set-Cookie: name=value; SameSite=Strict
Set-Cookie: name=value; SameSite=Lax
Set-Cookie: name=value; SameSite=None; Secure
```

- **Strict** — cookie is never sent in cross-site requests. Clicking a link from another site to your site won't include the cookie on the initial request. Maximum CSRF protection but can hurt UX (users appear logged out when arriving from external links)
- **Lax** — cookie is sent in top-level navigations (clicking a link) but not in cross-site subrequests (images, iframes, AJAX). Default in modern browsers. Good balance of security and usability
- **None** — cookie is sent in all contexts. **Requires `Secure` flag**. Use only when you need cross-site cookie access (e.g., third-party integrations)

#### Expires and Max-Age

```
Set-Cookie: name=value; Expires=Wed, 21 Oct 2025 07:28:00 GMT
Set-Cookie: name=value; Max-Age=3600
```

- **Expires** — absolute expiration date
- **Max-Age** — relative expiration in seconds from now
- If neither is set, the cookie is a **session cookie** — deleted when the browser is closed

#### __Host- and __Secure- Prefixes

```
Set-Cookie: __Host-session=abc; Secure; Path=/; SameSite=Strict
Set-Cookie: __Secure-token=xyz; Secure; SameSite=Lax
```

- **__Host-** — must have `Secure`, must not have `Domain`, must have `Path=/`
- **__Secure-** — must have `Secure`

These prefixes provide additional guarantees about cookie security.

### Cookie Limitations

- **Size** — approximately 4KB per cookie
- **Count** — browsers typically allow 50 cookies per domain, 300 total per browser
- **Sent with every request** — cookies increase request size, which matters for API calls
- **Not designed for large data** — use other storage mechanisms for significant amounts of data

### Accessing Cookies in JavaScript

```javascript
// Read all cookies (string)
console.log(document.cookie);
// "name1=value1; name2=value2"

// Set a cookie
document.cookie = "username=john; path=/; max-age=86400";

// Delete a cookie
document.cookie = "username=; path=/; max-age=0";
```

Note: `document.cookie` doesn't expose `HttpOnly` cookies.

### Common Cookie Patterns

```javascript
// Set a secure cookie (server-side)
res.cookie('session', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'lax',
  maxAge: 24 * 60 * 60 * 1000, // 24 hours
  path: '/'
});

// Read a specific cookie (client-side)
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}
```

## localStorage

`localStorage` is a key-value store that persists data with no expiration date. Data survives browser restarts.

### API

```javascript
// Store data
localStorage.setItem('theme', 'dark');
localStorage.setItem('user', JSON.stringify({ name: 'John', age: 30 }));

// Retrieve data
const theme = localStorage.getItem('theme'); // 'dark'
const user = JSON.parse(localStorage.getItem('user')); // { name: 'John', age: 30 }

// Remove data
localStorage.removeItem('theme');

// Clear all data for this origin
localStorage.clear();

// Get key by index
localStorage.key(0);

// Number of items
localStorage.length;
```

### Characteristics

- **Storage limit** — approximately 5-10MB per origin (varies by browser)
- **Persistence** — data persists until explicitly cleared
- **Synchronous API** — all operations are synchronous and block the main thread
- **String-only** — all values are stored as strings. Objects must be serialized with `JSON.stringify()`
- **Same-origin** — data is isolated per origin (protocol + host + port)

### When to Use localStorage

- User preferences (theme, language)
- Application state that should persist across sessions
- Cached data that doesn't need to be sent to the server
- Draft content (auto-saving form data)

### When NOT to Use localStorage

- Sensitive data (accessible to any JavaScript on the page — XSS vulnerable)
- Data that needs to be sent to the server (use cookies)
- Large binary data (use IndexedDB)
- Data that needs to be accessed from web workers (use IndexedDB)

### Storage Events

When `localStorage` is modified in one tab, other tabs on the same origin receive a `storage` event:

```javascript
window.addEventListener('storage', (event) => {
  console.log(event.key);       // key that changed
  console.log(event.oldValue);  // previous value
  console.log(event.newValue);  // new value
  console.log(event.url);       // URL of the page that made the change
});
```

This is useful for syncing state across tabs.

## sessionStorage

`sessionStorage` is identical to `localStorage` in API but differs in lifetime and scope.

### Key Differences from localStorage

- **Lifetime** — data is cleared when the **tab** (or window) is closed
- **Scope** — data is isolated to the specific tab. Even the same URL opened in two different tabs has separate `sessionStorage`
- **Not shared** — duplicating a tab copies the `sessionStorage` to the new tab

### API

```javascript
// Same API as localStorage
sessionStorage.setItem('step', '2');
sessionStorage.getItem('step'); // '2'
sessionStorage.removeItem('step');
sessionStorage.clear();
```

### When to Use sessionStorage

- Multi-step form wizard (tracking current step)
- Temporary state that shouldn't persist (e.g., search filters)
- Tab-specific data (different tabs can have different states)
- Security-sensitive temporary data (cleared when tab closes)

## IndexedDB

IndexedDB is a low-level API for storing large amounts of structured data, including files and blobs. It's a full transactional database built into the browser.

### Core Concepts

- **Database** — a collection of object stores, scoped to an origin
- **Object Store** — like a table in a relational database, stores key-value pairs
- **Index** — allows querying by properties other than the primary key
- **Transaction** — all reads and writes happen within transactions (atomic, consistent, isolated)

### Basic Usage

```javascript
// Open (or create) a database
const request = indexedDB.open('MyDatabase', 1);

// Handle version upgrade (create object stores and indexes)
request.onupgradeneeded = (event) => {
  const db = event.target.result;

  // Create an object store
  const store = db.createObjectStore('users', { keyPath: 'id', autoIncrement: true });

  // Create indexes
  store.createIndex('email', 'email', { unique: true });
  store.createIndex('name', 'name', { unique: false });
};

request.onsuccess = (event) => {
  const db = event.target.result;

  // Add data
  const tx = db.transaction('users', 'readwrite');
  const store = tx.objectStore('users');
  store.add({ name: 'John', email: 'john@example.com', age: 30 });
  store.add({ name: 'Jane', email: 'jane@example.com', age: 25 });

  tx.oncomplete = () => console.log('Transaction completed');
};

request.onerror = (event) => {
  console.error('Database error:', event.target.error);
};
```

### Reading Data

```javascript
const tx = db.transaction('users', 'readonly');
const store = tx.objectStore('users');

// Get by primary key
const getRequest = store.get(1);
getRequest.onsuccess = () => console.log(getRequest.result);

// Get all
const getAllRequest = store.getAll();
getAllRequest.onsuccess = () => console.log(getAllRequest.result);

// Query by index
const index = store.index('email');
const emailRequest = index.get('john@example.com');
emailRequest.onsuccess = () => console.log(emailRequest.result);

// Cursor iteration
const cursorRequest = store.openCursor();
cursorRequest.onsuccess = (event) => {
  const cursor = event.target.result;
  if (cursor) {
    console.log(cursor.key, cursor.value);
    cursor.continue();
  }
};
```

### Deleting Data

```javascript
const tx = db.transaction('users', 'readwrite');
const store = tx.objectStore('users');

store.delete(1); // delete by key

// Delete by index
const index = store.index('email');
const getRequest = index.getKey('john@example.com');
getRequest.onsuccess = () => {
  if (getRequest.result !== undefined) {
    store.delete(getRequest.result);
  }
};
```

### When to Use IndexedDB

- Large amounts of structured data (>5MB)
- Binary data (images, files, blobs)
- Complex queries (using indexes)
- Offline-first applications
- Progressive Web Apps (PWAs)
- Data that needs to be accessed from web workers

### Libraries That Simplify IndexedDB

IndexedDB's raw API is verbose and callback-heavy (though Promise wrappers exist). Popular libraries:

- **idb** — a tiny Promise wrapper by Jake Archibald
- **Dexie.js** — clean API with querying support
- **localForage** — localStorage-like API backed by IndexedDB

```javascript
// With idb library
import { openDB } from 'idb';

const db = await openDB('MyDatabase', 1, {
  upgrade(db) {
    db.createObjectStore('users', { keyPath: 'id', autoIncrement: true });
  }
});

await db.add('users', { name: 'John', email: 'john@example.com' });
const user = await db.get('users', 1);
const allUsers = await db.getAll('users');
```

## The Cache API

The Cache API is designed for caching HTTP responses, primarily used with Service Workers:

```javascript
// Open a cache
const cache = await caches.open('my-cache-v1');

// Store a response
await cache.put('/api/data', new Response(JSON.stringify({ items: [1, 2, 3] })));

// Retrieve
const response = await cache.match('/api/data');
const data = await response.json();
```

## Comparison Table

| Feature | Cookies | localStorage | sessionStorage | IndexedDB |
|---------|---------|-------------|----------------|-----------|
| Storage | ~4KB | 5-10MB | 5-10MB | Hundreds of MB+ |
| Sent to server | Yes (automatically) | No | No | No |
| API | String (document.cookie) | String key-value | String key-value | Structured (transactions) |
| Expiration | Configurable | Never | Tab close | Never (manual) |
| Accessible from | HTTP + JS (unless HttpOnly) | JS only | JS only | JS + Web Workers |
| Synchronous | Yes | Yes | Yes | Async (event-driven) |
| Cross-tab | Yes | Yes (same origin) | No | Yes (same origin) |

## Security Considerations

### XSS and Storage

- `localStorage` and `sessionStorage` are fully accessible to JavaScript — any XSS vulnerability means all stored data is compromised
- Never store auth tokens in `localStorage` — use HttpOnly, Secure cookies instead
- Always sanitize data before rendering

### CSRF and Cookies

- Cookies are automatically sent with requests, making them vulnerable to CSRF
- Use `SameSite=Lax` or `SameSite=Strict` to mitigate CSRF
- Combine with CSRF tokens for defense in depth

### Best Practices

- Use `HttpOnly` + `Secure` + `SameSite` for authentication cookies
- Store sensitive data in HttpOnly cookies, not localStorage
- Use IndexedDB for large or binary data
- Encrypt sensitive data before storing client-side (though keys must also be stored, which limits the security benefit)
- Clear storage when users log out

## Key Interview Points

- Cookies are sent with every HTTP request; localStorage and sessionStorage are not
- `HttpOnly` cookies can't be accessed by JavaScript (XSS protection)
- `SameSite` defaults to `Lax` in modern browsers
- `localStorage` persists across sessions; `sessionStorage` is per-tab and per-session
- IndexedDB is the only option for large amounts of structured data
- All client-side storage is same-origin isolated
- Never store sensitive data in `localStorage` (XSS vulnerable)
- IndexedDB is asynchronous; localStorage is synchronous (can block main thread)
