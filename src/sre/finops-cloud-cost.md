# FinOps and Cloud Cost Optimization

> "You can't reduce what you can't see; you can't govern what you can't attribute." — paraphrase of the FinOps Foundation's three-phase doctrine.

FinOps — "Cloud Financial Operations" — is the discipline of bringing financial accountability to variable-spend cloud infrastructure. It is the cultural and tooling answer to the single biggest surprise of the cloud era: that the unit economics of a service can flip from *amazing* to *bank-breaking* the moment the workload stops fitting the billing model you assumed at design time. The FinOps Foundation (a Linux Foundation working group founded in 2019 by practitioners from Atlassian, AWS, Google, Microsoft, and VMware) codifies the practice around three phases — **Inform, Optimize, Operate** — and a small set of primitives: unit economics, showback/chargeback, commitment-based discounts (reserved, savings plans, spot), and the unit-economics view that ties spend to a business denominator.

This chapter is the SRE-flavored version of that practice. The end state is not "cheaper" — it is *cost per request* as a tracked SLO-class metric, plotted next to latency and error rate on the same Grafana dashboard.

## The FinOps Lifecycle

The Foundation's three-phase model is iterative, not linear. A mature team runs all three in parallel every week.

```
              ┌──────────────────────────────────────────┐
              │              INFORM                      │
              │  Visibility: tag, allocate, allocate,    │
              │  aggregate, surface spend to engineers   │
              └────────────────────┬─────────────────────┘
                                   │
              ┌────────────────────▼─────────────────────┐
              │             OPTIMIZE                      │
              │  Right-size, reserve, schedule, terminate │
              │  waste, switch pricing models             │
              └────────────────────┬─────────────────────┘
                                   │
              ┌────────────────────▼─────────────────────┐
              │             OPERATE (Govern)             │
              │  Policies, budgets, anomaly alerts,       │
              │  rate-limit / freeze on overrun            │
              └────────────────────┬─────────────────────┘
                                   │
                                   └── feeds back into INFORM
```

### Phase 1 — Inform (Visibility)

The hardest phase, because it requires three things that orgs resist:

1. **Tagging policy.** Every cloud resource carries tags `team`, `service`, `env`, `cost-center`, `business-unit`. Untagged resources are blocked at provisioning time, not discovered later.
2. **Cost allocation rules.** Most spend is not directly taggable — shared services (Kubernetes control plane, VPC NAT gateways, shared load balancers) need to be split across consumers. AWS Cost Explorer supports split-charge and allocation rules; Kubecost does this natively for k8s by namespace and label.
3. **A daily-refresh dashboard** that engineers actually look at. Monthly reports are useless — by the time you see a $40k anomaly it's already next quarter's budget. Cost Explorer, CloudHealth, and Kubecost all support daily granularity.

Visibility is the precondition for everything else. A common failure mode: an org buys a $200k FinOps tool, skips the tagging policy, and the tool produces nothing actionable because 60% of spend is "untagged."

### Phase 2 — Optimize

Once spend is allocated, optimization is a small set of high-ROI moves:

| Lever | Description | Typical saving | Risk |
|---|---|---|---|
| Right-size instances | Replace `m5.2xlarge` at 12% CPU with `m5.large` | 20–50% per instance | low (if peak covered) |
| Commit to Reserved Instances / Savings Plans | 1- or 3-year commitment in exchange for discount | 30–60% off on-demand | medium (commitment lock-in) |
| Use Spot / Preemptible for stateless | Replace baseline on-demand with spot, plus on-demand buffer | 60–90% off baseline | high (interruptions) |
| Schedule non-prod | Turn off staging/dev nights & weekends | 60–70% off non-prod compute | low |
| Tier storage | Move objects > 30 days to Infrequent Access, > 90 days to Glacier | 40–80% off storage | low (retrieval cost) |
| Delete orphaned resources | Unattached EIPs, unmounted EBS, idle RDS | 5–10% of bill | none |
| Networking: VPC endpoints + data egress | Replace NAT-gateway-bound traffic with VPC endpoints | up to 50% off data egress | low |

The economics of commitment-based discounts deserve a section of their own — see **Pricing Models** below.

### Phase 3 — Operate (Governance)

The mature state: cost is treated like reliability — a budget, an alerting policy, and an explicit process when the budget is at risk.

- **Budgets per team / per service**, with soft (alert) and hard (block) thresholds.
- **Anomaly detection** — sudden spikes (a dev left a `c5.24xlarge` running, a tight loop logged 2 TB to CloudWatch) auto-alerted within the day.
- **Procurement and rate optimization** as a quarterly cadence, not a one-off. Commitments are reviewed and rebalanced.

The cultural hard part is *engineers see the spend they generate*. Without that, FinOps is a back-office function arguing with team leads over spreadsheets.

