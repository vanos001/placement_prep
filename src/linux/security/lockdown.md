# Kernel Lockdown Mode

## Overview

Kernel lockdown is a security feature that restricts the kernel's own capabilities
to prevent both intentional and accidental compromise of kernel integrity and
confidentiality. When enabled, even root (UID 0) cannot perform actions that would
allow loading unsigned code into the kernel, reading kernel memory, or modifying
kernel parameters in ways that could subvert security guarantees.

Lockdown was merged into the mainline kernel in **Linux 5.4** (November 2019),
after years of discussion and multiple iterations. It addresses a fundamental
gap in Linux security: traditionally, root had unrestricted access to the kernel,
making any root compromise a complete system compromise.

## Motivation

### The Root-to-Kernel Problem

On a traditional Linux system, root can:

- Read and write arbitrary physical memory via `/dev/mem`
- Load kernel modules without signature verification
- Access kernel memory via `/proc/kcore` or `/dev/kmem`
- Modify kernel parameters via sysctl or debugfs
- Use `kexec` to boot an entirely different kernel
- Use `bpf` to probe and modify kernel behavior

Any of these capabilities allows an attacker who gains root to escalate to full
kernel-level control, bypassing all kernel security mechanisms (SELinux, AppArmor,
capabilities, etc.).

### Secure Boot Gap

UEFI Secure Boot verifies the boot chain up to the kernel image, but once the
kernel is running, nothing prevented root from loading an unsigned module or
patching kernel code. Lockdown closes this gap by extending the trust boundary
beyond boot into runtime.

## Lockdown Modes

The kernel defines two lockdown modes:

### Integrity Mode (`integrity`)

Prevents actions that would compromise the **integrity** of the running kernel:

- Loading unsigned kernel modules
- `kexec_load()` (loading a new kernel without verification)
- Writing to `/dev/mem`, `/dev/kmem`, `/proc/kcore`
- Writing to `/sys/firmware/efi/efivars` (modifying EFI variables)
- Using `bpf` to write kernel memory
- Modifying kernel code via `ftrace` or `kprobes` in write mode
- Accessing certain debugfs and tracefs entries

**What still works**: reading kernel memory for debugging (e.g., `/proc/kallsyms`
with appropriate permissions), most hardware access, and standard userspace
operation.

### Confidentiality Mode (`confidentiality`)

All of integrity mode restrictions, **plus** prevents actions that would leak
**confidential** kernel information:

- Reading `/dev/mem` (even read-only access to physical memory)
- Reading `/proc/kcore` (kernel memory dump)
- Using `kprobes` to inspect kernel internals
- Reading certain debugfs entries that expose kernel state
- Loading modules even if they appear to be signed (depending on policy)

**What still works**: standard userspace operation, no access to kernel internals
from userspace.

### Mode Hierarchy

```
none → integrity → confidentiality
```

- `none`: no lockdown (default on most systems)
- `integrity`: kernel integrity protection
- `confidentiality`: kernel integrity + confidentiality protection

Lockdown can only be escalated (e.g., from `none` to `integrity`), never
de-escalated, at runtime. This prevents an attacker from disabling lockdown
after gaining root.

## How Lockdown Is Enabled

### Command Line

```bash
# At boot via kernel command line
lockdown=integrity
# or
lockdown=confidentiality
```

### Secure Boot Integration

When UEFI Secure Boot is detected, many distributions automatically enable
lockdown in integrity mode. This is configured via:

```bash
# Check current lockdown status
cat /sys/kernel/security/lockdown
# [none] integrity confidentiality
```

The bracketed value indicates the current active mode.

### Sysfs Interface

```bash
# Read current lockdown mode
cat /sys/kernel/security/lockdown

# Escalate lockdown (requires CAP_SYS_ADMIN, and only escalates)
echo integrity > /sys/kernel/security/lockdown
```

### Runtime Trigger

Certain events can trigger lockdown escalation:

- **Secure Boot detection**: kernel enables integrity lockdown automatically
- **Module loading policy**: loading a tainted module may trigger lockdown
- **IMA (Integrity Measurement Architecture)**: IMA policy can enforce lockdown

