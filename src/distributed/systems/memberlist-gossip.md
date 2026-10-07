# Memberlist & Gossip Internals

## Overview

Cluster membership — knowing which nodes are alive, with bounded staleness — is the substrate every other distributed primitive stands on, and gossip protocols are how it scales without a central failure detector. HashiCorp Memberlist, the SWIM paper it implements, Serf, Consul's LAN/WAN pools, and Cassandra's failure detection all descend from the same design. This page goes to the internals: probe scheduling, indirect ping, suspicion, dissemination by piggybacking, and the QoS knobs (probe interval, suspicion multiplier, retransmit count) that trade detection latency against network load. Interviewers at infrastructure companies treat SWIM fluency as a strong signal for distributed-systems depth.

> **Interview Angle**: The memorable sequence is: naive all-to-all ping fails at scale → SWIM's indirect probing beats network asymmetry → suspicion prevents flapping → piggybacked dissemination removes the separate gossip channel. Each step solves a specific failure of the previous one; walk the interviewer through that chain.

## Why Central Failure Detectors Fail

Two naive designs break at scale. A **central pinger** (one node probes everyone) has its bandwidth and its blast radius concentrated: at 10,000 nodes and 1-second probes, the monitor sends 10k pings/second and its own network hiccup marks the entire cluster dead. **All-to-all heartbeats** are O(n²): each node sends to each peer, so 10,000 nodes generate 100M messages per round and failure-detection noise drowns real signal. The requirement is a protocol where each node does O(1) work per round while suspicion information still reaches everyone in O(log n) rounds — that is exactly SWIM's envelope.

## The SWIM Protocol

SWIM (Scalable Weakly-consistent Infection-style Process Group Membership, Das et al., NSDI 2002) runs a round-robin probe loop over a shuffled membership list:

1. **Direct ping**: pick the next target (round-robin over a shuffled list), send UDP ping, wait `probe_timeout` (typically 1s).
2. **Indirect ping**: on timeout, ask `k` random live nodes (default 3) to ping the target and report back (ping-req). This defeats the most common false positive — asymmetric loss where A→B drops but B→A flows.
3. **Suspicion**: if all indirect probes fail, the target is marked *suspect*, not dead. Suspects get a grace period (`suspicion_mult` × probe interval) during which any response from them refutes the suspicion. This prevents flapping on brief pauses (GC, VM migration).
4. **Dead/Away**: suspicion confirmed by timeout (or an explicit leave message) transitions the node to dead; the state disseminates by gossip.

```mermaid
sequenceDiagram
    participant A as Node A (prober)
    participant T as Target T
    participant K as k random peers
    A->>T: PING (udp)
    T--xA: loss or timeout 1s
    A->>K: PING-REQ(T)
    K->>T: direct PING
    K--xA: NACK / result
    Note over A: all fail → mark T SUSPECT
    Note over A: suspicion gossips; grace timer runs
    Note over A,T: no refutation → T becomes DEAD
```

Each probe piggybacks gossip payload: the PING and ACK messages carry a bounded number of membership broadcast entries (joins, suspect flags, dead notifications), each with an incarnation number and a retransmit counter. There is no separate gossip protocol to run — dissemination rides the failure detector's traffic, which is why SWIM is called infection-style: state spreads like an epidemic at a rate proportional to normal chatter.

## Incarnations and Lamport Clocks

Every membership change broadcasts carries the node's **incarnation number** — a per-node Lamport counter. A node refutes a false suspicion by bumping its incarnation and broadcasting alive(n+1); refutation messages only win against older incarnations, which prevents stale gossip from resurrecting dead nodes or re-suspecting recovered ones. Suspicion itself can also be mediated: SWIM's paper variant lets a suspect bump its own incarnation to convert suspect(n) → alive(n+1), while Memberlist adds *composite* suspicion — the grace period shrinks with the number of independent witnesses, so a suspicion confirmed by many nodes expires faster than one node's gripe.

## Dissemination Math

With fanout piggybacking of `b` broadcasts per message and retransmit count `r`, a broadcast reaches a cluster of n nodes in roughly `O(log n)` rounds — the epidemic argument: each infected node infects up to `b` others per round, so coverage grows exponentially until saturation, and `r` retransmissions cover the tail of nodes reached late. Memberlist defaults encode this: `retransmit_mult = 4` (a broadcast is piggybacked on ~4×log n messages), `probe_interval = 1s`, `probe_timeout = 500ms`, `suspicion_mult = 4-5`. Detection latency for a dead node is therefore `probe_timeout + suspicion grace ≈ 5-6s` by default — quote that number and its knob in interviews.

| Parameter | Default | Effect if raised | Effect if lowered |
|---|---|---|---|
| probe_interval | 1s | slower detection, less traffic | faster detection, more probes |
| probe_timeout | 500ms | tolerant of WAN RTT | false positives on slow links |
| suspicion_mult | 4-5 | flapping-resistant, slower convergence | quick eviction, flappy clusters |
| retransmit_mult | 4 | robust gossip, more overhead | faster payload expiry, gaps |
| gossip_nodes / fanout | 3 | faster spread | sparse coverage |

## Push-Pull Sync and Joins

Beyond periodic probes, Memberlist nodes periodically run a **push-pull** state exchange with a random peer: each side sends its full (or delta-compressed) membership state, both merge by (incarnation, state) ordering. Push-pull bounds divergence — even if piggybacked broadcasts were lost repeatedly, a push-pull cycle reconciles. Joins use a known seed list: the joining node sends a compound join message, existing nodes respond with full state, and the join broadcast then announces the new node to everyone else. Serf layers event/user messages on the same dissemination machinery, which is why a single Memberlist core serves both Consul (membership for catalog) and Serf (cluster-wide events).

