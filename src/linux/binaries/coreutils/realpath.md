# realpath — Print the resolved absolute path of a file

## Overview

`realpath` converts a path — possibly relative, dotted, or full of symlinks —
into a canonical absolute path. It is the tool to reach for when a script
needs "the actual path" of whatever the user passed in: resolving `..`
components, expanding symlinks, and eliminating double slashes in one step.

It ships in Debian package `coreutils` and lives at `/usr/bin/realpath` on
modern Debian/Ubuntu systems. Historically it was a standalone utility that
GNU coreutils absorbed in the 8.x series (early 2010s), which is why older
documentation sometimes describes it as an add-on. On BSD/macOS systems the
name exists but the implementation differs and the option set is smaller.

`realpath` is often confused with `readlink -f`: with default options they
produce the same output for most inputs. The differences are in edge
semantics (`-e`, `-m`, `-s`) and the fact that `realpath` is a
canonicalization tool while `readlink` is a symlink-inspection tool.
Another frequent confusion: `realpath` default mode does **not** require the
*last* component to exist — only everything above it.

| Field | Value |
|---|---|
| Package | coreutils (Debian bookworm) |
| Section (man) | 1 — User Commands |
| Path | /usr/bin/realpath |
| First appeared / lineage | standalone tool, absorbed into GNU coreutils (8.x series, early 2010s) |
| Standards | not in POSIX 2018; GNU coreutils implementation also present in busybox and modern BSDs |

## Synopsis

```
realpath [OPTION]... FILE...
```

```bash
realpath /etc/nginx/../init.d/    # default: resolve symlinks, all but last component must exist
realpath -e --relative-to=$HOME ./notes/todo.md
realpath -m -s "$1"               # canonicalize lexically, do not touch the filesystem
realpath --relative-base=/srv data/backup.tar
```

## How It Works

`realpath` resolves a path the same way the kernel would resolve it when
opening a file, then prints the result. The resolution loop, per component:

```
           ┌─────────────────────────────────────────────────┐
           │  realpath resolution loop (per path component)  │
           └─────────────────────────────────────────────────┘

  component ──► is it "." or "" ? ──yes──► drop it
       │                 │no
       │                 ▼
       │        is it ".." ? ──yes──► pop last kept component
       │                 │no              (unless -L: see below)
       │                 ▼
       │        does a symlink live here?
       │           │yes                    │no
       │           ▼                       ▼
       │    prepend symlink target     keep component
       │    to remaining input              │
       │           └───────────┬────────────┘
       ▼                       ▼
  print absolute result   stop on first missing component
                          (default: last one may be missing;
                           -e: none may be missing;
                           -m: missing components are tolerated)
```

The default (`-P`, physical) mode requires **all but the last component** to
exist, because it must walk them to resolve symlinks. This mirrors the
behavior of `readlink -f`:

```bash
$ realpath /usr/bin/nonexistent-name
/usr/bin/nonexistent-name          # last component need not exist
$ echo $?
0
$ realpath /usr/bin/../nope/../deeper
realpath: No such file or directory   # intermediate component 'nope' is missing
```

`-e` (canonicalize-existing) tightens the default: every component,
including the last, must exist. `-m` (canonicalize-missing) relaxes it:
no component needs to exist, so you can canonicalize paths you are *about*
to create — handy for generating install paths.

The `-L` (logical) option changes how `..` is handled. In physical mode,
`..` pops one *resolved* directory. In logical mode, `realpath` processes
`..` *before* resolving the next symlink, imitating the way a shell keeps
`$PWD` when you `cd` through a symlink:

```bash
# /v -> /var/log ; current dir is /v (a symlink)
# physical:  realpath -P -L-less behavior resolves against /var/log
# logical:   '..' is applied to the string /v first, so '..' -> /
```

Two relative-output options make `realpath` a portable replacement for
`readlink -f` + fragile string surgery:

- `--relative-to=DIR` — print the result relative to DIR.
- `--relative-base=DIR` — print relative to DIR only if the result is
  underneath it; otherwise print the absolute path. Together they are the
  standard idiom for "normalize an argument inside a root directory":

```bash
$ realpath --relative-to=/etc /etc/hosts
hosts
$ realpath --relative-to=/etc /var/log/syslog
../../var/log/syslog
```

Output is one path per line, newline-terminated; `-z` terminates each line
with NUL instead, which composes safely with `xargs -0`. Error messages go
to stderr; use `-q` to suppress most of them when a failure should just be
reflected in the exit status.

## Options That Matter

| Option | Effect |
|---|---|
| `-e`, `--canonicalize-existing` | every component of the path must exist |
| `-m`, `--canonicalize-missing` | no component needs to exist or be a directory |
| `-P`, `--physical` | resolve symlinks as encountered (default) |
| `-L`, `--logical` | resolve `..` components before symlinks |
| `-s`, `--strip`, `--no-symlinks` | do not expand symlinks; canonicalize lexically only |
| `--relative-to=DIR` | print the resolved path relative to DIR |
| `--relative-base=DIR` | relative to DIR if under it, absolute otherwise |
| `-q`, `--quiet` | suppress most error messages |
| `-z`, `--zero` | NUL-terminate output lines |

### Existence strictness

The three-way choice default / `-e` / `-m` is the part interviewers probe:

| Mode | Last component must exist | Intermediate components must exist | Symlinks resolved |
|---|---|---|---|
| default (`-P`) | no | yes | yes |
| `-e` | yes | yes | yes |
| `-m` | no | no | yes |
| `-s` | n/a — no filesystem interaction for symlinks | | no |

