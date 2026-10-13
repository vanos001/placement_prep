# mkdir — create directories

## Overview

`mkdir` creates one or more directories — a fresh, empty inode of type `d` linked into an existing parent. It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/mkdir`, has existed since the first editions of AT&T UNIX, and is POSIX-standardized. Two options carry all the scripting weight: `-p` to build missing parents and tolerate pre-existing directories, and `-m` to set the mode explicitly instead of inheriting the umask-derived default. Because `mkdir(2)` is atomic, `mkdir -p` is the standard idiom for race-free "make sure this path exists" logic in shell scripts, Makefiles, and install targets.

`mkdir` is often confused with `install -d` (creates directories with explicit modes and ownership in one step, without umask interference), with `touch` on a new path (creates a file, not a directory — fails if the parent is missing), and with `mktemp -d` (creates a *safely named, uniquely random* directory rather than a name you choose).

| Field | Value |
| --- | --- |
| Package | coreutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/mkdir |
| First appeared | AT&T UNIX, Version 1 (1971) |
| Standards | POSIX.1-2018 (`mkdir`) |

## Synopsis

```
mkdir [OPTION]... DIRECTORY...
```

Common one-line forms:

```
mkdir build                 # one directory, mode 0777 & ~umask
mkdir -p a/b/c              # create the whole chain, tolerate existing
mkdir -m 700 ~/.private     # explicit mode, bypassing the umask default
mkdir -pv deploy/{etc,log}  # verbose + brace expansion
```

## How It Works

### The syscall underneath

For each `DIRECTORY` operand, `mkdir` calls `mkdir(path, mode)` — an atomic kernel operation that fails unless the immediate parent exists and is writable. There is no shell loop involved: the directory springs into existence fully formed, and two concurrent `mkdir(2)` calls on the same path can only succeed once (the loser gets `EEXIST`). That atomicity is why `-p` is trusted in parallel builds and boot scripts.

### Default mode and the umask

Without `-m`, the new directory gets mode `0777 & ~umask` — typically `0755` with the common `umask 022`:

```bash
$ umask 022; mkdir plain; stat -c '%a' plain
755
```

With `-m`, GNU mkdir creates the directory and then enforces the requested mode exactly — the umask does not eat it. Verified under `umask 077`:

```bash
$ umask 077; mkdir -m 755 exact; stat -c '%a' exact
755
```

### -p: the parent chain

`-p` (`--parents`) walks the path component by component, creating whatever is missing. Two documented guarantees, both verified:

```bash
$ mkdir -p p1/q1/r1          # p1, q1, r1 all created
$ mkdir -p p1/q1/r1; echo $? # rerun: no error
0
```

- Existing components are **not** an error (unlike bare `mkdir`, which exits 1 with `File exists`).
- Missing parents are created with the **umask default**, regardless of any `-m`: "no error if existing, make parent directories as needed, with their file modes unaffected by any -m option", as `--help` states.

### The -m + -p ordering trap

`-m` applies only to the final component(s) actually named on the command line; the synthesized parents keep the umask mode. Verified:

```bash
$ umask 022
$ mkdir -p -m 700 p1/q1/r1
$ stat -c '%n %a' p1 p1/q1 p1/q1/r1
p1 755
p1/q1 755
p1/q1/r1 700
```

If the private-mode requirement covers the whole chain, run `mkdir -p` first and `chmod` afterwards — or reach for `install -d -m`, which applies the mode to every directory it creates.

```
mkdir -p -m 700 a/b/c
        │
        ▼
   a  ── 0755 (umask) ── not 700: -m never touches parents
   └─ b ── 0755 (umask)
        └─ c ── 0700 (-m applies to the named leaf)
