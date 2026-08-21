# Sidecar and Ambassador Patterns

The **Sidecar** pattern places a helper process alongside the application process in the same host (today: the same pod). The helper provides a cross-cutting concern — logging, metrics, configuration, proxying — so the application doesn't have to implement it. The **Ambassador** pattern is the same idea applied to a specific concern: an out-of-process proxy that sits between the application and an external dependency, giving the application a stable local interface while the proxy handles connection pooling, failover, TLS, and protocol translation. Both patterns are catalogued by the Microsoft Azure Architecture Center.

## The Sidecar pattern

A sidecar runs in the same runtime environment as the application but in a separate process or container. It shares the network namespace (often the filesystem, with limits) so it can observe the application's traffic, but it has its own lifecycle, language, and dependencies. The application knows nothing about the sidecar's internals; the sidecar knows nothing about the application's business logic.

```
   ┌──────────────────────────────────┐
   │              Pod                 │
   │                                  │
   │   ┌─────────────────────────┐    │
   │   │  Application container   │    │
   │   │   (Python/Go/Node)       │    │
   │   └────────────┬────────────┘    │
   │                │ localhost:9000   │
   │   ┌────────────▼────────────┐    │
   │   │  Sidecar container       │    │
   │   │  (Envoy / fluent-bit)    │    │
   │   └────────────┬────────────┘    │
   │                │                  │
   └────────────────┼──────────────────┘
                    │
                    ▼
              external services
```

Three things make a process a sidecar:

1. **Co-located**: same host/pod, shared network namespace (so the app can talk to the sidecar on `localhost`).
2. **Co-lifecycle**: started and stopped with the application.
3. **Heterogeneous**: written in a different language/stack than the application — that's the whole point, the sidecar does something the application shouldn't.

### What sidecars do

Common sidecar roles:

| Role | Example | Why sidecar |
|---|---|---|
| Log shipper | `fluent-bit`, `filebeat` | App shouldn't implement log forwarding |
| Metrics exporter | `prometheus/exporter` | Standardized scrape endpoint |
| Proxy / mesh | `Envoy`, `linkerd-proxy` | App gets mTLS, retries, circuit breaking for free |
| Config reloader | `configmap-reload` | App doesn't reload; sidecar sends signal |
| Auth helper | `oauth2-proxy` | App gets an `X-User` header; sidecar handles OIDC |

### A concrete sidecar: config-reloader

A pattern that exists in nearly every Kubernetes deployment: the application reads a config file on disk; a ConfigMapReloader sidecar watches a Kubernetes ConfigMap, writes the file when it changes, and sends `SIGHUP` to the application (or hits its reload endpoint).

```yaml
# Kubernetes pod with a reloader sidecar
apiVersion: v1
kind: Pod
metadata:
  name: app-with-reloader
spec:
  containers:
    - name: app
      image: my-app:1.2.3
      volumeMounts:
        - name: config
          mountPath: /etc/app
      lifecycle:
        preStop:
          exec: { command: ["/app", "drain"] }
    - name: config-reloader
      image: ghcr.io/jimmidyson/configmapreload:v0.7.1
      args:
        - --volume-dir=/etc/app
        - --webhook-url=http://localhost:8080/-/reload
      volumeMounts:
        - name: config
          mountPath: /etc/app
  volumes:
    - name: config
      configMap: { name: app-config }
```

The application container never knows that Kubernetes exists. The sidecar handles the platform integration. This is the strength of the pattern: the application code stays portable; the sidecar knows the platform. The same application container runs in dev (no sidecar, config read from local file) and in prod (with sidecar, config refreshed from the cluster).

### A logging sidecar

The classic logging sidecar: `fluent-bit` runs as a sidecar, tails the app's log file (shared via emptyDir volume), parses and ships to Elasticsearch/Loki/S3. The application writes plain stdout or a plain file in a known format; the sidecar does the parsing, batching, retries, and credential management for the log sink.

```
   ┌───────────────────────────────────────┐
   │                  Pod                  │
   │  /var/log/app (emptyDir volume)        │
   │                                       │
   │  ┌──────────────┐    ┌────────────┐   │
   │  │ Application   │───▶│ fluent-bit │   │
   │  │ writes logs   │    │  sidecar   │   │
   │  └──────────────┘    └─────┬──────┘   │
   └────────────────────────────┼──────────┘
                                │
                                ▼
                            Loki / ES
```

The app has no log shipper library, no client credentials, no batching code. The sidecar owns all of that. If you switch from Loki to Datadog, you swap the sidecar image; the application is rebuilt for unrelated reasons only.

## The Ambassador pattern

The Ambassador is a specific kind of sidecar: a proxy that sits between the application and an **external dependency**, giving the application a stable local interface. The name comes from the diplomatic role: the ambassador handles the relationship with a foreign power so the home country's leader (your application) doesn't have to.

