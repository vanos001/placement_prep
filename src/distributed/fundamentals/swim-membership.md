# SWIM and Failure Detection: Membership at Scale

## The Membership Problem

Every cluster service needs to answer two questions continuously: *who is currently part of the group?* and *is each member alive?* That state — the **membership list** — is what the load balancer routes against, what the scheduler places work onto, and what the database uses to form quorums. Getting it wrong in either direction is expensive: a dead node left in the list keeps receiving traffic and corrupting quorum counts, while a live node wrongly declared dead triggers failover storms, re-sharding, and needless churn.

Membership at scale is hard because failure detection runs over the same lossy network that causes the failures. A missed heartbeat can mean a crashed process, a network partition, a GC pause, or just packet loss — and the protocol must distinguish "slow" from "dead" quickly, with a message budget that does not itself melt the network. A node set of 10,000 machines makes the naive approach impossible: if every node pings every other node every second, that is 100 million messages per second of pure overhead.

## Baseline Designs and Why They Break

| Approach | Mechanism | Failure mode at scale |
|---|---|---|
| All-to-all heartbeats | every node pings every node each interval | O(N²) messages; N = 1,000 → 1M messages per interval |
| Central heartbeat server | one server tracks everyone | server CPU/network saturates; single point of failure |
| Ring / token passing | nodes ping their ring neighbor | detection latency grows with N; a partition stalls detection for the whole ring |

These are the designs the SWIM paper (Das, Gupta, Motivala — DSN 2002) took apart. SWIM's goal was detection latency that stays bounded as the cluster grows, with constant per-node overhead, while keeping false positives low.

## The SWIM Protocol

SWIM — Scalable Weakly-consistent Infection-style Process Group Membership — separates two jobs that the naive designs conflate: **failure detection** (is that node dead?) and **dissemination** (does everyone know what we know?). Each runs on its own mechanism, and each piggybacks on the same periodic traffic.

### Detection: Direct Ping, Then Indirect Ping

Time is divided into **protocol periods**. In each period, every node probes one other node (targets are picked round-robin from the membership list, so coverage is fair):

