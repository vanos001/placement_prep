# Linkerd Service Mesh

Linkerd is an open-source service mesh, originally developed by Buoyant in 2016 and donated to the CNCF (graduated in 2021). It is the simplest production-grade service mesh, with a focus on ease of use, performance, and Rust-based components. This page covers the architecture, the data plane (Linkerd2-proxy), the control plane, and the comparison to Istio.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Control Plane                                               │
│  - Destination service (configures sidecars)                 │
│  - Identity service (mTLS cert authority)                   │
│  - Proxy injector (mutating webhook)                       │
└─────────────────────────────────────────────────────────────┘
        │                              │
        │ gRPC                         │ cert distribution
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Pod A                │    │  Pod B                │
│  - Application         │    │  - Application        │
│  - Linkerd2-proxy      │    │  - Linkerd2-proxy     │
│    (Rust, ~10 MB)      │    │                       │
└──────────────────────┘    └──────────────────────┘
```

Linkerd's architecture is similar to Istio's (sidecar per pod, central control plane), but with key differences:
- The sidecar is **Linkerd2-proxy** (a.k.a. "the proxy"), a purpose-built Rust proxy, not Envoy.
- The control plane is simpler — fewer moving parts.

## The Linkerd2-Proxy

Linkerd2-proxy is a Rust-based L4/L7 proxy, purpose-built for the service mesh use case. Key features:
- **Smaller than Envoy**: ~10 MB binary vs Envoy's ~50 MB.
- **Lower memory**: ~10 MB per sidecar vs Envoy's ~50 MB.
- **Lower latency**: <1 ms per hop (Rust's zero-cost abstractions and no GC).
- **Limited protocols**: HTTP/1.1, HTTP/2, gRPC, TCP. (Envoy supports more.)
- **Limited extensibility**: no plugin system like Envoy's WASM filters.

```text
Linkerd2-proxy:
  - Reads config from the destination service via gRPC stream.
  - Maintains per-service routing tables.
  - mTLS to other proxies.
  - Emits metrics to Prometheus.
  - Emits traces to OpenTelemetry.
```

## The Control Plane

Linkerd's control plane has three main components:

### Destination Service

The destination service is the "brain" of Linkerd. It provides:
- Service discovery (which pods make up a service).
- Routing rules (from `ServiceProfile` resources).
- mTLS cert distribution.

```text
Proxy → destination service: "What's the address for service 'foo'?"
Destination service → proxy: ["10.0.0.1:8080", "10.0.0.2:8080", ...]
```

### Identity Service

The identity service is the mTLS certificate authority. It issues short-lived certs (default 24 hours) to each proxy. The proxy uses these certs for mTLS to other proxies.

The certs use SPIFFE IDs (same as Istio), allowing cross-mesh trust with other SPIFFE-compliant systems.

### Proxy Injector

A Kubernetes mutating webhook that injects the Linkerd2-proxy sidecar into pods. Triggered by namespace label `linkerd.io/inject=enabled`.

```bash
# Enable injection for a namespace
kubectl label namespace my-namespace linkerd.io/inject=enabled
```

## Traffic Management: ServiceProfiles

Linkerd's routing model is simpler than Istio's. `ServiceProfile` resources define per-service routing and retries:

```yaml
apiVersion: linkerd.io/v1alpha2
kind: ServiceProfile
metadata:
  name: my-service.my-namespace.svc.cluster.local
spec:
  routes:
    - name: get-items
      condition:
        method: GET
        pathRegex: /items/.*
      responseClasses:
        - condition:
            status:
              range: [500, 599]
          isFailure: true
  retryBudget:
    retryRatio: 0.2
    minRetriesPerSecond: 10
    ttl: 10s
