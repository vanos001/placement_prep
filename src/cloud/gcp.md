# Google Cloud Platform (GCP)

## Table of Contents

- [Global Infrastructure](#global-infrastructure)
- [Compute Services](#compute-services)
- [Storage & Databases](#storage--databases)
- [Networking](#networking)
- [Messaging](#messaging)
- [Identity & Access Management](#identity--access-management)
- [Monitoring & Operations](#monitoring--operations)
- [GCP vs AWS Comparison](#gcp-vs-aws-comparison)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Global Infrastructure

GCP operates on a hierarchical physical infrastructure:

- **Regions** — 40+ independent geographic zones (e.g., `us-central1`, `europe-west1`). Each region has at least 3 zones.
- **Zones** — Isolated deployment areas within a region. Each zone has one or more data centers with independent power, cooling, and networking.
- **Edge Points of Presence (PoPs)** — 150+ edge locations for Cloud CDN and Cloud Armor.

GCP's networking backbone is a private, software-defined WAN with >100 Tbps capacity, providing consistent low-latency inter-region communication.

## Compute Services

| Service | Model | Use Case |
|---------|-------|----------|
| **Compute Engine** | IaaS (VMs) | Legacy workloads, full OS control |
| **Google Kubernetes Engine (GKE)** | Managed Kubernetes | Container orchestration at scale |
| **Cloud Run** | Serverless containers | HTTP workloads, auto-scaling to zero |
| **Cloud Functions** | Serverless functions | Event-driven, short-lived tasks |
| **App Engine** | Managed PaaS | Web apps without infrastructure management |

### Compute Engine
- Custom machine types (vCPUs and memory independently configurable).
- Preemptible/Spot VMs for batch workloads (up to 91% cost savings).
- Sole-tenant nodes for regulatory compliance (no shared hardware).
- Persistent disks are network-attached SSDs with up to 256,000 IOPS.

### GKE
- **Standard mode** — You manage the node pool VMs.
- **Autopilot mode** — Google manages the underlying nodes; you pay only for pod resources.
- Integrated with Binary Authorization (container image verification) and Workload Identity (Kubernetes pods use GCP service accounts without storing keys).

### Cloud Run
- Runs any container that listens on a port (default 8080).
- Scales from 0 to 1000+ instances based on incoming request count.
- Maximum request timeout: 60 minutes (unlike Cloud Functions' 9-minute limit).
- Supports concurrency: a single instance can handle up to 1000 concurrent requests.

## Storage & Databases

| Service | Type | Characteristics |
|---------|------|-----------------|
| **Cloud Storage** | Object storage | Buckets, 4 storage classes, lifecycle policies |
| **Cloud SQL** | Managed relational | MySQL, PostgreSQL, SQL Server |
| **Cloud Spanner** | Globally distributed SQL | Horizontal scaling + ACID transactions + external consistency |
| **BigQuery** | Analytical data warehouse | Serverless, columnar, petabyte-scale, pay-per-query |
| **Firestore** | NoSQL document DB | Real-time sync, auto-scaling |
| **Memorystore** | Managed Redis/Memcached | In-memory caching |

### Cloud Spanner
Spanner is GCP's flagship differentiator — the only database that provides
**horizontal scaling, strong consistency (external consistency via TrueTime),
and global distribution** simultaneously. Uses the TrueTime API, which
synchronizes clocks across data centers using GPS and atomic clocks,
achieving bounded clock uncertainty (< 10ms).

### BigQuery
- Decoupled storage and compute: you pay separately for storage ($0.02/GB/month)
  and analysis ($5/TB scanned).
- Supports standard SQL and is optimized for analytical queries (columnar storage,
  vectorized execution).
- BigQuery ML enables training ML models using SQL directly against
  petabyte-scale datasets.

## Networking

- **VPC (Virtual Private Cloud)** — Software-defined network with custom subnets,
  firewall rules, and private Google Access (access GCP APIs without a NAT gateway).
- **Cloud Load Balancing** — Global HTTP(S) load balancer with a single anycast IP,
  SSL termination, URL maps, and backend services. Also internal load balancer for
  TCP/UDP traffic.
- **Cloud CDN** — Built on Google's global edge network. Integrated with Cloud
  Load Balancing — no separate configuration needed.
- **Cloud NAT** — Enables private instances to access the internet without public IPs.
- **Cloud Armor** — DDoS protection and WAF with preconfigured rules (OWASP Top 10)
  and custom rule evaluation.
- **Cloud Interconnect** — Dedicated or partner-provided private connections to
  GCP (bypasses public internet).

## Messaging

**Cloud Pub/Sub** is GCP's fully managed, globally distributed message bus:

- **At-least-once delivery** with configurable retry policies.
- Supports both push (webhook) and pull (streaming pull) subscription models.
- Dead-letter topics for messages that fail processing after max delivery attempts.
- Ordering keys guarantee FIFO ordering within a key.
- Throughput: millions of messages per second.

Use Pub/Sub for event-driven architectures, log ingestion, and decoupling
microservices. Compare to AWS SNS/SQS combined into a single service.

## Identity & Access Management

GCP IAM follows the **resource → policy → binding → member → role** model:

- **Members** — User accounts, service accounts, groups, or domains.
- **Roles** — Primitive (Owner/Editor/Viewer) or fine-grained (e.g., `storage.objectViewer`).
- **Service Accounts** — Identity for non-human actors (VMs, functions, pipelines).
- **Workload Identity** — Kubernetes pods authenticate to GCP using K8s service
  accounts, eliminating key management.
- **Organization Policies** — Enforce constraints (e.g., "disable public IPs on VMs")
  across all projects in an organization.

## Monitoring & Operations

- **Cloud Monitoring** — Metrics, dashboards, and alerting. Collects metrics from
  GCP services, custom applications (OpenTelemetry), and third-party integrations.
- **Cloud Logging** — Centralized log management with log-based metrics and
  log-based alerting. Supports log router for exporting to BigQuery, Pub/Sub, or
  Cloud Storage.
- **Cloud Trace** — Distributed tracing for microservices.
- **Error Reporting** — Automatic error aggregation and notification.
- **Cloud Profiler** — Continuous CPU and heap profiling for production workloads.

## GCP vs AWS Comparison

| Capability | GCP | AWS |
|-----------|-----|-----|
| IaaS VMs | Compute Engine | EC2 |
| Managed Kubernetes | GKE | EKS |
| Serverless containers | Cloud Run | Fargate |
| Serverless functions | Cloud Functions | Lambda |
| Object storage | Cloud Storage | S3 |
| Managed SQL | Cloud SQL | RDS |
| Global relational DB | Cloud Spanner | Aurora Global |
| Data warehouse | BigQuery | Redshift |
| Message bus | Pub/Sub | SNS + SQS |
| CDN | Cloud CDN | CloudFront |
| Load balancer | Cloud Load Balancing | ALB/NLB |
| IAM | Cloud IAM | IAM |
| Secret management | Secret Manager | Secrets Manager |
| Config management | Cloud Asset Inventory | AWS Config |

GCP strengths: data/analytics (BigQuery, Spanner), ML/AI (Vertex AI), and
networking (global anycast LB). AWS strengths: breadth of services (200+),
enterprise maturity, and larger partner ecosystem.

---

## Interview Questions

1. **What is TrueTime and why is it significant?**
   TrueTime is GCP's clock synchronization service that uses GPS and atomic clocks to provide bounded clock uncertainty across data centers. It enables Cloud Spanner to achieve external consistency (linearizability) by assigning timestamps with guaranteed ordering, even across geographically distributed replicas.

2. **When would you choose Cloud Run over Cloud Functions?**
   Choose Cloud Run when you need longer request timeouts (up to 60 min vs 9 min), want to run any container image (not just a function handler), need concurrency control, or have a more complex HTTP service. Cloud Functions is better for lightweight, event-triggered tasks (e.g., Cloud Storage object processing, Pub/Sub message handling).

3. **Explain GKE Autopilot vs Standard mode.**
   Standard mode gives you full control over node pools (VM types, scaling, OS). Autopilot provisions and manages nodes automatically — you define workload resource requests and Google handles the rest. Autopilot reduces operational overhead and cost (pay only for pod resources) but limits customization of node-level configurations.

4. **How does Cloud Pub/Sub ensure at-least-once delivery?**
   Pub/Sub acknowledges a message only after the subscriber confirms processing. If acknowledgment is not received within the configured deadline, the message is redelivered. For exactly-once semantics, the subscriber must implement idempotency.

5. **What is Workload Identity and why does it matter?**
   Workload Identity links a Kubernetes service account to a GCP service account, allowing pods to authenticate to GCP APIs using their K8s identity. This eliminates the need to store GCP service account keys as Kubernetes secrets, which is a significant security improvement.

6. **How does BigQuery's pricing model influence query design?**
   BigQuery charges $5 per TB of data scanned. This means query performance optimization (filtering with `WHERE` clauses, partitioning tables by date, using clustered columns) directly reduces cost. Avoid `SELECT *` and always query only the columns and partitions needed.

7. **Explain the GCP IAM policy structure.**
   An IAM policy is attached to a resource and contains a list of bindings. Each binding associates one or more members (users, groups, service accounts) with a role (a collection of permissions). Policies are evaluated at the nearest resource, and permissions are the union of all roles granted to a member.

8. **How does Cloud CDN integrate with Cloud Load Balancing?**
   Cloud CDN is configured as a backend service on the global HTTP(S) load balancer. When a request hits the load balancer, it checks the CDN cache at the nearest edge PoP. On a cache miss, it fetches from the origin backend. This single-anycast-IP architecture eliminates the need for separate DNS configuration.

## References

- [GCP Documentation](https://cloud.google.com/docs)
- [Cloud Spanner Paper](https://research.google/pubs/pub39966/)
- [GCP Architecture Framework](https://cloud.google.com/architecture/framework)
- [BigQuery Best Practices](https://cloud.google.com/bigquery/docs/best-practices)
- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
