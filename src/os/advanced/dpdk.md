# DPDK Internals — the User-Space NIC Data Plane

The Data Plane Development Kit is the working artifact of one idea: for a packet forwarder, the per-packet costs of a kernel network stack — system calls, interrupts, context switches, copies, cache thrash from shared queues — cost more than the packet processing itself. DPDK removes them by giving a user-space application direct ownership of three kernel responsibilities: PCI device access (UIO/VFIO), DMA memory (hugepages), and the driver's RX/TX rings (poll-mode drivers). It is deliberately not a framework: EAL, PMDs, and libraries are building blocks, and the application's main loop is yours. This page covers the mechanism layer — EAL memory layout, the UIO-to-VFIO shift, PMD ring anatomy, mempool caching, RSS flow steering — plus the two loop models and the kernel-fallback paths. For the graph-based forwarder built on top of this substrate, see [VPP internals](../../networks/advanced/fdio-vpp.md).

## What the kernel path was charging

A traditional NIC RX path charges per packet: MSI-X interrupt + NAPI softirq scheduling, skb allocation, protocol processing in softirq context, socket lookup, data copy to user space, and wakeup of the receiver. At 10 Mpps with 10 kernel hops, per-packet costs measured in microseconds dominate hardware latencies in nanoseconds. DPDK's removal list is explicit:

```text
Kernel path cost                    DPDK replacement
---------------------------------   ---------------------------------
interrupt + NAPI softirq        ->  polling (PMD) on dedicated cores
syscall per RX/TX               ->  direct ring access from user space
skb alloc/free per packet       ->  mbuf recycled from per-core mempool cache
cross-CPU cache-line ping-pong  ->  flow-to-core pinning (RSS + lcore model)
sw page-table walk for DMA      ->  hugepage memory with IOMMU mapping
lock-protected shared queues    ->  lock-free per-queue rings (rte_ring)
```

## EAL — Environment Abstraction Layer

