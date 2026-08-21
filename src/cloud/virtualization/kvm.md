# KVM (Kernel-based Virtual Machine)

KVM is the virtualization facility that turned the Linux kernel into a Type-1
hypervisor. Merged in 2.6.20 (2007), it does not invent a new scheduler or
memory subsystem — it reuses the kernel's existing primitives and adds a thin
layer that exposes the CPU's hardware virtualization extensions (Intel VMX /
AMD SVM) to userspace. A KVM virtual machine is a normal Linux process
(`QEMU`), pinned or scheduled like any other task, while its vCPUs execute
guest code directly on the physical CPU with the host kernel arbitrating the
boundary.

## The `/dev/kvm` character device

The user-visible API is a single character device, `/dev/kvm`, opened with
`O_RDWR` and operated on exclusively via `ioctl(2)`. There is no special
filesystem, no daemon, no network protocol — the entire contract is ioctl
numbers and structs declared in `<linux/kvm.h>`.

Three nested objects form a VM:

- A **VM** (`KVM_CREATE_VM` on the `/dev/kvm` fd) holds the guest physical
  address space and IRQ routing tables.
- A **vCPU** (`KVM_CREATE_VCPU` on the VM fd) represents a virtual CPU with
  its own run loop and private register state.
- A **device** (`KVM_CREATE_DEVICE`) wraps in-kernel emulated devices such as
  the in-kernel PIC/IOAPIC/PIT or virtio back-ends.

The flow when QEMU starts a VM is roughly:

```
  open("/dev/kvm")                          -> kvm_fd
  ioctl(kvm_fd, KVM_GET_API_VERSION)
  ioctl(kvm_fd, KVM_CREATE_VM, 0)           -> vm_fd
  ioctl(vm_fd, KVM_SET_USER_MEMORY_REGION)  /* maps guest GPA -> HVA */
  ioctl(vm_fd, KVM_CREATE_VCPU, 0)          -> vcpu_fd
  mmap(vcpu_fd, KVM_GET_VCPU_MMAP_SIZE)     -> struct kvm_run *
  ioctl(vcpu_fd, KVM_RUN)                   /* enters guest, returns on exit */
```

Guest memory is not allocated by the hypervisor. Userspace (`QEMU`) mmaps
anonymous memory and registers regions with `KVM_SET_USER_MEMORY_REGION`:

```c
struct kvm_userspace_memory_region region = {
    .slot            = 0,
    .guest_phys_addr = 0x10000,                  /* GPA in guest memory     */
    .memory_size     = 512ULL * 1024 * 1024,
    .userspace_addr  = (uint64_t)mmap_base,      /* HVA in QEMU process     */
    .flags           = 0,
};
ioctl(vm_fd, KVM_SET_USER_MEMORY_REGION, &region);
```

KVM installs the region into the EPT/NPT tables so that guest physical
addresses translate through one hardware walk to host virtual addresses, then
through the host page table to host physical addresses — a two-dimensional
page walk described below.

## VMCS and the per-vCPU run loop

On Intel VMX, every vCPU is bound to a **VMCS** (Virtual Machine Control
Structure) — a 4 KiB per-CPU hardware structure holding guest register state,
host register state, and execution controls. The kernel allocates one VMCS
per vCPU per physical CPU it can run on (the per-CPU VMCS is loaded with
`VMPTRLD` on entry, saved on exit).

The VMCS contains:

- **Guest-state area** — RAX–R15, RIP, RSP, RFLAGS, segment selectors and
  descriptors (CS, SS, DS, ES, FS, GS), LDTR, TR, GDTR, IDTR, SYSENTER MSRs.
  Loaded automatically on `VMLAUNCH`/`VMRESUME`.
- **Host-state area** — saved host RIP, RSP, segment state, restored
  automatically on `VMEXIT`.
- **VM-execution control fields** — pin controls (which interrupts cause
  exits), primary/secondary processor controls (which instructions cause exits
  — `RDTSC`, `INVD`, `MWAIT`, `HLT`, `INVLPG`, etc.), exception bitmap,
  I/O bitmaps, MSR bitmaps.
