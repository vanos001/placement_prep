# /sys/class/rc

| Field | Value |
|---|---|
| Subsystem | Remote Controller core (media subsystem), `drivers/media/rc/` (`obj-$(CONFIG_RC_CORE) += rc-core.o`, built from `rc-main.o`, `rc-ir-raw.o`, and under `CONFIG_LIRC` `lirc_dev.o`, torvalds/linux master) |
| Config gate | `CONFIG_RC_CORE` (obj line verified against torvalds/linux master 2026) |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-rc` (8 What entries); plus `Documentation/ABI/testing/sysfs-class-rc-nuvoton` for the driver-specific `wakeup_data` |
| Since | 2.6.35 (class dir, `rc<N>`); 2.6.36 (`protocols`); 3.15 (`filter`, `filter_mask`, `wakeup_filter`, `wakeup_filter_mask`); 4.6 (`wakeup_data`, nuvoton); 4.11 (`wakeup_protocols`) |
| Live (5.10.134 host) | class absent: no `/sys/class/rc` directory, no IR receiver registered |
| Ledger ID | SYSC-rc |

## What it represents

One directory per infrared remote-control receiver, `rc<N>`. The class is
the configuration plane for IR receivers: it selects which IR protocols the
receiver decodes (`protocols`), sets scancode filters, and programs wakeup
behavior so that a specific scancode can wake a suspended system. The
`wakeup_*` group is the interesting half: `wakeup_protocols` picks a single
protocol (variants are listed separately, e.g. `rc-6-6a-24` vs
`rc-6-6a-32`), and `wakeup_filter`/`wakeup_filter_mask` define the scancode
comparison that triggers the wake event.

## Relationship to the device model

`/sys/class/rc/rc<N>` is a class view over a receiver device under
`/sys/devices/...` (typically a media/USB/PCI or platform device). There is
no rc bus; the class exists for tuning and wakeup policy. The
`sysfs-class-rc` file says the sub-directory "belongs to the Remote
Controller core and provides a sysfs interface for configuring infrared
remote controller receivers". Driver-specific attributes can extend the
directory -- the nuvoton CIR driver adds `wakeup_data`, a raw
pulse/space wakeup sequence in microseconds that some systems reset to
factory defaults at each boot.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `rc<N>/protocols` | RW | space-separated list, enabled protocols in `[]`; write `+proto`/`-proto`/`proto`/`none`; EINVAL on invalid combination | always | ABI testing `sysfs-class-rc` (2.6.36) |
| `rc<N>/filter` | RW | scancode expected value; pairs with `filter_mask`; may reset to 0 on protocol change | always | ABI testing `sysfs-class-rc` (3.15) |
| `rc<N>/filter_mask` | RW | scancode bits to compare; 0 disables the filter | always | ABI testing `sysfs-class-rc` (3.15) |
| `rc<N>/wakeup_protocols` | RW | list of wakeup protocol variants; exactly one selectable; `none` disables wakeup | always | ABI testing `sysfs-class-rc` (4.11) |
| `rc<N>/wakeup_filter` | RW | scancode expected value to trigger wake | always | ABI testing `sysfs-class-rc` (3.15) |
| `rc<N>/wakeup_filter_mask` | RW | wakeup scancode comparison mask | always | ABI testing `sysfs-class-rc` (3.15) |
| `rc<N>/wakeup_data` | RW | stored CIR wakeup sequence: pulse, space, pulse ... in microseconds | driver-specific (nuvoton) | ABI testing `sysfs-class-rc-nuvoton` (4.6) |

## Safety and writes

Writes either fail cleanly (EINVAL for unknown protocols or combinations)
or silently reconfigure hardware filtering. Two caveats from the ABI text:
filters "may be reset to 0 if the current protocol is altered", so
writers must re-apply filters after protocol changes; and wakeup writes
fail if the hardware does not support wakeup. No capability requirements
are stated; in practice writing needs root or udev-granted rights.

## References

- `Documentation/ABI/testing/sysfs-class-rc`, `Documentation/ABI/testing/sysfs-class-rc-nuvoton` (cached copies; online: https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-rc)
- `drivers/media/rc/Makefile` (torvalds/linux master; fetched obj line)
- Ledger row SYSC-rc (9 documented attrs incl. the nuvoton entry); `/sys/class/rc` absent per `source-cache/live-sys/class-list.txt`
- Sibling pages: [input](./input.md)
