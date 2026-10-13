# systemd-udevd and udev Rules

## Overview

`systemd-udevd` is the userspace daemon that governs `/dev`. The kernel
creates device nodes, but what they are called, who may open them, which
symlinks point at them, and which kernel modules get loaded are policy
decisions — and that policy lives in udevd and its rule database. The
kernel emits a *uevent* for every device addition, removal, or change;
udevd receives it over netlink, matches it against the rule files, and
applies the winners: symlinks, permissions, stored properties, module
loads, and short-lived helper programs.

Three properties define the design. udevd is *event-driven*: it idles
until a uevent arrives, then processes it in a bounded worker pool. It is
*rule-based*: behavior is data (the `.rules` files), so distributions,
packages, and administrators extend device handling without touching the
daemon. And it is *init-agnostic*: systemd ships and integrates it
tightly, but udevd itself only needs starting by whatever init is in
charge — the same rules run on systemd, OpenRC, and runit alike.

This page covers the event pipeline, the rule grammar, `udevadm`
operation, persistent naming, and the systemd integration points. For the
kernel-side filesystem that manufactures the nodes, see
[devtmpfs](../../kernel/filesystems/devtmpfs.md); for operator recipes,
see [udev.md](../../admin/udev.md).

## The Role of systemd-udevd

### Uevents: the kernel-to-userspace device protocol

When a driver registers or tears down a device, the kernel calls
`kobject_uevent()`. The event travels over a broadcast netlink socket of
family `NETLINK_KOBJECT_UEVENT` (group 2) as plaintext: a header line
such as `add@/devices/.../ttyUSB0`, followed by NUL-separated key/value
pairs — `ACTION=add`, `DEVPATH=...`, `SUBSYSTEM=tty`, `SEQNUM=N`,
`MODALIAS=usb:v0403p6001...`. The monotonic `SEQNUM` lets userspace
detect gaps and replay what it missed — the basis of coldplug. udevd also
re-publishes each *processed* event on the "udev" netlink group for
libudev consumers.

### The devtmpfs relationship

A common misconception is that udev creates `/dev` nodes. It does not —
since kernel 2.6.32, *devtmpfs* does: the kernel creates the node itself at
driver registration, with default ownership and mode. udev operates on top:

| Concern | devtmpfs (kernel) | udevd (userspace) |
|---|---|---|
| Node existence | creates/removes nodes | never the first creator |
| Name | kernel-chosen | may rename (network interfaces) |
| Symlinks | none | `/dev/disk/by-*`, custom `SYMLINK+=` |
| Ownership/mode | root:root, fixed default | `OWNER=`/`GROUP=`/`MODE=` policy |
| Properties | uevent key/values | enriched, persisted to `/run/udev/data` |
| Module loading | none | kmod via `MODALIAS` |

A system without udevd still boots with working nodes for loaded drivers
(see the interview questions) but loses naming policy, access control, and
hotplug. Mounting devtmpfs at `/dev` is mandatory — udevd refuses to run
on a static `/dev`.

### mdev and busybox: the minimal alternative

BusyBox ships `mdev`, a minimal substitute: it scans `/sys` (`mdev -s`,
the initramfs idiom) or consumes uevents, matching devices against
`/etc/mdev.conf` regexes with per-device owner/mode/symlink and a helper
command.

| Aspect | udevd | busybox mdev |
|---|---|---|
| Config | full rule language | one flat conf file |
| Symlink persistence | database in `/run/udev` | best-effort |
| Module autoload | kmod builtin, robust | `modprobe` per regex |
| Predictable naming | full scheme | none |

Embedded systems with a fixed, small device set often choose mdev — see
[busybox.md](../../binaries/busybox.md); anything mounting devtmpfs gets
the nodes for free, and mdev contributes symlinks and module handling.

### Module autoload and coldplug

When a device appears, udevd sees `MODALIAS=usb:v...p...` and the shipped
rules run `IMPORT{builtin}="kmod"`, resolving the alias against
`modules.alias` and issuing `modprobe` — how plugging a USB-serial
adapter loads `ftdi_sio` before its `tty` node is processed. *Coldplug*
replays this at startup: devices that registered before udevd listened
would be permanently missed, so `systemd-udev-trigger.service` runs
`udevadm trigger` once, synthesizing `add` uevents for every device in
`/sys`. [boot-process.md](./boot-process.md) shows where the trigger sits.

