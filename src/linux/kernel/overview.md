# Linux Kernel Overview

## Introduction

The Linux kernel is the core of the Linux operating system — a monolithic, Unix-like kernel first released by Linus Torvalds in 1991. It manages hardware resources, provides system services to user-space applications, and enforces security and isolation between processes. As of 2024, the Linux kernel contains over 30 million lines of code and runs on everything from embedded devices to the world's largest supercomputers.

This chapter provides a high-level overview of the kernel's design philosophy, its major subsystems, and the boundary between kernel space and user space.

## Monolithic Design with Loadable Modules

Linux follows a **monolithic kernel** architecture, meaning that the entire operating system kernel runs in a single address space with full access to all hardware. This contrasts with microkernels (like MINIX or Mach) where only minimal services run in kernel space and most OS functionality lives in user-space servers.

However, Linux is not a *pure* monolithic kernel. It supports **loadable kernel modules (LKMs)** — pieces of code that can be loaded into and unloaded from the running kernel without rebooting. This gives Linux the performance benefits of a monolithic design while retaining much of the flexibility of a microkernel.

### Why Monolithic?

Linus Torvalds famously debated Andy Tanenbaum on this topic in 1992. The key arguments for Linux's monolithic design:

1. **Performance**: Direct function calls within kernel space are far faster than inter-process communication (IPC) between user-space servers.
2. **Simplicity**: A single address space eliminates the complexity of message passing and serialization.
3. **Practicality**: Device drivers and filesystems can directly access kernel data structures without marshalling data across protection boundaries.

The counterargument — that monolithic kernels are less reliable and harder to maintain — is mitigated by the module system, code review processes, and modern debugging tools.

### Loadable Kernel Modules

Loadable modules allow the kernel to be extended at runtime:

```
┌──────────────────────────────────────────────────┐
│                  Kernel Space                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Core     │  │ Module A │  │ Module B │       │
│  │ Kernel   │  │ (loaded) │  │ (loaded) │       │
│  │          │  │          │  │          │       │
│  │ Scheduler│  │ ext4     │  │ e1000e   │       │
│  │ Memory   │  │ driver   │  │ driver   │       │
│  │ VFS      │  │          │  │          │       │
│  └──────────┘  └──────────┘  └──────────┘       │
│       ▲              ▲              ▲             │
│       │    Module    │              │             │
│       │    Interface │              │             │
│       ▼              ▼              ▼             │
│  ┌──────────────────────────────────────┐        │
│  │    Hardware Abstraction Layer         │        │
│  └──────────────────────────────────────┘        │
└──────────────────────────────────────────────────┘
```

Modules are stored as `.ko` (kernel object) files and can be:

- **Built-in**: Compiled into the kernel image (`CONFIG_*=y`)
- **Module**: Compiled as loadable modules (`CONFIG_*=m`)
- **Disabled**: Not compiled at all (`CONFIG_*=n`)

See [Chapter: Kernel Modules](modules.md) for detailed coverage of writing and managing modules.

## Kernel Space vs User Space

The CPU provides hardware-level privilege separation through **rings** (x86) or **exception levels** (ARM). Linux uses this to create two distinct execution domains:

### Ring 0 — Kernel Space

- Full access to all hardware and memory
- Runs the kernel, device drivers, and kernel threads
- A crash here (kernel panic) brings down the entire system
- Code runs with elevated privileges, no memory protection between kernel components

### Ring 3 — User Space

- Restricted access to hardware; must request services via **system calls**
- Each process has its own virtual address space
- A crash in one process does not affect others
- Applications, libraries, and most daemons run here

```
User Space (Ring 3)          Kernel Space (Ring 0)
┌─────────────────┐         ┌─────────────────────┐
│ Application     │         │                     │
│ (e.g., bash)    │  syscall│   System Call        │
│                 │────────▶│   Interface          │
│ glibc           │         │                     │
│                 │◀────────│   VFS, Scheduler,    │
│ Virtual Memory  │  return │   Memory Manager,    │
│ (per-process)   │         │   Device Drivers     │
└─────────────────┘         │                     │
                            │   Hardware Access    │
                            └─────────────────────┘
```

