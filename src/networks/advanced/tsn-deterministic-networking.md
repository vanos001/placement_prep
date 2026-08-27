# TSN & Deterministic Networking: When "Best Effort" Is Not Good Enough

Standard Ethernet gives every frame a promise of roughly this shape: the frame will probably arrive, and its delay will probably be small. Queues are FIFO, scheduling is opportunistic, and congestion produces loss or jitter that applications must absorb. That contract is fine for file transfers and web traffic, and hopeless for a motion-control loop that needs a sensor sample every 250 us, an audio interface moving sample-accurate streams, or a robot controller whose worst-case deadline - not average delay - determines whether it ships. Time-Sensitive Networking (TSN) is the IEEE 802.1 answer: a toolbox of standards that turn a switched Ethernet into a deterministic network with **bounded latency, bounded jitter, and zero congestion loss** for selected streams, while ordinary traffic keeps flowing on the same wires.

The key reframing: best-effort networks manage *bandwidth*; deterministic networks manage *time*. Once every bridge shares a clock and agrees on when each queue may transmit, latency stops being a statistical property and becomes a schedule.

## What breaks without it

| Workload | Typical requirement | Best-effort Ethernet behavior |
|----------|--------------------|-------------------------------|
| Industrial motion control | 100 us - 1 ms cycle, jitter << 10% | Microseconds-to-milliseconds jitter under load; rare loss unacceptable |
| Pro audio / video (AVB lineage) | < 10 ms end-to-end, no buffer underruns | Occasional dropouts under bursts; per-hop queues add variable delay |
| Automotive ADAS / zonal | Camera, radar, control streams on one backbone | Priority alone (PCP/VLAN) cannot bound worst case; interference unbounded |
| 5G fronthaul (eCPRI) | ~100 us one-way, tightly jittered | Statistical multiplexing breaks radio timing budgets |
| Substation / grid protection | 4 ms transfer-trip messages | Cannot coexist safely with ordinary IT traffic |

A Diffserv codepoint or a VLAN priority tells switches *which* queue to favor; it cannot tell them *when* the frame will arrive. Every TSN mechanism below is ultimately a way to convert "priority" into a provable time bound.

## The standards toolbox

| Standard | Name (year) | Mechanism |
|----------|-------------|-----------|
| IEEE 802.1AS-2020 | Timing and Synchronization (gPTP) | Time sync across every bridge (originally 802.1AS-2011) |
| IEEE 802.1Qav-2009 | Forwarding & Queuing (now in 802.1Q-2018) | Credit-Based Shaper (CBS), classes A/B |
| IEEE 802.1Qbv-2015 | Enhancements for Scheduled Traffic | Time-Aware Shaper: time-gated egress queues (GCL) |
| IEEE 802.1Qbu-2016 + IEEE 802.3br-2016 | Frame Preemption + Interspersing Express Traffic | Preempt a lower-priority frame mid-transmission; shrinks guard bands |
| IEEE 802.1Qci-2017 | Per-Stream Filtering and Policing | Ingress gates + flow meters protect the schedule |
| IEEE 802.1Qca-2015 | Path Control and Reservation | Explicit path setup for streams (IS-IS extensions) |
| IEEE 802.1CB-2017 | Frame Replication and Elimination (FRER) | Send duplicates over disjoint paths; drop at merge |
| IEEE 802.1Qcc-2018 | Stream Reservation Protocol enhancements | Talker/Listener declarations, centralized network configuration (CNC) |
| IEEE 802.1Qch-2017 | Cyclic Queuing and Forwarding (CQF) | Ping-pong queues per cycle: delay = 2 cycles per hop |
| IEEE 802.1Qcp-2018 | Asynchronous Traffic Shaping (ATS) | Shaping for non-synchronized traffic |
| IEEE 802.1BA-2011 | AVB Systems Profile | The pro-audio baseline profile that started it all |
| IEEE 802.1CM-2018 | TSN Profile for Fronthaul | Carrier profile for 5G radio fronthaul |

