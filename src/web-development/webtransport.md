# WebTransport

WebTransport is a modern web API that provides bidirectional, low-latency client-server communication built directly on top of HTTP/3 (which itself runs over QUIC). It exposes three concurrency primitives — sessions, datagrams, and unidirectional/bidirectional streams — and lets applications choose between reliable ordered delivery, unreliable out-of-order delivery, and arbitrary multiplexed streams. It shipped in Chrome 97 (Jan 2022) and Firefox 114 (June 2023); Safari support is still partial as of 2024.

## Why HTTP/3 Is the Substrate

WebSocket runs over a single TCP connection. TCP guarantees in-order delivery of every byte; if a single packet is lost, all subsequent data is held in the kernel receive buffer until the loss is recovered by retransmission. This is **head-of-line blocking (HOLB)** — one slow byte stalls every message behind it, including unrelated messages that have already arrived.

QUIC fixes this by running multiple independent streams over a single encrypted UDP socket. A lost packet on stream A does not block stream B. WebTransport is the browser-facing API that exposes this property to JavaScript. It also exposes QUIC's datagram primitive (RFC 9221) for unreliable sends — useful for game state and live video where a stale retransmit is worse than a dropped packet.

```
       Browser (JS)                    Server
+-----------------------+        +--------------------+
| new WebTransport(url) |  ----  | WebTransport over |
|   .createBidirectional| HTTP/3 |  HTTP/3 session   |
|   .createUnidirectional|  QUIC |   (listener)      |
|   .sendDatagram()     |        |                   |
+-----------------------+        +--------------------+
              |                            |
       +------+------+
       | QUIC streams (independent, no HOLB)
       | QUIC datagrams (unreliable)
       | 0-RTT resumption
       +-------------+
```

## The Three Primitives

A `WebTransport` instance is one **session** over a single HTTP/3 `CONNECT` request (extended CONNECT, RFC 9220). On top of that session, applications use:

| Primitive | Reliability | Ordering | Use case |
|-----------|-------------|----------|----------|
| **Datagrams** | Unreliable (best-effort) | Per-datagram atomic, no inter-message order | Game state snapshots, audio frames |
| **Unidirectional streams** | Reliable | Per-stream ordered | Server push, file uploads |
| **Bidirectional streams** | Reliable | Per-stream ordered | RPC, request/response |

Crucially, multiple streams are multiplexed over the same QUIC connection and a lost packet only stalls the stream whose data was in that packet — not the others.

## Browser API

### Opening a Session

```js
// The URL scheme must be https:// (or wss:// for the fallback).
// The server must present a certificate trusted by the browser.
const url = 'https://wt.example.com:443/echo';
const transport = new WebTransport(url);

// Wait for the session to be ready (HTTP/3 CONNECT succeeds).
await transport.ready;
console.log('Connected, quic transport:', transport);
```

Optional `WebTransportOptions` allow the application to declare its reliability needs up front, which the server can use to reject the connection:

```js
const transport = new WebTransport(url, {
  // Allow the server to send unreliable datagrams.
  allowPooling: false,
  // Require the server to support datagrams; reject otherwise.
  requireUnreliable: true,
  // Pass an opaque blob the server can read during the handshake.
  serverCertificateHashes: [
    { algorithm: 'sha-256', value: base64Decode('...') },
  ],
});
```

The `serverCertificateHashes` option enables **server verification by certificate hash** — useful when the server uses a self-signed cert (e.g., a WebTransport relay in a CDN edge). The browser pins the cert without needing a CA. This is what enables WebTransport to be used in environments where TLS chain trust is awkward.

### Sending and Receiving Datagrams

Datagrams are bounded, unreliable, unordered messages. The maximum size is negotiated during the handshake and exposed as `transport.maxDatagramSize` (commonly ~1024 bytes after QUIC framing overhead).

```js
// Encode a small binary payload.
const payload = new TextEncoder().encode(JSON.stringify({
  t: performance.now(),
  x: 12.5,
  y: -8.1,
}));
const writer = transport.datagrams.writable.getWriter();
await writer.write(payload);
writer.releaseLock();

// Receive datagrams on the readable side.
const reader = transport.datagrams.readable.getReader();
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  console.log('datagram', value.byteLength, 'bytes');
}
```

Datagrams that exceed the negotiated size are silently dropped on send. Datagrams that are lost in flight are not retransmitted — the reader just never sees them.

### Unidirectional Streams

A unidirectional stream is a reliable, ordered byte channel that flows one way. The sender writes; the receiver reads.

```js
// Client opens a unidirectional stream and writes to it.
const uni = transport.createUnidirectionalStream();
const writer = uni.getWriter();
await writer.write(new TextEncoder().encode('hello'));
await writer.close();

// Server can push its own unidirectional streams.
const reader = transport.incomingUnidirectionalStreams.getReader();
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  // `value` is a ReadableStream — read bytes from it.
  const bytes = await new Response(value).arrayBuffer();
  console.log('server pushed:', bytes.byteLength);
}
```

