# "UDP is unreliable, so serious applications can't use it"

## Overview

Every networking course teaches the contrast in the same shape: TCP is the
reliable protocol, UDP is the "unreliable" one, and reliability is not
optional for serious systems. The conclusion most students carry away —
that anything important must ride on TCP — is contradicted by the traffic
mix of the modern web itself: HTTP/3, the current version of the protocol
that carries the web, runs on QUIC over UDP, and DNS — the Internet's
oldest load-bearing service — has run on UDP since 1983. This page audits
the claim that serious applications cannot use UDP, shows what UDP's
unreliability actually consists of, demonstrates that reliability is a
layer an application can *choose* to build (in userspace, per its own
semantics), and gives the honest accounting of why TCP's built-in
reliability is a blessing for most applications and a tax on a few.

## The Claim, Stated Fairly

The strongest common form is: "UDP can drop, reorder, and duplicate
packets, and it does nothing about it — so no serious application can
afford to build on it." The claim deserves fairness because UDP's
description is accurate and because, for most developers, the conclusion
has never failed them: request/response APIs, file transfer, and database
connections genuinely belong on TCP, and every attempt to hand-roll
transport logic has a well-earned reputation for producing subtle bugs.
The kernel of truth is that UDP really does provide almost nothing: no
delivery guarantee, no ordering, no flow control, no congestion control,
no connection state. The claim under audit is the *inference* from "UDP
provides no reliability" to "applications on UDP get no reliability" —
an inference that treats the kernel's feature list as the ceiling of what
a protocol stack can deliver.

## Verdict

**False.** UDP's unreliability is a description of the datagram service,
not a property of applications built on it; reliability is a mechanism,
and mechanisms can be added at whatever layer chooses to pay for them.
QUIC (RFC 9000) and HTTP/3 (RFC 9114) reimplement streams, reliability,
and congestion control above UDP and now serve a large share of web
traffic; game netcodes build ack-and-delta systems tuned to their
freshness requirements; DNS simply retries at the application layer. The
serious question is never "is UDP reliable?" but "which reliability
policy does this workload need, and where is it cheapest to implement?"
TCP is one pre-integrated answer with well-known costs — head-of-line
blocking and kernel rigidity chief among them — not the only possible one.

## Why People Believe It

The kernel of truth is that UDP's service model is exactly as advertised.
RFC 768 gives applications a checksum (mandatory in IPv6), ports for
demultiplexing, and the preservation of message boundaries — and nothing
else. Packets genuinely drop when queues overflow, reorder on equal-cost
paths, and duplicate when retransmission ambiguity strikes. Anyone who has
watched a naive UDP file transfer lose bytes has direct evidence, and the
discipline needed to do better is real: retransmission timers, sequence
space, ack tracing, congestion control, and flow control are subtle
individually and brutal in combination.

Three props hold the belief up. First, the kernel *does* provide
reliability for free under TCP, and free beats hand-rolled — most
applications should take the deal, so the advice is directionally correct
for most listeners. Second, the historical UD P experience that shaped
generation after generation of engineers was TFTP and early games: janky,
lossy, and visibly worse than TCP alternatives, reinforcing the moral of
the story. Third, "unreliable" is a loaded word — it sounds like a defect
rather than a deliberate design choice to leave policy to the application,
so the framing itself biases the conclusion.

What is lost is the cost side of TCP's integrated deal. Reliability at the
byte-stream layer means *ordered* delivery, which couples every stream
multiplexed on one connection: when one packet drops, TCP withholds
everything behind it even if the application could have used it. Ordering,
flow control, and congestion control are welded into the kernel, take
years of RFCs to evolve, and are identical for a chess move and a
gigabyte transfer. UDP is not "less than TCP"; it is *before* TCP — a
substrate on which a transport can be shaped to the workload.

## The Correct Formulation