### System Calls — The Gateway

System calls are the controlled entry points from user space into the kernel. On x86-64, a system call is invoked via the `syscall` instruction:

```c
// Simplified system call flow (x86-64)
static long sys_write(unsigned int fd, const char __user *buf, size_t count)
{
    struct fd f = fdget_pos(fd);
    if (f.file) {
        loff_t pos = *f.pos;
        ret = vfs_write(f.file, buf, count, &pos);
        *f.pos = pos;
        fdput_pos(f);
    }
    return ret;
}
```

The kernel maintains a **system call table** (`sys_call_table` on x86) that maps syscall numbers to handler functions:

```bash
# View the system call table
$ cat /usr/include/asm/unistd_64.h | head -20
#define __NR_read 0
#define __NR_write 1
#define __NR_open 2
#define __NR_close 3
#define __NR_stat 4
#define __NR_fstat 5
```

```bash
# Trace system calls for a command
$ strace ls /tmp 2>&1 | head -15
execve("/usr/bin/ls", ["ls", "/tmp"], 0x7ffd4a3b2c40 /* 42 vars */) = 0
brk(NULL)                               = 0x55a3c4e6e000
access("/etc/ld.so.preload", R_OK)      = -1 ENOENT
openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
fstat(3, {st_mode=S_IFREG|0644, st_size=78432, ...}) = 0
mmap(NULL, 78432, PROT_READ, MAP_PRIVATE, 3, 0) = 0x7f8b2c400000
close(3)                                = 0
```

## Major Kernel Subsystems

The Linux kernel is organized into several major subsystems, each responsible for a specific aspect of system management:

### 1. Process Scheduler

The scheduler determines which process runs on each CPU core and for how long. Linux uses the **Completely Fair Scheduler (CFS)** by default, which uses a red-black tree to track runnable tasks by their virtual runtime.

```bash
# View scheduling policy of a process
$ chrt -p $$
pid 1234's current scheduling policy: SCHED_OTHER
pid 1234's current scheduling priority: 0

# List available scheduling policies
$ chrt --help 2>&1 | grep -A5 policy
```

Key characteristics:
- **O(log n)** scheduling decisions via red-black tree
- **Per-CPU run queues** for scalability
- **Nice values** (-20 to 19) for priority adjustment
- **Real-time scheduling** classes: `SCHED_FIFO` and `SCHED_RR`
- **EEVDF scheduler** introduced in kernel 6.6 as the successor to CFS

See Process Scheduler for detailed coverage.

### 2. Memory Management

The memory management subsystem handles:

- **Virtual memory** with per-process address spaces
- **Page allocation** via the buddy allocator
- **Slab allocation** for kernel objects (SLUB allocator)
- **Page cache** for file I/O performance
- **Swap management** for overcommitting physical memory
- **Memory-mapped I/O** (`mmap`)

```bash
# View memory information
$ cat /proc/meminfo | head -10
MemTotal:       16384000 kB
MemFree:         8234560 kB
MemAvailable:   12345678 kB
Buffers:          524288 kB
Cached:          3145728 kB
SwapCached:            0 kB
Active:          4194304 kB
Inactive:        2097152 kB

# View per-process memory maps
$ cat /proc/self/maps | head -5
55a3c4e00000-55a3c4e26000 r--p 00000000 08:01 12345  /usr/bin/cat
55a3c4e26000-55a3c4e5a000 r-xp 00026000 08:01 12345  /usr/bin/cat
55a3c4e5a000-55a3c4e66000 r--p 0005a000 08:01 12345  /usr/bin/cat
```

See Memory Management for detailed coverage.

### 3. Virtual File System (VFS)

VFS provides an abstraction layer that allows Linux to support multiple filesystem types through a uniform interface:

```c
// VFS key operations structure
struct file_operations {
    struct module *owner;
    loff_t (*llseek)(struct file *, loff_t, int);
    ssize_t (*read)(struct file *, char __user *, size_t, loff_t *);
    ssize_t (*write)(struct file *, const char __user *, size_t, loff_t *);
    int (*open)(struct inode *, struct file *);
    int (*release)(struct inode *, struct file *);
    // ... many more
};
```

