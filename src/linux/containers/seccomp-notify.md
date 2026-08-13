# Seccomp Notify: SECCOMP_RET_USER_NOTIF

## Introduction

Seccomp (Secure Computing Mode) notify, introduced in Linux 5.0, allows a **supervisor
process** to handle system calls made by a sandboxed process. When a seccomp filter
returns `SECCOMP_RET_USER_NOTIF`, the system call is suspended, and a notification is
sent to a listener process via a file descriptor. The supervisor can inspect the call,
optionally emulate it, and return a result. This enables sophisticated sandboxing where
system call policy decisions are delegated to a user-space process.

## Architecture Overview

```mermaid
flowchart TD
    A[Sandboxed Process] --> B[Syscall Entry]
    B --> C[seccomp Filter]
    C --> D{Filter Result}
    D -->|ALLOW| E[Execute syscall]
    D -->|DENY| F[Return -EPERM]
    D -->|USER_NOTIF| G[Suspend syscall]
    G --> H[Send notification to listener FD]
    H --> I[Supervisor Process]
    I --> J{Decision}
    J -->|Emulate| K[Perform equivalent action]
    J -->|Forward| L[SECCOMP_IOCTL_NOTIF_SEND]
    J -->|Deny| M[Return error to sandboxed]
    K --> N[Return result]
    L --> O[Kernel executes real syscall]
    O --> N
    N --> P[Sandboxed process resumes]
```

## System Call Flow

### Sandboxed Process (Client)

The sandboxed process installs a seccomp filter that returns `SECCOMP_RET_USER_NOTIF`
for certain system calls:

```c
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <sys/prctl.h>

/* Install seccomp filter that sends notifications for openat */
int install_seccomp_filter(void)
{
    struct sock_filter filter[] = {
        /* Load syscall number */
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                 offsetof(struct seccomp_data, nr)),

        /* If openat, notify supervisor */
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_openat, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_USER_NOTIF),

        /* If open, notify supervisor */
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_open, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_USER_NOTIF),

        /* Otherwise, allow */
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
    };

    struct sock_fprog prog = {
        .len = sizeof(filter) / sizeof(filter[0]),
        .filter = filter,
    };

    /* Enable seccomp with the filter */
    prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
    return prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog, 0, 0);
}
```

### Supervisor Process (Listener)

The supervisor receives and handles notifications:

```c
#include <linux/seccomp.h>
#include <sys/ioctl.h>

int setup_supervisor(pid_t child_pid)
{
    int listener;

    /* Get the notification FD from the seccomp filter */
    /* (The FD is obtained via prctl(PR_GET_SECCOMP_LISTENER) or */
    /*  inherited/received from the process that installed the filter) */
    struct seccomp_notif_req *req;
    struct seccomp_notif_resp *resp;

    /* Allocate notification structures */
    req = malloc(sizeof(*req));
    resp = malloc(sizeof(*resp));

    while (1) {
        /* Receive a notification (blocks until a syscall is intercepted) */
        if (ioctl(listener, SECCOMP_IOCTL_NOTIF_RECV, req) < 0) {
            perror("SECCOMP_IOCTL_NOTIF_RECV");
            break;
        }

        printf("Notification: pid=%d, syscall=%lld, args=[%llx, %llx, %llx]\n",
               req->pid, req->data.nr,
               req->data.args[0], req->data.args[1], req->data.args[2]);

        /* Handle the syscall */
        resp->id = req->id;

        if (req->data.nr == __NR_openat) {
            /* Emulate: perform the open on behalf of the sandboxed process */
            int fd = openat(req->data.args[0],
                            (const char *)req->data.args[1],
                            req->data.args[2], req->data.args[3]);
            resp->error = 0;
            resp->val = fd;
        } else {
            /* Deny */
            resp->error = -EPERM;
            resp->val = 0;
        }

        /* Send the response back */
        if (ioctl(listener, SECCOMP_IOCTL_NOTIF_SEND, resp) < 0) {
            perror("SECCOMP_IOCTL_NOTIF_SEND");
        }
    }

    free(req);
    free(resp);
    return 0;
}
```

## Kernel Implementation

### Notification Structures

```c
/* include/uapi/linux/seccomp.h */

struct seccomp_data {
    int nr;                     /* System call number */
    __u32 arch;                 /* AUDIT_ARCH_* */
    __u64 instruction_pointer;  /* EIP/RIP */
    __u64 args[6];              /* System call arguments */
};

struct seccomp_notif {
    __u64 id;                   /* Unique notification ID */
    __u32 pid;                  /* PID of the target process */
    __u32 flags;                /* SECCOMP_NOTIF_FLAG_* */
    struct seccomp_data data;   /* System call data */
};

struct seccomp_notif_resp {
    __u64 id;                   /* Must match notification ID */
    __s64 val;                  /* Return value */
    __s32 error;                /* Error code (0 for success) */
    __u32 flags;                /* SECCOMP_NOTIF_FLAG_* */
};
```

