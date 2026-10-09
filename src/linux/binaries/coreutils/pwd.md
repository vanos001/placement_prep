# pwd — print working directory

## Overview

`pwd` prints the current working directory — but "the" directory has two
representations, and which one you get depends on which `pwd` you ran.
The shell tracks a **logical** path in `$PWD` (what you typed, with
symlinks intact), while the kernel's `getcwd(3)` returns the **physical**
path (every symlink resolved). The shell builtin defaults to logical
(`-L`); the coreutils binary defaults to physical (`-P`). That asymmetry
is the single most quoted fact about this command.

The binary ships in the Debian `coreutils` package at `/usr/bin/pwd`
(`/bin/pwd` is a merged-`/usr` symlink to it). Almost every interactive
invocation actually runs the *builtin* — `type -a pwd` shows `shell
builtin` before `/usr/bin/pwd` — which is why help output, defaults, and
error messages differ between contexts. The command is POSIX-standardized
and dates to the original Unix; it is often confused with `$PWD` (a
variable the shell maintains and can be wrong), `pwd -P` in scripts
(the fix for symlink surprises), and `$OLDPWD` (the shell's previous-dir
convenience).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/pwd` |
| First appeared | original AT&T Unix (Version 1 era) |
| Standards | POSIX 2018 utility |

## Synopsis

```
pwd [OPTION]...
```

Main forms:

```
pwd          # builtin default: logical ($PWD) if it is consistent
pwd -P       # physical: resolve every symlink (always getcwd)
pwd -L       # logical: print $PWD even if it contains symlinks
/usr/bin/pwd # the binary, which assumes -P when no option is given
```

## How It Works

Two sources of truth cooperate:

```
  shell builtin pwd (default -L)          /usr/bin/pwd (default -P)
  ┌────────────────────────────┐          ┌──────────────────────────┐
  │ print $PWD if it names the │          │ getcwd(3): walk inodes   │
  │ current dir, else fall     │          │ back up via ".."         │
  │ back to getcwd()           │          │ → fully physical path    │
  └────────────────────────────┘          └──────────────────────────┘
        trusting shell bookkeeping              trusting only the kernel
```

The kernel does not remember names — only inodes. `getcwd(3)` therefore
*reconstructs* the path by walking `..` to the root, resolving every
symlink by construction. The shell, by contrast, does lexical
bookkeeping: `cd /var && cd tmp` (through a symlinked `tmp`) sets
`$PWD=/var/tmp` — logical, symlink intact, and cheaper than asking the
kernel.

The coreutils help states its own default explicitly: *"If no option is
specified, -P is assumed"*, while bash's builtin help says *"By default,
`pwd` behaves as if `-L` were specified"*. Same command name, opposite
defaults:

```bash
$ pwd                     # builtin, -L: the logical path
/tmp/g2
$ /bin/pwd                # binary, -P: physical resolution
/tmp/g2
```

`-L` is not blind: the builtin prints `$PWD` only when it still names
the current directory. Hand it a stale or lying `$PWD` and it silently
falls back to `getcwd`:

```bash
$ PWD=/tmp/g2/.. /bin/pwd -L    # $PWD does not name the cwd
/tmp/g2                          # -> physical fallback, no error
```

(The example is deliberate: `/tmp/g2/..` refers to `/tmp`, not the cwd,
so the check fails and `getcwd` wins.)

With symlinked directories the two modes genuinely diverge — the classic
scenario is a link into a deep tree:

```bash
# /opt/rel -> /var/lib/app-v2   (symlink to a directory)
$ cd /opt/rel/config
$ pwd          # builtin -L: keeps the path you typed
/opt/rel/config
$ pwd -P       # resolves every link
/var/lib/app-v2/config
```

Scripts that compute locations from `$PWD` or plain `pwd` can break when
any component is a symlink that later gets retargeted (version flips,
atomic deploys); `pwd -P` (or the binary) pins them to reality.

## Options That Matter

| Option | Effect |
|---|---|
| `-L, --logical` | Print `$PWD` even if it contains symlinks (builtin default; validation applies) |
| `-P, --physical` | Resolve all symlinks — always `getcwd(3)` (binary default) |
| `--help` / `--version` | Informational |

Both modes are POSIX-specified, including the opposite defaults between
shells' builtins and the standalone utility. POSIX also permits `-L`
output to differ from `-P` only when the logical path is *reachable*;
if `$PWD` is unset or inconsistent, both modes converge on `getcwd`.

## Usage Patterns

```bash
# Script locates itself through symlinks (deploy dirs are symlinks)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
```

```bash
# Record the physical directory in a log for post-mortems
echo "ran in $(pwd -P)" >> run.log
```

```bash
# Show where a symlinked path really lives
cd /opt/rel && pwd -P
```

```bash
# Confirm shell logical bookkeeping matches the kernel view
[ "$(pwd)" = "$(pwd -P)" ] || echo "inside a symlink chain"
```

```bash
# Use $OLDPWD for a two-step compare
cd /etc && diff <(ls) <(cd "$OLDPWD" && ls)
```

```bash
# Physical cwd in a prompt without symlink clutter
PS1='\w \$ '            # bash already uses $PWD; for physical: $(pwd -P)
```

```bash
# Capture cwd before a cd-heavy function runs
BASE=$(pwd -P); cd /tmp/work || exit; ...; cd "$BASE"
```

```bash
# Guard against deleted-cwd weirdness in long-lived shells
cd "$(pwd -P)" 2>/dev/null || echo "cwd was removed; re-home me"
```

## Nuances and Gotchas

- **Opposite defaults between builtin and binary.** `pwd` in bash is
  logical; `/usr/bin/pwd` is physical. A one-liner that "works in my
  shell" can behave differently in `sh -c` under a shell without a pwd
  builtin (dash *has* one, but tiny shells may not).
- **`$PWD` is just an environment variable.** Any parent process can set
  it to garbage; the builtin validates (stat-compare) and falls back, but
  `/usr/bin/pwd -L` also validates before trusting. Never use `$PWD` in
  security-relevant logic without validation.
- **`getcwd` fails if the cwd was deleted** (`pwd: cannot get current
  directory` or an error per implementation) — a real failure mode for
  long-lived shells and daemons whose working directories were removed
  out from under them.
- **`pwd -L` prints the *bookkeeping* path**, which is lexical: after
  `cd ..` through a symlinked directory you may land somewhere your
  intuition disagrees with — `cd /opt/rel/config && cd ..` puts you in
  `/opt/rel` logically but `/var/lib/app-v2` physically, and *both* are
  "correct".
- **Name length limits.** `getcwd(3)` historically had a buffer-size
  failure mode for deep trees (`getcwd: cannot access parent
  directories`); the binary handles this by allocating dynamically, but
  shells' builtin `-L` path can still print more than fits in legacy
  buffers.
- **`PWD` and `pwd` disagree across mounts**: bind mounts and overlayfs
  (containers) can make the physical path differ from expectations in
  ways no option resolves — the kernel reports what it sees.
- **`pwd` output is newline-terminated**; command substitution strips it,
  but scripts doing `$(pwd)` inside `printf '%s'` styling must remember
  `$(pwd)` (not `$(pwd; echo)` oddities) — the usual quoting rules apply.

## Exit Status

| Code | Meaning |
|---|---|
| `0` | Path printed |
| `1` | `getcwd(3)` failed: cwd deleted, permission trouble walking to root, or path exceeds limits |
| `2` | Invalid option (bash builtin convention for bad usage) |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./readlink.md`](./readlink.md) — `readlink -f` is the name-resolving sibling of `pwd -P`.
- [`./pathchk.md`](./pathchk.md) — validate the long paths pwd can produce.
- [`../../shell/bash.md`](../../shell/bash.md) — `$PWD`, `$OLDPWD`, and cd's logical bookkeeping.

