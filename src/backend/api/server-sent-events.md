# Server-Sent Events (SSE) — One-Way Push over HTTP

Server-Sent Events is the web's simplest streaming protocol: a single long-lived HTTP connection from a browser to a server, over which the server pushes UTF-8 text messages until the client or server closes the connection. Unlike WebSockets, SSE is strictly one-way (server → client) and sits entirely inside HTTP/1.1 (or HTTP/2), which means it inherits HTTP's connection management, header semantics, TLS story, and proxy traversal without extra protocol negotiation. For live feeds, notifications, and AI token streaming, SSE is usually the right answer; for true bidirectional communication (chat, gaming), WebSockets remain the better tool.

## The Wire Format — `text/event-stream`

SSE messages are UTF-8 text frames separated by a pair of newline characters. The content type is `text/event-stream`, which is its own media type registered with IANA. The format is line-oriented and parser-trivial:

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache, no-transform
Connection: keep-alive
X-Accel-Buffering: no

event: message
data: hello
data: world

data: {"event":"tick","value":1}

: this is a comment, ignored by clients
retry: 5000

event: update
id: 42
data: second message
```

Four fields are defined:

| Field | Purpose |
|-------|---------|
| `data` | The message body. Multiple `data:` lines are concatenated with `\n` between them. |
| `event` | Names the event — selects which `addEventListener` handler fires on the client. |
| `id` | An opaque last-event-ID. Stored by the browser; re-sent as `Last-Event-ID` on reconnect. |
| `retry` | Milliseconds the client should wait before reconnecting after a drop. |

Lines starting with `:` (colon) are comments and are ignored by clients. Servers use them as heartbeats to keep proxies from closing idle connections. A message is terminated by an empty line (a `\n\n` sequence). Within a message, fields may appear in any order; only one `event`, `id`, and `retry` per message is honored (later values overwrite earlier).

Field parsing rules:

- A line is `<field>:<space><value>\n`. The leading space after the colon is stripped. A leading space before the colon is also stripped. A field with no colon is treated as if the colon were at the end of the line, with an empty value.
- Trailing whitespace on a line is preserved if it appears after the value, except for the single leading space that is stripped.
- A line with just a colon (e.g., `: keep-alive\n`) is a comment.

## The EventSource API

The browser-side API is `EventSource`, a WHATWG-standardized class in the HTML spec. It is intentionally minimal: it auto-reconnects, it dispatches `message` events for un-named frames and named events for frames with `event:`, and it tracks `lastEventId` for resumption.

```javascript
const es = new EventSource('/api/events');

// Fires for every unnamed `data:` frame
es.onmessage = (e) => {
  console.log('default', e.data);
};

// Fires for every `event: update\ndata: ...` frame
es.addEventListener('update', (e) => {
  const payload = JSON.parse(e.data);
  console.log('update', payload, 'lastId=', e.lastEventId);
});

es.onerror = (e) => {
  // EventSource will auto-reconnect. Use es.close() to stop.
  console.warn('connection dropped, reconnecting');
};

// To stop:
// es.close();
```

Key behaviors:

- **Auto-reconnect** — when the connection drops, the browser waits `retry` milliseconds (default 3s, set via the `retry:` field), then reconnects.
- **Last-Event-ID header** — on reconnect, the browser sends the last received `id:` value as the `Last-Event-ID` HTTP request header. The server can use this to resume.
- **HTTP status** — `EventSource` only fires `onopen` for `200 OK`. A `301/302/307/308` redirect is followed. A `401`/`403`/`404` causes the connection to fail with `readyState = CLOSED`; a `500`/`503` triggers a retry. Browsers will retry even some 4xx codes, but this is implementation-defined.
- **CORS** — cross-origin SSE requires the server to send `Access-Control-Allow-Origin` and either `Access-Control-Allow-Credentials: true` (when `withCredentials: true` is set) or omit it.
- **Cookies** — same-origin requests include cookies by default; cross-origin requests only include them if `new EventSource(url, { withCredentials: true })` is set.

```javascript
const es = new EventSource('https://api.example.com/events', {
  withCredentials: true,
});
```

## A Minimal Server

In Node.js with no framework:

```javascript
import http from 'node:http';

const server = http.createServer((req, res) => {
  if (req.url !== '/events') {
    res.writeHead(404).end();
    return;
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no', // tell nginx not to buffer
  });

  let lastEventId = parseInt(req.headers['last-event-id'] || '0', 10);

  const send = (event, data) => {
    lastEventId += 1;
    res.write(`event: ${event}\nid: ${lastEventId}\n`);
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  };

  // Heartbeat every 15s to keep proxies alive
  const heartbeat = setInterval(() => res.write(`:\n\n`), 15000);

  const timer = setInterval(() => {
    send('tick', { time: Date.now() });
  }, 1000);

  req.on('close', () => {
    clearInterval(heartbeat);
    clearInterval(timer);
    res.end();
  });
});

