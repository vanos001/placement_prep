# SELinux (Security-Enhanced Linux)

## Overview

**SELinux (Security-Enhanced Linux)** is a **Mandatory Access Control (MAC)** system implemented as a Linux Security Module (LSM). It enforces security policies that control how processes interact with files, network ports, and other system resources — beyond what traditional Unix permissions allow. Even root is confined by SELinux policy.

## Motivation

Traditional Unix DAC has fundamental weaknesses:
- **Root can do anything**: A compromised root process has unrestricted access
- **Owner controls permissions**: A trojan running as a user can access all that user's files
- **No isolation between services**: Apache and SSH both run as root and can access each other's files

SELinux adds a **mandatory** layer that even root cannot override (without changing the policy).

```
Without SELinux:
  Attacker exploits Apache → gets apache user → reads /etc/shadow
  (If Apache runs as root: game over)

With SELinux:
  Attacker exploits Apache → gets apache_t domain → SELinux blocks access
  to httpd_sys_content_t only → /etc/shadow labeled shadow_t → DENIED
  Even if Apache runs as root, SELinux confines it!
```

## SELinux Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    SELinux Architecture                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Userspace                                           │    │
│  │  • Policy utilities (semanage, semodule, setsebool)  │    │
│  │  • Labeling utilities (chcon, restorecon, matchpathcon)│   │
│  │  • Troubleshooting (setroubleshoot, sealert)         │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────┴──────────────────────────────┐    │
│  │  Kernel (LSM Framework)                               │    │
│  │  ┌──────────────────────────────────────────────┐     │    │
│  │  │  SELinux Module                               │     │    │
│  │  │  ┌──────────────┐  ┌──────────────────┐      │     │    │
│  │  │  │  AVC Cache   │  │  Policy Server   │      │     │    │
│  │  │  │  (Access     │  │  (Policy         │      │     │    │
│  │  │  │   Vector     │  │   Database)      │      │     │    │
│  │  │  │   Cache)     │  │                  │      │     │    │
│  │  │  └──────────────┘  └──────────────────┘      │     │    │
│  │  └──────────────────────────────────────────────┘     │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  LSM Hooks                                            │    │
│  │  • inode_permission: file access                      │    │
│  │  • file_open: file open                               │    │
│  │  • socket_connect: network connections                │    │
│  │  • task_kill: signal delivery                         │    │
│  │  • ... (hooks at every security-relevant operation)   │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

## Core Concepts

### Security Contexts (Labels)

Every subject (process) and object (file, port, socket) has a **security context**:

```
Format: user:role:type:level

Examples:
  Process:  system_u:system_r:httpd_t:s0
  File:     system_u:object_r:httpd_sys_content_t:s0
  Port:     system_u:object_r:http_port_t:s0

Components:
  user:   SELinux user identity (mapped from Unix UID)
  role:   Role in the RBAC portion of SELinux
  type:   The type (most important for TE policy)
  level:  MLS/MCS sensitivity level (s0, s0-s0:c0.c1023)
```

```bash
# View security context of files
ls -Z /var/www/html/
# system_u:object_r:httpd_sys_content_t:s0 index.html

# View security context of processes
ps auxZ | grep httpd
# system_u:system_r:httpd_t:s0    apache  1234  ...  /usr/sbin/httpd

# View security context of current process
id -Z
# unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023
```

### Type Enforcement (TE)

The core of SELinux policy — **types** define what a process (domain) can access:

```
Policy rules:
  allow httpd_t httpd_sys_content_t:file { read open getattr };
  allow httpd_t httpd_sys_content_t:dir { search };

Meaning:
  Processes in domain httpd_t can read files of type httpd_sys_content_t

If Apache tries to read /etc/shadow (type shadow_t):
  allow httpd_t shadow_t:file { read };
  ← No such rule! → DENIED
```

```
┌──────────────────────────────────────────────────────────────┐
│  Type Enforcement Example                                     │
│                                                              │
│  Process (Domain)     Object (Type)         Allowed          │
│  ─────────────────    ─────────────────     ───────────      │
│  httpd_t             httpd_sys_content_t   read, open        │
│  httpd_t             httpd_log_t           read, write       │
│  httpd_t             http_port_t           name_bind         │
│  httpd_t             shadow_t              (nothing!)        │
│                                                              │
│  sshd_t              sshd_var_run_t        read, write       │
│  sshd_t              ptmx_t                read, write       │
│                                                              │
│  httpd_t → shadow_t = DENIED (no allow rule)                │
│  sshd_t → httpd_sys_content_t = DENIED                      │
└──────────────────────────────────────────────────────────────┘
```

### SELinux Modes

