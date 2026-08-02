# Linux Capabilities

## Overview

Linux capabilities split the traditional "all-or-nothing" root privilege into fine-grained units. Instead of giving a process full root access (UID 0), you can grant only the specific privileges it needs. This implements the **principle of least privilege** at the kernel level.

## Motivation

Traditional Unix has a binary privilege model:
- **UID 0 (root)**: Can do anything — mount filesystems, bind ports < 1024, load kernel modules, access all files
- **Non-root**: Very limited

This is dangerous. A web server running as root can be exploited to do anything. But the web server only needs to bind port 80 — it doesn't need to load kernel modules!

```
Without capabilities:
  Web server needs port 80 → must run as root → can do EVERYTHING
  If exploited → attacker has full root access

With capabilities:
  Web server gets CAP_NET_BIND_SERVICE → can bind port 80 ONLY
  If exploited → attacker can only bind ports, not load modules
```

## Capability Categories

```
┌──────────────────────────────────────────────────────────────┐
│              Linux Capability Categories                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  File-Related                                        │    │
│  │  CAP_CHOWN          - Change file ownership          │    │
│  │  CAP_DAC_OVERRIDE   - Bypass file permission checks  │    │
│  │  CAP_DAC_READ_SEARCH- Bypass read/search checks      │    │
│  │  CAP_FOWNER         - Bypass owner checks            │    │
│  │  CAP_FSETID         - Set file sticky/setgid bits    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Network-Related                                     │    │
│  │  CAP_NET_ADMIN      - Network configuration          │    │
│  │  CAP_NET_BIND_SERVICE- Bind ports < 1024             │    │
│  │  CAP_NET_BROADCAST  - Send broadcast packets         │    │
│  │  CAP_NET_RAW        - Use raw sockets                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Process-Related                                     │    │
│  │  CAP_KILL           - Send signals to any process    │    │
│  │  CAP_SETUID         - Change UID                     │    │
│  │  CAP_SETGID         - Change GID                     │    │
│  │  CAP_SETPCAP        - Modify capability sets         │    │
│  │  CAP_SYS_PTRACE     - Trace any process              │    │
│  │  CAP_SYS_NICE       - Change process priority        │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  System-Related                                      │    │
│  │  CAP_SYS_ADMIN      - Catch-all "superpower"         │    │
│  │  CAP_SYS_BOOT       - Reboot the system              │    │
│  │  CAP_SYS_MODULE     - Load/unload kernel modules     │    │
│  │  CAP_SYS_RAWIO      - Raw I/O port access            │    │
│  │  CAP_SYS_RESOURCE   - Override resource limits        │    │
│  │  CAP_SYS_TIME       - Set system clock               │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Security-Related                                    │    │
│  │  CAP_LINUX_IMMUTABLE- Immutable file flag            │    │
│  │  CAP_AUDIT_CONTROL  - Configure audit system         │    │
│  │  CAP_AUDIT_WRITE    - Write to audit log             │    │
│  │  CAP_MKNOD          - Create device files            │    │
│  │  CAP_LEASE           - Establish file leases         │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Capability Sets

Each process has **four** capability sets:

```
┌──────────────────────────────────────────────────────────────┐
│              Process Capability Sets                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Permitted (P)                                       │    │
│  │  • Capabilities the process may use                  │    │
│  │  • Superset of effective and inheritable             │    │
│  │  • Process can add to effective set from here        │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Effective (E)                                       │    │
│  │  • Capabilities actually used for access checks      │    │
│  │  • Subset of permitted                               │    │
│  │  • This is what matters for most permission checks   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Inheritable (I)                                     │    │
│  │  • Capabilities that may be inherited across         │    │
│  │    exec()                                            │    │
│  │  • Child process gets: (P_parent & I_parent &        │    │
│  │    file_I) | (P_child & file_P)                      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Bounding Set (B)                                    │    │
│  │  • Upper limit on capabilities a process can gain    │    │
│  │  • Cannot be raised once lowered                     │    │
│  │  • Used for sandboxing                               │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Ambient (A)                                         │    │
│  │  • Capabilities preserved across exec() of           │    │
│  │    non-setuid programs                               │    │
│  │  • For unprivileged processes to retain caps         │    │
│  │  • Linux 4.3+                                        │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Capability Inheritance Across exec()