server.listen(3000);
```

Two non-obvious details:

1. **`X-Accel-Buffering: no`** is nginx-specific. Without it, nginx buffers the response and the client sees nothing until the buffer fills or the connection closes. Equivalent concerns apply to Cloudflare (`Cache-Control: no-cache, no-transform`), Apache (use `mod_proxy` with `flushpackets on`), and AWS ALB (use HTTP/2 backend; HTTP/1.1 ALB may buffer).
2. **The `req.on('close')` handler is critical** — without it, timers keep firing into a closed socket and your server leaks. Use a single on-close cleanup function.

In Python with FastAPI:

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import asyncio, json

app = FastAPI()

async def event_stream(request: Request):
    last_id = int(request.headers.get('last-event-id', 0))
    while True:
        if await request.is_disconnected():
            break
        last_id += 1
        yield f"event: tick\nid: {last_id}\n"
        yield f"data: {json.dumps({'time': asyncio.get_event_loop().time()})}\n\n"
        await asyncio.sleep(1)

@app.get("/events")
async def events(request: Request):
    return StreamingResponse(
        event_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
```

## Reconnection with `Last-Event-ID`

The combination of `id:` + browser-tracked `lastEventId` + auto-reconnect + `Last-Event-ID` header is what makes SSE robust enough for production use. The pattern:

```
Browser                              Server
   |                                    |
   |--- GET /events ------------------->|
   |                                    | (start streaming from cursor 0)
   |<-- data: ... id: 5 ----------------|
   |<-- data: ... id: 6 ----------------|
   |<-- data: ... id: 7 ----------------|
   |                                    |  (network glitch)
   |       (connection drops)           |
   |                                    |
   | (wait retry=3000ms)                |
   |                                    |
   |--- GET /events ------------------->|
   |    Last-Event-ID: 7                 |
   |                                    | (resume from cursor 8)
   |<-- data: ... id: 8 ----------------|
   |<-- data: ... id: 9 ----------------|
```

The server-side implementation reads `Last-Event-ID` and decides where to resume — typically by seeking into a log (Kafka offset, Redis stream ID, in-memory ring buffer). Note that **`Last-Event-ID` is sent as an HTTP request header**, not as a query parameter; this trips up developers the first time.

## AI Token Streaming — The Modern Killer Use Case

When an LLM generates tokens one at a time, SSE is the natural transport. The OpenAI Chat Completions API uses SSE for `stream: true`:

```bash
curl -N https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{"role":"user","content":"Tell me a story."}],
    "stream": true
  }'
```

Each emitted event looks like:

```
data: {"choices":[{"delta":{"content":"Once"}}]}

data: {"choices":[{"delta":{"content":" upon"}}]}

data: {"choices":[{"delta":{"content":" a time"}}]}

data: [DONE]
```

The `data: [DONE]` sentinel is OpenAI's convention to signal stream end; the SSE spec itself has no end-of-stream field — the server simply closes the connection.

Client-side handling:

```javascript
const es = new EventSource('/api/chat?prompt=tell+a+story');
let buffer = '';

es.onmessage = (e) => {
  if (e.data === '[DONE]') {
    es.close();
    return;
  }
  const chunk = JSON.parse(e.data);
  buffer += chunk.choices[0]?.delta?.content ?? '';
  document.body.textContent = buffer;
};
```

For server authors, the gotcha is **flush on every token** — many frameworks buffer responses until a certain size or until the request handler returns. The Node.js pattern is `res.flushHeaders()` after writing the status line, then `res.flush()` (or rely on the lack of buffering) after each `write()`. The FastAPI example above works because `StreamingResponse` flushes chunks as they are yielded.

## SSE vs WebSockets vs Long Polling

```
                    Long polling          SSE                 WebSocket
Connection         |  New per request    |  Long-lived       |  Long-lived
Direction          |  Server→client      |  Server→client    |  Bidirectional
Transport          |  HTTP               |  HTTP             |  WS frame protocol
Reconnect          |  Manual             |  Auto (built-in)  |  Manual
Resume             |  Via cookies        |  Last-Event-ID    |  Application-specific
Through proxies    |  Yes                |  Yes              |  Often blocked
Binary             |  No                 |  No (text only)   |  Yes
Max connections   |  Unlimited          |  6 per origin (HTTP/1.1) |  Unlimited
                   |                     |  Unlimited (HTTP/2)|
Backpressure       |  TCP                |  TCP              |  Application
```