## Unit Economics: Cost Per Request, Cost Per User

The single most important mental shift in FinOps is from **absolute spend** to **unit economics**: spend normalized by a business denominator. Two reasons:

1. Absolute spend *should* grow when the business grows. A 30% spend increase is fine if revenue grew 40%. It is a crisis if revenue was flat.
2. Unit economics surfaces inefficiency that absolute spend hides. A $50k/month API can be wildly inefficient if it's serving 100 RPS at peak and idle at 90% the rest of the day.

### Choosing the denominator

| Denominator | Good when | Bad when |
|---|---|---|
| Cost per request | API-shaped services, request-response workloads | Batch / streaming jobs (no "request") |
| Cost per active user / DAU | Consumer-facing products with consistent traffic | B2B with very different account sizes |
| Cost per transaction (checkout, message sent) | Services tied to monetizable events | Internal platform services |
| Cost per GB processed | Data pipelines, ETL | User-facing services |
| Cost per feature-flag evaluation | Edge / config services | Backend services |

Pick *one* denominator per service. The rule is: the denominator should be (a) something the business already tracks as a KPI, (b) something an engineer can move with a code change, and (c) something that scales linearly-ish with the spend on that service. If you have all three, you have a FinOps metric you can put next to your SLO.

### Example: a payments API

```
Last 30 days:
  Requests served:           412,880,000
  AWS bill allocated to API:  $11,420
  Cost per million requests: $27.66

SLO dashboards:
  Availability  99.96%
  p99 latency   180 ms
  Cost / Mreq   $27.66   ← plotted as a 3rd SLO-class metric
```

When the next deploy pushes p99 from 180 ms to 165 ms *and* cost/Mreq from $27.66 to $34.10, that trade-off is explicit and on the dashboard. The team can make a real decision: the latency improvement is worth ~25% more spend, or it isn't.

## Showback and Chargeback

Two distinct models for surfacing cloud spend to engineering teams:

- **Showback**: spend is allocated and shown to teams as informational. The team does not pay; central engineering / IT covers the bill. The pressure to optimize is reputational, not financial.
- **Chargeback**: spend is allocated and *transferred* — the team's actual budget is debited. Pressure is direct: optimize or run out of money.

| Property | Showback | Chargeback |
|---|---|---|
| Who pays | Central | The team |
| Behavior change | Slow (cultural) | Fast (financial) |
| Overhead | Low | High (budget transfers, internal accounting) |
| Best for | Phase 1 / org maturity 1–3 | Mature org, clear P&L boundaries |
| Failure mode | "Interesting, but not my problem" | Teams under-prod to save money, break reliability |

The FinOps Foundation's guidance, confirmed in their State of FinOps survey, is to *start with showback* and graduate to chargeback only when teams have (a) a tagging policy that's >90% complete, (b) a daily dashboard engineers look at, and (c) quarterly optimization OKRs. Premature chargeback tends to produce a wave of "shadow IT" — engineers sign up for credit cards to avoid internal accounting.

## Pricing Models: On-Demand, Reserved, Savings Plans, Spot

AWS, Azure, and GCP all expose the same four pricing models with slightly different names. The trade-off is always **price vs flexibility**.

```
                  price ↓    flexibility ↓
   Spot          ████████████  Interruptible (2-min warning), stateless only
   3-yr Reserved ████████░░░  Locked to instance family/region for 3 years
   1-yr Reserved ██████░░░░░  Locked for 1 year, can exchange / modify
   Savings Plan  ██████░░░░░  Locked $/hr commitment, flexible across family/region
   On-Demand     ██░░░░░░░░░  Most flexible, most expensive
```

| Model | Discount vs on-demand | Lock-in | Best for |
|---|---|---|---|
| On-Demand | 0% | none | Spiky workloads, dev, prototyping |
| 1-yr Reserved Instance (RI) | ~30–40% | instance family + region | Stable baseline load |
| 3-yr Reserved Instance | ~50–60% | instance family + region | Multi-year stable workloads |
| Compute Savings Plan (1-yr or 3-yr) | ~30–50% | $/hr commitment, *flexible* | Mix of instance families, regions |
| Spot / Preemptible | up to 90% | can be reclaimed with 2-min warning | Stateless, fault-tolerant, batch |

### Reserved Instances vs Savings Plans

The biggest practical decision is between **RIs** and **Savings Plans**.

- **RI**: a discount on a *specific instance family + size + region + tenancy + OS*. You commit to (say) `m5.2xlarge` Linux in `us-east-1` for a year. If you later want to run `c5.xlarge` instead, the RI doesn't apply.
- **Savings Plan**: a discount in exchange for a *dollar-per-hour commitment* to compute spend, regardless of instance family, size, OS, or region (within the same plan: compute, or EC2-instance). If you commit to $10/hr and your bill is `m5` in the morning and `c5` in the afternoon, the plan covers both.