Classic example: an application needs to talk to a Redis cluster. Redis clusters have multiple nodes, a slot-based sharding scheme (CRC16 of key mod 16384), and node-level failover. Implementing cluster client logic in every language and every application is repetitive and error-prone. The ambassador pattern: run `envoy` (or `twemproxy`, `mcrouter`, `haproxy`) as a sidecar; the app talks to `localhost:6379`; the sidecar handles the cluster topology, failover, and connection pooling.

```
   ┌──────────────────────────────────────────┐
   │                   Pod                    │
   │                                          │
   │  ┌──────────────┐    ┌────────────────┐  │
   │  │ Application   │    │ Ambassador     │  │
   │  │  redis-cli    │───▶│ (twemproxy /   │  │
   │  │  → localhost  │    │  envoy / etc)  │  │
   │  └──────────────┘    └────────┬───────┘  │
   └───────────────────────────────┼──────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
         Redis Node 1        Redis Node 2         Redis Node 3
         (slots 0-5460)      (slots 5461-10922)   (slots 10923-16383)
```

The application sees a single-host Redis. Failover, slot migration, and node health are managed by the ambassador, which can be updated independently of the application.

### When to use an ambassador

- **You're integrating with a legacy system that requires complex client logic** (e.g., a sharded DB, a service requiring mTLS with cert rotation, a service that needs request hedging).
- **Your application language lacks a good client for the dependency** (e.g., your team writes Python; the dependency needs a Java-only client).
- **You want to keep the application language-agnostic**: the app uses a standard protocol (Redis RESP, HTTP, Thrift), the ambassador handles the proprietary stuff.

### Ambassador as legacy integration

When the application cannot be modified (third-party binary, mainframe connector) but needs to talk to a modern service, the ambassador is the bridge. The unmodified app talks its old protocol to `localhost:port`; the ambassador translates to the modern protocol and forwards. This is the ambassador pattern's role in Strangler Fig migrations: the legacy app thinks it is talking to the old mainframe; the ambassador translates the call to the new gRPC service.

```
   ┌──────────────────────────────────────────┐
   │                   Pod                    │
   │                                          │
   │  ┌──────────────┐    ┌────────────────┐  │
   │  │ Legacy app    │    │ Ambassador      │  │
   │  │ (unmodified)  │───▶│ (protocol       │  │
   │  │ talks SOAP     │    │  translator)    │  │
   │  │ localhost:8080│    └────────┬───────┘  │
   └───────────────────────────────┼──────────┘
                                   │
                                   ▼  gRPC / HTTPS
                            New modern service
```

## Comparison to service mesh sidecars (Istio / Envoy)

A service mesh is the most common form of sidecar in production today. Istio (the most popular mesh) injects an Envoy proxy as a sidecar into every pod in the mesh. The application's outbound traffic is transparently redirected to the local Envoy, which handles mTLS, retries, circuit breaking, load balancing, and emits telemetry.

This is a specific instance of the sidecar pattern with two distinguishing properties:

1. **Transparent interception**: the application doesn't know Envoy is there. iptables rules in the pod's network namespace redirect outbound traffic to the local Envoy. The application "calls" `http://orders-service/`, the local Envoy intercepts, picks a healthy instance, does mTLS, and forwards.
2. **Control plane**: hundreds of Envoy sidecars are configured by a central control plane (Istiod) using a single set of traffic rules. Operators define "1% of traffic to v2" once; the control plane pushes the config to every sidecar.

```
   ┌─────────────────────────────────────────────┐
   │                   Pod                       │
   │  iptables: all outbound → 15001 (Envoy)     │
   │                                             │
   │  ┌──────────────┐         ┌──────────────┐  │
   │  │ Application   │ ──out──▶│ Envoy sidecar│  │
   │  │ (unmodified)  │◀──in─── │ mTLS, retry  │  │
   │  └──────────────┘         └──────┬───────┘  │
   └─────────────────────────────────┼───────────┘
                                     │
                                     ▼
                              target service
                              (also has Envoy)
                                     │
                                     ▼
                         Istiod (control plane)
                         pushes config to all
```

A non-mesh sidecar differs in two ways: it is **opt-in** (the application explicitly talks to the sidecar) and **per-application** (no central control plane).

| Aspect | Plain sidecar | Service mesh sidecar |
|---|---|---|
| Application awareness | Often explicit (localhost:port) | Transparent (iptables) |
| Control plane | None | Central (Istiod, Consul, Linkerd) |
| Scope | One application's concern | All services in the mesh |
| mTLS | App-protocol specific | Universal (any TCP) |
| Telemetry | Sidecar-specific format | Standardized (W3C trace context, OpenMetrics) |
| Operational cost | Low | High (control plane, version skew, upgrades) |

## Pros and cons

### Pros

