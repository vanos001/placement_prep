# Yama LSM: Yet Another Mandatory Access Control

## Overview

Yama is a Linux Security Module (LSM) that provides **ptrace restrictions** and **symlink/hardlink protections**. It is designed as a simple, opt-in security enhancement that can be stacked with other LSMs (SELinux, AppArmor, Smack). Yama addresses specific attack vectors that are not covered by discretionary access control (DAC) alone.

Yama is the simplest LSM in the kernel—its entire implementation is a single file (`security/yama/lsm.c`). Despite its simplicity, it provides important protections against:

- **Ptrace attacks**: preventing processes from debugging/attaching to unrelated processes
- **Symlink attacks**: preventing symlink following in world-writable directories
- **Hardlink attacks**: preventing hardlink creation to files the user doesn't own

## Configuration

### Enabling Yama

Yama can be enabled at boot via the LSM stacking mechanism:

```bash
# Boot parameter (older kernels, before LSM stacking)
lsm=lockdown,yama,capability,landlock

# Or as the sole LSM
security=yama

# Check if Yama is active
cat /sys/kernel/security/lsm
```

In kernels with LSM stacking support (5.x+), Yama can be enabled alongside other LSMs.

### Sysctl Parameters

```bash
# Ptrace scope (main control)
/proc/sys/kernel/yama/ptrace_scope

# Values:
#   0 - No restrictions (classic behavior)
#   1 - Only parent can ptrace child (default on most distros)
#   2 - Only admin can ptrace (CAP_SYS_PTRACE required)
#   3 - No ptrace at all (fully disabled)
```

### Persisting Configuration

```bash
# Temporary (until reboot)
echo 1 > /proc/sys/kernel/yama/ptrace_scope

# Permanent
echo "kernel.yama.ptrace_scope = 1" >> /etc/sysctl.d/10-ptrace.conf
sysctl -p /etc/sysctl.d/10-ptrace.conf

# Or via systemd
systemctl restart systemd-sysctl
```

## Ptrace Restrictions

### Scope 0: Classic (Unrestricted)

```bash
echo 0 > /proc/sys/kernel/yama/ptrace_scope
```

No restrictions. Any process can ptrace any other process owned by the same user (subject to normal DAC checks). This is the traditional Linux behavior.

### Scope 1: Parent-Only (Default)

```bash
echo 1 > /proc/sys/kernel/yama/ptrace_scope
```

A process can only ptrace its **direct descendants** (children, grandchildren, etc.). This is the default on Ubuntu, Debian, and many other distributions.

This prevents:
- Attach attacks: a compromised process attaching to a victim process
- Credential theft: reading `/proc/<pid>/mem` to extract secrets
- Injection attacks: writing to another process's memory

The parent-child exception is necessary for debuggers (GDB, strace) to work—they fork the target as a child and then ptrace it.

### Scope 2: Admin-Only

```bash
echo 2 > /proc/sys/kernel/yama/ptrace_scope
```

Only processes with `CAP_SYS_PTRACE` (typically root) can ptrace. Even parent-child relationships don't help—non-root processes cannot ptrace at all.

### Scope 3: Fully Disabled

```bash
echo 3 > /proc/sys/kernel/yama/ptrace_scope
```

No process can ptrace any other process, regardless of capabilities. This is the most restrictive setting and may break debugging tools entirely.

### Scope Comparison

| Scope | Parent→Child | Same User | Root (CAP_SYS_PTRACE) | Any Process |
|-------|-------------|-----------|----------------------|-------------|
| 0 | ✓ | ✓ | ✓ | ✓ |
| 1 | ✓ | ✗ | ✓ | ✗ |
| 2 | ✗ | ✗ | ✓ | ✗ |
| 3 | ✗ | ✗ | ✗ | ✗ |

## PR_SET_PTRACER

The `prctl(PR_SET_PTRACER, pid, ...)` call allows a process to explicitly declare another process as its ptracer, even under Yama restrictions. This is essential for:

- **Crash reporters**: a crashing process can designate a crash handler (e.g., `apport`, `crash`) as its ptracer
- **Debugger registration**: a process can register a debugger before entering a restricted state
- **Container runtimes**: allowing the container monitor to ptrace processes inside the container

### API

```c
#include <sys/prctl.h>

/* Allow process 'pid' to ptrace us */
prctl(PR_SET_PTRACER, pid, 0, 0, 0);

/* Allow any process to ptrace us (used by crash handlers) */
prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0);

/* Revoke ptrace permission */
prctl(PR_SET_PTRACER, 0, 0, 0, 0);

/* Check who is allowed to ptrace us */
prctl(PR_GET_PTRACER, 0, 0, 0, 0); /* Returns pid or PR_SET_PTRACER_ANY */
```