```bash
# View current mode
getenforce
# Enforcing

# View detailed status
sestatus
# SELinux status:                 enabled
# SELinuxfs mount:                /sys/fs/selinux
# Current mode:                   enforcing
# Mode from config file:          enforcing
# Policy version:                 33
# Policy denial state:            enforcing

# Change mode (temporary, resets on reboot)
sudo setenforce 0  # Permissive (log but don't deny)
sudo setenforce 1  # Enforcing (log and deny)

# Change permanently (edit config)
sudo vi /etc/selinux/config
# SELINUX=enforcing    ← enforcing, permissive, or disabled
# SELINUXTYPE=targeted
```

| Mode | Description | Use Case |
|------|-------------|----------|
| **Enforcing** | Policy enforced, denials logged | Production |
| **Permissive** | Denials logged but not enforced | Testing, debugging |
| **Disabled** | SELinux completely off | Not recommended |

### SELinux Policy Types

```
┌──────────────────────────────────────────────────────────────┐
│  Policy Types                                                 │
│                                                              │
│  1. Targeted (default, recommended)                          │
│     • Confines specific services (httpd, sshd, named, etc.)  │
│     • Unconfined domains for user processes                  │
│     • Most common, good balance of security/compatibility    │
│                                                              │
│  2. MLS (Multi-Level Security)                               │
│     • Full Bell-LaPadula model                               │
│     • Used in classified environments                        │
│     • Very restrictive                                        │
│                                                              │
│  3. Minimum                                                  │
│     • Minimal policy, only core system                       │
│     • For containers/embedded                                │
│                                                              │
│  4. Custom                                                   │
│     • Write your own policy modules                          │
│     • Reference policy as base                               │
└──────────────────────────────────────────────────────────────┘
```

## SELinux Booleans

Booleans toggle policy features without rewriting rules:

```bash
# List all booleans
getsebool -a
# httpd_can_network_connect --> off
# httpd_can_send_mail --> off
# httpd_enable_homedirs --> off
# ssh_sysadm_login --> off

# Set a boolean (temporary)
sudo setsebool httpd_can_network_connect on

# Set permanently (survives reboot)
sudo setsebool -P httpd_can_network_connect on

# Common booleans for web servers:
# httpd_can_network_connect: allow httpd to make outbound connections
# httpd_can_network_connect_db: allow httpd to connect to databases
# httpd_enable_homedirs: allow httpd to serve ~/public_html
# httpd_use_nfs: allow httpd to access NFS-mounted files
```

## File Context Management

```bash
# View default file contexts
semanage fcontext -l | grep /var/www
# /var/www(/.*)?     system_u:object_r:httpd_sys_content_t:s0

# Set file context (persistent)
sudo semanage fcontext -a -t httpd_sys_content_t "/srv/web(/.*)?"

# Apply contexts
sudo restorecon -Rv /srv/web

# Temporary context change (resets on restorecon)
sudo chcon -t httpd_sys_content_t /tmp/test.html

# View file context differences
sudo restorecon -nv /var/www/html/
```

```
Context Assignment Flow:

1. File created → kernel assigns context from parent directory's default
2. Policy may override based on file type and creating process
3. restorecon resets to policy-defined context
4. semanage fcontext defines persistent defaults

Example:
  /var/www/html/index.html gets httpd_sys_content_t
  because /var/www/html has default context httpd_sys_content_t

  If you move a file from /tmp to /var/www/html:
  → File keeps /tmp context (tmp_t) until restorecon runs!
  → Always use cp instead of mv, or run restorecon after mv
```

## SELinux Troubleshooting

```bash
# View SELinux denials
sudo ausearch -m avc -ts recent
# type=AVC msg=audit(1234567890.123:456): avc: denied { read } for
# pid=1234 comm="httpd" name="secret.txt" dev="sda1" ino=789
# scontext=system_u:system_r:httpd_t:s0
# tcontext=system_u:object_r:user_home_t:s0
# tclass=file

# Get human-readable solutions
sudo sealert -a /var/log/audit/audit.log
# ***** Plugin catchall_boolean (78.3 confidence) suggests *****
# sudo setsebool -P httpd_read_user_content on

# Or use setroubleshoot
sudo cat /var/log/messages | grep setroubleshoot

# Quick fix: generate and apply policy
sudo audit2allow -M mypolicy < /var/log/audit/audit.log
sudo semodule -i mypolicy.pp

# ⚠ Don't blindly allow everything! Fix the root cause:
# - Wrong file context? → restorecon
# - Legitimate access? → setsebool
# - Genuinely blocked? → leave denied
```

## Real-World Examples

### Securing Apache with SELinux

