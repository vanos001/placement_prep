# /sys/class/tpmrm

| Field | Value |
|---|---|
| Subsystem | TPM subsystem (TPM 2.0 character-device flavor), `drivers/char/tpm/` (`tpm-y += tpmrm-dev.o` inside the CONFIG_TCG_TPM object, torvalds/linux master) |
| Config gate | `CONFIG_TCG_TPM` (built within the tpm object; no separate Kconfig symbol found on master) |
| ABI documentation | none found in tree: no What entry mentions `tpmrm` in any `Documentation/ABI/` file (the stable `sysfs-class-tpm` documents only `/sys/class/tpm`) |
| Since | no kernel version stated in any cached source |
| Live (5.10.134 host) | class directory present, 0 devices (dir exists per live-sys enumeration; no chip registered) |
| Ledger ID | SYSC-tpmrm |

## What it represents

A second TPM class directory that appears next to `/sys/class/tpm` on
kernels with TPM 2.0 space-manager support. What the cached sources
establish, no more and no less: (a) the class exists as a distinct sysfs
class (`SYSC-tpmrm` ledger row, class dir enumerated live on the 5.10.134
host); (b) its implementation object is `tpmrm-dev.o`, built as part of the
TPM subsystem (`tpm-y += tpmrm-dev.o` in `drivers/char/tpm/Makefile`,
torvalds/linux master); (c) the attribute cache (`sysfs-attrs.json`) has no
tpmrm entry and the ABI tree has no tpmrm entry, so no per-attribute
documentation exists to cite. The widely known distinction -- tpmrm being
the TPM 2.0 device with auto client-managed locality -- is *not* asserted
in the attribute table below because no cached source states it; this page
deliberately stays at the evidence line.

## Relationship to the device model

The class directory exists in parallel with `/sys/class/tpm` (live host
shows both, each with 0 devices). By analogy with the parent subsystem, a
`tpmrm<N>` instance would be a class view over the same physical chip
device under `/sys/devices/...`, with a character-device counterpart
created by the same driver that builds `tpmrm-dev.o` -- but the cached
Documentation does not describe the device-model linkage, so this page
records the class dir and object name only.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| (none documented) | -- | no attribute of `/sys/class/tpmrm/...` is documented in the cached ABI tree or attribute cache | -- | negative result: grep over `Documentation/ABI/`, `sysfs-attrs.json` |

Generic class-device files (`uevent`, device links, power group) would
follow the standard device-model pattern but carry no tpmrm-specific
documentation in the cached sources.

## Safety and writes

Nothing is documented, so no write safety story can be cited. Reads of the
class directory itself (e.g. an empty enumeration) are trivially safe. Any
statement about ioctl surfaces, locality behavior, or capability gates for
tpmrm devices would require the driver sources (`drivers/char/tpm/`), which
the sparse cache does not contain.

## References

- `Documentation/ABI/stable/sysfs-class-tpm` (cached; checked for tpmrm mentions -- none)
- `drivers/char/tpm/Makefile` (torvalds/linux master; fetched `tpm-y += tpmrm-dev.o`)
- `source-cache/sysfs-attrs.json` (no tpmrm key -- negative evidence)
- Ledger row SYSC-tpmrm (live-only, 0 documented attrs); `/sys/class/tpmrm` present with 0 devices per `source-cache/live-sys/class-list.txt`
- Sibling pages: [tpm](./tpm.md)
