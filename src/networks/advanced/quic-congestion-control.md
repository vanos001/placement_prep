# QUIC Congestion Control and Loss Detection (RFC 9002)

TCP's congestion controller is kernel code, shared and policy-bound by the OS. A
QUIC endpoint instead links its own controller into the application: the kernel
only sees UDP datagrams, and every connection carries a private window
controller, RTT estimator, and pacer in user space. That inversion is why QUIC
could ship pacing, per-connection ECN handling, and swappable algorithms
(NewReno, CUBIC, BBR) without kernel releases — and why the IETF had to specify
a baseline controller inside the transport spec: RFC 9002, *QUIC Loss Detection
and Congestion Control*, a NewReno-derived reference controller plus a loss
detector built on monotonically numbered packets. Protocol basics (streams,
TLS 1.3 handshake, frames) live in [QUIC](../http/quic.md) and [QUIC
internals](../http/quic-internals.md); the mechanics below go past their summaries.

## One feedback loop, two congestion signals, three loss detectors

```text
              per-packet ACK frames (ACK ranges + ECN counts)
                                  |
              +-------------------v---------------------+
              |  loss detection (RFC 9002 S6)            |--> retransmit FRAMES
              |  packet threshold: >= 3 later acks       |    (fresh packet numbers)
              |  time threshold: unacked > 9/8 RTT       |
              |  PTO: silence beyond sRTT+4rttvar+MAD    |
              +-------------------+---------------------+
                                  | loss / ECN-CE increase = congestion event
              +-------------------v---------------------+
              |  NewReno controller (S7, App. B):        |
              |  halve cwnd | persistent -> kMinimumWin  |
              +-------------------+---------------------+
                                  | paced at cwnd/sRTT (S7.7)
                                  v   UDP, gated by anti-amplification:
                                      3x bytes received (RFC 9000 S8.1)
```

## What the reference controller keeps from TCP

RFC 9002 §7 names its lineage: "similar to TCP NewReno [RFC6582]", in three
states — slow start, recovery, congestion avoidance. Windows are in *bytes* of
QUIC payload; `max_datagram_size` is the PMTU-derived packet size (minimum
1200 bytes, IP/UDP overhead excluded — Appendix B.2).

| Rule | RFC 9002 behavior | Where |
|---|---|---|
| Initial window | min(10 x max_datagram_size, max(2 x max_datagram_size, 14,720)) — the 14,720 B cap binds above 1472 B | §7.2 |
| Minimum window | 2 x max_datagram_size; the floor of every reduction | §7.2 |
| Slow start | cwnd += bytes acked (exponential); MUST exit on loss or ECN-CE increase | §7.3.1 |
| Recovery entry | ssthresh = cwnd x kLossReductionFactor (0.5); cwnd = max(ssthresh, kMinimumWindow) | §7.3.2, B.6 |
| Recovery exit | when a packet *sent during* recovery is acked — not, as TCP does, when the lost segment is acked | §7.3.2 |
| Congestion avoidance | AIMD: at most one max_datagram_size of increase per cwnd of acked data | §7.3.3 |
| Persistent congestion | cwnd MUST drop to kMinimumWindow; sender re-enters slow start | §7.6.2 |

The initial window is IW10 (RFC 6928) rescaled for UDP: 10 packets, but the byte
cap is 14,720 = 10 x 1472, the largest useful UDP payload on a 1500-byte
Ethernet link, because UDP's 8-byte header leaves more room than TCP's 20-byte
header. PTO expiry itself never shrinks the window — the RTO-equivalent path is
persistent congestion.

## The loss detection trio

Loss is declared per packet number by three detectors (§6.1.1: implementations
SHOULD NOT lower the packet threshold below 3):

1. **Packet threshold** — an unacked packet is lost once three later packets in
   the same packet number space are acknowledged (kPacketThreshold = 3, from
   TCP practice in RFC 5681/6675). The QUIC twist: middleboxes can no longer
   see or reorder the flow (packet numbers are encrypted).
2. **Time threshold** — once a later packet is acked, an earlier one is lost if
   unacked for max(kTimeThreshold x max(smoothed_rtt, latest_rtt), kGranularity):
   kTimeThreshold = 9/8, kGranularity = 1 ms RECOMMENDED (§6.1.2). TCP's RACK
   (RFC 8985) uses a slightly larger 5/4.
3. **Probe Timeout (PTO)** — silence is *not* loss. With no ack for
   PTO = smoothed_rtt + max(4 x rttvar, kGranularity) + max_ack_delay (§6.2.1;
   max_ack_delay = 0 for Initial/Handshake spaces), send at least one
   ack-eliciting probe — up to two datagrams (§6.2.4). Probes MUST NOT be
   blocked by the congestion controller but count as in flight, so
   bytes_in_flight may exceed cwnd (§7.5).

