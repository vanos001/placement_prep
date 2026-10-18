# "More bandwidth will make it faster"

## Overview

This page examines the reflex that reaches for a pipe upgrade whenever a
system is slow: buy more bandwidth. The reflex works exactly on one class of
workload — bulk transfer — and does almost nothing on the other class,
where time is spent waiting for round trips, not moving bytes. Latency and
throughput are different axes with different fixes; conflating them is one
of the most common capacity-planning errors, and the arithmetic that
separates them (page loads, N+1 queries, physical distance floors) is
simple enough to do in an interview. This page states the claim fairly,
works both regimes, and names the one honest exception where bandwidth
really does buy latency.

## The Claim, Stated Fairly

The strongest common form of the claim is: "If the network is involved and
users say it is slow, the link is the bottleneck; upgrading bandwidth will
make it faster." Stated this way, the claim is not a caricature; it is the
standard escalation conclusion from "the network must be the problem," and
it has a real home market: file transfers, backups, video, and replication
streams genuinely speed up with bandwidth, so the person proposing the
upgrade is usually quoting a real success.

The claim deserves its fairness because bandwidth and latency are
*correlated* in naive experience: slow links (DSL, hotel Wi-Fi) tend to be
both narrow and high-RTT, and upgrading them improves everything at once,
hiding which axis was doing the work. The question is whether "bytes move
faster" honestly compresses to "everything finishes faster".

## Verdict

**Context-dependent.** For throughput-bound workloads (bulk transfer,
streaming, backups), more bandwidth is the fix, and the speedup is close to
linear. For RTT-bound workloads (chatty protocols, page loads of small
resources, queries in loops), time is dominated by round trips that
bandwidth cannot shorten — the upgrade buys nothing, and the honest fixes
are fewer round trips, batching, and distance. The workload decides.

## Why People Believe It

The kernel of truth is threefold. First, for bulk data the math is honest:
transfer time ≈ payload / bandwidth, so doubling bandwidth halves the time.
Second, historical links were narrow enough that even small payloads took
visible transfer time, so "more bandwidth" improved interactive workloads
too. Third, monitoring dashboards usually show link utilization, so
"saturated link" is the easiest network fact to observe — and saturation
*is* a latency problem (queueing delay), which makes the upgrade feel like
a latency fix.

What disappears in compression is the decomposition of response time:
time = (number of round trips × RTT) + (payload / bandwidth) + server
processing. When payloads are kilobytes and bandwidth is megabits or
gigabits, the second term is sub-millisecond and the first term owns the
response. No pipe upgrade touches the round-trip count.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Bandwidth makes it faster" | Bandwidth shortens payload/bandwidth; only that term |
| "The network is slow" | Separate: RTT (distance + path), round-trip count (protocol design), serialization (payload/bandwidth), queueing (saturation) |
| "Upgrade fixes user complaints" | If users wait on round trips, fix round trips: batch, parallelize, cache at the edge, reuse connections |
| "Latency is a bandwidth problem" | One honest exception: when the link is saturated, queueing delay *is* latency, and headroom removes it |
| "Physics is negotiable" | RTT has a floor of ~2 × distance / (speed of light in fiber ≈ 200,000 km/s); no bandwidth changes it |

The correct sentence: "First classify: is this workload throughput-bound or
RTT-bound? Bulk transfer responds to bandwidth; interaction latency
responds to fewer round trips and shorter distance. Measure which term
dominates before buying anything."

## Where It Breaks

**The page-load arithmetic.** A first visit to a page needs, roughly: DNS
(1 RTT), TCP handshake (1 RTT), TLS 1.2 handshake (2 RTTs; TLS 1.3 does it
in 1), then the HTTP request and response (1 RTT) — four to five round
trips before the first byte, matching the numbers in this repo's latency
reference. At a 50 ms RTT that is a ~200–250 ms floor that exists whether
the link is 100 Mbps or 10 Gbps. Then the subresources: thirty small
assets over six parallel connections arrive in roughly five waves — five
more RTTs, ~250 ms more. Total interaction time is owned by the ~10 RTT
term; every payload is kilobytes, serialized in well under a millisecond
at either bandwidth. The 10× bandwidth upgrade moves the page load by
milliseconds that no user can perceive. The fixes that actually work are
connection reuse, TLS 1.3/QUIC's fewer handshakes, HTTP/2+ multiplexing,
edge caching (distance reduction), and prefetching — all round-trip
reductions.

**The N+1 arithmetic.** A request handler issues one query to fetch 50
customers, then one query per customer for their latest order: 51
sequential round trips to a database whose RTT is 50 ms. Total query time:
51 × 50 ms = 2,550 ms. Upgrade bandwidth 10×: payloads are a few KB each,
so the serialization term shrinks from trivially small to slightly smaller
— the request still takes ~2.5 s. Batch the 51 queries into one (a join or
an IN-list): one round trip, 50 ms — a 51× improvement bought by protocol
design, not hardware. Even naive parallelism (fire all 50 together) lands
near two RTTs, ~100 ms. This is the shape of most "we added bandwidth and
nothing happened" incidents: chatty APIs are round-trip-count problems.

**The distance floor.** RTT cannot go below ~2 × distance divided by the
speed of light in fiber (~200,000 km/s). New York to London is ~5,600 km,
so the physical floor is ~56 ms of round trip before any equipment,
buffering, or routing overhead — consistent with the ~70–80 ms RTTs real
routes show. A transatlantic link at 400 Gbps and one at 10 Gbps have the
*same* floor. For interactive work spanning oceans, the only bandwidth-
compatible fixes are proximity (CDN, regional read replicas) and fewer
round trips per interaction (batching, 0-RTT resumption). This is the
"latency numbers every programmer should know" lesson in its purest form.

