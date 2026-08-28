# VM Exits and VM Entry: the Mechanics of the World Switch

A VM exit is the hardware-forced transfer of a physical CPU from guest (VMX
non-root / guest mode) to hypervisor (VMX root / host mode); VM entry is the
return trip. Every property of virtualization performance -- why `cpuid` hurts,
why APICv exists, why NVMe-in-guest is fast but a serial port is slow -- reduces
to two questions: *how often* does the CPU take this round trip, and *what
exactly* does the hardware have to save, load, and invalidate each time?

This page covers the transition mechanics themselves: the state containers
(VMCS/VMCB), the exit-reason taxonomy, a cycle-level cost model, the TLB
invalidation rules that ride along, and the exit-less mechanisms that remove
whole classes of exits. The conceptual VMM landscape is in
[Virtualization](./virtualization.md); KVM's subsystem layout, ioctls, and
memory model are in [KVM](../../cloud/virtualization/kvm.md). Here we go one
level lower than both.

## 1. The state containers: VMCS and VMCB

On Intel VMX, each vCPU has a **VMCS** (Virtual Machine Control Structure): a
4 KiB region whose first 8 bytes are a revision ID and an abort indicator,
followed by fields the CPU reads and writes on every transition. It is *not* a
documented structure -- fields are accessed only via `VMREAD`/`VMWRITE` with
26-bit field encodings. AMD's equivalent, the **VMCB**, is a documented 4 KiB
layout (control area, then guest state-save area) loaded via `VMLOAD`.

