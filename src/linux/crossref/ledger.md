# Cross-Layer Mapping Coverage Ledger

This ledger is the authoritative inventory for the [Cross-Layer Interface Maps](./overview.md). Rows are seeded from the
wave-2 mapping chapters; the Status column is merged from agent status
reports. Vocabulary: not-started | researched | documented | source-limited.

## libc API -> syscall -> kernel subsystem

| ID | Map | Status | Chapter | Notes |
|---|---|---|---|---|
| XR-001 | printf family -> write/writev -> vfs_write (stdio buffering path) | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-002 | fopen/fread family -> open/read -> VFS/page cache | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-003 | malloc -> brk/mmap -> mm allocator path (arena model, non-1:1) | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-004 | posix_spawn -> clone+execve composite (action list, non-1:1) | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-005 | pthread_create -> clone(CLONE_VM|CLONE_THREAD) -> scheduler | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-006 | pthread_mutex_lock -> futex -> futex wait queue | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-007 | readdir(3) -> getdents64 -> fs/readdir.c | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-008 | exec family -> execve/execveat -> fs/exec.c (binfmt) | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-009 | signal functions -> rt_sig* family -> kernel/signal.c | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-010 | clock_gettime/gettimeofday -> vDSO/clock_gettime64 -> timekeeping | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-011 | socket/connect/send -> socket family -> net/socket.c | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-012 | getpwnam/NSS -> no direct syscall -> /etc/passwd + NSS modules (musl: built-in) | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | glibc nss.texi module interface + host /etc/nsswitch.conf; musl src/passwd/getpw_a.c; libnss_files.so.2 is a stub (files service in libc 2.41) |
| XR-013 | ioctl -> fs/ioctl dispatch -> driver unlocked_ioctl (tty: tty_ioctl chain) | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | tty path via fetched drivers/tty/tty_io.c + cached ioctl_tty.2; termios-answer site (tty_ioctl.c) below cached sources |
| XR-014 | dynamic loader -> mmap/open/read -> ld.so program loading | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
## sysfs class -> subsystem -> driver model -> userspace tools

| ID | Map | Status | Chapter | Notes |
|---|---|---|---|---|
| XR-101 | /sys/class/block + bdi -> block core -> genhd/blk-sysfs -> lsblk, blockdev | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-102 | /sys/class/net -> net core -> net-sysfs -> ip, ethtool, NetworkManager | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | NetworkManager(8) 1.52.1 (manpages.debian.org): udev discovery, NM_UNMANAGED/ID_NET_MANAGED_BY |
| XR-103 | /sys/class/tty -> tty core -> tty_io -> stty, agetty, udev | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-104 | /sys/class/nvme -> nvme host core -> nvme-cli, libnvme | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-105 | /sys/class/hwmon -> hwmon core -> sensors (lm-sensors) | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-106 | /sys/class/thermal -> thermal core -> thermald | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | thermald(8) 2.5.9 (manpages.debian.org): scans /sys/class/thermal for sensors and cooling drivers |
| XR-107 | /sys/class/power_supply -> power supply core -> UPower | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | UPower ref manual v1.91.2 (upower.freedesktop.org): NativePath = sysfs power_supply path |
| XR-108 | /sys/class/leds + backlight -> leds/backlight cores -> brightnessctl, systemd-backlight | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-109 | /sys/class/{gpio,pwm,regulator,i2c-adapter} -> subsystem cores -> libgpiod, pinctrl tools | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-110 | /sys/class/input -> input core -> libinput/evdev | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | libinput 1.31.0 docs (wayland.freedesktop.org): ID_INPUT_* udev-property contract |
| XR-111 | /sys/class/drm + graphics -> DRM core -> libdrm/compositors | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | drm(7) + libdrm 2.4.124 man pages (manpages.debian.org): ioctl wrappers over /dev/dri/card0 |
| XR-112 | /sys/class/{msr,cpuid} -> x86 arch code -> msr-tools | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | msr-tools rdmsr/wrmsr docs unreachable (kernel.org anti-bot); cpuid(1) + msr(4) halves sourced |
| XR-113 | /sys/class/infiniband + devlink + dax -> RDMA/devlink/dax cores -> rdma, ndctl | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | rdma-core README (github.com/linux-rdma/rdma-core): uverbsX/rdma_cm/umadX nodes; ndctl README: libnvdimm scope |
| XR-114 | non-class trees (/sys/devices, /sys/bus, /sys/module, /sys/kernel, /sys/fs) -> sysctl, dmidecode | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | sysctl(8) procps 4.0.4 (/proc/sys) + dmidecode(8) 3.6 (sysfs DMI FILES) fetched |
## kernel feature -> minimum version -> libc availability -> runtime prerequisites

| ID | Map | Status | Chapter | Notes |
|---|---|---|---|---|
| XR-201 | io_uring (5.1/5.5+) -> liburing, no glibc wrapper -> kernel config + caps | documented | [feature-matrix](./feature-matrix.md) | — |
| XR-202 | pidfd API (5.3+) -> glibc 2.30+ wrappers -> kernel config | documented | [feature-matrix](./feature-matrix.md) | — |
| XR-203 | openat2/resize/landlock (5.6/5.13) -> no glibc wrapper era -> headers/libseccomp era | documented | [feature-matrix](./feature-matrix.md) | — |
| XR-204 | clone3 + struct sizzie (5.3+) -> glibc 2.34+ posix_spawn routing -> fallback story | documented | [feature-matrix](./feature-matrix.md) | — |
| XR-205 | time64 (5.1, 32-bit) -> glibc 2.30/2.32/2.34 stages -> runtime fallback | documented | [feature-matrix](./feature-matrix.md) | — |
| XR-206 | statx (4.11) -> glibc statx wrapper 2.28 -> header gates | documented | [feature-matrix](./feature-matrix.md) | — |
| XR-207 | mount API (5.2+) fsopen/move_mount -> no glibc wrapper -> libmount | documented | [feature-matrix](./feature-matrix.md) | — |
| XR-208 | memfd_secret (5.14) -> no glibc wrapper -> SECRETMEM config | documented | [feature-matrix](./feature-matrix.md) | full syscall page + header sweep; secretmem.enable v6.4/v6.5 flip stays tag-bisect sourced |
| XR-209 | cachestat (6.5) -> no glibc wrapper -> structs in linux/mman.h, raw syscall() | documented | [feature-matrix](./feature-matrix.md) | no linux/cachestat.h on host; structs ship in linux/mman.h (linux-libc-dev) |
| XR-210 | fchmodat2 (6.6) -> glibc 2.40 fchmodat routing -> runtime prereq | documented | [feature-matrix](./feature-matrix.md) | — |

Total rows: 38. Statuses: not-started=0, researched=0, source-limited=1, documented=37.
