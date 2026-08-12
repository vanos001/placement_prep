# Kernel Command Line Parameters

## Introduction

Kernel command line parameters (also called boot parameters) control the behavior of the Linux kernel during boot and runtime. They are passed by the bootloader to the kernel and can enable debug features, disable problematic hardware, configure subsystems, and control the init process.

This chapter covers the most important kernel parameters, how to set them, and practical use cases for debugging and system configuration.

## How Parameters Are Set

### Via Bootloader

#### GRUB 2

```bash
# Permanent: edit /etc/default/grub
$ sudo nano /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
GRUB_CMDLINE_LINUX=""

# Apply changes
$ sudo update-grub

# Temporary: edit at boot menu
# At GRUB menu, press 'e' to edit
# Find the 'linux' line and add parameters:
linux /vmlinuz-6.1.0 root=UUID=... ro quiet splash new_param=value
# Press Ctrl+X or F10 to boot
```

#### systemd-boot

```bash
# Edit loader entries
$ sudo nano /boot/loader/entries/my-kernel.conf
title   My Linux
linux   /vmlinuz-6.1.0
initrd  /initrd.img-6.1.0
options root=UUID=... ro quiet splash
```

### Via Kernel Config

```bash
# Some parameters can be set as defaults in kernel config
# CONFIG_CMDLINE="earlyprintk=ttyS0 console=ttyS0"
# CONFIG_CMDLINE_BOOL=y
```

### Reading Current Parameters

```bash
# View parameters of running kernel
$ cat /proc/cmdline
BOOT_IMAGE=/vmlinuz-6.1.0-23-amd64 root=UUID=12345678-... ro quiet splash

# Parsed parameters
$ cat /proc/cmdline | tr ' ' '\n' | sort
BOOT_IMAGE=/vmlinuz-6.1.0-23-amd64
quiet
ro
root=UUID=12345678-...
splash
```

## Parameter Syntax

Kernel parameters follow specific syntax rules:

```bash
# Boolean — presence means true
quiet               # Enable quiet mode
noapic              # Disable APIC

# Key=value
root=/dev/sda2      # Set root device
console=ttyS0       # Set console
debug               # Enable debug

# Subsystem parameters (using dots or dashes)
e1000e.InterruptThrottleRate=3000
modprobe.blacklist=nouveau

# Multiple values (comma-separated)
initcall_debug=init1,init2

# Negation (no prefix)
noapic              # Disable APIC
nolapic             # Disable local APIC
nohz=off            # Disable tickless
```

## Essential Parameters

### Root Filesystem

```bash
# Specify root device
root=/dev/sda2              # By device name
root=UUID=12345678-...      # By UUID (preferred)
root=LABEL=rootfs           # By label

# Root filesystem type
rootfstype=ext4             # Force filesystem type

# Root mount flags
ro                          # Mount read-only (default)
rw                          # Mount read-write
rootflags=data=ordered      # Filesystem-specific flags
rootwait                    # Wait for root device to appear
rootdelay=5                 # Wait N seconds for root
```

### Console and Output

```bash
# Set console device
console=tty0                # First virtual console
console=ttyS0,115200n8     # Serial console (115200 baud, 8N1)
console=tty0 console=ttyS0  # Both video and serial

# Log level
quiet                       # Only critical messages (loglevel=4)
loglevel=7                  # All messages (0-7)
debug                       # Enable debug messages
earlyprintk=vga             # Early console before regular console
earlyprintk=ttyS0,115200   # Early serial console
```

### init Process

```bash
# Specify init program
init=/bin/bash              # Drop to bash shell (recovery)
init=/sbin/init             # Default init
init=/usr/lib/systemd/systemd  # Explicit systemd
init=/path/to/custom/init   # Custom init

# initramfs
rdinit=/init                # init in initramfs
break                       # Break to shell in initramfs
break=premount              # Break before mounting root
break=mount                 # Break after mounting root
```

### Memory

```bash
# Limit memory
mem=512M                    # Only use 512MB
memmap=nn[KMG]@ss[KMG]     # Mark specific memory region
memmap=exactmap             # Use only memmap entries

# Memory debugging
slub_debug=FZPU             # SLUB allocator debugging
kmemleak=on                 # Enable memory leak detection
memtest                     # Run memtest on boot
```

### CPU and Scheduling

```bash
# CPU features
nosmp                       # Disable SMP (single CPU)
maxcpus=4                   # Limit to 4 CPUs
nr_cpus=8                   # Maximum number of CPUs
isolcpus=2-7                # Isolate CPUs 2-7 for RT work

# Scheduling
preempt=full                # Full preemption
preempt=voluntary           # Voluntary preemption
preempt=none                # No preemption (server)

# NUMA
numa=off                    # Disable NUMA
numa=fake=8G                # Fake NUMA nodes

# CPU frequency
cpufreq.default_gov=powersave  # Default governor
```

