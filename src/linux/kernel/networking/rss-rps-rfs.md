# RSS, RPS, and RFS: Spreading Receive Processing Across CPUs

NAPI answers a *scheduling* question: when is a given RX queue drained? (That machine
lives in [the NAPI page](./napi-polling.md).) This page answers the *placement*
questions NAPI inherits: which RX queue a flow lands on, which CPU runs the softirq,
and which CPU hands the bytes to the application thread. Get any of the three wrong and
you pay in cross-CPU cache misses and IPIs; get all three right and a flow is touched by
one cache-coherent CPU from descriptor to `recv()`. The survey-level tour is in
[the netdev page](./netdev.md); here we go a level deeper, with knobs and arithmetic.

## Three placement decisions, one packet

```text
                     +------------------------------------------------+
                     |  NIC, multi-queue                              |
  wire ------------->|  RSS: Toeplitz hash -> indirection table       |
                     +--------+----------------+----------------+-----+
                              |                |                |
                         RX queue 0       RX queue 1       RX queue 2
                              |                |                 (1) which queue?
                         MSI-X vec 37     MSI-X vec 38     MSI-X vec 39
                              |                |                 (2) which CPU irq?
                        smp_affinity:    smp_affinity:    smp_affinity:
                            CPU 2            CPU 3            CPU 4
                              |                |                |
                          napi poll        napi poll        napi poll
                              |                |                 (3) when? NAPI
                     +--------v----------------v----------------v-----+
                     | RPS: hash mod rps_cpus mask -> backlog + IPI   |
                     | RFS: sock_flow_table[flow] -> consumer CPU     |
                     |                                    (4) which CPU app?
                     +------------------------------------------------+
```

RSS decides (1) in silicon. With nothing else configured, (2) and (4) follow blindly:
the queue's irq is handled wherever affinity says, and the packet is processed and
consumed there -- or not, if the application thread lives elsewhere. RPS and RFS are
the software overlays that fix (2) and (4) when the hardware's view (flow -> queue) and
the scheduler's view (thread -> CPU) disagree.

## RSS: the hash engine in the NIC

The NIC hashes the network and transport headers -- for TCP and UDP, the 4-tuple of
source/destination IPs and ports -- and uses the result to pick an RX queue. The
dominant algorithm is the **Toeplitz hash**: a keyed hash over the packet bytes, with a
secret key of **40 bytes (320 bits)** that both sides of the config must agree on. NDIS
specifies `NdisHashFunctionToeplitz` with reference pseudocode for its four hash input
types, and it is the only hardware hash function you will meet in practice. The 32-bit
result rides in with the descriptor; drivers store it in `skb->hash`, where the rest of
the stack reuses it (tc classifiers see it as `skb->hash` too -- see
[the tc-BPF page](./tc-bpf.md)). One hash, many consumers.

The queue is *not* `hash % n_queues`. The NIC indexes an **indirection table** with the
low bits of the hash; each entry stores a queue number, and the table is programmable
at runtime (`ethtool -X` sets table, `hkey`, `hfunc toeplitz`; `ethtool -L eth0
combined N` sets queue count; the ethtool-netlink API exposes the same state as
`ETHTOOL_MSG_RSS_GET/SET`). Two consequences worth saying out loud in an interview:

- With a round-robin default table and a power-of-two queue count, every queue gets the
  same number of hash slots, so *flow counts* even out almost perfectly (demo below).
  Real imbalance comes from *packet-rate* skew -- elephant flows -- and from queue
  counts that do not divide the table: the kernel doc recommends a table at least 4x
  the queue count and notes that 4x still leaves ~16% worst-case imbalance.
- **Symmetric RSS** (`Symmetric-XOR`, `Symmetric-OR-XOR`) XORs/ORs source and
  destination fields before hashing, so both directions of a flow land on one queue/CPU
  -- valuable for IDS and firewalls, paid for in reduced input entropy (an attacker who
  knows the scheme can aim traffic). The key itself is configurable; randomizing it at
  driver init makes placement unpredictable to senders.

## RPS: the same trick in software

RPS is "logically a software implementation of RSS" (kernel docs) and runs when the
driver hands a packet up through `netif_rx()`/`netif_receive_skb()`. `get_rps_cpu()`
takes the flow hash -- the hardware Toeplitz value if the descriptor carried one,
otherwise a stack-computed 2-tuple/4-tuple hash -- and picks a CPU from the per-queue
bitmap, placing the packet on the tail of that CPU's backlog queue. At the end of the
current bottom half, one IPI per remote CPU that received packets wakes its backlog
processing -- per CPU per softirq run, not per packet.

