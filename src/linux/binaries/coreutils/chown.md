# chown — change file owner and group

## Overview

`chown` sets the owning user and/or group of files — both halves of the inode's ownership pair in one command. It is the tool of provisioning and migration: handing `/var/www` to `www-data:www-data` after a deploy, fixing the fallout of extracting an archive as root, or re-pointing thousands of files at new numeric IDs after an LDAP cutover. `chgrp` is its group-only sibling; `chmod` then decides what those owners may do.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/chown`, from upstream GNU coreutils. It is POSIX-standardized in its basic form, with GNU adding the reference/from convenience options and the `+ID` disambiguation.

It is often confused with `chgrp` (same syscall, group only), with `chmod` (permissions, not ownership), and with `install -o -g` (which sets ownership at copy time). Its most surprising behavior — silently clearing setuid/setgid bits — is not even chown's decision but the kernel's, and it is the answer to a whole class of "why did my suid binary stop working" questions.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/chown` |
| First appeared / lineage | AT&T Unix (first edition era); GNU coreutils implementation |
| Standards | POSIX.1-2018 (`chown`; `--reference`/`--from`/`+ID` are GNU extensions) |

## Synopsis

```
chown [OPTION]... [OWNER][:[GROUP]] FILE...
chown [OPTION]... --reference=RFILE FILE...
```

The five spellings of `NEW-OWNER`:

```
chown root /u          # owner only, group untouched
chown root:staff /u    # owner and group
chown root: /u         # owner; group -> root's login group
chown :staff /u        # group only (same effect as chgrp)
chown : /u             # nothing changed (legal no-op)
```

`OWNER` and `GROUP` may be names or numeric IDs; a leading `+` forces numeric interpretation. No spaces are allowed inside the spec.

## How It Works

### Who may chown what

chown is a direct call to `chown(2)`/`fchownat(2)`. The kernel's rules: changing the **owner** requires `CAP_CHOWN` — for practical purposes, root. Changing the **group** additionally allows an unprivileged process that owns the file to move it into a group the process is a member of (the same rule `chgrp` lives under). Anything else returns `EPERM`:

```bash
$ chown root report.txt
chown: changing ownership of 'report.txt': Operation not permitted
```

The GNU manual notes the group rule is historically system-dependent, but the membership restriction is what Linux (and POSIX's portable behavior) implement. Note that *group* changes by an ordinary user still succeed only because they do not really transfer anything — you remain the owner.

### The OWNER:GROUP grammar, precisely

| Spec | Effect |
|---|---|
| `user` | Owner set, group unchanged |
| `user:group` | Both set |
| `user:` | Owner set; group set to *user's login group* (from the user database) |
| `:group` | Group only — the chgrp case |
| `:` (or empty) | Nothing changed |

The `user:` form is a small hidden lookup: `chown www-data: f` turns the group into whatever `www-data`'s login group is — usually what you wanted on a web box, occasionally not what you wanted on a system with a differently-named primary group.

A legacy syntax survives: `chown user.group /u` (dot instead of colon). GNU accepts it but warns, and the manual recommends against it because it breaks on usernames containing a dot:

```bash
$ chown z.z /tmp/o1
chown: warning: '.' should be ':': 'z.z'
```

### Numeric IDs and the `+` escape

POSIX requires chown to first try the string as a **name**, and only then as an ID. So on a pathological system where a user *named* `42` exists with UID 1000, `chown 42 f` sets UID 1000. GNU adds a disambiguator: `chown +42 f` forces the string to be read as UID 42, skipping the name database entirely (also a speedup in loops over numeric IDs). The same works for group and for both parts: `chown +0:+0 /some/file`.

### chown clears setuid/setgid — the kernel's doing

A successful ownership change on a regular file strips its setuid and setgid bits. This is policy in `chown(2)`: elevated-execution bits must not survive a transfer of the file to another principal. Verified locally on GNU/Linux:

```bash
$ : > f && chmod 4664 f && stat -c %a f
4664
$ chown z:z f          # identical owner AND group - a no-op change
$ stat -c %a f
664                    # setuid gone anyway
```

Even a chown that changes nothing resets the bits, because coreutils issues the syscall regardless. Consequence for practice: re-owning a tree means re-auditing special bits afterwards (`find ... -perm /6000`).

### Symlinks: dereference by default, lchown for the link

For a symlink named on the command line, chown changes the **referent's** ownership; the link itself (which on Linux has its own uid/gid) keeps its values. `-h`/`--no-dereference` acts on the link instead, via `lchown(2)`. This is why archives and rescue workflows use `chown -hR`: without it, links met in a tree would have their targets' ownership rewritten.

Under `-R`, traversal is governed by the same three flags as chgrp, with **`-P` (no traversal) as the default**: links encountered in the tree are not followed (their own ownership is changed on systems with lchown), `-H` additionally traverses symlinks given as command-line arguments, and `-L` traverses every directory symlink encountered — explicitly documented as a security risk on attacker-writable trees, because your chown can land on an arbitrary target.

```
                CLI arg is symlink     link found inside tree
  -R (-P)       not traversed          not traversed
  -R -H         traversed              not traversed
  -R -L         traversed              traversed (recursive)