The AVB amendments (Qat/Qav/AS/BA) shipped 2009-2011; Qbv and friends (2015-2017) generalized to industry; most were folded into the 802.1Q-2018 bridge revision while retaining their amendment numbers as names. The IEC/IEEE 60802 joint profile now standardizes the industrial-Automation subset, and the [802.1 TSN task group page](https://1.ieee802.org/tsn/) tracks the maintenance tasks (ASdm, CBcv, and so on).

## Prerequisite one: a shared clock

Every mechanism below assumes all bridges and end stations agree on time to within microseconds - that is IEEE 802.1AS, the gPTP profile of PTP: every port timestamped in hardware, every bridge regenerating the sync so hop delay never accumulates as it would in NTP. Without it, Qbv gates on different switches drift apart and the schedule is fiction. The protocol mechanics, PTP hardware clocks (PHC), and Linux tooling (ptp4l, ts2phc) are covered in [Time Synchronization](./time-synchronization.md); TSN's new requirement beyond ordinary PTP is **phase alignment**: not just a common rate (syntonization) but a common definition of "now", because gate windows are offsets from a shared cycle boundary.

## Prerequisite two: shaping, the gentle tool (802.1Qav)

The Credit-Based Shaper predates time gating. Each traffic class gets `idle_slope` (a reserved bit rate); its credit accrues while the queue waits and drains while it transmits, and a frame may only start when credit is non-negative. The result is smooth, rate-limited transmission with bounded interference, at hardware cost near zero - which is why AVB (Class A: delivery within 2 ms across seven bridges; Class B: 50 ms) was deployable on early silicon. CBS bounds *average* behavior, not worst case: a burst from another talker still delays you by up to the max frame time, per hop. When even that residual is too much, you need gates on a clock - the token-bucket generalization behind this whole family is covered in [Traffic Shaping](./traffic-shaping.md).

## The time-aware shaper: 802.1Qbv

TAS gives each egress queue a repeating **gate control list (GCL)**: a cycle (say 1 ms) divided into slots; per slot, an 8-bit mask says which queue gates are open, and for how long, synchronized to the 802.1AS clock. A scheduled (ST) frame waits at most one cycle, transmits uncontended, and its delay per hop is computable by hand.

```text
    egress port timeline, one 1 ms GCL cycle on 1 Gb/s (4 queues: ST, A, B, BE)

    |<------- 826 us ------>|<-- 50 us -->|<-- 100 us -->|<- 12.2 us ->|<- 12 us ->|
    BE (gate mask 0001)     B (0010)      A (0100)       guard band    ST (1000)
                                                                      |
    cycle wraps: the NEXT cycle's ST window opens exactly at t = 1 ms,
    phase-locked to the 802.1AS grandmaster. The guard band exists because
    a 1522-byte best-effort frame (12.2 us at 1 Gb/s) already in flight
    cannot be stopped - unless 802.3br lets the port preempt it, which
    shrinks the guard to ~0.5 us (64-byte fragment overhead).
```

Sizing the schedule is arithmetic on wire time:

```python
# Time-aware shaper (802.1Qbv) arithmetic: gate-slot sizing, guard bands,
# and worst-case end-to-end delay on a multi-hop TSN path.
#
# Model: a talker emits one fixed-size frame per cycle on a stream whose
# class gate opens once per cycle. A lower-priority frame in flight when
# the gate closes forces a guard band; 802.3br preemption shrinks it.
LINK_BPS = 1_000_000_000          # 1 Gb/s full duplex
CYCLE_US = 1_000                  # 1 ms gate-control-list cycle
BE_MAX_BYTES = 1_522              # max interfering ordinary Ethernet frame
PREEMPT_OVERHEAD_B = 64           # residual guard with 802.3br (mPacket fragments)

def slot_us(payload_bytes, guard_bytes):
    """Time the express gate must stay open for one frame + guard band."""
    return (payload_bytes + guard_bytes) * 8 / LINK_BPS * 1e6

frame = 1_500                     # stream under design
gcl = [                           # (name, duration us) for the design check
    ("ST (Qbv express)", slot_us(frame, 0)),
    ("guard band, no preemption", slot_us(0, BE_MAX_BYTES)),
    ("guard band, with 802.3br", slot_us(0, PREEMPT_OVERHEAD_B)),
]
print(f"link {LINK_BPS/1e9:.0f} Gb/s, GCL cycle {CYCLE_US} us "
      f"({CYCLE_US * LINK_BPS / 8 / 1_000_000:.0f} bytes of wire time per cycle)")
for name, dur in gcl:
    print(f"  {name:<28} {dur:7.3f} us")

slot_no_pre = slot_us(frame, BE_MAX_BYTES)
slot_pre = slot_us(frame, PREEMPT_OVERHEAD_B)
print(f"\nper-hop worst case, one frame per cycle:")
print(f"  preemption off : {slot_no_pre:6.3f} us slot "
      f"({slot_no_pre / CYCLE_US * 100:.2f}% of cycle)")
print(f"  preemption on  : {slot_pre:6.3f} us slot "
      f"({slot_pre / CYCLE_US * 100:.2f}% of cycle)")

# Cyclic Queuing and Forwarding (802.1Qch) bound: ping-pong queues give
# delay = 2 cycles per bridge hop, independent of other traffic.
print("\nCQF (802.1Qch) worst-case end-to-end latency, 2 cycles per hop:")
for hops in (1, 2, 3, 4, 5):
    print(f"  {hops} hops: {2 * hops * CYCLE_US / 1000:.0f} ms")
```

Real output:

```text
link 1 Gb/s, GCL cycle 1000 us (125000 bytes of wire time per cycle)
  ST (Qbv express)              12.000 us
  guard band, no preemption     12.176 us
  guard band, with 802.3br       0.512 us

per-hop worst case, one frame per cycle:
  preemption off : 24.176 us slot (2.42% of cycle)
  preemption on  : 12.512 us slot (1.25% of cycle)

CQF (802.1Qch) worst-case end-to-end latency, 2 cycles per hop:
  1 hops: 2 ms
  2 hops: 4 ms
  3 hops: 6 ms
  4 hops: 8 ms
  5 hops: 10 ms
```

The design tension is visible in the numbers: guard bands nearly double the ST slot cost per hop until preemption hardware reclaims them, and short cycles (tight latency) waste more of the link on guard bands and slot quantization. CQF sidesteps guard bands entirely - frames only move queue-to-queue on cycle boundaries, buying a clean 2-cycles-per-hop bound at the price of doubled buffers and a cycle time that must fit every hop identically.

## The formal view in one paragraph

Network calculus makes these bounds algebra. Model a talker by an **arrival curve** (e.g., leaky-bucket `alpha(t) = b + r*t`) and each hop by a **service curve** `beta(t) = R*(t - T)+` (positive part: rate R after latency T); then the per-hop delay is bounded by the horizontal deviation `D <= T + b/R`, and backlogs by the vertical one. Concatenating hops composes service curves, so an n-hop path gets `D_total <= n*T + b/R` for CBS-style service, or `2n` cycles under CQF. Le Boudec & Thiran's *Network Calculus* (Springer LNCS 2050, full text on the [book site](https://leboudec.github.io/netcal/)) is the standard reference; TSN's contribution over the theory is silicon that actually implements the service curves.

## Reliability: FRER (802.1CB)

Bounded delay means bounded retransmission time - so TSN avoids retry and duplicates instead. A FRER talker sends each frame twice (or more) with a sequence number (R-Tag) over disjoint paths; bridges replicate or eliminate by sequence number, and the merge point passes the first copy and drops the rest. Combined with 802.1Qca path control (which pins the disjoint routes), a stream survives any single link cut with zero retransmission delay - the network-calculus bound now covers failure, not just scheduling.

## Coexistence and control planes

- **SRP / MSRP (802.1Qat)**: talkers declare streams (destination MAC, VLAN, class, bandwidth); bridges admit them only if the hop can still honor its reservations - admission control, the part plain Ethernet never had. **802.1Qcc** adds a centralized CNC and a NETCONF/YANG management model for larger networks.
- **802.1Qci** is the enforcer: ingress gates and per-stream flow meters mean a misbehaving or rogue talker physically cannot inject frames into someone else's time window. Without Qci, one unconfigured device's broadcast storm can defeat the whole schedule.
- Ordinary traffic keeps its queues (the BE gate above), with reservations capped so best-effort always retains link share; CBS classes A/B still run underneath for AVB-style streams that need rate shaping, not gates.

## DetNet: the same problem one layer up

TSN is IEEE 802.1 (bridged Ethernet). The IETF's **Deterministic Networking (DetNet)** working group asked what changes for routed IP/MPLS networks, and RFC 8655 defines the architecture: a DetNet data plane layered over existing IP/MPLS, carrying per-flow resource allocation and - the new acronym - **PREOF**: Packet Replication, Elimination and Ordering Functions (FRER's ideas generalized to layer 3). A DetNet network can hand a subnetwork segment to an 802.1 TSN island and map its flows onto TSN streams; the documents are explicit that TSN is one subnetwork technology DetNet composes with. Rule of thumb: same determinism math, different layer, different control plane (no GCLs on a router - DetNet over MPLS leans on shaping and explicit routes instead).

