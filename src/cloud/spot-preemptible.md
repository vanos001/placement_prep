# Spot and Preemptible Instances

Buying someone else's idle capacity is the deepest discount in cloud computing - and the only one that can be revoked at any moment. Spot (AWS), Spot VMs (GCP), and Spot/Low-priority (Azure) sell the same product: spare capacity that the provider can take back on short notice, typically at 60-90% below on-demand prices. The engineering question is not whether the discount is real (it is), but how much of it survives contact with an interruption rate, and what infrastructure you must build to collect the remainder.

## The Deal, Precisely

The three big providers differ in mechanics more than in economics:

| Aspect | AWS Spot | GCP Spot VM | Azure Spot VM |
|---|---|---|---|
| Typical discount | up to ~90% vs on-demand | fixed 60-91% vs on-demand | up to ~90% vs pay-as-you-go |
| Pricing model | market-driven, varies by pool | fixed discount, no bidding | fixed max price you set |
| Interruption notice | 2 min (instance reboot/hibernate options) | 30 s | 30 s |
| Eviction reason | capacity + price ceiling | capacity only | capacity + your max price |
| Max runtime | none | none (Spot VMs; old Preemptible had 24 h cap) | none |

Two design consequences fall out of this table. First, because AWS spot prices vary by *availability-zone pool*, the same instance type can be 3x cheaper in one AZ than a neighboring one - fleet diversification across instance types *and* AZs is the single biggest lever on both cost and interruption frequency. Second, the 30-second notices on GCP/Azure are wall-clock deadlines that start when the provider *sends* the signal; by the time your application notices and reacts, 25 of those seconds may be gone, so the eviction path has to be nearly free of work.

The eviction signal itself is metadata: AWS exposes it via the instance metadata service (`SpotInstanceRequestId`, plus the `instance-action` item that flips to `terminate`) and an EventBridge event; GCP pushes a `compute.instances.preempted` operation and sets a bit in the metadata server; Azure delivers a Scheduled Events document on the imds endpoint. A well-built worker polls this endpoint every few seconds and treats "notice received" as a hard deadline to flush state.

## What an Interruption Actually Costs

The naive cost model is "spot price x hours", which is the price of the *happy path*. The honest model is expected cost per *finished* job, and it has a denominator most teams forget:

```
E[cost per finished job] = E[billed hours x price] / P(job finishes)
```

Both factors punish interruptions. Restarted work re-bills hours, and each eviction rolls the dice again on the success probability. The simulation below makes this concrete with a stateless job that needs 6 uninterrupted hours inside an 8-hour window, under different hourly survival probabilities:

```python
# Expected cost per finished spot job vs interruption hazard.
# Job needs `job_hours` uninterrupted hours; a lost instance restarts from zero
# (stateless). 2000 Monte-Carlo runs per configuration; no external deps.
import random, statistics
random.seed(42)

HOURS = 8
N = 2000
job_hours = 6

types = [
    ("c6i.2xlarge", 0.995, 0.266),   # (name, keep-prob/hour, price ratio vs on-demand)
    ("m6i.2xlarge", 0.988, 0.320),
    ("r6i.2xlarge", 0.970, 0.300),
]

def sim(keep_prob):
    t = 0
    while t < HOURS:
        prog = 0
        while prog < job_hours:
            t += 1
            prog += 1
            if random.random() > keep_prob:
                break            # interrupted: progress lost
        else:
            return t, True
        if t >= HOURS:
            return t, False
    return t, False

print("spot fleet simulation: job needs", job_hours, "uninterrupted hours, window", HOURS, "h,", N, "runs")
print(f"{'type':14} {'keep/h':>7} {'success':>8} {'E[billed h]':>12} {'cost/OD-job':>12}")
for name, kp, od_ratio in types:
    succ = [sim(kp) for _ in range(N)]
    p_succ = sum(1 for _, s in succ if s) / N
    e_billed = statistics.mean(h for h, _ in succ)
    cost_per_success = e_billed * od_ratio / max(p_succ, 1e-9) / job_hours
    print(f"{name:14} {kp:7.3f} {p_succ:8.1%} {e_billed:12.2f} {cost_per_success:12.3f}")
print("on-demand baseline: success 100%, billed 6.00 h, cost 1.000")
print("=> hazard eats the discount: a 3%/h interruption rate halves the 70% saving")
```

Output:

```text
spot fleet simulation: job needs 6 uninterrupted hours, window 8 h, 2000 runs
type            keep/h  success  E[billed h]  cost/OD-job
c6i.2xlarge      0.995   100.0%         6.11        0.271
m6i.2xlarge      0.988    99.7%         6.23        0.334
r6i.2xlarge      0.970    99.0%         6.56        0.331
on-demand baseline: success 100%, billed 6.00 h, cost 1.000
=> hazard eats the discount: a 3%/h interruption rate halves the 70% saving
```

Three lessons hide in these numbers. A 0.5% hourly hazard is essentially free (74% discount kept). A 3% hazard - realistic for a single narrow instance type in one AZ - still leaves a 3.3x saving for *stateless restarts*, but the re-billed hours (6.56 vs 6.00) and the success denominator both worsen as job length grows. And for jobs that cannot restart from zero, the arithmetic collapses: a 12-hour stateful job with no checkpointing under a 1% hazard has a ~55% chance of never finishing in the window, and "0.7x price x 0.45 success" is not a discount anymore.

