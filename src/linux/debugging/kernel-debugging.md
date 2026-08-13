# Kernel Debugging

## Introduction

Debugging the Linux kernel is fundamentally different from debugging user-space programs.
A bug in the kernel can crash the entire system, corrupt memory invisibly, or manifest
as a random failure minutes later. Kernel debugging tools range from simple print-based
debugging to interactive debuggers and post-mortem crash analysis.

This page covers the major kernel debugging techniques and tools: printk, dynamic debug,
KGDB, KDB, kdump, and the crash utility. Each addresses different debugging scenarios,
from simple log messages to full interactive kernel debugging with hardware debuggers.

## The Kernel Debugging Landscape

```
┌──────────────────────────────────────────────────────────────┐
│                    Kernel Debugging Tools                      │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   printk    │  │   Dynamic   │  │    KASAN/UBSAN      │ │
│  │  (logging)  │  │   Debug     │  │  (sanitizers)       │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    KGDB     │  │     KDB     │  │    kdump + crash    │ │
│  │(remote gdb) │  │(interactive)│  │  (post-mortem)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   ftrace    │  │    perf     │  │    eBPF             │ │
│  │ (tracing)   │  │ (profiling) │  │ (programmable)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## printk — The Kernel's printf

`printk` is the most fundamental kernel debugging tool. It writes messages to the
kernel ring buffer, which can be read via `dmesg` or `/dev/kmsg`.

### Log Levels

```c
// Kernel log levels (0 = highest priority)
#define KERN_EMERG    "<0>"  // System is unusable
#define KERN_ALERT    "<1>"  // Action must be taken immediately
#define KERN_CRIT     "<2>"  // Critical conditions
#define KERN_ERR      "<3>"  // Error conditions
#define KERN_WARNING  "<4>"  // Warning conditions
#define KERN_NOTICE   "<5>"  // Normal but significant
#define KERN_INFO     "<6>"  // Informational
#define KERN_DEBUG    "<7>"  // Debug-level messages

// Usage
printk(KERN_ERR "mydriver: failed to allocate %zu bytes\n", size);
printk(KERN_DEBUG "mydriver: entering function %s\n", __func__);
pr_err("mydriver: failed to allocate %zu bytes\n", size);  // preferred macro
pr_debug("mydriver: value = %d\n", value);  // compiled out unless DEBUG defined
```

### Best Practices for printk

```c
// Use pr_fmt to prefix all messages
#define pr_fmt(fmt) KBUILD_MODNAME ": " fmt
#include <linux/printk.h>

// Now all pr_* calls are automatically prefixed
pr_info("device initialized\n");  // Output: "mydriver: device initialized"

// Use dev_dbg/dev_err for device-specific messages
dev_dbg(&pdev->dev, "probe called\n");
dev_err(&pdev->dev, "failed to map registers: %ld\n", PTR_ERR(base));

// Use pr_info_ratelimited to avoid flooding
pr_info_ratelimited("unexpected interrupt %d\n", irq);

// Use printk_once for one-time messages
pr_warn_once("using deprecated API\n");
```

### Reading Kernel Messages

```bash
# Read kernel ring buffer
dmesg

# Follow new messages
dmesg -w

# Filter by level
dmesg -l err,crit,alert,emerg

# With timestamps
dmesg -T

# JSON output
dmesg -J

# Clear ring buffer
dmesg -c

# Read from /dev/kmsg (persistent)
cat /dev/kmsg
```

### Controlling Console Log Level

```bash
# Show current console log level
cat /proc/sys/kernel/printk
# 4 4 1 7
# ─ ─ ─ ─
# │ │ │ └── Default level for new consoles
# │ │ └──── Minimum level for console
# │ └────── Default level for printk
# └──────── Current console log level

# Show all messages on console (including debug)
echo 8 > /proc/sys/kernel/printk

# Show only critical messages
echo 1 > /proc/sys/kernel/printk
```

## Dynamic Debug

Dynamic debug (`dyndbg`) allows you to enable/disable kernel debug messages at runtime
without recompiling. It works with `pr_debug()` and `dev_dbg()` calls that are compiled
with `CONFIG_DYNAMIC_DEBUG`.

### Usage

```bash
# Enable debug for a specific file
echo 'file drivers/usb/core/usb.c +p' > /sys/kernel/debug/dynamic_debug/control

