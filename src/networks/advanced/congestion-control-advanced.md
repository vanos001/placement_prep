# Advanced Congestion Control, AQM, and Queuing Theory

## BBR Internals

### The BBR State Machine

See [../tcp/bbr.md](../tcp/bbr.md) for the BBR overview. Here we cover the internal state machine and implementation details (Linux kernel, `net/ipv4/tcp_bbr.c`):

BBR operates in four states:

```
        STARTUP → DRAIN → PROBE_BW (main loop)
                                  ↓↑
                              PROBE_RTT

STARTUP:  Exponentially grow cwnd (2× per RTT) until BtlBw plateaus.
DRAIN:    Drain the queue built during STARTUP (send at BtlBw until inflight = BDP).
PROBE_BW: Pacing cycle: 8/8 gains [1.25, 0.75, 1, 1, 1, 1, 1, 1] to probe bandwidth.
PROBE_RTT: Every 10 seconds, drain to ~4 packets to measure true RTprop.
```

The **PROBE_BW** cycle is the steady state. BBR paces at a rate modulated by the gain cycle: one round of 1.25× pacing rate (to probe for more bandwidth), followed by a round of 0.75× (to drain any queue that built up), then six rounds at 1.0×. This periodic probing allows BBR to adapt to bandwidth changes without relying on loss.

### BBR v2 Improvements

BBR v1's weakness: it is **too aggressive** when sharing a bottleneck with loss-based flows. It fills the buffer, causing loss for CUBIC flows. BBR v2 (2021, `tcp_bbr2.c`) adds:

- **Congestion signal from loss + ECN**: When BBR detects loss or ECN marks, it reduces inflight to the estimated BDP.
- **Response to ECN**: BBR v2 treats ECN like loss — a signal to drain. This makes it more friendly on shared links.
- **Loss-based upper bound**: A new `inflight_lo` (lower bound) derived from loss events, complementing the existing `inflight_hi` (upper bound).

## Copa: Delay-Based Congestion Control

Copa (MIT, 2018) targets the same goal as BBR — operating at the bandwidth-delay product — but uses a simpler, delay-based approach:

```
if (delay <= target_delay):
    increase rate  (additive, +1 packet per RTT)
else:
    decrease rate  (multiplicative, ×0.7)

where target_delay = delta * base_RTT + k * standing_queue_estimate
```

Copa maintains a `delta` parameter that tracks the ratio of measured RTT to the minimum observed RTT. It aims to maintain a small standing queue (parameterized by `k`). The key insight: if delay is at the target (slightly above minimum), you're at the optimal operating point — maximizing throughput with minimal queueing.

## PCC: Machine Learning Congestion Control

PCC (Performance-oriented Congestion Control, MIT, 2015) frames congestion control as an **online learning problem**:

1. **Monitor**: Observe current throughput T and latency L for a short interval.
2. **Decide**: Choose a utility function U(T, L) = α·T - β·L (throughput vs. latency trade-off).
3. **Act**: If U is increasing, continue; if decreasing, adjust the rate.
4. **Learn**: PCC Vivace uses an explicit utility function and performs **gradient ascent**: try a small rate increase, measure utility change, and step in the direction that improves utility.

PCC is theoretically principled but has high implementation complexity (needs kernel modifications, fine-grained measurements). BBR won in practice because it's simpler and works in the kernel without per-packet RTT measurement overhead.

## ECN (Explicit Congestion Notification)

ECN allows routers to signal congestion **without dropping packets**. When a router's queue exceeds a threshold, it marks the ECT (ECN-Capable Transport) bits in the IP header instead of dropping:

```
IP header DSCP/ECN field (2 bits):
  00 = Not ECN-Capable
  01 or 10 = ECT(1) or ECT(0) — sender is ECN-capable
  11 = CE (Congestion Experienced) — router marks congestion
```

