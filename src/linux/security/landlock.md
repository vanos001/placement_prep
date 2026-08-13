# Landlock: Unprivileged Sandboxing

## Introduction

Landlock is a Linux security module (LSM) that enables **unprivileged process sandboxing**.
Introduced in Linux 5.13, Landlock allows any process to restrict its own access rights
(and those of its children) without requiring root privileges or any specific capabilities.
Unlike SELinux or AppArmor, which are managed by system administrators, Landlock is
designed to be used by applications themselves to reduce their attack surface after
they have performed necessary initialization.

## Design Principles

```mermaid
graph TD
    A[Application] --> B[Initialization Phase]
    B --> C[Restrict Access with Landlock]
    C --> D[Sandboxed Execution]
    D --> E{Attempt access}
    E -->|Allowed by rules| F[Access granted]
    E -->|Not in rules| G[Access denied]
    E -->|Kernel already denies| H[Access denied]
```

Key principles:
1. **Unprivileged**: No root or capabilities required
2. **Composable**: Multiple layers can stack
3. **Progressive**: Rules can only restrict, never expand access
4. **Filesystem-centric**: Primarily controls file access
5. **ABI-versioned**: Forward-compatible through versioned rule types

## Architecture

```mermaid
graph TD
    subgraph "User Space"
        A[Process] --> B[landlock_create_ruleset]
        B --> C[landlock_add_rule]
        C --> D[landlock_restrict_self]
    end

    subgraph "Kernel LSM Framework"
        E[Security Hooks]
        F[Landlock LSM]
        G[Ruleset Stack]
    end

    D --> F
    E --> F
    F --> G
    G --> H{Access Decision}
    H -->|Allowed| I[Permit]
    H -->|Denied| J[EPERM]
```

## System Calls

Landlock provides three system calls:

### landlock_create_ruleset()

Creates a new ruleset for collecting access control rules:

```c
#include <linux/landlock.h>
#include <sys/syscall.h>

int landlock_create_ruleset(const struct landlock_ruleset_attr *attr,
                             size_t size, __u32 flags)
{
    return syscall(__NR_landlock_create_ruleset, attr, size, flags);
}
```

```c
struct landlock_ruleset_attr {
    __u64 handled_access_fs;    /* Filesystem access rights to control */
    __u64 handled_access_net;   /* Network access rights (Linux 6.7+) */
};
```

### landlock_add_rule()

Adds a rule (e.g., filesystem path access) to a ruleset:

```c
int landlock_add_rule(int ruleset_fd, enum landlock_rule_type rule_type,
                       const void *rule_attr, __u32 flags)
{
    return syscall(__NR_landlock_add_rule, ruleset_fd, rule_type,
                    rule_attr, flags);
}
```

### landlock_restrict_self()

Applies the ruleset to the calling process:

```c
int landlock_restrict_self(int ruleset_fd, __u32 flags)
{
    return syscall(__NR_landlock_restrict_self, ruleset_fd, flags);
}
```

## Filesystem Access Rights

```c
/* Filesystem access rights (bitmask) */
#define LANDLOCK_ACCESS_FS_EXECUTE         (1ULL << 0)
#define LANDLOCK_ACCESS_FS_WRITE_FILE      (1ULL << 1)
#define LANDLOCK_ACCESS_FS_READ_FILE       (1ULL << 2)
#define LANDLOCK_ACCESS_FS_READ_DIR        (1ULL << 3)
#define LANDLOCK_ACCESS_FS_REMOVE_DIR      (1ULL << 4)
#define LANDLOCK_ACCESS_FS_REMOVE_FILE     (1ULL << 5)
#define LANDLOCK_ACCESS_FS_MAKE_CHAR       (1ULL << 6)
#define LANDLOCK_ACCESS_FS_MAKE_DIR        (1ULL << 7)
#define LANDLOCK_ACCESS_FS_MAKE_REG        (1ULL << 8)
#define LANDLOCK_ACCESS_FS_MAKE_SOCK       (1ULL << 9)
#define LANDLOCK_ACCESS_FS_MAKE_FIFO       (1ULL << 10)
#define LANDLOCK_ACCESS_FS_MAKE_BLOCK      (1ULL << 11)
#define LANDLOCK_ACCESS_FS_MAKE_SYM        (1ULL << 12)
#define LANDLOCK_ACCESS_FS_REFER           (1ULL << 13)
#define LANDLOCK_ACCESS_FS_TRUNCATE        (1ULL << 14)
```

