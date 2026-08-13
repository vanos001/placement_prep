# Seccomp BPF

## Overview

**Seccomp BPF** (Secure Computing with Berkeley Packet Filter) is a Linux kernel facility that allows processes to restrict which **system calls** they (and their children) can make. It uses a small BPF program as a filter, evaluated on every syscall entry, to decide whether to allow, deny, or kill the process.

Seccomp BPF is a critical security primitive for containers, sandboxing, and defense-in-depth.

> **See also:** Namespaces, [Capabilities](../security/capabilities.md), BPF

---

## Seccomp Modes

| Mode          | Description                                      |
|---------------|--------------------------------------------------|
| `SECCOMP_MODE_DISABLED` | Seccomp not active               |
| `SECCOMP_MODE_STRICT`   | Only `read`, `write`, `exit`, `sigreturn` allowed |
| `SECCOMP_MODE_FILTER`   | User-supplied BPF filter program |

### Strict Mode (Legacy)

```c
#include <linux/seccomp.h>
#include <sys/prctl.h>

prctl(PR_SET_SECCOMP, SECCOMP_MODE_STRICT);
/* From this point, only 4 syscalls are allowed */
```

### Filter Mode

```c
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <sys/prctl.h>
#include <sys/syscall.h>

/* Install a seccomp filter */
struct sock_filter filter[] = {
    /* Load syscall number */
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
             offsetof(struct seccomp_data, nr)),

    /* Allow read(0), write(1), exit(60) */
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_read, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_write, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_exit, 0, 1),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),

    /* Deny everything else with kill */
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),
};

struct sock_fprog prog = {
    .len = sizeof(filter) / sizeof(filter[0]),
    .filter = filter,
};

prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog);
```

---

## seccomp_data Structure

The BPF program receives a pointer to `struct seccomp_data`:

```c
struct seccomp_data {
    int nr;                     /* Syscall number */
    __u32 arch;                 /* AUDIT_ARCH_* value */
    __u64 instruction_pointer;  /* CPU instruction pointer */
    __u64 args[6];              /* Syscall arguments */
};
```

### BPF Access Offsets

| Offset Field                | BPF Access Expression                          |
|-----------------------------|------------------------------------------------|
| `nr`                        | `offsetof(struct seccomp_data, nr)`            |
| `arch`                      | `offsetof(struct seccomp_data, arch)`          |
| `instruction_pointer`       | `offsetof(struct seccomp_data, instruction_pointer)` |
| `args[0]` through `args[5]` | `offsetof(struct seccomp_data, args[0])` + 8*i|

---

## Return Values

The BPF program's return value determines the action:

| Return Value             | Action                                    |
|--------------------------|-------------------------------------------|
| `SECCOMP_RET_KILL_PROCESS` | Kill the entire process (SIGSYS)       |
| `SECCOMP_RET_KILL_THREAD`  | Kill the calling thread (SIGSYS)       |
| `SECCOMP_RET_TRAP`         | Send SIGSYS to the thread              |
| `SECCOMP_RET_ERRNO`        | Return errno (masked to lower 16 bits) |
| `SECCOMP_RET_USER_NOTIF`   | Forward to userspace notification fd   |
| `SECCOMP_RET_TRACE`        | Notify ptrace tracer                   |
| `SECCOMP_RET_LOG`          | Allow but log the syscall              |
| `SECCOMP_RET_ALLOW`        | Allow the syscall                      |

### Return Value Encoding

```
Bits 0-15:  Data (errno value for RET_ERRNO, 0 for others)
Bits 16-31: Reserved
Bits 32-47: Action (SECCOMP_RET_*)
Bits 48-63: Reserved
```

---

## seccomp_export_bpf

### Purpose

`seccomp_export_bpf()` exports a seccomp filter as a classic BPF (cBPF) program. This is used for:

- Inspecting installed filters
- Serialization and auditing
- Portability across processes

### API

```c
#include <linux/seccomp.h>
#include <sys/ioctl.h>

int seccomp_export_bpf(int filter_fd, void *prog, size_t size);
```

### Usage with seccomp_attr_get

