# MSI, MSI-X, and Message-Based Interrupt Delivery

PCIe devices do not raise interrupts; they **write to memory**. A message
signaled interrupt is an ordinary posted Memory Write TLP whose address names
a CPU (or an interrupt controller), whose data names a vector, and whose
arrival is interpreted by the root complex / APIC as "raise vector V at CPU
D". Everything on this page -- capability structures, per-vector masking,
affinity rewrites, interrupt remapping -- is bookkeeping around that one
sentence.

Scope: [PCI](./pci.md) covers enumeration and the `pci_alloc_irq_vectors`
driver API; [interrupt handling](./interrupt-handling.md) covers the
`irq_desc`/`irqaction` core; here we follow the *message* itself: its wire
format, how Linux composes it, and how the IOMMU rewrites it.

---

## 1. Why pins had to go

INTx (the four virtual wires INTA#-INTD#) has three structural problems:

1. **Sharing.** Multiple functions wire-OR onto one line, so every interrupt
   costs a driver-registry walk over all handlers on the line, and the OS
   cannot tell which device fired until each has been polled.
2. **Ordering with DMA.** An INTx assertion is not a bus transaction; it has
   no ordering relationship with the device's posted DMA writes. A device that
   raises INTx right after enqueueing DMA can have the CPU service the
   interrupt *before* the descriptors are visible in memory -- the classic
   "interrupt-before-data" race that forced read-flush workarounds.
3. **No per-source control.** Level and target are fixed in hardware; masking
   is all-or-nothing per line, and there is nothing to retarget for affinity.

MSI fixes all three by making the interrupt itself a posted write: it is
ordered after the device's own DMA writes (same posted-write stream), it
carries the vector in-band, and the destination CPU is just bits in the
address -- rewritable per vector at any time.

## 2. The message: address and data formats

On x86 the Local APIC defines the encoding (Intel SDM Vol 3, ch. 10.11):

| Field | Bits | Meaning |
|---|---|---|
| Address[31:20] | fixed | `0xFEE` (Local APIC base) |
| Address[19:12] | Destination ID | APIC ID of target CPU (physical mode) |
| Address[3] | RH | Redirection Hint (1 = aim at lowest-priority among focus) |
| Address[2] | DM | Destination Mode (0 = physical, 1 = logical) |
| Data[7:0] | Vector | the IDT vector to raise |
| Data[10:8] | Delivery Mode | 000 = Fixed, 001 = Lowest-Priority, ... |
| Data[15:14] | Level/Trigger | level for level-triggered delivery |

So "interrupt CPU 1 with vector 65" is a 32-bit write of `0x0041` to
`0xFEE01008` (the demo below composes these). The chipset routes the write to
the APIC, which sets IRR bit 65 on that CPU -- from there it is ordinary
interrupt delivery ([interrupt handling](./interrupt-handling.md)). ARM
(GIC ITS) and RISC-V (IMSIC) use different encodings (DT/IRT tables, msi
address regions) but the same abstraction, which is exactly why Linux wraps
composition in irq domains (Sec. 4).

## 3. Capability structures: MSI vs MSI-X

```text
  MSI capability (PCI cap ID 05h)          MSI-X capability (ID 11h)
  -------------------------------          --------------------------------
  hdr + next | cap ID=05h                  hdr + next | cap ID=11h
  Message Control (16b)                    Message Control (16b)
    bit0    MSI Enable                       bits10:0  Table Size = N-1
    bits3:1  Multiple Message Capable        bit14     Function Mask
    bits6:4  Multiple Message Enable         bit15     MSI-X Enable
    bit7     64-bit Address Capable        Table Offset/BIR (32b)
    bit8     Per-Vector Masking Capable      bits31:3 offset, bits2:0 BAR
    bit9     Extended Capable              PBA Offset/BIR (32b)
  Message Lower Address (32b)                same bit split
  Message Upper Address (32b, if 64-bit)
  Message Data (16b)                       MSI-X Table (in MMIO, N*16B):
  [Mask Bits (32b), if PVMC]                 +0  Message Address (32b)
  [Pending Bits (32b), if PVMC]              +4  Message Upper Address
                                             +8  Message Data (32b)
                                             +12 Vector Control (bit0 = mask)
```

The consequential differences:

| Property | MSI | MSI-X |
|---|---|---|
| Vectors per function | 1, 2, 4, ..., 32 (power of two) | up to 2048 |
| Address/data | one address; data = base vector | **independent per entry** |
| Per-vector masking | optional Mask/Pending dwords | always (Vector Control bit0 + PBA) |
| Table location | config space | MMIO (any BAR), co-located with PBA elsewhere |
| Affinity granularity | shared destination | per-entry destination |

The MSI-X **Pending Bit Array** mirrors the mask bits: if a vector is masked
and the device has an event, the device sets its PBA bit instead of writing;
on unmask the driver reads PBA to know whether to poll or expect the write.
This is how NVMe masks a queue's interrupt during busy poll without losing
completions ([NVMe](./nvme.md)).

## 4. Linux: irq domains and `compose_msi_msg`

Allocating an MSI-X vector walks a **hierarchical irq domain** stack. Each
level owns one decision, and `irq_data` chains parent pointers down:

```text
  driver: pci_alloc_irq_vectors(dev, 9, 9, PCI_IRQ_MSIX)
     |
     v
  MSI-X domain (.compose_msi_msg)     picks a Linux irq number, fills
     |                                msi_desc, allocates table entry
     v
  IR (remapping) domain, if on        allocates an IRTE index; compose writes
     |                                a *remappable* address (index, SHV)
     v
  x86 vector domain                   picks a CPU vector (vector routing),
     |                                programs the APIC
     v
  CPU                                 IRR bit set on message arrival
```

The composition callback writes the `msi_msg` (address + data). Affinity is
then just re-composition: `irq_set_affinity` -> domain callback recomputes
Destination ID (and, with remapping, rewrites the IRTE) -- the device never
learns anything changed, since the table entry or IRTE is updated on its
behalf. `/proc/interrupts` shows the result per vector, with `PCI-MSI` /
`PCI-MSI-X` labels; [interrupt
handling](./interrupt-handling.md) covers what runs once the vector fires.

## 5. Interrupt remapping: the IOMMU's other job

With VT-d (Intel) or AMD-Vi (AMD) remapping enabled, message writes are no
longer interpreted by the APIC directly: the IOMMU intercepts them and looks
up an **IRTE** (interrupt remapping table entry, one per allocated interrupt)
that *replaces* the message's destination and vector:

| IRTE (remapped format, abridged) | Field |
|---|---|
| Destination ID | real target CPU |
| Vector | real vector |
| IM | mode: 0 = remapped, 1 = posted |
| Posted format | PDA = address of Posted-Interrupt Descriptor (PIR + ON + NV) instead of dest+vector |

Three wins justify the indirection: (1) **safety** -- a device can only raise
interrupts an IRTE was allocated for, killing vector-spoofing DMA attacks
([IOMMU](./iommu.md)); (2) **retargetability** -- affinity changes touch the
IRTE, never the device, and the device's message format need not even encode
a CPU; (3) **posted interrupts** -- `IM=1` entries deliver guest interrupts
into a running vCPU without a VM exit, the mechanism described in
[VM exits](../../../os/advanced/vm-exits.md). Devices behind legacy (non-remappable)
MSI are what the "x2apic without IR" boot warnings complain about.

## 6. Why MSI-X wins for NVMe (and NICs)

An NVMe controller wants one interrupt per I/O queue pair plus one for the
admin queue -- 9 sources on an 8-CPU host. The three schemes allocate that
very differently, and the demo below computes the table: INTx gives one
shared line (8 sources muxed, order lost), MSI rounds the request up to the
next power of two and gives all messages *one* address -- hence one
destination CPU -- while MSI-X grants exactly 9 entries with independent
addresses, so each queue's completions are steered to the core that owns the
queue. For NICs the same argument separates RX/TX vectors and feeds RSS +
`irqbalance`/`smp_affinity` tuning ([fast
IO](../../../os/advanced/fast-io.md) touches the latency side).

```python
# MSI message composer + vector-plan model for an NVMe controller.
# Address/data per Intel SDM Table 10-2/10-3 (FEE0_0000h base, dest in addr[19:12],
# RH=bit3, DM=bit2; data = vector, fixed/edge). Deterministic integer math.

def compose(dest_apicid, vector, rh=1):
    """Physical, edge-triggered, fixed delivery. Returns (address, data)."""
    addr = 0xFEE00000 | (dest_apicid & 0xFF) << 12 | rh << 3 | 0 << 2
    data = vector & 0xFF          # delivery mode 000 (fixed), trigger 0 (edge)
    return addr, data

print("== composed MSI messages (Intel format, physical/edge/fixed) ==")
for dest, vec in [(0, 64), (1, 65), (7, 72), (255, 255)]:
    a, d = compose(dest, vec)
    print(f"  dest={dest:>3} vector={vec:>3} -> address=0x{a:08X} data=0x{d:04X}")

# ---- vector plan: NVMe SSD, 8 I/O queue pairs + 1 admin, 8-CPU host ------
IO, ADMIN, CPUS = 8, 1, 8
def pow2_ceil(n):
    p = 1
    while p < n:
        p *= 2
    return p

msi_granted = pow2_ceil(IO + ADMIN)
plans = [
    ("INTx",  1,  False, CPUS * 0 + 1),           # one shared line, one dest
    ("MSI",   msi_granted, False, 1),             # one address -> one dest
    ("MSI-X", IO + ADMIN, True,   IO + ADMIN),    # per-entry addr -> per-queue dest
]
print(f"\n== interrupt plan, NVMe ctrl: {IO} I/O queues + {ADMIN} admin, {CPUS} CPUs ==")
print("  scheme  vectors  per-vec masking  CPUs reachable  spare vectors")
for name, n, mask, reach in plans:
    print(f"  {name:<6} {n:>7}   {str(mask):<15} {reach:>14}   {n - IO - ADMIN:>12}")

print("\n  MSI-X affinity map (nvme-style):")
print("    admin  -> CPU0")
for q in range(IO):
    print(f"    ioq{q}   -> CPU{(1 + q) % CPUS}")

# ---- MSI-X vector-control / PBA bit math ---------------------------------
print("\n== MSI-X table vector-control + PBA indexing ==")
for vec in [0, 3, 32, 35]:
    dword, bit = vec // 32, vec % 32
    print(f"  vector {vec:>2}: PBA dword[{dword}] bit {bit};"
          f" table entry @0x{vec * 16:03X}, vector_control bit0=mask")

# sanity: masking bit round-trip
ctl = 0
ctl |= 1          # mask vector
ctl &= ~1         # unmask
assert ctl == 0 and (compose(1, 65)[0] >> 12) & 0xFF == 1
print("  mask/unmask bit round-trip OK; dest bits round-trip OK")
```

Real output:

```text
== composed MSI messages (Intel format, physical/edge/fixed) ==
  dest=  0 vector= 64 -> address=0xFEE00008 data=0x0040
  dest=  1 vector= 65 -> address=0xFEE01008 data=0x0041
  dest=  7 vector= 72 -> address=0xFEE07008 data=0x0048
  dest=255 vector=255 -> address=0xFEEFF008 data=0x00FF

== interrupt plan, NVMe ctrl: 8 I/O queues + 1 admin, 8 CPUs ==
  scheme  vectors  per-vec masking  CPUs reachable  spare vectors
  INTx         1   False                        1             -8
  MSI         16   False                        1              7
  MSI-X        9   True                         9              0

  MSI-X affinity map (nvme-style):
    admin  -> CPU0
    ioq0   -> CPU1
    ioq1   -> CPU2
    ioq2   -> CPU3
    ioq3   -> CPU4
    ioq4   -> CPU5
    ioq5   -> CPU6
    ioq6   -> CPU7
    ioq7   -> CPU0

== MSI-X table vector-control + PBA indexing ==
  vector  0: PBA dword[0] bit 0; table entry @0x000, vector_control bit0=mask
  vector  3: PBA dword[0] bit 3; table entry @0x030, vector_control bit0=mask
  vector 32: PBA dword[1] bit 0; table entry @0x200, vector_control bit0=mask
  vector 35: PBA dword[1] bit 3; table entry @0x230, vector_control bit0=mask
  mask/unmask bit round-trip OK; dest bits round-trip OK
```

Note the middle row: MSI "grants" 16 vectors for 9 requested (power-of-two
rule), yet all 16 share one destination -- more vectors, no extra parallelism.
The negative spare count for INTx is the queue-count deficit that made NVMe
spec MSI-X as a hard requirement.

## Interview questions

1. **"A device's interrupt arrives before its DMA data -- how is that possible,
   and how does MSI fix it?"** With INTx there is no ordering between the
   (non-transactional) interrupt and posted DMA writes. MSI is itself a posted
   write issued *after* the device's data writes in the same stream, so the
   root complex delivers data first, interrupt second.
2. **"Why can't MSI give vector 5 of 8 to a different CPU than vector 6?"**
   MSI multi-message grants one base address + consecutive data values; the
   destination lives in the single shared address. MSI-X entries each carry
   their own address, so per-vector destinations are free.
3. **"What breaks first if you boot with `iommu=off` and pass a VF to a
   guest?"** Without interrupt remapping, the guest controls raw MSI
   address/data and can target host vectors outside its assignment -- the
   vector-spoofing window that IRTEs close (and why VFIO requires
   `intel_iommu=on` for device assignment).
4. **"You masked an MSI-X vector and completions stopped forever. What did you
   forget?"** Reading/handling the Pending Bit Array: while masked, the device
   sets its PBA bit instead of writing the message; unmasking without
   checking PBA can leave you waiting for an interrupt that will never be
   re-sent.

## References

1. The MSI Driver Guide HOWTO (kernel docs; allocation API, fallback order):
   <https://docs.kernel.org/PCI/msi-howto.html> (HTTP 200).
2. Linux generic IRQ handling (irq domain hierarchy, chained irq_data):
   <https://docs.kernel.org/core-api/genericirq.html> (HTTP 200).
3. PCI-SIG specifications page (PCI Local Bus spec ch. on MSI capability;
   PCIe Base spec on MSI-X table/PBA):
   <https://pcisig.com/specifications> (HTTP 200).
4. M. Zyngier, "Per-device MSI domain & platform MSI" (LWN kernel page on the
   per-device MSI domain rework):
   <https://lwn.net/Articles/651071/> (HTTP 200).
5. M. Zyngier, "Per-device MSI domain & platform MSI" series (v2):
   <https://lwn.net/Articles/652669/> (HTTP 200).
6. Intel VT-d Architecture Specification (IRTE formats, remappable MSI
   address, posted interrupts):
   <https://www.intel.com/content/www/us/en/content-details/774206/intel-virtualization-technology-for-directed-i-o-architecture-specification.html> (HTTP 403 to automated fetchers -- bot-walled; canonical spec page).
