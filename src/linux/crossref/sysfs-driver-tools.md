# sysfs class -> driver model -> tools (XR-101..XR-114)

## Overview

This map runs the other direction from the [libc map](./libc-syscall-kernel.md):
it starts at a **sysfs class** the kernel publishes, names the **subsystem core**
that creates it (with the config gate), explains the **driver-model
relationship** (what registers the device, what the class directory inherits),
lists the **userspace consumers and how exactly they touch the class**, and
records the **/dev and /proc cross-refs** that duplicate or complement the
view. The rows are `XR-101..XR-114` of the [coverage ledger](./ledger.md)
(statuses authoritative there: 13 documented, 1 source-limited; the 7-d pass
upgraded XR-102, XR-106, XR-107, XR-110, XR-111, XR-113 and XR-114).

Sources and honesty rules for this page: attribute contracts come from the
kernel `Documentation/ABI/` tree; tool behavior comes from the tools' own
documentation (util-linux man pages, systemd man pages, project READMEs) or
source named per row; live observations are stamped **live@5.10.134** (the
container host this encyclopedia was built on; populations differ elsewhere and
prove nothing about other kernels). Where a consumer claim could not be
sourced, the row is **source-limited** and names the missing source instead of
asserting. Class IDs cite the [sysfs ledger](../sysfs/ledger.md); per-class
pages under [classes/](../sysfs/overview.md) carry the full attribute tables.

### How the rows were sourced

- **Kernel contracts**: the `Documentation/ABI/` tree grepped per class for
  `What:` entries (counts quoted per row: block 76 + block-device 8, bdi 10,
  net 31 + queues 14 + statistics 24, tty 17, nvme 66, hwmon 119, thermal 27,
  power 59, backlight 5 core, led 5 core, pwm 11, regulator 33, drm 1,
  devlink 7, bus-dax 18, infiniband 130, devices-system-cpu 19, module 5,
  plus the obsolete gpio tree and sysfs-fs-xfs).
- **Subsystem code**: the class-registration and attribute blocks named per
  row (`genhd.c`, `blk-sysfs.c`, `net-sysfs.c`, `tty_io.c`, `nvme/core.c`,
  `backing-dev.c`, `arch/x86/kernel/{msr,cpuid}.c`, ...), with config gates
  traced through Makefiles/Kconfig.
- **Tools**: the tool's own documentation or source (util-linux man pages,
  systemd man pages, iproute2, nvme-cli/libnvme, ndctl, lm-sensors,
  brightnessctl, libgpiod, thermal daemon) -- never assumed from the name;
  upstream tool documentation fetched for the 7-d pass (NetworkManager(8),
  thermald(8), the UPower reference manual, the libinput docs, drm(7)/libdrm
  man pages, rdma-core and ndctl READMEs, cpuid(1), msr(4), sysctl(8),
  dmidecode(8)).
- **Live snapshot**: `live@5.10.134` class populations, attribute listings,
  topology symlinks, and uevent payloads, read read-only; nothing was written
  to `/sys` during research.

### Reading rules

- `wraps` is not used here; the arrow vocabulary for tools is: **reads**
  (consumes attributes/uevents), **writes** (sets attributes or `ATTR` files),
  **bypasses** (uses netlink/ioctl/char-dev instead of sysfs), **gated-by**
  (config, boot param, or udev rule). Kernel-side arrows keep the encyclopedia
  vocabulary (`services`, `implements`, `consumes`).
- The **/dev, /proc cross-refs** column exists because sysfs is rarely the only
  view: most class devices have a char/block node (created from the uevent's
  `DEVNAME`), a `/proc` twin with a different shape (`/proc/partitions` vs
  `/sys/class/block`), or a sibling class (`vc` for `tty`). Where the live
  host had the class but not the node, the row says so -- that split is real
  on minimal/container systems, not a measurement error.
- Consumers are described by **HOW**, not by name-dropping: a tool that reads
  sysfs, one that writes an attribute, and one that bypasses via netlink or a
  char device are three different integration contracts, and the row records
  which one each tool uses, with the source named.
- Class populations quoted as "live N" are the 5.10.134 container host
  snapshot, not ABI promises.
- Non-1:1 is the point: udev is a consumer *and* a writer; several tools
  deliberately do **not** use sysfs (ip/ethtool use netlink, libgpiod uses the
  gpio char device); /proc and /dev twins exist for most rows.

---

