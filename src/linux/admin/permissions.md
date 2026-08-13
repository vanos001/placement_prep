# File Permissions and Security

Linux file permissions are the foundation of system security. Every file and directory has an owner, a group, and a set of permissions that control who can read, write, and execute it. This chapter covers traditional permissions, ACLs, umask, special permissions, and Linux capabilities.

## Traditional Unix Permissions

### Permission Model

```
┌─────────────────────────────────────────────────────┐
│  Unix Permission Model                               │
├─────────────────────────────────────────────────────┤
│                                                     │
│  File: -rwxr-xr-- 1 alice developers 4096 file.txt  │
│        │││││││││                                      │
│        │││││││└── Other: read                        │
│        ││││││└─── Other: (no write)                  │
│        │││││└──── Other: (no execute)                │
│        ││││└───── Group: read                        │
│        │││└────── Group: execute                     │
│        ││└─────── Group: (no write)                  │
│        │└──────── Owner: read                        │
│        └───────── Owner: execute                     │
│                                                     │
│  Type: - (file), d (directory), l (symlink)         │
│        c (char device), b (block device)            │
│        p (named pipe/FIFO), s (socket)              │
│                                                     │
│  Owner: alice       (user who owns the file)        │
│  Group: developers  (group that owns the file)      │
│  Size:  4096 bytes                                  │
└─────────────────────────────────────────────────────┘
```

### Permission Bits

| Bit | Octal | File Meaning | Directory Meaning |
|-----|-------|--------------|-------------------|
| `r` | 4 | Read file contents | List directory contents |
| `w` | 2 | Modify file contents | Create/delete files in directory |
| `x` | 1 | Execute file as program | Enter directory (cd) |
| `-` | 0 | No permission | No permission |

### Viewing Permissions

```bash
# Long listing
ls -la
# -rwxr-xr-x 1 root root  4096 Jan  1 00:00 script.sh
# drwxr-xr-x 2 root root  4096 Jan  1 00:00 directory

# Numeric (octal) representation
stat -c '%a %n' *
# 755 script.sh
# 755 directory

# Detailed stat
stat file.txt
#   File: file.txt
#   Size: 1234       Blocks: 8          IO Block: 4096   regular file
# Access: (0644/-rw-r--r--)  Uid: ( 1000/  alice)   Gid: ( 1000/ developers)

# List with numeric UIDs (useful for NFS)
ls -lan
```

## `chmod` — Change File Permissions

### Symbolic Mode

```bash
# Who: u (user/owner), g (group), o (other), a (all)
# Operation: + (add), - (remove), = (set exactly)
# Permission: r (read), w (write), x (execute)

# Add execute for owner
chmod u+x file.sh

# Remove write for group and others
chmod go-w file.txt

# Set exact permissions for all
chmod a=r file.txt           # read-only for everyone

# Multiple operations
chmod u+rwx,g+rx,o+r file.sh

# Remove all permissions for others
chmod o= file.txt

# Add execute for all
chmod +x file.sh             # Same as a+x
```

### Numeric (Octal) Mode

```bash
# Three or four digits: [special]owner group other
# Each digit = sum of: r=4, w=2, x=1

chmod 755 file.sh    # rwxr-xr-x
chmod 644 file.txt   # rw-r--r--
chmod 600 secret.txt # rw-------
chmod 700 private/   # rwx------ (directory)
chmod 777 public/    # rwxrwxrwx (dangerous!)
chmod 000 hidden/    # --------- (no access)

# Four-digit mode (with special permissions)
chmod 4755 suid.sh   # rwsr-xr-x (SUID)
chmod 2755 shared/   # rwxr-sr-x (SGID directory)
chmod 1777 /tmp      # rwxrwxrwt (sticky bit)
```

### Recursive Permissions

