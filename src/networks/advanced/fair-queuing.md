# Fair Queuing and Packet Scheduling

Every router, NIC, and load balancer must answer one question per packet: *who goes
next?* FIFO answers "whoever arrived first", which lets one noisy flow monopolize the
link. The fair-queuing family answers "whoever has received the least relative to its
entitlement". This page covers the algorithm lineage: bit-by-bit fair queuing, WFQ and
virtual time, max-min fairness, DRR, SFQ, hash-bucket fairness, and hierarchical
scheduling. CoDel/FQ-CoDel internals, the Linux `tc` command surface, and token-bucket
shaping live on their own pages: [fq_codel & pacing](./fq-codel-pacing.md),
[tc qdiscs](../../linux/kernel/networking/tc.md), [traffic shaping](./traffic-shaping.md),
and [DiffServ PHBs](./diffserv-qos.md).

## From round robin to the bit-by-bit ideal

Plain round robin is fair in *packets*, not in *bytes*: give flows with 1500-byte and
64-byte packets one slot each and the big-packet flow wins 23:1 in bytes. Demers,
Keshav, and Shenker's fix imagines the fluid ideal, transmitting one bit from each
backlogged flow per round, then rebuilds packets from that bit stream. In weighted form,
round `r` serves `w_i` bits of backlogged flow `i`; a packet of `L` bits arriving at
round `R(a)` gets:

```text
  F(i,k) = max( F(i,k-1), R(a(i,k)) ) + L / w_i
```

Packets leave in ascending `F` order, and the order does not depend on packet sizes: a
flow's *k*-th bit finishes no later than it would under the fluid ideal.

```text
  flows 1 (w=3) and 2 (w=1), unit packets, C = 1 pkt/ms, both backlogged
  finish tags  flow 1: 1/3 2/3 1 4/3 5/3 2 7/3 8/3 3 ...
               flow 2:   1       2       3      ...
  send order (merge by tag; ties at 1, 2, 3 -> lower flow id first):
               [F1 F1 F1 F2]  [F1 F1 F1 F2]  [F1 F1 F1 F2] ...
  real time ms: 0  1  2  3     4  5  6  7     8  9  10 11
```

Over any window the split is exactly 3:1 regardless of packet sizes. Two implementation
problems block direct use: computing the current round number `R(t)` for a mid-burst
arrival requires solving a quadratic (Demers et al. derive it), and dispatch needs the
minimum finish tag, giving O(log n) per packet with a heap.

## WFQ: finish tags and virtual time