### XR-101 -- /sys/class/block + bdi -> block core -> genhd/blk-sysfs -> lsblk, blockdev

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-block` (`/sys/class/block`, live 4: vda, pmem0, pmem0p1, zram0), `SYSC-bdi` (live 9) | block core: `block/genhd.c` (`block_class`, disk attrs), `block/blk-sysfs.c` (queue attrs), `block/partitions/core.c`; bdi: `mm/backing-dev.c` (`bdi_class`); `CONFIG_BLOCK` (default y) | disks/partitions register under `block_class`; the legacy `/sys/block` kobject survives as a symlink view; each disk links to its `bdi/<maj:min>` owner; queue attributes hang off the request queue | **lsblk**(8) walks `/sys/class/block` + device topology to build the tree (util-linux); **blockdev**(8) issues block-device ioctls (`--flushbufs`, `--setro`), so it bypasses sysfs for action and reads sysfs for state; **zramctl**(8) reports zram devices from their block attributes (util-linux source checked); udev imports uevent data and creates the node | `/dev/vda` node from the `block` uevent (`DEVNAME`/`DEVTYPE` payload, live@5.10.134); `/proc/partitions` lists the same disks; `/sys/dev/block/254:0` backlink verified |

ABI documentation: `stable/sysfs-block` (76 `What:` entries) plus
`testing/sysfs-block-device` (8); `testing/sysfs-class-bdi` (10). Live
interesting values: `vda/queue/rotational=1` vs `pmem0/rotational=0`;
`scheduler` reads `[mq-deadline] kyber bfq none` (the brackets are in the file
bytes, tool output strips them). Two honest gaps from the live pass: the
multipath-tools README documents its libudev-based walk of these directories
(a second consumer reading via udev's device database), and the `bdi` class's
six anonymous `0:N` directories on this host could not be traced to a named
registrant in the fetched sources -- the class page states the gap instead of
guessing. Topology is visible from this class too: on the live host `vda`
linked to its virtio controller while `pmem0` linked through an ndbus region
to a different parent -- which is how lsblk can show bus ancestry without any
block-specific tooling. Per-class pages:
[block](../sysfs/classes/block.md), [bdi](../sysfs/classes/bdi.md); kernel
side: [block devices](../kernel/block/devices.md).

### XR-102 -- /sys/class/net -> net core -> net-sysfs -> ip, ethtool, NetworkManager

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-net` (live 3: lo, eth0, dummy0) | net core: `net/core/net-sysfs.c` (`net_class_attrs[]`, per-queue and statistics groups); `CONFIG_NET` | netdev registered under `net_class`; `eth0/device` symlinks to the parent PCI/virtio device (live: `->virtio1`); statistics files mirror driver counters | **ip**(8) (iproute2) reads and *changes* state over **rtnetlink**, not sysfs -- sysfs is read-only observability here; **ethtool** speaks **ethtool netlink** (genetlink) per `ethtool-netlink.rst`; udev renames interfaces using the `INTERFACE`/`IFINDEX` uevent payload; **NetworkManager**(8) manages Ethernet/Wi-Fi/mobile-broadband devices, discovers them via **udev**(7) (the `NM_UNMANAGED` and `ID_NET_MANAGED_BY` udev properties gate manageability) and exports state over D-Bus (NetworkManager(8), trixie 1.52.1) | `/proc/net/dev` duplicates counters; `/proc/sys/net/` is the sysctl twin for tunables; no /dev node exists for netdevs |

The NetworkManager consumer claim upgraded in the 7-d pass: the fetched
NetworkManager(8) (Debian trixie 1.52.1) states that the daemon manages "the
primary network connection and other network interfaces, like Ethernet,
Wi-Fi, and Mobile Broadband devices" and "will connect any network device
when a connection for that device becomes available", that "udev(7) device
manager is used for the network device discovery", and names the udev
properties that steer management (`NM_UNMANAGED`, `ID_NET_MANAGED_BY`,
`ID_NET_AUTO_LINK_LOCAL_ONLY`, `ID_NET_DHCP_BROADCAST`) plus the D-Bus export
of network state. The page therefore documents NM's integration at the
udev/netlink/D-Bus layer and makes no direct-sysfs-read claim for it. ABI:
`testing/sysfs-class-net` (31),
`-queues` (14), `-statistics` (24). Live quirk: `eth0/speed` reads `-1` and `lo`
returns `EINVAL` for speed. The live pass also separated ABI-documented from
live-only attributes: `gro_flush_timeout`, `napi_defer_hard_irqs`, `proto_down`
and `traffic_class` exist in the source but predate their ABI entries, and
`threaded` (5.12) is correctly absent on this 5.10 host. The statistics
directory carried exactly the 24 ABI-named files. Pages:
[net](../sysfs/classes/net.md); kernel
side: [netdev](../kernel/networking/netdev.md), [netlink](../kernel/networking/netlink.md).

