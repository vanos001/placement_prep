# Backend Project Implementation Guides

Deep-dive guides for backend projects that demonstrate production-level thinking. Each project includes what to build, why it matters, the key technical decisions to make, and how to discuss it in interviews. These complement the ideas listed in [project-ideas.md](project-ideas.md) by providing architectural depth and implementation roadmaps.

---

## 1. REST API with Authentication, Rate Limiting, and Caching

### What to Build
A production-grade REST API for a resource management service (e.g., a bookmark manager, note-taking API, or task tracker) with JWT authentication, role-based access control, per-user rate limiting, and Redis-backed caching.

### Why It Matters
This project demonstrates that you understand the middleware stack every production backend needs — auth, rate limiting, and caching are non-negotiable in real services.

### Suggested Tech Stack
- **Language**: Go (for performance) or Node.js/Python (for speed of development)
- **Database**: PostgreSQL with connection pooling (pgxpool / Prisma)
- **Cache**: Redis
- **Auth**: JWT with RS256 signing, refresh token rotation
- **Rate Limiting**: Redis-based sliding window algorithm

### Key Architecture Decisions to Implement

**Authentication Flow**:
```
POST /auth/register → hash password (bcrypt) → store in DB → return tokens
POST /auth/login    → verify credentials → issue access + refresh tokens
POST /auth/refresh  → validate refresh token → rotate → issue new pair
```

**Rate Limiting Middleware**:
```
Request → Rate Limiter → Auth Middleware → Handler → Cache → Response
            │                            │
         Redis ZSET              Check cache first
         sliding window          → cache miss → DB query
```

**Caching Strategy**:
- Cache-aside pattern: check Redis before DB, populate on miss
- Cache invalidation: on write, delete the corresponding cache key
- TTL-based expiry for less-critical data

### What to Discuss in Interviews
- "Why did I use RS256 (asymmetric) instead of HS256 (symmetric) for JWT?"
- "How does refresh token rotation prevent token theft?"
- "Why sliding window over fixed window for rate limiting?"
- "Cache stampede prevention with singleflight/mutex"

### Difficulty: Intermediate | Estimated Time: 2–3 weeks

---

## 2. Real-Time Notification Service

### What to Build
A multi-channel notification service that accepts events via API, stores them, and delivers through WebSocket (for online clients), email, or webhooks. Support user preferences (opt-in/opt-out per channel), and notification batching.

### Why It Matters
Notifications are a core backend concern for any product with active users. This project shows you understand event-driven architecture and real-time communication.

### Suggested Tech Stack
- **API**: Node.js/Go with WebSocket support (ws / socket.io)
- **Queue**: Redis Streams or RabbitMQ for event buffering
- **Storage**: PostgreSQL for notification logs and user preferences
- **Email**: SMTP integration (Resend/SendGrid SDK)
- **Deployment**: Docker Compose for local, Kubernetes for production

### Key Architecture Decisions

```
Producer ──► API ──► Message Queue ──► Dispatcher
                 │                     ├──► WebSocket (real-time)
                 │                     ├──► Email Worker
                 │                     └──► Webhook Worker
                 ▼
              PostgreSQL
```

**Notification Flow**:
1. API receives notification request → validates → pushes to queue
2. Dispatcher reads from queue → checks user preferences → routes to appropriate channel
3. WebSocket: delivers immediately to connected clients; queues for offline delivery
4. Email: batch similar notifications to reduce email volume
5. Mark as read/delivered through API

### What to Discuss in Interviews
- "Why a message queue instead of direct delivery?" → decoupling, retry, backpressure
- "How do you handle WebSocket reconnection?" → heartbeat, message queue for offline state
- "How do you prevent notification spam?" → user preferences, rate limits, digest mode
- "At-least-once vs. exactly-once delivery trade-offs"

### Difficulty: Hard | Estimated Time: 3–4 weeks

---

## 3. URL Shortener with Analytics

