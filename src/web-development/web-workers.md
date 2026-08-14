# Web Workers

Web Workers enable running JavaScript in **background threads** separate from the main thread, preventing heavy computation from blocking the UI. This is essential for maintaining responsiveness in data-intensive web applications.

## How Workers Work

Workers run in an isolated global scope (`DedicatedWorkerGlobalScope` or `SharedWorkerGlobalScope`). They have no access to the DOM, `window`, or `document` — only a subset of Web APIs (fetch, IndexedDB, WebSocket, `importScripts`). Communication happens exclusively through **message passing**.

```javascript
// main.js — creating and communicating with a worker
const worker = new Worker('worker.js');

worker.postMessage({ type: 'compute', data: largeArray });

worker.onmessage = (event) => {
  console.log('Result:', event.data);
};

worker.onerror = (error) => {
  console.error('Worker error:', error.message);
};

worker.terminate(); // clean up
```

```javascript
// worker.js
self.onmessage = (event) => {
  const { type, data } = event.data;
  if (type === 'compute') {
    const result = heavyComputation(data);
    self.postMessage({ type: 'result', value: result });
  }
};
```

## Dedicated vs Shared Workers

| Feature | Dedicated Worker | Shared Worker |
|---|---|---|
| Scope | One owner (tab/iframe) | Multiple owners share one instance |
| Communication | Direct `postMessage` | Via `port` object |
| Lifecycle | Ends when creator closes | Ends when last connection closes |
| Use case | Offloading single-tab work | Shared state across tabs |

```javascript
// Shared worker — accessed from multiple tabs
const shared = new SharedWorker('shared-worker.js');
shared.port.start();
shared.port.postMessage('hello from tab');
shared.port.onmessage = (e) => console.log(e.data);
```

## Transferable Objects

By default, `postMessage` uses the **structured clone algorithm** — data is copied, which is slow for large objects. **Transferable objects** (`ArrayBuffer`, `MessagePort`, `OffscreenCanvas`, `ImageBitmap`) are transferred by reference (zero-copy), making the sender's reference unusable.

```javascript
// Transfer an ArrayBuffer (zero-copy)
const buffer = new Float64Array(1_000_000).buffer;
worker.postMessage(buffer, [buffer]); // buffer is neutered after transfer
// buffer.byteLength === 0 here
```

| Method | Copy Time | Sender Retains Access |
|---|---|---|
| Structured Clone | O(n) — copies data | Yes |
| Transferable | O(1) — moves ownership | No |

## Use Cases

- **Image/video processing** — pixel manipulation, encoding, decoding
- **Complex calculations** — sorting large datasets, Monte Carlo simulations
- **Data parsing** — CSV/JSON processing of large files
- **Cryptography** — hashing, encryption of large payloads
- **Pre-fetching** — loading and caching data in the background

## Limitations

- No DOM access (cannot update UI directly — must postMessage back)
- No `window`, `document`, or `localStorage`
- Worker creation has overhead (~50-100ms) — don't spawn for trivial work
- Message passing serialization adds latency for non-transferable data
- Debugging is harder (separate DevTools context in most browsers)
- Same-origin restrictions apply to worker scripts

## Interview Questions

**Q1: What is the difference between a Web Worker and the main thread?**
A: The main thread runs the event loop, handles DOM, rendering, and user events. A Web Worker runs in a separate thread with its own event loop, no DOM access, and communicates via `postMessage`. This separation prevents CPU-heavy tasks from blocking UI responsiveness.

**Q2: When should you use a Web Worker vs a Service Worker?**
A: Web Workers handle CPU-intensive computation (data processing, image manipulation). Service Workers act as a network proxy — they intercept requests, manage caches, and enable offline support. See [Service Workers](service-workers.md) for details.

**Q3: What are transferable objects and why do they matter?**
A: Transferable objects (`ArrayBuffer`, `MessagePort`) are transferred (not copied) between threads via `postMessage`. This provides zero-copy performance for large data, but the sender loses access to the transferred object. Without transfer, the structured clone algorithm copies data, which is O(n) and slow for large buffers.

**Q4: Can a Web Worker import external scripts?**
A: Yes, using `importScripts('script1.js', 'script2.js')` in classic workers, or `import` statements in module workers (`new Worker('worker.js', { type: 'module' })`). Module workers support ES module imports natively.

## Cross-References

- [Browser Event Loop](browser-event-loop.md) — Worker threads have their own event loop
- [Browser Architecture](browser-architecture.md) — Process model and thread architecture
- [Service Workers](service-workers.md) — Network-layer worker for offline support
- [WebSockets](websockets.md) — Alternative for server communication from workers

## References

- [MDN — Web Workers API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API)
- [Transferable Objects — web.dev](https://web.dev/articles/web-worker-transferable-objects)
