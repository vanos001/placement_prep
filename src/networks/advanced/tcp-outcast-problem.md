# The TCP Outcast Problem: When Loss Synchronization Picks a Victim

Datacenter TCP assumes the switch is a neutral referee: packets arrive, the
buffer fills, and if anything must be dropped, the pain lands more or less
evenly. Prakash, Dixit, Hu, and Kompella showed at NSDI 2012 that commodity
switches break this assumption in a specific, vicious way [1]. When bursts
from two input ports race to the same output port, the drop-tail queue does
not drop a fair sprinkle of packets -- it drops a *contiguous batch* from one
port and nothing from the other, a phenomenon the authors named a
**port-blackout**. The blackout itself is unbiased, hitting either port with
equal probability. The injustice happens downstream: a port carrying one
flow loses that flow's *entire* congestion window and sends it into an
RTO timeout, while a port carrying nine flows loses only a ninth of each
window, from which every flow fast-recovers. Repeated at every overflow,
the single flow is systematically "outcast" -- the paper measured victims
at a small fraction of their fair share on a real hardware testbed. This
page dissects the mechanism, builds a runnable model, and surveys the
mitigation families the follow-up literature produced.

## The port-blackout mechanism

Watch one output port of a commodity ToR switch. Its buffer holds a fixed
number of packets; the queue discipline is tail-drop, the default on cheap
silicon because it is one pointer and no bookkeeping. Two input ports --
say the ToR uplink toward a target rack and an aggregation port feeding the
same destination -- flush bursts in the same short interval:

```text
   input port A (1 flow)          input port B (9 flows)
        [v v v v v]                  [c1 c1 c1][c2 c2][c3 ...]
             \                             /
              \                           /
               v                         v
        +------------------------------------------+
        |  output port buffer (drop-tail, B slots) |
        +------------------------------------------+
                          |
                          v   shared destination
   A + B > B_slots  =>  tail-drop rejects the arriving burst back-to-back;
   the batch lands on ONE input port -- the port-blackout -- which the
   paper observed to be uniform at random between the two ports.
```

The critical property is *batchiness*. Drop-tail rejects the tail of an
arriving burst, and bursts are port-serial: the switch receives all of
port A's backlog, then all of port B's (or vice versa). When the offered
load exceeds the buffer, the rejected run of consecutive packets comes
almost entirely from whichever port's burst straddled the overflow point.
Nothing in the drop-tail rule looks at flow identity or fairness -- the
queue only samples *arrival order*, and synchronized arrival is precisely
what all-to-one datacenter patterns produce.

## Why the small set loses: whole-window loss vs fast recovery

The blackout is port-wide, but its *consequences* per flow scale inversely
with the number of flows sharing that port -- the asymmetry at the heart
of the problem:

- **Small set, one port.** The port's burst *is* one flow's in-flight
  window. Blacked out wholesale, the flow loses its entire window at once.
  Fast recovery needs surviving duplicate ACKs to clock the pipeline; with
everything gone there is none, so the flow waits out the retransmission
timeout (hundreds of milliseconds) and restarts from a tiny window. One
blackout erases dozens of successful rounds.
- **Large set, other port.** The same dropped batch interleaves across N
  windows: each flow loses ~1/N of its window -- a normal congestion
signal -- fast-recovers by halving, and keeps its ACK clock running. The
port as a whole barely pauses.

So although the *port* is chosen fairly, the *per-flow loss intensity* is
catastrophically asymmetric, and TCP's timeout rule converts that intensity
difference into a throughput difference that compounds every RTT -- largest
exactly when flow counts across the two ports are most unbalanced.

## The pattern that triggers it

Outcast needs a shared output bottleneck and unbalanced fan-in, which is
the geometry of an ordinary rack: several senders under one ToR pushing to
one destination reachable through another ToR's uplink. Barrier-style and
all-to-one workloads (distributed storage fan-in, shuffle, replication)
naturally put many flows on one side and few on the other. Khandelwal,
Jain, and Kamara showed the same geometry is weaponizable inside a cloud:
a handful of adversary VMs recreating the fan-in pattern drove a victim
flow to about 10 Mbps against a fair share of about 100 Mbps -- 10% of
fair share -- with nine competing flows, every one obeying TCP congestion
control and under per-VM rate caps [2]. The attack is covert by
construction: it looks like an ordinary workload, and every packet is a
legitimate TCP packet; aggressive per-VM caps damp it, and distributed
patterns circumvent exactly that.

## A runnable model of the asymmetry

The simulation models the two-port geometry with the paper's rules: bursts
contend at a drop-tail output buffer; on overflow the blackout hits one
input port uniformly at random; the single-flow port loses its whole window
(timeout, RTO freeze, restart at cwnd 1) while each flow on the many-flow
port loses a fraction (fast recovery, cwnd halves). A counterfactual pass
swaps port blackouts for packet-level randomized drops (RED-style) at
identical offered load and seed.

