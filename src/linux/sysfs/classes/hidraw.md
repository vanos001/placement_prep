# /sys/class/hidraw

| Field | Value |
|---|---|
| Subsystem | HID support, `drivers/hid/` (`hid-$(CONFIG_HIDRAW) += hidraw.o` in `drivers/hid/Makefile`, torvalds/linux master) |
| Config gate | `CONFIG_HIDRAW` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-driver-hid` (two class-path entries: `report_descriptor`, `country`); no dedicated `sysfs-class-hidraw` file exists in the tree |
| Since | KernelVersion printed as "2.0.39" for `report_descriptor` (as written in the ABI file; entry dated Jan 2011), 3.19 for `country` |
| Live (5.10.134 host) | class absent: no `/sys/class/hidraw` directory, no HID device registered |
| Ledger ID | SYSC-hidraw |

## What it represents

One directory per raw HID device node, `hidraw<num>` (up to
`HIDRAW_MAX_DEVICES` = 64 per the host header `/usr/include/linux/hidraw.h`).
Hidraw is primarily a character-device API (`/dev/hidrawN`, created by udev
per `Documentation/hid/hidraw.rst`): applications read and write HID reports
unparsed, using the `HIDIOCGRAWNAME`, `HIDIOCGRAWINFO`, `HIDIOCSFEATURE` /
`HIDIOCGFEATURE` and related ioctls defined in that header. The sysfs class
is the discovery side: it identifies the device and exports the raw HID
report descriptor so a userspace driver can interpret the report stream.

## Relationship to the device model

`/sys/class/hidraw/hidraw<num>` is a class view over the HID device under
`/sys/devices/...`; the `device/` subdirectory seen in the documented
attribute paths (`hidraw<num>/device/report_descriptor`) is that parent
link. `Documentation/hid/hidraw.rst` states hidraw uses a dynamic major
number and that udev creates the `/dev` nodes, so applications should locate
devices through libudev rather than fixed names. The same ABI file documents
identical `report_descriptor`/`country` attributes on USB bus paths and
bluetooth `hci<addr>` paths -- the hidraw class entries are the bus-agnostic
form. Sibling page: [bluetooth](./bluetooth.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `hidraw<num>/device/report_descriptor` | RO | raw binary HID report descriptor; cannot be written | always | ABI testing `sysfs-driver-hid` |
| `hidraw<num>/device/country` | RO | ASCII hex integer of the HID country code (e.g. 21 for US); cannot be written | always | ABI testing `sysfs-driver-hid` (3.19) |
| `hidraw<num>/dev` | RO | `<major>:<minor>` of the hidraw character device | always | ABI stable `sysfs-devices` (`/sys/devices/*/dev`, Jun 2006) |

Both ABI entries list `Users: HIDAPI library`, evidence of their real-world
consumer.

## Safety and writes

Both documented attributes are read-only and reading them is safe
(`report_descriptor` is binary). Writes are not part of the documented ABI.
Device access is controlled through the `/dev/hidrawN` node, not sysfs; the
header shows the ioctls, including the newer `HIDIOCREVOKE` ("Revoke device
access"), which is the revocation path for descriptors already handed out.
No sysfs-level capability requirements are stated in the cached sources.

## References

- `Documentation/ABI/testing/sysfs-driver-hid` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-driver-hid)
- `Documentation/ABI/stable/sysfs-devices` (cached; `dev` attribute)
- `Documentation/hid/hidraw.rst` (not in sparse cache; online: https://docs.kernel.org/hid/hidraw.html)
- `/usr/include/linux/hidraw.h` (host header: ioctls, `HIDRAW_MAX_DEVICES`)
- Ledger row SYSC-hidraw; `source-cache/sysfs-attrs.json` lists exactly the two driver attributes
