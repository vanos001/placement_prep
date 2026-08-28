# Data-Center TCP: Incast Collapse and the Congestion Controls Built Against It

Loss-based TCP was tuned for WANs: long RTTs, deep queues, rare synchronization. A
data-center rack inverts every assumption: RTTs of 50-100 us, shallow merchant-silicon
switch buffers, and applications (storage shards, MapReduce/Spark shuffle, parameter
servers, HDFS reads) that release hundreds of requests **synchronized by an application
barrier**. The result is incast: N senders, one receiver, one overloaded ToR port, and
completion times dominated not by bandwidth but by TCP's retransmission timer.

```text
        incast: many-to-one synchronized read (N=48 senders, one target)
 s1 ---> \
 s2 --->  \                     +--------------+
 s3 --->  +-------------------> | ToR switch   | --> single 10G egress port --> target
 ...      /                     | buf ~12MB    |     queue: min(arrivals, buffer)
 s48 ---> /                     +--------------+     overflow => drops for everyone else
   all N start within microseconds of each other (barrier release)
```

## Why the minimum RTO, not the buffer, is the killer

At 100 us RTT, a query that reads one 12 KB block from each of 48 shards should finish in
about a millisecond. What actually happens:

1. Every sender starts in slow start with IW10 (10 segments) -> 48 x 10 x 1500 B = 720 KB
   arrives at the ToR within ~1 RTT, on a port that drains ~8 packets per RTT at 1 Gb/s
   (10 Gb/s: ~83 packets/RTT). The instantaneous burst is 10-70x the drain rate.
2. The switch egress queue overflows. Because the burst is *simultaneous*, drops hit most
   flows at once; a flow can lose several segments, and with tail drop the survivors keep
   blasting while the victimized ones go silent.
3. Each victim waits for its RTO. RFC 6298 recommends a 1 s minimum; Linux enforces a
   200 ms floor (`TCP_RTO_MIN`, overridable per-route with `ip route ... rto_min`).
   200 ms / 100 us RTT = **2000 round trips wasted** per timeout.
4. After the RTO the sender retransmits one segment, refills slowly, and -- with 47 peers
   doing the same -- may lose again, chaining 200 ms multiples.

