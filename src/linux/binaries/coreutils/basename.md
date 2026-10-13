# basename — strip directory components and suffixes from paths

## Overview

`basename` removes the directory part of a pathname, optionally also removing
a trailing suffix, and prints the remainder. Given `/etc/nginx/nginx.conf` it
prints `nginx.conf`; given `archive.tar.gz` with suffix `.gz` it prints
`archive.tar`. It is the canonical companion of [`dirname`](./dirname.md):
together they split a path into directory and file components.

The binary ships in the Debian `coreutils` package at `/usr/bin/basename`.
Unlike [`echo`](./echo.md) there is no shell builtin competition worth worrying
about — every invocation is a real process — which matters for performance in
tight loops (see the parameter-expansion comparison below).

`basename` is the POSIX-standardized way to answer "what is this entry called
in its parent directory". Shell parameter expansion (`${var##*/}`) answers the
same question without forking a process; the trade-offs are real and covered
in How It Works. You reach for `basename` when the input comes from a
pipeline (find, git, awk output), when you also need suffix stripping, or when
clarity outranks the saved fork.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/basename` on modern Debian/Ubuntu |
| First appeared / lineage | 7th Edition UNIX; present in every Unix since |
| Standards | POSIX.1-2018 (`basename`) |

## Synopsis

```
basename NAME [SUFFIX]
basename OPTION... NAME...
```

Main forms:

```bash
basename /usr/local/bin/sort        # -> sort            (directory strip)
basename file.tar.gz .gz            # -> file.tar        (two-operand suffix form)
basename -s .gz file.tar.gz         # -> file.tar        (preferred -s form)
basename -a -s .md README.md NOTES.md   # -> README NOTES (multiple operands)
```

## How It Works

`basename` performs pure string processing on its argument — it never touches
the filesystem, so the path need not exist. The algorithm, per POSIX with GNU
refinements:

1. Delete all trailing `/` characters (unless that would delete everything).
2. If nothing remains, the result is `//`-handled specially (see below); else
   the result is the substring after the last remaining `/`.
3. If a suffix is given and the remainder *ends* with it, delete the suffix.
4. Print the result and a newline.

```bash
$ basename /usr/local/bin/sort
sort
$ basename /usr/local/bin/sort/      # trailing slashes deleted first
sort
$ basename /
/
$ basename //
/
$ basename usr
usr
```

The empty-ish inputs are the only surprising corners: `basename /` prints `/`
(there is no name "below" the root), and `basename /` with any number of
trailing slashes still prints `/`. For any non-root path the result is never
empty.

### Suffix stripping rules

The suffix is removed only if the name **ends** with it, and only once:

```bash
$ basename foo.txt .txt
foo
$ basename foo .txt        # suffix not present: name unchanged
foo
$ basename foo.txt.txt .txt
foo.txt                    # stripped once, not recursively
$ basename -s .tar.gz file.tar.gz
file                       # compound suffix works with -s
$ basename file.tar.gz .tar.gz
file                       # ... and with the operand form too
```

Note `basename foo.txt txt` prints `foo.` — the dot is not special; the suffix
is a literal string. The common idiom `$(basename "$f" .ext)` for "change the
extension" fails on files without the extension only in the sense that the
name comes back unchanged, which is usually what you want.

### Two-operand vs `-s`

`basename NAME SUFFIX` is the POSIX spelling; `basename -s SUFFIX NAME...` is
the GNU spelling that generalizes to multiple operands. They differ in one
trap: in the two-operand form there is no way to distinguish "suffix" from
"second path", and `-a` cannot be combined with the operand form. Prefer
`-s`/`-a` in new code; keep the operand form for POSIX-only shells.

```
input: /var/log/app/2026-10-09.log     suffix: .log
       │                         │
       ▼ trailing '/' removed    ▼ literal suffix match
     "2026-10-09.log"  ────────► "2026-10-09"
```

### basename vs ${var##*/}

In bash, `${var##*/}` deletes the longest prefix ending in `/` — the same
string operation, no subprocess:

| Aspect | `basename` | `${var##*/}` |
| --- | --- | --- |
| Cost per call | fork+exec (~1 ms) | sub-microsecond |
| Trailing slashes `/a/b/` | `b` | empty string |
| Root `/` | `/` | empty string |
| Suffix stripping | built in (`-s`) | needs a second expansion `${v%.gz}` |
| Multiple inputs in one call | `-a` | one variable at a time |
| Works with `-z`/NUL output | yes | no |
| Portability | every Unix | every POSIX shell (incl. dash) |