Weighted Fair Queuing (Parekh and Gallager's packet-level version is called PGPS)
materializes the tag formula. *Virtual time* `V(t)` is the round number of the fluid
system: while the server stays busy it advances at rate `C / sum(w_i)` over backlogged
flows; when every queue empties, `V` jumps to real time. A packet arriving at `a` into
flow `i` gets start tag `S = max(F_i_prev, V(a))` and finish tag `F = S + L/w_i`; the
server always sends the smallest-tagged packet. Three facts carry most interview
questions:

1. WFQ is work-conserving: if any queue is backlogged, the link is busy.
2. The PGPS bound: a packet starts service no later than its fluid-ideal *finishing*
   time plus `L_max/C` - the price of one packet jumping the fluid queue. All
   end-to-end delay and burstiness bounds for GPS networks transfer to WFQ plus this
   packetization term.
3. The cost is the heap: O(log n) per packet - exactly what DRR later removes.

## Max-min fairness and water-filling

Fair shares are usually *defined*, not derived, via max-min (Bertsekas and Gallager):
an allocation is max-min if it is feasible and no flow can get more without taking
bandwidth from a flow whose allocation is less than or equal to its own. The
computation is water-filling: sort demands ascending, saturate the smallest demands at
the current level, spread the remaining capacity equally over the still-unsatisfied
flows, and repeat. WFQ with equal weights converges to this when all flows are
backlogged; with weights `w_i`, flow `i`'s level scales by `w_i`. The demo at the end
of this page computes a water-filling allocation in its first lines.

## DRR: fair queuing in O(1)

Shreedhar and Varghese's Deficit Round Robin removes the sorting. Each backlogged flow
keeps a **deficit counter** `DC`; when the round-robin pointer visits flow `i`, add its
**quantum** `Q_i` to `DC`, then transmit packets while the head packet fits (`DC -= L`
per packet). A queue that empties resets `DC` to 0; a partially served visit carries
leftover credit to the next visit. Since `Q_i` is proportional to `w_i`, over `n` rounds
each flow receives `n * Q_i` bytes: exact long-run fairness with:

- O(1) work per packet: no tags, no heap, just a rotating active list;
- bounded bursts: one visit sends at most carried deficit plus one quantum (a little
  under two quanta for a continuously backlogged flow);
- latency as the price: a packet can wait nearly one full round, and a round takes
  `sum(Q_i)/C` of transmission time.

One rule the paper states plainly: the quantum must be at least the flow's MTU,
otherwise a big packet is repeatedly deferred while the deficit accrues. DRR is the
"fair enough, fast enough" point that most hardware and software schedulers implement.

## SFQ: start-time fair queuing

Golestani's Self-Clocked Fair Queueing (INFOCOM '94) keeps two tags but changes what
drives virtual time: `V` is defined as the *start tag of the packet currently in
service*, updated only at service completions. On arrival, `S = max(F_i_prev, V(a))`
and `F = S + L/w_i` as before. Because `V` now lives entirely in the scheduler's own
service events, the awkward round-number computation disappears; no quadratic, no
synchronization with a fluid clock. Golestani shows SFQ matches WFQ's throughput
fairness with the same O(log n) ordering, at the cost of slightly looser delay bounds.
The self-clocked idea survives inside `sch_fq` and fq_codel.

## Stochastic fairness: hash buckets and the DoS weakness