## Network Access Rights (Linux 6.7+)

```c
#define LANDLOCK_ACCESS_NET_BIND_TCP      (1ULL << 0)
#define LANDLOCK_ACCESS_NET_CONNECT_TCP   (1ULL << 1)
```

## ABI Versioning

Landlock uses versioned ABI to maintain forward compatibility:

```c
/* ABI versions and their capabilities */
#define LANDLOCK_RULE_PATH_BENEATH  1  /* v1: Basic path restrictions */
#define LANDLOCK_RULE_NET_PORT      2  /* v2: Network port restrictions */

/* Handled access rights per version */
/* v1 (5.13+): read_file, write_file, execute, read_dir, etc. */
/* v2 (6.2+):  + remove_file, remove_dir, refer, truncate */
/* v3 (6.7+):  + network access (bind_tcp, connect_tcp) */
```

### Checking ABI Version

```c
int get_landlock_abi_version(void)
{
    return landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION);
}
```

### ABI Version Details

| ABI Version | Kernel Version | Capabilities |
|-------------|---------------|--------------|
| 1 | 5.13+ | Basic FS: read, write, execute, read_dir, make_* |
| 2 | 6.2+ | + remove_file, remove_dir, refer, truncate |
| 3 | 6.7+ | + network: bind_tcp, connect_tcp |
| 4 | 6.10+ | + scoping (scoped signal, abstract unix sockets) |

## Complete Example: Filesystem Sandbox

```c
#define _GNU_SOURCE
#include <linux/landlock.h>
#include <sys/syscall.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static inline int
landlock_create_ruleset(const struct landlock_ruleset_attr *const attr,
                        const size_t size, const __u32 flags)
{
    return syscall(__NR_landlock_create_ruleset, attr, size, flags);
}

static inline int
landlock_add_rule(const int ruleset_fd,
                  const enum landlock_rule_type rule_type,
                  const void *const rule_attr, const __u32 flags)
{
    return syscall(__NR_landlock_add_rule, ruleset_fd, rule_type,
                    rule_attr, flags);
}

static inline int
landlock_restrict_self(const int ruleset_fd, const __u32 flags)
{
    return syscall(__NR_landlock_restrict_self, ruleset_fd, flags);
}

int setup_sandbox(void)
{
    int ruleset_fd, abi;
    struct landlock_ruleset_attr ruleset_attr;
    struct landlock_path_beneath_attr path_beneath;
    int err;

    /* Check Landlock ABI version */
    abi = landlock_create_ruleset(NULL, 0, LANDLOCK_CREATE_RULESET_VERSION);
    if (abi < 0) {
        perror("Landlock not supported");
        return -1;
    }
    printf("Landlock ABI version: %d\n", abi);

    /* Define which access rights to restrict */
    ruleset_attr.handled_access_fs =
        LANDLOCK_ACCESS_FS_READ_FILE |
        LANDLOCK_ACCESS_FS_WRITE_FILE |
        LANDLOCK_ACCESS_FS_READ_DIR |
        LANDLOCK_ACCESS_FS_EXECUTE |
        LANDLOCK_ACCESS_FS_MAKE_REG |
        LANDLOCK_ACCESS_FS_MAKE_DIR |
        LANDLOCK_ACCESS_FS_REMOVE_FILE |
        LANDLOCK_ACCESS_FS_REMOVE_DIR;

    /* Create ruleset */
    ruleset_fd = landlock_create_ruleset(&ruleset_attr,
                                          sizeof(ruleset_attr), 0);
    if (ruleset_fd < 0) {
        perror("landlock_create_ruleset");
        return -1;
    }

    /* Allow reading from /usr */
    int usr_fd = open("/usr", O_PATH | O_CLOEXEC);
    if (usr_fd < 0) { perror("open /usr"); return -1; }

    path_beneath.parent_fd = usr_fd;
    path_beneath.allowed_access =
        LANDLOCK_ACCESS_FS_READ_FILE |
        LANDLOCK_ACCESS_FS_READ_DIR |
        LANDLOCK_ACCESS_FS_EXECUTE;

    err = landlock_add_rule(ruleset_fd, LANDLOCK_RULE_PATH_BENEATH,
                             &path_beneath, 0);
    if (err) { perror("landlock_add_rule /usr"); return -1; }
    close(usr_fd);

    /* Allow reading and writing to /tmp */
    int tmp_fd = open("/tmp", O_PATH | O_CLOEXEC);
    if (tmp_fd < 0) { perror("open /tmp"); return -1; }

    path_beneath.parent_fd = tmp_fd;
    path_beneath.allowed_access =
        LANDLOCK_ACCESS_FS_READ_FILE |
        LANDLOCK_ACCESS_FS_WRITE_FILE |
        LANDLOCK_ACCESS_FS_READ_DIR |
        LANDLOCK_ACCESS_FS_MAKE_REG |
        LANDLOCK_ACCESS_FS_REMOVE_FILE;

    err = landlock_add_rule(ruleset_fd, LANDLOCK_RULE_PATH_BENEATH,
                             &path_beneath, 0);
    if (err) { perror("landlock_add_rule /tmp"); return -1; }
    close(tmp_fd);

    /* Apply the sandbox (irreversible) */
    err = landlock_restrict_self(ruleset_fd, 0);
    if (err) { perror("landlock_restrict_self"); return -1; }

    close(ruleset_fd);
    printf("Sandbox applied!\n");
    return 0;
}

int main(void)
{
    if (setup_sandbox())
        return 1;

    /* Now restricted: can read /usr, read/write /tmp */
    /* Cannot access /etc, /home, /root, etc. */

    /* This works: */
    FILE *f = fopen("/tmp/test.txt", "w");
    if (f) {
        fprintf(f, "sandboxed write\n");
        fclose(f);
    }

    /* This fails with EPERM: */
    f = fopen("/etc/passwd", "r");
    if (!f) {
        perror("Access to /etc/passwd denied (expected)");
    }

    return 0;
}
```

