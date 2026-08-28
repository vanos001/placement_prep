# GRO, GSO/TSO, and the Checksum Offload Contract

Receive coalescing (GRO) and transmit segmentation (GSO/TSO) are the same bargain
struck in opposite directions: build a 64 KiB "super-packet" in memory, pay per-packet
costs once instead of 45 times, and let the NIC (or the kernel) unbundle it at the
edge. The glue holding both directions together is the checksum offload contract — a
set of rules about *who* computes or verifies checksums *when* — and when any party
breaks it, coalescing silently degrades or packets silently corrupt. This page covers
the mechanics, the contract, a virtualization case study, and the debugging playbook.
The skb structures these features manipulate are detailed in
[the skb anatomy page](./skb-internals.md); the polling loop that runs GRO is covered
in [the NAPI page](./napi-polling.md).

## Why the kernel ships 64 KiB packets

Per-packet costs are fixed regardless of payload: an skb alloc, a stack traversal
(IP + TCP), a qdisc enqueue, driver descriptor setup, an interrupt slice. At 1460-byte
MSS, 10 Gbps is ~850 K packets/s of *pure overhead* if every segment is handled
individually. Coalescing 44 segments into one skb divides every per-packet constant by
44; that is the entire economic case for the offload family. The kernel's limits are
in `include/linux/netdevice.h`: `GRO_LEGACY_MAX_SIZE`/`GSO_LEGACY_MAX_SIZE` = 65536
bytes, with `GRO_MAX_SIZE` = 8 × 65535 (~512 KiB) reachable via per-device
`gso_max_size`/`gro_max_size` settings for Big-TTCP-style deployments, and
`gso_segs` being a 16-bit field caps segment counts at `GSO_MAX_SEGS` = 65535.

## The offload family map

| Feature | ethtool name | Direction | What it moves where |
|---|---|---|---|
| Generic Receive Offload | `rx-gro` | RX | Kernel merges segments into super-skbs |
| Hardware Receive Offload (LRO) | `rx-lro` | RX | NIC merges; deprecated — breaks forwarding/routing |
| Generic Segmentation Offload | `tx-gso` | TX | Kernel segments a super-skb just before the driver |
| TCP Segmentation Offload | `tx-tcp-segmentation` | TX | NIC segments; kernel only builds the super-skb |
| UDP Segmentation Offload (USO) | `tx-udp-segmentation` | TX | Same idea for UDP (kernels since 5.18, `SKB_GSO_UDP_L4`) |
| TX checksum offload | `tx-checksumming` | TX | NIC completes `CHECKSUM_PARTIAL` checksums |
| RX checksum offload | `rx-checksumming` | RX | NIC verifies; driver sets `ip_summed` accordingly |
| Scatter-gather | `tx-scatter-gather` | TX | skb fragments may point at pages, not one linear buffer |

The GRO/GSO split matters: GRO is always software (it runs in the NAPI poll), while
GSO *falls back* to software segmentation (`skb_gso_segment()`) when the NIC lacks
TSO. TSO is the hardware version of GSO. LRO is the hardware version of GRO, and it
lost: merged LRO frames lose original headers, so they cannot be forwarded, bridged,
or routed — GRO keeps the original segments (below) and is always safe to leave on.

## Receive: how GRO decides to coalesce

`napi_gro_receive(napi, skb)` hands the packet to a per-napi aggregation engine:

1. The packet is hashed into one of `GRO_HASH_BUCKETS` (8) flow buckets on the
   `napi_struct`.
2. A protocol-specific `gro_receive` callback (TCP: `tcp_gro_receive()`) compares it
   against the current aggregate for that flow: same addresses/ports, adjacent
   sequence numbers, compatible flags (no PSH mid-aggregate games), same timestamps
   options class.
3. Merge or flush. A merge grows the aggregate — payload typically appended as page
   fragments, original segment skbs chained on `frag_list` so they survive intact for
   taps and for later splitting. Anything non-contiguous (different flow, seq gap,
   size limit hit) *flushes*: the finished super-skb goes up the stack as one skb.
4. Batches leaving GRO are emitted in groups of `gro_normal_batch` (default 8) to
   amortize the hand-off.

