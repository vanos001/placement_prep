# useradd — create a new user account (shadow low level)

## Overview

`useradd` is the shadow suite's low-level account creation tool. It writes the new account into `/etc/passwd`, `/etc/shadow`, `/etc/group`, `/etc/gshadow`, and (on modern systems) `/etc/subuid`/`/etc/subgid`, and optionally builds a home directory from a skeleton tree. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/useradd` — it is an administrator tool, not an ordinary user command. Its own man page opens with the Debian-relevant caveat that administrators *usually* want `adduser(8)` instead: `useradd` is deliberately literal, creates nothing you did not ask for, and has no opinion about sane defaults for humans.

`useradd` is often confused with Debian's `adduser` (an interactive Perl front end that wraps useradd/groupadd and has its own `/etc/adduser.conf` policy), with `newusers` (a batch tool that feeds `/etc/passwd`-formatted lines through the same machinery), and with `groupadd` (which it may call internally for the per-user group). When you script account provisioning — Ansible, cloud-init, container builds — you are almost always invoking `useradd` directly, which is why it, and not `adduser`, is the interviewable binary.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/useradd |
| First appeared | System V lineage; shadow suite (Julianne F. Haugh, 1988+), now maintained by shadow-maint |
| Standards | Not POSIX; specified by LSB. Behavior partly configured via /etc/login.defs |

## Synopsis

```
useradd [options] LOGIN
useradd -D
useradd -D [options]
```

Common one-line forms:

```
useradd -m -s /bin/bash -c "Ann Doe" ann    # ordinary login account
useradd -r -s /usr/sbin/nologin svc-backup  # system service account
useradd -m -G docker,sudo dev1              # account with supplementary groups
useradd -D -s /bin/bash                     # persist a new default shell
```

## How It Works

### Three layers of defaults

Every invocation assembles the account from three layers, later layers winning:

```
layer 1: compiled-in fallbacks          (GROUP=100, HOME=/home, SKEL=/etc/skel, ...)
layer 2: /etc/login.defs                (UID ranges, aging, USERGROUPS_ENAB, HOME_MODE, UMASK)
layer 3: /etc/default/useradd           (SHELL=, HOME=, INACTIVE=, EXPIRE=, SKEL=, ...)
layer 4: command-line options           (always override everything above)
```

`useradd -D` prints layers 1-3 as it sees them. On this container:

```
$ useradd -D
GROUP=100
GROUPS=
HOME=/home
INACTIVE=-1
EXPIRE=
SHELL=/bin/sh
SKEL=/etc/skel
USRSKEL=/usr/etc/skel
CREATE_MAIL_SPOOL=no
LOG_INIT=yes
```

