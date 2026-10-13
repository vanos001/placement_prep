# /sys/class/drm

| Field | Value |
|---|---|
| Subsystem | DRM core; drivers/gpu/drm/drm_sysfs.c (drm_class, drm_sysfs_init) |
| Config gate | CONFIG_DRM (drm_sysfs.o is part of drm-y in drivers/gpu/drm/Makefile) |
| ABI documentation | Documentation/ABI/testing/sysfs-class-drm (1 What: entry: boot_display, January 2026, newer than the live host) |
| Since | Source-established for the class and the version file; the class version string is "drm 1.1.0 20060810" |
| Live (5.10.134 host) | 1 entry at class level only: the version file "drm 1.1.0 20060810"; no cardN devices (no DRM device in this container) |
| Ledger ID | SYSC-drm |

## What it represents

The DRM core's class. drm_sysfs_init() creates the "drm" class and attaches
one class-level read-only attribute, version, whose value is the fixed string
"drm 1.1.0 20060810" (CLASS_ATTR_STRING in drm_sysfs.c): the date of the
DRM ABI revision, not of the kernel. When a DRM driver registers a device,
its minor nodes appear here as separate class devices named card%d (primary
minor) and renderD%d (render minor), with connector subdevices named
card%d-`<connector>` (drm_sysfs.c). Those directories carry client and
connector state, populated by the DRM core and drivers, and their file set
is documented in the GPU documentation tree rather than in
Documentation/ABI. On a machine
without a DRM device (like this container) the class shows only the version
file.

## Relationship to the device model

Registered DRM devices get kdev->class = drm_class in drm_sysfs.c, and the
class devnode callback formats "dri/`<name>`" so devtmpfs creates
/dev/dri/cardN and /dev/dri/renderD`<N>`. The live host's
single version file proves the class exists because CONFIG_DRM is built in,
while the absence of card0 shows that no GPU driver bound a device: class
registration is config-gated, directory population is hardware-gated. The
same split appears in the ledger: SYSC-drm counts 1 live entry (the version
file) against 1 ABI-documented attribute that this kernel predates.

## Attributes (representative)

| Attribute | R/W | Value and unit | Source |
|---|---|---|---|
| version (class attr) | RO | fixed string "drm 1.1.0 20060810"; live-verified | drm_sysfs.c CLASS_ATTR_STRING(version, S_IRUGO); live check (5.10.134) |
| card`<N>`/... (client, connectors, props) | mixed | per-driver and per-device state | drm_sysfs.c device registration; documented in the DRM GPU docs, not ABI |
| card`<N>`/.../boot_display | RO | "1" if the display drove the boot sequence | ABI sysfs-class-drm, January 2026 (newer than live host) |

The ABI file's single entry postdates the 5.10.134 kernel; the class-level
version file and the cardN directory convention are source facts.

## Safety and writes

The version file is read-only and safe. Card directories contain writable
files (status, dpms, enabled on connectors, and more depending on driver),
but they are DRM core/driver territory with their own UAPI contracts and are
not documented in Documentation/ABI; writing them affects the live display
pipeline. Since this host exposes no cardN directories, none of that is
exercisable here. The /dev/dri/cardN and renderD nodes are the real UAPI
entry points; sysfs complements them with state, not commands.

## References

- drivers/gpu/drm/drm_sysfs.c, fetched from raw.githubusercontent.com/torvalds/linux/master
- Documentation/ABI/testing/sysfs-class-drm (cached at source-cache/linux-sparse)
- Live enumeration /sys/class/drm (version file only, read-only, kernel 5.10.134)
- Sibling pages: [graphics](./graphics.md); coverage: [ledger](../ledger.md)
