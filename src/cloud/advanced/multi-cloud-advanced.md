# Multi-Cloud and Advanced Cloud Architecture

## Multi-Cloud Orchestration

Multi-cloud deployments span two or more cloud providers (AWS + GCP, AWS + Azure, or all three). The drivers are typically: **risk mitigation** (avoiding vendor lock-in), **best-of-breed services** (using each provider's strongest offering), **regulatory compliance** (data residency requirements), and **negotiating leverage** (competitive pricing).

**Orchestration layers abstract provider differences:**

| Layer | Tools | What It Abstracts |
-------|-------|-------------------|
| **Infrastructure** | Terraform, Pulumi, Crossplane | VMs, networks, storage across providers |
| **Container** | Kubernetes (EKS, GKE, AKS) | Container orchestration | 
| **Application** | HashiCorp Waypoint, KEDA | Deployment, scaling, config |
| **Data** | Apache Kafka (Confluent), Snowflake | Data pipelines, warehousing |
| **Identity** | Okta, Azure AD, Auth0 | Authentication across clouds |

**The abstraction tax** is real: multi-cloud abstractions provide the lowest common denominator of features. If you need an AWS-specific capability (e.g., Lambda Layers, DynamoDB Streams), the abstraction either doesn't support it or requires provider-specific escape hatches. This is why most production multi-cloud systems use a "thin abstraction" approach — common tooling (Terraform, K8s) but provider-specific services where needed.

```
Multi-Cloud Architecture Patterns:

  1. Active-Active (both clouds serve traffic):
  ┌─────────┐     ┌──────────┐     ┌─────────┐
  │ Global  │────►│ Cloud A  │────►│Users in │
  │  LB /  │────►│ (AWS)    │     │Region 1 │
  │  DNS    │────►│          │     └─────────┘
  │         │     └──────────┘
  │         │     ┌──────────┐     ┌─────────┐
  │         │────►│ Cloud B  │────►│Users in │
  └─────────┘     │ (GCP)    │     │Region 2 │
                  └──────────┘     └─────────┘

  2. Primary + Backup (one cloud active, one standby):
  ┌──────────┐     ┌─────────┐
  │ Cloud A  │────►│ Primary │──► Users
  │ (AWS)    │     └─────────┘
  └────┬─────┘       │ (replication)
       │            ▼
       │     ┌─────────┐
       └────►│ Cloud B │   (standby, takes over on failure)
             │ (GCP)   │
             └─────────┘

  3. Best-of-Breed (different workloads on different clouds):
  ┌──────────┐  ML Training (TPUs)  ┌──────────┐
  │ Cloud B  │◄────────────────────│ GCP      │
  │          │                      │ (Vertex) │
  │          │  Web Serving         │          │
  │          │◄────────────────────│ AWS      │
  │          │  (ECS/Fargate)       │ (ECS)    │
  └──────────┘                      └──────────┘
```

## Cloud Bursting

Cloud bursting is a hybrid cloud pattern where a workload runs primarily on-premises (or in a primary cloud) and "bursts" to a secondary cloud during demand spikes.

**Challenges of cloud bursting:**

1. **Data gravity**: The data your application needs must be accessible from the burst environment. Replicating 10TB of data to a secondary cloud takes hours — too slow for demand spikes. Solutions: use shared storage (NFS over VPN), pre-replicate hot data, or architect the application to work with a subset of data during bursts.

2. **State migration**: If the application has in-memory state (sessions, caches), that state must be accessible from the burst environment. Memcached/Redis with cross-cloud replication or sticky sessions with DNS-based routing can help.

3. **Network latency**: Cross-cloud latency (10–50ms) is much higher than intra-cloud (0.5–2ms). Burst workloads must tolerate this latency.

4. **Cost unpredictability**: Burst capacity uses on-demand pricing, which can be 5–10x more expensive than reserved/spot pricing. Without automated burst-down, costs can escalate.

> **Interview Angle**: "Design a system that handles 10x traffic spikes during Black Friday using cloud bursting." Run the base load on-prem with 80% capacity headroom. Pre-replicate product catalog data to AWS S3. Configure Kubernetes Cluster Autoscaler with max node limits in AWS. Use a global load balancer with health checks to route overflow traffic to the burst cluster. Automate burst-down after traffic normalizes with HPA scaling rules.

## Workload Migration and Cloud Federation

**Workload migration** moves an application from one cloud (or on-prem) to another. This is a complex process involving:

- **Discovery**: Map all dependencies (services, databases, DNS, certificates, IAM policies).
- **Data migration**: Replicate databases, object storage, and message queues. Tools: AWS DMS, Azure Migrate, GCP Transfer Service.
- **Application refactoring**: Replace cloud-specific APIs with portable alternatives (or accept provider-specific code paths).
- **Traffic migration**: Gradually shift traffic using DNS weight adjustment (5% → 25% → 50% → 100%) with automated rollback on error rate increase.

**Cloud federation** goes further — it provides a unified control plane across multiple clouds, allowing workloads to run seamlessly across providers as if they were a single cloud. This is largely aspirational today, but projects like HashiCorp Waypoint and Crossplane are building toward it.

## Sovereign Cloud

Sovereign cloud ensures that data and workloads remain within a specific country's borders, complying with local data sovereignty laws (GDPR, China's PIPL, India's DPDP, Russia's Federal Law 242-FZ).

