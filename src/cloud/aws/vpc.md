# AWS VPC (Virtual Private Cloud)

## Overview

VPC is AWS's networking foundation — a virtual network isolated to your AWS account. It gives you complete control over IP addressing, subnets, routing, and network security. Every AWS resource (EC2, RDS, Lambda) runs inside a VPC. Understanding VPC is essential for designing secure, scalable cloud architectures.

## VPC Architecture

```mermaid
graph TD
    subgraph VPC[VPC: 10.0.0.0/16]
        subgraph PublicSubnet[Public Subnet: 10.0.1.0/24]
            EC2_PUB[EC2 Web Server]
            IGW[Internet Gateway]
        end

        subgraph PrivateSubnet[Private Subnet: 10.0.2.0/24]
            EC2_PRIV[EC2 App Server]
            RDS[RDS Database]
            NAT[NAT Gateway]
        end

        subgraph PrivateSubnet2[Private Subnet: 10.0.3.0/24]
            EC2_PRIV2[EC2 Worker]
        end
    end

    INTERNET[Internet] <--> IGW
    EC2_PUB <--> IGW
    EC2_PRIV --> NAT --> IGW
    EC2_PRIV <--> RDS
```

### Key Components

```mermaid
graph TD
    VPC[VPC] --> SUBNET[Subnets]
    VPC --> IGW[Internet Gateway]
    VPC --> NAT_GW[NAT Gateway]
    VPC --> RT[Route Tables]
    VPC --> NACL[Network ACLs]
    VPC --> SG[Security Groups]
    VPC --> VPC_PEERING[VPC Peering]
    VPC --> ENDPOINT[VPC Endpoints]

    SUBNET --> PUBLIC[Public: has route to IGW]
    SUBNET --> PRIVATE[Private: no route to IGW]
```

## Subnets

```mermaid
graph TD
    VPC[VPC: 10.0.0.0/16] --> SUB1[Public Subnet: 10.0.1.0/24, AZ-a]
    VPC --> SUB2[Private Subnet: 10.0.2.0/24, AZ-a]
    VPC --> SUB3[Public Subnet: 10.0.3.0/24, AZ-b]
    VPC --> SUB4[Private Subnet: 10.0.4.0/24, AZ-b]

    SUB1 -->|Route to IGW| INTERNET[Internet]
    SUB2 -->|Route to NAT| INTERNET
```

**Public subnet**: Has a route to an Internet Gateway. Resources get public IPs.
**Private subnet**: No direct internet route. Resources use NAT Gateway for outbound.

## Routing

### Route Tables

```mermaid
graph TD
    subgraph PublicRT[Public Route Table]
        PR1[10.0.0.0/16 → Local]
        PR2[0.0.0.0/0 → Internet Gateway]
    end

    subgraph PrivateRT[Private Route Table]
        PV1[10.0.0.0/16 → Local]
        PV2[0.0.0.0/0 → NAT Gateway]
    end
```

### Internet Gateway

```mermaid
graph LR
    EC2[EC2 with Public IP] -->|Outbound| IGW[Internet Gateway]
    IGW -->|Inbound| EC2
    INTERNET[Internet] <--> IGW
```

Internet Gateway enables communication between VPC and the internet. It performs NAT for public IPs.

### NAT Gateway

```mermaid
graph LR
    EC2_PRIVATE[EC2 (no public IP)] -->|Outbound only| NAT[NAT Gateway]
    NAT -->|Outbound| IGW[Internet Gateway]
    IGW --> INTERNET[Internet]

    INTERNET -.->|Cannot initiate inbound| EC2_PRIVATE
```

NAT Gateway allows private instances to access the internet (for updates, API calls) while preventing inbound connections.

## Security

### Security Groups vs NACLs

```mermaid
graph TD
    SG[Security Groups] --> SG1[Instance level]
    SG --> SG2[Stateful (return traffic auto-allowed)]
    SG --> SG3[Allow rules only]
    SG --> SG4[All rules evaluated]

    NACL[Network ACLs] --> NACL1[Subnet level]
    NACL --> NACL2[Stateless (must allow return traffic)]
    NACL --> NACL3[Allow and deny rules]
    NACL --> NACL4[Rules evaluated in order]
```