```
When process execs a new program:

New effective = (file_permitted & inheritable) | (process_permitted & file_inheritable & inheritable) | ambient

Where:
- file_permitted: capabilities in the file's permitted set
- file_inheritable: capabilities in the file's inheritable set
- process_permitted: process's permitted set
- inheritable: process's inheritable set
- ambient: process's ambient set

Simplified rules:
1. If file is setuid-root: new permitted = file_permitted (full root)
2. If file has no setuid: capabilities come from process + file inheritable sets
3. Ambient caps are added if the file has no setuid
```

## Real-World Linux Examples

### Viewing Capabilities

```bash
# View capabilities of a file
getcap /usr/bin/ping
# /usr/bin/ping = cap_net_raw+ep

# View capabilities of a running process
getpcaps $$
# 12345: =

# View all capabilities of current process
cat /proc/self/status | grep Cap
# CapInh: 0000000000000000
# CapPrm: 0000000000000000
# CapEff: 0000000000000000
# CapBnd: 0000003fffffffff
# CapAmb: 0000000000000000

# Decode capability bitmask
capsh --decode=0000000000000000

# View all capabilities
capsh --print
# Current: =
# Bounding set = cap_chown,cap_dac_override,...,cap_sys_admin,...
```

### Setting File Capabilities

```bash
# Give ping the ability to use raw sockets (instead of setuid-root)
sudo setcap cap_net_raw+ep /usr/bin/ping

# Give a binary multiple capabilities
sudo setcap cap_net_bind_service,cap_net_raw+ep /usr/bin/myserver

# Remove file capabilities
sudo setcap -r /usr/bin/myserver

# Find all files with capabilities
getcap -r / 2>/dev/null
```

### Dropping Capabilities

```c
#include <linux/capability.h>
#include <sys/prctl.h>

// Drop all capabilities except needed ones
void drop_privileges(void) {
    // Keep only CAP_NET_BIND_SERVICE
    cap_value_t caps[] = { CAP_NET_BIND_SERVICE };
    
    cap_t cap = cap_init();  // Empty capability set
    
    // Set the capability
    cap_set_flag(cap, CAP_PERMITTED, 1, caps, CAP_SET);
    cap_set_flag(cap, CAP_EFFECTIVE, 1, caps, CAP_SET);
    
    // Apply to process
    cap_set_proc(cap);
    cap_free(cap);
    
    // Prevent regaining capabilities
    prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
}
```

### Docker/Container Capabilities

```bash
# Docker drops most capabilities by default
# Run with specific capabilities
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE myimage

# View container capabilities
docker run --rm alpine sh -c 'cat /proc/self/status | grep Cap'

# Kubernetes security context
# spec:
#   containers:
#   - name: myapp
#     securityContext:
#       capabilities:
#         drop: ["ALL"]
#         add: ["NET_BIND_SERVICE"]
```

### Common Capabilities for Applications

```bash
# Web server (bind port 80)
setcap cap_net_bind_service+ep /usr/sbin/nginx

# Network tool (ping, traceroute)
setcap cap_net_raw+ep /usr/bin/ping

# NTP daemon (set time)
setcap cap_sys_time+ep /usr/sbin/ntpd

# Application that needs to change UID
setcap cap_setuid,cap_setgid+ep /usr/bin/myapp

# Application that needs to trace other processes
setcap cap_sys_ptrace+ep /usr/bin/strace
```

## The Dangerous CAP_SYS_ADMIN

```
CAP_SYS_ADMIN is the "god capability" — it's equivalent to root for many operations:
- Mount filesystems
- Use pivot_root
- Configure namespaces
- Set hostname
- Many ioctl operations
- Quota management
- Device access

⚠ Avoid giving CAP_SYS_ADMIN — it's too broad
✓ Use specific capabilities instead

If you need CAP_SYS_ADMIN, consider:
1. Can you use a more specific capability?
2. Can you use a seccomp profile to restrict what the process does with it?
3. Can you use SELinux to confine the process even with this capability?
```

