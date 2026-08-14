# Infrastructure Trade-offs

Infrastructure decisions determine how reliably and efficiently your systems run. From transport protocols to deployment strategies, these choices have long-lasting consequences on performance, cost, and operational complexity.

## TCP vs UDP

### When to Choose TCP
- Reliable delivery is required (file transfer, HTTP, database connections).
- Ordered data matters (streaming a video file from start to finish).
- Congestion control and flow control are needed to avoid overwhelming the network.
- The overhead of connection setup is acceptable relative to data volume.

### When to Choose UDP
- Low latency is more important than reliability (VoIP, gaming, live video streaming).
- You can tolerate packet loss (sensor telemetry, DNS, DHCP).
- You want to implement custom reliability semantics (QUIC builds reliability on top of UDP).
- Multicast/broadcast communication is needed.

### Key Trade-offs

| Dimension | TCP | UDP |
|-----------|-----|-----|
| Reliability | Guaranteed delivery, ACK-based | Best-effort, no ACKs |
| Ordering | Guaranteed | No ordering guarantee |
| Overhead | Higher (headers ~20-60 bytes, handshakes) | Lower (headers ~8 bytes) |
| Congestion Control | Built-in | None (application must implement) |
| Connection | Stateful (3-way handshake) | Stateless |
| Throughput | Adaptive (backs off on congestion) | Can burst to line rate |
| Use Cases | Web, email, databases | DNS, gaming, streaming, QUIC |

### Interview Tip
Note that QUIC (HTTP/3) uses UDP as its transport but implements its own reliability layer—combining UDP's latency benefits with TCP-like reliability without head-of-line blocking.

---

## HTTP/1.1 vs HTTP/2 vs HTTP/3

### Comparison Table

| Dimension | HTTP/1.1 | HTTP/2 | HTTP/3 |
|-----------|----------|--------|--------|
| Transport | TCP | TCP | UDP (QUIC) |
| Multiplexing | No (one request per connection, or pipelining) | Yes (multiple streams per connection) | Yes (multiple streams per connection) |
| Head-of-Line Blocking | Yes (per connection) | Yes (TCP-level, affects all streams) | No (per-stream, QUIC handles loss) |
| Header Compression | None | HPACK | QPACK |
| Server Push | No | Yes | Yes |
| Connection Setup | 1 RTT (TCP) + 1 RTT (TLS) | 1 RTT (TCP) + 1 RTT (TLS 1.3 = 1 RTT) | 1 RTT (QUIC + TLS combined) |
| Browser Support | Universal | Universal | Modern browsers |

### When to Choose Each
- **HTTP/1.1**: Maximum compatibility, simple single-request patterns, CDN caching with wide support.
- **HTTP/2**: Modern web applications with many parallel resources, API servers serving multiple concurrent clients.
- **HTTP/3**: High-latency environments (mobile networks), applications sensitive to head-of-line blocking, forward-looking deployments.

---

## Pull vs Push-Based Systems

### When to Choose Pull
- Consumers control their own rate of consumption (backpressure is implicit).
- Producers do not know or care about consumer state.
- Consumers can consume at different times (asynchronous batch processing).
- Simple to implement—consumer polls when ready.

### When to Choose Push
- Real-time requirements (notifications, alerts).
- Producers know when new data is available and want immediate delivery.
- Event-driven architectures where latency matters.
- Consumers are always available to receive.

### Key Trade-offs
| Dimension | Pull | Push |
|-----------|------|------|
| Backpressure | Natural (consumer controls rate) | Requires flow control mechanisms |
| Latency | Higher (polling interval) | Lower (immediate) |
| Resource Usage | Wasted polls when no data | Consumer must always be ready |
| Coupling | Loose (consumer decides when) | Tighter (producer drives) |
| Complexity | Simple | Higher (retry, buffering, overflow handling) |

---

## Blue-Green vs Canary vs Rolling Deployment

### Comparison Table

| Dimension | Blue-Green | Canary | Rolling |
|-----------|-----------|--------|---------|
| Risk | Low (full switch possible) | Very Low (gradual exposure) | Medium |
| Infrastructure Cost | High (2x capacity) | Medium (partial extra) | Low (reuse existing) |
| Rollback Speed | Instant (DNS/load balancer switch) | Fast (route traffic back) | Slow (must re-deploy) |
| Downtime | Zero | Zero | Zero (with readiness checks) |
| Testing | Full environment testing before switch | Real traffic testing on subset | Limited (gradual) |
| Best For | Critical systems, database migrations | Feature validation, A/B testing | Routine updates, small teams |

