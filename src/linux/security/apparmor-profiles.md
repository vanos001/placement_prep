# AppArmor Profiles

AppArmor is a Linux Security Module (LSM) that confines programs based on
per-application **profiles**. Unlike SELinux's label-based approach, AppArmor
uses **path-based** rules to restrict file access, capabilities, network access,
and more. Profiles are human-readable text files that are compiled into a
kernel-loadable binary format.

> **LSM:** AppArmor  
> **Profile format:** Text-based (compiled to binary for kernel)  
> **Tools:** `aa-genprof`, `aa-logprof`, `apparmor_parser`, `aa-complain`, `aa-enforce`

---

## Profile Basics

A profile defines the security rules for one or more executables. Here is a
minimal example:

```
#include <tunables/global>

/bin/my-app {
    #include <abstractions/base>

    /etc/my-app/config r,
    /var/lib/my-app/** rw,
    /tmp/my-app-* rw,

    network inet stream,
    network inet dgram,

    capability net_bind_service,
}
```

### Profile Structure

```
┌─────────────────────────────────────────────┐
│  Profile Header                             │
│  /path/to/binary (or "profile name")        │
│  flags=(complain|enforce|audit|...)         │
├─────────────────────────────────────────────┤
│  Includes                                   │
│  #include <abstractions/base>               │
├─────────────────────────────────────────────┤
│  File Access Rules                          │
│  /path r, /path2/** rw,                     │
├─────────────────────────────────────────────┤
│  Network Rules                              │
│  network inet stream,                       │
├─────────────────────────────────────────────┤
│  Capability Rules                           │
│  capability sys_admin,                      │
├─────────────────────────────────────────────┤
│  Subprofiles (Hats)                         │
│  ^hat_name { ... }                          │
└─────────────────────────────────────────────┘
```

### Profile Attachment

Profiles are attached to executables in several ways:

```bash
# Explicit path attachment
/usr/sbin/nginx { ... }

# Named profile (attached via change_profile)
profile my-service { ... }

# Glob patterns
/usr/lib/cgi-bin/* { ... }

# Variable-based
@{INSTALL_DIR}/bin/* { ... }
```

---

## File Access Modes

| Mode | Meaning |
|------|---------|
| `r` | Read |
| `w` | Write |
| `a` | Append |
| `l` | Link |
| `k` | Lock |
| `x` | Execute |
| `ix` | Inherit profile (execute in same profile) |
| `px` | Profile execute (transition to a specific profile) |
| `Px` | Profile execute with environment scrubbing |
| `cx` | Child profile execute |
| `Cx` | Child with environment scrubbing |
| `Ux` | Unconfined execute (dangerous) |
| `deny` | Explicitly deny access |

### Examples

```
# Read-only access to config
/etc/nginx/nginx.conf r,

# Read-write to data directory
/var/lib/myapp/** rw,

# Execute a helper in its own profile
/bin/helper px,

# Execute in a child profile
/usr/lib/myapp/plugin cx,

# Deny access to a specific file
deny /etc/shadow rw,

# Owner-only access
owner /home/*/Documents/** rw,

# File creation with specific mode
/var/log/myapp.log w -> /var/log/myapp.log,
```

### Glob Patterns

| Pattern | Matches |
|---------|---------|
| `*` | Any characters except `/` |
| `**` | Any characters including `/` (recursive) |
| `?` | Any single character except `/` |
| `[abc]` | Character class |

---

## Hat (Subprofile) Mechanism

**Hats** (also called subprofiles or `change_hat`) are a powerful AppArmor
feature allowing a confined application to temporarily assume a *more* or
*differently* restricted security context. This is useful for:

- Web server CGI scripts (Apache `mod_apparmor`)
- Plugin isolation within a main application
- Privilege separation

### Defining Hats

