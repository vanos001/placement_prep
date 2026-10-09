# readlink — print symlink targets and canonical paths

## Overview

`readlink` does two related jobs. With no flags, it prints the raw target
of each symlink operand — the literal contents of the link. With the
canonicalization flags (`-f`, `-e`, `-m`), it resolves every symlink in
every component of a path and prints the final absolute pathname, making
it the standard tool for answering "where does this path *really* point?"
in scripts. That second mode is why the binary exists in coreutils at
all: the `-f` idiom `$(readlink -f "$0")` is probably the most-embedded
coreutils invocation in shell history after `basename`.

It ships in the Debian `coreutils` package at `/usr/bin/readlink`
(the BSDs grew an equivalent from OpenBSD's implementation; GNU's version
dates from the 8.x-era consolidation when `realpath` was folded in as a
companion). It is a GNU/BSD extension — no POSIX spec — and is often
confused with `realpath` (same canonicalization, more flags, defaults to
`-f` behavior) and with `pwd -P` (same resolution applied to the current
directory only).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Man section | 1 |
| Path | `/usr/bin/readlink` |
| First appeared | BSD mid-1990s; GNU coreutils own variant |
| Standards | GNU extension — not POSIX |

## Synopsis

```
readlink [OPTION]... FILE...
```

Main forms:

```
readlink /bin                     # raw symlink target text
readlink -f path/to/thing         # canonicalize; all but last component must exist
readlink -e path/to/thing         # canonicalize; ALL components must exist
readlink -m path/to/thing         # canonicalize; existence never required
```

## How It Works

Without flags, `readlink` calls `readlink(2)` per operand and prints
whatever bytes the kernel stored when the link was created — relative
targets stay relative, nothing is validated:

```bash
# On merged-/usr Debian: /bin is a relative symlink into /usr
$ ls -ld /bin
lrwxrwxrwx 1 root root 7 Mar  2  2026 /bin -> usr/bin
$ readlink /bin
usr/bin
```

With `-f`, `-e`, or `-m`, the tool walks the path component by component,
following each symlink recursively, resolving `.`/`..`, and producing one
absolute, symlink-free result:

```
        input: /bin/../../usr/bin
                 │ each component resolved in turn
                 ▼
   /bin → usr/bin → /usr/bin ; ".." resolved against real dirs
                 ▼
        output: /usr/bin
```

```bash
$ readlink -f /bin/../../usr/bin
/usr/bin
```

The three flags differ *only* in what existence they demand — the exit
codes below are grounded:

```bash
# -f: everything except the final component must exist
$ readlink -f /nonexistent; echo $?
/nonexistent
0

# -e: the whole resolved path must exist -> failure is silent by default
$ readlink -e /nonexistent; echo $?
1

# -m: nothing must exist; pure lexical/anchor resolution
$ readlink -m /nonexistent/a/b; echo $?
/nonexistent/a/b
0
```

Applied to a non-symlink, flagless `readlink` prints nothing and fails:

```bash
$ readlink /etc/hostname; echo $?      # regular file: not a symlink
1
$ readlink -f /etc/hostname; echo $?   # -f just canonicalizes it
/etc/hostname
0
```

Error messages are suppressed *by default* (`-s/--silent` is the
default state per the help text); add `-v` when a script needs to know
why a resolution failed.

## Options That Matter

| Option | Effect |
|---|---|
| `-f, --canonicalize` | Resolve all symlinks; all components except the last must exist |
| `-e, --canonicalize-existing` | Resolve all symlinks; *every* component must exist |
| `-m, --canonicalize-missing` | Resolve all symlinks; no component needs to exist |
| `-n, --no-newline` | Omit the trailing newline (for embedding output in strings) |
| `-z, --zero` | NUL-terminate output instead of newline (xargs -0 pipelines) |
| `-v, --verbose` | Report error messages (off by default!) |
| `-s, --silent` | Suppress most error messages (the default) |
| `-q, --quiet` | Alias retained for compatibility |

Choosing among `-f`/`-e`/`-m`: `-f` for "the thing I will act on may not
exist yet, but its parent tree does" (planned files, new log names);
`-e` for "I am about to operate on this and it must be real";
`-m` for "I am constructing a path to create later".

## Usage Patterns

```bash
# The canonical script-locates-itself idiom
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
```

```bash
# Resolve through symlinked deploy directories
APP_HOME=$(readlink -f /opt/myapp/current)
```

```bash
# Check that a path exists AND get its real location in one step
real=$(readlink -e "$1") || { echo "missing: $1" >&2; exit 1; }
```

```bash
# Compare two paths that may traverse different symlinks
[ "$(readlink -f "$a")" = "$(readlink -f "$b")" ] && echo same file
```

```bash
# Where does this python really come from?
readlink -f "$(command -v python3)"
```

