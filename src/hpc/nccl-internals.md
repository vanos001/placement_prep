# NCCL Internals: Topology Discovery, Channels, and Protocols

NCCL (NVIDIA Collective Communications Library, pronounced "Nickel") calls itself "optimized
primitives for inter-GPU communication ... optimized to achieve high bandwidth on platforms
using PCIe, NVLink, NVswitch, as well as networking using InfiniBand Verbs or TCP/IP sockets"
(NCCL GitHub README). The interview-worthy part is not the API -- `ncclAllReduce` and friends
are thin -- but the machinery between the call and the wire: a discovered world model, a graph
search that turns it into parallel rings, and a three-protocol pipeline trading bandwidth for
latency. Facts are checked against the NCCL 2.31 docs and the GitHub sources (`src/graph/`,
`src/device/`, `src/include/device.h`, `src/proxy.cc`, `src/transport/bootstrap.cc`).

Scope split: what each collective *is* and the ring schedule live in
[Collective Communication](./collective-communication.md) and
[Ring AllReduce](../llm/advanced/distributed/ring-allreduce.md); the fabric in
[NVLink and NVSwitch](./nvlink-nvswitch.md); RDMA/SHARP economics in
[GPUDirect Networking](./gpudirect-networking.md). This page owns the library internals.

## 1. From API call to wire

```text
ncclAllReduce(buf, ..., comm)
   |  enqueue: work recorded on the calling stream (CUDA-graph capture aware)
   v
[1] plan lookup .... per-size algorithm/protocol choice, precomputed by graph search
[2] GPU kernels .... one CUDA block per channel; CTAs copy/reduce chunks hop to hop
[3] proxy thread ... one CPU thread per communicator (ncclProxyProgress) drives
                     IB verbs / sockets / SHM moves the GPU cannot do itself
   v
wire: NVLink/PCIe P2P  |  shared memory  |  IB verbs / TCP sockets
```

A communicator is built once per process group: ranks bootstrap over TCP (the root advertises
`NCCL_COMM_ID` in `<ipv4>:<port>` form, parsed in `src/transport/bootstrap.cc`), exchange
topology and connection info, run detection plus graph search, then connect transports. The
data plane is separate from the bootstrap plane, so an init hang is rarely a data-plane fault.

## 2. Topology detection: the XML world model

NCCL does not trust `cudaDeviceCanAccessPeer` alone. At init it builds an XML system model:

- Preferred source: the platform XML from `nvidia-topologyd`, loaded by default from
  `/var/run/nvidia-topologyd/virtualTopology.xml`; `NCCL_TOPO_FILE` (2.6+) overrides it,
  `NCCL_TOPO_DUMP_FILE` writes the post-detection tree back out.
- Detection completes the picture with a PCI bus walk, NVML (NVLink status, peer validation --
  `src/graph/paths.cc` checks `NVML_P2P_STATUS_OK`), CPU affinity, and a verbs probe of each HCA.
- Devices are typed CPU / PCI / GPU / NIC / NET, and every pair gets a *path type* -- the unit
  NCCL reasons in (`PATH_*` enums in `src/graph/paths.cc`):

| Path type | Meaning | Typical transport consequence |
|-----------|---------|-------------------------------|
| PATH_NVL | NVLink hop(s) | CUDA P2P |
| PATH_C2C | die-to-die CPU interconnect (Grace) | P2P / SHM |
| PATH_PIX | GPUs under one PCI switch | CUDA P2P |
| PATH_PXB | through PCI switches, same host bridge | CUDA P2P |
| PATH_PHB | crosses a CPU host bridge | SHM, or P2P if supported |
| PATH_SYS | crosses both CPU sockets | SHM |
| PATH_PXN | NIC reached via NVLink through an intermediate GPU | inter-node send via local GPU |
| PATH_DIS | disabled (e.g. P2P administratively off) | fall back down the ladder |