Savings Plans are strictly more flexible and are recommended for most modern (autoscaling, multi-AZ, multi-family) workloads. RIs still win in two cases: (1) steady-state single-family workloads like a primary database, (2) when you want to commit to specific instance types to discourage sprawl.

### Spot economics

Spot is up to 90% off on-demand but can be reclaimed with a 2-minute warning. The economics make sense only if:

1. The workload is **interruptible** — stateless web tier, batch, CI/CD workers, Spark workers. Not databases, not single-leader queues.
2. The workload **handles interruption gracefully** — k8s `node-rescheduler` / AWS Node Termination Handler drains pods, application retries, queues checkpoint.
3. There is a **buffer of on-demand** for capacity. Spot is not "always available when needed"; you still need 30–50% on-demand for guaranteed capacity at peak.

The standard pattern: 70% spot + 30% on-demand baseline, with autoscaling bringing in more on-demand when spot gets constrained. For workloads that cannot tolerate interruption, use reserved / savings plans.

## Multi-Cloud Cost Comparison

The honest answer on multi-cloud cost is that it is almost never worth it *for cost reasons*. Multi-cloud is justified by data sovereignty, latency, vendor lock-in avoidance, or procurement leverage — not by raw price. The reasons:

- The three clouds price the *same* resources at *similar* levels. AWS, Azure, and GCP all watch each other's price list; first-party services match within ~10%.
- Each cloud has a discount / commitment program (AWS RIs, Azure Reservations, GCP Committed Use Discounts) and the savings are similar in order of magnitude.
- The *real* cost differences are in egress pricing (GCP egress to internet is competitive; AWS egress to internet is high; intra-region traffic is free on AWS, metered on Azure), in *managed services* pricing (Cloud Spanner vs Aurora vs Azure SQL Hyperscale diverge by workload), and in *commitment trade-offs* (GCP CUDs apply broadly to compute, AWS RIs are family-specific).

