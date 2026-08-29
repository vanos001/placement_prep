# Learning-Based Congestion Control: Copa, PCC, and the Delay-Throughput Tradeoff

Every congestion controller answers one question differently: *what should the
bottleneck look like when I am pushing it?* Loss-based TCP answers "full, right
up to the drop" -- the buffer is a sensor and overflow is the reading.
[BBR](../tcp/bbr.md) answers "modeled but mostly out of the way" -- estimate
bottleneck bandwidth and propagation RTT, then sit at the knee. This page
covers the other two stances: **measured instrument** (Copa treats the queue
as something readable end-to-end and pins its own footprint on it at a chosen
`delta`-packet target) and **utility function** (PCC, Aurora, Remy treat rate
control as optimization: score each rate interval, climb the gradient, no
network model at all). The survey-level Copa/PCC treatment and the
congestion-control family table live in
[congestion-control-advanced.md](congestion-control-advanced.md); this page
goes deeper into the mechanisms, the delay-throughput tradeoff, and why these
designs struggle to coexist with CUBIC.

## Copa: pin your own standing queue at delta packets

Copa (Arun and Balakrishnan, NSDI 2018) is delay-based, windowed, and heavily
paced. Its central trick is reading *its own* contribution to the bottleneck
queue from measurements every TCP already has:

```text
 background ---> +-------------------------------------------+
 (loss-based,   |      shared FIFO queue, q bytes           |--> link drains
  on/off)       +-------------------------------------------+    C bytes/ms
 foreground --->    ^         ^
 (Copa or CUBIC)    |         |
   Copa watches:    RTT = RTTmin + q/C          (from every ACK)
   Copa controls:   own footprint = rate x (RTT - RTTmin)
                    [Little's law: your bytes in the queue = the rate
                     they drain at x how long each one waits]
   CUBIC watches:   only "did q overflow B?"    (drop-tail at B)
```

`rate x (RTT - RTTmin)` is the sender's standing queue, computed with no
network feedback at all. Copa holds that footprint at a target of `delta`
packets: at or below target it increases additively with the increment scaled
by `1/delta`, so a small target (1-2 packets) is reachable -- just slowly;
above target it cuts fast (halve the window per RTT). The asymmetry is what
lets the controller settle on a queue of a *known, chosen size* instead of
sawtoothing like AIMD. Two details make it practical:

- **Pacing is not optional.** Bursts would momentarily inflate everyone's RTT,
  including Copa's own estimate; packets are spaced over the RTT (see
  [fq-codel-pacing.md](fq-codel-pacing.md) for the qdisc machinery).
- **RTTmin is a min filter over a recent window**, not "smallest RTT ever".
  Route changes would poison a forever-min; a too-short window misses the
  drain troughs of a loss-based neighbor's sawtooth and biases RTTmin high.

### Latency mode, delay mode, and why the min filter gates the switch

| Mode | Target on the own-standing-queue instrument | Suited for |
| ----------- | -------------------------------------- | ---------- |
| Latency mode | `delta` packets (fixed byte count) | Bulk flows: throughput subject to small delay |
| Delay mode | `delta x RTTmin` of queueing delay | Interactive flows: RTT stays near `(1 + delta) x RTTmin` as bandwidth grows |

The sender switches modes when the measured RTT stays above a threshold
multiple of RTTmin, and switches back when it falls. Because the comparison is
against the min-filtered floor, one jitter spike or one burst of ACK
compression cannot flip the mode -- only sustained elevation can. That is
"robustness by min filter" in a nutshell: the filter removes the transient
component of the delay signal, and the mode logic reacts only to what remains.

## PCC: rate control as online learning

PCC (Performance-oriented Congestion Control, NSDI 2015) removes the network
model entirely. The sender commits to a rate for a short epoch, observes the
*consequences* (throughput, loss, latency), maps them to a scalar utility, and
runs local search on the rate: perturb up, perturb down, keep the direction
that raised the score. Nothing is assumed about bottleneck queueing, ECN
support, or what an RTT sample means -- only the score counts.

- **PCC Vivace (NSDI 2018)** turns the heuristic into textbook online
  learning: a concave utility over the rate, epochs that probe the empirical
  gradient, learning-rate-style steps toward the optimum. The payoff is
  provable convergence to a fair equilibrium; the cost is measurement
  discipline, since utility must be computed over epochs aligned with the rate
  actually applied -- which pushed real implementations into userspace.