### Filter Result Handling

```c
/* kernel/seccomp.c - simplified */
static int seccomp_do_user_notification(int this_syscall,
                                         struct seccomp_data *sd,
                                         struct seccomp_filter *match)
{
    struct seccomp_notif *notification;

    /* Allocate notification */
    notification = kzalloc(sizeof(*notification), GFP_KERNEL);
    notification->id = atomic64_inc_return(&match->notif_id);
    notification->pid = current->pid;
    memcpy(&notification->data, sd, sizeof(*sd));

    /* Add to pending notifications list */
    list_add_tail(&notification->list, &match->notif->pending);

    /* Wake up the listener */
    wake_up(&match->notif->wqh);

    /* Wait for response */
    wait_event(match->notif->response_wait,
               notification->state == SECCOMP_NOTIF_REPLIED);

    /* Return the response to the syscall dispatcher */
    if (notification->resp.error)
        return notification->resp.error;
    return notification->resp.val;
}
```

## ioctl Operations

| ioctl | Description |
|-------|-------------|
| `SECCOMP_IOCTL_NOTIF_RECV` | Receive a pending notification |
| `SECCOMP_IOCTL_NOTIF_SEND` | Send a response to a notification |
| `SECCOMP_IOCTL_NOTIF_ID_VALID` | Check if a notification ID is still valid |
| `SECCOMP_IOCTL_NOTIF_ADDFD` | Add a file descriptor to the target process |

### Adding File Descriptors (SECCOMP_IOCTL_NOTIF_ADDFD)

Instead of performing the syscall on behalf of the target, the supervisor can
inject file descriptors directly:

```c
/* Supervisor: open a file and inject the FD into the sandboxed process */
int inject_fd(int listener, int local_fd, int target_fd)
{
    struct seccomp_notif_addfd addfd = {
        .id = req->id,                    /* Match the notification */
        .srcfd = local_fd,                /* FD in supervisor */
        .newfd = target_fd,               /* Target FD number (0 = auto) */
        .flags = SECCOMP_ADDFD_FLAG_SEND, /* Also send response */
    };

    return ioctl(listener, SECCOMP_IOCTL_NOTIF_ADDFD, &addfd);
}
```

### Validating Notification IDs

```c
/* Check if the target process is still alive */
int is_notification_valid(int listener, __u64 id)
{
    struct seccomp_notif_id_valid valid = { .id = id };
    return ioctl(listener, SECCOMP_IOCTL_NOTIF_ID_VALID, &valid) == 0;
}
```

## Use Cases

### Container Runtime Proxy

Container runtimes use seccomp notify to proxy system calls:

```mermaid
flowchart TD
    A[Container Process] --> B[seccomp filter]
    B --> C{Dangerous syscall?}
    C -->|mount, pivot_root| D[USER_NOTIF]
    C -->|read, write| E[ALLOW]
    D --> F[Container Runtime]
    F --> G[Validate arguments]
    G -->|Allowed| H[SECCOMP_NOTIF_SEND]
    G -->|Denied| I[Return -EPERM]
    H --> J[Container process resumes]
```

### Filesystem Sandboxing

```c
/* Supervisor: intercept openat and restrict paths */
void handle_openat(int listener, struct seccomp_notif_req *req)
{
    const char *pathname = read_string_from_target(req->pid,
                                                    req->data.args[1]);

    /* Validate path */
    if (strncmp(pathname, "/etc/", 5) == 0) {
        /* Deny access to /etc */
        deny_notification(listener, req, -EACCES);
    } else if (strncmp(pathname, "/safe/", 6) == 0) {
        /* Allow and proxy the syscall */
        forward_notification(listener, req);
    } else {
        deny_notification(listener, req, -EPERM);
    }
}
```

### Syscall Auditing

```c
/* Supervisor: log all file opens */
void audit_openat(struct seccomp_notif_req *req)
{
    struct seccomp_data *data = &req->data;
    char *path = read_string_from_target(req->pid, data->args[1]);

    log_audit("PID=%d opened '%s' flags=%lld mode=%lld",
              req->pid, path, data->args[2], data->args[3]);

    free(path);
}
```

## Security Considerations

### TOCTOU (Time-of-Check-to-Time-of-Use) Races