| Dimension | AWS | Azure | GCP |
|---|---|---|---|
| Compute commitment | RIs (family-specific) or Savings Plans ($) | Reservations (instance-specific) | CUDs (resource-based, $/vCPU·hr flexible) |
| Spot naming | Spot Instances | Spot VMs | Spot VMs / Preemptible (slightly different reclaim) |
| Egress to internet (per GB, region varies) | ~$0.09 | ~$0.087 | ~$0.085 (tiered) |
| Free tier of egress (out) | 100 GB/mo | 100 GB/mo | 200 GB/mo (GCP's edge) |
| Native cost tool | AWS Cost Explorer | Azure Cost Management | GCP Billing / Recommender |

For most orgs: pick one cloud, push hard on commitment discounts, and only consider multi-cloud when one of the four real drivers above applies. The FinOps Foundation's State of FinOps report consistently shows >90% of mature FinOps teams are single-cloud-primary, with multi-cloud as a secondary strategy.

## Tools

| Tool | Scope | Strength | Weakness |
|---|---|---|---|
| **AWS Cost Explorer** | AWS-native | Free, fast, integration with AWS Organizations, budgets + anomaly detection | AWS only; allocation rules limited |
| **Azure Cost Management** | Azure-native | Free, deeply integrated with Azure policy | Azure only |
| **GCP Billing / Recommender** | GCP-native | Free, Recommender gives actionable rightsizing | GCP only; UI is opaque |
| **CloudHealth (VMware/Broadcom)** | Multi-cloud | Mature multi-cloud allocation, chargeback-ready reports | Expensive; requires careful tagging |
| **Apptio Cloudability** | Multi-cloud | Strong on showback/chargeback, finance workflows | Expensive; complex implementation |
| **Kubecost** | Kubernetes-native | Allocates k8s spend by namespace, label, deployment; open-core | k8s only (but covers the hardest allocation problem) |
| **OpenCost** | Open source | The CNCF sandbox project Kubecost is built on | Self-hosted; needs TLC |
| **Vantage** | Multi-cloud | Modern UI,工程师-friendly, Terraform-native | Smaller vendor |

The pragmatic stack for a k8s-heavy team is:

1. **AWS Cost Explorer / Azure Cost Management / GCP Billing** as the source of truth for cloud-spend totals and budgets.
2. **Kubecost (or OpenCost)** to allocate k8s spend by namespace and surface per-service unit economics.
3. A **showback** dashboard (Kubecost's, or a custom Grafana panel fed by Cost Explorer API) that engineers see in the same place they see SLOs.

The wrong instinct is to buy a single $300k/yr enterprise tool and call FinOps done. Tools do not enforce tagging policies; people do. The right stack is *small* and *looked at daily*.

## Cost of Reliability — the SRE Lens

For SREs, the FinOps lens is most useful when applied to the **cost of reliability choices**:

- Multi-region active-active doubles compute cost. Is the SLO improvement worth it? Compute the *revenue protected* per region-failure and compare to the spend.
- 99.99% availability has roughly 4× the cost of 99.9% (more redundancy, more idle capacity, more cross-region traffic). The error-budget math has to make this worth it — see [the SLO chapter](./slo-error-budget.md).
- Auto-scaling maxima determine spot-instance exposure. A high `maxReplicas` buys safety but also commits to spend on spike. Model the *99th-percentile* spend, not the average.
- Logging and observability spend is often 15–30% of the cloud bill. Sampling, log levels, and short retention on hot paths are pure cost wins with low reliability cost.

## Interview Questions

**Q1: What is FinOps and how does it differ from cloud cost optimization?**
A: FinOps ("Cloud Financial Operations") is the *cultural and operational* practice of bringing financial accountability to variable-spend cloud. It is broader than cost optimization: it includes visibility (tagging, allocation, daily dashboards), optimization (right-sizing, commitments, spot, scheduling), and governance (budgets, anomaly alerts, policy). The FinOps Foundation codifies this as the three-phase Inform/Optimize/Operate cycle. Optimization is one phase of FinOps, not the whole thing.

**Q2: How do you choose between Reserved Instances and Savings Plans on AWS?**
A: Savings Plans are *strictly more flexible* — they are a $/hr commitment that applies across instance families, sizes, OS, and regions. RIs are a discount on a *specific* instance family + region + size + tenancy + OS. For most modern autoscaling multi-AZ workloads, Savings Plans win. RIs still make sense for (a) steady-state single-family workloads like a primary database where you *want* the lock-in to discourage sprawl, and (b) very stable workloads where you can confidently commit 3 years for the deeper discount.

**Q3: What is the difference between showback and chargeback, and when would you move from one to the other?**
A: Showback is surfacing allocated spend to teams as *informational* — they see what they spend but central IT pays. Chargeback is *transferring* the spend — the team's budget is debited. Showback changes behavior slowly through culture; chargeback changes behavior fast through budget pressure but is operationally heavy (internal accounting) and risks teams under-provisioning reliability to save money. The FinOps Foundation's guidance is to start with showback and only graduate to chargeback when tagging is >90% complete, daily dashboards exist, and teams have quarterly optimization OKRs. Premature chargeback produces shadow IT.

**Q4: How would you build a unit-economics dashboard for a payments API?**
A: Pick one denominator that the business already tracks and that engineers can move: cost per million requests. Stream `RequestCount` from the API's metrics into a daily cost-allocation pipeline that joins with AWS Cost Explorer allocation for the `service=payments-api` tag. Plot `cost / Mreq` on the same Grafana dashboard as availability, p99 latency, and error rate. Set a soft budget alert when the metric climbs >15% week-over-week and a hard alert when it climbs >30%. The point is to make cost trade-offs explicit — when a deploy lowers p99 from 180 to 165 ms but raises cost/Mreq from $28 to $34, that trade-off is visible in the same place engineers look at reliability.

**Q5: When is multi-cloud justified for cost reasons?**
A: Almost never for raw price. The three hyperscalers watch each other's price list and match within ~10% on equivalent SKUs. Multi-cloud *is* justified for (a) data sovereignty (a regulator requires certain data in-country on a specific provider), (b) latency (regional presence AWS lacks), (c) procurement leverage (using the threat of a second cloud to negotiate better terms), or (d) avoiding single-vendor lock-in on a strategically important workload. The real cost differences are in egress (GCP gives 200 GB/mo free vs 100 GB on AWS) and managed-service pricing (Aurora vs Spanner vs Azure SQL Hyperscale diverge by workload shape) — but these are workload-specific, not blanket.

## References

- [FinOps Foundation — What is FinOps?](https://www.finops.org/introduction/what-is-finops/)
- [FinOps Foundation — State of FinOps report (annual)](https://data.finops.org/)
- [AWS Cost Explorer — User Guide](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html)
- [AWS Savings Plans — Documentation](https://aws.amazon.com/savingsplans/)
- [Google Cloud — Committed Use Discounts](https://cloud.google.com/compute/docs/instances/committed-use-discounts)
- [Kubecost — Documentation](https://docs.kubecost.com/)
- [OpenCost — CNCF sandbox project](https://www.opencost.io/)
- [VMware CloudHealth — Cloud Cost Management](https://www.vmware.com/products/cloudhealth.html)
- [Microsoft Azure — Cost Management documentation](https://learn.microsoft.com/azure/cost-management-billing/cost-management-billing-overview)
