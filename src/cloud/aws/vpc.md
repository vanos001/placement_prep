# Amazon VPC (Virtual Private Cloud)

## Introduction

Amazon VPC lets you provision a logically isolated section of the AWS Cloud where you can launch AWS resources in a virtual network that you define. You have complete control over your virtual networking environment, including IP address ranges, subnets, route tables, and network gateways.

## VPC Architecture

```mermaid
graph TB
    subgraph "VPC - 10.0.0.0/16"
        subgraph "Public Subnet - 10.0.1.0/24 (AZ-1)"
            EC2_PUB[EC2 Web Server]
            IGW_R[Route to Internet Gateway]
        end

        subgraph "Private Subnet - 10.0.2.0/24 (AZ-1)"
            EC2_PRIV[EC2 App Server]
            NAT_R[Route to NAT Gateway]
        end

        subgraph "Private Subnet - 10.0.3.0/24 (AZ-2)"
            RDS_INST[RDS Database]
        end

        subgraph "Public Subnet - 10.0.4.0/24 (AZ-2)"
            ALB[Application Load Balancer]
        end
    end

    IGW[Internet Gateway] --> IGW_R
    NAT[NAT Gateway] --> NAT_R
    USER[Internet Users] --> IGW
    EC2_PRIV --> NAT
    NAT --> IGW
```

### Key VPC Components

| Component | Description |
|-----------|-------------|
| **VPC** | Virtual network, defined by CIDR block (e.g., 10.0.0.0/16) |
| **Subnet** | Subdivision of VPC in a specific AZ |
| **Internet Gateway (IGW)** | Connects VPC to the internet |
| **NAT Gateway** | Allows private instances to access internet (outbound only) |
| **Route Table** | Rules that determine where network traffic is directed |
| **Security Group** | Stateful firewall at the instance level |
| **Network ACL (NACL)** | Stateless firewall at the subnet level |
| **VPC Endpoint** | Private connection to AWS services |

## Subnets

```mermaid
graph TB
    VPC_SUB[VPC - 10.0.0.0/16]

    subgraph "AZ-1"
        PUB1[Public Subnet 10.0.1.0/24]
        PRIV1[Private Subnet 10.0.2.0/24]
        DB1[DB Subnet 10.0.3.0/28]
    end

    subgraph "AZ-2"
        PUB2[Public Subnet 10.0.4.0/24]
        PRIV2[Private Subnet 10.0.5.0/24]
        DB2[DB Subnet 10.0.6.0/28]
    end

    VPC_SUB --> PUB1
    VPC_SUB --> PRIV1
    VPC_SUB --> DB1
    VPC_SUB --> PUB2
    VPC_SUB --> PRIV2
    VPC_SUB --> DB2
```

### Public vs Private Subnets

| Aspect | Public Subnet | Private Subnet |
|--------|--------------|----------------|
| **Internet Access** | Direct via IGW | Via NAT Gateway (outbound) |
| **Route Table** | Has route to IGW | No route to IGW, route to NAT |
| **Public IP** | Can assign | Not directly reachable |
| **Use Case** | Web servers, load balancers | App servers, databases |

**Determining factor**: A subnet is "public" if its route table has a route to an Internet Gateway.

## Route Tables

```mermaid
graph TB
    subgraph "Public Route Table"
        RT_PUB[Route Table]
        RT_PUB --> |10.0.0.0/16| LOCAL_P[Local - VPC internal]
        RT_PUB --> |0.0.0.0/0| IGW_RT[Internet Gateway]
    end

    subgraph "Private Route Table"
        RT_PRIV[Route Table]
        RT_PRIV --> |10.0.0.0/16| LOCAL_V[Local - VPC internal]
        RT_PRIV --> |0.0.0.0/0| NAT_RT[NAT Gateway]
    end
```

| Route | Destination | Target | Purpose |
|-------|-------------|--------|---------|
| **Local** | VPC CIDR | local | Intra-VPC communication (always exists, cannot delete) |
| **Public** | 0.0.0.0/0 | Internet Gateway | Internet access |
| **Private** | 0.0.0.0/0 | NAT Gateway | Outbound internet for private subnets |
| **VPC Peering** | Peer VPC CIDR | pcx-xxxxx | Cross-VPC communication |

