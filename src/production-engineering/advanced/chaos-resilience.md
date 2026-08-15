# Chaos Engineering & Resilience Testing

## Overview

Chaos engineering is the disciplined practice of experimenting on a system to build confidence in its capability to withstand turbulent conditions in production. Rather than waiting for failures to happen unexpectedly, chaos engineering proactively introduces controlled failures to discover weaknesses before they cause incidents. This chapter covers fault injection techniques, game days, resilience testing frameworks, disaster recovery verification, and production verification practices.

## Chaos Engineering Principles

The core principles of chaos engineering, as defined by Netflix (originators of Chaos Monkey):

1. **Start with a steady state**: define normal behavior as a measurable output (latency, error rate, throughput)
2. **Hypothesize**: "this system will continue to operate correctly even if [specific failure] occurs"
3. **Introduce controlled variables**: inject the failure in a safe, bounded manner
4. **Observe**: measure the system's response against the hypothesis
5. **Learn**: if the hypothesis is violated, investigate and fix; if confirmed, document and expand

Key distinction from random testing: chaos engineering is **hypothesis-driven** and **controlled**—failures are introduced deliberately, in staging or production, with safeguards.

## Fault Injection Techniques

### Network Fault Injection

| Fault Type | Description | Tool |
|------------|-------------|------|
| Latency injection | Add artificial delay to network calls | toxiproxy, iptables, tc/netem |
| Packet loss | Drop a percentage of packets | tc/netem, Chaos Mesh |
| Bandwidth throttling | Reduce available bandwidth | tc/netem, AWS network ACL |
| DNS failure | Return NXDOMAIN or timeout | Chaos Mesh DNS fault |
| Partition | Block all traffic between services | iptables, Chaos Mesh |
| Blackhole routing | Drop all packets to/from a target | iptables -j DROP, AWS security groups |

**Toxiproxy** (by Shopify) is a widely-used TCP proxy that sits between services and injects latency, timeouts, bandwidth limits, and connection failures via an HTTP API:

```
Client → Toxiproxy → Service

POST /proxies/my-service/toxics
{
  "type": "latency",
  "attributes": {"latency": 500, "jitter": 100},
  "name": "slow_service",
  "stream": "downstream"
}
```

### CPU / Resource Fault Injection

| Fault Type | Description | Tool |
|------------|-------------|------|
| CPU stress | Max out CPU on a node/container | stress-ng, Chaos Mesh |
| Memory pressure | Consume memory to trigger OOM | stress-ng, memhog |
| Disk I/O saturation | Max out disk throughput | stress-ng, dd |
| PID exhaustion | Fork bomb to exhaust process table | Custom script |
| File descriptor exhaustion | Open files until ulimit reached | Custom script |

**stress-ng** is a versatile stress testing tool that can load CPU, memory, I/O, and various kernel interfaces simultaneously.

### Dependency Failure Simulation

Most production incidents involve **dependency failures**—downstream services, databases, caches, message queues:

```
┌──────────┐      ┌──────────────┐      ┌──────────┐
│ Service  │─────▶│   Database   │─────▶│  Cache   │
│   A      │      │  (PostgreSQL)│      │ (Redis)  │
└──────────┘      └──────────────┘      └──────────┘
     │                  │                     │
     │  Failure         │  Failure            │  Failure
     │  scenarios:      │  scenarios:         │  scenarios:
     ▼                  ▼                     ▼
  • DB connection     • Disk full           • Latency spike
    pool exhaustion     • Replication lag      • Connection refused
  • Query timeout       • Read replica fail    • Stale data
  • Slow queries        • Split brain          • Eviction storm
```

Simulation approaches:

- **Service mesh faults**: Istio VirtualService with fault injection (delay, abort)
- **Sidecar injection**: Envoy fault filter, Linkerd failure injection
- **Application-level**: circuit breaker testing, timeout configuration validation
- **Infrastructure**: terminate/restart pods, stop nodes, disconnect network segments

## Chaos Engineering Tools

| Tool | Platform | Key Features |
|------|----------|-------------|
| Chaos Monkey | AWS/AWS-native | Randomly terminates EC2 instances; origin of chaos engineering |
| LitmusChaos | Kubernetes | CRD-based, 50+ chaos experiments, GitOps integration |
| Chaos Mesh | Kubernetes | CRD-based, visual dashboard, network/CPU/IO faults |
| Gremlin | Multi-cloud | SaaS platform, attack types for network/host/app, blast radius control |
| AWS Fault Injection Simulator | AWS | Managed service, IAM-integrated, controlled blast radius |
| Toxiproxy | Any (proxy-based) | TCP proxy for network fault injection via API |
| powerfulseal | Kubernetes | Combines stress tests with kill scenarios |

