# /sys/class/scsi_disk

| Field | Value |
|---|---|
| Subsystem | SCSI disk class; implementation file not in cached tree, and no cached source names the driver that creates it |
| Config gate | not verifiable from the cached tree: no SCSI Kconfig is cached and no cached file associates this class with a config symbol (not verified) |
| ABI documentation | none found in tree -- `rg -i scsi_disk` over Documentation/ABI/stable, testing, obsolete, removed and over the whole cached Documentation plus fetched source set returns no files; no file named `sysfs-driver-scsi-disk` or similar exists in the cached tree |
| Since | not stated by any cached source |
| Live (5.10.134 host) | class present with 0 entries: `/sys/class/scsi_disk` exists but is empty (no SCSI disk attached in the container) |
| Ledger ID | SYSC-scsi_disk |

## What it represents

A source-limited page: the cached authoritative sources document the existence of this class only by name. The live enumeration lists `scsi_disk` among the 46 classes present on the 5.10.134 host (with count 0), but neither the kernel ABI tree, nor the pre-extracted attribute index (`sysfs-attrs.json`, which has no `scsi_disk` entry), nor any fetched driver source mentions the class or its attributes. What the class represents on this host can therefore only be stated as: a SCSI-storage class directory that the kernel creates when SCSI disks are present, currently empty because the container has no attached SCSI disk. Any more specific claim (device naming, per-disk knobs) would be fabrication and is deliberately omitted.

## Relationship to the device model

Not verifiable from the cached tree: no cached documentation describes the parent devices, symlink layout, or bus relationship of scsi_disk entries. The only verifiable relationship is negative evidence of documentation, plus the live directory itself (`/sys/class/scsi_disk`, empty).

## Attributes

None citable. No cached source (ABI files, JSON attribute index, or fetched driver code) names a single attribute of this class, so the table is intentionally left empty rather than populated from memory. On the live host the empty class directory exposes no attribute rows to inspect either.

## Safety and writes

Unknown and undocumented in the cached tree: with no attribute inventory there is no basis for safety claims. Reads of the class directory itself are safe (it is an empty directory on this host). If the class gains entries on a machine with SCSI disks, treat writes to unknown attributes with normal sysfs caution (root-only writes, possible device behavior changes); that guidance is procedural, not source-based.

## References

- `source-cache/live-sys/class-list.txt`, row `scsi_disk	0` (live enumeration, kernel 5.10.134-013.15.kangaroo.al8.x86_64)
- Direct read-only inspection: `/sys/class/scsi_disk` exists and is empty
- `source-cache/sysfs-attrs.json`: no `scsi_disk` key (negative evidence)
- `Documentation/ABI/` search for `scsi_disk`: 0 matches in stable/testing/obsolete/removed (negative evidence)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-scsi_disk (status: live@5.10.134, 0 documented attributes)