## Security Groups vs NACLs

```mermaid
graph TB
    subgraph "Security Group - Instance Level"
        SG[Security Group]
        SG --> |Stateful| SG_IN[Inbound Rules]
        SG --> |Stateful| SG_OUT[Outbound Rules]
        SG_IN --> |Allow only| SG_ALLOW[No explicit deny]
    end

    subgraph "NACL - Subnet Level"
        NACL[NACL]
        NACL --> |Stateless| NACL_IN[Inbound Rules]
        NACL --> |Stateless| NACL_OUT[Outbound Rules]
        NACL_IN --> |Allow & Deny| NACL_RULES[Numbered rules, evaluated in order]
    end
```

| Feature | Security Group | NACL |
|---------|---------------|------|
| **Level** | Instance (ENI) | Subnet |
| **State** | Stateful (return traffic auto-allowed) | Stateless (must allow return traffic explicitly) |
| **Rules** | Allow only | Allow and Deny |
| **Evaluation** | All rules evaluated | Rules evaluated in order (lowest number first) |
| **Default** | Deny all inbound, allow all outbound | Allow all inbound and outbound |
| **Multiple** | Instance can have multiple SGs | Subnet has one NACL |

### Security Group Example

```json
{
    "GroupId": "sg-0123456789abcdef0",
    "InboundRules": [
        {
            "Protocol": "tcp",
            "Port": 443,
            "Source": "0.0.0.0/0",
            "Description": "HTTPS from anywhere"
        },
        {
            "Protocol": "tcp",
            "Port": 22,
            "Source": "203.0.113.0/24",
            "Description": "SSH from office IP"
        }
    ],
    "OutboundRules": [
        {
            "Protocol": "-1",
            "Port": "All",
            "Destination": "0.0.0.0/0",
            "Description": "All outbound traffic"
        }
    ]
}
```

### NACL Example

| Rule # | Type | Protocol | Port | Source | Action |
|--------|------|----------|------|--------|--------|
| 100 | HTTP | TCP | 80 | 0.0.0.0/0 | ALLOW |
| 110 | HTTPS | TCP | 443 | 0.0.0.0/0 | ALLOW |
| 120 | SSH | TCP | 22 | 203.0.113.0/24 | ALLOW |
| 200 | Ephemeral | TCP | 1024-65535 | 0.0.0.0/0 | ALLOW |
| * | All | All | All | 0.0.0.0/0 | DENY |

> **Key**: NACLs are stateless—you must explicitly allow both inbound AND outbound (including ephemeral ports for return traffic).

## NAT Gateway vs NAT Instance

```mermaid
graph TB
    subgraph "NAT Gateway (Managed)"
        EC2_NAT[Private Instance] --> NGW[NAT Gateway]
        NGW --> |Elastic IP| IGW_NG[Internet Gateway]
    end

    subgraph "NAT Instance (Self-managed)"
        EC2_NAT2[Private Instance] --> NI[NAT Instance - EC2]
        NI --> |Public IP| IGW_NI[Internet Gateway]
    end
```

| Feature | NAT Gateway | NAT Instance |
|---------|------------|-------------|
| **Management** | Fully managed by AWS | You manage (patch, scale) |
| **Availability** | Highly available within AZ | Single EC2 (need ASG for HA) |
| **Bandwidth** | Up to 100 Gbps | Depends on instance type |
| **Performance** | Automatic scaling | Limited by instance |
| **Cost** | Higher ($0.045/hr + data) | Lower (EC2 instance cost) |
| **Security Groups** | No | Yes |
| **Use Case** | Production | Dev/test, cost-sensitive |

> **Note**: NAT Gateway is per-AZ. For multi-AZ high availability, deploy a NAT Gateway in each AZ.

## VPC Peering

```mermaid
graph TB
    subgraph "VPC A - 10.0.0.0/16"
        VPC_A[VPC A]
    end

    subgraph "VPC B - 172.16.0.0/16"
        VPC_B[VPC B]
    end

    VPC_A <--> |VPC Peering Connection| VPC_B

    RT_A[Route Table A] --> |172.16.0.0/16 → pcx-xxx| VPC_A
    RT_B[Route Table B] --> |10.0.0.0/16 → pcx-xxx| VPC_B
```