## Checkpointing: The Enabling Technology

Spot economics for stateful work rest on one mechanism: periodically persist enough state that a replacement worker can resume. The design space:

- **External checkpoint to object storage.** The classic Spark/ML pattern. Every N minutes, serialize model/state to S3/GCS with a monotonic version suffix; on restart, load newest complete checkpoint. The math that matters is checkpoint cost vs rework cost: if a checkpoint takes `c` seconds every `T` seconds, overhead is `c/T`, while expected rework after a failure is ~`T/2` (uniformly distributed loss). Smaller `T` trades overhead for less rework - the same curve shape as database WAL commit intervals.
- **Durable execution engines.** Frameworks like Temporal or AWS Step Functions record every external interaction as an event; a resumed worker replays history and re-executes only side effects not yet durably recorded. Checkpointing is automatic but only covers logic expressed in the engine's programming model.
- **Hibernate/pause instead of die.** AWS supports `hibernate` as a Spot interruption behavior: RAM to disk, then on capacity return, resume. Works only for instances with encrypted EBS root volumes and memory that fits; it converts an eviction into a pause, at the cost of resume latency.
- **Queue-based natural checkpointing.** Pull-based workers processing one idempotent message at a time (SQS with visibility timeouts, Kafka with committed offsets) lose at most one in-flight unit per eviction. If each unit is small, no explicit checkpointing is needed - the queue offset *is* the checkpoint. This is the cheapest correct pattern and should be the default for embarrassingly-parallel work.

The non-negotiables regardless of pattern: writes must be idempotent (a worker may die mid-request and its replacement may retry), checkpoint writes must be atomic (write-then-rename or object-versioning; never in-place), and credentials must not live on the ephemeral local disk.

## Fleet Strategy: Diversify or Bleed

A spot fleet (AWS) or managed instance group (GCP) is a portfolio: bid policies decide which pools get your workload. AWS offers `lowest-price`, `capacity-optimized`, and `capacity-optimized-prioritized`; GCP MIGs distribute across zones with a target distribution. The empirical result reported repeatedly by AWS is that `capacity-optimized` - preferring pools with the *fewest* interruptions historically - reduces interruption rates enough to outweigh higher unit prices. The mechanism is adversarial: every buyer running `lowest-price` piles into the same pool, which raises its spot price toward the on-demand cap and concentrates eviction risk; capacity-optimized buyers are spread across pools that are cheap *because* nobody's there.

Practical fleet rules that survive production:

1. Diversify across at least 3 instance families of *similar compute* (e.g. c6i/c6a/m6i), not just sizes - a Nitro-chip shortage or one tenant's giant reservation can hollow out a single family for days.
2. Diversify across AZs but respect data-transfer topology: spot loss plus cross-AZ re-scrub can cost more than the discount if your shuffle traffic is heavy.
3. Keep an on-demand floor (or capacity-block reservation) sized for the minimum viable throughput; treat spot as the elastic 70-90%.
4. React to the 2-minute notice by *draining* (finish in-flight units, hand off queue offsets) rather than saving full VM state - image snapshots are too slow to finish inside the window.
5. Track interruption rate per pool as a first-class SLO; a pool degrading from 0.5% to 5% signals either a regional capacity crunch or your own bid/ceiling misconfiguration.

## Where Spot Is a Bad Idea

Some workloads should stay on-demand even though the discount is tempting: latency-critical serving where an eviction is an outage; databases whose replication topology assumes stable membership (replica churn on eviction causes quorum flapping - though providers now offer capacity reservations for exactly this); tightly-coupled MPI jobs where losing one rank at hour 9 of 10 forfeits everything (checkpoint/restart for HPC exists but the coupling makes the rework window brutal); and anything subject to compliance constraints on where state may be written - checkpoint buckets have a way of multiplying.

The interview-ready summary: spot converts a cost problem into an availability-engineering problem. The discount is the compensation you receive for building eviction tolerance that you should arguably have built anyway; teams that already run stateless, idempotent, queue-fed workers collect nearly the full discount with zero extra engineering, and teams that don't will discover every non-idempotent write path in their system during the first capacity crunch.

## References

- AWS documentation, "Spot Instances" (pricing model, interruption notices, allocation strategies): <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html>
- Google Cloud documentation, "Spot VMs" (fixed discount model, 30 s eviction signal): <https://cloud.google.com/compute/docs/instances/spot>
- Apache Spark documentation, "Decommissioning" (graceful spot shutdown for executors): <https://spark.apache.org/docs/latest/cluster-overview.html#decommissioning>
- AWS blog, "Capacity-Optimized Spot Instance allocation" (interruption-rate rationale for allocation strategies): <https://aws.amazon.com/blogs/compute/introducing-the-capacity-optimized-allocation-strategy-for-amazon-ec2-spot-fleets/>
- Azure documentation, "Azure Spot Virtual Machines" (eviction types and max-price semantics): <https://learn.microsoft.com/en-us/azure/virtual-machines/spot-vms>
