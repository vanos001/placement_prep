# Kexec: Fast Reboot and Crash Dumps

## Overview

kexec is a Linux kernel mechanism that allows **loading and booting a new kernel from a running kernel** without going through the BIOS/firmware. It has two primary use cases:

1. **Fast reboot (`kexec -e`)**: Skip the BIOS/POST and boot directly into a new kernel, reducing reboot time from minutes to seconds.
2. **Crash dumps (`kdump`)**: Load a secondary "capture" kernel that boots when the primary kernel panics, capturing the crashed kernel's memory for post-mortem analysis.

kexec works by loading the new kernel image into memory while the current kernel is running, then transferring control to the new kernel when triggered.

## System Calls

### kexec_load (Legacy)

```c
#include <linux/kexec.h>

long kexec_load(unsigned long entry, unsigned long nr_segments,
                struct kexec_segment *segments, unsigned long flags);
```

The legacy `kexec_load()` system call loads a kernel image into memory:

```c
struct kexec_segment {
    void __user *buf;      /* Data buffer in userspace */
    size_t bufsz;          /* Size of buffer */
    void __user *mem;      /* Destination in kernel memory */
    size_t memsz;          /* Size of destination */
};
```

**Flags:**

| Flag | Description |
|------|-------------|
| `KEXEC_ON_CRASH` | Load for crash kernel (kdump) |
| `KEXEC_PRESERVE_CONTEXT` | Preserve current context (hibernate) |
| `KEXEC_FILE_NO_INITRAMFS` | No initramfs needed |

### kexec_file_load (Modern)

```c
long kexec_file_load(int kernel_fd, int initrd_fd,
                     unsigned long cmdline_len, const char __user *cmdline,
                     unsigned long flags);
```

The modern `kexec_file_load()` uses file descriptors instead of memory buffers:

```c
/* Load a new kernel */
int kernel_fd = open("/boot/vmlinuz-6.1.0", O_RDONLY);
int initrd_fd = open("/boot/initrd.img-6.1.0", O_RDONLY);
const char *cmdline = "root=/dev/sda1 ro";

syscall(__NR_kexec_file_load, kernel_fd, initrd_fd,
        strlen(cmdline) + 1, cmdline, 0);
```

**Advantages over kexec_load:**

- **Simpler API**: just pass file descriptors and command line
- **Signature verification**: supports IMA and secure boot verification
- **No userspace memory staging**: kernel reads files directly
- **More secure**: reduced attack surface

**Flags:**

| Flag | Description |
|------|-------------|
| `KEXEC_FILE_UNLOAD` | Unload previously loaded kernel |
| `KEXEC_FILE_ON_CRASH` | Load for crash kernel |
| `KEXEC_FILE_NO_INITRAMFS` | No initramfs needed |
| `KEXEC_FILE_DEBUG` | Enable debug output |

## Fast Reboot

### How It Works

```
Current kernel (running)
    │
    │  kexec_load() — load new kernel into reserved memory
    │
    │  kexec -e (or reboot with kexec flag)
    │
    ↓
┌──────────────────────┐
│  kexec_reboot()      │
│  1. Disable IRQs     │
│  2. Shut down devices│
│  3. Load new kernel  │
│  4. Jump to entry    │
└──────────────────────┘
    │
    ↓
New kernel boots (skips BIOS)
```

### Usage

```bash
# Load a kernel for fast reboot
kexec -l /boot/vmlinuz-6.1.0 \
      --initrd=/boot/initrd.img-6.1.0 \
      --command-line="root=/dev/sda1 ro quiet"

# Execute the loaded kernel
kexec -e

# Or: reboot using kexec (systemd)
systemctl kexec
```

### Benefits

- **Speed**: Reboot in 2–5 seconds instead of 30–120 seconds (no BIOS POST)
- **Server farms**: massive time savings when rebooting hundreds of machines
- **Updates**: fast kernel updates with minimal downtime