On the receiver side, when a CE-marked packet arrives, the receiver sets the ECE flag in the TCP ACK. The sender reduces cwnd by half (same as a loss event in CUBIC) and sets CWR flag. This avoids packet loss while achieving the same congestion response.

### DCTCP (Datacenter TCP)

DCTCP (Alizadeh et al., 2010) is ECN-based congestion control designed for datacenters, where the goal is **low queue occupancy** (to keep latency low) rather than high utilization:

```
On receiving CE marks (fraction α of marked packets):
  cwnd = cwnd × (1 - α/2)

On receiving ACKs without CE:
  cwnd += 1/cwnd  (standard TCP increase)
```

DCTCP responds **proportionally** to the fraction of marked packets. If 10% are marked, cwnd reduces by 5% (not 50% like standard ECN response). This maintains a small queue (~5–10 packets) at the switch, providing both high throughput and low latency.

## Incast and Outcast

### Incast (Many-to-One)

Incast occurs when many servers simultaneously send data to a single receiver (e.g., a partitioned query in a distributed database or MapReduce shuffle). The problem: a burst of packets overflows the switch buffer near the receiver, causing massive packet loss and TCP timeouts (100ms–1s), destroying throughput.

```
                Switch buffer (small!)
Server 0 ────┐         ┌────→ Receiver
Server 1 ────┤ [====]  ├────→
Server 2 ────┤ [====]  ├────→
   ...       └─────────┘

All senders respond simultaneously → buffer overflow → incast
```

Mitigations: (1) Reduce switch buffer or use small per-flow queues (limits queueing delay). (2) Use ECN instead of tail-drop (DCTCP). (3) Use a finer-grained transport like QUIC with 0-RTT loss recovery. (4) Application-level: stagger responses, limit concurrency.

### Outcast (Many-to-Subset)

Outcast occurs when many flows share a bottleneck but only a subset of them have their next hop congested. The non-congested flows fill the shared bottleneck queue, starving the congested subset. Detected in multicast and multi-root tree topologies.

## Bufferbloat

Bufferbloat (Gettys & Nichols, 2011) describes the pathology of excessively large network buffers. Modern switches and routers ship with megabytes of buffer to absorb bursts. But when many TCP flows share such a link, they all grow cwnd until packets are dropped. The buffer fills to capacity, adding **hundreds of milliseconds of latency** without improving throughput.

Symptoms: Ping times jump from 1ms to 500ms under load. Video calls lag. Gaming becomes impossible. The fix: **Active Queue Management (AQM)**.

## AQM: CoDel and PIE

### CoDel (Controlled Delay)

CoDel (Nichols & Jacobson, 2012) is an AQM algorithm that targets a specific **sojourn time** (time a packet spends in the queue) rather than queue length:

```
Parameters:
  TARGET = 5ms       (target sojourn time)
  INTERVAL = 100ms   (minimum time between drops)

Algorithm:
  for each packet dequeued:
    sojourn = now - packet.arrival_time
    if sojourn > TARGET:
      if first_above_time == 0:
        first_above_time = now
      elif now - first_above_time >= INTERVAL:
        drop packet
        next_drop_time = now + INTERVAL/sqrt(dropping_count)
        dropping_count++
    else:
      first_above_time = 0
      dropping_count = 0
```

CoDel is **parameterless in practice** — the TARGET and INTERVAL work across link rates and RTTs. It drops packets at an exponentially increasing rate (sqrt spacing) to force TCP to back off. When the queue drains below TARGET, it stops dropping. The key insight: measuring delay (sojourn time) is self-scaling — a 5ms target means the same thing regardless of link speed.

### PIE (Proportional Integral controller Enhanced)

PIE (Pan et al., 2013) uses a classic PI control theory approach:

```
  error = current_delay - TARGET
  p = α * error + β * (error - prev_error)  // P + I terms
  drop_probability = clamp(p, 0, max_p)
```