### Special Values

| Value | Meaning |
|-------|---------|
| `0` | No ptracer designated |
| `>0` | Specific PID designated as ptracer |
| `PR_SET_PTRACER_ANY` (-1) | Any process may ptrace |

### Usage Example

```c
/* Crash handler registration */
void setup_crash_handler(void) {
    /* Tell kernel that our crash handler (PID 1234) may ptrace us */
    prctl(PR_SET_PTRACER, crash_handler_pid, 0, 0, 0);
}

/* In crash handler */
void handle_crash(pid_t target_pid) {
    ptrace(PTRACE_ATTACH, target_pid, NULL, NULL);
    /* ... read registers, memory, etc. ... */
    ptrace(PTRACE_DETACH, target_pid, NULL, NULL);
}
```

### Ptrace Scope Interaction

The `PR_SET_PTRACER` exception is checked in addition to the normal ptrace scope rules:

- **Scope 0**: No check needed, all ptrace allowed
- **Scope 1**: Ptrace allowed if target is descendant OR target has set `PR_SET_PTRACER` to our PID
- **Scope 2**: Ptrace allowed only if caller has `CAP_SYS_PTRACE` OR target has set `PR_SET_PTRACER` to our PID (still needs same UID check)
- **Scope 3**: Ptrace never allowed, `PR_SET_PTRACER` has no effect

## Link Protections

### Symlink Protection (protected_symlinks)

```bash
# Enable/disable symlink protection
/proc/sys/fs/protected_symlinks

# 0 = disabled (classic behavior)
# 1 = enabled (default on most distros)
```

When enabled, symlinks in **world-writable directories** (like `/tmp`) are only followed if:
- The follower is the owner of the symlink, OR
- The owner of the symlink is the owner of the directory

This prevents **symlink attacks** where an attacker creates a symlink in `/tmp` pointing to a sensitive file (e.g., `/etc/passwd`). When a privileged process follows the symlink, it might modify the target file with elevated permissions.

```
Attack scenario (without protection):
1. Attacker creates /tmp/foo -> /etc/shadow
2. Root process opens /tmp/foo for writing
3. Root accidentally writes to /etc/shadow

With protected_symlinks=1:
1. Attacker creates /tmp/foo -> /etc/shadow
2. Root process opens /tmp/foo
3. Kernel refuses to follow the symlink (owner mismatch)
4. Operation fails safely
```

### Hardlink Protection (protected_hardlinks)

```bash
# Enable/disable hardlink protection
/proc/sys/fs/protected_hardlinks

# 0 = disabled (classic behavior)
# 1 = enabled (default on most distros)
```

When enabled, hardlinks can only be created to files that the linker:
- Owns, OR
- Has read-write access to

This prevents **hardlink attacks** where an attacker creates a hardlink to a setuid binary. If the setuid binary is later exploited, the hardlink provides a secondary access path.

### Protected Regular Files (protected_regular)

```bash
# Value 0: no protection
# Value 1: sticky directory restriction
# Value 2: sticky + world-writable restriction (stricter)
/proc/sys/fs/protected_regular
```

This extends protection to regular files in sticky directories (like `/tmp`):

- **Value 1**: Prevents following of regular files in sticky directories when the follower is not the owner
- **Value 2**: Additionally prevents following of regular files in world-writable directories when the follower is not the owner

### Protected FIFOs (protected_fifos)

```bash
/proc/sys/fs/protected_fifos
# 0 = no protection
# 1 = prevent FIFO creation in sticky dirs by non-owners
# 2 = also prevent in world-writable dirs
```

Similar protections for named pipes in shared directories.

### Link Protection Summary

| Parameter | Default | Protects Against |
|-----------|---------|-----------------|
| `protected_symlinks` | 1 | Symlink attacks in /tmp |
| `protected_hardlinks` | 1 | Hardlink to setuid binaries |
| `protected_regular` | 1 | Regular file attacks in /tmp |
| `protected_fifos` | 1 | FIFO attacks in /tmp |

## Implementation

### Source Structure

```
security/yama/
└── lsm.c          # Complete Yama implementation (~400 lines)
```

### Key Functions

```c
/* Ptrace access check */
static int yama_ptrace_access_check(struct task_struct *child,
                                     unsigned int mode)
{
    int scope = yama_read_scope();

    switch (scope) {
    case YAMA_SCOPE_DISABLED:
        return 0;  /* No restrictions */

    case YAMA_SCOPE_RELATIONAL:
        /* Check parent-child relationship */
        if (!task_is_descendant(current, child) &&
            !ptracer_exception_found(current, child))
            return -EPERM;
        break;

    case YAMA_SCOPE_CAPABILITY:
        /* Require CAP_SYS_PTRACE */
        if (!ns_capable_noaudit(current_user_ns(), CAP_SYS_PTRACE) &&
            !ptracer_exception_found(current, child))
            return -EPERM;
        break;

    case YAMA_SCOPE_NO_ATTACH:
        return -EPERM;  /* Never allowed */
    }
    return 0;
}
```