| Feature | Security Group | Network ACL |
|---------|---------------|-------------|
| Level | Instance | Subnet |
| State | Stateful | Stateless |
| Rules | Allow only | Allow and Deny |
| Evaluation | All rules | In order (first match) |
| Default | Deny all inbound | Allow all |

### Security Group Example

```json
{
    "GroupId": "sg-12345",
    "InboundRules": [
        {"Protocol": "TCP", "Port": 443, "Source": "0.0.0.0/0"},
        {"Protocol": "TCP", "Port": 22, "Source": "203.0.113.0/24"}
    ],
    "OutboundRules": [
        {"Protocol": "All", "Port": "All", "Destination": "0.0.0.0/0"}
    ]
}
```

## VPC Peering

```mermaid
graph LR
    VPC_A[VPC A: 10.0.0.0/16] <-->|Peering| VPC_B[VPC B: 172.16.0.0/16]
    VPC_A <-->|Peering| VPC_C[VPC C: 192.168.0.0/16]
```

VPC Peering connects two VPCs using private IP addresses. Traffic stays on the AWS backbone. No transitive peering (A↔B and B↔C doesn't mean A↔C).

## VPC Endpoints

```mermaid
graph TD
    EC2[EC2 in Private Subnet] -->|Without endpoint| INTERNET[Internet → S3]
    EC2 -->|With endpoint| ENDPOINT[VPC Endpoint → S3]
    ENDPOINT --> S3[S3: aws::s3]

    EP_TYPES[Endpoint Types] --> GATEWAY[Gateway: S3, DynamoDB (free)]
    EP_TYPES --> INTERFACE[Interface: Other services (ENI, hourly cost)]
```

VPC Endpoints allow private instances to access AWS services without going through the internet.

## Flow Logs

```mermaid
graph TD
    VPC[VPC] --> FLOW[VPC Flow Logs]
    FLOW --> CW[CloudWatch Logs]
    FLOW --> S3[S3 Bucket]

    FLOW --> DATA[Capture: Accept/Reject, Source, Dest, Port, Bytes]
```

Flow Logs capture information about IP traffic going to and from network interfaces.

## Interview Questions

1. **Q: What is a VPC?**
   A: A Virtual Private Cloud is an isolated virtual network in AWS. You define IP address ranges, create subnets, configure routing, and set up security. It's the networking foundation for all AWS resources.

2. **Q: What is the difference between a public and private subnet?**
   A: A public subnet has a route to an Internet Gateway, and its resources can have public IPs. A private subnet has no direct internet route — resources use NAT Gateway for outbound-only internet access. Databases and app servers typically go in private subnets.

3. **Q: What is the difference between Security Groups and NACLs?**
   A: Security Groups are stateful (return traffic auto-allowed), operate at instance level, and allow rules only. NACLs are stateless (must explicitly allow return traffic), operate at subnet level, and support both allow and deny rules. Use Security Groups as primary defense; NACLs as secondary.

4. **Q: How would you design a VPC for a web application?**
   A: Public subnets (2 AZs) for load balancers and bastion hosts. Private subnets (2 AZs) for application servers. Private subnets (2 AZs) for databases. NAT Gateway in public subnet for outbound internet from private subnets. Security Groups restrict traffic between tiers.

5. **Q: What is a VPC Endpoint?**
   A: A VPC Endpoint enables private connectivity to AWS services without traversing the internet. Gateway endpoints (free) for S3 and DynamoDB. Interface endpoints (hourly cost) for other services. This improves security and reduces data transfer costs.

## Common Mistakes

- Placing databases in public subnets — always use private subnets for data stores.
- Opening SSH (port 22) to 0.0.0.0/0 — use VPN or bastion host.
- Not using multiple AZs — single AZ is a single point of failure.
- Forgetting to update route tables after creating subnets.
- Not enabling VPC Flow Logs — essential for security auditing and troubleshooting.

## Summary

VPC provides isolated networking for AWS resources. Key components: subnets (public/private), Internet Gateway, NAT Gateway, route tables, Security Groups, and NACLs. For interviews, understand the difference between public/private subnets, Security Groups vs NACLs, and how to design multi-tier VPC architectures.

## Cross-References

- [EC2](./ec2.md) — Runs inside VPC
- [RDS](./rds.md) — Deployed in VPC subnets
- [Lambda](./lambda.md) — Can be VPC-connected
- [AWS Overview](./README.md) — All AWS services
- [Cloud Overview](../overview.md) — Cloud fundamentals