```bash
# Recursive (use with caution)
chmod -R 755 directory/

# Different permissions for files and directories
find directory/ -type f -exec chmod 644 {} +
find directory/ -type d -exec chmod 755 {} +

# Using xargs (faster for many files)
find directory/ -type f -print0 | xargs -0 chmod 644
find directory/ -type d -print0 | xargs -0 chmod 755

# Only affect specific depth
find directory/ -maxdepth 1 -type f -exec chmod 644 {} +
```

### Reference Mode

```bash
# Copy permissions from another file
chmod --reference=source.txt target.txt

# Set permissions based on existing file
chmod $(stat -c '%a' source.txt) target.txt
```

## `chown` — Change Ownership

```bash
# Change owner
chown alice file.txt

# Change owner and group
chown alice:developers file.txt

# Change only group
chown :developers file.txt
chgrp developers file.txt    # Alternative command

# Recursive
chown -R alice:developers directory/

# Reference
chown --reference=source.txt target.txt

# Preserve root ownership on symlinks
chown -h alice symlink

# Numeric UID/GID
chown 1000:1000 file.txt

# Verbose
chown -v alice:developers file.txt
# changed ownership of 'file.txt' to alice:developers
```

## `umask` — Default Permission Mask

The umask determines default permissions for newly created files and directories.

### How umask Works

```
┌─────────────────────────────────────────────────────┐
│  umask Calculation                                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Default base permissions:                           │
│  Files:      666 (rw-rw-rw-)                        │
│  Directories: 777 (rwxrwxrwx)                       │
│                                                     │
│  umask 022:                                          │
│  Files:      666 - 022 = 644 (rw-r--r--)           │
│  Directories: 777 - 022 = 755 (rwxr-xr-x)          │
│                                                     │
│  umask 027:                                          │
│  Files:      666 - 027 = 640 (rw-r-----)           │
│  Directories: 777 - 027 = 750 (rwxr-x---)          │
│                                                     │
│  umask 077:                                          │
│  Files:      666 - 077 = 600 (rw-------)           │
│  Directories: 777 - 077 = 700 (rwx------)          │
└─────────────────────────────────────────────────────┘
```

### Setting umask

```bash
# View current umask
umask
# 0022

umask -p
# umask 0022

# Symbolic view
umask -S
# u=rwx,g=rx,o=rx

# Set umask (temporary, for current session)
umask 027

# Set in shell profile
echo 'umask 027' >> ~/.bashrc

# Set system-wide
# /etc/profile or /etc/login.defs
# umask 027
# Or for stricter:
# umask 077
```

### umask Best Practices

```bash
# Default (permissive): umask 022
# Good for: shared systems, development
umask 022

# Moderate: umask 027
# Good for: servers, multi-user systems
umask 027

# Strict: umask 077
# Good for: single-user, high-security
umask 077

# Per-user umask in /etc/login.defs
UMASK 027

# Per-group umask via PAM
# /etc/pam.d/common-session
session optional pam_umask.so umask=027
```

## Special Permissions

### SUID (Set User ID) — `4000` or `u+s`

When a file with SUID is executed, it runs with the permissions of the file **owner**, not the executing user.

```bash
# Set SUID
chmod u+s program
chmod 4755 program    # rwsr-xr-x

# Example: passwd command
ls -la /usr/bin/passwd
# -rwsr-xr-x 1 root root 68208 Jan 1 00:00 /usr/bin/passwd
# ↑ SUID bit: runs as root regardless of who executes it

# Find SUID files (security audit)
find / -perm -4000 -type f 2>/dev/null
find / -perm -u=s -type f 2>/dev/null

# Security implications
# SUID binaries can be dangerous if:
# - Owned by root and vulnerable to exploits
# - Have writable paths in $PATH
# - Are in world-writable directories
```

### SGID (Set Group ID) — `2000` or `g+s`

On files: runs with the group of the file.
On directories: new files inherit the directory's group.