PIE adjusts drop probability based on how far the queueing delay is from the target and how fast it's changing (the integral term handles steady-state error). PIE is used in DOCSIS cable modems and is the IETF-recommended AQM for home routers.

## Fair Queuing

### FIFO and Its Problems

A FIFO (tail-drop) queue treats all flows equally — but equally is not **fairly**. A bursty flow can fill the buffer, causing drops for other flows. Fair queuing ensures each flow gets its **fair share** of bandwidth.

### DRR (Deficit Round Robin)

DRR is a practical fair queuing algorithm that avoids per-packet sorting:

```
Each flow i has a deficit counter DC[i] and quantum Q.

Round:
  for each active flow i:
    DC[i] += Q
    while DC[i] >= packet_size(next_packet_in_flow_i):
      dequeue and send packet
      DC[i] -= packet_size
```

A flow with larger packets accumulates more deficit between rounds, so it can send when enough deficit accumulates. DRR is O(1) per packet (after sorting the active list) and is used in Linux's `fq_codel` qdisc.

### WFQ (Weighted Fair Queuing)

WFQ assigns each flow a **weight** w_i, guaranteeing it bandwidth proportional to w_i / Σw_j. Implemented by simulating a GPS (Generalized Processor Sharing) system: each packet is assigned a virtual finish time based on its size and the flow's weight, and packets are served in order of increasing virtual finish time.

WFQ is theoretically optimal but impractical for high-speed links (requires per-packet sorting). In practice, DRR with weighted quantums approximates WFQ.

### fq_codel

Linux's default AQM qdisc: **DRR** (for fairness) + **CoDel** (for AQM). Each flow gets its own CoDel-managed queue. This provides both per-flow fairness and bounded delay. It is the default on many Linux distributions and is recommended for broadband routers.

## Network Calculus

Network calculus provides a mathematical framework for computing **worst-case bounds** on latency and backlog in networks, using min-plus algebra.

### Core Concepts

- **Arrival curve α(t)**: Upper bound on cumulative traffic arriving in any interval of length t. A leaky bucket constrained flow: α(t) = σ + ρ·t (burst σ, rate ρ).
- **Service curve β(t)**: Lower bound on service provided. A rate-latency server: β(t) = R · max(0, t - T) (rate R after latency T).
- **Delay bound**: d ≤ sup{t ≥ 0 | α(t) > β(t)}. The horizontal distance between α and β curves.
- **Backlog bound**: b ≤ sup{t ≥ 0 | α(t) - β(t)}. The vertical distance.

```
Cumulative data
  ^
  |        α(t) = σ + ρt
  |       /
  |      /  ← delay bound d
  |     / _____β(t) = R·(t-T)
  |    /_/    
  |   /  ↑ backlog b
  |  /  _|
  | / _/ 
  |/_/
  +----------------------> time
     T
```

> **Interview Angle**: "When would you use network calculus?" — For hard real-time systems (industrial control, automotive, avionics) where you need **guaranteed** latency bounds, not just average performance. Network calculus gives deterministic worst-case bounds. It's also used in TSN (Time-Sensitive Networking) for computing schedule feasibility.

### Comparison: Congestion Control Families

| Family | Signal | Strength | Weakness | Example |
--------|--------|----------|----------|---------|
 **Loss-based** | Packet loss | Simple, works everywhere | High buffer occupancy | CUBIC, Reno |
 **Delay-based** | RTT increase | Low latency, near optimal | Fails with reverse-path congestion | Vegas, Copa |
 **Hybrid** | Loss + delay | Robust | More complex | BBR v2 |
 **ECN-based** | ECN marks | No loss needed | Requires ECN support in path | DCTCP, ECT(1) |
 **Learning-based** | Utility function | Adaptable | Complex, slow convergence | PCC Vivace |
 **Bounded** | Network calculus | Deterministic | Conservative (worst case) | TSN, industrial |