- **PCC Proteus (SIGCOMM 2020)** fixes an economic flaw: one fixed learning
  rate must trade off stealing idle capacity fast versus not overreacting in
  steady state. Proteus redesigns the utility so an aggressive "scavenger"
  phase that inhales free bandwidth coexists with a fair, stable equilibrium.
- **Aurora (Jay et al., ICML 2019)** replaces gradient ascent with deep
  reinforcement learning: a DQN whose state summarizes recent throughput,
  delay, and loss, whose actions are discrete multiplicative rate changes, and
  whose reward is, again, a utility. Trained in simulation and run on real
  Internet paths, it beat fixed designs *on the utility it was rewarded for*.
  Caveats: reward engineering is the whole game (you get exactly the metric
  you pay for), and policies are brittle outside their training distribution.
- **Remy (SIGCOMM 2013)** and the **learnability study (SIGCOMM 2014)** are
  the offline branch: search a space of computer-generated congestion rules
  against simulated networks and a designer-chosen objective, then ship the
  winner. Remy beat human-designed TCP *in the training environments*; the
  learnability study showed the advantage is real but sensitive to mismatch
  between training and deployed network -- foreshadowing the sim-to-real
  headaches Aurora-style RL later hit.

Positioning against BBR in one sentence: BBR estimates the *path*, Copa pins
its own *queue footprint*, PCC and Aurora estimate nothing and score
themselves.

## Why cross-protocol fairness is hard

On a shared FIFO drop-tail bottleneck the two families cannot converge to a
common equilibrium, because they react to different events. A loss-based
flow's steady state is a loss rate that exactly cancels AIMD growth -- it
*wants* a full buffer, and queueing delay is invisible to it. A delay-based
flow's steady state is a queueing delay just under its target -- it yields
*before* any loss happens. Share a FIFO and the dance is one-sided: the
delay-based sender cuts while the loss-based sender still sees zero loss and
keeps growing; the freed space is swallowed by the loss-based sender's
sawtooth. Repeat every RTT and the delay-based flow is crowded toward the
bottom of its operating curve -- the starvation result that motivated much of
the datacenter-transport literature. BBRv1-versus-CUBIC contention (see
[../tcp/bbr.md](../tcp/bbr.md)) is the same argument with a model-based sender
in the Copa seat. The coupling is structural: for a persistent sender on a
FIFO, throughput beyond the fair share literally *is* standing queue -- extra
packets held in the buffer waiting -- so throughput bought by ignoring delay
is delay imposed on everyone. Escaping it means changing the queue, not the
sender: per-flow queueing and AQM (FQ-CoDel) break the coupling, and ECN or
Swift moves the signal earlier than drop-tail ever allows (see
[datacenter-tcp.md](datacenter-tcp.md)).

## Demo: one bottleneck, two foreground laws

Simplified fluid model (1 ms ticks): 10 Mbit/s link, 10 ms propagation RTT,
30-packet drop-tail buffer, on-off CUBIC-like background (loss-driven AIMD
while on, idle 300 ms of every 900). Only the foreground law differs between
the two runs. Pure stdlib, deterministic.