- **Language-agnostic cross-cutting concerns.** A Java shop and a Go shop can both use the same Envoy sidecar for mTLS, without writing it in both languages.
- **Application code stays portable.** The app's logic is unaware of the platform; the sidecar handles platform specifics. The same application container runs in dev (no sidecar) and prod (with sidecar).
- **Independent upgrade.** The sidecar can be patched (e.g., a CVE in Envoy) without rebuilding the application. The platform team upgrades all sidecars; application teams don't know.
- **Failure isolation.** If the sidecar crashes (e.g., the log shipper), the application keeps running — log just isn't shipped for a while.
- **Standardized operations.** Every service gets the same telemetry, the same retry semantics, the same auth surface, regardless of language. Onboarding a new service to the platform is a sidecar-injection annotation, not a code change.

### Cons

- **Resource overhead.** Each pod gets an extra container with its own memory and CPU budget. Envoy sidecars typically use 100–500 MB of memory; across 1000 pods that is a real cost (on the order of hundreds of gigabytes of cluster RAM just for sidecars). This is the single biggest objection to service mesh adoption.
- **Cold start latency.** Each pod now starts two containers. If the sidecar takes 2 seconds to initialize (Envoy's first config fetch), the pod isn't ready until both are up. This is a real problem for autoscaling latency-sensitive workloads.
- **Operational complexity.** Sidecars add another thing to debug. When a request fails, you have to determine: was it the app, the sidecar, the network, or the destination? Distributed tracing through the mesh is necessary to make this tractable.
- **Version skew.** Application v1.4 talks to sidecar v1.2.3. If you upgrade the sidecar before the app supports new behavior, requests fail. This is the Istio upgrade burden — every minor version requires careful rollout.
- **Sidecar as a black box.** Application developers don't understand the sidecar's internals; when it misbehaves, they can't fix it. Ownership is split: platform owns sidecar, app team owns app, and the seam is fragile.
- **Init-order footguns.** If the sidecar must be ready before the app (so the app's outbound calls are immediately proxied), you need an `initContainer` to install the iptables rules first; otherwise the app can send traffic that bypasses the mesh. Modern Istio handles this; hand-rolled sidecars often don't.

## Sidecar without containers

The pattern predates containers. A Unix daemon that's co-located with a process (started by the same init script, sharing `/var/run`) is a sidecar. The most common pre-container examples:

- **`logrotate` + `httpd`**: a cron-driven sidecar that rotates logs; Apache doesn't know.
- **`collectd` / `statsd`**: metrics sidecars running on each host, scraping the application.
- **`memcached` + app on the same box**: a caching sidecar the app uses via localhost.

Containers made the pattern clean: the pod is the unit of co-location, the network namespace is shared, and the lifecycle is coupled. Kubernetes 1.28+ formalized "native sidecars" via `initContainers` with `restartPolicy: Always`, fixing the longstanding shutdown-order problem where the sidecar outlived the app.

## Ambassador vs Sidecar: when to choose which

The two patterns overlap. The ambassador is a sidecar that proxies to a specific external dependency. The choice is about scope:

- Use a **plain sidecar** for cross-cutting concerns that affect the application's behavior (logging, metrics, config reload).
- Use an **ambassador** when the concern is specific to one external dependency (a Redis cluster, a legacy mainframe, a particular SaaS API).
- Use a **service mesh sidecar** when the concern is universal across services in the system (mTLS between services, distributed tracing, traffic shifting).

## Cross-references

- [Service Mesh](../containers/service-mesh.md) — Istio/Linkerd as sidecar deployments
- [Kubernetes](../containers/kubernetes.md) — pods as the sidecar host
- [API Gateway](../api/api-gateway.md) — at the edge, often itself an Envoy
- [Anti-Corruption Layer](./anti-corruption-layer-deep.md) — an ambassador can be an ACL for legacy protocols
- [Strangler Fig](./strangler-fig.md) — ambassadors are a common tool in strangler migrations of legacy apps

## References

- [Microsoft Azure Architecture Center — Sidecar pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/sidecar) — the cloud-pattern catalog entry with code
- [Microsoft Azure Architecture Center — Ambassador pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/ambassador) — sibling entry for the proxy variant
- [Istio — Architecture overview](https://istio.io/latest/docs/ops/deployment/architecture/) — describes the sidecar-injection and control-plane model
- [Istio — Sidecar resource reference](https://istio.io/latest/docs/reference/config/networking/sidecar/) — the configuration object that scopes a sidecar's listeners
- [Envoy proxy — Architecture overview](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview) — the most common sidecar in production
- [Kubernetes — Pods (overview)](https://kubernetes.io/docs/concepts/workloads/pods/) — the runtime unit that hosts sidecars
- [Microsoft Azure Architecture Center — Cloud Design Patterns (catalog)](https://learn.microsoft.com/en-us/azure/architecture/patterns/) — broader pattern catalog including Sidecar, Ambassador, and the Anti-Corruption Layer