```bash
# 1. Check current contexts
ls -Z /var/www/html/
ps auxZ | grep httpd

# 2. Ensure correct file contexts
sudo restorecon -Rv /var/www/html/

# 3. Allow httpd to connect to database
sudo setsebool -P httpd_can_network_connect_db on

# 4. Serve files from non-standard location
sudo semanage fcontext -a -t httpd_sys_content_t "/data/web(/.*)?"
sudo restorecon -Rv /data/web/

# 5. Allow httpd to listen on non-standard port
sudo semanage port -a -t http_port_t -p tcp 8080

# 6. Debug denials
sudo ausearch -m avc -c httpd
```

### SELinux in Containers

```bash
# Containers get unique MCS labels for isolation
# Container 1: s0:c1,c2
# Container 2: s0:c3,c4
# → Container 1 can't access Container 2's files (MCS separation)

# Docker uses SELinux labels
docker run --security-opt label=type:my_container_t myimage

# Disable SELinux for a container (not recommended)
docker run --security-opt label=disable myimage
```

### SELinux with systemd Services

```ini
# /etc/systemd/system/myapp.service
[Service]
Type=simple
ExecStart=/usr/bin/myapp
User=myapp
# SELinux context for the service
SELinuxContext=system_u:system_r:myapp_t:s0
```

## SELinux Policy Writing (Simplified)

```te
# myapp.te - SELinux policy for myapp

# Define the domain
type myapp_t;
type myapp_exec_t;
init_daemon_domain(myapp_t, myapp_exec_t)

# Allow reading web content
allow myapp_t httpd_sys_content_t:file { read open getattr };
allow myapp_t httpd_sys_content_t:dir { search getattr };

# Allow binding to port 8080
allow myapp_t myapp_port_t:tcp_socket { name_bind };

# Allow network connections
allow myapp_t myapp_port_t:tcp_socket { name_connect };

# Define port type
type myapp_port_t;
portcon tcp 8080 system_u:object_r:myapp_port_t:s0
```

```bash
# Compile and install policy module
checkmodule -M -m -o myapp.mod myapp.te
semodule_package -o myapp.pp -m myapp.mod
sudo semodule -i myapp.pp

# Set file contexts
sudo semanage fcontext -a -t myapp_exec_t "/usr/bin/myapp"
sudo restorecon -v /usr/bin/myapp
```

## Interview Questions

### Beginner

**Q: What is SELinux and why is it needed?**
A: SELinux is a Mandatory Access Control system for Linux that enforces security policies beyond traditional Unix permissions. It's needed because traditional DAC has weaknesses — root can do anything, and a compromised service running as root can access everything. SELinux confines even root processes to only the resources specified in the policy.

**Q: What are the three SELinux modes?**
A:
- **Enforcing**: Policy is enforced and violations are denied and logged. This is the production mode.
- **Permissive**: Violations are logged but not enforced. Used for testing and debugging new policies.
- **Disabled**: SELinux is completely off. Not recommended as you lose all MAC protection.

### Intermediate

**Q: Explain type enforcement in SELinux.**
A: Type enforcement is the core of SELinux policy. Every process gets a **domain** (type) and every object gets a **type** label. Policy rules define which domains can access which types with which permissions. For example, `allow httpd_t httpd_sys_content_t:file { read }` lets Apache read web files. If no rule exists for a particular access, it's denied by default.

**Q: How do SELinux booleans work?**
A: Booleans are on/off switches that toggle parts of the SELinux policy without rewriting rules. For example, `httpd_can_network_connect` controls whether Apache can make outbound network connections. They allow administrators to adjust policy behavior without deep SELinux knowledge. Use `setsebool -P` to make changes persistent across reboots.

### FAANG-Level

**Q: Design an SELinux policy for a microservice that serves an API, reads from a database socket, writes logs, and sends metrics to a monitoring system. Show the types, rules, and how you'd confine it.**

A:

```
Design: Confined SELinux Domain for API Microservice

1. Domain Definition:
   type api_service_t;           # Process domain
   type api_service_exec_t;      # Executable type
   type api_service_log_t;       # Log files
   type api_service_conf_t;      # Configuration files
   type api_service_data_t;      # Application data
   type api_service_port_t;      # Network port (8443)
   type api_db_socket_t;         # Database Unix socket
   type monitoring_port_t;       # Metrics port (9090)

2. Domain Transition:
   # When init starts the service, transition to api_service_t
   init_daemon_domain(api_service_t, api_service_exec_t)

3. File Access Rules:
   # Read config
   allow api_service_t api_service_conf_t:file { read open getattr };
   allow api_service_t api_service_conf_t:dir { search getattr };

   # Read/write data
   allow api_service_t api_service_data_t:file { read write open create };
   allow api_service_t api_service_data_t:dir { search write add_name };

   # Write logs
   allow api_service_t api_service_log_t:file { read write append create };
   allow api_service_t api_service_log_t:dir { search write add_name };

4. Network Rules:
   # Bind to API port
   allow api_service_t api_service_port_t:tcp_socket { name_bind };
   portcon tcp 8443 system_u:object_r:api_service_port_t:s0

   # Connect to database socket
   allow api_service_t api_db_socket_t:sock_file { write connectto };

   # Send metrics to monitoring
   allow api_service_t monitoring_port_t:tcp_socket { name_connect };

5. Restrictive Rules (no access to):
   # No access to other service files
   # No access to /etc/shadow, /etc/passwd (beyond what's needed)
   # No kernel module loading
   # No reboot/shutdown
   # No ptrace other processes

6. Booleans for flexibility:
   bool api_service_can_send_mail false;
   bool api_service_can_use_nfs false;
   bool api_service_debug_mode false;

7. Neverallow rules (enforce at compile time):
   neverallow api_service_t shadow_t:file { read write };
   neverallow api_service_t kernel_t:system { module_load reboot };

8. Testing:
   - Run in permissive mode first
   - Use audit2allow to find legitimate denials
   - Fix file contexts with restorecon
   - Switch to enforcing

Result:
  ✓ API service can bind to 8443 and serve requests
  ✓ Can read config, write logs, connect to DB socket
  ✓ Can send metrics to monitoring
  ✗ Cannot read /etc/shadow, load modules, access other services
  ✗ Cannot ptrace, reboot, or modify system files
  ✗ Even if compromised, attacker is confined to api_service_t
```

**Q: A colleague argues that SELinux is unnecessary in a containerized environment because containers already provide isolation. How would you respond?**

A:

```
Containers provide isolation through namespaces and cgroups, but these
are NOT sufficient security boundaries:

1. Namespace escapes are real:
   - CVE-2022-0185: heap overflow in legacy parsing → container escape
   - CVE-2022-0492: cgroup release_agent escape
   - Namespaces were designed for isolation, not security

2. Shared kernel:
   - Containers share the host kernel
   - A kernel exploit in the container = host compromise
   - SELinux confines even after namespace escape

3. Defense in depth:
   - Container escape → still confined by SELinux
   - SELinux provides independent security layer
   - Each layer catches what others miss

4. Real-world evidence:
   - Red Hat, Fedora, RHEL all use SELinux with containers
   - Docker/Podman integrate with SELinux by default
   - Kubernetes supports SELinux security contexts

5. What SELinux adds:
   - MCS labels: each container gets unique label (c1,c2 vs c3,c4)
   - Even if container escapes namespace, can't access other containers
   - Confines container processes to specific file types
   - Prevents container from accessing host files

Practical:
  # Container without SELinux:
  Attacker escapes namespace → full host access

  # Container with SELinux:
  Attacker escapes namespace → confined by SELinux policy
  → Can only access container_file_t labeled files
  → Cannot read host_shadow_t, host_etc_t, etc.

Bottom line: Containers + SELinux = defense in depth
```

## Common Mistakes

1. **Disabling SELinux instead of fixing denials**: This removes all MAC protection. Use permissive mode for debugging, then fix the actual issues.
2. **Using `chcon` for permanent changes**: `chcon` changes are lost on `restorecon`. Use `semanage fcontext` for persistent changes.
3. **Blindly running `audit2allow`**: This allows whatever was denied, which may include attacks. Always review what you're allowing.
4. **Not labeling non-standard paths**: Files created in non-standard locations won't have correct contexts. Use `semanage fcontext` + `restorecon`.
5. **Confusing SELinux user with Unix user**: SELinux users are separate from Unix UIDs. One Unix user can map to multiple SELinux users.

## Summary

| Concept | Description |
|---------|-------------|
| Type Enforcement | Domain-type access rules (core of policy) |
| Security Context | Label on every subject and object |
| Enforcing | Policy active, denials enforced |
| Permissive | Denials logged only |
| Booleans | Toggle policy features |
| File Context | Label assigned to files/directories |
| AVC Cache | Caches access decisions for performance |

## Cross-References

- [Access Control](access-control.md) — DAC that SELinux extends
- [Capabilities](capabilities.md) — Complementary privilege mechanism
- [Containers: Docker](../containers/docker.md) — SELinux in containers
- [Containers: Namespaces](../containers/namespaces.md) — Container isolation


## Cross References

- [Access Control](access-control.md)
- [Capabilities](capabilities.md)
- [Namespaces](../containers/namespaces.md)
- [Firewalls](../../networks/security/firewalls.md)