```mermaid
sequenceDiagram
    participant S as Sandboxed
    participant K as Kernel
    participant L as Listener

    S->>K: openat("/safe/foo")
    K->>L: Notify (path="/safe/foo")
    Note over S: S races: changes memory
    Note over S: Path now = "/etc/shadow"
    L->>K: Forward (openat)
    K->>K: Opens /etc/shadow!
```

**Mitigation**: Use `SECCOMP_IOCTL_NOTIF_ADDFD` to inject FDs rather than
forwarding syscalls, or use `/proc/pid/mem` to read arguments atomically:

```c
/* Atomic read of target's memory via /proc/pid/mem */
char *read_target_string(pid_t pid, unsigned long addr)
{
    char path[64], buf[PATH_MAX];
    int fd;
    ssize_t nread;

    snprintf(path, sizeof(path), "/proc/%d/mem", pid);
    fd = open(path, O_RDONLY);
    if (fd < 0) return NULL;

    nread = pread(fd, buf, sizeof(buf) - 1, addr);
    close(fd);

    if (nread <= 0) return NULL;
    buf[nread] = '\0';
    return strdup(buf);
}
```

### Process Exit Races

```c
/* Always validate notification ID before responding */
int safe_respond(int listener, struct seccomp_notif_req *req,
                 struct seccomp_notif_resp *resp)
{
    struct seccomp_notif_id_valid valid = { .id = req->id };

    /* Verify the target hasn't exited */
    if (ioctl(listener, SECCOMP_IOCTL_NOTIF_ID_VALID, &valid) < 0) {
        /* Target exited, notification is stale */
        return -1;
    }

    return ioctl(listener, SECCOMP_IOCTL_NOTIF_SEND, resp);
}
```

### Supervisor Privilege Model

```c
/* The supervisor typically runs with elevated privileges */
/* It should be isolated and minimal */

/* Drop capabilities after setup */
cap_drop_bound(CAP_SYS_ADMIN);
cap_clear bounding_set;

/* Apply seccomp to the supervisor too (defense in depth) */
apply_supervisor_seccomp_filter();
```

## Complete Example: Minimal Proxy Sandbox

```c
#define _GNU_SOURCE
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>

static int listener_fd;

/* Supervisor loop */
void supervisor_loop(void)
{
    struct seccomp_notif *req;
    struct seccomp_notif_resp *resp;

    req = malloc(sizeof(*req));
    resp = malloc(sizeof(*resp));

    while (1) {
        if (ioctl(listener_fd, SECCOMP_IOCTL_NOTIF_RECV, req) < 0)
            break;

        printf("[SUPERVISOR] pid=%d syscall=%lld\n",
               req->pid, req->data.nr);

        resp->id = req->id;

        switch (req->data.nr) {
        case __NR_write:
            /* Allow writes */
            resp->error = 0;
            resp->val = req->data.args[2]; /* Return count */
            break;
        case __NR_exit:
        case __NR_exit_group:
            /* Allow exits */
            resp->error = 0;
            resp->val = 0;
            break;
        default:
            /* Deny everything else */
            resp->error = -EPERM;
            resp->val = 0;
            break;
        }

        if (ioctl(listener_fd, SECCOMP_IOCTL_NOTIF_SEND, resp) < 0)
            break;
    }

    free(req);
    free(resp);
}

int main(void)
{
    pid_t child;

    /* Create notification socketpair */
    int fds[2];
    socketpair(AF_UNIX, SOCK_STREAM, 0, fds);
    listener_fd = fds[0];

    child = fork();
    if (child == 0) {
        /* Child: sandboxed process */
        close(fds[0]);

        /* Install seccomp filter */
        struct sock_filter filter[] = {
            BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                     offsetof(struct seccomp_data, nr)),
            BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_write, 0, 1),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_USER_NOTIF),
            BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_exit, 0, 1),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_USER_NOTIF),
            BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, __NR_exit_group, 0, 1),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_USER_NOTIF),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
        };
        struct sock_fprog prog = {
            .len = sizeof(filter) / sizeof(filter[0]),
            .filter = filter,
        };

        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
        prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog, 0, 0);

        /* Try syscalls */
        write(STDOUT_FILENO, "Hello from sandbox!\n", 20);
        /* This would be blocked: open("/etc/passwd", O_RDONLY); */
        return 0;
    }

    /* Parent: supervisor */
    close(fds[1]);
    supervisor_loop();
    waitpid(child, NULL, 0);

    return 0;
}
```

## Tools and Libraries

### Go: seccomp-notify-bpf

