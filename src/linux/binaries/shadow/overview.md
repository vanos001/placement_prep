# shadow — Collection Overview

The shadow suite owns the account database: everything that creates,
modifies, audits, or retires user and group identities. `useradd`,
`usermod`, `userdel`, `passwd`, `groupadd`, and friends are the binaries
behind every Ansible user module, cloud-init provisioning run, and CI
runner registration. This collection covers them one page at a time; the
hub carries what they share — the four-file database model, the lock
discipline, and the security reasoning that interviews probe.

## The Four-File Model

Almost every page here edits a subset of four flat files, and the
consistency rules between them are the real exam material:

| File | Holds | Edited by |
|---|---|---|
| `/etc/passwd` | Account name, UID, GID, GECOS, home, shell | useradd/usermod/vipw |
| `/etc/shadow` | Password hash, aging fields (since pwconv) | passwd/chage/usermod -e |
| `/etc/group` | Group name, GID, member list | groupadd/groupmod/gpasswd |
| `/etc/gshadow` | Group password, admins (since grpconv) | gpasswd/grpconv |

The split exists because `/etc/passwd` must be world-readable (every tool
maps UIDs to names) while password hashes must not be. `pwconv` moves the
hash into `/etc/shadow` and leaves `x` behind; `grpconv` does the same for
groups. The `*conv`/`*unconv` pairs are therefore the collection's
history lesson — the [pwconv](./pwconv.md) and [pwunconv](./pwunconv.md)
pages walk the byte-level mechanics.

## Locking Discipline

These binaries edit multiple files and must look atomic. Each takes an
exclusive lock (`/etc/passwd.lock`, `.pwd.lock` via lckpwdf, and friends),
which is why two parallel `useradd` runs produce "cannot lock /etc/passwd;
try again later" — and why stale lock files after a crash are a classic
rescue scenario. Never edit these files with a plain editor; use
[vipw](./vipw.md)/`vigr`, which lock and validate, or the suite's own
tools. The [pwck](./pwck.md) and [grpck](./grpck.md) pages document the
consistency checks that catch what a hand edit broke.

## Inventory

### Accounts (9)

| Binary | One-liner | Page |
|---|---|---|
| `useradd` | Create accounts (flagship) | [useradd](./useradd.md) |
| `usermod` | Modify accounts (flagship) | [usermod](./usermod.md) |
| `userdel` | Delete accounts | [userdel](./userdel.md) |
| `passwd` | Change passwords and expiry | [passwd](./passwd.md) |
| `chage` | Aging policy query/edit | [chage](./chage.md) |
| `chfn` | Change GECOS fields | [chfn](./chfn.md) |
| `chsh` | Change login shell | [chsh](./chsh.md) |
| `expiry` | Force password-expiry check | [expiry](./expiry.md) |
| `gpasswd` | Group admin/members/password | [gpasswd](./gpasswd.md) |

### Groups and converters (8)

| Binary | One-liner | Page |
|---|---|---|
| `groupadd` | Create groups | [groupadd](./groupadd.md) |
| `groupdel` | Delete groups | [groupdel](./groupdel.md) |
| `groupmems` | Edit a group's member list | [groupmems](./groupmems.md) |
| `groupmod` | Modify groups | [groupmod](./groupmod.md) |
| `grpck` | Verify group files | [grpck](./grpck.md) |
| `grpconv` | Enable gshadow | [grpconv](./grpconv.md) |
| `grpunconv` | Disable gshadow | [grpunconv](./grpunconv.md) |
| `newusers` | Batch-create from passwd-format input | [newusers](./newusers.md) |

### Verify, convert, subids (6)

| Binary | One-liner | Page |
|---|---|---|
| `pwck` | Verify passwd/shadow files | [pwck](./pwck.md) |
| `pwconv` | Enable shadow passwords | [pwconv](./pwconv.md) |
| `pwunconv` | Disable shadow passwords | [pwunconv](./pwunconv.md) |
| `newuidmap` | Write subordinate UID map | [newuidmap](./newuidmap.md) |
| `newgidmap` | Write subordinate GID map | [newgidmap](./newgidmap.md) |
| `vipw` | Safely edit passwd/shadow (vigr) | [vipw](./vipw.md) |

