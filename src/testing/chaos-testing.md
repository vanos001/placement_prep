# Chaos Testing

## Overview

Chaos testing is the empirical investigation of a distributed system's resilience by injecting controlled failures — killing processes, dropping packets, exhausting resources, desynchronizing clocks — and observing whether the system continues to meet its steady-state SLOs. It is *not* random breakage for its own sake; it is the scientific method applied to production reliability. Each experiment starts with a hypothesis ("the system will keep serving at p99 < 200ms with error rate < 0.1% if any single node dies"), introduces a *specific* failure, and measures whether the steady-state holds. If it does, the system is resilient to that failure; if it doesn't, you have found a weakness to fix before the failure happens for real.

The discipline was pioneered at Netflix in 2011 with the Chaos Monkey, a service that randomly terminated production instances during business hours. The motivation was the company's migration from a self-managed data center to AWS: every part of the stack now ran on instances that could disappear at any moment, and the engineering team needed proof their software would survive. The experiment revealed that the database backups were misconfigured (one killed instance held the only copy of an index), that some services had implicit single points of failure, and that autoscaling rules assumed a longer startup time than reality allowed. The 2014–2016 Simian Army extended Chaos Monkey to Latency Monkey (inject network latency between services), Conformity Monkey (flag non-conforming instances), Doctor Monkey (health-check and quarantine). Netflix's experience, codified in the 2016 book *Chaos Engineering* by Casey Rosenthal, Nora Jones, and the Netflix SRE team, defines the discipline.

## The Anatomy of a Chaos Experiment

Beyer et al. describe a chaos experiment as a four-part artifact: steady state, hypothesis, intervention, blast radius. Without all four explicitly written down, what you are doing is *not* chaos engineering — it is operational debugging with extra steps.

```
+-------------------------------------------------------------+
|                   CHAOS EXPERIMENT                          |
+-------------------------------------------------------------+
|                                                             |
|  1. STEADY-STATE HYPOTHESIS                                 |
|     "Under normal conditions, the checkout API serves       |
|      1000 rps with p99 < 200ms and error rate < 0.1%."     |
|     Metric: API latency p99, error rate                   |
|     Source: Prometheus at http://prom/api/v1/query        |
|                                                             |
|  2. HYPOTHESIS                                             |
|     "If any single checkout pod is terminated, p99         |
|      will stay below 400ms and error rate below 1%        |
|      for the duration of the experiment."                  |
|                                                             |
|  3. INTERVENTION (the chaos)                               |
|     Kill one random checkout pod every 60 seconds         |
|     for 5 minutes; do not exceed 1 killed at a time.      |
|                                                             |
|  4. BLAST RADIUS                                           |
|     Namespace: production                                  |
|     Service: checkout-svc (3 replicas, max 1 down)        |
|     Tenant: exclude customer_tier=enterprise              |
|     Rollback: auto-abort if error rate > 2%               |
|                                                             |
+-------------------------------------------------------------+
```

**Steady state** is a measurable, time-series representation of "system working correctly." It is defined by SLOs (see [SLO/SLI/SLA](../sre/slo-sli-sla.md)) — latency p99, error rate, throughput, queue depth, retry count. Without a steady-state metric you can query continuously, you cannot tell whether the experiment broke anything.

**Hypothesis** is the falsifiable prediction: "under intervention X, steady-state metric Y stays within bounds Z." This is what distinguishes chaos engineering from fault injection — the latter injects failures to see *what happens*, the former injects failures to *test a prediction*. A hypothesis you cannot falsify is not a hypothesis; it is a wish.

**Intervention** is the actual chaos injected: kill a pod, add 500ms network latency between two services, fill the disk to 95%, skew the clock by 200ms. The intervention must be *reversible* and *bounded* — you must be able to stop it and the system must return to steady state within seconds.