Per-flow state is expensive when flow counts reach the millions. McKenney's Stochastic
Fairness Queueing (INFOCOM '90) hashes each flow key into a fixed number of queues
served round-robin: no per-flow bookkeeping, O(1) per packet, but fairness is per
*bucket*, and buckets are shared. Benign collisions make two unlucky flows split one
slot; adversarial collision is worse - an attacker who can predict the hash (a plain
5-tuple hash is public knowledge) sends traffic that lands in the victim's bucket, or
sprays enough distinct 5-tuples that every bucket holds attacker traffic. Hashing makes
the scheduler's DoS surface probabilistic, not zero. Linux `sfq` implements this and
partially mitigates it with `perturb N`, re-seeding the hash every N seconds so a
mapping learned by an attacker expires (the man page frames the goal as "preventing any
single flow from drowning out the rest"). `fq_codel` instead keeps bounded per-flow
state in a 1024-bucket table - see [fq_codel & pacing](./fq-codel-pacing.md).

## Hierarchical scheduling: HTB

Hierarchies express policy: "customer A gets 50 Mbit, and inside A, backups get 10".
Each node has a guaranteed `rate` and a cap `ceil`; a class using less than `rate`
lends the surplus to siblings, and a class may **borrow** up to `ceil` from its
parent's unused budget. Linux HTB pairs the hierarchy with a DRR-style inner scheduler:
`tc-htb(8)` defines `quantum` as the "number of bytes to serve from this class before
the scheduler moves to the next class", defaulted to `rate / r2q`. HTB is therefore
hierarchical DRR with token buckets bolted on for shaping - the bucket decides whether
a class is eligible, the deficit round robin decides the order eligible classes drain.
HFSC extends the idea with real-time service curves; shaping mechanics versus
scheduling is covered in [traffic shaping](./traffic-shaping.md).

## The FQ-CoDel descendant

FQ-CoDel is this lineage's modern synthesis: a bounded flow table with DRR-style
quantum dispatch plus sparse-flow priority (new flows are served first), with a CoDel
AQM running *per queue* instead of tail-drop. Its scheduler arithmetic is the DRR and
SFQ math above; its delay logic is CoDel's. Internals, defaults, and pacing belong to
[fq_codel & pacing](./fq-codel-pacing.md).

## Where schedulers sit in the Linux qdisc stack

```text
     socket buffers (per-flow queues live inside leaf qdiscs)
                       |
  +--------------------v-------------------------+
  | root qdisc  htb 1:0                           |
  |   class 1:1  rate 50Mbit  ceil 80Mbit  prio 1 |
  |      leaf qdisc: fq_codel (fair queue + AQM)  |
  |   class 1:2  rate 30Mbit  ceil 50Mbit  prio 2 |
  |      leaf qdisc: sfq (hash-bucket fairness)   |
  +---------------------+-------------------------+
                        |
  multiqueue NIC: mq clones the hierarchy per TX queue,
  so every hardware queue runs its own scheduler
```

Classification order is fixed: the root qdisc is the only entry point, filters steer
packets into classes, and each class owns exactly one child qdisc. The historical root
default was `pfifo_fast`; modern kernels ship `fq_codel`, putting the fair-queuing
lineage quietly on every interface.

| Qdisc    | Family                  | Per-packet cost | Role in the stack                    |
| -------- | ----------------------- | --------------- | ------------------------------------ |
| pfifo    | none                    | O(1)            | default leaf; pure queue             |
| sfq      | stochastic hash buckets | O(1)            | classless fairness, perturb rehash   |
| drr      | deficit round robin     | O(1)            | classful; per-class quantum          |
| fq_codel | DRR-style flows + AQM   | O(1)            | classless; modern default            |
| htb      | hierarchy + DRR classes | O(1) per class  | classful root; rate/ceil/borrow      |
| hfsc     | service curves          | O(log n)        | classful; real-time guarantees       |

`tc-drr(8)` describes DRR as "a more flexible replacement for Stochastic Fairness
Queuing": unlike sfq it has no built-in queues; you attach classes and the kernel
schedules them with the quantum/deficit math.

## GPS ideal vs WFQ vs DRR: one runnable model

The model below runs one 12-byte/ms link against three flows with weights 6, 4, 2
(packet sizes 72, 36, 24 bytes; flow A goes idle at t=60). It first computes a max-min
water-filling allocation, then serves the same arrival trace through a fluid GPS ideal
(fine-step simulation with exact fractions), WFQ finish tags, and DRR deficit counters,
printing per-flow service shares and per-packet completion-time divergence from the
ideal.

```python
from fractions import Fraction as F
import heapq

# --- max-min fairness by water-filling (Bertsekas-Gallager) --------------
def maxmin(demand, cap):
    order = sorted(range(len(demand)), key=lambda i: demand[i])
    alloc = [0.0] * len(demand); left, rem = float(cap), len(demand)
    for pos, i in enumerate(order):
        if demand[i] <= left / rem:              # flow i saturates here
            alloc[i] = demand[i]; left -= demand[i]; rem -= 1
        else:                                    # rest share what is left
            for j in order[pos:]: alloc[j] = left / rem
            return alloc
    return alloc
print("water-filling [60,40,90,10] on cap 100 ->", maxmin([60, 40, 90, 10], 100))
print()

# --- GPS vs WFQ vs DRR on a shared link ----------------------------------
C = F(12)                               # link capacity: 12 bytes per ms
W = {"A": F(6), "B": F(4), "C": F(2)}   # weights (sum == C)
SIZE = {"A": 72, "B": 36, "C": 24}      # packet size per flow (bytes)
arr = [(F(t), "A", 72) for t in range(0, 70, 10)]            # A: then idle
for name in ("B", "C"):
    arr += [(F(t), name, SIZE[name]) for t in range(0, 121, 8)]  # backlogged
arr.sort()
TOT = sum(s for _, _, s in arr)
N = {f: sum(1 for a in arr if a[1] == f) for f in W}

# GPS ideal: fluid simulation, dt = 1/256 ms, exact arithmetic
gps, cum, pend, npk = {}, {f: F(0) for f in W}, {f: F(0) for f in W}, {f: 0 for f in W}
ai, t = 0, F(0)
while ai < len(arr) or any(pend.values()):
    step = min(F(1, 256), arr[ai][0] - t) if ai < len(arr) else F(1, 256)
    t += step
    while ai < len(arr) and arr[ai][0] <= t:
        pend[arr[ai][1]] += arr[ai][2]; ai += 1
    pool = C * step
    while pool > 0:
        act = [f for f in W if pend[f] > 0]
        if not act: break
        ws = sum(W[f] for f in act); moved = F(0)
        for f in act:
            s = min(pool * W[f] / ws, pend[f]); pend[f] -= s; cum[f] += s; moved += s
        pool -= moved
        if moved == 0: break
    for f in W:
        while npk[f] < N[f] and cum[f] >= (npk[f] + 1) * SIZE[f]:
            gps[(f, npk[f])] = t; npk[f] += 1

def wfq():                              # finish tags + virtual time
    ft, V, seq = {f: F(0) for f in W}, F(0), {f: 0 for f in W}
    heap, q, done, tf = [], {f: 0 for f in W}, {}, F(0)
    i = 0
    while i < len(arr) or heap:
        t = tf
        while i < len(arr) and arr[i][0] <= t:
            _, f, L = arr[i]; i += 1
            tag = (max(ft[f], V) if not q[f] else ft[f]) + F(L) / W[f]
            ft[f] = tag; q[f] += 1
            heapq.heappush(heap, (tag, f, seq[f], L)); seq[f] += 1
        if not heap:
            tf = max(tf, arr[i][0]); V = max(V, tf); continue
        tag, f, k, L = heapq.heappop(heap); q[f] -= 1
        tf += F(L) / C; V = max(V, tag); done[(f, k)] = tf
    return done

def drr(base=12):                       # quantum = w_i * base per round
    q = {f: [] for f in W}; DC = {f: F(0) for f in W}
    done, tf, ai, k = {}, F(0), 0, {f: 0 for f in W}
    while ai < len(arr) or any(q.values()):
        while ai < len(arr) and arr[ai][0] <= tf:
            _, f, L = arr[ai]; q[f].append(L); ai += 1
        prog = False
        for f in sorted(W):
            if not q[f]:
                DC[f] = F(0); continue
            DC[f] += W[f] * base
            while q[f] and q[f][0] <= DC[f]:
                L = q[f].pop(0); DC[f] -= L; tf += F(L) / C
                done[(f, k[f])] = tf; k[f] += 1; prog = True
            if not q[f]: DC[f] = F(0)
        if not prog and ai < len(arr): tf = max(tf, arr[ai][0])
        elif not prog: break
    return done

w, d = wfq(), drr()
print("link 12 B/ms | weights A=6 B=4 C=2 | packets A=72 B=36 C=24 bytes")
print("offered bytes: A=%d B=%d C=%d, total=%d | A idle from t=60 ms" %
      (N["A"] * 72, N["B"] * 36, N["C"] * 24, TOT))
print("flow  weight  GPS_share  WFQ_share  DRR_share")
for f in W:
    row = [100 * sum(1 for k in range(N[f]) if (f, k) in s) * SIZE[f] / TOT
           for s in (gps, w, d)]
    print("%-4s  %-6s  %8.2f%%  %9.2f%%  %9.2f%%" % (f, float(W[f]), *row))
print("flow  vs GPS ideal (ms), max / mean:   WFQ          DRR")
for f in W:
    dw = [w[(f, k)] - gps[(f, k)] for k in range(N[f])]
    dd = [d[(f, k)] - gps[(f, k)] for k in range(N[f])]
    print("%-4s  %31s %4.2f/%4.2f  %4.2f/%4.2f" % (f, "",
          float(max(map(abs, dw))), float(sum(dw) / len(dw)),
          float(max(map(abs, dd))), float(sum(dd) / len(dd))))
```

Run with `python3`:

```text
water-filling [60,40,90,10] on cap 100 -> [30.0, 30.0, 30.0, 10]

link 12 B/ms | weights A=6 B=4 C=2 | packets A=72 B=36 C=24 bytes
offered bytes: A=504 B=576 C=384, total=1464 | A idle from t=60 ms
flow  weight  GPS_share  WFQ_share  DRR_share
A     6.0        34.43%      34.43%      34.43%
B     4.0        39.34%      39.34%      39.34%
C     2.0        26.23%      26.23%      26.23%
flow  vs GPS ideal (ms), max / mean:   WFQ          DRR
A                                     7.00/-5.14  11.00/-8.57
B                                     6.00/-0.78  10.00/2.47
C                                     4.00/-1.81  5.00/-2.19
```

Reading the numbers:

- All three schedulers deliver identical long-run shares, and those shares track
  *offered* bytes (504/576/384), not configured weights: A stops offering at t=60, and
  the freed capacity goes to B and C in their weight ratio 60:40. That is max-min
  behavior, and it confirms no scheduler keeps paying a departed flow.
- Timing is where the family members differ. WFQ stays within about one packet
  transmission (L_max/C = 6 ms) of the fluid ideal; DRR's worst divergence is 11 ms,
  bounded by its round time (72+48+24)/12 = 12 ms. The negative means show WFQ letting
  whole packets jump *ahead* of the fluid ideal, the packetization freedom the PGPS
  bound prices at L_max/C.

## Failure modes and interview traps

- **Quantum below MTU (DRR/HTB).** A quantum smaller than the flow's packets starves it
  while the deficit accrues; the paper's fix is quantum >= MTU, and HTB's `r2q` default
  exists to enforce the same relation (`quantum = rate / r2q`).
- **Reading DRR windows as unfair.** DRR is fair over rounds, not milliseconds; a short
  window can show a flow idle for a round then bursting two quanta. Judge on sums over
  at least one full round.
- **Virtual time frozen during idle.** A WFQ variant that fails to advance `V` when all
  queues empty hands the returning flow credit for the whole idle gap - the classic bug
  that motivated SFQ's self-clocked clock.
- **Trusting hash fairness against an adversary.** Bucketed schedulers (sfq) are fair
  only if the hash is unpredictable; without `perturb`, collision targeting is trivial.
- **Confusing CPU and packet scheduling.** Linux CFS gives *threads* virtual runtime -
  the same fair-queuing idea, but the OS family
  ([round robin](../../os/scheduling/round-robin.md)) schedules runnable tasks, not
  weighted packet flows.

## References

1. A. Demers, S. Keshav, S. Shenker. *Analysis and Simulation of a Fair Queueing
   Algorithm*. ACM SIGCOMM 1989. <https://doi.org/10.1145/75246.75248>
2. A. K. Parekh, R. G. Gallager. *A Generalized Processor Sharing Approach to Flow
   Control in Integrated Services Networks: The Single-Node Case*. IEEE/ACM ToN, 1993.
   <https://doi.org/10.1109/90.234856>
3. M. Shreedhar, G. Varghese. *Efficient Fair Queuing Using Deficit Round-Robin*.
   IEEE/ACM Transactions on Networking, 1996. <https://doi.org/10.1109/90.502236>
4. S. J. Golestani. *A Self-Clocked Fair Queueing Scheme for Broadband Applications*.
   IEEE INFOCOM 1994. <https://doi.org/10.1109/INFCOM.1994.337677>
5. P. E. McKenney. *Stochastic Fairness Queueing*. IEEE INFOCOM 1990.
   <https://doi.org/10.1109/INFCOM.1990.91316>
6. D. Bertsekas, R. Gallager. *Data Networks*, 2nd ed., section 6.5 (max-min fairness).
   <https://web.mit.edu/dimitrib/www/netbook.html>
7. `tc-htb(8)`, `tc-sfq(8)`, `tc-drr(8)` - Linux manual pages.
   <https://man7.org/linux/man-pages/man8/tc-htb.8.html>
8. T. Hoiland-Jorgensen et al. *The FlowQueue-CoDel Packet Scheduler*.
   <https://arxiv.org/abs/1705.07134>