## LSM Integration

Lockdown is implemented as a **Linux Security Module (LSM)** hook framework.
The lockdown LSM provides hooks that other LSMs (SELinux, AppArmor, etc.) and
the kernel itself use to enforce restrictions.

### Lockdown LSM Hooks

The lockdown LSM defines hooks for:

```c
enum lockdown_reason {
    LOCKDOWN_NONE,
    LOCKDOWN_MODULE_SIGNATURE,      /* Unsigned module */
    LOCKDOWN_DEV_MEM,               /* /dev/mem access */
    LOCKDOWN_EFI_TEST,              /* EFI test interface */
    LOCKDOWN_KEXEC,                 /* kexec_load() */
    LOCKDOWN_HIBERNATION,           /* Hibernate to disk */
    LOCKDOWN_PCI_ACCESS,            /* PCI config space access */
    LOCKDOWN_IOPORT,                /* I/O port access */
    LOCKDOWN_MSR,                   /* MSR register access */
    LOCKDOWN_ACPI_CUSTOM_METHOD,    /* ACPI custom methods */
    LOCKDOWN_PCMCIA_CIS,            /* PCMCIA CIS access */
    LOCKDOWN_TIOCSSERIAL,           /* Serial port config */
    LOCKDOWN_MODULE_PARAMETERS,     /* Unsigned module parameters */
    LOCKDOWN_MMIOTRACE,             /* MMIO tracing */
    LOCKDOWN_DEBUGFS,               /* Debugfs access */
    LOCKDOWN_XMON_WR,               /* XMON write access */
    LOCKDOWN_BPF_WRITE,             /* BPF write access */
    LOCKDOWN_INTEGRITY_MAX,         /* Integrity boundary */
    LOCKDOWN_KCORE,                 /* /proc/kcore */
    LOCKDOWN_KPROBES,               /* kprobes */
    LOCKDOWN_BPF_READ,              /* BPF read access */
    LOCKDOWN_PERF,                  /* perf_event access */
    LOCKDOWN_TRACEFS,               /* tracefs access */
    LOCKDOWN_XMON_RW,               /* XMON read-write */
    LOCKDOWN_CONFIDENTIALITY_MAX,   /* Confidentiality boundary */
};
```

### Interaction with SELinux

SELinux can enforce lockdown through its policy:

```bash
# SELinux boolean for kernel lockdown enforcement
setsebool -P secure_mode_insmod on
```

When SELinux and lockdown are both active:

- SELinux provides fine-grained access control (which domains can load modules,
  which files can be accessed)
- Lockdown provides a hard floor that even SELinux policy cannot override
- The most restrictive policy wins

### Interaction with IMA/EVM

IMA (Integrity Measurement Architecture) works with lockdown to provide
comprehensive integrity:

1. IMA measures all executables, modules, and files at access time
2. IMA can require signatures on all kernel modules
3. Lockdown prevents bypassing IMA by directly patching kernel memory
4. EVM (Extended Verification Module) protects IMA metadata from tampering

## Affected Kernel Interfaces

### Fully Blocked in Integrity Mode

| Interface        | Blocked Action           | Rationale                    |
|------------------|--------------------------|------------------------------|
| `/dev/mem`       | Write                    | Arbitrary kernel code patch  |
| `/dev/kmem`      | Read/Write               | Direct kernel memory access  |
| `/proc/kcore`    | Read (confidentiality)   | Kernel memory dump           |
| `kexec_load()`   | Load new kernel          | Bypass current kernel security|
| Module loading   | Unsigned modules         | Arbitrary kernel code        |
| `bpf()`          | Write to kernel memory   | Kernel code/data modification|
| EFI variables    | Runtime writes           | Firmware/secure boot bypass  |
| Debugfs          | Security-sensitive nodes | Kernel state exposure        |

### Partially Restricted