## Capability vs setuid

```
Traditional setuid approach:
  /usr/bin/ping is setuid-root
  ping runs as root
  ping can do ANYTHING (security risk!)
  If ping has a bug → attacker gets root

Capabilities approach:
  /usr/bin/ping has cap_net_raw
  ping runs as normal user
  ping can ONLY use raw sockets
  If ping has a bug → attacker only gets raw socket access
```

## Interview Questions

### Beginner

**Q: What are Linux capabilities?**
A: Capabilities split root's all-powerful privileges into fine-grained units. Instead of giving a process full root access, you grant only specific privileges like `CAP_NET_BIND_SERVICE` (bind ports < 1024) or `CAP_NET_RAW` (use raw sockets). This limits the damage if the process is compromised.

**Q: Why would you use capabilities instead of setuid-root?**
A: A setuid-root program runs with full root privileges, meaning any vulnerability gives an attacker complete control. With capabilities, the program only has the specific privileges it needs. For example, `ping` with `CAP_NET_RAW` can send ICMP packets but can't load kernel modules or access all files.

### Intermediate

**Q: Explain the four capability sets of a process.**
A:
- **Permitted**: The maximum capabilities the process can have. Acts as a ceiling.
- **Effective**: The capabilities actually used for permission checks. This is what matters for access control.
- **Inheritable**: Capabilities that can be passed to child processes across `exec()`.
- **Bounding set**: An upper limit that can only be decreased, never increased. Used for permanent capability restriction.

A capability must be in the permitted set to be added to the effective set. The bounding set limits what can ever appear in permitted.

**Q: How do capabilities work with containers?**
A: Containers (Docker, Kubernetes) drop most capabilities by default. A container typically has a subset like `CAP_NET_BIND_SERVICE`, `CAP_CHOWN`, `CAP_SETUID`, etc. This means even if the container is compromised, the attacker can't mount filesystems, load modules, or perform other dangerous operations. You can further restrict by dropping all capabilities and adding only what's needed.

### FAANG-Level

**Q: Design a capability-based security model for a microservice that needs to read files from a specific directory, bind port 443, and connect to a database. How would you minimize its attack surface?**

A:

```
Requirements:
1. Read files from /data/app/ only
2. Bind TCP port 443
3. Connect to database on port 5432
4. Nothing else

Design:

1. File access (don't use capabilities):
   - Run as unprivileged user (UID 1000)
   - Set directory permissions: /data/app/ owned by UID 1000
   - Use seccomp to block open() on other paths
   - Or use SELinux policy to confine file access

2. Port binding:
   - Grant CAP_NET_BIND_SERVICE
   - This allows binding port 443
   - Drop after binding (prctl PR_CAP_AMBIENT_DROP)

3. Network access:
   - Use iptables/nftables to allow outbound to db:5432 only
   - Drop CAP_NET_RAW (no raw sockets needed)
   - Use seccomp to block raw socket syscalls

4. Capability bounding:
   prctl(PR_CAP_BSET_DROP, CAP_SYS_ADMIN, ...);
   prctl(PR_CAP_BSET_DROP, CAP_SYS_MODULE, ...);
   // Drop all capabilities except needed ones from bounding set

5. Seccomp profile:
   // Allow: read, write, open, close, mmap, brk, socket, connect, bind, listen, accept
   // Block: mount, reboot, kexec, ptrace, etc.
   // This limits what syscalls the process can make

6. SELinux policy:
   type myservice_t;
   type myservice_data_t;
   allow myservice_t myservice_data_t:file { read open };
   allow myservice_t port_443_t:tcp_socket { name_bind };
   allow myservice_t postgresql_port_t:tcp_socket { connect };

Final capability set:
  Permitted: CAP_NET_BIND_SERVICE
  Effective: CAP_NET_BIND_SERVICE
  Inheritable: (empty)
  Bounding: CAP_NET_BIND_SERVICE
  Ambient: (empty, dropped after bind)

Attack surface after hardening:
  ✓ Can only read /data/app/ (SELinux + Unix permissions)
  ✓ Can only bind port 443 (capability)
  ✓ Can only connect to db:5432 (iptables)
  ✓ Can only make ~20 syscalls (seccomp)
  ✗ Cannot: mount, load modules, ptrace, reboot, raw sockets
```