```c
/* Get the filter fd via prctl or seccomp() syscall */
int fd = prctl(PR_GET_SECCOMP_FD);

/* Export as BPF bytecode */
struct sock_filter buf[256];
ssize_t len = read(fd, buf, sizeof(buf));
/* buf now contains the cBPF program */
```

---

## Architecture Validation

**Always validate the architecture** to prevent syscall number confusion across architectures:

```c
struct sock_filter filter[] = {
    /* Check architecture */
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
             offsetof(struct seccomp_data, arch)),
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K,
             AUDIT_ARCH_X86_64, 1, 0),
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),

    /* Load syscall number */
    BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
             offsetof(struct seccomp_data, nr)),

    /* ... syscall rules ... */
};
```

---

## libseccomp (Recommended)

Writing raw BPF is error-prone. **libseccomp** provides a high-level API:

```c
#include <seccomp.h>

int main(void)
{
    scmp_filter_ctx ctx;

    /* Initialize with default-deny */
    ctx = seccomp_init(SCMP_ACT_KILL_PROCESS);

    /* Allow specific syscalls */
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit_group), 0);

    /* Allow open() only for reading (arg2 = O_RDONLY) */
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(open), 1,
                     SCMP_A1(SCMP_CMP_EQ, O_RDONLY));

    /* Allow ioctl() only for specific commands */
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(ioctl), 1,
                     SCMP_A1(SCMP_CMP_EQ, TCGETS));

    /* Install the filter */
    seccomp_load(ctx);

    /* Clean up (filter is already installed) */
    seccomp_release(ctx);

    /* From here, only allowed syscalls succeed */
    return 0;
}
```

### libseccomp Rule Conditions

```c
/* Equal to */
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(open), 1,
                 SCMP_A0(SCMP_CMP_EQ, 3));

/* Not equal to */
SCMP_A1(SCMP_CMP_NE, 0)

/* Greater than */
SCMP_A2(SCMP_CMP_GT, 1024)

/* Less than or equal */
SCMP_A0(SCMP_CMP_LE, 255)

/* Masked comparison (bits in mask must match) */
SCMP_A0(SCMP_CMP_MASKED_EQ, 0xFFFF, 0x1234)
```

### Generating BPF for Inspection

```bash
# Use seccomp-tools to visualize a filter
seccomp-tools dump ./my_program

# Output:
#  line  CODE  JT   JF      K
# =================================
#  0000: 0x20 0x00 0x00 0x00000004  A = arch
#  0001: 0x15 0x00 0x05 0xc000003e  if (A != 0xc000003e) goto 0007
#  ...
```

---

## seccomp() System Call

The modern `seccomp()` syscall (since kernel 3.17) is preferred over `prctl()`:

```c
#include <linux/seccomp.h>
#include <sys/syscall.h>

/* Install a filter */
struct sock_fprog prog = { ... };
syscall(__NR_seccomp, SECCOMP_SET_MODE_FILTER, 0, &prog);

/* Get filter attributes */
struct seccomp_notif *notif;
syscall(__NR_seccomp, SECCOMP_GET_NOTIF_SIZES, 0, &sizes);
```

### Advantages over prctl()

- Supports `SECCOMP_GET_NOTIF_SIZES` for notification fd sizing
- Supports `SECCOMP_GET_ACTION_AVAIL` to check available actions
- Cleaner API for filter installation

---

## User Notification (SECCOMP_RET_USER_NOTIF)

### Concept

Since kernel 4.14, `SECCOMP_RET_USER_NOTIF` allows a filter to **forward syscall decisions** to a userspace supervisor process. The supervisor can inspect the syscall, perform it on behalf of the sandboxed process, or deny it.

### Supervisor Side

```c
#include <linux/seccomp.h>
#include <sys/ioctl.h>

/* Get notification fd from the filter */
int notify_fd = seccomp_notif_fd(ctx);

/* Wait for a notification */
struct seccomp_notif *req = NULL;
struct seccomp_notif_resp *resp = NULL;
seccomp_notif_alloc(&req, &resp);

while (1) {
    seccomp_notif_recv(notify_fd, req);

    printf("Process %d called syscall %d\n",
           req->pid, req->data.nr);

    /* Inspect and decide */
    if (req->data.nr == __NR_open) {
        /* Read the filename from the sandboxed process's memory */
        char path[256];
        seccomp_notif_id_recv(notify_fd, req->id, req, 0);
        /* ... read args ... */

        resp->id = req->id;
        resp->error = 0;        /* Allow */
        resp->val = 0;
        seccomp_notif_respond(notify_fd, resp);
    } else {
        resp->id = req->id;
        resp->error = -EPERM;   /* Deny */
        seccomp_notif_respond(notify_fd, resp);
    }
}
```

