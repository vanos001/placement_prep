# namei — follow a pathname and show every component

## Overview

`namei` walks a pathname exactly the way the kernel's path resolver does — component by component, following symlinks — and prints each component it encounters along with its type and (optionally) its permissions. The name comes from the classic kernel-internal function `namei` ("name to inode"). It ships in the `util-linux` package at `/usr/bin/namei` and exists for one dominant purpose: answering *"why can't I open this path?"* by exposing the permission bits and symlink hops of **every** directory on the way, not just the final file.

It is often confused with `ls -l` on the final component (which hides the directories that actually denied access), with `readlink -f` (which resolves to the endpoint but shows nothing about permissions or mount boundaries), and with `stat` (one inode, no walk). When an application fails with `EACCES` on a path that "looks fine", `namei -l` shows the whole chain in one shot.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/namei |
| First appeared | early-1990s Unix freeware; part of util-linux since the 2.x era |
| Standards | Not POSIX; util-linux extension |

## Synopsis

```
namei [options] <pathname>...
```

Main one-line forms:

```
namei /usr/bin/cc                 # show the full resolution chain
namei -l /etc/nginx/nginx.conf    # chain + mode bits + owner/group
namei -x /proc/1/status           # mark mountpoints with D
namei -n /bin/sh                  # do not follow symlinks
```

## How It Works

### The walk

For each operand, `namei` starts at `/`, resolves one component at a time, and indents output to visualize descent. Each line carries a type character in the first column:

```
f   the pathname being followed (header line)
d   directory
l   symbolic link (followed; the link target follows as a child line)
-   anything else (regular file, device, socket, fifo)
D   mountpoint directory (only with -x)
?   unresolvable (permission denied / missing component)
```

Recent util-linux refines that catch-all `-`: the man page also documents `s` (socket), `b` (block device), `c` (character device), and `p` (FIFO) as distinct type characters, so scripts keying on `-` to mean "regular file" are version-sensitive. Errors do not abort the walk: an unresolvable component prints with a `?` and the errno text inline (namei appends e.g. `- No such file or directory` to the offending line), and it prints an informative message if the walk exceeds the kernel's symlink limit (`ELOOP`, 40 hops) — one of the "too many levels of symbolic links" debug aids the tool was written for.

Real output (Debian merged-/usr system):

```
$ namei /bin/sh
f: /bin/sh
 d /
 l bin -> usr/bin
   d usr
   d bin
 l sh -> dash
   - dash
```

Read it top-down: `/` is a directory, `bin` is a symlink to `usr/bin` (so the walk descends into `usr`, then `bin`), then `sh` is a symlink to `dash`, a regular file. This is precisely the sequence of lookups the kernel performed, which makes `namei` the cheapest possible path-resolution debugger.

### Permission display

`-l` prints `ls -l`-style modes plus owner and group for every component; `-m` prints just the mode bits; recent releases add `-o` (owners), `-v` (vertical alignment) and `-Z` (SELinux context). This is the permission debugging form:

```
$ namei -l /etc/hosts
f: /etc/hosts
drwxr-xr-x root root /
drwxr-xr-x root root etc
-rw-r--r-- root root hosts
```

For an `EACCES` diagnosis, scan for a component where the *traversing user* lacks execute (`x`) on a directory or read on the final file. Remember that a directory needs `x` (search), not `r`, to pass through — `namei -m` makes that immediately visible.

### A worked access-debugging scenario

An app user cannot read `/srv/app/shared/config.yml`; `ls -l` on the file says `-rw-r--r--`. The walk shows where it actually breaks (component shapes illustrative):

```
$ namei -l /srv/app/shared/config.yml
f: /srv/app/shared/config.yml
drwxr-xr-x root  root  /        # fine
 drwxr-xr-x root  root  srv       # fine
 drwx------ root  root  app       # ← the culprit: no x/o for appuser
 drwxr-xr-x app   app   shared    # never reached
 -rw-r--r-- app   app   config.yml
```

One line, the whole answer — versus five `ls -ld` calls in the right order. The same session catches the subtler variant: a directory with `r` but no `x` (listing works, traversal fails), which looks healthy in casual `ls` output.

### Newer-release flags

Recent util-linux versions split the long listing into `-o/--owners` (owner/group only), `-v/--vertical` (aligned columns), and `-Z/--context` (SELinux contexts). Debian bookworm's `namei(1)` documents `-l`, `-m`, `-x`, `-n` — treat the others as version-dependent sugar.

