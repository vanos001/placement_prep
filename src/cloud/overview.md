# Cloud Computing Overview

## Introduction

Cloud computing delivers computing resources — servers, storage, databases, networking, software — over the internet on a pay-as-you-go basis. It has fundamentally changed how applications are built, deployed, and scaled. Understanding cloud architecture is essential for modern software engineering interviews, regardless of the specific role.

## Cloud Service Models

```mermaid
graph TD
    subgraph IaaS[IaaS - Infrastructure as a Service]
        I1[Virtual Machines]
        I2[Storage]
        I3[Networking]
        I4[You manage: OS, runtime, apps]
    end

    subgraph PaaS[PaaS - Platform as a Service]
        P1[Managed runtime]
        P2[Managed database]
        P3[Auto-scaling]
        P4[You manage: Code, data]
    end

    subgraph SaaS[SaaS - Software as a Service]
        S1[Gmail, Slack, Salesforce]
        S2[You manage: Configuration, data]
    end

    IaaS --> PaaS --> SaaS

    style IaaS fill:#4dabf7,color:#fff
    style PaaS fill:#69db7c,color:#000
    style SaaS fill:#ffa94d,color:#fff
```

| Model | You Manage | Provider Manages | Examples |
|-------|-----------|-----------------|----------|
| IaaS | OS, middleware, apps | Hardware, virtualization | EC2, GCE, Azure VMs |
| PaaS | Code, data | Runtime, OS, hardware | Elastic Beanstalk, App Engine, Heroku |
| SaaS | Configuration | Everything | Gmail, Salesforce, Slack |

## Deployment Models

```mermaid
graph TD
    DEPLOY[Deployment Models] --> PUBLIC[Public Cloud]
    DEPLOY --> PRIVATE[Private Cloud]
    DEPLOY --> HYBRID[Hybrid Cloud]
    DEPLOY --> MULTI[Multi-Cloud]

    PUBLIC --> P1[AWS, Azure, GCP]
    PUBLIC --> P2[Shared infrastructure]
    PUBLIC --> P3[Pay per use]

    PRIVATE --> PR1[On-premises or hosted]
    PRIVATE --> PR2[Dedicated infrastructure]
    PRIVATE --> PR3[More control, higher cost]

    HYBRID --> H1[Mix of public and private]
    HYBRID --> H2[Burst to cloud for peak loads]

    MULTI --> M1[Multiple cloud providers]
    MULTI --> M2[Avoid vendor lock-in]
```

## Core Cloud Concepts

### Regions and Availability Zones

```mermaid
graph TD
    REGION[Region: us-east-1] --> AZ1[Availability Zone A]
    REGION --> AZ2[Availability Zone B]
    REGION --> AZ3[Availability Zone C]

    AZ1 --> DC1[Datacenter 1]
    AZ2 --> DC2[Datacenter 2]
    AZ3 --> DC3[Datacenter 3]

    DC1 -->|Low-latency links| DC2
    DC2 -->|Low-latency links| DC3
```

- **Region**: Geographic area (e.g., us-east-1, eu-west-1). Contains multiple AZs.
- **Availability Zone (AZ)**: Isolated datacenter within a region. Independent power, cooling, networking.
- **Edge Location**: CDN endpoint for low-latency content delivery.

### Elasticity and Scalability

```mermaid
graph TD
    ELASTICITY[Elasticity] --> AUTO[Automatic scaling]
    AUTO --> UP[Scale up: more resources per instance]
    AUTO --> OUT[Scale out: more instances]
    AUTO --> DOWN[Scale down: remove excess resources]

    SCALABILITY[Scalability] --> VERT[Vertical: bigger machine]
    SCALABILITY --> HOR[Horizontal: more machines]

    VERT --> V1[Limited by hardware]
    HOR --> H1[Theoretically unlimited]
    HOR --> H2[Requires distributed architecture]
```

### Shared Responsibility Model

```mermaid
graph TD
    subgraph Customer[Customer Responsibility]
        C1[Data classification]
        C2[Identity & access management]
        C3[Application security]
        C4["OS patching (IaaS)"]
        C5[Network configuration]
    end

    subgraph Provider[Provider Responsibility]
        P1[Physical security]
        P2[Hardware maintenance]
        P3[Network infrastructure]
        P4[Virtualization layer]
        P5[Service availability]
    end

    Customer --> SHARED[Shared responsibility boundary]
    Provider --> SHARED
```

## Major Cloud Providers

### AWS (Amazon Web Services)

```mermaid
graph TD
    AWS[AWS Services] --> COMPUTE[Compute]
    AWS --> STORAGE[Storage]
    AWS --> DATABASE[Database]
    AWS --> NETWORK[Networking]
    AWS --> SECURITY[Security]

    COMPUTE --> EC2[EC2 - Virtual Machines]
    COMPUTE --> LAMBDA[Lambda - Serverless]
    COMPUTE --> ECS[ECS/EKS - Containers]

    STORAGE --> S3[S3 - Object Storage]
    STORAGE --> EBS[EBS - Block Storage]
    STORAGE --> EFS[EFS - File Storage]

    DATABASE --> RDS[RDS - Relational]
    DATABASE --> DYNAMO[DynamoDB - NoSQL]
    DATABASE --> REDSHIFT[Redshift - Data Warehouse]

    NETWORK --> VPC[VPC - Virtual Network]
    NETWORK --> ELB[ELB - Load Balancer]
    NETWORK --> CF[CloudFront - CDN]
```

### Azure