## Network Sandbox Example (Linux 6.7+)

```c
int setup_network_sandbox(void)
{
    struct landlock_ruleset_attr ruleset_attr = {
        .handled_access_net =
            LANDLOCK_ACCESS_NET_BIND_TCP |
            LANDLOCK_ACCESS_NET_CONNECT_TCP,
    };

    int ruleset_fd = landlock_create_ruleset(&ruleset_attr,
                                              sizeof(ruleset_attr), 0);
    if (ruleset_fd < 0) return -1;

    /* Allow binding to port 8080 */
    struct landlock_net_port_attr port_attr = {
        .allowed_access = LANDLOCK_ACCESS_NET_BIND_TCP,
        .port = 8080,
    };

    landlock_add_rule(ruleset_fd, LANDLOCK_RULE_NET_PORT,
                       &port_attr, 0);

    /* Allow connecting to port 443 */
    struct landlock_net_port_attr connect_attr = {
        .allowed_access = LANDLOCK_ACCESS_NET_CONNECT_TCP,
        .port = 443,
    };

    landlock_add_rule(ruleset_fd, LANDLOCK_RULE_NET_PORT,
                       &connect_attr, 0);

    /* Apply */
    landlock_restrict_self(ruleset_fd, 0);
    close(ruleset_fd);

    /* Now: can bind to port 8080, connect to port 443 only */
    return 0;
}
```

## Rule Stacking

Landlock supports stacking multiple ruleset layers:

```mermaid
graph TD
    A[Layer 3: Only /tmp write] --> B[Layer 2: /usr read + /tmp read/write]
    B --> C[Layer 1: All FS access]
    C --> D{Final Policy}
    D --> E[Most restrictive wins]
```

```c
/* Each restrict_self() call adds a new layer */
/* Layers can only restrict, never expand */

/* Layer 1: Full access (before any restrictions) */
/* Process starts with all normal permissions */

/* Layer 2: Restrict to /usr and /tmp */
landlock_restrict_self(ruleset_fd_2, 0);

/* Layer 3: Further restrict to only /tmp write */
landlock_restrict_self(ruleset_fd_3, 0);
/* Now only /tmp write is allowed */
```

### Stacking Rules from Parent to Child

```c
/* Parent sets up base sandbox */
void parent_sandbox(void) {
    int rs = create_basic_sandbox();  /* Allow /usr, /lib, /tmp */
    landlock_restrict_self(rs, 0);
}

/* Child applies additional restrictions */
void child_sandbox(void) {
    int rs = create_restrictive_sandbox();  /* Only /tmp */
    landlock_restrict_self(rs, 0);
    /* Child has intersection of parent and child rules */
}
```

## LSM Integration

Landlock hooks into the LSM framework at key security decision points:

```c
/* security/landlock/fs.c - simplified hook */
static int hook_file_open(const struct file *file)
{
    /* Check the Landlock ruleset stack */
    return check_access(file->f_path.dentry,
                         LANDLOCK_ACCESS_FS_READ_FILE);
}

static int hook_inode_create(struct inode *dir,
                              struct dentry *dentry, umode_t mode)
{
    return check_access(dir,
                         LANDLOCK_ACCESS_FS_MAKE_REG);
}
```

### Hook Points

| LSM Hook | Landlock Control |
|----------|-----------------|
| `file_open` | read_file, write_file, execute |
| `inode_create` | make_reg, make_dir, make_sock, etc. |
| `inode_unlink` | remove_file |
| `inode_rmdir` | remove_dir |
| `inode_rename` | refer (cross-directory moves) |
| `inode_mkdir` | make_dir |
| `file_truncate` | truncate |
| `socket_bind` | bind_tcp |
| `socket_connect` | connect_tcp |

## Comparison with Other Sandboxing

| Feature | Landlock | seccomp | SELinux | AppArmor |
|---------|----------|---------|---------|----------|
| Unprivileged | ✓ | ✓ | ✗ | ✗ |
| File path control | ✓ | ✗ | ✓ | ✓ |
| Network control | ✓ (v3) | ✗ | ✓ | ✓ |
| Syscall filtering | ✗ | ✓ | ✗ | ✗ |
| Stacking | ✓ | ✓ | ✗ | ✗ |
| Policy complexity | Low | Medium | High | Medium |
| Per-process | ✓ | ✓ | System-wide | System-wide |
| Runtime application | ✓ | ✓ | ✗ | ✗ |

### Combining Landlock with seccomp

```c
/* Use Landlock for filesystem + seccomp for syscalls */
int setup_full_sandbox(void)
{
    /* First: restrict filesystem with Landlock */
    setup_landlock_sandbox();

    /* Then: restrict syscalls with seccomp */
    setup_seccomp_filter();

    return 0;
}
```

## Tools and Libraries

### landlock-utils

```bash
# Install
apt install landlock-utils

# Create and apply a sandbox
landlock-sandbox --read /usr --read /lib --write /tmp -- /usr/bin/myapp
```

### landlock-cli (Community Tool)

```bash
# Install from source
git clone https://github.com/landlock-lsm/landlock-tools
cd landlock-tools && make

# Usage
./landlock-cli --read /usr --read /lib --read /etc --write /tmp -- bash
```

### Rust Binding

```rust
use landlock::*;

fn sandbox() -> Result<(), Error> {
    let ruleset = Ruleset::new()
        .handle_access(AccessFs::from_all(ABI::V2))?
        .create()?;

    ruleset.add_rule(PathBeneath::new(
        PathFd::new("/usr")?,
        AccessFs::from_read(ABI::V2),
    ))?;

    ruleset.restrict_self()?;
    Ok(())
}
```

### Python Binding (pylandlock)

```python
import landlock

# Create sandbox
ruleset = landlock.Ruleset()
ruleset.add_rule("/usr", landlock.ACCESS_FS_READ_FILE | landlock.ACCESS_FS_READ_DIR)
ruleset.add_rule("/tmp", landlock.ACCESS_FS_READ_FILE | landlock.ACCESS_FS_WRITE_FILE)
ruleset.restrict_self()

# Now restricted
# This works:
open("/tmp/test.txt", "w")

# This fails:
open("/etc/passwd", "r")  # EPERM
```

## Kernel Configuration

```
CONFIG_SECURITY_LANDLOCK=y
```

## Detection in User Space

```c
int check_landlock_support(void)
{
    int abi = landlock_create_ruleset(NULL, 0,
                                       LANDLOCK_CREATE_RULESET_VERSION);
    if (abi < 0) {
        if (errno == ENOSYS)
            printf("Landlock not supported by kernel\n");
        else if (errno == EOPNOTSUPP)
            printf("Landlock disabled (CONFIG_SECURITY_LANDLOCK=n)\n");
        return 0;
    }
    printf("Landlock ABI version: %d\n", abi);
    return abi;
}
```

## Common Use Cases

### Web Browser Sandbox