**Blast radius** is the scope of impact you accept. Start with a single instance in a non-production environment; expand to staging; eventually run in production but only during business hours when on-call is fresh, with the abort threshold set so that real customer impact is bounded to a small window. The cardinal rule: a chaos experiment must never cause more damage than the failure it is meant to prepare for.

## The Four Principles

Beyer et al. state the methodology as four principles — *vary, disrupt, observe, verify* — that apply to every experiment, regardless of tool.

1. **Vary (Hypothesize about steady state).** Define a measurable steady state and a hypothesis that the system will continue to meet it under the planned intervention. Without this, the experiment has no pass/fail criterion.
2. **Disrupt (Inject the failure).** Apply the intervention — kill, delay, deny, exhaust, corrupt — within the agreed blast radius. The intervention must be representative of a real failure the system could plausibly encounter.
3. **Observe (Watch the system).** Capture steady-state metrics before, during, and after the intervention. Watch secondary signals (CPU, memory, queue depth, retry rate, log volume) that may reveal cascading effects the primary metric misses.
4. **Verify (Decide pass/fail).** Compare the observed metrics against the hypothesis. Pass = steady state held, the system is resilient to this failure. Fail = hypothesis was wrong; either fix the system or amend the hypothesis and re-run. Both outcomes produce information.

```
        vary                  disrupt
          |                      |
          v                      v
   +-------------+       +----------------+
   | define SLO  |  -->  | inject failure |
   | + hypothesis|       | (bounded)     |
   +-------------+       +-------+--------+
                                  |
                                  v
                          +----------------+
                          | observe metrics|
                          | (steady state  |
                          |  + sidebands)  |
                          +-------+--------+
                                  |
                                  v
                          +----------------+
                          | verify vs     |
                          | hypothesis    |
                          +-------+--------+
                                  |
                          pass? --+-- fail?
                          |              |
                          v              v
                  record success    file bug, fix, re-run
```

This loop is the discipline. It runs continuously in mature deployments — not as a one-off "game day" but as a recurring experiment in production, gated by automated abort thresholds.

## Tools

| Tool | Origin / Platform | Approach | Typical Use |
|------|---------------------|----------|--------------|
| **Chaos Monkey** | Netflix / AWS (spans EC2) | Random instance termination | Continuous production resilience baseline |
| **Chaos Mesh** | Alibaba / Kubernetes | CRDs for pod kill, network delay, IO error, time skew | Kubernetes-native, namespace-scoped chaos |
| **Litmus** | MayaData / Kubernetes | CRD + ChaosEngine + ChaosExperiment; large experiment hub | Kubernetes chaos with replayable YAML experiments |
| **AWS Fault Injection Service (FIS)** | AWS | Managed service injecting CPU stress, network blackhole, instance stop, disk fill on EC2/ECS/EKS | AWS-native, integrated with CloudWatch alarms for auto-abort |
| **Gremlin** | Gremlin Inc. | SaaS chaos platform; CPU, IO, network, DNS, process, time | Enterprise chaos with strong safety controls |
| **Toxiproxy** | Shopify | Network proxy that adds latency, jitter, blacklist, timeouts, bandwidth limits | Application-level network chaos |
| **PowerfulSeal** | Bloomberg | Kubernetes chaos engine; kills pods, nodes; scenario-based | Multi-cloud K8s chaos |
| **Chaos Toolkit** | ChaosIQ | Python framework for writing chaos experiments as JSON/YAML | Reference implementation of the four principles |

A Chaos Mesh experiment in CRD form is illustrative. It is just another Kubernetes resource, applied with `kubectl apply`, scoped to a namespace, with a selector on pods, and a duration:

```yaml
# network-delay.yaml — inject 500ms latency between checkout and payment
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: checkout-payment-delay
  namespace: production
spec:
  action: delay          # delay, loss, duplicate, corrupt, partition...
  mode: all              # apply to all matching source pods
  selector:
    namespaces: [production]
    labelSelectors:
      "app": "checkout"
  direction: to          # only egress traffic
  target:                # apply only to traffic to these pods
    selector:
      namespaces: [production]
      labelSelectors:
        "app": "payment"
    mode: all
  delay:
    latency: "500ms"
    correlation: "0"
    jitter: "50ms"
  duration: "60s"
  scheduler:
    cron: "@every 30m"   # repeat
```

A Litmus experiment looks similar (a `ChaosEngine` CRD references a `ChaosExperiment` template, with the actual chaos logic in a `ChaosResult`):

```yaml
apiVersion: litmuschaos.io/v1alpha1
kind: ChaosEngine
metadata:
  name: pod-kill-checkout
  namespace: production
spec:
  appinfo:
    appns: production
    applabel: "app=checkout"
  chaosServiceAccount: litmus-admin
  experiments:
    - name: pod-delete
      spec:
        components:
          env:
            - name: TOTAL_CHAOS_DURATION
              value: "30"
            - name: CHAOS_INTERVAL
              value: "5"
            - name: FORCE
              value: "false"
            - name: PODS_AFFECTED_PERC
              value: "33"
        probe:        # the verification step
          - name: checkout-latency-probe
            type: httpProbe
            mode: Continuous
            httpProbe:
              url: http://checkout/api/health
              method: { get: { criteria: { responseCode: "200" } } }
```

Litmus probes are the explicit `verify` step in CRD form — the experiment aborts if the probe fails. AWS FIS expresses the same idea with `CloudWatchAlarm` abort conditions:

```json
{
  "Targets": [
    { "Key": "Instances", "Value": "checkout-asg", "ResourceType": "aws:ec2:autoscaling-group" }
  ],
  "Actions": [
    {
      "ActionType": "aws:ec2:terminate-instances",
      "Parameters": { "DurationBeforeScaleIn": "PT2M" },
      "Targets": { "Instances": "Instances" }
    }
  ],
  "StopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "checkout-error-rate-high"
    }
  ]
}
```

## Comparison to Resilience Testing

**Resilience testing** is the older umbrella — testing how the system behaves under failure — and includes both passive techniques (fault injection in staging, dependency-failure unit tests, circuit-breaker tests) and active techniques (chaos engineering). The distinction most practitioners draw is:

| Dimension | Resilience Testing | Chaos Engineering |
|-----------|--------------------|--------------------|
| **Where** | Typically staging | Production (or staging first, then production) |
| **When** | Release gate; pre-deployment | Continuously; game days; ad hoc |
| **Hypothesis** | Often implicit ("does it handle X?") | Explicit and falsifiable |
| **Failure set** | Hand-picked, exhaustive on small surface | Sampled, broad on large surface |
| **Scope** | Single component or pair | Whole system, real-world conditions |
| **Goal** | Pass the test | Discover unknown unknowns |

Resilience testing asks "does the system handle the failures we anticipated?" Chaos engineering asks "what failures did we fail to anticipate?" The two are complementary: a robust test suite includes both. Pure resilience testing on its own tends to ossify around the failures engineers already thought of, missing the cascading, multi-failure scenarios that actually take production down. Pure chaos engineering without underlying resilience testing produces a steady stream of surprises without the basic safety net to catch them.

A useful framing: resilience testing is the test pyramid's broad base (many fast tests of anticipated failures); chaos engineering is the apex (few, expensive experiments that probe the unknown). Both are required; neither is sufficient.

## Production Use

**Netflix** runs Chaos Monkey continuously in production, terminating instances during business hours (so the on-call team is fresh and the customer impact window is bounded). The Simian Army project retired some of its components in 2019 in favor of focused, well-instrumented chaos (ChAP — the Chaos Automation Platform — runs targeted experiments with automated SLO tracking). Netflix's MSL (Microservice Studio Lab) and the broader Failure Injection Testing framework extend chaos into multi-region scenarios.

