# "The network is reliable"

## Overview

This page audits the first and oldest of the fallacies of distributed
computing: the assumption that the network is reliable — that a message
sent is a message delivered. Every distributed system designer inherits
this assumption from a decade of local calls, where invoking a function and
having it execute are the same event. Across a network they are different
events separated by hardware, software, and physics that can lose, delay,
duplicate, or reorder the message while every component involved believes
it is healthy. Partitions happen; latency spikes masquerade as outages; DNS
blips, MTU mismatches, NIC failures, and route changes all convert "send"
into "maybe" without any error being raised where you are looking. The
design consequence is total: timeouts and retries everywhere, idempotency as
a requirement, and the CAP tradeoff existing at all because partitions must
be assumed. This page states the claim fairly, works the silent-loss
counterexample, and delineates it from its neighbor — the claim about what
TCP guarantees — because the two are conflated constantly and fail at
different layers.

## The Claim, Stated Fairly

The strongest common form of the claim is: "If we send a request and the
other service is up, it will arrive; networking is the cloud provider's
problem." Stated this way, the claim is rarely a conscious assertion — it
shows up as code with no timeout, a queue consumer assuming at-most-once, a
service-to-service call chain with no retry budget, or an architecture that
treats a datacenter as one failure domain.

The claim deserves its fairness because in the common regime the network is
astonishingly good. Well-run fabrics deliver packets with loss rates measured
in fractions of a percent and availability in the many nines, and most
messages most of the time simply arrive. TCP and the layers above paper over
the common losses so well that the engineer who has never read a packet
trace is honestly reporting their experience. The question is whether "the
network is very good" honestly compresses to "the network is reliable" —
a system is as reliable as its behavior during the events, not the rate.

## Verdict

**False.** The claim is contradicted outright: there exist ordinary, valid
scenarios in which a message is sent by a healthy sender to a healthy
receiver and never arrives, with no failure signaled to either side. The
counterexample does not require exotic hardware — a partitioned switch, a
GC pause that outlives a timeout, a dropped packet at the moment a
connection was half-open, or a DNS TTL race will do. The consequence is not
that networking is bad but that *reliability across a network must be
engineered at the endpoints* — timeouts, retries, idempotency, quorums —
because the network itself promises only best effort.

## Why People Believe It

The kernel of truth is statistical: modern networks fail rarely enough that
a career of mostly-working calls is an honest sample. The layers also hide
the failures that do occur — TCP retransmits invisibly, DNS caches absorb
blips, load balancers drain bad nodes — so the engineer's view of the
network is systematically better than the network. What survives to the
application is the quiet majority of successes, and the human belief tracks
the observed rate, not the tail.

The belief also has a respectable lineage: the fallacies list was written
(Deutsch, 1994; formalized at Sun) precisely as a list of *assumptions
newcomers make*, and the first entry is a warning label rather than a
doctrine. The warning has been quoted for thirty years while the code has
kept assuming — because every abstraction the industry builds, from RPC
frameworks to service meshes, is optimized to make the network feel like a
function call. The feel is the product; the assumption is the leak.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "The network is reliable" | Best effort only: loss, duplication, reordering, delay, and partition are ordinary events, not exceptions |
| "If it's sent, it arrives" | A send completes locally; delivery is a separate outcome the sender cannot observe without a response |
| "Partitions are rare" | Partitions include slow-is-indistinguishable-from-down: a 30-second stall is a partition at any practical timeout |
| "TCP makes it reliable" | TCP repairs the stream between two live endpoints while the connection lives; it cannot deliver across a broken path or to a crashed peer |
| "The cloud provider's problem" | Availability zones, routes, and DNS are your system's failure domain whether or not the SLA mentions them |
| "The engineering consequence" | Timeouts, retries with budgets, idempotency keys, quorum reads/writes, and partition-tolerant design are mandatory, not optional |

The correct sentence: "The network is best-effort: any message may be
lost, delayed, duplicated, or reordered, and any two components may be
unable to communicate while both believe they are healthy. Reliable
distributed systems are built by treating every send as unconfirmed until
acknowledged, and every operation as retried until designed otherwise."

## Where It Breaks

