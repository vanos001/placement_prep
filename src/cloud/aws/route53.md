# AWS Route 53

Route 53 is Amazon's managed Domain Name System (DNS) web service, launched in 2010. The "53" refers to the traditional DNS port (53). Route 53 provides DNS resolution, domain registration, health checking, and traffic routing policies (latency-based, geo-based, weighted, failover). This page covers the architecture, the routing policies, the health checks, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  Route 53 (globally distributed, managed)                  │
│  - Anycast DNS IPs at edge locations                      │
│  - 100% SLA availability                                    │
│  - Per-zone change propagation within 60 seconds             │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ DNS query (UDP/TCP 53)       │ health check updates
        │                              │
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  User's DNS resolver  │    │  Health checker      │
│  (e.g., 8.8.8.8)       │    │  (multiple regions)  │
└──────────────────────┘    └──────────────────────┘
                                      │
                                      ▼
                              Targets (ALB, EC2, etc.)
```

Route 53 uses anycast IPs at edge locations. A user's DNS query goes to the nearest Route 53 edge (often <5 ms latency).

## DNS Record Types

Route 53 supports all standard DNS record types:

- **A**: IPv4 address.
- **AAAA**: IPv6 address.
- **CNAME**: alias to another name.
- **MX**: mail exchange.
- **TXT**: text (used for SPF, DKIM, etc.).
- **NS**: name servers (delegation).
- **SOA**: start of authority (zone metadata).
- **PTR**: reverse DNS (IP to name).
- **SRV**: service record.
- **CAA**: certificate authority authorization.
- **NAPTR**: name authority pointer (used by SIP).

Route 53 also has special types:
- **Alias**: like CNAME, but for AWS resources (ALB, CloudFront, S3 website endpoint). Free (no per-query charge).

## Routing Policies

Route 53's key feature: routing policies that affect which IP is returned.

### Simple Routing

One record, one or more IPs. Random IP is returned.

```text
example.com → A → 1.2.3.4, 5.6.7.8 (random pick)
```

### Weighted Routing

Weights per record; the query returns IPs proportionally:

```text
example.com → A → 1.2.3.4 (weight=90)
            → A → 5.6.7.8 (weight=10)
```

90% of queries return 1.2.3.4; 10% return 5.6.7.8. Used for canary deployments.

### Latency-Based Routing

Records are tagged with regions; Route 53 returns the region with the lowest latency to the user:

```text
example.com → A (us-east-1) → 1.2.3.4
            → A (eu-west-1) → 5.6.7.8
            → A (ap-south-1) → 9.10.11.12

User in EU gets the EU IP.
```

"Latency" is based on Route 53's measurements between user locations and AWS regions.

### Geo-DNS (Geolocation Routing)

Records are tagged with continents/countries; Route 53 returns based on the user's location:

```text
example.com → A (Continent=EU) → 5.6.7.8 (EU data center)
            → A (Continent=NA) → 1.2.3.4 (US data center)
            → A (Default) → 9.10.11.12
```

Used for data residency ("EU users must hit EU servers") or geo-restrictions ("block users in country X").

### Geoproximity Routing (Traffic Flow)

Records have a "bias" — Route 53 biases traffic to a region based on the bias value. More sophisticated than geolocation; allows finer-grained traffic shifting.

### Failover Routing

Primary and secondary records; Route 53 monitors the primary's health. If primary is unhealthy, returns the secondary:

```text
example.com → A (PRIMARY, health_check=hc-123) → 1.2.3.4
            → A (SECONDARY) → 5.6.7.8 (DR site)

Primary health check fails → Route 53 returns secondary.
```

Used for disaster recovery.

### Multi-Value Answer

Up to 8 records, each with a health check. Route 53 returns up to 8 healthy records (shuffled).

```text
example.com → A (health_check=hc-1) → 1.2.3.4
            → A (health_check=hc-2) → 5.6.7.8
            → A (health_check=hc-3) → 9.10.11.12
```

The user's DNS resolver picks one. Used for simple load balancing.

## Health Checks

Route 53 can monitor endpoints and update routing based on health:

```bash
aws route53 create-health-check --health-check-config '
{
  "Type": "HTTP",
  "FullyQualifiedDomainName": "api.example.com",
  "IPAddress": "1.2.3.4",
  "Port": 443,
  "ResourcePath": "/health",
  "RequestInterval": 30,
  "FailureThreshold": 3
}'
```

The health check:
- Hits the endpoint every 30 seconds (configurable down to 10 seconds).
- Considers 2xx or 3xx as healthy; 4xx/5xx as unhealthy.
- After 3 consecutive failures (configurable), marks as unhealthy.

Route 53 health checks run from multiple regions globally. The endpoint is considered healthy only if reachable from all regions.

## Traffic Policies (Visual Editor)

Route 53 has a visual editor for complex routing:

```text
User →
  ├── Geolocation (continent):
  │     ├── EU → Latency-based: EU-West (1.2.3.4) or EU-Central (5.6.7.8)
  │     ├── NA → Latency-based: US-East (9.10.11.12) or US-West (13.14.15.16)
  │     └── Default → S3 website (17.18.19.20)
  └── All else → failover to DR region