```

### Verbose output and installers

`-v` turns `mkdir` into its own audit log — one line per directory actually created (pre-existing directories are silent under `-p`). Verified output:

```bash
$ mkdir -pv a/b
mkdir: created directory 'a'
mkdir: created directory 'a/b'
```

Package installers and CI pipelines rely on this to show exactly what a build touched, and the same lines are what `install -d -v` mirrors.

### mkdir(2) error gallery

Most `mkdir` failures map directly to kernel errors — the exact table an interviewer expects:

| Error | Trigger |
| --- | --- |
| `EEXIST` | A component (or the leaf) already exists — and `-p` only forgives *directories* |
| `ENOENT` | Parent directory missing (the reason `-p` exists) |
| `EACCES` | No write/search permission on the parent |
| `ENOTDIR` | A path component exists but is a regular file (`mkdir -p plain/sub` on a file `plain`) |
| `ENAMETOOLONG` | Component or path exceeds filesystem limits |
| `ENOSPC`/`EDQUOT` | No space or quota exhausted |
| `EROFS` | Read-only filesystem |
| `EMLINK` | Parent already holds the maximum number of subdirectories |

Note the `-p` subtlety in the first two rows, verified: `mkdir -p plain` where `plain` is a regular file still fails (`File exists`, exit 1), and so does `mkdir -p plain/sub` (`Not a directory`). `-p` forgives only existing *directories*.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p`, `--parents` | Create missing parents; existing components (directories) are not an error; parent modes unaffected by `-m` |
| `-m`, `--mode=MODE` | Set the mode as in `chmod` — applied exactly, not masked by umask; parents excluded (see trap above) |
| `-v`, `--verbose` | Print a message for each created directory (useful in install logs) |
| `-Z` | Set the SELinux security context of created directories to the default type |
| `--context[=CTX]` | Like `-Z`, or set an explicit SELinux/SMACK context |

## Usage Patterns

```bash
# The everyday single directory
mkdir build
```

```bash
# Ensure a whole path exists — the standard script idiom
mkdir -p /var/lib/myapp/cache
```

```bash
# Idempotency: safe under concurrency, thanks to atomic mkdir(2)
mkdir -p /run/lock/myapp || true
```

```bash
# Private directory with an explicit mode, ignoring the umask
mkdir -m 700 ~/private
```

```bash
# The trap in action: leaf gets 700, parents get umask-derived 755
mkdir -p -m 700 app/data/secrets
```

```bash
# If the whole chain must be private: two steps
mkdir -p app/data/secrets && chmod 700 app app/data app/data/secrets
```

```bash
# Or let install(1) do it in one shot with the mode on every level
install -d -m 700 app/data/secrets
```

```bash
# Brace expansion fans out a project skeleton in one call
mkdir -pv project/{src,tests,docs,build}
# mkdir: created directory 'project'
# mkdir: created directory 'project/src'
# ...
```

```bash
# Log what an installer created
mkdir -pv /opt/acme/{bin,etc,var}
```

```bash
# Guard against a component being a regular file (ENOTDIR), not just missing
[ -d "$dir" ] || mkdir -p "$dir"
```

```bash
# Copy a directory's mode to a new sibling
mkdir -p --mode="$(stat -c '%a' reference_dir)" new_dir
```

```bash
# Prepare a mount point before mounting (fstab expects the directory to exist)
mkdir -p /mnt/backup
```

```bash
# Split a single -p call from per-directory modes when parents matter too
mkdir -p -m 755 /srv/www && mkdir -m 750 /srv/www/private
```

## Nuances and Gotchas

- **`-m` + `-p` parent surprise.** The single most-asked interview trap (verified above): parents never receive the `-m` mode. Scripts that "proved it worked" on a one-level path silently regress on deep paths.
- **`-m` beats the umask, default mode does not.** Without `-m`, the umask shapes the result; with `-m`, GNU mkdir enforces the exact mode. Mixing the two mental models explains most "why is this 700/755?" puzzles.
- **`-p` forgives directories, not files.** An existing regular file at any component position is a hard error (`EEXIST` or `ENOTDIR`). Naive `mkdir -p "$path"` in front of writes still needs failure handling.
- **Trailing slashes and whitespace.** Unquoted variables with spaces or globs expand into multiple operands — quote `"$(...)"`-derived paths. A path with a trailing slash behaves as the directory itself, but `mkdir ""` fails outright.
- **Portability.** `-p` and `-m` are POSIX and present everywhere (GNU, BSD, BusyBox). `-v` is GNU (BSD/macOS also have it; BusyBox does not). `-Z`/`--context` are GNU+SELinux. Use only `-p`/`-m` in portable scripts.
- **Recursive chmod follows from this.** Because parents get umask modes, `mkdir -p -m 700 deep/path` + a later `chmod -R` is a common fix — but `chmod 700 deep` after the fact is cheaper and leaves the leaf alone.
- **Windows-style recursion doesn't exist.** There is no `-r`; depth is achieved only via `-p` or multiple operands. `mkdir a/b` without `-p` is always `ENOENT`.
- **SELinux contexts are distro-shaped.** `-Z` sets the default type for the path's level; `--context=CTX` forces one. On non-SELinux systems both are accepted but inert, which surprises nobody — but scripts that hard-code `--context` values break when moved between MLS policies.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Every requested directory exists (created now, or already there under `-p`) |
| 1 | Any failure: `EEXIST` without `-p`, missing parent, `EACCES`, `ENOTDIR`, and friends; diagnostics on stderr |

