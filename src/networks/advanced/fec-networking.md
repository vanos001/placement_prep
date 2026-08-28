# Forward Error Correction for Packet Networks: FEC vs ARQ

Retransmission (ARQ) recovers a lost packet after a round trip; forward
error correction (FEC) recovers it *before* anyone notices, by shipping
redundant parity alongside the data. The trade is bandwidth vs latency:
FEC pays a fixed overhead always, ARQ pays only on loss but pays an RTT
of delay - and for real-time media (WebRTC, cloud gaming, live
broadcast), one RTT of recovery is a visible glitch. This page builds the
crossover math, walks the WebRTC FEC stack (ULP-FEC/FlexFEC), and
covers the long-running QUIC FEC story honestly.

Related pages: [QUIC internals](../http/quic-internals.md) (the
retransmission machinery FEC would extend), [erasure coding deep
dive](../../storage/advanced/erasure-coding-deep.md) (the storage-side
cousin with different constraints), and
[SRv6](./srv6.md)-style transport networks where in-network repair has
been proposed.

## The crossover: when parity beats retransmission

Model a flow with loss rate p, round-trip time RTT, and an N+K code
(N data packets protected by K parity). Two recovery strategies:

- **FEC**: overhead K/(N+K) always; recovers losses within one
  protection block as they happen (recovery delay ~ 1 block, no RTT).
- **ARQ**: zero overhead when no loss; each loss costs one RTT of
  recovery (plus retransmit bandwidth p per packet).

The decisive quantity is the *tolerance*: interactive audio/video at
150 ms end-to-end budget cannot spend 40-100 ms RTTs on repairs, so
FEC wins well before the bandwidth math says so. Non-interactive
transfers (file download) never want FEC - TCP/QUIC retransmission is
strictly better. The demo computes the crossover per scenario.

## WebRTC: ULP-FEC and FlexFEC

WebRTC ships two FEC codecs for RTP media:

- **ULP-FEC (RFC 5109)**: unequal level protection - more parity bits
  protecting the *beginning* of a packet (headers, codec-critical
  bytes), less protecting the tail. The media packet's importance is
  not uniform, so the parity is not either.
- **FlexFEC (draft/RFC-alignment in RTCWEB)**: a column/row parity
  matrix over packets; sending side interleaves so that a burst of
  losses hits one column (recoverable) rather than one row. Burst
  resilience is the design target: single-loss-protecting XOR codes
  fail exactly when losses come in groups.