### Bidirectional Streams

A bidirectional stream has both a `readable` and `writable` side, each independently reliable and ordered. This is the closest analog to a WebSocket — but you can open thousands of them over one WebTransport session.

```js
const bidi = transport.createBidirectionalStream();

// Send a request.
const w = bidi.writable.getWriter();
await w.write(encodeRpcRequest({ method: 'getUser', id: 42 }));
await w.close();

// Read the response.
const r = bidi.readable.getReader();
const { value } = await r.read();
console.log('response:', new TextDecoder().decode(value));
```

Each `createBidirectionalStream()` allocates a new QUIC stream ID. The server side receives it through `transport.incomingBidirectionalStreams`, an async iterable of `WebTransportBidirectionalStream` objects.

### Teardown

```js
// Close cleanly with a reason.
await transport.close({ closeCode: 0, reason: 'shutdown' });

// Or watch for the server's close.
transport.closed.then((info) => {
  console.log('closed', info.closeCode, info.reason);
});
```

The `closeCode` is a 0–255 byte chosen by the application (QUIC application error codes); `reason` is a UTF-8 string up to 1024 bytes.

## Server API

### Node.js (using `@fails-components/webtransport')

There is no first-party Node.js API yet — Node has not exposed the `Http3Server` API as a stable module. The community-maintained `@fails-components/webtransport` package wraps the `quic` library and exposes a familiar WebSocket-like surface:

```js
import { WebTransportServer } from '@fails-components/webtransport';

const server = new WebTransportServer({
  port: 443,
  // PEM-encoded cert + key. WebTransport requires TLS 1.3.
  cert: fs.readFileSync('./cert.pem'),
  key: fs.readFileSync('./key.pem'),
});

server.on('session', (session) => {
  // Receive datagrams from the client.
  session.datagrams.on('data', (buf) => {
    console.log('datagram', buf.length, 'bytes from client');
  });

  // Accept incoming bidirectional streams.
  session.on('stream', (stream) => {
    stream.on('data', (data) => {
      // Echo back on the writable side.
      stream.write(upperCase(data));
    });
  });
});

await server.listen();
console.log('listening on :443');
```

### Python (using `aiohttp` + `aiortc')

For Python, the `aiohttp` project has been adding WebTransport support via `aiortc`/`aioquic`. The low-level surface is the `WebTransportServer` class, which surfaces sessions as async objects:

```python
import asyncio
from aiohttp import web
from aiohttp.web_protocol import WebTransportHandler

async def wt_handler(request: web.Request) -> WebTransportHandler:
    wt = await request.canonical_webtransport()
    async for stream in wt.accept_bidi_streams():
        async for chunk in stream:
            stream.write(chunk.upper())
    return wt

app = web.Application()
app.router.add_route('CONNECT', '/wt', wt_handler)
web.run_app(app, port=443, ssl_context=ssl_ctx)
```

The exact API is in flux across implementations; the W3C spec only standardizes the **browser** side. Server interfaces are an implementation detail — RFC 9220 defines the wire protocol, but each HTTP/3 server exposes it differently.

### Rust (using `wtransport` + `quinn`)

The `wtransport` crate wraps `quinn` (the most widely used Rust QUIC implementation) and exposes a futures-based API:

```rust
use wtransport::ServerConfig;
use wtransport::endpoint::EndpointServer;

#[tokio::main]
async fn main() {
    let config = ServerConfig::builder()
        .with_bind_default(443)
        .with_certificate(certs, key)
        .build();
    let server = EndpointServer::new(config).await.unwrap();
    while let Some(conn) = server.accept().await {
        tokio::spawn(async move {
            let session = conn.await.unwrap();
            for stream in session.accept_uni().await {
                // ... handle each stream
            }
        });
    }
}
```

## Comparison to WebSocket

| Aspect | WebSocket (RFC 6455) | WebTransport |
|--------|---------------------|--------------|
| Transport | TCP | QUIC (HTTP/3) |
| Multiplexing | Single stream | Many independent streams |
| HOLB | Yes — single loss stalls all messages | No — per-stream loss recovery |
| Unreliable mode | Not supported | Datagrams |
| Framing | Hand-rolled text/binary frames | Native byte streams |
| 0-RTT resumption | No | Yes (QUIC) |
| Server-side cert pinning | No | Yes (`serverCertificateHashes`) |
| Browser support | Universal | Chrome 97+, Firefox 114+ (behind flag) |

The biggest practical difference is the head-of-line blocking case. A WebSocket multiplexing a game's positional updates and chat messages over one TCP connection: a lost packet stalls chat behind the next 100 positional updates. WebTransport solves this by running each logical channel on its own QUIC stream.