## Related Commands

- [`rmdir`](./rmdir.md) — the inverse: removes empty directories, with `-p` walking back up.
- [`install`](./install.md) — `install -d` creates directories with exact modes/ownership, ignoring umask.
- [`rm`](./rm.md) — removes populated directory trees (`rm -r`), unlike `rmdir`.
- [`ls`](./ls.md) — verify what you just created (`ls -ld`).
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [permissions](../../admin/permissions.md) — the umask and mode-bit model behind every `-m` calculation.
- [bash](../../shell/bash.md) — brace expansion (`mkdir -p a/{b,c}`) and the quoting rules around paths.

## Interview Questions

### Q: What does `mkdir -p -m 700 a/b/c` actually create, and why?

`a` and `b` are created with the umask-derived default (typically 755); only `c`, the final named component, receives 700. GNU's `-p` documentation states parents' modes are "unaffected by any -m option". To make the whole chain 0700, follow with `chmod 700 a a/b a/b/c`, or use `install -d -m 700 a/b/c`, which applies the mode at every level it creates.

### Q: Why is `mkdir -p` considered race-safe?

Each directory comes into existence via a single atomic `mkdir(2)` call. If two processes run `mkdir -p` on the same path concurrently, one create wins and the other gets `EEXIST`, which `-p` deliberately treats as success. There is no check-then-act window (unlike `[ -d d ] || mkdir d`, which can race between the test and the create) — though `-p` still fails if a *file* occupies a component, so the path namespace itself must be sane.

### Q: A script runs `mkdir /tmp/build` and fails with "File exists" on the second run. What are the fixes, and what are their trade-offs?

`mkdir -p /tmp/build` is the idiomatic fix: idempotent, atomic, one syscall path — but it also forgives a *file* named `build` only in the sense of failing with a different error (`ENOTDIR`/`EEXIST`), so validation is still needed. `rm -rf` before `mkdir` is destructive and forbidden on shared directories. `[ -d ... ] || mkdir ...` reintroduces a race window. The general answer: `-p` for existence-tolerance, plus explicit checks when the component might be a non-directory.

### Q: How do mode, umask, and -m interact, exactly?

Default mode is `0777 & ~umask` at creation time — the umask is a kernel-side mask the process cannot see around without a follow-up call. `-m MODE` is chmod-style: GNU mkdir creates the directory with a restricted mode, then enforces MODE exactly, so `umask 077; mkdir -m 755 d` yields 755. Interviewers probe this because it contradicts the folk wisdom that "umask always wins" — it wins only for the default mode, not for `-m`.

### Q: Name three mkdir(2) errors you'd expect in production and what each tells you.

`EEXIST` — the target or a component already exists (with `-p`, this means a non-directory squats on the name). `EACCES` — the effective UID lacks write/search permission on the parent, common after chown mishaps or read-only bind mounts. `ENOSPC`/`EDQUOT` — the filesystem or quota is exhausted, typically surfacing during log-rotation or build jobs. Each maps to a different remediation: cleanup, permissions, capacity.

### Q: When would you choose install -d over mkdir -p -m?

Whenever the mode or ownership of *every* directory in the chain matters — package installers, image builds, state directories. `install -d -m 700 -o app -g app /var/lib/app/run` applies mode and ownership to each created level and bypasses the umask entirely, where `mkdir -p -m` styles only the leaf and cannot set ownership at all. For throwaway or top-level paths, plain `mkdir -p` remains simpler.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/mkdir.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — mkdir](https://pubs.opengroup.org/onlinepubs/9699919799/)
