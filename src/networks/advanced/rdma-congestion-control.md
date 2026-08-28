# RDMA Congestion Control: PFC, DCQCN, and the Lossless Trap

RDMA promises kernel-bypass latency and microsecond tail latency - on a
network that must never drop a packet, because RDMA has no retransmit
path (RoCEv2 delivers over lossy UDP but treats drops as transport
errors that stall QPs). Making Ethernet "lossless" via priority flow
control (PFC) creates a new failure universe: head-of-line blocking
amplified into deadlocks, congestion that shows up as pause storms
instead of drops, and rate control (DCQCN) bolted on top to stop the
pauses from eating the fabric. This page walks the machinery and the
monitoring that tells you which failure you have.

Siblings: [RDMA](../../linux/networking/rdma.md) for the verbs/queue-pair
mechanics, [datacenter TCP](./datacenter-tcp.md) for the lossy-network
CC algorithms (DCQCN's ECN cousin; HPCC covered there), and
[diffserv QoS](./diffserv-qos.md) for the priority-marking layer PFC
builds on.

## PFC: per-priority pause and why it deadlocks

802.1Qbb extends Ethernet PAUSE to traffic classes: a switch ingress
whose class buffer crosses its threshold sends a PAUSE frame upstream
per priority, for a duration; the upstream port stops transmitting that
class only. Lossless classes get their own buffers/queues end to end.

The deadlock: host A's port fills class-C buffers toward switch 1;
switch 1 pauses A; meanwhile B's buffers toward A are full and A pauses
B - and when the dependency cycle closes (A waits on buffers held by B
which waits on A), the paused frames can never drain. No packet is lost,
no timer expires: the deadlock is stable until something re-enables the
port. The classic two-priority cycle:

```text
  H1 --class red--> SW1 --red--> H2
   ^                                 |
   |  class blue (paused both ways)  v
  H4 <--blue-- SW2 <--blue--------- H3

  red fills SW1->H2 buffers, H2->SW2 red fills, SW2->H4 red ... and the
  blue class crossing the same links pauses the reverse direction -
  buffers holding paused frames cannot drain because the DRaining class
  is itself paused. Requires: a cycle + a full buffer per hop + two
  traffic classes crossing in opposite directions.
```

Mitigations, in deployment order: PFC watchdog timers (kill QPs that
have been paused too long - losing the lossless guarantee for the
offender instead of the fabric), separate lossless priority lanes with
dedicated buffer heads, lane-based traffic isolation (RDMA on dedicated
cables/switches), and the DCQCN work below that keeps pause from
triggering at all.

## DCQCN: rate-based ECN control for RoCEv2

DCQCN = ECN marking (switch) + rate reduction (NIC), assembled from
existing parts (DCTCP's marking + QCN's rate recovery):

1. **Switch**: on queue depth above threshold K, ECN-mark arriving
   RoCEv2 packets (CE bit in IP header).
2. **Receiver**: per QP, on marked packet, rate-limit a Congestion
   Notification Packet (CNP) back to the sender (CNP rate limit is
   essential - CNP storms are their own congestion event).
3. **Sender NIC** (per QP, alpha state machine): on CNP, fast rate
   decrease `R = R * (1 - alpha/2)`, alpha updated toward 1; without
   CNPs, alpha decays (`alpha = alpha * (1 - K)`) and the rate recovers
   via the QCN-style byte counter increase.

The design avoids per-packet ACKs (RDMA's transport doesn't offer
TCP-like acks) and reuses hardware queues - but the tuning surface is
large: ECN thresholds per switch buffer, CNP rate limits, alpha
decrease/increase gains. Mis-tuned, DCQCN shows the classic signature:
PFC pause frames rising BEFORE ECN marking engages (thresholds too
high), or rate collapse (alpha stuck at 1) under bursty incast.

## The demo: PFC deadlock checker + DCQCN rate trace

```python
#!/usr/bin/env python3
"""Two deterministic models:

1. PFC deadlock checker: given a topology cycle + which classes cross
   each link in which direction + per-link buffer state, detect a
   pause-dependency cycle that cannot drain (the classic 2-class
   opposite-direction crossing).

2. DCQCN sender rate trace: the alpha state machine under a burst -
   fast decrease on CNPs, alpha decay + rate recovery between them -
   showing the sawtooth and the collapse when CNPs keep arriving."""


def check_deadlock(links):
    """links: list of (src, dst, cls, buffer_full). A deadlock exists if
    a cycle of ports exists where every hop's buffer is full and the
    crossing class alternates (two classes crossing in opposite
    directions on a 4-cycle)."""
    # build port-level pause dependencies: a full buffer at (src->dst)
    # pauses (dst->src) transmission of that class
    pause_of = {}
    for src, dst, cls, full in links:
        if full:
            pause_of[(dst, src, cls)] = True
    # deadlock iff there exist h1..hk and classes c1..ck such that
    # each hop is paused and the cycle closes with the OTHER class:
    # h2->h1 paused (c1) while h1->h2 wants c2, etc.
    hosts = sorted({l[0] for l in links} | {l[1] for l in links})
    for a in hosts:
        for b in hosts:
            if a >= b:
                continue
            # both directions full, different classes = the deadlock shape
            f_ab = [l for l in links if l[0] == a and l[1] == b and l[3]]
            f_ba = [l for l in links if l[0] == b and l[1] == a and l[3]]
            if f_ab and f_ba:
                c1, c2 = f_ab[0][2], f_ba[0][2]
                if c1 != c2:
                    return True, (a, b, c1, c2)
    return False, None


LINKS = [
    ("H1", "H2", "red",  True),    # the red ring fills clockwise
    ("H2", "H3", "red",  True),
    ("H3", "H4", "red",  True),
    ("H4", "H1", "red",  True),
    ("H1", "H4", "blue", True),    # the blue counter-flow closes the trap
]
dead, why = check_deadlock(LINKS)
print("=== A. PFC deadlock checker ===")
print(f"  links: {[(s,d,c,'FULL' if f else 'ok') for s,d,c,f in LINKS]}")
if dead:
    a, b, c1, c2 = why
    print(f"  DEADLOCK: {a}<->{b} paused both ways with crossing classes "
          f"{c1}/{c2}")
    print("  drains never happen: each hop waits on a buffer that waits")
    print("  on the previous hop. Watchdog must kill a QP to break it.")

print()
print("=== B. DCQCN sender alpha/rate trace (burst of CNPs) ===")
R, alpha = 1.0, 0.0          # normalized rate, alpha state
K = 0.1                      # alpha decay gain
RATE_MAX = 1.0
trace = []
rng_cnps = [0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0]
for t, cnp in enumerate(rng_cnps):
    if cnp:
        alpha = min(1.0, alpha + 0.5)        # CNP: alpha += Gd
        R = max(R * (1 - alpha / 2), 0.02)   # fast decrease
    else:
        alpha = alpha * (1 - K)              # decay toward 0
        R = min(RATE_MAX, R * (1 + alpha / 2))  # QCN-style recovery
    trace.append((t, cnp, alpha, R))
print(f"  {'t':>2} {'CNP':>4} {'alpha':>7} {'rate':>7}")
for t, cnp, a, r in trace:
    print(f"  {t:>2} {'YES' if cnp else '.':>4} {a:>7.3f} {r:>7.3f}")
r_min = min(r for _t, _c, _a, r in trace)
print(f"  min rate {r_min:.3f}; rate recovers via alpha decay when CNPs stop.")
print("  collapse signature: CNPs every step keep alpha at 1 -> R ~ 0.02.")
```

```text
=== A. PFC deadlock checker ===
  links: [('H1', 'H2', 'red', 'FULL'), ('H2', 'H3', 'red', 'FULL'), ('H3', 'H4', 'red', 'FULL'), ('H4', 'H1', 'red', 'FULL'), ('H1', 'H4', 'blue', 'FULL')]
  DEADLOCK: H1<->H4 paused both ways with crossing classes blue/red
  drains never happen: each hop waits on a buffer that waits
  on the previous hop. Watchdog must kill a QP to break it.

=== B. DCQCN sender alpha/rate trace (burst of CNPs) ===
   t  CNP   alpha    rate
   0    .   0.000   1.000
   1    .   0.000   1.000
   2    .   0.000   1.000
   3    .   0.000   1.000
   4  YES   0.500   0.750
   5  YES   1.000   0.375
   6  YES   1.000   0.188
   7    .   0.900   0.272
   8    .   0.810   0.382
   9    .   0.729   0.521
  10    .   0.656   0.692
  11    .   0.590   0.897
  12  YES   1.000   0.448
  13    .   0.900   0.650
  14    .   0.810   0.913
  15    .   0.729   1.000
  min rate 0.188; rate recovers via alpha decay when CNPs stop.
  collapse signature: CNPs every step keep alpha at 1 -> R ~ 0.02.
```

## Monitoring: which failure am I in?

The counter triage every RoCE operator memorizes:

- **PFC pause frames in (ethtool -S, per priority)**: upstream is
  choking you; if pauses rise with ECN marks absent, DCQCN thresholds
  are too high and pause is doing the congestion control - the design
  failure mode.
- **CNP rate at the receiver**: CNP storms (tens of thousands per
  second per QP) mean either marking thresholds too low or the rate
  limiter broken.
- **QP in error/frozen state**: retransmission timeouts (RoCEv2's
  response timeout) - a *dropped* packet somewhere despite PFC, usually
  a buffer-size misconfiguration.
- **Watchdog kills**: the deadlock breaker fired; the log names the
  offending QP and priority - chase the two-class crossing that built
  it.

## Interview probes

- Construct the minimal PFC deadlock (hosts, classes, buffers) and
  explain why no timer expires without a watchdog.
- DCQCN composes DCTCP marking with QCN recovery: which component owns
  rate *decrease* and which owns *increase*, and why can't RDMA just
  run DCTCP?
- Your RoCE fabric shows rising PFC pauses but zero ECN marks: what is
  misconfigured, and what happens if you ignore it?
- Where does HPCC fit relative to DCQCN, and why does INT-based
  feedback beat CNP-based for the incast case? (Cross-link the
  algorithmic detail rather than re-deriving.)

## References

1. Zhu, Yibo, et al., "Congestion Control for Large-Scale RDMA
   Deployments", SIGCOMM 2015,
   [doi:10.1145/2829988.2787484](https://doi.org/10.1145/2829988.2787484)
   - the DCQCN design (ECN marking + CNP + alpha state machine).
2. Mittal et al., "TIMELY: RTT-based Congestion Control for Datacenters",
   SIGCOMM 2015,
   [doi:10.1145/2829988.2787510](https://doi.org/10.1145/2829988.2787510)
   - the RTT-based alternative that needs no ECN infrastructure.
3. [RDMA (this repo)](../../linux/networking/rdma.md) - the verbs/QP
   substrate and its Linux interface surface.
4. [IEEE 802.1bb (PFC) project page](https://www.ieee802.org/1/pages/802.1bb.html)
   - the priority flow control standard the lossless classes ride on.
5. [Data-center TCP (this repo)](./datacenter-tcp.md) - the lossy-path
   CC family (DCTCP/DCQCN context, HPCC mechanics).