```python
# Simplified fluid model, 1 ms ticks: one 10 Mbit/s FIFO with a 30-packet
# drop-tail buffer, an on-off CUBIC-like background source (AIMD while on,
# idle while off), and a foreground sender using either loss-based AIMD
# (+1 MSS per RTT growth, halve on loss, ignores delay) or a copa-mode law
# that pins its own standing queue at delta packets, estimated as
# rate * (RTT - min RTT). No slow start, no ACK clocking, no pacing gaps.
C, RTT0, PKT = 1250.0, 10.0, 1500   # capacity bytes/ms, base RTT ms, packet B
BUF, DELTA, DT = 30 * PKT, 2, 1.0   # buffer bytes, target packets, tick ms
T_TOTAL, T_MEAS = 3000, 1500        # simulated ms; measure the steady tail

def run(mode):
    q = 0.0                          # shared queue, bytes
    bg, fg = 0.25 * C, 0.15 * C      # background / foreground rates
    bg_l = fg_l = 0.0                # loss bytes accrued this epoch
    bg_t = fg_t = 0.0                # ms since last control update
    hist, sent, dsum, ticks, on = [], 0.0, 0.0, 0, True
    for t in range(T_TOTAL):
        if on and t % 900 >= 600: on, bg = False, 0.0
        elif not on and t % 900 < 600: on, bg = True, 0.25 * C
        arr = (fg + bg) * DT
        over = max(0.0, q + arr - BUF)                 # drop-tail overflow
        if arr > 0:
            fg_l += over * fg / arr; bg_l += over * bg / arr
        q = max(0.0, q + arr - over - min(q + arr - over, C * DT))
        rtt = RTT0 + q / C
        hist = hist + [rtt]
        if len(hist) > 600: hist.pop(0)                # min-filter window
        if t >= T_MEAS:
            sent += fg * DT; dsum += q / C; ticks += 1
        if on:
            bg_t += DT
            if bg_t >= rtt:                            # loss-only reaction
                bg = bg / 2 if bg_l > 0 else bg + PKT / rtt
                bg_l, bg_t = 0.0, 0.0
        fg_t += DT
        if mode == "loss" and fg_t >= rtt:
            fg = fg / 2 if fg_l > 0 else fg + PKT / rtt
            fg_l, fg_t = 0.0, 0.0
        elif mode == "copa" and fg_t >= rtt:
            if fg * (rtt - min(hist)) > DELTA * PKT:   # own queue over target
                fg *= 0.5                              # fast multiplicative cut
            else:
                fg += (PKT / DELTA) / rtt              # slow additive rise
            fg_l, fg_t = 0.0, 0.0
    return sent * 8 / ((T_TOTAL - T_MEAS) * 1000.0), dsum / ticks

rows = [(name, *run(m)) for name, m in
        [("loss-based", "loss"), ("copa-mode", "copa")]]
print("Bottleneck: 10 Mbit/s, RTTmin 10 ms, 30-pkt drop-tail buffer,\n"
      "background CUBIC-like source: on 600 ms / off 300 ms, on => AIMD.\n")
print("foreground      throughput    mean queueing delay")
for name, thr, delay in rows:
    print("%-14s  %6.2f Mbit/s  %8.2f ms" % (name, thr, delay))
d = dict((n, (a, b)) for n, a, b in rows)
print("\nOperating points (throughput, delay):\n"
      "  loss-based -> (%.1f Mbit/s, %.1f ms)   copa-mode -> (%.1f Mbit/s, %.1f ms)"
      % (d["loss-based"][0], d["loss-based"][1],
         d["copa-mode"][0], d["copa-mode"][1]))
```

Real output of the program above:

```text
Bottleneck: 10 Mbit/s, RTTmin 10 ms, 30-pkt drop-tail buffer,
background CUBIC-like source: on 600 ms / off 300 ms, on => AIMD.

foreground      throughput    mean queueing delay
loss-based        8.28 Mbit/s     20.97 ms
copa-mode         3.93 Mbit/s     10.68 ms

Operating points (throughput, delay):
  loss-based -> (8.3 Mbit/s, 21.0 ms)   copa-mode -> (3.9 Mbit/s, 10.7 ms)
```

Read the points against the physics. 21 ms of mean queueing delay is 58% of
the absolute worst case (30 packets at 10 Mbit/s = 36 ms): the loss-based
foreground chronically rides a near-full buffer it helped fill. The copa-mode
foreground holds *its own* footprint at `delta = 2` packets (2.4 ms of its own
making); its 10.7 ms mean is dominated by the background's sawtooth, which no
sender-side law can remove. That is the delay-throughput tradeoff in one
table: the loss-based law converts indifference to delay into ~2.1x
throughput; the copa-mode law spends that throughput buying the low-latency
operating point. Neither number is "wrong" -- they are different points on the
shared queue's frontier, selected by the control law.

## Measurement pitfalls that sink delay- and utility-based designs

- **ACK compression.** A burst queued on the reverse path stretches ACK
  spacing and inflates forward RTT samples that say nothing about the forward
  queue. A min filter absorbs short compressions (spikes vanish under the
  minimum), which is exactly why Copa is built on one, and why PCC averages
  utility over epochs instead of trusting single samples.
- **Min-filter poisoning, both directions.** A window that never saw a drain
  trough biases RTTmin high, so the own-queue estimate reads low and the
  sender overshoots the buffer it thinks it is probing. A window far too long
  keeps a stale RTTmin after a route change or bandwidth drop, so the sender
  sees standing queue where there is none and starves itself. Deployed designs
  re-arm the filter when the path may have changed.
- **Jitter bigger than the target, and misaligned epochs.** `delta = 1-2`
  packets is a few ms at access speeds; hypervisor pauses, radio scheduler
  slots, and Wi-Fi power save produce delay noise larger than the signal, so
  delay mode (target proportional to RTTmin) and larger deltas exist. The
  Vivace twin of this problem: gradients are only meaningful if each epoch's
  stats describe the rate actually applied during that epoch -- leaking
  in-flight data from the previous rate is the standard implementation bug.
