# TSN, Standard by Standard: Reading the IEEE 802.1 Time-Sensitive Networking Toolbox

Time-Sensitive Networking is not one protocol. It is a family of IEEE 802.1 amendments - each one a small, composable mechanism - that together turn a switched Ethernet into a network where selected flows get **provable bounds on latency, jitter, and loss** while everything else keeps flowing best-effort on the same wire. This page walks the family member by member: what each standard actually changes in a bridge, the arithmetic each one buys you, and where each is mandatory versus optional.

A companion page, [TSN & Deterministic Networking](./tsn-deterministic-networking.md), covers the deployment-level view: network calculus bounds, DetNet at layer 3, and the "one legacy switch breaks the chain" reality. Here we stay inside the bridge and read the standards as an engineer would.

## Why the family exists: two industries, one toolbox

**Pro audio started it.** In 2004-2005, live-sound and recording vendors were chaining laptops, mixers, and stage boxes over point-to-point FireWire and USB links, or over proprietary Dante-style solutions before Dante standardized. They needed multi-vendor, switched, sample-accurate audio over ordinary Ethernet hardware - no custom ASICs, consumer switch silicon. The IEEE 802.1 **Audio Video Bridging (AVB)** task group answered with four pieces (802.1AS sync, 802.1Qat reservation, 802.1Qav shaping, plus the 802.1BA systems profile): a stream admitted by SRP gets Class A delivery within **2 ms across up to 7 hops**, or Class B within 50 ms, using only a rate shaper and a synchronized clock.

**Automotive made it strict.** Around the same time, car makers were drowning in dedicated buses: a CAN for body electronics, FlexRay for chassis, MOST for infotainment, plus separate LVDS looms for every camera. Each bus is its own wiring harness, and harness weight is kilograms per vehicle. Replacing them with one Ethernet backbone demanded what AVB never promised: **hard worst-case bounds** (a brake-by-wire message cannot be "usually on time"), **protection against misbehaving nodes**, and **survival of a failed link without retransmission delay**. The 802.1 TSN task group (AVB renamed in 2012) delivered the 2015-2017 amendment wave: Qbv, Qbu/3br, Qci, Qch, CB, Qcc. Most were folded into the 802.1Q-2018 bridge revision but kept their amendment numbers as household names.

```text
genealogy of the 802.1 TSN family

2005        2009/2011            2012          2015-2017                2018->now
  |            |                   |               |                        |
AVB TG -->  AS Qat Qav BA -->  renamed TSN -->  Qbv Qbu Qci Qch CB -->  802.1Q-2018
(pro audio) (gPTP SRP CBS   (automotive     (3br IET frame           consolidation +
             AVB profile)    pulls harder)    preemption, FRER,        profiles: 802.1BA
                             Qcc CNC          CQF, policing)           AV, 802.1CM fronthaul,
                                              Qcp ATS                  IEC/IEEE 60802 industrial
```

The profiles matter more than the acronym soup suggests: 802.1BA says which parts a pro-AV system must implement; 802.1CM does the same for 5G fronthaul; IEC/IEEE 60802 (the joint IEC/IEEE project) defines the industrial-automation subset. When an interviewer says "TSN", the correct follow-up is "which profile?"

## How the pieces compose

```text
        what each layer of the toolbox does inside a bridge/end station

   reliability      802.1CB FRER ...... replicate over disjoint paths, dedupe
        |
   protection       802.1Qci PSFP ..... police ingress: filters, meters, gates
        |
   scheduling       802.1Qbv TAS ...... time-gated egress queues (GCL)
        |           802.1Qav CBS ...... rate-shape egress queues (credits)
        |           802.1Qch CQF ...... ping-pong queues per cycle
        |
   preemption       802.1Qbu + 802.3br  cut a preemptable frame mid-flight
        |
   time sync        802.1AS gPTP ...... one clock, phase-aligned, everywhere
        |
   management       802.1Qat SRP / 802.1Qcc CNC  declare, admit, configure
```

The dependency arrows point downward for a reason: scheduling is meaningless without a synchronized clock, and preemption exists mainly to shrink the guard bands that scheduling otherwise wastes.

## 802.1AS / gPTP: the substrate every other standard assumes

802.1AS profiles IEEE 1588 PTP for the bridged-LAN case and hardens it for real-time control:

