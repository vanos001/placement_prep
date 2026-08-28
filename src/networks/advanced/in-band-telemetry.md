# In-Band Telemetry: INT, IOAM, and the Per-Hop Metadata Stack

Every telemetry system answers one question: **what happened to this packet?**
Counters (SNMP, NetFlow/IPFIX, sFlow) answer it statistically; active probes
(ping/TWAMP) answer it for synthetic packets that avoid hot queues. In-band
telemetry answers it **exactly**: the packet itself accumulates a per-hop
record of where it went, which queue it sat in, and how long each leg took —
paid for in wire bytes, parser silicon, and export bandwidth.

## Three placements of the metadata

```text
(1) Hop-by-hop insert (INT-MD, IOAM Incremental Trace)

  src --+         +--[hop1]--prepend entry1-->[hop2]--prepend-->[hop3]--->  sink
        | insert  |                                                       |
        v         |   packet grows: [hdr][e3][e2][e1] ... [hdr][e1]       v
   [INT hdr+e0]   |                                  sink strips stack, exports it

(2) Postcard (packet untouched, per-hop clone out-of-band)

  src ----[pkt]-->[hop1]---->[hop2]---->[hop3]---> dst
                    |            |           |
                    + report(flow,seq,ports,queue,ts)  each hop exports a
                      "postcard"; a collector stitches them into a path

(3) Edge-to-edge (IOAM Edge-to-Edge option)

  src --[pkt + E2E fields]----[transit: untouched]----[dst reads fields]
```
(3) costs zero per hop but sees endpoints only (delay, seq — no queueing).

| Property | Hop-by-hop insert (INT-MD / IOAM-Incr) | Postcard | Edge-to-edge (IOAM E2E) |
|---|---|---|---|
| In-band growth | +1 entry per hop | Constant | Constant |
| Who exports | Sink only | Every hop | Sink only |
| Survives packet drop | No (stack lost with packet) | Yes (pre-drop hops reported) | Partial |
| Collector fabric | Thin (one sink per domain) | Heavy (every hop streams) | Thin |

The drop row is the killer interview point: a dropped packet's hop-by-hop stack
dies with it — exactly the packet you needed to debug — while the postcard's
pre-drop reports already left the switch. Production INT deployments pair the
stack with an out-of-band report.

## The INT metadata stack on the wire (P4.org spec v2.1)

INT (defined in the P4.org *In-band Network Telemetry* specification) embeds a
shim between L4 and the payload. The v2.1 fixed header is **12 bytes**, and the
per-hop metadata length is measured in **4-byte words** (5-bit `Hop ML` field,
max 31 words = 124 bytes per hop). The header carries the `Ver`, `D`, `E`
(max hop count exceeded) and `M` (MTU exceeded) flags; a `Remaining Hop Count`
(8 bits, decremented per node that pushes an entry — at 0 a node stops and sets
`E`); and a 16-bit `Instruction Bitmap` selecting per-hop fields, one 4-byte
word each: bit0 Node ID, bit1 ingress/egress interface IDs, bit2 hop latency,
bit3 Queue ID + occupancy, bit4/5 timestamps (8 bytes each), bit8 buffer
occupancy. Each hop **prepends** its entry:

```text
[ Eth ][ IP ][ TCP ][ INT hdr | e_hop3 | e_hop2 | e_hop1 ][ payload ]
INT hdr (12B): Ver4 D1 E1 M1 R12 HopML5 RemHop8 + InstructionBitmap16
e_hopN (4 words): switch_id4, ports2+2, hop_latency4, queue4
                  (one 4B word per selected bitmap bit)
INT-MX variant: fixed size -- source+sink only, transit adds nothing
```

## IOAM: the standards-track sibling (RFC 9197)

IOAM ("In Situ OAM", RFC 9197) standardizes the same idea with IETF option
types, scoped to a **telemetry domain** (encapsulating, transit, decapsulating
nodes). Three option types matter:

| Option type | Who writes | Growth |
|---|---|---|
| Pre-allocated Trace | Transit nodes fill pre-indexed slots | Fixed at encapsulation |
| Incremental Trace | Transit nodes push node data | +4 octets per field per hop |
| Edge-to-Edge | Encapsulator + decapsulator only | Constant |

RFC 9197 is strict about field sizes: each node data field selected by the
Trace-Type bitmap **MUST be 4 octets** (the only variable-length escape is the
Opaque State Snapshot), and a transit node populates *either* the pre-allocated
*or* the incremental option — never both. Encapsulation lives one layer up:
IPv6 carries IOAM in a Hop-by-Hop Options header (RFC 9486), and the deployment
survey (RFC 9378) documents use cases from data-center fabrics to **SRv6
networks**, where IOAM rides next to the Segment Routing Header (see
[SRv6](./srv6.md) for the SRH format and its stack-depth limits). Direct
exporting (RFC 9326) is IOAM's answer to the postcard: an
`IOAM-Transport-Option` marks selected packets so nodes **export** their data
out-of-band instead of growing the in-band stack; its aggregation option
pre-aggregates fields on the wire to cut export volume.

## Executed demo: header-space and export-volume budget

The two hard budgets of in-band telemetry are **header space vs MTU** and
**metadata generation rate vs export capacity**. The model uses the INT v2.1
constants (12-byte fixed header, 4-byte words, the spec's own MTU differential
formula `HopML*4*Hops + 12`) and RFC 9197's 4-octet data fields.

```python
# INT/IOAM in-band metadata budget model.
# P4.org INT v2.1: fixed INT header 12B, per-hop metadata in 4B words
# (Hop ML max 31); MTU differential = HopML*4*Hops + 12 (spec 5.7).
# RFC 9197: IOAM trace node data fields are 4 octets each.
FIXED_INT_HDR, WORD = 12, 4                 # INT fixed header, word size
IOAM_TRACE_HDR, POSTCARD_INBAND, MTU = 12, 8, 1500

def max_hops(budget, per_hop, fixed):
    """Largest n with fixed + n*per_hop <= budget."""
    return (budget - fixed) // per_hop if budget >= fixed else -1

print("A. In-band byte budget vs MTU (MTU=%d, headroom=packet size)" % MTU)
h1 = "mode                                    per-hop  8 hops  16 hops  max-hops@1500  max@900"
print(h1); print("-" * len(h1))
rows = [
    ("INT-MD, spec example (node id + queue)", 2 * WORD, FIXED_INT_HDR),
    ("INT-MD, +ports+hop-latency (4 words)",   4 * WORD, FIXED_INT_HDR),
    ("INT-MD, worst-case Hop ML (31 words)",  31 * WORD, FIXED_INT_HDR),
    ("IOAM incremental trace, 2 data fields",  2 * WORD, IOAM_TRACE_HDR),
    ("IOAM incremental trace, 5 data fields",  5 * WORD, IOAM_TRACE_HDR),
]
for name, per_hop, fixed in rows:
    print("%-39s %5d B/h %7d %8d %14d %8d" % (name, per_hop,
          fixed + 8 * per_hop, fixed + 16 * per_hop,
          max_hops(MTU, per_hop, fixed), max_hops(900, per_hop, fixed)))
print("%-39s %5d B   %7d %8d %14s %8s" % ("Postcard (constant in-band trigger)",
      POSTCARD_INBAND, POSTCARD_INBAND, POSTCARD_INBAND, "inf", "inf"))

print("\nB. Overhead of 16-hop INT-MD (4-word entries) on small packets")
for pkt in (1500, 900, 256, 64):
    added = FIXED_INT_HDR + 16 * 4 * WORD
    print("  pkt=%4dB  INT bytes=%3d  total=%4d  overhead=%5.1f%%" %
          (pkt, added, pkt + added, 100.0 * added / pkt))

print("\nC. Metadata generation rate at one 12.8 Tbps switch (800B avg pkt)")
PPS = int(12.8e12 / 8 / 800)                # ~2.0 Gpps
for label, frac in (("full-rate (1:1)", 1.0), ("sampled 1:1000", 1e-3),
                    ("triggered, top 0.01% of flows", 1e-5), ("sampled 1:1e6", 1e-6)):
    gbps = PPS * frac * 4 * WORD * 8 / 1e9  # 4-word (16B) INT entry
    print("  %-31s %8.3f Gbps raw  ~%6.3f GB/s  single-broker OK: %s" %
          (label, gbps, gbps / 8, "yes" if gbps / 8 <= 1.0 else "no"))

print("\nD. Spec prescription: MTU differential = HopML*4*Hops + fixed(12)")
print("   16 hops x 4 words x 4B + 12 = %d bytes of headroom required" %
      (16 * 4 * WORD + FIXED_INT_HDR))
```