```
/usr/sbin/apache2 {
    #include <abstractions/apache2-common>

    /var/www/** r,
    /var/www/html/** r,

    # Hat for a specific virtual host
    ^vhost_blog {
        /var/www/blog/** r,
        /var/www/blog/uploads/** rw,
        /var/www/blog/uploads/*.php deny x,
    }

    # Hat for admin interface
    ^vhost_admin {
        /var/www/admin/** r,
        # More restrictive network
        deny network,
    }
}
```

### Hat Behavior

```
┌─────────────────────────────────────────────────┐
│           Main Profile: /usr/sbin/apache2       │
│  Normal operation: full profile permissions      │
│                                                 │
│  ┌───────────────────────────────────────┐      │
│  │ Hat: ^vhost_blog                      │      │
│  │ More restrictive: only /var/www/blog  │      │
│  │ Also: adds upload write access        │      │
│  └───────────────────────────────────────┘      │
│                                                 │
│  ┌───────────────────────────────────────┐      │
│  │ Hat: ^vhost_admin                     │      │
│  │ Even more restrictive: no network     │      │
│  └───────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
```

### Using Hats in Code

```c
#include <sys/apparmor.h>

/* Transition into a hat */
aa_change_hat("vhost_blog", magic_token);

/* Do restricted work here */

/* Return to main profile (use the same token) */
aa_change_hat(NULL, magic_token);
```

The `magic_token` is a secret value used to prevent attackers from forcing a
return to the main profile. The kernel validates the token.

### Hat Nesting

```
/usr/sbin/nginx {
    ^vhost_a {
        ^plugin_x {
            # Nested: vhost_a → plugin_x
            # Permissions are the intersection of parent + hat
        }
    }
}
```

---

## Learning Mode (Complain Mode)

AppArmor has two enforcement modes:

| Mode | Behavior |
|------|----------|
| **enforce** | Denies violations; logged to audit |
| **complain** | Allows all access; violations logged for profile refinement |

### Switching Modes

```bash
# Put a profile in complain mode
aa-complain /etc/apparmor.d/usr.sbin.my-app

# Put a profile in enforce mode
aa-enforce /etc/apparmor.d/usr.sbin.my-app

# Check current mode
cat /proc/*/attr/current | grep apparmor
# or
aa-status
```

### Profile Development Workflow

```
┌──────────────────────────────────────────────────┐
│  1. Generate initial profile                      │
│     $ aa-genprof /usr/bin/my-app                  │
│                                                  │
│  2. Run application in complain mode              │
│     $ aa-complain /etc/apparmor.d/usr.bin.my-app  │
│                                                  │
│  3. Exercise all application features             │
│     (trigger all code paths)                      │
│                                                  │
│  4. Review logged accesses                        │
│     $ aa-logprof                                  │
│     (interactive: allow/deny/glob each access)    │
│                                                  │
│  5. Switch to enforce mode                        │
│     $ aa-enforce /etc/apparmor.d/usr.bin.my-app   │
│                                                  │
│  6. Monitor for denials                           │
│     $ dmesg | grep DENIED                         │
│     $ journalctl -k | grep apparmor               │
└──────────────────────────────────────────────────┘
```

### Using `aa-genprof`

```bash
# Step 1: Generate initial profile
sudo aa-genprof /usr/sbin/nginx

# This starts a scanning session:
# - Launches the application in complain mode
# - Monitors /var/log/syslog for access violations
# - Prompts you to Allow/Deny/Glob each access

# Typical session output:
# Profile:    /usr/sbin/nginx
# Path:       /etc/nginx/nginx.conf
# New Mode:   r
# [A]llow / [D]eny / [G]lob / Glob with [E]xtension / [N]ew: A
```

### Using `aa-logprof`

```bash
# Scan logs and refine existing profile
sudo aa-logprof

# Processes all logged access violations interactively
# For each violation, you choose:
#   (A)llow      - add this rule
#   (D)eny       - add explicit deny
#   (G)lob       - use glob pattern
#   (I)gnore     - skip for now
#   (N)ew profile - create a new profile for this path
```

