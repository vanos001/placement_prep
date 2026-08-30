# In-Band Network Telemetry: the INT Packet Walk, Modes, and Metadata Stack

Out-of-band telemetry watches the network from the outside: counters polled over SNMP, flow records exported after the fact, packet samples bounced to a collector. It answers *how much* traffic went where, but it cannot say what happened to one specific packet — which queue held it, for how long, and at which hop it started to hurt. In-band network telemetry (INT) inverts the plane: the packet itself carries a request for telemetry in its header, every switch along the path appends a small record of what it just did, and the receiver hands the accumulated stack to a collector. This page walks that packet hop by hop, dissects the metadata stack the P4.org INT specification actually puts on the wire, and compares the INT approach with the IETF's In Situ OAM and with passive telemetry. For the byte-budget and export-economics side of the same trade, see [In-Band Telemetry: INT, IOAM, and the Per-Hop Metadata Stack](./in-band-telemetry.md); for the parser silicon INT presupposes, see [P4 and the Programmable Data Plane](./p4-programmable-dataplane.md).

## Out-of-band telemetry and its blind spots

| Mechanism | What it observes | What it cannot tell you |
|-----------|------------------|-------------------------|
| SNMP / gNMI counter polling | Per-interface octet, packet, drop counters (tens of seconds granularity) | Anything per-packet or per-queue-instance; counters say *that* drops happened, never *whose* packets |
| NetFlow / IPFIX (RFC 7011) | Per-flow records assembled after packets leave | Per-hop queueing inside the fabric; records are built from observed traffic, not from switch internals |
| sFlow | Random 1-in-N packet samples forwarded to a collector | You sample headers, rarely the packet you needed, and never the queue state it experienced |
| TAP + packet sniffer | Full packets on one link, timestamped | Requires physical access per link and huge capture farms; sees wire order, not device internals |
| Active probes (ping, TWAMP) | Delay/loss for synthetic packets | Probes deliberately avoid the hot queues and lossy paths your real traffic suffered |

The arithmetic of polling makes those blind spots worse in practice. Counter polling at 30-second intervals integrates fine over steady load but glances right past a microburst that fills and drains a deep queue in 2 milliseconds, and flow records with 60-second idle timeouts cannot tell a loss-free flow from one that retransmitted quietly for half the interval. Sampling trades the integration problem for a probability problem — the rarer the event, the less likely it lands in the sample — which is exactly backwards for an operator chasing a 1-in-a-million stall.

The common thread: every out-of-band method observes the network *from outside the forwarding decision*. A sniffer sees a packet arrive late but cannot split that delay across five hops; an IPFIX record knows a flow was slow but not which device's egress queue caused it. The gap between "some flows are slow" and "hop 3, queue 0, on switch SW2, is holding packets 40 microseconds at a time" is exactly the gap in-band telemetry closes, and it closes it with per-packet, per-hop ground truth. The price is that the data plane itself must parse, act on, and grow the packet — which is why INT was born in the programmable-dataplane community (P4.org, 2015, per the spec's own history) rather than in the management-plane standards bodies.

## The packet walk: source, transit, sink

The INT specification defines three roles a node can play, and the walk below is the INT-MD mode ("embed data"), the classic hop-by-hop variant the spec treats as its default. The **INT source** (first switch in the telemetry domain) matches the flow against a watchlist, writes a 12-byte INT header plus its own metadata entry into the packet, and sets a Remaining Hop Count to bound the damage a forwarding loop could do. Every **transit hop** that matches reads the instruction bitmap, gathers the requested fields from its own pipeline (port IDs from the parser, queue occupancy from the traffic manager, timestamps from the device clock), **prepends** its entry to the stack, and decrements the Remaining Hop Count. The **sink** (last node in the domain) strips the whole INT construct before forwarding the payload and decides whether to report what it collected.

```text
 five-switch path, instruction bitmap asks each hop for: node ID + queue (id, occupancy)

              embed hdr+entry      prepend entry      prepend entry      prepend entry       strip & export
 SW1 (src)         SW2                SW3                SW4                SW5 (sink)
   |                 |                  |                  |                  |
   | [pkt]           |                  |                  |                  |
   |-- write 12B INT header + own entry -->              |                  |
   |            [pkt|H|SW1]             |                  |                  |
   |                 |-- prepend [SW2] -->                 |                  |
   |            [pkt|H|SW2|SW1]          |                  |                  |
   |                 |                  |-- prepend [SW3] -->                 |
   |            [pkt|H|SW3|SW2|SW1]         |                  |
   |                 |                  |                  |-- prepend [SW4] -->
   |            [pkt|H|SW4|SW3|SW2|SW1]      |        collector <-- report
   |                 |                  |                  |          (stack newest-hop-first)
   RHC: 5 -> 4       4 -> 3             3 -> 2             2 -> 1       receives RHC=1

 H = 12B INT metadata header; entries sit between header and payload; sink removes
 the header + stack, so the receiver sees an ordinary packet.
```

