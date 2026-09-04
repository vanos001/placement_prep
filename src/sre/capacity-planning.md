# Capacity Planning for SRE

## Capacity Estimation Methodology

Capacity planning answers one question: **Do we have enough resources to handle current and future load while meeting our SLOs?**

The systematic approach:

```
1. Characterize Current Load
   ↓
2. Identify Bottlenecks
   ↓
3. Model Growth & Spikes
   ↓
4. Add Headroom
   ↓
5. Plan Procurement/Scaling
   ↓
6. Continuously Re-evaluate
```

### Step 1: Characterize Current Load

Measure at every layer of the stack:

| Layer | Key Metrics | Tools |
|-------|------------|-------|
| **Compute** | CPU utilization, memory usage, goroutine/thread count | Prometheus, `top`, `sar` |
| **Network** | Bandwidth (bps), connections per second, packet loss | Prometheus, ntopng, `tc` |
| **Storage** | IOPS, throughput (MB/s), latency (p99), disk usage | Prometheus, `iostat`, `fio` |
| **Database** | QPS, connection pool usage, query latency, replication lag | Prometheus, `pg_stat_activity` |
| **Application** | Request rate, error rate, latency percentiles (p50/p95/p99) | APM, custom metrics |

### Step 2: Identify Bottlenecks

A system is limited by its most constrained resource. Apply **Little's Law**:

```
L = λ × W
L = number of concurrent requests in the system
λ = arrival rate (requests/second)
W = average service time (seconds)
```

If a service handles 1000 RPS with p99 latency of 100ms, then ~100 concurrent requests are in-flight at peak. Your thread pool, connection pool, and concurrent connection limits must accommodate this.

## Load Testing and Traffic Modeling

### Load Testing Types

| Type | Purpose | Tool Examples |
|------|---------|--------------|
| **Baseline** | Establish performance under expected load | k6, wrk, hey |
| **Stress** | Find the breaking point (degradation begins) | k6, Locust, Gatling |
| **Spike** | Test behavior under sudden load surges | k6 (ramp-up), Artillery |
| **Soak** | Identify memory leaks, connection exhaustion over hours | k6, Locust |
| **Chaos** | Test resilience under failure conditions | Chaos Monkey, Litmus |

### Traffic Modeling

Production traffic is never uniform. Model it realistically:

- **Diurnal pattern**: Peak at 2x-5x of trough (web services), 10x+ (streaming)
- **Seasonal spikes**: Black Friday (100x normal), holidays
- **Flash crowds**: Cache miss storms after deploy, viral events
- **Growth rate**: Linear (steady business), exponential (viral product)

```
Peak Load = Base Load × Growth Multiplier × Seasonal Factor × Safety Buffer

Example: 1000 RPS base × 1.5 (growth) × 3 (seasonal) × 1.3 (safety) = 5,850 RPS peak
```

## Queue Sizing for Bounded Latency

Little's Law (`L = λ × W`) does double duty in capacity planning: it sizes the
*steady-state* in-flight population (Step 2 above) and it caps the *queue* in front
of every bounded resource. A queue is a capacity buffer, and its length must be
derived from a latency budget, not from "more is safer":

```
queue_capacity = λ_peak × W_queue_max

Example: 5,000 req/s peak, willing to wait at most 100 ms queued:
queue_capacity = 5000 × 0.1 = 500 requests — beyond that, reject fast
```

A deeper queue does not add throughput (the servers set that); it adds *waiting*. The
utilization target is the other half of the decision, and this is where tail latency
is won or lost. For a single bottleneck resource (the M/M/1 model, derived in
[queueing fundamentals](../queueing-theory/fundamentals.md) and
[the M/M/1 page](../queueing-theory/mm1-queue.md)), average wait in queue scales as
`W_q = (ρ / (1 − ρ)) × S`:

| Utilization ρ | Mean queue wait (× service time) |
|---------------|----------------------------------|
| 0.50          | 1×                               |
| 0.80          | 4×                               |
| 0.90          | 9×                               |
| 0.95          | 19×                              |

This is why utilization targets above ~0.8 blow up tail latency: at 85% utilization a
request that arrives behind one slow one waits multiples of the service time, and p99
degrades long before throughput does. It is also why the industry rule of thumb is to
run latency-sensitive services at ρ = 0.6–0.7 — "provision for peak / 0.6" and the
2x headroom rule below are the same statement in different units. The pool-sizing
applications (connections, threads) are worked through in
[applied queueing theory](../queueing-theory/applied-systems.md); here the takeaway is
the planning rule: **queue capacity and utilization targets are latency-budget
decisions made during capacity planning, not afterthoughts discovered in load tests.**