# Enable debug for a specific function
echo 'func usb_probe_interface +p' > /sys/kernel/debug/dynamic_debug/control

# Enable debug for a module
echo 'module xhci_hcd +p' > /sys/kernel/debug/dynamic_debug/control

# Enable debug for a specific line
echo 'file drivers/usb/core/usb.c line 123 +p' > /sys/kernel/debug/dynamic_debug/control

# Disable debug
echo 'file drivers/usb/core/usb.c -p' > /sys/kernel/debug/dynamic_debug/control

# Enable with format string match
echo 'file drivers/usb/core/usb.c format "probe" +p' > /sys/kernel/debug/dynamic_debug/control

# Show all enabled debug points
cat /sys/kernel/debug/dynamic_debug/control | grep '=p'

# Enable all debug messages (very noisy!)
echo '+p' > /sys/kernel/debug/dynamic_debug/control
```

### Boot-Time Activation

```bash
# Enable via kernel command line
# In GRUB: dyndbg="file drivers/usb/core/usb.c +p"
# Or:       dyndbg="module xhci_hcd +p"
# Or:       dyndbg="+p"  (enable all)

# Via /etc/default/grub
GRUB_CMDLINE_LINUX="dyndbg=\"module mymodule +p\""
```

### Dynamic Debug Flags

| Flag | Meaning |
|------|---------|
| `+p` | Enable message |
| `-p` | Disable message |
| `+f` | Show function name |
| `+l` | Show line number |
| `+m` | Show module name |
| `+t` | Show thread ID |
| `_` | No flags (reset) |

## KASAN — Kernel Address Sanitizer

KASAN detects memory errors in the kernel: use-after-free, out-of-bounds access,
stack buffer overflow, and more.

### Enabling KASAN

```bash
# Kernel config
CONFIG_KASAN=y
CONFIG_KASAN_GENERIC=y          # Software-based (slower, more compatible)
# or
CONFIG_KASAN_SW_TAGS=y          # ARM64 MTE-based (faster on supported hardware)

# Runtime options
CONFIG_KASAN_INLINE=y           # Inline instrumentation (faster, larger kernel)
# or
CONFIG_KASAN_OUTLINE=y          # Outline instrumentation (slower, smaller kernel)
```

### KASAN Output Example

```
==================================================================
BUG: KASAN: use-after-free in mydriver_process+0x123/0x456
Read of size 8 at addr ffff888012345678 by task myprocess/1234

CPU: 0 PID: 1234 Comm: myprocess Not tainted 5.15.0 #1
Hardware name: QEMU Standard PC
Call Trace:
 dump_stack+0x89/0xcb
 print_report+0x172/0x4a0
 kasan_report+0xad/0xe0
 mydriver_process+0x123/0x456
 mydriver_handler+0x78/0x123
 ...

Allocated by task 1234:
 kmem_cache_alloc+0xd1/0x1f0
 mydriver_alloc+0x45/0x89
 mydriver_init+0x23/0x67
 ...

Freed by task 1234:
 kmem_cache_free+0x87/0x190
 mydriver_free+0x34/0x56
 mydriver_cleanup+0x12/0x34
 ...
==================================================================
```

## UBSAN — Undefined Behavior Sanitizer

UBSAN detects undefined behavior at runtime: integer overflow, shift out of bounds,
misaligned access, etc.

```bash
# Kernel config
CONFIG_UBSAN=y
CONFIG_UBSAN_SANITIZE_ALL=y

