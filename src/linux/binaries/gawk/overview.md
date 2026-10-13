# gawk — GNU awk and the awk-implementation collection

## Overview

`awk` is a field-oriented pattern-scanning *language* — and, unusually for
this book, a collection question: Debian ships several independent
implementations of it behind one `awk` name. The GNU implementation
(`gawk`) is the de-facto reference and superset; `mawk` is the small, very
fast interpreter that minimal systems actually get; `original-awk` is
Kernighan's own maintained C implementation; busybox carries an applet
subset. Debian resolves the generic name through `update-alternatives`, so
*what runs when you type `awk` is a system property, not a language
property* — verified on this container:

```
$ readlink -f "$(command -v awk)"
/usr/bin/mawk          # via /etc/alternatives/awk -> /usr/bin/mawk
$ awk --version
mawk 1.3.4 20250131    # gawk is not installed here
```

| Field | Value |
| --- | --- |
| Package | `gawk` (GNU); also `mawk`, `original-awk`; virtual package `awk` |
| Section | 1 |
| Path | `/usr/bin/gawk`; generic `awk` via `/etc/alternatives/awk` |
| This container | mawk 1.3.4.20250131-1 owns `awk`; gawk absent (verified) |
| First appeared | Bell Labs 1977 (Aho, Weinberger, Kernighan — the initials) |
| Standards | POSIX awk grammar; gawk adds a documented extension layer |

The language's usage depth — records and fields, patterns and actions,
arrays, one-liner idioms — lives in the shell track's combined page:
**[sed & awk in the shell track](../../shell/sed-awk.md)** is the deep
reference this page links to and never re-teaches. This page adds what a
hub must: which implementations exist, what only gawk supports, where the
POSIX grammar ends, and how scripts should behave when `awk` might be any
of four programs.

## Package inventory — awk is an alternatives target

Debian treats awk like an editor or a Java runtime: several packages
provide it, one symlink decides it. That machinery is the interview-relevant
part of the packaging story:

```
/usr/bin/awk  →  /etc/alternatives/awk  →  (gawk | mawk | original-awk)
        slaves: /usr/bin/nawk, /usr/share/man/man1/awk.1.gz
```

- The packages `gawk`, `mawk` and `original-awk` all register an
  alternatives group named `awk`; auto mode keeps whichever has the higher
  priority — when gawk is installed it normally wins, and the generic
  `awk`, `nawk` man link move with it.
- **Minimal images usually have only mawk** — as this container does
  (`update-alternatives --display awk` shows auto mode pointing at
  `/usr/bin/mawk`). Docker slim images and CI runners are frequently
  mawk-only, which is exactly where "works on my gawk laptop" scripts die.
- Ground-truth checks that work everywhere:

  ```bash
  readlink -f "$(command -v awk)"        # which implementation owns awk
  update-alternatives --display awk      # the Debian decision record
  awk --version 2>&1 | head -1           # gawk prints "GNU Awk", mawk "mawk …"
  ```

## The four awks

| | gawk | mawk | original-awk | busybox awk |
| --- | --- | --- | --- | --- |
| Debian package | `gawk` | `mawk` | `original-awk` | `busybox` |
| Binary | `/usr/bin/gawk` | `/usr/bin/mawk` | `/usr/bin/original-awk` | busybox applet |
| Lineage | GNU rewrite (Arnold Robbins, since the late 1980s) | Michael Brennan 1988–96; revived by Thomas E. Dickey | Kernighan's maintained "one true awk" | embedded subset |
| Personality | superset: POSIX + extensions | lean, fast, POSIX-plus-minimal | closest to the language as the book defines it | initramfs/rescue minimalism |
| `PROCINFO` | yes | no (verified: empty here) | no | no |
| `-i inplace` | yes | no (verified: `not an option: -i`, rc 2) | no | no |
| `\|&` coprocesses | yes | no | no | no |
| `gensub()`, `RT`, `FPAT` | yes | no | no | no |
| Multi-char regex `RS` | yes | no (single char) | no | no |
| `-M` big numbers, `--sandbox`, `--debug`, `-p` profiler | yes | no | no | no |

The practical split: **gawk** when you need the extension layer or the
best diagnostics; **mawk** when the script is POSIX-shaped and speed or
image size matters; **original-awk** when you want the authors' own
semantics; **busybox awk** when you are inside an initramfs and `gawk`
does not exist. A portable script targets the *intersection*; a gawk
script should say so (shebang or runtime guard).

## Synopsis

```
awk [-F fs] [-v var=value] 'program' [file...]
awk [-v var=value] -f progfile [file...]
gawk [GNU or POSIX options] -f progfile [--] [file...]
```

The program is a series of `pattern { action }` pairs; the shell page holds
the grammar. What varies by implementation is the option surface and the
library of built-in extensions — which is why the same one-liner can be
valid on one Debian box and a syntax error on the next.