```python
import random

random.seed(7)

# Two ToR input ports feed one drop-tail output port (Prakash et al., NSDI'12).
# Port A: 1 victim flow; Port B: 9 culprit flows. Each round both flush one
# burst (sum of active cwnds). On overflow the blackout hits ONE input port,
# uniformly at random, dropping its entire burst. The single-flow port loses
# its whole window -> RTO timeout, restart at cwnd 1; each culprit loses only
# ~1/N of its window -> fast recovery (cwnd halves).

PORT_A_FLOWS = 1
PORT_B_FLOWS = 9
ROUNDS = 300
BUFFER = 90          # output-port drop-tail buffer, packets
CWND_CAP = 45
RTO = 25             # timeout freeze, rounds
BASE = 10            # initial cwnd


class Flow:
    def __init__(self, name):
        self.name = name
        self.cwnd = BASE
        self.busy_until = 0
        self.delivered = 0
        self.timeouts = 0


def burst(flows, rnd):
    return sum(f.cwnd for f in flows if f.busy_until <= rnd)


def run(label):
    port_a = [Flow("V%d" % i) for i in range(PORT_A_FLOWS)]
    port_b = [Flow("C%d" % i) for i in range(PORT_B_FLOWS)]
    for rnd in range(ROUNDS):
        overflow = (burst(port_a, rnd) + burst(port_b, rnd)) > BUFFER
        hit_a = overflow and random.random() < 0.5
        hit_b = overflow and not hit_a
        for grp, hit, whole in ((port_a, hit_a, True), (port_b, hit_b, False)):
            if hit:  # port blacked out: its whole burst is dropped
                for f in grp:
                    if f.busy_until > rnd:
                        continue
                    if whole:  # single-flow port: whole-window loss -> RTO
                        f.timeouts += 1
                        f.busy_until = rnd + RTO
                        f.cwnd = 1.0
                    else:      # batch spread across N windows -> fast recovery
                        f.cwnd = max(BASE * 0.5, f.cwnd / 2)
            else:
                for f in grp:
                    if f.busy_until > rnd:
                        continue
                    f.delivered += int(f.cwnd)
                    f.cwnd = min(CWND_CAP, f.cwnd + 1)
    total = sum(f.delivered for f in port_a + port_b)
    va = sum(f.delivered for f in port_a) / total * 100.0
    vb = sum(f.delivered for f in port_b) / total * 100.0
    n_flows = PORT_A_FLOWS + PORT_B_FLOWS
    print("%s" % label)
    print("  victim port  (%d flow): %5.1f%% of bytes  (fair share %4.1f%%)"
          % (PORT_A_FLOWS, va, 100.0 / n_flows))
    print("  culprit port (%d flows): %5.1f%% of bytes (fair share %4.1f%%)"
          % (PORT_B_FLOWS, vb, 100.0 * PORT_B_FLOWS / n_flows))
    vt = port_a[0]
    print("  victim timeouts: %d of %d rounds frozen %d%% of the time"
          % (vt.timeouts, ROUNDS, 100 * vt.timeouts * RTO // ROUNDS))
    print("  per-flow throughput: victim %d vs culprit %d packets/flow"
          % (port_a[0].delivered, sum(f.delivered for f in port_b) // PORT_B_FLOWS))
    return va


share = run("drop-tail output buffer, 1-victim vs 9-culprit ports:")
print()
print("victim gets %.1f%% of delivered bytes vs 10.0%% fair share" % share)

# Counterfactual: same load and seed, but drops are packet-level randomized
# (RED-style) instead of port blackouts; no flow can lose its whole window.

random.seed(7)


def run_red():
    port_a = [Flow("V%d" % i) for i in range(PORT_A_FLOWS)]
    port_b = [Flow("C%d" % i) for i in range(PORT_B_FLOWS)]
    for rnd in range(ROUNDS):
        sent_a = sum(int(f.cwnd) for f in port_a if f.busy_until <= rnd)
        sent_b = sum(int(f.cwnd) for f in port_b if f.busy_until <= rnd)
        total = sent_a + sent_b
        p = max(0.0, (total - BUFFER) / total) if total else 0.0
        for grp in (port_a, port_b):
            for f in grp:
                if f.busy_until > rnd:
                    continue
                s = int(f.cwnd)
                # randomized drops hit each window in fraction p only, so a
                # whole-window loss (-> timeout) essentially never happens
                f.delivered += s - int(s * p)
                f.cwnd = max(2.0, f.cwnd * (1.0 - p)) if p else min(CWND_CAP, f.cwnd + 1)
    total_d = sum(f.delivered for f in port_a + port_b)
    return sum(f.delivered for f in port_a) / total_d * 100.0


share_red = run_red()
print()
print("RED-style randomized drops, same seed: victim gets %.1f%% vs 10.0%% fair share" % share_red)
```

Real output:

```text
drop-tail output buffer, 1-victim vs 9-culprit ports:
  victim port  (1 flow):   1.3% of bytes  (fair share 10.0%)
  culprit port (9 flows):  98.7% of bytes (fair share 90.0%)
  victim timeouts: 11 of 300 rounds frozen 91% of the time
  per-flow throughput: victim 237 vs culprit 2021 packets/flow

victim gets 1.3% of delivered bytes vs 10.0% fair share

RED-style randomized drops, same seed: victim gets 10.0% vs 10.0% fair share
```

Read the two passes as one controlled experiment: identical offered load,
identical seed, one changed property -- whether loss arrives as a port-wide
batch or as a per-packet sprinkle. The batch version sends the victim into
eleven RTO freezes, freezing it 91% of all rounds; the sprinkle version
never lets a flow lose its whole window, and fairness lands exactly on 10%.
The model is a cartoon of TCP dynamics: it makes the mechanism (batch loss
x uneven fan-in = asymmetric timeout exposure) legible, not throughputs.

## Mitigation families

| Family | Representative idea | Why it defuses outcast |
|---|---|---|
| Randomized queue management | RED-style early/random drops at the output buffer | no batch drops, so no flow loses its whole window; timeout exposure equalizes |
| ECN marking | DCTCP-style marking before drops (see [datacenter TCP](./datacenter-tcp.md)) | senders shrink before the buffer must batch-drop; the queue never blackouts a port |
| Per-flow scheduling | FQ-style byte fairness at the output port (see [advanced congestion control](./congestion-control-advanced.md)) | drops never concentrate on one input port's burst |
| Receiver-driven fairness | senders paced by receiver-granted rates (Huang et al. 2019 [5]) | removes the self-synchronized bursts that create blackouts |

The theoretical picture behind the table: outcast is a *loss-synchronization*
problem, sibling to incast but orthogonal -- incast destroys aggregate
goodput through buffer collapse, outcast destroys *per-flow fairness* through
batch-loss geometry. Analytical treatments followed quickly (Qin et al.,
ITC 2013 [4] and 2016 [3]), and the receiver-driven school hardened into
deployable proposals by 2019 [5].

## Interview drill

- **State the outcast mechanism in two sentences.** Drop-tail queues drop
contiguous batches, so an overflow blackouts one input port's burst
wholesale; ports are hit uniformly at random, but per-flow damage scales
inversely with the number of flows sharing the hit port.
- **Why does the single flow time out while the nine flows do not?** The
single flow's window is the entire dropped batch, so no ACK stream survives
to clock fast recovery -- it waits for RTO. Nine interleaved windows each
lose ~1/N of their window; enough ACKs remain, and each flow fast-recovers
with a halved window.
- **Why is this a datacenter problem and not an Internet problem?** It
needs low RTTs (windows comparable to switch buffers), synchronized
arrivals (all-to-one rack patterns), and shallow commodity edge buffers;
long-RTT Internet paths rarely synchronize bursts tightly enough for a
port-blackout to swallow whole windows.
- **How would you detect outcast in production, and what is the smallest-blast-radius fix?** Detect by per-flow throughput bimodality at ToR pairs
correlated with fan-in degree, plus RTO spikes on the minority side;
per-input-port tail-drop burst counters are the direct switch signal. Fix
with ECN marking (DCTCP-style) if endpoints support it -- it removes the
batch-drop mode entirely -- or RED-style randomization as a firmware-level
queue-discipline change.

## References

1. P. Prakash, A. A. Dixit, Y. C. Hu, R. R. Kompella, "The TCP Outcast Problem: Exposing Unfairness in Data Center Networks," USENIX NSDI 2012. <https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/prakash> (canonical page; bot-walled to automated fetch, verified via DBLP and the ACM DL entry 10.5555/2228298.2228339)
2. A. Khandelwal, N. Jain, S. Kamara, "Attacking Data Center Networks from the Inside" (covert outcast attack: victim driven to ~10 Mbps vs ~100 Mbps fair share at N=9 flows). <https://cs.brown.edu/people/seny/pubs/dcn.pdf>
3. Y. Qin, W. Yang, Y. Ye, Y. Shi, "Analysis for TCP in data center networks: Outcast and Incast," *Journal of Network and Computer Applications* 70, 2016. DOI 10.1016/j.jnca.2016.04.014 (Crossref-verified)
4. Y. Qin, Y. Shi, Q. Sun, L. Zhao, "Analysis for unfairness of TCP outcast problem in data center networks," *ITC 2013*. DOI 10.1109/ITC.2013.6662965 (Crossref-verified)
5. J. Huang, S. Li, R. Han, J. Wang, "Receiver-driven fair congestion control for TCP outcast in data center networks," *Journal of Network and Computer Applications* 130, 2019. DOI 10.1016/j.jnca.2019.01.024 (Crossref-verified)
6. USENIX ;login: vol. 37, no. 4, August 2012 (coverage of DCN performance pathologies incl. synchronized-arrival drops). <https://www.usenix.org/system/files/login/issues/august2012.pdf>
