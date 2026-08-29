# NVLink and NVSwitch: GPU Interconnect Fabric

A single H100 spends most of its wire budget talking to other GPUs, not to the host: NVLink
provides 900 GB/s per GPU while its PCIe Gen5 x16 provides 64 GB/s per direction. An 8-GPU
training node is therefore really a small switched network with 8 hosts attached, and the
"network" inside it has its own generations, its own switch silicon, its own topology rules,
and its own failure modes. This page covers that fabric itself: NVLink 1 through 5 (with 6
previewed), the three-plus NVSwitch generations that turn point-to-point cables into an
all-to-all fabric, the DGX/GB200 topologies, copper-vs-optics tradeoffs, and what MIG, NCCL,
and multi-node scaling do to it. The algorithms that consume the fabric live in
[Collective Communication](./collective-communication.md); the RDMA path in and out of it
lives in [GPUDirect Networking](./gpudirect-networking.md).

## 1. One Number, Two Directions

Every NVLink generation is quoted one way: **total bidirectional bandwidth per GPU**. Because
each link is full duplex, the per-direction figure is half of the headline. A interviewer who
says "Hopper has 900 GB/s" and an interviewer who says "NVLink 5 has 1800 GB/s" are both
right -- and both quoting different things:

- NVLink 4 (Hopper): 900 GB/s aggregate = 450 GB/s in each direction = 18 links x 25 GB/s/dir.
- NVLink 5 (Blackwell): 1,800 GB/s aggregate = 900 GB/s in each direction = 18 links x 50 GB/s/dir.

| NVLink gen | GPU (arch, year)   | Links/GPU | Per-link (bidir) | Aggregate per GPU (bidir) | Per direction | PCIe x16, same era        |
|------------|--------------------|-----------|------------------|---------------------------|---------------|---------------------------|
| 1          | P100 (Pascal 2016) | 4         | 40 GB/s          | 160 GB/s                  | 80 GB/s       | Gen3: ~16 GB/s/dir        |
| 2          | V100 (Volta 2017)  | 6         | 50 GB/s          | 300 GB/s                  | 150 GB/s      | Gen3: ~16 GB/s/dir        |
| 3          | A100 (Ampere 2020) | 12        | 50 GB/s          | 600 GB/s                  | 300 GB/s      | Gen4: ~31.5 GB/s/dir      |
| 4          | H100 (Hopper 2022) | 18        | 50 GB/s          | 900 GB/s                  | 450 GB/s      | Gen5: 64 GB/s/dir         |
| 5          | B200 (Blackwell 2024) | 18     | 100 GB/s         | 1,800 GB/s                | 900 GB/s      | Gen5: 64 GB/s/dir         |
| 6 (prelim) | Rubin (announced)  | 36        | 100 GB/s         | 3,600 GB/s                | 1,800 GB/s    | Gen6: 256 GB/s/dir        |

Verification notes (the numbers above were checked against NVIDIA sources in Aug 2026):

- The current [NVLink page](https://www.nvidia.com/en-us/data-center/nvlink/) tabulates only
  generations 4-6 (900 / 1,800 / 3,600 GB/s per GPU, 18 / 18 / 36 links). The Pascal/Volta/Ampere
  rows were confirmed from older primary sources: NVIDIA's "Inside Pascal" blog (160 GB/s
  bidirectional), the V100 datasheet (300 GB/s), and the Ampere architecture whitepaper, which
  states A100 totals "600 GB/sec ... versus 300 GB/sec for Tesla V100".
- Ampere changed the link recipe: NVLink 3 delivers "25 GB/second bandwidth in each direction ...
  using only half the number of signal pairs per link" compared with Volta (A100 whitepaper);
  NVLink 4 halves the pairs again at the same 25 GB/s/dir per link (Hopper blog).
- NVIDIA's own comparison anchor: NVLink 4 "operating at 900 GB/sec ... 7x the bandwidth of
  PCIe Gen 5" (900 vs 128 GB/s bidirectional); NVLink 6 is "over 14x the bandwidth of PCIe Gen6".