### What to Build
While the basic URL shortener is listed in [project-ideas.md](project-ideas.md), this guide focuses on the analytics engine: click tracking, geographic distribution, referrer analysis, device breakdown, and time-series aggregation for traffic patterns.

### Why It Matters
A URL shortener is read-heavy with a high QPS requirement. The analytics layer adds data engineering depth — aggregation, time-series queries, and dashboard serving.

### Suggested Tech Stack
- **Core API**: Go (for redirect performance)
- **Storage**: PostgreSQL for URL metadata, ClickHouse for analytics events
- **Cache**: Redis for hot URL lookups and rate limiting
- **Analytics Ingestion**: Kafka → ClickHouse
- **Dashboard**: Grafana or simple React frontend

### Key Architecture Decisions

```
Short URL Request → Redis Cache → Hit? → 301 Redirect
                                  → Miss? → PostgreSQL → Cache → 301

Click Event → Kafka Topic → ClickHouse (batch insert)
                                  ↓
                           Grafana Dashboard
```

**Analytics Schema Design**:
```sql
CREATE TABLE click_events (
    short_code String,
    click_time DateTime,
    ip_address String,
    country LowCardinality(String),
    referrer String,
    user_agent String,
    device_type Enum8('mobile'=1, 'desktop'=2, 'tablet'=3)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(click_time)
ORDER BY (short_code, click_time);
```

### What to Discuss in Interviews
- "Why ClickHouse over PostgreSQL for analytics?" → columnar storage, compression, fast aggregations
- "How do you handle click attribution when users block cookies?"
- "301 vs 302 redirect — which and why?" → 301 for caching, 302 for analytics accuracy
- "How do you prevent abuse (link farms, spam)?"

### Difficulty: Intermediate-Hard | Estimated Time: 3 weeks

---

## 4. Job Queue with Priority Scheduling

### What to Build
A distributed job queue that accepts tasks via API, schedules them based on priority (CRITICAL > HIGH > NORMAL > LOW), supports retries with exponential backoff, dead-letter queues, and worker health monitoring.

### Why It Matters
Every backend that does async work (email, report generation, data processing) needs a job queue. Building one shows understanding of producer-consumer patterns, reliability, and scheduling.

### Suggested Tech Stack
- **API + Scheduler**: Go or Python (FastAPI)
- **Queue Backend**: Redis (LIST + ZSET for priority) or PostgreSQL (SKIP LOCKED)
- **Workers**: Goroutine workers / Python multiprocessing
- **Monitoring**: Prometheus metrics + simple dashboard

### Key Architecture Decisions

```
Producer → API → Priority Queue (Redis ZSET)
                    │
                    ▼
              Dispatcher (polls by priority)
                    │
              ┌─────┼─────┐
              ▼     ▼     ▼
           Worker Worker Worker
              │
         ┌────┴────┐
         ▼         ▼
      Success   Failure
         │         │
         ▼         ▼
      Complete   Retry? → Re-enqueue with higher delay
                         │
                         ▼ (max retries exceeded)
                      Dead Letter Queue
```

**Priority Scheduling**:
```
Redis ZSET: key = "queue:pending"
  score = (priority * 10^12) + (MAX_RETRIES - remaining_retries) * 10^8 + timestamp
  → Poll with ZPOPMIN for highest-priority job
```

### What to Discuss in Interviews
- "Why Redis ZSET instead of a simple LIST?" → O(log N) priority dequeue
- "How do you prevent starvation of LOW priority jobs?" → aging: increase effective priority over time
- "What happens when a worker crashes mid-processing?" → heartbeat timeout → re-enqueue
- "Exactly-once vs. at-least-once processing" → idempotency keys

### Difficulty: Hard | Estimated Time: 2–3 weeks

---

## 5. API Gateway

### What to Build
A lightweight API gateway that sits in front of multiple backend services and handles routing, JWT authentication, rate limiting, request/response transformation, circuit breaking, and API versioning.