- **VM-entry/exit controls** — what is loaded on entry, what host state is
  restored on exit.

The KVM run loop is the heart of every vCPU thread:

```
    ┌───────────────────────────────────────────┐
    │ ioctl(KVM_RUN)              [userspace]    │
    └──────────────┬────────────────────────────┘
                   │
    ┌──────────────▼────────────────────────────┐
    │ vmlaunch / vmresume         [host kernel]  │  install VMCS, load guest
    └──────────────┬────────────────────────────┘
                   │
    ┌──────────────▼────────────────────────────┐
    │ GUEST MODE — runs at CPL 0 in guest kernel │  native CPU speed
    │ until a vmexit trigger fires               │
    └──────────────┬────────────────────────────┘
                   │  (HLT, IN/OUT, WRMSR, EPT violation, IRQ window…)
    ┌──────────────▼────────────────────────────┐
    │ vmexit handler in KVM      [host kernel]   │  decode exit reason,
    │  · emulate the offending insn              │  update KVM_RUN struct,
    │  · return to userspace if needed           │  return to QEMU on I/O
    └──────────────┬────────────────────────────┘
                   │
    ┌──────────────▼────────────────────────────┐
    │ ioctl(KVM_RUN) returns to QEMU             │  handle device I/O,
    │                                            │  then re-issue KVM_RUN
    └────────────────────────────────────────────┘
```

Exit reasons live in `struct kvm_run`. Frequent ones:

| Reason | Cause | Handled by |
|--------|-------|------------|
| `KVM_EXIT_HLT` | `HLT` instruction | kernel: block vCPU until IRQ |
| `KVM_EXIT_IO` | `IN`/`OUT` to untrapped port | userspace (QEMU) |
| `KVM_EXIT_MMIO` | read/write to MMIO region | userspace (QEMU) |
| `KVM_EXIT_IRQ_WINDOW_OPEN` | waiting for IRQ injection window | kernel |
| `KVM_EXIT_INTERNAL_ERROR` | triple fault, etc. | fatal |

The challenge of good virtualization is making exits rare. `HLT`, `MWAIT`,
and `PAUSE` can be left in (cheap); `INVLPG` and `WRMSR` of TSC can be passed
through; `RDPMC` can be configured to not exit. The processor-based
VM-execution controls are a knob-and-lever game measured by `perf kvm stat`.

## EPT and NPT: hardware two-dimensional paging

Without hardware support, KVM would have to **shadow** the guest page tables:
every guest `CR3` write would invalidate the shadow tables, every guest
page-fault would trigger a host exit, every guest PTE write would have to be
trapped. Shadow paging is roughly an order of magnitude slower than running
native.

Intel's **EPT** (Extended Page Tables, introduced with Nehalem) and AMD's
**NPT** (Nested Page Tables, also called RVI) eliminate this. The hardware
does two page walks in sequence:

```
   Guest virtual address (gVA)
            │
            ▼
   ┌──────────────────────┐
   │  Guest page table    │  walk gVA -> gPA  (guest owns CR3)
   │  (guest PML4..PTE)   │
   └──────────┬───────────┘
              │  guest physical address (gPA)
              ▼
   ┌──────────────────────┐
   │  EPT / NPT           │  walk gPA -> hPA  (host owns EPTP)
   │  (host EPT PML4..PTE)│
   └──────────┬───────────┘
              │  host physical address (hPA)
              ▼
        physical DRAM
```

