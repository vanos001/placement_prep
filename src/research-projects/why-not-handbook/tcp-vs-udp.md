# TCP vs UDP: Ordered Reliable Bytes vs Unreliable Datagrams

## Overview

TCP and UDP differ by exactly one design decision: **where reliability lives**. TCP builds a reliable, ordered, congestion-controlled byte stream into the transport — every byte is numbered, acknowledged, retransmitted, and delivered in order, and the congestion window is managed by the kernel. UDP provides almost nothing: a checksummed datagram (8-byte header, payload boundary preserved) that may arrive, may not, may be reordered, and has no built-in answer to congestion. Every property TCP has, UDP simply declines to provide — and that refusal is the feature, because it hands the transport decisions back to the application.

The interesting engineering is therefore not "which is better" but "which reliability model does the workload need, and who should own it." Real-time media rejects retransmitted data as worthless on arrival; DNS prefers one datagram and a retry clock over a connection; QUIC — arguably the most consequential transport design of the last decade — is a demonstration that "TCP's reliability, rebuilt on UDP, minus head-of-line blocking, in userspace" is worth an entire protocol generation. This page runs the [handbook framework](./index.md) over the pair; the sibling repo chapter [TCP vs UDP](../../networks/udp/tcp-vs-udp.md) holds the quick-reference table, while here the mechanisms are derived. The preview: **TCP wins whenever all bytes matter and ordering matters and you do not want to implement loss recovery; UDP wins whenever late data is worthless, when you need datagram semantics, or when you are building your own transport** — and the edge cases (lossy links, MTU black holes, middlebox behavior) decide more real deployments than the default argument does.

## Step 1: The Problem and Its Constraints

The workload: two endpoints exchange messages over a network that drops, reorders, delays, and duplicates packets, with a path MTU smaller than some messages. Constraints that decide the transport:

- **Is every byte valuable?** A file transfer where 99.9% delivered is a corrupted file is a TCP workload. A video call where a retransmitted frame arrives 300 ms late is a UDP workload — the data expired in transit.
- **Is ordering meaningful across messages?** Independent state updates ("player is now at position X") supersede each other; ordered delivery of a *stale* update is worse than a dropped one. Byte streams cannot express supersession; datagrams can.
- **Who pays for congestion control?** TCP's congestion window is mandatory and kernel-managed — nobody ships a TCP stack that ignores loss. UDP has none; an application flooding the network with datagrams is doing something TCP makes impossible, which is both a flexibility and a responsibility.
- **Connection setup tolerance.** TCP pays a handshake (one RTT before the first byte, plus TIME_WAIT state afterwards — see [TCP timers](../../networks/tcp/timers.md)); UDP sends immediately. For a single 40-byte query, the handshake can double the latency budget.
- **Middlebox traversal.** TCP is universally supported; UDP is sometimes blocked, throttled, or given short NAT binding timeouts. The "we chose UDP" plan must survive networks you do not control.

## Step 2: The Mechanisms

### Option 1: TCP — the reliable ordered byte stream

- **Sequence numbers and cumulative ACKs.** Every byte is numbered; the receiver acknowledges the highest in-order byte. Out-of-order arrivals are buffered, not delivered — ordering is enforced by holding back everything behind a gap.
- **Retransmission.** A retransmission timeout fires when an ACK is late; duplicate ACKs trigger [fast retransmit](../../networks/tcp/fast-retransmit.md) and [fast recovery](../../networks/tcp/fast-recovery.md). The mechanisms are tuned for throughput on long-lived flows (see [congestion control](../../networks/tcp/congestion-control.md), slow start and AIMD in [Reno](../../networks/tcp/reno.md) and [CUBIC](../../networks/tcp/cubic.md)).
- **Flow control.** The receive window keeps a sender from overrunning a receiver — a guarantee UDP does not make even in principle.
- **The byte-stream abstraction's cost.** TCP delivers a *stream*: message boundaries do not survive (the receiver reads bytes, not "packets"), and the ordering enforcement creates **head-of-line blocking** — segment 5,001 lost means segments 5,002 through 6,000 sit in the receive buffer regardless of which application messages they belong to. One lost segment stalls every multiplexed conversation sharing that connection for at least one RTT of retransmission.