## Consistency Guarantees — What You Actually Get

Membership via gossip is **eventually consistent and weakly consistent**: two observers can disagree about a node's state for up to a few dissemination rounds, and nothing in SWIM provides linearizability. Systems built on top must respect that boundary. Consul's health is a good example: gossip-based *serfHealth* detects agent liveness quickly but unreliably, while *service health checks* — which gate routing — run through the consensus-backed catalog, trading detection latency for correctness. Similarly, Cassandra uses phi-accrual failure detection (a different family: continuous suspicion scores) on top of its own gossip state. The interview answer: SWIM decides *who is in the group*; it never decides *who holds the truth* — that belongs to a consensus layer above it.

## Variants and Upgrades

- **Lifeguard (SWIM extension, 2020)**: fixes the "sick" large-cluster failure mode where a degraded node cannot disprove suspicions fast enough and generates refutation load that worsens its own health. Adds local health awareness — probes you send successfully lower your own probe intensity, and suspicion grace is derived from the suspender's health, not a global constant.
- **Phi-accrual detectors (Hayashibara et al.)**: output a continuous suspicion score from heartbeat inter-arrival history; applications pick thresholds per link. Cassandra ships this as `PhiConvict`.
- **Follower/anchor optimizations** and UDP-over-TCP fallbacks in Memberlist when packet loss crosses thresholds.

## Interview Questions

1. **Why does SWIM use indirect ping instead of just increasing timeouts?** Raising timeouts punishes every node for asymmetric packet loss between one pair. Indirect ping localizes the decision: k third parties that can reach the target refute the failure in the same round, keeping detection latency low while eliminating the dominant false-positive class. It converts a global tuning knob into a per-incident check.
2. **Walk through what happens when a GC pause of 8 seconds hits one node (defaults: 1s probe, 4x suspicion).** Direct ping times out, 3 peers indirect-ping it — peers that also time out. The prober marks it suspect and the suspicion gossips. The node wakes, sees suspect(incarnation i) messages, bumps to incarnation i+1 and broadcasts alive; every refutation that lands before the suspicion grace (≈4-5s after confirmation, adjusted by witness count) resets the flag. Detection only completes if no refutation arrives — a healthy wakeup beats the grace timer in most real clusters, which is the design intent.
3. **How does a broadcast reach all 10,000 nodes without a spanning tree?** It does not need one — piggyback on normal probe traffic with retransmit_mult≈4. Coverage grows exponentially (each carrier infects ~3-4 peers per round), giving log₂(10,000) ≈ 14 rounds of base spread, with retransmissions mopping up stragglers. The cost is bounded overhead per message instead of tree maintenance, and the scheme is immune to any single node's death.
4. **When would you refuse to build routing decisions on SWIM membership alone?** Whenever a wrong route costs correctness rather than just latency: leader election, quorum decisions, and request routing to a "primary" all need consensus-backed truth, because SWIM can briefly show a partitioned-but-alive leader as healthy or a healthy node as suspect. Use SWIM for liveness and topology; use Raft/Paxos (or lease-bound fencing) for authority — exactly Consul's split between serfHealth and catalog health.
5. **What does Lifeguard add over textbook SWIM?** Self-awareness of local health. A node that succeeds in its probes dials down its own probe intensity and suspicion rate, so a overloaded node stops spending its remaining capacity on refuting suspicion storms. Suspicion grace also becomes a function of the *suspender's* health, removing the global-constant coupling that made 1,000+ node SWIM deployments degrade under partial congestion.

## Key Takeaways

- Round-robin direct + indirect probing + suspicion gives O(1) per-node work with ~5s detection at sane defaults.
- Incarnation numbers make gossip self-correcting: newer incarnations always beat older state.
- Piggybacked, retransmitted broadcasts give O(log n) dissemination without a separate gossip channel.
- Membership is liveness, not truth: gate anything correctness-critical on consensus or fencing above the gossip layer.
- Lifeguard and phi-accrual variants exist because fixed global knobs break at scale and under congestion.

## References

- SWIM paper (Das, Gupta, Motivala — NSDI 2002): [usenix.org/legacy/events/nsdi02/tech/swim.html](https://www.usenix.org/legacy/events/nsdi02/tech/swim.html)
- Lifeguard: SWIM-ing with Situational Awareness (HashiCorp): [hashicorp.com/blog/lifeguard-swim-with-situational-awareness](https://www.hashicorp.com/blog/lifeguard-swim-with-situational-awareness)
- Memberlist library and docs: [github.com/hashicorp/memberlist](https://github.com/hashicorp/memberlist)
- Consul architecture (gossip pools vs catalog): [developer.hashicorp.com/consul/docs/architecture](https://developer.hashicorp.com/consul/docs/architecture)
- Phi-accrual failure detector paper (Hayashibara et al., 2004): [ieeexplore.ieee.org/document/1351239](https://ieeexplore.ieee.org/document/1351239)

## Cross-References

- [Gossip Protocols](../fundamentals/gossip-protocols.md) — the general epidemic-style dissemination model
- [Failure Detectors](../fundamentals/failure-detectors.md) — the theoretical properties (completeness, accuracy) behind SWIM
- [Chubby & Consul](./chubby-and-consul.md) — how Consul layers consensus-backed health over gossip
- [etcd Internals](./etcd-internals.md) — the consensus-first alternative when membership must be linearizable
- [Consistency Verification](./consistency-verification.md) — how systems like this get their protocols checked