```go
package main

import (
    "github.com/seccomp/libseccomp-golang"
)

func main() {
    // Create filter with USER_NOTIF
    filter := seccomp.NewFilter(seccomp.ActAllow)
    filter.AddRule(seccomp.ScmpSyscall(openatNr), seccomp.ActNotify)
    filter.Load()
}
```

### OCI Runtime Integration

```json
{
    "linux": {
        "seccomp": {
            "defaultAction": "SCMP_ACT_ALLOW",
            "architectures": ["SCMP_ARCH_X86_64"],
            "syscalls": [
                {
                    "names": ["mount", "umount2"],
                    "action": "SCMP_ACT_NOTIFY"
                }
            ]
        }
    }
}
```

## Kernel Configuration

```
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
CONFIG_SECCOMP_USER_NOTIFICATION=y
```

## Cross-References

- [seccomp](../security/seccomp.md) - seccomp fundamentals and BPF filters
- [BPF (Berkeley Packet Filter)](../debugging/ebpf.md) - BPF for filtering
- [Capabilities](../security/capabilities.md) - Fine-grained privileges
- [Namespaces](../kernel/processes/namespaces.md) - Resource isolation
- [Docker Internals](../containers/docker-internals.md) - Container security
- [Container Security](../containers/security.md) - Container hardening
- [Landlock](../security/landlock.md) - Complementary filesystem sandboxing

## seccomp-notify in Container Runtimes

### Podman and conmon

Podman uses seccomp-notify via conmon (container monitor) for enhanced container security:

```bash
# Podman's container runtime configuration with seccomp-notify
# /etc/containers/seccomp.json — OCI-compliant seccomp profile

# Enable seccomp-notify for a container
podman run --security-opt seccomp=notify:listener.sock \
    docker.io/library/alpine:latest

# conmon creates a Unix socket for the listener
# The supervisor (conmon or external) receives notifications

# Podman's built-in seccomp profile:
# https://github.com/containers/common/blob/main/pkg/seccomp/default.json
# Blocks: mount, kexec_load, reboot, swapon, swapoff, sysfs, etc.
# Allows: read, write, open, close, stat, mmap, etc.
```

### Docker seccomp Profiles

```bash
# Docker uses seccomp profiles (not notify by default)
# Default profile: https://github.com/moby/moby/blob/master/profiles/seccomp/default.json

# Run with custom seccomp profile
docker run --security-opt seccomp=custom-profile.json alpine

# Run without seccomp (NOT recommended)
docker run --security-opt seccomp=unconfined alpine

# Docker's default profile blocks ~44 of ~300+ syscalls
# Including: kexec_load, mount, reboot, swapon, etc.
```

### Containerd and seccomp-notify

```bash
# containerd supports seccomp-notify through the OCI runtime spec
# In config.toml:
# [plugins."io.containerd.grpc.v1.cri".containerd]
#   default_runtime_name = "runc"
# [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
#   runtime_type = "io.containerd.runc.v2"
#   [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
#     BinaryName = "runc"
```

## Performance Considerations

### Overhead of seccomp-notify

```c
// seccomp-notify has two main overhead sources:
// 1. Context switch: syscall → filter → notification → supervisor → response
// 2. Supervisor processing time per notification

// Typical overhead per intercepted syscall:
// Without seccomp-notify: ~100ns (direct syscall)
// With SECCOMP_RET_ALLOW: ~200ns (filter evaluation)
// With SECCOMP_RET_USER_NOTIF: ~10-50µs (depends on supervisor)
```

### When to Use seccomp-notify vs. Other Mechanisms

| Mechanism | Overhead | Use Case |
|-----------|----------|----------|
| SECCOMP_RET_ALLOW | ~100ns | No filtering needed |
| SECCOMP_RET_ERRNO | ~200ns | Simple deny with error |
| SECCOMP_RET_KILL | ~200ns | Immediate termination |
| SECCOMP_RET_USER_NOTIF | ~10-50µs | Complex policy decisions |
| SECCOMP_RET_TRACE | ~5-20µs | ptrace-based tracing |
| ptrace | ~50-200µs | Full syscall interception |

```bash
# Benchmark seccomp overhead
# Install seccomp benchmark tool
git clone https://github.com/seccomp/libseccomp.git
cd libseccomp/tests
make bench
./bench

# Compare:
# No filter:      ~100ns/syscall
# Simple allow:   ~200ns/syscall
# Simple deny:    ~250ns/syscall
# USER_NOTIF:     ~15µs/syscall (with fast supervisor)
```

## seccomp-notify vs. ptrace