This produces the signature completion-time distribution: mass at 200, 400, 600 ms...
on a network whose RTT is 100 us. Measured incast stalls of 100+ ms in storage clusters
were first quantified by Phanishayee et al. (SIGCOMM'08); the numbers above explain them.

## Switch buffer sizing math

Merchant ToR silicon exposes a shared packet buffer (commonly 12-32 MB) divided
dynamically among 32-128 ports. Two facts follow:

- Per-port effective buffer is small: 12 MB / 48 egress ports ~ 250 KB ~ 166 packets,
  versus a 10 Gb/s, 100 us RTT bandwidth-delay product of ~833 packets. Data-center
  switches are *shallow-buffered relative to BDP* by an order of magnitude.
- No plausible buffer absorbs incast: absorbing one synchronized round needs
  B >= sum of in-flight = N x cwnd x MTU. For N=48, cwnd=10: 720 KB *just for round one*,
  and the queue builds again every RTT as ACKs release more data. Buffering instead of
  dropping merely converts loss into hundreds of microseconds of queueing latency for
  every other tenant sharing the switch (the bufferbloat trade).

So the fix has to change sender behavior within a round trip -- which is what all four
designs below do, differing in the congestion signal they use.

## DCTCP: ECN as a multi-bit signal (SIGCOMM'10)

DCTCP (Alizadeh et al.) keeps the switch nearly empty and never (in steady state) drops:

- Switch: mark the IP ECN field with CE when the instantaneous queue exceeds a small
  threshold K (reference value ~20 packets at 10 Gb/s). Marking is per-packet, so an ACK
  stream carries the *fraction* of packets that experienced queue -- multi-bit feedback
  from a 1-bit field.
- Sender: maintain EWMA of the marked fraction, alpha = (1-g)*alpha + g*F with g = 1/16.
  Once per RTT (aggregated over ACKs), scale the window: cwnd *= (1 - alpha/2) in the
  decrease direction, cwnd += (1 - alpha) in the increase direction.
- Consequences: 10% marks -> 5% window cut (not CUBIC's 30% cut), so the queue parks just
  above K, about K/(1-alpha) packets ~ tens of packets ~ tens of microseconds of delay.
  Flows sharing the bottleneck converge to fairness roughly once per RTT.

DCTCP requires ECN enabled end-to-end and -- critically for incast -- it does not remove
the RTO problem by itself: the DCTCP paper's incast experiments also shrink the minimum
RTO. Production data centers combine `dctcp` + low `rto_min` + ECN marking on every switch.

## DCQCN: the RDMA/RoCEv2 variant, and the PFC trap

RoCEv2 (RDMA over Converged Ethernet) carries kernel-bypass UDP/IP traffic that cannot
safely drop (a drop becomes a transport-level Go-Back-N event on the NIC). DCQCN
(Zhu et al., SIGCOMM'15) is the de-facto congestion control there:

- Switch: ECN-mark as in DCTCP. Receiver relays CE via the Congestion Notification Tag.
- NIC (reaction point): on CE, reduce rate multiplicatively using a DCTCP-style alpha,
  then rebuild rate in timer-based increase phases.
- Underneath sits IEEE 802.1Qbb Priority Flow Control: per-priority PAUSE frames stop
  the upstream port when a queue crosses a watermark. PFC prevents drops but creates
  head-of-line blocking that propagates congestion *backwards* hop by hop; a misconfigured
  DCQCN/PFC pair can cascade into a "PFC storm" where an entire pod pauses. Operational
  rule: DCQCN must react (mark/reduce) *before* PFC triggers, or the network pauses.

## HPCC and IRN: measure the link, not the queue

HPCC (Li et al., NSDI'19) exploits programmable switches: each packet carries In-Band
Network Telemetry (INT) metadata, so the sender sees, per RTT, the *actual* per-link
utilization, queuing, and transmit delay along its path. The sender inflates its window
toward eta x max-link-load x RTT -- direct measurement of available bandwidth -- instead
of inferring congestion from marks. In the paper's testbed and ns-3 evaluations HPCC
sustained near-full throughput at tiny buffers where DCQCN collapsed, at the cost of INT
support in hardware (Mellanox/NVIDIA NICs and switching ASICs exposed it; commodity
non-programmable fleets cannot run it). Related result: IRN (Mittal et al., NSDI'18)
showed that giving RDMA NICs ordinary TCP-style selective retransmission (PSN-based SACK
state) makes drops cheap enough that shallow-buffer losses stop being catastrophic.

## Swift: delay as the signal for deep and shallow buffers alike

Google's Swift (SIGCOMM'20) uses RTT itself as the congestion signal, with two decoupled
control loops: one on fabric (switch) RTT targeting a rate-vs-delay envelope, one on host
NIC RTT targeting nic-based queues. Because RTT is graded (not a threshold like ECN or an
event like loss), Swift scales across shallow-buffer incast-prone fabrics and deep-buffered
crossings alike, and reacts within a fraction of an RTT to a burst -- Google reports
broad deployment across its fleet, including storage. The cost is careful RTT filtering:
you must separate queueing delay from ACK processing noise and make the target envelope
admission-rate aware (a delay target admits fewer flows as the fleet grows).

## CUBIC vs DCTCP tail behavior

| Property | CUBIC (loss-based) | DCTCP (ECN fraction) |
|---|---|---|
| Congestion signal | packet drop | fraction of CE-marked ACKs |
| Steady-state switch queue | fills until drop (deep) | ~K + small oscillation |
| Window response | cut 0.7x per loss event | scale by (1 - alpha/2) |
| 99.9p queueing latency | unbounded under load | tens of us |
| Incast behavior | 200 ms+ RTO chains | rare drops; needs low min RTO too |
| Deployment requirements | none | ECN in every switch + host |

The interview-relevant summary: CUBIC treats a drop as the *first* congestion symptom;
in a shallow-buffer fabric the first drop already means latency died, so DCTCP/Swift/HPCC
move the signal *earlier* (marks, delay, telemetry) and *finer* (per-packet fraction,
microsecond RTT, per-link bytes). Every one of them is trying to avoid the RTO floor,
because 200 ms is 2000 RTTs of pure waste.

## Toy simulation: the 200 ms quantization, with and without fine-grained ECN

Round-based model: 64 synchronized senders, 100 us RTT, switch drains 8 pkts/RTT with a
24-packet egress buffer, IW10, 8-packet flows. Left column: tail drop + Linux-default
200 ms min RTO + slow-start restart. Right column: ECN marking of buffered packets +
DCTCP-style alpha reaction + tuned 1 ms min RTO.

```python
"""Toy round-based incast model: loss-based TCP (default 200 ms min RTO)
vs ECN/DCTCP-style response (tuned 1 ms min RTO). Times in microseconds."""
import random

RTT = 100.0                 # us; one round in a rack
N = 64                      # synchronized senders (barrier release)
FLOW = 8                    # pkts per sender (12 KB block)
CAP = 8                     # pkts drained per RTT at 1 Gbps / 1500 B
BUF = 24                    # switch egress buffer (pkts) beyond link drain
TRIALS = 100
SEED = 11

def run(ecn, rng):
    cwnd = [10.0] * N       # IW10 initial window
    left = [FLOW] * N
    alpha = [0.0] * N
    rto = [0.0] * N
    rto_len = 1000.0 if ecn else 200000.0   # tuned 1 ms vs Linux 200 ms
    done = [None] * N
    t = 0.0
    for _ in range(50000):                  # guard: 5 s simulated time
        t += RTT
        arrivals = []
        for i in range(N):
            if done[i] is not None:
                continue
            if rto[i] > 0.0:                # frozen until min-RTO fires
                rto[i] -= RTT
                continue
            k = min(max(1, int(cwnd[i])), left[i])   # floor: 1 pkt/RTT
            arrivals += [i] * k
        if not arrivals:
            continue
        rng.shuffle(arrivals)
        dropped = set()
        marked = set()
        served = arrivals[:CAP]
        queued = arrivals[CAP:CAP + BUF]
        beyond = arrivals[CAP + BUF:]
        dropped |= set(beyond)              # tail drop
        if ecn:
            marked |= set(queued)           # ECN mark everything buffered
        for i in served + queued:
            left[i] -= 1
            if left[i] == 0 and done[i] is None:
                done[i] = t
        for i in dropped:
            rto[i] = rto_len                # segment stays queued for retransmit
            cwnd[i] = 1.0                   # retransmit one pkt after RTO
        if ecn:
            for i in set(arrivals) - dropped:
                f = 1.0 if i in marked else 0.0
                alpha[i] = (1 - 1/16) * alpha[i] + (1/16) * f
                if i in marked:
                    cwnd[i] = max(0.5, cwnd[i] * (1 - alpha[i] / 2))
                else:
                    cwnd[i] = cwnd[i] + (1 - alpha[i])   # scaled AI
        else:
            for i in set(arrivals) - dropped:
                cwnd[i] = min(2 * cwnd[i], left[i])      # slow start
    assert all(d is not None for d in done)
    return done

rng = random.Random(SEED)
for ecn, label in ((False, "tail-drop + 200ms minRTO"), (True, "ECN/DCTCP + 1ms minRTO")):
    samples = sorted(x for k in range(TRIALS) for x in run(ecn, rng))
    n = len(samples)
    p = lambda q: samples[min(n - 1, int(q * n))] / 1000.0   # ms
    print("%-26s p50=%6.2fms  p95=%6.2fms  p99=%6.2fms  max=%6.2fms"
          % (label, p(0.50), p(0.95), p(0.99), samples[-1] / 1000.0))
```

Real output (Python 3.12, ~25 s wall time -- the RTO chain is slow by design):

```text
tail-drop + 200ms minRTO   p50=800.90ms  p95=1201.10ms  p99=1201.20ms  max=1201.20ms
ECN/DCTCP + 1ms minRTO     p50=  2.80ms  p95=  4.00ms  p99=  4.10ms  max=  4.10ms
```

Read the left row carefully: completions land at 800.9 and 1201.1 ms -- multiples of the
200 ms timer offset by a few RTTs. With 64 flows retransmitting one segment at a time
against a 32-packet switch budget, each flow loses repeatedly and serially pays RTOs.
That staircase, not link capacity, is the incast completion time. The right row shows what
every production fix converges on: keep the burst under the buffer within a couple of RTTs
(fine-grained ECN reaction), and make the residual loss cost 1 ms instead of 200 ms.

## Failure modes worth knowing

- ECN misconfiguration: DCTCP against a switch with ECN off degenerates to loss-based
  behavior; K set too high re-creates bufferbloat (queue ~ K/(1-alpha) always).
- PFC watchdog: many fleets monitor PFC pause-frame rates and auto-disable PFC on a port
  pair when a storm is detected, accepting drops over head-of-line deadlock.
- HPCC without INT-capable hardware along the whole path is a no-op; deployment reality
  is that INT stays confined to RDMA islands.
- Timer resolution: tuning min RTO below ~1 ms requires HZ-free timers (kernel TCP uses
  microsecond-ish granularity via high-res timers; older kernels quantize at jiffies).

## References

- [DCTCP: Data Center TCP, Alizadeh et al., SIGCOMM 2010](https://doi.org/10.1145/1851182.1851192)
- [DCQCN: Congestion Control for Large-Scale RDMA Deployments, Zhu et al., SIGCOMM 2015](https://doi.org/10.1145/2829988.2787484)
- [HPCC: High Precision Congestion Control, Li et al., NSDI 2019](https://doi.org/10.1145/3341302.3342085)
- [Swift: Delay is Simple and Effective for Congestion Control in the Data Center, SIGCOMM 2020](https://doi.org/10.1145/3387514.3406591)
- [Linux ip-route(8): per-route rto_min and other TCP metrics](https://man7.org/linux/man-pages/man8/ip-route.8.html)