Supported filesystem types include: ext4, XFS, Btrfs, ZFS, NTFS, FAT, tmpfs, procfs, sysfs, and many more.

```bash
# List mounted filesystems
$ mount | column -t
/dev/sda1    on  /          type  ext4         (rw,relatime)
devtmpfs     on  /dev       type  devtmpfs     (rw,nosuid)
tmpfs        on  /dev/shm   type  tmpfs        (rw,nosuid,nodev)
proc         on  /proc      type  proc         (rw,nosuid,nodev,noexec)
sysfs        on  /sys       type  sysfs        (rw,nosuid,nodev,noexec)
```

### 4. Network Subsystem

The networking stack implements the full TCP/IP protocol suite and provides socket-based communication:

```
┌─────────────────────────────────────────┐
│           User-space Application        │
├─────────────────────────────────────────┤
│           Socket Interface              │
├──────────┬──────────┬───────────────────┤
│   TCP    │   UDP    │  Other Protocols  │
├──────────┴──────────┴───────────────────┤
│           IP Layer (IPv4/IPv6)          │
├─────────────────────────────────────────┤
│     Network Device Interface Layer      │
├──────────┬──────────┬───────────────────┤
│ Ethernet │   WiFi   │  Other Drivers    │
└──────────┴──────────┴───────────────────┘
```

```bash
# View network statistics
$ cat /proc/net/snmp | head -10
Ip: Forwarding DefaultTTL InReceives InHdrErrors InAddrErrors
Ip: 2 64 1234567 0 0
Tcp: RtoAlgorithm RtoMin RtoMax MaxConn ActiveOpens
Tcp: 1 200 120000 -1 5432
```

### 5. Device Drivers

Device drivers constitute the largest portion of the kernel source tree (~60%). They provide a uniform interface for hardware devices:

```bash
# View loaded kernel modules (drivers)
$ lsmod | head -10
Module                  Size  Used by
ext4                  786432  1
mbcache                16384  1 ext4
jbd2                  131072  1 ext4
e1000e                294912  0
xhci_pci               20480  0
```

```bash
# View hardware information
$ lspci | head -5
00:00.0 Host bridge: Intel Corporation Xeon E3-1200 v5
00:02.0 VGA compatible controller: Intel Corporation HD 530
00:14.0 USB controller: Intel Corporation 100 Series/C230
00:1f.2 SATA controller: Intel Corporation Q170/H170 SATA
```

### 6. Inter-Process Communication (IPC)

Linux supports multiple IPC mechanisms:

| Mechanism | Description | System Call |
|-----------|-------------|-------------|
| Pipes | Unidirectional byte stream | `pipe()`, `pipe2()` |
| Signals | Asynchronous notifications | `kill()`, `signal()` |
| Shared Memory | Fastest IPC, shared address space | `shmget()`, `mmap()` |
| Message Queues | Structured message passing | `msgget()`, `mq_open()` |
| Semaphores | Synchronization primitives | `semget()`, `sem_init()` |
| Unix Sockets | Bidirectional communication | `socket(AF_UNIX)` |
| D-Bus | High-level IPC (user-space) | N/A |

### 7. Security Subsystem

Linux provides multiple security frameworks:

- **DAC** (Discretionary Access Control): Traditional Unix permissions
- **MAC** (Mandatory Access Control): SELinux, AppArmor
- **Capabilities**: Fine-grained privilege model
- **Seccomp**: System call filtering
- **Namespaces & cgroups**: Isolation and resource control (containers)

```bash
# Check SELinux status
$ getenforce
Enforcing

# View capabilities of a binary
$ getcap /usr/bin/ping
/usr/bin/ping = cap_net_raw+ep
```

## Preemption Models

Linux supports several preemption models that determine when the kernel
can be preempted:

| Model | Config | Description |
|---|---|---|
| No Forced Preemption | `PREEMPT_NONE` | Server default; best throughput |
| Voluntary Preemption | `PREEMPT_VOLUNTARY` | Explicit preemption points |
| Full Preemption | `PREEMPT` | Preempt almost anywhere; best latency |
| Real-Time (PREEMPT_RT) | `PREEMPT_RT` | Full RT with threaded interrupts |