The two empty-string cases are the real trap: for `p=/` , `basename /` is `/`
but `${p##*/}` is empty, and for `p=/a/b/` the expansion yields nothing while
`basename` yields `b`. Expansion code that "works on test data" with no
trailing slashes silently breaks on directory paths.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-a`, `--multiple` | Treat every operand as a NAME; print one result per line |
| `-s`, `--suffix=SUFFIX` | Remove trailing SUFFIX from each name; implies `-a` |
| `-z`, `--zero` | Terminate each output line with NUL instead of newline (for `xargs -0`) |
| `--` | End option processing; required to handle names starting with `-` |

`-s` implies `-a`, so `basename -s .md README.md NOTES.md` is valid without a
separate `-a`. The two-operand `NAME SUFFIX` form cannot be mixed with `-a`.

## Usage Patterns

```bash
# Strip the directory from each hit of a find walk
find /etc -name '*.conf' -exec basename {} \;
```

```bash
# Loop over basenames once, cheaply, with -a
basename -a /usr/bin/[a-z]* | head -20
```

```bash
# Rename *.log to *.txt preserving the stem
for f in *.log; do mv -- "$f" "$(basename -s .log "$f").txt"; done
```

```bash
# Derive a service name from an init script path
svc=$(basename -s .sh /etc/init.d/fail2ban.sh)   # -> fail2ban
```

```bash
# NUL-safe processing of weird filenames through xargs
printf '/tmp/a\nb.txt\0' | basename -az | xargs -0 -n1 echo got:
```

```bash
# Show only the failing test file names from a log
grep '^FAIL ' results.txt | awk '{print $2}' | xargs -n1 basename
```

```bash
# Branch on the file name, not the full path
case $(basename "$0") in deploy.sh) MODE=prod;; test.sh) MODE=ci;; esac
```

```bash
# Combine with dirname for a full split
p=/etc/nginx/sites-enabled/default
d=$(dirname "$p"); b=$(basename "$p"); echo "dir=$d base=$b"
```

```bash
# Strip both container layers of a registry image reference
img=registry.example.com/team/api:1.4.2
echo "repo=$(basename "${img%%:*}")"
```

## Nuances and Gotchas

- **`${var##*/}` returns empty where `basename` returns `/` or the last
  component.** If your variable can end in `/` or be exactly `/`, the
  expansion is not equivalent — either normalize with
  `p=${p%/}` first or use `basename`.
- **Suffix is stripped once and only if present.** `file.tar.gz` with suffix
  `.gz` becomes `file.tar`; a recursive "strip all extensions" loop needs
  `while` iteration or `sed`.
- **The suffix is a literal string, not a pattern.** `basename x.txt '*'`
  will not match anything special; `basename x.txt .t*` treats `.t*` literally
  too. Wildcard expectations are a recurring bug report.
- **Nonexistent paths are fine.** `basename /no/such/file` prints `file`,
  exit 0. Some scripts mistakenly use basename as an existence check.
- **`--` matters.** `basename -s .md -funky.md` fails to do what you expect
  (the name looks like an option). Use `basename -s .md -- -funky.md`.
- **POSIX leaves one corner open:** the result of `basename //` is
  implementation-defined (POSIX requires `/` for a single slash but allows
  `//` to be special as on Cygwin). GNU prints `/`.
- **Performance:** in a loop over thousands of files, `${f##*/}` beats
  `$(basename "$f")` by orders of magnitude; but when the value flows through
  `xargs`/`awk` anyway, `basename -a` in one process is the cheapest form.
- **Obsolescent form:** POSIX marks `basename string suffix` as kept only for
  compatibility; GNU help text calls it obsolete. New scripts use `-s`.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Output printed successfully |
| nonzero | Usage error: no operand, or `-s`/`-a` mixed with the two-operand form |

With no arguments at all, GNU basename prints usage to stderr and exits 1.
Filesystem state can never affect the exit status (no path is ever opened).

## Related Commands

- [`dirname`](./dirname.md) — the mirror operation: prints everything before the last `/`
- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- [`echo`](./echo.md) — the other string-processing coreutils tool with expansion-based alternatives
- Shell parameter expansion (`${var##*/}`) — covered in the bash scripting page: [bash](../../shell/bash.md)

## Interview Questions

### Q: What does `basename /` print and why?

A single `/`. POSIX specifies that after deleting trailing slashes nothing is
left, and the standard defines the result for that case as `/` — the root has
no name below it. Related: `basename /a/b/` deletes the trailing slash first
and prints `b`. This pair of cases is exactly where shell
parameter expansion `##*/` behaves differently (empty string), so interviewers
use it to probe whether you really know both tools.

### Q: You need `report-2026-10-09` out of `/srv/data/report-2026-10-09.tar.gz`. Write the call and explain the suffix rule.

`basename -s .tar.gz /srv/data/report-2026-10-09.tar.gz` prints
`report-2026-10-09`. The suffix is a literal string removed only when the
final component ends with it, and removed exactly once — so `.tar.gz` is
matched as a whole; giving only `.gz` would leave `report-2026-10-09.tar`.
The directory part is irrelevant to the suffix step; stripping happens after
the last `/` is cut.

### Q: When would you still choose `basename` over `${var##*/}` in a bash script despite the fork cost?

Three situations: when the input may end in `/` (expansion gives the wrong
answer, basename normalizes); when a suffix must be stripped at the same time
(one call instead of two expansions and a correctness re-check); and when the
data is already outside a shell variable — `find ... | xargs basename -a` or
`basename -az` for NUL safety processes all inputs in one process, which is
faster than a shell loop doing expansions.

### Q: Why does `basename file.txt .txt` not become a security problem with attacker-controlled input, while `basename $unquoted` does?

`basename`'s suffix handling is pure string logic, so the first form is safe.
The real hazard is the *unquoted* variable in shell context: a value
containing spaces becomes multiple operands (with `-a` semantics triggered by
accident, or a usage error), and a value starting with `-` is parsed as an
option. The fix is the same in both cases: quote the operand and use `--`.

### Q: `basename -s .md README.md` and `basename README.md .md` — which is POSIX and which is the portable-across-implementations choice?

The two-operand form `basename README.md .md` is the POSIX spelling and works
everywhere including minimal busybox. `-s` is a GNU extension (also present on
BSDs and in busybox in recent versions) that additionally supports multiple
operands via implied `-a`. For strict-POSIX scripts pick the operand form;
otherwise `-s` is clearer and safer because it cannot be confused with a
second path.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/basename.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
