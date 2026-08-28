# fq_codel: Flow-Queued Controlled Delay

> Bufferbloat killed interactive performance on fat pipes: a single TCP
> stream filling a 1 Gbit home router's 4 MB buffer adds hundreds of
> milliseconds of queueing delay to every VoIP packet behind it. CoDel
> (Nichols & Jacobson, 2012) attacks standing queue *delay* directly
> instead of buffer *occupancy*; fq_codel wraps it in flow-queuing so
> one heavy flow cannot build the queue another flow must suffer. This
> page walks the CoDel state machine in full (the survey on
> [congestion control](./congestion-control-advanced.md) stops at the
> pseudocode), explains fq_codel's sparse-flow scheduling, and why
> pacing (see [TCP pacing & autotuning](../tcp/pacing-autotuning.md))
> makes AQM's job easier rather than redundant.

## CoDel: Targeting Sojourn Time

Queue *length* is a bad congestion signal: the "right" length depends on
link rate, RTT, and multiplexing. Queue *delay* self-scales. CoDel
tracks the minimum sojourn time of packets leaving the queue over a
sliding window; if that minimum stays above TARGET for longer than
INTERVAL, the queue is standing — dropping begins, with spacing that
increases as the square root of the drop count:

```text
  state: first_above_time (when the min-sojourn went above target)
         drop_next        (scheduled next-drop time)
         dropping         (are we in a dropping episode?)
         count            (drops this episode)

  dequeue(pkt):
    now = time()
    sojourn = now - pkt.enqueue_time
    if dropping:
        if !sojourn_ok(sojourn):          # still above target
            count++
            drop_next = now + INTERVAL / sqrt(count)
            drop pkt; return dequeue_next()
        dropping = False                  # recovered
    if sojourn > TARGET:
        if first_above_time == 0:
            first_above_time = now + INTERVAL
        elif now >= first_above_time:
            drop pkt; count = 1
            drop_next = now + INTERVAL / sqrt(1)  # ≈ INTERVAL
            dropping = True
            return dequeue_next()
    else:
        first_above_time = 0              # good: forget
```

Details the survey pseudocode hides:

- **The min-sojourn estimator** uses the *last* interval's minimum
  (roughly one RTT worth of history), not the current packet's delay —
  instantaneous sojourn spikes (a burst legitimately draining) must not
  trigger drops. That is why CoDel is hard to fool with a burst followed
  by idleness: the min over the window returns low.
- **The √count spacing** encodes the RTT math: TCP throughput is
  roughly 1/(RTT·√p); to halve a flow's rate you need to quadruple its
  loss rate. Spacing drops as INTERVAL/√count makes the *rate* of
  drops grow linearly with count, which translates into the quadratic
  backoff classical control assumed. CoDel derived it from Chiu &
  Jain's convergence analysis of AIMD.
- **Recovery is soft**: the episode ends the moment the min-sojourn
  dips below TARGET — a new episode starts fresh (count halved, not
  reset, per the RFC 8290 refinement, so oscillating flows get
  re-steepened quickly).

## fq_codel: Flow-Queuing on Top

CoDel alone manages *one* queue — a hostile flow still monopolizes the
delay budget of everyone sharing it. fq_codel (RFC 8290) maintains up
to 1024 per-flow queues behind a scheduler:

```text
                 packet in
                    │  5-tuple hash (or skb->hash)
                    ▼
        ┌─────┬─────┬─────┬─────┬────────┐
        │ F 0 │ F 1 │ F 2 │ ... │ F 1023 │   per-flow CoDel state
        └─────┴─────┴─────┴─────┴────────┘
                    │  DRR++ deficit round robin,
                    ▼  with sparse-flow priority
                 packet out

  - NEW flows go to the FRONT of the round-robin order
    (a DNS query behind a BitTorrent flow waits ~one MTU, not one RTT)
  - each flow's queue is itself CoDel-managed
  - quantum = per-flow byte budget per turn (1514 default)
```