Two guards make this survivable in a real fabric. If the Remaining Hop Count reaches 0, the next node **must ignore the instructions, push nothing, and set the E bit** (max hop count exceeded) — the spec's defense against loops burning header space forever. And if a node cannot insert its entry without exceeding the *egress link MTU*, it must insert nothing at all and set the **M bit** rather than truncate the stack halfway; the spec notes corrective action (MTU reconfiguration, path MTU discovery participation) may be needed, since the M bit deliberately does not identify which hop skipped. These two bits are the first thing to check when a deployed stack comes back shorter than the path.

### Inside one transit hop

Matching the flow is the cheap part; gathering is where the architecture shows. The spec deliberately leaves open *how* a node measures its own fields — queue occupancy comes from the traffic manager at the egress port, hop latency from the device's own forwarding timing, TX utilization from link statistics — but every read must complete inside the same forwarding pass that carries the packet, or the entry would lie about the hop it describes. That constraint is why INT's natural habitat is the programmable pipeline described on [the P4 page](./p4-programmable-dataplane.md): a parser that can chase a variable-length stack plus registers fast enough to feed it are precisely the RMT machine's party tricks, and precisely what a fixed-function ASIC had to harden at tape-out.

One spec detail worth stealing for designs: the specification's own worked example requests exactly node ID + queue occupancy per hop — a `Hop ML` of 2 words — which is the configuration the demo below simulates. The same section lets the source embed *source-only* domain-specific metadata outside the per-hop budget, so a controller can tag packets with flow or policy context that transit hops never touch or pay for. Between the loose field semantics and these extensible fields, INT is less a fixed format than a contract template that each domain fills in.

## The metadata stack on the wire

The INT-MD metadata header is 12 bytes, followed by a stack of per-hop entries; each entry is a whole number of 4-byte words, and the header's `Hop ML` field (5 bits, maximum 31 words) fixes how long every hop's entry is. Transit hops may not change `Hop ML`, the instruction bitmap, or the domain-specific instruction fields — only the source configures the stack's shape.

```text
 INT-MD metadata header (12 bytes)                    entry (per selected instruction bit)
+--------------------------------------------------+   bit0  node ID                    4B
| Ver(4b) D(1b) E(1b) M(1b) R(12b)                 |   bit1  L1 ingress port(16b) +
| Hop ML(5b) | Remaining Hop Cnt(8b)               |         L1 egress port (16b)      4B
+--------------------------------------------------+   bit2  hop latency               4B
| Instruction Bitmap (16b) | Domain Spec. ID (16b) |   bit3  queue ID(8b) +
+--------------------------------------------------+         queue occupancy(24b)     4B
| DS Instruction (16b)     | DS Flags (16b)         |   bit4  ingress timestamp         8B
+--------------------------------------------------+   bit5  egress timestamp          8B
|  e_hop4 | e_hop3 | e_hop2 | e_hop1 |  payload -> |   bit7  egress TX utilization     4B
+--------------------------------------------------+   bit8  buffer ID(8b)+occupancy   4B
 (newest hop first: each hop prepends)                 bit15 checksum complement      4B
```

The instruction bitmap is the whole contract: one bit per baseline field, bits 0–14 standard, and each set bit costs every hop exactly 4 bytes of metadata — except bits 4–6 (timestamps and level-2 port IDs), which cost 8. The field definitions are deliberately loose about units: the spec defines hop latency as "time taken for the INT packet to be switched within the device" and queue occupancy as "the build-up of traffic in the queue (in bytes, cells, or packets) that the INT packet observes," and states that the exact semantics per device travel **out of band** (via a metadata-semantics YANG model) because a ToR ASIC and a SmartNIC will measure them differently. The bits between the bitmap and the wire are the next section's subject: something short must make this stack recognizable — and removable — by parsers that were never taught about it.

