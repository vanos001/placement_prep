# /sys/class/zram-control

| Field | Value |
|---|---|
| Subsystem | zram driver (compressed RAM block devices), control class for hot-adding/removing zram devices; implementation file not in cached tree |
| Config gate | not verifiable from the cached sources (cached tree has no Kconfig or driver files); the class exists on the live host, so its gate (zram support) is enabled there |
| ABI documentation | `Documentation/ABI/testing/sysfs-class-zram` (`/sys/class/zram-control/`, `hot_add`, `hot_remove`); the zram device attributes are documented separately in the same file |
| Since | August 2015, KernelVersion 4.2 (all entries) |
| Live (5.10.134 host) | class present with exactly 2 entries: `hot_add` (mode r--------, 0400) and `hot_remove` (mode -w-------, 0200) - verified live |
| Ledger ID | SYSC-zram-control |

## What it represents

The zram device-manager interface. Reading `hot_add` makes the kernel create a new zram device (zram1, zram2, ...) and returns its device id, which maps to `/dev/zram<id>`; writing a device id to `hot_remove` removes that zram device. This is how userspace (zramctl, systemd, Android init) sizes the zram pool dynamically instead of relying on the `zram_num_devices` module parameter.

## Relationship to the device model

The class directory is a control object, not a device: it has no parent bus and its two files act on the zram driver's device table. The created devices appear in the [block](./block.md) class (live host: zram0 at 253:0) with their own disk attribute set, documented in `Documentation/ABI/testing/sysfs-block-zram` - out of scope for this page.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `hot_add` | RO | read returns the new device id (integer), or an error code | always | ABI `sysfs-class-zram`, 4.2; live mode 0400 |
| `hot_remove` | WO | write device id X to remove /dev/zramX | always | ABI `sysfs-class-zram`, 4.2; live mode 0200 |

The live permission bits confirm the ABI: `hot_add` is read-only (the act of reading creates a device - there is no value to write), `hot_remove` is write-only.

## Safety and writes

`hot_add` consumes kernel memory on first use (the device becomes a compressed RAM disk once a disksize is set); unbounded reads create unbounded devices, so library code reads it once. `hot_remove` destroys a zram device - any data stored in it is lost - and fails if the device is in use (mounted or swapped-on); live host usage: zram0 exists and is managed through this interface. Both files are root-only by permission (0400/0200 live). Removal of the active swap device would be a self-inflicted outage; verify with zramctl which id is free first.

## References

- `Documentation/ABI/testing/sysfs-class-zram` (cached copy; zram-control entries, August 2015, 4.2)
- Implementation: not in cached tree
- Sibling page: [block](./block.md) (zram0 appears there live at 253:0); coverage: [ledger](../ledger.md)
- Live check: /sys/class/zram-control enumerated read-only (kernel 5.10.134): hot_add 0400, hot_remove 0200