### Debugging Parameters

```bash
# Enable debugging
debug                       # Enable debug messages
initcall_debug              # Trace initcall timing
printk.time=1               # Add timestamps to printk
stacktrace                  # Enable stack traces
panic_on_warn=1             # Panic on WARN()

# Crash debugging
crashkernel=256M            # Reserve memory for kdump
crashkernel=auto            # Auto-size crash kernel
nmi_watchdog=1              # Enable NMI watchdog
softlockup_panic=1          # Panic on soft lockup
hardlockup_panic=1          # Panic on hard lockup
hung_task_panic=1           # Panic on hung tasks

# Kernel address space
kaslr                       # Enable KASLR (default)
nokaslr                     # Disable KASLR
```

### Networking

```bash
# Network configuration
ip=dhcp                     # DHCP on all interfaces
ip=192.168.1.100::192.168.1.1:255.255.255.0::eth0:off

# Disable networking
net.ifnames=0               # Disable predictable names
biosdevname=0               # Disable biosdevname

# IPv6
ipv6.disable=1              # Disable IPv6
```

### Security

```bash
# SELinux
selinux=0                   # Disable SELinux
selinux=1                   # Enable SELinux
enforcing=0                 # Permissive mode

# AppArmor
apparmor=0                  # Disable AppArmor
apparmor=1                  # Enable AppArmor

# Security features
mitigations=off             # Disable CPU vulnerability mitigations
tsx=off                     # Disable TSX
smt=off                     # Disable SMT (Hyper-Threading)

# Kernel lockdown
lockdown=confidentiality    # Full lockdown
lockdown=integrity          # Integrity lockdown
```

### Filesystem

```bash
# Filesystem options
ro                          # Mount root read-only
rw                          # Mount root read-write

# Specific filesystem options
ext4.errors=continue        # ext4: continue on errors
ext4.errors=panic           # ext4: panic on errors
xfs.xfsbug=warn             # XFS: warn on bugs
```

### ACPI and Power

```bash
# ACPI
acpi=off                    # Disable ACPI entirely
acpi=on                     # Force ACPI on
acpi=noirq                  # Don't use ACPI for IRQ routing
acpi_osi="Windows 2012"     # Report specific OS to ACPI

# Power management
noapm                       # Disable APM
reboot=hard                 # Force hard reboot
pci=noacpi                  # Don't use ACPI for PCI
```

### PCI and Devices

```bash
# PCI
pci=nomsi                   # Disable MSI (Message Signaled Interrupts)
pci=nommconf                # Disable MMCONFIG
pci=noaer                   # Disable Advanced Error Reporting

# USB
nousb                       # Disable USB entirely
usb-storage.delay_use=5     # USB storage delay

# GPU / Graphics
nomodeset                   # Disable kernel mode setting
i915.modeset=0              # Disable Intel GPU KMS
nouveau.modeset=0           # Disable Nouveau KMS
nvidia.modeset=1            # Enable NVIDIA KMS
video=VGA-1:1024x768@60     # Set video mode
```

## Parameter Categories

### Module Parameters on Command Line

Module parameters can be passed on the kernel command line using the `module.parameter=value` syntax:

```bash
# Format: module_name.parameter=value
e1000e.InterruptThrottleRate=3000
e1000e.debug=4
bonding.mode=4
bonding.miimon=100

# Blacklist a module via command line
modprobe.blacklist=nouveau,nvidiafb

# Force module loading
e1000e.eeprom_bad_csum_allow=1
```

### Subsystem-Specific Parameters

```bash
# I/O scheduler
elevator=mq-deadline         # Default I/O scheduler

# Block layer
deadline.read_expire=500     # Read deadline in ms
cfq.quantum=8                # CFQ quantum

# SCSI
scsi_mod.scsi_logging_level=0x1f  # SCSI logging
```

## Practical Use Cases

### 1. Recovery from Boot Failure

```bash
# GRUB menu → press 'e' → add to linux line:

# Option A: Single-user mode
single

# Option B: Emergency shell
init=/bin/bash

# Option C: Disable problematic driver
modprobe.blacklist=nvidia

# Option D: Disable graphics
nomodeset

# Option E: Verbose boot for debugging
debug loglevel=7 earlyprintk=vga
```

### 2. Performance Tuning

```bash
# Server-optimized boot
GRUB_CMDLINE_LINUX_DEFAULT="quiet \
    nohz_full=2-15 \
    isolcpus=2-15 \
    rcu_nocbs=2-15 \
    intel_pstate=disable \
    processor.max_cstate=1 \
    idle=poll \
    transparent_hugepages=always"
```