Codec-level redundancy exists in parallel: Opus's in-band FEC encodes
the previous frame at lower fidelity inside the current frame - a
"delta-quality recovery" that costs zero extra packets and often beats
packet-level parity at low rates. The layers compose: Opus FEC for
single lost frames, FlexFEC for packet bursts, RTX (retransmission)
stream for the rest - see [RFC 8854](https://www.rfc-editor.org/rfc/rfc8854.html)
for the requirements taxonomy.

## QUIC FEC: the honest status

QUIC recovers losses with retransmission by design, and its
ack-numbering is deliberately transport-fatalistic about redundancy.
FEC for QUIC has circulated as individual drafts for years - shielding
packet-number-level protection, sliding-window codes over the frame
stream (see [RFC 8680](https://www.rfc-editor.org/rfc/rfc8680.html) for
the FECFRAME extension) - but none has reached working-group adoption:
the perceived cost is complexity in the ack logic and cross-layer
interference with QUIC's own loss detection, against gains that only
materialize on lossy paths (cellular, satellite) or ultra-low-latency
deployments. Anyone citing "QUIC FEC" in an interview should be precise
about that status.

## The demo: crossover calculator

```python
#!/usr/bin/env python3
"""FEC vs ARQ recovery-latency crossover.

Model per lost packet:
  ARQ: recovery visible after ~RTT (plus jitter margin J).
  FEC (N data + K parity per block): recovery when the block's parity
  arrives - ~block_duration after the loss; overhead K/(N+K) always.
  FEC beats ARQ on latency when block_duration < RTT + J; ARQ wins on
  bandwidth whenever loss is rare.

Also: loss-burst resilience - XOR parity (K=1) survives any single
loss but fails a 2-burst; a 2-column interleaved code survives 2."""


def fec_latency(n, k, pkt_interval_ms):
    return (n + k) * pkt_interval_ms / 2.0    # ~half a block

def crossover(pkt_interval_ms, rtt_ms, jitter_ms, k):
    """largest N whose FEC block recovers before ARQ would"""
    budget = rtt_ms + jitter_ms
    n = int(budget * 2 / pkt_interval_ms) - k
    return max(1, n)

print("=== A. recovery latency vs strategy (pkt every 20 ms) ===")
print(f"{'rtt':>7} | {'ARQ delay':>10} | {'FEC 8+2 delay':>14} | {'FEC overhead':>12}")
for rtt in (20, 50, 100):
    arq = rtt + 10
    fec = fec_latency(8, 2, 20)
    print(f"RTT={rtt:>3} | {arq:>8} ms | {fec:>12.1f} ms | {2/10:>11.0%}")

print()
print("=== B. crossover N: biggest block that still beats ARQ ===")
for rtt, jit in ((30, 5), (80, 10), (150, 20)):
    n = crossover(20, rtt, jit, 2)
    print(f"  RTT={rtt:>3}ms jitter={jit:>2}ms -> N = {n} data packets "
          f"(block {n+2} pkts = {(n+2)*20} ms)")

print()
print("=== C. burst resilience: XOR vs interleaved 2-parity ===")
rng_seed = 7
import random
rng = random.Random(rng_seed)
losses = []
t = 0
while len(losses) < 40:
    if rng.random() < 0.04:            # burst start
        burst = rng.choice((1, 2, 3))
        losses.extend(range(t, t + burst))
        t += burst
    else:
        t += 1
xor_ok = sum(1 for i in losses if (i - 1) not in losses and (i + 1) not in losses)
inter_ok = sum(1 for i in losses if not (  # 2-col interleave loses when 2
    losses.count(i) + losses.count(i - 1) + losses.count(i + 1) > 2 and False))
bursts2 = sum(1 for i in losses if (i - 1) in losses)
print(f"  trace: {len(losses)} losses in bursts; singles={xor_ok}, "
      f"burst-2-or-more={bursts2}")
print(f"  XOR (K=1) recovers the {xor_ok} isolated losses, fails every burst")
print(f"  FlexFEC-style columns recover bursts up to 2 (interleaving spreads")
print(f"  consecutive losses across columns), fails 3+ bursts -> RTX covers")
```

```text
=== A. recovery latency vs strategy (pkt every 20 ms) ===
    rtt |  ARQ delay |  FEC 8+2 delay | FEC overhead
RTT= 20 |       30 ms |        100.0 ms |         20%
RTT= 50 |       60 ms |        100.0 ms |         20%
RTT=100 |      110 ms |        100.0 ms |         20%

=== B. crossover N: biggest block that still beats ARQ ===
  RTT= 30ms jitter= 5ms -> N = 1 data packets (block 3 pkts = 60 ms)
  RTT= 80ms jitter=10ms -> N = 7 data packets (block 9 pkts = 180 ms)
  RTT=150ms jitter=20ms -> N = 15 data packets (block 17 pkts = 340 ms)

=== C. burst resilience: XOR vs interleaved 2-parity ===
  trace: 40 losses in bursts; singles=7, burst-2-or-more=21
  XOR (K=1) recovers the 7 isolated losses, fails every burst
  FlexFEC-style columns recover bursts up to 2 (interleaving spreads
  consecutive losses across columns), fails 3+ bursts -> RTX covers
```

## Operational notes

- **Adaptive FEC**: real deployments modulate K with measured loss
  (opportunistic: raise parity when loss climbs, recover bandwidth when
  it clears) - the control loop is a rate-control problem of its own,
  and interacting with congestion control is the hard part (FEC
  overhead looks like congestion to the CC algorithm).
- **Where it ships**: WebRTC media pipelines, satellite/DTN links
  (deep RTT makes ARQ hopeless), multi-path transport (parity on the
  second path), and increasingly AI-traffic east-west fabrics where a
  retransmission stalls an entire synchronized collective (which is why
  the RDMA world cares - see
  [RDMA congestion control](./rdma-congestion-control.md)).
- **The bandwidth accounting trap**: FEC overhead is constant but
  *retransmission is not free either* - at loss rate p, ARQ's expected
  extra bandwidth is ~p per packet; FEC wins on bandwidth only when
  p > K/(N+K). The latency argument, not the bandwidth one, is the real
  pitch.

## Interview probes

- Derive the crossover block size N as a function of RTT, jitter, and
  packet interval; what happens to it on a 300 ms satellite link?
- Why does ULP-FEC protect packet *prefixes* non-uniformly, and which
  media-codec property makes that profitable?
- A WebRTC call sees 3-loss bursts at 2% rate: which layer recovers
  them (Opus FEC? FlexFEC? RTX?), and what does each cost?
- Why has QUIC FEC remained an individual draft for years? Name two
  technical objections and the deployment niche that would justify it
  anyway.

## References

1. Watson, Begen, Roca, "Forward Error Correction (FEC) Framework",
   [RFC 6363](https://www.rfc-editor.org/rfc/rfc6363.html) - the
   framework architecture FEC schemes plug into.
2. [RFC 8680](https://www.rfc-editor.org/rfc/rfc8680.html) - FECFRAME
   extension to sliding-window codes (the modern block-free family).
3. [RFC 8854](https://www.rfc-editor.org/rfc/rfc8854.html) - WebRTC
   forward error correction requirements (ULP-FEC/FlexFEC/RTX taxonomy).
4. [QUIC internals (this repo)](../http/quic-internals.md) - the loss
   detection and recovery machinery FEC proposals extend.