### When to Choose Each
- **Blue-Green**: Major version changes, database schema migrations that cannot be rolled back, systems where any downtime is catastrophic.
- **Canary**: New features with uncertain performance impact, validating against real traffic before full rollout, A/B testing.
- **Rolling**: Standard deployments, resource-constrained environments, small teams without dedicated infra.

### Interview Tip
Discuss database migrations with blue-green: you need backward-compatible schemas that work with both old and new code during the transition period.

---

## Infrastructure as Code: Terraform vs Pulumi vs CloudFormation

### Comparison Table

| Dimension | Terraform | Pulumi | CloudFormation |
|-----------|----------|--------|----------------|
| Language | HCL (domain-specific) | General-purpose (Python, Go, TypeScript, etc.) | YAML/JSON |
| Cloud Support | Multi-cloud (AWS, GCP, Azure, etc.) | Multi-cloud | AWS only |
| State Management | Remote state (S3, GCS, etc.) | Managed by Pulumi Cloud or self-managed | Managed by AWS |
| Learning Curve | Medium (HCL + provider docs) | Low (use languages you know) | Low (if already in AWS ecosystem) |
| Ecosystem | Massive (thousands of providers) | Growing (Terraform provider bridge) | AWS services only |
| Testing | Limited (plan output) | Full (unit tests in host language) | Limited |
| Drift Detection | `terraform plan` shows drift | `pulumi refresh` | Drift detection (limited) |

### When to Choose Each
- **Terraform**: Multi-cloud or vendor-neutral strategy, largest community, mature ecosystem.
- **Pulumi**: Teams that prefer real programming languages (loops, conditionals, types, testing), complex logic in infrastructure code.
- **CloudFormation**: AWS-only shops, want tight integration with AWS services and support, no desire for multi-cloud.

---

## Message Queues: Kafka vs RabbitMQ vs NATS vs SQS

### Comparison Table

| Dimension | Kafka | RabbitMQ | NATS | SQS |
|-----------|-------|----------|------|-----|
| Model | Event streaming / log | Message queue | Messaging system | Fully managed queue |
| Ordering | Per-partition | Per-queue (FIFO queue) | Per-subject (streaming) | FIFO queues available |
| Persistence | Disk-based, configurable retention | Disk-based (persistent queues) | Optional (JetStream) | Managed (by AWS) |
| Throughput | Very high (millions/sec) | Moderate (tens of thousands/sec) | High (millions/sec) | Moderate (AWS-managed) |
| Replay | Yes (offset-based) | No (once consumed) | Yes (JetStream) | No |
| Protocols | Custom binary | AMQP | Custom (NATS protocol) | AWS API (HTTP) |
| Managed Service | Confluent Cloud, MSK | CloudAMQP | Synadia | Native AWS |
| Complexity | High (operators, ZooKeeper/KRaft) | Medium | Low | Zero |
| Consumer Groups | Yes | Yes (competing consumers) | Yes (queue groups) | Yes |

### When to Choose Each
- **Kafka**: Event sourcing, log aggregation, stream processing, high-throughput durable messaging.
- **RabbitMQ**: Task queues with complex routing (topic exchanges, headers), when you need exactly-once or transactional messaging, moderate throughput.
- **NATS**: Ultra-low-latency messaging, lightweight pub/sub, microservices communication where simplicity is valued.
- **SQS**: When you want zero ops, already in AWS, simple decoupling of components, no need for replay or stream processing.

---

## Interview Questions

1. **"Why does HTTP/3 use UDP instead of TCP?"**
   TCP's head-of-line blocking means a single lost packet stalls all multiplexed streams. QUIC over UDP implements stream-level isolation—only the affected stream waits for retransmission while others continue.

2. **"Design a deployment strategy for a payment processing system."**
   Blue-green deployment with backward-compatible database schema changes. Route 1% of traffic to green, monitor error rates and latency, then progressively shift. Keep blue warm for instant rollback.

3. **"When would you use NATS over Kafka?"**
   When you need ultra-low-latency pub/sub for microservices internal communication and do not need persistent replay or stream processing. NATS is lighter to operate and faster for fire-and-forget messaging.

4. **"Compare pull and push models for a notification delivery system."**
   Push for real-time notifications (WebSocket/SSE). Pull for batch notification retrieval (mobile app polling when opened). Hybrid: push a signal ("you have 5 new notifications"), client pulls details on open.

5. **"Your Terraform state file is corrupted. What do you do?"**
   Restore from remote state backup (S3 versioning, Terraform Cloud state locking). Re-import resources if necessary with `terraform import`. This highlights why state backends with versioning and locking are critical.