---

## Profile Compilation and Loading

AppArmor profiles are stored as text in `/etc/apparmor.d/` and compiled to
binary for kernel loading.

### Text → Binary

```bash
# Compile and load a profile
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.my-app

# Compile only (don't load)
sudo apparmor_parser -b /etc/apparmor.d/usr.sbin.my-app

# Remove a profile
sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.my-app

# Replace existing (load new, remove old)
sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.my-app
```

### Binary Cache

```bash
# Profiles are cached at:
/var/cache/apparmor/

# Force recompilation
sudo apparmor_parser -r --force-reload /etc/apparmor.d/usr.sbin.my-app
```

### Profile Includes

```
# System abstractions (shared rule sets)
#include <abstractions/base>          # Core utilities access
#include <abstractions/nameservice>   # DNS/NIS/NSS
#include <abstractions/openssl>       # OpenSSL shared libs
#include <abstractions/apache2-common> # Apache common rules
#include <abstractions/mysql>         # MySQL client access

# Local custom includes
#include <local/usr.sbin.my-app>

# Variable definitions
@{PROC}=/proc
@{HOME}=@{HOMEDIRS}/*/ /root/
@{INSTALL_DIR}=/opt/my-app
```

### Variables

```
# Define in /etc/apparmor.d/tunables/global or local
@{my_app_dirs}=/var/lib/my-app /srv/my-app

# Use in profile
@{my_app_dirs}/** rw,
```

---

## Network Rules

```
# Allow TCP IPv4 connections
network inet stream,

# Allow UDP IPv4
network inet dgram,

# Allow TCP IPv6
network inet6 stream,

# Allow Unix domain sockets
network unix stream,
network unix dgram,

# Restrict to specific socket options
network inet stream,
setsockopt,

# Deny all networking
deny network,
```

### Network Rule Modifiers

```
# Allow binding to privileged ports
capability net_bind_service,

# Allow raw sockets (ping, etc.)
capability net_raw,
```

---

## Capability Rules

Linux capabilities can be granted or denied:

```
# Allow specific capabilities
capability sys_admin,
capability net_bind_service,
capability chown,

# Deny a capability
deny capability sys_ptrace,

# Common capability grants
capability dac_override,      # bypass file permission checks
capability setuid,            # change UID
capability setgid,            # change GID
capability sys_admin,         # broad admin (dangerous)
capability net_admin,         # network configuration
capability net_bind_service,  # bind ports < 1024
```

---

## Advanced Profile Features

### Profile Transitions

```
# Transition to another profile on exec
/usr/bin/helper -> helper_profile,

# Transition to a child profile (inherits parent's rules)
/usr/lib/myapp/plugin cx,

# Named transition
/usr/bin/helper px -> my_helper_profile,
```

### Pivot Root / Chroot

```
# Allow pivot_root
pivot_root,

# Allow chroot
chroot,
```

### Signal Rules

```
# Allow sending signals to specific profiles
signal (send) peer=/usr/sbin/my-daemon,

# Allow receiving signals
signal (receive) set=(term, kill),
```

### Ptrace Rules

```
# Allow ptrace on children
ptrace (trace) child,

# Allow reading /proc/<pid> of children
ptrace (read) peer=unconfined,
```

### DBus Rules

```
# Allow sending to system bus
dbus (send) bus=system path=/org/freedesktop/DBus interface=org.freedesktop.DBus member=Hello,

# Allow receiving from a specific service
dbus (receive) bus=system peer=(name=org.freedesktop.login1),
```

### Mount Rules (AppArmor 3.0+)

```
# Allow specific mounts
mount fstype=proc -> /proc/,
mount fstype=sysfs -> /sys/,

# Allow overlay mounts
mount fstype=overlay options=(lowerdir=/lower,upperdir=/upper,workdir=/work) -> /merged/,

# Umount
umount /mnt/tmp/,
```