### Option 2: UDP — the honest datagram

- **Datagram semantics.** Each datagram is independent: boundaries preserved, no ordering, no retransmission, no connection state on either side. A lost datagram costs nothing but its own content; nothing behind it waits.
- **Checksum, and that is mostly it.** The IPv4 UDP checksum is optional (zero means "skip"); IPv6 makes it mandatory. There is no congestion control, no flow control, no handshake — the application's problem, by design.
- **Fragmentation as the hidden failure.** A datagram larger than the path MTU is fragmented by IP (IPv4) or dropped-with-ICMP (IPv6, expecting [PMTUD](../../networks/protocols/pmtud-and-mss.md)). Fragments are not retransmitted individually: losing one fragment of a large datagram discards the whole datagram, and some firewalls drop fragments or the ICMP that would report the problem — the classic **PMTUD black hole**.
- **Ownership transfer.** Because UDP provides nothing, everything above it is the application's design: DNS adds its own retry timeout and re-asks; RTP adds sequence numbers and jitter buffers; QUIC rebuilds the entire TCP reliability suite — streams, ACKs, loss recovery, [congestion control](../../networks/advanced/quic-congestion-control.md) — in userspace, where it can evolve at application release cadence instead of kernel-and-decade cadence. [QUIC](../../networks/http/quic.md) also encrypts transport metadata, making the middlebox-opaque design explicit; connection migration ([QUIC connection migration](../../networks/protocols/quic-connection-migration.md)) falls out of the connection being identified by a connection ID rather than a 4-tuple.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | TCP | UDP |
|----------|-----|-----|
| Delivery guarantee | All bytes, exactly once, in order (within connection lifetime) | None: loss, duplication, reordering all possible |
| Message boundaries | Not preserved (byte stream) | Preserved (datagrams) |
| Head-of-line blocking | Structural: one lost segment stalls the stream | None: datagrams are independent |
| Congestion control | Mandatory, kernel-owned | None; application-owned if any |
| Flow control | Receive window | None |
| Setup cost | Handshake: 1 RTT + state (TIME_WAIT after close) | None |
| First-byte latency | Handshake + RTT | One RTT |
| Application complexity | Low: read/write | High: reliability, reordering, retry, rate limiting are yours |
| Middlebox behavior | Universal | Sometimes blocked/throttled; NAT bindings time out |
| Signature failure | Head-of-line stalls on loss; bufferbloat under loss-based CC on wireless | Fragment-loss discards whole datagrams; amplification abuse (DNS reflection) |

**The latency profile difference is structural, not tuning.** TCP's first byte on a fresh connection waits out the handshake; a resumed TLS 1.3 session or [TCP Fast Open](../../networks/advanced/tcp-fast-open.md) reduces but does not eliminate the cost. UDP's first datagram is sent immediately — which is why DNS and real-time transports are datagram-based. The mirror image: TCP's congestion control is exactly what lets a bulk transfer coexist with the rest of the internet; an application that replaces TCP with raw UDP at scale *inherits the duty not to congest the network*.

## Step 4: When Each Wins

**UDP wins** when: data is time-sensitive and superseded — voice, video, game state (late data is worthless, so retransmission is waste); the exchange is a small query/reply where a connection is pure overhead (DNS, NTP, DHCP); multicast or broadcast is needed; you are building a transport (QUIC, custom RPC over datacenter fabrics) and want userspace control; or datagram boundaries are the natural model and you will implement the reliability you actually need, no more.

**TCP wins** when: all bytes matter and order matters (file transfer, web, email, database replication); you want battle-tested congestion control and flow control for free; the connection is long-lived and the setup cost amortizes; or middlebox reachability is a requirement — TCP to port 443 with TLS works essentially everywhere on Earth, which is a deployment guarantee no UDP-based design can yet make. The "loser" here is not a strawman: UDP's winning workloads are real, but any UDP-based system that moves bulk data must reimplement enough of TCP (acknowledgment, retransmission, congestion avoidance) that QUIC's size — tens of thousands of lines — is the honest measure of what "just use UDP" means.

## Step 5: Edge Cases and Counterexamples

