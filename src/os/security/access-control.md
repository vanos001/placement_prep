# Access Control

## Overview

Access control is the mechanism that determines **who** can access **what** resources and **how**. It's the cornerstone of OS security — every file read, network connection, and process operation goes through access control checks. Different models provide different tradeoffs between security, flexibility, and administrative overhead.

## Motivation

Without access control, any user could read any file, kill any process, or use any device. Access control provides:
- **Confidentiality**: Users can't read each other's private files
- **Integrity**: Users can't modify system files or each other's work
- **Accountability**: Access decisions are logged for auditing

## Access Control Models

```
┌──────────────────────────────────────────────────────────────┐
│              Access Control Models                            │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐ │
│  │      DAC       │  │      MAC       │  │      RBAC      │ │
│  │  (Discretionary│  │  (Mandatory    │  │  (Role-Based)  │ │
│  │   Access       │  │   Access       │  │                │ │
│  │   Control)     │  │   Control)     │  │                │ │
│  ├────────────────┤  ├────────────────┤  ├────────────────┤ │
│  │ Owner decides  │  │ System policy  │  │ Roles define   │ │
│  │ who can access │  │ controls access│  │ permissions    │ │
│  │                │  │                │  │                │ │
│  │ Unix rwx bits  │  │ SELinux,       │  │ Admin, User,   │ │
│  │ ACLs           │  │ AppArmor       │  │ Guest roles    │ │
│  ├────────────────┤  ├────────────────┤  ├────────────────┤ │
│  │ ✓ Flexible     │  │ ✓ Strong       │  │ ✓ Scalable     │ │
│  │ ✗ Weak against │  │ ✗ Complex      │  │ ✓ Manageable   │ │
│  │   root/trojan  │  │ ✗ Hard to      │  │ ✗ May be too   │ │
│  │                │  │   configure    │  │   coarse       │ │
│  └────────────────┘  └────────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## DAC (Discretionary Access Control)

The traditional Unix model — the **owner** of a resource controls who can access it.

### Unix File Permissions

```
Permission bits: rwxrwxrwx
                 │││││││││
                 ││││││││└── Other: execute
                 │││││││└─── Other: write
                 ││││││└──── Other: read
                 │││││└───── Group: execute
                 ││││└────── Group: write
                 │││└─────── Group: read
                 ││└──────── Owner: execute
                 │└───────── Owner: write
                 └────────── Owner: read

Example:
$ ls -la /etc/passwd
-rw-r--r-- 1 root root 2345 Aug  2 10:00 /etc/passwd
│└┬┘└┬┘└┬┘
│ │   │  └── Other: read
│ │   └───── Group: read
│ └───────── Owner: read+write
└─────────── Regular file
```

### Numeric Representation

```
r = 4, w = 2, x = 1

rwx = 4+2+1 = 7
rw- = 4+2+0 = 6
r-x = 4+0+1 = 5
r-- = 4+0+0 = 4

