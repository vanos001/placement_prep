# mktemp — race-free temporary file and directory creation

## Overview

`mktemp` creates a temporary file or directory whose name did not exist
before the call, prints that name to stdout, and exits. The name is derived
from a template you supply (`/tmp/build_XXXXXXXX`) by replacing each `X`
with random characters; the file is created atomically with `open(O_CREAT |
O_EXCL)`, so either the name is brand new or the call fails — there is no
window in which an attacker can slip a symlink into place between the
existence check and the creation.

That guarantee is the entire point. The older shell idiom
`tmpfile=/tmp/myapp.$$` derives a name from the PID, which is predictable:
an attacker who can write to `/tmp` pre-creates a symlink at that path
pointing at, say, `/home/you/.ssh/authorized_keys`, and your script follows
it on first write. `mktemp` was written on OpenBSD specifically to kill
that bug class (insecure temporary files, CWE-377), and it is now the
standard answer in shell, Makefiles, and any POSIX-ish language.

Debian ships it in `coreutils` at `/usr/bin/mktemp`; it is not a POSIX
utility, but every mainstream system (GNU, BSD, macOS, BusyBox) provides a
compatible core. Do not confuse it with the obsolete C library function
`mktemp(3)`, which had exactly the race this command fixes and has been
removed from modern libc — same name, opposite lesson.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/mktemp` on modern Debian/Ubuntu |
| First appeared / lineage | OpenBSD 2.1 (1997, Todd C. Miller); adopted by GNU coreutils in the 5.1 era (2003); Debian's once-separate `mktemp` package has been absorbed into coreutils |
| Standards | Not in POSIX; de-facto standard across GNU/BSD/macOS/BusyBox |

## Synopsis

```
mktemp [OPTION]... [TEMPLATE]
```

Main forms:

```bash
mktemp                              # default: /tmp/tmp.XXXXXXXXXX (file)
mktemp /var/tmp/build_XXXXXXXX      # file from a template
mktemp -d myapp_XXXXXXXX            # directory instead of a file
mktemp --suffix=.json cfg_XXXXXX    # template need not end in X
mktemp -u demo_XXXXXX               # dry-run: print a name, create nothing
```

With no TEMPLATE, mktemp uses `tmp.XXXXXXXXXX` in `/tmp` (or `$TMPDIR`),
which is why `--tmpdir` is implied in that case.

## How It Works

### Name generation and the O_EXCL guarantee

For each `X` in the template's final component, mktemp substitutes a random
character from the 62-character set `a-z A-Z 0-9`. It then attempts to
create the file with `open(..., O_CREAT|O_EXCL, 0600)`. `O_EXCL` is the
load-bearing part: the check-and-create is a single atomic syscall, so the
classic TOCTOU symlink attack against a *checked-then-opened* path cannot
succeed. If the name is taken (or was pre-planted), mktemp picks another
random name and retries; if creation still fails, it reports failure and
exits nonzero.

```
   predictable name                      mktemp name
   /tmp/myapp.$$                         /tmp/tmp.Gk7Qz3XpW9
   ┌─────────────────────┐               ┌─────────────────────────┐
   │ attacker knows PID  │               │ attacker cannot guess   │
   │ space in advance    │               │ the name beforehand     │
   │ pre-links symlink → │               │ O_CREAT|O_EXCL: atomic  │
   │ victim writes there │               │ create-or-fail, no gap  │
   └─────────────────────┘               └─────────────────────────┘
```

Entropy scales with the number of `X`s: 6 trailing Xs give 62^6 ≈ 5.7×10^10
candidates, the default 10 give 62^10 ≈ 8.4×10^17. Collisions are handled by
retry, not by panic.

### The template rules

- The template must contain **at least 3 consecutive `X`s in the last
  path component**. `mktemp foo_XX` fails with
  `mktemp: too few X's in template 'foo_XX'` and exit status 1.
- `X`s must sit in the final component: `mktemp /tmp/x_XXXX` is fine,
  but the random part is always appended where the `X` run is.
- If the template does not end in `X` (`log_XXXXXX.json`), everything
  after the last `X` is treated as an implicit `--suffix`.
- A relative template (`foo_XXXX`) creates in the current directory —
  sometimes exactly what you want for scratch files tied to a repo.

```bash
$ mktemp foo_XXXX
foo_zvi3
$ mktemp foo_XX
mktemp: too few X's in template 'foo_XX'
$ mktemp log_XXXXXX.json
log_IOqTPX.json
```

### Where it creates: TMPDIR, -p, -t