**Amazon/AWS** runs Fault Injection Service (FIS, GA 2021) in production for its own services, including DynamoDB and S3. The infamous 2015 DynamoDB us-east-1 outage led to a multi-year investment in failure injection as a continuous discipline — AWS now routinely tests regional failover for its own managed services. FIS supports stress on CPU, memory, disk; network blackhole and bandwidth limits; and "stop EC2 instance" with controlled ScaleIn. https://aws.amazon.com/fis/

**Microsoft** runs chaos internally on Azure; the Azure chaos engineering platform (Azure Chaos Studio, GA 2022) is the commercial version. **Google** uses chaos at scale for its Site Reliability Engineering practice; Google's 2020 SRE book chapter on chaos engineering describes "Disaster Recovery Game Days" as a recurring practice. **Dropbox** migrated from self-hosted chaos to Litmus when it moved to Kubernetes. **Target**, **National Australia Bank**, and **Mercedes-Benz** are public Litmus case studies.

**AWS's 2019 Deep Dive on FIS** documents the design constraints: abort within 5 seconds of an SLO breach, never affect more than the configured blast radius, log every action for audit. FIS's safety model is a useful reference for any in-house chaos platform.

## Game Days

A **game day** is a scheduled, team-wide chaos exercise. The structure (Netflix, Gremlin, AWS all recommend similar):

1. **Plan (1 week ahead):** Define the experiment, the SLO, the abort threshold, the rollback procedure. Notify stakeholders. Schedule for business hours.
2. **Execute (the day):** Run the experiment; the team observes dashboards, alerts, response time, customer-impact channels. A facilitator runs the chaos; everyone else watches.
3. **Observe (during):** Collect metrics, screenshots, alert timelines, customer reports. The facilitator calls abort if any threshold trips.
4. **Discuss (after):** What worked? What didn't? What did we learn? What needs to be fixed?
5. **Action items (the next sprint):** Bug tickets, runbook updates, autoscale tuning, monitoring additions. A game day without action items is just a party.

Game days surface organizational bugs as often as technical ones — on-call runbooks that are stale, alert fatigue that drowns the real signal, dashboards that don't show the metric that actually moved. Each game day should produce concrete fixes that go into the next sprint's backlog.

## Pitfalls and Best Practices

- **Start small.** Single instance in staging first. Graduate to single instance in production only when staging has been green for weeks. Expand blast radius incrementally.
- **Always have an abort.** Every experiment must have an automated abort threshold (CloudWatch alarm, Chaos Mesh `pauseAfter` plus probe, Litmus probe failure) that stops the chaos if real SLOs break. A chaos experiment without an abort is just vandalism.
- **Don't chaos during deployments.** Chaos and deploys in the same window is the source of most chaos incidents; gate chaos on no-active-deploy.
- **Pre-flight dry run.** Most tools have a `--dry-run` mode that simulates the experiment without injecting. Run it; check the selector matches what you expect.
- **Beware blast radius creep.** A `labelSelector` that's too broad will kill pods you didn't intend to. Use `mode: fixed` with a numeric limit, and `PodsAffectedPerc` in Litmus, to bound the count.
- **Don't chaos what you can't observe.** If you can't see the metric in real time, you can't verify the hypothesis — and you can't abort. Observability first, chaos second.
- **Don't chaos alone.** A chaos experiment run by one person with no second pair of eyes is how incidents happen. Have a facilitator and an observer.
- **Frequency matters more than intensity.** A 5-minute experiment weekly is more valuable than a 2-hour game day quarterly. Repetition catches regressions; one-off events surface one bug.

## Interview Questions

**Q1: What is chaos engineering and what problem does it solve?**
A: The empirical investigation of a distributed system's resilience by injecting controlled failures and observing whether steady-state SLOs hold. It solves the problem of unknown unknowns — failures the team didn't anticipate in design or resilience testing. By running experiments continuously in production, the team discovers and fixes these weaknesses before they cause real incidents.