```
/sys/class/net/eth0/queues/rx-0/rps_cpus        # CPU bitmap; 0 = disabled (default)
```

RPS compiles in with `CONFIG_RPS` (on by default for SMP) but does nothing until
`rps_cpus` is set. Its selling points: works on any NIC including single-queue parts,
can hash protocols the hardware does not know, and does not raise the hardware irq rate
(the hardirq stays on one line). The cost: every remotely-enqueued packet is a backlog
hop and a cold cache away from where it will be consumed -- the gap RFS closes.

## RFS: steering to the application

RFS's stated goal is to "increase datacache hitrate by steering kernel processing of
packets to the CPU where the application thread consuming the packet is running." RPS
spreads load; RFS aims it, with two soft-state tables:

| Table | Scope | Maps | Written by |
|---|---|---|---|
| `rps_sock_flow_table` | global | flow -> *desired* CPU | `inet_recvmsg()`, `inet_sendmsg()`, `tcp_splice_read()` |
| `rps_dev_flow_table` | per RX queue | flow -> *current* CPU + backlog tail counter | receive path |

Per packet, `get_rps_cpu()` compares both tables. If the desired CPU equals the current
one, the packet goes there. If they differ, the flow migrates only when the old CPU has
nothing outstanding: the recorded tail counter is below the old CPU's head counter, or
the recorded CPU is unset or offline. That is the out-of-order guard -- a flow never
moves with packets still in flight on the previous CPU, because those in-flight packets
would arrive after packets already processed on the new CPU.

Sizing (kernel doc guidance, both values rounded up to powers of two):

```
/proc/sys/net/core/rps_sock_flow_entries              # global table
/sys/class/net/eth0/queues/rx-N/rps_flow_cnt          # per-queue table
```

Size the global table to concurrently *active* flows -- 65536 works well on a moderately
loaded server, big servers want 1048576 or more -- then give each of N queues roughly
`rps_sock_flow_entries / N` (e.g. 131072 total, 16 queues, 8192 per queue). On NUMA
hosts, allocate the global table interleaved (`numactl --interleave=all`). A flow not
tracked -- table too small, entry evicted -- falls back to plain RPS placement: RFS
degradation is silent, packets still arrive, just on the wrong CPU.

**Accelerated RFS** is "to RFS what RSS is to RPS": the stack pushes the flow->CPU
decision into the NIC by calling the driver's `ndo_rx_flow_steer()` whenever the dev
flow table updates a flow; the driver programs an ntuple filter so packets land directly
on the queue whose irq CPU is local to the consumer. The CPU-to-queue map is derived
from the IRQ affinities via the `cpu_rmap` library. Requirements: `CONFIG_RFS_ACCEL`,
driver support, and ntuple filtering on (`ethtool -K eth0 ntuple on`). In-tree since
2.6.35.

## Numbers: indirection spread and RFS locality

The model uses a 32-bit FNV-1a over the 4-tuple as a stand-in for Toeplitz (only output
uniformity matters for spreading), routes flows through a 128-entry indirection table,
then models an 8-queue/8-app-CPU host where thread `t` is pinned to CPU `t`. The RFS
part counts how often a packet is processed on its consumer's CPU: with RSS alone that
is 1/8 in expectation, because queue placement (hash) and thread placement (epoll
accept order) are independent. Cost model: 0.8 us of extra latency per non-local
delivery (IPI plus cold caches; a modeling constant, not a measurement).