### Use Cases

- **Container runtimes** — OCI runtime monitoring
- **Sandboxing** — Chrome sandbox, Flatpak
- **Syscall auditing** — Record all syscalls from untrusted code

---

## Common Seccomp Profiles

### Docker Default Profile

Docker's default seccomp profile allows ~44 syscalls and blocks dangerous ones:

```json
{
    "defaultAction": "SCMP_ACT_ERRNO",
    "defaultErrnoRet": 1,
    "architectures": ["SCMP_ARCH_X86_64"],
    "syscalls": [
        {
            "names": ["read", "write", "open", "close",
                      "stat", "fstat", "mmap", "mprotect",
                      "munmap", "brk", "exit_group"],
            "action": "SCMP_ACT_ALLOW"
        }
    ]
}
```

### Minimal Sandboxed Profile

```json
{
    "defaultAction": "SCMP_ACT_KILL_PROCESS",
    "syscalls": [
        {
            "names": ["read", "write", "exit", "exit_group"],
            "action": "SCMP_ACT_ALLOW"
        }
    ]
}
```

---

## Integration with Containers

### Docker

```bash
# Use default profile
docker run --security-opt seccomp=default ubuntu

# Use custom profile
docker run --security-opt seccomp=myprofile.json ubuntu

# Disable seccomp (not recommended)
docker run --security-opt seccomp=unconfined ubuntu
```

### Kubernetes

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: seccomp-pod
spec:
  securityContext:
    seccompProfile:
      type: Localhost
      localhostProfile: profiles/my-seccomp.json
  containers:
  - name: app
    image: myapp
    securityContext:
      seccompProfile:
        type: RuntimeDefault
```

### systemd

```ini
# /etc/systemd/system/my-service.service
[Service]
SystemCallFilter=@system-service
SystemCallFilter=~@mount  # Remove mount-related syscalls
SystemCallArchitectures=native
```

---

## Testing Seccomp Filters

### Audit Mode First

Before enforcing, test with `SECCOMP_RET_LOG` to see what syscalls are used:

```json
{
    "defaultAction": "SCMP_RET_LOG",
    "syscalls": [...]
}
```

```bash
# Check audit log for blocked syscalls
dmesg | grep "seccomp"
# or
journalctl | grep "seccomp"
```

### strace Analysis

```bash
# Find all syscalls used by a program
strace -f -e trace=all ./my_program 2>&1 | \
    awk -F'(' '{print $1}' | sort -u
```

### seccomp-tools

```bash
# Install
gem install seccomp-tools

# Dump filter from a running process
seccomp-tools dump $(pidof my_program)

# Trace syscalls with filter applied
seccomp-tools asm my_filter.asm
```

---

## Troubleshooting

### Common Issues

| Problem                          | Cause                              | Solution                          |
|----------------------------------|------------------------------------|-----------------------------------|
| `EPERM` on allowed syscalls      | Missing architecture check         | Add `AUDIT_ARCH_*` check          |
| Process killed unexpectedly      | `KILL_PROCESS` on missing syscall  | Use `LOG` first to test           |
| `prctl` fails with `EINVAL`      | Missing `PR_SET_NO_NEW_PRIVS`      | Call `prctl(PR_SET_NO_NEW_PRIVS)` before filter |
| Child processes can bypass filter | Using `KILL_THREAD` instead of `KILL_PROCESS` | Use `SECCOMP_RET_KILL_PROCESS` |

### Debug Checklist

```bash
# 1. Check kernel support
zcat /proc/config.gz | grep SECCOMP

# 2. Enable audit logging
echo 1 > /proc/sys/kernel/printk