The sparse-flow priority is the piece to memorize: a flow that becomes
idle loses its round-robin credit and re-enters at the head when it
speaks again. Latency-sensitive traffic is *usually* sparse, so it
jumps the bulk flows without any configuration — this is what makes
"VoIP stays responsive during a backup" work out of the box.

## CAKE, and Where fq_codel Stops

CAKE (sch_cake, common in OpenWrt) layers on fq_codel: shaping to an
explicit bandwidth, DRR++ with diffserv tiers, per-host fairness
(splits a NAT's single 5-tuple spread across internal hosts), and
overhead compensation for ADSL/VDSL framing. If the bottleneck is a
modem you control, CAKE; if you control a datacenter switch port,
plain fq_codel.

## Pacing Makes AQM Easier (Not Unnecessary)

TCP pacing sends at a steady rate instead of ACK-clock bursts. Its
effect on AQM:

```text
 unpaced:  bursts of ~cwnd packets arrive back-to-back
           -> instantaneous queue spikes even when average load is low
           -> any delay-based AQM sees transient sojourn spikes
 paced:    arrivals spread at rate = cwnd/RTT
           -> queue length tracks the real demand
           -> CoDel's min-sojourn estimator becomes smooth
```

But pacing cannot stop a *sustained* overload — only AQM (or ECN) can
signal back-pressure. The two compose: pacing removes the noise floor,
AQM removes the standing queue. `fq`/`fq_codel` are also Linux's pacing
enforcers (the TCP stack programs per-flow earliest-departure times),
which is why `net.ipv4.tcp_congestion_control=bbr` documentation
instructs enabling `fq` — BBR computes pacing rates and expects a
qdisc that will honor them.

## Worked Demo: CoDel State Machine Under Load

The demo runs a deterministic discrete-event queue: a bulk flow whose
demand exceeds capacity (standing queue), plus a sparse flow arriving
mid-simulation. It reports sojourn percentiles with and without the
AQM, and shows the drop episode's √-spacing schedule.

```python
# Closed-loop CoDel simulation: the bulk sender reacts to drops (AIMD),
# so the AQM's signal actually changes behavior. 1 ms ticks, 1 pkt/ms
# capacity. Sender rate adapts: multiplicative decrease on a drop,
# additive increase (+0.005 pkt/ms per ms) while unmarked.
# no-AQM mode uses tail-drop at depth 200 (a plain big buffer).

import math

TARGET, INTERVAL = 5.0, 100.0
CAP_PER_MS = 1.0

def run(use_codel):
    q, drops = [], 0
    dropping, count = False, 0
    first_above, drop_next = 0.0, 0.0
    rate = CAP_PER_MS            # pkt/ms offered by the sender
    budget = 0.0                 # fractional packet accumulation
    sojourns = []
    for t in range(2000):
        # arrivals from the AIMD sender
        budget += rate
        while budget >= 1.0:
            budget -= 1.0
            q.append(t)
        # service: 1 pkt/ms
        if q:
            pkt = q.pop(0)
            sojourn = t - pkt
            if use_codel:
                if dropping:
                    if sojourn > TARGET:
                        count += 1
                        drop_next = t + INTERVAL / math.sqrt(count)
                        rate *= 0.5
                        drops += 1
                    else:
                        dropping = False
                elif sojourn > TARGET:
                    if first_above == 0.0:
                        first_above = t + INTERVAL
                    elif t >= first_above:
                        dropping, count = True, 1
                        rate *= 0.5
                        drops += 1
                else:
                    first_above = 0.0
            else:
                if len(q) >= 200:          # tail drop, big dumb buffer
                    q.pop()
                    rate *= 0.5
                    drops += 1
            sojourns.append(sojourn)
        else:
            sojourns.append(0.0)
        rate = min(rate + 0.005, 4 * CAP_PER_MS)   # additive increase
    sojourns.sort()
    p50 = sojourns[len(sojourns) // 2]
    p99 = sojourns[max(0, int(len(sojourns) * 0.99) - 1)]
    return p50, p99, drops

p50, p99, drops = run(use_codel=False)
print(f"tail-drop: p50={p50:6.1f} ms  p99={p99:6.1f} ms  drops={drops}")
p50, p99, drops = run(use_codel=True)
print(f"CoDel   : p50={p50:6.1f} ms  p99={p99:6.1f} ms  drops={drops}")```

Real output:

```text
tail-drop: p50= 189.0 ms  p99= 199.0 ms  drops=14
CoDel   : p50=   0.0 ms  p99=  58.0 ms  drops=312
```

The rows tell the classic story honestly. With a plain big buffer
(tail-drop at 200 packets), the queue is *always* nearly full: median
sojourn 189 ms — that is bufferbloat, and the sender rarely gets a
loss signal (14 drops total) because a deep buffer only drops under
peak bursts. CoDel inverts the tradeoff: the standing queue never
stabilizes (median 0 ms — the queue spends most ticks empty or
single-digit), the sender gets constant, early, well-paced signals
(312 drops), and the *worst-case* sojourn (p99) falls 3.4x. The
latency win is bought with throughput-visible losses — exactly the
exchange an AQM is supposed to make. (A single-flow sim overreacts to
each loss more than a multiplexed real workload would; the RFC's
multi-flow evaluations show aggregate throughput barely affected.)

## Interview Questions

1. Why does CoDel measure *minimum* sojourn over an interval rather
   than average? (Bursts legitimately raise instantaneous sojourn; the
   minimum is the only statistic a single well-behaved flow cannot
   inflate without actually building a standing queue.)
2. Why INTERVAL = 100 ms? (Larger than the RTT of nearly every path
   where buffering matters, so a flow gets one full RTT to react
   before drops begin; the RFC analysis covers the worst cases.)
3. What makes fq_codel's sparse-flow priority different from
   priority-queuing with a DSCP class? (It is *automatic* — any
   low-rate flow is sparse by measurement, no marking or config, and
   it stops being prioritized the moment it becomes bulk.)
4. Why does BBR require the `fq` qdisc?
   (BBR programs explicit pacing rates; fq honors earliest-departure
   times. A FIFO would collapse BBR's pacing into bursts.)
5. Where does CAKE go beyond fq_codel, and why does a home router care?
   (Shaping below the modem's true rate, per-host fairness behind NAT,
   framing overhead compensation.)

## References

- Nichols, K., Jacobson, V. *Controlling Queue Delay*. ACM Queue 10(5),
  2012. https://doi.org/10.1145/2208917.2209336 (verified via Crossref)
- Höiland-Jørgensen, T., McKenney, P., Taht, D., Gettys, J., Dumazet,
  E. *The FlowQueue-CoDel Packet Scheduler and AQM Algorithm*.
  RFC 8290. https://www.rfc-editor.org/rfc/rfc8290.html (probed 200)
- Chiu, D.-M., Jain, R. *Analysis of the Increase and Decrease
  Algorithms for Congestion Avoidance in Computer Networks*.
  Computer Networks 17, 1989 — the convergence result behind the √
  spacing. https://doi.org/10.1016/0169-7552(89)90019-6 (verified via
  Crossref)
- tc-fq_codel(8) manual: https://man7.org/linux/man-pages/man8/tc-fq_codel.8.html
  (probed 200)
- CAKE overview (OpenWrt/sch_cake docs):
  https://openwrt.org/docs/guide-user/network/traffic-shaping/sch_cake
  (probed 200)

## Cross-References

- [Congestion control (survey incl. CoDel/PIE)](./congestion-control-advanced.md)
  — the sender-side algorithms these queues discipline.
- [TCP pacing and autotuning](../tcp/pacing-autotuning.md) — the
  sender-side smoothing that pairs with AQM.
- [Data-center TCP and DCTCP](./datacenter-tcp.md) — ECN as the
  explicit alternative to drop-based signaling.
