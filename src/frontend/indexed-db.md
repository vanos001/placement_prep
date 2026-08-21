# IndexedDB

IndexedDB is a browser-based NoSQL database, standardized by W3C in 2015 (modern API). It provides durable, structured storage for web applications, with support for transactions, indexes, and large data sets (multi-megabyte). This page covers the data model, the transaction semantics, the comparison to other browser storage, and the production patterns.

## The Data Model

IndexedDB stores data in "databases" → "object stores" → "objects":

```text
Database: my-app
  Object Store: users
    Records (objects):
      - { id: 1, name: 'Alice', email: 'alice@example.com' }
      - { id: 2, name: 'Bob', email: 'bob@example.com' }
    Indexes:
      - by_email: indexed by 'email' field (unique)
      - by_name: indexed by 'name' field (not unique)
  Object Store: orders
    ...
```

- A **database** is per-origin (one per website).
- An **object store** is a collection of records (like a table).
- A **record** is a JavaScript object with a key (auto or specified).
- An **index** is a sorted view by a specific field.

## Opening a Database

```js
// Open (or create) a database
const request = indexedDB.open('my-app', 1);

request.onupgradeneeded = (event) => {
  const db = event.target.result;
  
  // Create object stores (only available in upgrade events)
  if (!db.objectStoreNames.contains('users')) {
    const users = db.createObjectStore('users', { keyPath: 'id', autoIncrement: true });
    users.createIndex('by_email', 'email', { unique: true });
    users.createIndex('by_name', 'name', { unique: false });
  }
  
  if (!db.objectStoreNames.contains('orders')) {
    db.createObjectStore('orders', { keyPath: 'id' });
  }
};

request.onsuccess = (event) => {
  const db = event.target.result;
  // Use the database
};
```

The `onupgradeneeded` callback is called when the database version changes; this is the only place you can create/modify object stores and indexes.

## The Transaction Model

All operations happen in a transaction:

```js
const tx = db.transaction('users', 'readwrite');  // or 'readonly'
const store = tx.objectStore('users');

// Add a record
const addRequest = store.add({ name: 'Alice', email: 'alice@example.com' });
addRequest.onsuccess = () => console.log('Added:', addRequest.result);  // the auto ID

// Get a record by key
const getRequest = store.get(1);
getRequest.onsuccess = () => console.log('Got:', getRequest.result);

// Update a record
store.put({ id: 1, name: 'Alice Updated', email: 'alice@example.com' });

// Delete a record
store.delete(1);

tx.oncomplete = () => console.log('Transaction committed');
tx.onerror = () => console.log('Transaction failed:', tx.error);
```

Transaction rules:
- **Atomicity**: all operations in the transaction succeed or all fail.
- **Isolation**: transactions don't see uncommitted changes from other transactions.
- **Auto-commit**: when no requests are pending, the transaction auto-commits.

## Queries

### By Key

```js
const request = store.get(1);  // exact key
const range = IDBKeyRange.bound(10, 20);  // range
const range = IDBKeyRange.lowerBound(10);  // open range
const cursorRequest = store.openCursor(range);
```

### By Index

```js
const index = store.index('by_email');
const request = index.get('alice@example.com');  // find by email
```

### Cursors

For iterating over many records:

```js
const request = store.openCursor();
request.onsuccess = (event) => {
  const cursor = event.target.result;
  if (cursor) {
    console.log(cursor.key, cursor.value);
    cursor.continue();  // advance
  } else {
    console.log('Done');
  }
};
```

Cursors are the way to iterate; there's no "list all" convenience method.

## Production Patterns

### Promise-Based Wrapper

IndexedDB's API is callback-based; most production code wraps it in Promises:

```js
function idbGet(db, store, key) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(store, 'readonly');
    const request = tx.objectStore(store).get(key);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Usage
const user = await idbGet(db, 'users', 1);
```

