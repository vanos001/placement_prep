# dirname — strip the last component from a path

## Overview

`dirname` prints a pathname with its final component removed: the directory
part of a file path. Given `/etc/nginx/conf.d/default.conf` it prints
`/etc/nginx/conf.d`; given `scripts/deploy.sh` it prints `scripts`. It is
the exact mirror of [`basename`](./basename.md) — together they decompose
any path into `(directory, filename)`.

The binary ships in the Debian `coreutils` package at `/usr/bin/dirname`.
It performs pure string processing: the path need not exist and is never
opened, so exit status reflects only argument errors.

Like `basename`, `dirname` competes with shell parameter expansion —
`${var%/*}` — which is faster in loops but differs on edge cases in ways
that produce real bugs. That comparison is the heart of this page, since
interviewers and code reviewers both probe exactly those corners: what is
"the directory" of `file.txt` alone, of `/`, of `a/b/`?

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/dirname` on modern Debian/Ubuntu |
| First appeared / lineage | 7th Edition UNIX; part of GNU shellutils/fileutils, then coreutils |
| Standards | POSIX.1-2018 (`dirname`) |

## Synopsis

```
dirname [OPTION] NAME...
```

Main forms:

```bash
dirname /etc/nginx/nginx.conf        # -> /etc/nginx
dirname -a a/b c/d                   # -> a c        (multiple operands)
dirname -s /path/file.txt            # -> /path      (suffix form, GNU)
dirname -z "$p"                      # NUL-terminated output
```

POSIX requires support for exactly one NAME; `-a`, `-s`, `-z` are GNU
extensions (widely copied by busybox and BSDs).

## How It Works

The algorithm is deletion-only string processing:

1. Strip all trailing `/` characters.
2. Delete everything from the last remaining `/` onward.
3. If nothing remains, print `.` (a lone filename has no directory; POSIX
   says the result is a single `.`).
4. If the path consists only of slashes and step 1 leaves at least one, the
   result is `/`.

```bash
$ dirname /etc/nginx/conf.d/default.conf
/etc/nginx/conf.d
$ dirname /etc/nginx/conf.d/default.conf/
/etc/nginx/conf.d                 # trailing slash stripped first
$ dirname default.conf
.                                 # no slash: "current directory"
$ dirname /
/
$ dirname ///
/
$ dirname usr
.
```

Two results deserve emphasis because they invert naive expectations:

- `dirname default.conf` → `.`. The *correct* directory of a bare filename
  really is the current directory, so this is not a special case — it is
  the honest answer, and `cd "$(dirname "$0")"` works because of it.
- `dirname /` → `/`. The root is its own directory.

```
  input path                    output
  ─────────────────────────    ─────────────────
  /a/b/c            ────────►  /a/b
  /a/b/c/           ────────►  /a/b      (trailing slashes first)
  /a                ────────►  /
  c                 ────────►  .
  /                 ────────►  /