```python
import random, struct

N_FLOWS, INDIR, QUEUES = 100_000, 128, 8
CROSS_CPU_US, TABLE_TOTAL = 0.8, 32_768   # us per non-local delivery; sock flow entries

def flow_hash(t):
    """32-bit FNV-1a over the 4-tuple: stand-in for the Toeplitz hash the
    NIC computes over the same fields. Only uniformity matters here."""
    data = struct.pack("!IIHH", *t)
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h

rng = random.Random(49)
flows = [(rng.getrandbits(32), rng.getrandbits(32),
          1 + rng.getrandbits(15), 1 + rng.getrandbits(15)) for _ in range(N_FLOWS)]
hashes = [flow_hash(f) for f in flows]

print("== RSS indirection spread (%d flows, %d-entry table, queue = indir[hv & 127]) =="
      % (N_FLOWS, INDIR))
for k in (1, 2, 4, 8, 16):
    indir = [i % k for i in range(INDIR)]        # default table: round-robin
    counts = [0] * k
    for hv in hashes:
        counts[indir[hv & (INDIR - 1)]] += 1
    imb = (max(counts) / (N_FLOWS / k) - 1.0) * 100.0
    detail = counts if k <= 4 else "min %d max %d" % (min(counts), max(counts))
    print("  k=%2d queues: %-40s max-load imbalance %5.2f%%" % (k, detail, imb))

print()
print("== RFS flow->CPU locality model (%d queues / %d app CPUs / %d active flows) =="
      % (QUEUES, QUEUES, N_FLOWS))
owner = [i % QUEUES for i in range(N_FLOWS)]     # thread t pinned to CPU t
p_tracked = min(1.0, TABLE_TOTAL / N_FLOWS)
situations = (("RSS-only", [False] * N_FLOWS),
              ("RFS, %d entries" % TABLE_TOTAL,
               [hv % 10_000 < p_tracked * 10_000 for hv in hashes]),
              ("RFS, sized to workload", [True] * N_FLOWS))
for name, is_tracked in situations:
    remote = sum(1 for i, hv in enumerate(hashes)
                 if (owner[i] if is_tracked[i] else hv & (QUEUES - 1)) != owner[i])
    cost = remote / N_FLOWS * 1_000_000 * (CROSS_CPU_US / 1e6)   # per 1M packets
    print("  %-26s %6.2f%% packets on consumer CPU   non-local cost %.2f s per 1M pkts"
          % (name, (N_FLOWS - remote) / N_FLOWS * 100.0, cost))
```

Output (deterministic; seed 49):

```text
== RSS indirection spread (100000 flows, 128-entry table, queue = indir[hv & 127]) ==
  k= 1 queues: [100000]                                 max-load imbalance  0.00%
  k= 2 queues: [50138, 49862]                           max-load imbalance  0.28%
  k= 4 queues: [24946, 24884, 25192, 24978]             max-load imbalance  0.77%
  k= 8 queues: min 12408 max 12609                      max-load imbalance  0.87%
  k=16 queues: min 6164 max 6372                        max-load imbalance  1.95%

== RFS flow->CPU locality model (8 queues / 8 app CPUs / 100000 active flows) ==
  RSS-only                    12.55% packets on consumer CPU   non-local cost 0.70 s per 1M pkts
  RFS, 32768 entries          41.17% packets on consumer CPU   non-local cost 0.47 s per 1M pkts
  RFS, sized to workload     100.00% packets on consumer CPU   non-local cost 0.00 s per 1M pkts
```

Read the halves differently. Top half: hardware spreading is near-perfect for *flow
counts* at power-of-two queue counts -- the 0.3-2% is hash noise; your real risk is
rate skew and non-power-of-two queue counts, not the hash. Bottom half, the RFS pitch
in one line: RSS-only placement leaves ~87% of packets processing one hop from their
consumer (~0.7 s of accumulated penalty per million packets at the modeled 0.8 us); an
undersized flow table (32768 entries against 100k active flows) recovers only part of
the gap (41% local) because untracked flows silently fall back to RSS placement. Size
the table to concurrent active flows, not to open connections.

## XPS: the transmit mirror

XPS applies the same idea to TX: the per-TX-queue bitmap at
`/sys/class/net/eth0/queues/tx-N/xps_cpus` pins each queue's transmit work to a CPU set,
so allocation, segmentation, and completion processing stay cache-local and TX queue
locks stay off shared CPUs. The naming is the giveaway: `rps_cpus`/RFS steer receive,
`xps_cpus` steers transmit. Configured via sysfs.

## Interactions worth knowing

- **NAPI**: RSS fans queues out, NAPI drains each -- one `napi_struct` per MSI-X vector,
  each with its own budget, with the global `net.core.netdev_budget` capping softirq
  work per CPU. The budget arithmetic is on [the NAPI page](./napi-polling.md).
- **Busy polling**: `SO_BUSY_POLL` bypasses the irq path by spinning in the socket
  layer; it changes *when* queues drain, not *which* CPU -- orthogonal to steering
  (same NAPI page, mixed-mode section).
- **GRO**: coalesced super-frames follow RPS/RFS/XPS placement, so a bad steering
  config multiplies its cost by the coalescing factor
  ([offloads page](./rx-offloads-gro-gso-tso.md)).