### Mount boundaries

With `-x`, mountpoints are marked `D`, letting you see where a path crosses filesystems:

```
$ namei -x /proc/1/status
f: /proc/1/status
 D /
 D proc
 d 1
 - status
```

### Link handling

By default every symlink is followed recursively — including symlinks found *inside* a symlink target's directory, and distro chains like `/bin → usr/bin`. `-n` (`--nosymlinks`) stops after printing the literal path components as given. Broken symlinks and missing components are reported in place rather than aborting the walk, so you still see how far resolution got.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-l`, `--long` | Long listing: mode bits + owner/group for each component (`-m -o -v`) |
| `-m`, `--modes` | Show mode bits (`rwx` groups) for each component |
| `-x`, `--mountpoints` | Show mountpoint directories with a `D` |
| `-n`, `--nosymlinks` | Do not follow symlinks; show the literal path |
| `-o`, `--owners` | Owner and group per component (newer releases) |
| `-v`, `--vertical` | Vertical alignment of modes/owners columns (newer releases) |
| `-Z`, `--context` | SELinux security context per component (newer releases) |
| `-h` / `-V` | Help / version |

## Usage Patterns

```bash
# Diagnose EACCES: which component denies access to user www-data?
sudo -u www-data namei -l /srv/app/shared/config.yml
```

```bash
# Understand a distro symlink maze (/bin is /usr/bin here)
namei /usr/bin/awk
```

```bash
# Show only modes — scan quickly for a directory missing the x bit
namei -m /opt/vendor/tool/bin/run.sh
```

```bash
# See where a path crosses filesystems (mount boundaries)
namei -x /var/lib/docker/overlay2/xxx/diff
```

```bash
# Literal view: what is the raw path without link chasing?
namei -n /etc/alternatives/cc
```

```bash
# Multiple paths in one run
namei /var/log/syslog /var/log/auth.log
```

```bash
# Pre-flight check before bind-mounting a file into a container
namei -l /etc/resolv.conf
```

```bash
# Scripted sanity check: fail if the final component is not reachable
namei -l "$path" | tail -1 | grep -q '^-' || echo "not a regular file: $path"
```

```bash
# Assert the path contains no symlinks (security-sensitive config load)
[ -z "$(namei -n "$path" | awk '$1=="l"')" ] || echo "unexpected symlink in $path"
```

```bash
# Document a container image's layout quirks in CI logs
namei -l /usr/bin/python3
```

```bash
# Check every component as the service user before a drop-privileges daemon starts
sudo -u appuser namei -m /var/lib/app/socket
```

```bash
# Combined view: modes + owners + mount boundaries in one pass
namei -lx /etc/systemd/system/multi-user.target.wants/nginx.service
```

```bash
# Literal skeleton of a deep alternatives/nix-style chain (no link chasing)
namei -n /etc/alternatives/editor
```

## Nuances and Gotchas

- **`namei` shows mode bits, not the full access decision.** POSIX ACLs, capabilities, LSM rules (SELinux/AppArmor), and mount flags like `noexec` or `ro` are invisible — a path can be world-executable in `namei -m` yet still deny access. Treat output as *necessary* conditions, not sufficient ones.
- **It is a snapshot, not the kernel's trace.** Between your `namei` run and the failing program's call, permissions or symlinks can change (TOCTOU). For reliable reproduction, run as the same user with the same environment.
- **Symlink chains recurse fully.** On deep chains (alternatives systems, usrmerge, nix-style stores) the tree grows fast; `-n` gives you the literal skeleton when the full walk is noise.
- **Type `-` covers everything that is not a directory or link** — devices, sockets, FIFOs. Don't read it as "regular file" without `-l`, which lets you see the actual mode character.
- **Relative operands are shown as given.** `namei ../data` walks from the *literal* components; the kernel would resolve `..` against your cwd — quote full paths in scripts to keep the picture honest.
- **Owner/group are names, resolved from your namespace's user database.** Inside containers or with LDAP-managed users, names can fail to resolve even though the numeric IDs are fine.
- **Not a substitute for strace.** When you need the *exact* syscalls and returned errors, `strace -e trace=%file openat...` beats reconstruction; `namei` is the fast visual pre-diagnosis.
- **It can trigger automounts.** Walking through an autofs mountpoint performs lookups on it, which may fire a mount (and a hang if the server is slow). On hosts with aggressive autofs maps, prefer `-n` or resolve the path on the server side.
- **The `-m` modes compress special bits.** Sticky/setgid directories show as `t`/`s` in the mode string exactly like `ls`; if you are scripting on mode letters, parse the first column (`d`/`l`/`-`) and the mode triplet separately.
- **Missing components still exit 1 — and the walk continues.** A broken path yields inline `?` lines with the errno text but no abort, and the exit status is nonzero even though namei "did its job". Scripts must therefore test exit codes for path validity, not for tool failure, and must not treat stderr noise as a crash.
- **In `-x` mode the `D` leaks into the mode string too.** With `-lx`, a mountpoint root renders as `Drwxr-xr-x` — parse the first character with that in mind rather than assuming a bare `d`.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All paths followed successfully |
| 1 | Error: an operand could not be resolved, or usage error |