The exact key set grows with the shadow version (`USRSKEL` and `LOG_INIT` are recent additions; Debian bookworm's 4.13 stops at `CREATE_MAIL_SPOOL`). Note `SHELL=/bin/sh`: Debian's default useradd shell is plain `sh`, not `bash` — the file itself documents that this is intentional, because useradd is a low-level tool. Interactive systems get `bash` because `adduser` defaults to it, not because useradd does.

`/etc/login.defs` contributes the rest: `UID_MIN`/`UID_MAX` (1000-60000 here), `SYS_UID_MIN`/`SYS_UID_MAX` (101-999 by default, or explicitly set), `PASS_MAX_DAYS`/`PASS_MIN_DAYS`/`PASS_WARN_AGE` (99999/0/7 here), `USERGROUPS_ENAB yes`, `HOME_MODE 0700`, and `UMASK`.

### UID selection

Without `-u`, useradd picks the first unused UID in the configured range:

- ordinary accounts: `UID_MIN`..`UID_MAX`, scanning upward from 1000;
- `-r` system accounts: `SYS_UID_MIN`..`SYS_UID_MAX` (default 101..999), and shadow scans this range *downward* from `SYS_UID_MAX`, which is why successive system daemons tend to collect at the top of the range (999, 998, ...).

A UID is "used" if it appears in `/etc/passwd`. useradd does not check filesystem ownership — UID reuse on a box where files from an older user were never chowned is a classic mess. `-u N` pins the UID; `-u N -o` explicitly allows a duplicate (shared-UID setups, mostly legacy and generally a design smell).

### Group machinery

With `USERGROUPS_ENAB yes` (Debian and Fedora default) and no `-g`/`-N`, useradd creates a per-user group: a group named after the login with the same GID as the user's UID, set as primary. This is the Debian/Red Hat "user private group" model that makes umask 002 with setgid directories workable.

```
-g staff     use an existing group as primary (no per-user group created)
-N           do not create the per-user group (primary becomes GROUP= default)
-U           force the per-user group (explicit form of the default)
-G a,b,c     supplementary memberships (in addition to whatever primary results)
```

If the group name is taken but the user name is not (or vice versa), useradd fails — username and groupname share one namespace check.

### Home directory and /etc/skel

Home creation only happens with `-m` (or `-M` to forbid it, useful when a config file somewhere passes `-m` unconditionally). The procedure:

1. create `HOME/<login>` (`-d` overrides the base path entirely);
2. copy everything from the skeleton directory (`-k DIR`, default from `SKEL=/etc/skel`) — including dotfiles, which is why `ls /etc/skel` shows `.bashrc`, `.profile`, `.bash_logout`;
3. chown the tree to the new UID:GID and apply the mode: `HOME_MODE` if set (0700 here), otherwise `0777 & ~UMASK`.

If the target directory already exists, useradd does **not** copy the skeleton — it leaves the directory alone. That is a frequent source of "new user got a bare shell" reports: the home was pre-created by some other mechanism.

`CREATE_MAIL_SPOOL=yes` (in `/etc/default/useradd`) additionally touches `/var/spool/mail/<login>`.

### What lands where

```
/etc/passwd     name:x:UID:GID:GECOS:home:shell      (the "x" means shadowed)
/etc/shadow     name:!hash:lastchg:min:max:warn:inactive:expire:   (hash starts '!')
/etc/group      per-user group line (unless -N/-g)
/etc/gshadow    matching secure group line
/etc/subuid     name:100000:65536   (subordinate UID range, if subuids configured)
/etc/subgid     name:100000:65536
/var/spool/mail login spool file    (only if CREATE_MAIL_SPOOL=yes)
home directory  skel copies          (only with -m)
```

The initial shadow password is `!` — a locked field. A freshly created account cannot log in with a password no matter what else you do until you set one with `passwd LOGIN` (or deliver a crypt hash with `-p`/`chpasswd`). This is a feature: it prevents accidentally creating working accounts from a provisioning script before the secret distribution step.

Updates are done under a lock (`/etc/passwd.lock` and friends) and leave `.bak`-style backups (`/etc/passwd-`, `/etc/shadow-`), which is why you should treat `/etc/passwd-` as sensitive as `/etc/passwd`.

### System accounts (-r)

`-r` changes four things at once:

- UID is chosen from `SYS_UID_MIN`-`SYS_UID_MAX` (101-999) instead of the login range;
- no aging information is written to `/etc/shadow` (min/max/warn stay empty) — daemons must never be locked out by a password policy;
- no home directory is created even though `-r` implies `-M`; pass `-m` explicitly if you want one;
- since shadow 4.14, subordinate ID ranges are *not* allocated for system accounts unless you add `-F/--add-subids-for-system`.

The conventional pairing is `useradd -r -s /usr/sbin/nologin ...`: a system account that can own files and run a service but has no interactive shell and (via the locked password) no password login. The account is still fully functional as a file/process owner.

### Subordinate IDs

Modern shadow allocates each ordinary user a subordinate UID/GID range from `/etc/login.defs` (`SUB_UID_MIN 100000`, `SUB_UID_MAX 600100000`, `SUB_UID_COUNT 65536` here) into `/etc/subuid`/`/etc/subgid`. These ranges are what unprivileged `user_namespace` operations — `podman`, `lxc`, `unshare -U` — map into the container's root. After creating a user:

```
$ cat /etc/subuid
bun:100000:65536
z:165536:65536
```

Allocation is sequential (each user gets the next free `COUNT`-sized block), so on a busy multi-tenant machine the blocks tell you creation order more reliably than UIDs do.

### The -D mode: persistence, not enforcement

`useradd -D` with no options is read-only. With `-b`, `-e`, `-f`, or `-g`, it writes the corresponding key back to `/etc/default/useradd` (`HOME`, `EXPIRE`, `INACTIVE`, `GROUP`), making it the *future* default. Two consequences worth internalizing:

- `-D` has no effect on accounts that already exist, and passing `-D` together with `LOGIN` is an error. It configures the factory, not the product.
- The settable keys are the four the man page documents (`-b`, `-e`, `-f`, `-g`); current shadow also accepts `-s`, but `SKEL=` and `CREATE_MAIL_SPOOL=` remain file-edit only in every version.

## Options That Matter

### Account shape

| Option | Effect |
| --- | --- |
| -c COMMENT | GECOS full-name/comment field (commas and colons are trouble; see chfn) |
| -d HOME_DIR | absolute home path (implies the path you give; no copy without -m) |
| -m / -M | create / do not create the home directory |
| -k SKEL_DIR | alternate skeleton source (only meaningful with -m) |
| -s SHELL | login shell; written verbatim, not validated against /etc/shells |
| -e EXPIRE_DATE | account expiration, YYYY-MM-DD (or days since epoch); empty = none |

### Identity: UID and GID

| Option | Effect |
| --- | --- |
| -u UID | explicit UID (fails with exit 4 if taken, unless -o) |
| -o | allow duplicate UID (pair with -u) |
| -g GROUP | existing group (name or GID) as primary |
| -N / -U | suppress / force the per-user group |
| -G LIST | comma-separated supplementary groups (must all exist, else exit 6) |
| -K KEY=VALUE | override any /etc/login.defs key for this invocation (e.g. -K UID_MIN=5000) |

### Aging and passwords

| Option | Effect |
| --- | --- |
| -p HASH | crypt(3) hash written straight into /etc/shadow (openssl passwd -6 generates these) |
| -f DAYS | days after password expiry until the account is disabled (-1 = never) |
| -e DATE | account expiration date; enforced by login/SSH regardless of password state |

### System and chroot operation

| Option | Effect |
| --- | --- |
| -r | system account: SYS_UID range, no aging, no home, no subids (4.14+) |
| -R CHROOT_DIR | operate inside a chroot (OS images, recovery) |
| -P PREFIX | use PREFIX/etc files instead of chrooting (cross-distro image building) |
| -Z SEUSER | SELinux user mapping (RHEL-family images) |
| -F | allocate subids even for -r accounts (shadow 4.14+) |

## Usage Patterns

```bash
# Ordinary login account, done the way provisioning scripts should do it
useradd -m -s /bin/bash -c "Ann Doe" ann
passwd ann                     # the '!' lock stays until a password is set
```

```bash
# Daemon account: no home, no aging, no shell, UID from the system range
useradd -r -s /usr/sbin/nologin -c "backup service" svc-backup
```

```bash
# View defaults, then persist a saner default shell for future accounts
useradd -D | grep SHELL
useradd -D -b /export/home
```

```bash
# Account with supplementary groups (both must exist first)
groupadd -f docker && useradd -m -G docker,adm builder
```

```bash
# Pre-encrypt a password in one step (avoids leaving plaintext in shell history)
useradd -m -p "$(openssl passwd -6 'S3cret!')" -s /bin/bash shortlived
```

```bash
# Expire the account on a fixed date (intern, contractor)
useradd -m -e 2025-09-30 -f 7 -c "intern" intern1
```

```bash
# Override login.defs for one call: reserve the 5000+ range for humans
useradd -K UID_MIN=5000 -K UID_MAX=5999 -m proj2
```

```bash
# Pin UID and GID (e.g. to match an NFS server's numeric ownership)
groupadd -g 2100 deploy && useradd -u 2100 -g deploy -m deploy
```

```bash
# Container image build: user inside a chroot, not the running system
useradd -R /mnt/rootfs -r -s /usr/sbin/nologin _nginx
```

```bash
# Non-unique UID: legacy "same account" trick (audit attractor - use sparingly)
useradd -o -u 0 -g 0 -s /bin/bash -c "emergency root alias" rootalt
```

```bash
# Btrfs: home as a subvolume instead of a plain directory (shadow supports it)
useradd -m --btrfs-subvolume-home -s /bin/bash btuser
```

```bash
# Print what a new user would inherit, without creating anything
grep -E '^(PASS_|UID_MIN|SHELL)' /etc/login.defs /etc/default/useradd 2>/dev/null
useradd -D
```

## Nuances and Gotchas

- **No home by default.** On Debian, `useradd bob` creates the passwd/shadow entries but no `/home/bob` and no skel copies. Every tutorial that ends with "user can't even `cd`" skipped `-m`. `adduser` avoids this by making home creation its default.
- **The new account is locked.** Password field is `!`. `su - bob` as root works (no password needed for root via `su`), but SSH and login fail with "Authentication failure" until `passwd bob` runs. This is not a bug and there is no flag to pre-unlock it safely.
- **`-G` must reference existing groups.** A typo in a group list aborts the whole creation with exit 6 — useradd does not create missing groups (that is `groupadd`'s job), and it will not leave a half-built user behind; creation is transactional under the passwd/shadow locks.
- **`-p` wants a crypt hash, not a password.** `useradd -p 'hunter2'` stores the *string* `hunter2` as the hash, which then never matches anything (and lands in shell history). Generate with `openssl passwd -6` or feed plaintext through `chpasswd`.
- **Debian shell default is `/bin/sh`.** People who learned useradd on RHEL (also `/bin/sh` there, but delivered via `adduser` habits) are surprised that `-s` is not optional if they want bash. Set it per call with `-s`, or persist it via `SHELL=` in `/etc/default/useradd` (a plain `KEY=value` file) so every future account inherits it.
- **UID scanning ignores filesystem reality.** Deleting a user and re-adding a different one can reuse the UID while old files still carry the old ownership. Audit with `find / -xdev -uid OLDUID -nouser` before reuse (see `userdel`).
- **`-o` duplicate UIDs** make `ps`, backups, and per-user quota behave in ways no one remembers. It exists for migration corner cases; don't ship it as a design.
- **skel is not copied over an existing directory.** Pre-creating `/home/x` (NFS auto-mount, tmpfiles.d, Ansible `file:`) silently disables skeleton provisioning.
- **System accounts get no subids by default (shadow 4.14+).** If a `--userns`-based daemon account needs to map container roots, add `-F` or write `/etc/subuid` manually.
- **`--badname` exists but is deprecated.** Older shadow allowed relaxable name checks via `--badname`; newer versions warn and it will go away. Names that fail the check are rejected for good reason: tools above the passwd layer assume `[a-z_][a-z0-9_-]*`.
- **login.defs is read at creation time.** Later edits to `PASS_MAX_DAYS` do not retroactively apply — existing shadow entries keep their stored values. Retro-aging a population is a job for `chage -M` in a loop, not for login.defs.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 1 | can't update password file (permission, lock contention) |
| 2 | invalid command syntax |
| 3 | invalid argument to option |
| 4 | UID already in use (and no -o) |
| 6 | specified group doesn't exist |
| 9 | username or group name already in use |
| 10 | can't update group file |
| 12 | can't create home directory (mkdir/copy failed) |
| 14 | can't update SELinux user mapping |

Scripts should treat anything above 0 as abort-and-report; because creation is transactional, a failure leaves the account absent rather than half-present.

## Related Commands

- [`usermod`](./usermod.md) — modify an account after creation (groups, shell, home move, lock).
- [`userdel`](./userdel.md) — the inverse operation, with its own home-directory policy.
- [`passwd`](./passwd.md) — set the password that useradd's `!` lock is waiting for.
- [`chage`](./chage.md) — adjust aging fields useradd seeded from login.defs.
- [`chsh`](./chsh.md) — change the login shell later (with the /etc/shells gate).
- [`gpasswd`](./gpasswd.md) — group membership administration beyond useradd's -G.
- [`expiry`](./expiry.md) — login-time password-expiry enforcement for the accounts created here.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together.
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: What does `useradd -m` actually copy, and from where?

It creates the home directory and copies the contents (including dotfiles) of the skeleton directory — `/etc/skel` by default, overridable with `-k` or `SKEL=` in `/etc/default/useradd`. It then chowns the tree to the new UID:GID and sets the mode from `HOME_MODE` in login.defs (or `0777 & ~UMASK` when HOME_MODE is unset). On Debian the skeleton is typically `.bashrc`, `.profile`, and `.bash_logout`. If the target directory already exists, the copy is skipped entirely — which is why pre-created home directories come up without dotfiles.

### Q: A script ran `useradd svc && useradd -G docker svc` and the second call failed with exit 6. Why?

Exit 6 means "specified group doesn't exist" — `docker` was not present on that host (it is created by the Docker package, not by the base system). useradd never invents groups; the fix is `groupadd -f docker` first, or `useradd -G docker svc` only after the package that owns the group is installed. Interviewers like this one because it tests the boundary between useradd and groupadd responsibilities.

### Q: Why does a freshly useradd'ed account fail SSH login even though you set no password policy at all?

Because useradd writes `!` as the encrypted-password field in `/etc/shadow`, which is the locked state — no hash can ever match. The account exists and owns files, but password authentication is disabled until `passwd LOGIN` installs a real hash (or an SSH key is authorized). This default is deliberate: provisioning can create accounts safely before secrets exist.

### Q: What is different about `-r` beyond "lower UID"?

`-r` selects the UID from `SYS_UID_MIN`-`SYS_UID_MAX` (scanning downward), writes no password-aging fields into `/etc/shadow` so policy expiry can never disable a service account, skips home creation even though the default for normal users requires `-m` explicitly anyway, and (shadow 4.14+) skips subordinate ID allocation unless `-F` is given. The usual companion is `-s /usr/sbin/nologin` plus a locked password, giving an identity that can own files and processes but not interactively log in.

### Q: You need the next 100 accounts to come from UID 5000-5099 without touching global config. How?

Use `-K` overrides per invocation: `useradd -K UID_MIN=5000 -K UID_MAX=5099 -m ...`. `-K` layers any login.defs key over this call only. Alternatively pin each UID with `-u`. What does *not* work is exporting shell variables — useradd reads only login.defs, /etc/default/useradd, and argv.

### Q: `useradd -D -s /usr/bin/zsh` fails or doesn't do what the admin expected. Explain.

`-D` mode only persists `-b`, `-e`, `-f`, and `-g` (HOME, EXPIRE, INACTIVE, GROUP) into `/etc/default/useradd`. Shell, skeleton, and mail spool defaults are edited directly in that file. On older shadow the `-D -s` combination is rejected; on newer ones it may be accepted but `-D` overall still only affects *future* useradd invocations, never existing accounts. Knowing which defaults are file-editable versus flag-persistable is the actual interview point.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/useradd.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