- **Link-local L2 transport**: EtherType `0x88F7`, multicast `01-80-C2-00-00-0E` - no IP stack, no UDP ports, no risk of a router blackholing sync.
- **Peer delay mechanism on every link**: each port measures one-way link delay to its neighbor with `Pdelay_Req`/`Resp`, so a multi-hop path never accumulates unknown queuing estimates.
- **Per-port hardware timestamps**: every bridge port has its own clock (bridges behave as boundary clocks); sync is regenerated hop by hop rather than end-to-end.
- **A simplified BMCA** elects the grandmaster and, critically for TSN, establishes a common *phase*, not just a common rate: gate windows in Qbv are offsets from a shared cycle start, so "we agree on 1 ms cycles" is useless unless we also agree on where cycle 0 is.

The protocol mechanics (offset equations, ptp4l/PHC tooling, profile tuning) belong to [Time Synchronization](./time-synchronization.md); for TSN the takeaway is narrower: **802.1AS with hardware timestamping gives sub-microsecond phase alignment per hop, and every downstream standard silently assumes it.** Drift the clocks and Qbv gates open at different moments on different switches - the schedule becomes fiction.

## 802.1Qav: the credit-based shaper (CBS)

CBS is AVB's original traffic control. Each shaped queue carries a credit that evolves with two configured rates:

- `idleSlope` - the bandwidth the class is *reserved* (credit accrues at this rate while the queue is blocked),
- `sendSlope = idleSlope - portTransmitRate` (negative; credit drains at this rate while the queue transmits).

A frame may begin transmission only when credit >= 0. The bridge hardware derives the clamp values from one interference parameter (largest frame that can block the class):

```text
hicredit = maxInterferenceSize * idleSlope  / portTransmitRate    (>= 0)
locredit = maxInterferenceSize * sendSlope  / portTransmitRate    (< 0)
```

(these are exactly the formulas the Linux `tc-cbs` man page documents). With Class A at, say, 30% idleSlope on a 1 Gb/s port, an AVB stream's *average* bandwidth is guaranteed and its interference from best-effort traffic is bounded by one maximum frame per hop - which is precisely enough to promise 2 ms over seven hops for admitted streams, and no more.

That "no more" is the design lesson: CBS guarantees a rate, never a *time*. A burst of same-class traffic still delays you by up to max-frame-time per hop. If your traffic tolerates statistical rather than hard service, ordinary congestion control (see [Advanced Congestion Control](./congestion-control-advanced.md)) or Diffserv shaping is far cheaper; you reach for CBS when admission control plus rate guarantees suffice, and for Qbv when they do not.

## 802.1Qbv: the time-aware shaper (TAS)

TAS upgrades shaping to scheduling. Each egress port runs a repeating **gate control list (GCL)**: an N-cycle sequence of entries, each an 8-bit gate mask (one bit per traffic class queue) plus an interval length, all phase-locked to the 802.1AS cycle. A class may transmit only while its gate bit is 1. A scheduled flow therefore experiences:

```text
one-hop worst-case delay for a scheduled flow
  = worst wait for the next gate opening      (arrive just after your gate closed)
  + queueing behind co-class frames in that window
  + own wire time
```

Designing a GCL is checking three inequalities per class, per port:

1. **Capacity**: demand in the window (`frames/cycle x wire time`) <= window length.
2. **Deadline**: `wait + queue-ahead + tx <= deadline` for every scheduled flow.
3. **Guard band**: every closed gap before an express gate reopens must exceed the longest frame that can still be in flight (max frame wire time, unless 802.3br preemption shrinks it to a fragment).

Adding the flow-vs-window assignment makes this a scheduling optimization problem (NP-hard in general; solvers or heuristics in real tools). The simulator below checks inequalities 1-3 for a concrete schedule.