## The Event Pipeline

```text
              kernel driver / hotplug controller
                              |
                              | uevent (netlink, KOBJECT_UEVENT group 2)
                              | ACTION=add DEVPATH=/devices/... SUBSYSTEM=block SEQNUM=N
                              v
              libudev monitor socket in systemd-udevd
                              |
                              | event serialized into the queue (ordered by SEQNUM)
                              v
            worker process pool (bounded by children_max)
                              |
             +----------------+-----------------+
             |                |                 |
      match rule files   IMPORT{builtin}    RUN{program}+=
      (lexical order)    (blkid, kmod...)   (async, short-lived)
             |                |                 |
             v                v                 v
          assignments applied: SYMLINK+= MODE= OWNER= ENV{} TAG=
                              |
                              v
           device database written: /run/udev/data/b8:16
                              |
                              v
          /dev node finalized + /dev/disk/by-uuid/... symlinks
```

Events for one device are serialized; distinct devices may proceed in
parallel in the worker pool. Each processed event leaves a property
database file under `/run/udev/data` (named after node type and numbers,
e.g. `b8:16`), which `udevadm info` reads back. Pool size, timeouts, and
log level are tunable via `/etc/udev/udev.conf` (`children_max=`,
`exec_delay=`, `event_timeout=`) or the kernel command line
(`udev.children_max=`, `udev.event_timeout=`); defaults are sized from
machine resources (heuristic in `systemd-udevd(8)`). udevd runs as
`systemd-udevd.service`, socket-activated by control and kernel sockets,
so early `udevadm` use pulls the daemon in on demand.

## Rule File Locations and Merge Order

Rule files are collected from three trees and treated as one database:

| Directory | Role |
|---|---|
| `/usr/lib/udev/rules.d` | shipped by distribution packages |
| `/run/udev/rules.d` | runtime-generated |
| `/etc/udev/rules.d` | administrator rules; shadows same-named files below it |

The merge rules from `udev(7)`:

1. Only files ending in `.rules` are read; everything else is ignored.
2. All files are sorted **lexicographically by filename across all three
   directories** — the directory matters for shadowing, not ordering.
3. Same filename in several directories: `/etc` wins over `/run`, which
   wins over `/usr/lib`; the shadowed file is skipped entirely. This is
   how package rules are overridden — copy the name, not a new prefix.
4. Within one file, rules run top to bottom; across files, in the lexical
   order above. Later `=` assignments overwrite, `+=` appends.

The two-digit prefix convention makes this order predictable: low numbers
set properties, high numbers make decisions. Administrator rules use `99-`
— unless the rule must *win* an assignment race (`NAME=`), which needs a
lower number than the competing rule.

## Rule Grammar: Match and Assignment Keys

Each line is a comma-separated list of `KEY op VALUE` clauses; a rule
applies only if every match clause succeeds.

### Operators

| Operator | Meaning |
|---|---|
| `==` / `!=` | match equality / inequality |
| `=` | assign a plain value |
| `+=` | append to a list-valued key (`SYMLINK`, `TAG`, `RUN`, `ENV`) |
| `:=` | final assignment — later rules may no longer change this key |

### Match keys

| Key | Matches against |
|---|---|
| `ACTION` | uevent action: `add`, `remove`, `change`, `bind`, `unbind`, `move` |
| `KERNEL` / `KERNELS` | kernel name of the event device / of it or any parent |
| `SUBSYSTEM` / `SUBSYSTEMS` | subsystem of the event device / of it or any parent |
| `DRIVERS` | driver name of the device or any parent |
| `DEVPATH` | sysfs path under `/sys` (glob-friendly) |
| `ATTR{file}` / `ATTRS{file}` | sysfs attribute of the event device / of a parent |
| `ENV{key}` | a property in the udev event database |
| `TEST{mode}` | existence (and optional access mode) of a file |
| `PROGRAM` + `RESULT` | run a helper; match its stdout via `RESULT` in the same rule |

### Assignment keys