| Property | UDP alone | UDP + app/quic layer | TCP |
|---|---|---|---|
| Delivery | Best-effort; checksum, no repair | Repair policy chosen per stream: ack/retransmit, FEC, or accept loss | Fully reliable byte stream |
| Ordering | None | Selective: order what the application orders | Total ordering, always |
| Flow control | None | Per-application budgets | Built-in, kernel-managed |
| Congestion control | None (sender's responsibility) | Per-protocol: QUIC copies TCP-style AIMD; games may rate-limit by policy | Built-in (Reno/CUBIC/BBR family) |
| Head-of-line blocking | None (no ordering to block on) | Streams decoupled (QUIC) — one lost packet stalls only its stream | Yes: one drop stalls the whole byte stream |
| Connection migration | N/A | Connection IDs survive address changes (QUIC) | Bound to the 4-tuple; a path change resets the connection |

The precise statement: UDP provides a datagram service; every higher
property is a policy decision. The design space has three honest options.
Option one: do nothing and make requests idempotent — DNS clients resend
after a timeout because resending a *query* is safe; this is why DNS over
UDP has worked for four decades despite zero transport reliability. Option
two: build selective reliability — acks, retransmission, and delta
compression for the data that matters, freshness over completeness for
the data that does not, which is the shape of every competitive game
netcode since Quake. Option three: use QUIC, a standardized transport
over UDP that supplies streams, reliability, and congestion control with
the structural fixes TCP cannot make in-kernel.

## Where It Breaks

**HTTP/3: the existence proof at web scale.** The HTTP/2 experience made
TCP's cost concrete: a single lost TCP segment stalls *all* streams on
the connection, because TCP delivers one ordered byte stream no matter
how the application multiplexed requests. Measured packet loss of under
1% degraded HTTP/2 throughput below HTTP/1.1's (six parallel
connections) in the well-known measurements that motivated QUIC. HTTP/3
moves the transport to QUIC over UDP: independent streams repair
individually, eliminating transport-level head-of-line blocking; the
handshake folds transport and TLS negotiation (0-RTT resumption);
connection IDs survive network switches, which a TCP 4-tuple cannot.
Chrome, and through it a majority of browsers, now speak HTTP/3 by
default to services that enable it — "serious applications" in the most
literal sense, running on the "unreliable" protocol.

**Game netcode: reliability of the wrong thing.** A first-person shooter
transmitting position updates does not want delivery guarantees for old
state — by the time packet N arrives, N+2 has superseded it, and the
only thing worse than a dropped 50 ms-old position is retransmitting it
ahead of fresh ones. Real netcodes send periodic full snapshots or delta
updates over UDP, add an ack channel for *reliable* sub-channels (chat,
loadouts, kills), interpolate and extrapolate to hide loss, and rate-limit
fairly by policy. This is a reliability design — a *different* one,
optimized for freshness — and it is unavailable inside TCP's mandatory
total ordering, which is precisely why games left TCP.

**DNS and the idempotent-request regime.** A DNS query is safe to
repeat, so the application does not need per-packet reliability — it
needs a timeout and a retry policy, plus truncation handling that falls
back to TCP for oversized responses (as specified alongside the UDP
port in the DNS specifications). UDP further allows a lightweight client
to avoid per-lookup connection setup and lets servers shed load by
simply not answering (the historical root-server mitigation against
flooding). The design point generalizes: wherever requests are idempotent
and latency matters more than per-packet guarantees, "reliability at the
application layer" is one retry statement long.

**When it accidentally works.** The myth's regime is real: most services
never leave TCP's comfort zone. Workloads that need *all* the bytes in
*order* — file transfer, request/response APIs, database sessions — find
TCP's integrated reliability, flow control, and congestion avoidance
correct, battle-tested, and free of custom-code bugs, and they would
gain nothing from QUIC-style stream independence because they open one
stream anyway. Hand-rolled transports have produced real, decades-long
bug lists; congestion-control misbehavior by custom UDP protocols has
been a genuine Internet-scale concern. The claim "fails" not because
most developers are wrong to stay on TCP, but because "serious" was
never the dividing line — workload shape is.

## Practical Implications

- Choose by loss policy, not fear: if stale data is worthless (state
  sync, telemetry), UDP with freshness-oriented design beats ordered
  retransmission; if every byte matters (files, transactions), use TCP
  or QUIC streams — do not hand-roll reliability without need.
- If you enable HTTP/3/QUIC, do not assume transport HOL is gone
  everywhere: QUIC removes *transport*-level blocking, but a lost
  initial packet can still stall streams that need it, and application-
  level serialization (one big response blocking a small one in a queue
  you wrote) remains your problem.