```bash
# Set SGID on file
chmod g+s program
chmod 2755 program    # rwxr-sr-x

# Set SGID on directory (common and useful)
chmod g+s /shared/project/
# New files in this directory will inherit the 'project' group
# regardless of the creating user's primary group

# Find SGID files
find / -perm -2000 -type f 2>/dev/null

# Find SGID directories
find / -perm -2000 -type d 2>/dev/null

# Example: shared project directory
mkdir /srv/project
chgrp developers /srv/project
chmod 2775 /srv/project
# Now all new files in /srv/project will be owned by 'developers' group
```

### Sticky Bit — `1000` or `+t`

On directories: only the file owner, directory owner, or root can delete/rename files.

```bash
# Set sticky bit
chmod +t directory/
chmod 1777 directory/    # rwxrwxrwt

# Classic example: /tmp
ls -ld /tmp
# drwxrwxrwt 15 root root 4096 Jan 1 00:00 /tmp
# ↑ Sticky bit: users can create files but can't delete others' files

# Without sticky bit on /tmp:
# User A creates /tmp/file
# User B could delete /tmp/file (if directory is writable)

# With sticky bit:
# Only User A (file owner), /tmp owner (root), or root can delete

# Find sticky bit directories
find / -perm -1000 -type d 2>/dev/null
```

### Special Permissions Summary

```
┌─────────────────────────────────────────────────────┐
│  Special Permissions Summary                         │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Permission │ Octal │ File Effect    │ Dir Effect   │
│  ───────────┼───────┼────────────────┼────────────  │
│  SUID       │  4000 │ Run as owner   │ No effect    │
│  SGID       │  2000 │ Run as group   │ Inherit group│
│  Sticky     │  1000 │ No effect      │ Owner-only   │
│             │       │                │ delete       │
│                                                     │
│  Display:                                            │
│  SUID on  executable: -rws------                    │
│  SUID off executable: -rwS------ (capital S = error)│
│  SGID on  executable: ---rws---                     │
│  SGID off executable: ---rwS--- (capital S = error) │
│  Sticky on  directory: ------rwt                    │
│  Sticky off directory: ------rwT (capital T = error)│
└─────────────────────────────────────────────────────┘
```

## Access Control Lists (ACLs)

ACLs provide fine-grained permission control beyond the traditional owner/group/other model.

### When to Use ACLs

```bash
# Scenario: Give user 'bob' read access to a file owned by 'alice'
# Traditional: Only owner, group, and other — no per-user control
# ACL: Yes!

# Scenario: Different permissions for different users in same group
# Traditional: All group members get same permissions
# ACL: Yes!
```

### `getfacl` — View ACLs

```bash
# View ACL
getfacl file.txt
# file: file.txt
# owner: alice
# group: developers
# user::rw-
# user:bob:r--
# group::r--
# mask::r--
# other::---

# View default ACL (for directories)
getfacl directory/
# # file: directory/
# owner: alice
# group: developers
# user::rwx
# group::r-x
# other::---
# default:user::rwx
# default:group::r-x
# default:other::---

# View ACL of specific user
getfacl -a file.txt    # Access ACL only
getfacl -d directory/  # Default ACL only
```

### `setfacl` — Set ACLs

```bash
# Set user ACL
setfacl -m u:bob:rw file.txt

# Set group ACL
setfacl -m g:developers:r file.txt

# Set other ACL
setfacl -m o::r file.txt

# Set mask (effective permissions limit)
setfacl -m m::rx file.txt

# Multiple ACLs at once
setfacl -m u:bob:rw,g:developers:r,o::--- file.txt

# Remove ACL for specific user
setfacl -x u:bob file.txt

# Remove all ACLs
setfacl -b file.txt

# Recursive ACLs
setfacl -R -m u:bob:rw directory/

# Default ACLs (inherited by new files in directory)
setfacl -m d:u:bob:rw directory/
setfacl -m d:g:developers:r directory/

# Set ACL from file
setfacl -M acl_rules.txt file.txt

# Copy ACL from another file
getfacl source.txt | setfacl --set-file=- target.txt

# Backup and restore ACLs
getfacl -R directory/ > acl_backup.txt
setfacl --restore=acl_backup.txt

# ACL mask calculation
# The mask is the union of group, named user, and named group ACLs
# Effective permissions = ACL permissions AND mask
```

