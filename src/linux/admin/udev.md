# udev

`udev` is the Linux device manager that ships with systemd. It runs in userspace (`udevd`), listens to kernel `uevent`s via netlink, applies rules to set device permissions, create stable device names, load drivers, and emit synthetic events. This page covers the device model, the rules language, the kernel-userspace protocol, and the common pitfalls that have shaped 15 years of `udev` practice.

## Why udev Exists

Before 2003, Linux used a static `/dev` directory shipped in `dev.tar.gz` containing every device node the system might ever have (~20,000 entries). `devfs` (Linux 2.4) tried to populate `/dev` only with devices present at boot, but had ordering and naming issues. Hot-pluggable devices (USB, FireWire) created a new requirement: a user-space daemon that saw kernel events and adjusted `/dev` accordingly.

In 2003, Greg Kroah-Hartman and Kay Sievers wrote `udev`. By 2012 it was merged into systemd. The current architecture:

```text
   Kernel emits uevent                              udevd
   (netlink KOBJECT_*)                              (user space, persistent)
        │                                              │
        │  ──────── KOBJECT_ACTION (ADD/CHANGE/REMOVE)─→│
        │                                              │ 1. Match against /etc/udev/rules.d/*
        │                                              │ 2. Apply rules: RUN+=, SYMLINK+=, OWNER, GROUP, MODE
        │                                              │ 3. Apply hwdb database lookups
        │                                              │ 4. Synthesize events for dependent devices
        │                                              │
        │ ←───── may call back into kernel via         │
        │         /sys/devices/.../uevent write       │
        │                                              │
        ▼                                              ▼
```

## The Device Model and `uevent`

The kernel maintains a hierarchical tree under `/sys/devices/` describing every device the system knows about. Each device has:

- A `uevent` file — writing `add`, `remove`, `change` triggers a synthetic KOBJECT event.
- A `modalias` file — for bus drivers to claim the device.
- A `subsystem` symlink — points to `/sys/class/net/`, `/sys/block/`, etc.

When a kernel module enumerates a device (PCI, USB, platform), it calls `kobject_uevent_env()` with an action and key=value pairs. The kernel formats these as a `null`-separated string buffer and broadcasts it on the `NETLINK_KOBJECT_UEVENT` socket.

A captured USB add event looks like:

```text
ACTION@add
DEVPATH@/devices/pci0000:00/0000:00:14.0/usb1/1-3
SUBSYSTEM@usb
TYPE@usb_device
PRODUCT@1058/2598/1102
SEQNUM@12345
MAJOR@189
MINOR@132
DEVNAME@bus/usb/001/133
TAGS@:systemd:
```

`udevd` reads these on the netlink socket. The rules engine then matches against the event fields.

## Rules Files

Rules live in three places:

1. `/lib/udev/rules.d/*.rules` — shipped by the OS packages; do not modify.
2. `/etc/udev/rules.d/*.rules` — local overrides; process alphabetically.
3. `/run/udev/rules.d/*.rules` — volatile, generated at boot.

Files are processed in lexical order; within a file, rules are processed top to bottom. A rule has the form:

```udev
# /etc/udev/rules.d/99-placement.rules

# Match USB block devices and assign a stable symlink
SUBSYSTEM=="block", ACTION=="add", KERNEL=="sd*[!0-9]", \
    ATTRS{vendor}=="Western Digital", \
    SYMLINK+="wd-disk-%k", \
    OWNER="root", GROUP="disk", MODE="0660", \
    RUN+="/usr/local/bin/on-wd-add $env{DEVNAME}"

# Pin a particular serial number to a fixed device name
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", \
    ATTRS{serial}=="AB12345", \
    SYMLINK+="ttyUSART0"

# Disable autosuspend for a flaky device
SUBSYSTEM=="usb", ATTRS{idVendor}=="0451", ATTRS{idProduct}=="6141", \
    ATTR{power/control}="on", \
    ATTR{power/autosuspend_delay_ms}="-1"
```

The matching keys (`==`) are non-final; the assignment keys (`=`, `+=`, `:=`) are final. Use `:=` for assignments you want to be sticky across subsequent rules.

Key fields include:

| Key | Meaning |
|-----|---------|
| `ACTION`       | `add`, `remove`, `change`, `online`, `offline` |
| `SUBSYSTEM`    | e.g., `block`, `net`, `tty`, `usb`, `pci` |
| `KERNEL`       | The kernel name (e.g., `sda`, `eth0`) |
| `DEVPATH`      | Path in /sys |
| `ATTR{...}`    | A file in the device's sysfs directory |
| `ATTRS{...}`   | A file in the device's sysfs dir or any ancestor's |
| `ENV{...}`     | An environment variable, settable with `ENV{key}="val"` |
| `PROGRAM`      | Run an external program; its stdout is split into `%c{1..N}` |
| `RESULT`       | Match PROGRAM's stdout against a pattern |
| `IMPORT{...}`  | Import variables from a builtin or external source |
| `OPTIONS`      | `static_node=`, `ignore_remove`, `watch` |

The most useful pattern is `IMPORT{builtin}="hwdb"` which queries the `hwdb.bin` (the hardware database at `/etc/udev/hwdb.bin`) for vendor-specific metadata like keyboard scan codes, mouse button mappings, and persistent device properties.

