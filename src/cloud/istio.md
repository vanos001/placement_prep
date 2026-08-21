# Istio Service Mesh

Istio is an open-source service mesh, originally developed by Google, IBM, and Lyft in 2017 and donated to the CNCF. It uses Envoy as its data plane (one sidecar per pod) and provides traffic management, security, observability, and policy enforcement for microservices. This page covers the architecture, the sidecar injection model, the traffic management features, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Control Plane (istiod)                                     │
│  - Pilot: configures Envoy sidecars via xDS                 │
│  - Citadel: mTLS certificate management (now part of istiod)│
│  - Galley: config validation (now part of istiod)            │
└─────────────────────────────────────────────────────────────┘
        │                              │
        │ xDS (gRPC)                  │ cert distribution
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Pod A                │    │  Pod B                │
│  - Application         │    │  - Application        │
│  - Envoy sidecar       │    │  - Envoy sidecar      │
└──────────────────────┘    └──────────────────────┘
        │                              │
        └────── mTLS traffic ─────────┘
```

The control plane (istiod, a single binary since Istio 1.5) manages all sidecars in the mesh via xDS APIs. Each pod has an Envoy sidecar that intercepts inbound and outbound traffic.

## Sidecar Injection

Istio's sidecar injection uses Kubernetes mutating admission webhooks:

```yaml
# Pod with istio-injection=enabled
apiVersion: v1
kind: Pod
metadata:
  name: my-app
  labels:
    app: my-app
  annotations:
    sidecar.istio.io/inject: "true"
spec:
  containers:
    - name: my-app
      image: my-app:latest
    # (Istio's webhook injects the Envoy sidecar here)
    - name: istio-proxy
      image: docker.io/istio/proxyv2:1.21.0
      ...
```

Namespace-level injection: any namespace labeled `istio-injection=enabled` has sidecars auto-injected.

The injection process:
1. K8s admission webhook is called on Pod creation.
2. Istio's webhook adds the `istio-proxy` container, the `istio-init` init container, and necessary volumes.
3. The init container sets up iptables to redirect traffic to the Envoy sidecar.
4. The Pod runs with traffic transparently redirected.

## Traffic Management

Istio provides a virtual service + destination rule model:

```yaml
# VirtualService: routing rules
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: my-service
spec:
  hosts:
    - my-service
  http:
    - match:
        - uri:
            prefix: "/v1"
      route:
        - destination:
            host: my-service
            subset: v1
    - route:
        - destination:
            host: my-service
            subset: v2
          weight: 10
        - destination:
            host: my-service
            subset: v1
          weight: 90

# DestinationRule: load balancing + subsets
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata:
  name: my-service
spec:
  host: my-service
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
  trafficPolicy:
    loadBalancer:
      simple: LEAST_REQUEST
```

This enables:
- **Canary deployments**: 10% of traffic to v2, 90% to v1.
- **Path-based routing**: `/v1/*` to v1, else default.
- **Load balancing**: least-request algorithm.

## Security: mTLS

Istio automatically establishes mTLS between sidecars:

```text
Pod A's Envoy  ──── mTLS ────  Pod B's Envoy

The sidecars:
  1. Use SPIFFE to verify each other's identity.
  2. Encrypt traffic with TLS 1.3.
  3. Rotate certs hourly.
```

The certs are issued by istiod, which acts as a SPIFFE-compatible CA. Each pod has a SPIFFE ID derived from its service account and namespace.

Authorization policies:

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata:
  name: my-service-policy
spec:
  selector:
    matchLabels:
      app: my-service
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/default/sa/frontend"]
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/api/*"]
```

This policy: only the `frontend` service account can call `my-service`, and only via GET/POST to `/api/*`.

## Observability

Istio automatically generates:
- **Metrics**: per-request latency, error rate, request count. Exposed via Prometheus.
- **Distributed tracing**: Zipkin/Jaeger spans for each hop.
- **Access logs**: per-sidecar request logs.

```yaml
# Telemetry configuration
apiVersion: telemetry.istio.io/v1
kind: Telemetry
metadata:
  name: default
spec:
  accessLogging:
    - providers:
        - name: otel
  tracing:
    - providers:
        - name: otel
```

## Production Performance

Istio's published overhead (per pod, sidecar Envoy):
- **CPU**: ~10% of the pod's CPU.
- **Memory**: ~50 MB base + ~10 KB per connection.
- **Latency**: ~1 ms added per hop (P99).
- **Throughput**: ~100K req/sec per sidecar.

For a 100-pod cluster, Istio's overhead is ~50 MB × 100 = 5 GB of Envoy memory.

## Istio Ambient Mode (1.22+)

A newer deployment mode (ambient, announced 2023, GA in 2024):
- Replaces per-pod sidecars with per-node Envoy (ztunnel for L4 mTLS).
- Per-namespace L7 Envoy (waypoint) for routing and policy.
- Reduces sidecar memory footprint dramatically.

```text
Pod (no sidecar)
   │
   ▼
Node's ztunnel (mTLS)
   │
   ▼ (for L7 features)
Waypoint Envoy (routing, policy)
   │
   ▼
Target pod
```

Ambient mode is the future of Istio for most deployments; the sidecar model remains for compatibility.

## Common Pitfalls

1. **Forgetting that sidecars need to be re-injected on Istio upgrade.** Old sidecars running with a new istiod may have config drift. Use `istioctl kube-inject` to update.

2. **Forgetting that mTLS requires SPIFFE.** A pod without a service account can't have a SPIFFE ID and can't do mTLS. Always set service accounts explicitly.

3. **Forgetting that the sidecar intercepts all traffic.** If the application makes external HTTP calls (e.g., to a third-party API), the sidecar applies the same rules. Use `ServiceEntry` to add external services to the mesh.

4. **Forgetting that VirtualService rules are processed in order.** The first matching rule wins; order matters.

5. **Forgetting that the Envoy sidecar uses significant memory.** For very small pods (10 MB), the sidecar's 50 MB is significant overhead. Use ambient mode if available.

6. **Forgetting that authorization policies are DENY by default.** With `action: ALLOW`, only the specified traffic is allowed; everything else is denied. Be careful with `deny` rules.

## Comparison to Other Service Meshes

| Aspect | Istio | Linkerd | Consul Connect | AWS App Mesh |
|--------|-------|---------|-----------------|---------------|
| Data plane | Envoy | Linkerd2-proxy (Rust) | Envoy | Envoy |
| License | Apache 2.0 | Apache 2.0 | MPL 2.0 | AWS proprietary |
| Feature set | Richest | Essential | Medium | Limited |
| Complexity | High | Low | Medium | Medium |
| Best for | Enterprise | Simple deployments | Hybrid infra | AWS-only |

Istio has the richest features; Linkerd is simpler; Consul works in non-K8s environments; App Mesh is for AWS-only deployments.

## References

- [Istio documentation](https://istio.io/latest/docs/)
- [Istio GitHub repository](https://github.com/istio/istio)
- [Istio Ambient mode](https://istio.io/latest/blog/2023/ambient-reached-beta/)
- [Istio Performance benchmarks](https://istio.io/latest/docs/ops/deployment/performance-and-scalability/)
- [Bookinfo (Istio's canonical demo app)](https://istio.io/latest/docs/examples/bookinfo/)
- [Linkerd vs Istio comparison](https://linkerd.io/istio-vs-linkerd/)
- [LWN: Istio overview (2022)](https://lwn.net/Articles/856675/)
