# /sys/class/bsr

| Field | Value |
|---|---|
| Subsystem | IBM POWER Barrier Synchronization Register support (Kconfig title, `drivers/char/Kconfig` line 113 of the fetched copy); implementation file not in cached tree |
| Config gate | `CONFIG_IBM_BSR` -- verified from the fetched `char-Kconfig`: tristate "IBM POWER Barrier Synchronization Register support", depends on PPC_PSERIES |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-bsr` |
| Since | 2.6.27 (entries dated Jul 2008) |
| Live (5.10.134 host) | class absent: no `bsr` row in the cached live enumeration of 46 classes (x86_64 host; the driver is POWER-only) |
| Ledger ID | SYSC-bsr |

## What it represents

The sysfs view of IBM POWER Barrier Synchronization Registers: a hardware mechanism for fast synchronization of threads across a large system that, per the Kconfig help text, "avoids bouncing a cacheline between several cores on a system". Each `bsr*` directory in the class describes one BSR device and exposes the geometry a userspace program needs before mapping it: the register size, the mappable memory-region length, and the stride at which the allocated BSR bytes repeat within the mapping. The class exists only on IBM POWER systems (pSeries); the actual synchronization object is reached by mapping the device, not by writing sysfs.

## Relationship to the device model

The class directories are attachments over platform/OF-discovered devices on pSeries machines; the ABI documents only the three geometry attributes and no device-management path. On non-POWER systems -- including the x86_64 container host -- neither the driver nor the class is built. The char-device side (mapping the registers) lives outside sysfs; the class is the discovery layer.

## Attributes

All documented attributes are read-only, per the "(RO)" markers in the ABI file.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `bsr*/bsr_size` | RO | size of the barrier-synchronization register, in bytes | always | ABI testing `sysfs-class-bsr` |
| `bsr*/bsr_length` | RO | length of memory region that can be mapped, in bytes | always | ABI testing `sysfs-class-bsr` |
| `bsr*/bsr_stride` | RO | stride, i.e. interval at which the allocated BSR bytes repeat within the mapping | always | ABI testing `sysfs-class-bsr` |

## Safety and writes

No sysfs writes are documented; all three attributes are read-only. Reads are safe. The synchronization registers themselves are memory-mapped, so the hazard story (concurrent clobbering of shared registers by other partitions or threads) belongs to the mapping interface, not this class. On this x86_64 host the class is absent, consistent with the PPC_PSERIES dependency.

## References

- `Documentation/ABI/testing/sysfs-class-bsr` (cached copy; three What: entries, contacts Arnd Bergmann / Greg Kroah-Hartman)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-bsr)
- Fetched `char-Kconfig` (drivers/char/Kconfig), `config IBM_BSR` block
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-bsr