Resolution order for the directory: an absolute template wins outright;
otherwise `-p DIR` / `--tmpdir=DIR`; otherwise `$TMPDIR` if set; otherwise
`/tmp`. Bare `--tmpdir` (no argument) means "honor `$TMPDIR`, else `/tmp`",
and is implied when no template is given at all. The deprecated `-t` flag
changes interpretation of the template (single file-name component relative
to the resolved directory) — see the gotchas section.

```bash
$ export TMPDIR=/var/tmp
$ mktemp
/var/tmp/tmp.016ClXQEJy
$ mktemp -p /var/tmp
/var/tmp/tmp.qPn5RWAxoJ
```

### Modes: 0600 files, 0700 directories

mktemp creates files with mode `u+rw` (0600) and directories with `u+rwx`
(0700), minus any further restriction from the umask. The tight default is
deliberate: a temp file often holds secrets (credentials, unencrypted
data), and group/other read must never leak by accident. Files you create
*inside* a `mktemp -d` directory inherit the umask as usual.

```bash
$ F=$(mktemp); stat -c '%a' "$F"
600
$ D=$(mktemp -d); stat -c '%a' "$D"
700
```

### The lifecycle pattern

mktemp only creates; it never cleans up. The canonical shell pairing is
command substitution plus a trap so the file dies with the script:

```bash
tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
work_in "$tmp"
```