## 2. NVSwitch: From Cable Mesh to Fabric Chip

NVLink 1/2 without a switch meant cable pairs: GPU0-GPU1, GPU0-GPU2, ... and a six-GPU Volta
node was already at the wiring limit. NVSwitch (2018) is a crossbar chip with NVLink ports on
both sides: plug every GPU into the switch layer and every GPU pair communicates at full
point-to-point NVLink speed, concurrently. NVIDIA's description of the first chip:

> "NVSwitch is a non-blocking device which has 18-NVLink ports at 51.5 GBps per port and 928
> GBps aggregate bidirectional bandwidth." -- NVIDIA Technical Blog, "NVSwitch Accelerates
> NVIDIA DGX-2" (2018)

| NVSwitch gen | Debut system            | NVLink gen | Fabric per 8-GPU island   | GPU domain      | All-to-all per GPU (bidir) |
|--------------|-------------------------|------------|---------------------------|-----------------|----------------------------|
| 1 (2018)     | DGX-2 (16x V100 32GB)   | 2          | crossbar chips, 18 ports, 928 GB/s each | 16 GPUs | 300 GB/s |
| 2 (2020)     | DGX A100                | 3          | 6 chips                   | 8 GPUs          | 600 GB/s                   |
| 3 (2022)     | DGX H100                | 4          | 4 chips, 64 ports, 13.6 Tb/s each | 8 GPUs (32 nodes via switch system) | 900 GB/s |
| 4 (2024-25)  | DGX B200 / GB200 NVL72  | 5          | 2 chips (B200); 18 chips (NVL72)  | 8 GPUs / 72 GPUs | 1,800 GB/s               |

The headline change per generation is not just bandwidth: gen 3 added in-fabric collectives
(multicast and SHARP in-network reduction), and gen 4 added the rack-scale 72-GPU domain.
Gen 2's fabric aggregate is "4.8 TB/s total bidirectional bandwidth (2.4 TB/s full-duplex)"
across six switches (A100 whitepaper) -- exactly 8 GPUs x 600 GB/s.

## 3. Three Islands, Three Topologies

The same eight GPUs can be wired into the fabric with very different switch counts, because
switch port counts grew faster than GPU link counts. All figures below are from the DGX user
guides (see references) plus simple arithmetic on link counts.

```text
DGX A100 island: 8 A100 x 12 NVLink3 links = 96 GPU links -> 6 NVSwitches
  (96 links / 6 switches = 16 ports per switch used = 2 links from each GPU)

  GPU0   GPU1   GPU2   GPU3   GPU4   GPU5   GPU6   GPU7
   |12    |12    |12    |12    |12    |12    |12    |12
  +------------------------------------------------------+
  |  NVSw0   NVSw1   NVSw2   NVSw3   NVSw4   NVSw5       |
  +------------------------------------------------------+
  any pair: 600 GB/s bidirectional  ("600 GB/s GPU-to-GPU bandwidth",
                                     DGX A100 user guide)
```

```text
DGX H100 island: 8 H100 x 18 NVLink4 links = 144 GPU links -> 4 NVSwitches
  (144 / 4 = 36 ports per switch used, out of 64 ports per chip)

  GPU0  GPU1  GPU2  GPU3  GPU4  GPU5  GPU6  GPU7
   |18   |18   |18   |18   |18   |18   |18   |18
  +------------------------------------------------+
  |  NVSw0     NVSw1     NVSw2     NVSw3           |
  +------------------------------------------------+
  any pair: 900 GB/s bidirectional; 4 switches give
  "900 GB/s GPU-to-GPU bandwidth" (DGX H100/H200 user guide)
```