## How It Works — the POSIX grammar boundary

The POSIX awk grammar draws a line that all four implementations respect,
and the interview question "what can I rely on?" has a precise answer:

```
  POSIX awk (the shared core)                implementation-specific
  ────────────────────────────────────       ─────────────────────────
  pattern { action } pairs                   PROCINFO array (gawk)
  records/fields: RS, FS, NR, NF, $0..       -i inplace / -l lib (gawk)
  dynamic regexes with ~ and !~              coprocesses  "cmd" |& getline
  associative arrays, delete                 gensub(), RT, FPAT (gawk)
  printf, length, substr, split, sub/gsub    switch statement (gawk)
  user functions, getline variants, exit     -M bignum, /inet sockets (gawk)
  fflush, END/ BEGIN blocks                  -W extended options (mawk)
```

Two boundary notes worth being able to defend:

1. **The 2024 POSIX revision folded in long-standing practice** — items
   like whole-array `delete arr` and the `func` alias that all modern
   implementations already supported. The *extension layer* (right column)
   remains explicitly outside POSIX and outside the portability guarantee.
2. **gawk is POSIX-plus by design**: `gawk --posix` (or `-P`) turns the
   extensions off and enforces the grammar; `gawk --traditional` emulates
   the 1985 awk. Both are the cleanest way to *test* whether a script
   really is portable rather than to hope it is.

Runtime detection — the guard that makes a gawk script fail loudly instead
of subtly (verified on this container: mawk evaluates the condition false):

```bash
awk 'BEGIN {
  if (PROCINFO["version"] != "") print "gawk", PROCINFO["version"];
  else                           print "not gawk — extensions unavailable"
}'
```

## Options That Matter

Portable core (all awks):

| Option | Effect |
| --- | --- |
| `-F fs` | field separator (one char, or an ERE as a string) |
| `-v var=value` | assign program variables before the first record |
| `-f progfile` | read the program from a file — the shebang-friendly form |
| `--` | end of options; everything after is data |

gawk-only surface (the ones interviewers probe):

| Option | Effect |
| --- | --- |
| `-i inplace` | in-place edit extension — sed-like temp+rename semantics |
| `-l lib` | load an awk library (e.g. `-l time`, `filefuncs`) |
| `-M` | arbitrary-precision numbers via GMP/MPFR |
| `-P` / `--posix` | disable extensions, enforce the POSIX grammar |
| `-c` / `--traditional` | emulate historical awk, extensions off |
| `-p` / `--profile` | profiler; `-o` pretty-printer; `--debug` (was `dgawk`) |

mawk extends through its own channel — `-W` options (`mawk -W usage`) —
which is how it stays POSIX-clean while still offering knobs.

## Usage Patterns

```bash
# Know your awk before writing a one-liner against it
readlink -f "$(command -v awk)"
```

```bash
# Fail loudly on a mawk-only box instead of misbehaving subtly
awk 'BEGIN{ if (PROCINFO["version"]==""){ print "needs gawk" | "cat >&2"; exit 1 } }' input
```

```bash
# The portable subset: works identically on gawk, mawk, busybox
awk -F: '$3 >= 1000 { print $1 }' /etc/passwd
```

```bash
# gawk's in-place edit — note the temp+rename, same caveats as sed -i
gawk -i inplace '{ gsub(/old\.example\.com/, "new.example.com"); print }' hosts.txt
```

```bash
# Column report: totals without leaving the shell
awk -F, 'NR>1 { sum += $3 } END { printf "%.2f records-summed=%d\n", sum, NR-1 }' data.csv
```

```bash
# Deliberately use mawk for a big ETL pass (direct path bypasses alternatives)
/usr/bin/mawk -F'\t' '{ n[$1]++ } END { for (k in n) print n[k], k }' big.log
```

```bash
# Pin the implementation for a team script: gawk if present, else fail
AWK=$(command -v gawk) || { echo "gawk required" >&2; exit 1; }
"$AWK" -v tag=nightly -f jobs.awk data/
```

```bash
# The portable shebang form — implementation chosen by the system
#!/usr/bin/awk -f
NR == 1 { print "first record:", $0 }
```

## Nuances and Gotchas

- **`awk` is whoever owns the alternative.** A script that runs on your
  gawk workstation and crashes on a CI container is almost always using
  gawk extensions (`-i`, `gensub`, `PROCINFO`, `|&`) behind the generic
  name. Decide per script: POSIX subset through `awk`, or an explicit
  `gawk` dependency (shebang or guard).
- **`-i inplace` is not sed's `-i` either**: gawk-only (mawk exits with
  *not an option: -i*, verified) and implemented by redirecting output to
  a temporary file renamed over the original — new inode, symlinks
  unlinked, same class of surprises as `sed -i`.
