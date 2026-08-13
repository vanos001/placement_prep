# Users and Groups

User and group management is fundamental to Linux security. Every file, process, and resource is owned by a user and belongs to a group. This chapter covers user/group databases, management commands, PAM authentication, and LDAP integration.

## User and Group Databases

### `/etc/passwd` — User Database

Each line represents one user with colon-separated fields:

```bash
# Format:
# username:password:UID:GID:GECOS:home_directory:login_shell

$ cat /etc/passwd | head -5
root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
```

| Field | Description | Example |
|-------|-------------|---------|
| Username | Login name | `root` |
| Password | `x` means shadow (see below) | `x` |
| UID | User ID number | `0` |
| GID | Primary group ID | `0` |
| GECOS | Full name/comment | `root` |
| Home | Home directory | `/root` |
| Shell | Login shell | `/bin/bash` |

### `/etc/shadow` — Password Database

Stores hashed passwords and account aging information:

```bash
# Format:
# username:password:last_change:min:max:warn:inactive:expire:reserved

$ sudo cat /etc/shadow | head -3
root:$6$rounds=656000$salt$hash:19876:0:99999:7:::
daemon:*:19876:0:99999:7:::
user1:$6$rounds=656000$salt$hash:19876:0:99999:7:14::
```

| Field | Description | Example |
|-------|-------------|---------|
| Username | Login name | `root` |
| Password | Hashed password (or `!`, `*` for locked) | `$6$rounds=...` |
| Last change | Days since Jan 1, 1970 since password change | `19876` |
| Min days | Minimum days between password changes | `0` |
| Max days | Maximum days password is valid | `99999` |
| Warn days | Days before expiry to warn user | `7` |
| Inactive | Days after expiry before account is locked | (empty) |
| Expire | Days since Jan 1, 1970 when account expires | (empty) |
| Reserved | Reserved for future use | (empty) |

### `/etc/group` — Group Database

```bash
# Format:
# group_name:password:GID:members

$ cat /etc/group | head -5
root:x:0:
daemon:x:1:
bin:x:2:
sys:x:3:
adm:x:4:syslog,user1
```

### `/etc/gshadow` — Group Shadow

```bash
# Format:
# group_name:password:admins:members

$ sudo cat /etc/gshadow | head -3
root:*::
daemon:*::
sudo:*::user1,user2
```

### UID Ranges

| Range | Purpose |
|-------|---------|
| 0 | root |
| 1-999 | System users (daemons) |
| 1000-60000 | Regular users |
| 60001-65534 | Nobody, overflow |
| 65535 | `nobody` (traditional) |

```bash
# View UID ranges
grep -E '^UID_' /etc/login.defs

# Typical login.defs settings
UID_MIN           1000
UID_MAX           60000
SYS_UID_MIN       100
SYS_UID_MAX       999
GID_MIN           1000
GID_MAX           60000
SYS_GID_MIN       100
SYS_GID_MAX       999
```

## User Management Commands

### `useradd` — Create Users

```bash
# Basic user creation
sudo useradd username

# Full-featured creation
sudo useradd \
    --uid 1001 \
    --gid users \
    --groups sudo,docker,adm \
    --home /home/username \
    --create-home \
    --shell /bin/bash \
    --comment "Full Name" \
    --expire-date 2025-12-31 \
    --password "$(openssl passwd -6 'password')" \
    username

# System user (no login, no home)
sudo useradd --system --shell /usr/sbin/nologin myservice

# User with specific home directory skeleton
sudo useradd --skel /etc/custom-skel username

# Check what useradd would do (dry run)
sudo useradd -D
# Default settings from /etc/default/useradd and /etc/login.defs

# Set defaults
sudo useradd -D --shell /bin/bash
sudo useradd -D --expire-date 2025-12-31
```

### `usermod` — Modify Users