| Aspect | seccomp-notify | ptrace |
|--------|---------------|--------|
| Mechanism | Filter-based notification | Full process tracing |
| Privilege | Filter owner + listener | CAP_SYS_PTRACE |
| Process state | Suspended during notification | Stopped (SIGSTOP) |
| Overhead | ~10-50µs | ~50-200µs |
| Granularity | Syscall-level | Syscall + signal + memory |
| Sandboxing | Primary use case | Debugging/tracing |
| Multi-thread | Per-thread notifications | Per-thread tracing |
| Race conditions | TOCTOU risk | Lower risk |

## Advanced: Combining seccomp-notify with Landlock

Landlock and seccomp-notify can be combined for defense in depth:

```c
// Landlock: filesystem access control (kernel-enforced, no supervisor needed)
// seccomp-notify: syscall-level control (supervisor-mediated)

// Combined approach:
// 1. Apply Landlock for filesystem restrictions (fast, kernel-enforced)
// 2. Apply seccomp-notify for remaining syscalls (mount, umount, etc.)
// 3. Supervisor handles complex policy decisions

// This reduces the number of notifications (Landlock handles common cases)
// while maintaining flexibility for complex decisions
```

## Advanced: seccomp-notify with pidfd

Linux 5.9+ supports pidfd for race-free process identification:

```c
#include <sys/pidfd.h>

// Get pidfd for the target process
int pidfd = pidfd_open(req->pid, 0);

// Use pidfd for race-free operations:
// - /proc/pid/mem access (via pidfd)
// - Signal delivery (pidfd_send_signal)
// - Process status check

// This avoids PID reuse races when the target exits
```

## seccomp-notify Limitations

### Cannot Intercept All Syscalls

```c
// seccomp-notify cannot intercept syscalls that are:
// 1. Already executed (SECCOMP_RET_USER_NOTIF only works pre-execution)
// 2. Architecture-specific (must match arch in seccomp_data)
// 3. vDSO calls (clock_gettime, gettimeofday, etc.)
//    vDSO calls bypass the syscall interface entirely

// The vDSO limitation means you cannot intercept:
// - clock_gettime() — often used via vDSO for performance
// - gettimeofday() — same
// - time() — sometimes via vDSO
// - getcpu() — sometimes via vDSO

// Workaround: set SECCOMP_FILTER_FLAG_TSYNC to apply filter to all threads
```

### Thread Handling

```c
// seccomp filters are per-thread by default
// Use SECCOMP_FILTER_FLAG_TSYNC to sync across all threads

prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog, 0, 0);
// Only this thread gets the filter

// For multi-threaded applications:
// Option 1: Apply filter before creating threads
// Option 2: Use TSYNC flag
// Option 3: Use seccomp(SECCOMP_SET_MODE_FILTER, flags, &prog) syscall
//   with SECCOMP_FILTER_FLAG_TSYNC
```

### Notification Queue Depth

```c
// The notification queue has a limited depth
// If the supervisor doesn't consume notifications fast enough,
// subsequent syscalls will block or fail

// Check and set queue depth (via seccomp_attr_set):
// SECCOMP_USER_NOTIF_FLAG_CONTINUE — continue with default action on timeout
```

## seccomp-notify vs. AppArmor and SELinux

| Feature | seccomp-notify | AppArmor | SELinux |
|---------|---------------|----------|---------|
| Scope | Syscall filtering | Path-based MAC | Label-based MAC |
| Supervisor | User-space process | Kernel | Kernel |
| Granularity | Per-syscall | Per-file-path | Per-object-label |
| Policy language | BPF | Profile files | Policy modules |
| Flexibility | Very high (Turing-complete supervisor) | Moderate | High |
| Performance | Per-notification overhead | Kernel-only (fast) | Kernel-only (fast) |
| Container use | OCI runtime integration | AppArmor profiles for containers | SELinux contexts for containers |

## Further Reading

- [seccomp user notification (LWN.net)](https://lwn.net/Articles/756233/)
- [seccomp notify documentation](https://www.kernel.org/doc/html/latest/userspace-api/seccomp_filter.html)
- [SECCOMP_RET_USER_NOTIF patches](https://lore.kernel.org/lkml/?q=SECCOMP_RET_USER_NOTIF)
- [Tycho Andersen's seccomp notify talk](https://www.youtube.com/watch?v=iU7JqH9i3sI)
- [OCI runtime spec: seccomp](https://github.com/opencontainers/runtime-spec/blob/main/config-linux.md#seccomp)
- [libseccomp](https://github.com/seccomp/libseccomp)
- [seccomp notify proxy example](https://github.com/containers/conmon)
- [Landlock documentation](https://docs.kernel.org/userspace-api/landlock.html)
- [Podman seccomp](https://github.com/containers/common/tree/main/pkg/seccomp)