### Why It Matters
API gateways are the front door of microservice architectures. Building one demonstrates systems thinking — you're building infrastructure that other services depend on.

### Suggested Tech Stack
- **Language**: Go (net/http, reverse proxy) or Rust (actix-web)
- **Config**: YAML-based route definitions
- **Rate Limiting**: Redis-backed sliding window
- **Discovery**: Static config → extend to Consul/etcd
- **Metrics**: Prometheus client library

### Key Architecture Decisions

```
Client → API Gateway → Route Config → Backend Service A
                          │
                    ┌─────┼─────┐
                    │ Auth Middleware   │
                    │ Rate Limiter     │
                    │ Circuit Breaker  │
                    │ Logger           │
                    └─────────────────┘
```

**Route Configuration Example**:
```yaml
routes:
  - path: /api/v1/users
    upstream: http://user-service:8080
    methods: [GET, POST]
    auth: true
    rate_limit: 100/minute
    timeout: 5s
    circuit_breaker:
      threshold: 5
      timeout: 30s
      half_open_requests: 3
  - path: /api/v1/orders
    upstream: http://order-service:8080
    methods: [GET, POST, PUT]
    auth: true
    rate_limit: 50/minute
```

### What to Discuss in Interviews
- "Why build a gateway instead of using Kong/Envoy?" → understanding the internals, educational
- "How does the circuit breaker state machine work?" → closed → open → half-open
- "How do you handle upstream timeouts?" → context cancellation, configurable timeout per route
- "Path-based vs. header-based routing trade-offs"

### Difficulty: Hard | Estimated Time: 3–4 weeks

---

## 6. Rate Limiter as a Service

### What to Build
A standalone rate limiting microservice that other services call (or deploy as a sidecar). Supports multiple algorithms (token bucket, sliding window, fixed window, leaky bucket), configurable limits per API key/user/IP, and a management API for dynamic rule updates.

### Why It Matters
Rate limiting is a cross-cutting concern. Building it as a service shows you understand distributed coordination and can design reusable infrastructure.

### Suggested Tech Stack
- **Language**: Go (for the service) + Lua scripts for Redis atomicity
- **State Store**: Redis (atomic operations via Lua scripts)
- **Protocol**: gRPC for inter-service calls, HTTP for management API
- **Deployment**: Docker, configurable as sidecar or standalone

### Key Architecture Decisions

```
Client → Protected Service → Rate Limiter (gRPC call) → Redis
              │                       │
              ▼                       ▼
         Rate Limited?         Token Bucket Check
         Return 429              via Lua Script (atomic)
```

**Atomic Rate Check (Redis Lua)**:
```lua
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count < limit then
    redis.call('ZADD', key, now, now .. ':' .. math.random())
    redis.call('EXPIRE', key, window)
    return {count + 1, limit}
else
    return {-1, limit}
end
```

### What to Discuss in Interviews
- "Why Lua scripts instead of separate Redis commands?" → atomicity, no race condition
- "Token bucket vs. sliding window — when to use which?"
- "How does the sidecar pattern compare to a centralized service?"
- "Handling clock skew in distributed environments"

### Difficulty: Intermediate-Hard | Estimated Time: 2 weeks

---

## How to Choose Your Project

| Your Target Role | Recommended Projects |
|---|---|
| Backend SWE | #1 REST API, #3 URL Shortener Analytics, #4 Job Queue |
| Platform/Infra SWE | #5 API Gateway, #6 Rate Limiter Service |
| Full-Stack SWE | #1 REST API (add frontend), #2 Notification Service |
| Senior SWE | #5 API Gateway, #2 Notification Service, #4 Job Queue |

## Common Mistakes

1. **Skipping observability** — add logging, metrics, and health checks from day one
2. **Not writing tests** — even 5 integration tests show engineering maturity
3. **Hardcoding configuration** — use environment variables and config files
4. **Ignoring error handling** — every API should have proper error responses with status codes
5. **No documentation** — README with architecture diagram, API docs, and run instructions
