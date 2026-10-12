# /sys/class/ocxl

| Field | Value |
|---|---|
| Subsystem | OCXL AFU (accelerator function unit) class, OpenCAPI; contact linuxppc-dev@lists.ozlabs.org; implementation file not in cached tree |
| Config gate | not verifiable from cached tree (no drivers/Kconfig cached) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-ocxl` (6 What: entries) |
| Since | not stated in the ABI file (Date January 2018; reload_on_reset Date February 2020) |
| Live (5.10.134 host) | class absent: /sys/class/ocxl does not exist in this container |
| Ledger ID | SYSC-ocxl |

## What it represents

One directory per OpenCAPI AFU, named by AFU name. The attributes expose
the AFU's own configuration space (afu_version, mmio area sizes), the
context usage counter, and a control for FPGA image reload on link reset.
This is the userspace-visible surface of OpenCAPI accelerators on Power
platforms, a successor interface to the older CAPI [cxl](./cxl.md) class
(which lived in the same /sys/class namespace under a different name and
was removed in 6.15).

## Relationship to the device model

The ABI consistently reads sizes and versions "as defined in the
configuration space of the AFU" / "in the configuration space of the AFU",
i.e. the class files are views over the AFU device's config space.
global_mmio_area gives read/write access to "the global mmio area for the
AFU". No bus, parent, or symlink structure is described in the cached file;
no further device-model claims are made here.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| afu_version | RO | version of the AFU, `<major>:<minor>`, read from AFU config space | always | ABI testing sysfs-class-ocxl, Jan 2018 |
| contexts | RO | `<n>/<max>`: active contexts (for debug) over maximum contexts supported | always | ABI, Jan 2018 |
| pp_mmio_size | RO | size of the per-process MMIO area, from config space | always | ABI, Jan 2018 |
| global_mmio_size | RO | size of the global MMIO area, from config space | always | ABI, Jan 2018 |
| global_mmio_area | RW | access to the global MMIO area of the AFU | always | ABI, Jan 2018 |
| reload_on_reset | RW | 0 do not reload FPGA image from flash, 1 reload, "unavailable" if unsupported; needs a vendor-specific logic block on the FPGA | if device supports it | ABI, Feb 2020 |

## Safety and writes

Reads are safe. The two writable files touch hardware state:
global_mmio_area exposes the AFU's global MMIO to whomever can write sysfs,
and reload_on_reset decides whether a link reset reflashes the FPGA image --
a persistent firmware-affecting action. The class is absent on the 5.10.134
host (x86 container, no OpenCAPI), so no live read was possible and no
permission bits or value examples are reported.

## References

- `Documentation/ABI/testing/sysfs-class-ocxl` (cached copy)
- https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-class-ocxl
- sysfs-attrs.json entry `ocxl`; live enumeration: class absent, kernel 5.10.134
- Related page: [cxl](./cxl.md) (removed CAPI class); coverage: [ledger](../ledger.md)