| Interface        | Restriction              | Allowed                    |
|------------------|--------------------------|----------------------------|
| `ftrace`         | No code modification     | Read-only tracing          |
| `kprobes`        | No code patching         | Read-only probing (integrity)|
| `perf`           | Limited access           | Non-kernel-memory events   |
| `/proc/kallsyms` | May show zeros           | Symbol resolution          |
| `bpf()`          | No kernel memory write   | Network/tracing BPF (integrity)|

### Unaffected

- Standard file I/O, networking, and process management
- Hardware device access (unless it exposes kernel memory)
- Container and namespace operations
- Most userspace debugging (ptrace, GDB on userspace processes)

## Impact on Kernel Features

### Module Loading

With lockdown in integrity mode:

```bash
# This fails if the module is not signed
insmod my_module.ko

# Error: insmod: ERROR: could not insert module: Operation not permitted
# Kernel log: Lockdown: insmod: unsigned module loading is restricted
```

Modules must be signed with a key in the kernel's keyring:

```bash
# Sign a module
scripts/sign-file sha256 certs/signing_key.pem certs/signing_key.x509 my_module.ko

# Or use a distribution-signed module
modprobe ext4  # typically pre-signed by the distribution
```

### kexec

`kexec_load()` is blocked, but `kexec_file_load()` may be allowed if the kernel
image is signed and verified:

```bash
# This may work with lockdown if the kernel image is signed
kexec -l /boot/vmlinuz --initrd=/boot/initrd.img --reuse-cmdline

# This definitely fails
kexec --load-legacy /boot/vmlinuz
```

### BPF

In integrity mode:
- Network BPF programs: generally allowed
- Tracing BPF programs: allowed for read-only tracing
- BPF programs that write to kernel memory: blocked

In confidentiality mode:
- BPF programs that read kernel memory: also blocked

### Kernel Debugging

Lockdown significantly impacts kernel debugging:

- **GDB stub** (`kgdb`): blocked (can read/write kernel memory)
- **crash**: blocked (reads `/proc/kcore`)
- **ftrace**: allowed in read-only mode, but function modification blocked
- **SystemTap**: requires module loading → blocked without signing

Workaround: use a debug kernel with lockdown disabled, or sign debugging modules.

### perf

```bash
# perf partially works under lockdown
perf stat ls           # OK - counting events
perf record -g ls      # OK - sampling
perf probe -a func     # Blocked - kprobe creation requires write

# In confidentiality mode
perf top               # Blocked - reads kernel symbols
```

## Distributions and Lockdown

### Fedora/RHEL

Fedora was the first major distribution to enable lockdown by default with
Secure Boot:

```bash
# Fedora enables lockdown=integrity when Secure Boot is active
# Check with:
mokutil --sb-state
cat /sys/kernel/security/lockdown
```

### Ubuntu

Ubuntu enables lockdown with Secure Boot since 20.04:

```bash
# Ubuntu lockdown status
cat /sys/kernel/security/lockdown
```

### Debian

Debian enables lockdown in its kernel builds starting with Debian 11 (Bullseye).

### Disabling Lockdown

On most distributions, lockdown can be disabled by:

1. Disabling Secure Boot in UEFI settings
2. Adding `lockdown=none` to the kernel command line
3. Using a kernel built without `CONFIG_SECURITY_LOCKDOWN_LSM`

**Warning**: disabling lockdown reduces system security, especially on systems
exposed to network access.

```bash
# Disable lockdown via kernel command line
# Edit GRUB config:
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash lockdown=none"
sudo update-grub

# Or at boot: edit GRUB entry and add lockdown=none
```

## Building a Custom Kernel with Lockdown

```bash
# In .config
CONFIG_SECURITY_LOCKDOWN_LSM=y
CONFIG_SECURITY_LOCKDOWN_LSM_EARLY=y
CONFIG_LOCK_DOWN_KERNEL_FORCE_INTEGRITY=y
# or
CONFIG_LOCK_DOWN_KERNEL_FORCE_CONFIDENTIALITY=y

# For module signing
CONFIG_MODULE_SIG=y
CONFIG_MODULE_SIG_FORCE=y
CONFIG_MODULE_SIG_SHA256=y
CONFIG_SYSTEM_TRUSTED_KEYS="certs/signing_key.x509"
```