1. **Direct ping** the target, wait for an ack within a small timeout.
2. If no ack arrives, pick **k other members** at random and ask each to send an **indirect ping** (a ping request relayed on the prober's behalf — "ping node X and tell me if it answers *you*"). This routes around the very common case where the *prober–target* path is broken but the target is fine — one of the biggest sources of false positives in naive heartbeating.
3. If neither the direct nor any indirect ping produces an ack by the end of the period, **mark the target suspected**.

```
Period p (prober = A, target = D)

A ──ping──▶ D            (timeout: no ack)
A ──ping-req(D)──▶ B     B ──ping──▶ D   (D answers B, not A:
A ──ping-req(D)──▶ C     C ──ping──▶ D    A↔D path is lossy)
A ──ping-req(D)──▶ E     E ──ping──▶ D

D acks via B or C ─▶ healthy, D stays in list
No ack anywhere   ─▶ D marked SUSPECTED
```

The latency and cost analysis is the heart of the paper: detection of a real failure completes in **O(1) protocol periods regardless of N** (roughly: one period for the miss, one more to confirm via indirect probes), and per-period cost is **O(k) messages per node** — a small constant — instead of O(N). For N = 10,000 with k = 3: SWIM sends ~40,000 probe messages per period where all-to-all would send 100,000,000.

### Dissemination: Infection-Style Gossip

Membership *updates* — joins, alives, suspicions, confirmations — spread **epidemically**: each node holds a queue of recent updates and piggybacks a few of them on every ping, indirect-ping-request, and ack it sends. Recipients merge what they learn into their own queues, so news propagates exponentially fast, and the message cost of dissemination is amortized onto traffic the detector was sending anyway.

Because the two planes are decoupled, a node can learn "D is suspected" from gossip *before* its own probe of D times out, which speeds up real-failure detection; and membership is only **weakly consistent** — different nodes' lists can disagree transiently — which is exactly the trade that makes the thing scalable.

### Suspicion and Incarnation Numbers

Direct + indirect probing already filters out most false positives, but lossy networks still produce them, and blindly *ejecting* a live node on one period of missed pings is dangerous. So SWIM adds a **suspicion** sub-protocol:

- A suspected node is tagged with the *suspicion* plus an **incarnation number** — a per-node counter.
- The suspected node, hearing about its own suspicion, refutes it by broadcasting an **ALIVE** message with its incarnation *incremented*. Only a message with a higher incarnation can overwrite a node's state, so a rejoining old node cannot roll the list backward.
- Suspicion news is disseminated **faster** than alive news (suspicions are queued ahead — "bad news travels first"), because the cost of a late suspicion (a live node serving traffic) is lower than the cost of a late confirmation (a dead node kept in quorums).
- After a suspicion persists for a configurable multiple of the protocol period, the node is **confirmed** and ejected.

The combination — indirect probes, suspicion with refutation, epidemic dissemination — is the full "**SWIM with suspicion**" variant that virtually every production implementation ships.

## Phi-Accrual Failure Detection

SWIM decides alive/dead from timeouts; a complementary line of work makes the *detector itself* quantitative. The **φ-accrual failure detector** (Hayashibara et al., SRDS 2004) replaces the binary "missed N heartbeats" with a continuous **suspicion level** derived from the observed heartbeat *inter-arrival distribution*:

```python
# Phi-accrual suspicion level, normal-distribution approximation
# (the variant used by Akka and Cassandra's gossip).
import math
import statistics

class PhiAccrualDetector:
    def __init__(self, threshold=8.0, min_samples=20, max_samples=200):
        self.threshold = threshold
        self.min_samples = min_samples
        self.max_samples = max_samples
        self.samples = []          # inter-arrival times in ms
        self.last_arrival = None

    def record_heartbeat(self, now_ms):
        if self.last_arrival is not None:
            self.samples.append(now_ms - self.last_arrival)
            self.samples = self.samples[-self.max_samples:]
        self.last_arrival = now_ms

    def phi(self, now_ms):
        """log10 of 1/P(now > t_since_last | history). Higher = worse."""
        if len(self.samples) < self.min_samples:
            return 0.0                                   # not enough history
        since = now_ms - self.last_arrival
        mean = statistics.fmean(self.samples)
        var = statistics.pvariance(self.samples)
        std = max(math.sqrt(var), 0.001)                 # guard degenerate
        # P(arrival gap > since) under N(mean, std):
        z = (since - mean) / (std * math.sqrt(2.0))
        p_later = 0.5 * math.erfc(z)
        if p_later <= 0.0:
            return float("inf")
        return -math.log10(p_later)

    def is_suspect(self, now_ms):
        return self.phi(now_ms) > self.threshold
```

Interpretation: `φ = 1` means the probability of observing a heartbeat this late is about 1 in 10; `φ = 8` means about 1 in 100 million. Applications pick a φ threshold matching how much false-positive risk they tolerate, and — crucially — the same threshold **adapts automatically** to network conditions: over a jittery link the inter-arrival spread widens, so a 700 ms gap may mean nothing; over a clean LAN the same gap is off the chart. Fixed timeouts cannot do both. This is why gossip-based stores (Cassandra's gossip layer) and Akka Cluster adopted accrual detection, while SWIM-style cluster managers (Serf, Consul) refined timeout-based probing with indirect pings to the same end.

## SWIM in Production Systems

- **HashiCorp Serf / Consul** implement SWIM with suspicion as their core (Serf calls it its "gossip protocol"; Consul layers catalogs, health checks, and DNS on top of the membership layer). Consul organizes members into separate **LAN and WAN gossip pools**, so datacenter-internal detection is tuned for low-latency LANs while the WAN pool tracks datacenter liveness with slower, higher-cost probes — one protocol, two parameterizations.
- **Memberlist** (the Go library behind Consul/Serf) is the reference open-source SWIM implementation, exposing protocol period, indirect-ping fanout k, and suspicion multipliers as tunables.
- **Cassandra's gossip** layer uses phi-accrual detection with SWIM-like epidemic dissemination of state (the two ideas compose naturally: accrual detectors as the *signal*, gossip as the *transport*).

## Message-Cost Math, Made Concrete

```python
# Probe-message cost per protocol period: SWIM vs all-to-all heartbeats.
K_INDIRECT = 3
for n in (100, 1_000, 10_000):
    swim = n * (1 + K_INDIRECT)          # 1 direct + k indirect per node
    naive = n * (n - 1)                  # every node pings every node
    print(f"N={n:>6}: SWIM {swim:>7} msgs/period, "
          f"all-to-all {naive:>12,} msgs/period "
          f"(ratio {naive / swim:,.0f}x)")
```

```text
N=   100: SWIM     400 msgs/period, all-to-all        9,900 msgs/period (ratio 25x)
N= 1,000: SWIM   4,000 msgs/period, all-to-all      999,000 msgs/period (ratio 250x)
N=10,000: SWIM  40,000 msgs/period, all-to-all   99,990,000 msgs/period (ratio 2,500x)
```

The gap widens linearly with N — which is the entire reason a 10,000-node cluster is even *considered* the same problem class as a 100-node cluster.

## Interview Angles

- **Why indirect pings?** A missed ack often means the *prober–target* path failed, not the target. Asking k third parties separates "network path to me is bad" from "node is dead," cutting false-positive ejections — the most expensive membership mistake.
- **What is the failure-detector theory here?** Chandra–Toueg define detectors by completeness/accuracy; SWIM approximates strong completeness (every crashed node is eventually suspected by every correct node) through epidemic suspicion dissemination, while indirect pings defend accuracy.
- **Why can membership only be weakly consistent?** Strong consistency of the *list* would itself require consensus on every membership change — precisely what you cannot afford on a lossy network during failures (FLP context). Systems bound the damage with incarnation numbers and quorum-using consumers.
- **Design failure detection for 50,000 IoT gateways over cellular.** Cover: long protocol periods, phi-accrual thresholds per-link-quality, indirect probing via regional relays, and hysteresis (suspect → confirm only after long persistence) to survive flaky links.
- **Your cluster keeps ejecting live nodes during deploys. Diagnose.** Rolling restarts make every node briefly unresponsive — check whether probes treat graceful shutdown as suspicion-worthy, whether indirect pings fan out across availability zones, and whether the suspicion window is shorter than your JVM pause times.

## References

- [Das, Gupta & Motivala, "SWIM: Scalable Weakly-consistent Infection-style Process Group Membership Protocol", DSN 2002](https://ieeexplore.ieee.org/document/1028914)
- [Hayashibara et al., "The φ Accrual Failure Detector", SRDS 2004](https://www.computer.org/csdl/proceedings-article/srds/2004/22390066/12OmNvT2phv)
- [Consul — Architecture (SWIM-based gossip, LAN/WAN pools)](https://www.consul.io/docs/architecture)
- [Serf — Gossip internals (SWIM lifecycle: alive, suspect, dead)](https://www.serf.io/docs/internals/gossip.html)