## Interview Questions

### Q: What is the difference between pwd's -L and -P modes?

`-L` prints the shell's logical path from `$PWD` — the route you typed,
with symlinks unexpanded — while `-P` asks the kernel (`getcwd(3)`) for
the physical path with every symlink resolved. In a directory reached
through a symlink, `pwd` shows `/opt/rel/config` and `pwd -P` shows
`/var/lib/app-v2/config`. Both are truthful; they answer "what did I
say" versus "where is this actually".

### Q: Why do the bash builtin and /usr/bin/pwd disagree on the default?

POSIX specifies both: the standalone utility defaults to `-P` (its help:
"If no option is specified, -P is assumed"), while shells' builtins
default to `-L` because the shell maintains `$PWD` as part of cd's
logical bookkeeping. Since the builtin shadows the binary in interactive
use, people learn "pwd is logical" and are surprised by the binary — the
interviewer is testing whether you know which program actually ran.

### Q: A script computes its own directory with `pwd` and breaks when deployed via a symlinked release dir. Fix it.

Plain `pwd` (builtin, logical) reports the symlinked path, and when the
deploy flips the symlink to a new release, relative logic anchored to the
old logical path can misfire. Fix by resolving physically:
`SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)` — or
`readlink -f`. The pattern is standard precisely because release
directories, `current` symlinks, and bind mounts make logical paths
unstable.

### Q: When does pwd fail even though the process is running?

When the working directory has been deleted (rmdir'd or its mount
removed): `getcwd(3)` cannot reconstruct a path to a nonexistent inode,
so `pwd` errors and exits nonzero. Long-lived shells and services in
ephemeral directories hit this; the fix is to re-home (`cd` to a valid
directory) or restart. It is a classic post-mortem finding for cron jobs
whose spool directories were cleaned.

### Q: Is $PWD trustworthy?

Only after validation. It is an ordinary environment variable inherited
from the parent process, so anything can set it. The builtin's `-L` mode
(and `/usr/bin/pwd -L`) stat-compares `$PWD` against the actual cwd and
silently falls back to `getcwd` on mismatch — the observed behavior —
but scripts should treat `$PWD` as a hint, never as evidence, and use
`pwd -P` (or the binary) where the physical location matters.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/pwd.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec — pwd](https://pubs.opengroup.org/onlinepubs/9699919799/)
