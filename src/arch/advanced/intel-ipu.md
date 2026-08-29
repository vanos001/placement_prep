# Intel IPU: x86's Answer to the DPU

The [DPUs and SmartNICs page](dpu-smartnic-offload.md) covers the category: why
virtual switching, overlay crypto, and virtio processing are worth moving off
the host CPU. This page is the Intel-specific half of the story: what an
"Infrastructure Processing Unit" is, how its two-track silicon strategy
differs from a single-ASIC merchant DPU, what actually ships (the IPU Adapter
E2100), and the honest economics of when such a card pays for itself.

## Naming first: what "IPU" adds to "DPU"

IPU is Intel's own category name for the device class the rest of the industry
calls DPU or SmartNIC; ServeTheHome's hands-on is explicit that "IPU is the
Intel-specific term for its 'Infrastructure Processing Unit' that others in the
industry generally call DPUs." Intel's 2021 announcement framed the name around
three jobs rather than around the card:

```text
  THE THREE JOBS OF AN IPU (Hot Chips 2021, "Major Advantages of IPUs")
  1. Separation of infrastructure and tenant: "Guest can fully control the CPU
     with their SW, while CSP maintains control of the infrastructure and Root
     of Trust"
  2. Infrastructure offload: "Accelerators help process these tasks
     efficiently. Minimize latency and jitter and maximize revenue from CPU"
  3. Diskless server architecture: "Simplifies data center architecture while
     adding flexibility for the CSP"
```

The third job -- booting servers with no local disks, storage arriving over
the fabric through the IPU -- is the disaggregation argument made in
[resource disaggregation](../../cloud/resource-disaggregation.md); the IPU
terminates the storage leg of it.

## Two tracks: FPGA and ASIC

Where NVIDIA shipped one DPU line (ConnectX silicon plus Arm cores), Intel
committed to two parallel lines. Its Programmable Solutions Group's write-up
of the Vision 2022 roadmap gives the rationale: "ASIC-based IPUs deliver
optimized performance and power ... FPGA-based IPUs deliver faster time to
market for evolving network standards, provide a reprogrammable and secure
datapath, and can more flexibly handle many types of custom workloads."

| Track | Codename | Silicon | Rate | Status |
|---|---|---|---|---|
| FPGA | Oak Springs Canyon | Intel Xeon D + Intel Agilex FPGA | 200G | announced Aug 2021; partner ecosystem |
| FPGA | Big Spring Canyon | Stratix 10 FPGA + Xeon D-1612 | 200G | lab/demo card; STH hands-on June 2022 |
| FPGA | Hot Springs Canyon | next-gen FPGA | 400G | roadmap only (Vision 2022) |
| ASIC | Mount Evans | first Intel ASIC IPU, co-designed with Google | 200G | reached production as IPU Adapter E2100 |
| ASIC | Mount Morgan | next-gen ASIC | 400G | roadmap only (Vision 2022) |

Details that survive contact with the hardware: Oak Springs Canyon pairs a
general x86 SoC with an FPGA, not Arm cores with a switch ASIC. Big Spring
Canyon, the card ServeTheHome dissected, carries a Stratix 10 with hardened
PCIe and Ethernet IP plus a 4-core/8-thread Xeon D-1612 running its own OS;
the FPGA emulates a virtio/NVMe device to the host while terminating RDMA
NVMe-oF upstream -- a storage-disaggregation fabric in a card. Mount Evans
was announced in August 2021, presented at Hot Chips 2021, and is documented
by Intel as "designed in collaboration with Google for the Google Cloud
Platform." The 2022 roadmap projected 400G codename parts and an 800G
generation "during 2025 or later"; Intel's live catalog currently lists the
E2100 as the IPU offering.

## Anatomy of the shipping part: Intel IPU SoC E2100

The E2100 product brief and the 2021 Mount Evans slides describe the same
partition: a programmable-packet-processor network subsystem, an Arm compute
complex, and a management processor:

```text
        HOST (up to 4 Xeon sockets, per the 2021 slides)
            |  PCIe 4.0 x16; 12K flexible host queues
            |  virtio-net / virtio-blk device models
  +---------v------------------------------------------------------+
  | INTEL IPU SoC E2100                     (200 Gb/s full duplex) |
  |                                                                |
  |  NETWORK SUBSYSTEM            COMPUTE COMPLEX                  |
  |  - P4-programmable packet     - 16x Arm Neoverse N1 @ 2.5 GHz  |
  |    processor + traffic        - 32 MB system-level cache       |
  |    shaper, up to 200 Mpps     - 3x LPDDR4x/DDR4 channels       |
  |  - ICE: inline IPsec,         - lookaside crypto/compression   |
  |    anti-replay                  100 Gb/s + 100 Gb/s concurrent |
  |  - RDMA RoCEv2: 200 Gb/s,                                      |
  |    150 M msg/s, 1 M QPs       MANAGEMENT PROCESSOR             |
  |  - NVMe engine: up to         - secure boot, root of trust,    |
  |    6M IOPS/direction            lifecycle management           |
  |    (Optane lineage)                                            |
  |  - "Falcon" hardware             |  8 lanes 56G SerDes         |
  |    reliable transport            |  PAM4/NRZ, up to 4 ports    |
  +----------------------------------+-----------------------------+
                                     v
                           2 x 100 GbE or 1 x 200 GbE
```

| Function | Mount Evans claim (Hot Chips 2021) | E2100 spec (product brief) |
|---|---|---|
| Arm compute | up to 16x Neoverse N1, up to 3 GHz | 16x Neoverse N1, up to 2.5 GHz |
| Packet pipeline | programmable, 200 Mpps | P4 pipeline + shaper, 200 Mpps |
| Storage | NVMe interface scaled from Optane tech | NVMe engine, up to 6M IOPS/direction |
| Transport | "Next Generation Reliable Transport" | Falcon (delay-based CC, SACK, multipath) |
| Crypto | inline IPsec at wire speed | ICE full IPsec offload, anti-replay |
| Memory | system-level cache, 3 channels LP/DDR4 | 32 MB SLC, 3x LPDDR4x/DDR4 |

Two details deserve a pause. The host interface is PCIe 4.0 x16, not Gen 5 --
arithmetic says fit, not oversight: 200 Gb/s is 25 GB/s, inside Gen 4 x16's
~31.5 GB/s per direction, with Gen 5 headroom for the 400G generation. And
"Falcon" is a reliable, congestion-controlled transport in hardware -- the
same insight Nitro's networking and BlueField's RDMA engines encode:
packet-recovery behavior belongs in silicon, because a lossy-network tail is
what software hides worst at these rates.

## The software stack: P4, IPDK, IDPF, OPI

Intel's software story is the mirror image of NVIDIA's DOCA: open-source
first, P4 at the center.

- **P4 and PNA.** The pipeline descends from Intel's Barefoot Tofino line
  (the 2021 slides say "P4 Studio based on Barefoot"); the P4 Language
  Consortium's target architecture for this device class is the **Portable
  NIC Architecture (PNA)** on p4.org -- worth knowing precisely, since the
  acronym is often expanded incorrectly. P4 itself is covered in [P4 and
  programmable data planes](../../networks/advanced/p4-programmable-dataplane.md),
  which cites the IPU as the commercial pitch.
- **IPDK.** The Infrastructure Programmer Development Kit describes itself as
  "an open source, vendor agnostic framework of drivers and APIs for
  infrastructure offload and management that runs on a CPU, IPU, DPU or
  switch," built on SPDK, DPDK, and P4. Its networking recipe ("P4 Control
  Plane," successor to P4-OVS) wired OVS offload to the IPU's P4 pipeline --
  the same tc-flower/switchdev model described in [SR-IOV and network
  virtualization offload](../../networks/advanced/sr-iov-networking.md).
- **IDPF.** On the host, the device presents through the Linux `idpf` driver,
  which kernel documentation titles "idpf Linux Base Driver for the Intel(R)
  Infrastructure Data Path Function" -- the standard-driver path for IPU
  networking.
- **OPI.** The Linux Foundation's Open Programmable Infrastructure project
  ("community-driven standards-based open ecosystem ... based on DPU/IPU-like
  technologies") absorbed IPDK's storage work and aims at vendor-neutral
  DPU/IPU APIs.

The honest status line: the flagship open-source artifact, the IPDK
networking recipe, is archived -- its README opens with "THIS PROJECT IS
ARCHIVED" and "Intel will not provide or guarantee development of or support
for this project." The E2100 brief's promised stack (P4 toolchain, SPDK
plugins for NVMe-over-TCP, DPDK via IDPF, IPU SDK use cases from tenant
hosting to Kubernetes acceleration) is the vendor stack. Compare the general
category's software-distribution problem in
[DPUs and SmartNICs](dpu-smartnic-offload.md): Intel's version of that problem
ended in an archive notice rather than an LTS line.

## Control plane, data plane, and the trust split