| Key | Effect |
|---|---|
| `NAME` | rename the device node; in practice only network interfaces |
| `SYMLINK+=` | append a symlink name (relative to `/dev`) |
| `OWNER=` / `GROUP=` / `MODE=` | node ownership and permissions |
| `ENV{key}=` | set a property; visible to later rules, `udevadm info`, systemd |
| `TAG+=` | add a udev tag — how other subsystems select devices (`TAG+="systemd"`) |
| `ATTR{file}=` | write a value to a sysfs attribute (e.g. `ATTR{power/control}="on"`) |
| `RUN{program}+=` | execute a helper after rule processing — async, must be short-lived |
| `IMPORT{...}` | import key/value output of a program, file, or builtin (`blkid`, `kmod`, `hwdb`, `usb_id`, `input_id`, `path_id`, `net_setup_link`) |
| `OPTIONS+=` | flags: `link_priority=`, `string_escape=`, `db_persist`, `static_node=`, `watch`, `nowatch`, `all_partitions`, `final` |
| `LABEL` / `GOTO` | rule-file internal jumps, like shell `goto` |

### ATTR vs ATTRS, ENV vs ATTR

Two confusions account for most broken rules. First, `ATTR{}` matches an
attribute of the **event device itself**, while `ATTRS{}` walks *up* the
device chain to the nearest parent carrying that attribute. A `tty` device
has no `idVendor`; its USB parent does — so `ATTRS{idVendor}=="0403"`
matches, `ATTR{idVendor}=="0403"` never does. The documented restriction:
all `ATTRS` matches in one rule must resolve to attributes of the *same*
parent device.

Second, `ATTR{}` reads sysfs from disk, while `ENV{}` reads and writes the
in-memory event database built up during this event's rule processing.
Properties from `IMPORT{builtin}="blkid"` (`ID_FS_UUID`, `ID_FS_TYPE`)
land in `ENV` space, not sysfs — matching `ENV{ID_FS_UUID}=="..."` works,
`ATTR{ID_FS_UUID}` never will. The distinction matters for systemd too:
`ENV{SYSTEMD_WANTS}` is read by the device-unit machinery.

## A Real Rule, Dissected

```text
# /etc/udev/rules.d/99-ftdi-gps.rules
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", \
  SYMLINK+="gps0", MODE="0660", OWNER="root", GROUP="dialout", \
  RUN+="/usr/local/bin/gps-hotplug.sh %n"
```

- `SUBSYSTEM=="tty"` — the uevent of interest is the `tty` class node
  (`ttyUSB0`) that the `ftdi_sio` driver registered, not the USB device
  itself, which would match `SUBSYSTEM=="usb"`.
- `ATTRS{idVendor}=="0403"` — the tty device has no such attribute;
  `ATTRS` walks up to the USB device parent. Hex values are lowercase and
  the comparison is a plain string match against the sysfs file content.
- `ATTRS{idProduct}=="6001"` — same parent; per the single-parent
  restriction, both `ATTRS` matches must land on the same node.