# Select specific checks
CONFIG_UBSAN_BOUNDS=y
CONFIG_UBSAN_SHIFT=y
CONFIG_UBSAN_DIV_ZERO=y
CONFIG_UBSAN_BOOL=y
CONFIG_UBSAN_ENUM=y
```

## KGDB — Kernel GDB

KGDB allows you to debug the kernel using GDB over a serial connection or network.
It provides full interactive debugging with breakpoints, single-stepping, and
variable inspection.

### Architecture

```
┌────────────────┐  Serial/Network  ┌────────────────┐
│   Development  │◄────────────────►│  Target Machine│
│   Machine      │  (kgdboc/ttyS0)  │  (KGDB stub)   │
│                │                  │                 │
│  ┌──────────┐  │                  │  ┌───────────┐  │
│  │   GDB    │  │                  │  │  Kernel   │  │
│  │(vmlinux) │  │                  │  │  being    │  │
│  │          │  │                  │  │  debugged │  │
│  └──────────┘  │                  │  └───────────┘  │
└────────────────┘                  └────────────────┘
```

### Setup

#### Kernel Configuration

```
CONFIG_KGDB=y
CONFIG_KGDB_SERIAL_CONSOLE=y
CONFIG_KGDB_KDB=y
CONFIG_FRAME_POINTER=y        # Better stack traces
CONFIG_DEBUG_INFO=y            # Debug symbols
CONFIG_GDB_SCRIPTS=y           # GDB helper scripts
```

#### Target Machine

```bash
# Boot with kgdb parameters
# In GRUB: kgdboc=ttyS0,115200 kgdbcon

# Or set at runtime
echo ttyS0 > /sys/module/kgdboc/parameters/kgdboc

# Enter KGDB (trigger breakpoint)
echo g > /proc/sysrq-trigger

# Or use sysrq from keyboard: Alt+SysRq+g
```

#### Development Machine

```bash
# Connect serial cable, then:
gdb vmlinux

# Connect to target
(gdb) target remote /dev/ttyS0
# Or for network:
(gdb) target remote :1234

# Set baud rate
(gdb) set serial baud 115200

# Continue execution
(gdb) continue

# Set breakpoint
(gdb) break mydriver_probe

# When breakpoint hits, inspect
(gdb) bt
(gdb) print pdev->name
(gdb) info threads
(gdb) thread apply all bt
```

### KGDB with QEMU

```bash
# Start QEMU with KGDB support
qemu-system-x86_64 -kernel bzImage -append "console=ttyS0 kgdboc=ttyS0,115200" \
    -nographic -s -S -hda rootfs.img

# Connect GDB
gdb vmlinux
(gdb) target remote :1234
(gdb) break start_kernel
(gdb) continue
```

## KDB — Kernel Debugger

KDB is a simpler, built-in kernel debugger that runs directly on the target machine's
console. No external connection needed.

### Basic KDB Commands

```bash
# Enter KDB
echo g > /proc/sysrq-trigger
# Or: Alt+SysRq+g

# KDB commands
kdb> bp mydriver_probe         # Set breakpoint
kdb> bl                        # List breakpoints
kdb> bc 1                      # Clear breakpoint 1
kdb> go                        # Continue execution
kdb> bt                        # Backtrace
kdb> bt 1234                   # Backtrace of PID 1234
kdb> lsmod                     # List modules
kdb> ps                        # Process list
kdb> cpu                       # CPU info
kdb> dmesg                     # Kernel log
kdb> md 0xffffffff81000000 16  # Memory dump (16 lines)
kdb> mm 0xaddr 0xvalue         # Memory modify
kdb> rd                        # Read registers
kdb> id 0xffffffff81000000     # Disassemble
kdb> sr                        # Show stack (current)
kdb> env                       # Environment
kdb> set KDBFLAGS 0            # Set flags
kdb> help                      # Help
kdb> reboot                    # Reboot
```

### KDB vs KGDB

| Feature | KDB | KGDB |
|---------|-----|------|
| Interface | Console (text) | GDB (remote) |
| Breakpoints | Simple | Conditional, watchpoints |
| Single-step | Instruction only | Source-level |
| Variables | Manual address | Symbol names |
| Stack trace | Basic | Full with source |
| Ease of setup | Built-in | Requires serial/network |
| Use case | Quick inspection | Deep debugging |

## kdump — Kernel Crash Dumps

kdump captures the kernel's memory state at the moment of a crash, allowing
post-mortem analysis with the crash utility.

### How kdump Works

```
┌─────────────────────────────────────────────┐
│           Normal Boot                        │
│  ┌────────────────────────────────────────┐ │
│  │  Production Kernel (1st kernel)        │ │
│  │  Crash → kexec into capture kernel     │ │
│  └────────────────────┬───────────────────┘ │
│                       │ kexec (fast reboot)  │
│  ┌────────────────────▼───────────────────┐ │
│  │  Capture Kernel (2nd kernel)           │ │
│  │  Runs in reserved memory region        │ │
│  │  Saves /proc/vmcore to disk            │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### Setup