Datagrams are the other differentiator. For state that's only useful for one frame (player position, video frame), a stale retransmit wastes bandwidth and increases latency. With WebSocket, you'd implement "drop stale" in application code; with WebTransport datagrams, the kernel/QUIC layer does it for you.

## Use Cases

### Game Networking

Real-time multiplayer games send positional updates 20–60 times per second. Each packet contains a snapshot; the only snapshot that matters is the latest. Datagrams fit naturally:

```js
const writer = transport.datagrams.writable.getWriter();
function tick() {
  const state = encodeGameState(getLocalPlayer());
  writer.write(state);  // fire and forget
}
setInterval(tick, 1000 / 30);  // 30 Hz
```

Reliable side-channels (chat, RPC for inventory) ride on bidirectional streams. A late positional datagram doesn't delay chat delivery.

### Live Streaming

Cloudflare Stream and YouTube Live have experimented with WebTransport to deliver media segments over unreliable channels. Each media chunk goes out as a datagram; the player drops chunks that don't arrive in time and asks for I-frames on a reliable stream when resync is needed.

The WebCodecs API pairs well here — decode individual H.264 chunks as they arrive, never buffering more than a couple of frames.

### Sub-second Pub/Sub

For chat/notifications, you'd use a bidirectional stream — same shape as WebSocket, lower latency thanks to QUIC 0-RTT session resumption.

## Pitfalls

1. **Datagram size limits.** Max ~1024 bytes after QUIC framing. Large messages must be split or sent on a stream.
2. **No Safari support yet.** Have a WebSocket fallback.
3. **HTTP/3 is required.** If your CDN doesn't terminate HTTP/3, WebTransport won't work.
4. **Backpressure.** `WritableStream.getWriter().write()` returns a promise — await it, or you'll queue unbounded data in memory.
5. **Stream leaks.** Always `close()` unidirectional streams; an abandoned stream lingers on the server.

## Interview Questions

**Q1: Why does WebTransport use QUIC instead of TCP like WebSocket?**
A: QUIC runs over UDP and multiplexes independent streams over one encrypted connection. A loss on stream A only blocks stream A — the others keep flowing. TCP gives you a single in-order byte stream, so any loss head-of-line-blocks everything behind it. For latency-sensitive traffic (game state, live video), this is a dealbreaker.

**Q2: When would you use a datagram vs a stream in WebTransport?**
A: Datagrams are unreliable and unordered — they're for state where stale data is useless (positional updates, video frame chunks). Streams are reliable and ordered — they're for RPC, file transfer, chat. If you need a retransmit, you want a stream; if you'd throw away a retransmitted packet anyway, you want a datagram.

**Q3: How does WebTransport handle the certificate chain?**
A: Standard TLS chain trust works (HTTPS URLs). Additionally, the `serverCertificateHashes` constructor option lets the browser pin the server certificate by SHA-256 hash, allowing self-signed certs (e.g., edge relays). This is a trust-on-first-use model, not a substitute for TLS — the connection is still encrypted and QUIC's identity checks still apply.

**Q4: How is the WebTransport handshake different from WebSocket's?**
A: WebSocket uses HTTP/1.1 `Upgrade: websocket` with a `Sec-WebSocket-Key` challenge, then switches to a binary frame protocol. WebTransport uses HTTP/3's extended CONNECT (RFC 9220) — the client sends a `:method=CONNECT` with `:protocol=webtransport`, the server returns 2xx, and a session is established. There's no per-message framing layer beyond what QUIC streams already provide.

**Q5: What's the head-of-line blocking problem, and how does WebTransport solve it?**
A: HOLB happens when an in-order transport like TCP stalls unrelated data behind a retransmit. If you multiplex 50 messages over one TCP socket and message 3 is lost, messages 4-50 sit in the kernel buffer even though they've arrived — they can't be delivered until 3 is retransmitted. WebTransport solves this by running each logical channel as an independent QUIC stream; loss recovery on stream N doesn't touch stream M.

## References

- [W3C WebTransport Specification](https://www.w3.org/TR/webtransport/)
- [MDN: WebTransport API](https://developer.mozilla.org/en-US/docs/Web/API/WebTransport)
- [Chrome Developers: WebTransport](https://developer.chrome.com/docs/capabilities/web-transport)
- [RFC 9220 — Proxying UDP in HTTP (extended CONNECT)](https://www.rfc-editor.org/rfc/rfc9220)
- [RFC 9221 — An Unreliable Datagram Extension to QUIC](https://www.rfc-editor.org/rfc/rfc9221)
- [IETF draft-ietf-webtrans-http3 (WebTransport over HTTP/3)](https://datatracker.ietf.org/doc/html/draft-ietf-webtrans-http3)
- [Chrome blog: WebTransport now shipped](https://developer.chrome.com/blog/webtransport-shipped)
- [quinn (Rust QUIC) — wtransport crate docs](https://docs.rs/wtransport)