The `Ver` field is a compatibility contract of its own. This spec is version 2, and the rules are strict: a minor version may define 4-byte metadata that older nodes can still account for, while 8-byte metadata is reserved for the next major version — the spec spells out the consequence that a 2.0 node and a 3.0 node cannot share a domain once 3.0 introduces an 8-byte field, because the 2.0 node's parser would chase a stack shape it was never built for. Domains that mix vendor firmware versions hit exactly this wall, which is one more reason INT deployments live inside administratively coherent domains rather than spanning them.

## Getting INT to the wire: shims and encapsulations

An INT stack dropped raw between TCP and the payload would break every middlebox on the path, so the spec defines short shim headers that make the construct recognizable and skippable without understanding it. For ordinary L4 traffic, a 4-byte TCP/UDP shim sits between the transport header and the INT metadata: in the UDP case the packet is re-addressed to a reserved INT destination port while the *original* destination port is preserved inside the shim (alongside a next-protocol-type field), and the sink swaps the original port back before forwarding — the receiving application sees an untouched flow. For tunnel-heavy fabrics, INT rides as a GRE shim carrying type and total length (so a parser can skip the whole stack without parsing it), or as a VXLAN/Geneve option, which is the natural placement for overlay data centers. Whichever shim a domain picks, the spec strongly recommends picking exactly one: a mixed domain multiplies the parser cases every node must handle for zero benefit. None of this changes the metadata semantics — the shim exists purely to make an in-band parasite polite on networks that were never built for it.

## The spec's three modes: XD, MX, MD

"INT" is an umbrella; the specification distinguishes its modes by how much the packet itself is modified, and Figure 1 of the spec draws exactly this axis:

| Mode | Packet modification | Who exports | Lineage / inspiration |
|------|--------------------:|-------------|------------------------|
| **INT-XD** (eXport Data) | None | Every watchlisted hop exports reports | Aka "Postcard" in older Telemetry Report spec versions; inspired by NSDI'14 packet histories |
| **INT-MX** (eMbed instruct(X)ions) | Instruction header only | Source, every transit, and sink export individually | Inspired by IOAM Direct Export |
| **INT-MD** (eMbed Data) | Header + growing stack | Sink only (or intermediate report on MTU trouble) | Classic hop-by-hop INT; the spec's default mode |

The mode choice is really a choice about who pays the export fabric. INT-MD concentrates everything at one sink, which keeps the collector story simple but loses the stack entirely if the packet is dropped mid-path; INT-XD modifies nothing in-band and survives drops (each hop's postcard already left the switch), but every hop streams reports and a collector must stitch them per flow; INT-MX sits between — the packet carries only instructions, so it barely grows, while each node still exports its own metadata out-of-band. Production designs often pair modes: INT-MD for deep per-packet forensics on a sampled or triggered subset, INT-XD always-on for drop diagnosis (the sibling page's postcard row makes the same point from the budget side). Two spec-level details round out the picture. First, the modes share the instruction vocabulary — XD and MX reuse the watchlist and bitmap machinery, so a node that implements MD has most of what it needs for the others. Second, MX and MD support source-inserted domain-specific metadata via the header's `DS Instruction`/`DS Flags` fields, which is how a source smuggles per-flow context (tenant, test marker, policy class) to sinks or collectors without spending per-hop bytes; INT applied to synthetic probe traffic — cloned packets or purpose-built probes — rides the same machinery, which is how INT doubles as an active measurement tool.

## INT, IOAM, and passive telemetry compared

| | INT (P4.org spec v2.1) | IOAM (IETF RFC 9197) | Passive (sFlow / IPFIX) |
|--|------------------------|----------------------|-------------------------|
| Standards home | P4.org Applications WG | IETF (Standards Track) | RFC 3176 (sFlow, informational); IPFIX RFC 7011 |
| Metadata origin | Switch pipeline at line rate | Switch/encapsulating node, IETF-defined option types | Sampling or flow assembly after the fact |
| Packet modification | XD none / MX header / MD grows per hop | Pre-allocated trace (fixed), incremental trace (+4 octets per field per hop), edge-to-edge (endpoints only) | None |
| Field vocabulary | Instruction bitmap: node ID, port IDs, hop latency, queue/buffer occupancy, timestamps, TX utilization | Trace-Type data fields, fixed 4-octet each (except Opaque State Snapshot) | n/a — records, not in-band fields |
| Deployment scoping | INT domain of cooperating nodes; shim per encapsulation | Explicit encapsulating/transit/decapsulating node roles; deployment survey in RFC 9378 | Network-wide, no in-band cooperation needed |
| Drop forensics | MD loses the stack; XD survives | Direct exporting (RFC 9326) survives | Survives (samples/reports pre-exist) |