```bash
# Install kdump tools
# Debian/Ubuntu:
sudo apt install linux-crashdump kdump-tools
# RHEL/Fedora:
sudo dnf install kexec-tools crash

# Enable kdump
sudo systemctl enable kdump
sudo systemctl start kdump

# Configure memory reservation
# In GRUB: crashkernel=256M
# Or in /etc/default/grub:
GRUB_CMDLINE_LINUX="crashkernel=256M"
sudo update-grub

# Verify kdump status
sudo kdump-config show
sudo systemctl status kdump
```

### Testing kdump

```bash
# Trigger a crash (DANGEROUS — do in test environment only!)
echo c > /proc/sysrq-trigger

# After reboot, check for crash dump
ls -la /var/crash/

# The dump file is at /var/crash/*/vmcore
```

### Analyzing Crash Dumps

```bash
# Open crash dump
sudo crash /usr/lib/debug/boot/vmlinux-$(uname -r) /var/crash/*/vmcore

# Or with System.map
sudo crash vmlinux /var/crash/*/vmcore /boot/System.map-$(uname -r)
```

## crash Utility

The `crash` utility is the primary tool for analyzing kernel crash dumps. It provides
an interactive environment similar to GDB for examining kernel state.

### Basic crash Commands

```
crash> bt                    # Backtrace of crashing task
crash> bt -a                # Backtrace of all active tasks
crash> bt -l                # With line numbers

crash> log                  # Kernel log (dmesg)
crash> log -m               # Messages from specific buffer

crash> ps                   # Process list
crash> ps -m                # Show memory usage
crash> ps | grep UN         # Find tasks in UNINTERRUPTIBLE state

crash> vm                  # Virtual memory info
crash> vm -p 1234          # VM of specific task
crash> vm -f               # Show page flags

crash> files 1234          # Open files of task
crash> net                 # Network info
crash> sys                 # System info
crash> mod                 # Loaded modules

crash> struct task_struct ffff888012345678    # Dump structure
crash> struct task_struct.pid ffff888012345678  # Single field

crash> dis do_sys_open    # Disassemble function
crash> dis 0xffffffff81000000  # Disassemble at address

crash> rd 0xffffffff81000000 16  # Read memory
crash> rd -8 0xffffffff81000000 16  # 8-byte words

crash> sym 0xffffffff81000000   # Symbol lookup
crash> sym -m mymodule          # Module symbols

crash> task -r 1234         # Task registers
crash> task -f 1234         # Task flags
crash> runq                 # Run queues

crash> swap                 # Swap info
crash> kmem -i              # Memory usage summary
crash> kmem -s              # Slab info
crash> kmem -v 0xffff888012345000  # Virtual to physical

crash> mount                # Mounted filesystems
crash> mount -f             # Super blocks

crash> exit                 # Exit crash
```

### Analyzing a Crash

```
crash> log | tail -50
[  123.456789] BUG: unable to handle kernel NULL pointer dereference at 0000000000000010
[  123.456790] PGD 0 P4D 0
[  123.456791] Oops: 0000 [#1] SMP PTI
[  123.456792] CPU: 2 PID: 1234 Comm: myprocess Not tainted 5.15.0 #1

crash> bt
PID: 1234  TASK: ffff888012345600  CPU: 2   COMMAND: "myprocess"
 #0 [ffff888012345a00] machine_kexec at ffffffff81001234
 #1 [ffff888012345a58] __crash_kexec at ffffffff81089012
 #2 [ffff888012345b20] panic at ffffffff81078934
 #3 [ffff888012345ba0] oops_end at ffffffff81002345
 #4 [ffff888012345bc0] no_context at ffffffff81004567
 #5 [ffff888012345c00] __bad_area_nosemaphore at ffffffff81004890
 #6 [ffff888012345c40] do_page_fault at ffffffff81005678
 #7 [ffff888012345d00] page_fault at ffffffff81800123
 #8 [ffff888012345d80] mydriver_process at ffffffff82000456 [mydriver]
 #9 [ffff888012345e00] mydriver_handler at ffffffff82000789 [mydriver]

crash> struct task_struct.comm ffff888012345600
  comm = "myprocess\000\000\000\000\000"

crash> dis mydriver_process
0xffffffff82000456 <mydriver_process>:  push   %rbp
0xffffffff82000457 <mydriver_process+1>:  mov    %rsp,%rbp
0xffffffff8200045a <mydriver_process+4>:  mov    0x10(%rdi),%rax
0xffffffff8200045e <mydriver_process+8>:  mov    0x10(%rax),%rdx   ← crash here
0xffffffff82000462 <mydriver_process+12>: test   %rdx,%rdx
```

