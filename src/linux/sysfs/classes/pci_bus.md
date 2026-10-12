# /sys/class/pci_bus

| Field | Value |
|---|---|
| Subsystem | PCI core (per-bus objects of the PCI subsystem); implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); the empty class directory exists on the live host, so PCI core support is enabled there |
| ABI documentation | none for the class itself; one What entry in `Documentation/ABI/testing/sysfs-bus-pci` spells a pci_bus subtree: `/sys/bus/pci/devices/.../pci_bus/.../rescan` (May 2011) |
| Since | not stated for the class; the single ABI reference is dated May 2011 |
| Live (5.10.134 host) | class present and empty: live-sys/class-list.txt records `pci_bus 0`; /sys/class/pci_bus verified empty live (this VM has no PCI host bridge, its virtio devices sit on virtio-mmio) |
| Ledger ID | SYSC-pci_bus |

## What it represents

The class of PCI bus objects: one directory per PCI bus number (for example `0000:00`) for buses the PCI core has enumerated. A PCI bus directory aggregates the bus-level view - as opposed to `/sys/bus/pci/devices/...`, which lists individual functions. On hosts with PCI hardware this is where the per-bus files live; on this virtio-mmio-only container the class exists but no bus was ever registered, so it is empty.

## Relationship to the device model

PCI buses are `struct device`-backed objects in the PCI device hierarchy (each bus is the parent container of its slot devices and child buses). The single cached ABI reference ties the class into the device tree from the other side: a What entry documents `rescan` under the spelling `/sys/bus/pci/devices/.../pci_bus/.../rescan` - writing a non-zero value forces a rescan of that bus and all child buses and re-discovers devices removed earlier from that part of the tree. `Documentation/PCI/` and any per-bus attribute documentation (for example cpuaffinity-style files) are not in the cached tree, so nothing else about the directory layout can be cited here.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<bus>/rescan` (as spelled `/sys/bus/pci/devices/.../pci_bus/.../rescan`) | WO | write non-zero to rescan this bus and all child buses | PCI bus present | ABI `sysfs-bus-pci`, May 2011 |

That is the only attribute reachable from the cached sources. Commonly seen per-bus files on real hosts (CPU affinity of the bus, legacy I/O and memory windows) are NOT documented in the cached tree and are not verified on this host (the class is empty), so they are deliberately omitted.

## Safety and writes

`rescan` triggers hardware enumeration: a bus rescan can discover or re-probe devices, re-run configuration cycles and change the device tree underneath mounted drivers - it is a recovery/hot-plug action, root-only in effect. On the live host there is nothing to write (empty class). Reads of the class directory itself are safe. No other safety statement can be sourced from the cached tree.

## References

- `Documentation/ABI/testing/sysfs-bus-pci` (cached copy; the `/sys/bus/pci/devices/.../pci_bus/.../rescan` What entry, May 2011)
- Live enumeration: /sys/class/pci_bus empty (kernel 5.10.134); live-sys/class-list.txt row `pci_bus 0`
- Implementation: not in cached tree; `Documentation/PCI/` absent from the cached tree
- Sibling coverage: [ledger](../ledger.md), sysfs [overview](../overview.md)
