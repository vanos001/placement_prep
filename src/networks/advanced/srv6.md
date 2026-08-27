# SRv6: Segment Routing over IPv6

Classic IP forwarding is destination-based: each router independently picks a next hop, and the
path a packet takes is emergent. Segment Routing (SR, RFC 8402) inverts the model: the *source*
encodes the path into the packet, and each named waypoint — a *segment* — executes its
instruction and hands the packet onward. SRv6 is the IPv6 instantiation: segments are 128-bit
IPv6 addresses riding in a Segment Routing Header (SRH, RFC 8754). This page walks the wire
format, the RFC 8986 programming model, uSID compression, TI-LFA, SR policies, and the
operational wrinkles (overhead, MTU, SID depth, brownfield). For the label-based sibling read
[MPLS](./mpls.md); for Linux dataplane commands see
[SRv6 on Linux](../../linux/kernel/networking/segment-routing.md).

## Why put the path in the packet

MPLS traffic engineering with RSVP-TE installs per-LSP state on *every* transit router: 10K
LSPs means 10K paths the core must signal, refresh, and repair. SR collapses that state to the
edge — the core routers only need their own local SIDs (one per node, a handful per link), and
the path itself travels with the packet. Three consequences matter operationally:

1. **Zero signaling for new paths.** Compose a path from existing SIDs; no per-flow handshake,
   no refresh timers, no graceful-restart drama.
2. **Per-packet granularity.** Different packets can carry different segment lists — slice
   traffic, replicate, steer.
3. **The network stays loop-free underneath.** Locators are ordinary IGP routes
   (IS-IS/OSPFv3); a broken path fails over via normal routing plus TI-LFA repair (below).

## The SRH on the wire

The SRH is IPv6 Routing Type 4 (RFC 8754). It sits between the IPv6 header and the payload
(or another extension header):

```text
+----------+----------+----------+----------+
| Next Hdr | HdrExtLen| RtType=4 | Segments |
|          |          |   (=4)   |   Left   |
+----------+----------+----------+----------+
| LastEntry |  Flags  |        Tag           |
+----------+----------+----------------------+
|       Segment List[0]  (16 bytes)          |
|       Segment List[1]                      |
|       ...                                  |
|    optional TLVs (HMAC, padding)           |
+--------------------------------------------+
```

Fields:

| Field       | Bits | Meaning                                                   |
|-------------|------|-----------------------------------------------------------|
| Next Header | 8    | Protocol following the SRH (e.g., TCP = 6)                |
| Hdr Ext Len | 8    | SRH length in 8-octet units, excluding the first 8        |
| Routing Type| 8    | 4 for SRH                                                 |
| Segments Left| 8   | Index of the *active* segment in the segment list         |
| Last Entry  | 8    | Index of the last valid entry in the segment list         |
| Flags       | 8    | OAM / protection / quick-fail bits (see RFC 8754 s3)      |
| Tag         | 16   | Opaque per-policy marking                                 |

The core invariant: **the packet's Destination Address always equals the active segment.**
The segment list is encoded in reverse order — `Segment List[0]` holds the *last* segment of
the path, and the active segment is `Segment List[Segments Left]`. Processing at a segment
endpoint (RFC 8754 s4.3.1) is a three-line loop: verify you own DA, decrement Segments Left,
copy the next segment into DA, forward. No TTL lives in the SRH: only the outer IPv6 Hop
Limit decrements per physical hop, and transit (non-segment) routers never touch the SRH.

**Reduced mode (RFC 8754 s4.1.1).** The first segment must sit in the DA anyway, so listing it
again wastes 16 bytes per packet. A *reduced* SRH omits it: the headend writes segment 1 into
DA and lists only segments 2..n — cheap, and decisive at line rate on short paths.

## Packet walk: a shrinking stack

Ingress A steers traffic to a v4 VPN destination behind S4 via segments `[S1 S2 S3 S4]`,
encapsulated (outer IPv6 + SRH + inner customer packet). S3 and S4 run the PSP flavor
(penultimate segment pop) so the SRH disappears one hop early:

```text
hop 0   A  -> S1 : DA=S1  SL=3  [S4][S3][S2][S1] | inner pkt
hop 1   S1 -> S2 : End: SL 3->2, DA=S2            | inner pkt
hop 2   S2 -> S3 : End: SL 2->1, DA=S3            | inner pkt
hop 3   S3 -> S4 : End(PSP): SL 1->0, DA=S4,
                   SRH REMOVED before transmit    | inner pkt
hop 4   S4       : End.DT4: decap, IPv4 FIB lookup, deliver
```

Intermediate routers that are *not* segments forward purely on DA and never see the SRH — the
stack shrinks only where segments live.

## SIDs and endpoint behaviors (RFC 8986)

An SRv6 SID is an IPv6 address structured as `LOCATOR : FUNCTION : ARGUMENTS`. The locator is
a routable prefix advertised in the IGP that steers the packet to the node; the function names
a *behavior* — a program the node runs on the packet; arguments carry per-flow parameters.