## Related Commands

- [`permissions`](../../admin/permissions.md) — the mode-bit and traversal model `namei` displays.
- [`find`](../../shell/find.md) — `-L`/`-xtype` for scanning trees *containing* broken symlinks at scale.
- [`mountpoint`](./mountpoint.md) — precise mountpoint testing with exit codes (namei `-x` is the visual cousin).
- [`overview`](./overview.md) — hub page of the util-linux collection.

## Interview Questions

### Q: A process gets EACCES opening /srv/app/config.yml, but ls -l shows it world-readable. How does namei help?

`ls -l` inspected only the final component; access requires search (`x`) permission on *every* directory along the way. `namei -l /srv/app/config.yml` prints each component's modes and owners, so a `drwx------ root root srv` or a missing `x` bit anywhere in the chain becomes obvious immediately. It replaces five or six manual `ls -ld` calls with one command and the same ordering the kernel used.

### Q: What is the kernel's namei-style resolution actually doing, and what does the tool abstract away?

The kernel resolves a path by looking up components one at a time in dentry/inode caches, following symlinks by prepending their targets (with `ELOOP` protection at 40 hops), and checking execute permission on each directory traversal. `namei` re-implements that walk in userspace and prints it. What it abstracts away: dentry caching, automount triggers, LSM hooks, and ACL evaluation — all reasons its "yes" is necessary but not sufficient.

### Q: How would you find whether a path crosses a filesystem boundary, and why would you care?

`namei -x` marks mountpoint components with `D`, or compare `df`/`findmnt` for the path. It matters because behaviors differ across the boundary: quotas, `ro`/`noexec`/`nosuid` mount flags, snapshots, backup coverage, and permission semantics (root-squash on NFS). Debugging "the same file is writable here and not there" is frequently a mount-flag question, and `-x` shows you where the flags start applying.

### Q: When would you prefer `readlink -f`, `namei`, and `strace` over each other?

`readlink -f` answers "where does this link chain end?" — endpoint only, no metadata. `namei` answers "what does resolution look like, and what permissions sit on each hop?" — the debugging view. `strace` answers "what did this specific process actually attempt, and what did the kernel return?" — ground truth including races, automounts, and failures namei cannot see. Escalate in that order when a path problem resists the cheaper tool.

### Q: Why does a directory need execute (x) permission for a path to work, and how does namei expose that?

For directories, `r` grants listing names and `x` grants *traversal* — the ability for the kernel to resolve inodes of entries within. A directory with `r--` can be listed but not traversed, so every file inside fails with EACCES even though `ls` appears to work; a directory with `--x` is invisible to listing but reachable if you know the exact name. `namei -m` prints each component's mode triplet, so a missing `x` anywhere on the chain is visible as a column scan — the single most common real-world hit in permission debugging sessions.

### Q: How does namei behave at a path that is broken mid-chain versus one that fails on the last component, and why does that matter for scripting?

Both produce inline `?`-marked lines with the errno text and exit status 1; the walk itself does not stop, so you still see every resolvable prefix. That asymmetry (no abort, nonzero exit) makes namei usable as a *path validator* in scripts — `namei -l "$p" >/dev/null 2>&1 || handle_broken "$p"` — while the printed chain tells the operator exactly where the break is. It also means namei is the wrong tool if you need a silent boolean; that is `test -e`/`-x` territory, or `readlink -e`.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/namei.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
