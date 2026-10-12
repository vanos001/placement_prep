# /sys/class/udc

| Field | Value |
|---|---|
| Subsystem | USB gadget UDC (Device Controller) core, `drivers/usb/gadget/udc/` (`obj-$(CONFIG_USB_GADGET) += udc-core.o`, torvalds/linux master) |
| Config gate | `CONFIG_USB_GADGET` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/stable/sysfs-class-udc` (11 What entries) |
| Since | 3.1 (all entries except `function`); 4.13 (`function`) |
| Live (5.10.134 host) | class absent: no `/sys/class/udc` directory, no gadget-capable controller bound |
| Ledger ID | SYSC-udc |

## What it represents

One directory per USB Device Controller -- the device-side hardware that
lets Linux act as a USB peripheral (gadget). Each `<udc>` directory carries
the controller's negotiation state: `maximum_speed` and `current_speed`
(the latter the negotiated speed of the active connection), the OTG
attribute group (`is_otg`, `srp`, `a_hnp_support`, `a_alt_hnp_support`,
`b_hnp_enable`, `is_a_peripheral`), and the gadget state machine
(`state`: not-attached, attached, powered, reconnecting, unauthenticated,
default, addressed, configured, suspended -- with the ABI noting not all
controllers report all states). `function` names the currently running
gadget driver. Userspace gadget binders (configfs-based gadget stacks,
`usb-gadget` configfs ABI) select a UDC by writing its name into
`UDC` -- the class is what that name indexes.

## Relationship to the device model

`/sys/class/udc/<udc>` is a class view over the controller device under
`/sys/devices/...`. The gadget framework keeps one registered UDC per
controller; configfs gadget functions hang off devices in the gadget tree,
not in this class (the attrs cache records one such nested path,
`udc.name/device/gadget/video4linux/video.name/function_name`, which the
ledger counts toward its 12 paths but which the stable ABI file does not
document). Role changes with dual-role hardware are coordinated with the
USB role switch class: sibling page [usb_role](./usb_role.md); Type-C side:
[typec](./typec.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `<udc>/state` | RO | state machine string: not-attached / attached / powered / reconnecting / unauthenticated / default / addressed / configured / suspended | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/current_speed` | RO | negotiated speed of the current connection | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/maximum_speed` | RO | maximum USB speed supported by the port | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/function` | RO | name of the currently running USB gadget driver | always | ABI stable `sysfs-class-udc` (4.13) |
| `<udc>/is_otg` | RO | port supports OTG | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/srp` | WO (manual trigger) | start Session Request Protocol | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/a_hnp_support` | RO | OTG A-Host supports HNP at this port | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/a_alt_hnp_support` | RO | OTG A-Host supports HNP at an alternate port | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/b_hnp_enable` | RO | OTG A-Host enabled HNP support | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/is_a_peripheral` | RO | default Host on an OTG session switched to peripheral via HNP | always | ABI stable `sysfs-class-udc` (3.1) |
| `<udc>/soft_connect` | RW | disconnect data pullup resistors, causing logical disconnection from the host | always | ABI stable `sysfs-class-udc` (3.1) |

## Safety and writes

Reads are safe. `soft_connect` is the dangerous one: writing it logically
disconnects the gadget from the host by dropping the pullups. `srp`
initiates a session request on OTG hardware. The ABI states no capability
requirements; writes require appropriate privileges in practice. The file
carries empty `Users:` sections, so no documented consumers are cited.

## References

- `Documentation/ABI/stable/sysfs-class-udc` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/stable/sysfs-class-udc)
- `Documentation/ABI/testing/configfs-usb-gadget*` (cached; the configfs side of gadget binding)
- `drivers/usb/gadget/udc/Makefile` (torvalds/linux master; fetched obj line)
- Ledger row SYSC-udc; `/sys/class/udc` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [usb_role](./usb_role.md), [typec](./typec.md)