```bash
# Check current preemption model
$ cat /sys/kernel/debug/sched/preempt
# none | voluntary | full

# Or from kernel config
$ zcat /proc/config.gz | grep PREEMPT
CONFIG_PREEMPT_NONE=y
# CONFIG_PREEMPT_VOLUNTARY is not set
# CONFIG_PREEMPT is not set
```

### Real-Time Kernel (PREEMPT_RT)

The PREEMPT_RT patchset makes the Linux kernel fully preemptible:

- **Threaded interrupts**: IRQ handlers run as kernel threads.
- **Priority inheritance**: Spinlocks become RT-mutexes.
- **Deterministic latency**: Sub-100µs worst-case latency.

```bash
# Check if running RT kernel
$ uname -v
# Look for "PREEMPT_RT" in version string
$ uname -v
Linux version 6.1.0-rt7 (... #1 SMP PREEMPT_RT ...)

# View RT latency
$ cyclictest -t1 -p80 -i1000 -l1000
# T: 0 (12345) P:80 I:1000 C:  1000 Min:      1 Act:    3 Max:   15
```

## Kernel Debugging and Tracing

### printk and dmesg

```c
/* Kernel log levels */
#define KERN_EMERG    "<0>"   /* System is unusable */
#define KERN_ALERT    "<1>"   /* Action must be taken immediately */
#define KERN_CRIT     "<2>"   /* Critical conditions */
#define KERN_ERR      "<3>"   /* Error conditions */
#define KERN_WARNING  "<4>"   /* Warning conditions */
#define KERN_NOTICE   "<5>"   /* Normal but significant */
#define KERN_INFO     "<6>"   /* Informational */
#define KERN_DEBUG    "<7>"   /* Debug-level messages */

pr_info("driver loaded: version %s\n", VERSION);
pr_err("device timeout on %s\n", dev_name(dev));
```

```bash
# View kernel messages
$ dmesg | tail -20
$ dmesg -l err,crit,alert,emerg  # Only errors and above
$ dmesg --follow  # Live follow

# Control console log level
$ cat /proc/sys/kernel/printk
7       4       1       7
# console_loglevel default_level minimum_level boot_delay
```

### Dynamic Debug

```bash
# Enable debug messages for a specific module
$ echo 'module my_driver +p' > /sys/kernel/debug/dynamic_debug/control

# Enable all debug messages in a file
$ echo 'file drivers/net/ethernet/intel/e1000e/netdev.c +p' > /sys/kernel/debug/dynamic_debug/control

# View all enabled debug points
$ cat /sys/kernel/debug/dynamic_debug/control | grep '=p'
```

### kprobes and kretprobes

```c
#include <linux/kprobes.h>

static struct kprobe kp = {
    .symbol_name = "do_sys_open",
};

static int handler_pre(struct kprobe *p, struct pt_regs *regs)
{
    pr_info("do_sys_open called\n");
    return 0;
}

static int __init kprobe_init(void)
{
    kp.pre_handler = handler_pre;
    return register_kprobe(&kp);
}
```

### ftrace

```bash
# List available tracers
$ cat /sys/kernel/debug/tracing/available_tracers
function function_graph nop

# Trace a specific function
$ echo 'do_sys_open' > /sys/kernel/debug/tracing/set_ftrace_filter
$ echo function > /sys/kernel/debug/tracing/current_tracer
$ echo 1 > /sys/kernel/debug/tracing/tracing_on
$ cat /sys/kernel/debug/tracing/trace_pipe | head -20

# Function graph tracer
$ echo function_graph > /sys/kernel/debug/tracing/current_tracer
$ echo 1 > /sys/kernel/debug/tracing/tracing_on
```

### BPF and bpftrace

```bash
# Trace system calls
$bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# Count syscalls by process
$bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'

# Trace block I/O latency
$bpftrace -e '
tracepoint:block:block_rq_complete {
    @usecs = hist((nsecs - @start[args->dev, args->sector]) / 1000);
}
tracepoint:block:block_rq_issue {
    @start[args->dev, args->sector] = nsecs;
}'
```