- Respect the responsibilities UDP leaves with you: without congestion
  control your protocol is rude to shared links; implement pacing and
  backoff (or use QUIC's) before exposing it to the public Internet.
- Remember the edge cases UDP gives you for free that TCP cannot:
  message boundaries, connection migration (QUIC connection IDs), and
  broadcast/multicast on LANs — sometimes the choice is not about
  reliability at all.
- In interviews, name the three-layer answer: what UDP guarantees,
  what each design option adds, and why TCP's ordering is a feature or
  a bug depending on whether the workload has one logical stream or many.

## Interview Questions

### What exactly does UDP guarantee, and what are the first three things an application must add to become reliable?

UDP guarantees checksum-based error detection (mandatory in IPv6),
port-based demultiplexing, and preservation of message boundaries — and
explicitly nothing about delivery, ordering, duplication, flow, or
congestion. To become reliable an application needs a sequence/ack
scheme with retransmission timers, receiver-side flow control (so a
fast sender cannot drown a slow one), and congestion control (so the
sender reacts to loss as a shared-network signal). QUIC is the
standardized version of exactly this list.

### Why does a single lost packet hurt HTTP/2 more than HTTP/1.1, and how does HTTP/3 fix it?

HTTP/1.1 spreads requests across multiple TCP connections, so one loss
stalls only its connection; HTTP/2 multiplexes all streams over one TCP
byte stream, so one loss stalls every stream behind it in the ordering —
transport head-of-line blocking. HTTP/3 moves streams into QUIC, where
each stream's data is acked and retransmitted independently, so loss
repairs only the affected stream. Residual blocking can remain at the
application layer, which no transport fixes.

### Design a reliable 1 GB file transfer over UDP. What are your non-negotiables?

Sequence-numbered data blocks with selective acks and fast retransmit
(per-block, not stop-and-wait), a congestion-control scheme with slow
start and AIMD-style backoff so the flow coexists with TCP traffic,
receiver flow control via an advertised window, a checksum/verification
pass over the reassembled file, and session establishment with a
handshake to prevent accepting stale duplicates. Then ask the
discriminating question: does anything in these requirements argue
against TCP? Usually not — which is the honest conclusion.

### Name a workload where TCP is the *wrong* transport even though reliability is required, and justify it.

Live state synchronization: the useful content is the newest state, so
total-order retransmission delivers obsolete bytes first and delays
fresh ones — TCP's ordering converts a freshness workload into a
delivery workload. The fix is UDP with snapshot/delta state, an ack
channel for genuinely-reliable sub-messages, and interpolation on the
receiver. VoIP and video are the same shape: FEC and jitter buffers beat
retransmission for anything real-time, which is why RTP rides on UDP.

## Key Takeaways

- UDP's "unreliability" is a service definition, not a prohibition;
  reliability is a mechanism the application chooses to add — or to
  deliberately not add.
- The three honest designs above UDP are idempotent retry (DNS),
  selective per-channel reliability (game netcode, WebRTC), and a
  full userspace transport (QUIC) — each tuned to a workload shape TCP
  serves poorly or not at all.
- TCP's reliability is real and mostly free, but it bundles total
  ordering (head-of-line blocking), kernel immutability (slow to evolve,
  no path migration), and one-size congestion control; HTTP/3 exists
  because those bundles cost enough at web scale.
- The myth "accidentally works" because most workloads need every byte
  in order and should stay on TCP — the error is stating that as a law
  instead of a workload observation.
- The interview-ready sentence: "UDP leaves policy to the application;
  the serious question is which reliability policy the workload needs
  and where it is cheapest to implement."

## Cross-References

- [Misconception: TCP Guarantees the Application Receives the Data](./tcp-guarantees-delivery.md)
  — the sibling myth about what TCP's reliability actually covers
- [TCP vs UDP](../../networks/udp/tcp-vs-udp.md) — the book's full
  comparison of the two transports' mechanics
- [QUIC](../../networks/http/quic.md) and [QUIC Internals](../../networks/http/quic-internals.md)
  — how reliability, streams, and congestion control are rebuilt above UDP
- [HTTP/3](../../networks/http/http3.md) — the deployment story of the
  web's migration off TCP
- [SCTP](../../networks/protocols/sctp.md) — the message-oriented,
  multi-streaming transport that anticipated QUIC's fixes
- [UDP Applications](../../networks/udp/applications.md) — DNS, VoIP,
  gaming, and the workload patterns that choose UDP deliberately
- [Why-Not Handbook: TCP vs UDP](../why-not-handbook/tcp-vs-udp.md)
  — the decision framework for the paired transport choice this page
  audits the misconception around

## References

- J. Postel (ed.). *User Datagram Protocol*. RFC 768, August 1980.
  <https://www.rfc-editor.org/rfc/rfc768.html>
- J. Iyengar and M. Thomson (eds.). *QUIC: A UDP-Based Multiplexed and
  Secure Transport*. RFC 9000, May 2021.
  <https://www.rfc-editor.org/rfc/rfc9000.html>
- M. Bishop (ed.). *HTTP/3*. RFC 9114, June 2022.
  <https://www.rfc-editor.org/rfc/rfc9114.html>
- P. Mockapetris. *Domain Names — Implementation and Specification*.
  RFC 1035, November 1987 (UDP queries, truncation, TCP fallback).
  <https://www.rfc-editor.org/rfc/rfc1035.html>
- R. Stewart (ed.). *Stream Control Transmission Protocol*. RFC 4960,
  September 2007. <https://www.rfc-editor.org/rfc/rfc4960.html>
