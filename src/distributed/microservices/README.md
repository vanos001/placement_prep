# Microservices Architecture

## Overview

Microservices is an architectural style where an application is built as a collection of **small, independent services** that communicate over the network. Each service is owned by a single team, can be deployed independently, and is organized around a business capability. This contrasts with monolithic architectures where the entire application is a single deployable unit.

## Monolith vs. Microservices

```mermaid
graph TD
    subgraph "Monolith"
        M[Single Application] --> UM[User Module]
        M --> OM[Order Module]
        M --> PM[Payment Module]
        M --> IM[Inventory Module]
        M --> DB[(Single Database)]
    end
    
    subgraph "Microservices"
        US[User Service] --> UDB[(User DB)]
        OS[Order Service] --> ODB[(Order DB)]
        PS[Payment Service] --> PDB[(Payment DB)]
        IS[Inventory Service] --> IDB[(Inventory DB)]
        
        US <-->|API| OS
        OS <-->|API| PS
        OS <-->|API| IS
    end
```

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Deployment** | Single unit | Independent per service |
| **Scaling** | Scale everything | Scale per service |
| **Technology** | Single stack | Polyglot |
| **Team** | Shared codebase | Team ownership |
| **Failure** | Entire app affected | Isolated failures |
| **Complexity** | Simple initially | Distributed complexity |

## Microservices Principles

```mermaid
graph TD
    P[Principles] --> S[Single Responsibility]
    P --> I[Independence]
    P --> D[Decentralization]
    P --> R[Resilience]
    P --> O[Observability]
    
    S --> S1["Each service does one thing well"]
    I --> I1["Deploy, scale, fail independently"]
    D --> D1["Decentralized data and governance"]
    R --> R1["Design for failure"]
    O --> O1["Monitor everything"]
```

## Communication Patterns

### Synchronous (Request-Response)

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API Gateway
    participant S1 as Service A
    participant S2 as Service B
    
    C->>A: HTTP Request
    A->>S1: Forward request
    S1->>S2: RPC call
    S2-->>S1: Response
    S1-->>A: Response
    A-->>C: Response
```

### Asynchronous (Event-Driven)

```mermaid
sequenceDiagram
    participant S1 as Service A
    participant Q as Message Queue
    participant S2 as Service B
    participant S3 as Service C
    
    S1->>Q: Publish event
    Q->>S2: Deliver event
    Q->>S3: Deliver event
    S2->>S2: Process independently
    S3->>S3: Process independently
```

### Comparison

| Aspect | Synchronous | Asynchronous |
|--------|------------|--------------|
| **Coupling** | Tight | Loose |
| **Latency** | Higher (waiting) | Lower (fire-and-forget) |
| **Error handling** | Immediate | Deferred |
| **Use case** | Queries, CRUD | Events, notifications |

## Data Management

### Database per Service

```mermaid
graph TD
    subgraph "Service A"
        SA[Service A Logic] --> DBA[(Database A)]
    end
    subgraph "Service B"
        SB[Service B Logic] --> DBB[(Database B)]
    end
    
    SA -->|"API call"| SB
```

### Saga Pattern (Distributed Transactions)

```mermaid
sequenceDiagram
    participant O as Order Service
    participant I as Inventory Service
    participant P as Payment Service
    
    O->>I: Reserve inventory
    I-->>O: Reserved
    
    O->>P: Process payment
    P-->>O: Payment failed!
    
    O->>I: Compensate: Release inventory
    I-->>O: Released
    
    Note over O: Order cancelled
```

## Service Mesh

```mermaid
graph TD
    subgraph "Service Mesh"
        S1[Service A] <--> P1[Sidecar Proxy A]
        S2[Service B] <--> P2[Sidecar Proxy B]
        S3[Service C] <--> P3[Sidecar Proxy C]
        
        P1 <--> P2
        P2 <--> P3
        P3 <--> P1
    end
    
    subgraph "Control Plane"
        CP[Control Plane] --> P1
        CP --> P2
        CP --> P3
    end