An EPT PTE has its own `R`/`W`/`X` permission bits and a memory type field.
A guest page-fault (the guest's own #PF on its own tables) becomes a normal
guest interrupt — no vmexit. Only when the EPT walk itself faults (page not
present in EPT, or permission violation) does the CPU trap with
`EXIT_REASON_EPT_VIOLATION`. EPT walks themselves cost more cycles than a
single walk — but with EPT PTEs cached in the TLB (tagged with **VPID** on
Intel, **ASID** on AMD), the steady-state cost is small. Two implications
worth memorising:

1. **Large pages.** KVM can map a 2 MiB guest page with a single 2 MiB EPT
   PTE (instead of 512 4 KiB EPT PTEs), roughly halving EPT TLB pressure.
   QEMU/KVM does this automatically when the backing memory is 2 MiB-aligned
   and `CONFIG_TRANSPARENT_HUGEPAGE` permits.
2. **Region churn.** `KVM_SET_USER_MEMORY_REGION` invalidates EPT entries for
   the affected range; the cost of adding/removing memory regions on a live
   VM is non-trivial because every vCPU's EPT for that range must be flushed.

## virtio: the paravirtualized device contract

If EPT makes memory fast, **virtio** makes I/O fast. The contract is a
memory-only ring buffer shared between the guest front-end driver and the host
back-end. The guest enqueues descriptors, optionally writes to a "kick" door
bell (a PCI BAR or MMIO register), and the host pops descriptors, does the
I/O, posts completions, and signals the guest via an IRQ.

```
  Guest userspace process
        │  (syscall: read on /dev/vda, sendto on eth0…)
        ▼
  Guest kernel: virtio-blk / virtio-net front-end driver
        │  writes descriptor (addr, len, RW) to shared ring "vring"
        │  writes SCHED_NOTIFY to PCI BAR ("kick")
        ▼
  ┌──────────────────────────────────────┐
  │  Host-side processing                 │
  │                                      │
  │  (a) QEMU userspace     — generic,   │  1 syscall per poll
  │                           slow       │
  │  (b) vhost-net kernel   — fast,      │  ring handled in kernel
  │  (c) vDPA / SR-IOV       — fastest,   │  hardware handles ring
  └──────────────────────────────────────┘
        │  raises IRQ via irqfd → KVM IRQ injection
        ▼
  Guest kernel: vring interrupt fires, front-end processes completion
```

A split virtqueue has three parts in guest memory:

```c
struct virtq {
    struct virtq_desc  *desc;   /* 16-byte: addr, len, flags, next      */
    struct virtq_avail *avail;  /* guest→host: "I added descriptors"    */
    struct virtq_used   *used;  /* host→guest: "I processed these"      */
    uint16_t last_avail_idx;   /* host-side shadow of avail->idx        */
    uint16_t last_used_idx;    /* guest-side shadow of used->idx        */
};
```

The crucial fact: the ring lives in **guest memory**, so after the host has
registered the region via `KVM_SET_USER_MEMORY_REGION`, both sides see the
same physical page. No copying, no hypercall per descriptor — just an
interrupt to wake the poller.

## vhost: moving the back-end into the kernel

For network I/O, the QEMU userspace back-end requires a syscall to read the
ring and another to inject the completion IRQ. That is two context switches
per packet, which dominates at 10 GbE and above.

**vhost-net** (`/dev/vhost-net`) moves the back-end into the kernel. QEMU
sets up the virtio ring in guest memory, hands it to `vhost-net` via
`VHOST_SET_VRING_ADDR`, and gets out of the data path. From then on the
kernel polls the ring (either by the kick write trapping directly to vhost,
or by an `ioeventfd`), calls `sock_sendmsg`/`sock_recvmsg` against a TAP
device, and writes back completions — entirely in kernel mode, including the
IRQ injection through `irqfd`.

**ioeventfd** lets a guest kick trap straight into vhost without going
through QEMU. QEMU registers a memory address with `KVM_IOEVENTFD`:

```c
struct kvm_ioeventfd kev = {
    .addr      = 0xc000,                /* virtio PCI "queue notify" port   */
    .len       = 2,
    .datamatch = 0,
    .fd       = eventfd,                /* an eventfd shared with vhost-net */
    .flags    = KVM_IOEVENTFD_FLAG_DATAMATCH,
};
ioctl(vm_fd, KVM_IOEVENTFD, &kev);
```

When the guest does the notify-store, the in-kernel `kvm_io_bus` matches it
and `eventfd_signal`s without exiting to userspace. vhost-net's kernel thread
wakes, processes the ring, posts completions via the kernel `irqfd`, and the
guest sees a normal interrupt. QEMU is bypassed for the whole packet path.

**irqfd** is the symmetric counterpart: an `eventfd` registered with
`KVM_IRQFD` that lets any kernel context inject a guest IRQ by signalling the
fd, again without bouncing through userspace.

## KVM dirty page tracking and live migration

Live migration has three phases:

1. **Warm-up.** The destination creates an empty VM with the same
   configuration. The source iterates over its memory and sends it to the
   destination.
2. **Iterative pre-copy.** The source keeps running the VM. While running it
   queries KVM's dirty log every few hundred milliseconds and re-sends only
   pages that changed since the previous iteration.
3. **Stop-and-copy.** When the dirty rate is low enough that one final
   iteration will be fast (or after a max-downtime threshold is breached), the
   source pauses the VM, sends the final dirty pages plus CPU/device state,
   and the destination resumes execution.

The dirty log is the linchpin. Without it the source would have to
write-protect every guest page, take a `#PF` vmexit on every write, mark the
page dirty, restore write permission, and continue. That is unusably slow.

KVM uses hardware-assisted dirty tracking where available (Intel **PML** —
Page Modification Logging — and AMD's equivalent). PML adds a small per-CPU
log buffer; on every guest write to a page whose EPT PTE has the
dirty-tracking bit set, the CPU logs the guest physical address to the PML
buffer and continues execution. No vmexit. When the buffer fills (512
entries) KVM handles it (one vmexit per 512 dirty writes, amortised).
Without PML, KVM falls back to write-protecting each page on the dirty log
request and re-protecting after.

Userspace turns the log on by setting `KVM_MEM_LOG_DIRTY_PAGES` in the
`flags` of `kvm_userspace_memory_region`, then periodically calls:

```c
struct kvm_dirty_log dlog = {
    .slot         = region_slot,
    .dirty_bitmap = bitmap,            /* one bit per page, page-aligned */
};
ioctl(vm_fd, KVM_GET_DIRTY_LOG, &dlog);
```

Each bit set in the returned bitmap indicates a 4 KiB page dirtied since the
last query. Modern usage has moved to
`KVM_CAP_MANUAL_DIRTY_LOG_PROTECT2` which lets userspace clear bits (mark
pages clean) without write-protecting them again — important because the
stop-and-copy phase needs to know the working set without pausing the VM long
enough to re-fault every page.

## Comparison: KVM vs Xen vs VMware ESXi

| Dimension | KVM | Xen | VMware ESXi |
|-----------|-----|-----|--------------|
| Architecture | Kernel module in Linux; each VM is a Linux process | Standalone microkernel + Dom0 (Linux) + DomU guests | Standalone VMkernel (POSIX-ish microkernel) |
| CPU virtualization | VMX/SVM with EPT/NPT | Same | Same |
| I/O model | virtio + vhost, plus SR-IOV, vDPA | PV front/back drivers ("netfront/netback", "blkfront/blkback"), plus hardware passthrough | vmxnet3, PVSCSI, vSAN client, NSX |
| Memory mgmt | Linux page cache, KSM, THP | Per-domain balloon driver, host page table managed by Xen | TPS (transparent page sharing), ballooning, compression, swapping |
| Management API | libvirt, virtctl | xl, Xen Orchestra, XAPI | vCenter SOAP API, PowerCLI |
| Live migration | `virsh migrate --live`, QEMU migration protocol | `xl migrate` | vMotion |
| Host attack surface | Whole Linux kernel | Xen hypervisor (small) + Dom0 kernel (large) | VMkernel (smaller than Linux but full POSIX surface) |
| Notable users | AWS (Nitro), Google Cloud, OpenStack, Proxmox, Oracle Cloud | Citrix Hypervisor, originally AWS EC2 | vSphere enterprise estate, VMware Cloud on AWS |

Three substantive technical differences worth memorising:

1. **Scheduling.** KVM vCPUs are scheduled by Linux's CFS/EEVDF alongside
   everything else. Xen has its own scheduler (credit2) for guests; Dom0 is
   also scheduled by Xen. ESXi has its own scheduler (co-scheduling with
   relaxed guest synchronisation). The KVM approach gives you free integration
   with cgroups (you can put a VM in a CPU-limited cgroup and CFS does the
   rest) but makes per-vCPU latency subject to host load.
2. **Device model location.** In Xen, `netback`/`blkback` live in Dom0 (a
   separate Linux kernel) and guest→host is a hypercall. In KVM, `vhost` runs
   in the same kernel as the guest, which means fewer mode switches but a
   worse failure blast radius (a `vhost-net` bug can panic the host and every
   VM on it).
3. **Memory accounting.** KVM guests share the host's page cache and KSM can
   deduplicate identical pages across VMs. Xen has no automatic cross-domain
   sharing. ESXi's TPS used to dedup aggressively across VMs but is now off by
   default for security (cross-VM side-channel risk).

## Pitfalls and interview-style questions

**Why is `/dev/kvm` a character device and not a syscall?**
Because the existing `ioctl(2)` mechanism is sufficient and keeps the API out
of the syscall table. ioctls are versioned via `_IOR`/`_IOW`/`_IOWR` macros
in `<linux/kvm.h>`; adding new ones does not require kernel/userspace ABI
churn. The device model also naturally supports capabilities
(`KVM_CHECK_EXTENSION`) and per-VM/VCPU fd ownership.

**What does `vcpu->mode == IN_GUEST_MODE` mean?**
A vCPU struct has a per-CPU state machine: `OUTSIDE_GUEST_MODE`,
`IN_GUEST_MODE`, `EXITING_GUEST_MODE`. When in `IN_GUEST_MODE`, signals
targeting the vCPU thread are deferred — the kernel must wait for a vmexit
before delivering them. This is why `KVM_RUN` is interruptible but with care:
KVM uses `signal_pending()` checks at the next exit boundary, not
immediately.

**Why is dirty page tracking important for snapshot-based backups too?**
Because the same primitive powers crash-consistent snapshots across multiple
VMs on a host. Back up all VMs' disks via storage-layer snapshot, then walk
each KVM dirty log to discover which guest pages were being modified during
the storage snapshot, and re-read those from a copy-on-write image. The dirty
log is the bridge between "what the guest sees" and "what's on disk".

## Cross-references

- [Hypervisors overview](./hypervisors.md) — KVM in context with Xen and ESXi
- [Firecracker](./firecracker.md) — a Rust VMM that drives KVM at scale
- [Kata Containers](./kata-containers.md) — OCI runtime backed by KVM
- [AWS EC2 and Nitro](../aws/ec2.md) — AWS's KVM-based hypervisor
- [Linux kernel module concepts](../../cheatsheets/linux.md)

## References

- [KVM — kernel.org documentation](https://docs.kernel.org/virt/kvm/index.html)
- [KVM API reference](https://docs.kernel.org/virt/kvm/api.html)
- [LWN: KVM merge announcement (2007)](https://lwn.net/Articles/221019/)
- [LWN: KVM — a Type-1 hypervisor (2007)](https://lwn.net/Articles/239261/)
- [Intel 64 and IA-32 SDM, Vol. 3C, Ch. 23–35 (VMX architecture)](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html)
- [AMD64 Architecture Programmer's Manual, Vol. 2 (SVM)](https://developer.amd.com/resources/developer-guides-manuals/)
- [LWN: vhost-net, a kernel-level virtio back-end (2010)](https://lwn.net/Articles/361301/)
- [QEMU live migration documentation](https://www.qemu.org/docs/master/devel/migration.html)
- [KVM Forum archives](https://kvmforum2023.sched.com/)
