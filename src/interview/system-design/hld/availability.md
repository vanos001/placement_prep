# High Availability

## What is High Availability?

High availability (HA) is a system's ability to remain operational and accessible for a **long period of time**, minimizing downtime. It's measured as a percentage of uptime.

### Availability Levels

| Availability | Downtime per Year | Downtime per Month | Common Name |
|-------------|-------------------|-------------------|-------------|
| 99% | 3.65 days | 7.3 hours | Two nines |
| 99.9% | 8.76 hours | 43.8 minutes | Three nines |
| 99.99% | 52.6 minutes | 4.38 minutes | Four nines |
| 99.999% | 5.26 minutes | 26.3 seconds | Five nines |

### What Each Level Means
- **99%**: Acceptable for internal tools
- **99.9%**: Standard for most web applications
- **99.99%**: Expected for critical services (banking, e-commerce)
- **99.999%**: Reserved for life-critical systems (healthcare, aviation)

## SLA, SLO, SLI

These three terms are often confused but are distinct concepts.

### SLI (Service Level Indicator)
A **quantitative measure** of a service aspect.

```
SLIs:
- Request latency: p99 < 200ms
- Error rate: < 0.1% of requests
- Throughput: > 1000 requests/second
- Availability: successful requests / total requests
```

### SLO (Service Level Objective)
The **target value** for an SLI.

```
SLOs:
- 99.9% of requests complete in < 200ms
- Error rate < 0.1%
- 99.95% availability
```

### SLA (Service Level Agreement)
A **contract** with consequences (usually financial) for missing SLOs.

```
SLA:
- 99.9% uptime guarantee
- If uptime < 99.9%: 10% credit
- If uptime < 99%: 30% credit
```

### Relationship
```
SLI (measurement) → SLO (target) → SLA (contract with penalties)
```

## Redundancy

Eliminating single points of failure by duplicating components.

### Server Redundancy
```
Before (SPOF):
[Client] → [Server] → [Database]  ← Any component fails = system down

After (Redundant):
[Client] → [LB] → [Server 1] → [DB Primary]
                → [Server 2]    → [DB Replica]
                → [Server 3]
```

### Types of Redundancy

| Type | How | Use Case |
|------|-----|----------|
| **Active-Active** | All nodes serve traffic | Load balancing, high throughput |
| **Active-Passive** | Standby takes over on failure | Databases, critical services |
| **N+1** | One extra node for failover | Cost-effective redundancy |
| **N+M** | M extra nodes for N active | Multiple failure tolerance |
| **2N** | Full duplicate of everything | Maximum redundancy (financial, healthcare) |

### Active-Active vs Active-Passive

```
Active-Active:
[LB] → [Server 1] ←→ [Server 2]  (both serving traffic)

Active-Passive:
[Server 1] → [Server 2]  (Server 2 is standby, takes over on failure)
```

| Aspect | Active-Active | Active-Passive |
|--------|--------------|----------------|
| Resource utilization | 100% | 50% (standby idle) |
| Failover time | Instant | Seconds to minutes |
| Complexity | Higher | Lower |
| Cost | Higher | Lower |
| Data consistency | Harder | Simpler |

## Failover

The process of switching to a redundant system when the primary fails.

### Automatic Failover
```
1. Health check detects failure
2. Failover mechanism activates
3. Traffic routed to standby
4. DNS/LB updated
```

### Database Failover
```
Primary DB fails → Promote Replica to Primary → Update app config
         ↓
    [Detection: 10-30s]
    [Promotion: 10-60s]
    [Total downtime: 20-90s]
```

### Failover Challenges

| Challenge | Problem | Solution |
|-----------|---------|----------|
| **Split-brain** | Both primary and replica think they're primary | Fencing, quorum |
| **Data loss** | Async replication loses recent writes | Sync replication (slower) |
| **Failover time** | Detection + promotion takes time | Faster health checks, pre-promoted standby |
| **Cascading failures** | Failover causes overload on remaining nodes | Over-provision, circuit breakers |

## Disaster Recovery (DR)

### DR Strategies

| Strategy | RPO | RTO | Cost | Use Case |
|----------|-----|-----|------|----------|
| **Backup & Restore** | Hours | Hours-Days | Low | Non-critical |
| **Pilot Light** | Minutes | Minutes | Medium | Important systems |
| **Warm Standby** | Seconds | Minutes | High | Critical systems |
| **Multi-site Active** | Near zero | Near zero | Very high | Mission-critical |

