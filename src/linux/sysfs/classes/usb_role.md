# /sys/class/usb_role

| Field | Value |
|---|---|
| Subsystem | USB role switch class, `drivers/usb/roles/` (`obj-$(CONFIG_USB_ROLE_SWITCH) += roles.o`, torvalds/linux master) |
| Config gate | `CONFIG_USB_ROLE_SWITCH` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-usb_role` (3 What entries) |
| Since | Jan 2018 (class dir, `role`); Feb 2024 (`connector`) |
| Live (5.10.134 host) | class absent: no `/sys/class/usb_role` directory, no role switch registered |
| Ledger ID | SYSC-usb_role |

## What it represents

One directory per USB role switch -- a device that can select the data role
(host or device) for a USB port. The ABI defines the class as the "place in
sysfs for USB Role Switches". This is the non-Type-C side of USB dual-role
handling: the `role` attribute description explicitly says that with USB
Type-C ports "the ABI defined for USB Type-C connector class must be used",
reserving `usb_role` for plain dual-role ports (many SoC USB controllers)
where no connector class device exists. For those, `role` is the single
knob: reading shows `none`, `host`, or `device`; writing requests a swap.
The `connector` attribute (Feb 2024) optionally links the switch to its
Type-C connector when both abstractions describe the same physical
receptacle.

## Relationship to the device model

`/sys/class/usb_role/<switch>` is a class view over a role-switch device
under `/sys/devices/...`. Role switches are registered by USB controller
and PHY drivers, and are consumed by mux/driver code rather than by char
nodes -- there is no /dev side and no usb_role bus. The class coordinates
with two neighbors: the Type-C connector class
([typec](./typec.md)), which owns role policy on Type-C ports, and the UDC
class ([udc](./udc.md)), whose device-mode side is engaged when the role
switch selects `device`.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<switch>/role` | RW | `none`, `host`, or `device`; write requests a role swap | always | ABI testing `sysfs-class-usb_role` (Jan 2018) |
| `<switch>/connector` | RO symlink | optional symlink to the USB Type-C connector | optional | ABI testing `sysfs-class-usb_role` (Feb 2024) |
| `/sys/class/usb_role/` | -- | container directory for switches | always | ABI testing `sysfs-class-usb_role` (Jan 2018) |

The ledger records exactly these 3 paths; no other attribute is documented
anywhere in the tree.

## Safety and writes

`role` is the only writable, and a write physically re-points the USB
controller between host and peripheral roles -- devices and hosts attached
to the port see a disconnect/reconnect. The ABI states no error conventions
or capability requirements; in practice writes need root or udev-granted
permissions. Reads are safe. The two-line ABI leaves behavior details
(swap latency, failure modes) undocumented; nothing more may be claimed
from the cached sources.

## References

- `Documentation/ABI/testing/sysfs-class-usb_role` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-usb_role)
- `drivers/usb/roles/Makefile` (torvalds/linux master; fetched obj line)
- Ledger row SYSC-usb_role; `/sys/class/usb_role` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [typec](./typec.md), [usb_power_delivery](./usb_power_delivery.md), [udc](./udc.md)