```

### dirname vs ${var%/*}

`${var%/*}` deletes the shortest suffix matching `/*`. When a slash exists
the result matches `dirname`; when there is **no slash**, `%/*` matches
nothing and the expansion returns the string *unchanged* — the divergence
that breaks scripts:

| Input | `dirname` | `${var%/*}` |
| --- | --- | --- |
| `/etc/nginx/nginx.conf` | `/etc/nginx` | `/etc/nginx` |
| `/a` | `/` | `` (empty!) |
| `file.txt` | `.` | `file.txt` (unchanged) |
| `/` | `/` | `` (empty) |
| `a/b/` | `a` | `a` |
| `a/b//` | `a` | `a/b` (only one trailing slash removed!) |

Every row where they differ is a row where a script behaves differently on
"test data" (absolute paths with files) versus production data (bare
filenames, multiple trailing slashes). Robust expansion-based code
normalizes first: `p=${p%/}; dir=${p%/*}` — and even then the bare-filename
case needs `case` logic to yield `.`. That is precisely why `dirname`
exists as a command.

### Suffix option (GNU)

`dirname -s` strips a trailing suffix *after* removing the last component:

```bash
$ dirname -s .conf /etc/nginx/nginx.conf
/etc/nginx
$ dirname -s .conf /etc/nginx/
/etc/nginx          # no component left to strip; unchanged
```

It composes with `-a` for batch processing, mirroring
[`basename -s`](./basename.md).

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a`, `--multiple` | Process every operand; one output line each |
| `-s`, `--suffix=SUFFIX` | Also remove a trailing SUFFIX from each result |
| `-z`, `--zero` | End each output line with NUL instead of newline |
| `--` | End of options; needed for paths starting with `-` |

## Usage Patterns

```bash
# Script that operates relative to its own location
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
```

```bash
# Create the parent directory of a target file if missing
mkdir -p -- "$(dirname "$target")"
```

```bash
# Split a path once, use both halves
p=/srv/data/2026/10/report.csv
d=$(dirname "$p"); b=$(basename "$p"); echo "in $d, file $b"
```

```bash
# Walk config directories two levels up from found files
find /etc -name '*.conf' -exec dirname {} \; | sort -u
```

```bash
# Batch: directories of every hit in one process
printf '%s\n' /usr/bin/[a-z]* | xargs -n1 dirname | sort -u | head
```

```bash
# NUL-safe with hostile filenames
find /tmp -name '*.tmp' -print0 | xargs -0 -n1 dirname -z
```

```bash
# Install a file preserving its relative directory layout
rel=$(dirname "${src#/srv/pool/}"); mkdir -p "/srv/dest/$rel"
```

```bash
# Guard: only act on files directly inside /etc
[ "$(dirname "$f")" = /etc ] && process "$f"
```

```bash
# Derive a sibling path: /a/b/tool -> /a/bin/tool
d=$(dirname "$0"); exec "$d/../bin/tool" "$@"
```

## Nuances and Gotchas

- **`${var%/*}` silently passes bare filenames through.** The single most
  common dirname bug: `dir=${p%/*}` on `file.txt` yields `file.txt`, then
  `mkdir -p file.txt` creates a directory named after the file. Either use
  `dirname` or add explicit case handling.
- **Multiple trailing slashes:** `${var%/*}` removes only one slash; 
  `dirname` normalizes all of them. Paths ending `//` from string
  concatenation are exactly where the two diverge.
- **`dirname` never creates, checks, or resolves anything.** `dirname
  /nonexistent/x/y` prints `/nonexistent/x`, exit 0. Symlinks, mounts, and
  existence are irrelevant; for the *physical* directory use
  `cd ... && pwd -P` (as in the script-location pattern above).
- **`.` for bare filenames is correct, not a quirk.** It makes
  `cd $(dirname "$0")` valid for `./script.sh` (→ `.`) and `script.sh` on
  PATH (→ whatever PATH dir, since `$0` is absolute there).
- **`dirname a b` without `-a`** is a usage error on GNU (no silent
  concatenation); scripts relying on the historical BSD behavior of
  ignoring extra operands break.
- **Unquoted variables re-split on spaces** before dirname even runs —
  `dirname $p` with `p="/my dir/f"` yields `/my`. Quote: `dirname "$p"`.
- **`-s` composes left-to-right:** first the last component is removed,
  then the suffix is matched against the remainder. Suffix matching on the
  full input is a misreading that shows up in bug reports.
- **Performance:** one `dirname -a` process beats a shell loop of
  substitutions only when inputs arrive via pipeline; inside a pure-shell
  loop over variables, expansions win. Choose by data flow, not habit.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Output printed successfully |
| nonzero | Usage error: no operand, unknown option, `-s` without `-a` semantics conflict |

As with `basename`, filesystem state cannot affect the exit status.

## Related Commands

- [`basename`](./basename.md) — the mirror operation: prints the final component instead of removing it
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- [bash](../../shell/bash.md) — parameter expansion (`${var%/*}`) semantics and quoting rules behind the comparison table

## Interview Questions

### Q: What do `dirname file.txt`, `dirname /`, and `dirname a/b/` print, and why is each the "right" answer?

`file.txt` → `.`: a bare filename's directory is the current directory, so
`cd $(dirname f)` and `mkdir $(dirname f)` behave correctly. `/` → `/`: the
root has no parent, and printing empty would break `mkdir -p` and `cd`
usages. `a/b/` → `a`: trailing slashes are stripped *before* the last
component is removed, so `a/b/` is the directory `a` containing `b`, not
`a/b` containing nothing. These three cover nearly every dirname interview
question because each rules out a different naive implementation.

### Q: Your script does `dir=${p%/*}` and works in staging but creates bogus directories in production. What class of input difference explains it?

Production inputs include bare filenames (no slash) or values with multiple
trailing slashes. `%/*` on a slash-less string matches nothing and returns
the string itself, so `dir` silently becomes the filename; with `a/b//` it
returns `a/b` (only one slash removed). `dirname` normalizes both cases to
`.`, `/`, and `a` respectively. Fix by using `dirname`, or by normalizing
(`p=${p%/}`) and case-handling the no-slash situation — the underlying
lesson is that expansion and dirname are not drop-in equivalents.

### Q: Why does the canonical "script directory" snippet use `cd ... && pwd` after dirname instead of just dirname's output?

`$(dirname "$0")` yields a *logical* path that may contain `.`, `..`,
symlinks, or relative components. To hand other code an absolute,
symlink-resolved directory you `cd` into it and capture `pwd -P`, which
resolves symlinks in the whole path. dirname performs string surgery only;
it cannot resolve anything because it never touches the filesystem.

### Q: When is `dirname -a` actually faster than per-item shell expansion, given that expansions avoid fork+exec?

When the inputs already flow through a pipeline: `find ... -print0 |
xargs -0 dirname -z` pays one process for the entire set, while an
expansion-based loop pays shell-internal cost per item *plus* keeps the
data in shell variables (quoting risk). For data already in variables and
processed in place, expansions win. The trade is about data flow location,
not raw operation speed — a good answer names both sides.

### Q: POSIX requires only the single-operand form. What breaks in a script that uses GNU `-a`/`-s` on a minimal busybox system?

BusyBox dirname implements `-a`/`-s` only in recent versions; on older
builds the invocation fails with an invalid-option error, and worse, the
script may have composed `dirname -s .conf "$p"` expecting suffix
stripping and instead gets an error and empty output — failing *open* if
the result is used unguarded. The robust pattern is feature-testing
(`dirname -a </dev/null 2>/dev/null || fallback`) or restricting to the
POSIX form and doing suffix work with expansions on dirname's output.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/dirname.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