**Q2: Describe the anatomy of a chaos experiment.**
A: Four parts: steady-state hypothesis (measurable SLOs the system meets normally), hypothesis (falsifiable prediction that SLOs hold under intervention), intervention (the specific failure injected — kill, delay, deny, exhaust), and blast radius (scope of impact, abort threshold, rollback procedure). Without all four explicitly written down, what you're doing is debugging, not chaos engineering.

**Q3: What are the four principles of chaos engineering?**
A: Vary (define steady state and hypothesis), disrupt (inject the failure), observe (collect metrics before/during/after), verify (compare observation to hypothesis and decide pass/fail). Both outcomes — pass (resilient) or fail (weakness found) — produce information. The loop is continuous, not one-off.

**Q4: Compare Chaos Monkey, Chaos Mesh, Litmus, and AWS FIS.**
A: Chaos Monkey (Netflix) terminates random EC2 instances; oldest tool, spans EC2 only. Chaos Mesh (Alibaba) is Kubernetes-native via CRDs for pod, network, IO, and time chaos. Litmus (MayaData) is also Kubernetes-native with CRDs and a large experiment hub; its distinguishing feature is the ChaosResult object and rich probe framework. AWS FIS is a managed service for AWS-native chaos with CloudWatch abort conditions and tight integration with EC2, ECS, EKS, and ASGs. Choose by platform: EC2 → Chaos Monkey or FIS; Kubernetes → Chaos Mesh or Litmus; multi-cloud enterprise → Gremlin.

**Q5: How does chaos engineering differ from resilience testing?**
A: Resilience testing asks "does the system handle the failures we anticipated?" and is typically run as a release gate in staging with hand-picked failures. Chaos engineering asks "what failures did we fail to anticipate?" and is run continuously in production with sampled, broad failures and explicit falsifiable hypotheses. Resilience testing is the broad base of the test pyramid; chaos engineering is the apex. Both are required.

**Q6: What is a game day and why run one?**
A: A scheduled, team-wide chaos exercise: plan the experiment, run it with a facilitator and observers, watch dashboards in real time, abort on threshold breach, then debrief and produce action items. Game days surface both technical weaknesses (broken circuit breakers, misconfigured autoscale) and organizational ones (stale runbooks, alert fatigue, dashboards missing the metric that actually moved). Action items go into the next sprint's backlog — a game day without action items is just a party.

## References

- Beyer, B., Jones, C., Petoff, J., Murphy, N. R. (eds.) (2016). *Site Reliability Engineering*. O'Reilly. The SRE book has multiple chapters on failure injection and chaos.
- Rosenthal, C., Jones, N., Merz, S. (2017). *Chaos Engineering*. O'Reilly. The canonical book by the Netflix team.
- [Chaos Mesh documentation](https://chaos-mesh.org/docs/) — Kubernetes-native chaos via CRDs; source at https://github.com/chaos-mesh/chaos-mesh
- [Litmus Chaos documentation](https://docs.litmuschaos.io/) — Kubernetes chaos with CRDs and an experiment hub; source at https://github.com/litmuschaos/litmus
- [AWS Fault Injection Service](https://aws.amazon.com/fis/) — managed fault injection for AWS resources with CloudWatch abort conditions
- [Netflix Tech Blog — Chaos Engineering at Netflix](https://netflixtechblog.com/tagged/chaos-engineering) — the original Chaos Monkey team's writings
- [Principles of Chaos Engineering](https://principlesofchaos.org/) — community statement of the methodology
- See also: [SRE Chaos Engineering](../sre/chaos-engineering.md), [SLO/SLI/SLA](../sre/slo-sli-sla.md), [Circuit Breakers](../distributed/microservices/circuit-breakers.md), [Resilience Patterns](../sre/reliability-patterns.md)