### XR-103 -- /sys/class/tty -> tty core -> tty_io -> stty, agetty, udev

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-tty` (live 70: console, ptmx, tty, ttyprintk, tty0-63, ttyS0-1) | tty core: `drivers/tty/tty_io.c` (`tty_class`); serial attrs from `serial_core.c` (`tty_dev_attrs[]`); `CONFIG_TTY` | each tty device registers under `tty_class` with its driver; `console/active` names the active console device (live: `ttyS1`); device numbers visible in uevents (`MAJOR=4`) | **stty**(1) sets line discipline via **termios ioctls** (`TCGETS`/`TCSETS`), bypassing sysfs; **agetty**(8) inspects tty attributes and then works on the char device; **udev** consumes the tty uevent and creates `/dev/ttyN`, `/dev/ttyS0` nodes | `/dev/tty*` nodes (live `console` 5:1, `tty` 5:0, `ptmx` 5:2); `/sys/class/vc` (vcs devices, dev 7:0) is the screen-content twin class; no /proc twin beyond `/proc/tty` |

ABI: `testing/sysfs-tty` (17 entries). Live serial facts: `ttyS0/uartclk=1843200`,
`type=4` (= `PORT_16550A` per `include/uapi/linux/serial.h`); `console/active`
reads `ttyS1` on this host while `tty0/active` reads `tty1` -- the attr names
the current backend of that device. The interesting
split: sysfs tty attributes are driver-provided metadata; line settings live in
the termios interface that stty drives, and the serial-driver group
(`TIOCGSERIAL`-family ioctls) is documented as a separate attr group. Note the
devnode contract: the tty class is one of the few where the uevent `MAJOR`
(4) maps to the classic `/dev/ttyN` naming without udev rules doing anything
clever. The screen-content twin class `SYSC-vc` (vcs/vcsa/vcsu families, dev
7:0/7:64/7:128 live) is documented alongside because agetty-class tools and
screenshot tools read it for the same ttys. Pages:
[tty](../sysfs/classes/tty.md); the libc/ioctl side of termios is mapped in
XR-013 of the [libc map](./libc-syscall-kernel.md).

### XR-104 -- /sys/class/nvme -> nvme host core -> nvme-cli, libnvme

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-nvme` (live 0 entries on this host -- no NVMe device), `SYSC-nvme-subsystem` (researched row) | nvme host: `drivers/nvme/host/core.c` (`nvme_class`), `sysfs.c` (device + subsystem attrs, fabrics-gated via `are_visible`); `CONFIG_NVME_CORE` | controllers, subsystems and namespaces appear as class devices; namespace attributes are mirrored under the block device (XR-101); the class directory is empty without hardware | **nvme-cli** uses libnvme: `tree.c`/`filters.c` **scan `/sys/class/nvme`** to build the controller/namespace topology, then issue admin/IO commands through `/dev/nvmeN` **ioctl**s (`ioctl.c`, `NVME_IOCTL_*`); so nvme-cli reads sysfs and acts via ioctl | `/dev/nvme0`, `/dev/nvme0n1` char/block nodes; `/sys/class/block/nvme0n1` twin (XR-101); no /proc twin of substance |

ABI: `stable/sysfs-nvme` (66 `What:` entries, 39 class-level per the ledger).
Honesty note: this host has no NVMe device, so **no live attribute was
verified** -- the entry is ABI + source only by design. Source detail worth
keeping: the subsystem class (`SYSC-nvme-subsystem`, 6 attrs) hangs below the
controller class with its own attribute set, and the fabrics-gated attributes
are visibility-filtered per transport, so a tool scanning the class must
handle absent attrs gracefully -- which is exactly what libnvme's filter code
does. Pages:
[nvme](../sysfs/classes/nvme.md), kernel side: [nvme driver](../kernel/drivers/nvme.md).