### 3. Real-Time Kernel Configuration

```bash
# Low-latency configuration
GRUB_CMDLINE_LINUX_DEFAULT="quiet \
    threadirqs \
    isolcpus=1-7 \
    nohz_full=1-7 \
    rcu_nocbs=1-7 \
    nosoftirqd=1-7 \
    nohz=on \
    rcutree.kthread_prio=11"
```

### 4. Container Host Configuration

```bash
# Optimized for containers
GRUB_CMDLINE_LINUX_DEFAULT="quiet \
    cgroup_enable=memory \
    swapaccount=1 \
    systemd.unified_cgroup_hierarchy=1 \
    namespace.nesting=1"
```

### 5. Debugging Memory Issues

```bash
# Memory debugging boot parameters
GRUB_CMDLINE_LINUX="debug \
    slub_debug=FZPU \
    kmemleak=on \
    page_poison=1 \
    debug_pagealloc=on"
```

### 6. Security Hardening

```bash
# Security-focused parameters
GRUB_CMDLINE_LINUX=" \
    lockdown=confidentiality \
    module.sig_enforce=1 \
    mitigations=auto \
    slub_debug=FZP \
    init_on_alloc=1 \
    init_on_free=1 \
    page_poison=1 \
    vsyscall=none \
    pti=on"
```

### 7. Kdump Configuration

```bash
# Reserve memory for crash kernel
GRUB_CMDLINE_LINUX="crashkernel=256M"

# Crash kernel parameters
# In /etc/kdump.conf:
# path /var/crash
# core_collector makedumpfile -l --message-level 1 -d 31
```

## Debugging with Parameters

### Kernel Debugging

```bash
# Trace initcalls (see where boot time is spent)
initcall_debug

# Example output:
[    0.123456] initcall net_ns_init+0x0/0x100 returned 0 after 1234 usecs
[    0.123789] initcall inet_init+0x0/0x200 returned 0 after 5678 usecs

# Enable function tracing
ftrace=function_graph
ftrace_graph_filter=some_function

# Dynamic debug at boot
dyndbg="file drivers/net/e1000e/* +p"
```

### Hardware Debugging

```bash
# Disable problematic hardware
acpi=off                    # ACPI issues
pci=noacpi                  # PCI/ACPI interaction
noapic                      # APIC problems
nolapic                     # Local APIC issues
no_timer_check              # Timer issues
```

### Boot Failure Debugging

```bash
# Get maximum information
earlyprintk=vga console=tty0 loglevel=8 debug initcall_debug

# With serial console
earlyprintk=ttyS0,115200 console=ttyS0,115200 loglevel=8 debug

# Break into initramfs for investigation
break
# Then at the shell:
# cat /proc/cmdline
# ls /dev/
# mount
# dmesg
```

## Parameter Types and Validation

### How Parameters Are Parsed

```c
/* include/linux/moduleparam.h */
/* Boolean parameter */
module_param_named(enable_debug, debug_enabled, bool, 0644);

/* Integer parameter with range check */
static int buffer_size = 4096;
module_param(buffer_size, int, 0644);
MODULE_PARM_DESC(buffer_size, "Buffer size (64-65536)");

/* String parameter */
static char *mode = "default";
module_param(mode, charp, 0644);
```

### Early Parameters vs Module Parameters

```c
/* Early parameters — parsed before modules are loaded */
early_param("earlyprintk", setup_early_printk);

__setup("init=", init_setup);

/* Module parameters — parsed when module is loaded */
module_param_named(debug, drv_debug, int, 0644);
```

## Complete Parameter Reference

### Boot Loader Parameters

| Parameter | Description |
|-----------|-------------|
| `BOOT_IMAGE=` | Set by bootloader, path to kernel |
| `root=` | Root filesystem device |
| `ro` | Mount root read-only |
| `rw` | Mount root read-write |
| `rootfstype=` | Root filesystem type |
| `rootflags=` | Root filesystem mount options |
| `rootwait` | Wait for root device |
| `rootdelay=` | Seconds to wait for root |

### System Parameters

| Parameter | Description |
|-----------|-------------|
| `init=` | Path to init program |
| `rdinit=` | Path to init in initramfs |
| `break` | Break into initramfs shell |
| `single` | Single-user mode |
| `emergency` | Emergency shell |
| `systemd.unit=` | Boot to specific systemd target |

### Debug Parameters