## Security Analysis

### Threat Model

Lockdown protects against:

1. **Post-exploitation privilege escalation**: attacker gains root, cannot load
   kernel code or patch kernel memory
2. **Evil maid attacks**: Secure Boot + lockdown ensures the running kernel
   matches what was verified at boot
3. **Insider threats**: even privileged users cannot subvert kernel security
4. **Firmware attacks**: EFI variable writes are blocked

### Limitations

1. **Hardware attacks**: lockdown does not protect against physical access,
   DMA attacks, or hardware implants
2. **Kernel vulnerabilities**: a kernel bug that allows arbitrary code execution
   bypasses lockdown (lockdown protects the kernel from root, not from itself)
3. **Denial of service**: an attacker with root can still cause denial of service
   within the constraints of lockdown
4. **Covert channels**: lockdown does not prevent information leakage through
   side channels (timing, cache, power analysis)

### Bypass Vectors

Known bypass techniques (and mitigations):

| Bypass                  | Mitigation                      |
|-------------------------|---------------------------------|
| Unsigned module via `init_module` | Blocked by lockdown LSM   |
| `/dev/mem` for code patch | Blocked in both modes        |
| `kexec` to malicious kernel | Blocked; `kexec_file_load` requires signature |
| EFI variable modification | Blocked                      |
| `/proc/kcore` memory read | Blocked in confidentiality   |
| DMA via Thunderbolt     | IOMMU, Thunderbolt security    |
| Physical memory access  | Full-disk encryption, TPM      |

## Debugging Lockdown Issues

```bash
# Check if lockdown is active
cat /sys/kernel/security/lockdown

# Check why a specific operation is blocked
dmesg | grep -i lockdown
# Lockdown: insmod: unsigned module loading is restricted
# Lockdown: /dev/mem: kmem access is restricted

# Check Secure Boot state
mokutil --sb-state

# Check if module is signed
modinfo -F sig my_module
modinfo -F signer my_module

# Verify kernel module signing
scripts/verify-module-sig /lib/modules/$(uname -r)/kernel/drivers/my_module.ko
```

## Appendix: Lockdown and Container Security

Lockdown affects containers and virtual machines:

```bash
# Containers share the host kernel
# Lockdown restrictions apply to containerized processes

# Container with privileged mode may bypass some restrictions
# But lockdown provides a hard floor

# Check lockdown from inside container
docker run --rm alpine cat /sys/kernel/security/lockdown
# [none] integrity confidentiality

# Docker with lockdown
# Use --privileged cautiously
docker run --privileged ...  # Bypasses many restrictions
# But lockdown still blocks unsigned modules, /dev/mem writes, etc.

# Kubernetes security context
apiVersion: v1
kind: Pod
spec:
  securityContext:
    privileged: false  # Don't use privileged mode
    capabilities:
      drop:
        - SYS_ADMIN  # Remove CAP_SYS_ADMIN
```

### Lockdown in Virtual Machines

```bash
# VMs have their own kernel
# Lockdown in VM is independent of host lockdown

# QEMU/KVM with Secure Boot
qemu-system-x86_64 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE.fd \
  -drive if=pflash,format=raw,file=/tmp/OVMF_VARS.fd \
  ...

# VM kernel will enable lockdown if Secure Boot is active
```

## Appendix: Lockdown vs Other Security Features

| Feature | Protects Against | Scope | Kernel Version |
|---------|-----------------|-------|----------------|
| Lockdown | Root→kernel escalation | Kernel integrity/confidentiality | 5.4+ |
| SELinux | Policy-based access control | Process/file access | 2.6+ |
| AppArmor | Path-based access control | Process/file access | 2.6.36+ |
| seccomp | Syscall filtering | Syscall level | 3.5+ |
| IMA/EVM | File integrity | File content/metadata | 2.6.30+ |
| Secure Boot | Boot chain integrity | Boot process | N/A (UEFI) |
| dm-verity | Block integrity | Root filesystem | 3.4+ |

### Layered Security