## Where it ships

- **Automotive**: domain controllers consolidated into zonal gateways with multi-gig Ethernet backbones; camera, radar, display, and control streams share one harness, with Qbv + CB + AS as the backbone contract and Qci policing every ingress port. Wiring weight is the real driver - one deterministic network replaces dozens of dedicated buses.
- **Pro audio/video**: the original AVB market (802.1BA profile): mixing consoles, stage boxes, audio interfaces trading word-clock-accurate streams over Cat6 with consumer-grade switches.
- **Industrial automation**: the IEC/IEEE 60802 profile selects the toolbox (AS, Qbv, Qbu/3br, Qci, CB, Qcc) for PLC-class determinism; OPC UA FX (Field eXchange) profiles controller-to-controller traffic over it, letting deterministic control traffic and IT traffic share one converged plant network.
- **5G fronthaul**: 802.1CM profiles TSN for the radio-unit-to-distributed-unit link, where radio timing tolerances translate directly into latency/jitter budgets.

## Linux support and hardware reality

Linux implements most of the toolbox in the qdisc layer (see [tc](../../linux/kernel/networking/tc.md) for qdisc fundamentals):

- `tc-taprio` - the software model of 802.1Qbv: `num_tc` traffic classes, a `map` from priority to class, and the GCL as schedule entries with `base-time`/`cycle-time`. The man page is explicit about phase: *"If 'base-time' is a time in the past, the schedule will start at base-time + (N * cycle-time) where N is the smallest integer so the resulting time is greater than 'now'"* - you never wait for a full epoch, the kernel picks the next aligned cycle. `txtime-assist` mode lets the qdisc work with the `etf` qdisc, and `full-offload` pushes the GCL into the NIC so the CPU sleeps through empty slots.
- `tc-etf` - Earliest TxTime First, pairing with the `SO_TXTIME` socket option: applications stamp each packet with a deadline and the qdisc/NIC enforces the launch time.
- `tc-cbs` - 802.1Qav credit-based shaper (`idleslope`, `sendslope`, `hicredit`, `locredit`).
- `mqprio` - the traffic-class scaffolding everything else attaches to.

Hardware expectations: a PTP hardware clock per port (802.1AS timestamps), NIC launch-time transmit (Qbv), MAC Merge sublayer (802.3br preemption), and - the non-negotiable - every bridge on the path must implement the same mechanisms. TSN is a chain: one legacy office switch between two compliant bridges restores best-effort for every stream crossing it. That deployment fact, more than any single standard, is what TSN engineers spend their time on.

## References

- [IEEE 802.1 Time-Sensitive Networking Task Group](https://1.ieee802.org/tsn/) - official status of every standard named above
- J.-Y. Le Boudec and P. Thiran, [Network Calculus](https://leboudec.github.io/netcal/) - arrival/service curves and deterministic bounds (LNCS 2050)
- [RFC 8655: Deterministic Networking Architecture](https://www.rfc-editor.org/rfc/rfc8655.html) - the DetNet framework, PREOF, TSN as subnetwork
- [tc-taprio(8) - Linux](https://man7.org/linux/man-pages/man8/tc-taprio.8.html) - 802.1Qbv qdisc; see also [tc-etf(8)](https://man7.org/linux/man-pages/man8/tc-etf.8.html)
- [Kernel timestamping documentation](https://docs.kernel.org/networking/timestamping.html) - hardware timestamps and SO_TXTIME
