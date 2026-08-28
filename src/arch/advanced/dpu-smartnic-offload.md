# DPUs and SmartNICs: Offloading the Data Path

## The Amdahl argument of the data path

In 2003, Jeffrey Mogul's HotOS paper put it as "TCP offload is a dumb idea whose time
has come" -- dumb because hardware that ships faster than software freezes a protocol
stack into silicon, and inevitable because at some link speed there is no software left
to run it. Twenty years on, the argument has been settled not by
protocol offload but by *function* offload: at 100-400 Gb/s per host, the cycles spent
on virtual switching, overlay encapsulation, and packet crypto are no longer a rounding
error, they are the majority of what the host CPU does with a packet.

The arithmetic is unforgiving. A 100 Gb/s stream of 64-byte packets is ~149 Mpps; even
an optimized software dataplane spends fractions of a microsecond of core time per
packet, which means tens of cores doing nothing but moving someone else's bytes. The
same arithmetic explains why every hyperscaler converged on the same answer:

1. Split the **control plane** (flow setup, policy decisions, slow-path exceptions) from
   the **data plane** (per-packet work once a flow is established).
2. Sink the data plane into dedicated silicon that terminates at line rate, leaving the
   host CPU for tenants and applications.

That split is the entire product category. The NIC card executing it is marketed as a
**SmartNIC** or **DPU** (data processing unit); NVIDIA positions it as the "third
pillar" next to CPU and GPU, which is marketing, but the underlying Amdahl ratio is
real. Mogul's warning still bites, though: everything hard-coded into the silicon is
something you cannot patch. The industry's answer to *that* is programmability, which
is why the software stack matters as much as the chips.

## Four ways to build one

| Design class | Example line | Data-plane engine | Strengths | Limits |
|---|---|---|---|---|
| Fixed-function offload ASIC | AWS Nitro cards | purpose-built packet/EBS engines | cheapest per byte, zero tenant attack surface | no new features without new silicon |
| NIC SoC + Arm cores | NVIDIA BlueField-1/2/3 | switch ASIC + embedded Arm cluster | runs full Linux; general-purpose services | Arm cores are slow per-watt vs fixed logic |
| NPU (flow/policy programmable) | AMD Pensando | network processor + P4-class pipeline | near-ASIC efficiency with protocol flexibility | narrower programming model, fewer services |
| FPGA SmartNIC | Microsoft Catapult lineage | reconfigurable fabric | arbitrary protocols, custom pipelines | hardest to program, highest power/cost |