### Limitations

- **No firmware re-initialization**: hardware state may not be fully reset
- **ACPI**: tables from the old kernel are reused
- **KASLR**: new kernel may have different ASLR offsets
- **Device state**: devices may retain state from the old kernel
- **Not a cold boot**: memory errors or hardware issues won't be cleared

## Kdump (Crash Dumps)

### Architecture

```
┌──────────────────────────────────────────────┐
│              Normal Operation                 │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  Production Kernel (kernel 1)        │    │
│  │  Running normally                    │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ┌──────────────────────────────────────┐    │
│  │  Crash Kernel (kernel 2) — loaded    │    │
│  │  but NOT running                     │    │
│  │  (reserved memory area)              │    │
│  └──────────────────────────────────────┘    │
└──────────────────────────────────────────────┘

Kernel 1 panics!
    │
    ↓
┌──────────────────────────────────────────────┐
│              Crash Event                     │
│                                              │
│  1. Panic handler triggers kexec             │
│  2. Control transfers to crash kernel        │
│  3. Crash kernel boots in reserved memory    │
│  4. Old kernel's memory is /proc/vmcore      │
│  5. Crash dump saved to disk/network         │
└──────────────────────────────────────────────┘
```

### Setup

#### Step 1: Reserve Memory for Crash Kernel

Add to kernel command line (GRUB):

```bash
# In /etc/default/grub
GRUB_CMDLINE_LINUX="crashkernel=256M"

# Or more specific (range-based reservation)
GRUB_CMDLINE_LINUX="crashkernel=256M@64M"

# Update GRUB
update-grub
```

Memory reservation sizes:

| System RAM | Recommended crashkernel |
|------------|----------------------|
| < 4 GB | 128M |
| 4–16 GB | 256M |
| 16–64 GB | 512M |
| > 64 GB | 1G+ |

#### Step 2: Load the Crash Kernel

```bash
# Load crash kernel
kexec -p /boot/vmlinuz-$(uname -r) \
      --initrd=/boot/initrd.img-$(uname -r) \
      --command-line="$(cat /proc/cmdline) irqpoll maxcpus=1 reset_devices"

# The -p flag means "load for panic" (kdump mode)
```

The crash kernel command line typically includes:

| Parameter | Purpose |
|-----------|---------|
| `irqpoll` | Try all IRQs (crash kernel may not have correct IRQ routing) |
| `maxcpus=1` | Boot only on one CPU (the one that panicked) |
| `reset_devices` | Attempt to reset devices |
| `1` or `single` | Boot to single-user mode |
| `root=/dev/...` | Root filesystem |

#### Step 3: Automatic Loading (systemd)

```bash
# Enable kdump service
systemctl enable kdump
systemctl start kdump

# Check status
systemctl status kdump
kdump-config show
```

### Saving Crash Dumps

After the crash kernel boots, the old kernel's memory is available at `/proc/vmcore`. Various mechanisms save it:

#### Local Disk

```bash
# makedumpfile: compressed, filtered dump
makedumpfile -l -d 31 /proc/vmcore /var/crash/vmcore.dump

# Compression levels:
#   -d 0  = no filter (all pages)
#   -d 1  = exclude zero pages
#   -d 2  = exclude zero and cache pages
#   -d 4  = exclude user data pages
#   -d 8  = exclude free pages
#   -d 31 = all filters combined
```

#### Network (SSH/SCP)

```bash
# Save to remote server
makedumpfile -l -d 31 /proc/vmcore | ssh user@server "cat > /var/crash/vmcore.dump"

# Or using netdump/diskdump protocols
```

#### Remote Dump Server

```bash
# Configure /etc/kdump.conf
ssh user@dumpserver
path /var/crash
core_collector makedumpfile -l -d 31
```

### Analyzing Crash Dumps

