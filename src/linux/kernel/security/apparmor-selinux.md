# AppArmor and SELinux — The Two Linux MAC Systems

Linux has two **Mandatory Access Control** (MAC) systems in the mainline kernel that are widely deployed in production: **AppArmor** (default on Ubuntu, SUSE, Debian) and **SELinux** (default on RHEL/Fedora/CentOS, Android, and most government-validated distributions). Both are **Linux Security Modules** (LSMs) and slot into the same hook set in `security/`, but they have radically different models of identity, policy language, and granularity. This page covers both side-by-side, then compares them.

## 1. What MAC means here

DAC (Discretionary Access Control — the traditional UNIX permission bits and POSIX ACLs) lets a process with `rwx` on a file do what it likes. MAC additionally requires a **policy** to authorise the action regardless of DAC. So even if a process runs as `root` and the file mode is `0777`, MAC can still deny the access. The "mandatory" qualifier means the *system* (the kernel) enforces the policy; the *user* cannot turn it off without privilege.

Both AppArmor and SELinux are LSMs. They attach to roughly 200 hooks in the kernel — `security_inode_permission`, `security_file_open`, `security_task_setuid`, etc. — and either return `0` (allow) or `-EACCES` (deny). The two systems **cannot both be active at the same time** on the same hook; only one LSM may attach to a given hook. The recent [LSM stacking work](https://lwn.net/Articles/914855/) allows multiple stacks for some hooks (e.g. stacking BPF-LSM with Yama), but stacking two full MAC implementations is still not supported.

## 2. AppArmor

AppArmor confines **programs** by **path**. A profile is a list of rules saying "the binary at `/usr/bin/foo` may read these files, write these, connect to these sockets, and use these capabilities." The policy language is human-readable and lives in `/etc/apparmor.d/`.

### 2.1 Profile format

A profile is named after the path it confines, with slashes replaced by dots:

```
# /etc/apparmor.d/usr.sbin.tcpdump
#include <tunables/global>

profile tcpdump {
  #include <abstractions/base>
  #include <abstractions/nameservice-strict>

  network raw,
  network packet,
  capability net_raw,
  capability net_admin,
  capability dac_override,
  capability setuid,
  capability setgid,

  /usr/sbin/tcpdump      rix,            # r=read, i=inherit, x=execute
  /usr/share/tcpdump/**  r,
  /etc/protocols         r,
  /etc/services          r,
  /var/log/              rw,
  /var/log/tcpdump.log   w,
  /sys/class/net/        r,
  /sys/devices/**/net/** r,

  # Allow ptrace on self only:
  ptrace peer=unconfined,
  # Allow signal to self only:
  signal peer=unconfined,

  deny @{PROC}/sys/kernel/stack_tracer_enabled rw,
  deny @{PROC}/sys/net/** rw,
}
```

Key tokens:

- `r w a ix px ux rix` — read, write, append, inherit-exec, profile-exec, unconfined-exec, read+inherit-exec. The exec modes are crucial: `px` re-loads the profile for the executed binary, `ix` runs it under the current profile, `ux` runs it unconfined (very dangerous).
- `network raw` — allow raw socket creation.
- `capability net_raw` — allow `CAP_NET_RAW`.
- `#include` — pull in shared abstractions from `/etc/apparmor.d/abstractions/` and `/etc/apparmor.d/tunables/`.
- Variables: `@{PROC}`, `@{HOME}`, `@{pid}` — defined in `tunables/global`.
- `deny ...` — explicit denial; overrides any allow.

### 2.2 Modes: enforce, complain, audit

A profile can be in one of three modes:

| Mode | Behaviour |
|------|-----------|
| **enforce** | Violations are blocked. Logged to audit/log. |
| **complain** | Violations are **allowed** but logged. Use to test a profile. |
| **audit** | Same as enforce but with verbose logging. |

Switching modes:

```bash
# Put one profile into complain mode (test a new profile)
$ sudo aa-complain /etc/apparmor.d/usr.sbin.tcpdump

# Back to enforce
$ sudo aa-enforce /etc/apparmor.d/usr.sbin.tcpdump

# List all profiles and their modes
$ aa-status
apparmor module is loaded.
44 profiles are loaded.
30 profiles are in enforce mode.
14 profiles are in complain mode.
4 processes have profiles defined.
3 processes are in enforce mode.
1 processes are in complain mode.

# Disable AppArmor entirely
$ sudo systemctl disable --now apparmor
$ sudo systemctl stop apparmor
```

After editing a profile, reload it:

```bash
$ sudo apparmor_parser -r /etc/apparmor.d/usr.sbin.tcpdump
```

(`-r` means reload; `-R` removes; `-W` warns on unknown rules.)

### 2.3 Generating a profile from scratch

The standard workflow uses `aa-genprof`, which watches a process and produces rules from observed access:

```bash
$ sudo aa-genprof /usr/bin/myapp
# In another terminal, run myapp through its full workflow.
# Back in aa-genprof: scan the audit log, accept/deny each access.
```

Internally, AppArmor logs to `/var/log/audit/audit.log` (if auditd is installed) or to the kernel log. The userspace `aa-logparse` translates the denied entries into draft rules. This is the "complain, then enforce" loop.

### 2.4 Where AppArmor falls short

AppArmor is **path-based**. This means:

- A file **moved** from `/var/log/foo` to `/var/lib/foo` changes which profile rule applies, even though the inode is the same.
- Symlinks are evaluated as the **target** path, so writes through a symlink need the target path to be allowed.
- Bind mounts of the same inode to a new path are not transparently allowed.

This makes AppArmor easier to read but less precise than SELinux for a filesystem with many equivalent paths (containers, overlayfs, bind mounts). On the other hand, AppArmor profiles are typically 30–100 lines vs SELinux modules of thousands of lines.

## 3. SELinux

SELinux confines processes by **type** (a label attached to the inode via an extended attribute). It was originally developed by the NSA on the [Flask architecture](https://www.nsa.gov/portals/75/documents/news-features/news-stories/2005/selinux.pdf) and merged in kernel 2.6.0 (December 2003). The model is **label-based** and **type-enforcement (TE)** is the dominant policy class.

### 3.1 Labels, types, roles, domains

Every process and every inode has an **SELinux context**:

```bash
$ ps -eZ | head
LABEL                               PID TTY      TIME CMD
system_u:system_r:init_t:s0           1 ?        00:00:00 systemd
system_u:system_r:kernel_t:s0        2 ?        00:00:00 kthreadd
system_u:system_r:unconfined_service_t:s0  1234 ? 00:00:00 sshd

$ ls -Z /var/www/html/index.html
-rw-r--r--. 1 root root unconfined_u:object_r:httpd_sys_content_t:s0 /var/www/html/index.html
```

The format is `user:role:type:level`. The **type** is what matters for type-enforcement; in the example `init_t`, `kernel_t`, `httpd_sys_content_t`. Processes run in a **domain** (a type applied to a process); files have a type. A TE rule says "domain A may perform operation X on objects of type B."

Example: `allow httpd_t httpd_sys_content_t : file { read getattr open };` means "processes in the `httpd_t` domain may read, getattr, and open files whose type is `httpd_sys_content_t`."

### 3.2 Policy modules and source

SELinux policy is written in a small DSL and compiled into the binary policy at `/etc/selinux/<policy>/policy.*`. For the default `targeted` policy on Fedora:

```bash
$ sudo dnf install selinux-policy-devel
$ cd /root/myapp-selinux
$ cat myapp.te
policy_module(myapp, 1.0)

type myapp_t;
type myapp_exec_t;
type myapp_log_t;

init_daemon_domain(myapp_t, myapp_exec_t)
# ^ transition to myapp_t when /usr/sbin/myapp is exec'd from init_t

logging_log_file(myapp_log_t)

# Allow myapp to read/write its log
allow myapp_t myapp_log_t:file { create read write append };

# Allow myapp to listen on tcp port 8080
corenet_tcp_bind_generic_port(myapp_t, 8080)
```

Compile and install:

```bash
$ make -f /usr/share/selinux/devel/Makefile myapp.pp
$ sudo semodule -i myapp.pp
$ sudo restorecon -v /usr/sbin/myapp /var/log/myapp
```

`semodule -i` loads the binary module; `restorecon` relabels files according to the fcontext database:

```bash
$ sudo semanage fcontext -a -t myapp_exec_t '/usr/sbin/myapp'
$ sudo semanage fcontext -a -t myapp_log_t '/var/log/myapp(/.*)?'
$ sudo restorecon -Rv /usr/sbin/myapp /var/log/myapp
```

### 3.3 MLS vs targeted

There are two shipped policies on RHEL-family:

| Policy | Path | Purpose |
|--------|------|---------|
| `targeted` | `/etc/selinux/targeted/` | Most daemons confined; user sessions unconfined (in `unconfined_t`). The default. |
| `mls` | `/etc/selinux/mls/` | Multi-Level Security: every subject has a clearance (e.g. `s0:c0.c100`); every object has a classification; Bell-LaPadula + Biba. Used in high-assurance systems. |
| `minimum` | `/etc/selinux/minimum/` | Minimal policy for embedded use. |

MLS adds the `level` component to every label. A process at `s0:c10` cannot read an object at `s0:c20` (no read up), and cannot write to `s0:c5` (no write down). This is Bell-LaPadula for confidentiality and Biba for integrity, expressed in a single mandatory label. The `targeted` policy uses a much simpler **MCS** (Multi-Category System) form of this for container isolation: each container gets a unique `s0:c<N>,c<M>` pair, and the policy says two processes can only interact if their MCS levels overlap. No TE rules need to be written for this.

### 3.4 Modes: enforcing, permissive, disabled

```bash
$ getenforce
Enforcing

$ sudo setenforce 0       # Permissive (denials are logged but not enforced)
$ getenforce
Permissive

$ sudo setenforce 1       # Back to enforcing

# Persist across reboots:
$ sudo vim /etc/selinux/config
SELINUX=enforcing      # or permissive, or disabled
```

`setenforce 0` is great for capturing logs of what would be denied. The persistent setting lives in `/etc/selinux/config`. To make a single domain permissive without flipping the whole system, use `semanage permissive -a myapp_t`.

### 3.5 audit2allow

When you see audit denials like:

```
type=AVC msg=audit(1717823456.123:456): avc:  denied  { read } for pid=1234 \
  comm="myapp" name="foo.txt" dev="dm-0" ino=789012 \
  scontext=system_u:system_r:myapp_t:s0 \
  tcontext=system_u:object_r:var_log_t:s0 tclass=file
```

you can pipe the audit log to `audit2allow`:

```bash
$ sudo grep myapp /var/log/audit/audit.log | audit2allow -m myapp_local > myapp_local.te
$ cat myapp_local.te
module myapp_local 1.0;

require {
    type myapp_t;
    type var_log_t;
    class file read;
}

allow myapp_t var_log_t:file read;

$ sudo audit2allow -M myapp_local < /var/log/audit/audit.log
$ sudo semodule -i myapp_local.pp
```

This is the SELinux equivalent of "complain mode + accept rules": it generates the minimum-allow policy from observed denials. Caveat: `audit2allow` is a **permissive** tool; it generates allow rules that may be **overly broad**. Every generated rule needs human review.

### 3.6 Booleans

For tunable policy knobs SELinux exposes **booleans**:

```bash
$ getsebool -a | grep httpd
httpd_can_network_connect --> off
httpd_can_sendmail --> off
httpd_unified --> off

$ sudo setsebool -P httpd_can_network_connect on
```

Booleans let you toggle pre-defined allow rules without recompiling the policy. The `-P` makes it persistent across reboots. Common ones:

- `httpd_can_network_connect` — allow Apache to connect to backends
- `httpd_can_sendmail` — allow Apache to call sendmail
- `use_nfs_home_dirs` — allow user home dirs on NFS
- `unprivileged_userns` — allow non-root users to create user namespaces

## 4. Comparison

| Dimension | AppArmor | SELinux |
|-----------|----------|---------|
| **Identity model** | path of binary | label (xattr) on inode |
| **Granularity** | program + file paths | type + role + MLS level |
| **Policy language** | DSL, INI-like | M4 macro + TE/IF/FC files |
| **Learning curve** | shallow | steep |
| **Profile size** | 30–200 lines typical | thousands of lines |
| **Container support** | tunable per-app; profiles must match path | MCS labels per container |
| **Audit tool** | aa-logparse, aa-status | audit2allow, sealert, aureport |
| **Default distros** | Ubuntu, Debian, SUSE, openSUSE | RHEL, Fedora, CentOS, Android |
| **MLS / Bell-LaPadula** | no | yes (`mls` policy) |
| **Stacking** | yes (one of multiple LSMs) | yes |
| **In-tree since** | 2.6.36 (2010) | 2.6.0 (2003) |
| **Hook** | `apparmor_*` in `security/apparmor/` | `selinux_*` in `security/selinux/` |

AppArmor's path-based model wins on **clarity** ("the rule literally says `/var/log/tcpdump.log w`") and on **distribution profile portability** — the same profile works on Debian and SUSE. SELinux's label-based model wins on **precision**: a label survives `mv`, `cp -a`, tarball extraction, bind mounts, and even NFSv4 (`sec_label` xattr). For container workloads SELinux's **MCS** (Multi-Category System) separates tenants at the label level — every container gets its own `s0:c<N>,c<M>` — with no policy writing required.

A common production posture: **enable both LSMs for defense-in-depth, with AppArmor as the lightweight confinement layer and SELinux as the heavyweight isolation layer.** As of kernel 5.x you can stack AppArmor + SELinux + BPF-LSM + Yama + Lockdown in many configurations, although the fine details depend on `CONFIG_LSM=` at build time.

## 5. Common debugging commands

```bash
# AppArmor
$ aa-status
$ aa-logprof
$ dmesg | grep apparmor
$ journalctl -t audit | grep DENIED | grep apparmor

# SELinux
$ getenforce
$ sestatus
$ semanage login -l
$ semanage fcontext -l | grep myapp
$ chcon -t httpd_sys_content_t /var/www/html/index.html   # one-shot relabel (not persistent!)
$ restorecon -Rv /var/www/html                              # relabel from fcontext rules
$ aureport -a | tail
$ ausearch -m avc -ts recent
$ sealert -a /var/log/audit/audit.log
$ semanage permissive -l
$ semodule -l | head
```

## References

- AppArmor project wiki, https://gitlab.com/apparmor/apparmor/-/wikis/home
- AppArmor man pages index, https://manpages.ubuntu.com/manpages/noble/en/man5/apparmor.d.5.html
- SELinux Project Notebook, https://github.com/SELinuxProject/selinux-notebook
- NSA SELinux paper (Loscocco, Smalley, et al.), https://www.nsa.gov/portals/75/documents/news-features/news-stories/2005/selinux.pdf
- SELinux User's and Administrator's Guide (Red Hat), https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/using_selinux/index
- LWN: "AppArmor and SELinux" — Jake Edge, https://lwn.net/Articles/223784/
- LWN: "A look at the AppArmor controversy" — Jonathan Corbet, https://lwn.net/Articles/209815/
- LWN: "LSM stacking" — Jonathan Corbet, https://lwn.net/Articles/914855/
- LWN: "Multi-category Security for SELinux containers" — Jake Edge, https://lwn.net/Articles/436451/
- The Linux Security Module framework documentation, https://www.kernel.org/doc/html/latest/security/lsm.html
- SELinux Project documentation index, https://selinuxproject.org/
- man setenforce(8), https://man7.org/linux/man-pages/man8/setenforce.8.html
