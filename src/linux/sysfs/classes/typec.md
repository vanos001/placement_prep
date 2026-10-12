# /sys/class/typec

| Field | Value |
|---|---|
| Subsystem | USB Type-C connector class, `drivers/usb/typec/` (`typec-y := class.o mux.o bus.o pd.o retimer.o mode_selection.o`; `obj-$(CONFIG_TYPEC) += typec.o`, torvalds/linux master) |
| Config gate | `CONFIG_TYPEC` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-typec` (31 What entries); `Documentation/ABI/obsolete/sysfs-class-typec` (class alt-mode files deprecated in favor of `sysfs-bus-typec`) |
| Since | April 2017 (core role/mode files); Feb 2020 (`orientation`); Nov 2020 (`number_of_alternate_modes`); Jan 2021 (partner/cable `usb_power_delivery_revision`); May 2022 (`select_usb_power_delivery`); Nov 2024 (`usb_capability`, partner `usb_mode`); Jul 2025 (alt-mode `priority`) |
| Live (5.10.134 host) | class absent: no `/sys/class/typec` directory, no connector registered |
| Ledger ID | SYSC-typec |

## What it represents

Three kinds of devices under one class: ports (`port0`), partners
(`port0-partner`), and cables (`port0-cable`, with `port0-plug0` for
electronically marked cables). Ports expose role control: `data_role`
(host/device), `power_role` (source/sink), `port_type` (source/sink/dual),
and `vconn_source`, each with synchronous swap semantics -- the ABI states
write(2) does not return until the swap finished, poll(2) wakes on role
changes, and changes raise KOBJ_CHANGE uevents. PD negotiation surfaces as
`power_operation_mode` (default / 1.5A / 3.0A / usb_power_delivery),
`usb_power_delivery_revision`, `select_usb_power_delivery`, and
`usb_capability` (usb2/usb3/usb4). Partner and cable directories carry
product-type discovery (`type`, `accessory_mode`, `plug_type`), the
`identity/` VDO directory from the Discover Identity command, and
`number_of_alternate_modes`.

## Relationship to the device model

The driver-api typec doc states every port is presented as its own device
under `/sys/class/typec/`, and that the partner device's parent is always
its port (e.g. `/sys/class/typec/port0/port0-partner/`). Alternate-mode
devices originally appeared under the class too, but the obsolete ABI
header says those files are deprecated and "the same files are available
under /sys/bus/typec" -- `sysfs-bus-typec` documents the surviving
`svid`/`mode`/`vdo`/`active` set there. The class coexists with
[usb_role](./usb_role.md) (role switches for non-Type-C ports) and
[usb_power_delivery](./usb_power_delivery.md) (PDO trees).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `port/data_role` | RW | `[host] device` style list; bracketed = current; write to swap | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `port/power_role` | RW | `[source] sink` style list; write to swap | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `port/port_type` | RW | source / sink / dual | always | ABI testing `sysfs-class-typec` (May 2017) |
| `port/vconn_source` | RW | yes / no | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `port/preferred_role` | RW | source / sink / none (Try.SRC / Try.SNK hint) | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `port/power_operation_mode` | RO | default, 1.5A, 3.0A, usb_power_delivery | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `port/usb_power_delivery_revision` | RO | "2.0", "3.0", "3.1", or 0.0 | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `port/usb_typec_revision` | RO | Type-C spec revision | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `port/orientation` | RO | normal / reverse / unknown (CC1/CC2) | always | ABI testing `sysfs-class-typec` (Feb 2020) |
| `port/select_usb_power_delivery` | RW | PD capabilities list, bracketed = used | always | ABI testing `sysfs-class-typec` (May 2022) |
| `port/usb_capability` | RW | usb2 / usb3 / usb4, bracketed = default Enter_USB mode | always | ABI testing `sysfs-class-typec` (Nov 2024) |
| `port/supported_accessory_modes` | RO | space-separated accessory mode list | always | ABI testing `sysfs-class-typec` (Apr 2017) |
| `partner/{supports_usb_power_delivery,type,accessory_mode,usb_mode,number_of_alternate_modes}` | RO | yes/no; product type (hub, peripheral, psd, ama, host, power_brick, amc); usb2/usb3/usb4 | some hidden until PD discovery | ABI testing `sysfs-class-typec` (2017-2024) |
| `{partner,cable}/identity/{id_header,cert_stat,product,product_type_vdo1..3}` | RO | VDO hex values; 0 until Discover Identity result available; pollable | dir appears only if driver supports it | ABI testing `sysfs-class-typec` (2017-2020) |
| `cable/type`, `cable/plug_type` | RO | active/passive/undefined; type-a/type-b/type-c/captive | if visible to driver | ABI testing `sysfs-class-typec` (Apr 2017) |
| `<alt-mode>/supported_roles`, `<alt-mode>/priority` | RO / RW | source/sink; integer 0-255, lower = higher priority | alt modes only | ABI testing `sysfs-class-typec` (2017, Jul 2025) |
| `<dev>/mode<index>/{svid,description,vdo,active}` | mixed | alt-mode VDO data; `active` enters/exits the mode | deprecated under the class; live under /sys/bus/typec | ABI obsolete `sysfs-class-typec`; testing `sysfs-bus-typec` (Jul 2018) |

## Safety and writes

Role swaps, `port_type` changes, VCONN swaps, and mode enter/exit are
synchronous hardware operations -- a write blocks until the physical
negotiation finishes, and can fail outright (the ABI documents errors for
unsupported swaps via the poll/KOBJ_CHANGE contract). Writing
`select_usb_power_delivery`, `usb_capability`, and `priority` re-negotiates
what the port advertises. Reads are safe, including pollable identity VDOs.
No capability requirements are stated; in practice writes need root or
udev-granted rights.

## References

- `Documentation/ABI/testing/sysfs-class-typec`, `Documentation/ABI/obsolete/sysfs-class-typec`, `Documentation/ABI/testing/sysfs-bus-typec` (cached copies; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-typec)
- `Documentation/driver-api/usb/typec.rst` (not in sparse cache; device-model statements cited from it)
- `drivers/usb/typec/Makefile` (torvalds/linux master; fetched obj line)
- Ledger row SYSC-typec; `/sys/class/typec` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [usb_power_delivery](./usb_power_delivery.md), [usb_role](./usb_role.md), [udc](./udc.md)