**When the upgrade genuinely is a latency fix: saturation.** The one
honest exception: when a link runs at capacity, packets *queue*, and the
queue is paid as latency — that is bufferbloat, the ping time that
explodes when someone starts a backup. Here more bandwidth (or better
scheduling/AQM on the bottleneck) removes queueing delay, and latency
improves *because of* headroom, not because bytes moved faster. This is
why the claim survives: in saturated home and office links, the upgrade
really does lower ping. The diagnostic tells the cases apart — if latency
rises only under load and normalizes when idle, you have a queueing
problem; if latency is high at idle, it is RTT, and bandwidth is
irrelevant.

**The throughput-bound case, done honestly.** Copying a 100 GB backup over
1 Gbps takes ~800 s ≈ 13.3 minutes (100 × 8 = 800 Gb / 1 Gbps); over 10
Gbps it takes ~80 s. Database snapshot shipping, video streaming, log
drain, and data migrations live here, and for them "more bandwidth" is the
correct, complete answer — up to the point where the RTT window limits TCP
throughput on long paths, which is where buffer sizes and congestion
control, not capacity, become the bottleneck.

## Practical Implications

- Before proposing any network fix, decompose response time into round
  trips × RTT, payload/bandwidth, and server time — then name the
  dominant term. Capacity requests follow the term, not the reflex.
- For RTT-bound paths: batch (N+1 → 1), parallelize independent calls,
  reuse connections, adopt TLS 1.3/QUIC 0-RTT, cache at the edge, and
  place state near users (read replicas, CDNs).
- For throughput-bound paths: bandwidth math is honest — size links from
  payload and deadline, and check the long-path TCP window if transfers
  underperform the raw capacity.
- Investigate saturation before blaming RTT: latency that appears only
  under load is queueing, and headroom or AQM fixes it.
- In design interviews, volunteering the decomposition (round trips vs
  bytes) signals seniority; so does quoting the distance floor when
  someone proposes "faster bandwidth" across an ocean.

## Interview Questions

### A page takes 3 seconds to load and the team proposes a bandwidth upgrade. Walk your reasoning.

Decompose first: count round trips (DNS, TCP, TLS, request, resource
waves) versus bytes moved. Kilobyte payloads serialize in under a
millisecond on any modern link, so the 3 s lives in RTTs, server time, and
resource dependencies. At 50 ms RTT, ~10 round trips is already ~500 ms,
and the rest is server processing — fix with connection reuse, TLS 1.3,
multiplexing, edge caching, and backend profiling. Bandwidth upgrades only
the payload/bandwidth term, which is not dominant. Also check saturation:
if latency spikes only under load, it is queueing, not RTT.

### An API call makes 51 sequential queries at 50 ms RTT each. What are the numbers, and what are your options?

51 × 50 ms = 2,550 ms of pure round-trip waiting. Bandwidth is irrelevant —
the payloads are small. Options in order of impact: batch into one query
(~50 ms, 51×), parallelize the independent ones (~100 ms, two round-trip
times), cache repeated lookups, or move the caller next to the database to
shrink the RTT. The lesson: the round-trip count is the variable to attack.

### When *would* you recommend a bandwidth upgrade for a latency complaint?

Two cases. One: the workload is genuinely throughput-bound — bulk
transfers, backups, streaming, replication — where time ≈ payload/bandwidth
and the upgrade is linear (100 GB: ~13 min at 1 Gbps, ~80 s at 10 Gbps).
Two: the link is saturated, so observed latency is queueing delay
(bufferbloat); headroom or active queue management removes it. The
diagnostic separator: latency high at idle is RTT (bandwidth irrelevant);
latency high only under load is queueing (headroom helps).

## Key Takeaways

- Response time = round trips × RTT + payload/bandwidth + processing;
  bandwidth only touches the second term — diagnose which term dominates.
- RTT-bound workloads (page loads, N+1 queries, chatty protocols) are
  invisible to bandwidth upgrades; the fixes are batching, parallelism,
  fewer handshakes, caching, and proximity.
- Throughput-bound workloads (bulk transfer) are exactly where bandwidth
  is the fix, with honest linear arithmetic.
- Saturation is the honest exception: queueing delay is latency, and
  headroom (or AQM) removes it — latency-under-load versus latency-at-idle
  is the diagnostic.
- Distance floors RTT at the speed of light in fiber; no contract upgrade
  renegotiates physics.

## Cross-References

- [Connection Atlas: Scheduling & Queueing](../connection-atlas/scheduling-queueing.md)
  — the queueing mechanics behind the saturation exception
- [Assumptions Hunt: Network & Distributed](../assumptions-hunt/network-distributed.md)
  — the hidden assumptions in "the network will just get faster"
- [Latency Numbers Every Programmer Should Know](../../interview/system-design/latency-numbers.md)
  — the magnitudes this page's arithmetic uses
- [Networks Overview](../../networks/overview.md) — the layered reality
  behind RTT and throughput
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- J. Dean. *Building Software Systems at Google and Lessons Learned*.
  LADIS 2009 keynote — the origin of the "latency numbers every programmer
  should know" table, cited by title.
- S. Cheshire. *It's the Latency, Stupid*. 1996 — the classic essay on
  latency versus bandwidth, cited by title.
- J. Dean and L. A. Barroso. *The Tail at Scale*. Communications of the
  ACM, 2013 — latency variability and tail behavior in large services,
  cited by title.
- E. Rescorla. *The Transport Layer Security (TLS) Protocol Version 1.3*.
  RFC 8446, August 2018 — the 1-RTT (and 0-RTT) handshake behind the
  round-trip reductions above.
  <https://www.rfc-editor.org/rfc/rfc8446.html>