```mermaid
graph TD
    AZURE[Azure Services] --> COMPUTE_A[Compute]
    AZURE --> STORAGE_A[Storage]
    AZURE --> DATABASE_A[Database]

    COMPUTE_A --> VM[Virtual Machines]
    COMPUTE_A --> AKS[AKS - Kubernetes]
    COMPUTE_A --> FUNCTIONS[Azure Functions]

    STORAGE_A --> BLOB[Blob Storage]
    STORAGE_A --> FILES[Azure Files]

    DATABASE_A --> SQL[Azure SQL]
    DATABASE_A --> COSMOS[Cosmos DB]
```

### GCP (Google Cloud Platform)

```mermaid
graph TD
    GCP[GCP Services] --> COMPUTE_G[Compute]
    GCP --> STORAGE_G[Storage]
    GCP --> DATABASE_G[Database]

    COMPUTE_G --> GCE[Compute Engine]
    COMPUTE_G --> GKE[GKE - Kubernetes]
    COMPUTE_G --> CLOUD_FUNCTIONS[Cloud Functions]

    STORAGE_G --> GCS[Cloud Storage]
    DATABASE_G --> SPANNER[Spanner]
    DATABASE_G --> BIGQUERY[BigQuery]
```

## Cloud Architecture Patterns

### Microservices on Cloud

```mermaid
graph TD
    CLIENT[Client] --> LB[Load Balancer]
    LB --> GW[API Gateway]

    GW --> AUTH[Auth Service]
    GW --> USER[User Service]
    GW --> ORDER[Order Service]
    GW --> PAY[Payment Service]

    USER --> RDS1[(User DB)]
    ORDER --> RDS2[(Order DB)]
    PAY --> DYNAMO[(Payment Store)]

    ORDER --> SQS[Message Queue]
    SQS --> NOTIFY[Notification Service]
```

### Multi-Tier Architecture

```mermaid
graph TD
    subgraph Presentation[Tier 1: Presentation]
        WEB[Web Servers]
    end
    subgraph Application[Tier 2: Application]
        APP[Application Servers]
    end
    subgraph Data[Tier 3: Data]
        DB[Database]
    end

    WEB --> APP --> DB
```

## Well-Architected Framework

AWS Well-Architected Framework pillars:

```mermaid
graph TD
    WA[Well-Architected] --> PILLAR1[Operational Excellence]
    WA --> PILLAR2[Security]
    WA --> PILLAR3[Reliability]
    WA --> PILLAR4[Performance Efficiency]
    WA --> PILLAR5[Cost Optimization]
    WA --> PILLAR6[Sustainability]

    PILLAR1 --> O1[Automate, monitor, improve]
    PILLAR2 --> S1[Least privilege, encryption, logging]
    PILLAR3 --> R1[Fault tolerance, recovery]
    PILLAR4 --> PE1[Right sizing, caching, CDN]
    PILLAR5 --> CO1[Right sizing, reserved instances, spot]
    PILLAR6 --> SU1[Efficient resources, minimize waste]
```

## Interview Questions

1. **Q: Explain the difference between IaaS, PaaS, and SaaS.**
   A: IaaS provides raw infrastructure (VMs, storage, networking) — you manage the OS and above. PaaS provides a managed platform (runtime, scaling) — you just deploy code. SaaS provides complete software — you just configure and use it. Each trades control for convenience.

2. **Q: What is the shared responsibility model?**
   A: Cloud security is shared between provider and customer. The provider secures the infrastructure (physical, network, hypervisor). The customer secures what they put in the cloud (data, access control, OS patches for IaaS, application code). The boundary shifts based on service model.

3. **Q: What is the difference between vertical and horizontal scaling?**
   A: Vertical scaling (scale up) adds more resources to a single machine (CPU, RAM). Limited by hardware. Horizontal scaling (scale out) adds more machines. Requires distributed architecture but is theoretically unlimited. Cloud makes horizontal scaling easy with auto-scaling groups.

4. **Q: What is an Availability Zone vs a Region?**
   A: A region is a geographic area (e.g., us-east-1) containing multiple isolated datacenters. An Availability Zone is a single datacenter or group of datacenters within a region, with independent power, cooling, and networking. Deploying across AZs provides fault tolerance within a region.

5. **Q: How would you design a highly available application on AWS?**
   A: Deploy across multiple AZs. Use an Application Load Balancer to distribute traffic. Use Auto Scaling Groups for EC2 instances. Use RDS Multi-AZ for database failover. Use S3 for static assets (11 nines durability). Use CloudFront CDN for global reach.

## Common Mistakes

- Single point of failure — not deploying across multiple AZs.
- Not using managed services — reinventing the wheel for databases, queues, etc.
- Ignoring cost — cloud costs can spiral without monitoring and right-sizing.
- Over-engineering — don't use Kubernetes for a simple web app.
- Not planning for failure — design for failure, it will happen.

## Summary

Cloud computing provides on-demand resources with pay-as-you-go pricing. The three service models (IaaS, PaaS, SaaS) trade control for convenience. Core concepts include regions/AZs, elasticity, and the shared responsibility model. For interviews, understand the service models, scaling strategies, and how to design for high availability and fault tolerance.

## Cross-References

- [Virtualization](./virtualization/README.md) — The foundation of cloud
- [AWS Services](./aws/README.md) — Deep dive into AWS
- [Kubernetes](./kubernetes/README.md) — Container orchestration
- [CI/CD](./cicd/README.md) — Deployment pipelines
- [Observability](./observability/README.md) — Monitoring and logging
- [Storage Overview](../storage/overview.md)
- [Networking Overview](../networks/README.md)
- [MLOps Infrastructure](../ml/mlops/infrastructure.md)
- [Interview System Design](../interview/system-design/README.md)