chmod 755 file  →  rwxr-xr-x
chmod 644 file  →  rw-r--r--
chmod 700 file  →  rwx------
```

### Special Permission Bits

```
┌──────────────────────────────────────────────────────────────┐
│  Special Bits                                                 │
│                                                              │
│  1. Setuid (4000):                                           │
│     - On executable: run as file owner (not caller)          │
│     - Example: /usr/bin/passwd (runs as root to modify       │
│       /etc/shadow)                                           │
│     - -rwsr-xr-x  (note the 's' in owner execute)           │
│                                                              │
│  2. Setgid (2000):                                           │
│     - On executable: run as file group                       │
│     - On directory: new files inherit directory's group      │
│     - -rwxr-sr-x  (note the 's' in group execute)           │
│                                                              │
│  3. Sticky bit (1000):                                       │
│     - On directory: only file owner can delete files         │
│     - Example: /tmp (everyone can write, nobody can          │
│       delete others' files)                                  │
│     - drwxrwxrwt  (note the 't' in other execute)           │
└──────────────────────────────────────────────────────────────┘
```

```bash
# Setuid example
ls -la /usr/bin/passwd
# -rwsr-xr-x 1 root root 68208 ... /usr/bin/passwd
# When a user runs passwd, it executes as root (setuid bit set)
# This is needed because passwd modifies /etc/shadow (owned by root)

# Setgid example
chmod g+s /shared/project/
# New files in /shared/project/ inherit the directory's group

# Sticky bit example
ls -la / | grep tmp
# drwxrwxrwt  1 root root 4096 ... /tmp
# Users can create files but can't delete others' files
```

### Access Control Lists (ACLs)

Unix permissions are limited — you can only specify one owner, one group, and others. ACLs extend this:

```bash
# View ACLs
getfacl /home/alice/document.txt
# file: home/alice/document.txt
# owner: alice
# group: users
# user::rw-
# user:bob:r--          # Bob can read
# group::r--
# group:developers:rw-  # Developers group can read/write
# mask::rw-
# other::---

# Set ACL
setfacl -m u:bob:r /home/alice/document.txt
setfacl -m g:developers:rw /home/alice/document.txt

# Default ACL (inherited by new files)
setfacl -d -m g:developers:rw /home/alice/

# Remove ACL
setfacl -x u:bob /home/alice/document.txt
```

```
ACL vs Traditional Permissions:

Traditional:
  file.txt: owner=alice, group=users, mode=640
  → alice: rw-, users: r--, others: ---
  → Can't give bob (in group "users") write without giving all users write

ACL:
  file.txt: owner=alice, group=users
  user::rw-
  user:bob:rw-      # Bob specifically gets write
  group::r--
  group:devs:rwx    # Devs group gets full access
  other::---
  → Fine-grained control per user/group
```

## MAC (Mandatory Access Control)

The **system** (not the owner) controls access based on security policy. Even root can't override MAC policy (without changing the policy itself).

```
DAC vs MAC:

DAC:
  User creates file → User decides permissions
  User can chmod 777 sensitive_file  ← Owner can give access to anyone
  ⚠ Compromised user can change permissions

MAC:
  System defines policy → Policy applies regardless of owner
  Even if user chmod 777, MAC policy may deny access
  ✓ Compromised user can't override system policy
```

### MAC in Practice (SELinux Example)

```
DAC check (first):
  Does user have Unix permission? → No? DENY
  
MAC check (second, if DAC passes):
  Does SELinux policy allow this access? → No? DENY
  
  Even root with full DAC access can be denied by MAC!
```

### Label-Based MAC (SELinux)

```
Every subject (process) and object (file) gets a security label:

Process label: system_u:system_r:httpd_t:s0
File label:    system_u:object_r:httpd_sys_content_t:s0

Policy: httpd_t can read httpd_sys_content_t
Result: Apache can read web files

If a file is labeled incorrectly:
  File label: system_u:object_r:user_home_t:s0
  Policy: httpd_t cannot read user_home_t
  Result: Apache CANNOT read the file, even if Unix permissions allow it
```

### Path-Based MAC (AppArmor)

```
AppArmor uses file paths instead of labels:

Profile for /usr/sbin/apache2:
  /var/www/** r,     # Can read web files
  /etc/apache2/** r, # Can read config
  /bin/** ix,        # Can execute binaries (inherit)
  deny /etc/shadow,  # Explicitly deny

  Simpler than SELinux but less flexible
```

## RBAC (Role-Based Access Control)

Users are assigned **roles**, and roles are assigned **permissions**.

```
┌──────────────────────────────────────────────────────┐
│              RBAC Model                               │
│                                                      │
│  Users ────► Roles ────► Permissions                 │
│                                                      │
│  alice ───── admin ───── read, write, delete, config │
│  bob ─────── editor ──── read, write                 │
│  charlie ─── viewer ──── read                        │
│                                                      │
│  Advantages:                                         │
│  • Easy to manage (assign role, not individual perms)│
│  • Principle of least privilege (role = min perms)   │
│  • Audit-friendly (who has which role?)              │
│  • Scales well (new user → assign existing role)     │
└──────────────────────────────────────────────────────┘
```

### Linux RBAC with sudo

```bash
# /etc/sudoers file defines role-like access

# User alice can run anything as root
alice ALL=(ALL:ALL) ALL

# Group developers can restart web server
%developers ALL=(root) /usr/bin/systemctl restart nginx

# User bob can run specific commands without password
bob ALL=(root) NOPASSWD: /usr/bin/apt update, /usr/bin/apt upgrade

# sudo provides role-based access to root privileges
```

## Access Control in the Linux Kernel

```
┌──────────────────────────────────────────────────────────────┐
│  Kernel Access Control Flow                                   │
│                                                              │
│  Process makes syscall (e.g., open("/etc/shadow", O_RDONLY)) │
│     │                                                        │
│     ▼                                                        │
│  1. DAC Check (VFS layer)                                    │
│     • Check UID/GID against file owner/group                 │
│     • Check permission bits or ACL                           │
│     • FAIL → return -EACCES                                  │
│     │                                                        │
│     ▼                                                        │
│  2. LSM Hook (security_inode_permission)                     │
│     • SELinux/AppArmor/Smack checks policy                   │
│     • FAIL → return -EACCES (or -EPERM)                      │
│     │                                                        │
│     ▼                                                        │
│  3. Capability Check (if needed)                             │
│     • Check if process has required capability               │
│     • FAIL → return -EPERM                                   │
│     │                                                        │
│     ▼                                                        │
│  4. Access Granted                                           │
│     • Return file descriptor to process                      │
└──────────────────────────────────────────────────────────────┘
```

## Real-World Linux Examples

### Permission Management

```bash
# Change ownership
chown alice:developers project/

# Change permissions
chmod 750 project/        # rwxr-x---
chmod u+s program         # Set setuid bit
chmod g+s directory/      # Set setgid bit
chmod +t /tmp             # Set sticky bit

# Find setuid binaries (security audit)
find / -perm -4000 -type f 2>/dev/null
# /usr/bin/passwd
# /usr/bin/sudo
# /usr/bin/su

# Find world-writable files (security risk)
find / -perm -0002 -type f 2>/dev/null

# Find files with no owner (orphaned files)
find / -nouser -o -nogroup 2>/dev/null
```

### Process Access Control

```bash
# View process UID/GID
ps -o pid,uid,gid,user,comm -p $$
#   PID   UID   GID USER     COMMAND
# 12345  1000  1000 alice    bash

# Real vs Effective UID
# Real UID: who actually ran the program
# Effective UID: used for access checks (changed by setuid)

# Example: running passwd
# Real UID: alice (1000)
# Effective UID: root (0) — because of setuid bit

# View capabilities of a process
getpcaps $$

# Run program as different user
sudo -u bob ls /home/bob/
su -c "command" bob
```

### Security Auditing

```bash
# Audit file access
sudo auditctl -w /etc/shadow -p rwa -k shadow_access

# View audit log
sudo ausearch -k shadow_access

# Check for SUID/SGID anomalies
sudo find / -type f \( -perm -4000 -o -perm -2000 \) -exec ls -la {} \;

# Monitor permission changes
sudo inotifywait -m -r /etc/ -e attrib
```

## Interview Questions

### Beginner

**Q: What is the difference between DAC and MAC?**
A: In DAC (Discretionary Access Control), the resource owner decides who can access it (e.g., Unix file permissions). In MAC (Mandatory Access Control), the system enforces a centralized policy that even the owner can't override. DAC is simpler but weaker; MAC is stronger but more complex.

**Q: What is the setuid bit and why is it needed?**
A: The setuid bit makes a program run with the file owner's privileges (typically root) instead of the caller's. This is needed for programs like `passwd` that must modify system files (`/etc/shadow`) that regular users can't access directly. The program runs as root temporarily to perform the privileged operation.

### Intermediate

**Q: Explain how ACLs extend traditional Unix permissions. What problem do they solve?**
A: Traditional Unix permissions only allow specifying access for one owner, one group, and everyone else. ACLs allow specifying access for multiple users and groups with different permission levels. For example, with ACLs you can give user Alice read-write and user Bob read-only access to a file, while denying everyone else — something impossible with traditional permissions alone.

**Q: How does the Linux kernel combine DAC and MAC checks?**
A: The kernel performs DAC checks first (UID/GID + permission bits/ACLs). If DAC denies access, the request fails immediately. If DAC allows, the LSM hook runs MAC checks (SELinux, AppArmor, etc.). If MAC denies, the request fails. Both must allow for access to be granted. This means MAC can restrict access that DAC would allow, but cannot grant access that DAC denies.

### FAANG-Level

**Q: Design an access control system for a multi-tenant cloud platform where tenants share the same kernel but must be completely isolated.**

A:

```
Requirements:
- Tenant A cannot see Tenant B's files, processes, or network
- Tenant A cannot exhaust shared resources (DoS protection)
- Root in Tenant A ≠ root on host
- Audit trail for compliance

Design: Layered Defense

Layer 1: Namespaces (isolation)
  • PID namespace: each tenant sees only its processes
  • Mount namespace: each tenant has its own filesystem view
  • Network namespace: each tenant has its own network stack
  • User namespace: tenant root maps to unprivileged host UID
  • UTS namespace: each tenant has its own hostname

Layer 2: Cgroups (resource limits)
  • CPU: limit each tenant to N cores
  • Memory: limit each tenant to M GB
  • I/O: limit disk bandwidth per tenant
  • PIDs: limit process count (prevent fork bomb)

Layer 3: MAC (mandatory policy)
  • SELinux/AppArmor policies per container
  • Even if tenant escapes container, MAC blocks access
  • Label all tenant files with tenant-specific labels

Layer 4: Seccomp (syscall filtering)
  • Restrict dangerous syscalls per container
  • Block: mount, reboot, kexec_load, ptrace
  • Allow: read, write, open, mmap, etc.

Layer 5: Capabilities (privilege splitting)
  • Drop all capabilities except needed ones
  • Container root ≠ host root
  • No CAP_SYS_ADMIN, CAP_NET_ADMIN unless explicitly needed

Layer 6: Storage isolation
  • Overlay filesystem per container
  • No shared writable mounts between tenants
  • Encrypted at rest

Layer 7: Network isolation
  • Separate network namespace per tenant
  • Network policies (Calico, Cilium) for microsegmentation
  • Encryption in transit (mTLS between services)

Layer 8: Audit and monitoring
  • Log all access denials
  • Monitor for escape attempts
  • Runtime anomaly detection (Falco)

Implementation:
  Container runtime (containerd/runc) + SELinux + cgroups v2 + seccomp
  Orchestrator (Kubernetes) enforces resource policies
  Network plugin (Cilium) enforces network policies
```

**Q: A process running as root is compromised. How would you limit the damage using modern Linux security features?**

A:

```
Pre-compromise hardening:

1. Capabilities: Don't run as full root
   • Drop all capabilities, add only needed ones
   • CAP_NET_BIND_SERVICE for port 80, not full CAP_NET_ADMIN

2. Seccomp: Restrict syscalls
   • Filter: no mount(), reboot(), kexec_load()
   • Use seccomp-bpf for fine-grained filtering
   • Example: Docker's default seccomp profile blocks 44 of 300+ syscalls

3. Namespaces: Isolate the process
   • Separate PID, mount, network, user namespaces
   • Process can't see other processes or host filesystem

4. MAC: Mandatory access control
   • SELinux policy restricts what the process can access
   • Even root is confined by the policy

5. Read-only filesystem
   • Mount root filesystem read-only
   • Use tmpfs for writable directories

6. No new privileges
   • PR_SET_NO_NEW_PRIVS: prevent setuid escalation
   • prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)

Post-compromise detection:

1. Integrity checking
   • AIDE/Tripwire: detect modified system files
   • dm-verity: read-only verified filesystem

2. Runtime monitoring
   • Audit framework: log all syscalls
   • Falco/Tracee: detect anomalous behavior

3. Automated response
   • Kill compromised container
   • Revoke credentials
   • Alert security team
```

## Common Mistakes

1. **Relying only on DAC**: Unix permissions are easily bypassed by root. Use MAC (SELinux) for defense in depth.
2. **Overly permissive setuid**: Don't make programs setuid unless absolutely necessary. Use capabilities instead.
3. **Ignoring ACLs**: When you need per-user access beyond owner/group/other, use ACLs instead of adding users to groups.
4. **Not auditing access**: Enable audit logging for sensitive files. Without logs, you can't detect breaches.
5. **Sticky bit on /tmp**: Always set the sticky bit on world-writable directories to prevent users from deleting each other's files.

## Summary

| Model | Control | Strength | Example |
|-------|---------|----------|---------|
| DAC | Owner | Moderate | Unix rwx, ACLs |
| MAC | System policy | Strong | SELinux, AppArmor |
| RBAC | Roles | Scalable | sudo, enterprise systems |

| Permission | Value | Purpose |
|------------|-------|---------|
| Setuid (4000) | Run as owner | passwd, sudo |
| Setgid (2000) | Run as group / inherit group | Directories |
| Sticky (1000) | Owner-only delete | /tmp |

## Cross-References

- [Capabilities](capabilities.md) — Fine-grained privilege splitting
- [SELinux](selinux.md) — MAC implementation in Linux
- [Containers: Namespaces](../containers/namespaces.md) — Isolation mechanisms
- [Containers: Cgroups](../containers/cgroups.md) — Resource control


## Cross References

- [Capabilities](../os/security/capabilities.md)
- [SELinux](../os/security/selinux.md)
- [Namespaces](../os/containers/namespaces.md)
- [TLS/SSL](../networks/security/tls.md)