### XR-105 -- /sys/class/hwmon -> hwmon core -> sensors (lm-sensors)

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-hwmon` (live 0 entries) | hwmon core: `drivers/hwmon/hwmon.o` (`CONFIG_HWMON`); chip drivers attach attribute groups | each chip driver creates one `hwmonN` device with in_/temp_/fan_/power_ attribute groups named by ABI contract; names come from chip drivers | **sensors**(1) (lm-sensors): the lm-sensors README states it reads sysfs; libsensors roots its scan at `SENSORS_SYSFS_ROOT` (`/sys/class/hwmon`), maps chip labels and exposes named readings | no /dev node; `/proc` has no hwmon twin (older drivers kept legacy `/proc` paths, not covered by ABI docs) |

ABI: `testing/sysfs-class-hwmon` (119 `What:` entries; a full-tree recount
finds 120 including one driver-specific file -- both figures are stated on the
class page). The class being empty live on
this container host is the config-vs-population gate in action: `CONFIG_HWMON`
may be on, but no chip driver matched hardware. The attribute naming contract
is the reason libsensors can be generic: every chip driver maps its readings
onto the same `inN_input` / `tempN_input` / `fanN_input` shapes, so the tool
needs no per-chip knowledge to list them. Page:
[hwmon](../sysfs/classes/hwmon.md).

### XR-106 -- /sys/class/thermal -> thermal core -> thermald

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-thermal` (live 0 entries) plus the cooling-device directory `/sys/class/thermal_cooling` (no ledger row of its own) | thermal core: `thermal_sys.o` (`CONFIG_THERMAL`); zones, cooling devices and governor choices exposed as attributes | thermal zone devices register with the core; governor + policy attributes select behavior; cooling devices link to consumers (cpufreq, etc.) | **thermald**(8) (Intel thermal daemon): per thermald(8) (trixie 2.5.9), it "looks for thermal sensors and thermal cooling drivers in the Linux thermal sysfs (/sys/class/thermal) and builds a list of sensors and cooling drivers", binds sensors to cooling drivers and works from trip points, with `thermal-conf.xml` as the user override | no /dev node; `/proc` twin absent; trip points pair with hwmon readings (XR-105) |