- Transport selection follows the ladder: CUDA P2P where the path allows, then shared memory --
  used "between devices when peer-to-peer cannot happen" (`NCCL_SHM_DISABLE` docs) -- then the
  network. `NCCL_P2P_LEVEL` and `NCCL_NET_GDR_LEVEL` (2.3.4+) take these path types as cutoffs;
  the latter decides when a NIC may DMA straight into GPU memory.

## 3. Channels, CTAs, and the proxy thread

NCCL never runs one ring per communicator. It builds **channels**: independent copies of the
schedule, each with its own buffers, connection fifos, and CUDA blocks. `MAXCHANNELS` is 64
(`src/include/device.h`).

- The graph search (`src/graph/search.cc`) scores candidate rings on the XML model's bandwidth
  numbers, maximizes the bottleneck, then replicates the winner into multiple channels.
- On rail-optimized clusters each channel maps to one NIC per node so egress adds up;
  `NCCL_CROSS_NIC` (default 0) "tries to use the same NICs when communicating between nodes, to
  allow for a network design where each NIC on a node connects to a different network switch
  (network rail)" (NCCL docs).
- Channels cost SMs: "NCCL will launch one CUDA block per communication channel" with
  `NCCL_NTHREADS` threads (cap `NCCL_MAX_NTHREADS = 640`), so every collective occupies SMs and
  competes with compute. The docs cap CTA counts by default on GPU-heavy platforms ("Increasing
  the number of CTAs will consume more GPU resources but possibly increase throughput");
  `NCCL_MIN/MAX_NCHANNELS` were deprecated (2.17) for `NCCL_MIN/MAX_CTAS` -- channels and CTAs
  are one budget now. On sm90+, `NCCL_CGA_CLUSTER_SIZE` (2.16) groups blocks into CUDA
  thread-block clusters for L2/SMEM locality.
- Network progress is CPU-side: a single proxy thread per communicator (`ncclProxyProgress`,
  `src/proxy.cc`) posts verbs work, polls completions, and services SHM/net chunk moves; GPU
  kernels hand data to it through per-connection fifos.

## 4. Algorithms: ring vs double-binary tree, plus the in-network family

| Version | Algorithm | In-network reduction? |
|---------|-----------|-----------------------|
| 2.5+    | Ring      | no |
| 2.5+    | Tree (double-binary) | no |
| 2.5-2.13 | Collnet  | IB SHARP via plugin |
| 2.14+   | CollnetChain, CollnetDirect | IB SHARP via plugin |
| 2.17+   | NVLS      | NVSwitch (NVLink SHARP) |
| 2.18+   | NVLSTree  | NVSwitch, chained across nodes |
| 2.23+   | PAT       | no (pattern-based, huge rank counts) |

The two point-to-point workhorses have complementary costs. Ring allreduce moves
`2(n-1)/n * m` bytes per GPU in `2(n-1)` latency hops -- bandwidth-optimal, latency linear in
`n`. Tree allreduce (double-binary tree, `src/graph/trees.cc`) pays more bandwidth for only
`O(log n)` hops. The trees.cc tree makes ranks "alternate leaves and nodes"; the second tree is
a mirror (even rank counts) or a one-rank shift (odd), so for even `n` every rank sends in one
tree while it receives in the other.

Early NCCL picked between them with byte thresholds (`NCCL_SINGLE_RING_THRESHOLD`,
`NCCL_LL_THRESHOLD`, `NCCL_TREE_THRESHOLD` -- removed in 2.3 / 2.5 / 2.5). Since 2.5 the choice
comes from the graph-search time model evaluated per message size on the detected topology;
that is also why the docs discourage setting `NCCL_ALGO` / `NCCL_PROTO` -- both exist mainly to
*exclude* a suspected-broken path (prefix `^`). `NCCL_NVLS_ENABLE` (2.17, default 2) enables
NVLink SHARP -- "available in third-generation NVSwitch systems (NVLink4) with Hopper and later
GPU architectures, allowing collectives such as ncclAllReduce to be offloaded to the NVSwitch
domain" -- with `NVLSTree` chaining islands across nodes; NVLS rejects MIG slices and
multiple-ranks-per-GPU (fabric side in [NVLink and NVSwitch](./nvlink-nvswitch.md), IB SHARP /
`NCCL_COLLNET_ENABLE` analog in [GPUDirect Networking](./gpudirect-networking.md)).

## 5. Protocols: Simple, LL, LL128

Each algorithm runs over one of three wire protocols (`NCCL_PROTO` values `LL`, `LL128`,
`Simple`; default "LL,LL128,Simple on platforms which support LL128, and LL,Simple otherwise"):

| Protocol | Wire format per line | Efficiency | Regime |
|----------|----------------------|------------|--------|
| LL | 16 B line = 2 x (4 B data + 4 B flag) words (`union ncclLLFifoLine`, `src/device/prims_ll.h`) | 50% | tiny latency-bound ops, any fabric |
| LL128 | 128 B line, 15 of 16 8-byte words are data (120 B), one flag thread per line (`NCCL_LL128_LINESIZE/LINEELEMS/DATAELEMS`, `src/include/device.h`) | 93.75% | NVLink-class fabrics, small/mid messages |
| Simple | raw chunked copy+reduce | ~100% | large messages |

- LL/LL128 receivers spin on flag words instead of completion handshakes -- the latency win,
  paid in bandwidth and in LL128's strict platform support: "enabling LL128 on platforms that
  don't support it can lead to data corruption" (docs).
- Simple chunks through ring buffers of `NCCL_STEPS = 8` slots per connection; the default
  buffer is 4 MiB (`DEFAULT_BUFFSIZE = (1 << 22)`, `src/init.cc`; `NCCL_BUFFSIZE`).
- `NCCL_P2P_LL_THRESHOLD` (2.14) caps the message size using LL for P2P operations.

## 6. Multi-node: bootstrap, verbs, rails

- Bootstrap is TCP-only: root listens, ranks connect via `NCCL_COMM_ID`, and the bootstrap
  allgather exchanges unique IDs and topology. Firewalls or wrong interfaces surface as init
  hangs before the first collective.
- Data plane is IB verbs (RC queue pairs) or TCP sockets. Addressing (source-verified): for
  RoCE, NCCL programs the address handle's global route header -- destination GID, source GID
  index from `NCCL_IB_GID_INDEX`, hop limit 255, traffic class from `NCCL_IB_TC` (`ah_attr.grh`
  in `src/transport/net_ib.cc`); with the index unset (2.21+) the GID is picked dynamically per
  `NCCL_IB_ADDR_FAMILY` / `NCCL_IB_ADDR_RANGE`.
- QPs scale with the fabric: `NCCL_IB_QPS_PER_CONNECTION` (2.10) is "useful on multi-level
  fabrics which need multiple queue pairs to have good routing entropy";
  `NCCL_IB_SPLIT_DATA_ON_QPS` (2.18) picks per-message split vs round-robin;
  `NCCL_IB_ADAPTIVE_ROUTING` (2.16) opts into AR-capable service levels;
  `NCCL_IB_MERGE_NICS` (2.20) aggregates dual-port NICs.
- Rail-optimized fabrics pair GPU *i* with the NIC on rail *i*; channels stay on one rail.
  PXN (2.12, `NCCL_P2P_PXN_LEVEL` default 2) sends via "a non-local NIC, using NVLink and an
  intermediate GPU" so a rank reaches its destination rail through NVLink, not a long PCIe path.
  `NCCL_IB_DISABLE` falls back to IP sockets; `NCCL_MNNVL_ENABLE` (2.21) extends the NVLink
  domain across racks on NVL72-class systems (needs an IMEX domain).

## 7. Tuning and hang forensics

Env knobs that matter (all from the NCCL env docs):

| Variable | Since | Effect |
|----------|-------|--------|
| NCCL_DEBUG | 2.0 | VERSION / WARN / INFO / TRACE ladder |
| NCCL_DEBUG_SUBSYS | 2.3.4 | filter INFO by subsystem (INIT, NET, GRAPH, ...); `^` inverts |
| NCCL_DEBUG_FILE | 2.2.12 | log to file with %h / %p substitution |
| NCCL_ALGO / NCCL_PROTO | 2.5 | restrict or exclude algorithms / protocols |
| NCCL_NVLS_ENABLE | 2.17 | NVLS offload, default 2 (auto) |
| NCCL_MAX_CTAS / NCCL_MIN_CTAS | 2.17 | CTA budget (replaces NCCL_MAX/MIN_NCHANNELS) |
| NCCL_BUFFSIZE | 2.0 | Simple buffer, default 4 MiB |
| NCCL_P2P_LEVEL / NCCL_NET_GDR_LEVEL | 2.3.4 | path-type cutoffs for P2P / GPUDirect |
| NCCL_CROSS_NIC | 2.0 | 0 keeps rings rail-pinned across nodes |
| NCCL_SOCKET_IFNAME | 2.0 | bootstrap interface filter (containers: set it) |
| NCCL_IB_GID_INDEX / NCCL_IB_TC | 2.1.4 / 2.1.15 | RoCE GID / traffic class |
| NCCL_TOPO_FILE / NCCL_TOPO_DUMP_FILE | 2.6 | override / dump the XML topology |

Hang taxonomy, ordered by frequency:

1. **Rank divergence.** A rank runs a different collective sequence (data-dependent control
   flow, missing `ncclGroupEnd`); all ranks block. With `NCCL_DEBUG=INFO` the last collective
   printed per rank shows where they disagree. NCCL itself imposes no collective timeout;
   frameworks add one -- PyTorch's watchdog knobs `TORCH_NCCL_ASYNC_ERROR_HANDLING` (default 3),
   `TORCH_NCCL_BLOCKING_WAIT`, and `TORCH_NCCL_DESYNC_DEBUG` are read in
   `ProcessGroupNCCL.cpp`.
2. **Bootstrap blocked.** Firewall drops the root port or containers bind the wrong interface;
   the job hangs (or times out) before any collective completes. Fix `NCCL_SOCKET_IFNAME` /
   `NCCL_COMM_ID` reachability.
3. **Fabric silently degraded.** IB link down or wrong GID (`show_gids`), IOMMU/ACS stripping
   P2P, one rank with `NCCL_P2P_DISABLE=1` while peers differ. Either busbw collapses or the
   first large message wedges.
4. **Protocol/platform mismatch.** Forcing LL128 on unsupported hardware can corrupt data
   (docs warning); forcing an unavailable in-network algorithm fails communicator setup.

Bisect with `nccl-tests` (`all_reduce_perf -b 8 -e 256M -f 2 -g 8`): it reports time, algbw,
and busbw, where busbw applies the `2(n-1)/n` correction so allreduce numbers compare against
fabric peak regardless of rank count (nccl-tests PERFORMANCE.md).

## 8. Two recomputable models

Demo 1 (MODEL): the alpha-beta model behind section 4 -- ring
`2(p-1)/p * m/B + 2(p-1) * a` vs double-binary tree `2*d * (m/(2B) + a)`, `d = ceil(log2 p)`
(two phases, half the message per tree, one latency per level).

```python
import math


def ring_time(m, p, B, a):
    return 2 * (p - 1) / p * m / B + 2 * (p - 1) * a


def dbt_time(m, p, B, a):
    d = math.ceil(math.log2(p))
    return 2 * d * (m / (2 * B) + a)


def crossover(p, B, a):
    # solve 2(p-1)/p * m/B + 2(p-1)a = d*m/B + 2*d*a  for m
    d = math.ceil(math.log2(p))
    num = 2 * a * (d - (p - 1))
    den = 2 * (p - 1) / p - d
    return num / den * B if den < 0 else float("inf")


SCEN = [
    ("NVSwitch island p=8, a=2us, B=450GB/s", 8, 450e9, 2e-6),
    ("PCIe island     p=8, a=8us, B=32GB/s", 8, 32e9, 8e-6),
    ("IB multi-node p=64, a=5us, B=50GB/s", 64, 50e9, 5e-6),
]
MSGS = [64 * 1024, 1 << 20, 16 << 20, 512 << 20]

print("Predicted allreduce time (ms); winner marked; crossover m* below")
print("%-39s %9s %9s %9s %9s" % ("Scenario", "64KiB", "1MiB", "16MiB", "512MiB"))
for name, p, B, a in SCEN:
    cells = []
    for m in MSGS:
        tr, tt = ring_time(m, p, B, a), dbt_time(m, p, B, a)
        cells.append("%.3f%s" % (min(tr, tt) * 1e3, "R" if tr <= tt else "T"))
    print("%-39s %9s %9s %9s %9s" % (name, *cells))
print()
for name, p, B, a in SCEN:
    m = crossover(p, B, a)
    print("%-39s m* = %s" % (name, "--" if m == float("inf") else "%.2f MB (ring faster above)" % (m / 1e6)))
```

Real output:

```text
Predicted allreduce time (ms); winner marked; crossover m* below
Scenario                                    64KiB      1MiB     16MiB    512MiB
NVSwitch island p=8, a=2us, B=450GB/s      0.012T    0.019T    0.093R    2.116R
PCIe island     p=8, a=8us, B=32GB/s       0.054T    0.146T    1.030R   29.472R
IB multi-node p=64, a=5us, B=50GB/s        0.068T    0.186T    1.291R   21.769R

NVSwitch island p=8, a=2us, B=450GB/s   m* = 5.76 MB (ring faster above)
PCIe island     p=8, a=8us, B=32GB/s    m* = 1.64 MB (ring faster above)
IB multi-node p=64, a=5us, B=50GB/s     m* = 7.07 MB (ring faster above)
```

Read as a model, not a benchmark: the latency terms (`2*d*a` vs `2(p-1)*a`) make trees win
small messages, the bandwidth terms (`d*m/B` vs `2(p-1)/p * m/B`) make rings win big ones, and
the crossover scales with the fabric's latency-bandwidth product -- the same trade NCCL's
graph search re-derives per message size.

Demo 2 (MODEL): the double-binary tree construction, ported from `src/graph/trees.cc`
(`ncclGetBtree` / `ncclGetDtree`) and checked against its invariants.

```python
# Port of NCCL src/graph/trees.cc: ncclGetBtree + ncclGetDtree.


def btree(n, r):
    """One binary tree: root 0, ranks alternate leaves and nodes."""
    bit = 1
    while bit < n and not (bit & r):
        bit <<= 1
    if r == 0:
        return -1, (-1, (bit >> 1) if n > 1 else -1)
    up = (r ^ bit) | (bit << 1)
    if up >= n:
        up = r ^ bit
    lo = bit >> 1
    d0 = r - lo if lo else -1
    d1 = r + lo if lo else -1
    while d1 >= n:
        lo >>= 1
        d1 = r + lo if lo else -1
    return up, (d0, d1)


def dtree(n, r):
    """Second tree: mirror ranks (even n) or shift by one (odd n)."""
    b0 = btree(n, r)
    if n % 2:
        u, (d0, d1) = btree(n, (r - 1 + n) % n)
        f = lambda x: -1 if x == -1 else (x + 1) % n
    else:
        u, (d0, d1) = btree(n, n - 1 - r)
        f = lambda x: -1 if x == -1 else n - 1 - x
    return b0, (f(u), (f(d0), f(d1)))


for p in (8, 9):
    pairs = [dtree(p, r) for r in range(p)]
    kids = [[[] for _ in range(p)] for _ in range(2)]
    for t in (0, 1):
        for r in range(p):
            if pairs[r][t][0] != -1:
                kids[t][pairs[r][t][0]].append(r)
    internal = [set(r for r in range(p) if kids[t][r]) for t in (0, 1)]
    assert internal[0] | internal[1] == set(range(p))  # no rank idle in both
    if p % 2 == 0:
        assert internal[0].isdisjoint(internal[1])     # even p: clean split
    print("p=%d (%s): internal tree0=%s tree1=%s"
          % (p, "mirror" if p % 2 == 0 else "shift", sorted(internal[0]), sorted(internal[1])))
    for r in range(p):
        ch0 = kids[0][r] if kids[0][r] else "leaf"
        ch1 = kids[1][r] if kids[1][r] else "leaf"
        print("  rank %d | tree0 parent %2d / %-11s | tree1 parent %2d / %-11s"
              % (r, pairs[r][0][0], ch0, pairs[r][1][0], ch1))
```

Real output:

```text
p=8 (mirror): internal tree0=[0, 2, 4, 6] tree1=[1, 3, 5, 7]
  rank 0 | tree0 parent -1 / [4]         | tree1 parent  1 / leaf
  rank 1 | tree0 parent  2 / leaf         | tree1 parent  3 / [0, 2]
  rank 2 | tree0 parent  4 / [1, 3]       | tree1 parent  1 / leaf
  rank 3 | tree0 parent  2 / leaf         | tree1 parent  7 / [1, 5]
  rank 4 | tree0 parent  0 / [2, 6]       | tree1 parent  5 / leaf
  rank 5 | tree0 parent  6 / leaf         | tree1 parent  3 / [4, 6]
  rank 6 | tree0 parent  4 / [5, 7]       | tree1 parent  5 / leaf
  rank 7 | tree0 parent  6 / leaf         | tree1 parent -1 / [3]
p=9 (shift): internal tree0=[0, 2, 4, 6, 8] tree1=[0, 1, 3, 5, 7]
```

The even-`p` table shows the partition: ranks 0/2/4/6 forward in tree0, 1/3/5/7 in tree1, so
no rank waits on itself and depth is `log2(p)` instead of `p` hops. The odd-`p` shift gives
rank 0 a role in both trees -- the asymmetry the mirror variant exists to avoid.

## 9. Cross-references and references

Related: [Ring AllReduce](../llm/advanced/distributed/ring-allreduce.md) (the schedule these
channels execute), [HPC Infrastructure](./hpc-infra.md) (scheduling whole islands), and
[Slurm Scheduling](./slurm-scheduling.md) (rank placement, GPU binding per job).

1. NCCL docs -- Environment Variables: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html
2. NCCL docs -- Overview (NCCL 2.31): https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/overview.html
3. NCCL docs -- Collective Operations: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/usage/collectives.html
4. NCCL GitHub repository (README, sources): https://github.com/NVIDIA/nccl
5. NCCL source -- src/graph/trees.cc (double-binary tree): https://github.com/NVIDIA/nccl/blob/master/src/graph/trees.cc
6. NCCL source -- src/include/device.h (MAXCHANNELS, NCCL_STEPS, LL128 line format): https://github.com/NVIDIA/nccl/blob/master/src/include/device.h
7. nccl-tests -- Performance page (busbw definition): https://github.com/NVIDIA/nccl-tests/blob/master/doc/PERFORMANCE.md
8. Hu, Shen, Bonato, Jeaugey et al., "Demystifying NCCL: An In-depth Analysis of GPU Communication Protocols and Algorithms": https://arxiv.org/abs/2507.04786
9. PyTorch source -- torch/csrc/distributed/c10d/ProcessGroupNCCL.cpp (watchdog env vars): https://github.com/pytorch/pytorch/blob/main/torch/csrc/distributed/c10d/ProcessGroupNCCL.cpp