The honest reading of the table: IOAM is the standards-track reformulation of the same idea — scoped to a telemetry domain, with fixed-size 4-octet data fields, an IPv6 hop-by-hop option for its IPv6 encapsulation, and RFC 9326's direct exporting as its INT-MX counterpart — while passive telemetry remains the only option that needs nothing from the forwarding plane. The IETF even ships a deployment RFC for the idea — RFC 9378 is Informational and exists precisely to catalog the scoping and node-role choices operators make — which tells you the standards body considers IOAM deployable, not just standardized. Interoperability reality is grimmer than the table suggests: INT's field semantics are per-device out-of-band, IOAM requires every transit node in a domain to implement the option, and both inflate packets in their MD-like modes, so multi-vendor INT domains are rarer than single-vendor ones (a hyperscaler's fabric or a single-vendor campus, not the open Internet).

## Production realities: the bandwidth tax, sampling, and collector fan-in

The bandwidth tax is per-hop and per-packet, which is exactly why it compounds. A five-hop path with two 4-byte words per hop adds 44 bytes of overhead (12 header + 32 metadata) to every watchlisted packet — 5.5% on 800-byte flows but over 40% on 64-byte ACKs, and the M bit warns you when deeper stacks stop fitting under the egress MTU at all. Because the tax is proportional to how *interesting* the traffic is (congested, small-packet, high-rate flows are the ones you want telemetry on, and also the ones where added bytes hurt most), production systems almost never run INT on every packet: watchlists select the flow set, sampling or color-triggering selects packets within the set, and the sibling page's export-panel arithmetic shows why (a 12.8-Tbps switch at full rate generates roughly 32 GB/s of raw reports).

Collector fan-in is the second hidden cost, and it is mode-dependent. INT-MD funnels everything to per-domain sinks, so the sink becomes a stateful bottleneck that must strip, timestamp, and forward at line rate, then stream records to analytics; INT-XD inverts this into N hops × report rate of out-of-band traffic that a tier of collectors must join back into per-flow path views. The join itself is fiddly in ways demos hide: hop records arrive out of order, device semantics differ per platform (the spec says so explicitly), and the M bit means the stack you received may be silently shorter than the path. Treat INT as a *correlated signal* to be fused with counters and syslogs, not a self-contained truth database, and size the trigger path so that the interesting 0.01% of flows gets full stacks while the rest gets sampled postcards.

Sink placement is a design decision with failure modes of its own. A sink at each ToR localizes the stripping work but only sees paths that end at that rack; a sink at the fabric boundary sees whole paths but concentrates the work at fewer, bigger boxes; and the spec's intermediate-report option — a transit hop that hits the MTU wall may export what it has collected and start a fresh stack — blurs the two deliberately. Whatever the placement, the spec defines report *formats* rather than transport, so teams still choose between gRPC streams, message buses, or the vendor's own telemetry pipeline, and must version the collector's schema against the YANG-side field semantics — because the unit of queue occupancy is, ultimately, whatever the vendor says it is.

Every production design is therefore a set of levers traded against the same three costs — wire bytes, parser budget, export bandwidth:

| Lever | What it buys | What it costs |
|-------|--------------|---------------|
| Watchlist scope (which flows) | Predictable, bounded metadata volume | Misses flows outside the list |
| `Hop ML` / stack depth | Richer per-hop localization | MTU pressure, M-bit gaps, parser budget |
| Sampling rate (1-in-N) | Coverage at N× less export volume | Rare events vanish; needs long windows |
| Trigger-based coloring | Full stacks exactly on suspect flows | Trigger state, reaction latency |
| Mode choice (XD/MX/MD) | Drop forensics vs sink simplicity | Export fabric size vs stack loss on drop |
| Sink placement | Load spread vs path completeness | ToR sinks see partial paths; boundary sinks concentrate load |

## Executed demo: a 5-switch INT walk with congestion localization

The simulator below runs the packet walk from the diagram: SW1 sources a packet with an instruction bitmap asking for node ID + queue occupancy, SW2–SW4 prepend their entries from a fixed synthetic profile, and SW5 receives the stack as the sink. It then prints the exported stack and does the one analysis operators actually want from INT — pointing at the hop whose queue was full when the packet went by.

```python
# INT-MD walk of one packet across 5 switches (P4.org INT spec v2.1 semantics).
# Header: 12B fixed. Instruction bitmap: bit0 = node ID (4B), bit3 = queue ID (8b)
# + queue occupancy (24b) -> Hop ML = 2 words (8B per inserting hop).
FIXED_HDR, WORD = 12, 4
NODE_ID_BIT, QUEUE_BIT = 1 << 0, 1 << 3
INSTR_BITMAP = NODE_ID_BIT | QUEUE_BIT          # source's request to every hop
HOP_ML_WORDS = 2
REMAINING_HOPS = 5                              # Remaining Hop Count set by source

# Fixed synthetic profile: (name, role, node_id, egress_queue_id, queue_occupancy_bytes)
PATH = [
    ("SW1", "source",  0x0101, 0, 9_600),
    ("SW2", "transit", 0x0102, 0, 118_400),     # the congested hop
    ("SW3", "transit", 0x0103, 3, 29_600),
    ("SW4", "transit", 0x0104, 0, 6_400),
    ("SW5", "sink",    0x0105, None, None),     # sink strips; pushes nothing
]

stack, rhc = [], REMAINING_HOPS
print("walk: source writes 12B header + own entry; transits prepend; sink strips")
for name, role, node_id, qid, occ in PATH:
    if role == "sink":
        print(f"  {name} {role:<8}: strips {len(stack)} entries, exports report")
        break
    rhc -= 1
    stack.insert(0, (node_id, qid, occ))        # spec: each node PREPENDS its metadata
    print(f"  {name} {role:<8}: prepend {hex(node_id)}, queue {qid}={occ:>6}B, RHC-> {rhc}")

total = FIXED_HDR + len(stack) * HOP_ML_WORDS * WORD
print(f"\nwire: bitmap={INSTR_BITMAP:#06x}, HopML={HOP_ML_WORDS} words, "
      f"INT bytes={total} on this packet, RHC left={rhc}, E=0 M=0")

print("\nexported stack at sink (newest hop first):")
print(f"  {'pos':<4} {'node_id':<8} {'queue_id':<9} {'occupancy':>9}")
for pos, (node_id, qid, occ) in enumerate(stack, 1):
    print(f"  {pos:<4} {hex(node_id):<8} {qid:<9} {occ:>7}B")

import statistics
hot = max(stack, key=lambda e: e[2])
second = sorted(e[2] for e in stack)[-2]
med = statistics.median(e[2] for e in stack)
print(f"\ncongestion localization: max occupancy at {hex(hot[0])} (queue {hot[1]}, "
      f"{hot[2]}B)")
print(f"  = {hot[2] / second:.1f}x the 2nd-hottest hop, {hot[2] / med:.1f}x the median hop")
```

Real output:

```text
walk: source writes 12B header + own entry; transits prepend; sink strips
  SW1 source  : prepend 0x101, queue 0=  9600B, RHC-> 4
  SW2 transit : prepend 0x102, queue 0=118400B, RHC-> 3
  SW3 transit : prepend 0x103, queue 3= 29600B, RHC-> 2
  SW4 transit : prepend 0x104, queue 0=  6400B, RHC-> 1
  SW5 sink    : strips 4 entries, exports report

wire: bitmap=0x0009, HopML=2 words, INT bytes=44 on this packet, RHC left=1, E=0 M=0

exported stack at sink (newest hop first):
  pos  node_id  queue_id  occupancy
  1    0x104    0            6400B
  2    0x103    3           29600B
  3    0x102    0          118400B
  4    0x101    0            9600B

congestion localization: max occupancy at 0x102 (queue 0, 118400B)
  = 4.0x the 2nd-hottest hop, 6.0x the median hop
```

Reading the output the way an operator would: the sink's exported stack names SW2 as the bottleneck (118 KB observed in queue 0 — 4× the second-hottest hop), which is the entire value proposition of in-band telemetry in one line; out-of-band methods would have shown "some flow is slow" and left the localization to guesswork. In a real pipeline the sink joins this stack with its flow table — the 5-tuple plus a time window — and reports the path as a unit, which is where the per-device field semantics (bytes? cells? packets?) must be reconciled before the localization line is believed. Note also what the wire line says: 44 INT bytes on the packet, Remaining Hop Count of 1 left at the sink — had a sixth switch matched the watchlist after RHC hit 0, it would have pushed nothing and set the E bit, and had any hop's insertion breached egress MTU, that hop would have pushed nothing and set the M bit instead. HPCC (SIGCOMM 2019) is the canonical example of exactly this loop run continuously: per-hop queue and byte metadata riding on ACKs, consumed as a congestion signal (see [Data-Center TCP](./datacenter-tcp.md)).

## Interview questions

- **"sFlow and IPFIX are cheap and universal — when do you actually need INT?"** When the question is per-packet and per-hop: which queue held *this* packet, how long, at which switch. sFlow samples headers (not device internals) at 1-in-N; IPFIX assembles flow records after the fact; both are statistical and both are blind to per-hop queueing state. INT answers exactly, at the cost of data-plane support and the bandwidth tax; the design discussion is making the interviewer weigh "always-on approximate" against "triggered exact."
- **"A stack comes back from a 5-hop path with only 3 entries and no E bit. What happened?"** Check the M bit first: an egress-MTU breach makes a hop insert *nothing* (not a truncated entry) and flag M, so MTU inflation on one link produces silent, non-consecutive gaps. Then check for a non-INT middlebox stripping the shim, and for per-device watchlist mismatches (a hop matched no INT rule — Node IDs in the stack reveal which hop is missing). E is reserved for the Remaining-Hop-Count exhaustion case, so no E means space, not hop count.
- **"Design INT for a Clos fabric with a drop problem — which mode, and why?"** Pair them: INT-XD (postcards) always-on for the drop story, because a dropped packet's MD stack dies with it while each hop's postcard already left; and INT-MD on a triggered subset (queue-depth or loss triggers) for full-stack forensics. Budget accordingly: XD converts in-band bytes into per-hop export traffic with a collector join, MD concentrates at sinks, and the sibling page's arithmetic shows why neither survives full-rate without sampling.
- **"Why did the IETF standardize IOAM when INT already existed?"** INT is a P4.org dataplane spec — born from programmable switch silicon, precise about its bitmap and shims but loose about field semantics (units travel out-of-band per device). IOAM put the same idea on the standards track: explicit node roles, fixed 4-octet data fields, defined IPv6 encapsulation, and a deployment RFC. The interview-grade summary: INT proved feasibility in P4-programmable fabrics; IOAM is the interop-oriented, domain-scoped reformulation — and RFC 9326 gives IOAM its own export-based mode, so the mode taxonomy converges even if the encodings never will.

## Related pages and references

**Related:** [In-Band Telemetry: INT, IOAM, and the Per-Hop Metadata Stack](./in-band-telemetry.md) (wire-byte budgets, export fabric, and silicon limits — the economics half of this story), [P4 and the Programmable Data Plane](./p4-programmable-dataplane.md) (the parser/PHV budget INT runs into), [Programmable Networks](./programmable-networks.md) (the DPDK/XDP/eBPF survey context), [Data-Center TCP](./datacenter-tcp.md) (INT metadata consumed as a congestion signal).

1. P4.org Applications Working Group, *In-Band Network Telemetry (INT) Dataplane Specification*, Version 2.1, 2020-11-11 — <https://github.com/p4lang/p4-applications/blob/master/docs/INT_latest.pdf>
2. N. Handigol, B. Heller, V. Jeyakumar, D. Mazières, N. McKeown, "I Know What Your Packet Did Last Hop: Using Packet Histories to Troubleshoot Networks," USENIX NSDI 2014 — <https://www.usenix.org/conference/nsdi14/technical-sessions/presentation/handigol>
3. F. Brockners, S. Bhandari, T. Mizrahi (Eds.), "Data Fields for In Situ Operations, Administration, and Maintenance (IOAM)," RFC 9197, Standards Track, May 2022 — <https://www.rfc-editor.org/rfc/rfc9197.html>
4. F. Brockners, S. Bhandari, D. Bernier, T. Mizrahi (Eds.), "In Situ Operations, Administration, and Maintenance (IOAM) Deployment," RFC 9378, Informational — <https://www.rfc-editor.org/rfc/rfc9378.html>
5. H. Song, B. Gafni, F. Brockners, S. Bhandari et al., "In Situ Operations, Administration, and Maintenance (IOAM) Direct Exporting," RFC 9326, Standards Track, November 2022 — <https://www.rfc-editor.org/rfc/rfc9326.html>
6. M. Li, R. Miao, C. Liu et al., "HPCC: High Precision Congestion Control," ACM SIGCOMM 2019 — <https://doi.org/10.1145/3341302.3342085>
