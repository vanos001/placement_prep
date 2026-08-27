# SR-IOV and Network Virtualization Offload

A virtualized NIC is normally a software invention: a device model (QEMU e1000/virtio-net)
emulated in the hypervisor, with every packet crossing a VM boundary through exits,
copies, and a vhost thread. SR-IOV pushes the multiplexing into the hardware itself: one
physical NIC presents many PCI functions, and a guest drives its function directly with
DMA into its own memory. This page covers PF/VF, the isolation machinery
(VFIO/IOMMU/ATS), why the data path is fast and migration is painful, the virtio-keeping
middle ground (vDPA), switchdev and representors, OVS offload, and the Kubernetes
plumbing. General passthrough and IOMMU-group mechanics are in
[VFIO](../../linux/virtualization/vfio.md); the virtio side in
[virtio & vhost](../../linux/virtualization/virtio.md).

## Three ways to give a VM a NIC

```text
 (a) emulated / paravirtual            (b) SR-IOV passthrough           (c) vDPA
 --------------------------            ----------------------           ----------------
   guest VM                               guest VM                        guest VM
   virtio-net driver                      ixgbe/mlx5 driver               virtio-net driver
     | ring (virtqueue)                     | real NIC rings                | virtqueue layout
     v                                      v                               v
   kvm ioeventfd / vhost                  IOMMU (DMA remap)               vDPA framework
     |                                      |                               |  ctrl: QEMU
     v                                      v                               v  data: HW
   userspace/kernel vhost worker          NIC queues (VF rx/tx)           NIC HW queues
     |                                      |                               |
     v                                      v                               v
   PF (host-owned)  <----------------- eswitch (PF side) -------------------> eswitch
     |                                      |                               |
   softswitch (OVS/bridge)                direct to wire                 direct to wire
     |
     v
   uplink NIC
 copies: 2+   exits: per packet      zero-copy, no exits, no worker    zero-copy, virtio ABI
 latency: ~10-40 us                   ~2-5 us class                    ~virtio interface,
 migration: easy                      migration: painful                migration: tolerated
```

## PF/VF: the hardware model

The PCI-SIG SR-IOV specification (Single Root I/O Virtualization and Sharing, rev 1.1)
extends PCIe with functions that share one device:

- The **PF** (Physical Function) is the full PCI function the host driver owns. It
  configures SR-IOV through a standard extended capability: the driver writes NumVFs,
  sets the VF Enable bit, and the device materializes VFs as new PCI functions with their
  own config space, MSI-X tables, and queue sets. ARI (Alternative Routing-ID
  Interpretation) extends the function-number space so large VF counts fit.
- Each **VF** is a stripped PCI function: its own rings, filters, interrupts -- but no
  independent reset semantics you can trust (see failure modes) and no direct wire access
  without the eswitch on the PF side forwarding/steering.
- MMIO is carved up at enable time: the capability declares a VF BAR offset and stride,
  and each VF gets its window. Sizing this wrong is a classic bring-up failure (see the
  MMIO math below).
- Count examples: Intel 82599-class 10GbE parts expose up to 63 VFs per port (the DPDK
  intel_vf guide documents the 63 + 1 PF split); ConnectX-5 exposes up to 64 VFs per
  port (128 per dual-port card). Order of magnitude: tens of VFs per NIC, not thousands.

Hardware guard rails the PF driver must set: MAC/VLAN anti-spoof per VF, VF link state
control, rate limiting, and trust mode (a trusted VF may program offloads that an
untrusted one may not).

Operational sequence on the host (illustrative; device names vary by driver):

```bash
# 1) create VFs (driver-specific module param or devlink param)
echo 8 > /sys/bus/pci/devices/0000:03:00.0/sriov_numvfs
# 2) see the VFs appear as separate PCI functions
lspci -d 0000:03: | tail -n +2          # 03:00.1, 03:00.2, ... 03:10.7
# 3) hand one to a VM: unbind from host, bind to vfio-pci
echo 0000:03:00.2 > /sys/bus/pci/devices/0000:03:00.2/driver/unbind
echo vfio-pci > /sys/bus/pci/devices/0000:03:00.2/driver_override
echo 0000:03:00.2 > /sys/bus/pci/drivers/vfio-pci/bind
# 4) QEMU consumes it as a host device (-device vfio-pci,host=03:00.2)
```

## Passthrough mechanics: VFIO, IOMMU, ATS

Binding a VF to vfio-pci hands the guest three things: the PCI function itself (config
space, BARs, MSI-X), interrupt delivery (posted MSI-X into the guest), and -- the part
that makes it safe -- DMA isolation. The IOMMU (Intel VT-d / AMD-Vi) reprograms DMA
remapping per device: the guest programs its VF's rings with *guest-physical* addresses
and the IOMMU translates them through an I/O page table, so the device can only reach the
frames the guest actually owns. A VF therefore lands in its own IOMMU group; if ACS
(Access Control Services) is missing or disabled on the path, functions can snoop each
other's traffic -- the `pcie_acs_override` kernel parameter "fixes" grouping by punching
a hole in isolation and should never exist in a multi-tenant fleet (see
[VFIO](../../linux/virtualization/vfio.md) for the grouping workflow).

