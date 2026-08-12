# Chaos Engineering

## Principles

1. **Build a hypothesis** about steady-state behavior
2. **Vary real-world events** (server failure, network latency, resource exhaustion)
3. **Run experiments** in production (or staging)
4. **Automate** experiments to run continuously
5. **Minimize blast radius** (start small, expand gradually)

## Steady State Hypothesis

```
"Under normal conditions, our API serves 1000 rps with p99 < 200ms 
and error rate < 0.1%."

If this holds during chaos experiment → system is resilient.
If this breaks → found a weakness to fix.
```

## Common Experiments

| Experiment | Tool | What It Tests |
|---|---|---|
| Kill a server | Chaos Monkey | Failover, redundancy |
| Add network latency | TC, Toxiproxy | Timeouts, retries |
| Fill disk | dd, chaos-mesh | Alerting, cleanup |
| CPU stress | stress-ng | Autoscaling, throttling |
| DNS failure | Block DNS | Fallback, caching |
| Dependency failure | Mock server | Circuit breakers |

## Tools

| Tool | Platform | Approach |
|---|---|---|
| **Chaos Monkey** | AWS | Random instance termination |
| **Litmus** | Kubernetes | CRD-based experiments |
| **chaos-mesh** | Kubernetes | Pod/network/IO chaos |
| **Gremlin** | Multi-cloud | SaaS chaos platform |
| **Toxiproxy** | Network | Proxy with fault injection |

## Game Days

Scheduled chaos experiments with the full team:

1. **Plan**: Define experiment, expected outcome, rollback plan
2. **Execute**: Run experiment while team observes
3. **Observe**: Monitor dashboards, alerts, response time
4. **Discuss**: What worked, what didn't, what to improve
5. **Action items**: Fix weaknesses found

## Blast Radius Control

- Start in staging, graduate to production
- Start with single instance, expand gradually
- Use feature flags to control experiments
- Have automated rollback
- Time-box experiments
- Exclude critical paths initially

## Interview Questions

**Q: What is chaos engineering?**
A: Intentionally injecting failures into systems to find weaknesses before they cause real outages. The goal is to build confidence in the system's ability to handle turbulent conditions. Netflix pioneered this with Chaos Monkey.

**Q: How do you safely run chaos experiments in production?**
A: (1) Define steady-state metrics, (2) start with smallest blast radius, (3) have automated rollback, (4) time-box the experiment, (5) exclude critical paths initially, (6) run during low-traffic periods, (7) have the team watching dashboards.

**Q: What is a Game Day?**
A: A scheduled chaos engineering exercise where the team practices responding to failures. Similar to fire drills. The team runs chaos experiments, observes system behavior, and identifies improvement opportunities. Builds muscle memory for incident response.

## References

- [Principles of Chaos Engineering](https://principlesofchaos.org/)
- [Netflix Chaos Engineering](https://netflix.github.io/chaosmonkey/)
- [Chaos Engineering Book — Casey Rosenthal](https://www.oreilly.com/library/view/chaos-engineering/9781491988459/)