- **`PROCINFO` evaluates falsy elsewhere** — on mawk, referencing it
  yields an empty value rather than an error (verified), so truthiness
  guards *work* — but `PROCINFO["sorted_in"]`-style use silently
  mis-sorts on mawk.
- **Multi-char `RS` is gawk territory.** POSIX `RS` is a single character
  (or empty for paragraph mode); gawk accepts full regexes — treat regex
  `RS` scripts as gawk scripts.
- **CSV is not awk's job in POSIX**: `FS=","` splits quoted commas too;
  gawk's `FPAT` handles quoted fields, portable code changes the format.
- **mawk is fast for a reason**: it is a smaller interpreter with less
  per-record machinery; for POSIX-shaped programs over big files it is
  routinely the fastest awk — but it will *reject* rather than approximate
  gawk features, which is the right behavior to rely on.
- **Numeric formatting stays C-locale** (dot decimal) unless gawk is
  explicitly asked for locale numerics (`--use-lc-numeric`).
- **Whole input lives in memory when you use arrays** — every awk holds
  arrays in RAM; `awk '{ seen[$0]=1 } END { ... }' hugefile` is a memory
  cliff, not a speed cliff. `sort -u` or `sort | uniq` scale differently.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | program completed normally |
| >0 | syntax error or fatal runtime error (gawk: 2; exact value is implementation-defined) |
| N | explicit `exit N` — in the main body it jumps to `END`; an `exit N` *inside* `END` wins |

Note the awk-specific subtlety: `exit` without a value keeps the status
so far, and a fatal I/O error overrides a later plain `exit` — scripts that
need a guaranteed status compute it explicitly in `END`.

## Related Commands

- [sed & awk deep dive](../../shell/sed-awk.md) — the language itself:
  patterns, actions, arrays, getline, hold-space sed side of the pair.
- [`bash`](../../shell/bash.md) — how one-liners get quoted and where
  `-v var="$shellvar"` fits the pipeline.
- [Man pages](../../reference/man-pages.md) — gawk's info manual is the
  reference implementation's book-length documentation.
- [Part overview](../overview.md) — the other userland binary collections.

## Interview Questions

### Q: On a Debian system, what decides which awk runs when you type `awk`?

The `awk` alternatives group. `gawk`, `mawk` and `original-awk` all
register providers; `update-alternatives` in auto mode points
`/usr/bin/awk` (and the `nawk` slave and `awk.1.gz` man page) at the
highest-priority one — normally gawk when installed. On minimal images
only mawk is present, so `awk` is mawk; this container is exactly that
case (`/etc/alternatives/awk -> /usr/bin/mawk`).

### Q: Name three gawk-only features and the correct way to guard a script
that uses them.

`PROCINFO` (runtime info, sorted_in), `-i inplace`, and coprocesses with
`|&` (plus `gensub`, `RT`, `FPAT`). Guard by either targeting gawk
explicitly — shebang `#!/usr/bin/gawk -f` or invoking `gawk` — or testing
at runtime (`if (PROCINFO["version"] == "") exit 1`), which fails loudly
on mawk where the feature call would otherwise fail mid-script.

### Q: What is the division of labor between sed and awk?

sed edits *text*: one pattern space, one hold space, transformation of
records — strongest at substitutions, deletions, in-place edits. awk
processes *fields*: it splits each record and runs a real language with
variables, arrays and arithmetic — strongest at selection by column,
aggregation and reports. Rule of thumb: substitute with sed, compute with
awk; when a sed script grows hold-space gymnastics, move to awk.

### Q: Why would a data team deliberately choose mawk over gawk?

For POSIX-shaped programs, mawk is smaller and routinely faster: less
per-record machinery, quicker startup, lower memory. ETL-style pipelines
that stay inside the POSIX grammar get the same results faster — and mawk
*rejects* gawk extensions instead of approximating them, so the team gets
a portability enforcement for free. The trade is losing the extension
layer (in-place, gensub, FPAT, bignum).

### Q: Where exactly does the POSIX awk grammar end?

At the extension layer: no `PROCINFO`, no `-i`/`-l` include/library
mechanism, no `|&` coprocesses, no `gensub`/`RT`/`FPAT`, no `switch`
statement, no arbitrary-precision math, single-character `RS`. The 2024
revision folded in de-facto items like whole-array `delete` and the `func`
alias, but everything in gawk's documented "extensions" appendix remains
out. `gawk --posix` is the practical conformance test.

### Q: How does `gawk -i inplace` actually work, and what are the failure
modes?

It loads the `inplace` extension library, which redirects awk's output to
a temporary file and renames it over the original when the program ends.
Consequences mirror `sed -i`: new inode (symlinks and hardlinks severed),
write permission needed on the *directory*, temp file left behind on
abnormal termination. Add `inplace::suffix` for per-file backups.

## References

- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/gawk/)
- [Source — Debian sources](https://sources.debian.org/src/gawk/)
- [Deep dive — shell track](../../shell/sed-awk.md)