Real output of `python3 int_budget.py`:

```text
A. In-band byte budget vs MTU (MTU=1500, headroom=packet size)
mode                                    per-hop  8 hops  16 hops  max-hops@1500  max@900
----------------------------------------------------------------------------------------
INT-MD, spec example (node id + queue)      8 B/h      76      140            186      111
INT-MD, +ports+hop-latency (4 words)       16 B/h     140      268             93       55
INT-MD, worst-case Hop ML (31 words)      124 B/h    1004     1996             12        7
IOAM incremental trace, 2 data fields       8 B/h      76      140            186      111
IOAM incremental trace, 5 data fields      20 B/h     172      332             74       44
Postcard (constant in-band trigger)         8 B         8        8            inf      inf

B. Overhead of 16-hop INT-MD (4-word entries) on small packets
  pkt=1500B  INT bytes=268  total=1768  overhead= 17.9%
  pkt= 900B  INT bytes=268  total=1168  overhead= 29.8%
  pkt= 256B  INT bytes=268  total= 524  overhead=104.7%
  pkt=  64B  INT bytes=268  total= 332  overhead=418.8%

C. Metadata generation rate at one 12.8 Tbps switch (800B avg pkt)
  full-rate (1:1)                  256.000 Gbps raw  ~32.000 GB/s  single-broker OK: no
  sampled 1:1000                     0.256 Gbps raw  ~ 0.032 GB/s  single-broker OK: yes
  triggered, top 0.01% of flows      0.003 Gbps raw  ~ 0.000 GB/s  single-broker OK: yes
  sampled 1:1e6                      0.000 Gbps raw  ~ 0.000 GB/s  single-broker OK: yes

D. Spec prescription: MTU differential = HopML*4*Hops + fixed(12)
   16 hops x 4 words x 4B + 12 = 268 bytes of headroom required
```

Read the panels together: a 16-hop path with a 4-word entry needs **268 bytes
of MTU headroom** — the spec's own prescription — and on 64-byte ACK-sized
packets the metadata is **4x the payload**. Full-rate telemetry from one
12.8 Tbps switch generates **32 GB/s** of raw reports — more than a Kafka
broker comfortably ingests (~1 GB/s). That is the case for sampling.

## Export paths: gRPC, Kafka, and the two-tier pipeline

The INT/telemetry-report specs define the *format* of reports; transport is an
architecture decision:

```text
switch ASIC --(gRPC/protobuf)--> collector tier --(Kafka)--> analytics
                                       |                        |
                            dedupe, filter, sample    flow join, path reconstruction
```

- **gRPC streaming** is the hop-1 transport: persistent HTTP/2 streams, small
  per-report overhead, backpressure — pairing with the gNMI/gRPC telemetry
  channels used elsewhere on the box.
- **Kafka** is the hop-2 buffer: collectors fan out to stream processors that
  join reports into path views. Panel C's 0.26 Gbps at 1:1000 sampling fits a
  broker; full-rate does not — collectors pre-aggregate before producing.