**Q: How would you use capabilities to implement a "sudo-lite" that gives a user specific root-like powers without full sudo?**

A:

```
Traditional sudo: user gets FULL root
sudo-lite: user gets specific capabilities

Implementation:

1. File-based capabilities on specific programs:
   # Instead of making /usr/bin/systemctl setuid-root:
   setcap cap_dac_override,cap_sys_admin+ep /usr/bin/systemctl
   # Now systemctl can manage services without full root

2. Wrapper scripts with ambient capabilities:
   #!/bin/bash
   # restart-nginx.sh — allows user to restart nginx without root
   exec capsh --caps="cap_net_bind_service+ep" -- -c "systemctl restart nginx"

3. Systemd capability bounding:
   [Service]
   CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_DAC_READ_SEARCH
   AmbientCapabilities=CAP_NET_BIND_SERVICE
   User=www-data

4. PAM capability module:
   # /etc/security/capability.conf
   cap_net_bind_service    alice
   # Alice gets CAP_NET_BIND_SERVICE on login

5. Per-program capability via systemd:
   # Allow specific users to run specific services with capabilities
   # No sudo needed!

Comparison:
  sudo systemctl restart nginx
  → Runs as full root (dangerous)

  sudo-lite with capabilities:
  → Runs with CAP_SYS_ADMIN only (much safer)
  → Can't read /etc/shadow, load modules, etc.

Tradeoffs:
  ✓ Finer-grained than sudo
  ✓ Audit trail per capability
  ✓ No shared root password
  ✗ More complex to configure
  ✗ Some operations need CAP_SYS_ADMIN anyway
```

## Common Mistakes

1. **Using CAP_SYS_ADMIN as a catch-all**: It's too broad. Use specific capabilities whenever possible.
2. **Not dropping capabilities after use**: If a process only needs a capability during startup (e.g., bind port), drop it afterward.
3. **Confusing permitted and effective**: A capability in permitted but not effective is available but not used. Ensure the right set is configured.
4. **Forgetting the bounding set**: The bounding set limits what capabilities can ever be gained. If you don't drop capabilities from the bounding set, they can be regained.
5. **Not using PR_SET_NO_NEW_PRIVS**: Without this, a process can exec a setuid binary and gain root. Always set this in sandboxed processes.

## Summary

| Set | Purpose | Can Be Changed? |
|-----|---------|-----------------|
| Permitted | Maximum available | Yes (within bounding) |
| Effective | Currently active | Yes (subset of permitted) |
| Inheritable | Passed to children via exec | Yes |
| Bounding | Upper limit | Only decreased |
| Ambient | Non-setuid inheritance | Yes (must be in permitted+bounding) |

| Capability | Purpose |
|-----------|---------|
| CAP_NET_BIND_SERVICE | Bind ports < 1024 |
| CAP_NET_RAW | Raw sockets (ping) |
| CAP_SYS_ADMIN | Broad admin (avoid!) |
| CAP_SYS_PTRACE | Trace processes |
| CAP_SETUID/GID | Change UID/GID |
| CAP_DAC_OVERRIDE | Bypass file permissions |
| CAP_KILL | Signal any process |

## Cross-References

- [Access Control](access-control.md) — Traditional Unix permissions
- [SELinux](selinux.md) — MAC enforcement that complements capabilities
- [Containers: Namespaces](../containers/namespaces.md) — Container isolation
- [Containers: Docker](../containers/docker.md) — Docker capability management


## Cross References

- [Access Control](../os/security/access-control.md)
- [SELinux](../os/security/selinux.md)
- [Namespaces](../os/containers/namespaces.md)