```text
DGX B200 island: 8 B200 x 18 NVLink5 links = 144 GPU links -> 2 NVSwitches
  (144 / 2 = 72 ports per switch -- the full gen-4 switch, no spare ports)

  GPU0  GPU1  GPU2  GPU3  GPU4  GPU5  GPU6  GPU7
   |18   |18   |18   |18   |18   |18   |18   |18
  +------------------------------------+
  |        NVSw0         NVSw1         |   "2 x 5th generation NVLink
  +------------------------------------+    switches, 14.4 TB/s aggregate
  any pair: 1,800 GB/s bidirectional        bandwidth" (DGX B200 user guide)
```

Reading the three diagrams as one trend: NVLink 2 switches per 8 GPUs (Ampere) shrinks to 4
(Hopper) and 2 (Blackwell) while per-GPU bandwidth triples. Fewer chips means fewer hops, less
power, less failure surface -- and in the GB200 design, the switch stops being a daughterboard
and becomes a rack-level device.

## 4. Rack Scale: 8-GPU Islands Become a 72-GPU Domain

Hopper already had a multi-node story: second-level "NVLink Switch System" switches could
network "up to 32 nodes or 256 GPUs ... in a 2:1 tapered, fat tree topology ... capable of
delivering 57.6 TB/sec of all-to-all bandwidth" (Hopper architecture blog). Blackwell folded
the scale-up into one rack. GB200 NVL72 connects "36 Grace CPUs and 72 Blackwell GPUs" with a
"72-GPU NVLink domain that acts as a single, massive GPU" (NVIDIA GB200 NVL72 page). NVIDIA is
explicit that this is new territory: before it, "the maximum number of GPUs that could be
connected in a single NVLink domain was limited to eight on an HGX H200 baseboard" (OCP blog).

```text
GB200 NVL72: one rack, one 72-GPU NVLink 5 domain (1.8 TB/s per GPU)
+------------------------------------------------------------------+
| 18 compute trays: 36 Grace CPUs + 72 Blackwell GPUs (4/tray)     |
|    GPU0-3   GPU4-7  ...  GPU68-71      18 NVLink5 links each     |
|         ||                                                       |
| 4 NVLink cartridges at rack rear: >5,000 active copper cables    |
|         ||                                                       |
| 9 switch trays: 18 NVSwitch chips (72 x 18 = 1,296 links)        |
+------------------------------------------------------------------+
  aggregate all-to-all 130 TB/s  |  AllReduce bandwidth 260 TB/s
```

Copper, not optics, inside the rack. The OCP contribution describes "four NVLink cartridges
mounted vertically at the rear of the rack ... over 5,000 active coaxial copper cables". The
engineering logic is a reach/power trade: NVLink 5's 100 GB/s-per-link signaling reaches under
two meters, the rack needs only ~1-2 m runs, and passive copper needs no transceiver lasers --
no watt per link spent on electro-optic conversion, no laser-failure line item. Optics enter
one level up, in the scale-out InfiniBand/Ethernet fabric between racks, where runs are tens of
meters and beyond. Keep the two fabrics distinct in interviews: NVLink is the scale-up fabric
(inside an island or rack, copper), InfiniBand/Ethernet is the scale-out fabric (between
racks, optics), and the demo below shows what each ceiling costs.

## 5. The Software Looks Down: NCCL, NVLS, and MIG

NCCL treats the fabric as a first-class topology to discover, not a fixed environment: "It has
been optimized to achieve high bandwidth on platforms using PCIe, NVLink, NVswitch, as well as
networking using InfiniBand Verbs or TCP/IP sockets" (NCCL README). Consequences:

- **Ring order follows copper.** NCCL builds rings neighbor-by-neighbor along detected
  NVLink/PCIe paths, which is why rank order and ring order differ; the ring math itself is on
  [Ring AllReduce](../llm/advanced/distributed/ring-allreduce.md).