`EXIT` fires on normal exit and on signals that bash translates to exit
(INT, TERM); the `|| exit 1` guarantees you never trap an empty variable.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-d`, `--directory` | Create a directory (0700) instead of a file (0600) |
| `-p`, `--tmpdir[=DIR]` | Interpret TEMPLATE relative to DIR; bare `-p` honors `$TMPDIR` then `/tmp` |
| `--suffix=SUFF` | Append SUFF after the random part; implied when TEMPLATE does not end in `X`; SUFF must not contain a slash |
| `-q`, `--quiet` | Suppress diagnostics about creation failure (exit status still 1) |
| `-u`, `--dry-run` | Print a candidate name but create nothing — reintroduces the race; avoid |
| `-t` | Interpret TEMPLATE as one name component relative to `$TMPDIR`/`-p`/`/tmp` — deprecated in GNU, and means something *different* on BSD |

## Usage Patterns

```bash
# Scratch file for one command's intermediate data
out=$(mktemp) || exit 1
```

```bash
# The standard safe pattern: create, trap, use
tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT
curl -s "$url" -o "$tmp/page.html"
```

```bash
# A directory per build so many files share one cleanup trap
build=$(mktemp -d /tmp/build_XXXXXXXX)
```

```bash
# Tools that insist on an extension (compilers, editors, parsers)
src=$(mktemp --suffix=.c probe_XXXXXX)
```

```bash
# Respect the user's or job's temp location
TMPDIR=/mnt/bigscratch mktemp -d
```

```bash
# Quiet failure inside a bigger pipeline where the message would mislead
f=$(mktemp -q 2>/dev/null) || { echo "no writable tmp"; exit 1; }
```

```bash
# Same cleanup under set -e, signals, and normal exit alike
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT INT TERM
```

```bash
# Repo-local scratch that never escapes git (template is relative)
scratch=$(mktemp -d ./.scratch_XXXXXX)
```

```bash
# Feed a fifo-like flow: create once, reuse across a function
resp=$(mktemp); trap 'rm -f "$resp"' EXIT
http_code=$(curl -s -o "$resp" -w '%{http_code}' "$url")
```

## Nuances and Gotchas

- **`/tmp/$$` is the bug, mktemp is the fix.** PID-derived names are
  guessable; an attacker with write access to the directory wins the symlink
  race against any check-then-open sequence. Interviewers expect the
  O_EXCL explanation, not just "mktemp is random".
- **mktemp narrows, but does not erase, the race.** The *name* is safe from
  creation onward, but between `mktemp` and your first `open` of that name,
  an attacker who can write to the same directory can still replace it —
  mktemp's `O_EXCL` protected the inode, not your subsequent opens. In
  hostile directories, create a `mktemp -d` directory once (mode 0700 stops
  the attacker entirely) rather than many files.
- **`-u` is a trap door.** It prints a name without creating anything, so
  the atomic-create guarantee vanishes; GNU docs flag it as unsafe, and its
  only legitimate use is generating names where you accept the race (see
  below — usually you don't).
- **Template rules bite quietly.** Fewer than 3 consecutive `X`s in the
  last component is a hard error; `X`s in a non-final component do nothing
  useful; a template not ending in `X` silently turns the tail into a
  suffix. All three are runtime surprises in generated scripts.
- **Portability of `-t`:** GNU's `-t` is deprecated with one meaning
  (component-relative-to-TMPDIR), while BSD/macOS `-t` takes a bare prefix
  with no `X`s at all. Scripts using `-t` break across platforms — use an
  explicit template plus `-p` instead. BusyBox mktemp covers the core form
  and `-d`; `--suffix` and `--tmpdir=DIR` may be absent on minimal systems.
- **`$TMPDIR` is not always set, and `-p` overrides it.** Programs that
  hardcode `/tmp` break in sandboxes or read-only `/tmp` setups; always
  resolve through mktemp so the environment stays configurable.
- **The cleanup trap is part of the contract.** A created-but-abandoned
  temp file in `/tmp` is a leak and a hygiene problem; `trap ... EXIT`
  (and `-d` for multi-file flows) is the house pattern.
- **Modes can only shrink.** 0600/0700 minus umask: you never get 0644
  out of mktemp — if you `chmod` it wider, that is on you.
- **Old `tempfile(1)` scripts:** that utility is gone from modern Debian;
  likewise the libc `mktemp(3)` function is removed — seeing either in
  review is a finding, not a style nit.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | File or directory created; its name printed to stdout |
| 1 | Failure: too few `X`s, unwritable or missing target directory, name collisions exhausted — diagnostics to stderr unless `-q` |

## Related Commands

- [`mkdir`](./mkdir.md) — creates directories but with caller-chosen (colliding) names; mktemp -d adds the safe naming layer
- [`install`](./install.md) — creates files with explicit mode/owner when the name is already safe
- [`chmod`](./chmod.md) — tighten or (rarely) widen the 0600/0700 defaults after creation
- [`env`](./env.md) — run a command with a controlled `$TMPDIR` for reproducible temp placement
- [bash](../../shell/bash.md) — `trap ... EXIT` cleanup and command substitution drive the canonical pattern
- [permissions](../../admin/permissions.md) — why 0600/0700 defaults and hostile-directory semantics matter
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages

## Interview Questions

### Q: Why is `tmpfile=/tmp/myapp.$$` unsafe, and what exactly does mktemp change?

The PID-derived name is predictable, so an attacker who can write to `/tmp`
pre-creates a symlink there pointing at a victim file; the script's first
write follows the link. The attack exploits the gap between checking a path
and opening it. mktemp removes both halves of the problem: the name is
unguessable (62^n random space), and creation is a single atomic
`open(O_CREAT|O_EXCL)` that either makes a fresh inode or fails — there is
no check-then-use window left for the initial create.

### Q: Does mktemp make the file safe forever? What window remains?

It guarantees the created inode is fresh and private (0600), nothing more.
If an attacker can write to the same directory, they can still rename or
replace the path between mktemp and your subsequent opens of that path —
mktemp protected one create, not your whole session. The robust pattern in
shared directories is `mktemp -d` (a 0700 directory the attacker cannot
enter) and doing all work inside it. Truly adversarial cases reach for
fd-based tricks (`/proc/self/fd/N`) or per-user temp dirs.

### Q: How much randomness do the Xs buy, and why does the default template have ten?

Each `X` is one character from a 62-symbol alphabet, so n Xs give 62^n
candidates: six Xs ≈ 5.7×10^10, the default ten Xs ≈ 8.4×10^17. With
`O_EXCL` retries, collisions are just retries, but small templates raise
the odds a hostile pre-planter guesses your name; that is why the man page
pushes more Xs and why the default grew. Three Xs is the floor, not a
recommendation.

### Q: Your script needs several files plus a subdirectory for one job, then everything must vanish. Sketch the mktemp-based layout.

Create one `work=$(mktemp -d)` at the top, derive all paths inside it
(`$work/in.c`, `$work/out`), and install a single
`trap 'rm -rf "$work"' EXIT` right after creation. Directory mode 0700
keeps other users out; one trap covers normal exit, errors, and signals.
This beats multiple `mktemp` files because cleanup is one variable, and
because the directory's tight mode closes the replacement-race window that
individual files in `/tmp` leave open.

### Q: When is `--suffix` genuinely needed rather than cosmetic?

Tools dispatch on extension: compilers (`gcc` wants `.c`/`.o`), editors and
linters pick syntax from the suffix, `file(1)` and web servers guess types.
A temp file holding a `.c` probe or a `.json` payload often must end in the
extension for the downstream tool to accept it, while the random part must
stay before the dot. `mktemp --suffix=.c probe_XXXXXX` (or the implicit
suffix in `probe_XXXXXX.c`) gives both; note the suffix cannot contain a
slash, so it cannot relocate the file.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/mktemp.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