```text
  packets sent:   PN 40   41   42   43   44   45
  acked ranges:              [43..45 acked]      PN 40,41,42: >= 3 later acks
                             \------- time -------/   -> packet-threshold loss
                                                     -> also > 9/8 RTT old:
                                                        time-threshold loss
  total silence:  ........ nothing acked for PTO .......  -> PTO: send 2 probes,
                                                           cwnd untouched (S7.5)
```

Loss always triggers retransmission, but the window shrinks only outside a
recovery period — the once-per-round-trip rule TCP NewReno encodes with
duplicate-ACK counting.

## Anti-amplification: the other ceiling on the server's window

Address validation imposes a ceiling that is not a congestion rule at all.
RFC 9000 §8.1: "Prior to validating the client address, servers MUST NOT send
more than three times as many bytes as they have received" (respect it: §6.2.2.1,
§7.2):

- The limit does not modify cwnd — it can just prevent it from being used, so
  the controller may look application-limited during the handshake.
- A server at the limit MUST NOT arm its PTO timer (probes would violate the
  cap); each client datagram restores credit and re-arms the timer.
- The handshake deadlock (server out of credit, client out of reasons to send)
  is broken by requiring the *client* to send on PTO — a duty TCP never had.
- On migration, cwnd and the RTT estimator reset (RFC 9000 §9.4) and the 3x cap
  re-applies until PATH_CHALLENGE/PATH_RESPONSE validates the new path.

## ECN: the second congestion signal

If the path validates ECN (RFC 3168, updated by RFC 8311), a rising ECN-CE count
reported in the ACK frame is treated exactly like loss: `ProcessECN` (B.7)
raises a congestion event and exits slow start; during recovery it does nothing
extra (wire-side machinery: RFC 9000 §13.4). Counts are compared monotonically
per ack, so the sender reacts at most once per round trip.

## Persistent congestion: the RTO equivalent, without the RTO timer

The most-misdescribed part: RFC 9002 does *not* use consecutive PTO expiries.
Persistent congestion is a duration test evaluated when acks resume (§7.6.2), if:

- two ack-eliciting packets were declared lost, and no packet sent between them
  was acknowledged;
- their send times span more than (smoothed_rtt + max(4 x rttvar, kGranularity)
  + max_ack_delay) x kPersistentCongestionThreshold — RECOMMENDED 3, "approximately
  equivalent to a TCP sender declaring an RTO after two TLPs";
- an RTT sample existed before the first of the two (handshake silence is exempt).

Reaction: cwnd MUST drop to kMinimumWindow and the sender re-enters slow start —
the only path back into slow start in the state machine. The spec rejects "N
consecutive PTOs" because application silence patterns can suppress or
manufacture PTO expiries; send-time durations cannot.

## Beyond NewReno: what stacks actually ship

NewReno is the floor, not the product: the controller is a plug point, and the
three most-deployed stacks have converged on CUBIC (RFC 9438 — it obsoletes RFC
8312 and updates RFC 5681) as the default, with BBR available or behind flags:

| Stack | Default | Alternatives in tree | Initial cwnd |
|---|---|---|---|
| quic-go (Go) | CUBIC (Chromium-derived port, beta 0.7, betaLastMax 0.85) | none — only the CUBIC sender remains in internal/congestion | 32 packets |
| quiche (Cloudflare, Rust) | CUBIC | Reno; BBRv2 ("bbr2_gcongestion") | 10 packets |
| MsQuic (Microsoft, C) | CUBIC | BBR, compiled only with QUIC_API_ENABLE_PREVIEW_FEATURES | 10 packets (InitialWindowPackets) |