```bash
# Using the crash utility
crash /usr/lib/debug/boot/vmlinux-$(uname -r) /var/crash/vmcore

# Inside crash:
crash> bt              # Backtrace of crashed task
crash> bt -a           # All tasks
crash> log             # Kernel log (dmesg)
crash> ps              # Process list
crash> vm              # Virtual memory info
crash> files           # Open files
crash> kmem -i         # Memory usage
crash> sys             # System info
crash> irq             # IRQ info
crash> mod             # Loaded modules
crash> rd -d <addr>    # Read memory
crash> struct task_struct <addr>  # Inspect data structures
```

## Implementation

### kexec_load Flow

```c
/* In kernel/kexec.c */
SYSCALL_DEFINE4(kexec_load, unsigned long, entry, unsigned long, nr_segments,
                struct kexec_segment __user *, segments, unsigned long, flags)
{
    /* 1. Validate arguments */
    /* 2. Check capabilities (CAP_SYS_BOOT) */
    /* 3. Copy segments from userspace */
    /* 4. If KEXEC_ON_CRASH: validate crash kernel memory reservation */
    /* 5. Load segments into kernel memory */
    /* 6. Store the loaded image in kimage (per-flag: normal vs crash) */
}
```

### kexec_execute

When `kexec -e` is called (or the system reboots with kexec flag):

```c
/* In kernel/kexec.c */
void kernel_kexec(void)
{
    struct kimage *image;

    image = kexec_image;
    if (!image)
        return;

    /* 1. Freeze all CPUs (except the executing one) */
    /* 2. Suspend devices */
    /* 3. Disable IRQs */
    /* 4. Machine-specific reboot hook */
    /* 5. Jump to the new kernel's entry point */
}
```

### Crash Path

When the kernel panics:

```c
/* In kernel/panic.c */
void panic(const char *fmt, ...)
{
    /* ... existing panic handling ... */

    /* Try kexec if a crash kernel is loaded */
    if (kexec_crash_loaded()) {
        /* Disable preemption, stop other CPUs */
        /* Jump to crash kernel */
        machine_kexec(kexec_image);
    }
}
```

### machine_kexec (Architecture-Specific)

```c
/* In arch/x86/kernel/relocate_kernel_64.S */
/* Assembly code that:
 * 1. Switches to a new page table (identity mapping)
 * 2. Copies the new kernel to its load address
 * 3. Jumps to the new kernel's entry point
 */
```

The relocation code runs in a special identity-mapped environment since the old kernel's page tables will be destroyed.

## Kernel Configuration

```bash
CONFIG_KEXEC=y              # Enable kexec_load
CONFIG_KEXEC_FILE=y         # Enable kexec_file_load
CONFIG_KEXEC_SIG=y          # Require signature on kexec images
CONFIG_KEXEC_SIG_FORCE=y    # Enforce signature verification
CONFIG_CRASH_DUMP=y         # Enable crash dump support
CONFIG_PROC_VMCORE=y        # Enable /proc/vmcore
CONFIG_DEBUG_INFO=y         # Required for crash analysis
CONFIG_DEBUG_INFO_DWARF4=y  # DWARF4 debug info
```

## Security Considerations

### Secure Boot

With secure boot, kexec loading is restricted:

```bash
# Check if kexec signature is required
cat /sys/kernel/kexec_loaded
cat /sys/kernel/kexec_crash_loaded

# Signed kexec: kernel verifies image signature
CONFIG_KEXEC_SIG=y
CONFIG_KEXEC_SIG_FORCE=y
```

Without `KEXEC_SIG_FORCE`, unsigned kernels can be loaded if the platform doesn't enforce signature checking.

### CAP_SYS_BOOT

```bash
# kexec_load requires CAP_SYS_BOOT
# Typically only root has this capability
```

### Lockdown Mode

When the kernel is in lockdown mode (integrity or confidentiality), kexec is restricted:

```bash
# Check lockdown status
cat /sys/kernel/security/lockdown
# [none] integrity confidentiality

# In integrity mode: kexec requires signed images
# In confidentiality mode: kexec is disabled entirely
```

## Troubleshooting

### Common Issues

```bash
# Crash kernel not loading — check reservation
dmesg | grep -i crash
# "Reserving 256MB of memory at X for crashkernel"

# Check if crash kernel is loaded
kdump-config show

# Check reserved memory
cat /proc/iomem | grep -i crash

# Verify kexec binary
kexec --version
```

### Memory Reservation Failures

```bash
# If crashkernel reservation fails, try:
# 1. Different offset
crashkernel=256M@256M

# 2. Range-based reservation
crashkernel=256M-1G:128M,1G-:256M
# (128M for systems with 256M-1G RAM, 256M for 1G+ systems)

# 3. High memory reservation
crashkernel=512M,high
```

### Crash Kernel Boot Issues

```bash
# If crash kernel fails to boot:
# 1. Check crash kernel command line
# 2. Ensure initramfs has necessary drivers
# 3. Try adding 'debug' to crash kernel command line
# 4. Check serial console output if available

# Enable early console for crash kernel
# Add to crash kernel cmdline:
earlycon=uart8250,io,0x3f8,115200n8
```

### vmcore Analysis Issues

```bash
# If crash can't read vmcore:
# 1. Ensure vmlinux has debug info
# 2. Check makedumpfile filtering level
# 3. Verify vmcore isn't truncated

# Check vmcore header
file /var/crash/vmcore.dump
# Should show: "kdump captured vmcore"

# Verify debug info
crash> sym panic
# Should show the symbol address
```

## Integration with initramfs

For kdump, a special initramfs is often needed:

```bash
# Ubuntu/Debian
sudo apt install linux-crashdump
# Automatically sets up kdump

# RHEL/CentOS/Fedora
sudo yum install kexec-tools
sudo systemctl enable kdump

# Generate kdump initramfs
mkdumprd /boot/initramfs-$(uname -r)kdump.img $(uname -r)
```

### Custom kdump initramfs

```bash
# /etc/kdump.conf
# Destination
ext4 /dev/sda1
# Path on destination
path /var/crash
# Core collector
core_collector makedumpfile -l -d 31
# Extra binaries
extra_bins /usr/bin/vim
# Hook scripts
kdump_post /usr/local/bin/kdump-notify.sh
```

## Source Files

- `kernel/kexec.c` — kexec_load and kexec_file_load system calls
- `kernel/kexec_core.c` — core kexec functionality
- `kernel/kexec_file.c` — file-based kexec loading
- `kernel/crash_core.c` — crash dump core
- `kernel/crash_dump.c` — /proc/vmcore implementation
- `arch/x86/kernel/machine_kexec_64.c` — x86_64 kexec implementation
- `arch/x86/kernel/relocate_kernel_64.S` — assembly relocation code
- `include/linux/kexec.h` — kexec data structures
- `include/uapi/linux/kexec.h` — userspace API
- `fs/proc/vmcore.c` — /proc/vmcore filesystem

## kexec in Cloud and Container Environments

### Cloud Provider Use

Major cloud providers use kexec extensively for fast kernel updates:

```bash
# AWS: Fast kernel update with kexec (reduces downtime from minutes to seconds)
# 1. Install new kernel
sudo yum install kernel-5.14.0-362

# 2. Load via kexec
sudo kexec -l /boot/vmlinuz-5.14.0-362.el9_3.x86_64 \
    --initrd=/boot/initramfs-5.14.0-362.el9_3.x86_64.img \
    --command-line="$(cat /proc/cmdline)"

# 3. Execute (takes 2-5 seconds vs 30-120 for full reboot)
sudo kexec -e

# Google Cloud: Uses kexec for live migration of VMs
# Azure: Supports kexec-based fast reboot for kernel patches
```