**The silent-loss counterexample, worked end to end.** A client sends a
payment initiation to the ledger service; the TCP connection was idle past
the middlebox's timeout, the SYN-retry lands in a black-holed route, and
after the client's 2-second timeout the request is marked failed. The
ledger, meanwhile, was healthy and later receives the retried request
through a second path — but the client had already surfaced "payment
failed" and the user re-submitted. Two payments, zero network errors
reported by any component. Nothing is malfunctioning: no NIC is dead, no
alarm fires. The network was neither reliable nor observably unreliable —
it was *ambiguous*, and ambiguity is the failure mode the claim cannot
represent. Every idempotency-key convention in the industry exists because
this scenario is ordinary.

**The fallacies are a system, not a list.** The first fallacy drags the
others with it. Latency is not zero (the second fallacy), so a slow peer
and a dead peer are indistinguishable at any finite timeout — the partition
that CAP discusses includes the stall. Bandwidth is not infinite, so
retries can amplify an outage (a service that times out at 2 s and retries
3x turns a 1% loss event into a 4x load multiplier — the retry storm).
Topology does not stay fixed: route changes, NIC replacements, MTU
mismatches on new paths, and DNS TTL races all produce correctness
incidents in systems that assumed a stable, faithful substrate. The
GitHub October 2018 incident is the canonical modern case: a 43-second
partition between GitHub's East Coast network hub and its primary East
Coast data center — planned optical maintenance, restored in 43 seconds —
was enough for the failover automation to promote the US West Coast data
center while each side briefly held writes the other lacked. Divergence,
not downtime, was the expensive part: 24 hours and 11 minutes of degraded
service, multi-terabyte restores, and hundreds of writes reconciled by
hand, from one partition measured in seconds inside one of the best-run
networks on the planet.

**The consequence stack is the proof.** Look at what mature distributed
systems actually build: timeouts on every call, retry budgets with jitter,
idempotency keys on every mutating endpoint, quorum replication, leader
election, fencing tokens, and gossip failure detectors. None of these
exists because engineers enjoy complexity; each is a direct payment against
the unreliability of the network. The claim is refuted by the
architecture of every serious system built on top of it: if the network
were reliable, quorums would be pointless and CAP would be a footnote
about an impossible event.

**What "reliable enough" buys and what it costs.** The honest engineering
position is conditional: well-run fabrics make loss rare, which makes
endpoint reliability machinery cheap in the common case and decisive in
the tail. Designing *as if* the claim were true saves seconds of thought
per call and purchases hours of reconciliation per incident. The
assumption is not merely false; it is unprofitable — its cost curve is
exactly inverted, trivial savings upfront, catastrophic payouts at the
tail.

## Practical Implications

- Put a timeout on every network call and treat "no response" as the
  normal, expected outcome class — not an error condition but an answer:
  "unknown", to be resolved by idempotent retry or query.
- Design every mutating endpoint for idempotency from day one; retrofit is
  the expensive version of the same requirement.
- Budget retries (circuit breakers, jitter, retry caps) so the network's
  bad moments do not amplify into system-wide load storms.
- Test partition behavior deliberately — kill links, add latency, drop
  packets in CI or staging — because the failure classes you must survive
  are invisible to functional tests on a healthy fabric.
- When a "flaky" failure is reported, stop debugging the client first: the
  network was a suspect from the first fallacy, and packet traces, not
  vibes, decide.

## Interview Questions

### "The network is reliable" is called the first fallacy of distributed computing. What does the fallacy actually assert, and what is the evidence against it?

It asserts that message delivery across a network can be assumed rather
than engineered. The evidence is that loss, delay, duplication, reordering,
and partition are ordinary events even on healthy fabrics, and that the
entire toolset of distributed systems — timeouts, retries, idempotency,
quorums, consensus — exists to compensate. A strong answer notes the
conflation trap: TCP's reliability is a stream-level repair mechanism, not
a system-level delivery guarantee.

### A caller times out after 2 seconds. What are the possible states of the request on the server, and what does your client need to do safely?

Unreceived, received-but-processing, completed-before-timeout, and
completed-after-the-caller-gave-up are all live possibilities — the caller
cannot distinguish them without querying. Therefore the safe client treats
the timeout as "unknown", retries only idempotent operations or carries an
idempotency key, and the server deduplicates. This question is the
practical refutation of the fallacy: uncertainty, not failure, is the
default outcome class.

### Distinguish this claim from "TCP guarantees delivery". Why is one false at the system level while the other is true at the connection level?