The IPU expresses the control/data split at the *server* boundary rather than
inside a kernel: tenants get the Xeon cores "with their SW" while the CSP
keeps "the infrastructure and Root of Trust" on the card. Concretely, the
E2100 models virtio-net and virtio-blk devices to the host -- the guest sees
the standard paravirtual interfaces from
[virtio](../../linux/virtualization/virtio.md), the data plane runs in the
packet processor, and the vSwitch control plane runs on the N1 cores. That is
the vDPA shape (virtio control plane, hardware data plane) described in
[SR-IOV and network virtualization
offload](../../networks/advanced/sr-iov-networking.md), extended with enough
compute to host the whole control plane locally.

The isolation rationale is the same zero-trust argument as for any DPU: the
management processor owns secure boot and root of trust, the ICE encrypts
every packet inline, and infrastructure state (flow tables, keys, telemetry)
never lives in a kernel the tenant can reach. The auditability caveat from
the [DPUs and SmartNICs](dpu-smartnic-offload.md) trust-boundary section
applies with one Intel wrinkle: the FPGA track's reprogrammable datapath
absorbs protocol churn -- Microsoft's Derek Chiou, on Intel's Vision 2022
stage, tied FPGA-based acceleration to a 5x latency reduction for Azure
customers -- but reprogrammability and auditability pull in opposite
directions. For the bare-metal variant, see
[bare-metal clouds](../../cloud/bare-metal-clouds.md); for the
confidential-computing angle, [Confidential
Computing](../../security/advanced/confidential-computing.md).

## MODEL: what an IPU buys back, and when it pays for itself

Intel's pitch line is "maximize revenue from CPU." This model prices that
claim: a software infra path of 0.45 us/packet (OVS lookup, encap/ACL, virtio
kicks, inline crypto) shrinks to 0.15 us/packet after offload; how many cores
come back, what are they worth at bulk cloud vCPU pricing, and where does
that value overtake a card's carrying cost? All cost figures are assumptions,
not vendor specs.

```python
# MODEL: what an IPU buys back, and when it pays for itself.
# If the IPU absorbs the OVS + virtio + crypto work, how many host cores come
# back, what are they worth at bulk cloud pricing, and at what host utilization
# does that value overtake the card's carrying cost? Costs below are
# order-of-magnitude modeling assumptions, not vendor specs.
SW_US, RESID_US = 0.45, 0.15  # us/pkt: software infra path -> after IPU offload
CORES, VCPU_H = 64, 0.031     # Xeon host cores; $/vCPU-hour (bulk reserved)
CARD_MO = 2500 / 48 + 25 * 0.730 * 0.10  # $2500 over 48 mo + 25 W @ $0.10/kWh

def mpps(gbps, frame):
    return (gbps * 1e9 / 8) / (frame + 20) / 1e6   # wire Mpps (20B overhead)

def value_at_70(rec):
    return min(rec, CORES) * 0.70 * 730 * VCPU_H   # cap: cannot reclaim > host

print(f"software path {SW_US} us/pkt -> after IPU offload {RESID_US} us/pkt")
print(f"IPU carrying cost: ${CARD_MO:.2f}/card/month\n")
print(f"{'GbE':>4} {'frame':>6} {'Mpps':>8} {'sw':>6} {'post':>6} "
      f"{'reclaim':>8} {'value $/mo':>11} {'break-even':>12}")
for gbps in (25, 100, 200):
    for frame in (64, 256, 1500):
        p = mpps(gbps, frame)
        rec = p * SW_US - p * RESID_US             # core-seconds per second
        be = CARD_MO / (rec * 730 * VCPU_H)
        print(f"{gbps:>4} {frame:>5}B {p:>8.1f} {p * SW_US:>6.1f} {p * RESID_US:>6.1f} "
              f"{rec:>8.1f} {value_at_70(rec):>11.0f} {(f'{be:.0%}' if be <= 1 else 'never'):>12}")
```

Output (from a real run):

```text
software path 0.45 us/pkt -> after IPU offload 0.15 us/pkt
IPU carrying cost: $53.91/card/month

 GbE  frame     Mpps     sw   post  reclaim  value $/mo   break-even
  25    64B     37.2   16.7    5.6     11.2         177          21%
  25   256B     11.3    5.1    1.7      3.4          54          70%
  25  1500B      2.1    0.9    0.3      0.6          10        never
 100    64B    148.8   67.0   22.3     44.6         707           5%
 100   256B     45.3   20.4    6.8     13.6         215          18%
 100  1500B      8.2    3.7    1.2      2.5          39          97%
 200    64B    297.6  133.9   44.6     89.3        1014           3%
 200   256B     90.6   40.8   13.6     27.2         430           9%
 200  1500B     16.4    7.4    2.5      4.9          78          48%
```

