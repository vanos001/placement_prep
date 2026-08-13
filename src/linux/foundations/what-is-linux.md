# What Is Linux?

Linux is a free and open-source Unix-like operating system kernel first created by Linus Torvalds in 1991. Today, the term "Linux" is used in two distinct ways: strictly, it refers to the **kernel** itself — the core software that manages hardware resources and provides services to running programs. More broadly, it refers to complete **operating systems** (called distributions) that pair the Linux kernel with userspace tools, libraries, and package managers to form a usable system.

This dual meaning has been the source of decades of naming debates (GNU/Linux vs. Linux), but in practice the distinction matters less than understanding what each layer does and how they fit together.

## The Linux Kernel

The Linux kernel is a **monolithic kernel** — meaning that the entire operating system core runs in a single address space with full access to all hardware. Device drivers, file systems, network protocol stacks, and process schedulers all execute in kernel mode (also called supervisor mode or ring 0 on x86).

This is in direct contrast to **microkernels** (like Mach, L4, or MINIX), where the kernel is kept minimal and most OS services run as separate user-space processes communicating via message passing.

### Why Monolithic?

Torvalds made this design choice early and defended it vigorously in the famous [Tanenbaum–Torvalds debate](https://en.wikipedia.org/wiki/Tanenbaum%E2%80%93Torvalds_debate) of 1992. Andrew Tanenbaum, creator of MINIX, argued that microkernels were the future and that monolithic kernels were "a giant step back into the 1970s." Torvalds countered that practical performance and simplicity mattered more than theoretical elegance.

History sided with Torvalds in terms of adoption, though the debate continues in academic circles. Linux's monolithic design provides:

- **Performance**: No inter-process communication (IPC) overhead for kernel services
- **Simplicity**: All kernel code shares a single address space, making function calls cheap
- **Flexibility**: Loadable kernel modules allow extending the kernel at runtime without rebooting

To mitigate the downsides of a monolithic design (a buggy driver can crash the entire kernel), Linux introduced **loadable kernel modules (LKMs)** and increasingly strict coding standards, static analysis tools, and sandboxing mechanisms.

### Kernel Architecture

```mermaid
graph TB
    subgraph "User Space"
        APP1[Application 1]
        APP2[Application 2]
        APP3[Application 3]
        GLIBC[glibc / musl]
        LIBS[Other Libraries]
    end

    subgraph "Kernel Space"
        SYSCALL[System Call Interface]
        VFS[Virtual File System]
        PROC[Process Scheduler]
        NET[Network Stack]
        MM[Memory Manager]
        DRV[Device Drivers]
        ARCH[Architecture-Dependent Code]
    end

    subgraph "Hardware"
        CPU[CPU]
        MEM[RAM]
        DISK[Storage]
        NIC[Network Cards]
        DEV[Other Devices]
    end

    APP1 --> GLIBC
    APP2 --> GLIBC
    APP3 --> LIBS
    GLIBC --> SYSCALL
    LIBS --> SYSCALL
    SYSCALL --> VFS
    SYSCALL --> PROC
    SYSCALL --> NET
    SYSCALL --> MM
    VFS --> DRV
    PROC --> ARCH
    NET --> DRV
    MM --> ARCH
    DRV --> CPU
    DRV --> MEM
    DRV --> DISK
    DRV --> NIC
    ARCH --> CPU
    ARCH --> MEM
```

## Kernel Space vs. User Space

The separation between **kernel space** and **user space** is one of the most fundamental concepts in Linux (and operating systems in general).

### Kernel Space

Kernel space is the memory region where the kernel code executes. Code running in kernel space has unrestricted access to:

- All hardware (CPU instructions, I/O ports, memory-mapped registers)
- All of physical memory (via virtual memory mappings)
- All CPU privileged instructions (disabling interrupts, changing page tables, etc.)

When a user program needs to perform a privileged operation — reading a file, sending a network packet, creating a process — it cannot do so directly. Instead, it makes a **system call**, which transitions the CPU from user mode to kernel mode.

### User Space

User space is where all normal applications run. Each process has its own virtual address space, isolated from other processes and from the kernel. User-space code cannot:

- Access hardware directly
- Read or write another process's memory
- Execute privileged CPU instructions
- Access kernel data structures

If a user-space program attempts any of these, the CPU generates a fault (like a segmentation fault / SIGSEGV), and the kernel intervenes — typically by terminating the offending process.

### The System Call Interface

The boundary between user space and kernel space is the **system call interface**. On Linux/x86-64, system calls are invoked via the `syscall` instruction. Each system call has a number:

```bash
# View system call numbers for your architecture
$ cat /usr/include/asm/unistd_64.h | head -20
#define __NR_read 0
#define __NR_write 1
#define __NR_open 2
#define __NR_close 3
#define __NR_stat 4
#define __NR_fstat 5
```

Common system calls include:

| System Call | Purpose |
|-------------|---------|
| `read()`    | Read from a file descriptor |
| `write()`   | Write to a file descriptor |
| `open()`    | Open a file |
| `close()`   | Close a file descriptor |
| `fork()`    | Create a new process |
| `execve()`  | Execute a program |
| `mmap()`    | Map memory |
| `ioctl()`   | Device-specific control operations |
| `socket()`  | Create a network socket |
| `brk()`     | Change data segment size |

You can trace system calls made by any program using `strace`:

```bash
$ strace ls /tmp
execve("/usr/bin/ls", ["ls", "/tmp"], 0x7ffd4a3b2c40 /* 52 vars */) = 0
brk(NULL)                               = 0x55a1e6e27000
access("/etc/ld.so.preload", R_OK)      = -1 ENOENT (No such file or directory)
openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
fstat(3, {st_mode=S_IFREG|0644, st_size=78456, ...}) = 0
mmap(NULL, 78456, PROT_READ, MAP_PRIVATE, 3, 0) = 0x7f8e1a200000
close(3)                                = 0
openat(AT_FDCWD, "/lib/x86_64-linux-gnu/libc.so.6", O_RDONLY|O_CLOEXEC) = 3
read(3, "\177ELF\2\1\1\3\0\0\0\0\0\0\0\0\3\0>\0\1\0\0\0\360q\2\0\0\0\0\0"..., 832) = 832
fstat(3, {st_mode=S_IFREG|0755, st_size=1922136, ...}) = 0
mmap(NULL, 8192, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0x7f8e1a1fe000
# ... many more calls ...
```

## Linux vs. Unix

Linux is often described as "Unix-like" or "Unix-compatible" but it is **not Unix** in the legal or historical sense. Understanding the distinction requires some history (covered in detail in [Unix Heritage](./unix-heritage.md)).

### Key Differences

| Aspect | Traditional Unix | Linux |
|--------|-----------------|-------|
| **Source code** | Proprietary (AT&T, later various vendors) | Open source (GPL v2) |
| **Kernel** | Various (System V, BSD, etc.) | Monolithic, written from scratch |
| **Lineage** | Direct descendant of AT&T Unix | Independently written, POSIX-compatible |
| **Trademark** | "UNIX®" is a trademark of The Open Group | Not trademarked; anyone can use the name |
| **Hardware** | Originally minicomputers, later workstations | Runs on everything from phones to supercomputers |
| **Standardization** | Single UNIX Specification (SUS) | Follows POSIX but is not officially certified |

### What Linux Borrows from Unix

Despite being written from scratch, Linux inherits nearly all of Unix's design philosophy:

1. **"Everything is a file"**: Devices, processes, and system information are represented as files in the filesystem (e.g., `/dev/sda`, `/proc/cpuinfo`)
2. **Small, composable tools**: Programs do one thing well and are combined via pipes (`|`)
3. **Plain text configuration**: Most configuration files are human-readable text
4. **Hierarchical filesystem**: Single root (`/`) with standard directories (`/bin`, `/etc`, `/home`, `/var`, etc.)
5. **Multiuser, multitasking**: Multiple users can run multiple programs concurrently
6. **Shell as the primary interface**: `bash`, `zsh`, and other shells provide powerful scripting capabilities

## Distributions: The Complete Package

A Linux **distribution** (or "distro") packages the Linux kernel with:

- A **C library** (usually glibc or musl)
- Core **userspace utilities** (from GNU, BusyBox, or other projects)
- A **package manager** for installing and updating software
- A **bootloader** (usually GRUB)
- An **init system** (usually systemd, OpenRC, or runit)
- Optionally: a **desktop environment** (GNOME, KDE, XFCE, etc.)
- Optionally: a **display server** (X11 or Wayland)

This is why some people insist on calling it "GNU/Linux" — the GNU project provided many essential userspace tools (coreutils, GCC, glibc, bash) that form the foundation of most distributions.

### Major Distribution Families

```mermaid
graph TD
    LINUX[Linux Kernel 1.0 - 6.x]
    LINUX --> SLACKWARE[Slackware 1993]
    LINUX --> DEBIAN[Debian 1993]
    LINUX --> REDHAT[Red Hat 1994]
    LINUX --> SUSE[SUSE 1994]

    DEBIAN --> UBUNTU[Ubuntu 2004]
    DEBIAN --> MINT[Linux Mint 2006]
    DEBIAN --> KALI[Kali Linux]
    DEBIAN --> RASPBIAN[Raspberry Pi OS]

    REDHAT --> FEDORA[Fedora 2003]
    REDHAT --> RHEL[RHEL]
    REDHAT --> CENTOS[CentOS]
    REDHAT --> ORACLE[Oracle Linux]

    SUSE --> OPENSUSE[openSUSE]
    SUSE --> SLES[SLES]

    LINUX --> ARCH[Arch Linux 2002]
    ARCH --> MANJARO[Manjaro]
    ARCH --> ENDEAVOUR[EndeavourOS]

    LINUX --> GENTOO[Gentoo 1999]
    LINUX --> ALPINE[Alpine Linux]
    LINUX --> VOID[Void Linux]
```

For a comprehensive guide to choosing and comparing distributions, see [Distributions](./distributions.md).

## The Linux Ecosystem Today

Linux dominates in nearly every computing category except the desktop:

- **Servers**: ~80% of web servers run Linux
- **Supercomputers**: 100% of the TOP500 run Linux (as of 2024)
- **Mobile**: Android (based on the Linux kernel) runs on ~70% of smartphones
- **Cloud**: The vast majority of cloud instances (AWS, GCP, Azure) run Linux
- **Embedded**: Routers, smart TVs, cars, IoT devices
- **Desktop**: ~4% market share, but growing

### Why Linux Dominates

1. **Free and open source**: No licensing fees; anyone can inspect, modify, and redistribute
2. **Portability**: Runs on virtually any CPU architecture (x86, ARM, RISC-V, MIPS, PowerPC, s390x, etc.)
3. **Stability**: Many Linux servers have uptime measured in years
4. **Security**: Open code review, rapid patching, strong permission model
5. **Community**: Thousands of contributors worldwide, massive corporate support (Red Hat, Google, Microsoft, Intel, etc.)

## The Boot Process

Understanding how Linux starts illuminates the relationship between hardware, kernel, and userspace. The boot sequence has several stages:

```mermaid
sequenceDiagram
    participant HW as Hardware
    participant FW as Firmware
    participant BL as Bootloader
    participant K as Kernel
    participant INIT as Init System
    
    HW->>FW: Power on
    FW->>FW: POST (Power-On Self-Test)
    FW->>BL: Load bootloader from disk
    BL->>K: Load kernel image + initramfs
    K->>K: Decompress, initialize subsystems
    K->>K: Mount root filesystem
    K->>INIT: Execute /sbin/init (PID 1)
    INIT->>INIT: Start services, getty, display manager
```

### BIOS/UEFI

The firmware (BIOS or UEFI) initializes hardware and loads the bootloader. Modern systems use **UEFI** (Unified Extensible Firmware Interface), which replaced the legacy BIOS. UEFI provides:

- **GPT partition tables** (replacing MBR's 2 TB limit and 4 primary partition limit)
- **Secure Boot** — verifies cryptographic signatures of bootloaders and kernels
- **EFI System Partition (ESP)** — a FAT32 partition holding bootloader binaries

```bash
# Check if system uses UEFI
$ [ -d /sys/firmware/efi ] && echo "UEFI" || echo "BIOS"

# View EFI boot entries
$ efibootmgr -v
Boot0000* ubuntu    HD(1,GPT,...)/File(\EFI\ubuntu\shimx64.efi)
Boot0001* Windows   HD(1,GPT,...)/File(\EFI\Microsoft\Boot\bootmgfw.efi)
```

### The Bootloader: GRUB

**GRUB** (GRand Unified Bootloader) is the most common Linux bootloader. It:

1. Presents a menu of boot options
2. Loads the kernel image (`vmlinuz`) into memory
3. Loads the **initramfs** (initial RAM filesystem) — a small filesystem containing drivers needed to mount the real root filesystem
4. Transfers control to the kernel

```bash
# GRUB configuration
$ cat /etc/default/grub
GRUB_DEFAULT=0
GRUB_TIMEOUT=5
GRUB_DISTRIBUTOR=`lsb_release -i -s 2> /dev/null || echo Debian`
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_CMDLINE_LINUX=""

# Regenerate GRUB config after changes
$ sudo update-grub

# View kernel command line parameters
$ cat /proc/cmdline
BOOT_IMAGE=/vmlinuz-6.8.0-40-generic root=UUID=abc123... ro quiet splash
```

### Kernel Initialization

After GRUB loads the kernel, the kernel:

1. **Decompresses** itself (the `vmlinuz` image is compressed)
2. **Initializes CPU and memory** management
3. **Starts the init process** (PID 1) — traditionally `/sbin/init`, now usually `systemd`
4. The init process starts all other services

```bash
# What is PID 1?
$ ps -p 1 -o comm=
systemd

# Or on older systems:
# init

# Kernel boot messages
$ dmesg | head -20
[    0.000000] Linux version 6.8.0-40-generic (buildd@lcy02-amd64-048)
[    0.000000] Command line: BOOT_IMAGE=/vmlinuz-6.8.0-40-generic root=UUID=...
[    0.000000] BIOS-provided physical RAM map:
[    0.000000] BIOS-e820: [mem 0x0000000000000000-0x000000000009fbff] usable
```

### initramfs

The **initramfs** (initial RAM filesystem) is a temporary root filesystem loaded into memory by the bootloader. It contains essential kernel modules and scripts needed to mount the real root filesystem:

```bash
# Inspect the initramfs
$ lsinitramfs /boot/initrd.img-$(uname -r) | head -20
.
kernel
kernel/x86
kernel/x86/microcode
kernel/x86/microcode/AuthenticAMD.bin
bin
bin/cat
bin/chmod
bin/chroot

# Extract initramfs for inspection
$ mkdir /tmp/initrd && cd /tmp/initrd
$ unmkinitramfs /boot/initrd.img-$(uname -r) .
```

## The /proc and /sys Filesystems

Linux exposes kernel and hardware information through virtual filesystems. These don't exist on disk — the kernel generates their contents dynamically.

### /proc — Process and Kernel Information

```bash
# CPU information
$ cat /proc/cpuinfo
processor	: 0
vendor_id	: GenuineIntel
model name	: Intel(R) Core(TM) i7-12700K
cpu MHz		: 3600.000
cache size	: 25600 KB

# Memory information
$ cat /proc/meminfo
MemTotal:       32768000 kB
MemFree:        12345678 kB
MemAvailable:   20000000 kB
Buffers:          512000 kB
Cached:          8000000 kB

# Process-specific information
$ ls /proc/self/
attr/    cmdline  comm     cwd ->   environ  exe ->   fd/      maps
mem      mounts   net/     oom_score  stat   status   task/

# View a process's open file descriptors
$ ls -la /proc/self/fd/
total 0
lrwx------ 1 user user 64 Jul 22 10:00 0 -> /dev/pts/0
lrwx------ 1 user user 64 Jul 22 10:00 1 -> /dev/pts/0
lrwx------ 1 user user 64 Jul 22 10:00 2 -> /dev/pts/0

# Kernel version
$ cat /proc/version
Linux version 6.8.0-40-generic (buildd@lcy02-amd64-048)
```

### /sys — Device and Kernel Subsystem Information

The **sysfs** filesystem (mounted at `/sys`) exposes kernel objects as a directory hierarchy:

```bash
# Block devices
$ ls /sys/block/
sda  sdb  nvme0n1

# Network interfaces
$ ls /sys/class/net/
eth0  lo  wlan0

# CPU topology
$ cat /sys/devices/system/cpu/cpu0/topology/physical_package_id
0

# View kernel parameters (tunable)
$ sysctl vm.swappiness
vm.swappiness = 60

# Change a parameter temporarily
$ sudo sysctl -w vm.swappiness=10

# Persistent changes in /etc/sysctl.conf or /etc/sysctl.d/
```

## Linux Security Model

Linux implements a multi-layered security model:

### Traditional Permissions

Every file and process has an owner (UID) and group (GID). The classic rwx (read/write/execute) permission model:

```bash
$ ls -la /etc/passwd
-rw-r--r-- 1 root root 2847 Jul 10 09:00 /etc/passwd
# owner(root):rw-  group(root):r--  others:r--
```

### Capabilities

Linux divides root's privileges into distinct **capabilities**, allowing fine-grained privilege assignment:

```c
#include <sys/prctl.h>
#include <linux/capability.h>

/* Grant only network capability instead of full root */
prctl(PR_SET_KEEPCAPS, 1);
setuid(unprivileged_uid);

/* Set specific capability */
struct __user_cap_header_struct hdr = { .version = _LINUX_CAPABILITY_VERSION_3 };
struct __user_cap_data_struct data[2] = {0};
data[0].effective = (1 << CAP_NET_RAW);
data[0].permitted = (1 << CAP_NET_RAW);
capset(&hdr, data);
```

Key capabilities include:

| Capability | Allows |
|---|---|
| `CAP_NET_RAW` | Raw sockets (ping, packet capture) |
| `CAP_SYS_ADMIN` | Mount, namespace operations, many admin tasks |
| `CAP_NET_BIND_SERVICE` | Bind to ports below 1024 |
| `CAP_DAC_OVERRIDE` | Bypass file permission checks |
| `CAP_SYS_PTRACE` | Trace other processes (strace, gdb) |

### Namespaces and Containers

Linux **namespaces** isolate processes from each other, forming the basis of containers:

| Namespace | Isolates |
|---|---|
| `PID` | Process IDs |
| `NET` | Network stack |
| `MNT` | Mount points |
| `UTS` | Hostname |
| `IPC` | IPC resources |
| `USER` | UID/GID mappings |
| `CGROUP` | Cgroup root |

```bash
# Run a process in new namespaces
$ sudo unshare --pid --net --mount --uts --ipc --fork /bin/bash

# View namespaces of a process
$ ls -la /proc/self/ns/
total 0
lrwxrwxrwx 1 root root 0 Jul 22 10:00 cgroup -> 'cgroup:[4026531835]'
lrwxrwxrwx 1 root root 0 Jul 22 10:00 ipc -> 'ipc:[4026531839]'
lrwxrwxrwx 1 root root 0 Jul 22 10:00 mnt -> 'mnt:[4026531841]'
lrwxrwxrwx 1 root root 0 Jul 22 10:00 net -> 'net:[4026531969]'
lrwxrwxrwx 1 root root 0 Jul 22 10:00 pid -> 'pid:[4026531836]'
lrwxrwxrwx 1 root root 0 Jul 22 10:00 user -> 'user:[4026531837]'
lrwxrwxrwx 1 root root 0 Jul 22 10:00 uts -> 'uts:[4026531838]'
```

### SELinux and AppArmor

Linux supports mandatory access control (MAC) through security modules:

- **SELinux** (Security-Enhanced Linux) — developed by the NSA, uses security contexts and policies. Default on Red Hat/Fedora.
- **AppArmor** — path-based security profiles. Default on Ubuntu/SUSE.

```bash
# Check SELinux status
$ getenforce
Enforcing

# View SELinux context of a file
$ ls -Z /etc/passwd
system_u:object_r:passwd_file_t:s0 /etc/passwd

# AppArmor profile status
$ sudo aa-status
profiles are loaded
profiles are in enforce mode
  /usr/sbin/cupsd
  /usr/sbin/ntpd
```

## Building and Running the Kernel

For those curious about the kernel itself, here's how to build it from source:

```bash
# Get the source
$ git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git
$ cd linux

# Configure (use current system config as base)
$ make defconfig        # or: make menuconfig for interactive config

# Build
$ make -j$(nproc)       # compile with all available CPU cores

# Install
$ sudo make modules_install
$ sudo make install
$ sudo update-grub       # on Debian/Ubuntu
```

The kernel's `Makefile` reveals the current version:

```bash
$ head -5 Makefile
# SPDX-License-Identifier: GPL-2.0
VERSION = 6
PATCHLEVEL = 12
SUBLEVEL = 0
EXTRAVERSION =
```

## What's in the Kernel Source Tree?

The Linux kernel source tree is organized as follows:

| Directory | Contents |
|-----------|----------|
| `arch/` | Architecture-specific code (x86, arm64, riscv, etc.) |
| `block/` | Block I/O layer |
| `drivers/` | Device drivers (the largest directory) |
| `fs/` | Filesystem implementations (ext4, btrfs, xfs, etc.) |
| `include/` | Kernel header files |
| `init/` | Kernel initialization code (`main.c`) |
| `kernel/` | Core kernel subsystems (scheduler, signals, etc.) |
| `lib/` | Helper library routines |
| `mm/` | Memory management |
| `net/` | Networking stack |
| `scripts/` | Build scripts and utilities |
| `security/` | Security modules (SELinux, AppArmor, etc.) |
| `sound/` | Audio subsystem |
| `tools/` | Userspace tools for kernel development |
| `usr/` | initramfs-related code |

## Try It Yourself

You can explore your running kernel:

```bash
# Kernel version
$ uname -r
6.8.0-40-generic

# Detailed kernel info
$ uname -a
Linux myhost 6.8.0-40-generic #45-Ubuntu SMP PREEMPT_DYNAMIC x86_64 GNU/Linux

# Loaded kernel modules
$ lsmod | head -10
Module                  Size  Used by
nvidia_drm            114688  1
nvidia_modeset       1536000  1 nvidia_drm
nvidia              60719104  3 nvidia_modeset
i915                 4046848  8
drm_kms_helper        315392  2 nvidia_drm,i915

# Kernel parameters
$ cat /proc/cmdline
BOOT_IMAGE=/vmlinuz-6.8.0-40-generic root=UUID=... ro quiet splash

# System call table (partial)
$ cat /proc/kallsyms | grep sys_call_table | head -3
ffffffff8a000280 R sys_call_table
ffffffff8a000a80 R ia32_sys_call_table
```

## Kernel Development Model

The Linux kernel follows a unique development model that has produced one of the largest and most successful open-source projects in history.

### The Release Cycle

Since Linux 2.6 (2003), the kernel uses a time-based release cycle:

```mermaid
graph LR
    A["Merge Window<br>~2 weeks"] --> B["RC1<br>Stabilization"]
    B --> C["RC2-RC7<br>Bug fixes only"]
    C --> D["Final Release<br>~7 weeks total"]
    D --> A
```

1. **Merge window** (~2 weeks): New features are merged into the mainline tree
2. **Release candidates** (RC1–RC7, ~5 weeks): Only bug fixes; no new features
3. **Final release**: Linus Torvalds tags the release
4. **Stable releases**: Greg Kroah-Hartman maintains stable branches with backported fixes

```bash
# Check current kernel version and release candidate
$ uname -r
6.8.0-40-generic

# View the latest mainline release
$ git -C /usr/src/linux describe --tags
v6.12-rc5
```

### Contribution Statistics

The kernel is one of the most actively developed software projects:

| Metric | Value |
|---|---|
| Lines of code | ~30 million (2024) |
| Contributors | 20,000+ since 1991 |
| Companies | 1,700+ organizations |
| Commits per release | ~10,000–15,000 |
| Release cycle | ~9–10 weeks |
| Active subsystems | 100+ |

```bash
# Count contributors to the kernel
$ git -C /usr/src/linux shortlog -sn --all | wc -l
20000+

# Top contributing companies (by commits)
$ git -C /usr/src/linux shortlog -sn --all | head -10
```

### The MAINTAINERS File

The kernel source includes a `MAINTAINERS` file that maps every subsystem to its maintainer:

```bash
# Find who maintains a subsystem
$ ./scripts/get_maintainer.pl -f drivers/net/ethernet/intel/e1000e/netdev.c
Jeff Kirsher <jeffrey.t.kirsher@intel.com> (maintainer:INTEL ETHERNET DRIVERS)
intel-wired-lan@lists.osuosl.org (open list:INTEL ETHERNET DRIVERS)
netdev@vger.kernel.org (open list:NETWORKING DRIVERS)
```

### Kernel Coding Style

The kernel has a strict coding style documented in `Documentation/process/coding-style.rst`:

```c
/*
 * Indentation: tabs (8 characters wide)
 * Braces: K&R style
 * Naming: lowercase_with_underscores
 * Functions: short and sweet, do one thing
 */

/* Good kernel code example */
static int my_driver_probe(struct platform_device *pdev)
{
	struct my_device *dev;
	int ret;

	dev = devm_kzalloc(&pdev->dev, sizeof(*dev), GFP_KERNEL);
	if (!dev)
		return -ENOMEM;

	ret = my_hw_init(dev);
	if (ret)
		return ret;

	platform_set_drvdata(pdev, dev);
	return 0;
}
```

```bash
# Check kernel coding style
$ ./scripts/checkpatch.pl my_driver.c
```

## References and Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [The Linux Kernel documentation](https://www.kernel.org/doc/html/latest/) — Official kernel documentation
- [Linux kernel source code](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git) — Torvalds' mainline tree
- [The Linux Kernel Module Programming Guide](https://sysprog21.github.io/lkmpg/) — Excellent guide to writing kernel modules
- [Linux From Scratch](https://www.linuxfromscratch.org/) — Build your own Linux system from source
- [man7.org](https://man7.org/linux/man-pages/) — Comprehensive Linux man pages
- [LWN.net](https://lwn.net/) — Linux Weekly News, covering kernel development
- [The Tanenbaum-Torvalds Debate](https://www.oreilly.com/openbook/opensources/book/appa.html) — The original 1992 debate about kernel design
- [kernel.org](https://www.kernel.org/) — Official kernel releases

## Related Topics

- [Linux History](./history.md) — The complete story from 1991 to today
- [Unix Heritage](./unix-heritage.md) — Where Linux's ideas came from
- [Distributions](./distributions.md) — Choosing and comparing Linux distributions
