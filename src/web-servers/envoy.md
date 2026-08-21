# Envoy Proxy

Envoy is an open-source layer 7 (L7) network proxy and communication bus, originally developed at Lyft in 2016 and donated to the CNCF (becoming a graduated project in 2018). It is the data plane for service meshes (Istio, Consul, AWS App Mesh) and API gateways (Ambassador, Gloo). Envoy is written in C++ and optimized for high-throughput, observability, and extensibility. This page covers the architecture, the filter chain, the xDS configuration API, and the production deployment patterns.

## The Architecture

```text
┌────────────────────────────────────────────────────────────────┐
│  Envoy Process (single process, multi-threaded)                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Main thread (config + control)                            │ │
│  │  - Listens to xDS for config updates                       │ │
│  │  - Manages worker threads                                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Worker thread 1 (one per core)                            │ │
│  │  - Owns a set of connections                                │ │
│  │  - Filter chain for each connection                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Worker thread 2                                            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  ...                                                            │
└────────────────────────────────────────────────────────────────┘
```

Envoy uses an event loop (libevent) per worker thread. Connections are assigned to worker threads (sticky), avoiding cross-thread synchronization.

## The Filter Chain

Envoy's core abstraction is the **filter chain**. Each connection has a sequence of filters that process the data:

```text
Connection (incoming bytes)
   │
   ▼
Network filters (L4):
   - Listener filter (e.g., TLS inspector, original_dst)
   - Proxy protocol filter
   - Tcp proxy (or HTTP connection manager)
   │
   ▼
HTTP filters (L7):
   - Router (path-based routing)
   - Rate limit filter
   - JWT authentication filter
   - RBAC filter
   - Compression filter (gzip/brotli)
   - CORS filter
   - ...
   │
   ▼
Upstream (outgoing bytes)
```

Filters are pluggable. The configuration determines which filters run and in what order. Custom filters can be written in C++ or compiled as WASM.

## The xDS Configuration API

Envoy's configuration is managed by the **xDS** (Discovery Service) protocol. The control plane (e.g., Istio's istiod) pushes config updates to Envoy via gRPC streams:

- **LDS (Listener Discovery Service)**: defines listeners (ports to listen on).
- **RDS (Route Discovery Service)**: defines routes (path/host → cluster).
- **CDS (Cluster Discovery Service)**: defines clusters (groups of upstream endpoints).
- **EDS (Endpoint Discovery Service)**: defines endpoints (IP addresses in a cluster).
- **SDS (Secret Discovery Service)**: defines TLS certs/keys.
- **VHDS (Virtual Host Discovery Service)**: dynamically grows route configs.

```text
Control Plane (Istio, etc.)
   │ gRPC streams (xDS)
   ▼
Envoy data plane
```

The xDS API allows hot-reloading of config without restarting Envoy. A config change in the control plane is reflected in all Envoy proxies within seconds.

## Observability: Stats, Tracing, Logging

Envoy exposes rich observability:

- **Stats**: counters, gauges, histograms for every connection, request, and cluster. Exposed via `/stats` endpoint (Prometheus format).
- **Tracing**: spans are emitted to Zipkin, Jaeger, Datadog, or OpenTelemetry.
- **Access logging**: per-request logs in customizable format (JSON, LTSV).

```yaml
# Stats configuration
stats_sinks:
  - name: envoy.statsd
    typed_config:
      "@type": type.googleapis.com/envoy.config.stats.v3.StatsdSink
      address: { socket_address: { address: "statsd", port_value: 8125 } }

# Tracing
tracing:
  provider:
    name: envoy.tracers.zipkin
    typed_config:
      "@type": type.googleapis.com/envoy.config.trace.v3.ZipkinConfig
      collector_cluster: jaeger
      collector_endpoint: /api/v2/spans
      trace_id_128bit: true
```

## Production Patterns

### Pattern 1: Service Mesh Sidecar

The most common Envoy deployment: a sidecar proxy per service in a Kubernetes pod:

```text
┌──────────────────────────────┐
│  Pod                          │
│  ┌────────────────────────┐  │
│  │  Application container  │  │
│  │  Listens on :8080       │  │
│  └────────────────────────┘  │
│             ↑                  │
│             │ localhost:8080  │
│             ▼                  │
│  ┌────────────────────────┐  │
│  │  Envoy sidecar          │  │
│  │  Listens on :15001      │  │
│  │  (intercepts all traffic)│  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

The sidecar intercepts all inbound and outbound traffic, applying:
- mTLS for service-to-service auth.
- Routing to other services.
- Rate limiting.
- Observability (stats, tracing).

Istio, Linkerd, and AWS App Mesh use this pattern.

### Pattern 2: API Gateway

Envoy as an edge proxy:

```text
Internet → Envoy (port 443, TLS termination)
            │
            ├── /api/v1/* → backend-service-1
            ├── /api/v2/* → backend-service-2
            ├── /admin/*  → admin-service (with JWT auth)
            └── /        → static-content-service
```

Ambassador and Gloo are API gateways built on Envoy.

### Pattern 3: Internal Load Balancer

Envoy as an internal L7 load balancer:

```text
Service A → Envoy → Service B (3 replicas)
                 → Service B' (3 replicas)
                 → Service B'' (3 replicas)
```

Envoy handles:
- Health checks (remove failed endpoints).
- Load balancing (round-robin, random, least-request).
- Retries (retry on 5xx).
- Timeouts.
- Circuit breaking (stop sending to failing endpoints).

## Production Performance

Envoy's published performance numbers (single Envoy process, 8 cores):

| Metric | Value |
|--------|-------|
| HTTP/1.1 throughput (small requests) | 100K req/sec |
| HTTP/2 throughput | 200K req/sec |
| TCP throughput (no L7) | 100 Gbps |
| Latency added (P99) | 0.5 ms |
| Memory per connection | 5-10 KB |

Envoy's overhead is small enough to be invisible for most workloads; the observability and reliability gains dominate.

## Comparison to Nginx and HAProxy

| Aspect | Envoy | Nginx | HAProxy |
|--------|-------|-------|---------|
| Origin | Lyft 2016 | 2002 | 2001 |
| Language | C++ | C | C |
| L7 protocols | HTTP/1.1, HTTP/2, HTTP/3, gRPC, TCP, MongoDB, MySQL, Redis, PostgreSQL, Thrift | HTTP/1.1, HTTP/2, HTTP/3, TCP, UDP | HTTP/1.1, HTTP/2, TCP |
| Dynamic config | xDS (gRPC streams) | Reload on config change | Runtime API (less rich) |
| Service mesh integration | First-class (Istio data plane) | None | None |
| Observability | Built-in stats, tracing, access logs | Requires 3rd-party modules | Limited |
| Best for | Service mesh, dynamic routing | Edge proxy, content serving | L4 load balancing |

Envoy's advantage is dynamic config and rich observability. Nginx's advantage is mature ecosystem and content serving. HAProxy's advantage is simplicity and L4 performance.

## Common Pitfalls

1. **Forgetting to set `concurrency` correctly.** Default is the number of CPU cores; for high-throughput, more worker threads can help (up to 16). For latency, fewer is better.

2. **Forgetting to tune timeouts.** Envoy's default idle timeout is 1 hour; for high-throughput, 60 seconds is more appropriate.

3. **Forgetting the resource overhead.** A sidecar Envoy uses ~50 MB RAM per pod. On a 100-pod cluster, that's 5 GB of Envoy.

4. **Forgetting that Envoy's xDS updates take time.** Config changes propagate within seconds; if you need instant, use a static config.

5. **Forgetting that custom filters need a stable Envoy version.** A custom filter compiled against Envoy 1.20 may not work with 1.25.

6. **Forgetting that Envoy's hot restart has a small downtime.** Hot restart swaps listeners, but there's a ~100 ms window where requests may fail. Use multiple Envoy replicas for HA.

## References

- [Envoy documentation](https://www.envoyproxy.io/docs)
- [Envoy GitHub repository](https://github.com/envoyproxy/envoy)
- Matt Klein (Lyft), "[Envoy: An Open-Source L7 Proxy and Communication Bus](https://eng.lyft.com/announcing-envoy-proxy-3b013f5d56a7)" (2016)
- [xDS protocol documentation](https://www.envoyproxy.io/docs/envoy/latest/api-docs/xds_protocol)
- [Istio architecture (Envoy as data plane)](https://istio.io/latest/docs/ops/deployment/architecture/)
- [Envoy vs Nginx vs HAProxy (Cloud Native Computing Foundation)](https://www.cncf.io/blog/2020/11/04/envoy-vs-nginx-vs-haproxy/)
- [LWN: Envoy internals (2020)](https://lwn.net/Articles/816455/)