- **TCP on lossy wireless: the congestion misdiagnosis.** Loss-based congestion control (Reno, CUBIC) treats any loss as congestion and cuts the window — but wireless links lose packets to noise, not queue overflow. The result is a sawtooth throughput collapse on high-loss links even when the path is idle; bufferbloat makes it worse by inflating RTT until every loss looks like congestion. The responses — [BBR](../../networks/tcp/bbr.md) modeling bottleneck bandwidth instead of inferring it from loss, and [datacenter TCP](../../networks/advanced/datacenter-tcp.md) using ECN marks instead of drops — are both, at heart, fixes for trusting the wrong loss signal.
- **UDP MTU/fragmentation: the whole-datagram discard.** A 8,000-byte datagram on a 1,500-byte-MTU path becomes six fragments; losing any one discards all six at reassembly. Worse, only the first fragment carries the UDP header, so middleboxes that filter on transport headers handle fragments badly, and if the ICMP "fragmentation needed" message is filtered, the sender keeps sending too-large datagrams into a void — the PMTUD black hole. This is why QUIC mandates a 1,200-byte minimum datagram and initial-packet padding: stay under the almost-everywhere MTU, and pad to prevent amplification attacks from small spoofed queries.
- **UDP's amplification tax.** A spoofed small DNS query can elicit a large response — reflection/amplification DDoS. The protocol has no handshake to verify the requester's address, so the ecosystem's answer is operational (rate limiting, response rate limiting, BCP-style guidance) rather than protocol-level. Any UDP service design inherits this review question; TCP's handshake (with SYN cookies for the flood case — see [SYN cookies](../../networks/tcp/syn-cookies.md)) at least binds the peer to a return path.
- **The DNS edge case: UDP-first with TCP fallback.** DNS responses over 512 bytes (or the EDNS negotiated size) fall back to TCP — a designed-in acknowledgment that the datagram model serves the common case and the stream model serves the tail. Encrypted DNS ([DoH](../../networks/dns/doh.md)) moves even the common case onto HTTP/TCP-family transports, trading the 1-RTT datagram for middlebox-proofness — the same trade QUIC makes.
- **NAT binding timeouts: UDP's quiet liveness problem.** A NAT mapping for an idle UDP flow expires in tens of seconds to minutes; the sender learns nothing. Applications must send keepalives (STUN-based, see [STUN/TURN](../../networks/advanced/stun-turn.md)) to hold the binding. TCP's connection state is longer-lived and its keepalives standardized (see [keepalive](../../networks/tcp/keepalive.md)) — "the flow worked" is not the same as "the flow will still work in 60 seconds."
- **Head-of-line blocking inside QUIC.** QUIC solves TCP's transport-level HOL by making streams independent, but the QUIC packet layer still acknowledges packets carrying multiple streams' frames: losing a packet can delay frames from *other* streams until its retransmission is recovered. The HOL problem is reduced, not abolished — a good interview answer names which layer each guarantee lives at.

## Step 6: Decision Framework

1. **Is every byte of the transfer valuable, in order?** Yes → TCP; retransmission and ordering are the product.
2. **Is late data worthless?** (Media, game state, sensor streams.) Yes → UDP; design supersession and drop policies at the application layer.
3. **Is the exchange a short query/reply where connection setup doubles latency?** Yes → UDP (or QUIC if 0-RTT and encryption are wanted).
4. **Are you building a transport or protocol?** Yes → UDP is the substrate by definition; budget for loss recovery, congestion control, and the amplification/MTU constraints from day one.
5. **Does the path include middleboxes you do not control?** (Public internet, enterprise networks.) Then TCP is the reachability default; UDP needs a fallback story (DNS-style TCP fallback, TURN relay).
6. **Will your datagrams exceed the path MTU?** If yes, either clamp payloads under ~1,200 bytes for the public internet or implement and test PMTUD paths — fragmented UDP is a reliability illusion.
7. **Default in doubt:** TCP for anything that must not lose data; UDP only with a concrete answer to "what does the application do on loss, reorder, and congestion?" — if the answer is "what TCP does," use TCP.

## Interview Questions

