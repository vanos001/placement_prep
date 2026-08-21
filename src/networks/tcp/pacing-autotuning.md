# TCP Pacing and Autotuning

TCP pacing and TCP autotuning are two related but independent Linux kernel features that improve TCP throughput in high-bandwidth-delay-product (BDP) networks. Pacing spreads packet transmissions evenly over time, avoiding bursts that cause switch buffer drops. Autotuning dynamically adjusts the receive socket buffer size based on the connection's RTT and the application's read rate, allowing the window to grow with the BDP without manual tuning. This page covers the algorithms, the kernel sysctls, and when each is beneficial.

## The Problem: Bursts and Stalls

A TCP sender transmits in response to ACKs. If ACKs arrive in a burst (e.g., after a period of congestion cleared up), the sender responds with a burst of data. This causes:

1. **Switch buffer overflow**: a 100 µs burst of 100 packets (10 Gbps × 100 µs) overflows a 4 MB switch buffer if multiple flows burst simultaneously.
2. **Congestion collapse**: bursts cause drops; drops cause retransmits; retransmits cause more bursts.

The classic fix is **TCP pacing**: instead of sending N packets as soon as ACKs arrive, spread the N packets evenly over the next RTT. The average throughput is the same; the burstiness is gone.

## Linux's `fq` qdisc: Pacing in Practice

Linux's `fq` (Fair Queue) qdisc is the production pacing implementation. When enabled on a network interface, `fq`:

- Maintains a per-flow queue (identified by 5-tuple hash).
- Paces each flow's transmissions based on a per-flow "completion time" the TCP stack sets.
- Drops packets only when a flow's queue exceeds its budget (preventing one flow from starving others).

```bash
# Enable fq on eth0
tc qdisc add dev eth0 root fq

# Or system-wide via sysctl
sysctl -w net.core.default_qdisc=fq
```

The TCP stack (since kernel 3.18+ with `TCP_CONG_CUBIC`) sets a per-skb " skb->tstamp" indicating when the skb should be sent. The `fq` qdisc honors this timestamp, pacing the flow.

For BBR congestion control (kernel 4.9+), pacing is mandatory — BBR sets a precise pacing rate based on its bandwidth estimate, and `fq` enforces it. Without `fq`, BBR's pacing is bypassed by the default pfifo qdisc, and BBR's throughput collapses.

## TCP Autotuning: Dynamic Buffer Sizing

Linux's autotuning adjusts the receive socket buffer size (`SO_RCVBUF`) dynamically based on the connection's RTT and the application's read rate. The goal: allow the receive window to grow large enough to fill the BDP without manual configuration.

Without autotuning:
- A 100 ms RTT link at 1 Gbps needs a 12.5 MB window.
- The default `SO_RCVBUF` is 64 KB — the receive window is capped at 64 KB, throughput is capped at 5 Mbps regardless of link capacity.
- Administrators had to manually set `SO_RCVBUF` to 16 MB or so on every long-fat-pipe server.

With autotuning:
- The kernel observes the BDP (RTT × bandwidth).
- It grows `sk_rcvbuf` up to a configurable max (`net.ipv4.tcp_rmem[2]`, default ~6 MB).
- The receive window in ACK packets grows accordingly.

```bash
# View the receive buffer min/default/max (in bytes)
sysctl net.ipv4.tcp_rmem
# default: 4096 87380 6291456 (4 KB / 87 KB / 6 MB)

# View the send buffer min/default/max
sysctl net.ipv4.tcp_wmem
# default: 4096 16384 4194304 (4 KB / 16 KB / 4 MB)

# Enable autotuning (default: on)
sysctl net.ipv4.tcp_moderate_rcvbuf
# default: 1 (on)
```

## How Autotuning Works Internally

When the application reads data from the socket, the receive buffer frees up. Without autotuning, the receive window is set to `min(free_buffer, sk_rcvbuf)`.

With autotuning, the kernel tracks:
- `rcvq_space`: the recent max of (bytes in receive buffer + bytes just read by app).
- `rcv_rtt`: the smoothed RTT.
- `rcv_rate`: estimated bytes-per-RTT that the receiver can drain.

Every ~RTT, the kernel recomputes `sk_rcvbuf`:

```c
target_buf = max(rcvq_space, BDP_estimate);
sk_rcvbuf = clamp(target_buf, tcp_rmem[0], tcp_rmem[2]);
```

The buffer grows up to the max if the application drains fast enough (high read rate). It shrinks if the application stalls (to avoid wasting memory).

## TCP Pacing Mechanics in the Stack

The TCP stack (since 4.x with `tcp_pacing_*` sysctls, or implicitly via fq) computes a per-skb "send time":

```c
// Pseudocode for pacing the next packet
skb->skb_mstamp = now + (1 / pacing_rate);
```

The pacing rate is computed by the congestion control algorithm:
- CUBIC: pacing rate = `cwnd / RTT` (the conservative estimate).
- BBR: pacing rate = `bandwidth_estimate × 1.25` (slightly above BDP-achieving rate, with 25% headroom for growth).
- DCTCP: pacing rate = `cwnd / RTT` (data-center TCP, similar to CUBIC but with finer ECN-based signals).