### Chaos Mesh Architecture (Kubernetes)

```
┌─────────────────────────────────────────────┐
│             Chaos Mesh Control Plane        │
│  ┌─────────────────────────────────────┐    │
│  │  Chaos Dashboard (Web UI)           │    │
│  │  - Create/manage experiments       │    │
│  │  - View results, timelines         │    │
│  └─────────────────────────────────────┘    │
│  ┌─────────────────────────────────────┐    │
│  │  Chaos Controller (Manager)        │    │
│  │  - Orchestrates experiments        │    │
│  │  - Applies CRDs to target cluster  │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────┐
│           Target Kubernetes Cluster           │
│  ┌─────────┐ ┌─────────┐ ┌─────────────┐   │
│  │ PodChaos│ │NetChaos │ │ IOChaos     │   │
│  │ (kill,  │ │(latency,│ │ (disk,      │   │
│  │  stress)│ │ partition│ │  memory)    │   │
│  └─────────┘ └─────────┘ └─────────────┘   │
└─────────────────────────────────────────────┘
```

## Game Days

A **game day** is a planned, facilitated exercise where a team simulates a production incident in a controlled environment. Unlike automated chaos experiments, game days involve people, process, and tooling together:

### Game Day Structure

```
Pre-game:
  1. Define scenario (e.g., "primary database fails over to replica")
  2. Prepare environment (staging or production with safeguards)
  3. Assign roles (incident commander, operator, observer, scribe)
  4. Set success criteria (RTO/RPO targets, runbook steps validated)

Game day:
  1. Brief participants on scenario and safety boundaries
  2. Initiate failure (chaos engineering tool or manual)
  3. Observe response: detection time, diagnosis time, mitigation time
  4. Document findings: what worked, what failed, what was unclear

Post-game:
  1. Blameless retrospective
  2. Action items with owners and deadlines
  3. Update runbooks, on-call playbooks, alerting rules
  4. Schedule follow-up game day for unresolved issues
```

### Types of Game Days

| Type | Focus | Example |
|------|-------|---------|
| Component failure | Individual service/dependency failure | "Redis cache becomes unavailable" |
| Infrastructure failure | Platform-level failure | "Entire availability zone goes down" |
| Cascading failure | Multi-service interaction under stress | "Downstream latency spike propagates" |
| Data plane failure | Data consistency/corruption | "Replication lag causes stale reads" |
| Human process | On-call response quality | "Simulated page during off-hours" |

## Resilience Testing

### Resilience vs. Chaos Engineering

**Chaos engineering** discovers unknown failure modes through experimentation. **Resilience testing** validates that known failure modes are handled correctly:

- Chaos engineering: "What happens if we kill the leader node? Let's find out."
- Resilience testing: "We expect the leader to be re-elected in < 10 seconds. Let's verify."

### Resilience Testing Framework

```
┌─────────────────────────────────────────────────────┐
│              Resilience Test Suite                   │
│                                                      │
│  1. Failure Injection                               │
│     - Inject specific failure (timeout, crash, lag)  │
│                                                      │
│  2. Observable Outcome Measurement                  │
│     - SLO: error rate < 0.1% during failure         │
│     - RTO: recovery within 30 seconds                │
│     - RPO: no data loss                              │
│                                                      │
│  3. Automated Assertion                             │
│     - Compare measured vs. expected outcomes          │
│     - Pass/fail with evidence                        │
│                                                      │
│  4. Regression Tracking                             │
│     - Track resilience test results over time       │
│     - Detect regressions in recovery behavior       │
└─────────────────────────────────────────────────────┘
```

### Resilience Patterns to Test

| Pattern | What to Verify |
|---------|---------------|
| Circuit breaker | Opens after threshold failures, recovers after timeout |
| Retry with backoff | Retries with exponential backoff, doesn't amplify load |
| Bulkhead | Failure in one pool doesn't exhaust resources for others |
| Timeout | Requests fail fast when dependency is slow |
| Rate limiting | Graceful degradation under load spike |
| Graceful degradation | Reduced functionality when dependencies are unavailable |
| Leader election | New leader elected within SLA when current leader fails |

## Disaster Recovery (DR) Testing

DR testing validates that the organization can recover from catastrophic failures:

### DR Testing Levels

