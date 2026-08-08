# API Gateways

## Overview

An API gateway is a **single entry point** for all client requests in a microservices architecture. It handles cross-cutting concerns like authentication, rate limiting, load balancing, and request routing, so individual services can focus on business logic. The gateway pattern simplifies client-side code and provides a unified API surface.

## Why API Gateways?

```mermaid
graph TD
    subgraph "Without Gateway (Client routes directly)"
        C[Client] --> S1[Service A]
        C --> S2[Service B]
        C --> S3[Service C]
        Note1["Client must know:\n- All service addresses\n- Auth for each\n- How to aggregate"]
    end
    
    subgraph "With Gateway"
        C2[Client] --> G[API Gateway]
        G --> S4[Service A]
        G --> S5[Service B]
        G --> S6[Service C]
        Note2["Client only knows:\n- Gateway address"]
    end
```

## Core Functions

```mermaid
graph TD
    G[API Gateway] --> R[Request Routing]
    G --> A[Authentication/Authorization]
    G --> RL[Rate Limiting]
    G --> LB[Load Balancing]
    G --> CB[Circuit Breaking]
    G --> Cache[Caching]
    G --> Agg[Request Aggregation]
    G --> Transform[Request/Response Transformation]
    G --> Log[Logging/Monitoring]
    G --> SSL[TLS Termination]
```

## Request Routing

```mermaid
graph LR
    C[Client] --> G[API Gateway]
    G -->|"/api/users/*"| US[User Service]
    G -->|"/api/orders/*"| OS[Order Service]
    G -->|"/api/products/*"| PS[Product Service]
    G -->|"ws://api/chat"| CS["Chat Service (WebSocket)"]
```

```yaml
# NGINX routing configuration
routes:
  - path: /api/users/**
    service: user-service
    port: 8080
  - path: /api/orders/**
    service: order-service
    port: 8081
  - path: /api/products/**
    service: product-service
    port: 8082
```

## Authentication and Authorization

```mermaid
sequenceDiagram
    participant C as Client
    participant G as API Gateway
    participant Auth as Auth Service
    participant S as Target Service
    
    C->>G: Request (with JWT)
    G->>G: Validate JWT
    alt JWT valid
        G->>S: Forward request (with user context)
        S-->>G: Response
        G-->>C: Response
    else JWT invalid
        G-->>C: 401 Unauthorized
    end
```

```python
# Gateway middleware
def auth_middleware(request):
    token = request.headers.get('Authorization')
    if not token:
        return Response(status=401)
    
    try:
        payload = jwt.decode(token, SECRET_KEY)
        request.user = payload
        return None  # Continue to next middleware
    except jwt.InvalidTokenError:
        return Response(status=401)
```

## Rate Limiting

```mermaid
graph TD
    subgraph "Rate Limiting Algorithms"
        TK[Token Bucket] --> TK1["Tokens added at fixed rate\nConsume token per request\nReject when empty"]
        LK[Leaky Bucket] --> LK1["Requests queued\nProcessed at fixed rate\nReject when queue full"]
        SW[Sliding Window] --> SW1["Count requests in window\nReject when limit exceeded"]
        FC[Fixed Counter] --> FC1["Reset counter each window\nSimple but bursty"]
    end
```

### Token Bucket Implementation

```python
import time

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate  # tokens per second
        self.last_refill = time.time()
    
    def allow_request(self):
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, 
                         self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

### Rate Limiting Headers

```python
# Response headers
headers = {
    'X-RateLimit-Limit': '100',        # Max requests per window
    'X-RateLimit-Remaining': '42',      # Remaining requests
    'X-RateLimit-Reset': '1625097600',  # Window reset time
    'Retry-After': '30'                 # Seconds to wait (if limited)
}
```

## Request Aggregation

```mermaid
sequenceDiagram
    participant C as Client
    participant G as API Gateway
    participant US as User Service
    participant OS as Order Service
    
    C->>G: GET /api/dashboard/user/123
    
    par Parallel requests
        G->>US: GET /users/123
        G->>OS: GET /orders?user_id=123
    end
    
    US-->>G: User data
    OS-->>G: Order data
    
    G->>G: Aggregate responses
    G-->>C: Combined dashboard data
```

## Popular API Gateways

### Kong

```mermaid
graph TD
    subgraph "Kong Architecture"
        C[Client] --> K[Kong Gateway]
        K --> DB[(PostgreSQL/Cassandra)]
        K --> S1[Service 1]
        K --> S2[Service 2]
    end
```

```bash
# Add a service
curl -X POST http://localhost:8001/services/ \
  --data name=user-service \
  --data url=http://user-service:8080

# Add a route
curl -X POST http://localhost:8001/services/user-service/routes \
  --data paths[]=/api/users

# Add rate limiting plugin
curl -X POST http://localhost:8001/services/user-service/plugins \
  --data name=rate-limiting \
  --data config.minute=100