Draft-vs-reality notes: the BBR Internet-Draft (draft-ietf-ccwg-bbr, "BBR
Congestion Control", Experimental, CCWG) specifies BBRv3, not the Linux kernel's
BBRv1 — its state machine is covered in [advanced congestion
control](congestion-control-advanced.md). And the user-space pay-off cuts both
ways: quic-go's 32-packet initial window (Chromium heritage) is divergence that
used to require kernel patches — the same IW10 that makes [datacenter
incast](datacenter-tcp.md) dangerous.

### The ACK-frequency problem (draft-ietf-quic-ack-frequency)

QUIC's default ACK discipline (RFC 9000 §13.2.1) lets the receiver delay acks
with no sender input, and that choice silently perturbs the sender's math:
max_ack_delay feeds the PTO formula, so a receiver that acks too rarely can time
out a sender whose packets were all delivered — spurious PTOs the controller
pays for. The draft ("QUIC Acknowledgment Frequency", still an I-D as of the
rfc-index checked 28 August 2026) adds an `ack_frequency` transport parameter
and two frames: ACK_FREQUENCY (sender requests the peer's reordering threshold
and max_ack_delay) and IMMEDIATE_ACK (force an ack now, e.g. on PTO probes).
Its motivation is mostly not congestion — ACK-packet CPU cost, ACK-bound reverse
paths (DOCSIS, LTE, satellite; the RFC 3449 problem), battery — but its PTO
rules are pure loss-recovery hygiene: while an ACK_FREQUENCY update is in flight
the sender MUST use the larger of old and new max_ack_delay, and a zero peer
reordering threshold forces PTO > max_ack_delay — both to avoid spurious PTOs.

## Worked simulator: the RFC 9002 rules, one round at a time

Each round is one RTT; windows are in packets. Trace A: sparse single-packet
loss. Trace B: a three-period blackout (persistent congestion).

```python
# NewReno-over-QUIC window simulator, packet units (1 packet = max_datagram_size).
# RFC 9002 rules: IW 10, kMinimumWindow 2 (S7.2/B.1); halving via kLossReductionFactor
# 0.5 (S7.3.2/B.6); recovery ends when a post-reduction packet is acked (S7.3.2);
# AIMD +1 per cwnd acked (S7.3.3); PTO probes not CC-blocked (S7.5/S6.2.4);
# persistent congestion after >= 3 lost PTO periods (S7.6.1-7.6.2).
IW, MIN_CWND, BETA, PTO_PC = 10, 2, 0.5, 3

def run(name, loss):
    cwnd, ssthresh, recovery, streak = IW, float("inf"), False, 0
    print(f"== {name} ==")
    for r, l in enumerate(loss, 1):
        sent = cwnd
        lost = 0 if l == 0.0 else max(1, round(sent * l))
        if sent == lost:                    # a full PTO period of silence
            streak += 1; print(f"r{r}  sent={sent:3d} cwnd={cwnd:3d}  PTO: 2 probes, not CC-blocked (S6.2.4/S7.5)"); continue
        if streak >= PTO_PC:                # acks resume after the blackout
            print(f"r{r}  sent={sent:3d} cwnd={MIN_CWND:3d}  PERSISTENT CONGESTION (S7.6.2): "
                  f"{streak} PTO periods lost -> kMinimumWindow, re-enter SS")
            cwnd, recovery, streak = MIN_CWND, False, 0
        elif lost and recovery:
            print(f"r{r}  sent={sent:3d} cwnd={cwnd:3d}  in recovery: no further reduction (S7.3.2)")
        elif lost:
            ssthresh = max(MIN_CWND, int(BETA * sent)); cwnd = max(ssthresh, MIN_CWND); recovery = True
            print(f"r{r}  sent={sent:3d} cwnd={cwnd:3d}  packet-threshold loss: SS exit, ssthresh = {sent} * 0.5")
        elif recovery:
            recovery = False; print(f"r{r}  sent={sent:3d} cwnd={cwnd:3d}  recovery exit: post-reduction packet acked (S7.3.2)")
        elif cwnd < ssthresh or ssthresh == float("inf"):
            cwnd *= 2; print(f"r{r}  sent={sent:3d} cwnd={cwnd:3d}  slow start: x2 per RTT (S7.3.1)")
        else:
            cwnd += 1; print(f"r{r}  sent={sent:3d} cwnd={cwnd:3d}  congestion avoidance: +1 MTU per cwnd (S7.3.3)")
    print()

print("Real output:")
run("trace A: sparse single-packet loss", [0, 0, 0, 0.1, 0, 0, 0, 0])
run("trace B: three-round blackout",      [0, 0, 1, 1, 1, 0, 0, 0])
```

```text
Real output:
== trace A: sparse single-packet loss ==
r1  sent= 10 cwnd= 20  slow start: x2 per RTT (S7.3.1)
r2  sent= 20 cwnd= 40  slow start: x2 per RTT (S7.3.1)
r3  sent= 40 cwnd= 80  slow start: x2 per RTT (S7.3.1)
r4  sent= 80 cwnd= 40  packet-threshold loss: SS exit, ssthresh = 80 * 0.5
r5  sent= 40 cwnd= 40  recovery exit: post-reduction packet acked (S7.3.2)
r6  sent= 40 cwnd= 41  congestion avoidance: +1 MTU per cwnd (S7.3.3)
r7  sent= 41 cwnd= 42  congestion avoidance: +1 MTU per cwnd (S7.3.3)
r8  sent= 42 cwnd= 43  congestion avoidance: +1 MTU per cwnd (S7.3.3)

== trace B: three-round blackout ==
r1  sent= 10 cwnd= 20  slow start: x2 per RTT (S7.3.1)
r2  sent= 20 cwnd= 40  slow start: x2 per RTT (S7.3.1)
r3  sent= 40 cwnd= 40  PTO: 2 probes, not CC-blocked (S6.2.4/S7.5)
r4  sent= 40 cwnd= 40  PTO: 2 probes, not CC-blocked (S6.2.4/S7.5)
r5  sent= 40 cwnd= 40  PTO: 2 probes, not CC-blocked (S6.2.4/S7.5)
r6  sent= 40 cwnd=  2  PERSISTENT CONGESTION (S7.6.2): 3 PTO periods lost -> kMinimumWindow, re-enter SS
r7  sent=  2 cwnd=  4  slow start: x2 per RTT (S7.3.1)
r8  sent=  4 cwnd=  8  slow start: x2 per RTT (S7.3.1)
```

Read trace A for the halving path (SS exit on the first loss even though
ssthresh was still infinite) and trace B for the two rules people get wrong:
PTO fires through the blackout without touching cwnd, and the collapse to 2
packets happens only when the post-blackout ACK passes the duration test.

## Interview questions

**Q1. Why does QUIC need PTO if it has packet- and time-threshold detection?**
A. Both thresholds need a *later* packet to be acknowledged — they are dead when
the tail of the window (or everything) is lost. PTO is the silence fallback:
unlike TCP's RTO it does not itself reduce the window; only the
persistent-congestion duration test does.

**Q3. What limits a QUIC server before the handshake finishes?**
A. Two independent ceilings: the congestion window (initially ~10 datagrams, in
slow start) and the anti-amplification limit — 3x bytes received until address
validation completes (RFC 9000 §8.1). The cap also forbids arming PTO probes
while blocked, applies per path, and re-applies after migration.

**Q4. Is QUIC's default congestion controller CUBIC?**
A. No — RFC 9002's normative reference controller is NewReno (Appendix B's
pseudocode). CUBIC (RFC 9438) is what the major stacks ship as their *default*
(quic-go, quiche, MsQuic), but as an extension checked against the baseline.

