# /sys/class/iommu

| Field | Value |
|---|---|
| Subsystem | IOMMU subsystem (per-IOMMU device view; AMD and Intel driver subdirectories documented); contact Alex Williamson; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-iommu`, `sysfs-class-iommu-amd-iommu`, `sysfs-class-iommu-intel-iommu` (7 What: entries total) |
| Since | 3.17 (June 2014, all entries) |
| Live (5.10.134 host) | class directory present, 0 devices (empty; no IOMMU exposed in this container) |
| Ledger ID | SYSC-iommu |

## What it represents

One directory per IOMMU hardware unit in the system. The class exists so
that userspace can associate a given IOMMU with the devices it translates
and read the IOMMU's identity and capability registers. The generic ABI
states the pairing rule: drivers "are able to link devices managed by a
given IOMMU" under /sys/class/iommu/<iommu>/devices/, and conversely "link
the IOMMU for a given device" at /sys/devices/.../iommu. Driver-specific
files then hang below the per-IOMMU directory (amd-iommu/, intel-iommu/).

## Relationship to the device model

The class is a lookup side-table over the device model rather than a device
family: the devices/ subdirectory and the reverse device/.../iommu symlink
are the documented join. The intel-iommu address file makes the same join
against firmware tables: it shows "the Physical address of the VT-d DRHD
for this IOMMU ... This allows association of a sysfs intel-iommu with a
DMAR DRHD table entry." IOMMU groups, a separate concept with its own ABI
(sysfs-kernel-iommu_groups, cached), are not part of this class.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| <iommu>/devices/ | RO | links to devices managed by this IOMMU | if driver populates it | ABI testing sysfs-class-iommu, 3.17 |
| <iommu>/amd-iommu/cap | RO | capability header per AMD IOMMU spec, %x | AMD IOMMUs | ABI testing sysfs-class-iommu-amd-iommu, 3.17 |
| <iommu>/amd-iommu/features | RO | extended features, %llx | AMD IOMMUs | ABI testing sysfs-class-iommu-amd-iommu, 3.17 |
| <iommu>/intel-iommu/address | RO | physical address of the VT-d DRHD unit, %llx | Intel IOMMUs | ABI testing sysfs-class-iommu-intel-iommu, 3.17 |
| <iommu>/intel-iommu/cap | RO | cached hardware capability register of this DRHD unit, %llx | Intel IOMMUs | ABI testing sysfs-class-iommu-intel-iommu, 3.17 |
| <iommu>/intel-iommu/ecap | RO | cached hardware extended capability register, %llx | Intel IOMMUs | ABI testing sysfs-class-iommu-intel-iommu, 3.17 |
| <iommu>/intel-iommu/version | RO | architecture version from VT-d VER_REG, %d:%d major:minor | Intel IOMMUs | ABI testing sysfs-class-iommu-intel-iommu, 3.17 |

The mirror-side link /sys/devices/.../iommu (device to IOMMU) is documented
in the same generic ABI file.

## Safety and writes

Every documented file is read-only; the ABI records no writable attribute
for this class, so there is no write hazard here (unlike, say, the debugfs
Intel IOMMU toggles, which live elsewhere and are not sysfs). On the
5.10.134 host the class is present but empty -- the container exposes no
IOMMU -- so no capability value could be read live and none is reported.

## References

- `Documentation/ABI/testing/sysfs-class-iommu`, `sysfs-class-iommu-amd-iommu`, `sysfs-class-iommu-intel-iommu` (cached copies)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-iommu
- sysfs-attrs.json entry `iommu` (7 paths, matching the seven What: entries)
- Live enumeration: /sys/class/iommu (empty, read-only, kernel 5.10.134); coverage: [ledger](../ledger.md)
