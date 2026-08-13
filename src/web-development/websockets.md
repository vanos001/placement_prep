# WebSockets

WebSockets provide full-duplex, bidirectional communication between a client and server over a single TCP connection. They're the foundation of real-time web applications like chat, live notifications, collaborative editing, and gaming.

## The WebSocket Protocol

### Overview

The WebSocket protocol (RFC 6455) operates on top of TCP and provides:

- **Full-duplex communication** — both client and server can send messages at any time
- **Persistent connection** — once established, the connection stays open
- **Low latency** — no overhead of HTTP headers on each message
- **Lightweight framing** — minimal per-message overhead (as low as 2 bytes)

### The Handshake

WebSocket connections begin with an HTTP upgrade handshake:

```
# Client request
GET /chat HTTP/1.1
Host: server.example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
Origin: http://example.com

# Server response
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

Key aspects:

1. The client sends an HTTP request with `Upgrade: websocket` and `Connection: Upgrade` headers
2. `Sec-WebSocket-Key` is a random base64-encoded value for security
3. The server responds with `101 Switching Protocols` and computes `Sec-WebSocket-Accept` by concatenating the key with a magic GUID and SHA-1 hashing
4. After this handshake, the protocol switches from HTTP to WebSocket

### WebSocket Frames

After the handshake, data is transmitted in **frames**. A frame has:

- **FIN bit** — indicates if this is the final fragment
- **Opcode** — type of frame (text, binary, ping, pong, close)
- **Mask bit** — client-to-server frames must be masked
- **Payload length** — variable length encoding (7 bits, 16 bits, or 64 bits)
- **Masking key** — 4 bytes, XOR'd with the payload
- **Payload data** — the actual message content

Frame types:
- `0x01` — text frame (UTF-8)
- `0x02` — binary frame
- `0x08` — connection close
- `0x09` — ping
- `0x0A` — pong

### Using WebSockets in JavaScript

```javascript
// Create connection
const ws = new WebSocket('wss://example.com/socket');

// Connection opened
ws.addEventListener('open', (event) => {
  console.log('Connected');
  ws.send('Hello, Server!');
});

// Listen for messages
ws.addEventListener('message', (event) => {
  console.log('Message from server:', event.data);

  // If JSON
  const data = JSON.parse(event.data);
  console.log(data);
});

// Connection closed
ws.addEventListener('close', (event) => {
  console.log('Disconnected:', event.code, event.reason);
});

// Error handling
ws.addEventListener('error', (event) => {
  console.error('WebSocket error:', event);
});

// Send different data types
ws.send('text message');                    // string
ws.send(new ArrayBuffer(8));                // binary
ws.send(new Blob(['binary data']));         // binary

// Close connection
ws.close(1000, 'Normal closure');
```

### Connection States

```javascript
ws.readyState
// 0 - CONNECTING: connection not yet open
// 1 - OPEN: connection open and ready
// 2 - CLOSING: connection is closing
// 3 - CLOSED: connection is closed
```

### Reconnection Strategy

```javascript
class WebSocketClient {
  constructor(url, options = {}) {
    this.url = url;
    this.reconnectDelay = options.reconnectDelay || 1000;
    this.maxReconnectDelay = options.maxReconnectDelay || 30000;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = options.maxReconnectAttempts || Infinity;
    this.handlers = {};
    this.connect();
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.addEventListener('open', () => {
      console.log('Connected');
      this.reconnectAttempts = 0;
      this.handlers.open?.();
    });

    this.ws.addEventListener('message', (event) => {
      this.handlers.message?.(event.data);
    });

    this.ws.addEventListener('close', (event) => {
      console.log('Disconnected:', event.code);
      this.handlers.close?.(event);

      if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(
          this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
          this.maxReconnectDelay
        );
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
      }
    });

    this.ws.addEventListener('error', (event) => {
      console.error('WebSocket error');
      this.handlers.error?.(event);
    });
  }

  send(data) {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
    }
  }

  on(event, handler) {
    this.handlers[event] = handler;
  }

  close() {
    this.maxReconnectAttempts = 0; // prevent reconnection
    this.ws.close();
  }
}

// Usage
const client = new WebSocketClient('wss://example.com/ws', {
  reconnectDelay: 1000,
  maxReconnectAttempts: 5
});