```python
# GCL feasibility check (802.1Qbv): can every scheduled flow meet its
# one-hop deadline, given gate windows, frame sizes, and the link rate?
LINK_BPS = 1_000_000_000          # 1 Gb/s full-duplex egress port
CYCLE_US = 1_000                  # GCL cycle, phase-locked to 802.1AS
L1_OVERHEAD = 20                  # 8 B preamble + 12 B interframe gap

# GCL: (start us, length us, gate mask, class label). "ctrl" opens twice
# per cycle (0 us and 500 us); the 940-1000 us closed gap doubles as the
# guard band before "ctrl" reopens.
GCL = [
    (  0,  40, 0b0100, "ctrl"),
    (100, 180, 0b1000, "video"),
    (350, 150, 0b0010, "avb-a"),
    (500,  40, 0b0100, "ctrl"),
    (540, 400, 0b0001, "be"),
]

# Scheduled flows: (name, class, frame bytes, frames per cycle, deadline us)
FLOWS = [
    ("ctrl-1",   "ctrl",   128, 4, 600),
    ("sensor-1", "ctrl",   256, 1, 700),
    ("video-1",  "video", 1000, 4, 825),
]

def wire_us(b):
    """Wire time of one frame including L1 overhead."""
    return (b + L1_OVERHEAD) * 8 / LINK_BPS * 1e6

def worst_wait_us(label):
    """Arrive just after the gate closes; wait until the next open."""
    wins = sorted((s, d) for s, d, m, lab in GCL if lab == label)
    opens = [s for s, _ in wins] + [wins[0][0] + CYCLE_US]
    closes = [s + d for s, d in wins]
    return max(o - c for o, c in zip(opens[1:], closes))

def class_demand_us(label):
    return sum(n * wire_us(b) for _, c, b, n, _ in FLOWS if c == label)

print(f"link {LINK_BPS/1e9:.0f} Gb/s, cycle {CYCLE_US} us, "
      f"L1 overhead {L1_OVERHEAD} B/frame")
print("window check (demand vs gate-open time per class):")
for lab in sorted({lab for _, _, _, lab in GCL}):
    opens = [s for s, x, m, l2 in GCL if l2 == lab]
    win = sum(x for s, x, m, l2 in GCL if l2 == lab)
    dem = class_demand_us(lab)
    if dem > 0:
        shown = "/".join(f"{s:>4}" for s in opens)
        print(f"  {lab:<6} opens at {shown} us, {win:>3} us total "
              f"| demand {dem:7.3f} us | {dem / win * 100:5.1f}% of window")

rows = []
for name, cls, b, n, deadline in FLOWS:
    wait = worst_wait_us(cls)
    ahead = sum(o * wire_us(ob) for nm, c, ob, o, _ in FLOWS
                if c == cls and nm != name)
    rows.append((name, wait, ahead, wire_us(b),
                 wait + ahead + wire_us(b), deadline))

print("\nflow feasibility (one-hop worst = wait + queue-ahead + own tx):")
for name, wait, ahead, tx, worst, deadline in rows:
    verdict = "PASS" if worst <= deadline else "FAIL"
    print(f"  {name:<9} wait {wait:7.3f} + ahead {ahead:6.3f} "
          f"+ tx {tx:6.3f} = {worst:8.3f} us  deadline {deadline:5d}  {verdict}")

max_be = wire_us(1522)
gap = CYCLE_US - max(s + d for s, d, m, lab in GCL)
print(f"\nguard band: closed gap before ctrl reopens = {gap} us, "
      f"max BE frame = {max_be:.3f} us -> "
      f"{'OK' if gap >= max_be else 'VIOLATED'}")
print("3-hop worst case, identical GCL per hop (conservative N x one-hop):")
for name, wait, ahead, tx, worst, deadline in rows:
    print(f"  {name:<9} {3 * worst:9.3f} us")
```

Real output:

```text
link 1 Gb/s, cycle 1000 us, L1 overhead 20 B/frame
window check (demand vs gate-open time per class):
  ctrl   opens at    0/ 500 us,  80 us total | demand   6.944 us |   8.7% of window
  video  opens at  100 us, 180 us total | demand  32.640 us |  18.1% of window

flow feasibility (one-hop worst = wait + queue-ahead + own tx):
  ctrl-1    wait 460.000 + ahead  2.208 + tx  1.184 =  463.392 us  deadline   600  PASS
  sensor-1  wait 460.000 + ahead  4.736 + tx  2.208 =  466.944 us  deadline   700  PASS
  video-1   wait 820.000 + ahead  0.000 + tx  8.160 =  828.160 us  deadline   825  FAIL

guard band: closed gap before ctrl reopens = 60 us, max BE frame = 12.336 us -> OK
3-hop worst case, identical GCL per hop (conservative N x one-hop):
  ctrl-1     1390.176 us
  sensor-1   1400.832 us
  video-1    2484.480 us
```