```

### --from and the migration race

`--from=OLD-OWNER` changes a file only if its current owner/group matches — the check and the change happen in one call per file. The manual motivates it with UID migrations: the two-step `find / -owner OLDUSER -print0 | xargs -0 chown NEWUSER` has a wide race window between test and change; `find ... -exec chown -h NEWUSER {} \;` narrows it but is slow; the documented recipe is:

```bash
chown -h -R --from=OLDUSER NEWUSER /
```

`--reference=RFILE` copies both owner and group from the reference file (which is always dereferenced), completing the "make this look like that" pair with chmod's own `--reference`.

## Options That Matter

| Option | Effect |
|---|---|
| `-c, --changes` | Report only files whose ownership actually changes |
| `-f, --silent, --quiet` | Suppress most error messages |
| `-v, --verbose` | Diagnostic for every file processed (even retained ones) |
| `-h, --no-dereference` | Change symlinks themselves (uses `lchown`) |
| `--dereference` | Change the referent of each symlink (default) |
| `--from=OLD-OWNER` | Only change files currently owned as specified |
| `--reference=RFILE` | Copy owner and group from RFILE |
| `-R, --recursive` | Recurse into directories |
| `-H` / `-L` / `-P` | Traversal policy for `-R`; **`-P` is chown's default** |
| `--preserve-root` | Refuse to recurse on `/` (not the default for chown) |

## Usage Patterns

```bash
# Hand a web root to the service account, owner and group
sudo chown -R www-data:www-data /var/www/html
```

```bash
# Owner plus its login group in one spec
sudo chown -R postgres: /var/lib/postgresql
```

```bash
# Group-only change through chown (equivalent to chgrp)
sudo chown :developers /srv/code
```

```bash
# Recurse without following symlinks; change links' own ownership too
sudo chown -hR appuser:appgroup /opt/app
```

```bash
# UID migration with a guard: only files still owned by the old UID
sudo chown -hR --from=olduser newuser: /home
```

```bash
# Make a file's ownership match a known-good one
sudo chown --reference=/etc/passwd /var/secret/file
```

```bash
# Force numeric interpretation (no name lookups, no 'named 1000' traps)
sudo chown +1000:+1000 /mnt/vol/data
```

```bash
# Audit what changed during a big recursive run
sudo chown -Rc www-data: /var/www | wc -l
```

```bash
# In cron: silence expected EPERM noise from foreign-owned stragglers
chown -f app:app /var/tmp/queue/* 2>/dev/null || true
```

```bash
# Restore ownership of a bind-mounted volume's contents
docker run --rm -v site:/data alpine chown -R 33:33 /data
```

```bash
# Fix ownership of links without touching shared targets
sudo chown -h deploy /srv/releases/current
```

```bash
# Check the result: owner, group, and mode in one line
stat -c '%U:%G %a %n' /var/www/html/index.html
```

## Nuances and Gotchas

- **chown clears setuid/setgid on regular files — even a no-op chown does.** The syscall is issued regardless of whether values change (verified above). Any script that re-owns a tree silently disarms suid binaries; audit with `find -perm /6000` and re-set bits deliberately.
- **`user:` uses the user's *login* group**, which is a database lookup at chown time — on systems where `www-data`'s primary group is not what you assume, `chown www-data:` lands somewhere unexpected. Spell `user:group` when it matters.
- **The dot separator is deprecated and warned about**: `chown user.group f` works on GNU but fails on other systems and misparses usernames containing dots. Always `user:group`.
- **`chown 1000 f` is a name lookup first.** If a user literally named `1000` exists, you get *their* UID. Use `+1000` to force the ID (GNU extension; not portable).
- **Non-root chown of the owner always fails** — there is no "give my file away" even to a group you belong to; only the group half is user-movable, and only into your own groups (`Operation not permitted` otherwise).
- **Hard links share one inode**, so chowning any link changes ownership for all of them; there is no per-link ownership. Do not "fix" one link and expect the others to differ.
- **`-R` with dereferencing is a documented escalation risk** on trees others can write: an attacker can swap in symlinks mid-traversal and receive your (root) chown on arbitrary targets. Keep the `-P` default, or use `find -xdev -type f -exec chown` for belt-and-braces control.
- **`--preserve-root` is not the default** for chown (unlike rm). `chown -R user /` from a root shell is a system-relabeling event with no undo. Alias it in for interactive shells.
- **Filesystems without Unix ownership** (vfat, exFAT, some network mounts) reject chown outright or fake it in the driver; the error appears even as root, and `stat` may show a fabricated owner.
- **`-v` prints "retained" lines even when `--from` skips a file** — verbose means "every operand processed", so grep for `changed`/`failed` when scripting an audit, or use `-c`.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All operands processed successfully |
| nonzero (1 in practice) | Bad owner spec, nonexistent operand, `EPERM`, or any per-file failure; remaining operands are still processed |

## Related Commands

- [`chgrp`](./chgrp.md) — the group-only spelling of `chown :group`.
- [`chmod`](./chmod.md) — sets the permission bits that owner/group/others map onto; clears/keeps special bits in its own documented way.
- [`chcon`](./chcon.md) — SELinux context: a third ownership-like attribute on the same files.
- [`stat`](./stat.md) — reads owner/group back (`%U`, `%G`, `%u`, `%g`) in parseable formats.
- [`groups`](./groups.md) — shows the memberships that gate unprivileged group changes.
- [`install`](./install.md) — copies with `-o user -g group -m mode` applied atomically at create time.
- [`../../admin/users-groups.md`](../../admin/users-groups.md) — users, groups, and where IDs come from.
- [`../../admin/permissions.md`](../../admin/permissions.md) — the ownership/permission model in full.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Walk through what `chown www-data: file` does versus `chown www-data file`.

`chown www-data file` changes only the owner; the group stays as-is. `chown www-data:` additionally sets the group to www-data's **login (primary) group** as recorded in the user database at the moment of the call. Both are single `chown(2)` calls; the trailing colon is just grammar for "and the login group". The trap: the login group is looked up by name at chown time, so on an unusual system it may not be the group you assumed — spell `www-data:www-data` in anything long-lived.

### Q: Why does chown clear the setuid bit, and is there any way to chown without losing it?

The kernel strips setuid/setgid from regular files on any successful ownership change: the bits exist to let a process run as the *file's* owner/group, and after a chown that principal is a different one — keeping the bits would silently extend trust to whoever now owns the file. There is no userspace flag to preserve them; even a chown that sets the same owner/group clears them because the syscall is issued anyway. The workflow is: chown first, then re-apply special bits with chmod.

### Q: A script does `find / -owner 1001 -print0 | xargs -0 chown 1002`. What is wrong with it?

Three things. First, it is racy: between find's test and chown's change, files can change hands, and the wide window is exactly what `chown --from=1001 1002` was added to shrink — check and change in one syscall per file. Second, `chown 1002` performs a name lookup first (POSIX order), so on a system with a user named "1002" it re-points at that user's real UID; `chown +1002` forces the numeric ID. Third, recursing on `/` needs traversal hygiene (`-h` so symlinks are changed themselves, not followed; `--preserve-root` as a seatbelt).

### Q: What do `-H`, `-L`, and `-P` do during `chown -R`, and which is the default?

They are mutually exclusive traversal policies, last-one-wins, with `-P` the default for chown/chgrp. `-P` never traverses symlinks: links met in the tree have their *own* ownership changed (via lchown) but targets are untouched. `-H` additionally descends through directory symlinks that appear as explicit command-line arguments. `-L` descends through every directory symlink encountered, recursively — documented as a security risk because, on a tree others can write, your root chown can be steered to arbitrary targets. Note chmod's `-R` defaults to `-H` instead, since chmod cannot touch links anyway.

### Q: Can a regular user ever change file ownership?

Only half. Changing the owner requires `CAP_CHOWN` (root). A regular user who owns a file may change its **group**, but only to a group they are a member of — POSIX calls the stricter behaviors system-dependent, but Linux implements the membership rule. So `chown :staff myownfile` works for a staff member, `chown otheruser myownfile` never does, and "giving the file away" is a root operation by design.

### Q: What does `chown -R` do to symlinks by default, and why do rescue scripts add `-h`?

By default (`-P`), symlinks encountered in the tree are not traversed, and on Linux coreutils changes the links' own ownership rather than their targets'. That is usually what a rescue or archive-restore wants, so `-h` is added mainly for the command-line-argument case: a bare `chown -R user link-to-dir` without `-H` will not descend the target directory, and `chown -h user link` relabels the link itself. The combination `chown -hR` is the belt-and-braces spelling: links are ownership-stamped, trees are traversed physically, and nothing behind a symlink gets surprises.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/chown.1.en.html)