### ACL Examples

```bash
# Example 1: Share directory with specific users
mkdir /srv/project
chown root:developers /srv/project
setfacl -m u:alice:rwx /srv/project
setfacl -m u:bob:rx /srv/project
setfacl -m d:u:alice:rwx /srv/project    # Default for new files
setfacl -m d:u:bob:rx /srv/project

# Example 2: Web server access
setfacl -m u:www-data:rx /srv/www/uploads/
setfacl -m d:u:www-data:rx /srv/www/uploads/

# Example 3: Read-only access for auditor
setfacl -R -m u:auditor:r /var/log/
setfacl -R -m d:u:auditor:r /var/log/

# Example 4: Team access with different levels
setfacl -m g:senior-dev:rwx /srv/app/
setfacl -m g:junior-dev:rx /srv/app/
setfacl -m g:intern:r /srv/app/

# Example 5: ACL on executable
setfacl -m u:deploy:rx /usr/local/bin/deploy.sh

# Verify effective permissions
getfacl -c file.txt
# user::rw-
# user:bob:rwx                  #effective:r-x  ← mask limits to r-x
# group::r--
# mask::r-x
# other::---
```

### ACL Behavior with `cp` and `mv`

```bash
# cp preserves ACLs with -p or --preserve=all
cp -p file.txt copy.txt          # ACLs preserved
cp --preserve=all file.txt copy.txt

# mv preserves ACLs (same filesystem)
mv file.txt newname.txt          # ACLs preserved

# cp without -p does NOT preserve ACLs
cp file.txt copy.txt             # ACLs lost (default umask applies)

# Archive with ACLs
tar --acls -czf backup.tar.gz directory/
tar --acls -xzf backup.tar.gz
```

## Linux Capabilities

Capabilities break the all-or-nothing model of root privileges into fine-grained units.

### Capability Model

```
┌─────────────────────────────────────────────────────┐
│  Linux Capabilities                                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Traditional:                                        │
│  root = ALL privileges                               │
│  regular user = NO privileges                        │
│                                                     │
│  Capabilities:                                       │
│  CAP_NET_BIND_SERVICE → bind to ports < 1024        │
│  CAP_NET_RAW          → use raw sockets              │
│  CAP_SYS_ADMIN        → mount, swapon, etc.          │
│  CAP_DAC_OVERRIDE     → bypass file permission checks│
│  CAP_CHOWN            → change file ownership        │
│  CAP_KILL             → send signals to any process  │
│  CAP_SETUID           → set UID                      │
│  CAP_SETGID           → set GID                      │
│  CAP_SYS_PTRACE       → trace processes              │
│  CAP_SYS_TIME         → set system clock             │
│                                                     │
│  File capabilities (on executables):                 │
│  Permitted → capabilities the process may have       │
│  Effective → capabilities currently active           │
│  Inheritable → capabilities passed to child          │
└─────────────────────────────────────────────────────┘
```

### Common Capabilities