## Usage Patterns

```bash
# Resolve a user-supplied relative argument inside a script
TARGET=$(realpath "${1}")
```

```bash
# Refuse paths outside a project root (relative-base keeps outsiders absolute)
case "$(realpath --relative-base="$ROOT" "$arg")" in
  /*) echo "refusing path outside $ROOT" >&2; exit 1 ;;
esac
```

```bash
# Canonicalize a path that does not exist yet (about to be created)
mkdir -p "$(dirname "$(realpath -m "$opt_output")")"
```

```bash
# Compare two paths after normalizing both — avoids false negatives
[ "$(realpath -e "$a")" = "$(realpath -e "$b")" ] && echo same
```

```bash
# Strip only '..' and redundant slashes, leave symlinks intact (-s)
realpath -s "$path"
```

```bash
# NUL-safe mass canonicalization (filenames may contain newlines)
find . -print0 | xargs -0 realpath -e -z | xargs -0 rm --batch-check 2>/dev/null
```

```bash
# Resolve a script's own location portably (works even when invoked via a link)
SELF_DIR="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
```

```bash
# Show what a package-maintained symlink really points at in absolute terms
realpath /usr/bin/awk
```

```bash
# Quiet mode: rely on exit status only, keep stderr clean in loops
if realpath -q -e "$candidate" 2>/dev/null; then use "$candidate"; fi
```

```bash
# Generate a relative reference path for a config file (no ../.. guessing)
echo "include: $(realpath --relative-to=/etc/app /var/lib/app/defaults.yaml)"
```

## Nuances and Gotchas

- **Not POSIX.** There is no `realpath` in the POSIX utility set, so option
  spelling varies: GNU supports `-e`/`-m`/`--relative-to`, busybox supports a
  subset, and older macOS/BSD `realpath` lacks most GNU options. Scripts that
  need portability often shell out to `cd ... && pwd -P` instead — which is
  itself a partial `realpath -P`.
- **`readlink -f` vs `realpath` defaults.** Both resolve symlinks and both
  require intermediate components to exist, but `realpath -e` requires the
  final component too, while `readlink -f` does not. Matching the wrong one
  in a test suite produces confusing diffs.
- **The last-component exemption surprises people.** `realpath /tmp/nope`
  exits 0 and prints `/tmp/nope`. If you need full existence checking, pass
  `-e` explicitly; do not rely on a nonzero exit to validate a file.
- **`-L` changes meaning, not existence rules.** Logical mode can produce
  paths that contain a symlinked prefix plus `..` — a path that may not
  actually resolve the same way through the kernel. Do not feed `-L` output
  back into security checks that assume kernel-equivalent resolution.
- **Multiple arguments, multiple failures.** With several FILE operands,
  `realpath` continues after an error and exits nonzero if *any* failed;
  decide deliberately whether partial output is acceptable.
- **Quoting.** Spaces and globs in arguments must be quoted, and output
  captured with `"$(...)"` — unquoted command substitution re-splits on
  whitespace, silently corrupting the canonical path.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | every FILE was canonicalized successfully |
| 1 | at least one operand failed (missing component, permission, bad option) |

With multiple operands the process continues past failures and still exits
nonzero; check the exit status, not just stdout.

## Related Commands

- [`stat`](./stat.md) — attribute inspection for the resolved file
- `readlink` (not covered here) — symlink target printing; `readlink -f` overlaps realpath's default mode
- [Collection overview](./overview.md) — all pages in the GNU Coreutils collection

## Interview Questions

### Q: How does `realpath` default mode differ from `-e` and `-m`?

Default (`-P`) mode requires all but the final component to exist, because
symlink resolution has to walk intermediate directories; the final name is
allowed to be a path that does not exist yet. `-e` requires the final
component to exist as well, while `-m` drops all existence requirements so
paths can be canonicalized before creation. A common bug is assuming the
default validates the whole path — it validates only the prefix.

### Q: When would you use `realpath -m -s` instead of the default?

`-m -s` is pure lexical canonicalization: it collapses `..`, `.`, and
duplicate slashes without consulting the filesystem at all and without
expanding symlinks. That is what you want when normalizing a path that is
about to be created, or when the argument may contain a symlink you
deliberately want to preserve — for example, constructing an installation
prefix before `mkdir -p`.

### Q: What is the difference between physical and logical mode?

Physical mode (`-P`) resolves the path exactly as the kernel would, popping
`..` against the already-resolved directory. Logical mode (`-L`) processes
`..` components before symlink resolution, like a shell's `$PWD` bookkeeping
after `cd` through a symlink. The two agree on symlink-free paths but can
disagree on paths such as `/symlink-to-dir/../file`, and only the physical
result is guaranteed to resolve consistently through open(2).

### Q: Your backup script must reject any argument that escapes `/srv/data`. How?

Use `realpath --relative-base=/srv/data "$arg"`. When the resolved path lies
under the base, it is printed relative to the base; otherwise the absolute
path is printed. Treating a leading `/` in the output as "outside the root"
gives a one-line containment check without hand-rolled string matching —
which is important because arguments like `../..` only become visible after
canonicalization.

### Q: Why is `realpath` not a drop-in on macOS or older BSD systems?

POSIX never standardized it, so the name was implemented independently: the
GNU version absorbed into coreutils has `-e`/`-m`/`--relative-to`, while BSD
derivations historically supported fewer options and different defaults.
Portable scripts either detect option support at runtime, use busybox/GNU
exclusively, or fall back to the `cd "$(dirname ...)" && pwd -P` idiom.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/realpath.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