EAL is the layer that makes "Linux process that owns hardware" bootable and portable. Its documented service set: core affinity (lcores mapped/pinned to physical CPUs), hugepage-backed memory management (memzones carved from mmap'd hugepage segments), PCI bus enumeration and device binding, timers and alarms, log/trace, and interrupt/alarm threads for the minority of work that still needs callbacks. Command-line plumbing (`-c`/`-l` core mask, `--huge-dir`, `--iova-mode`) is parsed here; the EAL init sequence walks PCI devices, binds/claims drivers, and sets up the memory configuration other libraries consume.

The memory map EAL assembles is the key to why DMA works at all from user space:

```text
DPDK process address space (illustrative)
+-------------------------------------------+
| app text/data                             |
| EAL mapped hugepages:                     |
|   2 MiB / 1 GiB pages, contiguous VA      |<-- memzones slice this
|   (VA == PA in no-iommu mode, or          |    into mempools, rings,
|    IOVA-contiguous via IOMMU)             |    memzones
| PCI sysfs maps: BARs of owned NICs        |<-- PMD register access
+-------------------------------------------+
```

Two subtleties worth interview credit. First, IOVA mode: with an IOMMU present, DPDK can use arbitrary IOVA (virtual addresses as DMA addresses); without one, memory must be physically contiguous, which is why `--iova-mode=pa` and 1 GiB hugepages matter on bare-metal hosts. Second, `--legacy-mem` and the memory subsystem's later rework (dynamic allocation, hotplug of hugepage segments) changed how addresses are guaranteed stable — code that caches physical addresses must pin before use.

## From UIO to VFIO — device ownership with a memory-safety story

Before DPDK, no standard way existed for user space to both touch a PCI device's registers and safely receive its DMA. The two driver stacks:

| | UIO (`uio_pci_generic` / `igb_uio`) | VFIO (`vfio-pci`) |
|---|-------------------------------------|--------------------|
| In-tree status | `uio_pci_generic` minimal in-tree; `igb_uio` maintained out-of-tree (dpdk-kmods) | full in-tree driver framework |
| DMA safety | none from UIO itself — device may DMA anywhere it is programmed | IOMMU enforces per-device IOVA ranges |
| Interrupts | block-device-style mmap + read on fd | eventfd-based, per-device |
| Group model | none | IOMMU groups + containers (`/dev/vfio/<group>`) |
| Recommended for | legacy hosts, labs | production |

The DPDK setup guide's sequence — enable IOMMU, load `vfio-pci`, bind with `dpdk-devbind.py`, and set hugepages — is effectively the production checklist. `igb_uio`'s out-of-tree status is precisely because UIO predates safe DMA: it exposes device memory and interrupts but leaves DMA programming wholly to the (trusted) application. VFIO's group/container model is also what makes SR-IOV virtual functions usable per-VM and per-container safely. Deeper VFIO mechanics: [VFIO](../../linux/virtualization/vfio.md); the kernel-side API contract: <https://docs.kernel.org/driver-api/vfio.html>.

## PMD anatomy — rings without interrupts

A poll-mode driver is the NIC's datasheet made into a library function. The RX side of an emulated virtio device or a physical NIC follows the same shape:

```text
RX queue (per lcore, per queue-id)
  descriptor ring: N descriptors, each naming an mbuf's DMA address
        |
  NIC DMA-writes packet -> descriptor -> mbuf buffer
        |
  rte_eth_rx_burst(port, queue, mbufs[], 32):
        walk descriptors in order, check DD (done) bit,
        swap fresh mbufs into the ring (rearm), prefetch payloads,
        return up to 32 mbufs to the caller
        |
  TX: fill descriptors with packet pointers, bump tail register (doorbell)
```

Details that decide performance: the driver *rearms* the ring with fresh buffers as it drains, so the NIC never stalls for want of descriptors; payload prefetch (the `rte_pktmbuf_prefetch_part1/2` idiom in examples) hides DRAM latency behind descriptor processing; and because the core spins on the DD bit, an idle queue burns a core — the price of removing interrupts, and why lcore-to-queue mapping is a workload decision, not an implementation detail. The ethdev API layer (`rte_eth_rx_burst`, `rte_eth_tx_burst`, queue setup with `rte_eth_rxconf`) is the stable contract above all PMDs: <https://doc.dpdk.org/guides/prog_guide/ethdev/index.html>.

## Mempools and mbufs — the allocator that never mallocs

Every packet lives in an `rte_mbuf`: a fixed-layout control block (metadata: pool back-pointer, port/queue, offload flags, timestamp) followed by a configurable headroom, then the data buffer. Mbufs come from an `rte_mempool` created over EAL memzones in hugepages. The performance-critical property is the **per-lcore cache**: each mempool carries a small per-core object cache (default size 512 objects in many configs) so the hot path allocates and frees from a core-local stack, touching the shared backend ring only on cache refill/drain. That converts a cross-core contention point into a single-core push/pop — the same reason per-CPU freelists exist in kernel SLUB.

Hugepages serve three roles at once: (1) fewer TLB misses for packet loops that touch a new buffer every few hundred nanoseconds; (2) DMA-friendly contiguity for NIC descriptor rings; (3) pinning — mempool memory never migrates, keeping IOVA addresses valid for the NIC's lifetime. Hugepage sizing and NUMA-local allocation (`--socket-mem`, per-socket mempools) are the knobs: <https://doc.dpdk.org/guides/linux_gsg/sys_reqs.html> (and the repository page on [huge pages](../../os/memory/huge-pages.md) for the kernel-side mechanics).

## RSS — turning flows into core affinity

Receive Side Scaling is how a NIC spreads packets across hardware RX queues without reordering any single flow. The NIC computes a **Toeplitz hash** over the packet's 4-tuple (src/dst IP + src/dst ports; L3-only for fragmented/non-TCP/UDP), using a 40-byte key programmed into the NIC (typically the Microsoft default key), then takes low bits of the hash as an index into the **RETA** (redirection table, typically 128–512 entries), whose entries name RX queues. DPDK exposes key and RETA via `rte_eth_dev_rss_reta_update` and the `rss_conf` in device configuration; the same Toeplitz algorithm ships as a software library (`rte_thash`) for steering decisions that need to know *where a flow would land* before the packet arrives: <https://doc.dpdk.org/guides/prog_guide/toeplitz_hash_lib.html>.

The RSS hash is deterministic and symmetric-by-construction-of-input — identical flows always land on the same queue, so pinning one lcore per queue makes an entire connection's state single-core. The demo at the bottom computes the real hashes and RETA placements for the Intel 82599 datasheet's verification suite.

## Run-to-completion vs pipeline — the two loop shapes

```text
Run-to-completion (l2fwd/l3fwd default)
  lcore 0: rx q0 -> classify -> rewrite -> tx q1     (whole packet life, one core)
  lcore 1: rx q1 -> classify -> rewrite -> tx q0

Pipeline (VPP-style graph; each stage is a node with a vector of packets)
  lcore 0: dpdk-input -> ... hand off via rings ...
  lcore 1:  -> lookup node -> rewrite node -> dpdk-output

  Stage handoff: producer pushes a burst into an rte_ring; consumer
  drains in bursts. Vector processing amortizes I-cache/dcache misses
  across the whole burst per node.
```

| | Run-to-completion | Pipeline (graph nodes) |
|---|--------------------|------------------------|
| Packet touch count | one core touches all stages | N cores, handoff overhead added |
| Worst-case latency | lowest (no queues between stages) | higher (ring hops) |
| Scalability past one core's work | requires RSS queue split | nodes parallelize naturally |
| Cache behavior | per-packet I-miss per stage | per-burst I-miss per stage (vector wins) |
| Complexity | a loop | node framework + lock-free handoff |

**Burst sizes** are the silent multiplier: `rte_eth_rx_burst`/`tx_burst` take an `nb_pkts` cap (commonly 32; examples use `BURST_SIZE 32`) because the per-call costs — reading the ring index, PCI doorbell write, function overhead — amortize across the burst. The performance-guidelines chapter treats burst sizing, prefetch distance, and cache alignment as first-order tuning: <https://doc.dpdk.org/guides/prog_guide/perf_opt_guidelines.html>. The trade mirrored from kernel folklore: batching amortizes fixed costs but adds queueing delay at the head of the burst.

## KNI and TAP — the kernel is still there for the control plane

A data-plane app still needs what the kernel does well: ARP, ICMP replies, SSH to the box, protocols nobody ported. DPDK's kernel-interworking paths hand a subset of packets (or a virtual interface) back into Linux:

- **TAP PMD** — a user-space PMD over `/dev/tap`, i.e., a regular kernel TAP interface driven by DPDK's poll loop. Packets DPDK sends appear inside the kernel network stack as if they arrived on an interface, and vice versa. This is the documented kernel-interworking PMD in current docs: <https://doc.dpdk.org/guides/nics/tap.html>.
- **KNI (Kernel Network Interface)** — the historical path: a kernel module plus `/dev/kni` with a FIFO pair moving skbs between the DPDK mempool world and the kernel stack. It allowed a DPDK app to keep a *real kernel interface* (with kernel IP address, routing, ethtool semantics) fed from the data plane. KNI chapters no longer appear in the current Programmer's Guide (docs tree 26.07 as of mid-2026) — new designs are steered to the TAP PMD and virtio-user/vhost paths.
- **virtio-user + vhost-user** — the modern fallback for talking to a kernel stack or another process over shared-memory queues (the mechanics overlap with [virtio](../../linux/virtualization/virtio.md)).

The routing rule: control-plane traffic (low rate, feature-rich) goes to the kernel via TAP/virtio-user; data-plane traffic stays in PMDs. Multicast/ARP handling — responding *before* the slow path — is a classic hybrid-design interview question.

## Worked demo — Toeplitz RSS against the 82599 verification suite

The demo implements the Microsoft-spec Toeplitz hash in pure Python (bit-stream XOR of a 40-byte key over the packet tuple) and validates it against the exact vectors DPDK's own unit test uses (`app/test/test_thash.c`, taken from the "82599 Datasheet 7.1.2.8.3 RSS Verification Suite"), then shows RETA placement and single-bit sensitivity.

```python
"""Software Toeplitz RSS, checked against the Intel 82599 RSS verification
suite (the exact vectors DPDK's app/test/test_thash.c uses, from the
"82599 Datasheet 7.1.2.8.3 RSS Verification Suite")."""

DEFAULT_RSS_KEY = bytes([
    0x6d, 0x5a, 0x56, 0xda, 0x25, 0x5b, 0x0e, 0xc2,   # 40-byte key, the same
    0x41, 0x67, 0x25, 0x3d, 0x43, 0xa3, 0x8f, 0xb0,   # default key most NICs
    0xd0, 0xca, 0x2b, 0xcb, 0xae, 0x7b, 0x30, 0xb4,   # ship with (MS spec)
    0x77, 0xcb, 0x2d, 0xa3, 0x80, 0x30, 0xf2, 0x0c,
    0x6a, 0x42, 0xb7, 0x3b, 0xbe, 0xac, 0x01, 0xfa,
])

def toeplitz_hash(key, data):
    # bit n of input XORs bit n of the 320-bit key stream shifted left 31
    result = 0
    for n, byte in enumerate(data):
        for b in range(8):
            if byte & (1 << (7 - b)):
                bitpos = n * 8 + b
                w = 0
                for j in range(32):
                    kb = (bitpos + j) // 8
                    w = (w << 1) | ((key[kb] >> (7 - (bitpos + j) % 8)) & 1)
                result ^= w
    return result & 0xFFFFFFFF

# dst_ip, src_ip, dport, sport, expected L3 hash, expected L3+L4 hash
V4_TBL = [
    ((161, 142, 100, 80), (66, 9, 149, 187),   1766, 2794,  0x323e8fc2, 0x51ccc178),
    ((65, 69, 140, 83),   (199, 92, 111, 2),   4739, 14230, 0xd718262a, 0xc626b0ea),
    ((12, 22, 207, 184),  (24, 19, 198, 95),  38024, 12898, 0xd2d0a5de, 0x5c2b394a),
    ((209, 142, 163, 6),  (38, 27, 205, 30),   2217, 48228, 0x82989176, 0xafc7327f),
    ((202, 188, 127, 2),  (153, 39, 163, 191), 1303, 44251, 0x5d1809c5, 0x10e828a2),
]

RETA_SIZE, NB_QUEUE = 128, 4        # 128-entry redirection table, 4 rx queues
reta = [i % NB_QUEUE for i in range(RETA_SIZE)]

print("== 82599 verification suite (default 40-byte key) ==")
hits = [0] * NB_QUEUE
for dst, src, dport, sport, want3, want34 in V4_TBL:
    tup = bytes(src) + bytes(dst) + bytes([sport >> 8, sport & 0xFF]) \
                       + bytes([dport >> 8, dport & 0xFF])
    h3 = toeplitz_hash(DEFAULT_RSS_KEY, tup[:8])
    h34 = toeplitz_hash(DEFAULT_RSS_KEY, tup)
    q = reta[h34 & (RETA_SIZE - 1)]
    hits[q] += 1
    ok3, ok34 = "OK" if h3 == want3 else "FAIL", "OK" if h34 == want34 else "FAIL"
    print(f"{src[0]:>3}.{src[1]}.{src[2]}.{src[3]:<3} -> "
          f"{dst[0]:>3}.{dst[1]}.{dst[2]}.{dst[3]:<3} p{sport:>5}->{dport:<5} "
          f"L3 {h3:08x}/{ok3}  L4 {h34:08x}/{ok34}  queue {q}")
print("queue hit counts:", hits)

print("== sensitivity: flip one sport bit (13) of flow 1 ==")
dst, src, dport, sport, _, _ = V4_TBL[0]
alt_sport = sport ^ (1 << 13)
h_a = toeplitz_hash(DEFAULT_RSS_KEY, bytes(src) + bytes(dst)
                    + bytes([sport >> 8, sport & 0xFF]) + bytes([dport >> 8, dport & 0xFF]))
h_b = toeplitz_hash(DEFAULT_RSS_KEY, bytes(src) + bytes(dst)
                    + bytes([alt_sport >> 8, alt_sport & 0xFF]) + bytes([dport >> 8, dport & 0xFF]))
print(f"sport {sport} -> hash {h_a:08x} queue {reta[h_a & (RETA_SIZE-1)]}")
print(f"sport {alt_sport} -> hash {h_b:08x} queue {reta[h_b & (RETA_SIZE-1)]}")
print(f"hashes differ: {h_a != h_b}, queues differ: {reta[h_a & (RETA_SIZE-1)] != reta[h_b & (RETA_SIZE-1)]}")
```

Real output:

```text
== 82599 verification suite (default 40-byte key) ==
 66.9.149.187 -> 161.142.100.80  p 2794->1766  L3 323e8fc2/OK  L4 51ccc178/OK  queue 0
199.92.111.2   ->  65.69.140.83  p14230->4739  L3 d718262a/OK  L4 c626b0ea/OK  queue 2
 24.19.198.95  ->  12.22.207.184 p12898->38024 L3 d2d0a5de/OK  L4 5c2b394a/OK  queue 2
 38.27.205.30  -> 209.142.163.6   p48228->2217  L3 82989176/OK  L4 afc7327f/OK  queue 3
153.39.163.191 -> 202.188.127.2   p44251->1303  L3 5d1809c5/OK  L4 10e828a2/OK  queue 2
queue hit counts: [1, 0, 3, 1]
== sensitivity: flip one sport bit (13) of flow 1 ==
sport 2794 -> hash 51ccc178 queue 0
sport 10986 -> hash 5450558d queue 1
hashes differ: True, queues differ: True
```

Every `OK` confirms the pure-Python hash reproduces hardware-verified values — the same numbers a real 82599/Niantic-class NIC computes in silicon. The sensitivity check shows why RSS needs full 4-tuple entropy: one flipped bit of the source port completely changes hash and queue.

## Interview questions

1. **"Where does DPDK get physically contiguous DMA memory in user space?"** EAL mmaps hugepage segments at init (VA==PA when running without an IOMMU, or IOVA-mapped through VFIO/IOMMU), and mempools carve per-socket memzones from them; mbuf pool buffers therefore have stable DMA addresses for the NIC's descriptor rings.
2. **"Why did VFIO displace UIO for production?"** UIO gives register access and interrupts but no DMA containment — a mis-programmed descriptor can write anywhere. VFIO wraps devices in IOMMU groups with per-device IOVA pinning, plus eventfd interrupts; `igb_uio` survives only as out-of-tree (dpdk-kmods).
3. **"Why is the RX queue a per-core structure, and what breaks if two cores share one?"** Descriptor indices, rearm, and the mbuf cache are core-local, so no locks; two cores on one queue would need synchronization on indices and would thrash the NIC's hot descriptor cache lines. Sharing is avoided by RSS spreading flows across queues, one lcore per queue.
4. **"You must terminate 20 Mpps with per-flow state — run-to-completion or pipeline?"** Run-to-completion if the whole lookup+rewrite fits in one core's budget per flow (RSS guarantees flow locality); pipeline if per-stage working sets or packet-transform chains exceed one core, accepting rte_ring handoff latency in exchange for per-stage cache vectoring.
5. **"When does a DPDK app deliberately route packets into the kernel?"** Control-plane: ARP/ICMP replies, management protocols, anything needing the kernel's socket ecosystem — via the TAP PMD or virtio-user/vhost-user shared-memory paths, keeping the hot data path entirely in user space.

## References

1. DPDK Programmer's Guide, "Environment Abstraction Layer": <https://doc.dpdk.org/guides/prog_guide/env_abstraction_layer.html> (HTTP 200).
2. DPDK Programmer's Guide, "Mempool Library" and "Mbuf Library": <https://doc.dpdk.org/guides/prog_guide/mempool_lib.html>, <https://doc.dpdk.org/guides/prog_guide/mbuf_lib.html> (HTTP 200).
3. DPDK Linux Getting Started Guide, system requirements (hugepages) and enabling functionality (VFIO/UIO binding): <https://doc.dpdk.org/guides/linux_gsg/sys_reqs.html>, <https://doc.dpdk.org/guides/linux_gsg/enable_func.html> (HTTP 200).
4. DPDK Programmer's Guide, "Toeplitz Hash Library" (rte_thash): <https://doc.dpdk.org/guides/prog_guide/toeplitz_hash_lib.html> (HTTP 200).
5. DPDK Ethernet Device Library (ethdev API): <https://doc.dpdk.org/guides/prog_guide/ethdev/index.html> and Performance Optimization Guidelines: <https://doc.dpdk.org/guides/prog_guide/perf_opt_guidelines.html> (HTTP 200).
6. DPDK NIC driver guides, TAP PMD and virtio PMD: <https://doc.dpdk.org/guides/nics/tap.html>, <https://doc.dpdk.org/guides/nics/virtio.html> (HTTP 200).
7. Kernel documentation, VFIO driver API: <https://docs.kernel.org/driver-api/vfio.html>; UIO howto: <https://docs.kernel.org/driver-api/uio-howto.html> (HTTP 200).
8. DPDK project site: <https://www.dpdk.org/> (HTTP 200).
