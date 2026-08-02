# API Design Principles

## Why API Design Matters

APIs are the contract between services. Good API design enables scalability, maintainability, and developer productivity. Poor API design leads to tight coupling, versioning nightmares, and developer frustration.

## API Paradigms

### 1. REST (Representational State Transfer)

The most common API paradigm for web services.

```
GET    /api/v1/users          → List users
GET    /api/v1/users/123      → Get user 123
POST   /api/v1/users          → Create user
PUT    /api/v1/users/123      → Update user 123 (full)
PATCH  /api/v1/users/123      → Update user 123 (partial)
DELETE /api/v1/users/123      → Delete user 123
```

#### REST Principles
| Principle | Description | Example |
|-----------|-------------|---------|
| **Stateless** | Each request contains all needed info | Auth token in header |
| **Resource-based** | URLs represent resources, not actions | `/users` not `/getUsers` |
| **HTTP methods** | Use standard methods (GET, POST, etc.) | GET for reads, POST for creates |
| **HATEOAS** | Links to related resources | Response includes `next` URL |
| **Uniform interface** | Consistent naming and structure | `/users/{id}/orders` |

#### REST Best Practices
```
✅ Good:
GET /api/v1/users/123/orders
POST /api/v1/users
DELETE /api/v1/users/123

❌ Bad:
GET /api/v1/getUser?id=123
POST /api/v1/createUser
POST /api/v1/deleteUser/123
```

#### Status Codes
```
200 OK              → Successful GET/PUT/PATCH
201 Created         → Successful POST
204 No Content      → Successful DELETE
400 Bad Request     → Invalid input
401 Unauthorized    → Missing/invalid auth
403 Forbidden       → Authenticated but not allowed
404 Not Found       → Resource doesn't exist
409 Conflict        → Duplicate or conflict
429 Too Many Reqs   → Rate limited
500 Server Error    → Internal error
503 Unavailable     → Service down
```

### 2. GraphQL

Query language for APIs, developed by Facebook.

```
# Schema
type User {
  id: ID!
  name: String!
  email: String!
  orders: [Order!]!
}

type Query {
  user(id: ID!): User
  users(limit: Int, offset: Int): [User!]!
}

type Mutation {
  createUser(input: CreateUserInput!): User!
}

# Query (client specifies what it needs)
query {
  user(id: "123") {
    name
    orders {
      id
      total
    }
  }
}
```

#### GraphQL vs REST

| Aspect | REST | GraphQL |
|--------|------|---------|
| Endpoints | Multiple | Single |
| Data fetching | Fixed structure | Client specifies |
| Over-fetching | Common | Eliminated |
| Under-fetching | Common (multiple calls) | Eliminated |
| Caching | Easy (HTTP caching) | Harder |
| Complexity | Simpler | More complex |
| File uploads | Native | Requires workaround |
| Real-time | WebSocket | Subscriptions |

#### When to Use GraphQL
- Mobile apps (bandwidth sensitive)
- Complex data relationships
- Multiple client types with different needs
- Rapid frontend iteration

#### When to Use REST
- Simple CRUD APIs
- Public APIs (easier to document/cache)
- Microservices (simpler inter-service communication)
- File-heavy operations

### 3. gRPC (Google Remote Procedure Call)

High-performance RPC framework using Protocol Buffers.

```protobuf
// user.proto
syntax = "proto3";

service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (stream User);
  rpc CreateUser(CreateUserRequest) returns (User);
}

message User {
  int32 id = 1;
  string name = 2;
  string email = 3;
}
```

#### gRPC vs REST

| Aspect | gRPC | REST |
|--------|------|------|
| Protocol | HTTP/2 | HTTP/1.1 (usually) |
| Format | Protobuf (binary) | JSON (text) |
| Speed | Faster (binary, multiplexing) | Slower |
| Streaming | Native (bidirectional) | Limited (SSE, WebSocket) |
| Browser support | Requires proxy | Native |
| Code generation | Built-in | Manual or OpenAPI |
| Learning curve | Steeper | Lower |

#### When to Use gRPC
- Microservice-to-microservice communication
- Low-latency requirements
- Streaming data
- Polyglot environments (auto-generated clients)

### API Paradigm Comparison

| Criteria | REST | GraphQL | gRPC |
|----------|------|---------|------|
| Learning curve | Low | Medium | High |
| Performance | Good | Good | Excellent |
| Flexibility | Medium | High | Medium |
| Caching | Easy | Hard | N/A |
| Tooling | Excellent | Good | Good |
| Browser support | Native | Native | Needs proxy |
| Best for | Public APIs | Client-driven queries | Internal services |

## API Versioning

### Versioning Strategies

#### URL Versioning
```
GET /api/v1/users
GET /api/v2/users
```
- Pros: Clear, easy to route
- Cons: URL changes, client must update

#### Header Versioning
```
GET /api/users
Accept: application/vnd.myapi.v2+json
```
- Pros: Clean URLs
- Cons: Less visible, harder to test

#### Query Parameter Versioning
```
GET /api/users?version=2
```
- Pros: Easy to implement
- Cons: Clutters URL, easy to forget

#### Best Practice
```
URL versioning for public APIs (clear, explicit)
Header versioning for internal APIs (clean URLs)
```

## Pagination

### Offset-Based Pagination
```
GET /api/v1/users?offset=20&limit=10

Response:
{
  "data": [...],
  "total": 1000,
  "offset": 20,
  "limit": 10
}
```

