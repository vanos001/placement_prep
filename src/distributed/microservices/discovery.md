# Service Discovery

## Overview

Service discovery is the mechanism by which services in a distributed system **find and communicate with each other**. In microservices architectures, where services are dynamically deployed, scaled, and replaced, hardcoded addresses don't work. Service discovery provides a registry where services register themselves and look up other services.

## The Problem

```mermaid
graph TD
    subgraph "Hardcoded Addresses (Doesn't Scale)"
        S1["Service A\n(config: service-b:8080)"] --> S2["Service B"]
        S1 -.->|"IP changed!"| X[Connection Failed]
    end
    
    subgraph "Service Discovery"
        S3[Service A] --> R[Registry]
        S4[Service B] --> R
        S3 -->|"Lookup service-b"| R
        R -->|"Return address"| S3
        S3 -->|"Connect"| S4
    end
```

## Service Discovery Patterns

### Client-Side Discovery

```mermaid
sequenceDiagram
    participant C as Client Service
    participant R as Service Registry
    participant S as Target Service
    
    S->>R: Register (service-b, 10.0.0.2:8080)
    
    C->>R: Where is service-b?
    R-->>C: 10.0.0.2:8080
    C->>S: Request (directly)
    S-->>C: Response
```

**Pros**: Client can implement custom load balancing
**Cons**: Client coupled to registry; logic in every service

### Server-Side Discovery

```mermaid
sequenceDiagram
    participant C as Client Service
    participant LB as Load Balancer
    participant R as Service Registry
    participant S as Target Service
    
    S->>R: Register (service-b, 10.0.0.2:8080)
    
    C->>LB: Request for service-b
    LB->>R: Where is service-b?
    R-->>LB: 10.0.0.2:8080
    LB->>S: Forward request
    S-->>LB: Response
    LB-->>C: Response
```

**Pros**: Client is simple; central load balancing
**Cons**: Extra hop; LB is a potential bottleneck

## Registration Methods

### Self-Registration

```mermaid
graph TD
    S[Service] -->|"Register on startup"| R[Registry]
    S -->|"Heartbeat"| R
    S -->|"Deregister on shutdown"| R
```

### Third-Party Registration

```mermaid
graph TD
    S[Service] --> D[Deployer/Orchestrator]
    D -->|"Register on behalf"| R[Registry]
    D -->|"Deregister on stop"| R
```

## Health Checking

```mermaid
graph TD
    subgraph "Push-based (Heartbeat)"
        S1[Service] -->|"I'm alive!"| R[Registry]
        Note1["Service sends heartbeat"]
    end
    
    subgraph "Pull-based (Health Check)"
        R2[Registry] -->|"GET /health"| S2[Service]
        S2 -->|"200 OK"| R2
        Note2["Registry polls services"]
    end
```

| Method | Pros | Cons |
|--------|------|------|
| **Push** | Low latency detection | Service must be configured |
| **Pull** | Centralized control | Polling interval = detection delay |

## Service Discovery Tools

### Consul

```mermaid
graph TD
    subgraph "Consul Cluster"
        C1[Consul Server 1] <--> C2[Consul Server 2]
        C2 <--> C3[Consul Server 3]
        C3 <--> C1
    end
    
    subgraph "Services"
        S1[Service A] --> AG1[Consul Agent]
        S2[Service B] --> AG2[Consul Agent]
        AG1 --> C1
        AG2 --> C2
    end
```

**Features**: Service discovery, health checking, KV store, multi-datacenter

```bash
# Register service
curl -X PUT http://localhost:8500/v1/agent/service/register \
  -d '{"name": "web", "port": 8080, "check": {"http": "http://localhost:8080/health", "interval": "10s"}}'

# Discover service
curl http://localhost:8500/v1/catalog/service/web
```

### Eureka

```mermaid
graph TD
    subgraph "Eureka Server Cluster"
        E1[Eureka Server 1] <--> E2[Eureka Server 2]
    end
    
    subgraph "Services"
        S1[Service A] --> E1
        S2[Service B] --> E2
        S3[Service C] --> E1
    end
```

**Features**: Service discovery, health checking, REST-based