Libraries like `idb` (Jake Archibald's npm package) provide a cleaner Promise-based API:

```js
import { openDB } from 'idb';

const db = await openDB('my-app', 1, {
  upgrade(db) {
    const users = db.createObjectStore('users', { keyPath: 'id', autoIncrement: true });
    users.createIndex('by_email', 'email', { unique: true });
  },
});

await db.add('users', { name: 'Alice', email: 'alice@example.com' });
const user = await db.get('users', 1);
await db.put('users', { id: 1, name: 'Alice U', email: 'alice@example.com' });
await db.delete('users', 1);
```

### Caching Offline Data

For PWAs (Progressive Web Apps), IndexedDB caches API responses for offline use:

```js
async function fetchWithCache(url) {
  // Try cache first
  const cached = await idbGet(db, 'api-cache', url);
  if (cached && Date.now() - cached.timestamp < 3600000) {
    return cached.data;
  }
  
  // Fetch and cache
  const response = await fetch(url);
  const data = await response.json();
  await idbPut(db, 'api-cache', { url, data, timestamp: Date.now() });
  return data;
}
```

### Large File Storage

For files (e.g., user uploads), IndexedDB can store Blobs directly:

```js
const blob = await fileInput.files[0].arrayBuffer();
await db.put('files', { id: 'my-file', blob });
```

Files up to ~50 MB are practical; larger files should use the File System Access API (where available).

## Storage Quotas

Browsers limit IndexedDB storage:
- Chrome: ~60% of free disk space, with a "best-effort" eviction policy.
- Firefox: 2 GB per origin by default; user can grant unlimited.
- Safari: 1 GB per origin; explicit user permission for more.

```js
// Check quota
const estimate = await navigator.storage.estimate();
console.log(`Used: ${estimate.usage} bytes; Quota: ${estimate.quota} bytes`);

// Request persistent storage (no eviction)
if (navigator.storage.persist) {
  const persisted = await navigator.storage.persist();
  console.log('Persistent:', persisted);
}
```

Persistent storage protects against eviction (when the browser is low on disk).

## Comparison to Other Browser Storage

| Aspect | IndexedDB | localStorage | sessionStorage | Cookies | Cache API |
|--------|-----------|---------------|-----------------|---------|-----------|
| Capacity | ~50+ MB | 5-10 MB | 5-10 MB | 4 KB | ~50+ MB |
| API | Async, transactional | Sync, simple | Sync, simple | Sync (with request) | Async, simple |
| Data type | Structured (objects) | Strings only | Strings only | Strings only | Response objects |
| Best for | App state, offline data | Small config | Session state | Auth tokens | HTTP responses |

localStorage is simpler but limited (5-10 MB, sync = blocks the main thread). IndexedDB is more powerful but more complex. Cache API is for HTTP responses (Service Worker use).

## Common Pitfalls

1. **Forgetting that object store creation requires version bump.** You can't add a store without incrementing the database version. Plan migrations carefully.

2. **Forgetting that transactions auto-commit when idle.** A long async operation between two IndexedDB calls may have already auto-committed the transaction.

3. **Forgetting that IndexedDB is async.** Each request's `onsuccess` runs in a separate task; chaining requires callbacks or Promises.

4. **Forgetting that Safari has quirks.** Safari's IndexedDB has had many bugs over the years (e.g., 1 GB hard limit, limited cursor support). Test on Safari specifically.

5. **Forgetting that IndexedDB stores structured objects, not arbitrary JS.** Objects with circular references, functions, or class instances don't serialize (only plain objects, arrays, Dates, Blobs, etc.).

6. **Forgetting that indexedDB's performance degrades with large indexes.** An index on a high-cardinality field (e.g., a unique ID per record) is expensive to maintain. Use indexes selectively.

## References

- [MDN: IndexedDB](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)
- [IndexedDB specification (W3C)](https://www.w3.org/TR/IndexedDB/)
- [idb: Jake Archibald's Promise-based wrapper](https://github.com/jakearchibald/idb)
- [Using IndexedDB (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Using_IndexedDB)
- [Storage quota and eviction policy](https://web.dev/articles/storage-for-the-web)
- [IndexedDB vs localStorage (web.dev)](https://web.dev/articles/indexeddb-best-practices)
- [LWN: IndexedDB overview (2020)](https://lwn.net/Articles/815575/)