1. **What is TCP head-of-line blocking, and why does UDP not have it?** TCP enforces in-order delivery by holding back every byte behind a missing segment; one loss stalls all subsequent data on the connection regardless of application-message independence. UDP delivers each datagram independently, so a loss costs only that datagram. QUIC exists largely to get TCP's reliability without this coupling — streams recover independently at the transport layer.
2. **Why does QUIC exist if TCP already provides reliability?** Reliability in TCP is kernel-owned and decades-slow to evolve; QUIC rebuilds streams, loss recovery, and congestion control in userspace where applications ship improvements at release cadence, adds transport-level encryption and connection migration, and removes TCP's stream-level head-of-line blocking. UDP is the substrate because it provides nothing to fight with.
3. **A UDP application's large datagrams intermittently vanish while small ones flow. Diagnose.** Path-MTU fragmentation: datagrams above the path MTU are fragmented, and either a fragment is dropped (discarding the whole datagram, since fragments are not individually recoverable) or the ICMP fragmentation-needed message is filtered, producing a PMTUD black hole. Fix: keep datagrams under the safe MTU (~1,200 bytes for the public internet) or implement PLPMTUD-style probing.
4. **Why is loss-based TCP congestion control problematic on wireless links, and what are two protocol-level responses?** Wireless loss is noise, not congestion, but Reno/CUBIC interpret any loss as congestion and collapse the window — throughput drops even on an idle path. BBR models bottleneck bandwidth and RTT instead of inferring congestion from loss; DCTCP/ECN-based approaches get explicit congestion signals instead of drops.
5. **Your real-time game uses UDP. What responsibilities did you just inherit from TCP?** At minimum: some form of acknowledgment or supersession policy for important state, rate limiting/congestion avoidance to protect the network, jitter handling for reordering, keepalives for NAT bindings, and MTU clamping for payloads. The datagram is free; the transport engineering is not.

## Key Takeaways

- The single design variable is where reliability lives: in the transport (TCP, mandatory and kernel-owned) or in the application (UDP, optional and explicitly designed).
- TCP's guarantees are a package: reliability, ordering, flow control, and congestion control arrive together, paid for in handshake latency and head-of-line blocking.
- UDP's "no features" is the feature: datagram boundaries, immediate send, and full control — with the duty to implement whatever reliability the workload actually needs.
- QUIC is the existence proof that the interesting question is not TCP vs UDP but "which layer owns recovery" — userspace evolution, transport encryption, and per-stream independence are the wins TCP could not ship.
- The edge cases that decide real deployments: lossy-link congestion misdiagnosis, MTU fragmentation black holes, amplification abuse, and NAT timeout behavior — none appear in the default TCP-vs-UDP table, and all appear in production.

## Cross-References

- [TCP vs UDP](../../networks/udp/tcp-vs-udp.md) — the repo's quick-reference chapter for this pair.
- [UDP Applications](../../networks/udp/applications.md) and [UDP Header](../../networks/udp/header.md) — the datagram mechanics and their users.
- [TCP Flow Control](../../networks/tcp/flow-control.md) and [Congestion Control](../../networks/tcp/congestion-control.md) — the guarantees UDP omits.
- [TCP Timers](../../networks/tcp/timers.md) — TIME_WAIT and retransmission timing that shape connection lifecycles.
- [QUIC](../../networks/http/quic.md), [QUIC Congestion Control](../../networks/advanced/quic-congestion-control.md), and [QUIC Connection Migration](../../networks/protocols/quic-connection-migration.md) — reliability rebuilt on UDP.
- [PMTUD and MSS](../../networks/protocols/pmtud-and-mss.md) — the fragmentation black-hole mechanism in depth.
- [BBR](../../networks/tcp/bbr.md) and [Datacenter TCP](../../networks/advanced/datacenter-tcp.md) — congestion signals that fix the lossy-link misdiagnosis.
- [TCP Lifecycle: Follow-up Tree](../followup-tree/tcp-lifecycle.md) — escalating interview chain on handshakes, TIME_WAIT, and congestion.
- [TCP Guarantees Delivery: Misconceptions](../misconceptions/tcp-guarantees-delivery.md) — the false belief this page's failure modes correct.
- [Checksums and Erasure Coding: Connection Atlas](../connection-atlas/checksums-erasure-coding.md) — integrity and repair beyond the UDP checksum.
- [DNS Resolution](../../networks/dns/resolution.md) — the canonical UDP-first, TCP-fallback workload.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