```c
/* Restrict browser to read-only filesystem except downloads */
void sandbox_browser(void) {
    /* Allow reading system files */
    add_path_rule(ruleset, "/usr", READ | EXECUTE);
    add_path_rule(ruleset, "/lib", READ | EXECUTE);
    add_path_rule(ruleset, "/etc", READ);

    /* Allow writing to downloads only */
    add_path_rule(ruleset, home_downloads, READ | WRITE | MAKE_REG);

    /* Allow network access to HTTPS */
    add_net_rule(ruleset, 443, CONNECT_TCP);

    /* Apply */
    landlock_restrict_self(ruleset, 0);
}
```

### Build System Sandbox

```c
/* Restrict build system to source and build directories */
void sandbox_build(void) {
    add_path_rule(ruleset, source_dir, READ | EXECUTE);
    add_path_rule(ruleset, build_dir, READ | WRITE | MAKE_REG | MAKE_DIR);
    add_path_rule(ruleset, "/usr", READ | EXECUTE);
    add_path_rule(ruleset, "/tmp", READ | WRITE | MAKE_REG);

    /* No network access during build */
    /* (network ruleset with empty rules = no network) */

    landlock_restrict_self(ruleset, 0);
}
```

### Container Runtime Sandbox

```c
/* Apply Landlock inside container for defense in depth */
void sandbox_container(void) {
    /* Container already has namespace isolation */
    /* Landlock adds file-level restrictions */

    add_path_rule(ruleset, "/app", READ | EXECUTE);
    add_path_rule(ruleset, "/app/data", READ | WRITE);
    add_path_rule(ruleset, "/tmp", READ | WRITE);
    add_path_rule(ruleset, "/etc/resolv.conf", READ);

    landlock_restrict_self(ruleset, 0);
}
```

## Troubleshooting

```bash
# Check if Landlock is supported
# Method 1: Kernel version
uname -r  # >= 5.13

# Method 2: ABI check
python3 -c "
import ctypes, ctypes.util
libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
NR = 444  # __NR_landlock_create_ruleset on x86_64
abi = libc.syscall(NR, None, 0, 0)
print(f'ABI version: {abi}' if abi >= 0 else 'Not supported')
"

# Method 3: Check kernel config
zcat /proc/config.gz | grep LANDLOCK
# CONFIG_SECURITY_LANDLOCK=y

# Check if Landlock is enabled
cat /sys/kernel/security/lsm
# Should include "landlock"

# Common issues:
# ENOSYS: Kernel doesn't support Landlock (< 5.13)
# EOPNOTSUPP: CONFIG_SECURITY_LANDLOCK=n
# EPERM: Access denied by Landlock rules
# EINVAL: Invalid ruleset or rule attributes
```

## Security Considerations

### Limitations

1. **No network granularity**: Cannot restrict to specific IPs (only ports)
2. **No IPC control**: Cannot restrict IPC mechanisms (except abstract Unix sockets in v4)
3. **Path-based**: Rules are path-based, not inode-based (hardlinks can bypass)
4. **No dynamic rules**: Rules cannot be added after `restrict_self()`
5. **Inheritance**: Child processes inherit all parent restrictions

### Threat Model

| Attack | Landlock Defense | Limitation |
|--------|-----------------|------------|
| File exfiltration | Restrict read access | Only FS paths, not network |
| Malicious writes | Restrict write access | Cannot prevent all writes |
| Privilege escalation | No new privileges | Cannot expand access |
| Container escape | File restrictions | Not a complete container solution |
| Network attacks | Port restrictions (v3) | No IP-level restrictions |

## Cross-References

- [seccomp](seccomp.md) - System call filtering (complementary)
- [SELinux](selinux.md) - Mandatory access control
- [AppArmor](apparmor.md) - Path-based mandatory access control
- [Capabilities](capabilities.md) - Fine-grained privileges
- [Security Model](security-model.md) - Linux security overview
- [Namespaces](../kernel/processes/namespaces.md) - Resource isolation
- [seccomp notify](../containers/seccomp-notify.md) - seccomp user notification

## Further Reading

- [Landlock documentation](https://www.kernel.org/doc/html/latest/userspace-api/landlock.html)
- [Landlock RFC (LWN.net)](https://lwn.net/Articles/703939/)
- [Landlock merged in 5.13 (LWN.net)](https://lwn.net/Articles/858234/)
- [Mickaël Salaün's Landlock talk](https://www.youtube.com/watch?v=UkIvREfS0qM)
- [landlock.io (project page)](https://landlock.io/)
- [landlock-lsm GitHub](https://github.com/landlock-lsm)
- [Landlock network support (LWN.net)](https://lwn.net/Articles/918106/)