| Parameter | Description |
|-----------|-------------|
| `debug` | Enable kernel debug messages |
| `initcall_debug` | Trace initcall timing |
| `loglevel=` | Console log level (0-7) |
| `earlyprintk=` | Early console |
| `printk.time=1` | Add timestamps |
| `kasan=on` | Enable KASAN |
| `kmemleak=on` | Enable memory leak detection |
| `hung_task_panic=1` | Panic on hung tasks |

### Performance Parameters

| Parameter | Description |
|-----------|-------------|
| `isolcpus=` | Isolate CPUs from scheduler |
| `nohz_full=` | Full tickless CPUs |
| `rcu_nocbs=` | Offload RCU callbacks |
| `transparent_hugepages=` | THP mode (always/madvise/never) |
| `elevator=` | I/O scheduler |
| `intel_pstate=` | Intel P-state driver control |

### Security Parameters

| Parameter | Description |
|-----------|-------------|
| `selinux=` | Enable/disable SELinux |
| `apparmor=` | Enable/disable AppArmor |
| `lockdown=` | Kernel lockdown mode |
| `mitigations=` | CPU vulnerability mitigations |
| `module.sig_enforce=` | Enforce module signatures |

## Additional Parameters (from kernel docs)

The following parameters are documented in the kernel's command-line parameters reference at `docs.kernel.org/admin-guide/kernel-parameters.html`:

### Memory

```bash
# Control memory acceptance (for TDX/SEV guests)
accept_memory=eager    # Accept all unaccepted memory at boot
accept_memory=lazy     # Accept lazily (default, faster boot)

# Contiguous Memory Allocator (CMA)
cma=nn[MG]             # Set CMA region size

# Memory hotplug
memblock=debug         # Enable memblock debugging

# Huge pages
hugepagesz=2M          # Huge page size
hugepages=512          # Number of huge pages
transparent_hugepages=always  # THP mode (always/madvise/never)
```

### CPU and Scheduler

```bash
# CPU isolation for real-time workloads
isolcpus=domain,2-7        # Isolate CPUs from scheduler domains
nohz_full=2-15             # Full tickless on specified CPUs
rcu_nocbs=2-15             # Offload RCU callbacks

# Scheduler tuning
sched_verbose              # Enable verbose scheduler debugging

# Intel P-state driver
intel_pstate=passive       # Use passive mode (governor-managed)
intel_pstate=active        # Use active mode (hardware-managed)
intel_pstate=no_hwp        # Disable HWP (Hardware P-states)

# CPU bug mitigations
mitigations=off            # Disable all CPU mitigations
mds=off                    # Disable MDS mitigation
tsx=on                     # Enable TSX
tsx=off                    # Disable TSX
smt=off                    # Disable SMT (Hyper-Threading)
```

### ACPI and Power

```bash
# ACPI control
acpi=force                 # Force ACPI on
acpi=noirq                 # Don't use ACPI for IRQ routing
acpi=strict                # Be less tolerant of non-compliant platforms
acpi_osi="Windows 2012"    # Report specific OS to ACPI firmware
acpi_backlight=native      # Use native backlight driver

# Power management
processor.max_cstate=1     # Limit C-states for low latency
idle=poll                  # Busy-wait in idle (lowest latency)
```

### Tracing and Debug

```bash
# Event tracing at boot
trace_event=sched_switch,sched_wakeup
trace_event=block:*        # All block events

# Function tracing
ftrace=function_graph
ftrace_graph_filter=some_function

# Dynamic debug
dyndbg="file drivers/net/e1000e/* +p"

# Fault injection
fail_make_request=<probability>  # Inject block I/O failures
```

### Networking

```bash
# Network configuration at boot
ip=dhcp                    # DHCP on all interfaces
ip=192.168.1.100::192.168.1.1:255.255.255.0::eth0:off

# Disable features
ipv6.disable=1             # Disable IPv6
net.ifnames=0              # Disable predictable names

# Network stack tuning
netdev_budget=600          # NAPI budget per cycle
netdev_budget_usecs=8000   # NAPI time budget (µs)
```

## Further Reading

- [The kernel's command-line parameters — docs.kernel.org](https://docs.kernel.org/admin-guide/kernel-parameters.html)
- [Linux kernel command line howto](https://tldp.org/HOWTO/html_single/BootPrompt-HOWTO/)
- [systemd kernel command line](https://www.freedesktop.org/software/systemd/man/kernel-command-line.html)
- [Arch Linux kernel parameters](https://wiki.archlinux.org/title/Kernel_parameters)
- [GRUB 2 documentation](https://www.gnu.org/software/grub/manual/grub/)

## Related Topics

- [Boot Process](boot-process.md) — Complete boot chain
- [Configuration](configuration.md) — Kernel configuration
- [Kernel Overview](overview.md) — Kernel architecture
- [Kernel Modules](modules.md) — Module parameters
