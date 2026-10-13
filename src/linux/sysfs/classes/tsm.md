# /sys/class/tsm

| Field | Value |
|---|---|
| Subsystem | TEE Security Manager core (confidential computing), `drivers/virt/coco/` (`obj-$(CONFIG_TSM) += tsm-core.o`; `config TSM` is `bool` in `drivers/virt/coco/Kconfig`, torvalds/linux master) |
| Config gate | `CONFIG_TSM` (Kconfig entry and Makefile obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-tsm` (a single What entry for the class directory itself; no Date or KernelVersion line) |
| Since | not stated in the cached source |
| Live (5.10.134 host) | class absent: no `/sys/class/tsm` directory |
| Ledger ID | SYSC-tsm |

## What it represents

One device, `tsmN`, per platform TEE Security Manager -- the confidential
computing (CoCo) component that a VM trusts for device security state. The
entire cached ABI text is the class-directory entry: "tsmN is a device that
represents the generic attributes of a platform TEE Security Manager. It is
typically a child of a platform enumerated TSM device." Its stated purpose
is signaling: `/sys/class/tsm/tsmN/uevent` fires when the PCI layer becomes
able to support link encryption and other device-security features
coordinated through the platform TSM. No per-device attributes are
documented in the class ABI at all. The report-request machinery lives
elsewhere: `Documentation/ABI/testing/configfs-tsm-report` documents a
configfs interface (`configfs-tsm-report`), which is a different filesystem
and outside this class.

## Relationship to the device model

`tsmN` is "typically a child of a platform enumerated TSM device" -- an
explicit parent/child statement, unusual for a class ABI. The class sits at
the junction of the VM guest kernel and PCI device-security plumbing; the
uevent is the notification channel toward userspace (e.g. device assignment
agents waiting for the PCI layer to be ready). No bus, no char node, and no
documented sysfs attributes: this is a pure class-existence + uevent
surface in the cached tree. Related TEE-side machinery: sibling page
[tee](./tee.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `tsmN/uevent` | RO (write to trigger from kernel side) | uevent signaling PCI-layer readiness for link encryption / device-security features | always per ABI text | ABI testing `sysfs-class-tsm` |

That is the complete documented set -- one directory entry, zero
per-attribute rows. The ledger records 1 documented path, matching.

## Safety and writes

Nothing beyond the uevent mechanism is documented, so there is no
attribute-level safety story to cite. The uevent itself is the documented
integration point: userspace reacting to it changes device-security
decisions (link encryption readiness), so consumers should treat
"uevent seen" as "PCI layer reports capability", not as a guarantee about
any specific device. No capability requirements are stated.

## References

- `Documentation/ABI/testing/sysfs-class-tsm` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-tsm)
- `Documentation/ABI/testing/configfs-tsm-report` (cached; related configfs interface, not this class)
- `drivers/virt/coco/Makefile`, `drivers/virt/coco/Kconfig` (torvalds/linux master; fetched)
- Ledger row SYSC-tsm (1 path); `/sys/class/tsm` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [tee](./tee.md)