```

This profile defines:
- A route for `GET /items/*`.
- 5xx responses are failures (eligible for retry).
- Retry budget: 20% of requests can be retries, min 10 retries/sec, budget expires in 10s.

Linkerd's model is simpler than Istio's VirtualService/DestinationRule; it focuses on retry and timeout, not complex routing.

## Observability

Linkerd automatically generates:
- **Per-service metrics**: request count, latency (P50, P95, P99), success rate. Exposed via Prometheus.
- **Per-pod metrics**: same, per pod.
- **Tap**: real-time inspection of traffic to a service (similar to `tcpdump` but at L7).

```bash
# Tap into traffic to a service
linkerd tap service my-service

# View service metrics
linkerd viz stat service my-service
```

Linkerd's "viz" CLI is a key differentiator — a one-line command to see a service's health.

## Production Performance

Linkerd's published overhead (per pod, sidecar proxy):
- **CPU**: ~5% of the pod's CPU.
- **Memory**: ~10 MB base.
- **Latency**: ~0.5 ms per hop (P99).
- **Throughput**: ~100K req/sec per sidecar.

For a 100-pod cluster, Linkerd's overhead is ~10 MB × 100 = 1 GB of proxy memory. Istio would be ~5 GB.

## Comparison to Istio

| Aspect | Linkerd | Istio |
|--------|---------|-------|
| Data plane | Linkerd2-proxy (Rust) | Envoy (C++) |
| Binary size | ~10 MB | ~50 MB |
| Memory per sidecar | ~10 MB | ~50 MB |
| Latency overhead | ~0.5 ms | ~1 ms |
| Feature richness | Essential | Rich |
| Extensibility | Limited | WASM filters, etc. |
| License | Apache 2.0 | Apache 2.0 |
| Best for | Simplicity, performance | Complex routing, policy |

Linkerd wins on simplicity and performance; Istio wins on features and ecosystem.

## Production Use Cases

### Simple mTLS + Observability

For a Kubernetes cluster that just needs mTLS between services and basic observability:

```bash
linkerd install | kubectl apply -f -
linkerd viz install | kubectl apply -f -

# Inject sidecars
kubectl label namespace my-apps linkerd.io/inject=enabled
```

That's it — mTLS, per-service metrics, and tracing are now active. No complex configuration.

### Multi-Cluster Communication

Linkerd's multi-cluster extension allows services in different clusters to communicate via mTLS:

```text
Cluster A: my-service → gateway → Cluster B: my-service
```

Each cluster has a "gateway" pod that forwards cross-cluster traffic. The mTLS certs are cross-trusted via a shared SPIFFE bundle.

### Canary Deployments

Linkerd integrates with Flagger and Argo Rollouts for automated canary:

```yaml
# Flagger with Linkerd
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: my-service
spec:
  serviceMeshProvider: linkerd
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-service
  progressDeadlineSeconds: 60
  service:
    port: 80
    targetPort: 8080
  analysis:
    interval: 30s
    threshold: 5
    metrics:
      - name: success-rate
        thresholdRange:
          min: 99
        query: |
          1 - (sum(rate(fl_linkerd_request_total{status_classification="failure", deployment="{{ $targetRef }}" }[30s])) / sum(rate(fl_linkerd_request_total{deployment="{{ $targetRef }}" }[30s])))
```

Flagger shifts traffic to the canary; Linkerd provides the metrics. If success rate drops, Flagger rolls back.

## Common Pitfalls

1. **Forgetting that Linkerd2-proxy doesn't support all Envoy features.** If you need Envoy's WASM filters or HTTP/3, Linkerd isn't the right choice.

2. **Forgetting that ServiceProfiles are per-service, not per-route.** A complex routing topology (multiple paths, multiple services) requires many ServiceProfiles.

3. **Forgetting that the proxy injector is namespace-level.** Per-pod injection requires annotation; per-namespace is the default.

4. **Forgetting that Linkerd's tap may leak sensitive data.** Real-time inspection sees request bodies (if HTTP). Restrict `linkerd tap` access.

5. **Forgetting that multi-cluster requires the gateway component.** Without it, cross-cluster mTLS doesn't work.

6. **Forgetting that Linkerd doesn't support L7 policy by default.** Authorization is at L4 (source IP / port). For L7 policy (e.g., per-path), use the policy extension.

## References

- [Linkerd documentation](https://linkerd.io/2/overview/)
- [Linkerd GitHub repository](https://github.com/linkerd/linkerd2)
- [Linkerd2-proxy source code](https://github.com/linkerd/linkerd2-proxy)
- Buoyant, "[Linkerd2: The service mesh for Kubernetes](https://buoyant.io/2020/12/10/linkerd-2-10)" (2020)
- [Linkerd vs Istio comparison (Buoyant)](https://linkerd.io/istio-vs-linkerd/)
- [Linkerd: Production deployments (Linkerd blog)](https://linkerd.io/2021/01/11/production-deployments/)
- [LWN: Linkerd overview (2021)](https://lwn.net/Articles/856775/)