client.on('message', (data) => {
  const msg = JSON.parse(data);
  console.log(msg);
});
```

## Heartbeat / Ping-Pong

To detect dead connections, WebSocket implementations use heartbeats:

```javascript
// Client-side heartbeat
class HeartbeatWebSocket {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.heartbeatInterval = 30000; // 30 seconds
    this.heartbeatTimeout = 5000;   // 5 seconds

    this.ws.addEventListener('open', () => {
      this.startHeartbeat();
    });

    this.ws.addEventListener('message', (event) => {
      if (event.data === 'pong') {
        this.clearHeartbeatTimeout();
        return;
      }
      // Handle normal message
      this.onMessage?.(event.data);
    });
  }

  startHeartbeat() {
    this.pingInterval = setInterval(() => {
      this.ws.send('ping');
      this.pingTimeout = setTimeout(() => {
        console.log('No pong received, closing');
        this.ws.close();
      }, this.heartbeatTimeout);
    }, this.heartbeatInterval);
  }

  clearHeartbeatTimeout() {
    clearTimeout(this.pingTimeout);
  }
}
```

## WebSocket vs SSE vs Polling

### Polling

The client periodically sends HTTP requests to check for updates.

```javascript
setInterval(async () => {
  const response = await fetch('/api/updates');
  const data = await response.json();
  handleUpdate(data);
}, 5000); // every 5 seconds
```

**Pros:**
- Simple to implement
- Works everywhere
- Uses standard HTTP

**Cons:**
- High latency (up to the polling interval)
- Wasted requests when no updates exist
- Server overhead from frequent requests

### Long Polling

The client sends a request, and the server holds it open until data is available or a timeout occurs.

```javascript
async function longPoll() {
  try {
    const response = await fetch('/api/updates', {
      signal: AbortSignal.timeout(30000)
    });
    const data = await response.json();
    handleUpdate(data);
  } catch (error) {
    // Timeout or error, reconnect
  }
  longPoll(); // immediately start next poll
}
```

**Pros:**
- Lower latency than regular polling
- Works through proxies and firewalls
- Compatible with HTTP/1.1

**Cons:**
- Server holds connections open (resource intensive)
- Not truly real-time
- Connection setup overhead on each response

### Server-Sent Events (SSE)

The server pushes updates to the client over a persistent HTTP connection using the `text/event-stream` format.

```javascript
// Client
const source = new EventSource('/api/events');

source.addEventListener('message', (event) => {
  console.log(event.data);
});

source.addEventListener('custom-event', (event) => {
  console.log(event.data);
});

source.addEventListener('error', (event) => {
  console.log('Connection lost, reconnecting...');
});

source.close(); // close connection
```

Server format:
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type": "update", "value": 42}

event: custom-event
data: {"message": "hello"}
id: 123
retry: 5000

data: multi-line\n
data: message\n
\n
```

**Pros:**
- Simple server implementation
- Automatic reconnection built into `EventSource`
- Uses standard HTTP (works with proxies, load balancers)
- Text-based, easy to debug
- Event types and IDs supported

**Cons:**
- Server-to-client only (need separate mechanism for client-to-server)
- Limited to ~6 connections per browser (HTTP/1.1 limitation, solved by HTTP/2)
- Text only (binary requires encoding)
- No binary data support

### WebSockets

**Pros:**
- True full-duplex communication
- Lowest latency
- Supports binary and text data
- Minimal per-message overhead

**Cons:**
- More complex server implementation
- May not work through some proxies/firewalls
- Requires handling reconnection logic
- Stateful connections (harder to scale)

### When to Use What

| Use Case | Best Choice |
|----------|-------------|
| Chat application | WebSocket |
| Live notifications | SSE or WebSocket |
| Real-time collaboration | WebSocket |
| Live sports scores | SSE |
| Dashboard updates | SSE |
| Online gaming | WebSocket |
| Stock ticker | SSE or WebSocket |
| Simple status updates | Polling or SSE |

## Scaling WebSockets

### The Challenge

WebSocket connections are **stateful** and **long-lived**, which creates scaling challenges:

- Each connection holds server memory and a file descriptor
- Sticky sessions are required (a client's messages must go to the same server)
- Horizontal scaling requires message routing between servers

### Load Balancing

**Sticky Sessions:**
Ensure that once a client connects to a specific server, all subsequent messages go to the same server.

```nginx
# Nginx sticky sessions
upstream websocket_backend {
    ip_hash; # route by client IP
    server backend1:8080;
    server backend2:8080;
}

server {
    location /ws {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400; # keep connection alive
    }
}
```

### Pub/Sub for Message Routing

When messages need to reach clients connected to different servers, use a pub/sub system:

```
Client A → Server 1 → Redis Pub/Sub → Server 2 → Client B
```

**Redis Pub/Sub:**

```javascript
const Redis = require('ioredis');
const redis = new Redis();
const subscriber = new Redis();

// Publishing server
redis.publish('channel', JSON.stringify({ type: 'message', data: 'hello' }));

// Subscribing server
subscriber.subscribe('channel');
subscriber.on('message', (channel, message) => {
  const data = JSON.parse(message);
  // Forward to connected WebSocket clients on this server
  clients.forEach(client => client.send(message));
});
```

**Redis Streams** provide persistence and consumer groups for more robust message routing.

### Connection Management

```javascript
// Track connections per user
const connections = new Map();

wss.on('connection', (ws, req) => {
  const userId = authenticateUser(req);

  // Close existing connection for this user
  const existing = connections.get(userId);
  if (existing) existing.close(1000, 'New connection');

  connections.set(userId, ws);

  ws.on('close', () => {
    connections.delete(userId);
  });
});

// Broadcast to all
function broadcast(data) {
  const message = JSON.stringify(data);
  connections.forEach((ws) => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(message);
    }
  });
}

// Send to specific user
function sendToUser(userId, data) {
  const ws = connections.get(userId);
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}
```

### Resource Limits

```javascript
// Rate limiting per connection
const rateLimit = new Map();

ws.on('message', (data) => {
  const now = Date.now();
  const lastTime = rateLimit.get(ws) || 0;

  if (now - lastTime < 100) { // max 10 messages per second
    ws.send(JSON.stringify({ error: 'Rate limit exceeded' }));
    return;
  }

  rateLimit.set(ws, now);
  handleMessage(data);
});
```

## WebSocket Libraries

### Socket.IO

The most popular WebSocket library, adding features on top of raw WebSockets:

- Automatic reconnection
- Rooms and namespaces
- Fallback to long-polling
- Binary support
- Event-based API

```javascript
// Server
const io = require('socket.io')(server, {
  cors: { origin: 'https://example.com' }
});

io.on('connection', (socket) => {
  socket.join('room-name');
  io.to('room-name').emit('message', 'Hello room');
  socket.on('chat', (msg) => io.emit('chat', msg));
});

// Client
const socket = io('https://example.com');
socket.emit('chat', 'Hello');
socket.on('message', (msg) => console.log(msg));
```

### ws (Node.js)

A lightweight, no-dependency WebSocket implementation:

```javascript
const { WebSocketServer } = require('ws');

const wss = new WebSocketServer({ port: 8080 });

wss.on('connection', (ws) => {
  ws.on('message', (data) => {
    // Echo back
    ws.send(data.toString());
  });
});
```

## Security Considerations

### Authentication

WebSockets don't support custom headers in the browser API, so authentication must happen during the handshake:

1. **Token in URL** — `wss://example.com/ws?token=abc123` (visible in server logs, use HTTPS)
2. **Cookie-based** — cookies are sent with the upgrade request
3. **First message** — authenticate after connection, close if invalid

```javascript
// Server-side verification during upgrade
wss.on('upgrade', (request, socket, head) => {
  const token = new URL(request.url, 'http://localhost').searchParams.get('token');
  if (!verifyToken(token)) {
    socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
    socket.destroy();
    return;
  }
});
```

### Denial of Service

- Limit connections per IP
- Limit message size and rate
- Set timeouts for idle connections
- Monitor memory usage

### Input Validation

- Always validate and sanitize messages from clients
- Don't trust client-sent data (user IDs, room names, etc.)
- Use schema validation (Zod, Joi) for JSON messages

## Key Interview Points

- WebSocket handshake starts as HTTP, then upgrades to the WebSocket protocol
- The handshake uses `Upgrade: websocket` and `101 Switching Protocols`
- WebSockets are full-duplex; HTTP is request-response
- SSE is server-to-client only with automatic reconnection; WebSockets are bidirectional
- Polling is simple but has high latency; long polling reduces latency but holds server connections
- Scaling WebSockets requires sticky sessions and a pub/sub system (Redis) for cross-server messaging
- WebSocket connections are stateful, making horizontal scaling harder than stateless HTTP
- Authentication for WebSockets typically happens during the handshake or via the first message
- `ws` (lowercase) is the Node.js library; `WebSocket` is the browser API
