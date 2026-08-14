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

## References

- [Google SRE Book — Chapter on Capacity Planning](https://sre.google/sre-book/forward-facing-capacity-planning/)
- [Kubernetes HPA Documentation](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [Karpenter](https://karpenter.sh/) — Kubernetes-native cluster autoscaling

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