```bash
# Build (not-yet-existing) destination path for a create step
dest=$(readlink -m "/srv/data/$datestamp/out.bin")
```

```bash
# NUL-safe bulk resolution of a file list
find /etc -type l -print0 | xargs -0 -n1 readlink -v -f
```

```bash
# Raw target inspection: is this link relative or absolute?
readlink /etc/localtime
```

```bash
# Inline use without newline when composing a string
printf 'resolving %s -> ' "$p"; readlink -n -f "$p"; echo
```

## Nuances and Gotchas

- **Flagless mode is all-or-nothing per operand.** A regular file yields
  empty output and exit 1 — scripts that only wanted canonicalization
  forget the flag and ship a tool that "sometimes prints nothing".
- **`-f`'s existence rule is precise.** Only the *final* component may be
  missing. `readlink -f /a/missing/deeper` fails if `/a` is missing too,
  but succeeds for `/etc/nope` (the parent `/etc` exists).
- **Silent by default.** Failures print nothing unless `-v` is given —
  great for pipelines, terrible for debugging. Cron jobs failing at
  `readlink -e` with empty output are a recurring support ticket.
- **Not POSIX.** Behavior is GNU/BSD; busybox implements `-f` but not
  always `-e`/`-m`. Strictly portable scripts either require coreutils or
  use `cd -P`-based tricks.
- **`realpath` overlap.** GNU `realpath` does what `readlink -f/-e/-m`
  does plus relative-path computation (`-r`), `-s` no-symlink mode, and
  more. Both exist in coreutils; `readlink` remains the smaller hammer.
- **Symlink loops** (`ln -s a b; ln -s b a`) are detected: canonicalization
  fails with "too many levels of symbolic links" (with `-v`) rather than
  hanging.
- **Multiple operands change output shape.** One line per input
  (newline- or NUL-terminated); `-n` with multiple inputs glues them
  together without separators — an easy way to mangle a list.
- **Trailing-slash semantics.** `readlink -f /link/` treats the slash as
  requiring the target to be a directory; flagless `readlink /link/` may
  behave differently across kernels/implementations (kernel resolves the
  slash through the link).

## Exit Status

| Code | Meaning |
|---|---|
| `0` | Every operand resolved/printed successfully |
| `1` | Any operand is not a symlink (flagless), does not exist per the mode's rule, a loop was hit, or usage error |

## Related Commands

- [`./overview.md`](./overview.md) — GNU Coreutils collection hub.
- [`./pwd.md`](./pwd.md) — `pwd -P` canonicalizes the *current* directory.
- [`./pathchk.md`](./pathchk.md) — length/portability checks on the paths readlink produces.
- [`./seq.md`](./seq.md) — companion in the "GNU extensions scripts lean on" set.

## Interview Questions

### Q: What is the difference between readlink -f, -e, and -m?

All three canonicalize a path — resolve every symlink in every component
and print the absolute result. They differ only in existence requirements:
`-f` requires everything except the final component to exist, `-e`
requires the entire resolved path to exist, and `-m` requires nothing
(pure resolution for paths you plan to create). Pick `-f` for
not-yet-created files in existing trees, `-e` before acting on a path,
`-m` when constructing new locations.

### Q: Why does plain `readlink /etc/hostname` print nothing and fail?

The flagless mode answers exactly one question: what symlink target is
stored at this path? `/etc/hostname` is a regular file, `readlink(2)`
returns `EINVAL`, and the tool prints nothing and exits 1 — silently,
because errors are suppressed by default. The fix for "give me the real
path" is `readlink -f`, which canonicalizes regular files happily.

### Q: How do readlink -f and pwd -P relate?

They run the same resolution machinery on different inputs: `pwd -P`
applies it to the process's current directory via `getcwd(3)`, while
`readlink -f path` applies it to an arbitrary operand (which may be
handled by `realpath(3)`-style walking internally). For the "script
locates itself" problem you combine both ideas: cd to the script's
dirname, then either `pwd -P` or `readlink -f "$0"`.

### Q: A cron job runs `readlink -e $CONFIG` and produces no output and no error message. What happened and how do you debug it?

`readlink` is silent by default — suppression of error messages is the
default state — so a missing `$CONFIG` (or a missing intermediate
component) yields empty output and exit 1, which the cron wrapper
discarded. Debug with `readlink -v -e "$CONFIG"` to see the actual
message, and in scripts branch on the exit status before using the
output. This "empty + silent" failure signature is the tool's most
common support complaint.

### Q: What happens with a symlink loop, and why doesn't readlink hang?

`ln -s a b; ln -s b a` then `readlink -f a` hits the kernel's
`ELOOP` limit (40 nested resolutions) and fails with "too many levels of
symbolic links" (visible with `-v`). The kernel caps traversal depth, so
no userspace tool can hang on a cycle — the same bound that protects
every `open()` of a looped link.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/readlink.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
