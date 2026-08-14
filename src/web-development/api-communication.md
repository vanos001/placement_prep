# API Communication Patterns

This guide covers the communication patterns used between browsers and servers — from REST conventions to modern alternatives like GraphQL and WebTransport. For HTTP fundamentals, see [HTTP Fundamentals](http-fundamentals.md); for WebSockets, see [WebSockets](websockets.md).

## REST Best Practices

REST (Representational State Transfer) is the dominant API architecture. Key conventions:

### URL Design

```
GET    /api/users           # List users
GET    /api/users/123       # Get user 123
POST   /api/users           # Create user
PUT    /api/users/123       # Replace user 123
PATCH  /api/users/123       # Partially update user 123
DELETE /api/users/123       # Delete user 123

GET    /api/users/123/posts  # Nested resource: posts of user 123
```

**Rules:** Use nouns (not verbs), plural nouns for collections, nest only one level deep, use query parameters for filtering/sorting/pagination:

```
GET /api/users?role=admin&sort=created_at&page=2&limit=20
```

### Status Codes

| Code | Usage |
|------|-------|
| `200` | Successful GET/PUT/PATCH |
| `201` | Successful POST (include `Location` header) |
| `204` | Successful DELETE (no body) |
| `400` | Validation error (return error details in body) |
| `401` | Missing or invalid authentication |
| `403` | Authenticated but not authorized |
| `404` | Resource not found |
| `409` | Conflict (e.g., duplicate email) |
| `422` | Valid JSON but semantically invalid |
| `429` | Rate limited |

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email is required",
    "details": [
      { "field": "email", "message": "must not be empty" }
    ]
  }
}
```

### Versioning

```
/api/v1/users    # URL path versioning (most common)
/api/users       # Header versioning: Accept: application/vnd.api.v1+json
```

## GraphQL

GraphQL is a query language for APIs that lets clients request exactly the data they need:

```graphql
# Query
query {
  user(id: 123) {
    name
    email
    posts(limit: 5) {
      title
      createdAt
    }
  }
}

# Mutation
mutation {
  createPost(input: { title: "Hello", content: "World" }) {
    post { id, title }
    errors { field, message }
  }
}
```

### When to Use GraphQL vs REST

| Factor | REST | GraphQL |
|--------|------|---------|
| Data requirements | Fixed, uniform | Varies significantly per client |
| Over-fetching | Common | Eliminated |
| Multiple resources | Multiple requests | Single request |
| Caching | HTTP caching (ETag, Cache-Control) | More complex (needs DataLoader) |
| Learning curve | Low | Higher |
| Tooling | Minimal | Strong type system, introspection |
| File uploads | Simple (multipart) | More complex |

**Use REST when:** the API is simple, caching is critical, or you're building a public API. **Use GraphQL when:** clients have diverse data needs, you're avoiding multiple requests, or you want a strong type system.

## gRPC-Web

gRPC uses Protocol Buffers for efficient binary serialization. gRPC-Web enables browser clients to call gRPC services:

```protobuf
// user.proto
service UserService {
  rpc GetUser(GetUserRequest) returns (UserResponse);
}

message GetUserRequest { int32 id = 1; }
message UserResponse { string name = 1; string email = 2; }
```

**Advantages:** Small payload size, strong typing via protobuf, bidirectional streaming (with gRPC-Web experimental support). **Trade-off:** Requires a proxy layer, more setup than REST/GraphQL.

## Server-Sent Events (SSE)

SSE provides server-to-client streaming over a single HTTP connection (covered briefly in [WebSockets](websockets.md) — here's a focused look):

```javascript
const source = new EventSource('/api/notifications');

source.onmessage = (event) => {
  const data = JSON.parse(event.data);
  showNotification(data);
};

// Listen for named events
source.addEventListener('progress', (event) => {
  updateProgressBar(event.data);
});
```

**Best for:** notifications, live feeds, stock prices, progress updates. Not suitable for bidirectional communication.

## WebTransport

WebTransport is a modern API for secure, multiplexed data transfer over QUIC (HTTP/3):

```javascript
const transport = new WebTransport('https://example.com/transport');
await transport.ready;

// Send unreliable datagrams (like UDP)
const stream = await transport.createUnidirectionalStream();
const writer = stream.writable.getWriter();
writer.write(new Uint8Array([1, 2, 3]));

// Receive bidirectional streams
transport.incomingBidirectionalStreams
  .then(readable => readable.getReader())
  .then(reader => reader.read());
```

**Advantages over WebSockets:** Multiple streams per connection (no head-of-line blocking), unreliable datagram support (for gaming/real-time), QUIC-based (built-in congestion control, connection migration). Still experimental with limited browser support.

## Fetch API & AbortController

```javascript
// Basic fetch
const response = await fetch('/api/users', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name: 'John' })
});

if (!response.ok) throw new Error(`HTTP ${response.status}`);
const data = await response.json();

// AbortController for cancellation
const controller = new AbortController();
const timeout = AbortSignal.timeout(5000); // 5-second timeout

try {
  const res = await fetch('/api/slow', {
    signal: AbortSignal.any([controller.signal, timeout])
  });
} catch (err) {
  if (err.name === 'AbortError') console.log('Request cancelled or timed out');
}

// Manual abort
controller.abort(); // cancels the fetch
```

### Fetch Interceptors (Axios-style)

Axios provides built-in interceptors. With native `fetch`, create a wrapper:

```javascript
async function fetchWithAuth(url, options = {}) {
  const token = getAccessToken();
  const headers = new Headers(options.headers);

  if (token) headers.set('Authorization', `Bearer ${token}`);
  headers.set('Content-Type', 'application/json');

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) return fetchWithAuth(url, options); // retry
    window.location.href = '/login'; // redirect
  }

  return response;
}
```

## Interview Questions

**Q: What are the key principles of REST?**
A: Statelessness (each request contains all needed info), uniform interface (standard HTTP methods and status codes), resource-based URLs (nouns, not verbs), and proper use of HTTP features (status codes, caching headers, content negotiation).

**Q: When would you choose GraphQL over REST?**
A: GraphQL excels when clients have varying data needs (mobile vs desktop, different views) that would cause over/under-fetching with REST, or when you need to aggregate data from multiple sources in a single request. REST is better when HTTP caching is critical or the API surface is simple and stable.

**Q: How does AbortController work with fetch?**
A: AbortController creates an `AbortSignal` that can be passed to `fetch`. Calling `controller.abort()` cancels the in-flight request, rejecting the promise with an `AbortError`. This enables timeouts, user-initiated cancellation, and cleanup when components unmount.

**Q: What is the difference between SSE and WebSockets?**
A: SSE is server-to-client only, uses standard HTTP, auto-reconnects, and supports event types. WebSockets are full-duplex (bidirectional), support binary data, and require manual reconnection logic. Choose SSE for one-way server push; WebSockets for bidirectional real-time communication.

## References

- [MDN — Fetch API](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [GraphQL Official Documentation](https://graphql.org/learn/)
- [MDN — WebTransport](https://developer.mozilla.org/en-US/docs/Web/API/WebTransport)
- [RESTful API Design Best Practices](https://restfulapi.net/)