```

Traffic policies support nested rules (geo → latency → failover).

## Private Hosted Zones

A private zone is a Route 53 hosted zone that's only resolvable from within a VPC (or set of VPCs):

```text
Private zone: internal.example.com
  Records:
    db.internal.example.com → 10.0.0.5  (private IP)
    api.internal.example.com → 10.0.0.6

These records are only visible to VPCs associated with the zone.
```

Used for internal service discovery. The VPC's DNS resolver queries Route 53 via a private link (no internet traffic).

## Production Use Cases

### Multi-Region Active-Active

```text
example.com (latency routing):
  us-east-1: 1.2.3.4 (ALB US-East)
  eu-west-1: 5.6.7.8 (ALB EU-West)
  ap-south-1: 9.10.11.12 (ALB AP-South)
```

Users get the lowest-latency region. With Route 53's ~5 ms latency for DNS, the user's first request is fast.

### Multi-Region Active-Passive (DR)

```text
example.com (failover routing):
  Primary: 1.2.3.4 (us-east-1, health-checked)
  Secondary: 5.6.7.8 (eu-west-1, DR site)
```

The primary serves traffic; if its health check fails, Route 53 returns the secondary. Failover takes ~30-60 seconds (DNS TTL + Route 53's update propagation).

### Canary Deployment

```text
example.com (weighted routing):
  v1: 1.2.3.4 (weight=99)
  v2: 5.6.7.8 (weight=1)
```

1% of traffic to v2; monitor; if good, increase weight; if bad, set v2 to 0.

### Domain Registration

Route 53 is also a domain registrar. Register domains directly; the registration automatically creates the hosted zone.

## Production Performance

Route 53's published performance:
- DNS query latency: <5 ms (anycast, edge locations).
- Change propagation: ~60 seconds (changes appear in all resolvers).
- Availability: 100% SLA (the only AWS service with this SLA).
- Health check propagation: ~30 seconds.

DNS is on the critical path for every HTTP request; Route 53's low latency and high availability are crucial.

## Common Pitfalls

1. **Forgetting that DNS TTLs affect failover speed.** A record with TTL=3600 (1 hour) caches for 1 hour; users see the old IP for that long. Use short TTLs (60 seconds) for records that may failover.

2. **Forgetting that some DNS resolvers ignore TTLs.** A 60-second TTL doesn't guarantee 60-second updates; some ISPs cache longer. For critical failovers, expect 5-15 minute DNS propagation.

3. **Forgetting that health checks increase Route 53 costs.** Each health check is ~$0.50/month. For 1000 endpoints, that's $500/month — significant.

4. **Forgetting that geolocation can be wrong.** Route 53 uses the user's DNS resolver's IP to estimate location; a VPN user in EU using a US resolver gets the US endpoint.

5. **Forgetting that weighted routing can have hot shards.** A weighted record with weight=1 might get 0% or 5% of traffic (variance); use weight=10 for finer control.

6. **Forgetting that private zones need VPC association.** A private zone is only visible to associated VPCs; if you have multiple VPCs, associate all of them.

## Comparison to Other DNS Providers

| Aspect | Route 53 | Cloudflare DNS | Google Cloud DNS | NS1 |
|--------|----------|-----------------|-------------------|-----|
| Edge count | ~30+ regions | ~300+ | ~20+ | ~20+ |
| Health checks | Yes (paid) | Free | No | Yes (advanced) |
| Routing policies | Many | Limited | Limited | Many (filter chain) |
| Pricing | $0.40/M queries + health checks | Free (with CDN) | $0.20/M queries | Enterprise |
| Best for | AWS-integrated | Free, fast DNS | GCP-integrated | Filter-based routing |

Route 53 is the choice for AWS-integrated deployments. Cloudflare is the choice for free DNS with a CDN. NS1 has the most advanced routing (filter chains).

## References

- [AWS Route 53 documentation](https://docs.aws.amazon.com/route53/)
- [Route 53 routing policies](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-policy.html)
- [Route 53 health checks](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover.html)
- [Route 53 Traffic Flow (visual editor)](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/traffic-flow.html)
- [Route 53 private hosted zones](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zones-private.html)
- [Route 53 vs Cloudflare DNS (AWS blog)](https://aws.amazon.com/route53/cloudflare-alternative/)
- [LWN: Route 53 overview (2020)](https://lwn.net/Articles/820133/)