### Kubernetes Node Updates

```bash
# kexec-based node drain and reboot strategy
#!/bin/bash
NODE=$(hostname)

# Drain the node
kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data

# Load new kernel
kexec -l /boot/vmlinuz-$(uname -r) \
    --initrd=/boot/initramfs-$(uname -r).img \
    --command-line="$(cat /proc/cmdline)"

# Reboot via kexec (fast)
kexec -e

# After reboot, uncordon
kubectl uncordon $NODE
```

### Container Host Updates

```bash
# Docker/Podman host: fast kernel update
# Containers restart quickly since BIOS POST is skipped

# Before kexec: pause containers
docker pause $(docker ps -q)

# kexec reboot
kexec -e

# After reboot: containers automatically resume (if using restart policy)
docker unpause $(docker ps -q)
```

## kexec-tools Package

The userspace `kexec` tool is part of the kexec-tools package:

```bash
# Install
sudo apt install kexec-tools       # Debian/Ubuntu
sudo dnf install kexec-tools        # RHEL/Fedora
sudo pacman -S kexec-tools          # Arch Linux

# kexec-tools provides:
# kexec       — Load and execute kernels
# kdump       — Crash dump service
# makedumpfile — Compressed/filtered crash dumps
# vmcore-dmesg — Extract dmesg from vmcore
# kdump-lib.sh — Helper functions for kdump scripts

# Version
kexec --version
# kexec-tools 2.0.27
```

### kdump Configuration File

```bash
# /etc/kdump.conf

# Local filesystem dump
ext4 /dev/mapper/vg_data-lv_crash
path /var/crash

# Remote dump via SSH
ssh user@dumpserver
sshkey /root/.ssh/kdump_id_rsa
path /var/crash

# Remote dump via NFS
nfs dumpserver:/exports/crash
path /var/crash

# Core collector with filtering
core_collector makedumpfile -l -d 31 --message-level 1

# Actions before/after dump
kdump_pre /usr/local/bin/kdump-pre.sh
kdump_post /usr/local/bin/kdump-post.sh

# Extra modules to include in kdump initramfs
extra_modules virtio_net

# Debug shell access after crash
# (for interactive debugging, only in non-production)
# shell /bin/bash

# Reboot after dump (default: reboot)
default reboot
# Or: default halt, poweroff, shell, mount_root_run_init
```

## makedumpfile Deep Dive

makedumpfile creates filtered and compressed crash dumps, dramatically reducing dump size:

```bash
# Dump levels (bitmap filters):
# Level 0: No filter (full dump)
# Level 1: Exclude zero pages
# Level 2: Exclude zero + cache pages (non-private)
# Level 4: Exclude user process pages
# Level 8: Exclude free pages
# Level 16: Exclude reserved pages (hardware)
# Level 31: All filters combined (most aggressive)

# Typical dump size comparison (for 16GB RAM system):
# Level 0 (no filter): ~16 GB
# Level 1 (zero pages): ~12 GB
# Level 31 (all filters): ~500 MB - 2 GB

# Create filtered dump
makedumpfile -l -d 31 /proc/vmcore /var/crash/vmcore.dump

# Show dump file info
makedumpfile --dump-dumpfile /var/crash/vmcore.dump

# Extract dmesg from dump
makedumpfile --dump-dmesg /proc/vmcore /var/crash/dmesg.txt

# Split dump into multiple files (for size-limited storage)
makedumpfile -l -d 31 --split /proc/vmcore /var/crash/vmcore

# Reassemble split dump
makedumpfile --reassemble /var/crash/vmcore.1 /var/crash/vmcore.2 /var/crash/vmcore.full
```

## Architecture Support

kexec is supported on multiple architectures:

| Architecture | kexec_load | kexec_file_load | Notes |
|---|---|---|---|
| x86_64 | ✅ | ✅ | Full support, most mature |
| x86 (32-bit) | ✅ | ✅ | Legacy, still supported |
| ARM64 | ✅ | ✅ | DTB required |
| ARM (32-bit) | ✅ | ✅ | DTB required, zImage support |
| s390x | ✅ | ✅ | IBM mainframe |
| ppc64 | ✅ | ✅ | PowerPC |
| RISC-V | ❌ | ✅ | Only file_load (newer arch) |
| MIPS | ✅ | Partial | Various sub-architectures |

```bash
# ARM64 kexec requires DTB
kexec -l /boot/Image \
    --dtb=/boot/board.dtb \
    --initrd=/boot/initramfs.img \
    --command-line="console=ttyAMA0 root=/dev/mmcblk0p2"

# s390x: kexec with IPL parameters
kexec -l /boot/vmlinuz \
    --command-line="root=/dev/sda1" \
    --initrd=/boot/initrd
```

## Testing kexec

### In a VM (Safe Testing)

```bash
# Test kexec in a QEMU VM
qemu-system-x86_64 -m 2G -kernel /boot/vmlinuz \
    -initrd /boot/initrd.img \
    -append "root=/dev/sda1" \
    -drive file=test.qcow2 \
    -nographic

# Inside the VM:
kexec -l /boot/vmlinuz-new --initrd=/boot/initrd-new.img \
    --command-line="root=/dev/sda1 console=ttyS0"
kexec -e
```

### Testing kdump

```bash
# Trigger a kernel panic (CAUTION: crashes the system!)
echo c > /proc/sysrq-trigger

# Or use a kernel module that panics
# (for testing kdump setup in a safe environment)

# After crash, check if dump was saved
ls -la /var/crash/
# Should contain: vmcore, vmcore-dmesg.txt, kexec-dmesg

# Verify dump
crash /usr/lib/debug/boot/vmlinux-$(uname -r) /var/crash/vmcore
```

## Performance Benchmarks

```bash
# Typical kexec reboot times (measured on various hardware):
# Full reboot (BIOS POST + kernel boot): 30-120 seconds
# kexec reboot (kernel boot only):       2-10 seconds
# Time saved: 80-95%

# Factors affecting kexec speed:
# - Kernel decompression time
# - initramfs size and content
# - Hardware re-initialization needs
# - Filesystem mount time

# Measure kexec time
time kexec -e  # (measured from another terminal or serial console)
```

## Alternatives to kexec

| Mechanism | Use Case | Limitation |
|---|---|---|
| kexec | Fast reboot, crash dumps | No firmware re-init |
| `reboot` | Full reboot | Slow (BIOS POST) |
| `systemctl kexec` | Fast reboot via systemd | Same as kexec |
| hibernate/suspend | Save/restore state | Complex, hardware-dependent |
| livepatch | Patch kernel without reboot | Limited to specific changes |
| kexec_file_load | Secure kexec loading | Requires kernel support |

## Further Reading

- **Documentation/admin-guide/kdump/kdump.rst** — comprehensive kdump documentation
- **Documentation/admin-guide/kdump/vmcoreinfo.rst** — vmcoreinfo format
- **Documentation/devicetree/bindings/chosen/kexec.yaml** — DT kexec bindings
- **man kexec** — kexec(8) manual page
- **man crash** — crash(8) analysis tool
- **LWN: kexec** — <https://lwn.net/Articles/138222/>
- **kexec-tools** — <https://github.com/horms/kexec-tools>
- **makedumpfile** — <https://github.com/makedumpfile/makedumpfile>
- **crash utility** — <https://github.com/crash-utility/crash>

## See Also

- [Stack Traces](../debugging/stack-trace.md) — analyzing crash dumps
- Kernel Panic — panic handling
- Boot Process — kernel boot sequence
- [ACPI](../kernel/drivers/acpi.md) — ACPI table handling during kexec
- [Secure Boot](../security/secure-boot.md) — secure boot and kexec