## Namespaces and Containers

Linux namespaces provide process isolation:

| Namespace | Flag | Isolates |
|---|---|---|
| PID | `CLONE_NEWPID` | Process IDs |
| Network | `CLONE_NEWNET` | Network stack |
| Mount | `CLONE_NEWNS` | Filesystem mounts |
| UTS | `CLONE_NEWUTS` | Hostname |
| IPC | `CLONE_NEWIPC` | IPC resources |
| User | `CLONE_NEWUSER` | User/group IDs |
| Cgroup | `CLONE_NEWCGROUP` | Cgroup root |
| Time | `CLONE_NEWTIME` | System clocks |

```bash
# Create a namespace
$ unshare --pid --net --mount --uts --ipc --fork /bin/bash

# List namespaces of a process
$ ls -la /proc/$$/ns/
total 0
lrwxrwxrwx 1 root root 0 Jul 21 10:00 cgroup -> 'cgroup:[4026531835]'
lrwxrwxrwx 1 root root 0 Jul 21 10:00 ipc -> 'ipc:[4026531839]'
lrwxrwxrwx 1 root root 0 Jul 21 10:00 mnt -> 'mnt:[4026531841]'
lrwxrwxrwx 1 root root 0 Jul 21 10:00 net -> 'net:[4026531969]'
lrwxrwxrwx 1 root root 0 Jul 21 10:00 pid -> 'pid:[4026531836]'
```

## Control Groups (cgroups)

cgroups provide resource limiting, prioritization, and accounting:

```bash
# cgroup v2 hierarchy
$ mount | grep cgroup
cgroup2 on /sys/fs/cgroup type cgroup2 (rw,nosuid,nodev,noexec)

# Create a cgroup
$ mkdir /sys/fs/cgroup/mygroup

# Set CPU limit
$ echo 50000 100000 > /sys/fs/cgroup/mygroup/cpu.max
# 50% of one CPU (50ms per 100ms period)

# Set memory limit
$ echo 1073741824 > /sys/fs/cgroup/mygroup/memory.max
# 1 GiB limit

# Assign process
$ echo $PID > /sys/fs/cgroup/mygroup/cgroup.procs

# View stats
$ cat /sys/fs/cgroup/mygroup/cpu.stat
usage_usec 123456789
user_usec 100000000
system_usec 23456789
```

## seccomp (System Call Filtering)

seccomp restricts which system calls a process can make:

```c
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>

/* BPF filter to allow only read, write, exit */
struct sock_filter filter[] = {
    BPF_STMT(BPF_LD+BPF_W+BPF_ABS, offsetof(struct seccomp_data, nr)),
    BPF_JUMP(BPF_JMP+BPF_JEQ+BPF_K, __NR_read, 0, 1),
    BPF_STMT(BPF_RET+BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP+BPF_JEQ+BPF_K, __NR_write, 0, 1),
    BPF_STMT(BPF_RET+BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP+BPF_JEQ+BPF_K, __NR_exit_group, 0, 1),
    BPF_STMT(BPF_RET+BPF_K, SECCOMP_RET_ALLOW),
    BPF_STMT(BPF_RET+BPF_K, SECCOMP_RET_KILL_PROCESS),
};
```

```bash
# Check seccomp status
$ cat /proc/$$/status | grep Seccomp
Seccomp:    0    # 0=disabled, 1=strict, 2=filter

# Use strace to see seccomp kills
$strace -f ./sandboxed_app 2>&1 | grep SECCOMP
```

## Kernel Version Numbers

Linux kernel versions follow the format `MAJOR.MINOR.PATCH`:

```
6.1.0
│ │ └── Patch level (bug fixes, security)
│ └──── Minor version (new features, drivers)
└────── Major version (fundamental changes)
```

Starting from kernel 3.0, the version numbering shifted: the "major" number is incremented for significant milestones, while the "minor" number increments with each release. Odd minor numbers (e.g., 5.17-rc1) denote development kernels.