- **In-fabric collectives (NVLS).** The NCCL docs define `NCCL_NVLS_ENABLE` (since 2.17):
  "Enable the use of NVLink SHARP (NVLS). NVLink SHARP is available in third-generation
  NVSwitch systems (NVLink4) with Hopper and later GPU architectures, allowing collectives
  such as ncclAllReduce to be offloaded to the NVSwitch domain." Algorithm history in the same
  docs: Ring/Tree (2.5+), CollnetDirect/CollnetChain (2.14+), NVLS (2.17+), NVLSTree (2.18+).
  Caveat: NVLS is "not compatible with multiple ranks within the same communicator using the
  same GPU" -- with the default `NCCL_NVLS_ENABLE=2` it silently disables in that case.
- **MIG breaks the fabric guarantees.** From the MIG user guide: "With driver R570, Only P2P
  between MIG instances on the same GPU is supported. P2P between MIG instances on different
  GPUs, or between MIG instances to non-MIG mode GPU devices are not supported," and "CUDA IPC
  across GPU instances is not supported." So a partitioned DGX H100 still has its 900 GB/s
  NVLink fabric electrically intact, but slices on different GPUs cannot use it for P2P; a
  sharded job should fill whole GPUs first and use MIG for consolidation, or expect NCCL to
  fall back through PCIe/host paths.
- The GPUDirect/RDMA and PCIe-P2P economics behind these fallbacks are worked through in
  [GPUDirect Networking](./gpudirect-networking.md), including why a "0 PCIe crossings" NVLink
  peer access beats the one-crossing paths.

## 6. What the Fabric Buys You -- and What It Does Not

- **Tensor parallelism and fused MoE routing live or die on NVLink.** An all-reduce per
  transformer sub-layer over PCIe is infeasible; the same collective over NVLink is a rounding
  error next to the matmul (see [Collective Communication](./collective-communication.md) for
  the parallelism-to-collective mapping).
- **NVLS moves the all-reduce into the switch.** NVIDIA claims in-fabric multicast and
  reductions "provide up to 2x throughput gain while significantly reducing latency for small
  block size collectives" versus NCCL on A100 -- the small-block case ring handles worst.
- **MoE all-to-all is the newest heavy consumer.** NVIDIA markets the rack domain around
  exactly this: 72 GPUs "in an all-to-all topology for a total of 260 TB/s, providing massive
  bandwidth for the all-to-all communications needed for training and inference of leading
  mixture-of-experts model architectures" (NVLink page). Expert-parallel dispatch/combine fits
  in the domain; cross-rack, it inherits the scale-out ceiling
  ([Expert Parallelism](../llm/advanced/distributed/expert-parallelism.md)).
- **The honest part: NVLink ends at the rack.** Per node, 8 NDR400 rails give 400 GB/s
  cross-node versus 450 GB/s per GPU inside the island -- and a flat 64-GPU ring still pays
  126 sequential steps. The model below quantifies both effects.

## 7. A Ring All-Reduce Time Model You Can Recompute

Upper-bound model (deliberately serial, no chunk pipelining): a ring all-reduce runs
`2(N-1)` steps; each step every GPU sends an `S/N` chunk at the fabric's per-GPU per-direction
bandwidth `B`, paying a fixed per-hop cost `L` (software handoff plus fabric latency).

```python
def ring_time(s_bytes, n_gpus, bw_per_gpu, hop_s):
    """Serial upper-bound ring all-reduce time (seconds)."""
    steps = 2 * (n_gpus - 1)
    chunk = s_bytes / n_gpus
    t_step = chunk / bw_per_gpu + hop_s
    return steps * t_step


def metrics(s_bytes, n_gpus, bw, hop):
    t = ring_time(s_bytes, n_gpus, bw, hop)
    algbw = s_bytes / t / GB
    busbw = algbw * 2 * (n_gpus - 1) / n_gpus          # NCCL busbw convention
    return t, algbw, busbw, 100.0 * busbw / (bw / GB)  # util % of peak egress


FABRICS = [
    ("A. NVSwitch island (8, NVLink4)", 8, 450 * GB, 2e-6),
    ("B. PCIe-only island (8, Gen5 x16)", 8, 63 * GB, 8e-6),
    ("C. Multi-node IB (64, 1 rail/GPU)", 64, 50 * GB, 3e-6),
]
MSG = 2 * 2 ** 30  # 2 GiB
print("Ring all-reduce, S = 2 GiB (2147483648 bytes), serial upper-bound model")
print("%-37s %5s %7s %9s %8s %8s %6s"
      % ("Fabric", "GPUs", "Peak", "Time", "algbw", "busbw", "Util"))
for name, n, bw, hop in FABRICS:
    t, alg, bus, util = metrics(MSG, n, bw, hop)
    print("%-37s %5d %6.0fG %8.2fms %7.1fG %7.1fG %5.1f%%"
          % (name, n, bw / GB, t * 1e3, alg, bus, util))
```