```
┌─────────────────────────────────────────┐
│  UEFI Secure Boot                       │  ← Firmware verification
├─────────────────────────────────────────┤
│  Kernel Lockdown (integrity)            │  ← Runtime integrity
├─────────────────────────────────────────┤
│  IMA/EVM                                │  ← File integrity
├─────────────────────────────────────────┤
│  SELinux / AppArmor                     │  ← Access control
├─────────────────────────────────────────┤
│  seccomp                                │  ← Syscall filtering
├─────────────────────────────────────────┤
│  Namespaces / cgroups                   │  ← Resource isolation
└─────────────────────────────────────────┘
```

## Appendix: System Administration Under Lockdown

### What Admins Can Still Do

```bash
# File operations - fully allowed
cp, mv, rm, mkdir, chmod, chown

# Process management - fully allowed
ps, top, kill, nice, systemctl

# Network configuration - fully allowed
ip, iptables, nftables, ss

# Package management - allowed (packages are signed)
apt install, dnf install

# Service management - fully allowed
systemctl start/stop/enable

# Log viewing - fully allowed
journalctl, dmesg (may be limited)

# User management - fully allowed
useradd, passwd, groupadd
```

### What Admins Cannot Do Under Lockdown

```bash
# Load unsigned kernel modules
insmod unsigned_module.ko  # BLOCKED

# Read kernel memory
cat /proc/kcore  # BLOCKED in confidentiality mode

# Patch kernel code
echo 1 > /proc/sys/kernel/ftrace_enabled  # May be restricted

# Write to /dev/mem
dd if=/dev/zero of=/dev/mem bs=1 count=1 seek=0  # BLOCKED

# kexec to new kernel
kexec -l /boot/vmlinuz --initrd=/boot/initrd.img  # BLOCKED (unsigned)

# Modify EFI variables
echo 1 > /sys/firmware/efi/efivars/TestVar  # BLOCKED
```

## Appendix: Lockdown Configuration Checklist

```bash
# 1. Enable Secure Boot in UEFI
# 2. Install signed kernel
apt install linux-image-$(uname -r)

# 3. Verify lockdown is active
cat /sys/kernel/security/lockdown
# Should show: [integrity] or [confidentiality]

# 4. Verify module signing
modinfo -F sig ext4

# 5. Test unsigned module is blocked
insmod unsigned.ko 2>&1 | grep -i lockdown

# 6. Verify /dev/mem is blocked
dd if=/dev/mem of=/dev/null bs=1 count=1 2>&1 | grep -i lockdown

# 7. Check kexec is blocked
kexec -l /boot/vmlinuz 2>&1 | grep -i lockdown

# 8. Review kernel logs for lockdown events
dmesg | grep -i lockdown
```

## See Also

- [User Namespace Security](../containers/user-namespace-security.md) —
  namespace-level privilege restrictions
- [Ring Buffer](../debugging/ring-buffer.md) — kernel data structures
  affected by lockdown
- [Page Table Isolation](../performance/page-table-isolation.md) — another
  kernel security hardening feature
- [IMA/EVM](./ima.md) — integrity measurement and appraisal
- [Secure Boot](./secure-boot.md) — UEFI trust chain
- LSM Framework — Linux Security Module framework

## Further Reading

- **Kernel source**: `security/lockdown/lockdown.c`
- **Documentation**: `Documentation/admin-guide/LSM/lockdown.rst`
- **LWN article**: ["Kernel lockdown in Linux 5.4"](https://lwn.net/Articles/790332/) —
  merge announcement and analysis
- **LWN article**: ["A lockdown update"](https://lwn.net/Articles/756915/) —
  design evolution
- **Matthew Garrett's blog**: "UEFI Secure Boot and Linux" — comprehensive
  explanation of the threat model
- **Red Hat documentation**: "Kernel lockdown mode" — RHEL-specific configuration
- **Fedora wiki**: "SecureBoot" — Fedora's Secure Boot implementation details
- **commit 5d48fe7**: "security: Add a locked-down LSM"
- **OpenSSF**: "Linux Kernel Lockdown" — security hardening overview
- **kernel.org**: "Lockdown" — LSM lockdown documentation