TCP guarantees that bytes accepted by the sender's kernel arrive in order
at the receiver's kernel *while the connection lives* — it repairs packet
loss on a working path. It says nothing about the network staying connected,
the peer staying alive, or the application reading the bytes; a partition
or a crashed peer voids it entirely. The network-reliability claim is about
the substrate across all connections and time; TCP's promise is scoped to
one live connection. Both are frequently over-claimed, in opposite
directions.

### Your multi-region system must behave correctly during a network partition. Name the design elements this forces.

Explicit partition handling: quorum writes or a consensus protocol so two
sides cannot both accept conflicting writes, or an explicit
availability-versus-consistency choice per operation; fencing tokens so a
deposed leader cannot act; idempotent, reconcilable writes if
availability is chosen; and partition testing in the release process. If
the team has none of these, their design silently assumes the first
fallacy.

## Key Takeaways

- The network is best effort: loss, delay, duplication, reordering, and
  partition are ordinary events, and "slow" and "down" are
  indistinguishable at any finite timeout.
- A completed send is not a delivered message; until acknowledged, every
  request's outcome is "unknown" — and systems must be designed for that
  state, not for success and failure as the only outcomes.
- TCP does not rebut the fallacy: it repairs streams on live connections
  and delivers nothing across a broken path or to a dead peer.
- The engineering stack — timeouts, retry budgets, idempotency keys,
  quorums, consensus, fencing — is the cost of this fallacy, paid by every
  serious system; the assumption's price is deferred, then compounded.
- The fallacies travel together: latency, bandwidth, topology, and
  administrative assumptions all encode the same error of treating the
  network as a reliable function-call substrate.

## Cross-References

- [Misconception: "TCP guarantees the application receives the data"](./tcp-guarantees-delivery.md)
  — the neighbor claim this page must be read against: TCP's ordered,
  reliable stream is real but scoped to a live connection between two
  endpoints; this page is about the substrate assumption beneath every
  connection, and the two fail at different layers for different reasons.
- [Misconception: "A distributed system can always provide consistency and availability during a partition"](./consistency-availability-partition.md)
  — the theoretical continuation: CAP exists because this page's events
  must be assumed; Gilbert–Lynch formalizes the cost of the partition the
  first fallacy says not to expect.
- [Misconception: "UDP is unreliable, so serious applications can't use it"](./udp-cannot-be-reliable.md)
  — the design-freedom sibling: once reliability is understood as an
  endpoint property, building it on UDP becomes an engineering choice, not
  a heresy.
- [Assumptions Hunt: Network & Distribution](../assumptions-hunt/network-distributed.md)
  — the systematic sweep of the hidden assumptions in distributed designs,
  of which this fallacy is the founding entry.
- [Failure Casebook: GitHub October 2018](../failure-casebook/github-october-2018.md)
  — the partition case study: a 43-second network failure becoming 24
  hours of degraded service, with the reconciliation mechanics explained.
- [Connection Atlas: TCP & Distributed Failure](../connection-atlas/tcp-distributed-failure.md)
  — the bridge page connecting TCP semantics to system-level failure
  handling, where the delineation above is worked in detail.
- [Assumptions Hunt: Timeouts & Retries](../assumptions-hunt/timeouts-and-retries.md)
  — the engineering consequence stack: budgeting, jitter, and the
  retry-storm arithmetic this page gestures at.
- [Common Failures](../../failure-modes/common-failures.md) — the catalog
  of failure modes whose first entries are the network's.
- [Misconceptions index](./index.md) — the taxonomy used for this verdict.

## References

- P. Deutsch. *Eight Fallacies of Distributed Computing*. Sun Microsystems,
  1994 — the origin list, cited by title.
- J. Postel (ed.). *Internet Protocol*. RFC 791, September 1981 — the
  best-effort datagram service contract in the standard's own words.
  <https://www.rfc-editor.org/rfc/rfc791.html>
- W. Eddy (ed.). *Transmission Control Protocol (TCP) Specification*.
  RFC 9293, August 2022 — the current TCP standard, and the precise scope
  of what the protocol does and does not promise.
  <https://www.rfc-editor.org/rfc/rfc9293.html>
- GitHub Engineering. *Post-incident analysis: October 21, 2018* — the
  partition, its 43-second trigger window, and the reconciliation cost.
  <https://github.blog/2018-10-30-oct21-post-incident-analysis/>
- A. Tanenbaum and M. van Steen. *Distributed Systems: Principles and
  Paradigms* — the system-model framing in which reliability is an
  endpoint property, cited by title.