| VMCS field group | Examples | When it moves |
|---|---|---|
| Guest-state area | RIP, RSP, RFLAGS, CR0/3/4, DR7, FS/GS base, EPTP (`CR3` of the guest's second-level tables) | Guest -> saved on exit; restored on entry |
| Host-state area | RIP (host entry point), RSP, CR0/3/4, FS/GS/TR selectors | Loaded on *every* exit |
| VM-execution controls | Pin/CPU-based/secondary exec controls, IO & MSR bitmaps, TSC offset, APIC-access page, VPID, Posted-interrupt notification vector | Consulted while guest runs |
| VM-exit controls | Save/load debug controls, host address-space size | Applied on exit |
| VM-entry controls | Event injection (interrupt/exception/NMI), IA-32e mode | Applied on entry |
| Exit information (RO) | Exit reason, exit qualification, guest-linear address, guest-physical address, IDT-vectoring info | Written by CPU at exit |

Two details matter for cost anatomy. First, register save/restore is
**hardware-automatic but partial**: GPRs are *not* in the VMCS -- the exit
handler must spill/refill them (KVM does it in a small assembly stub). Second,
KVM keeps one VMCS per vCPU *per pCPU*, because host-state fields must
describe the pCPU the vCPU currently runs on.

```text
        one VM exit round trip (Intel)

   guest (non-root)                    host (root, KVM)
   ----------------                    -----------------
   ...guest instructions... exit-triggering event
        |
        v
   [1] CPU saves guest state to VMCS (RIP/RSP/RFLAGS/CRs/DR7) + writes
       exit reason, exit qualification (+ gVA/gPA if memory exit)
   [2] CPU loads host state: host RIP -> exit handler, host CR3, GS base
   [3] GPR spill in KVM asm stub; switch stack
        |                                  vmx_handle_exit(reason)
        |                                  [4] dispatch on exit reason
        |                                  [5] emulate/fix/inject
        |                                  [6] re-entry path: VMRESUME
   VMRESUME                                 [7] GPRs restored, event injected
        |                                   via VM-entry interruption-info
        v
   ...guest resumes after faulting insn (or at injected event)...
```

Steps 1-3 and 6-7 are fixed cost (the *world switch*); 4-5 is handler-specific
and is usually the larger half.

## 2. Exit reasons: what forces a switch

The 32-bit exit-reason field carries a 16-bit basic reason (Intel SDM Vol 3,
Appendix C enumerates ~90) plus qualifier bits (bit 31 set = failure *during*
VM entry, in which case guest state is not loaded at all). Exit
qualification -- a per-reason second word -- refines the basic reason:

| Class | Trigger examples | Typical qualifier content |
|---|---|---|
| Privileged instructions | `CPUID`, `WRMSR`, `INVD`, `INVLPG`, `MOV CR/DR` (per-bit controlled) | source/dest CR, MSR index |
| I/O | `IN`/`OUT` instructions; VMCB/VMCS can intercept only ranges via bitmaps | port, size, in/out, rep prefix |
| MMIO / APIC access | access to intercepted physical page range | guest-linear address |
| Memory (2nd-level faults) | **EPT violation**, EPT misconfiguration | access type (R/W/X), GPA |
| Interrupt/event delivery | guest interrupt-window exit, external interrupt (host-owned), NMI window | vector if external |
| Exceptions | guest `#PF` when intercepting (shadow page tables, some nested cases) | exception vector + error code |
| Timer / preemption | VMX preemption timer expired, guest TSC deadline | -- |
| Halt / pause / host-kick | `HLT` idle, `PAUSE` storm, posted-interrupt notification vector | -- |

Two rules of thumb: (1) *frequent-by-design* exits -- local APIC EOI, IPIs,
timer, MMIO doorbells -- are exactly what APICv/posted interrupts/paravirt
target (Sec. 5); (2) *cold* exits (EPT violations, `CPUID`) cost 4,000+ cycles
with handler but collapse in frequency once caches populate.

## 3. Cost anatomy

Published transition costs cluster around 1,000-2,000 cycles for the bare
switch on modern x86 (SDM quotes ~1,300 cycles for exit+entry on older
hardware; newer cores are similar -- the work is fixed, mostly VMCS reads plus
TLB checks). The *handler* dominates:

```text
cost of one emulated MMIO exit (illustrative, 3.0 GHz)

  0us          exit+entry hardware path                    ~1,200 cycles
               |- save/load VMCS state, host RIP/CR3
  handler      KVM dispatch + decode + emulate + inject    ~2,500 cycles
               |- vmexit -> handle_io -> emulate insn
               |- (worst case) exit to QEMU userspace:
               |    +sched latency + ioctl round trip
  resume       VMRESUME                                    included above
               total per event: ~3,700 cycles ~ 1.2us
```

A guest doing 20,000 such events per second burns 74 M cycles/s ~ 2.5% of one
core *before* counting QEMU round trips. The demo below runs this budget
across three mitigation stages; handler costs vary an order of magnitude by
exit class, and KVM's debugfs exit histograms (`kvm_stat`) are the empirical
source for a given machine.

## 4. TLB side effects: VPID, EPT tagging, and the 24-access problem

A transition must decide which translations remain valid. Intel's rules
(SDM Vol 3 Sec. 27.5, Sec. 28.3):

- **Guest linear mappings** are tagged with the 16-bit **VPID** (host runs as
  VPID 0). With VPID enabled, guest entries survive exit and re-entry -- no
  flush, no refill storm. Without VPID, guest linear mappings must be
  invalidated at each transition (the pre-Nehalem cost
  [Virtualization](./virtualization.md) describes).
- **Combined mappings** (guest-physical -> host-physical, cached by the EPT
  walker) are tagged with the EPTP's PML4 address (EP4TA) and persist across
  transitions for the same EPTP; software must issue **INVEPT** after changing
  EPT mappings -- what KVM does on mmu invalidations (mmu_notifier).
  **INVVPID** targets linear mappings by (VPID, address), e.g. for guest TLB
  shootdowns ([TLB Shootdowns](./tlb-shootdowns.md)).
- AMD mirrors this: the VMCB carries a 32-bit **ASID**; `INVLPGB`/`TLBRELOAD`
  (and `INVLPGA` for gVA+ASID) do the targeted invalidations.

The deeper interplay is the **two-dimensional walk**: a guest virtual access
under EPT/NPT walks guest page tables *and* EPT tables. Worst case with 4-level
guest tables and 4-level EPT: 4 guest-walk accesses, each triggering a 4-level
host walk (16), plus the data access's own 4-level host walk -- **24 memory
accesses** for one load. Large pages cut the depth; the
[page-table walks](../../arch/advanced/page-table-walks.md) page covers the
base machinery. EPT violations then become VM exits whose qualification encodes
R/W/X and the faulting GPA -- KVM's TDP page-fault path installs the mapping
and re-enters.

## 5. Making the frequent exits disappear

The design goal since ~2009 (Intel Broadwell APICv, AMD AVIC) is to keep the
vCPU running while the hardware services what used to trap:

| Frequent exit | Exit-less mechanism | How |
|---|---|---|
| Local APIC EOI | APICv EOI virtualization; Linux **PV-EOI** (`MSR_KVM_PV_EOI`) | CPU decrements/clears ISR in the virtual-APIC page without exit; PV-EOI instead writes a shared-memory byte |
| Send IPI | Posted interrupts (APICv/AVIC); Linux **PV IPI** hypercall `KVM_HC_SEND_IPI` | Target CPU's PIR set + notification vector delivered while non-root; PV hypercall batches N targets in one exit |
| Receive interrupt | **Posted-interrupt processing** | IRTE (VT-d) or AVIC routes interrupt to Posted-Interrupt Request bitmap + ON bit; running CPU moves PIR->IRR on notification vector, no exit |
| APIC register access (TPR etc.) | APIC-access page + TPR shadow, x2APIC MSR virtualization | Accesses hit the virtual-APIC page; only unsupported accesses exit |
| Timer | VMX preemption timer, guest TSC-deadline in virtual APIC | Deadline evaluated in hardware |
| Emulated device MMIO/PIO | vhost/vDPA kernels or SR-IOV VFs | Device work moves to kernel thread or real hardware -- see [virtio](../../linux/virtualization/virtio.md), [SR-IOV](../../networks/advanced/sr-iov-networking.md) |
| TLB shootdown | paravirt flush batching, `KVM_HC_KICK_CPU`/`SCHED_YIELD` for wakeup | Fewer IPIs -> fewer exits (see [hypercalls doc](https://docs.kernel.org/virt/kvm/x86/hypercalls.html)) |

The posted-interrupt path deserves the detail, because it is the pattern every
modern interrupt fabric (GICv4/v5, RISC-V IMSIC included) copied:

```text
                 device MSI-X write (remappable format, IRTE posted=1)
                     |
                     v
   [IOMMU/IR] look up IRTE -> PDA (posted-interrupt descriptor address)
                     |
                     v
   Posted Interrupt Descriptor (in guest-visible memory)
     PIR[256]: bit v set                  ON=1, NV=notification vector (e.g. 0xF2)
                     |
                     v
   CPU delivers self-IPI with vector NV  ->  arrives while vCPU in non-root
                     |
                     v
   hardware moves PIR -> vIRR, clears ON     (guest never exits)
```

If the vCPU is *not* running, the notification lands in the host; KVM then
wakes the vCPU thread and syncs PIR to IRR on the next entry. This is why
posted interrupts matter for device assignment: a guest NVMe queue's MSI-X
write reaches a running vCPU with zero exits. The remapping side (IRTE
programming, vector-spoofing prevention) is the IOMMU's job --
[IOMMU](../../linux/kernel/drivers/iommu.md),
[MSI/MSI-X](../../linux/kernel/drivers/msi-msix.md).

## 6. KVM's handling flow

Per vCPU, the loop is: `ioctl(KVM_RUN)` -> `vcpu_run` -> `vmx_vcpu_run` ->
assembly `vmx_vmenter` -> guest runs -> exit -> assembly stub -> C
`vmx_handle_exit` -> vendor handler table (`handle_io`, `handle_ept_violation`,
`handle_apic_access`, ...) -> either re-enter (fastpath: APIC-EOI, registered
MMIO write handlers) or set `vcpu->run->exit_reason` (`KVM_EXIT_IO`,
`KVM_EXIT_MMIO`, ...) and return to userspace QEMU for emulation it owns. The
[KVM API documentation](https://docs.kernel.org/virt/kvm/api.html) defines the
userspace-visible exit contract; the [KVM page](../../cloud/virtualization/kvm.md)
covers the device/vhost side. Exit *rates* per reason are observable per-VM
in debugfs KVM stats (`/sys/kernel/debug/kvm/<pid>-<vm>/stats/`, counters
such as `ept_violations` and `io_exits`) -- `kvm_stat` renders them live.

```python
# World-switch budget model: exits/second x per-exit cost -> vCPU overhead.
# All integer arithmetic; frequencies and costs are illustrative model constants.
FREQ = 3_000_000_000          # cycles per second (3.0 GHz)
SWITCH = 1_200                # exit+entry transition cost, cycles (both directions)

# event mix per vCPU-second: (class, exits/s, handler_cycles)
MIX_BASE = [
    ("PIO/MMIO emulated IO",  20_000, 2_500),
    ("APIC access (unvirt)",   5_000, 1_500),
    ("IPI without PV",         2_000, 2_000),
    ("EOI without PV",         8_000, 1_200),
    ("EPT violation (cold)",      50, 4_000),
    ("cpuid/wrmsr",             300, 1_500),
    ("timer",                    250, 1_500),
]
MIX_PV = [
    ("PIO/MMIO emulated IO",  20_000, 2_500),
    ("APIC access (unvirt)",   5_000, 1_500),
    ("EPT violation (cold)",      50, 4_000),   # PV-EOI + PV-IPI removed two rows
    ("cpuid/wrmsr",             300, 1_500),
    ("timer",                    250, 1_500),
]
MIX_EXITLESS = [
    ("EPT violation (cold)",      50, 4_000),   # + APICv/posted/vhost removed IO rows
    ("cpuid/wrmsr",             300, 1_500),
    ("timer",                    250, 1_500),
]

def budget(mix, label):
    exits = sum(n for _, n, _ in mix)
    cycles = sum(n * (SWITCH + h) for _, n, h in mix)
    pct = 100 * cycles // FREQ
    print(f"{label}")
    print(f"  exits/s={exits:>7,}  cycles/s lost={cycles:>12,}  vCPU overhead={pct:>2}%")
    return exits, cycles

print(f"model: {FREQ // 1_000_000} MHz vCPU, transition cost {SWITCH} cycles (exit+entry)")
print()
e_a, c_a = budget(MIX_BASE, "scenario A: unmitigated guest")
budget(MIX_PV, "scenario B: + PV-EOI + PV-IPI (KVM_HC_SEND_IPI)")
e_c, c_c = budget(MIX_EXITLESS, "scenario C: + APICv/posted ints + vhost (exit-less IO)")
print()
print(f"exits/s A->C: {e_a:,} -> {e_c:,} ({100 * (e_a - e_c) // e_a}% removed)")
print(f"switch cycles A->C: {c_a:,} -> {c_c:,} ({100 * (c_a - c_c) // c_a}% removed)")
print(f"sustainable exits/s at 1% overhead, free handler: {FREQ // 100 // SWITCH:,}")
print(f"same, with avg 2,000-cycle handler:             {FREQ // 100 // (SWITCH + 2_000):,}")
```

Real output:

```text
model: 3000 MHz vCPU, transition cost 1200 cycles (exit+entry)

scenario A: unmitigated guest
  exits/s= 35,600  cycles/s lost= 114,845,000  vCPU overhead= 3%
scenario B: + PV-EOI + PV-IPI (KVM_HC_SEND_IPI)
  exits/s= 25,600  cycles/s lost=  89,245,000  vCPU overhead= 2%
scenario C: + APICv/posted ints + vhost (exit-less IO)
  exits/s=    600  cycles/s lost=   1,745,000  vCPU overhead= 0%

exits/s A->C: 35,600 -> 600 (98% removed)
switch cycles A->C: 114,845,000 -> 1,745,000 (98% removed)
sustainable exits/s at 1% overhead, free handler: 25,000
same, with avg 2,000-cycle handler:             9,375
```

The takeaway is structural: mitigation does not make exits cheaper, it deletes
exit *classes* -- and the remaining 1%-of-CPU budget caps how many exits/s any
remaining emulation can cost (25,000/s with a free handler; under 10,000/s
once handlers average 2,000 cycles).

## Interview questions

1. **"Why is `CPUID` a VM exit, and why can't paravirt remove it?"** `CPUID`'s
   results are identity- and feature-shaped per vCPU (masked features,
   hypervisor leaves 0x40000000+), so hardware cannot fake them cheaply; KVM
   intercepts, filters, and returns a per-vCPU answer. Hypercalls reduce the
   *frequency* of work that would have exited, not the `CPUID` exit itself.
2. **"Guest writes to its own APIC EOI register -- trace both worlds."** Without
   APICv: MSR/APIC access exit -> KVM updates virtual-APIC state, re-injects
   pending -> re-entry (thousands of cycles x every interrupt). With APICv EOI
   virtualization: CPU clears ISR and, if an interrupt is pending in IRR,
   delivers it -- no exit. With PV-EOI: guest writes a shared page byte, host
   sees it lazily -- no exit even on older hardware without APICv.
3. **"Where do the 24 memory accesses of a 2D walk come from?"** 4-level guest
   walk needs 4 PTE accesses; each access itself requires a 4-level EPT/NPT walk
   (4x4 = 16); the final data access needs its own 4-level host walk (4). TLB
   caching collapses this in practice; the worst case explains why EPT large
   pages and VPID/ASID discipline matter ([page-table
   walks](../../arch/advanced/page-table-walks.md)).
4. **"What actually invalidates EPT-cached translations in a live-migration
   dirty-tracking scenario?"** Nothing automatically: hardware keeps combined
   mappings until software says otherwise. KVM writes EPT entries read-only /
   clears D-bits then issues INVEPT before the guest can take the write fault
   the dirty log needs.

## References

1. Intel 64 and IA-32 Architectures Software Developer's Manual, Vol 3, ch. 27-28
   (VM exits, VM entries, APIC virtualization) and Appendix C (exit reasons):
   <https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html> (HTTP 403 to automated fetchers -- bot-walled; canonical download page).
2. AMD64 Architecture Programmer's Manual, Vol 2: System Programming (SVM, VMCB,
   ASID, AVIC): <https://docs.amd.com/v/u/en-US/24593_3.45_APM_Vol2> (HTTP 200).
3. KVM API documentation (`KVM_RUN`, `KVM_EXIT_*` contract):
   <https://docs.kernel.org/virt/kvm/api.html> (HTTP 200).
4. KVM x86 hypercalls (`KVM_HC_SEND_IPI`, `KVM_HC_KICK_CPU`):
   <https://docs.kernel.org/virt/kvm/x86/hypercalls.html> (HTTP 200).
5. J. Corbet, "Using the KVM API", LWN, Oct 2015: <https://lwn.net/Articles/658511/> (HTTP 200).
6. J. Corbet, "Ten years of KVM", LWN, Dec 2015: <https://lwn.net/Articles/705160/> (HTTP 200).
7. J. Corbet, "A recap of KVM Forum 2019" (exit-less/AVIC/APICv state of play):
   <https://lwn.net/Articles/805097/> (HTTP 200).