The classes are converging. BlueField adds more fixed engines each generation,
Pensando NPUs gained general Arm subsystems, and AWS's fixed-function Nitro is
surrounded by a large Annapurna Labs silicon portfolio. What does *not* converge is the
trust model -- see [the zero-trust section](#the-dpu-as-trust-boundary) for why a
fixed-function card and a Linux-running DPU isolate very differently.

## History: from TOE to Nitro to a product category

```text
2003   Mogul, "TCP offload is a dumb idea whose time has come" (HotOS IX)
2007-  TOEs ship, disappoint: TCP in silicon breaks through VM migration,
       buffers, and every kernel upgrade cycle
2013   AWS ships its first Nitro card (networking I/O offload); it is not
       announced, it just makes C4 instances cheaper than they should be
2015   AWS acquires Annapurna Labs (Israeli silicon team) -> in-house ASICs
2016   Microsoft Catapult v2: FPGA SmartNICs in every Azure server
2017   Nitro Hypervisor (KVM-derived) replaces Xen; Nitro cards for network,
       EBS, and instance storage are now the storage/network fabric
2019   NVIDIA buys Mellanox ($6.9B, closed 2020); BlueField-1 DPU appears
2020-21 AWS publishes the Nitro Security whitepaper; BlueField-2 GA
2022   AMD buys Pensando ($1.9B); NVIDIA sends BlueField-3 to production
2023   Azure Boost GA (DPU-based storage/networking offload)
2025   BlueField-4 announced: 64 Arm cores, 800 Gb/s (GTC Washington, Oct 2025)
```

The Nitro System is the cleanest case study because its components are public:
**Nitro Cards** (network, EBS, instance storage), the **Nitro Security Chip** (locks
out the card bus and firmware paths so no operator or compromised host software can
read guest memory), and the **Nitro Hypervisor** (a stripped KVM derivative with no
operator-facing interface). Nitro Enclaves later reused the same isolation machinery to
carve protected containers out of an ordinary EC2 instance. The essential Nitro idea is
that *the host is untrusted*: disks and NICs are connected to the network through cards
that speak to guests on their own terms.

## BlueField and Pensando, concretely

| Generation | Year | Network speed | Compute engines | Notable firsts |
|---|---|---|---|---|
| BlueField-1 | 2019 | up to 200 Gb/s | 16x Cortex-A72 | Mellanox ConnectX-5 + Arm cluster, "SmartNIC that runs Linux" |
| BlueField-2 | 2021 | up to 200 Gb/s | 8x Cortex-A72 + crypto engines | first mainstream DPU with inline AES-XTS + RegEx |
| BlueField-3 | 2022-23 | up to 400 Gb/s | 16x Cortex-A78 | volume GPU-fabric DPU; SNAP storage emulation at scale |
| BlueField-4 | announced Oct 2025 | up to 800 Gb/s | 64 Arm cores | positions the DPU as an "AI factory" infrastructure computer |

Two architectural notes that survive the marketing. First, the Arm cores are *not* the
data plane: packets at line rate flow through the switch ASIC and embedded engines;
Arm cores handle control-plane daemons, slow-path exceptions, and services. A
BlueField-3 can saturate 400 Gb/s while its 16 A78 cores look mostly idle. Second, AMD
Pensando took the opposite partition: a programmable network processor ("P4-class"
flow pipeline) does per-flow work in silicon, and the P4 programs are loadable, which
buys protocol flexibility that a fixed ASIC cannot match. Pensando's third-generation
parts (Salina 400 DPU, Pollara 400 AI NIC, announced October 2024) target AI-fabric
east-west traffic; AMD's DPU line and NVIDIA's are now the two serious merchant
offerings, with Intel's IPU program never gaining merchant traction and Microsoft's
Azure Boost a first-party deployment rather than a product you can buy.

## What actually gets offloaded

### Virtual switching and routing

The canonical workload: a host runs Open vSwitch, every packet from every VM hits the
flow table, and the flow table is the Amdahl tax. Hardware offload pushes established
flows into the NIC's embedded switch: the Linux `tc` flower classifier (or the OVS
datapath) programs a flow, `skip_sw` marks it "must be offloaded", and the NIC does
encap, decap, ACL, and NAT in silicon; misses go up to the Arm cores, which run the
full OVS userspace and push new flows down. This is exactly the switchdev +
representor model described in [SR-IOV and network virtualization
offload](../../networks/advanced/sr-iov-networking.md) -- the DPU is that model plus
enough compute to run the control plane locally instead of on the host. NVIDIA's OVS
kernel hardware-acceleration documentation and the upstream OVS TC-flower howto are
the two references that describe the mechanics without marketing.

### Storage: SNAP and NVMe-oF

A BlueField running the SNAP (scalable-packaged NVMe/virtio) service presents virtio-blk
or NVMe devices to the host over PCIe, but the backing store is remote NVMe-oF: the
DPU terminates the fabric, caches, and maps it into emulated local drives. The host
thinks it has NVMe SSDs; physically it has a network-attached disaggregated pool. This
is the "DPU as storage front-end" half of the offload spectrum described in
[Computational Storage](../../storage/computational-storage.md), which covers the
*media-side* end of the same idea (compute inside the drive); the two compose, and that
page's postmortem on why computational storage underdelivered applies word-for-word to
DPU services: silicon shipped, portability of the software did not.

Inline crypto rides along for free: BlueField-2/3 encrypt/decrypt at line rate with
AES-XTS (512-bit keys) for data at rest, plus MACsec/IPsec for data in flight, and the
NVMe Key Per I/O (KPIO) spec gives per-namespace key plumbing. The important property
is *inline*: there is no "then encrypt" step, because encryption is part of the
per-packet/per-block pipeline, so encryption stops being an Amdahl line item at all.
For the HPC angle -- RDMA transports and InfiniBand HCAs, which BlueField is also
built on -- see [MPI and parallelism](../../hpc/mpi-parallelism.md); the fabric
mechanics are shared.

### The slow path is still the point

Every offload story has the same shape: hardware does flows, software does first
packets. The DPU's Arm cores exist because the exception path -- a cache miss in the
flow table, a malformed packet, a policy update, a control protocol -- is where
correctness lives. Interview-ready phrasing: *offload accelerates the common case; the
DPU exists to make the uncommon case cheap enough not to matter.* If the slow path is
throttled, the fast path is irrelevant; this is why DOCA's programming model (below) is
mostly about control and services, not packet processing.

## The DPU as trust boundary

East-west traffic -- VM-to-VM, pod-to-pod inside a rack -- never crosses a perimeter
firewall. The zero-trust answer (NIST SP 800-207 is the canonical articulation) is to
push policy to every node, which is economically viable only if the per-node policy
engine runs for free. That is the DPU's second job:

```text
                     ONE RACK, TWO ADMIN DOMAINS

   tenant domains (compromisable)        infrastructure domain (hardened)
 +----------------+----------------+    +--------------------------------+
 |  VM / pod /    |  VM / pod /    |    |  BlueField / Nitro DPU         |
 |  container     |  container     |    |  - firewall + microseg policy  |
 |                |                |    |  - flow telemetry (encrypted)  |
 |   never sees   |   never sees   |    |  - storage encryption keys     |
 |   its own      |   the infra    |    |  - boots only signed firmware  |
 |   filter rules |   control path |    |  - owns the packet tap         |
 +-------+--------+--------+-------+    +----------------+---------------+
         |                 |                             |
         |  tenant data plane only         infra data plane (tunneled,
         +-----------------------------+   encrypted, policy-enforced here)
                                       |
                            the DPU is the only element both
                            sides must trust -- and it is the
                            thing neither side can reconfigure
```

The isolation argument differs by design class, and this is where a fixed ASIC beats a
general-purpose DPU. Nitro's security chip is small enough to verify (the AWS white
paper walks its attack surface); a BlueField runs a complete Linux with DOCA services,
which means it inherits Linux's attack surface, patched by NVIDIA, inside every server.
The counter-argument: a general-purpose DPU can run *tenant-visible* isolation tools
(distributed firewalls, IDS, encrypted telemetry) that a fixed ASIC cannot. Both are
"trust boundaries"; they differ in whether the boundary is auditable silicon or a
patchable OS. Either way the architectural consequence is the same -- **the network
tap, the encryption keys, and the filter rules move out of the kernel the tenant
shares a CPU with.** Related reading on the confidential-computing version of this
argument (protecting the *host* from *tenants* with TEEs) is in
[Confidential Computing](../../security/advanced/confidential-computing.md).

## The software stack

DOCA is NVIDIA's DPU software framework: a BSP (Linux + drivers), service
infrastructure (firewall, telemetry, SNAP, encryption services), and APIs (DOCA Flow
for pipeline programming, DOCA DevCntl/Comch for host-DPU communication). It went 1.x
(2022), 2.x LTS (2023), and is at 3.4 as of mid-2026, with the SNAP and OVS services
packaged rather than compiled-in. The honest summary of the last five years: the chips
arrived in 2020-2022; the software distribution problem -- DOCA releases tracking
kernel versions, service portability across BlueField generations -- took years longer,
which is precisely the failure mode the computational-storage page predicted for that
category. Host-side alternatives (DPDK, XDP/eBPF, AF_XDP) remain cheaper for the same
problem at <25 Gb/s; they are covered in
[Programmable Networks](../../networks/advanced/programmable-networks.md), and the DPU
is best understood as what happens when those techniques stop being enough at 100 Gb/s
and someone moves them off your CPUs onto someone else's.

## Demo: the break-even frame size

The model below decomposes per-packet host work into five steps, marks which a DPU can
absorb into silicon, and computes when a 48-core host runs out of CPU at 100 Gb/s --
before and after offload.

```python
# Data-path Amdahl: what 100 Gb/s costs a host CPU, and what remains after
# a DPU absorbs the switch + crypto work into forwarding silicon.
#
# Per-packet cost assumptions (order-of-magnitude, from public DPDK/OVS
# measurements; the model's shape is what matters, not the exact cents):

LINK_GBPS = 100
CORES     = 48

STEPS = [
    ("rx_dma_poll", 0.10, False),   # driver + DMA bookkeeping   (stays on host)
    ("flow_lookup", 0.18, True),    # vSwitch flow table          (offloadable)
    ("encap_decap", 0.12, True),    # overlay encap, ACL checks   (offloadable)
    ("crypto",      0.35, True),    # AES-GCM per packet          (offloadable)
    ("tx_doorbell", 0.15, False),   # doorbell + completion       (stays on host)
]

def wire_pps(gbps, frame):
    # Ethernet overhead: 20B preamble + IFG + MAC trailer per frame on the wire
    return (gbps * 1e9 / 8) / (frame + 20)

def core_share(pps, us_per_pkt):
    # core-seconds of work arriving per second (1.0 = one full core busy)
    return pps * us_per_pkt * 1e-6

sw_us   = sum(c for _, c, _ in STEPS)
host_us = sum(c for _, c, off in STEPS if not off)
print(f"per-packet host work: software {sw_us:.2f} us -> after offload {host_us:.2f} us")
print(f"offloadable share of the data path: {(sw_us-host_us)/sw_us:.0%} (Amdahl's f)\n")

print(f"{'frame':>6} {'Mpps@100G':>10} {'sw-only cores':>14} {'after DPU':>10}  verdict")
for frame in (64, 1500, 9000):
    pps = wire_pps(LINK_GBPS, frame)
    sw, res = core_share(pps, sw_us), core_share(pps, host_us)
    verdict = "HOST SATURATES" if sw > CORES else f"ok, {CORES - res:.1f} cores free"
    print(f"{frame:>5}B {pps/1e6:>10.2f} {sw:>14.1f} {res:>10.1f}  {verdict}")

for label, cost in (("software-only", sw_us), ("with DPU offload", host_us)):
    for frame in range(2000, 40, -1):   # walk frames small<-large: find the cliff
        if core_share(wire_pps(LINK_GBPS, frame), cost) > CORES * 0.9:
            print(f"\n{label}: a 48-core host is 90%-spent below {frame}B frames")
            break
```