| Level | Name | What's Tested | Frequency |
|-------|------|--------------|------------|
| 1 | Tabletop | Walk through DR plan with stakeholders | Quarterly |
| 2 | Simulation | Simulate failure in staging environment | Monthly |
| 3 | Parallel execution | Run DR procedures alongside production | Quarterly |
| 4 | Full cut-over | Actually fail over to DR environment | Annually (or semi-annually) |

### Key DR Metrics

- **RTO (Recovery Time Objective)**: maximum acceptable downtime. "We must restore service within 4 hours."
- **RPO (Recovery Point Objective)**: maximum acceptable data loss. "We can lose at most 5 minutes of data."
- **RTO < RPO < RCO** (Recovery Consistency Objective): data must be consistent after recovery

### DR Testing Checklist

- [ ] Backup restoration verified (within RTO)
- [ ] Data integrity validated after restoration (checksums, row counts)
- [ ] DNS failover tested and timing measured
- [ ] Configuration management verified (infrastructure-as-code applies correctly to DR region)
- [ ] Runbook steps validated (each step works as documented)
- [ ] Communication plan tested (incident channels, customer notification)
- [ ] Rollback plan verified (can you fail back to primary?)
- [ ] Third-party dependencies available in DR region (APIs, SaaS, external services)

## Production Verification

### Production Readiness Review

Before launching a new service or major change, verify:

```
Production Readiness Checklist:
├── Observability
│   ├── Dashboards with key SLIs (latency, error rate, throughput)
│   ├── Alerts with correct thresholds and runbooks
│   ├── Distributed tracing configured
│   └── Logging with structured fields and trace correlation
│
├── Reliability
│   ├── SLOs defined with error budget policy
│   ├── Circuit breakers for all dependencies
│   ├── Graceful degradation path documented
│   └── Capacity tested (load testing, stress testing)
│
├── Resilience
│   ├── Chaos engineering experiments passing
│   ├── DR plan documented and tested
│   └── Blast radius limited (multi-AZ, no single points of failure)
│
├── Security
│   ├── Authentication/authorization configured
│   ├── Secrets management (no secrets in code/config)
│   ├── Network policies (least privilege)
│   └── Supply chain verified (signed images, SBOMs)
│
└── Operability
    ├── On-call rotation with runbook
    ├── Deployment pipeline with canary/progressive rollout
    ├── Rollback procedure tested
    └── Escalation path documented
```

### Blast Radius Control

Limit the impact of failures:

- **Multi-AZ / multi-region deployment**: no single infrastructure failure takes down the service
- **Bulkhead isolation**: separate connection pools, thread pools, and processes for different dependencies
- **Graceful degradation**: define fallback behavior for each dependency (cached response, default value, feature flag disable)
- **Progressive rollout**: canary → percentage → full; automatic rollback on SLO violation

### Progressive Delivery

```
Commit → Build → Test → Canary (1%) → Monitor (SLO check) → 10% → 50% → 100%

At each stage:
  - Compare SLOs (error rate, latency) against baseline
  - If SLO violation detected → automatic rollback
  - Manual approval gate at critical percentages (optional)
```

## Interview Angle

> **"How would you design a chaos engineering program for a company with 500 microservices?"**

Start with the highest-risk services (those handling money, user data, or with complex dependency graphs). Implement automated experiments as CI/CD pipeline gates: each deploy must pass resilience tests (circuit breaker fires, graceful degradation works, recovery within RTO). Use Chaos Mesh for K8s-native fault injection. Run monthly game days with cross-functional teams, focusing on realistic scenarios (multi-service cascading failures). Track resilience test results over time as a reliability metric alongside SLOs.

> **"Your service handles 10K RPS with a 99.99% SLO. How do you test that your DR plan actually works?"**

(1) Monthly: run chaos experiments in staging that simulate AZ failure, database failover, and cache invalidation. Measure RTO/RPO. (2) Quarterly: parallel DR execution—stand up the DR environment and run production traffic against it (shadow traffic or canary), verify data consistency and SLO compliance. (3) Annually: actual failover test—redirect production traffic to DR region, validate all SLOs, fail back. Document every discrepancy between expected and actual behavior. Use results to update runbooks and fix gaps.

## Key References

- Casey Rosenthal & Nora Jones, "Chaos Engineering: Building Confidence in System Behavior" (O'Reilly, 2020)
- Netflix Tech Blog — Chaos Monkey, Chaos Automation Platform
- Chaos Mesh documentation (chaos-mesh.org)
- Google SRE Book, Chapter 13 — Incident Response
- AWS Fault Injection Simulator documentation
- "Production Readiness Reviews at Google" (SREcon 2017)