```bash
# Change login name
sudo usermod --login newname oldname

# Change home directory
sudo usermod --move-home --home /new/home username

# Add to groups (append)
sudo usermod --append --groups docker,video username

# Change shell
sudo usermod --shell /bin/zsh username

# Lock account
sudo usermod --lock username

# Unlock account
sudo usermod --unlock username

# Set expiry date
sudo usermod --expiredate 2025-12-31 username

# Set password expiry
sudo usermod --maxdays 90 username
sudo usermod --mindays 7 username
sudo usermod --warndays 14 username

# Change UID
sudo usermod --uid 2001 username

# Change primary group
sudo usermod --gid 100 username

# Lock and expire (disable without deleting)
sudo usermod --lock --expiredate 1 username
```

### `userdel` — Delete Users

```bash
# Delete user (keep home)
sudo userdel username

# Delete user and home directory
sudo userdel --remove username

# Delete user, home, and mail spool
sudo userdel --remove --selinux-username username
# Also remove:
sudo rm -rf /var/mail/username /var/spool/mail/username

# Force deletion (even if logged in)
sudo userdel --force --remove username
```

### `passwd` — Password Management

```bash
# Change own password
passwd

# Change another user's password (as root)
sudo passwd username

# Set initial password
sudo passwd --stdin username <<< "newpassword"
echo "newpassword" | sudo passwd --stdin username  # RHEL
echo "username:newpassword" | sudo chpasswd         # Debian/Ubuntu

# Lock account (disable password)
sudo passwd --lock username
sudo passwd -l username

# Unlock account
sudo passwd --unlock username
sudo passwd -u username

# Set password expiry
sudo passwd --expire username           # Force change on next login
sudo passwd --expire 90 username        # Expire after 90 days

# Check password status
sudo passwd -S username
# Output: username P 2024-01-01 0 99999 7 -1

# Generate random password
openssl rand -base64 12
pwgen 16 1                              # If pwgen installed

# Set minimum password age
sudo passwd -n 7 username               # Can't change for 7 days

# Set maximum password age
sudo passwd -x 90 username              # Must change every 90 days

# Set warning period
sudo passwd -w 14 username              # Warn 14 days before expiry
```

### `chage` — Password Aging

```bash
# Interactive password aging
sudo chage username

# View aging info
sudo chage -l username
# Output:
# Last password change                    : Jan 01, 2024
# Password expires                        : Apr 01, 2024
# Password inactive                       : never
# Account expires                         : never
# Minimum number of days between password change : 0
# Maximum number of days between password change : 90
# Number of days of warning before password expires : 7

# Set specific values
sudo chage -d 2024-01-01 username    # Last change date
sudo chage -m 7 username             # Min days
sudo chage -M 90 username            # Max days
sudo chage -W 14 username            # Warning days
sudo chage -I 30 username            # Inactive days after expiry
sudo chage -E 2025-12-31 username    # Account expiry date

# Force password change on next login
sudo chage -d 0 username

# Disable password expiry
sudo chage -M -1 username
sudo chage -M 99999 username
```

## Group Management Commands

### `groupadd` — Create Groups

```bash
# Basic group creation
sudo groupadd groupname

# With specific GID
sudo groupadd --gid 2001 groupname

# System group
sudo groupadd --system groupname

# Non-unique GID (multiple groups share GID)
sudo groupadd --non-unique --gid 100 groupname2
```

### `groupmod` — Modify Groups

```bash
# Rename group
sudo groupmod --new-name newname oldname

# Change GID
sudo groupmod --gid 2002 groupname
```

### `groupdel` — Delete Groups

```bash
# Delete group
sudo groupdel groupname

# Can't delete primary group of existing user
# Must change user's primary group first
```

### `gpasswd` — Group Administration

```bash
# Add user to group
sudo gpasswd --add user groupname

# Remove user from group
sudo gpasswd --delete user groupname

# Set group administrators
sudo gpasswd --admin user1 --admin user2 groupname

# Set group password (rarely used)
sudo gpasswd groupname

# Remove group password
sudo gpasswd -r groupname

# Set members (replaces all)
sudo gpasswd --members user1,user2,user3 groupname
```

### `newgrp` — Change Primary Group

```bash
# Switch to group (creates new shell)
newgrp docker

# Switch with password
newgrp docker   # Prompts if group has password

# Log in as group
sg docker -c "docker ps"  # Run command with group
```

## `/etc/login.defs` — Login Defaults