**Implementation approaches:**
1. **Cloud provider sovereign regions**: AWS GovCloud (US), Azure China (operated by 21Vianet), AWS Europe (Frankfurt, Paris). These are physically and operationally isolated regions.
2. **Air-gapped deployments**: Full isolation from the public internet. Used by defense and intelligence agencies.
3. **Sovereign cloud providers**: National cloud providers (GCP China via Tencent, OVHcloud in Europe, Scaleway in France) that are subject to local jurisdiction.

The challenge: sovereign clouds often have limited service availability. AWS China offers ~50% of the services available in us-east-1. Architecture must account for missing services.

## Confidential Cloud and Confidential Containers

Confidential computing protects data *in use* by encrypting it during processing in hardware-isolated enclaves (Intel SGX, AMD SEV, ARM CCA, Intel TDX).

```
Confidential Computing Layers:

  Data at Rest  (encrypted storage)     ← S3 SSE, EBS encryption
  Data in Transit (encrypted network)    ← TLS, mTLS
  Data in Use   (encrypted computation) ← Confidential Computing

┌─────────────────────────────────┐
│ Normal VM:                       │
│   Hypervisor can read guest     │
│   memory, inspect computation   │
├─────────────────────────────────┤
│ Confidential VM:                │
│   ┌───────────────────────────┐ │
│   │ TEE / Encrypted Memory    │ │
│   │   App Code + Data         │ │
│   │   (encrypted by HW key)   │ │
│   └───────────────────────────┘ │
│   Hypervisor CANNOT read        │
│   encrypted memory              │
└─────────────────────────────────┘
```

**Confidential containers** extend confidential computing to container workloads. Rather than running a full VM, a container runs inside a lightweight TEE. Key systems:

- **AMD SEV-SNP**: Encrypts VM memory with a per-VM key. The hypervisor cannot read the VM's memory. Google CCoE (Confidential Compute on ECC) uses SEV-SNP.
- **Intel TDX**: Creates trust domains — hardware-isolated VMs where even the cloud provider's management software cannot inspect memory.
- **Azure Confidential Computing**: Offers both SGX enclaves and SEV-SNP VMs. Used for multi-party ML training where different organizations contribute data without revealing it.

**Use cases for confidential computing:**
- Multi-party analytics: Two companies jointly analyze data without either seeing the other's raw data.
- Regulated workloads: Healthcare (HIPAA), finance (PCI-DSS) processing in the cloud.
- Confidential AI: Protecting model weights and inference data from the cloud provider.

## Resource Disaggregation

Resource disaggregation separates compute, memory, storage, and accelerators into independent pools connected by high-speed interconnects. This allows independent scaling and higher resource utilization.

```
Traditional Server:              Disaggregated Rack:
┌──────────────────┐          ┌───────────┐ ┌───────────┐ ┌───────────┐
│ CPU + Memory +   │          │  Compute  │ │  Memory   │ │  Storage  │
│ Storage + NIC    │          │  (CPU/GPU)│ │  (CXL/    │ │  (NVMe)   │
│ (tightly coupled)│          │           │ │   RDMA)   │ │           │
│                  │          └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
│ Problem: Over-   │                │             │             │
│ provision each   │                └──────┬──────┘             │
│ resource because │                       │                    │
│ they're coupled  │                ┌──────▼────────────────────▼─────┐
└──────────────────┘                │    CXL / PCIe Switch Fabric     │
                                    └──────────────────────────────────┘
```

**Types of disaggregation:**

| Type | Interconnect | Status | Example |
|------|-------------|--------|---------|
| **Compute/Storage** | NVMe-oF, iSCSI | Production | AWS EBS (storage is separate from EC2) |
| **Compute/Memory** | CXL 2.0/3.0 | Early production | Intel Tiber (CXL memory expansion) |
| **Compute/Accelerator** | PCIe, CXL | Production | AWS Inferentia (chips separate from CPU) |
| **GPU/Memory** | NVLink, CXL | Research/Early | NVIDIA Grace Hopper (CPU+GPU with shared memory) |
| **Storage/Memory** | CXL | Research | Samsung CXL memory expander |

### CXL Cloud

CXL enables a new cloud architecture where memory is a shared, dynamically allocable resource:

- **Memory pooling**: Multiple servers share a pool of CXL-attached memory. A VM that needs 512GB can access it from the pool without over-provisioning physical memory on its host.
- **Memory tiering**: Hot data in HBM/DDR, warm data in CXL-attached DDR5, cold data in CXL-attached SSDs. The CPU sees it all as a unified address space.
- **Live memory migration**: VMs can be live-migrated while keeping their memory on the CXL fabric, reducing migration time.