- The trailing `\` continues the rule onto the next line — one rule per
  logical line, however it is wrapped.
- `SYMLINK+="gps0"` — creates `/dev/gps0` pointing at `/dev/ttyUSB0`;
  `+=` because several rules may contribute symlinks to one device.
- `MODE=`, `OWNER=`, `GROUP=` — node permissions; combined with `dialout`
  membership this beats a global `chmod 666`.
- `RUN+="/usr/local/bin/gps-hotplug.sh %n"` — `%n` is the kernel number
  (`0` in `ttyUSB0`). The script runs after this event finishes
  processing, in parallel with other events, and must exit in seconds.

## udevadm: The Operator Interface

```bash
udevadm info --query=property --name=/dev/sdb        # final property set
udevadm info --attribute-walk --name=/dev/ttyUSB0    # the ATTRS chain
udevadm info --export-db                             # whole /run/udev db
udevadm trigger --subsystem-match=tty --action=add   # replay uevents
udevadm settle --timeout=10                          # wait for queue drain
udevadm control --reload                             # re-read rule files
udevadm monitor --kernel --udev --property           # raw + processed view
udevadm test "$(udevadm info --query=path --name=/dev/sdb)"  # dry run
```

Daily workflow when writing rules: `info --attribute-walk` to find
matchable attributes (the indentation shows the parent chain — the tool
that answers "ATTR or ATTRS?"), then `udevadm test <devpath>` to simulate
one event without replugging, then `control --reload` plus `trigger` to
apply to existing devices. `monitor --property` shows raw and post-rules
events; `settle` blocks until the queue drains.

## Persistent Names: /dev/disk and Predictable Interfaces

### /dev/disk/by-uuid, by-label, by-id, by-path

The shipped `60-persistent-storage.rules` runs the `blkid` builtin on
every block device and exports what it finds:

| Directory | Key source | Stability |
|---|---|---|
| `/dev/disk/by-uuid` | filesystem UUID (`ENV{ID_FS_UUID}`) | highest — survives any re-plug |
| `/dev/disk/by-label` | filesystem label | high; collisions possible |
| `/dev/disk/by-id` | serial/model/WWN (`ID_SERIAL`, `ID_WWN`) | high; shifts if controller type changes |
| `/dev/disk/by-path` | physical path (`path_id`: PCI slot + port) | reflects *where* it is plugged |

This is why `/etc/fstab` entries should reference `UUID=` — the symlink
comes from hardware identity, not enumeration order; mount units resolve
through it (see [boot-process.md](./boot-process.md)).

### Predictable network interface names

udevd also renames network interfaces (the one case where `NAME=` still
applies routinely), driven by the `net_setup_link` builtin and `.link`
files (see [networkd-resolved.md](./networkd-resolved.md)). The scheme,
with common decompositions:

| Name | Decomposition |
|---|---|
| `eno1` | embedded NIC, onboard index 1 |
| `ens33` | PCI hotplug slot 33 |
| `enp0s3` | PCI bus 0, slot 3, function 0 |
| `wlp2s0` | wireless, PCI bus 2, slot 0 |
| `enx001122334455` | by MAC address (fallback) |

Prefixes: `en`=ethernet, `wl`=wlan, `ww`=wwan; names derive from hardware
topology rather than probe order, so `eth0` cannot swap with `eth1` across
boots. To revert: kernel command line `net.ifnames=0` plus
`biosdevname=0`, or a `.link` file with `NamePolicy=` — masking the
shipped `/usr/lib/systemd/network/99-default.link` with a `/dev/null`
symlink in `/etc/systemd/network` also works.

## systemd Integration: Device Units and Device-Triggered Services

systemd synthesizes a `.device` unit from every uevent (see
[unit-types.md](./unit-types.md)); unit names encode the sysfs path. By
default these units are inert; the shipped `99-systemd.rules` adds
`TAG+="systemd"` to devices, and only tagged devices get pulled into the
boot graph (`sysinit.target`) and can carry dependencies. Administrator
rules then attach *wants*:

```text
# /etc/udev/rules.d/99-backup.rules
ACTION=="add", SUBSYSTEM=="block", KERNEL=="sdb1", TAG+="systemd", \
  ENV{SYSTEMD_WANTS}="disk-backup@%k.service"
