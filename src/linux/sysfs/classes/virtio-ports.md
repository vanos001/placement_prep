# /sys/class/virtio-ports

| Field | Value |
|---|---|
| Subsystem | virtio console driver, drivers/char/virtio_console.c (class `port_class`, name "virtio-ports") |
| Config gate | CONFIG_VIRTIO_CONSOLE, "Virtio console", depends on TTY (drivers/char/Kconfig) |
| ABI documentation | none found - checked the stable/, testing/ and obsolete/ ABI listings and grep for virtio-ports; attributes below are traced to drivers/char/virtio_console.c |
| Since | not stated by the sources checked (no ABI What: entries exist) |
| Live (5.10.134 host) | class present with 0 entries (no virtio console device attached) |
| Ledger ID | SYSC-virtio-ports |

## What it represents

One device per virtio serial port exported by a host over virtio. Ports back hvc consoles, generic bidirectional char streams, and the host-named ports tools address through /dev/vport* style udev symlinks. The char major is registered dynamically under the name "virtio-portsdev" (virtio_console.c register_chrdev).

## Relationship to the device model

Port devices are named vport`<device-index>`p`<port-id>` (device_create format "vport%up%u") and are parented by the virtio device of their console device. A debugfs twin exists: a "virtio-ports" directory with per-port files showing the port name and connection state (port_debugfs_show).

## Attributes (source: drivers/char/virtio_console.c)

| Attribute | R/W | Meaning |
|---|---|---|
| `name` | RO | Host-assigned port name (show_port_name); the group is created only once the host sends a name, followed by a KOBJ_CHANGE uevent so udev can create symlinks |

## Safety and writes

The single attribute is read-only. Port open/close and data flow are handled through the char device (port_fops) and the control virtqueue, not sysfs; the class exists so user space can enumerate ports and map names to device nodes. Present but empty on the container host because the container has no virtio console device.

## References

- drivers/char/virtio_console.c (fetched from torvalds/linux master into source-cache)
- [sysfs overview](../overview.md), [ledger](../ledger.md), [char devices](../../kernel/drivers/char-devices.md), [udev](../../admin/udev.md)
