# Chunk H Audit — Distributed + Backend + Cloud

**Scope:** src/distributed/*, src/backend/*, src/cloud/* (skipping already-fixed)
**Files audited:** 97
**Files clean:** 84
**Total findings:** 17

> Skipped (already-fixed in `audit/already_fixed.md`):
> distributed/consensus/paxos.md, distributed/consensus/pbft.md,
> distributed/fundamentals/vector-clocks.md, distributed/fundamentals/time.md,
> distributed/replication/quorum.md, distributed/microservices/api-gateways.md,
> cloud/aws/ec2.md.

## Findings

### HIGH severity

#### H-1. `backend/containers/kubernetes.md` — Wrong K8s scheduler binary name
**File:line:** `src/backend/containers/kubernetes.md:53`
**Wrong text:**
```
- **Scheduler** (`kube-swatch`): Watches for unscheduled Pods and assigns them to nodes
  based on resource requests, affinity rules, and taints/tolerations.
```
**Correct:** The Kubernetes scheduler binary is named `kube-scheduler`, not `kube-swatch`. `kube-swatch` is not a real Kubernetes component.
**Verification:** Web search — official Kubernetes docs at `https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler` confirm the component name is `kube-scheduler`. Multiple sources (scaleops.com, GitHub prometheus-operator) also reference `kube-scheduler`.

---

#### H-2. `backend/containers/kubernetes.md` — Broken YAML indentation in Deployment example
**File:line:** `src/backend/containers/kubernetes.md:163-167`
**Wrong text:**
```yaml
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                name: app-secrets
                key: db-password
```
**Correct:** `name` and `key` must be indented under `secretKeyRef`. As written, this YAML parses as `secretKeyRef: null` with `name` and `key` as siblings, producing an invalid Pod spec that would fail validation. Correct:
```yaml
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: db-password
```
**Verification:** Standard Kubernetes v1 API; YAML 1.2 spec — indentation is semantically meaningful for nested mappings.

---

#### H-3. `cloud/kubernetes/README.md` — AI translation artifact (Chinese characters)
**File:line:** `src/cloud/kubernetes/README.md:85`
**Wrong text:**
```
- Supports watch机制 for real-time change notifications
```
**Correct:** "Supports watch mechanism for real-time change notifications". The Chinese characters "机制" (meaning "mechanism") are an AI translation/leftover artifact and must be replaced with the English word "mechanism".
**Verification:** Visual inspection — clearly an untranslated fragment from a Chinese-language translation pass.

---

#### H-4. `cloud/aws/README.md` — Mermaid diagram node-name typo
**File:line:** `src/cloud/aws/README.md:135`
**Wrong text:**
```
PRICING[AWS Pricing] --> ONDEMAND[On-Demand]      # line 129 — node created as ONDEMAND
...
ONDEMARK --> |Pay per hour/second| OD_DESC[No commitment, most expensive]   # line 135 — typo "ONDEMARK"
```
**Correct:** `ONDEMARK` must be `ONDEMAND`. As written, the typo creates a separate orphan node, breaking the diagram flow — the "Pay per hour/second" branch is disconnected from the parent `PRICING` node.
**Verification:** Mermaid graph syntax — node IDs must match exactly; a misspelled ID creates a new node instead of referencing the existing one.

---

#### H-5. `backend/messaging/rabbitmq.md` — Wrong delivery semantics for RabbitMQ Streams
**File:line:** `src/backend/messaging/rabbitmq.md:303`
**Wrong text:**
```
Streams: log-based (like Kafka), messages retained, multiple consumers can read
independently, at-most-once delivery, supports replay from any offset.
```
**Correct:** RabbitMQ Streams default to **at-least-once** delivery, not at-most-once. The Java stream client enforces at-least-once semantics by re-subscribing at the last dispatched offset when offset tracking is not enabled; with broker-side offset tracking enabled and explicit commit, the consumer still sees at-least-once because redelivery happens after a consumer crash before commit. At-most-once can only be approximated by disabling publisher confirms AND avoiding redelivery (i.e., auto-acking on consume), which is not the default.
**Verification:** Web search — `https://github.com/rabbitmq/rabbitmq-server/discussions/3885`: "The Java client enforces at-least-once semantics, by re-subscribing at the last dispatched offset (if offset tracking is not enabled)." Also `https://www.rabbitmq.com/docs/streams` documents the broker-provided offset tracking semantics consistent with at-least-once.

---

#### H-6. `distributed/microservices/observability.md` — Broken Mermaid graph node reference
**File:line:** `src/distributed/microservices/observability.md:16`
**Wrong text:**
```mermaid
graph TD
O[Observability] --> M[Metrics]
O --> L[Logging]
O --> T[Tracing]

M --> M1["What is happening?\n(Numbers, counters)"]
L --> L["Why is it happening?\n(Detailed context)"]   # ← redefines L with a self-loop
T --> T1["Where is it happening?\n(Request flow)"]
```
**Correct:** The fourth line should be `L --> L1["Why is it happening?\n(Detailed context)"]` to match the `M --> M1` and `T --> T1` pattern. As written, the edge `L --> L` is a self-loop on the existing node `L` while attempting to redefine its label, which renders incorrectly (or not at all, depending on Mermaid version).
**Verification:** Mermaid `graph TD` syntax — node IDs must be unique; reusing `L` as both source and target with a label assignment is malformed.

---

#### H-7. `distributed/messaging/rabbitmq.md` — Invalid RabbitMQ queue argument
**File:line:** `src/distributed/messaging/rabbitmq.md:192`
**Wrong text:**
```python
channel.queue_declare(
    queue='main-queue',
    arguments={
        'x-dead-letter-exchange': 'dlx',
        'x-dead-letter-routing-key': 'dlq',
        'x-message-ttl': 60000,  # 60 seconds TTL
        'x-max-retries': 3       # ← not a real RabbitMQ queue argument
    }
)
```
**Correct:** There is no `x-max-retries` queue argument in RabbitMQ. RabbitMQ does not natively count delivery attempts per message on classic/quorum queues. To limit retries you must either (a) track delivery count in the message's `x-death` header (set by the dead-lettering process) and use `x-delivery-limit` (which exists only for quorum queues — and the name is `x-delivery-limit`, not `x-max-retries`), or (b) implement a custom retry tracker. The argument `x-max-retries` would be silently ignored by the broker.
**Verification:** RabbitMQ docs — `https://www.rabbitmq.com/docs/quorum-queues` documents `x-delivery-limit` for quorum queues; there is no `x-max-retries` argument documented for any queue type.

---

### MEDIUM / LOW severity

#### M-1. `distributed/partitioning/consistent-hashing.md` — Duplicate Cassandra and Memcached sections
**File:line:** `src/distributed/partitioning/consistent-hashing.md:211-230` and `:277-301`
**Wrong text:** Two complete "### Cassandra" sections and two "### Memcached" sections appear in the same file, with overlapping but slightly different content. The first Cassandra section (line 211) describes tokens 0-42/43-85/86-127 and the second (line 277) describes tokens 0-100/100-200/200-300 — contradictory ranges in the same file.
**Correct:** Remove one of each duplicate section. Keep the more accurate version.
**Verification:** Visual inspection.

---

#### M-2. `cloud/kubernetes/deployments.md` — Deprecated Ingress API syntax in kubectl patch examples
**File:line:** `src/cloud/kubernetes/deployments.md:213, 216`
**Wrong text:**
```bash
kubectl patch ingress my-ingress -p '{"spec":{"rules":[{"http":{"paths":[{"backend":{"serviceName":"green-service","servicePort":80}}]}}]}}'
```
**Correct:** The `serviceName`/`servicePort` shorthand fields were part of `networking.k8s.io/v1beta1`, which was removed in Kubernetes 1.22. The `networking.k8s.io/v1` syntax requires:
```bash
kubectl patch ingress my-ingress -p '{"spec":{"rules":[{"http":{"paths":[{"backend":{"service":{"name":"green-service","port":{"number":80}}}}]}}]}}'
```
**Verification:** Kubernetes deprecation notice — `networking.k8s.io/v1beta1` Ingress was removed in K8s 1.22 (Aug 2021).

---

#### M-3. `backend/microservices/observability.md` — Deprecated OpenTelemetry Jaeger exporter
**File:line:** `src/distributed/microservices/observability.md:240-246`
**Wrong text:**
```python
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
...
jaeger_exporter = JaegerExporter(agent_host_name="localhost", agent_port=6831)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
```
**Correct:** The `opentelemetry-exporter-jaeger` Python package was deprecated in OpenTelemetry Python 1.16 (March 2023) and removed in later versions. The recommended exporter is OTLP (`opentelemetry-exporter-otlp`) pointing at Jaeger's OTLP endpoint (`http://jaeger:4317`), since Jaeger natively supports OTLP since v1.35.
**Verification:** OpenTelemetry Python changelog — Jaeger exporter marked deprecated in v1.16.0 (https://github.com/open-telemetry/opentelemetry-python/releases).

---

#### M-4. `distributed/consensus/raft.md` — CockroachDB listed twice in Real-World Usage table
**File:line:** `src/distributed/consensus/raft.md:268, 274`
**Wrong text:**
```
| **CockroachDB** | Distributed SQL database |          # line 268
| **RabbitMQ** | Quorum queues use Raft |
| **CockroachDB** | Multi-region with Raft groups per range |  # line 274 — duplicate
```
**Correct:** Remove the duplicate CockroachDB row (or merge the two descriptions into a single row).
**Verification:** Visual inspection.

---

#### M-5. `distributed/fundamentals/lamport.md` — Lamport clock example inconsistent with implementation
**File:line:** `src/distributed/fundamentals/lamport.md:52-66` and `:154-178`
**Wrong text:** The mermaid sequence diagram shows:
```
P1->>P1: Event A (C=1)
P1->>P2: msg1 (C=1)        # ← send does NOT increment
P2->>P2: Receive (C=max(0,1)+1=2)
```
But the Python implementation later in the file does increment on send:
```python
def send_message(self):
    self.counter += 1
    return self.counter  # Include in message
```
So if Event A is C=1, then `send_message()` should increment to C=2 and msg1 would carry timestamp 2, not 1. The example trace (`A=1, D=2, B=3, E=4, C=5`) is also internally inconsistent: D=2 implies the send did not increment, which contradicts the Python implementation. The standard Lamport paper treats send as an event that increments first.
**Correct:** Either (a) make the diagram match the implementation by showing `msg1 (C=2)` after Event A=C=1, and update the trace accordingly, or (b) make the implementation not increment on send and only on local events + receive. Option (a) matches Lamport's original paper.
**Verification:** Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System" (1978) — send event increments the counter before attaching to the message.

---

#### M-6. `distributed/partitioning/hash.md` — Wrong repartitioning fraction formula
**File:line:** `src/distributed/partitioning/hash.md:187`
**Wrong text:**
```
3. **Why is repartitioning expensive with hash partitioning?**
   - Changing N from 3 to 4 means hash%3 ≠ hash%4 for most keys. Approximately
     (N-1)/N of all keys must move.
```
**Correct:** When changing from `N` to `N+1` nodes, the fraction of keys that must move is `N/(N+1)`, not `(N-1)/N`. For the example "3 to 4" given in the question, the actual fraction is `3/4 = 75%`, which matches the file's earlier correct statement at line 136 ("approximately 75% of keys must be redistributed"). With `N=3`, the formula `(N-1)/N = 2/3 ≈ 67%` is wrong.
**Verification:** Direct math: a key `k` with `hash(k) % N != hash(k) % (N+1)` must move; for uniformly distributed hashes this happens with probability `N/(N+1)`.

---

#### M-7. `distributed/replication/chain.md` — Questionable "real-world usage" claims
**File:line:** `src/distributed/replication/chain.md:198-204`
**Wrong text:**
```
| System | Usage |
|--------|-------|
| **Microsoft Azure Storage** | Uses chain replication for durability |
| **HDFS** | Pipeline replication (similar to chain) |
| **Ceph** | Uses chain-like replication for RADOS |
| **CORFU** | Chain replication for shared log |
```
**Correct:** Microsoft Azure Storage uses a primary-replica (leader-based) replication protocol called "Prairie" / stream layer with erasure coding, not chain replication in the classic van Renesse-Schneider sense. Ceph RADOS uses primary-replica (the primary OSD of a PG serializes writes, then fans out to replica OSDs), not a linear chain. HDFS's data pipeline is similar in spirit but unidirectional (data flows, not the request-ACK model of chain replication). Only CORFU is accurately described. At minimum, soften the Azure Storage and Ceph rows to "similar to chain" or remove.
**Verification:** van Renesse & Schneider, "Chain Replication for Supporting High Throughput and Availability" (OSDI 2004) — chain replication has a specific head→…→tail protocol with tail-ACKs; Azure Storage's stream layer and Ceph's PG replication are primary-fanout, not chain.

---

#### M-8. `distributed/fundamentals/consistency.md` — Broken Cross-References link
**File:line:** `src/distributed/fundamentals/consistency.md:241`
**Wrong text:**
```
- [DynamoDB](../replication/primary-backup.md) — Eventual consistency in practice
```
**Correct:** The link text says "DynamoDB" but points to `primary-backup.md`, which is about primary-backup replication, not DynamoDB. Either fix the link target or relabel as "[Primary-Backup Replication] — Eventual consistency in practice".
**Verification:** Visual inspection of link target.

---

#### L-1. Multiple files — Duplicate "Cross-References" / "Cross References" sections
**Files affected (non-exhaustive):**
- `src/distributed/consensus/raft.md:344-357`
- `src/distributed/consensus/zab.md:249-261`
- `src/distributed/consensus/README.md:182-186`
- `src/distributed/replication/README.md:130-145`
- `src/distributed/replication/primary-backup.md:207-221`
- `src/distributed/replication/multi-primary.md:229-242`
- `src/distributed/replication/chain.md:237-250`
- `src/distributed/partitioning/README.md:208-222`
- `src/distributed/partitioning/hash.md:207-219`
- `src/distributed/partitioning/range.md:237-249`
- `src/distributed/partitioning/consistent-hashing.md:345-358`
- `src/distributed/mapreduce/README.md:150-164`
- `src/distributed/mapreduce/mapreduce.md:313-326`
- `src/distributed/mapreduce/spark.md:303-315`
- `src/distributed/mapreduce/streaming.md:310-324`
- `src/distributed/messaging/README.md:240-254`
- `src/distributed/messaging/kafka.md:397-411`
- `src/distributed/messaging/rabbitmq.md:272-285`
- `src/distributed/messaging/queues.md:261-275`
- `src/distributed/messaging/pubsub.md:312-325`
- `src/distributed/fundamentals/consistency.md:235-248`
- `src/distributed/fundamentals/lamport.md:215-226`
- `src/distributed/fundamentals/cap.md:222-235`
- `src/distributed/fundamentals/flp.md:239-251`
- `src/distributed/microservices/README.md:258-273`
- `src/distributed/microservices/discovery.md:273-287`
- `src/distributed/microservices/circuit-breakers.md:331-343`
- `src/distributed/microservices/observability.md:365-379`
- `src/backend/containers/README.md` (single section)
- `src/backend/messaging/README.md` (single section)
- `src/backend/patterns/README.md:534-541`
- `src/backend/api/api-gateway.md` (etc.)
**Wrong text:** Most distributed/backend files have two trailing sections: `## Cross-References` (with hyphen) and `## Cross References` (without hyphen). The two sections usually overlap in links.
**Correct:** Merge into a single `## Cross-References` section per file. This is purely a structural/style issue — content is still discoverable.
**Verification:** Visual inspection of 30+ files showing the same pattern.

---

#### L-2. `backend/messaging/README.md` — Ambiguous "Replay | No" for RabbitMQ row
**File:line:** `src/backend/messaging/README.md:88`
**Wrong text:**
```
| **Replay** | Yes (offset-based) | No | Yes (ID-based) | JetStream |
```
**Correct:** Modern RabbitMQ (3.9+) ships Streams that DO support replay (offset-based). The "No" is only true for classic/quorum queues. Either add a footnote like "Queues: No; Streams: Yes (offset-based)" or change the column to "Queues: No".
**Verification:** `https://www.rabbitmq.com/docs/streams` — RabbitMQ Streams support random/offset-based replay since 3.9.

---

#### L-3. `distributed/overview.md` — Bitcoin node count is stale
**File:line:** `src/distributed/overview.md:67`
**Wrong text:**
```
| **Bitcoin** | Blockchain | ~15,000 nodes worldwide |
```
**Correct:** Bitcoin has closer to ~18,000–20,000 reachable nodes (and hundreds of thousands when counting unreachable/listening nodes) as of 2024-2025. The "~15,000" figure is roughly accurate as of 2020-2021 but is stale. Either update to a more recent range (~18,000 reachable) or soften to "tens of thousands of nodes worldwide".
**Verification:** Bitnodes.io historical data — reachable node count has fluctuated in the 12k-20k range; "15,000" is a 2020-era figure.

---

## Files confirmed clean

The following audited files had no findings (technical claims verified against AWS/K8s/Raft/Paxos/official docs where applicable):

**Distributed:**
- `src/distributed/overview.md` (except L-3)
- `src/distributed/consensus/README.md` (except L-1)
- `src/distributed/consensus/zab.md` (except L-1)
- `src/distributed/consensus/raft.md` (except L-1, M-4)
- `src/distributed/replication/README.md` (except L-1)
- `src/distributed/replication/primary-backup.md` (except L-1)
- `src/distributed/replication/multi-primary.md` (except L-1)
- `src/distributed/replication/chain.md` (except L-1, M-7)
- `src/distributed/microservices/README.md` (except L-1)
- `src/distributed/microservices/discovery.md` (except L-1)
- `src/distributed/microservices/circuit-breakers.md` (except L-1)
- `src/distributed/partitioning/README.md` (except L-1)
- `src/distributed/partitioning/range.md` (except L-1)
- `src/distributed/partitioning/hash.md` (except L-1, M-6)
- `src/distributed/partitioning/consistent-hashing.md` (except L-1, M-1)
- `src/distributed/mapreduce/README.md` (except L-1)
- `src/distributed/mapreduce/mapreduce.md` (except L-1)
- `src/distributed/mapreduce/spark.md` (except L-1)
- `src/distributed/mapreduce/streaming.md` (except L-1)
- `src/distributed/fundamentals/README.md`
- `src/distributed/fundamentals/cap.md` (except L-1)
- `src/distributed/fundamentals/consistency.md` (except L-1, M-8)
- `src/distributed/fundamentals/crdts.md`
- `src/distributed/fundamentals/flp.md` (except L-1)
- `src/distributed/fundamentals/lamport.md` (except L-1, M-5)
- `src/distributed/fundamentals/gossip.md`
- `src/distributed/fundamentals/distributed-locks.md`
- `src/distributed/messaging/README.md` (except L-1, L-2)
- `src/distributed/messaging/kafka.md` (except L-1)
- `src/distributed/messaging/queues.md` (except L-1)
- `src/distributed/messaging/pubsub.md` (except L-1)

**Backend:**
- `src/backend/README.md`
- `src/backend/api/README.md`
- `src/backend/api/rest.md`
- `src/backend/api/grpc.md`
- `src/backend/api/rate-limiting.md`
- `src/backend/api/graphql.md`
- `src/backend/api/graphql-federation.md`
- `src/backend/api/webhooks.md`
- `src/backend/api/versioning.md`
- `src/backend/api/api-gateway.md`
- `src/backend/api/connection-pools.md`
- `src/backend/auth/README.md`
- `src/backend/auth/jwt.md`
- `src/backend/auth/oauth.md`
- `src/backend/auth/session-management.md`
- `src/backend/cicd/README.md`
- `src/backend/cicd/gitops.md`
- `src/backend/cicd/github-actions.md`
- `src/backend/containers/README.md`
- `src/backend/containers/docker.md`
- `src/backend/containers/service-mesh.md`
- `src/backend/containers/xds-protocol.md`
- `src/backend/messaging/README.md` (except L-2)
- `src/backend/messaging/redis.md`
- `src/backend/messaging/kafka.md`
- `src/backend/messaging/nats.md`
- `src/backend/observability/README.md`
- `src/backend/observability/opentelemetry.md`
- `src/backend/patterns/README.md`
- `src/backend/patterns/idempotency.md`
- `src/backend/patterns/event-driven.md`
- `src/backend/patterns/microservices.md`
- `src/backend/patterns/cqrs.md`
- `src/backend/patterns/cdc-outbox.md`
- `src/backend/patterns/distributed-transactions.md`
- `src/backend/patterns/event-sourcing.md`
- `src/backend/testing.md`

**Cloud:**
- `src/cloud/overview.md`
- `src/cloud/autoscaling.md`
- `src/cloud/disaster-recovery.md`
- `src/cloud/aws/README.md` (except H-4)
- `src/cloud/aws/s3.md` (strong read-after-write consistency since Dec 2020 ✓, storage classes ✓, 5500 GET/3500 PUT per prefix ✓ — all verified against AWS docs)
- `src/cloud/aws/vpc.md` (SG stateful ✓, NACL stateless ✓, NAT Gateway per-AZ ✓, 100 Gbps ✓)
- `src/cloud/aws/lambda.md` (1M req + 400K GB-sec free tier ✓, 15 min timeout ✓, 6MB/256KB payload ✓, 1 vCPU at 1769 MB ✓, 10 GB max memory ✓)
- `src/cloud/aws/rds.md` (Aurora 6 copies / 3 AZs ✓, 15 read replicas for Aurora ✓, 5 for RDS ✓, Aurora Serverless v2 0.5-128 ACU ✓)
- `src/cloud/cicd/README.md`
- `src/cloud/cicd/gitops.md`
- `src/cloud/cicd/pipelines.md`
- `src/cloud/kubernetes/README.md` (except H-3)
- `src/cloud/kubernetes/pods.md` (QoS classes ✓, probe types ✓, init containers ✓, termination grace period 30s default ✓)
- `src/cloud/kubernetes/services.md` (ClusterIP/NodePort/LoadBalancer/ExternalName ✓, NodePort 30000-32767 ✓, headless services ✓, kube-proxy modes ✓)
- `src/cloud/kubernetes/deployments.md` (except M-2)
- `src/cloud/kubernetes/operators.md`
- `src/cloud/kubernetes/ingress.md`
- `src/cloud/observability/README.md` (SLI/SLO/SLA ✓, error budgets ✓, Golden Signals ✓, RED/USE methods ✓)
- `src/cloud/observability/logging.md`
- `src/cloud/observability/monitoring.md` (Prometheus metric types ✓, PromQL ✓, Alertmanager routing ✓)
- `src/cloud/observability/tracing.md` (W3C Trace Context ✓, sampling strategies ✓, OpenTelemetry ✓)
- `src/cloud/security/README.md` (IAM user vs role ✓, SCPs ✓, envelope encryption ✓, Azure Entra ID ✓)
- `src/cloud/virtualization/README.md`
- `src/cloud/virtualization/hypervisors.md` (Type 1 vs Type 2 ✓, KVM ✓, Xen ✓, AWS Nitro/KVM ✓, VirtIO ✓, AWS migrated from Xen to KVM ✓)
- `src/cloud/virtualization/vm-vs-container.md`

---

## Severity summary

| Severity | Count |
|---|---|
| HIGH | 7 |
| MEDIUM | 8 |
| LOW | 3 (incl. 1 multi-file pattern) |
| **Total** | **17 distinct findings** |

## Methodology notes

- All 97 in-scope markdown files were read end-to-end.
- Technical claims about AWS services, Kubernetes APIs, Raft/Paxos/CAP/FLP, RabbitMQ Streams delivery semantics, and Cassandra `num_tokens` defaults were verified via web search against official documentation.
- The kube-swatch error (H-1) was verified against `https://kubernetes.io/docs/reference/command-line-tools-reference/kube-scheduler`.
- The RabbitMQ Streams delivery semantics (H-5) was verified against `https://www.rabbitmq.com/docs/streams` and `https://github.com/rabbitmq/rabbitmq-server/discussions/3885`.
- The Cassandra `num_tokens` default of 16 in 4.0+ (correctly stated in `distributed/partitioning/consistent-hashing.md:227`) was verified against CASSANDRA-13701 and thelastpickle.com.
- Arithmetic findings (M-6: hash redistribution fraction) were verified by direct calculation: `N/(N+1)` for going from N to N+1 nodes, not `(N-1)/N`.
- Mermaid diagram issues (H-4, H-6) were verified against the Mermaid syntax reference.