The `fq` qdisc enforces this pacing. Without `fq`, the kernel's `sch_direct_xmit` or `qdisc_noqueue` sends packets as soon as they're ready, ignoring the pacing timestamp.

## Sysctls and Defaults

```bash
# Default qdisc (production recommendation: fq or fq_codel)
sysctl net.core.default_qdisc
# default: fq_codel (good for most workloads)

# Receive buffer tuning (production: raise max for high-BDP links)
sysctl net.ipv4.tcp_rmem
# default: 4096 87380 6291456
# production (10 Gbps × 100 ms RTT = 125 MB BDP):
# 4096 87380 268435456  (raise max to 256 MB)

# Send buffer tuning
sysctl net.ipv4.tcp_wmem
# default: 4096 16384 4194304
# production:
# 4096 16384 268435456

# Enable autotuning
sysctl net.ipv4.tcp_moderate_rcvbuf
# default: 1 (on)

# TCP pacing (since 4.x)
sysctl net.ipv4.tcp_pacing_ss_ratio
# default: 200 (200% for slow-start pacing)
sysctl net.ipv4.tcp_pacing_ca_ratio
# default: 120 (120% for congestion-avoidance pacing)
```

## When Pacing Helps

Pacing helps when:
- The bottleneck link has small buffers (e.g., a 100 Mbps WAN link with 1 MB buffer).
- Multiple flows share the same bottleneck (fairness improves with pacing).
- The sender's congestion control benefits from smooth transmission (BBR, DCTCP).

Pacing doesn't help (and may hurt) when:
- The link is underutilized and the bottleneck has plenty of buffer (pacing adds latency without throughput benefit).
- The sender is single-flow (no fairness issue to mitigate).
- The application is latency-bound (pacing adds 1-2 ms of per-packet delay).

## When Autotuning Helps

Autotuning helps when:
- The connection's BDP is large (>1 MB) and varies (so manual tuning is impractical).
- The application's read rate varies (autotuning adapts to the application).
- Multiple connections with different RTTs share the same server (autotuning per-connection is the only sane approach).

Autotuning doesn't help when:
- The BDP is small (<1 MB) — the default buffer is enough.
- The application needs deterministic latency (autotuning's growth/shrink can cause jitter).
- Memory is constrained (autotuning may over-allocate).

## Production Tuning

For a server with mixed workloads (some local LAN, some high-latency WAN):
- Keep `tcp_moderate_rcvbuf=1`.
- Set `tcp_rmem` to a wide range: `4096 87380 134217728` (max 128 MB).
- Set `tcp_wmem` to: `4096 16384 134217728`.
- Use `fq_codel` as the default qdisc (better than plain fq for queue management).

For a BBR-enabled server:
- Use `fq` as the qdisc (BBR's pacing needs it).
- Set `tcp_rmem` max to at least 2× the BDP (for headroom).
- Disable `tcp_slow_start_after_idle` (default 0 on modern kernels; check).

## Common Pitfalls

1. **Using BBR without `fq` qdisc.** BBR's pacing rate is set on each skb, but without `fq` to enforce it, the kernel sends packets as soon as they're ready. BBR's throughput collapses to "send at line rate" — the opposite of what BBR is designed to do.

2. **Setting `SO_RCVBUF` and disabling autotuning.** If the application calls `setsockopt(SO_RCVBUF, ...)`, autotuning is disabled for that socket (the buffer is fixed at the set value). Most applications should not call `SO_RCVBUF` at all; let the kernel tune it.

3. **Setting `tcp_rmem[2]` too high on a memory-constrained server.** A 100 MB max × 1000 connections = 100 GB of potential buffer memory. Cap the max based on available RAM.

4. **Forgetting that `fq` requires a recent kernel.** Older kernels (3.x) had a buggy `fq` implementation that interacted poorly with old congestion controls. Use `fq_codel` (a more recent, more battle-tested qdisc) if in doubt.

5. **Mixing `fq` and `pfifo` on different interfaces.** The default qdisc is per-interface; you can have `fq` on `eth0` and `pfifo` on `lo`. This is fine but inconsistent. Pick one for sanity.

## References

- [Linux TCP pacing documentation](https://www.kernel.org/doc/html/latest/networking/tcp_fairness.html)
- [LWN: fq qdisc and pacing (2014)](https://lwn.net/Articles/617986/)
- [TCP autotuning in the Linux kernel](https://www.kernel.org/doc/html/latest/networking/tcp.html#tcp-tuning)
- [BBR: Congestion-Based Congestion Control](https://research.google/pubs/pub45387/) (Google, ACM Queue 2016)
- [Soheil Hassas Yeganeh et al., "fq_codel"](https://www.ietf.org/proceedings/84/slides/slides-94-tsvarea-0.pdf)
- [Production TCP tuning for high-BDP networks](https://www.psc.edu/research/networking/tuning-tcp)
- [Linux networking sysctls](https://www.kernel.org/doc/Documentation/networking/ip-sysctl.txt)
