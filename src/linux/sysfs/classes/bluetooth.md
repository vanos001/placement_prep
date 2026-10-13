# /sys/class/bluetooth

| Field | Value |
|---|---|
| Subsystem | Bluetooth core, net/bluetooth/hci_sysfs.c (class `bt_class`, name "bluetooth") |
| Config gate | CONFIG_BT, "Bluetooth subsystem support" (net/bluetooth/Kconfig) |
| ABI documentation | Documentation/ABI/stable/sysfs-class-bluetooth (1 What: entry); HID child attrs in Documentation/ABI/testing/sysfs-driver-hid |
| Since | `reset` dated 14-Jan-2025, KernelVersion 6.13; the class itself is older but the sources checked state no date for it |
| Live (5.10.134 host) | none observed (no Bluetooth adapter in the container) |
| Ledger ID | SYSC-bluetooth |

## What it represents

HCI host devices (device type "host", named hci`<N>`) and per-connection link devices (device type "link", named hciN:`<handle>`, net/bluetooth/hci_sysfs.c). RFCOMM tty devices are moved off the link device before its destruction (the __match_tty/device_move path in the same file), so the class also hosts rfcomm nodes transiently.

## Relationship to the device model

Host devices are parents of their link devices and of HID-over-BT child devices; those children expose the HID attributes documented in sysfs-driver-hid. The rfkill and tty layers are separate interfaces and are not part of this class.

## Attributes (representative; source per row)

| Attribute | R/W | Meaning (source) |
|---|---|---|
| `hci<index>/reset` | WO | Write any data to trigger the vendor reset method; may go through the transport (UART/USB) or out of band such as GPIO (ABI stable/sysfs-class-bluetooth; DEVICE_ATTR_WO(reset) in hci_sysfs.c) |
| `hci<addr>/<hid-dev>/report_descriptor` | RO | HID report descriptor of a Bluetooth HID child (ABI testing/sysfs-driver-hid) |
| `hci<addr>/<hid-dev>/country` | RO | HID country code (ABI testing/sysfs-driver-hid) |

## Safety and writes

`reset` is write-only and resets the whole controller through the vendor hook; on systems with GPIO resets this can drop every active connection. No other attributes are named by the sources checked. None observed on the container host.

## References

- Documentation/ABI/stable/sysfs-class-bluetooth, Documentation/ABI/testing/sysfs-driver-hid
- net/bluetooth/hci_sysfs.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [interface encyclopedia method](../../interface-encyclopedia.md)