```

The sidecar proxies handle:
- Service discovery
- Load balancing
- Circuit breaking
- mTLS encryption
- Observability

## Deployment Patterns

### Blue-Green Deployment

```mermaid
graph LR
    LB[Load Balancer] -->|"Current"| B["Blue (v1)"]
    LB -.->|"Next"| G["Green (v2)"]
    
    Note["Switch traffic from Blue to Green"]
```

### Canary Deployment

```mermaid
graph LR
    LB[Load Balancer] -->|"90%"| V1[Version 1]
    LB -->|"10%"| V2[Version 2]
    
    Note["Gradually increase traffic to v2"]
```

### Rolling Deployment

```mermaid
graph TD
    subgraph "Step 1"
        I1[Instance 1: v2]
        I2[Instance 2: v1]
        I3[Instance 3: v1]
    end
    subgraph "Step 2"
        I4[Instance 1: v2]
        I5[Instance 2: v2]
        I6[Instance 3: v1]
    end
    subgraph "Step 3"
        I7[Instance 1: v2]
        I8[Instance 2: v2]
        I9[Instance 3: v2]
    end
```

## Challenges

```mermaid
graph TD
    C[Challenges] --> D[Distributed Complexity]
    C --> N[Network Issues]
    C --> DC[Data Consistency]
    C --> T[Testing]
    C --> O[Observability]
    
    D --> D1["Debugging, tracing"]
    N --> N1["Latency, failures"]
    DC --> DC1["Eventual consistency"]
    T --> T1["Integration testing"]
    O --> O1["Monitoring distributed systems"]
```

## Interview Questions

1. **What are microservices and how do they differ from monoliths?**
   - Microservices: small, independent services communicating over network. Each service has its own database and can be deployed independently. Monolith: single deployable unit with shared database.

2. **When would you choose microservices over a monolith?**
   - Microservices: large teams, need for independent deployment, polyglot technology, different scaling requirements. Monolith: small teams, simple domain, starting a new project.

3. **How do microservices communicate?**
   - Synchronous: HTTP/REST, gRPC (request-response). Asynchronous: message queues, event streaming (pub/sub). Each has trade-offs in coupling, latency, and error handling.

4. **What is the saga pattern?**
   - A distributed transaction pattern where each service performs its local transaction and publishes events. If one step fails, compensating transactions undo previous steps.

5. **What is a service mesh?**
   - Infrastructure layer that handles service-to-service communication. Sidecar proxies handle routing, load balancing, circuit breaking, and observability. Examples: Istio, Linkerd.

6. **What are the main challenges of microservices?**
   - Distributed complexity (debugging, tracing), network issues (latency, failures), data consistency (eventual consistency), testing (integration), and observability (monitoring).

## Common Mistakes

- Starting with microservices for a **new, small project** — monolith first
- **Too many services** — nano-services create unnecessary complexity
- **Shared databases** between services — defeats the purpose
- Not planning for **failure** — network calls will fail
- Ignoring **observability** — hard to debug without proper monitoring
- **Synchronous chains** — long chains of service calls amplify failures

## Summary

Microservices enable independent development, deployment, and scaling of services. They trade local complexity for distributed complexity. Key patterns include service discovery, circuit breakers, API gateways, and observability. The choice between monolith and microservices depends on team size, domain complexity, and operational maturity.

## Cross-References

- [Service Discovery](discovery.md) — Finding services
- [Circuit Breakers](circuit-breakers.md) — Handling failures
- [API Gateways](api-gateways.md) — Entry point for clients
- [Observability](observability.md) — Monitoring microservices
- [Message Queues](../messaging/queues.md) — Async communication
- [Pub/Sub](../messaging/pubsub.md) — Event-driven patterns

## Cross References

- [API Gateways](api-gateways.md)
- [Service Discovery](discovery.md)
- [Circuit Breakers](circuit-breakers.md)
- [Observability](observability.md)
- [Load Balancing](../../networks/load-balancing/README.md)
