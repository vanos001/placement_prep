# Virtualization

Hardware virtualization allows multiple operating systems to share a single physical machine, each believing it owns the hardware. This is the foundation of cloud computing, and understanding the mechanics of VM exits, extended page tables, and device assignment is critical for anyone working on cloud infrastructure, hypervisors, or performance-sensitive virtualized workloads.

## OS-Level Virtualization vs. Paravirtualization vs. Hardware-Assisted

### OS-Level Virtualization (Containers)

Containers share the host kernel and use [namespaces](../containers/namespaces.md) and [cgroups](../containers/cgroups.md) for isolation. There is no hypervisor, no guest kernel — processes run directly on the host with restricted views of system resources. Near-zero overhead but limited to the host OS ABI. Docker, LXC, and Kubernetes use this model.

### Paravirtualization

The guest OS is modified to be aware it is virtualized. Instead of executing privileged instructions that would trap, the guest calls **hypercalls** — explicit calls into the hypervisor (analogous to system calls into a kernel). Xen's paravirtualized guests replace `cli`/`sti`, `iret`, and page table updates with hypercalls like `HYPERVISOR_event_channel_op`.

Performance advantage: no VM exit for operations the guest knows are virtualized. Disadvantage: requires kernel modifications (though Linux has built-in Xen and KVM paravirt support via `CONFIG_PARAVIRT`). The `pvops` (paravirt ops) infrastructure in Linux uses function pointers that are patched at boot time to either native instructions or hypercalls.

### Hardware-Assisted Virtualization (HVM)

Intel VT-x (2005) and AMD-V (2006) added hardware support for virtualization. The CPU gains a new privilege mode above ring 0: **VMX root mode** (ring -1) for the hypervisor, with guests running in **VMX non-root mode**. Certain instructions automatically cause **VM exits** that transition control from the guest to the hypervisor.

## VM Exit and VM Entry

A VM exit is the fundamental cost of virtualization. When the guest executes a privileged instruction (e.g., `cpuid`, `invlpg`, `wrmsr`, or an I/O port access), the CPU saves the guest state to a **VMCS** (Virtual Machine Control Structure) and jumps to the hypervisor's VM exit handler. A VM entry reverses this.

```
Guest Execution (VMX non-root mode)
    │
    │ Executes: outb(0x3F8, data)  ← I/O instruction
    │
    ▼
VM Exit (~500-2000 cycles on modern CPUs)
    │
    │ 1. Save guest state to VMCS
    │ 2. Load host state from VMCS
    │ 3. Jump to VM exit handler (hypervisor)
    │
    ▼
Hypervisor handles I/O (emulated or passthrough)
    │
    ▼
VM Entry (~200-500 cycles)
    │
    ▼
Guest resumes execution
```

VM exit latency varies by cause: EPT violations are ~300 cycles, I/O port exits are ~1000 cycles, and MSR accesses can be ~1500 cycles. KVM and Xen minimize VM exits through techniques discussed below.

### Common VM Exit Causes

- **EPT Violation**: Guest accessed a physical page not mapped in EPT (see below). Used for shadow page table management and demand paging in the guest.
- **I/O Port Access**: Guest accessed an I/O port (`in`/`out` instructions). The hypervisor emulates the device.
- **MSR Access**: Guest read/wrote a model-specific register. Often for APIC or TSC access.
- **Exception/Interrupt Window**: Guest requested interrupt injection or masked interrupts too long.
- **HLT/PAUSE**: Guest halted or entered a spin-wait loop.
- **CR Access**: Guest modified CR0/CR3/CR4. CR3 changes trigger EPT flush.

## Extended Page Tables (EPT) and Nested Page Tables (NPT)

Without EPT/NPT, the hypervisor must maintain **shadow page tables**: for each guest page table, the hypervisor maintains a corresponding "shadow" page table that translates guest virtual → host physical addresses. Every guest page table modification triggers a VM exit to update the shadow. This is expensive — KVM's shadow page table path involves ~1000 cycles per guest TLB miss.

**EPT (Intel)** and **NPT (AMD)** add a second-level address translation in hardware: **GVA → GPA → HPA**. The guest manages its own page tables (GVA → GPA). A separate EPT/NPT page table (managed by the hypervisor) translates GPA → HPA. Both translations are performed by the CPU's MMU in a single TLB lookup using a unified **guest-physical TLB**.