The merged skb is a proper GSO skb: `gso_size` = MSS, `gso_segs` = segment count —
which means the *transmit* side can re-segment it later (bridges, forwarding,
container veth hops) without ever un-coalescing in software. Two structural extras:

- **gro_cells**: tunnels (ipip, sit, GRE, VXLAN) get a `gro_cells` receive cell so
  that encapsulated traffic is coalesced *after* decapsulation, in the tunnel's own
  queue, instead of being flushed by the outer-flow hash.
- **Deferred flush**: with `gro_flush_timeout` + `napi_defer_hard_irqs` set, GRO
  holds aggregates across a grace period, betting more segments of the same flow will
  arrive — higher coalescing, higher latency.

## Transmit: gso_size, gso_segs, and skb_is_gso

On the send side, TCP (and now UDP with USO) builds skbs much larger than the MTU and
marks them:

- `skb_shinfo(skb)->gso_size` — the MSS each wire segment must carry (e.g. 1460).
- `gso_segs` — how many segments the skb represents.
- `gso_type` — `SKB_GSO_TCPV4`, `SKB_GSO_TCPV6`, `SKB_GSO_UDP_L4`, plus modifiers
  like `SKB_GSO_TCP_FIXEDID` and tunnel/inner variants (documented in the kernel's
  segmentation-offloads doc).

`skb_is_gso()` simply asks whether `gso_size` is set. Every layer between TCP and the
NIC passes the skb whole — qdiscs shape 64 KiB logical packets, BPF at TC sees one
skb — until one of three things un-bundles it: the NIC's TSO engine, the driver
requesting software segmentation, or `skb_gso_segment()` in the stack when features
require it (e.g. device without TSO, or a transformation that forces it). USO extends
the identical pattern to UDP datagrams, which is what makes QUIC/UDP proxies cheap at
high rates; the kernel documentation notes UFO (old UDP fragmentation offload) is
obsolete because USO segments *packets* rather than emitting IP fragments.

## The checksum contract