### Task Relationship Check

The `task_is_descendant()` function walks the process tree to check if one process is a descendant of another:

```c
static int task_is_descendant(struct task_struct *parent,
                               struct task_struct *child)
{
    struct task_struct *walker = child;
    rcu_read_lock();
    while (walker) {
        if (walker == parent) {
            rcu_read_unlock();
            return 1;
        }
        walker = rcu_dereference(walker->real_parent);
    }
    rcu_read_unlock();
    return 0;
}
```

### Ptrace Exception List

Yama maintains a per-task list of ptrace exceptions:

```c
struct ptrace_relation {
    struct list_head node;
    struct task_struct *tracer;
    struct task_struct *tracee;
    bool invalid;
};
```

When `PR_SET_PTRACER` is called, a new entry is added to this list. The list is checked during `yama_ptrace_access_check()`.

### LSM Hooks

Yama registers these LSM hooks:

```c
static struct security_hook_list yama_hooks[] = {
    LSM_HOOK_INIT(ptrace_access_check, yama_ptrace_access_check),
    LSM_HOOK_INIT(ptrace_traceme, yama_ptrace_traceme),
    LSM_HOOK_INIT(task_prctl, yama_task_prctl),
    LSM_HOOK_INIT(task_free, yama_task_free),
};
```

## Stacking with Other LSMs

Yama is designed to be **stacked** with other LSMs. In modern kernels (5.x+), multiple LSMs can be active simultaneously:

```bash
# Boot with both SELinux and Yama
lsm=capability,yama,selinux
```

When stacked, the Yama hooks are called in addition to the other LSM hooks. If any LSM denies the operation, it is denied.

### LSM Stacking Order

The order in the `lsm=` parameter determines hook call order. For Yama, the order generally doesn't matter because its checks are independent of other LSMs.

## Use Cases

### Container Security

Yama is commonly used in container environments to prevent container escape via ptrace:

```bash
# Disable ptrace in containers
echo 3 > /proc/sys/kernel/yama/ptrace_scope
```

This prevents processes inside a container from ptracing the container runtime or other containers.

### Desktop Security

On desktops, scope 1 (parent-only) is a good default:

```bash
# Ubuntu default
echo 1 > /proc/sys/kernel/yama/ptrace_scope
```

