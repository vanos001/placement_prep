# /sys/class/usb_power_delivery

| Field | Value |
|---|---|
| Subsystem | USB Power Delivery class, `drivers/usb/typec/` (`pd.o` is a member of `typec-y := class.o mux.o bus.o pd.o retimer.o mode_selection.o`; torvalds/linux master) |
| Config gate | `CONFIG_TYPEC` (same gate as the Type-C connector class; obj/Makefile line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-usb_power_delivery` (37 What entries) |
| Since | May 2022 (core tree); Feb 2023 (sink `higher_capability`); Oct 2023 (source fixed-supply `peak_current`); Oct 2025 (AVS `spr_adjustable_voltage_supply` group) |
| Live (5.10.134 host) | class absent: no `/sys/class/usb_power_delivery` directory, no PD device registered |
| Ledger ID | SYSC-usb_power_delivery |

## What it represents

The Power Data Object (PDO) trees exchanged in USB Power Delivery
`Source_Capabilities` and `Sink_Capabilities` messages. Each PDO becomes
its own device named `<position>:<type>` (position first, then supply
type), so a capabilities list reads as a directory listing:
`1:fixed_supply`, `2:variable_supply`, `3:programmable_supply`, etc.
Position 1 is special: the ABI states the first PDO is always the vSafe5V
Fixed Supply, the only mandatory PDO, and it alone carries the USB-bit
attributes (`dual_role_power`, `unconstrained_power`,
`usb_communication_capable`, `dual_role_data`,
`usb_suspend_supported`, `higher_capability`,
`unchunked_extended_messages_supported`). Supply-type directories expose
the decoded PDO fields: fixed supplies carry `voltage` (millivolts),
`maximum_current` / `operational_current` (milliamperes, source/sink
respectively) and `fast_role_swap_current` (0-3); variable and battery
supplies carry `minimum_voltage`/`maximum_voltage` (millivolts) plus
`maximum_power`/`operational_power` (milliwatts); programmable (PPS) and
AVS augmented PDOs carry their current/voltage ranges and
`pps_power_limited`.

## Relationship to the device model

The class sits beside the Type-C connector class: the `...` in every
documented path is a per-device prefix (a port or partner device), and the
`source-capabilities` / `sink-capabilities` directories branch beneath it.
This is a pure presentation of protocol state -- the objects mirror PD
messages, so the directory shape changes when a partner is renegotiated,
and no bus or char node is involved. Sibling pages:
[typec](./typec.md) (the port that negotiates the messages),
[usb_role](./usb_role.md).

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `.../revision` | RO | PD spec revision used in communication | always | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `.../version` | RO | version of that revision; "in most cases ... not known and the file is not available" | optional | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `.../source-capabilities/`, `.../sink-capabilities/` | RO dirs | one device per PDO, named `<position>:<type>` | PD-capable devices | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `<cap>/1:fixed_supply/{dual_role_power,unconstrained_power,usb_communication_capable,dual_role_data,unchunked_extended_messages_supported}` | RO | boolean bit fields of the vSafe5V object | vSafe5V PDO | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `source-capabilities/1:fixed_supply/usb_suspend_supported` | RO | boolean | source vSafe5V | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `sink-capabilities/1:fixed_supply/higher_capability` | RO | 0/1 (sink needs more than vsafe5V) | sink vSafe5V | ABI testing `sysfs-class-usb_power_delivery` (Feb 2023) |
| `<pos>:fixed_supply/voltage` | RO | millivolts | fixed PDOs | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `source-capabilities/<pos>:fixed_supply/{maximum_current,peak_current}` | RO | milliamperes; peak-current capability field | source fixed PDOs | ABI testing `sysfs-class-usb_power_delivery` (May 2022, Oct 2023) |
| `sink-capabilities/<pos>:fixed_supply/{operational_current,fast_role_swap_current}` | RO | milliamperes; FRS level 0-3 | sink fixed PDOs | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `<pos>:variable_supply/{minimum_voltage,maximum_voltage}` + source `maximum_current` / sink `operational_current` | RO | millivolts / milliamperes | variable PDOs | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `<pos>:battery/{minimum_voltage,maximum_voltage}` + source `maximum_power` / sink `operational_power` | RO | millivolts / milliwatts | battery PDOs | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `<pos>:programmable_supply/{minimum_voltage,maximum_voltage,maximum_current}` + source `pps_power_limited` | RO | millivolts / milliamperes; PPS power limited bit | PPS APDOs | ABI testing `sysfs-class-usb_power_delivery` (May 2022) |
| `<pos>:spr_adjustable_voltage_supply/{maximum_current_9V_to_15V,maximum_current_15V_to_20V,peak_current}` | RO | milliamperes | AVS APDOs | ABI testing `sysfs-class-usb_power_delivery` (Oct 2025) |

## Safety and writes

Everything documented is read-only: the class decodes already-negotiated
messages, and negotiation itself is driven through the Type-C port class
([typec](./typec.md)). Reads are safe. No capability requirements or
warnings appear in the ABI file. The practical caveat is volatility: files
appear and disappear as PDOs are discovered, so readers must tolerate
ENOENT.

## References

- `Documentation/ABI/testing/sysfs-class-usb_power_delivery` (cached copy; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-usb_power_delivery)
- `drivers/usb/typec/Makefile` (torvalds/linux master; `pd.o` within `typec-y`)
- Ledger row SYSC-usb_power_delivery (36 paths); `/sys/class/usb_power_delivery` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [typec](./typec.md), [usb_role](./usb_role.md), [udc](./udc.md)