```

When `/dev/sdb1` appears, systemd starts `disk-backup@sdb1.service` as a
dependency of the device unit — a device-triggered start, no polling
daemon required. Device units vanish when hardware goes away, so anything
bound to them stops; unit-side dependencies reference `*.device` names
directly (see [dependency-management.md](./dependency-management.md)), and
`systemd.device(5)` documents `SYSTEMD_ALIAS=`/`SYSTEMD_READY=`.

## udev in the Initramfs

Early userspace needs udevd before the root filesystem exists: the root
device may sit behind a USB controller, dm-crypt, or an NVMe driver that
must be autoloaded. Initramfs generators (dracut, mkinitcpio) ship a
private udevd copy plus a trimmed rule set, run `udevadm trigger` while
hunting for the root device, and the `/run/udev` state survives
`switch_root` into the main system.

## Common Mistakes and Troubleshooting

- **Rules edited but nothing changed.** Rule files are read into memory;
  apply with `udevadm control --reload`, then re-process with
  `udevadm trigger --action=add --subsystem-match=...` (or replug).
- **ATTR vs ATTRS, case sensitivity.** Matching a USB attribute with
  plain `ATTR` never fires on tty/block devices (use `ATTRS`); hex
  values like `idVendor=="0403"` are lowercase in sysfs, and
  `udevadm test` catches both classes of bug.
- **Matching properties that do not exist yet.** `ENV{ID_FS_UUID}` is
  only present *after* the `blkid` builtin ran in
  `60-persistent-storage.rules`; a rule at `50-` matching it never fires.
  Move to a higher prefix.
- **Filename ordering mistakes.** A `10-local.rules` assigning `NAME=`
  can be overridden by distro rules sorted later; `+=` accumulates, `=`
  overwrites. Decide per key whether to run early or late.
- **Blocking `RUN{}`.** Scripts that sleep, mount, or wait on a device
  occupy a worker and stall the queue. Move long work into a systemd
  unit triggered by `ENV{SYSTEMD_WANTS}`; keep `RUN` for logging and
  quick setup. Never call `udevadm settle` inside `RUN` — that
  deadlocks the queue against itself.

## Interview Questions

### Q: What is the difference between udev and busybox mdev, and when does mdev suffice?

mdev is a single-purpose tool: match sysfs entries against
`/etc/mdev.conf` regexes, set owner/mode, make symlinks, optionally run a
helper — either by scanning `/sys` once or handling uevents. udevd is a
rule database with a full match/assignment language, worker pools, a
property database, builtins (blkid, kmod, hwdb), predictable naming, and
libudev consumers. mdev suffices for a fixed, small device set (initramfs,
single-purpose boards); general-purpose distros need the full rule engine.

### Q: Why must RUN{program} handlers exit quickly? What breaks otherwise?

`RUN` programs execute inside udev event workers; the worker is not
finished until the program exits, and events for other devices can
exhaust the bounded worker pool (`children_max`) if several handlers
block — visible symptoms are `udevadm settle` hangs and delayed hotplug.
Long-running work (mounting, networking, backups) belongs in a systemd
service triggered via `ENV{SYSTEMD_WANTS}`.

### Q: Walk through how a USB stick gets its /dev/disk/by-uuid entry.

The kernel enumerates the device and emits uevents for the whole chain
(usb device, scsi disk, partitions). For the block partitions udevd runs
rules in lexical order; `60-persistent-storage.rules` matches
`SUBSYSTEM=="block"` and executes `IMPORT{builtin}="blkid"`, which probes
the filesystem and exports `ID_FS_UUID` into the event property set. A
later rule in the same file matches `ENV{ID_FS_UUID}` and adds
`SYMLINK+="disk/by-uuid/<uuid>"`; the processed event is written to
`/run/udev/data/b8:17` and the symlink is created. Uevent → blkid →
symlink assignment is the whole story; nothing scans `/dev` afterwards.

### Q: What exactly happens on a system without udevd?

devtmpfs still provides every node for every loaded driver, so a
statically-configured system can boot and run. What is lost: module
autoloading from `MODALIAS`, `/dev/disk/by-*` symlinks (fstab by-UUID
entries fail), permission and group policy on nodes, predictable network
names, and the property database systemd consumes — device units become
bare and `SYSTEMD_WANTS` never fires. That is why even minimal distros
run *some* hotplug agent; they only argue about which one.

## References

- https://www.freedesktop.org/software/systemd/man/latest/udev.html
- https://www.freedesktop.org/software/systemd/man/latest/udevadm.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd-udevd.service.html
- https://manpages.debian.org/bookworm/udev/udev.7.en.html
- https://manpages.debian.org/bookworm/udev/udevadm.8.en.html
- https://manpages.debian.org/bookworm/udev/systemd-udevd.8.en.html

## Cross-References

- [boot-process.md](./boot-process.md) — where udev-trigger coldplug and udevd startup sit in the boot graph.
- [networkd-resolved.md](./networkd-resolved.md) — `.link` files, `net_setup_link`, and predictable interface naming.
- [unit-types.md](./unit-types.md) — the `.device` unit type synthesized from uevents.
- [dependency-management.md](./dependency-management.md) — how `SYSTEMD_WANTS` and device units become real dependencies.
- [udev.md](../../admin/udev.md) — operator-level udev notes and day-to-day recipes.
- [devtmpfs.md](../../kernel/filesystems/devtmpfs.md) — the kernel-side node filesystem udev layers policy onto.
- [busybox.md](../../binaries/busybox.md) — busybox mdev, the embedded alternative to udevd.
- [README.md](../README.md) — init-systems section hub.
- [comparison.md](../comparison.md) — device management compared across init families.
