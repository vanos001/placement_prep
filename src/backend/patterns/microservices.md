# Microservices Architecture

## Overview

Microservices is an architectural style where an application is composed of small, independently deployable services. Each service owns its data, runs in its own process, and communicates via well-defined APIs.

## Monolith vs Microservices

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Deployment** | Single unit | Independent per service |
| **Scaling** | Scale entire app | Scale individual services |
| **Technology** | Single stack | Polyglot |
| **Data** | Shared database | Database per service |
| **Team** | Large team, shared code | Small teams, ownership |
| **Complexity** | Simple initially | Complex (distributed) |

## Service Decomposition

### Decomposition Strategies

```mermaid
flowchart TD
    DECOMPOSE[Decompose By...] --> DOMAIN[Domain/Business Capability]
    DECOMPOSE --> SUBDOMAIN["Subdomain (DDD)"]
    DECOMPOSE --> DATA[Data Ownership]
    
    DOMAIN --> USER[User Service]
    DOMAIN --> ORDER[Order Service]
    DOMAIN --> PAYMENT[Payment Service]
    DOMAIN --> INVENTORY[Inventory Service]
```

### Domain-Driven Design (DDD)

```mermaid
flowchart TD
    subgraph "Core Domain"
        ORDER[Order Management]
    end
    subgraph "Supporting Domains"
        USER[User Management]
        INVENTORY[Inventory]
    end
    subgraph "Generic Domains"
        EMAIL[Email Service]
        LOGGING[Logging]
    end
```

## Communication Patterns

### Synchronous (HTTP/gRPC)

```mermaid
flowchart LR
    CLIENT[Client] --> GW[API Gateway]
    GW --> ORDER[Order Service]
    ORDER -->|HTTP/gRPC| USER[User Service]
    ORDER -->|HTTP/gRPC| PAYMENT[Payment Service]
```

### Asynchronous (Message Queue)

```mermaid
flowchart LR
    ORDER[Order Service] -->|Publish| MQ[Message Broker]
    MQ -->|Subscribe| PAYMENT[Payment Service]
    MQ -->|Subscribe| INVENTORY[Inventory Service]
    MQ -->|Subscribe| EMAIL[Email Service]
```

| Sync | Async |
|------|-------|
| Simple | Complex |
| Tight coupling | Loose coupling |
| Blocking | Non-blocking |
| Real-time | Eventual consistency |

## API Gateway

```mermaid
flowchart TD
    CLIENT[Client] --> GW[API Gateway]
    GW --> RATE[Rate Limiting]
    GW --> AUTH[Authentication]
    GW --> ROUTE[Routing]
    
    ROUTE --> S1[Service 1]
    ROUTE --> S2[Service 2]
    ROUTE --> S3[Service 3]
```

**Responsibilities:**
- Request routing and composition
- Authentication and authorization
- Rate limiting and throttling
- SSL termination
- Request/response transformation
- Load balancing

## Data Management

### Database per Service

```mermaid
flowchart TD
    ORDER[Order Service] --> ORDER_DB[(Orders DB)]
    USER[User Service] --> USER_DB[(Users DB)]
    PAYMENT[Payment Service] --> PAYMENT_DB[(Payments DB)]
```

### Saga Pattern

```mermaid
sequenceDiagram
    participant O as Order Service
    participant P as Payment Service
    participant I as Inventory Service
    
    O->>P: Reserve payment
    P->>I: Reserve inventory
    I-->>O: Success
    O->>P: Confirm payment
    Note over O,I: If any step fails, compensate
```

### Event Sourcing

```mermaid
flowchart LR
    CMD[Command] --> AGG[Aggregate]
    AGG -->|Emit| EVENT[Event Store]
    EVENT -->|Project| PROJ[Read Model]
    EVENT -->|Replay| AGG
```

## Resilience Patterns

### Circuit Breaker

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open: Failures exceed threshold
    Open --> HalfOpen: Timeout expires
    HalfOpen --> Closed: Success
    HalfOpen --> Open: Failure
```

```python
class CircuitBreaker:
    def __init__(self, threshold=5, timeout=60):
        self.failures = 0
        self.threshold = threshold
        self.timeout = timeout
        self.state = "CLOSED"
        self.last_failure = 0
    
    def call(self, func, *args):
        if self.state == "OPEN":
            if time.time() - self.last_failure > self.timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitOpenError()
        
        try:
            result = func(*args)
            self.failures = 0
            self.state = "CLOSED"
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.threshold:
                self.state = "OPEN"
            raise
```

### Bulkhead

Isolate failures to prevent cascading. Use separate thread pools or connection pools per service.

### Retry with Exponential Backoff

```python
def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

## Service Mesh

```mermaid
flowchart LR
    subgraph "Service A"
        A[App] --> PA[Sidecar Proxy]
    end
    subgraph "Service B"
        B[App] --> PB[Sidecar Proxy]
    end
    PA -->|mTLS| PB
    PA --> CONTROL[Control Plane]
    PB --> CONTROL
```

**Features:** mTLS, traffic management, observability, canary deployments

## Interview Questions

1. **When to use microservices?** — Large team, different scaling needs, polyglot, independent deployment
2. **When NOT to use microservices?** — Small team, simple domain, tight coupling between features
3. **How to handle distributed transactions?** — Saga pattern (choreography or orchestration), eventual consistency
4. **API Gateway vs Service Mesh?** — Gateway: north-south (external). Service mesh: east-west (internal).
5. **How to handle service discovery?** — DNS, Consul, Kubernetes Services, etcd
6. **Strangler fig pattern?** — Incrementally migrate monolith to microservices by routing traffic to new services
7. **How to test microservices?** — Contract testing (Pact), integration tests, end-to-end tests
8. **Database per service — how to join data?** — API composition, CQRS, materialized views

## Related Topics

- [Docker](../containers/docker.md) — Containerization
- [Kubernetes](../containers/kubernetes.md) — Orchestration
- [Service Mesh](../containers/service-mesh.md) — Internal communication
- [Event-Driven](./event-driven.md) — Async patterns
- [Distributed Transactions](./distributed-transactions.md) — Cross-service consistency