CXL 3.0 (2023) adds fabric topology management, enabling multi-host, multi-switch memory pooling. Major cloud providers (Google, Microsoft, Meta) are actively deploying CXL in next-generation data centers.

## Bare-Metal Cloud

Bare-metal clouds provide dedicated physical servers without a hypervisor layer. This is essential for workloads that need:
- Full hardware performance (no virtualization overhead)
- Direct GPU/NIC access (GPUDirect RDMA, SR-IOV)
- Hardware-based security (no hypervisor attack surface)
- Custom OS kernels or hypervisors

| Provider | Service | Key Feature |
|----------|---------|-------------|
| AWS | Bare Metal EC2 (i3.metal, etc.) | Direct hardware access, same VPC integration |
| GCP | Sole-tenant nodes | Dedicated hosts with C2/M1 instances |
| Azure | Bare Metal (HB/HC series) | Optimized for HPC and AI workloads |
| Equinix Metal | Bare metal | Multi-cloud, custom hardware |
| Lambda Labs | GPU bare metal | NVIDIA H100 clusters for AI training |

## Spot Instance Scheduling and Preemptible Workloads

Spot instances (AWS), preemptible VMs (GCP), and low-priority VMs (Azure) offer 60–90% cost savings by using unused cloud capacity. The catch: they can be terminated with little notice (2 minutes on AWS).

**Designing for spot instances:**

```
Spot Instance Architecture:

  ┌──────────────────────────────────────────────┐
  │           Application Layer                  │
  │  (stateless, can tolerate instance loss)     │
  └──────────────────────┬───────────────────────┘
                         │
  ┌──────────────────────▼───────────────────────┐
  │         Spot Instance Manager                │
  │                                               │
  │  1. Monitor: Spot termination notice (2 min) │
  │  2. Graceful shutdown: drain connections     │
  │  3. Relaunch: request replacement spot        │
  │  4. Fallback: if no spot available, use OD    │
  └──────────────────────────────────────────────┘

  Spot Lifecycle:
  Launch ──► Running ──► Notice (2min) ──► Terminated
                                │
                                ▼
                    Drain connections / checkpoint
                                │
                                ▼
                    Launch replacement instance
```

**Spot instance strategies:**

1. **Spot diversification**: Run across multiple instance types and AZs. AWS terminates spot instances per instance type per AZ. Diversifying across 5+ types and 3+ AZs reduces the probability of simultaneous termination.

2. **Spot capacity-optimized**: AWS can allocate spot instances from the pools with the most available capacity, reducing termination probability. Use `CapacityOptimized` allocation strategy.

3. **Spot + On-Demand mix**: Run 50–70% on spot, 30–50% on on-demand. If spot capacity drops, on-demand instances absorb the traffic.

4. **Checkpointing for long-running jobs**: For batch workloads (ML training, rendering), periodically checkpoint state to durable storage. On termination, resume from the last checkpoint on a new spot instance.

**Spot-friendly vs. spot-unfriendly workloads:**

| Spot-Friendly | Spot-Unfriendly |
|---------------|-----------------|
| Stateless web serving | Database primary |
| Batch processing | Real-time bidding |
| ML training (with checkpointing) | Payment processing |
| CI/CD builds | Session-based applications |
| Data processing pipelines | In-memory caching (without replication) |

> **Interview Angle**: "How would you reduce compute costs by 60% without changing the application architecture?" Use spot instances for 70% of capacity with on-demand fallback. Use EC2 Fleet or GCP Managed Instance Groups for automatic replenishment. Add a 2-minute graceful shutdown handler. Use spot diversification (multiple instance types, multiple AZs). Use checkpointing for any stateful batch jobs.

## Composable Disaggregation

Composable infrastructure takes disaggregation further by enabling dynamic composition of resources at runtime. Rather than provisioning a fixed set of CPU, memory, and accelerator resources, the system composes them on-demand from shared pools.

This is the vision behind **composable CXL fabrics**: a rack of compute nodes, memory nodes, and accelerator nodes connected by a CXL fabric, where the data center management software dynamically allocates memory and accelerators to compute nodes based on workload demand. A VM requiring 256GB memory and 2 GPUs can be composed from separate CPU, memory, and GPU pools in seconds.

## Key Takeaways

1. **Multi-cloud is about trade-offs**, not technology — you pay an abstraction tax for flexibility. Most successful multi-cloud setups use K8s as the common layer.
2. **Cloud bursting requires pre-positioned data** — you can't replicate 10TB during a spike. Architecture for data locality from the start.
3. **Confidential computing protects against the cloud provider** — hardware enclaves ensure even the infrastructure operator cannot read your data.
4. **CXL is the most important emerging interconnect** — it enables memory pooling and disaggregation that will reshape cloud architecture.
5. **Spot instances are free money for stateless workloads** — 60–90% savings with proper diversification and graceful shutdown handling.
6. **Sovereign cloud is a compliance requirement, not an architecture choice** — design for limited service availability from day one.