## Related pages

The protocol side — streams, UDP framing, 0-RTT — is in [QUIC](../http/quic.md)
and [QUIC internals](../http/quic-internals.md); the wider controller zoo in
[advanced congestion control](congestion-control-advanced.md) and [learning
congestion control](learning-congestion-control.md); the AQM side of the queue
this pacer avoids filling in [fq_codel and pacing](fq-codel-pacing.md); and why
initial-window bursts collide with shallow buffers in [Data-center TCP](datacenter-tcp.md).

## References

1. Iyengar, J. (ed.), Swett, I. (ed.), *QUIC Loss Detection and Congestion Control*, RFC 9002, May 2021 — https://www.rfc-editor.org/rfc/rfc9002.txt
2. Iyengar, J. (ed.), Thomson, M. (ed.), *QUIC: A UDP-Based Multiplexed and Secure Transport*, RFC 9000, May 2021 — https://www.rfc-editor.org/rfc/rfc9000.txt
3. Xu, L., Ha, S., Rhee, I., Goel, V., Eggert, L. (ed.), *CUBIC for Fast and Long-Distance Networks*, RFC 9438, August 2023 (obsoletes RFC 8312, updates RFC 5681) — https://www.rfc-editor.org/rfc/rfc9438.txt
4. Dumazet, J., Cheng, Y., Chu, J., *Increasing TCP's Initial Window*, RFC 6928 — https://www.rfc-editor.org/rfc/rfc6928.txt
5. Cardwell, N. (ed.), Swett, I. (ed.), Beshay, J. (ed.), *BBR Congestion Control* (specifies BBRv3), draft-ietf-ccwg-bbr, Experimental, IETF CCWG — https://github.com/ietf-wg-ccwg/draft-ietf-ccwg-bbr
6. Iyengar, J., Swett, I., *QUIC Acknowledgment Frequency* (Internet-Draft, not yet an RFC), IETF QUIC WG — https://github.com/quicwg/ack-frequency
7. quic-go contributors, congestion control sources (Chromium-derived CUBIC, initial window 32 packets) — https://github.com/quic-go/quic-go/blob/master/internal/congestion/cubic_sender.go
8. Cloudflare quiche, recovery/congestion module (Reno, CUBIC default, BBRv2) — https://github.com/cloudflare/quiche/blob/master/quiche/src/recovery/mod.rs
9. Microsoft MsQuic, QUIC_CONGESTION_CONTROL_ALGORITHM enum (CUBIC default; BBR under preview flag) — https://github.com/microsoft/msquic/blob/main/src/inc/msquic.h
10. quiche API: CongestionControlAlgorithm (Reno, CUBIC, Bbr2Gcongestion) — https://docs.rs/quiche/latest/quiche/enum.CongestionControlAlgorithm.html