- **Bonding**: a bond's TX spreading is governed by its own `xmit_hash_policy`
  (e.g. `layer3+4`) -- a separate hash from each slave's RSS engine; received traffic
  lands in slave queues where RSS/RPS apply as usual ([bonding page](./bonding.md)).
- **AF_XDP**: sockets bind to one RX queue id, so RSS must steer the target flows to
  that queue or packets land in the kernel stack instead of your ring
  ([AF_XDP internals](./af-xdp-internals.md)).
- **Load balancing**: RSS is in-host ECMP -- same flow-affinity and consistent-hash
  concerns as an L4 balancer, one machine down
  ([L4 load balancing](../../../networks/advanced/l4-load-balancing-internals.md)).

## Tuning pitfalls

1. **Single-queue NIC**: no RSS to configure; `rps_cpus` is the only spreading lever,
   but the single irq line still pins every interrupt to one CPU -- spread the backlog,
   not the irq.
2. **Flow counts too small**: `rps_sock_flow_entries` below the active-flow count makes
   RFS silently degrade to RPS; measure concurrent active flows, not listen-queue depth.
   Per-queue `rps_flow_cnt` values that do not sum to the global table waste entries or
   starve queues; start at the doc's `rps_sock_flow_entries / N` and watch the
   power-of-two rounding.
3. **irqbalance fights**: the daemon "may override any manual settings" (kernel doc
   wording), rewriting `/proc/irq/*/smp_affinity` and undoing a hand-tuned layout
   mid-run. Stop it or restrict its scope before tuning.
4. **Cross-NUMA steering**: pointing `rps_cpus` outside the interrupting CPU's memory
   domain buys latency for nothing; the kernel doc's single-queue suggestion is the same
   memory domain.
5. **Assuming RSS buys application locality**: RSS evens queues; only RFS/aRFS tracks
   where the consumer runs. Pinning irqs and threads to matching CPUs approximates RFS
   only while the scheduler cooperates.

## Interview questions

1. A server's 4-RX-queue NIC shows one queue at 90% utilization. Two causes and fixes?
   (Few flows relative to queues or a skewed indirection table -> resize with
   `ethtool -X`; elephant flows -> the table cannot fix rate skew, use aRFS/flow steer.)
2. Why does RFS need two tables? (Desired CPU comes from the socket layer, current CPU
   from the receive path; comparing them plus the tail-counter check migrates a flow
   only when the old CPU is drained, preventing reordering.)
3. What does RPS cost that RSS does not? (Backlog queueing plus IPIs and a cold cache on
   the target CPU; RSS places packets at the hardware irq, before any queueing.)
4. How does `skb->hash` get set, and who consumes it? (NIC Toeplitz hash passed in the
   descriptor, or computed in software by `get_rps_cpu()`; consumed by RPS/RFS and
   available to tc/BPF and stack hashing.)
5. You enable aRFS and see no effect. Checklist? (`CONFIG_RFS_ACCEL` in the kernel,
   driver support, `ethtool -K eth0 ntuple on`, sane irq affinities -- the CPU->queue
   map is derived from them.)

## References

- [Scaling in the Linux networking stack](https://docs.kernel.org/networking/scaling.html)
  -- normative source for RSS, RPS, RFS, aRFS, XPS, sysfs/sysctl names, sizing guidance.
- [ethtool(8) man page](https://man7.org/linux/man-pages/man8/ethtool.8.html)
  -- `-X`/`--set-rxfh-indir` (indirection table, `hkey`, `hfunc`), `-L`/`--set-channels`.
- [RSS Hashing Functions (Microsoft WDK docs)](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/rss-hashing-functions)
  -- Toeplitz definition and the 40-byte (320-bit) key.
- [Introduction to Receive Side Scaling (Microsoft WDK docs)](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/introduction-to-receive-side-scaling)
  -- indirection table model and hash types from the spec side.
- [NVIDIA mlx5 driver guide (DPDK)](https://doc.dpdk.org/guides/nics/mlx5.html)
  -- NIC-driver view of RSS dispatch and indirection on ConnectX hardware.
- [Receive packet steering (LWN, Oct 2009)](https://lwn.net/Articles/362339/)
  -- Tom Herbert's original RPS/RFS patch series, with the IPI/backlog rationale.
- [NAPI documentation](https://docs.kernel.org/networking/napi.html)
  -- the scheduling layer this page's steering feeds into.
- [Receive Packet Steering (Red Hat Performance Tuning Guide)](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/6/html/performance_tuning_guide/network-rps)
  -- RPS/RFS configuration walkthrough (site blocks scripted fetches; content verified
  via search index).