```bash
# Password hashing algorithm
ENCRYPT_METHOD SHA512

# Password aging
PASS_MAX_DAYS   99999
PASS_MIN_DAYS   0
PASS_WARN_AGE   7
PASS_MIN_LEN    8

# UID/GID ranges
UID_MIN                1000
UID_MAX               60000
SYS_UID_MIN           101
SYS_UID_MAX           999
GID_MIN                1000
GID_MAX               60000
SYS_GID_MIN           101
SYS_GID_MAX           999

# Home directory creation
CREATE_HOME     yes
HOME_MODE       0750

# User/group deletion
USERDEL_CMD     /usr/sbin/userdel_post.sh

# Login definitions
LOGIN_RETRIES           5
LOGIN_TIMEOUT           60
DEFAULT_HOME            yes
```

## `/etc/skel` — Skeleton Directory

Files in `/etc/skel` are copied to new users' home directories:

```bash
# View skeleton
ls -la /etc/skel/
# .bash_logout
# .bashrc
# .profile

# Customize skeleton
sudo cp /path/to/custom/.bashrc /etc/skel/
sudo mkdir -p /etc/skel/.config
sudo cp /path/to/custom/config /etc/skel/.config/
```

## PAM — Pluggable Authentication Modules

PAM provides a flexible framework for authentication, authorization, and session management.

### PAM Configuration

```bash
# PAM config directory
ls /etc/pam.d/

# Example: /etc/pam.d/sshd
# Type    Control   Module
auth      required  pam_env.so
auth      required  pam_env.so envfile=/etc/default/locale
auth      required  pam_nologin.so
@include  common-auth
account   required  pam_nologin.so
@include  common-account
session   required  pam_limits.so
session   required  pam_env.so
@include  common-session
@include  common-password
```

### PAM Module Types

| Type | Purpose |
|------|---------|
| `auth` | Verify user identity (password, biometric) |
| `account` | Account validity (expiry, access restrictions) |
| `password` | Password change rules |
| `session` | Setup/teardown session (logging, limits) |

### PAM Control Flags

| Flag | Meaning |
|------|---------|
| `required` | Must succeed; continue checking on failure |
| `requisite` | Must succeed; fail immediately on failure |
| `sufficient` | If succeeds and no prior required fails, skip remaining |
| `optional` | Success/failure only matters if this is the only module |
| `include` | Include another config file |
| `substack` | Like include, but failure in substack doesn't fail parent |

### PAM Flow

```
┌─────────────────────────────────────────────────────┐
│  PAM Authentication Flow                             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Login Request                                      │
│  ├── auth     → pam_unix.so (check password)        │
│  ├── auth     → pam_ldap.so (LDAP auth)             │
│  ├── account  → pam_access.so (access control)      │
│  ├── account  → pam_time.so (time restrictions)     │
│  ├── password → pam_unix.so (password change)       │
│  ├── password → pam_cracklib.so (strength check)    │
│  ├── session  → pam_limits.so (resource limits)     │
│  ├── session  → pam_systemd.so (logind session)     │
│  └── session  → pam_motd.so (message of the day)    │
│                                                     │
│  Control Flow:                                       │
│  required → fail continues, overall fails           │
│  requisite → fail stops immediately                  │
│  sufficient → success skips remaining (if no fails) │
│  optional → only matters if sole module              │
└─────────────────────────────────────────────────────┘
```

### Common PAM Modules

```bash
# pam_unix.so — Traditional Unix authentication
auth    required    pam_unix.so nullok try_first_pass

# pam_ldap.so — LDAP authentication
auth    sufficient  pam_ldap.so use_first_pass

# pam_deny.so — Always deny
auth    required    pam_deny.so

# pam_permit.so — Always permit
auth    required    pam_permit.so

# pam_wheel.so — Require wheel group for su
auth    required    pam_wheel.so use_uid

# pam_limits.so — Resource limits
session required    pam_limits.so

# pam_cracklib.so / pam_pwquality.so — Password strength
password required   pam_pwquality.so retry=3 minlen=12

# pam_tally2.so / pam_faillock.so — Account lockout
auth    required    pam_faillock.so preauth deny=5 unlock_time=900
auth    required    pam_faillock.so authfail deny=5 unlock_time=900

# pam_access.so — Access control
account required    pam_access.so

# pam_time.so — Time-based access
account required    pam_time.so

# pam_securetty.so — Root login only on secure ttys
auth    required    pam_securetty.so

# pam_env.so — Environment variables
auth    required    pam_env.so

# pam_mkhomedir.so — Create home on first login
session required    pam_mkhomedir.so skel=/etc/skel umask=0022
```