| Behavior    | Program executed at the SID owner                          |
|-------------|------------------------------------------------------------|
| End         | Advance to next segment (the loop above)                    |
| End.X       | Advance, then cross-connect to a given L3 adjacency         |
| End.DX4     | Decap outer header; forward inner IPv4 out a fixed next hop |
| End.DT4     | Decap; look up inner IPv4 in a specific VRF table           |
| End.DT6     | Decap; look up inner IPv6 in a specific VRF table           |
| End.B6.Encaps| Insert a new SRH for a bound SR policy (nesting, chaining) |
| End.BM      | Forward into an SR-MPLS policy (v6<->MPLS interworking)     |

The naming is a grammar: **D**ecapsulation, **T**able lookup, **X** cross-connect, **B**inding.
`End.DT4` on a PE router is functionally the SRv6 equivalent of an MPLS *VPN label* — the
locator gets the packet to the PE, the function selects the VRF — but with no label protocol at
all: the PE simply advertises `2001:db8:4::/64` (say) into the IGP and anyone can use it.
Behaviors additionally come in *flavors*: **PSP** (penultimate pop), **USP** (ultimate pop),
and **USD** (ultimate decapsulation) — orthogonal knobs on any behavior.

## uSID: compressing long paths (RFC 9800)

Sixteen bytes per segment makes deep paths expensive (overhead, MTU, and hardware SID depth).
RFC 9800, *Compressed SRv6 Segment List Encoding* (June 2025, updating RFC 8754), defines
**REPLACE-CSID** containers — the standardization of the vendor uSID/micro-SID scheme. One
128-bit SID is packed with a short locator (commonly 32 bits) plus up to six 16-bit
micro-segments; an endpoint running a NEXT-CSID flavor treats the active container as an
instruction, slides the window, and moves on. Qualitatively: a 6-hop path that costs
`8 + 16*6 = 104` SRH bytes in full mode fits in a single compressed SID (`8 + 16 = 24` bytes),
which is exactly why deep-path designs converge on uSID.

## TI-LFA fast reroute

Link or node failures need sub-50ms repair — OSPF/IS-IS reconvergence alone is far slower.
Topology-Independent LFA computes, *pre-failure*, the path traffic would take **after** the
IGP converges around the failure, then encodes that post-convergence path as a repair segment
list. On failure detection the PLR pushes the repair list and forwards immediately — no
microloop, no dependency on the failure's topology type (hence "topology independent"):

```text
pre-computed:  S2's path around failed link S2-S3 is [S5, S3], cost matches post-convergence
normal:    A --> S1 --> S2 --X--> S3 --> S4        X = link down
repair:    S2 --> S5 --> S3 --> S4   (S2 pushes repair list [S5] atop the active SID)
```

Because the repair list reuses the same SID space as data-plane policies, TI-LFA needs no
separate backup-tunnel signaling — a large part of why RSVP-TE fell out of favor.

## SR policies and BGP (RFC 9256)

An SR Policy (RFC 9256) is the control-plane object that produces segment lists. It is
identified by the tuple **(headend, color, endpoint)**; color encodes intent (low-latency,
protected...). Each policy holds one or more *candidate paths* with a preference; the
highest-preference valid path becomes active and hands its segment lists to the headend's
steering engine. Candidate paths are computed by a controller or PCE and delivered via BGP
(the SR Policy SAFI) or PCEP. Steering is by color: a BGP VPN route carrying color community
C and next-hop E makes any headend with policy (headend, C, E) steer matching traffic into it.

## SR-MPLS vs SRv6

SR is data-plane-agnostic: the same source-routing architecture runs over MPLS labels or
IPv6 SIDs.

| Aspect            | SR-MPLS                          | SRv6                                  |
|-------------------|----------------------------------|---------------------------------------|
| Per-segment cost  | 4 bytes (label)                  | 16 bytes (SID) + 8-byte fixed SRH     |
| Encapsulation     | label stack only                 | outer IPv6 + SRH (MTU planning!)      |
| Service programming| labels are opaque (VPN label)   | functions + arguments, end-to-end IPv6|
| Where it runs     | provider core (RFC 8660-family)  | core, edge, DC, host-to-host          |
| Hardware age      | mature everywhere                | needs SRH-aware ASICs; MSD-limited    |
| Compression       | natural (4B labels)              | needs uSID/REPLACE-CSID for depth     |