Session-entry tools that shadow upstream also builds (`login`, `newgrp`,
`sg`, `nologin`, `faillog`, `lastlog`) live in the
[login collection](../login/overview.md) because Debian ships them there.

## Concepts the Pages Share

- **UID/GID selection**: auto-pick from `UID_MIN..UID_MAX` in
  `/etc/login.defs`, downward for `-r` system ranges; collisions and the
  `-o` non-unique escape are covered per page.
- **Aging fields**: `chage` and `passwd -e` map directly onto
  `/etc/shadow` columns (lastchg, min, max, warn, inact, expire) —
  [chage](./chage.md) holds the canonical table.
- **Debian tooling overlay**: `adduser`/`deluser` (the Perl front-ends)
  wrap this suite with policy; the underlying files are identical. Pages
  mention the overlay without depending on it.
- **PAM boundary**: password quality, lockout, and much of the behavior
  interviews attribute to these binaries actually comes from the PAM
  stack (`pam_pwquality`, `pam_faillock`); the [passwd](./passwd.md) page
  marks that boundary precisely.
- **Subordinate IDs**: `newuidmap`/`newgidmap` plus `/etc/subuid` /
  `/etc/subgid` are what let rootless containers map container-root to
  unprivileged host users — the modern reason shadow tooling still grows.

## Reading Order For Interview Prep

1. [useradd](./useradd.md), [usermod](./usermod.md),
   [passwd](./passwd.md) — the daily three, asked about constantly.
2. The four-file model: [pwconv](./pwconv.md), [pwck](./pwck.md),
   [vipw](./vipw.md), [chage](./chage.md).
3. Groups: [gpasswd](./gpasswd.md), [groupmems](./groupmems.md),
   [grpck](./grpck.md).
4. Subids for the container-literate:
   [newuidmap](./newuidmap.md), [newgidmap](./newgidmap.md).

Related depth: [Users & Groups](../../admin/users-groups.md) in the admin
track covers the model itself; this collection is the tooling.

## Interview Questions

### Q: Why does /etc/shadow exist at all?

`/etc/passwd` is world-readable by design — `ls -l`, `id`, and every
getpwnam() caller need it. Storing hashes there gave any local user a
dictionary-attack target. The `pwconv` design moves hashes to a
root-readable `/etc/shadow`, leaves `x` as a placeholder, and adds aging
columns in the same stroke. The [pwconv](./pwconv.md) page walks the
conversion mechanics and why `pwunconv` is almost always the wrong move.

### Q: useradd without -m created no home directory — what happened?

That is documented behavior: `useradd` alone creates the account records
and copies nothing; `-m` (or CREATE_HOME in login.defs, which Debian sets
via the adduser policy layer, not for raw useradd) creates the home and
populates it from `/etc/skel`. The interview point is knowing which layer
supplies the policy — see [useradd](./useradd.md) defaults sections.

### Q: Two cron jobs run useradd concurrently and one fails with a lock message. Diagnose.

The suite serializes on lock files; the failure is the designed
contention path. Check for stale locks if the message persists with no
other process running (`/etc/passwd.lock` and siblings), and re-run
serially. The deeper answer: account edits are multi-file transactions
without a journal, so the lock IS the consistency mechanism —
[Locking Discipline](#locking-discipline) above and the
[vipw](./vipw.md) page cover the recovery steps.

### Q: What are subordinate UIDs for?

Kernel user-namespace mappings allow a process to hold uid 0 *inside* a
namespace while mapping to an unprivileged host uid. `/etc/subuid`
allocates each host user a legal mapping range, and `newuidmap` (setuid
root) is the helper that writes `/proc/<pid>/uid_map` from that policy.
Rootless podman/docker-less container stacks are built on exactly this —
[newuidmap](./newuidmap.md) has the file formats.

## References

- [Source — GitHub](https://github.com/shadow-maint/shadow)
- [Source — Debian sources](https://sources.debian.org/src/shadow/)
- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/passwd/)
