# /sys/class/switchtec

| Field | Value |
|---|---|
| Subsystem | Microsemi Switchtec PCI Switch Management Endpoint (ABI doc header); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: the ABI doc names no Kconfig symbol and no switchtec Kconfig/Makefile is cached (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-switchtec` (header: "For details on this subsystem look at Documentation/driver-api/switchtec.rst" -- that file is not in the cached tree) |
| Since | v4.11 (entries dated 05-Jan-2017) |
| Live (5.10.134 host) | class absent: no `switchtec` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-switchtec |

## What it represents

One directory `switchtecX` (X an integer >= 0) per registered Switchtec management endpoint -- the management interface of Microsemi (now Microchip) Switchtec PCIe switches. The class exposes the switch identity card: component/product vendor, id and revision strings, device and firmware versions, and the partition topology (this device's partition number and the total partition count). The ABI states every value is read-only ("(read only)" on each entry). Actual management operations (firmware upgrade, MRPC commands) go through the char device interface referenced by the driver-api doc, not through sysfs.

## Relationship to the device model

Each class entry is backed by a PCI function implementing the Switchtec management endpoint; the identity attributes are read from hardware registers ("as stored in the hardware", per the ABI). `partition` and `partition_count` describe the switch's partition split, which maps one physical switch onto several independent PCIe domains. No bus-specific or device-management attributes are documented in the ABI file; it defines only the class directory, its naming scheme, and the ten identity attributes.

## Attributes

All documented attributes are read-only; values per the ABI "Values:" fields.

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `switchtec[0-9]+/component_vendor` | RO | arbitrary string, e.g. "MICROSEM" | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/component_id` | RO | arbitrary string, e.g. "PM8543" | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/component_revision` | RO | integer | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/product_vendor` | RO | arbitrary string, e.g. "MICROSEM" | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/product_id` | RO | arbitrary string, e.g. "PSX 48XG3" | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/product_revision` | RO | arbitrary string, e.g. "RevB" | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/device_version` | RO | integer | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/fw_version` | RO | integer in hexadecimal (currently running firmware version) | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/partition` | RO | integer, partition number of this device | always | ABI testing `sysfs-class-switchtec` |
| `switchtec[0-9]+/partition_count` | RO | integer, total partitions in the switch | always | ABI testing `sysfs-class-switchtec` |

## Safety and writes

No write path exists in the ABI file: all ten attributes are read-only hardware-identity views, so reads are safe and side-effect free. The identity pair (product/vendor/component) plus `fw_version` is the natural inventory hook for fleet tooling. Anything that changes switch state is out of scope here per the ABI; the referenced `Documentation/driver-api/switchtec.rst` (not cached) is the pointer for the management interface.

## References

- `Documentation/ABI/testing/sysfs-class-switchtec` (cached copy; eleven What: entries, contact Logan Gunthorpe)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-switchtec)
- `source-cache/sysfs-attrs.json` switchtec entry (10 paths, matching)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-switchtec
