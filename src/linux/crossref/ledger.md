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
| XR-012 | getpwnam/NSS -> no direct syscall -> /etc/passwd + NSS modules (musl: built-in) | source-limited | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-013 | ioctl -> fs/ioctl dispatch -> driver unlocked_ioctl (terminal path source-limited) | source-limited | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
| XR-014 | dynamic loader -> mmap/open/read -> ld.so program loading | documented | [libc-syscall-kernel](./libc-syscall-kernel.md) | — |
## sysfs class -> subsystem -> driver model -> userspace tools

| ID | Map | Status | Chapter | Notes |
|---|---|---|---|---|
| XR-101 | /sys/class/block + bdi -> block core -> genhd/blk-sysfs -> lsblk, blockdev | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-102 | /sys/class/net -> net core -> net-sysfs -> ip, ethtool (source-limited: NetworkManager docs) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-103 | /sys/class/tty -> tty core -> tty_io -> stty, agetty, udev | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-104 | /sys/class/nvme -> nvme host core -> nvme-cli, libnvme | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-105 | /sys/class/hwmon -> hwmon core -> sensors (lm-sensors) | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-106 | /sys/class/thermal -> thermal core -> thermald (detail source-limited) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-107 | /sys/class/power_supply -> power supply core -> UPower (source-limited) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-108 | /sys/class/leds + backlight -> leds/backlight cores -> brightnessctl, systemd-backlight | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-109 | /sys/class/{gpio,pwm,regulator,i2c-adapter} -> subsystem cores -> libgpiod, pinctrl tools | documented | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-110 | /sys/class/input -> input core -> libinput/evdev (source-limited) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-111 | /sys/class/drm + graphics -> DRM core -> libdrm/compositors (source-limited) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-112 | /sys/class/{msr,cpuid} -> x86 arch code -> msr-tools (source-limited) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-113 | /sys/class/infiniband + devlink + dax -> RDMA/devlink/dax cores -> rdma, ndctl (source-limited) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
| XR-114 | non-class trees (/sys/devices, /sys/bus, /sys/module, /sys/kernel, /sys/fs) -> sysctl, dmidecode (source-limited) | source-limited | [sysfs-driver-tools](./sysfs-driver-tools.md) | — |
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
| XR-208 | memfd_secret (5.14) -> no glibc wrapper -> SECRETMEM config (source-limited) | source-limited | [feature-matrix](./feature-matrix.md) | — |
| XR-209 | cachestat (6.5) -> no glibc wrapper -> header-free use via syscall() (source-limited note) | source-limited | [feature-matrix](./feature-matrix.md) | — |
| XR-210 | fchmodat2 (6.6) -> glibc 2.40 fchmodat routing -> runtime prereq | documented | [feature-matrix](./feature-matrix.md) | — |

Total rows: 38. Statuses: not-started=0, researched=0, source-limited=12, documented=26.