### Password Quality Configuration

```bash
# /etc/security/pwquality.conf
minlen = 12
dcredit = -1        # At least 1 digit
ucredit = -1        # At least 1 uppercase
lcredit = -1        # At least 1 lowercase
ocredit = -1        # At least 1 special character
maxrepeat = 3       # Max 3 consecutive identical chars
maxclassrepeat = 4  # Max 4 consecutive same-class chars
gecoscheck = 1      # Reject if similar to GECOS
dictcheck = 1       # Check against dictionary
usercheck = 1       # Reject if similar to username
enforcing = 1       # Reject non-compliant passwords
retry = 3           # 3 attempts before error
```

### Account Lockout with pam_faillock

```bash
# /etc/pam.d/common-auth (Debian/Ubuntu)
auth    required    pam_faillock.so preauth silent deny=5 unlock_time=900
auth    required    pam_faillock.so authfail deny=5 unlock_time=900

# /etc/pam.d/system-auth (RHEL/CentOS)
auth    required    pam_faillock.so preauth silent deny=5 unlock_time=900
auth    [default=die] pam_faillock.so authfail deny=5 unlock_time=900

# Check failed attempts
sudo faillock --user username

# Unlock user
sudo faillock --user username --reset

# /etc/security/faillock.conf
deny = 5
unlock_time = 900
fail_interval = 900
audit
even_deny_root
root_unlock_time = 600
```

## LDAP Integration

### OpenLDAP Client Configuration

```bash
# Install packages
sudo apt install libnss-ldap libpam-ldap nscd    # Debian/Ubuntu
sudo yum install nss-pam-ldapd openldap-clients    # RHEL/CentOS

# Or use SSSD (recommended)
sudo apt install sssd sssd-ldap sssd-tools         # Debian/Ubuntu
sudo yum install sssd sssd-ldap sssd-tools          # RHEL/CentOS
```

### SSSD Configuration

```ini
# /etc/sssd/sssd.conf
[sssd]
config_file_version = 2
services = nss, pam
domains = example.com

[domain/example.com]
id_provider = ldap
auth_provider = ldap
chpass_provider = ldap
access_provider = ldap

# LDAP settings
ldap_uri = ldap://ldap.example.com:389
ldap_backup_uri = ldap://ldap2.example.com:389
ldap_search_base = dc=example,dc=com
ldap_default_bind_dn = cn=readonly,dc=example,dc=com
ldap_default_authtok = secret_password
ldap_tls_reqcert = demand
ldap_tls_cacert = /etc/ssl/certs/ca-certificates.crt

# User/group mapping
ldap_user_search_base = ou=People,dc=example,dc=com
ldap_group_search_base = ou=Groups,dc=example,dc=com
ldap_user_object_class = posixAccount
ldap_group_object_class = posixGroup

# ID mapping
ldap_id_use_start_tls = true
cache_credentials = true
enumerate = false

# Access control
ldap_access_order = filter
ldap_access_filter = (objectClass=posixAccount)

# Shell/home fallback
override_shell = /bin/bash
override_homedir = /home/%u

[nss]
filter_groups = root
filter_users = root
reconnection_retries = 3

[pam]
pam_verbosity = 1
```

```bash
# Set permissions
sudo chmod 600 /etc/sssd/sssd.conf
sudo systemctl enable sssd
sudo systemctl start sssd

# Test
id username
getent passwd username
getent group groupname
```

### Name Service Switch (NSS)

```bash
# /etc/nsswitch.conf
passwd:         compat systemd sss
group:          compat systemd sss
shadow:         compat sss
hosts:          files dns myhostname
services:       files sss
netgroup:       nis sss

# Test NSS resolution
getent passwd username
getent group groupname
getent hosts hostname

# Debug NSS
LC_ALL=C getent -s sss passwd username
```

