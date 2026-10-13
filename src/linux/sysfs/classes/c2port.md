# /sys/class/c2port

| Field | Value |
|---|---|
| Subsystem | C2 port interface (ABI doc, contact Rodolfo Giometti); implementation file not in cached tree |
| Config gate | not verifiable from the cached tree: no Kconfig or Makefile mentioning c2port exists in the cached tree, and the ABI entry names no config symbol (not verified) |
| ABI documentation | `Documentation/ABI/testing/sysfs-c2port` |
| Since | not stated in the ABI entries (dated October 2008) |
| Live (5.10.134 host) | class absent: no `c2port` row in the cached live enumeration of 46 classes |
| Ledger ID | SYSC-c2port |

## What it represents

A unified interface to C2 ports: debug/programming connections to a connected microcontroller, exposed per port as `c2portX` directories. The ABI describes the directory set as providing files "to manage and control its C2 port": an enable gate (`access`), identity reads (`dev_id`, `rev_id`), and a flash subsystem (`flash_access` gate, geometry reads `flash_block_size`/`flash_blocks_num`, content export `flash_data`, and the `flash_erase` command). Everything hangs off the two gates `access` and `flash_access`, without which "no commands can be sent", per the ABI wording.

## Relationship to the device model

Each `c2portX` entry is created by a hardware-specific driver that bit-bangs or drives the C2 protocol over its own bus/IO; the class is the uniform userspace layer above those drivers. The ABI documents no bus, no parent device and no uevent behavior -- only the class directory tree and its files. Device identity comes from the connected micro (`dev_id`, `rev_id`), read after `access` is enabled.

## Attributes

| Attribute | R/W | Unit/format | Conditional? | Source |
|---|---|---|---|---|
| `c2portX/access` | RW | enable gate for the C2 port; no commands can be sent while 0 | always | ABI testing `sysfs-c2port` |
| `c2portX/dev_id` | RO | device ID of the connected micro | always | ABI testing `sysfs-c2port` |
| `c2portX/rev_id` | RO | revision ID of the connected micro | always | ABI testing `sysfs-c2port` |
| `c2portX/flash_access` | RW | enable gate for on-board flash access; no commands can be sent while 0 | always | ABI testing `sysfs-c2port` |
| `c2portX/flash_block_size` | RO | on-board flash block size | always | ABI testing `sysfs-c2port` |
| `c2portX/flash_blocks_num` | RO | on-board flash blocks number | always | ABI testing `sysfs-c2port` |
| `c2portX/flash_data` | RO (per ABI wording "export the content") | content of the on-board flash | always | ABI testing `sysfs-c2port` |
| `c2portX/flash_erase` | W (triggers the erase command) | executes "erase" on the on-board flash | always | ABI testing `sysfs-c2port` |
| `c2portX/reset` | W (triggers reset) | executes a "reset" command on the connected micro | always | ABI testing `sysfs-c2port` |

## Safety and writes

This class exists to perform writes with hardware side effects: `flash_erase` erases the micro's flash, `reset` resets the micro, and `flash_data` dumps its content. Both `access` and `flash_access` must be enabled first (commands are refused while the gates are 0), which limits accidental damage; still, treat any write here as reprogramming/erasing a device. Writability of `flash_data` (programming) is not stated in the ABI text and is not verified.

## References

- `Documentation/ABI/testing/sysfs-c2port` (cached copy; eleven What: entries including the class directory itself)
- [ABI doc online](https://github.com/torvalds/linux/blob/master/Documentation/ABI/testing/sysfs-c2port)
- [sysfs overview](../overview.md), [ledger](../ledger.md)
- Ledger row SYSC-c2port