### RPO and RTO
```
RPO (Recovery Point Objective): How much data can we lose?
  → "We can lose up to 1 hour of data" → RPO = 1 hour

RTO (Recovery Time Objective): How quickly must we recover?
  → "System must be back within 15 minutes" → RTO = 15 minutes
```

### Multi-Region Deployment
```
┌─────────────────────────────────────────┐
│              Global DNS                 │
│         (Route 53 / CloudFlare)         │
└──────────────┬──────────────────────────┘
       ┌───────┴───────┐
       ▼               ▼
┌─────────────┐  ┌─────────────┐
│  US Region  │  │ EU Region   │
│  ┌────┐     │  │  ┌────┐    │
│  │App │     │  │  │App │    │
│  └──┬─┘     │  │  └──┬─┘    │
│  ┌──┴─┐     │  │  ┌──┴─┐    │
│  │ DB │←────┼──┼──│ DB │    │
│  └────┘     │  │  └────┘    │
└─────────────┘  └─────────────┘
       ↑ Cross-region replication
```

## Designing for High Availability

### 1. Eliminate Single Points of Failure
```
SPOF Checklist:
□ Load balancers (use active-passive pair)
□ Application servers (multiple behind LB)
□ Databases (primary + replicas)
□ Cache (cluster mode)
□ Message queues (clustered)
□ DNS (use multiple providers)
□ Network (redundant paths)
```

### 2. Graceful Degradation
When a component fails, degrade functionality rather than total failure.

```
Full functionality: All features working
Degraded: Core features work, non-critical disabled
  → Example: Amazon - browse works, recommendations disabled
Failure: System completely down
```

### 3. Circuit Breaker Pattern
```
Closed (normal) → Open (failures exceed threshold) → Half-Open (test)
      ↓                    ↓                              ↓
   Allow all          Block all                  Allow some requests
   requests           requests                   If success → Closed
                                                If failure → Open
```

### 4. Bulkhead Pattern
Isolate components so failure in one doesn't cascade.

```
Before (shared thread pool):
[Service A] → [Shared Pool: 100 threads] → [Service B]
[Service C] → [Same pool]                → [Service D]
If A floods pool → C fails too

After (isolated pools):
[Service A] → [Pool A: 50 threads] → [Service B]
[Service C] → [Pool C: 50 threads] → [Service D]
If A floods Pool A → Pool C still works
```

### 5. Timeout and Retry
```python
def call_with_retry(func, max_retries=3, backoff=1):
    for attempt in range(max_retries):
        try:
            return func(timeout=5)
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            sleep(backoff * (2 ** attempt))  # Exponential backoff
```

## Real-World HA Architectures

### Netflix
- Multi-region active-active
- Chaos Monkey (randomly kills instances)
- Circuit breakers (Hystrix)
- Fallback mechanisms for every dependency

### Amazon
- Multi-AZ deployments by default
- Auto-scaling groups
- ELB with health checks
- Cross-region replication for critical data

### Google
- Live migration (move VMs without downtime)
- Global load balancing
- Automatic failover at every layer

## Interview Tips

1. **Define availability target** — "We need 99.9% availability"
2. **Identify SPOFs** — Walk through the architecture and find them
3. **Discuss redundancy at every layer** — LB, app, DB, cache, queue
4. **Mention specific strategies** — "Active-passive for DB, active-active for app servers"
5. **Consider failure modes** — "What happens if the primary DB fails?"
6. **Talk about DR** — "Cross-region replication with RPO of 1 minute"
7. **Include monitoring** — "Health checks every 10 seconds, alert on 3 failures"
8. **Don't over-engineer** — Match HA level to business requirements

## Common Mistakes

- ❌ Ignoring SPOFs in the design
- ❌ Not defining SLO/SLA targets
- ❌ Over-engineering for five nines when three nines suffice
- ❌ Forgetting about database failover
- ❌ Not testing failover procedures
- ❌ Ignoring cascading failures

## Cross-References

- [Load Balancing](./load-balancing-design.md) — Distributes traffic for HA
- [Scalability](./scalability.md) — Scaling enables redundancy
- [Consistency Tradeoffs](./consistency-tradeoffs.md) — CAP theorem trade-offs
- [Monitoring](./monitoring-observability.md) — Detect failures for failover
- [Messaging Systems](./messaging-systems.md) — Queues for fault tolerance
- [Availability Patterns](../availability-patterns.md)
- [Cloud Overview](../../cloud/overview.md)
- [DBMS Replication](../../dbms/distributed/replication.md)