**Pros**: Simple, can jump to any page
**Cons**: Inconsistent with concurrent inserts/deletes, slow at high offsets

### Cursor-Based Pagination
```
GET /api/v1/users?cursor=eyJpZCI6MTAwfQ&limit=10

Response:
{
  "data": [...],
  "next_cursor": "eyJpZCI6MTEwfQ",
  "has_more": true
}
```

**Pros**: Consistent, efficient for large datasets
**Cons**: Can't jump to arbitrary page

### Keyset Pagination
```
GET /api/v1/users?created_after=2024-01-01T00:00:00Z&limit=10
```

**Pros**: Efficient (uses index), consistent
**Cons**: Requires sortable column

### Pagination Comparison

| Strategy | Consistency | Performance | Jump to Page | Use Case |
|----------|------------|-------------|--------------|----------|
| Offset | Poor | Degrades | Yes | Small datasets |
| Cursor | Good | Consistent | No | Large datasets, infinite scroll |
| Keyset | Good | Excellent | No | Time-series, feeds |

## Rate Limiting

### Why Rate Limiting?
- Prevent abuse and DDoS
- Ensure fair resource usage
- Protect backend services
- Manage costs

### Rate Limiting Algorithms

#### Token Bucket
```
Bucket: capacity=10, refill=2/sec
Request: Takes 1 token
Empty: Reject request

Time 0: [10 tokens] → Request ✓
Time 1: [9 tokens] → Request ✓
Time 5: [5+2=7 tokens] → Multiple requests ✓
```

#### Sliding Window
```
Window: 60 seconds, Limit: 100 requests
Track: timestamps of each request
Count: requests in last 60 seconds
Exceed: Reject
```

#### Fixed Window
```
Window: 1 minute (00:00-00:60), Limit: 100
Count: requests in current minute
Problem: Burst at window boundary
00:59: 100 requests (OK)
00:01: 100 requests (OK)
Total: 200 in 2 seconds (exceeds intended rate)
```

#### Sliding Window Log
```
Log: [T1, T2, T3, ...]
On request: Remove entries older than window
Count remaining: If < limit, allow
```

### Algorithm Comparison

| Algorithm | Memory | Accuracy | Burst Handling | Use Case |
|-----------|--------|----------|----------------|----------|
| Token Bucket | Low | Good | Allows burst | API gateways |
| Sliding Window | Medium | Good | Smooth | General purpose |
| Fixed Window | Low | Fair | Boundary burst | Simple cases |
| Sliding Log | High | Exact | Smooth | Strict limiting |

### Rate Limit Headers
```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200

HTTP/1.1 429 Too Many Requests
Retry-After: 30
```

## API Security

### Authentication Methods

| Method | How | Use Case |
|--------|-----|----------|
| **API Key** | Simple string in header | Public APIs, simple auth |
| **OAuth 2.0** | Token-based delegation | Third-party access |
| **JWT** | Signed token with claims | Stateless auth |
| **mTLS** | Mutual certificate auth | Service-to-service |

### API Security Best Practices
```
✅ Always use HTTPS
✅ Validate all input
✅ Implement rate limiting
✅ Use authentication (OAuth/JWT)
✅ Use authorization (RBAC/ABAC)
✅ Log all API access
✅ Sanitize error messages (no stack traces)
✅ Use CORS properly
✅ Implement request size limits
```

## Error Handling

### Consistent Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_abc123"
  }
}
```

### Error Code Categories
```
VALIDATION_ERROR    → 400 Bad Request
AUTHENTICATION_ERROR → 401 Unauthorized
AUTHORIZATION_ERROR → 403 Forbidden
NOT_FOUND          → 404 Not Found
CONFLICT           → 409 Conflict
RATE_LIMITED       → 429 Too Many Requests
INTERNAL_ERROR     → 500 Server Error
```

## API Documentation

### OpenAPI (Swagger)
```yaml
openapi: 3.0.0
paths:
  /users/{id}:
    get:
      summary: Get user by ID
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: User found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
```

## Interview Tips

1. **Choose paradigm based on use case** — REST for public API, gRPC for internal, GraphQL for complex queries
2. **Always discuss versioning** — "We'll use URL versioning for backward compatibility"
3. **Include pagination** — "Cursor-based pagination for the feed"
4. **Mention rate limiting** — "Token bucket algorithm, 100 requests per minute"
5. **Consider error handling** — "Consistent error format with request IDs"
6. **Think about security** — "OAuth 2.0 for third-party, JWT for internal"
7. **Document the API** — "OpenAPI spec for REST, proto files for gRPC"
8. **Discuss caching** — "ETags for conditional requests, cache headers"

## Common Mistakes

- ❌ Using verbs in URLs (`/getUsers`)
- ❌ Ignoring versioning
- ❌ No pagination on list endpoints
- ❌ Inconsistent error formats
- ❌ No rate limiting
- ❌ Returning 200 for errors
- ❌ Exposing internal IDs or stack traces

## Cross-References

- [Security Design](./security-design.md) — Authentication and authorization
- [Scalability](./scalability.md) — API gateway patterns
- [Load Balancing](./load-balancing-design.md) — Rate limiting at LB
- [Monitoring](./monitoring-observability.md) — API metrics and logging
- [Caching Strategy](./caching-strategy.md) — HTTP caching headers
- [RPC](../rpc.md)
- [Networks HTTP](../../networks/http/rest.md)
- [Rate Limiter](../rate-limiter.md)
- [Cloud API Gateway](../../cloud/aws/vpc.md)