```

**Features**: Plugin-based, supports auth, rate limiting, logging, transformations

### Envoy

```yaml
# Envoy configuration
static_resources:
  listeners:
    - name: listener_0
      address:
        socket_address:
          address: 0.0.0.0
          port_value: 8080
      filter_chains:
        - filters:
            - name: envoy.filters.network.http_connection_manager
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
                route_config:
                  virtual_hosts:
                    - name: backend
                      domains: ["*"]
                      routes:
                        - match:
                            prefix: "/api/users"
                          route:
                            cluster: user_service
  clusters:
    - name: user_service
      type: STRICT_DNS
      load_assignment:
        cluster_name: user_service
        endpoints:
          - lb_endpoints:
              - endpoint:
                  address:
                    socket_address:
                      address: user-service
                      port_value: 8080
```

**Features**: High performance, service mesh sidecar, advanced load balancing

### NGINX

```nginx
# NGINX as API Gateway
http {
    upstream user_service {
        server user-service-1:8080;
        server user-service-2:8080;
    }
    
    upstream order_service {
        server order-service-1:8081;
        server order-service-2:8081;
    }
    
    server {
        listen 80;
        
        location /api/users/ {
            proxy_pass http://user_service;
            proxy_set_header X-Real-IP $remote_addr;
            rate_limit zone=api burst=10;
        }
        
        location /api/orders/ {
            proxy_pass http://order_service;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

## Comparison

| Gateway | Type | Performance | Extensibility | Use Case |
|---------|------|-------------|---------------|----------|
| **Kong** | Standalone | High | Plugin-based | General purpose |
| **Envoy** | Sidecar/Edge | Very high | xDS API | Service mesh |
| **NGINX** | Reverse proxy | Very high | Modules/Config | High performance |
| **AWS API GW** | Managed | High | Limited | AWS ecosystem |
| **Traefik** | Reverse proxy | High | Labels/Docker | Container-native |

## BFF (Backend for Frontend)

```mermaid
graph TD
    subgraph "Frontend Clients"
        Web[Web App]
        Mobile[Mobile App]
        IoT[IoT Device]
    end
    
    subgraph "BFF Layer"
        WebBFF[Web BFF]
        MobileBFF[Mobile BFF]
        IoTBFF[IoT BFF]
    end
    
    subgraph "Services"
        US[User Service]
        OS[Order Service]
        PS[Product Service]
    end
    
    Web --> WebBFF
    Mobile --> MobileBFF
    IoT --> IoTBFF
    
    WebBFF --> US
    WebBFF --> OS
    WebBFF --> PS
    
    MobileBFF --> US
    MobileBFF --> OS
    MobileBFF --> PS
```

Each BFF tailors responses for its client type (web gets full data, mobile gets minimal data).

## Interview Questions

1. **What is an API gateway and why is it needed?**
   - A single entry point for all client requests in microservices. It handles routing, authentication, rate limiting, and other cross-cutting concerns, simplifying client code and providing a unified API.

2. **What functions does an API gateway provide?**
   - Request routing, authentication/authorization, rate limiting, load balancing, circuit breaking, caching, request aggregation, and logging/monitoring.

3. **What is the BFF pattern?**
   - Backend for Frontend: separate gateway per client type (web, mobile, IoT). Each BFF tailors responses for its client, reducing over-fetching and simplifying client code.

4. **How does rate limiting work in an API gateway?**
   - Algorithms like token bucket, leaky bucket, or sliding window track request counts. When limits are exceeded, the gateway returns 429 Too Many Requests with Retry-After header.

5. **Compare Kong, Envoy, and NGINX as API gateways.**
   - Kong: plugin-based, good for general use. Envoy: high performance, service mesh sidecar. NGINX: very high performance, configuration-based. All support routing, auth, and rate limiting.

6. **How does an API gateway handle authentication?**
   - Validates JWT tokens or API keys in each request. Can integrate with OAuth2 providers. Adds user context to requests before forwarding to services.

## Common Mistakes

- Making the gateway a **single point of failure** — deploy multiple instances
- Putting **business logic** in the gateway — keep it focused on cross-cutting concerns
- Not implementing **circuit breakers** — slow services can block the gateway
- Ignoring **caching** — reduces load on backend services
- Not **versioning APIs** — breaking changes affect all clients
- Over-complicating the gateway — too many plugins add latency

## Summary

API gateways provide a unified entry point for microservices, handling cross-cutting concerns like routing, auth, rate limiting, and load balancing. Popular options include Kong, Envoy, and NGINX. The BFF pattern tailors gateways per client type. Proper configuration and monitoring are essential for reliable operation.

## Cross-References

- [Microservices Overview](README.md) — Microservices architecture
- [Service Discovery](discovery.md) — How gateway finds services
- [Circuit Breakers](circuit-breakers.md) — Failure handling
- [Observability](observability.md) — Monitoring gateways
- [Rate Limiting](circuit-breakers.md) — Rate limiting patterns
- [Pub/Sub](../messaging/pubsub.md) — Event-driven patterns

## Cross References

- [Load Balancing](../../networks/load-balancing/README.md)
- [Reverse Proxy](../../networks/load-balancing/reverse-proxy.md)
- [Service Discovery](discovery.md)
- [Rate Limiting](../../interview/system-design/rate-limiter.md)
