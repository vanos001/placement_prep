# Scalability Fundamentals

## What is Scalability?

Scalability is a system's ability to handle **increasing load** without degrading performance. A scalable system can grow from serving 1,000 users to 10 million users by adding resources rather than rewriting code.

## Vertical Scaling (Scale Up)

Adding more power to a single machine.

```
Before:  4 CPU, 16GB RAM  →  After:  16 CPU, 64GB RAM
```

### Pros
- Simple — no code changes needed
- No distributed system complexity
- Strong consistency is easy (single machine)

### Cons
- Hardware limits (max CPU/RAM per machine)
- Single point of failure
- Expensive at the high end (cost grows exponentially)
- Downtime during upgrades

### When to Use
- Early-stage startups
- Databases (before sharding becomes necessary)
- When simplicity matters more than scale

## Horizontal Scaling (Scale Out)

Adding more machines to distribute the load.

```
Before:  [Server 1]
After:   [Server 1] [Server 2] [Server 3] [Server 4]
              ↑ Load Balancer ↑
```

### Pros
- Near-infinite scaling potential
- Cost-effective (commodity hardware)
- Built-in redundancy
- No single point of failure

### Cons
- Distributed system complexity
- Data consistency challenges
- Requires load balancing
- Network overhead between nodes

### When to Use
- Production systems with variable load
- Microservices architectures
- When high availability is required

## Scaling Patterns

### 1. Database Scaling

#### Read Replicas
```
         ┌──────────┐
         │  Primary  │ ←── Writes
         │   DB      │
         └─────┬────┘
          ┌────┼────┐
          ▼    ▼    ▼
        [R1]  [R2]  [R3]  ←── Reads
```

- Primary handles writes
- Replicas handle reads (eventually consistent)
- Great for read-heavy workloads (90%+ reads)

#### Sharding (Horizontal Partitioning)
```
         ┌──────────┐
         │  App /    │
         │  Router   │
         └────┬─────┘
         ┌────┼────┐
         ▼    ▼    ▼
       [Sh1] [Sh2] [Sh3]
       A-H   I-P   Q-Z   (by user name)
```

- Split data across multiple databases
- Each shard holds a subset of data
- Challenges: cross-shard queries, rebalancing

#### Sharding Strategies

| Strategy | How It Works | Pros | Cons |
|----------|-------------|------|------|
| **Range** | A-M in shard 1, N-Z in shard 2 | Simple, range queries work | Hotspots if data is skewed |
| **Hash** | hash(key) % num_shards | Even distribution | Range queries don't work |
| **Directory** | Lookup table maps key → shard | Flexible | Lookup table is SPOF |
| **Geographic** | US users in US, EU in EU | Low latency | Cross-region queries |
| **Consistent Hashing** | Hash ring with virtual nodes | Minimal redistribution | More complex |

### 2. Application Scaling

#### Stateless Services
```
Client → Load Balancer → [App1] [App2] [App3]
```

- No server-side session state
- Any request can go to any server
- Session data in external store (Redis)

#### Auto-scaling
```
Metric: CPU > 80% for 5 min → Add 2 instances
Metric: CPU < 20% for 15 min → Remove 1 instance
```

- Scale based on metrics (CPU, memory, request count)
- Cloud providers offer this natively (AWS ASG, GCP MIG)

### 3. Microservices Scaling

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ User     │  │ Order    │  │ Payment  │
│ Service  │  │ Service  │  │ Service  │
│ ×3       │  │ ×5       │  │ ×2       │
└──────────┘  └──────────┘  └──────────┘
```

- Scale each service independently
- High-traffic services get more instances
- Low-traffic services save resources

## Common Bottlenecks

### 1. Database Bottlenecks
**Symptom**: Slow queries, connection pool exhaustion
**Solutions**:
- Add read replicas
- Optimize queries (indexes, query plans)
- Implement caching
- Shard if write-heavy

### 2. Network Bottlenecks
**Symptom**: High latency, timeouts
**Solutions**:
- CDN for static content
- Compress responses (gzip)
- Connection pooling
- Reduce round trips (batch requests)

### 3. CPU Bottlenecks
**Symptom**: High CPU usage, slow response times
**Solutions**:
- Horizontal scaling
- Optimize algorithms
- Use async processing
- Offload to specialized hardware (GPU for ML)

### 4. Memory Bottlenecks
**Symptom**: OOM errors, swapping
**Solutions**:
- Increase memory / use larger instances
- Implement caching with TTL
- Optimize data structures
- Use streaming for large datasets

### 5. Disk I/O Bottlenecks
**Symptom**: Slow reads/writes, high disk utilization
**Solutions**:
- Use SSDs
- Implement caching
- Batch writes
- Use write-ahead logs (WAL)

## Scaling a Real System: Example

### Scaling Twitter from 0 to 500M Users

**Phase 1: Single Server (0-1K users)**
```
[Client] → [App + DB on same machine]
```

**Phase 2: Separate App and DB (1K-100K users)**
```
[Client] → [App Server] → [Database]
```

**Phase 3: Add Caching + CDN (100K-1M users)**
```
[Client] → [CDN] → [LB] → [App] → [Cache] → [DB]
```

**Phase 4: Read Replicas + Service Split (1M-100M users)**
```
[Client] → [CDN] → [LB] → [Tweet Service] → [Cache] → [Primary DB]
           → [LB] → [User Service] → [Read Replicas]
```

**Phase 5: Full Microservices (100M-500M users)**
```
[Client] → [CDN] → [API Gateway] → [Tweet Service] → [Cache] → [Sharded DB]
                                → [Timeline Service] → [Fan-out Service]
                                → [User Service] → [Search Service]
                                → [Notification Service] → [Message Queue]
```

## Horizontal vs Vertical Scaling Decision Matrix

| Factor | Vertical | Horizontal |
|--------|----------|------------|
| Complexity | Low | High |
| Cost at scale | High | Moderate |
| Max capacity | Limited | Near-infinite |
| Fault tolerance | Low | High |
| Data consistency | Easy | Hard |
| Downtime | Required | Zero-downtime |
| Best for | DB, early stage | Stateless services |

## Interview Tips

1. **Always ask about scale** — "How many users? What's the read/write ratio?"
2. **Start simple** — Begin with a single server, then scale
3. **Identify bottlenecks** — "The database will be the first bottleneck because..."
4. **Use numbers** — "If we have 100M users and 10% are DAU, that's 10M DAU..."
5. **Mention specific technologies** — "Use Redis for caching, Kafka for async processing"
6. **Discuss trade-offs** — "Sharding gives us write scaling but makes joins expensive"
7. **Consider the data model** — Your data model drives your scaling strategy

## Common Mistakes

- ❌ Over-engineering from day one (don't shard at 1K users)
- ❌ Ignoring the read/write ratio
- ❌ Forgetting about data consistency
- ❌ Not considering the cost of scaling
- ❌ Assuming everything needs to scale to billions

## Cross-References

- [Load Balancing](./load-balancing-design.md) — Distribute traffic across scaled instances
- [Caching Strategy](./caching-strategy.md) — Reduce database load
- [Database Design](./database-design.md) — Sharding and replication
- [Capacity Planning](./capacity-planning.md) — Estimate scale requirements
- [Consistency Tradeoffs](./consistency-tradeoffs.md) — CAP theorem and its implications
- [Performance vs Scalability](../performance-vs-scalability.md)
- [Cloud Auto Scaling](../../cloud/aws/ec2.md)
- [Storage Distributed](../../storage/distributed.md)