The field pattern is unambiguous: cores keep SR-MPLS (cheap, mature, no MTU surprises), while
SRv6 grows from the edge inward where its service programming (per-tenant SIDs, network
function chaining, slicing) pays for itself. Interworking behaviors (`End.BM` toward SR-MPLS
policies, plus the spring working group's SRv6/SR-MPLS interworking work) span both planes.
Cross-reference the LDP/RSVP-TE machinery in [MPLS](./mpls.md) — SR replaces exactly that layer.

## Operational realities

**Per-packet overhead and MTU.** Encapsulation adds a 40-byte outer IPv6 header plus the SRH
(8 + 16n full, 8 + 16(n-1) reduced). On a 1500-byte access MTU, a 6-segment policy burns 144
bytes before the payload exists. Standard mitigations: raise core MTU (9000+) on SRv6 domains,
prefer reduced/PSP modes plus uSID on deep paths, and mind PMTU on internet-facing tunnels —
the outer header makes inner 1500-byte packets oversize on 1500-byte links unless hosts do
packet-too-big discovery or the edge clamps MSS.

**ASIC SID depth.** Forwarding silicon processes the segment list with limited iterations per
packet — the *Maximum SID Depth* (MSD), commonly single digits on real hardware and advertised
in the IGP and BGP-LS so controllers compute lists that fit. A list deeper than the MSD forces
binding-SID nesting or uSID compression. Reduced mode saves 16 bytes per packet by not
duplicating the first segment; PSP additionally lets the penultimate node strip the header
entirely. Interview angle: "your controller computes a 9-segment list and the PE reports
MSD 6 — what are your options?" (nest, compress, split the path, or re-hardware).

**Brownfield.** Nobody cuts over in a day: SRv6 arrives edge-first for new services (5G uplink
classification, L3VPN without LDP), coexists with SR-MPLS via binding behaviors, and uSID eases
depth economics once hardware supports it. Expect mixed-plane traceroute stories for years.

**Troubleshooting.** Only the outer IPv6 Hop Limit drops per physical hop, so traceroute still
shows every physical router while the segment list stays invisible unless endpoints expose
telemetry. Drops at a segment endpoint are behavior bugs (wrong VRF in `End.DT4`, missing
adjacency in `End.X`) — debug per-node, not per-path.

## Runnable: SRH overhead vs path length

The model below quantifies the three costs that drive every SRv6 design review — SRH bytes
(full vs reduced), encapsulation overhead against a 1500 MTU, and overhead on small packets:

```python
# SRH wire overhead: full vs reduced mode (RFC 8754 s4.1.1);
# each Segment List entry is a 16-byte IPv6 address
IPV6_HDR = 40   # outer IPv6 header used by encapsulation mode
SRH_FIXED = 8   # SRH fixed part: next-hdr, hdr-ext-len, rt-type, seg-left,
                # last-entry, flags, tag (HMAC TLV not counted)

def srh_bytes(n_segments, mode):
    if mode == "full":            # every segment of the path listed
        return SRH_FIXED + 16 * n_segments
    if mode == "reduced":         # first segment carried in the outer DA
        return SRH_FIXED + 16 * (n_segments - 1)
    raise ValueError(mode)

print("segs  fullSRH  redSRH  saved  encap_full  maxpayload@1500  ohead_64B%")
for n in range(1, 9):
    full, red = srh_bytes(n, "full"), srh_bytes(n, "reduced")
    encap = IPV6_HDR + full
    payload = 1500 - encap                    # max inner packet under 1500 MTU
    small = 100.0 * encap / (64 + encap)      # overhead on a 64-byte flow
    print(f"{n:>4}  {full:>7}  {red:>6}  {full-red:>5}  {encap:>10}  "
          f"{payload:>15}  {small:>9.1f}")

MSD = 8   # assumed forwarding-ASIC maximum SID depth
print(f"\nMSD limit assumed: {MSD} segments")
for depth in (4, 6, 10, 12):
    verdict = "fits" if depth <= MSD else "EXCEEDS -> binding SID or uSID needed"
    print(f"path depth {depth:>2}: {verdict}")
```

Real output:

```text
segs  fullSRH  redSRH  saved  encap_full  maxpayload@1500  ohead_64B%
   1       24       8     16          64             1436       50.0
   2       40      24     16          80             1420       55.6
   3       56      40     16          96             1404       60.0
   4       72      56     16         112             1388       63.6
   5       88      72     16         128             1372       66.7
   6      104      88     16         144             1356       69.2
   7      120     104     16         160             1340       71.4
   8      136     120     16         176             1324       73.3

MSD limit assumed: 8 segments
path depth  4: fits
path depth  6: fits
path depth 10: EXCEEDS -> binding SID or uSID needed
path depth 12: EXCEEDS -> binding SID or uSID needed
```

Read the table the way a design review would: reduced mode buys a constant 16 bytes (one
segment-list entry) at any depth; each extra hop costs 16 bytes of overhead budget; the
percentage column shows why small-packet flows suffer most; the MSD block is the controller's
per-node constraint.

## References

- [RFC 8754: IPv6 Segment Routing Header (SRH)](https://www.rfc-editor.org/rfc/rfc8754.txt)
- [RFC 8986: SRv6 Network Programming (SID format, endpoint behaviors, flavors)](https://www.rfc-editor.org/rfc/rfc8986.txt)
- [RFC 9256: Segment Routing Policy Architecture](https://www.rfc-editor.org/rfc/rfc9256.txt)
- [RFC 8402: Segment Routing Architecture](https://www.rfc-editor.org/rfc/rfc8402.txt)
- [RFC 9800: Compressed SRv6 Segment List Encoding (REPLACE-CSID / uSID)](https://www.rfc-editor.org/rfc/rfc9800.txt)
