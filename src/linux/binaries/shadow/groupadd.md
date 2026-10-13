# groupadd — create a new group (shadow low level)

## Overview

`groupadd` is the shadow suite's low-level group creation tool. It appends one entry to `/etc/group` and — when the system uses shadowed groups, i.e. `/etc/gshadow` exists — a matching locked entry there. It ships in the `passwd` package (Debian's binary package for the upstream shadow suite) and lives in `/usr/sbin/groupadd`: an administrator tool, not something an ordinary user runs. Nothing else on a Debian system creates groups directly — `adduser` and `useradd` call into the same machinery — so `groupadd` is the atom from which every group on the box was made.

`groupadd` is often confused with `useradd`'s implicit group creation (with `USERGROUPS_ENAB yes`, `useradd -m bob` creates a namesake group `bob` behind the scenes), with `adduser` (Debian's interactive front end, which also picks GIDs but adds home directories and prompts), and with `gpasswd` (which administers an existing group's members and password rather than creating one). In provisioning scripts you reach for `groupadd` when a package or policy expects a named group to exist before users are placed into it.

| Field | Value |
| --- | --- |
| Package | passwd (Debian bookworm; source package `shadow`, upstream "shadow suite") |
| Man section | 8 |
| Path | /usr/sbin/groupadd |
| First appeared | System V lineage; shadow suite (Julianne F. Haugh, 1988+), now maintained by shadow-maint |
| Standards | Not POSIX; specified by LSB. GID selection configured via /etc/login.defs |

## Synopsis

```
groupadd [options] GROUP
```

Common one-line forms:

```
groupadd deploy                        # next free GID >= GID_MIN
groupadd -r dockersvc                  # system group, SYS_GID range
groupadd -g 2100 deploy                # pin the GID
groupadd -f -r _prom                   # idempotent: no-op if it exists
```

## How It Works

### GID selection

With no `-g`, groupadd scans for the smallest GID that is both `>= GID_MIN` and greater than every GID currently in use — not "first free hole", but "one past the highest occupied" within the range. With `-r`, the search moves to the system range `SYS_GID_MIN`–`SYS_GID_MAX` and scans *downward* from `SYS_GID_MAX` (defaults 101–`GID_MIN-1`, so usually 101–999). Demonstrated against a scratch tree (shadow writes the group with `x` in the group file and a locked `!` in gshadow):

```
$ tail -3 /tmp/lab/etc/group       # before: highest GID is 100
users:x:100:
$ groupadd -P /tmp/lab teamA
$ tail -2 /tmp/lab/etc/group
users:x:100:
teamA:x:1000:                      # smallest >= GID_MIN(1000), above all
$ groupadd -P /tmp/lab -r syssvc && groupadd -P /tmp/lab -r syssvc2
$ tail -2 /tmp/lab/etc/group
syssvc:x:999:
syssvc2:x:998:                     # system range, allocated downward
```

The decision flow, including how `-f` and `-o` perturb it:

```
                pick GID for GROUP
                        |
        +---------------+----------------+
        | -g GID given   | no -g          |
        | use GID as-is  | -r ? SYS range | normal GID_MIN..GID_MAX
        |                | scan downward  | smallest >= GID_MIN > all used
        +-------+--------+----------------+
                |
        GID already used?  --no--> write /etc/group + /etc/gshadow
                |                       (password 'x' / '!')
        -o given? --yes--> write anyway (alias GID)
                |
        -f given? --yes--> ignore -g, pick next free GID instead
                |
                no --> exit 4 "GID 'N' already exists"
```

### What gets written

One invocation writes both databases (groupadd holds the usual shadow locks while doing so):

```
/etc/group    deploy:x:2100:            # name:passwd:GID:members
/etc/gshadow  deploy:!::                # name:passwd:admins:members
```

The `x` in `/etc/group` is a placeholder meaning "real password lives in /etc/gshadow"; the `!` in `/etc/gshadow` is the locked-password state. With no group password set — the overwhelmingly common case — a `!` is all you will ever see. Members passed with `-U` (recent shadow) land in the member list of both files.

### Name rules

From the man page: groupnames may contain lower- and uppercase letters, digits, underscores, or dashes; may end with a dollar sign; dashes may not start the name; fully numeric names and the names `.` or `..` are disallowed; maximum 32 characters. Invalid names fail before anything is touched:

```
$ groupadd '9bad*'
groupadd: '9bad*' is not a valid group name      # exit 3
```

The same validation is *not* consistently applied by `groupmod -n` — see that page's gotchas.

### Configuration knobs

`GID_MIN`, `GID_MAX`, `SYS_GID_MIN`, `SYS_GID_MAX` come from `/etc/login.defs` and can be overridden per invocation with `-K`. `MAX_MEMBERS_PER_GROUP` (default 0 = unlimited) makes the shadow tools split long member lists across repeated lines with the same name/GID — a NIS legacy you should leave at 0 unless you serve NIS.

### Locking and concurrency

Like the rest of the suite, groupadd takes `/etc/group.lock`/`/etc/gshadow.lock` (and `passwd`/`shadow` locks) around the update. A concurrent `useradd`/`gpasswd` shows up as `cannot lock /etc/group; try again later.` — a retryable condition, not a corruption. Runaway locks (killed processes leaving stale `.lock` files) are the usual cause of "try again later" that never clears; removing the stale lock files as root is the fix. Non-root invocations fail the same way with `Permission denied.` first, because they cannot create the lock files at all.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-g GID` | Pin the numeric GID; must be unique unless `-o`. Non-negative decimal only |
| `-r` | System group: allocate from `SYS_GID_MIN`–`SYS_GID_MAX`, downward from `SYS_GID_MAX` |
| `-f` | Idempotence: exit 0 if the group exists; with `-g`, fall back to auto-GID instead of failing |
| `-o` | Allow a duplicate GID (alias). Name must still be unique |
| `-K KEY=VALUE` | Override one login.defs key for this call (repeatable); `-K GID_MIN=10,GID_MAX=499` does NOT work |
| `-p HASH` | Pre-set an encrypted group password (crypt(3) output). Rarely wanted; leaks via `ps` |
| `-U USERS` | Comma-separated initial members (shadow 4.16+; absent in Debian bookworm's groupadd) |
| `-R DIR` | Chroot into DIR and operate on its /etc files (image building) |
| `-P DIR` | Prefix mode: edit DIR/etc/* without chroot (cross-compilation staging) |

## Usage Patterns

```bash
# Plain project group at the next free GID
groupadd deploy
```

```bash
# Service group at a pinned GID, so the same GID exists on every host
# (NFS-exported or rsynced trees carry numeric ownership)
groupadd -g 2100 deploy
```

```bash
# System group for a daemon; lands in 101-999, below human groups
groupadd -r dockersvc
```

```bash
# Idempotent provisioning: safe to re-run in Ansible/cloud-init
groupadd -f docker && useradd -G docker builder
```

```bash
# -f also rescues a colliding -g: picks the next free GID instead of dying
groupadd -f -g 2100 deploy     # exit 0 even if 2100 or 'deploy' was taken
```

```bash
# Deliberate duplicate GID: "same rights as" alias group
groupadd -o -g 100 alias100
```

```bash
# Reserve the 5000-5999 band for project groups, one call only
groupadd -K GID_MIN=5000 -K GID_MAX=5999 proj7
```

```bash
# Pre-set a group password from a precomputed hash (see gotchas before using)
groupadd -p "$(openssl passwd -6 'grouppass')" consultants
```

```bash
# Seed members at creation time (recent shadow; otherwise use gpasswd/usermod)
groupadd -U alice,bob qa
```

```bash
# Container image build: create the group inside the staging root
groupadd -R /mnt/rootfs -r _nginx
```

```bash
# Cross-compile staging tree: edit /target/etc/group without chroot
groupadd -P /target build
```

```bash
# Before/after check in scripts: verify with getent, not by grepping blindly
groupadd -f deploy && getent group deploy || echo "creation failed"
```

```bash
# Group for a package's postinst to consume (same pattern packages use)
getent group _mqtt >/dev/null || groupadd -r _mqtt
```

```bash
# Audit what the next auto GID would be without creating anything
getent group | awk -F: '$3 >= 1000 {if ($3 > max) max = $3} END {print max + 1}'
```

## Nuances and Gotchas

- **`-f` silently changes meaning under conflict.** `groupadd -f -g 2100 x` does not fail if 2100 is taken — it discards your `-g` and picks another GID. In strict provisioning where the GID must match other hosts, that silent fallback is worse than the failure; use plain `-g` and handle exit 4 yourself.
- **Exit 4 vs exit 9.** GID collision is 4, name collision is 9 (`groupadd: group 'teamA' already exists`). Scripts that test only "nonzero" cannot distinguish "rename your group" from "pick another GID".
- **`-o` aliases confuse humans, not the kernel.** File ownership and access checks are numeric; after `groupadd -o -g 100 alias100`, `ls -l` shows `users` on alias-owned files. Permission audits and `getent group 100`-based tooling get ambiguous. It exists for migration/SMB corner cases, not as a design.
- **`-p` puts the hash on the process list.** Every user can read `/proc/*/cmdline` while groupadd runs. Prefer creating locked (the default `!`) and setting a password later via `gpasswd` if you truly need group passwords — which you usually do not (see gpasswd).
- **Group passwords are a museum piece.** The password field gates `newgrp` joins by non-members. Modern practice leaves it locked (`!`) and manages access purely by membership; a `-p`ed group password becomes a crackable hash sitting in gshadow.
- **32-character limit and no leading dash.** The checks are enforced here but `groupmod -n` renames have historically bypassed re-validation; never rely on groupmod to sanitize a name.
- **`GID_MIN`-`GID_MAX` exhaustion.** A cluttered system with tens of thousands of groups can push "one past the highest used" beyond `GID_MAX` (default 60000); allocation then fails with an update error. Prune stale groups or widen the range via `-K`.
- **-P mode checks conflicts against the host database.** In prefix mode the GID/name uniqueness probes resolve via the host's NSS (the man page's caveat: NIS/LDAP not verified), so a GID free on the host but taken in the prefix tree may produce inconsistent results. Treat `-P` output as staging, not truth.
- **`-K KEY=V1,KEY=V2` is not parsed.** The man page notes `-K GID_MIN=10,GID_MAX=499` does not work — pass separate `-K` flags.
- **Split groups (`MAX_MEMBERS_PER_GROUP`) are half-supported.** Even some shadow tools mishandle repeated same-GID lines; leave the default 0 alone.
- **`groupadd` knows nothing about directories.** A setgid directory for the new group is a separate `mkdir` + `chmod g+s` + `chgrp` step; people who expect a work area to materialize are thinking of a different tool's policy layer (`adduser`-style defaults simply do not exist here).
- **Trailing `$` is legal (Samba legacy).** Machine account names like `win10$` pass validation because they may end with a dollar sign — don't "fix" them, but do remember shell quoting: `groupadd 'host$'` needs the quotes or the shell eats the `$`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | success |
| 2 | invalid command syntax |
| 3 | invalid argument to option (includes invalid group name) |
| 4 | GID already in use (called without `-o`) |
| 9 | group name already in use |
| 10 | can't update group file (lock failure, permission, corrupted db) |

Creation is transactional under the shadow locks: a failure leaves no half-written group behind.

## Related Commands

- [`groupmod`](./groupmod.md) — rename or re-GID the group this command created.
- [`groupdel`](./groupdel.md) — remove it again; refuses a group that is somebody's primary.
- [`groupmems`](./groupmems.md) — edit the member list without touching GID or name.
- [`gpasswd`](./gpasswd.md) — group passwords, administrators, and day-to-day membership.
- [`useradd`](./useradd.md) — creates a namesake group implicitly under USERGROUPS_ENAB.
- [`grpck`](./grpck.md) — verifies the files groupadd writes; run it if anything looks off.
- [overview](./overview.md) — the shadow suite collection: how these tools fit together.
- [users-groups](../../admin/users-groups.md) — the admin-side model of users, groups, and /etc files.

## Interview Questions

### Q: Without `-g`, what GID does `groupadd` pick, and is it "first free"?

It picks the smallest GID that is `>= GID_MIN` and greater than *every* GID in use — so on a system whose highest group is 1001 the next group gets 1002 even if 537 is free. "First free hole" would reuse deleted GIDs and silently re-grant file access to whichever new group inherits the number, so the one-past-the-top rule is a safety property. System groups with `-r` behave the opposite way, scanning downward from `SYS_GID_MAX` to keep service GIDs in the low band.

### Q: What is the difference between `groupadd -f` and `groupadd -o`?

They defuse two different collisions. `-f` is about *name* collisions and idempotence: if the group exists, exit 0 without changing anything, and if a supplied `-g` collides, abandon it and auto-pick instead of failing. `-o` is about *GID* collisions: with `-o -g N` the tool creates a second group sharing GID N. You often want `-f` in scripts and almost never want `-o` — duplicate GIDs make numeric ownership ambiguous for tools and auditors.

### Q: A runbook does `groupadd -g 2100 deploy` on every host. Why pin the GID, and what breaks if you don't?

Files carry numeric GIDs, not names. If `deploy` is GID 2100 on the file server but GID 2107 on a client, a setgid or group-writable tree copied/rsynced between them grants `deploy` rights to whatever group happens to hold the number on the other side. Pinning (with a documented range, e.g. via `-K GID_MIN=...`) keeps numeric ownership meaningful across machines — the same argument as pinning service UIDs.

### Q: Where does the group password actually live, and why do fresh groups show `!`?

When `/etc/gshadow` exists, groupadd writes `x` into the password field of the `/etc/group` entry — a placeholder meaning "see the shadow file" — and `!` (locked) into `/etc/gshadow`'s password field. `!` can never match a crypt(3) result, so `newgrp` password joins are impossible until an admin explicitly sets one with `gpasswd`. That default is deliberate: group passwords are a legacy `newgrp` feature and a standing crack target; membership should be managed by tools, not shared secrets.

### Q: Your Ansible task `groupadd docker` fails on re-run with exit 9. Fix it properly.

Exit 9 is "group name already in use". The fix is `groupadd -f docker` (or `ansible.builtin.group` with `state: present`, which does the existence check for you). Note the asymmetry: `-f` makes the *name* check idempotent, but if the task also pinned `-g` and another group owns that GID, you still get exit 4 — in that case the runbook and reality disagree about GIDs, and the right response is to investigate, not to force.

### Q: What locks does groupadd take, and what does a stale lock look like?

It takes the shared shadow locks (`/etc/group.lock`, `/etc/gshadow.lock`, plus the passwd/shadow pair) for the duration of the update, so concurrent group- or user-creating jobs serialize instead of racing. A killed groupadd can leave the `.lock` files behind; subsequent runs then fail with `cannot lock /etc/group; try again later.` forever. The remedy is to verify no group tool is actually running (`pgrep -a 'user|group|gpasswd|newusers'`), then remove the stale lock files as root. Because the failure mode is retryable, wrapping provisioning in a short retry loop for exit 10 is reasonable.

### Q: Which files does `groupadd` touch, and what are the two password-field conventions?

Two files: `/etc/group` (`name:x:GID:members`) and `/etc/gshadow` (`name:!:admins:members`). The `x` in the group file is the placeholder telling NSS that the real (locked) password state is in gshadow, which is mode 0640 root:shadow so ordinary users cannot even see group password hashes. If the two files disagree — a group in one but not the other, or a non-`x` password beside a gshadow entry — that is drift, and `grpck` is the tool that reports (and interactively offers to fix) it.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/groupadd.8.en.html)
- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