# 3. Test with LOG action first
# Change defaultAction to SCMP_RET_LOG

# 4. Check for missing syscalls
strace -c ./my_program
```

---

## Advanced Filter Techniques

### Multi-Level Filtering

Seccomp supports **layered filters** — each new filter is prepended to the chain. The most recently installed filter runs first:

```c
/* Layer 1: Base filter (installed by container runtime) */
/* Allows ~44 syscalls */

/* Layer 2: Application filter (installed by app) */
/* Further restricts to only needed syscalls */

/* Example: Application adds its own filter on top */
scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);

/* Block specific dangerous syscalls even if base allows them */
seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(ptrace), 0);
seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(mount), 0);
seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(reboot), 0);

seccomp_load(ctx);
```

### Argument-Based Filtering

Filter based on syscall arguments for fine-grained control:

```c
/* Allow ioctl() only for specific terminal operations */
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(ioctl), 1,
                 SCMP_A1(SCMP_CMP_EQ, TCGETS));
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(ioctl), 1,
                 SCMP_A1(SCMP_CMP_EQ, TCSETS));

/* Allow open() only for reading (flags & O_ACCMODE == O_RDONLY) */
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(openat), 1,
                 SCMP_A2(SCMP_CMP_MASKED_EQ, O_ACCMODE, O_RDONLY));

/* Allow prctl() only for specific operations */
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(prctl), 1,
                 SCMP_A0(SCMP_CMP_EQ, PR_SET_NAME));
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(prctl), 1,
                 SCMP_A0(SCMP_CMP_EQ, PR_GET_NAME));

/* Allow socket() only for specific domains */
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(socket), 1,
                 SCMP_A0(SCMP_CMP_EQ, AF_UNIX));
seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(socket), 1,
                 SCMP_A0(SCMP_CMP_EQ, AF_INET));
```

### BPF Jump Table Optimization

For many syscalls, use a jump table pattern instead of linear scanning:

```c
/* Inefficient: linear search (O(n) per syscall) */
BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_read, 0, 1),
BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_write, 0, 1),
BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
/* ... many more ... */

/* Efficient: binary search or jump table */
/* Load syscall number, subtract base, jump into table */
BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
BPF_STMT(BPF_ALU | BPF_SUB | BPF_K, __NR_read),  /* Normalize */
BPF_JUMP(BPF_JMP | BPF_JGE | BPF_K, 10, 0, default_action),
/* Jump table based on normalized value */
```

### Seccomp Notify with Supervisor

The `SECCOMP_RET_USER_NOTIF` mechanism enables sophisticated supervisor programs:\n
```c
#include <linux/seccomp.h>
#include <sys/ioctl.h>

/* Supervisor process */
int supervisor_loop(int notify_fd) {
    struct seccomp_notif *req = NULL;
    struct seccomp_notif_resp *resp = NULL;
    struct seccomp_notif_sizes sizes;

    syscall(__NR_seccomp, SECCOMP_GET_NOTIF_SIZES, 0, &sizes);
    req = malloc(sizes.seccomp_notif);
    resp = malloc(sizes.seccomp_notif_resp);

    while (1) {
        /* Wait for a notification */
        if (ioctl(notify_fd, SECCOMP_IOCTL_NOTIF_RECV, req) < 0)
            continue;

        printf("PID %d called syscall %lld\n", req->pid, req->data.nr);

        /* Decision logic */
        switch (req->data.nr) {
        case __NR_openat: {
            /* Read filename from sandboxed process */
            char path[PATH_MAX];
            struct iovec iov = { path, sizeof(path) };
            struct seccomp_notif_addfd addfd = {
                .id = req->id,
                .flags = SECCOMP_ADDFD_FLAG_SEND,
            };

            /* Read the path argument */
            process_vm_readv(req->pid, &iov, 1, /* ... */);

            /* Check against policy */
            if (is_path_allowed(path)) {
                /* Open file on behalf of sandboxed process */
                int fd = open(path, req->data.args[1]);
                addfd.fd = fd;
                ioctl(notify_fd, SECCOMP_IOCTL_NOTIF_ADDFD, &addfd);
            } else {
                resp->id = req->id;
                resp->error = -EACCES;
                ioctl(notify_fd, SECCOMP_IOCTL_NOTIF_SEND, resp);
            }
            break;
        }
        default:
            resp->id = req->id;
            resp->error = -EPERM;
            ioctl(notify_fd, SECCOMP_IOCTL_NOTIF_SEND, resp);
        }
    }
}
```

### Systemd System Call Filtering

systemd provides high-level seccomp configuration:

```ini
[Service]
# Allow only specific syscall groups
SystemCallFilter=@system-service @io-event @network-io