### SSSD Cache Management

```bash
# Clear cache
sudo sss_cache --everything
sudo sss_cache -E

# Clear specific user
sudo sss_cache -u username

# View cached data
sudo sssctl user-show username
sudo sssctl group-show groupname

# Check SSSD status
sudo sssctl domain-status example.com
```

## Advanced User Management

### Restricting User Access

```bash
# Restrict to specific hosts (PAM)
# /etc/security/access.conf
# + : admin : ALL
# + : user1 : 10.0.0.0/24
# - : ALL : ALL

# Restrict login times
# /etc/security/time.conf
# login ; * ; user1 ; Wk0800-1800

# Restrict resource limits
# /etc/security/limits.conf
# user1    hard    nproc     100
# user1    hard    nofile    1024
# @group1  soft    core      0
# *        hard    maxlogins 10

# Restrict to specific ttys
# /etc/securetty
# tty1
# tty2
# (empty = no root login on any tty)
```

### `su` and `sudo`

```bash
# Switch user
su - username         # Login shell (full environment)
su username           # Non-login shell
su -c "command" user  # Run command as user

# sudo configuration
sudo visudo           # Edit /etc/sudoers safely

# /etc/sudoers syntax
# user    host=(runas)    commands
root    ALL=(ALL:ALL) ALL
user1   ALL=(ALL:ALL) ALL
%admin  ALL=(ALL:ALL) ALL
%sudo   ALL=(ALL:ALL) NOPASSWD: ALL

# Command restrictions
user1   ALL = /usr/bin/systemctl restart nginx, /usr/bin/systemctl status nginx

# Require password re-entry
Defaults timestamp_timeout=0

# No password for specific commands
user1   ALL = NOPASSWD: /usr/bin/apt update, /usr/bin/apt upgrade

# Group-based
%devs   ALL = (deploy) /usr/local/bin/deploy.sh

# Host aliases
Host_Alias WEBSERVERS = web1, web2, web3
WEBSERVERS = /usr/bin/systemctl restart nginx

# Command aliases
Cmnd_Alias RESTART = /usr/bin/systemctl restart nginx, /usr/bin/systemctl restart apache2
user1   ALL = RESTART
```

### `last`, `lastlog`, `who`, `w`

```bash
# View login history
last                    # All logins
last username           # Specific user
last -n 10              # Last 10 logins
last -s yesterday       # Since yesterday

# View last login for all users
lastlog
lastlog -u username

# Currently logged in users
who                     # Basic info
w                       # Detailed info (what they're doing)
whoami                  # Current username
id                      # Current UID/GID/groups

# View failed logins
lastb                   # Failed login attempts (requires root)
```

### Account Expiry and Aging Summary

```bash
# Check account status
chage -l username       # Password aging info
passwd -S username      # Password status
sudo faillock --user username  # Failed login attempts

# Set account expiry
usermod -e 2025-12-31 username
chage -E 2025-12-31 username

# Force password change
passwd -e username
chage -d 0 username

# Disable account
usermod -L username     # Lock password
usermod -s /usr/sbin/nologin username  # Change shell
usermod --expiredate 1 username        # Expire immediately

# Re-enable account
usermod -U username     # Unlock password
usermod -s /bin/bash username          # Restore shell
usermod --expiredate "" username       # Remove expiry
```

## Cross-References

- [File Permissions](permissions.md) — Ownership and ACL management
- [systemd](systemd.md) — systemd-logind and PAM integration
- [Package Management](package-management.md) — Installing LDAP/SSSD packages

## Further Reading

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [Linux System Administration Handbook](https://www.admin.com/) — Comprehensive admin guide
- [PAM Administrator's Guide](https://linux.die.net/man/8/pam) — PAM documentation
- [SSSD Documentation](https://sssd.io/) — SSSD project documentation
- [OpenLDAP Admin Guide](https://www.openldap.org/doc/admin26/) — OpenLDAP documentation
- [Red Hat: Managing Users and Groups](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_systems_using_the_rhel9_web_console/assembly_managing-users-and-groups-from-the-web-console_system-management-using-the-rhel9-web-console) — RHEL documentation