## The hwdb Database

`/etc/udev/hwdb.bin` is a precompiled binary database of device property records. Source files live in `/etc/udev/hwdb.d/*.hwdb` and `/lib/udev/hwdb.d/*.hwdb`. Each entry is:

```text
# A USB device's properties
usb:v1058p2598*
 KEYBOARD_KEY_90001=mail
 KEYBOARD_KEY_90002=www
 ID_INPUT_KEYBOARD=1

# A laptop's accelerometer orientation
sensor:modalias:*
 ACCEL_MOUNT_MATRIX=1,0,0;0,1,0;0,0,1
```

`udevadm hwdb --update` rebuilds `hwdb.bin`. The lookup at event time is O(1) via a trie in the binary file.

## udevadm

`udevadm` is the user-facing tool for inspecting the rules pipeline:

```bash
# Show every event that fired for a device, in order, with timing
udevadm monitor --udev --kernel

# Trigger a rescan of a device (writes "add" to its uevent file)
udevadm trigger --action=add /sys/devices/pci0000:00/0000:00:14.0

# Walk the rule tree for a device and explain what was matched
udevadm test /sys/devices/pci0000:00/0000:00:14.0/usb1/1-3

# Show all properties of the device as udev sees them
udevadm info --query=all --path=/sys/devices/...
udevadm info --query=property --name=/dev/sda
```

`udevadm info --attribute-walk` walks up the device tree showing every sysfs attribute available for matching — the canonical starting point when writing a new rule.

## Persistent Device Naming

`/dev/disk/by-id/`, `/dev/disk/by-uuid/`, `/dev/disk/by-partlabel/`, and `/dev/disk/by-path/` are all udev-created symlinks. They live in `/usr/lib/udev/rules.d/` (e.g., `60-persistent-storage.rules`) and use the model:

```udev
KERNEL=="sd*[!0-9]", IMPORT{program}="/usr/lib/udev/ata_id --export $devnode"
KERNEL=="sd*[!0-9]", ENV{ID_FS_UUID}=="?*", SYMLINK+="disk/by-uuid/$env{ID_FS_UUID}"
KERNEL=="sd*[!0-9]", ENV{ID_SERIAL}=="?*", SYMLINK+="disk/by-id/ata-$env{ID_SERIAL}"
```

`ata_id`, `scsi_id`, `usb_id` are helper programs that read device identification pages and emit env vars. The same pattern is used for NICs (`/dev/disk/by-path/pci-...`) and is why `ls /dev/disk/by-*/` is the recommended way to address storage in `fstab` and `crypttab`.

## Network Interface Naming

`/etc/systemd/network/*.link` files (originally udev rules, moved to `systemd-udevd`'s netlink backend in systemd 197) give stable names to NICs:

```ini
# /etc/systemd/network/70-wired.link
[Match]
MACAddress=00:11:22:33:44:55

[Link]
Name=eth0
```

Without a `.link` rule, systemd uses predictable naming: `enp3s0` (PCI bus 3, slot 0), `enx001122334455` (USB MAC suffix), `ens1` (PCI hotplug slot 1). The old `eth0`/`eth1` enumeration order was unstable across reboots when drivers loaded in different orders.

## Common Pitfalls

1. **Race conditions with `RUN` programs.** `RUN+=` executes in `udevd`'s context after the rules match but before the event is "complete". If the program blocks (waits on a network mount), the whole udev event pipeline stalls. Use `OPTIONS+="event_timeout=10"` and never do long-running work in `RUN`; spawn a separate systemd service with `SYSTEMD_WANTS+=`.
2. **Forgetting `--reload` after editing rules.** `udevadm control --reload-rules` reloads the rules without restarting `udevd`. Without this, edits only take effect on the next event after a daemon restart.
3. **Overwriting `lib` rules with `etc` rules of the same name.** `udev` lexically sorts files; `99-my.rules` and `99-my.rules` in `/lib` will conflict. The `etc` copy wins silently — your changes survive package updates but the next `apt upgrade` may surprise you.
4. **Using `ATTR` instead of `ATTRS`.** `ATTR{...}` matches only files in the device's own sysfs directory; `ATTRS{...}` walks up the parent chain. Most real-world rules want `ATTRS`.
5. **Trusting `udevadm trigger` to fix broken state.** `trigger --action=add` re-runs ADD rules, but `--action=change` (the default) is safer for re-applying permissions after rule edits.

## References

- [udev(7)](https://www.freedesktop.org/software/systemd/man/udev.html)
- [udevadm(8)](https://www.freedesktop.org/software/systemd/man/udevadm.html)
- Greg Kroah-Hartman, "[udev: A Userspace Implementation of devfs](https://www.kernel.org/pub/linux/utils/kernel/hotplug/udev-ols.pdf)" (OLS 2003)
- Kay Sievers, "[Persistent Device Naming](https://systemd.io/PERSISTENT_DEVICE_NAMING/)"
- [LWN: "Revising the udev rules" (2012)](https://lwn.net/Articles/490336/)
- systemd source: [`src/udevd`](https://github.com/systemd/systemd/tree/main/src/udevd)