Output (from a real run):

```text
per-packet host work: software 0.90 us -> after offload 0.25 us
offloadable share of the data path: 72% (Amdahl's f)

 frame  Mpps@100G  sw-only cores  after DPU  verdict
   64B     148.81          133.9       37.2  HOST SATURATES
 1500B       8.22            7.4        2.1  ok, 45.9 cores free
 9000B       1.39            1.2        0.3  ok, 47.7 cores free

software-only: a 48-core host is 90%-spent below 240B frames

with DPU offload: a 48-core host is 90%-spent below 52B frames
```

Read the two break-even lines together: offloading 72% of the path moves the host's
saturation point from 240-byte frames to 52-byte frames -- a ~4.6x margin, exactly the
1/(1-f) shape Amdahl's law predicts. The residual 0.25 us/packet is the floor: DMA and
doorbells stay on the host until the PCIe boundary itself moves.

## Trends: XPUs, SiP, and the AI-fabric pull

- **XPU is the umbrella term** for infrastructure processors (DPU, IPU, NPU); it
  signals that vendors expect a rack to have workload silicon (GPU/CPU) plus
  infrastructure silicon, each on its own upgrade cadence.
- **System-in-package (SiP) integration**: DPUs are converging with other accelerators
  on interposers -- BlueField-4 pairs 800 Gb/s of Ethernet with Grace-class Arm
  subsystems, and the packaging economics that make that possible (yield, die-to-die
  interfaces) are the same ones covered in [Chiplets & UCIe](chiplets-ucie.md). Expect
  "DPU" to stop being a card and become a tile.
- **AI factories change the ratios**: GPU clusters are so expensive that any cycle a
  NIC steals from them is unacceptable, which is why east-west fabric offload
  (collectives, storage check-pointing, telemetry) is the volume driver now, and why
  the 2024-2025 DPU launches (Salina/Pollara, BlueField-4) all lead with AI-fabric
  claims rather than hypervisor offload.
- **Confidential infrastructure**: DPUs are becoming the key holders for TEE ecosystems
  (attestation plumbing, encrypted storage keys); the TEE comparison itself is in
  [Confidential Computing](../../security/advanced/confidential-computing.md).

## Interview lens

- *Why offload at 100 Gb/s and not 10 Gb/s?* Core-seconds per second scales with Mpps,
  not bits; at 10 Gb/s the software path costs ~1-2 cores, at 100 Gb/s it costs
  dozens. The Amdahl ratio crosses the "spare cores" threshold somewhere near 25-50 Gb/s.
- *Why did TCP offload fail but DPU offload succeed?* TOE froze one protocol in
  silicon and fought kernel evolution; DPUs offload *workloads* (switch, storage,
  crypto) behind stable interfaces (virtio, NVMe, tc), with programmable Arm/NPU
  fallback for the rest.
- *Where do the keys live?* On the DPU -- which is either the strongest point of the
  design (keys never touch the tenant kernel) or the weakest (a patchable OS holds
  every tenant's secrets), depending on the silicon class.
- *What is the slow path and why does it matter?* Flows not yet programmed, malformed
  packets, policy changes. Line rate on the fast path is worthless if the slow path
  drops to 10 kpps and the workload churns flows.

## References

1. AWS, "The Security Design of the AWS Nitro System" (whitepaper):
   https://docs.aws.amazon.com/whitepapers/latest/security-design-of-aws-nitro-system/the-components-of-the-nitro-system.html
2. NVIDIA BlueField networking platform (product architecture):
   https://www.nvidia.com/en-us/networking/products/data-processing-unit/
3. NVIDIA, "NVIDIA Launches BlueField-4" (Oct 2025):
   https://blogs.nvidia.com/blog/bluefield-4-ai-factory
4. DOCA software framework + release notes (DOCA 3.4 archive):
   https://networking-docs.nvidia.com/doca/archive/3-4-0/doca-release-notes
5. AMD Pensando DPU technology (Salina/Pollara generation):
   https://www.amd.com/en/products/data-processing-units/pensando.html (search-verified;
   amd.com blocks curl)
6. Open vSwitch, "Flow Hardware offload with Linux TC flower":
   https://docs.openvswitch.org/en/latest/howto/tc-offload
7. NIST SP 800-207, "Zero Trust Architecture":
   https://csrc.nist.gov/pubs/sp/800/207/final