- **Where you timestamp.** Kernel softirq time, NIC hardware timestamps, and
  receiver-side QUIC reports give materially different RTT samples on loaded
  hosts; a controller tuned on one measurement plane misbehaves on another.
  The RDMA and Swift line of work sidesteps inference by having switches
  measure the queue directly (see
  [rdma-congestion-control.md](rdma-congestion-control.md)).

## Where the ideas actually run

- **BBR** is the only member of this wave shipping as a selectable kernel TCP
  variant; it is model-based rather than learning-based, which is precisely
  why it survived kernel integration. BBRv2/v3 added loss and ECN response
  largely to fix the cross-protocol fairness problem above.
- **Vivace-style online learning** fits userspace QUIC stacks, where
  per-packet pacing and timestamps are free; kernel PCC attempts fought the
  epoch alignment problem for years. The estimator most engineers touch daily
  is WebRTC's GCC -- a hybrid delay-gradient trendline plus loss response,
  i.e., a hand-designed point between the two families on this page.
- **Copa** has kernel prototypes and anchors the modern robustness literature:
  Agarwal, Arun, Ray, Martins, and Seshan's "Towards provably performant
  congestion control" (NSDI 2024) formalizes the noise and min-filter failure
  modes this page describes qualitatively.

> **Interview Angle**: (1) "Why can't a delay-based flow and a loss-based flow
> converge to a fair share on one FIFO?" -- answer with the two equilibrium
> conditions above, then say the fix is queue discipline, not the sender.
> (2) "Your min-RTT window is 1 s and a flow gets re-routed mid-life; what
> breaks, and how do you detect it?" (3) "Design a utility function for a
> video-call sender: which term punishes loss, and why is a loss *burst* worse
> than the same loss rate spread out?" (retransmit latency spikes and stale
> reference frames, not average loss.)

## References

All URLs probed from this sandbox in Aug 2026; usenix.org and doi.org answer
403 to automated curl, so those were verified via DBLP/Crossref records (keys
and DOIs noted inline) instead.

- [Copa: Practical Delay-Based Congestion Control for the Internet -- Venkat Arun, Hari Balakrishnan, NSDI 2018 (DBLP conf/nsdi/ArunB18, pp. 329-342)](https://www.usenix.org/conference/nsdi18/presentation/arun)
- [PCC Vivace: Online-Learning Congestion Control -- Mo Dong et al., NSDI 2018 (DBLP NSDI'18 session listing)](https://www.usenix.org/conference/nsdi18/presentation/dong)
- [PCC: Re-architecting Congestion Control for Consistent High Performance -- Mo Dong et al., NSDI 2015 (arXiv 1409.7092)](https://arxiv.org/abs/1409.7092)
- [PCC Proteus: Scavenger Transport And Beyond -- Tong Meng, Neta Rozen Schiff, P. Brighten Godfrey, Michael Schapira, SIGCOMM 2020, pp. 615-631 (DOI 10.1145/3387514.3405891)](https://doi.org/10.1145/3387514.3405891)
- [A Deep Reinforcement Learning Perspective on Internet Congestion Control (Aurora) -- Nathan Jay, Noga Rotman, P. Brighten Godfrey, Michael Schapira, Aviv Tamar, ICML 2019, PMLR v97](https://proceedings.mlr.press/v97/jay19a.html)
- [TCP ex machina: computer-generated congestion control (Remy) -- Keith Winstein, Hari Balakrishnan, SIGCOMM 2013, pp. 123-134 (DOI 10.1145/2486001.2486020)](https://doi.org/10.1145/2486001.2486020)
- [An Experimental Study of the Learnability of Congestion Control -- Anirudh Sivaraman, Keith Winstein, Pratiksha Thaker, Hari Balakrishnan, SIGCOMM 2014 (DOI 10.1145/2619239.2626324)](https://doi.org/10.1145/2619239.2626324)
- [Towards provably performant congestion control -- Anup Agarwal, Venkat Arun, Devdeep Ray, Ruben Martins, Srinivasan Seshan, NSDI 2024](https://www.usenix.org/conference/nsdi24/presentation/agarwal-anup)
- [Swift: Delay is Simple and Effective for Congestion Control in the Data Center -- Gautam Kumar et al., SIGCOMM 2020 (DOI 10.1145/3387514.3406591)](https://doi.org/10.1145/3387514.3406591)