# Deny specific groups
SystemCallFilter=~@mount @reboot @swap @clock @debug

# Kill process on violation (default)
SystemCallErrorNumber=EPERM

# Restrict to native architecture
SystemCallArchitectures=native

# Log violations
SystemCallLog=@system-service

# Example: Minimal service
SystemCallFilter=read write open close mmap mprotect
SystemCallFilter=~@privileged @resources
```

### Go seccomp Profile Generator

```go
package main

import (
    "encoding/json"
    "fmt"
    "os/exec"
    "strings"
)

// Generate seccomp profile by tracing a program
func generateProfile(binary string) {
    // Run under strace to collect syscalls
    cmd := exec.Command("strace", "-f", "-e", "trace=all", binary)
    output, _ := cmd.CombinedOutput()

    // Parse unique syscalls
    syscalls := make(map[string]bool)
    for _, line := range strings.Split(string(output), "\n") {
        if idx := strings.Index(line, "("); idx > 0 {
            syscall := strings.TrimSpace(line[:idx])
            if !strings.HasPrefix(syscall, "---") {
                syscalls[syscall] = true
            }
        }
    }

    // Generate profile
    profile := map[string]interface{}{
        "defaultAction": "SCMP_ACT_KILL_PROCESS",
        "syscalls": []map[string]interface{}{{
            "names": mapKeys(syscalls),
            "action": "SCMP_ACT_ALLOW",
        }},
    }

    json.NewEncoder(os.Stdout).Encode(profile)
}
```

## Security Considerations

### TOCTOU (Time-of-Check-Time-of-Use)

When using `SECCOMP_RET_USER_NOTIF`, the supervisor reads arguments from the sandboxed process's memory. Between the read and the action, the sandboxed process could modify the arguments:

```c
/* Mitigation: use SECCOMP_IOCTL_NOTIF_ADDFD */
/* This atomically adds a file descriptor to the sandboxed process */
/* The supervisor opens the file and passes the fd */

/* Also: use process_vm_readv for consistent reads */
/* Pin memory pages where possible */
```

### Filter Complexity Limits

The kernel limits BPF filter complexity:

```bash
# Maximum instructions per filter (default: 4096)
cat /proc/sys/kernel/seccomp/actions_logged

# Maximum filter stack depth (default: 256)
# Each nested filter counts toward the limit
```

### Audit Logging

```bash
# Enable seccomp audit logging
echo 1 > /proc/sys/kernel/seccomp/actions_logged

# Check audit log
ausearch -m SECCOMP

# Example audit entry:
# type=SECCOMP msg=audit(1234567890.123:456): auid=1000 uid=1000
#   pid=1234 comm="myapp" exe="/usr/bin/myapp"
#   sig=0 arch=c000003e syscall=16 compat=0
#   code=SECCOMP_RET_ERRNO
```

## Further Reading

- [Linux kernel source: `kernel/seccomp.c`](https://elixir.bootlin.com/linux/latest/source/kernel/seccomp/)
- [kernel.org: Seccomp BPF](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
- [seccomp(2) man page](https://man7.org/linux/man-pages/man2/seccomp.2.html)
- [libseccomp](https://github.com/seccomp/libseccomp)
- [seccomp-tools](https://github.com/david942j/seccomp-tools)
- [Docker: Seccomp security profiles](https://docs.docker.com/engine/security/seccomp/)
- [Kubernetes: Seccomp](https://kubernetes.io/docs/tutorials/security/seccomp/)
- [LWN: A seccomp overview](https://lwn.net/Articles/656307/)

> **Related topics:** Namespaces, [Capabilities](../security/capabilities.md), BPF, Container Security