This allows debuggers to work normally (they're parent processes) while preventing cross-process attacks.

### Server Hardening

On servers, scope 2 (admin-only) is recommended:

```bash
echo 2 > /proc/sys/kernel/yama/ptrace_scope
```

This requires root privileges for any ptrace operation, which is appropriate for production servers.

### Production Recommendations

| Environment | Recommended Scope | Rationale |
|-------------|-------------------|-----------|
| Development | 0 or 1 | Debugging flexibility |
| Desktop | 1 | Balance security and usability |
| Server | 2 | Maximum security for production |
| Container | 3 | Prevent container escape |
| Embedded | 3 | Minimal attack surface |

## Limitations

1. **Not a complete MAC system**: Yama only covers ptrace and link protections. It doesn't restrict file access, network access, or other operations.
2. **Scope 3 is extreme**: completely disabling ptrace breaks many debugging and monitoring tools (GDB, strace, ltrace, perf).
3. **PR_SET_PTRACER is per-process**: each process must explicitly opt in; there's no system-wide exception mechanism.
4. **Race conditions in symlink checks**: Yama's symlink protection has some inherent TOCTOU limitations, though the practical risk is low.

## Interaction with Other Security Features

### seccomp

Yama and seccomp are complementary:

- **seccomp**: restricts which system calls a process can make
- **Yama**: restricts who can ptrace the process

Using both together provides defense in depth.

```bash
# seccomp: block ptrace syscall entirely
# (for processes that never need to be debugged)
# In code:
prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
seccomp(SECCOMP_SET_MODE_FILTER, 0, &prog);
```

### Ptrace scopes in systemd

systemd uses Yama ptrace scopes:

```ini
# In a service unit
[Service]
ProtectKernelModules=yes
RestrictSUIDSGID=yes
# These indirectly interact with ptrace
```

### AppArmor / SELinux

When stacked, Yama provides an additional layer. AppArmor or SELinux can restrict ptrace independently, and Yama's restrictions are checked in addition to the MAC restrictions.

## Debugging Yama

### Audit Logs

When Yama denies a ptrace operation, it generates an audit log:

```bash
# Check audit logs for Yama denials
ausearch -m AVC -ts recent | grep yama
# Or
dmesg | grep -i yama

# Enable Yama audit logging
echo 1 > /proc/sys/kernel/yama/ptrace_scope
# Denials will appear in dmesg
```

### Testing Ptrace Scope

```bash
# Check current scope
cat /proc/sys/kernel/yama/ptrace_scope

# Test: try to strace a non-child process
strace -p <pid>  # Should fail under scope 1+

# Test: strace a child process (should work under scope 1)
strace ls /tmp

# Test: strace with root (should work under scope 2)
sudo strace -p <pid>
```

### PR_SET_PTRACER Testing

```c
/* Test program to verify PR_SET_PTRACER */
#include <sys/prctl.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    pid_t mypid = getpid();

    /* Allow any process to ptrace us */
    prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0);
    printf("PID %d: now allows any process to ptrace\n", mypid);

    /* Wait for debugger */
    pause();
    return 0;
}
```

### Common Error Messages

```bash
# "ptrace: Operation not permitted"
# Cause: Yama scope prevents ptrace
# Fix: Check scope, adjust or use PR_SET_PTRACER

# "strace: attach: ptrace(PTRACE_SEIZE, pid): Operation not permitted"
# Cause: Scope 2+, not root
# Fix: Run as root or use scope 1

# "Cannot attach to process: Operation not permitted"
# Cause: Yama or seccomp blocking
# Fix: Check both Yama scope and seccomp filters
```

## Appendix: Yama and Docker/Kubernetes

```bash
# Docker: Yama ptrace scope applies to containers
docker run --rm alpine cat /proc/sys/kernel/yama/ptrace_scope
# Shows host value (containers share kernel)

# Docker with --cap-add=SYS_PTRACE
# Allows ptrace inside container (if Yama scope allows)
docker run --cap-add=SYS_PTRACE ...

# Kubernetes: security context
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: debug
    securityContext:
      capabilities:
        add:
        - SYS_PTRACE  # Allow ptrace
```

### Container Escape Prevention

```bash
# Scope 3 prevents container escape via ptrace
# Attacker cannot ptrace host processes from container

echo 3 > /proc/sys/kernel/yama/ptrace_scope

# Verify from container
docker run --rm alpine sh -c 'cat /proc/sys/kernel/yama/ptrace_scope'
# Output: 3
```

## Appendix: Yama and Debugging Tools

| Tool | Scope 0 | Scope 1 | Scope 2 | Scope 3 |
|------|---------|---------|---------|--------|
| gdb (attach) | ✓ | ✗ | ✓ (root) | ✗ |
| gdb (fork) | ✓ | ✓ | ✓ | ✗ |
| strace -p | ✓ | ✗ | ✓ (root) | ✗ |
| strace (child) | ✓ | ✓ | ✓ | ✗ |
| ltrace -p | ✓ | ✗ | ✓ (root) | ✗ |
| perf record | ✓ | ✗ | ✓ (root) | ✗ |
| lldb (attach) | ✓ | ✗ | ✓ (root) | ✗ |
| crash | ✓ | ✗ | ✓ (root) | ✗ |

### Workarounds for Scope 2+

```bash
# Option 1: Use PR_SET_PTRACER in the target process
# Add to application startup:
prctl(PR_SET_PTRACER, debugger_pid, 0, 0, 0);

# Option 2: Run debugger as root
sudo strace -p <pid>

# Option 3: Temporarily lower scope
echo 1 > /proc/sys/kernel/yama/ptrace_scope
# ... debug ...
echo 2 > /proc/sys/kernel/yama/ptrace_scope

# Option 4: Use crash handler with PR_SET_PTRACER_ANY
prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0);
# ... crash ...
crash_handler attaches and dumps core
```

## Source Files

- `security/yama/lsm.c` — complete Yama implementation
- `include/linux/security.h` — LSM hook declarations
- `include/uapi/linux/prctl.h` — `PR_SET_PTRACER` definitions
- `kernel/sys.c` — `prctl()` implementation (calls Yama hooks)
- `security/security.c` — LSM infrastructure

## Further Reading

- **Documentation/admin-guide/LSM/Yama.rst** — kernel Yama documentation
- **LWN: Yama** — <https://lwn.net/Articles/393012/>
- **Ubuntu Yama page** — <https://wiki.ubuntu.com/Security/Features#ptrace>
- **man 2 prctl** — PR_SET_PTRACER documentation
- **man 2 ptrace** — ptrace system call
- **LSM stacking** — Documentation/security/lsm-development.rst

## See Also

- LSM Framework — Linux Security Module framework
- [seccomp](../security/seccomp.md) — system call filtering
- ptrace — ptrace system call
- [AppArmor](../security/apparmor.md) — AppArmor LSM
- [SELinux](../security/selinux.md) — SELinux LSM