---

## Profile Modes and Flags

```
# Enforce mode (default)
/usr/sbin/my-daemon {
    ...
}

# Complain mode (log but allow)
/usr/sbin/my-daemon flags=(complain) {
    ...
}

# Audit mode (log all accesses, even allowed)
/usr/sbin/my-daemon flags=(audit) {
    ...
}

# Combined
/usr/sbin/my-daemon flags=(complain,audit) {
    ...
}
```

### Mediate Deleted Files

```
# Allow access to files that have been deleted but still open
owner /var/run/my-app.sock rw,
```

---

## Integration with Containers

AppArmor is commonly used with containers:

```bash
# Docker uses AppArmor by default (docker-default profile)
docker run --security-opt apparmor=docker-default my-image

# Custom profile
docker run --security-opt apparmor=my-custom-profile my-image

# Unconfined (not recommended)
docker run --security-opt apparmor=unconfined my-image
```

### Container Profile Example

```
#include <tunables/global>

profile container-profile flags=(attach_disconnected,mediate_deleted) {
    #include <abstractions/base>

    # Deny dangerous operations
    deny mount,
    deny umount,
    deny pivot_root,

    # Allow proc/sys as read-only
    /proc/** r,
    /sys/** r,

    # Application files
    /app/** r,
    /app/data/** rw,

    # Temporary files
    /tmp/** rw,

    # Network
    network inet stream,
    network inet dgram,
    network inet6 stream,

    # Capabilities
    capability net_bind_service,
    capability setuid,
    capability setgid,
}
```

---

## Troubleshooting

### Viewing Denials

```bash
# Kernel audit log
dmesg | grep -i apparmor

# Journal
journalctl -k | grep apparmor

# Example denial:
# [12345.678] audit: type=1400 audit(1625000000.123:456):
#   apparmor="DENIED" operation="open" profile="/usr/sbin/my-app"
#   name="/etc/secret.conf" pid=1234 comm="my-app"
#   requested_mask="r" denied_mask="r"
```

### Profile Syntax Check

```bash
# Check for syntax errors
apparmor_parser -Q -T /etc/apparmor.d/usr.sbin.my-app

# Preprocess (show expanded includes)
apparmor_parser -p /etc/apparmor.d/usr.sbin.my-app
```

### Useful Commands

```bash
# Show loaded profiles
sudo aa-status

# List profiles in a specific mode
sudo aa-status | grep complain

# Reload all profiles
sudo systemctl reload apparmor

# Disable AppArmor entirely (not recommended)
sudo systemctl stop apparmor
sudo systemctl disable apparmor
```

---

## Relation to Other Security Mechanisms

- **AppArmor** is path-based; **SELinux** is label-based. Both are LSMs.
- **Seccomp** restricts system calls; AppArmor restricts file/cap/network access.
- **Namespaces** isolate views; AppArmor restricts actions within a namespace.
- **Landlock** is a newer LSM for unprivileged sandboxing.

---

## Further Reading

- [AppArmor Wiki](https://gitlab.com/apparmor/apparmor/-/wikis/home)
- [AppArmor Profile Language](https://apparmor.net/docs/latest/apparmor.html)
- [Kernel docs: AppArmor](https://www.kernel.org/doc/html/latest/admin-guide/LSM/apparmor.html)
- [Ubuntu AppArmor documentation](https://ubuntu.com/server/docs/security-apparmor)
- [SUSE AppArmor documentation](https://documentation.suse.com/sles/15-SP4/html/SLES-all/cha-apparmor.html)
- [AppArmor core policy reference](https://gitlab.com/apparmor/apparmor/-/wikis/AppArmor_Core_Policy_Reference)
- See also: [SELinux](/security/selinux), [Seccomp](/security/seccomp), [Landlock](/security/landlock), [LSM](/security/lsm)