**VPC Peering Characteristics:**
- Direct network connection between two VPCs
- Uses AWS backbone (not public internet)
- No transitive peering (A↔B and B↔C doesn't mean A↔C)
- CIDR blocks must not overlap
- Can be cross-region and cross-account

## VPC Endpoints

```mermaid
graph TB
    subgraph "Without VPC Endpoint"
        PRIV_EC2[Private Instance] --> NAT_GW[NAT Gateway] --> IGW_EP[Internet Gateway] --> S3_PUB[S3 Public Endpoint]
    end

    subgraph "With VPC Endpoint"
        PRIV_EC2_EP[Private Instance] --> VPCE[VPC Endpoint] --> S3_PRIV[S3 - Private]
    end
```

### Endpoint Types

| Type | Service | Connection | Use Case |
|------|---------|------------|----------|
| **Gateway Endpoint** | S3, DynamoDB | Route table entry | Free, no NAT needed |
| **Interface Endpoint (PrivateLink)** | Most AWS services | ENI in subnet | Private IP access to services |

```mermaid
graph TB
    subgraph "Gateway Endpoint"
        GW_RT[Route Table] --> |Prefix list| GW_EP[Gateway Endpoint]
        GW_EP --> S3_GW[S3]
    end

    subgraph "Interface Endpoint"
        IF_ENI[ENI in Subnet] --> IF_EP[Interface Endpoint]
        IF_EP --> |PrivateLink| SQS_IF[SQS / SNS / etc.]
    end
```

## VPC Flow Logs

```mermaid
sequenceDiagram
    participant ENI as Network Interface
    participant FL as Flow Logs
    participant CWL as CloudWatch Logs
    participant S3_FL as S3 Bucket

    ENI->>FL: Capture IP traffic metadata
    FL->>CWL: Publish to log group
    FL->>S3_FL: Or publish to S3
```

**Flow Log Record Format:**
```
version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status
2 123456789012 eni-0123456789 10.0.1.50 10.0.2.100 49152 3306 6 10 840 1620142800 1620142860 ACCEPT OK
```

**What Flow Logs capture (and don't):**
- ✅ Source/destination IP, ports, protocol, action (ACCEPT/REJECT)
- ✅ Packet and byte counts
- ❌ Actual packet content (no payload)
- ❌ DNS traffic to Amazon-provided DNS
- ❌ Instance metadata (169.254.169.254)

## NAT Gateway vs Internet Gateway

| Feature | Internet Gateway | NAT Gateway |
|---------|-----------------|-------------|
| **Purpose** | Bidirectional internet access | Outbound-only internet access |
| **IP** | Public IP on instance | Elastic IP on NAT |
| **Direction** | Inbound + Outbound | Outbound only |
| **Subnet** | Public subnet | Private subnet (routes through NAT) |
| **Cost** | Free | Per-hour + per-GB charges |

## Complete VPC Design

```mermaid
graph TB
    subgraph "Production VPC - 10.0.0.0/16"
        subgraph "Public Subnets"
            ALB1[ALB - AZ-1 - 10.0.1.0/24]
            ALB2[ALB - AZ-2 - 10.0.4.0/24]
        end

        subgraph "Private App Subnets"
            APP1[App Server - AZ-1 - 10.0.2.0/24]
            APP2[App Server - AZ-2 - 10.0.5.0/24]
        end

        subgraph "Private DB Subnets"
            DB1[Database - AZ-1 - 10.0.3.0/24]
            DB2[Database - AZ-2 - 10.0.6.0/24]
        end

        subgraph "NAT Gateways"
            NAT1[NAT GW - AZ-1]
            NAT2[NAT GW - AZ-2]
        end
    end

    IGW_PROD[Internet Gateway] --> ALB1
    IGW_PROD --> ALB2
    ALB1 --> APP1
    ALB2 --> APP2
    APP1 --> DB1
    APP2 --> DB2
    APP1 --> NAT1
    APP2 --> NAT2
    NAT1 --> IGW_PROD
    NAT2 --> IGW_PROD
```

## Interview Questions

### Q1: Explain the difference between Security Groups and NACLs.
**Answer**: Security Groups operate at the instance level, are stateful (return traffic auto-allowed), and support only allow rules. NACLs operate at the subnet level, are stateless (must explicitly allow return traffic), and support both allow and deny rules. Security Groups evaluate all rules; NACLs evaluate in rule number order. Use Security Groups for instance-level control; use NACLs for subnet-level defense in depth (e.g., blocking known malicious IPs).

### Q2: What is a NAT Gateway and when do you need one?
**Answer**: A NAT Gateway allows instances in private subnets to access the internet for outbound traffic (e.g., downloading updates, calling external APIs) while preventing the internet from initiating connections to those instances. You need one when you have private instances that require internet access but shouldn't be publicly reachable. It's deployed in a public subnet with an Elastic IP, and private subnet route tables direct 0.0.0.0/0 traffic to it.

### Q3: How do you design a highly available VPC?
**Answer**: (1) Use at least 2 AZs, (2) Create public and private subnets in each AZ, (3) Deploy NAT Gateways in each AZ (not just one), (4) Use Application Load Balancer spanning public subnets, (5) Deploy application instances in private subnets across AZs, (6) Place databases in private subnets with Multi-AZ, (7) Use separate route tables per AZ for NAT Gateway routing, (8) Apply least-privilege Security Groups.

### Q4: What is VPC Peering and what are its limitations?
**Answer**: VPC Peering creates a direct network connection between two VPCs using AWS backbone. Limitations: (1) No transitive peering—if A peers with B and B peers with C, A cannot reach C through B, (2) CIDR blocks must not overlap, (3) Cannot peer VPCs with matching or overlapping IPv4/IPv6 CIDRs, (4) Cross-account peering requires acceptor approval. For transitive routing, use Transit Gateway.

### Q5: Explain VPC Endpoints and their types.
**Answer**: VPC Endpoints enable private connectivity to AWS services without traversing the internet. Two types: (1) Gateway Endpoints—for S3 and DynamoDB only, implemented as route table entries, free to use, (2) Interface Endpoints (PrivateLink)—for most AWS services, create an ENI in your subnet with a private IP, charged per-hour and per-GB. Benefits: improved security (no public internet), lower latency (AWS backbone), reduced NAT Gateway costs.

## Common Mistakes

1. **Overlapping CIDR blocks**: VPCs that need peering cannot have overlapping ranges
2. **Single NAT Gateway**: Not deploying per-AZ NAT Gateways creates a single point of failure
3. **Using NACLs for everything**: Security Groups are simpler for most use cases; use NACLs for defense in depth
4. **Forgetting ephemeral ports in NACLs**: Must allow return traffic (ports 1024-65535) in NACL outbound rules
5. **Public subnet for databases**: Databases should always be in private subnets
6. **Overly permissive security groups**: 0.0.0.0/0 on port 22 (SSH) is a security risk
7. **Not using VPC endpoints**: Routing S3 traffic through NAT Gateway wastes money and bandwidth

## Summary

| Concept | Key Takeaway |
|---------|-------------|
| **VPC** | Isolated virtual network with customizable CIDR |
| **Subnets** | Public (IGW route) vs Private (NAT route) |
| **Security Groups** | Stateful, instance-level, allow-only |
| **NACLs** | Stateless, subnet-level, allow & deny |
| **NAT Gateway** | Managed outbound internet for private subnets |
| **VPC Peering** | Direct VPC-to-VPC connection, no transitive |
| **VPC Endpoints** | Private access to AWS services |

## Cross-References

- **EC2**: [ENIs](./ec2.md) — Network interfaces in VPC
- **RDS**: [Multi-AZ](./rds.md) — Database in private subnets
- **Lambda**: [VPC Config](./lambda.md) — Lambda inside VPC
- **Kubernetes**: [Services](../kubernetes/services.md) — K8s networking in VPC
- **Cloud Overview**: [Networking](../overview.md) — Cloud networking concepts