```
Guest Virtual Address (GVA)
    │ Guest Page Tables (guest manages)
    ▼
Guest Physical Address (GPA)
    │ EPT/NPT (hypervisor manages)
    ▼
Host Physical Address (HPA)

Without EPT:  GVA → [VM exit] → shadow PT → HPA  (slow)
With EPT:    GVA → guest PT → GPA → EPT → HPA   (fast, hardware)
```

EPT reduces VM exits dramatically: CR3 changes no longer trap, and most memory accesses proceed without hypervisor involvement. The cost is ~5% overhead on EPT walk for TLB misses. KVM uses EPT by default on Intel and NPT on AMD since Linux 2.6.27.

### EPT Misconfigurations and Violations

An **EPT misconfiguration** occurs when the EPT entry itself is malformed (e.g., reserved bits set). This is a hypervisor bug. An **EPT violation** occurs when the guest accesses a GPA that is not mapped or lacks sufficient permissions in EPT. EPT violations are normal — they're used for: demand paging, page swapping, and memory ballooning.

## Nested Virtualization

Nested virtualization runs a hypervisor inside a VM. KVM supports this via `vmx` (Intel) or `svm` (AMD) nested virtualization. The challenge: VMX non-root mode doesn't support running `VMXON`, so the guest hypervisor's VMX instructions must be trapped and emulated by the host hypervisor.

```
L0 Hypervisor (KVM on bare metal)  — VMX root mode
  └── L1 Guest (KVM in VM)         — VMX non-root mode
        └── L2 Guest (VM in VM)    — "VMX non-root^2" (emulated)
```

Every L2 VM exit becomes a double VM exit: L2 guest → L1 hypervisor (trapped by hardware) → L0 hypervisor (emulated). This is called **VMCS shadowing**. Intel added `VMCS shadowing` (VMFUNC) in Haswell to reduce this: L0 maintains a shadow VMCS for L1, and hardware can transition between L1 and L2 without L0 intervention for most exits. Without VMCS shadowing, nested virt adds ~5-10x overhead; with it, ~2-3x.

## IOMMU — Input/Output Memory Management Unit

The IOMMU (Intel VT-d, AMD-Vi) extends virtualization to devices. Without an IOMMU, a DMA-capable device can write to any physical address, bypassing the hypervisor's address translation. The IOMMU creates a **DMA remapping table** that constrains each device's DMA to specific physical address ranges.

```c
// IOMMU DMA remapping: device sees GPA, hardware translates to HPA
// Without IOMMU: device DMA → arbitrary HPA (security hole)
// With IOMMU:    device DMA → GPA → IOMMU → HPA (safe)
```

The IOMMU also enables: **interrupt remapping** (preventing interrupt spoofing), **DMA protection** (preventing rogue devices from corrupting memory), and is a prerequisite for both SR-IOV and VFIO device passthrough.

## SR-IOV — Single Root I/O Virtualization

SR-IOV allows a single physical PCIe device (e.g., a 100 GbE NIC) to present itself as multiple **Virtual Functions (VFs)** — up to 256 — each with its own configuration space, DMA queues, and interrupt vectors. Each VF can be directly assigned to a different VM.

```
Physical Function (PF) — managed by hypervisor
  ├── VF 0 → VM 0 (direct hardware access, no emulation)
  ├── VF 1 → VM 1
  ├── VF 2 → VM 2
  └── VF N → VM N
```

Each VF is a lightweight PCIe function that shares the physical device's resources (MAC, queues, DMA engines) but appears as an independent device to the guest. The PF manages resource allocation and configuration. SR-IOV eliminates the hypervisor's device emulation overhead entirely — the guest driver talks directly to hardware.

Performance: an SR-IOV VF on a ConnectX-5 NIC delivers ~95% of bare-metal throughput with <1 µs additional latency vs. direct assignment.

## VirtIO — Paravirtualized Device Framework

VirtIO (Rusty Russell, 2008) is a standardized paravirtualized device interface for KVM/QEMU. Rather than emulating real hardware (e.g., an Intel E1000 NIC, which requires trapping every MMIO access), VirtIO defines a minimal, efficient interface that reduces VM exits.

The core mechanism is **virtqueues** — shared ring buffers between guest and host:

```c
// Simplified virtqueue layout (split virtqueue)
struct virtqueue {
    struct vring_desc *desc;   // Descriptor table (shared memory)
    struct vring_avail *avail; // Available ring (guest → host)
    struct vring_used *used;   // Used ring (host → guest)
    // All in guest-allocated, host-mapped memory
};

// Guest posts a buffer:
// 1. Fill descriptor with buffer address + length
// 2. Add descriptor index to avail ring
// 3. Kick (notify) host via MMIO write

// Host processes:
// 1. Read avail ring (no VM exit, shared memory)
// 2. DMA data directly from guest memory
// 3. Write completion to used ring
// 4. Inject interrupt into guest
```

VirtIO devices include: `virtio-net` (networking), `virtio-blk` (block), `virtio-scsi`, `virtio-gpu`, `virtio-fs` (shared filesystem via FUSE). Modern QEMU defaults to VirtIO for all device types. The `virtio_ring` supports three modes: split (legacy), packed (reduced memory usage, single ring), and in-order (processing hints).

## VFIO — Virtual Function I/O

VFIO is the Linux kernel framework for **direct device passthrough** to user-space or VMs. Combined with an IOMMU, VFIO gives a process or VM direct, unmediated access to a physical device — no emulation, no shared ring buffers.

```bash
# Bind a NIC to vfio-pci (unbind from normal driver first)
echo 0000:01:00.0 > /sys/bus/pci/devices/0000:01:00.0/driver/unbind
echo vfio-pci > /sys/bus/pci/devices/0000:01:00.0/driver_override
echo 0000:01:00.0 > /sys/bus/pci/drivers_probe

# Pass to QEMU VM
qemu-system-x86_64 -device vfio-pci,host=01:00.0 ...
```

VFIO exposes device regions (MMIO, PIO, config space) as `mmap()`-able files in `/dev/vfio/`. The IOMMU ensures the device can only DMA to the VM's memory. VFIO supports: single device passthrough, SR-IOV VF passthrough (combines SR-IOV + VFIO), and mediated devices (mdev) where a physical device exposes multiple virtual devices (e.g., NVIDIA vGPU).

## Comparison

| Feature | Full Emulation | VirtIO (Paravirt) | SR-IOV | VFIO Passthrough |
|---------|---------------|-------------------|--------|-----------------|
| VM exits per I/O | High (MMIO traps) | Low (ring buffer) | Near zero | Zero |
| Guest driver needed | Native (e.g., e1000) | VirtIO driver | Native | Native |
| Device isolation | Full | Full (hypervisor) | Per-VF | Full (IOMMU) |
| Overhead vs bare metal | 20-50% | 3-10% | 1-5% | <1% |
| Live migration | Yes | Yes | Limited | No (device state) |
| Multi-VM sharing | Yes (emulated) | Yes (multiplexed) | Yes (VFs) | No (exclusive) |

## Interview Questions

1. **"What is a VM exit and why is it expensive?"** Answer hint: A VM exit saves the full guest architectural state (~700 bytes) to the VMCS, performs a mode transition from VMX non-root to root, and loads the host state. This costs ~500-2000 cycles depending on the exit reason. Each exit also flushes the guest's TLB entries, causing subsequent memory accesses to be slower.

2. **"How does EPT improve virtualization performance?"** Answer hint: EPT adds a second-level hardware page table translation (GPA→HPA) so the hypervisor doesn't need to maintain shadow page tables. This eliminates VM exits on CR3 changes and TLB flushes, reducing VM exit frequency by ~10-100x for memory-intensive workloads. The trade-off is ~5% overhead on TLB miss walk latency.

3. **"VirtIO vs. SR-IOV — when would you choose each?"** Answer hint: SR-IOV for maximum throughput (trading flexibility for performance), VirtIO when you need live migration, shared device multiplexing, or don't have SR-IOV-capable hardware. SR-IOV requires NICs that support it; VirtIO works with any emulated device.

4. **"What does the IOMMU protect against?"** Answer hint: DMA attacks by untrusted devices (a malicious USB device DMAing into kernel memory), interrupt storms (interrupt remapping), and is required for safe device passthrough (VFIO). Without IOMMU, any device can DMA to any physical address.

## References
- Intel SDM, Volume 3C, Chapters 28-30 (VMX) and Chapter 30 (VT-d)
- Russell, R. "virtio: Towards a De-Facto Standard for Virtual I/O Devices." 2008.
- Ben-Yehuda et al. "The Price of Virtualization." EuroSys 2010.