The verdicts read like a real design review. The control flows pass with 130+ us of margin because their class opens twice per cycle - halving the worst wait is worth more than widening one window. The video flow misses its deadline by 3.2 us despite using only 18% of its window: its single opening sits 280 us into the cycle, so the worst-case arrival eats 820 us of pure waiting. The fixes are the three levers a TAS designer always has - open the video gate twice, move the window earlier, or shorten the cycle - and each one trades deadline margin against guard-band overhead elsewhere in the schedule.

## Choosing between the shapers: CBS vs TAS

| Property | 802.1Qav CBS | 802.1Qbv TAS |
|---|---|---|
| Mechanism | Credit accumulator per queue | Time-gated queues (GCL) |
| Clock dependency | None (rate-based) | Full: 802.1AS phase sync required |
| What is bounded | Reserved rate + 1 max-frame interference per hop | Exact worst-case delay per hop |
| Guarantee type | Statistical-soft (rate) | Deterministic-hard (time) |
| Schedule effort | Configure two slopes, done | GCL design per port, network-wide coordination |
| Guard-band waste | None | Real (unless preemption enabled) |
| Best for | Audio/video streams, rate-limited control | Motion control, safety loops, tight jitter budgets |
| Origin / era | AVB, 2009 | TSN, 2015 |

In deployed networks they coexist: CBS queues run underneath for admitted AVB-style streams while TAS windows carve out the safety-critical classes.

## Shrinking the guard bands: 802.1Qbu + 802.3br frame preemption

The cost model of TAS changes completely when the port can interrupt a frame. IEEE 802.3br splits a physical MAC into an **express MAC (eMAC)** and a **preemptable MAC (pMAC)** - the *MAC Merge sublayer* interleaves their traffic on the wire. A preemptable frame is chopped into **mPacket fragments** (minimum 64 bytes, each carrying a Start-mPacket-Delimiter code and CRC protection); when an express frame becomes ready, the egress asserts a hold on the pMAC, the current fragment finishes, the express frame goes out, and the remainder continues as a continuation fragment.

- **Guard band math**: without preemption, the port must reserve one max frame (1522 B = 12.2 us at 1 Gb/s) before every express window; with preemption, one fragment (64 B = 0.512 us). On short cycles that is most of the TAS overhead gone.
- **Costs**: pMAC frames gain per-fragment overhead and reassembly buffering; receivers without MAC Merge support see the fragmented stream as garbage, so capability is negotiated via LLDP before a port enables preemption.
- **Layer split is deliberate**: 802.1Qbu (bridging side: hold requests, express/preemptable traffic classes) and 802.3br (physical side: MAC Merge, SMD codes, fragment minimums). Interviewers love asking which amendment does what - Qbu decides *when*, 3br decides *how*.

## Protecting the schedule at the edge: 802.1Qci (PSFP)

A GCL is only as safe as the frames entering it. **Per-Stream Filtering and Policing** gives every ingress port a three-stage pipeline:

1. **Stream filters** - match frames on source/destination MAC, VLAN ID, and priority, with optional flow-membership tests (stream identity).
2. **Flow meters** - per-stream token buckets that drop or downgrade frames exceeding a committed information rate.
3. **Stream gates** - per-stream ingress gates that only let frames through during configured intervals.

Together they enforce two invariants a schedule depends on: a rogue or misconfigured talker cannot exceed its reserved rate, and it cannot inject frames into classes whose gates are closed. The 2017 amendment is unspectacular on paper and non-negotiable in deployment - Qci is what makes it safe to plug a diagnostic laptop into a zonal backbone.

## Bulk-determinism shortcuts: 802.1Qch CQF and 802.1CB FRER

**Cyclic Queuing and Forwarding (Qch)** replaces per-flow GCLs with two ping-pong queues per class: frames received in cycle *i* are transmitted in cycle *i+1*, synchronized network-wide. Per-hop delay is bounded at roughly two cycles regardless of other traffic, guard bands disappear, and composition across hops is trivial - at the price of a fixed cycle everywhere on the path and double buffering. When deadlines are loose relative to the cycle, CQF is the low-effort member of the family; when they are tight, TAS with preemption wins.