The break-even column is the business case: hyperscalers running 100-200 GbE
fabrics with heavy small-packet and crypto loads clear the card's cost at
trivial utilization -- which is why Google co-designed an IPU and why the
best merchant customers build their own -- while an enterprise at 25 GbE with
1500-byte packets never does. The 200 GbE/64B row is the asymptote: the model
caps reclaimed value at the host's 64 cores, and the host could never reach
that line rate in software anyway.

## Honest tradeoffs, and where the program stands

- **Captive, not merchant.** The design that reached production was
  co-designed with Google; there is no DOCA-equivalent third-party services
  ecosystem around the E2100, and the general-purpose DPU market consolidated
  around NVIDIA and AMD (the competitive read is in
  [DPUs and SmartNICs](dpu-smartnic-offload.md)).
- **The roadmap outran the silicon.** Vision 2022 promised 400G codename
  parts and 800G by 2025 or later; Intel's catalog still fronts a 200G part,
  and the open-source networking recipe is archived.
- **The FPGA track is the differentiated asset.** Reprogrammable datapaths
  absorbed protocol churn (Microsoft's Catapult lineage) at the cost of power
  and programming difficulty.
- **Storage offload is the least contested win.** The 6M IOPS NVMe engine and
  virtio-blk emulation deliver disaggregated storage with no host software --
  the pattern the [computational
  storage](../../storage/computational-storage.md) postmortem and the DPU
  SNAP service both converge on.

## Interview lens

- *IPU vs DPU -- is there a technical difference?* Mostly branding, but
  Intel's framing emphasizes the CSP business split (tenant buys the CPU,
  provider owns the infrastructure and root of trust) and its two-track
  silicon; architecturally it is a DPU: programmable pipeline + Arm complex +
  crypto and storage engines.
- *Why co-design an ASIC instead of buying merchant DPUs?* The model above is
  the answer: at 100-200 GbE the offloaded work is worth hundreds of dollars
  per card per month, every watt is contested, and the provider -- not a
  merchant -- owns the feature list.
- *What is Falcon and why put a transport in hardware?* Reliable transport
  with delay-based congestion control and selective ACKs bounds tail latency
  under loss, which software handles worst at these rates.
- *Why P4 and open source on the IPU?* A bet that the software layer, not the
  silicon, decides adoption (PNA, IPDK, OPI). The archive notice on the
  networking recipe shows how that bet has fared so far.

## References

1. Intel / Brad Burres et al., "Intel's Hyperscale-Ready Infrastructure Processing Unit (IPU)," Hot Chips 2021 slides: https://hc33.hotchips.org/assets/program/conference/day1/Intel%20TLM%20Hotchips%202021%20-%20Mt%20Evans%20R2a%20-%20Final%20version%202.pdf
2. Intel, IPU product page (E2100, use cases) and IPU SoC E2100 Product Brief (engine/interface specs) -- intel.com blocks curl; both fetched via text-render proxy: https://www.intel.com/content/www/us/en/products/details/network-io/ipu.html and https://www.intel.com/content/www/us/en/content-details/818147/content-details.html
3. Intel PSG, "Intel Rolls Out Multi-Generation IPU Roadmap at Vision 2022" (two-track rationale, codenames, Google collaboration): https://community.altera.com/blog/fpga-blog/intel-rolls-out-multi-generation-infrastructure-processing-unit-ipu-roadmap-at-v/246424
4. Intel Community, "The IPU: A New, Strategic Resource for Cloud Service Providers" (Aug 2021 Mount Evans announcement; page blocks curl, search-verified): https://community.intel.com/t5/Blogs/Tech-Innovation/Data-Center/The-IPU-A-New-Strategic-Resource-for-Cloud-Service-Providers/post/1335081
5. ServeTheHome, "This Changes Networking: Intel IPU Hands-on with Big Spring Canyon" (June 2022): https://www.servethehome.com/this-changes-networking-intel-ipu-hands-on-with-big-spring-canyon/
6. IPDK README and archived Networking Recipe / P4 Control Plane README: https://github.com/ipdk-io/ipdk and https://github.com/ipdk-io/networking-recipe
7. P4 Language Consortium, Portable NIC Architecture (PNA) repo and specs page: https://github.com/p4lang/pna and https://p4.org/specs
8. Open Programmable Infrastructure (OPI) Project, Linux Foundation: https://opiproject.org/
9. Linux kernel docs, "idpf Linux Base Driver for the Intel(R) Infrastructure Data Path Function": https://docs.kernel.org/networking/device_drivers/ethernet/intel/idpf.html