- **Direct export (RFC 9326)** moves the fan-out into the network: nodes export
  their own data for *marked* packets, so no single sink must drain every stack.

## Switch-silicon limits: why Hop ML caps at 31

Every byte of a growing in-band stack must be **parsed and reassigned by every
hop's ingress pipeline**, and fixed-function ASICs budget parser bits and PHV
(packet header vector) containers once at tape-out. A variable-length stack
conflicts with a fixed parser schedule: hardware either reserves worst-case
space (wasting PHV on ordinary packets) or **recirculates** INT packets through
the pipeline a second time, halving effective bandwidth while adding latency to
exactly the packets being measured. The 5-bit `Hop ML`
(max 31 words) and 8-bit hop counter bound what silicon can be assumed to
handle — the same story as SRv6's 16-byte-per-segment SRH stack (see
[SRv6](./srv6.md), including uSID compression). Programmable pipelines make the
budget explicit instead: a P4 parser decides how deep a stack it will chase —
INT's original habitat (see [P4 and the Programmable Data
Plane](./p4-programmable-dataplane.md) for parser/MAU costs and Tofino's
discontinuation, which pushed INT-style work toward NICs). At the MTU end, the
`M` bit flags hops that skipped insertion rather than overflow egress MTU.

## Sampling, triggering, and the case against full-rate

| Strategy | What you get | What it costs | Typical trigger |
|---|---|---|---|
| Sampled INT (1:N) | Statistical path view | Misses rare events | Hash-based or random |
| Triggered (iFIT-style) | Full detail on suspect flows | Filter state, trigger latency | SRv6 policy, queue depth, ECN, loss |
| Postcard on every hop | Drop forensics | Per-hop export fabric | Always-on, sampled flows |
| Active probes (TWAMP) | Independent ground truth | Probes avoid congestion | Scheduled |

The iFIT framework (in-situ Flow Information Telemetry) popularized the
**color-triggered** pattern used with SRv6 policies: only controller-selected
flows get colored packets, and only colored packets export — aligning detail
with suspicion instead of with traffic volume. HPCC takes the opposite point on
the same spectrum: INT metadata rides on *acknowledgments* as a congestion
signal (see [Data-Center TCP](./datacenter-tcp.md)). Two failure modes: in-band
telemetry **amplifies congestion** (adding bytes to already-queued flows), and
sink-collected stacks **vanish with dropped packets** — pair the stack with
postcards or direct export before trusting it for loss debugging.

## Interview angles

- "INT makes the network observable — why isn't it everywhere?" Answer with
  the three budgets: 268 B MTU headroom, parser/PHV cost, 32 GB/s export.
- "Your INT metadata disappeared at hop 9." Check the `M` bit (MTU), `E` bit
  (hop count), parser limits, and whether a middlebox stripped the shim.

## Related pages and references

**Related:** [P4 and the Programmable Data Plane](./p4-programmable-dataplane.md)
(the parser budget INT runs into), [SRv6: Segment Routing over IPv6](./srv6.md)
(the other growing-header stack, and the SRv6+IOAM path), [Data-Center
TCP](./datacenter-tcp.md) (INT as congestion signal, latency visibility),
[Modern Network Architecture](./modern-network-arch.md) (survey level).

- [RFC 9197: Data Fields for In Situ OAM (IOAM)](https://www.rfc-editor.org/rfc/rfc9197.html)
- [RFC 9326: IOAM Direct Exporting and Aggregation](https://www.rfc-editor.org/rfc/rfc9326.html)
- [P4.org In-band Network Telemetry (INT) Dataplane Specification, v2.1](https://github.com/p4lang/p4-applications/blob/master/docs/INT_latest.pdf)
- [HPCC: High Precision Congestion Control (INT in the data plane), Li et al., SIGCOMM 2019](https://doi.org/10.1145/3341302.3342085)
- [In-band Network Telemetry: A Survey, Tan et al., Computer Networks 2021](https://doi.org/10.1016/j.comnet.2020.107763)