(Elided from the listing above: the `GB = 1e9` constant, a message-size sensitivity sweep, and
the slowdown ratios, all in the same style.) Real output of the full script:

```text
Ring all-reduce, S = 2 GiB (2147483648 bytes), serial upper-bound model

Fabric                                 GPUs    Peak      Time    algbw    busbw   Util
--------------------------------------------------------------------------------------
A. NVSwitch island (8, NVLink4)           8    450G     8.38ms   256.3G   448.5G  99.7%
B. PCIe-only island (8, Gen5 x16)         8     63G    59.76ms    35.9G    62.9G  99.8%
C. Multi-node IB (64, 1 rail/GPU)        64     50G    84.94ms    25.3G    49.8G  99.6%

Sensitivity: utilization vs message size (same three fabrics)
Fabric                                Util@16 MiB Util@256 MiB Util@2 GiB
--------------------------------------------------------------------------------------
A. NVSwitch island (8, NVLink4)          70.0%    97.4%    99.7%
B. PCIe-only island (8, Gen5 x16)        80.6%    98.5%    99.8%
C. Multi-node IB (64, 1 rail/GPU)        63.6%    96.5%    99.6%

Slowdown vs fabric A at 2 GiB: B = 7.1x, C = 10.1x
Cross-node ceiling: 8 rails x 50 GB/s = 400 GB/s per node vs 450 GB/s NVLink per GPU
```

How to read it (it is a model, not a benchmark):

- At 2 GiB every ring saturates its bottleneck link (utilization 99%+): fabric choice changes
  the *slope*, 7.1x between the island fabrics, and the cross-node ring is 10.1x slower than
  the NVSwitch island despite 64 GPUs.
- The sensitivity rows are the counterintuitive part: at 16 MiB the *fast* fabric has the
  *worst* utilization (70%), because a fixed 2 us hop is 43% of its step while 8 us is a
  rounding error on a 63 GB/s PCIe hop. Fast fabrics are hurt more by fixed per-step software
  overheads -- which is precisely the small-message regime NVLS offload targets.
- PCIe Gen5 x16 is counted at 63 GB/s/dir (NVIDIA counts 64; ~1.6% is 128b/130b encoding).
  Real NCCL numbers land below these ceilings: pipelining reclaims the small-message case, and
  dual-socket systems split the PCIe island in two.

## 8. Interview Angles

- "Why did NVSwitch happen?" -- Point-to-point NVLink topologies cap the domain at the number
  of links per GPU; a crossbar chip turns O(n^2) cables into O(n) GPU-side links plus switch
  chips, and lets any pair run at full link speed concurrently (DGX-2 was the proof point).
- "You enable MIG on a DGX H100. What happens to NVLink?" -- Electrically nothing; logically
  cross-GPU P2P is unsupported between MIG instances, CUDA IPC across GPU instances is off,
  and NVLS needs whole GPUs -- plan shards to fill whole GPUs or accept PCIe/host fallbacks.
- "Why is GB200 NVL72 copper?" -- Sub-2-meter reach, passive cables, no transceiver power or
  laser failure modes; optics stay in the scale-out fabric where runs are long. If asked for
  numbers: >5,000 copper cables, 130 TB/s all-to-all, 260 TB/s AllReduce in one NVLink domain.