The **6-connection-per-origin** limit is the single biggest reason teams abandon SSE: HTTP/1.1 allows browsers to open only 6 simultaneous connections per origin, so opening 7 SSE streams on the same origin causes the 7th to queue. HTTP/2 multiplexes all streams over one TCP connection, eliminating this limit; any production deployment should be on HTTP/2 or later. CDNs and load balancers must support HTTP/2 end-to-end (AWS ALB does; Cloudflare does; older nginx needs explicit configuration).

WebSocket's bidirectional capability matters for chat, collaborative editing (CRDT-style merging), and gaming; SSE's one-way nature is enough for live dashboards, notifications, log tails, and LLM streaming. Picking WebSocket for one-way use cases adds handshake complexity, separate port handling on proxies, and no auto-reconnect — pure downside.

## Common Mistakes

- **Forgetting `Cache-Control: no-cache`** — intermediary caches may swallow the stream and return the first chunk forever.
- **No heartbeat** — proxies (especially corporate proxies, AWS ALB with HTTP/1.1, and nginx with default settings) close idle connections after 60-120s. Send `:` comments every 15-30s.
- **Ignoring `Last-Event-ID`** — without resumption, every reconnect duplicates events that were already delivered. Always wire up the cursor.
- **Buffers between you and the client** — `X-Accel-Buffering: no` for nginx; `proxy_buffering off` for Apache; disable buffering on Vercel/Netlify edge functions; explicitly flush in Node.js (`res.flush()`).
- **Sending binary data** — SSE is text-only. Base64-encode binary payloads, or use WebSockets.
- **Opening more than 6 SSE streams per origin over HTTP/1.1** — switch to HTTP/2 or split origins.
- **Not closing `EventSource` when the component unmounts** — React effects that forget to `es.close()` leak connections and crash server capacity.

## Interview Questions

1. **What is SSE, and how does it differ from WebSockets?**
   SSE is a one-way (server→client) HTTP-based streaming protocol using `text/event-stream`. WebSockets is a bidirectional protocol that upgrades the HTTP connection to a different frame-based protocol. SSE is simpler, auto-reconnects, and works through proxies; WebSockets supports two-way traffic and binary frames.

2. **How does SSE handle reconnection?**
   The browser tracks the last `id:` it received. When the connection drops, it waits `retry` milliseconds (default 3s) and reconnects, sending the last id as the `Last-Event-ID` HTTP request header. The server uses this to resume the stream.

3. **What is the 6-connection limit and how do you avoid it?**
   HTTP/1.1 limits browsers to 6 simultaneous connections per origin. Each SSE stream consumes one. HTTP/2 multiplexes streams over a single TCP connection, removing the limit. Modern deployments should be on HTTP/2 or later.

4. **How do you keep proxies from closing the SSE connection?**
   Send a comment (`:`) line every 15-30s as a heartbeat. Set `Cache-Control: no-cache, no-transform` and `X-Accel-Buffering: no` (for nginx). Disable response buffering at every layer between you and the client.

5. **Why is SSE popular for LLM token streaming?**
   Token streaming is one-way (server → client), benefits from auto-reconnect, and works through corporate proxies that block WebSocket upgrades. The `data: <chunk>\n\n` framing is trivial to parse in JavaScript and matches the developer's mental model of "incremental text."

## References

- WHATWG HTML Living Standard — Server-sent events section: https://html.spec.whatwg.org/multipage/server-sent-events.html
- WHATWG HTML — The EventSource interface: https://html.spec.whatwg.org/multipage/comms.html#the-eventsource-interface
- MDN Web Docs — Server-sent events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- MDN — EventSource reference: https://developer.mozilla.org/en-US/docs/Web/API/EventSource
- IANA — `text/event-stream` media type registration: https://www.iana.org/assignments/media-types/text/event-stream
- RFC 9110 — HTTP Semantics (Cache-Control, Connection): https://www.rfc-editor.org/rfc/rfc9110
- RFC 9113 — HTTP/2 (multiplexing eliminates the 6-connection limit): https://www.rfc-editor.org/rfc/rfc9113
- OpenAI Chat Completions streaming reference: https://platform.openai.com/docs/api-reference/chat/streaming
- HTML Spec — Using server-sent events (developer guide): https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- Cloudflare docs — SSE buffering: https://developers.cloudflare.com/workers/runtime-apis/streams/
