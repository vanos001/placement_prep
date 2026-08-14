# Microsoft Azure

## Table of Contents

- [Overview & Regions](#overview--regions)
- [Compute Services](#compute-services)
- [Storage & Databases](#storage--databases)
- [Networking](#networking)
- [Messaging & Events](#messaging--events)
- [Identity & Access Management](#identity--access-management)
- [Monitoring & Operations](#monitoring--operations)
- [Azure vs AWS vs GCP Comparison](#azure-vs-aws-vs-gcp-comparison)
- [Interview Questions](#interview-questions)
- [References](#references)

---

## Overview & Regions

Azure operates in **60+ regions** across 140+ countries — the broadest geographic
footprint of any cloud provider. Azure's unique advantage is deep integration with
Microsoft's enterprise ecosystem (Active Directory, Windows Server, SQL Server,
Office 365, GitHub).

- **Regions** — Pairs of data centers (at least 2 per region for availability zone support).
- **Availability Zones** — Physically separate data centers within a region, each with
  independent power, cooling, and networking.
- **Sovereign clouds** — Azure Government, Azure China (21Vianet), and Azure Germany
  for regulatory compliance.

## Compute Services

| Service | Model | Use Case |
|---------|-------|----------|
| **Virtual Machines** | IaaS (VMs) | Full OS control, lift-and-shift |
| **Azure Kubernetes Service (AKS)** | Managed Kubernetes | Container orchestration |
| **Azure Functions** | Serverless functions | Event-driven workloads |
| **App Service** | Managed PaaS | Web apps, API apps, mobile backends |
| **Azure Container Apps** | Serverless containers | Microservices, Dapr-based |
| **Azure VM Scale Sets** | Auto-scaling VMs | Batch processing, legacy workloads |

### Azure Virtual Machines
- Supports Windows and Linux.
- **Spot VMs** (like AWS Spot Instances) for interruptible workloads.
- **Azure Dedicated Host** — Physical server dedicated to your organization (compliance).
- **Serial Console** — Built-in rescue console for troubleshooting without SSH/RDP.

### AKS
- **Free control plane** — You pay only for worker nodes.
- **Virtual Nodes** (ACI integration) for burst scaling without managing additional VMs.
- **AKS Arc** — Run AKS on-premises or at the edge using Azure Arc.
- Integrates with Azure AD (Entra ID) for pod identity — no Kubernetes RBAC required.

### Azure Functions
- Supports **Consumption** (pay-per-execution), **Premium** (pre-warmed instances), and
  **Dedicated** (App Service Plan) hosting plans.
- **Durable Functions** — Stateful orchestrations (fan-out/fan-in, human interaction,
  chaining patterns) built on the Durable Task Framework.
- Triggers: HTTP, timer, queue, blob, Event Hub, Service Bus, and more.

## Storage & Databases

| Service | Type | Characteristics |
|---------|------|-----------------|
| **Blob Storage** | Object storage | Hot/Cool/Archive tiers, lifecycle management |
| **Azure Files** | Managed file shares | SMB/NFS, accessible from VMs and on-premises |
| **Azure SQL Database** | Managed relational | Fully managed SQL Server, auto-tuning |
| **Cosmos DB** | Multi-model NoSQL | Global distribution, 5 consistency levels |
| **Azure Redis Cache** | Managed Redis | Caching, session store, pub/sub |
| **Azure Database for PostgreSQL/MySQL** | Managed open-source | Community edition engines |

### Cosmos DB
Cosmos DB is Azure's flagship database — a **globally distributed, multi-model**
database supporting SQL (Core API), MongoDB, Cassandra, Gremlin, and Table APIs.

Five tunable consistency levels:

| Consistency | Latency | Staleness |
|------------|---------|-----------|
| Strong | Highest | None (linearizable) |
| Bounded Staleness | High | Bounded by time or version |
| Session | Medium | Monotonic reads/writes per session |
| Consistent Prefix | Low | No gap in prefix ordering |
| Eventual | Lowest | Convergent eventually |

**Request Units (RU/s)** — Single metric for throughput. Cosmos DB automatically
partitions data and scales RU/s elastically. Supports serverless (pay-per-request)
and provisioned throughput modes.

### Azure SQL Database
- **Hyperscale** tier — separates compute and storage, enabling rapid scale-out.
- **Auto-tuning** — Automatically creates/drops indexes based on query patterns.
- **Geo-replication** — Active geo-replication and auto-failover groups.
- **Serverless** tier — Auto-pauses during inactivity (scales to zero).

## Networking

- **Virtual Networks (VNets)** — Software-defined networks with subnets, NSGs (Network
  Security Groups), and private endpoints.
- **Azure Front Door** — Global load balancer + WAF + CDN. Layer 7 routing with
  path-based rules, SSL termination, and DDoS protection.
- **Azure CDN** — Edge caching with Verizon and Akamai PoPs.
- **Application Gateway** — Regional L7 load balancer with WAF, cookie affinity,
  and URL-based routing.
- **Azure Private Link** — Access Azure services (Storage, SQL, Cosmos DB) via a
  private endpoint within your VNet — no public internet exposure.
- **Azure ExpressRoute** — Dedicated private connectivity to Azure (bypasses internet).
- **Azure Firewall** — Managed, stateful firewall with threat intelligence filtering.

## Messaging & Events

### Event Hubs
- **Event streaming platform** (equivalent to AWS Kinesis, Kafka).
- Supports millions of events per second with partitioned consumers.
- **Event Hub Capture** — Automatically archives streams to Blob Storage or Data Lake.
- Used for telemetry, log ingestion, and real-time analytics pipelines.

### Service Bus
- **Enterprise message broker** (equivalent to AWS SQS/SNS combined).
- **Queues** — Point-to-point messaging with dead-lettering, scheduled delivery, and
  transactions.
- **Topics** — Publish-subscribe with subscription rules and filters.
- Supports **transactions** across multiple messages/queues and **duplicate detection**.

### When to use which?

| Scenario | Use |
|----------|-----|
| High-throughput event streaming | Event Hubs |
| Guaranteed delivery with transactions | Service Bus |
| Simple decoupling between services | Service Bus Queues |
| Real-time analytics on event streams | Event Hubs + Stream Analytics |

## Identity & Access Management

**Microsoft Entra ID** (formerly Azure Active Directory) is the cloud-based identity
service:

- **Users & Groups** — Centralized identity management.
- **App Registrations** — Register applications for OAuth 2.0 / OIDC authentication.
- **Managed Identities** — System-assigned or user-assigned identities for Azure
  resources to access other Azure services without credentials.
- **Conditional Access** — Policy-based access control (MFA, location, device compliance,
  risk score).
- **Privileged Identity Management (PIM)** — Just-in-time access elevation for
  privileged roles.
- **RBAC** — Role-based access at resource, resource group, or subscription scope.

## Monitoring & Operations

- **Azure Monitor** — Central hub for metrics, logs, and traces. Collects from Azure
  resources, applications (Application Insights), and custom sources.
- **Application Insights** — APM for web apps. Auto-instruments .NET, Java, Node.js,
  Python. Provides distributed tracing, dependency tracking, and smart detection of
  anomalies.
- **Log Analytics Workspace** — Stores and queries log data using Kusto Query Language (KQL).
- **Alerts** — Metric alerts, log alerts, and activity log alerts with action groups.
- **Azure Resource Graph** — Query all resources across subscriptions using KQL.
- **Azure Advisor** — AI-driven recommendations for cost, performance, security, and
  reliability.

## Azure vs AWS vs GCP Comparison

| Capability | Azure | AWS | GCP |
|-----------|-------|-----|-----|
| IaaS VMs | Virtual Machines | EC2 | Compute Engine |
| Managed Kubernetes | AKS | EKS | GKE |
| Serverless functions | Azure Functions | Lambda | Cloud Functions |
| Serverless containers | Container Apps | Fargate | Cloud Run |
| Object storage | Blob Storage | S3 | Cloud Storage |
| Managed SQL | Azure SQL | RDS | Cloud SQL |
| NoSQL (global) | Cosmos DB | DynamoDB (single-region) | Firestore / Spanner |
| Data warehouse | Synapse Analytics | Redshift | BigQuery |
| Event streaming | Event Hubs | Kinesis | Pub/Sub |
| Message broker | Service Bus | SQS / SNS | Pub/Sub |
| CDN + WAF | Front Door | CloudFront + WAF | Cloud CDN + Armor |
| Identity | Entra ID | IAM | Cloud IAM |
| IaC | ARM / Bicep | CloudFormation / CDK | Deployment Manager / CDK |

Azure strengths: enterprise integration (Microsoft ecosystem), hybrid cloud (Azure
Arc), Cosmos DB's multi-model global distribution, and Entra ID's maturity.

---

## Interview Questions

1. **What are the five consistency levels in Cosmos DB and when would you use each?**
   Strong guarantees linearizability but has the highest latency — use for financial transactions. Bounded staleness allows configurable lag — good for leaderboards. Session is the default, providing monotonic reads/writes per session — sufficient for most applications. Consistent prefix ensures no gaps in ordering — useful for chat or feed. Eventual offers the lowest latency — suitable for product catalogs where slight staleness is acceptable.

2. **Explain the difference between Azure Event Hubs and Service Bus.**
   Event Hubs is an event streaming platform optimized for high-throughput, partitioned data streams (millions of events/sec). It's append-only; consumers read from offsets. Service Bus is a transactional enterprise message broker with queues (point-to-point) and topics (pub/sub), supporting dead-lettering, scheduled delivery, and transactions. Use Event Hubs for telemetry/streaming; Service Bus for reliable messaging with delivery guarantees.

3. **What is Azure Private Link and why is it important?**
   Private Link provides a private endpoint (a private IP address) within your VNet to access Azure services (Storage, SQL, Cosmos DB, etc.) without traffic traversing the public internet. This is critical for regulatory compliance (HIPAA, PCI-DSS) and defense-in-depth architectures.

4. **How do Managed Identities work in Azure?**
   A managed identity is an Azure AD identity automatically provisioned for an Azure resource (VM, App Service, Function). When the resource needs to access another Azure service (e.g., read a secret from Key Vault), it requests an access token from the local IMDS (Instance Metadata Service) endpoint using its managed identity. No credentials are stored in code or configuration.

5. **What is Durable Functions and what patterns does it support?**
   Durable Functions extends Azure Functions with stateful orchestration. It supports: **Function chaining** (sequential execution), **Fan-out/fan-in** (parallel execution followed by aggregation), **Async HTTP API** (long-running operations with polling), **Human interaction** (external events pausing/resuming workflows), and **Monitoring** (monitoring a condition with timeouts). Built on the Durable Task Framework.

6. **How does Azure Kubernetes Service compare to GKE Autopilot?**
   Both offer managed Kubernetes. AKS has a free control plane but you manage and pay for node pools. AKS supports Virtual Nodes (ACI) for serverless burst. GKE Autopilot manages the entire node layer — you pay only for pod resources. AKS integrates natively with Entra ID; GKE integrates with Cloud IAM via Workload Identity.

7. **What is Kusto Query Language (KQL) and where is it used?**
   KQL is the query language used by Azure Monitor's Log Analytics, Application Insights, and Azure Resource Graph. It supports tabular operations (project, filter, join, summarize, extend) optimized for log and telemetry analysis. Syntax is similar to SQL but designed for time-series and semi-structured data.

8. **Explain Azure Front Door vs Application Gateway.**
   Front Door is a **global** Layer 7 load balancer with WAF, routing traffic across regions via anycast. Application Gateway is a **regional** Layer 7 load balancer with WAF, operating within a single VNet. Use Front Door for global traffic distribution and Application Gateway for internal microservice routing within a region.

## References

- [Azure Documentation](https://learn.microsoft.com/en-us/azure/)
- [Cosmos DB Consistency Levels](https://learn.microsoft.com/en-us/azure/cosmos-db/consistency-levels)
- [Azure Well-Architected Framework](https://learn.microsoft.com/en-us/azure/well-architected/)
- [Azure Functions Durable Extensions](https://learn.microsoft.com/en-us/azure/azure-functions/durable/)
- [Microsoft Entra ID Documentation](https://learn.microsoft.com/en-us/entra/identity/)