| Capability | Purpose |
|-----------|---------|
| `CAP_NET_BIND_SERVICE` | Bind to ports below 1024 |
| `CAP_NET_RAW` | Use raw sockets, packet sockets |
| `CAP_NET_ADMIN` | Network configuration |
| `CAP_SYS_ADMIN` | Mount, swapon,quotactl, etc. |
| `CAP_SYS_PTRACE` | Trace/debug processes |
| `CAP_SYS_TIME` | Set system clock |
| `CAP_SYS_RESOURCE` | Override resource limits |
| `CAP_DAC_OVERRIDE` | Bypass file read/write/execute checks |
| `CAP_DAC_READ_SEARCH` | Bypass file read checks and directory read/execute |
| `CAP_CHOWN` | Change file ownership |
| `CAP_FOWNER` | Bypass permission checks on operations that check file UID |
| `CAP_SETUID` | Set UID |
| `CAP_SETGID` | Set GID |
| `CAP_KILL` | Send signals to processes |
| `CAP_SETPCAP` | Modify process capabilities |
| `CAP_AUDIT_WRITE` | Write to audit log |
| `CAP_AUDIT_CONTROL` | Configure audit system |
| `CAP_MKNOD` | Create device special files |
| `CAP_LINUX_IMMUTABLE` | Set/clear immutable flag |
| `CAP_IPC_LOCK` | Lock memory |
| `CAP_SYS_MODULE` | Load/unload kernel modules |
| `CAP_SYS_RAWIO` | Raw I/O port access |
| `CAP_SYS_BOOT` | Reboot system |

### Managing Capabilities with `setcap`/`getcap`

```bash
# View file capabilities
getcap /usr/bin/ping
# /usr/bin/ping = cap_net_raw+ep

# Set capabilities on file
sudo setcap cap_net_bind_service=ep /usr/bin/myserver
# e = effective (active immediately)
# p = permitted (can be raised)
# i = inheritable (passed to children)

# Multiple capabilities
sudo setcap cap_net_bind_service,cap_net_raw=ep /usr/bin/myserver

# Remove capabilities
sudo setcap -r /usr/bin/myserver

# Find all files with capabilities
getcap -r / 2>/dev/null

# Set capability on script (requires careful handling)
# Scripts with shebangs need special care
# The capability applies to the interpreter, not the script

# Capability format:
# capability_type=flags
# flags: e (effective), p (permitted), i (inheritable)
```

### Capability Examples

```bash
# Allow web server to bind to port 80 without root
sudo setcap cap_net_bind_service=ep /usr/sbin/nginx

# Allow ping without root
sudo setcap cap_net_raw=ep /usr/bin/ping

# Allow nmap to use raw sockets
sudo setcap cap_net_raw=ep /usr/bin/nmap

# Allow program to change system time
sudo setcap cap_sys_time=ep /usr/bin/ntpdate

# Allow program to trace processes
sudo setcap cap_sys_ptrace=ep /usr/bin/strace

# Capability-aware code (C)
# cap_set_proc(cap_from_text("cap_net_bind_service+ep"))

# Docker capabilities
docker run --cap-add NET_BIND_SERVICE --cap-drop ALL myimage
```

### Capabilities in systemd Services

```ini
# /etc/systemd/system/myapp.service
[Service]
# Grant specific capabilities
CapabilityBoundingSet=CAP_NET_BIND_SERVICE CAP_NET_RAW
AmbientCapabilities=CAP_NET_BIND_SERVICE CAP_NET_RAW
NoNewPrivileges=true

# Drop all capabilities except specified
# CapabilityBoundingSet= defines what the process CAN have
# AmbientCapabilities= defines what the process STARTS with
# NoNewPrivileges=true prevents gaining new capabilities
```

### Capability Sets

```bash
# View process capabilities
cat /proc/self/status | grep Cap
# CapInh: 0000000000000000
# CapPrm: 0000000000000000
# CapEff: 0000000000000000
# CapBnd: 0000003fffffffff
# CapAmb: 0000000000000000

# Decode capability sets
capsh --decode=0000000000000000
capsh --decode=0000003fffffffff

# Capability sets:
# CapInh (Inheritable): inherited across execve
# CapPrm (Permitted): limiting superset for effective
# CapEff (Effective): currently active capabilities
# CapBnd (Bounding): limits what can be in permitted
# CapAmb (Ambient): added to effective/permitted on execve

# Run process with limited capabilities
capsh --caps="cap_net_bind_service+eip" -- -c "/usr/bin/myserver"
```