**Frame Replication and Elimination (CB)** attacks the other failure mode: link loss. A FRER talker tags frames with a sequence number (R-Tag) and sends duplicates over two or more *member streams* on disjoint paths; sequence-recovery functions at merge points pass the first arrival and discard the rest. No retransmission, no head-of-line blocking - availability by redundancy instead of retry. The [companion page](./tsn-deterministic-networking.md) shows how DetNet generalizes this as PREOF at layer 3.

## Where the family ships

**Automotive zonal architectures.** Modern E/E platforms evolved from one ECU per function (distributed), to one per domain (powertrain / chassis / infotainment controllers), to **zonal**: a handful of zone controllers near the wire harness entry points, a central computer running the applications, and a multi-gigabit TSN Ethernet backbone between them. The backbone carries camera and radar streams, control loops, diagnostics, and OTA traffic on one cable plant; the TSN toolbox is the contract that lets them coexist - 802.1AS for the common time base, Qbv (+Qbu/3br) for sensor and control windows, Qci at every zone-controller ingress, CB on safety-relevant streams, Qcc/CNC for configuration. Domain controllers already used AVB for audio/video rings in the mid-2010s; zonal platforms made the full toolbox standard.

**Industrial automation.** The IEC/IEEE 60802 profile selects a defined subset of the toolbox (sync, TAS, preemption, policing, FRER, centralized configuration) and adds industrial-specific profiles for cyclic I/O. Above it sits **OPC UA over TSN**: OPC UA PubSub frames carry the controller-to-controller and controller-to-device payloads, and the TSN toolbox underneath carries their timing - which is how deterministic PLC traffic and IT traffic end up sharing one converged plant network without separated cabling. Field eXchange (OPC UA FX) defines the controller-to-controller interaction model on top.

## Linux tooling: the qdisc names, verified

The kernel implements the family as traffic-control disciplines (qdiscs). Names you will actually type:

| Standard | qdisc / tool | Key knobs |
|---|---|---|
| 802.1Qbv TAS | `tc-taprio` | `num_tc`, `map`, GCL entries, `base-time`, `cycle-time`, `full-offload`, `txtime-assist` |
| Launch time | `tc-etf` | `SO_TXTIME` socket option; qdisc/NIC enforces per-packet tx deadline |
| 802.1Qav CBS | `tc-cbs` | `idleslope`, `sendslope`, `hicredit`, `locredit` |
| Class scaffolding | `tc-mqprio` | priority-to-TC map; the substrate the others attach to |

`tc-taprio` with `full-offload` pushes the GCL into NIC hardware; with `txtime-assist` it pairs with `tc-etf` so software-emulated TAS still launches packets inside their windows. See [tc-taprio(8)](https://man7.org/linux/man-pages/man8/tc-taprio.8.html) for the schedule phase semantics (a `base-time` in the past starts at the next aligned cycle) and [tc-cbs(8)](https://man7.org/linux/man-pages/man8/tc-cbs.8.html) for the credit formulas quoted above.

## References

- [IEEE 802.1AS-2025 - Timing and Synchronization for TSN](https://standards.ieee.org/ieee/802.1AS/11968) - current revision of the gPTP substrate (foundational: 802.1AS-2020)
- [IEEE 802.1Qbv-2015 - Enhancements for Scheduled Traffic](https://standards.ieee.org/ieee/802.1Qbv/6068) - the time-aware shaper amendment
- [IEEE 802.3br-2016 - Interspersing Express Traffic](https://standards.ieee.org/ieee/802.3br/5814) - MAC Merge sublayer, mPacket fragments, preemption physical layer
- [IEEE 802.1CB-2017 - Frame Replication and Elimination for Reliability](https://standards.ieee.org/ieee/802.1CB/5703) - FRER, R-Tag, sequence recovery
- [tc-cbs(8) - Linux manual page](https://man7.org/linux/man-pages/man8/tc-cbs.8.html) - CBS credit formulas; see also [tc-taprio(8)](https://man7.org/linux/man-pages/man8/tc-taprio.8.html) and [tc-etf(8)](https://man7.org/linux/man-pages/man8/tc-etf.8.html)