```java
// Registration (Spring Boot)
@SpringBootApplication
@EnableEurekaClient
public class ServiceAApplication { }

// Discovery
@Autowired
private DiscoveryClient discoveryClient;

List<ServiceInstance> instances = 
    discoveryClient.getInstances("service-b");
```

### etcd / ZooKeeper

```mermaid
graph TD
    subgraph "etcd/ZooKeeper"
        K["/services/web/instance-1\n10.0.0.1:8080"]
        K2["/services/web/instance-2\n10.0.0.2:8080"]
    end
    
    S1[Service] -->|"Watch key"| K
    S2[Service] -->|"Register"| K2
```

**Features**: Distributed KV store, strong consistency, watches

## DNS-Based Discovery

```mermaid
graph LR
    C[Client] -->|"web.service.local"| DNS[DNS Server]
    DNS -->|"10.0.0.1, 10.0.0.2"| C
    C -->|"Connect"| S1[Service Instance 1]
```

```bash
# SRV record for service discovery
_web._tcp.service.local.  IN SRV 0 0 8080 instance1.service.local.
_web._tcp.service.local.  IN SRV 0 0 8080 instance2.service.local.
```

**Pros**: Works with any language; no SDK needed
**Cons**: DNS caching; TTL-based updates are slow

## Comparison

| Tool | Consistency | Health Check | KV Store | Multi-DC |
|------|------------|--------------|----------|----------|
| **Consul** | Strong (Raft) | Yes | Yes | Yes |
| **Eureka** | Eventual | Yes | No | No |
| **etcd** | Strong (Raft) | TTL-based | Yes | No |
| **ZooKeeper** | Strong (ZAB) | Session-based | Yes | No |
| **DNS** | N/A | No | No | Yes |

## Kubernetes Service Discovery

```mermaid
graph TD
    subgraph "Kubernetes"
        S[Service: web] --> P1[Pod 1: 10.0.0.1]
        S --> P2[Pod 2: 10.0.0.2]
        S --> P3[Pod 3: 10.0.0.3]
        
        C[Client Pod] -->|"web.default.svc.cluster.local"| S
    end
```

```yaml
# Service definition
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
---
# DNS: web.default.svc.cluster.local
```

## Interview Questions

1. **What is service discovery and why is it needed?**
   - The mechanism for services to find each other dynamically. Needed because in microservices, services are deployed, scaled, and replaced dynamically — hardcoded addresses don't work.

2. **What is the difference between client-side and server-side discovery?**
   - Client-side: client queries registry and connects directly (custom load balancing). Server-side: client goes through a load balancer that queries registry (simpler client).

3. **How does Consul handle service discovery?**
   - Services register with Consul agents. Agents perform health checks. Clients query Consul for healthy instances. Consul uses Raft for strong consistency and supports multi-datacenter replication.

4. **What is the role of health checking in service discovery?**
   - Ensures only healthy instances are returned. Push-based: services send heartbeats. Pull-based: registry polls health endpoints. Unhealthy instances are removed from the registry.

5. **How does Kubernetes handle service discovery?**
   - Kubernetes provides built-in service discovery through Services and DNS. Each service gets a DNS name (web.default.svc.cluster.local). kube-proxy handles routing to healthy pods.

## Common Mistakes

- Not implementing **health checks** — registry returns dead instances
- Using **DNS without low TTL** — stale records cause connection failures
- Not handling **registry failures** — service discovery becomes a single point of failure
- **Hardcoding** service addresses in configuration
- Not considering **multi-datacenter** scenarios
- Forgetting about **client-side caching** — reduces registry load but may return stale data

## Summary

Service discovery enables dynamic communication between microservices. Client-side discovery gives clients control over load balancing; server-side discovery simplifies clients. Tools like Consul, Eureka, etcd, and Kubernetes provide different trade-offs in consistency, features, and complexity. Health checking ensures only healthy instances are discoverable.

## Cross-References

- [Microservices Overview](README.md) — Microservices architecture
- [Circuit Breakers](circuit-breakers.md) — Handling service failures
- [API Gateways](api-gateways.md) — Entry point for clients
- [Observability](observability.md) — Monitoring services
- [Consensus Algorithms](../consensus/README.md) — Used by Consul, etcd
- [Consistent Hashing](../partitioning/consistent-hashing.md) — Load balancing