## Database Capacity Estimation

### Working Set vs RAM: the Hit-Rate Cliff

A database is fast while its hot working set fits in RAM (buffer pool / shared
buffers) and an order of magnitude slower the moment it does not — there is no gentle
degradation between the two regimes. Capacity planning for a datastore therefore
starts from the working set, not from QPS:

- Estimate the **hot working set** from the access distribution (a small fraction of
  rows usually carries most reads); size the buffer pool to hold it plus margin, not
  the whole dataset. PostgreSQL's own
  [guidance](https://www.postgresql.org/docs/current/runtime-config-resource.html)
  makes the point concretely: the `shared_buffers` default (128 MB) is a conservative
  floor, and on a dedicated server "a reasonable starting value is 25% of the memory
  in your system" — i.e., cache sizing is a deliberate capacity decision, not a
  default.
- Watch the **leading indicator**: buffer-pool hit ratio trending down, or storage
  read IOPS climbing while QPS is flat, means the working set has outgrown RAM — you
  are planning a memory upgrade (or sharding) months ahead of the outage, which is
  exactly what capacity planning is for.

### The Connection Pool Is a Queue

Every connection pool — app-side and the server's `max_connections` — is a queueing
system, and oversizing it makes latency *worse*: more concurrent queries means more
contention for the same cores and cache. Plan connections like any other constrained
resource: total app-side pool ≤ a budget derived from DB capacity (a common starting
point is HikariCP's `cores × 2 + spindles` per DB node), divided across instances,
minus reserved connections for admin and replication. The failure mode and the math
are in [applied queueing theory](../queueing-theory/applied-systems.md) — the capacity
planning move is to treat `max_connections` as a shared budget across the whole fleet,
not a per-instance setting.

### Replication Lag as a Capacity Signal

Read replicas only add capacity while they can keep up: `pg_stat_replication`'s replay
lag ([PostgreSQL monitoring](https://www.postgresql.org/docs/current/monitoring-stats.html))
is the gauge. If lag grows with traffic, read scaling is exhausted — adding more read
traffic to replicas does not add capacity, it widens the staleness window (reads
served from further behind) and lengthens failover RPO. Budget lag like an SLO (e.g.
p99 replay lag < 1 s at peak) and treat sustained growth as a sharding trigger.

## Kafka Cluster Capacity

Kafka's capacity unit is the **partition**, and it is simultaneously the unit of
parallelism and the unit of fixed cost: open file handles, replication-fetcher
buffers, controller metadata, and leader-election time all scale with partition
count. Two planning facts from the
[Kafka documentation](https://kafka.apache.org/documentation/):

- The request path is partition-shaped — brokers cap partitions served per request
  (`max.request.partition.size.limit`, default 2000), one of several reasons clusters
  are planned with partition counts per broker (order of 2–4k) as an explicit design
  target rather than an accident.
- Partition count is expensive to change *after* the fact: adding partitions to a
  keyed topic re-shards keys and breaks per-key ordering guarantees. Over-provision
  partitions up front; this is headroom you cannot buy reactively.

Throughput planning works in bytes, and must account for replication: with
replication factor 3, every client byte is written to disk and shipped over the
network three times. `BytesInPerSec` measures client ingress per broker,
`ReplicationBytesInPerSec` the replica traffic ([monitoring
metrics](https://kafka.apache.org/43/operations/monitoring/)); the broker ceiling is
the smaller of its NIC and disk budget, and consumer fan-out multiplies reads (each
consumer group re-reads everything it subscribes to).

The leading overload signal is **ISR shrinkage**: `UnderReplicatedPartitions` should
sit at 0, and `IsrShrinksPerSec` / `IsrExpandsPerSec` should be ~0 outside broker
restarts. Sustained ISR shrink at constant traffic means followers cannot keep up
(disk or network saturated) — the cluster is out of capacity *before* producers see
any error. Deep-dive: [Kafka internals](../distributed/messaging/kafka.md) and
[Kafka for interviews](../backend/messaging/kafka.md).

## Resource Right-Sizing

### Over-provisioning vs. Under-provisioning

| Aspect | Over-Provisioned | Under-Provisioned |
|--------|-----------------|-------------------|
| Cost | High (wasted resources) | Low (efficient) |
| Performance | Consistent | Variable, SLO risk |
| Headroom | Abundant | Minimal or none |
| Failure impact | Absorbed | Cascading failures |

### Right-Sizing Process

1. **Collect resource utilization data** over 2-4 weeks (include peak)
2. **Analyze percentiles**, not averages: p95 CPU tells you the real story
3. **Set requests at p50-p75** of actual usage (allows bin-packing)
4. **Set limits at p99 + 20-50%** (prevents OOMKilled while allowing bursts)
5. **Identify zombie resources**: instances with <10% utilization

For Kubernetes, use **VPA (Vertical Pod Autoscaler)** in recommendation mode first:

```bash
# Run VPA in recommender-only mode (no auto-patching)
vpa-recommender --v=4
# Review recommendations, then manually apply or enable auto mode
```

## Auto-Scaling Strategies

### Horizontal Pod Autoscaler (HPA)

Scales pod replicas based on metrics.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15  # Double every 15s
```

**HPA calculation**: `desiredReplicas = ceil(currentReplicas × (currentMetricValue / targetMetricValue))`

### Vertical Pod Autoscaler (VPA)

Adjusts CPU/memory requests/limits for pods.

| Mode | Behavior |
|------|----------|
| `Off` | Recommendations only (no mutations) |
| `Initial` | Sets requests on pod creation only |
| `Recreate` | Restarts pods when recommendations change |
| `Auto` | Both initial and recreate |

**Caveat**: VPA and HPA on the same resource (CPU/memory) conflict—VPA changes requests, HPA counts replicas based on utilization. Use VPA for non-CPU metrics or use it for HPA `minReplicas` sizing only.

### Cluster Autoscaler

Adds/removes nodes based on pending pods.

```
Pod pending (unschedulable)
    → Cluster Autoscaler provisions new node group
    → New node joins cluster
    → Pending pods get scheduled

Node underutilized (< 50% for 10 min)
    → Cluster Autoscaler evicts pods (respecting PDBs)
    → Node removed
```

Key considerations:
- Scale-up is slow (2-5 minutes for node provisioning)
- Use **Karpenter** (Kubernetes-native, faster) as an alternative
- Set **PodDisruptionBudgets** to prevent evicting critical pods during scale-down

## Cost Optimization

| Strategy | Technique | Typical Savings |
----------|-----------|----------------|
| Right-sizing | Match instance types to actual usage | 20-40% |
| Spot/Preemptible | Run non-critical workloads on cheap instances | 60-90% |
| Reserved instances | Commit to 1-3 year usage for discounts | 30-60% |
| Graviton/ARM | Use ARM-based instances for better price/perf | 20-40% |
| Auto-scaling | Scale to zero during off-peak | 30-70% |
| Storage tiering | Move cold data to cheaper storage classes | 40-80% |

## Headroom and Buffer Planning

### The Rule of 2x

Plan for 2x your current peak load. This provides:
- Room for traffic growth without emergency scaling
- Capacity to absorb a single failure (node, zone)
- Buffer for load testing without impacting production

### N+1 and N+2 Redundancy

| Redundancy Level | Survives | Cost Multiplier |
|------------------|----------|----------------|
| N | Nothing | 1x |
| N+1 | 1 failure | ~1.5x |
| N+2 | 2 simultaneous failures | ~2x |

For databases and other hard-to-scale systems, N+2 is standard. For stateless services, N+1 with auto-scaling is typically sufficient.

### Headroom Is Measured on the Bottleneck Resource

N+1 is a statement about a *resource*, and CPU is only the most visible proxy. If a
service runs at 40% CPU but its database connection pool sits at 90%, the service has
10% headroom, not 60% — the next incident will be connection exhaustion, and the CPU
chart will look calm the whole time. The planning procedure:

1. For each tier, list the constrained resources: CPU, memory, DB connections, Kafka
   partitions, file descriptors, ephemeral ports/conntrack, thread pools.
2. Compute headroom per resource: `(capacity − peak_demand) / capacity`.
3. **The service's headroom is the minimum across resources** — plan procurement and
   alerts against that.

N+1 then becomes concrete arithmetic. Example: a 3-zone service must serve 9,000 RPS
total and survive one zone down, so each zone needs capacity for 4,500 RPS (peak /
(N−1)); if per-instance capacity is 750 RPS that is 6 instances per zone, not 4 —
and the same per-zone computation must be repeated for the DB connection budget,
since 6 instances × 10 connections each changes the database side of the plan too.
The common interview miss is stating "N+1" as a slogan and sizing only the CPU leg.

### Predictive Scaling Pitfalls

Forecasts are tempting to wire directly into autoscalers, and the two clocks matter
there more than anywhere else: a model refit weekly is unvalidated for decisions made
every 15 seconds. Use forecasts to set `minReplicas`/`maxReplicas` bounds and
to schedule pre-warming ahead of predictable peaks; let the reactive HPA fill the gap
in real time. The classic failure modes — forecasting the mean and missing the diurnal
peak, models going stale after a product change, and feedback loops where the scaled
metric is itself affected by scaling — are catalogued in
[workload forecasting](./workload-forecasting.md).

## References

- [Google SRE Workbook — Managing Load](https://sre.google/workbook/managing-load/) (capacity planning, load testing, predictable spikes)
- [Google SRE Book — Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Kubernetes HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Karpenter](https://karpenter.sh/) — Kubernetes-native cluster autoscaling
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/) — broker configs (`max.request.partition.size.limit`, `num.partitions`) and [monitoring metrics](https://kafka.apache.org/43/operations/monitoring/) (`UnderReplicatedPartitions`, `IsrShrinksPerSec`, `BytesInPerSec`)
- [PostgreSQL — Server Configuration: Resource Consumption](https://www.postgresql.org/docs/current/runtime-config-resource.html) and [pg_stat_replication monitoring](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [HikariCP Wiki — About Pool Sizing](https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing)

## Interview Questions

### Q1: How would you approach capacity planning for a new service?
**Answer**: I'd start with load testing to establish a baseline: measure CPU, memory, network, and database resource consumption at expected, 2x, and 5x load. Identify the bottleneck at each tier. Model expected traffic growth and seasonal patterns. Then plan capacity with the 2x rule—provision for double the current peak. Set up auto-scaling (HPA for pods, cluster autoscaler for nodes) to handle organic growth. Implement resource alerts at 70-80% utilization to catch trends early. Continuously re-evaluate monthly based on actual traffic data.

### Q2: Explain the difference between HPA and VPA.
**Answer**: HPA scales the **number of replicas** horizontally—adding or removing pod instances. VPA scales the **resource requests/limits** vertically—giving pods more or fewer CPU/memory. HPA is ideal for stateless services that can be replicated. VPA is ideal for workloads like databases or caches where you can't add replicas easily but need more resources per instance. A key caveat: running both HPA and VPA on the same metric (CPU/memory) creates conflicts, since VPA changes the request which changes the utilization percentage that HPA uses. Best practice: use VPA for sizing the baseline, and HPA for scaling out based on custom metrics.

### Q3: What is the cluster autoscaler and what are its limitations?
**Answer**: The cluster autoscaler adds nodes when pods are pending due to insufficient resources and removes underutilized nodes. Limitations: (1) **Scale-up latency**—provisioning a new node takes 2-5 minutes, during which pods remain pending. (2) **Scale-down safety**—it respects PodDisruptionBudgets, so it may not remove nodes even when underutilized. (3) **No scaling to zero**—minimum node group size applies. (4) **Fragmentation**—pods with different resource profiles can leave nodes partially utilized. (5) **Cloud provider specific**—each provider needs its own implementation. Karpenter addresses several of these limitations with faster provisioning and bin-packing.

### Q4: How do you determine the right resource requests and limits for pods?
**Answer**: I run the VPA recommender in off (advisory) mode for 1-2 weeks in production. VPA observes actual usage and generates recommendations. I then analyze the data: set **requests at p50-p75** of actual usage (enables good bin-packing on nodes) and **limits at p99 + 20-50%** (allows bursts without OOMKilled). I verify with stress testing that the limits are adequate under peak load. For JVM workloads, I ensure heap sizing respects the container's memory limit. I also set up alerts on `container_memory_working_set_bytes` approaching 80% of the limit.

### Q5: How do you handle a sudden traffic spike that exceeds your capacity?
**Answer**: Defense in depth: (1) **HPA auto-scales** pods up (fast, ~15-30 seconds). (2) If nodes are needed, **cluster autoscaler** provisions new nodes (slow, 2-5 minutes). (3) **Rate limiting** and **circuit breakers** protect downstream services from cascading failure. (4) **Graceful degradation**: serve cached/stale responses, disable non-critical features. (5) **CDN and edge caching** absorb read-heavy spikes. (6) **Queue-based load leveling**: requests queue in Kafka/SQS and are processed at the system's sustainable rate. After the event, I'd analyze the spike, adjust capacity planning, and potentially add predictive scaling based on patterns.

### Q6: Why do SREs target 60-70% utilization instead of 90%+?
**Answer**: Because queue wait explodes nonlinearly near saturation: for a single
bottleneck resource, mean queue wait is `(ρ/(1−ρ)) × service_time` — 4× service time
at 80% utilization, 9× at 90%, 19× at 95%. Tail latency degrades long before
throughput does, and bursts that briefly push ρ toward 1.0 drain slowly at high
utilization. Targeting ρ ≈ 0.6–0.7 is the same decision as the N+1/2x headroom rules:
it buys back the tail of the latency distribution and absorbs a single failure without
an SLO breach.