### crash with Modules

```bash
# Load module debug info
crash> mod -s mydriver /path/to/mydriver.ko

# List module symbols
crash> sym -m mydriver

# Translate address in module
crash> sym 0xffffffffa0000456
```

## Kernel Debugging Techniques

### Binary Search for Regressions (git bisect)

```bash
# Start bisect
git bisect start
git bisect bad                 # Current version is bad
git bisect good v5.14          # v5.14 was good

# Git will checkout middle commits
# Build and test each one
git bisect good                # If this version works
git bisect bad                 # If this version is broken

# Automate with a test script
git bisect run ./test_kernel.sh

# Finish bisect
git bisect reset
```

### Lockdep — Lock Dependency Validator

```bash
# Enable lockdep
CONFIG_LOCKDEP=y
CONFIG_PROVE_LOCKING=y
CONFIG_DEBUG_LOCK_ALLOC=y

# Lockdep detects:
# - Deadlock potential (circular locking dependencies)
# - Lock ordering violations
# - Missing lock releases
# - RCU violations

# Example lockdep output:
# =============================================
# WARNING: possible circular locking dependency detected
# 5.15.0 #1 Not tainted
# ---------------------------------------------
# myprocess/1234 is trying to acquire lock:
#  ffff888012345678 (&lock_A){+.+.}-{3:3}, at: my_func+0x12/0x34
# but task already holds lock:
#  ffff888012345690 (&lock_B){+.+.}-{3:3}, at: my_func+0x56/0x78
# which lock already depends on the new lock.
```

### Kmemleak — Memory Leak Detector

```bash
# Enable kmemleak
CONFIG_DEBUG_KMEMLEAK=y

# Trigger scan
echo scan > /sys/kernel/debug/kmemleak

# Read results
cat /sys/kernel/debug/kmemleak

# Clear
echo clear > /sys/kernel/debug/kmemleak
```

## Choosing the Right Tool

```
Problem                          → Tool
────────────────────────────────────────────────
Quick check "is X being called?" → printk / dynamic debug
Memory corruption                → KASAN
Use-after-free                   → KASAN
Undefined behavior               → UBSAN
Deadlock                         → Lockdep
Memory leak                      → Kmemleak
Interactive debugging            → KGDB or KDB
Post-mortem analysis             → kdump + crash
Performance issue                → perf, ftrace, eBPF
Intermittent bug                 → KGDB + hardware breakpoint
Network issue                    → eBPF, tcpdump
```

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Kernel Debugging Documentation](https://www.kernel.org/doc/html/latest/dev-tools/gdb-kernel-debugging.html)
- [crash Whitepaper](https://crash-utility.github.io/)
- [KGDB Documentation](https://www.kernel.org/doc/html/latest/dev-tools/kgdb.html)
- [KASAN Documentation](https://www.kernel.org/doc/html/latest/dev-tools/kasan.html)
- [kdump Documentation](https://www.kernel.org/doc/html/latest/admin-guide/kdump/kdump.html)
- [Kernel Testing and Debugging](https://www.kernel.org/doc/html/latest/dev-tools/index.html)

## Related Topics

- [GDB](./gdb.md) — GDB fundamentals (shared by KGDB and user-space debugging)
- [ftrace](./ftrace.md) — Kernel function and event tracing
- [perf](./perf.md) — Hardware counter profiling
- [eBPF](./ebpf.md) — Programmable kernel tracing