ATS (Address Translation Services) closes the performance gap that isolation opens:
without it, every DMA misses the IOMMU's IOTLB and costs a translation walk. With ATS,
the device keeps its own translation cache (ATC) and requests translations through the
ATS capability; PRI (Page Request Interface) extends this so the device can demand-page
guest memory. On modern NICs with large ATCs, translation overhead for hot ring buffers
amortizes to nearly nothing.

## Why it is fast -- and why migration hurts

The win is subtraction, not addition: no VM exits per packet, no vhost worker hop, no
copy (DMA lands directly in guest buffers), and interrupts are delivered as guest MSI-X.
A 25/100G VF driven by DPDK or the kernel's native driver runs at line rate with a
fraction of one core; the same wire through vhost-user costs more CPUs and tens of
microseconds more latency. Kernel bypass stacks (DPDK poll-mode drivers, RDMA verbs --
see [RDMA](../../linux/networking/rdma.md)) sit naturally on VFs; XDP is the in-kernel
bypass alternative ([XDP](../../linux/kernel/networking/xdp-advanced.md)).

The price shows up at migration time. A virtio device's state is a handful of rings and
registers that QEMU can serialize; a VF's state lives in hardware queues, flow-steering
tables, filters, and driver-private context that no migration protocol can capture.
Standard practice: hot-unplug the VF before the stop phase and let the VM continue on a
companion virtio NIC. The kernel automates this with the net_failover pair: a standby
virtio netdev and the VF are joined under a failover master, so removing the VF for
migration switches traffic to virtio with the same MAC
([net_failover docs](https://docs.kernel.org/networking/net_failover.html)). It works,
but the minutes on virtio are slower, and any VF that refuses to unplug stalls migration.

## vDPA: virtio control plane, hardware data plane

vDPA (virtio data path acceleration) is the compromise: the device's data plane obeys
the virtio ring format (hardware consumes virtqueues directly), while a vendor-specific
control plane is abstracted by a kernel vDPA driver. The framework (merged in 2020)
splits into a vDPA bus, a management interface (`vdpa mgmtdev show`, `vdpa dev add
mgmtdev pci/0000:03:00.0 name vdpa0`), and two device flavors: virtio-vdpa (presents a
virtio device to the *host* kernel) and vhost-vdpa (a /dev/vhost-vdpa-N character device
for userspace, e.g. QEMU). The guest stays 100% virtio -- migration tooling, drivers,
and feature negotiation survive -- while the data path gets hardware speeds. VDUSE
extends the same interface the other way, letting a userspace daemon *supply* a vDPA
device ([VDUSE docs](https://docs.kernel.org/userspace-api/vduse.html)); Red Hat's
framework introduction is the clearest overview
([Red Hat vDPA blog](https://www.redhat.com/en/blog/introduction-vdpa-kernel-framework)).

## Switchdev, representors, OVS offload

VFs that bypass the host strand the softswitch: OVS on the host never sees VF traffic, so
tunnels, ACLs, and mirroring silently stop applying. Switchdev mode fixes this. The NIC
eswitch is set to `switchdev` (`devlink dev eswitch set pci/0000:03:00.0 mode switchdev`),
and each VF gains a **representor** netdev in the host (`ens1f0v0`, ...). A packet from
VF0 surfaces on ens1f0v0; a packet injected into ens1f0v0 is emitted from VF0. Now OVS
or a Linux bridge can treat VFs as ports -- and offload the slow path:

```bash
# switchdev mode + representor ports (see devlink page for the full workflow)
devlink dev eswitch set pci/0000:03:00.0 mode switchdev
ethtool -K ens1f0 hw-tc-offload on
# hardware flow: VF0 <-> uplink, L4 port 443, via tc flower with skip_sw
tc qdisc add dev ens1f0v0 clsact
tc filter add dev ens1f0v0 ingress protocol ip flower \
    ip_proto tcp dst_port 443 action mirred egress redirect dev ens1f0
# skip_sw means "must be offloaded": if the NIC rejects the flow, tc errors out
# (skip_hw would mean "software only"). Verify with:
tc filter show dev ens1f0v0 ingress        # in_hw count indicates offloaded filters
```

OVS uses the same tc-flower offload underneath when `other_config:hw-offload=true` is
set; flows that the datapath classifies get programmed into the eswitch ACL tables, and
only unmatched first packets traverse userspace
([OVS tc offload howto](https://docs.openvswitch.org/en/latest/howto/tc-offload/)).
Devlink is the control surface for eswitch mode, rate limiters, and port flavour
(`pf`/`vf`) state -- [devlink](../../linux/kernel/networking/devlink.md) documents the
command-level workflow, which this page deliberately does not duplicate.

## Kubernetes plumbing

Kubernetes exposes VFs through the device plugin API: a daemonset enumerates VFs per
node (filtering by driver type -- netdevice vs vfio-pci -- and by RDMA capability) and
advertises them as extended resources (e.g. `intel.com/intel_sriov_netdevice`,
vendor-specific prefixes for NVIDIA parts). A pod requesting the resource gets a
specific PCI VF allocated by kubelet. The **SR-IOV CNI** then moves that VF into the
pod's network namespace at pod creation (repo: k8snetworkplumbingwg/sriov-cni on
GitHub), applying MAC/VLAN from the annotation.
Multus wires the extra interface in via a NetworkAttachmentDefinition, because the
default CNI keeps the cluster network while SR-IOV adds the fast one
([sriov-network-device-plugin](https://github.com/k8snetworkplumbingwg/sriov-network-device-plugin)).

```yaml
# NetworkAttachmentDefinition: pod gets a VF on vlan 42
apiVersion: k8s.cni.cncf.io/v1
kind: NetworkAttachmentDefinition
metadata:
  name: sriov-vlan42
spec:
  config: |
    {
      "type": "sriov",
      "cniVersion": "0.3.1",
      "name": "sriov-vlan42",
      "master": "ens1f0",
      "vlan": 42,
      "ipam": {
        "type": "static",
        "addresses": [{ "address": "10.42.0.17/24" }]
      }
    }
```

Note what the pod loses on the VF path: NetworkPolicy (the cluster CNI never sees these
packets), service load balancing, and conntrack. Treat the SR-IOV interface as a
point-to-point or switch-offloaded leg, with control traffic on the regular pod network.

## MMIO window math (why sriov_numvfs fails at boot)

VFs request their MMIO up front. If the sum exceeds the PCI root bridge window the
BIOS/firmware carved (often 256 MiB below 4G), VF creation fails with "not enough MMIO
space" -- a favorite first-day failure on big cards and dense hosts:

```python
"""Does the SR-IOV BAR allocation fit a typical 256 MiB below-4G window?
BAR sizes are device-specific; check with `lspci -vv` (VF BAR stride/offset)."""
WINDOW = 256 * 1024 * 1024        # bytes; common BIOS VF window below 4G

rows = [(16, 64 * 1024), (32, 64 * 1024), (64, 1 * 1024 * 1024), (128, 1 * 1024 * 1024)]
print(f"{'VFs':>4} | {'VF BAR':>7} | {'total MMIO':>11} | fits 256MiB window")
for numvfs, bar in rows:
    total = numvfs * bar
    print(f"{numvfs:>4} | {bar//1024:>5}KiB | {total/1048576:>9.1f}MiB | "
          f"{'yes' if total <= WINDOW else 'NO -> raise window or cut VFs'}")
```

Real output (Python 3.12):

```text
 VFs |  VF BAR |  total MMIO | fits 256MiB window
  16 |    64KiB |       1.0MiB | yes
  32 |    64KiB |       2.0MiB | yes
  64 |  1024KiB |      64.0MiB | yes
 128 |  1024KiB |     128.0MiB | yes
```

Single-VF BARs of this size always fit; failures appear with multi-BAR VFs, resizable
BARs, or when the same window also holds GPUs (another large-BAR tenant). The fix is
firmware: enlarge the above-4G MMIO window (`pci=realloc`, BIOS "SR-IOV support" toggles)
-- not "try fewer VFs and hope".

## Failure modes

- **PF reset takes the VFs with it.** Function-level reset or a PF driver reload on the
  shared NIC resets all VFs: every VM on that card loses its NIC simultaneously. One
  host's driver update is a fleet-wide network event.
- **sriov_numvfs is write-once-ish.** Changing the count requires the PF down (and often
  a driver reload); doing it under load strands VFs in a half-configured state.
- **VF link flap storms.** An eswitch policy change or cable-level event can flap all VF
  carriers at once; upper-layer stacks (bonding, BGP) see a synchronized outage and
  stampede on reconvergence.
- **Isolation regressions.** ACS override or a broken IOMMU group lets VFs DMA outside
  their lease; the failure is silent until it is a security incident.
- **Migration hangs.** A VF that fails to hot-unplug leaves the VM paused mid-migration;
  monitor the failover pair state, not just the VF.
- **Driver/firmware skew.** VFs created by a newer PF firmware may expose features the
  guest VF driver mishandles; pin PF firmware and guest driver versions together.

## References

- [PCI-SIG: Single Root I/O Virtualization and Sharing Spec 1.1](https://pcisig.com/PCIExpress/Specs/IOV/SingleRootIOVirtualizationandSharing_1.1)
- [Kernel docs: net_failover (VF + virtio failover pair)](https://docs.kernel.org/networking/net_failover.html)
- [Kernel docs: VDUSE / vDPA userspace interface](https://docs.kernel.org/userspace-api/vduse.html)
- [sriov-network-device-plugin (Kubernetes device plugin for VFs)](https://github.com/k8snetworkplumbingwg/sriov-network-device-plugin)
- [Open vSwitch howto: tc flower hardware offload](https://docs.openvswitch.org/en/latest/howto/tc-offload/)
