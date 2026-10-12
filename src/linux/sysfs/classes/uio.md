# /sys/class/uio

| Field | Value |
|---|---|
| Subsystem | Userspace I/O core, `drivers/uio/` (`obj-$(CONFIG_UIO) += uio.o`, torvalds/linux master) |
| Config gate | `CONFIG_UIO` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | none found in tree: no `sysfs-class-uio` file exists under `Documentation/ABI/`; attributes are documented in `Documentation/driver-api/uio-howto.rst` (torvalds/linux master); one driver-specific ABI file exists (`Documentation/ABI/testing/sysfs-driver-uio_pci_sva-pasid`, a bus-path attribute) |
| Since | not stated in any cached source (the howto only says the `portio/` directory "was added", without a version) |
| Live (5.10.134 host) | class directory present, 0 devices (no UIO device registered in the container) |
| Ledger ID | SYSC-uio |

## What it represents

One directory per userspace-I/O device, `uioX`. UIO is the framework for
minimal kernel drivers that map hardware registers into userspace and
signal interrupts there, leaving all device logic to a userspace process.
Sysfs is the discovery plane: `name` identifies the device (the howto
recommends the kernel module name), `version` is the driver-defined version
string so the userspace half can adapt, and `event` counts interrupts
handled since the device node was last read -- the handshake that pairs
with `read(2)`/`poll(2)` on `/dev/uioX`. Mapping geometry is exported
below `maps/` (and ioport regions below `portio/`), which is what a
userspace driver needs before calling `mmap()`.

## Relationship to the device model

`/sys/class/uio/uioX` is a class view over the underlying device
(PCI, platform, ...). The howto warns that "this directory might be a
symlink, and not a real directory. Any userspace code that accesses it must
be able to handle this." Memory mappings are addressed through the
`/dev/uioX` node: mapping N uses offset N * page size, with the sysfs
`maps/mapN/offset` value added for non-page-aligned device memory. No char
major allocation story is documented in the cached sources. Sibling page:
[mem](./mem.md) (the raw `/dev/mem` route to the same kind of access, minus
the interrupt handshake).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `uioX/name` | RO | device name string (recommended: kernel module name) | always | `Documentation/driver-api/uio-howto.rst` (master) |
| `uioX/version` | RO | driver-defined version string | always | uio-howto (master) |
| `uioX/event` | RO | total interrupts handled since the device node was last read | always | uio-howto (master) |
| `uioX/maps/mapN/name` | RO | string identifier for the mapping; may be empty | per mapping, only if size != 0 | uio-howto (master) |
| `uioX/maps/mapN/addr` | RO | address of mappable memory | per mapping | uio-howto (master) |
| `uioX/maps/mapN/size` | RO | size in bytes of the memory at addr | per mapping | uio-howto (master) |
| `uioX/maps/mapN/offset` | RO | bytes to add to the mmap pointer for non-page-aligned memory | per mapping | uio-howto (master) |
| `uioX/portio/portN/{name,start,size,porttype}` | RO | ioport region: first port, port count, port type string | only if driver registers port regions | uio-howto (master) |

## Safety and writes

No attribute here is documented as writable; UIO writes happen through
`/dev/uioX` and, above all, through `mmap()`ed device memory -- which is
unmediated hardware access, the whole point of the framework. Reading sysfs
is safe. The host header check matters for citations:
`/usr/include/linux/uio.h` exists but is the unrelated Berkeley-style
`iovec` scatter/gather header -- the UIO subsystem has no uapi header, so
no ioctl surface exists at all. A modern driver-specific extension
(`uio_pci_sva` PASID attribute, Sept 2025) shows userspace reading sysfs to
program IOMMU state after opening the device.

## References

- `Documentation/driver-api/uio-howto.rst` (torvalds/linux master; fetched copy consulted; online: https://docs.kernel.org/driver-api/uio-howto.html)
- `Documentation/ABI/testing/sysfs-driver-uio_pci_sva-pasid` (cached copy)
- `drivers/uio/Makefile` (torvalds/linux master; fetched obj line)
- `/usr/include/linux/uio.h` (host header; verified to be the iovec header, not a UIO uapi)
- Ledger row SYSC-uio; `/sys/class/uio` present with 0 devices per `source-cache/live-sys/class-list.txt` and live listing