## File Attributes (`chattr`/`lsattr`)

Extended file attributes provide additional control beyond permissions.

```bash
# View attributes
lsattr file.txt
# ----i---------e-- file.txt

# Set immutable (can't modify, delete, or rename)
sudo chattr +i file.txt
sudo chattr -i file.txt    # Remove

# Set append-only (can only append, not overwrite)
sudo chattr +a /var/log/syslog
sudo chattr -a /var/log/syslog

# Common attributes
sudo chattr +i file.txt     # Immutable
sudo chattr +a file.txt     # Append-only
sudo chattr +c file.txt     # Compressed
sudo chattr +d file.txt     # No dump
sudo chattr +e file.txt     # Extent format (always set by ext4)
sudo chattr +j file.txt     # Data journaling
sudo chattr +s file.txt     # Secure deletion (zero on delete)
sudo chattr +u file.txt     # Undeletable (contents saved)
sudo chattr +A file.txt     # No atime updates

# Recursive
sudo chattr -R +i directory/

# Use case: Protect critical files
sudo chattr +i /etc/passwd /etc/shadow
# Prevents even root from modifying (must remove +i first)

# Use case: Append-only logs
sudo chattr +a /var/log/auth.log
# Log files can only be appended to, not truncated
```

## Security Best Practices

### Permission Auditing

```bash
# Find world-writable files
find / -type f -perm -o+w 2>/dev/null

# Find world-writable directories (without sticky bit)
find / -type d -perm -o+w ! -perm -1000 2>/dev/null

# Find SUID/SGID files
find / -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null

# Find files with no owner
find / -nouser -o -nogroup 2>/dev/null

# Find recently modified files
find / -type f -mtime -1 2>/dev/null

# Find files with capabilities
getcap -r / 2>/dev/null

# Find files with ACLs
find / -type f -exec getfacl -skip-base {} + 2>/dev/null | grep -B1 "user:"
```

### Common Permission Patterns

```bash
# Web server files
find /var/www -type f -exec chmod 644 {} +
find /var/www -type d -exec chmod 755 {} +
chown -R www-data:www-data /var/www

# SSH directory
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_rsa ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_rsa.pub ~/.ssh/id_ed25519.pub
chmod 644 ~/.ssh/authorized_keys
chmod 644 ~/.ssh/config
chmod 644 ~/.ssh/known_hosts

# Cron jobs
chmod 600 /etc/crontab
chmod 700 /etc/cron.d /etc/cron.daily /etc/cron.hourly
chmod 600 /var/spool/cron/crontabs/*

# Configuration files
chmod 644 /etc/nginx/nginx.conf
chmod 600 /etc/ssl/private/*.key
chmod 644 /etc/ssl/certs/*.crt

# Home directories
chmod 750 /home/username    # Owner full, group read/execute
```

## Cross-References

- [Users and Groups](users-groups.md) — User/group management
- [systemd](systemd.md) — Capabilities in service units
- [Package Management](package-management.md) — File permission during package install

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Linux man pages: chmod(1)](https://man7.org/linux/man-pages/man1/chmod.1.html) — chmod reference
- [Linux man pages: acl(5)](https://man7.org/linux/man-pages/man5/acl.5.html) — ACL specification
- [Linux man pages: capabilities(7)](https://man7.org/linux/man-pages/man7/capabilities.7.html) — Capabilities reference
- [Linux man pages: chattr(1)](https://man7.org/linux/man-pages/man1/chattr.1.html) — File attributes
- [POSIX ACL Tutorial](https://users.suse.com/~agruen/acl/linux-acls/online/) — Andreas Grünbacher's tutorial
- [Red Hat: Managing File Permissions](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_file_systems/assembly_controlling-access-to-files-and-directories_managing-file-systems) — RHEL documentation