ABI: `testing/sysfs-class-thermal` (27 entries, no per-entry Date/KernelVersion
lines -- the ABI file is older-style, which is why the class page carries no
since dates). The thermal story spans three sysfs views: this class (zones),
the cooling-device directory `/sys/class/thermal_cooling` (outside the
class ledger's seeded rows), and the hwmon mirror some drivers
register (XR-105); a tool that only reads one of them sees half the picture.
Kernel side: [thermal](../kernel/drivers/thermal.md); class page:
[thermal](../sysfs/classes/thermal.md). The thermald consumer claim
upgraded in the 7-d pass: the fetched thermald(8) man page states the sysfs
scan verbatim (the row's former missing source was per-file usage evidence).

### XR-107 -- /sys/class/power_supply -> power supply core -> UPower

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-power_supply` (live 0 entries) | power supply core: `power_supply.o` (`CONFIG_POWER_SUPPLY`); battery/AC/UPS class devices with type, capacity, status attributes | each registered supply creates one class device; properties are driver-populated; changes can trigger uevents | **UPower**: the standard desktop battery stack; the UPower reference manual (upower.freedesktop.org, v1.91.2) documents each device's `NativePath` property as the "OS specific native path of the power source. On Linux this is the sysfs path" with the example `/sys/devices/LNXSYSTM:00/device:00/PNP0C0A:00/power_supply/BAT0`, and marks `VoltageMinDesign`/`VoltageMaxDesign` "as reported by the kernel"; UPower(7) frames the daemon as the interface to "enumerate power sources on the system" over `org.freedesktop.UPower` | no /dev node; `/proc` twin absent; `/sys/class/leds` charge-status LEDs are the visual sibling (XR-108) |

ABI: `testing/sysfs-class-power` (59 core `What:` entries; 82 documented paths
ledger-wide including driver ABI files; the earliest per-entry KernelVersion
lines date to 2.6.35). The class models everything with a charge state --
batteries, AC adapters, UPSes -- with `type` selecting which properties apply,
which is what makes generic desktop consumers possible. The UPower consumer
claim upgraded in the 7-d pass: the fetched reference manual gives the
concrete class-to-daemon linkage (NativePath = the sysfs power_supply path,
kernel-reported properties) and UPower(7) names the enumeration contract.
Pages:
[power_supply](../sysfs/classes/power_supply.md).

### XR-108 -- /sys/class/leds + backlight -> leds/backlight cores -> brightnessctl, systemd-backlight

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-leds` (live 0), `SYSC-backlight` (live 0) | leds core: `led-class.o` (`CONFIG_LEDS_CLASS`); backlight core: `backlight.o` (`CONFIG_BACKLIGHT_CLASS_DEVICE`) | LED devices expose `brightness`/`max_brightness` (+ triggers); backlight devices expose `bl_power`, `brightness`, `actual_brightness`, `max_brightness`, `type` (the 5 stable ABI attrs) | **brightnessctl** writes `brightness` (README-sourced; scales against `max_brightness`); **systemd-backlight@.service** saves the brightness at shutdown and restores it via a **udev ATTR write** at plug time (systemd man page); udev itself is a *writer* here | no /dev node; `/proc` twin absent; contrast with DRM connectors (XR-111) which own display brightness on modern GPUs |

ABI: `stable/sysfs-class-backlight` (5 core attrs; 16 `What:` lines across the
ABI tree vs the ledger's 15 -- both figures recorded on the class page) and
`testing/sysfs-class-led` (5 core; 96 tree-wide including
flash/multicolor/trigger files). This row is the cleanest **write-path**
example: normal users change one attribute file and the kernel translates it
into driver calls; the tool surface is deliberately thin (brightnessctl is a
few hundred lines around read-scale-write). The systemd restore flow is the
second write-path pattern worth knowing: state is persisted per device at
shutdown and replayed by a udev rule when the device reappears, which works
because the attribute exists from device registration on. Pages:
[leds](../sysfs/classes/leds.md),
[backlight](../sysfs/classes/backlight.md).

### XR-109 -- /sys/class/{gpio,pwm,regulator,i2c-adapter} -> subsystem cores -> libgpiod, i2c-tools

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-gpio` (deprecated ABI), `SYSC-pwm` (ABI 11), `SYSC-regulator` (ABI 33), `SYSC-i2c-adapter` (live present; 3 non-ABI attrs) | gpiolib `gpiolib-sysfs.o` (`CONFIG_GPIO_SYSFS`); pwm core (`CONFIG_PWM`); regulator core (`CONFIG_REGULATOR`); i2c core (`CONFIG_I2C`) + `i2c-dev.o` (`CONFIG_I2C_CHARDEV`) | gpio's sysfs ABI is **obsolete** (the ABI file itself says the sysfs interface was removed after 2020); pwm/regulator expose per-device control attributes; i2c-adapter exposes `name`, `new_device`, `delete_device` | **libgpiod bypasses sysfs entirely**: it uses the `/dev/gpiochipN` **char device** (gpio-cdev ABI since 4.4); **i2cdetect** and friends use `/dev/i2c-N` **ioctl**s (`Documentation/i2c/dev-interface.rst`); `new_device`/`delete_device` are the classic write-to-sysfs instantiation path | `/dev/gpiochipN` (the modern path), `/dev/i2c-N`; `/sys/kernel/debug/gpio` is the debugfs sibling (not ABI) |

This row is the map's clearest **bypass** story: the tools moved to char
devices while the class dirs remain for compatibility and for the i2c
instantiate/remove convenience. The gpio ABI file itself says the sysfs
interface was to be removed after 2020 (the `chipX` tree it documents lives in
the `obsolete/` directory), and the cdev ABI (`testing/gpio-cdev`, since 4.4)
is what libgpiod's README points at. Regulators remain a genuine sysfs write
surface (constraints/state attrs), and pwm exposes per-channel export/enable/
duty-cycle attrs. Pages: [gpio](../sysfs/classes/gpio.md),
[pwm](../sysfs/classes/pwm.md), [regulator](../sysfs/classes/regulator.md),
[i2c-adapter](../sysfs/classes/i2c-adapter.md); kernel side:
[gpio](../kernel/drivers/gpio.md), [regulator](../kernel/drivers/regulator.md),
[i2c/spi](../kernel/drivers/i2c-spi.md).

### XR-110 -- /sys/class/input -> input core -> libinput/evdev

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-input` (live 2 entries) | input core: `drivers/input/input.c` (attr groups: `name`, `phys`, `uniq`, `modalias`, `properties`, `id/*`, `capabilities/*`); evdev (`drivers/input/evdev.c`, `event%d` devices) | each input device registers with the core, which creates the class device and an evdev char device; udev's `input_id` builtin computes capability-based properties (`ID_INPUT_*`) from the sysfs `capabilities/*` files | **libinput**: per the libinput 1.31.0 docs, devices are recognized and typed via **udev properties**: `ID_INPUT` must be set (devices without it are ignored) and `ID_INPUT_KEYBOARD`/`ID_INPUT_KEY`/`ID_INPUT_MOUSE`/`ID_INPUT_TOUCHPAD`/`ID_INPUT_TOUCHSCREEN`/`ID_INPUT_TABLET`/`ID_INPUT_JOYSTICK`/`ID_INPUT_ACCELEROMETER` select the initialized device type; configuration rides `LIBINPUT_CALIBRATION_MATRIX`, `LIBINPUT_IGNORE_DEVICE` and `ID_SEAT`; libinput itself is "a full input stack for display servers and other applications that need to handle input devices provided by the kernel", reading the evdev event nodes; udev's `input_id` builtin computes the `ID_INPUT_*` properties from the sysfs `capabilities/*` files (systemd source) | `/dev/input/eventN` (evdev) and `/dev/input/mice`; on the live host `/dev/input` was **absent** while class entries existed -- a devnode-vs-sysfs split observed, not a rule |

ABI: no class-level ABI file (only driver-specific ones); claims above trace
to named kernel sources. The capability tree is the interesting part:
`capabilities/ev`-style bitmaps are what udev's `input_id` builtin parses to
set `ID_INPUT_KEYBOARD`/`ID_INPUT_MOUSE`-class properties, which downstream
devices rules then match on -- the sysfs files are the raw material for the
event-device classification. The libinput consumer claim upgraded in the
7-d pass: the fetched libinput documentation (wayland.freedesktop.org,
1.31.0, device-configuration-via-udev) documents the udev-property contract
verbatim, closing the row's former gap. Page:
[input](../sysfs/classes/input.md).

### XR-111 -- /sys/class/drm + graphics -> DRM core -> libdrm/compositors

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-drm` (live: version-only, `drm 1.1.0 20060810`), `SYSC-graphics` (live: fbcon) | DRM core: `drivers/gpu/drm/drm_sysfs.c` (`card%d`, `renderD%d`, devnode `dri/`); fbdev: `fb_class` (`graphics`, `fb%d`, FB_MAJOR 29) | DRM registers render/card devices under `drm`; the legacy fbdev layer separately registers framebuffers under `graphics`; `boot_display` is the class's single ABI entry | **libdrm/compositors**: per drm(7) (libdrm 2.4.124 man pages), "All these interfaces are based on ioctl(2) commands on the DRM character device. The libdrm library provides wrappers for these system-calls and many helpers", and "Each connected GPU is then presented to user-space via a character-device that is usually available as /dev/dri/card0"; mode-setting (KMS) is restricted to the current DRM master (`drmSetMaster(3)`), and `drmModeGetResources(3)` exposes the crtcs/encoders/connectors/fbs topology compositors drive; `drmAvailable(3)` probes for a loaded DRM driver | `/dev/dri/cardN`, `/dev/dri/renderD N`; on the live host `/dev/dri` was absent while the class existed; fbcon live attrs `rotate`, `cursor_blink` |

ABI: `testing/sysfs-class-drm` (1 entry: `boot_display`). The live snapshot
makes the split concrete: the drm class carried only its version attribute,
while the fbdev layer under `graphics` carried the live framebuffer console
(`fbcon`, with `rotate`, `cursor_blink` and write-only `rotate_all`). On
machines with real GPUs the card/render device directories are where
connector and client state lives, which is the part drm(7) now documents:
the libdrm wrappers over the DRM character-device ioctls (7-d pass fetch;
the gitlab.freedesktop.org repo itself stayed unreachable behind an
anti-bot wall, so the Debian-shipped libdrm man pages are the citation).
Pages:
[drm](../sysfs/classes/drm.md), [graphics](../sysfs/classes/graphics.md).

### XR-112 -- /sys/class/{msr,cpuid} -> x86 arch code -> msr-tools (source-limited)

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-msr` (live 2: msr0, msr1 at 202:0/202:1), `SYSC-cpuid` (live 2: 203:0/203:1) | `arch/x86/kernel/msr.c` (`msr%d`, `allow_writes` module param, 0600), `arch/x86/kernel/cpuid.c` (`cpu/%u/cpuid`); `CONFIG_X86_MSR` / `CONFIG_X86_CPUID` | one class device per CPU; these classes exist to anchor the **char devices**; x86-only by construction | **rdmsr/wrmsr (msr-tools)**: still **unsourced** -- the msr-tools documentation is not reachable (kernel.org gitweb serves an anti-bot page; Debian and Ubuntu ship no rdmsr/wrmsr man pages), so tool-level claims stay **not asserted** (the row's named missing source); sourced in the 7-d pass: `msr(4)` documents the device contract (`/dev/cpu/CPUNUM/msr`: seek to the MSR number as offset, read/write in 8-byte chunks, root-only, `modprobe msr` since the driver is not auto-loaded) and `cpuid(1)` documents its `--kernel` option ("Use the CPUID kernel module", typically root) versus the default `--inst` CPUID-instruction mode | `/dev/cpu/N/msr`, `/dev/cpu/N/cpuid` -- both **absent** on the live host while the class dirs existed; writes to msr additionally gated by the `allow_writes` param |

No class ABI file exists for either class; all claims trace to the named arch
sources. The safety story is unusually sharp here: msr writes can boot-loop or
worse a machine, which is why the driver added the `allow_writes` parameter
(`on`/`off`/`default`) gating writes on the char device -- a layering where
the class directory is inert and all the policy sits on the /dev side. Pages:
[msr](../sysfs/classes/msr.md), [cpuid](../sysfs/classes/cpuid.md),
[mem/misc context](../sysfs/classes/mem.md). The 7-d fetch pass narrowed the
gap without closing it: msr(4) and cpuid(1) are now cited above, but the
msr-tools rdmsr/wrmsr documentation remains unfetched, so the tool-to-device
linkage is still unasserted.

### XR-113 -- /sys/class/infiniband + devlink + dax -> RDMA/devlink/dax cores -> rdma, ndctl

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| `SYSC-infiniband` (ABI 130 `What:` entries), `SYSC-devlink` (ABI 7), `SYSC-nd` (live 1: ndctl0, char 253:0 via `register_chrdev(0, "ndctl")`) | infiniband core (`drivers/infiniband/core/`); devlink class in `drivers/base/core.c` with the **devlink netlink family** in `net/devlink/core.c` (name collision, two different things); nvdimm/dax bus (`sysfs-bus-dax`, 18 entries) | IB devices expose ports, counters and MAD/verbs char devices; devlink class devices (`<bus>:<dev>--<bus>:<dev>` links) are device-pair metadata; nd exposes nvdimm regions/buses for libndctl | **ndctl** reads `/sys/class/nd` via `libndctl.c` (sourced); the ndctl README calls the project the "Utility library for managing the libnvdimm (non-volatile memory device) sub-system in the Linux kernel"; **rdma-core** README (official repo): "the userspace components for the Linux Kernel's drivers/infiniband subsystem", naming the library-per-device-node mapping -- `/dev/infiniband/uverbsX` (libibverbs), `/dev/infiniband/rdma_cm` (librdmacm), `/dev/infiniband/umadX` (libibumad) -- plus per-driver provider libraries and the srp_daemon/iwpmd/ibacm daemons; rdma(8) usage stays tool-doc sourced | `/dev/infiniband/uverbsN`, `/dev/infiniband/ucmN`; `/dev/ndctlN` (live: ndctl0); devlink's real control channel is **netlink**, not its class dir |

Pages: [infiniband](../sysfs/classes/infiniband.md),
[infiniband_verbs](../sysfs/classes/infiniband_verbs.md),
[devlink](../sysfs/classes/devlink.md), [nd](../sysfs/classes/nd.md);
RDMA background: [rdma](../networking/rdma.md). The rdma-core and ndctl
halves upgraded in the 7-d pass: the official rdma-core README
(github.com/linux-rdma/rdma-core) states the userspace-components claim and
the uverbsX/rdma_cm/umadX node mapping, and the ndctl README
(github.com/pmem/ndctl) states the libnvdimm-management scope; the umad and
uverbs devnode details below keep their kernel-source attributions. Source
details kept from the
fetch pass: the umad class devices carry an `abi_version` attr and a
`infiniband/%s` devnode; uverbs devnodes are mode 0666 (user-level verbs need
access from unprivileged processes); and on the live host `ndctl0` was a
**char** device at 253:0 while `/sys/dev/block/253:0` pointed at zram0 -- the
two `/sys/dev` namespaces are separate major spaces, verified live.

### XR-114 -- non-class trees (/sys/devices, /sys/bus, /sys/module, /sys/kernel, /sys/fs) -> sysctl, dmidecode

| class | subsystem + config | driver-model relationship | consumers with HOW | /dev, /proc cross-refs |
|---|---|---|---|---|
| non-class: `/sys/devices/system/cpu` (ABI 19 entries: cpufreq/cpuidle/topology), `/sys/module` (ABI 5), `/sys/kernel` (btf), `/sys/fs` (xfs ABI) | device tree core (`/sys/devices`), bus types, module kobjects (`sysfs-module`), kernel-global attrs, filesystem-specific attrs (`sysfs-fs-xfs`) | not classes at all: the kobject hierarchy that classes hang off; per-CPU cpufreq policy dirs live here, not in a class | **cpupower**(1) reads/writes cpufreq attributes under `/sys/devices/system/cpu/cpuN/cpufreq` (cpupower.1 + `cpufreq.rst` sourced); **lscpu**(1) reads CPU topology (util-linux); **sysctl(8)** (procps 4.0.4): "used to modify kernel parameters at runtime. The parameters available are those listed under /proc/sys/. Procfs is required for sysctl support in Linux" -- i.e. sysctl(8) is a `/proc/sys` tool, and `/sys/kernel` is a distinct attribute tree, not a sysctl frontend; **dmidecode**(8) (3.6): locates the DMI table "first ... from sysfs" -- FILES: `/sys/firmware/dmi/tables/smbios_entry_point` and `/sys/firmware/dmi/tables/DMI` (Linux only) -- falling back to `/dev/mem` | `/proc/modules` vs `/sys/module` (same inventory, different shapes); `/proc/sys/` is the sysctl tree; `/sys/fs/cgroup` is the cgroup2 mount, not a class |

Pages: [cpu-freq](../kernel/drivers/cpu-freq.md), [cgroups-v2](../containers/cgroups-v2.md);
procfs context: [proc](../observability/proc.md). What distinguishes this row
from the class rows: there is no class directory to cite -- consumers address
paths under `/sys/devices` (per-CPU policy dirs), `/sys/module` (per-module
parameters and sections), `/sys/kernel` (global attrs like the BTF blob) and
`/sys/fs` (filesystem-specific trees, plus the cgroup2 mount). The ABI files
mirror that structure: `sysfs-devices-system-cpu` (19), `sysfs-module` (5),
`sysfs-kernel-btf`, `sysfs-fs-xfs`. The 7-d fetch pass sourced both remaining
consumer claims: procps' sysctl(8) is explicitly a `/proc/sys` tool (quote
above), and dmidecode(8) reads the DMI table from sysfs first
(`/sys/firmware/dmi/tables/...`) before `/dev/mem`.

---

## Coverage and gaps

| Row | Status | Missing source (exact) |
|---|---|---|
| XR-101 block/bdi | documented | -- |
| XR-102 net | documented | -- (NetworkManager(8) 1.52.1 fetched: udev discovery + NM_UNMANAGED/ID_NET_MANAGED_BY properties) |
| XR-103 tty | documented | -- |
| XR-104 nvme | documented | -- (no live device on the build host; ABI+source only) |
| XR-105 hwmon | documented | -- |
| XR-106 thermal | documented | -- (thermald(8) 2.5.9 fetched: sysfs scan stated verbatim) |
| XR-107 power_supply | documented | -- (UPower reference manual v1.91.2 fetched: NativePath = sysfs path) |
| XR-108 leds/backlight | documented | -- |
| XR-109 gpio/pwm/regulator/i2c-adapter | documented | -- |
| XR-110 input | documented | -- (libinput 1.31.0 docs fetched: ID_INPUT_* udev-property contract) |
| XR-111 drm/graphics | documented | -- (drm(7)/libdrm 2.4.124 man pages fetched: ioctl wrappers over /dev/dri/card0) |
| XR-112 msr/cpuid | source-limited | msr-tools rdmsr/wrmsr documentation (kernel.org gitweb unreachable); cpuid(1) and msr(4) halves now sourced |
| XR-113 infiniband/devlink/dax | documented | -- (rdma-core README: uverbsX/rdma_cm/umadX node mapping; ndctl README: libnvdimm scope) |
| XR-114 non-class trees | documented | -- (sysctl(8) procps wording and dmidecode(8) sysfs FILES fetched) |

## Key Takeaways

- The decisive question for any tool row is **read, write, or bypass**: lsblk
  and sensors read; brightnessctl and cpupower write; ip/ethtool, libgpiod,
  i2c-tools, nvme-cli (action side) and devlink all bypass sysfs via
  netlink/ioctl/char devices.
- udev appears on both sides of the interface: it consumes uevents and writes
  `ATTR` files (systemd-backlight restore), while human tools see the result.
- Class population is config- and hardware-gated: empty live dirs (hwmon,
  thermal, power_supply, leds, backlight, i2c-adapter, nvme) say nothing about
  the ABI contract, and missing /dev nodes (input, cpu, dri) on the build host
  are snapshots, not rules.
- The source-limited set is down to one row (XR-112): kernel-side contracts
  are documented everywhere, and the consumer documentation (NetworkManager,
  thermald, UPower, libinput, libdrm, rdma-core/ndctl, sysctl/dmidecode) was
  fetched upstream in the 7-d pass -- only the msr-tools rdmsr/wrmsr docs
  remain unreachable, and XR-112 names its missing source.

## Interview Questions

1. **Does `ip link set eth0 up` write to `/sys/class/net/eth0`?** No -- ip(8)
   uses rtnetlink; sysfs netdev attributes are read-side observability (XR-102).
2. **Why does libgpiod ignore `/sys/class/gpio`?** The gpio sysfs ABI is
   obsolete (removed after 2020 per its own ABI file); the supported interface
   is the `/dev/gpiochipN` char device (XR-109).
3. **What writes your backlight level at boot?** systemd-backlight@.service,
   via a udev ATTR write of the saved `brightness` value (XR-108).

## Cross-References

- [Method and coverage](../interface-encyclopedia.md) -- status vocabulary.
- [Cross-layer maps overview](./overview.md) and [coverage ledger](./ledger.md).
- [Sysfs overview](../sysfs/overview.md), [sysfs ledger](../sysfs/ledger.md),
  [sysfs internals](../kernel/filesystems/sysfs.md), [observing sysfs](../observability/sysfs.md).
- [udev](../admin/udev.md) -- uevent consumption and ATTR writes.
- [libc -> syscall -> kernel](./libc-syscall-kernel.md) and [feature matrix](./feature-matrix.md) -- sibling maps.