## 9. Cross-References and Sources

Related pages: [GPUDirect Networking](./gpudirect-networking.md) (RDMA in/out of the fabric,
PCIe crossing economics, SHARP-over-IB contrast), [Collective Communication](./collective-communication.md)
(all-reduce patterns and the parallelism-to-collective mapping), [HPC Infrastructure](./hpc-infra.md)
(scheduling whole islands), and [Ring AllReduce](../llm/advanced/distributed/ring-allreduce.md)
(ring math consumed by this page's model).

References (all probed live, Aug 2026):

1. NVIDIA, "NVLink & NVLink Switch" product page. https://www.nvidia.com/en-us/data-center/nvlink/ (gen 4-6 spec table: 900/1,800/3,600 GB/s per GPU, 18/18/36 links; NVL72 aggregates).
2. NVIDIA, "GB200 NVL72" product page. https://www.nvidia.com/en-us/data-center/gb200-nvl72/ (36 Grace + 72 Blackwell, 72-GPU NVLink domain, 130 TB/s NVLink bandwidth, 13.4 TB HBM3E).
3. NVIDIA Technical Blog, "NVSwitch Accelerates NVIDIA DGX-2" (2018). https://developer.nvidia.com/blog/nvswitch-accelerates-nvidia-dgx2/ (gen-1 chip: 18 ports, 51.5 GBps/port, 928 GBps aggregate).
4. NVIDIA Technical Blog, "NVIDIA Hopper Architecture In-Depth" (2022). https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/ (NVSwitch 3: 64 ports, 13.6 Tb/s; SHARP/multicast; 32-node/256-GPU NVLink Switch System at 57.6 TB/s all-to-all; PCIe Gen5 = 64 GB/s/dir).
5. NVIDIA Technical Blog, "NVIDIA Contributes NVIDIA GB200 NVL72 Designs to Open Compute Project" (2024). https://developer.nvidia.com/blog/nvidia-contributes-nvidia-gb200-nvl72-designs-to-open-compute-project/ (18 compute trays, 9 switch trays, >5,000 copper cables, 130 TB/s all-to-all, 260 TB/s AllReduce).
6. DGX H100/H200 User Guide. https://docs.nvidia.com/dgx/dgxh100-user-guide/introduction-to-dgxh100.html (4 NVSwitches, 900 GB/s GPU-to-GPU).
7. DGX A100 User Guide. https://docs.nvidia.com/dgx/dgxa100-user-guide/introduction-to-dgxa100.html (6 second-generation NVSwitches, 600 GB/s GPU-to-GPU).
8. DGX B200 User Guide. https://docs.nvidia.com/dgx/dgxb200-user-guide/introduction-to-dgxb200.html (2 fifth-generation NVLink switches, 14.4 TB/s aggregate).
9. NVIDIA Ampere (A100) Architecture Whitepaper. https://images.nvidia.com/aem-dam/en-zz/Solutions/data-center/nvidia-ampere-architecture-whitepaper.pdf (NVLink 3: 12 links, 600 vs 300 GB/s; DGX A100 fabric: 4.8 TB/s total bidirectional).
10. NVIDIA Technical Blog, "Inside Pascal" (2016). https://developer.nvidia.com/blog/inside-pascal (NVLink 1: 160 GB/s bidirectional).
11. NCCL User Guide, environment variables. https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html (NCCL_NVLS_ENABLE, NVLink SHARP on third-generation NVSwitch, algorithm version table) and NCCL README. https://github.com/NVIDIA/nccl
12. NVIDIA Multi-Instance GPU User Guide. https://docs.nvidia.com/datacenter/tesla/mig-user-guide/deployment-considerations.html (R570 P2P-between-MIG-instances constraints, CUDA IPC limits).
13. NVIDIA Tesla V100 Datasheet. https://images.nvidia.com/content/technologies/volta/pdf/tesla-volta-v100-datasheet-letter-fnl-web.pdf (NVLink 2: 300 GB/s).