```bash
# Check your kernel version
$ uname -r
6.1.0-23-amd64

# Detailed kernel version info
$ uname -a
Linux hostname 6.1.0-23-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.1.97-1 x86_64 GNU/Linux

# Check kernel build config
$ cat /proc/version
Linux version 6.1.0-23-amd64 (debian-kernel@lists.debian.org) (gcc-12 (Debian 12.2.0-14) 12.2.0, GNU ld (GNU Binutils for Debian) 2.40) #1 SMP PREEMPT_DYNAMIC Debian 6.1.97-1
```

## Kernel Source Tree Layout

The kernel source tree is organized as follows:

```
linux/
├── arch/           # Architecture-specific code (x86, arm64, etc.)
│   ├── x86/
│   ├── arm64/
│   └── ...
├── block/          # Block I/O layer
├── certs/          # Signing certificates for module verification
├── crypto/         # Cryptographic API
├── Documentation/  # Kernel documentation
├── drivers/        # Device drivers (largest subsystem)
├── fs/             # Filesystem implementations
├── include/        # Kernel header files
├── init/           # Kernel initialization code
├── ipc/            # Inter-process communication
├── kernel/         # Core kernel (scheduler, signals, etc.)
├── lib/            # Helper functions and library routines
├── mm/             # Memory management
├── net/            # Networking stack
├── samples/        # Example code
├── scripts/        # Build scripts and helper tools
├── security/       # Security frameworks (SELinux, AppArmor)
├── sound/          # Audio subsystem
├── tools/          # User-space tools (perf, etc.)
├── usr/            # initramfs support
└── virt/           # Virtualization support (KVM)
```

```bash
# Count lines of code by subsystem
$ find . -name '*.c' -o -name '*.h' | head -1000 | xargs wc -l | tail -1
# Or use cloc
$ cloc --by-file --include-lang=C drivers/ | tail -5
```

## Kernel Configuration System

The kernel is highly configurable through the **Kconfig** system. Each feature can be:

- Built into the kernel image (`=y`)
- Compiled as a loadable module (`=m`)
- Disabled (`# ... is not set`)

```bash
# Configure the kernel
$ make menuconfig     # ncurses-based menu
$ make xconfig        # Qt-based GUI
$ make gconfig        # GTK-based GUI
$ make olddefconfig   # Use existing .config, defaults for new options
```

See [Chapter: Build System](build-system.md) and [Chapter: Configuration](configuration.md) for details.

## Kernel Development Model

The Linux kernel uses a time-based release model:

- **Merge window**: ~2 weeks after each release, new features are merged
- **Release candidates**: Weekly RC builds after merge window closes
- **Stable releases**: Final release after ~7 RCs
- **Long-term support (LTS)**: Selected versions maintained for 2-6 years

```bash
# View current kernel releases
$ curl -s https://www.kernel.org | grep -oP 'linux-\K[0-9]+\.[0-9]+(\.[0-9]+)?'
```

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [The Linux Kernel documentation](https://www.kernel.org/doc/html/latest/)
- [Linux Kernel Newbies](https://kernelnewbies.org/)
- [Linux kernel mailing list FAQ](http://vger.kernel.org/lkml/)
- [LWN.net kernel coverage](https://lwn.net/Kernel/)
- [Torvalds-Tanenbaum debate](https://en.wikipedia.org/wiki/Tanenbaum%E2%80%93Torvalds_debate)
- [Understanding the Linux Kernel, 3rd Edition](https://www.oreilly.com/library/view/understanding-the-linux/0596005652/) — Bovet & Cesati
- [Linux Kernel Development, 3rd Edition](https://www.oreilly.com/library/view/linux-kernel-development/9780768696974/) — Robert Love

## Related Topics

- [Kernel Architecture](architecture.md) — Detailed subsystem relationships
- [Build System](build-system.md) — How the kernel is compiled
- [Configuration](configuration.md) — Customizing kernel features
- [Kernel Modules](modules.md) — Extending the kernel at runtime
- [Boot Process](boot-process.md) — How the kernel starts
- [Command Line Parameters](cmdline-params.md) — Kernel boot parameters
- [Data Structures](data-structures.md) — Core kernel data structures