The offload family only works because checksums were made lazy. The contract, per
direction (the kernel's checksum-offloads doc is normative here):

| Stage | Stack's obligation | NIC/driver's obligation |
|---|---|---|
| Local TX, offload on | Fill everything but the L4 checksum field; set `ip_summed = CHECKSUM_PARTIAL`, `csum_start` = L4 header offset, `csum_offset` = field offset | Compute checksum over `[csum_start, skb->len)` and store it at `csum_start + csum_offset` |
| Local TX, offload off | Compute the full checksum (`skb_checksum_help()` resolves a PARTIAL skb) | None |
| Remote RX, hardware verified | Trust driver's `CHECKSUM_UNNECESSARY`, or validate `CHECKSUM_COMPLETE` in `skb->csum` | Verify and set `ip_summed` honestly |
| Remote RX, no offload | Verify in software (`CHECKSUM_NONE`) | Report `CHECKSUM_NONE` |

Two subtleties worth knowing cold. First, the pseudo-header: the stack pre-fills the
TCP/UDP checksum field with the pseudo-header sum so the NIC only needs to fold in the
packet bytes — that is why a GRO-merged skb can keep working with a *single* L4 header
plus accumulated partial sums. Second, GRO *sets* `CHECKSUM_PARTIAL` on merged skbs
(the doc explicitly notes it "may be set in the input path in GRO"): the aggregate
carries one header and a running sum, and a later software segmentation can finish it.
A NIC that reports bad checksums (or a driver that lies with `CHECKSUM_UNNECESSARY`)
breaks this chain quietly: coalescing stalls because GRO cannot trust its input, or
worse, corrupt data gets marked verified. See failure modes below.

## Scatter-gather: why TSO needs SG

A TSO super-skb is rarely contiguous. Sendmsg payloads live in user pages referenced
as `frags[]`; zerocopy sends are *entirely* paged. The NIC must therefore DMA from a
scatter list — which is why `ethtool` marks scatter-gather as a *hard dependency* of
TSO and TX checksum offload: with SG off, the kernel must linearize the skb, and the
super-skb construction loses its point. The dependency graph (`netdev-features` doc
walks the "mess") is: `tx-scatter-gather` enables `tx-checksum-*` enables `tx-tso-*`;
GRO's RX side is independent of SG but its output skbs are non-linear, so a forwarded
GRO skb needs TX SG on the egress device or it linearizes at 64 KiB a packet.

## Case study: virtio-net negotiation

Virtio-net is the cleanest place to read the whole contract, because guest and host
must *negotiate* every offload explicitly through feature bits before a single packet
flows (spec: [virtio v1.2 §5.1.5](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)):

| Bit | Name | Direction of the bargain |
|---|---|---|
| 0 | `VIRTIO_NET_F_CSUM` | Host accepts guest packets with `CHECKSUM_PARTIAL` (guest TSO precondition) |
| 1 | `VIRTIO_NET_F_GUEST_CSUM` | Guest accepts host-marked partial/verified checksums |
| 7/8/9 | `VIRTIO_NET_F_GUEST_TSO4/TSO6/ECN` | Host may deliver GRO-coalesced super-frames to the guest |
| 11/12/13 | `VIRTIO_NET_F_HOST_TSO4/TSO6/ECN` | Guest may send TSO super-frames for the host to segment |
| 15 | `VIRTIO_NET_F_MRG_RXBUF` | Guest accepts host-merged RX buffers (host-side GRO assist) |
| 56 | `VIRTIO_NET_F_HOST_USO` | Guest UDP segmentation offload |

The mapping onto the kernel contract is direct: guest `VIRTIO_NET_F_HOST_TSO4` ⇔ the
host device advertises TSO so the guest stack can build `CHECKSUM_PARTIAL` + `gso_*`
skbs; `VIRTIO_NET_F_GUEST_TSO4` ⇔ the host (vhost/net backend or device) performs GRO
and the guest driver marks received skbs `CHECKSUM_UNNECESSARY`. Neither side may
assume anything the negotiation didn't grant — which is exactly why offload bugs in
VMs present as "works on bare metal, breaks in the VM": a tap or older backend that
dropped a feature bit silently switched the guest to software segmentation and
software checksums. The virtqueue mechanics behind these handoffs are in
[the virtio page](../../virtualization/virtio.md), and tun/tap devices (the
userspace half of this contract) expose the same knobs via `TUNSETOFFLOAD`.

## When offloads bite: failure modes

- **Broken NIC checksum → bad GRO.** GRO only aggregates packets whose checksum
  state it can trust; a NIC (or driver) that marks bad frames as verified leads to
  corrupted aggregates, and one that never marks them verified quietly disables
  coalescing. Symptom: throughput drops ~10–40× when a firmware update flips
  `rx-checksumming` off. Check `ethtool -k` and `ip -s link` before blaming TCP.
- **Capture distortion.** With GRO on, tcpdump shows 60+ KiB "packets" that never
  existed on the wire, with kernel-computed timestamps; packet-size distributions and
  retransmit analyses must be taken with GRO off (or via hardware taps).
- **Forwarding/bridging with LRO.** LRO-merged frames have no original headers —
  routing them is impossible, so LRO must stay off on routers/bridges; GRO is the
  safe replacement because it preserves segments on `frag_list`.
- **Offload toggles as PMTU/MTU lie detectors.** A path that only works with TSO/GRO
  disabled usually has a middlebox mangling large frames or MTU mis-discovery; the
  offload turns a hard failure into a subtle stall.
- **Checksum after transformation.** NAT, VLAN push, or encapsulation on a
  `CHECKSUM_COMPLETE` skb invalidates the verified sum; the stack re-marks it, and
  drivers that forget to re-mark (a recurring driver-bug class) deliver "verified"
  frames whose checksum predates the rewrite.

## Debugging: ethtool -k, counters, perf

A workable loop for "is this an offload problem?":

```bash
# 1. Inventory what is actually negotiated (device + driver reality, not config intent)
ethtool -k eth0
ethtool -i eth0                      # driver/firmware versions first
ip -details link show eth0           # gso_max_size / gso_max_segs in effect

# 2. A/B the suspicion: toggle one feature, re-measure ( pktgen or iperf, not curl )
ethtool -K eth0 gro on  ; iperf3 -c host -t 10
ethtool -K eth0 gro off ; iperf3 -c host -t 10

# 3. Attribute cost inside the kernel: where do cycles go with GRO on/off?
perf record -a -g -e cycles -- sleep 5
#    GRO on:  expect time in napi_gro_receive / tcp_gro_receive / inet_gro_receive
#    GRO off: expect it smeared into ip_rcv / tcp_v4_rcv per packet

# 4. Watch drops and coalescing behavior live
bpftrace -e 'tracepoint:skb:kfree_skb { @[kstack] = count(); }'
cat /proc/net/softnet_stat            # col2 = dropped (backlog full), col3 = time squeeze
```

`/proc/net/softnet_stat`'s third column ("time squeeze") is the NAPI budget counter —
a non-zero value under load means `netdev_budget`/`netdev_budget_usecs` are binding,
which is a [NAPI page](./napi-polling.md) discussion. For synthetic packet generation
to isolate NIC behavior from the application, see [the pktgen page](./pktgen.md),
which also explains why benchmarks disable GRO/TSO to get comparable small-packet
numbers. TLS-level offloads are a separate contract, covered in
[the TLS offload page](./tls-offload.md).

## Super-packet to wire: the segmentation picture

The mandatory picture: one 64 KiB class super-skb becomes 45 wire frames at MTU 1500
(the simulation below uses 44 × 1460 = 64240 B payload for clean math), and each frame
re-derives its IP/TCP headers from `gso_size`:

```text
 TX side:  application write() stream
 +----------------------------------------------------------------+
 |                        64240 B of TCP payload                   |
 +----------------------------------------------------------------+
            |  TCP builds ONE skb, marks it GSO
            v
 +----------------------------------------------------------------+
 | skb: len=64240  gso_size=1460  gso_segs=44  ip_summed=PARTIAL   |
 | linear header + frags[] payload pages                           |
 +----------------------------------------------------------------+
            |  TSO (NIC) or skb_gso_segment() (software)
            v
 +-------------+  +-------------+  +-------------+     +-----------+
 | ETH|IP|TCP| \ | ETH|IP|TCP| \ | ETH|IP|TCP|  ... | ETH|IP|TCP| \
 |    1460B    | |    1460B    | |    1460B    |     |    1460B   |  <- 44 frames,
 +-------------+  +-------------+  +-------------+     +-----------+     1514 B each

 RX side:  the mirror image — NIC (LRO/hw GRO) or driver+napi_gro_receive
 +-------------+  +-------------+  +-------------+     +-----------+
 | frame 1     |  | frame 2     |  | frame 3     | ... | frame 44  |
 +-------------+  +-------------+  +-------------+     +-----------+
            \             |             |                 /
             v            v             v                v
 +----------------------------------------------------------------+
 | ONE skb: 64240 B, gso_size=1460, gso_segs=44, originals on      |
 | frag_list, CHECKSUM_PARTIAL carrying the folded running sum     |
 +----------------------------------------------------------------+
            |  ONE pass of IP -> TCP -> socket
            v
     sk_receive_queue gets 64240 B with 1 skb, not 44
```

## Worked model: coalescing and segmentation math

```python
#!/usr/bin/env python3
"""GRO coalescing and GSO/TSO segmentation calculator.

Uses exact MSS arithmetic with the kernel's real limits:
  - GRO coalesces until the super-skb payload reaches 65536 B
    (GRO_LEGACY_MAX_SIZE), flushing on flow gaps;
  - TSO builds super-skbs of up to 64 KiB payload segmented by the
    NIC into MSS-sized frames on the wire.
Deterministic: MSS=1460 (TCP no options), 16 MiB bulk transfer.
"""

MSS = 1460
GRO_LIMIT = 65536          # GRO_LEGACY_MAX_SIZE: max coalesced payload
XFER = 16 * 1024 * 1024    # 16 MiB bulk flow

segs = (XFER + MSS - 1) // MSS           # wire-sized TCP segments
per_gro = GRO_LIMIT // MSS               # segments that fit in one coalesced skb
gro_skbs = -(-segs // per_gro)           # ceil
tso_skbs = -(-segs // per_gro)           # same limit on the TX side

print(f"MSS = {MSS} B, transfer = {XFER} B ({XFER / (1024 * 1024)} MiB)")
print()
print("=== RX: segments delivered to the TCP stack ===")
print(f"{'GRO':<4} {'stack skbs':>10} {'skipped':>10} {'coalesce':>9}")
print(f"{'off':<4} {segs:>10} {segs:>10} {'1.0x':>9}")
print(f"{'on':<4} {gro_skbs:>10} {segs - gro_skbs:>10} "
      f"{segs / gro_skbs:>8.1f}x")
print(f"savings: {segs - gro_skbs} skipped IP/TCP traversals "
      f"({100 * (segs - gro_skbs) // segs}%)")
print()
print("=== one coalesced GRO super-skb ===")
last = segs - (gro_skbs - 1) * per_gro
print(f"typical: {per_gro} segs x {MSS} B = {per_gro * MSS} B payload, "
      f"gso_size={MSS}, gso_segs={per_gro}")
print(f"final GRO skb of the transfer: {last} segs = {last * MSS} B payload")
print()
print("=== TX: skbs handed to the driver for 16 MiB write() ===")
print(f"{'TSO':<4} {'skbs enqueued':>13} {'qdisc ops':>9} {'wire frames':>11}")
print(f"{'off':<4} {segs:>13} {segs:>9} {segs:>11}")
print(f"{'on':<4} {tso_skbs:>13} {tso_skbs:>9} {segs:>11}")
print(f"per-skb cost 1.5 us: off={segs * 15 / 10000:.1f} ms, on={tso_skbs * 15 / 10000:.1f} ms")
print()
print("=== wire framing of the first super-skb (MTU 1500) ===")
print(f"{per_gro} frames of {14 + 20 + 20 + MSS} B on the wire "
      f"(Ethernet 14 + IPv4 20 + TCP 20 + payload {MSS})")
```

Output (verified byte-for-byte against a run of this exact script):

```text
MSS = 1460 B, transfer = 16777216 B (16.0 MiB)

=== RX: segments delivered to the TCP stack ===
GRO  stack skbs    skipped  coalesce
off       11492      11492      1.0x
on          262      11230     43.9x
savings: 11230 skipped IP/TCP traversals (97%)

=== one coalesced GRO super-skb ===
typical: 44 segs x 1460 B = 64240 B payload, gso_size=1460, gso_segs=44
final GRO skb of the transfer: 8 segs = 11680 B payload

=== TX: skbs handed to the driver for 16 MiB write() ===
TSO  skbs enqueued qdisc ops wire frames
off          11492     11492       11492
on             262       262       11492
per-skb cost 1.5 us: off=17.2 ms, on=0.4 ms

=== wire framing of the first super-skb (MTU 1500) ===
44 frames of 1514 B on the wire (Ethernet 14 + IPv4 20 + TCP 20 + payload 1460)
```

The headline numbers: a 16 MiB bulk flow costs the stack 11492 skb traversals with
offloads off and 262 with them on — a 43.9× reduction — while the wire still carries
exactly 11492 frames either way. Offloads change *where* per-packet work happens, not
how many packets the network sees.

## References

- [Checksum offloads — kernel documentation](https://docs.kernel.org/networking/checksum-offloads.html)
  — the normative `ip_summed`/`CHECKSUM_PARTIAL` contract.
- [Segmentation offloads — kernel documentation](https://docs.kernel.org/networking/segmentation-offloads.html)
  — `gso_type` values, USO, tunnel segmentation, `SKB_GSO_*` modifiers.
- [Netdev features mess and how to get out from it alive](https://docs.kernel.org/networking/netdev-features.html)
  — why feature dependencies (SG → checksum → TSO) behave the way they do.
- [VIRTIO specification v1.2](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)
  — device types / network device: feature bits 0–56 cited in the case study.
- [Scaling in the Linux network stack](https://docs.kernel.org/networking/scaling.html)
  — RPS/RFS/XPS, which determine where GRO output gets processed.
- [include/linux/netdevice.h](https://github.com/torvalds/linux/blob/master/include/linux/netdevice.h)
  — `GRO_LEGACY_MAX_SIZE`, `GRO_MAX_SIZE`, `GSO_MAX_SEGS`, `NAPI_POLL_WEIGHT`.
