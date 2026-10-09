# grep — GNU grep: one binary, three pattern engines, four names

## Overview

`grep` is the Unix answer to "which lines contain this?" — and the Debian
package `grep` ships more than its name suggests: one 200 KB binary at
`/usr/bin/grep`, compatibility wrappers (`egrep`, `fgrep`, `rgrep`), and an
info manual. Inside the single binary live several pattern interpreters — BRE
(the default), ERE (`-E`), literal strings (`-F`), and Perl-compatible
regexes (`-P`, backed by libpcre2 on Debian) when built with it.

| Field | Value |
| --- | --- |
| Package | `grep` (Debian; present in every distro and busybox) |
| Section | 1 |
| Path | `/usr/bin/grep`; `/bin/grep` is the usrmerge symlink |
| Also ships | `/usr/bin/egrep`, `/usr/bin/fgrep`, `/usr/bin/rgrep` (sh wrappers), `grep.info` |
| This container | GNU grep 3.11-4, Debian 13 (trixie); `-P` compiled in |
| First appeared | Thompson's `grep`, 1974 (Bell Labs); GNU rewrite 1988 |
| Standards | POSIX `grep` (BRE/ERE); `-P`, `-z`, `--include` are GNU extensions |

The lineage matters for interviews: `grep` was extracted from `ed` — the name
is literally the `ed` script `g/re/p` (global regular-expression print).
Ken Thompson wrote the standalone tool in 1974; the GNU rewrite (Mike
Haertel, late 1980s) added the two-tier engine design still used today.
This page covers the *package*: what ships, how the engines and wrappers
are organized, where it diverges across platforms. The regex dialects and
everyday flag depth live in the shell track —
**[grep in the shell track](../../shell/grep.md)** is the deep reference
this page links to, with **[regex syntax (BRE/ERE/PCRE)](../../shell/regex.md)**
as its companion.

## Package inventory

What `dpkg -L grep` puts on disk (verified on this container):

| File | Role |
| --- | --- |
| `/usr/bin/grep` | the one real binary; all engines live here |
| `/usr/bin/egrep` | 2-line sh wrapper: `exec grep -E "$@"` |
| `/usr/bin/fgrep` | 2-line sh wrapper: `exec grep -F "$@"` |
| `/usr/bin/rgrep` | 2-line sh wrapper: `exec grep -r "$@"` |
| `/usr/share/info/grep.info.gz` | the full GNU manual |
| `/usr/share/doc/grep/` | NEWS (wrapper deprecation history), changelog |

`rgrep` is the one even many sysadmins miss: Debian preserves the historical
standalone name as a wrapper around `grep -r` — and `cat /usr/bin/egrep`
is a legitimate way to answer "what does egrep do on *this* system?".

## Synopsis

```
grep [OPTION]... PATTERNS [FILE]...
grep [OPTION]... -e PATTERN... [-f PATTERN-FILE]... [FILE]...
grep [OPTION]... -r [--include=GLOB] PATTERN DIRECTORY...
```

The four names, all the same engine:

```
grep -E  ==  egrep     # extended regex
grep -F  ==  fgrep     # fixed strings
grep -r  ==  rgrep     # recursive (GNU wrapper)
grep     ==  (default BRE)
```

## How It Works — one binary, three matchers

Every invocation walks the same pipeline; only the matcher stage differs:

```
        pattern text
             │
             ▼
   ┌─────────────────────┐   -G (default)  BRE compiler  ─┐
   │  pattern dispatcher │   -E / egrep     ERE compiler  ├─► DFA / backtracking
   │  (-E -F -G -P)      │   -F / fgrep     literal set    │     matcher
   └─────────────────────┘   -P              PCRE (libpcre2)┘          │
                                                                        ▼
   input (files, dirs, stdin) ──► line/binary scanner ──► output layer
                                        │                (-n -l -L -c -o
                                        ▼                 -q --color -A/-B/-C)
                                 binary detection
                                 ("Binary file matches" / -a)
```

Design points worth being able to explain:

1. **The dispatcher is the flag set, not four programs.** `-E`/`-F`/`-P`
   select which *compiler* builds the internal matcher from the same pattern
   string — which is why `grep -F -E` is an error: one dispatcher, one engine.
2. **`-F` is the performance escape hatch.** Fixed-string matching uses a
   Boyer–Moore-family algorithm over the whole line, skipping characters in
   bulk instead of simulating a state machine. Rewriting a slow alternation
   of literals as `grep -F -f patterns.txt` is the classic speed fix.
3. **`-P` is a different world, and optional.** PCRE brings lookaround,
   non-greedy quantifiers, `\K`, even NUL matching (`grep -aP 'x\x00y'`
   works here — which sed cannot do). Compile-time option: minimal builds
   error with *"support for -P not compiled"*.
4. **Recursion is a file-walking layer, not a matcher feature.** `-r`/`-R`
   enumerate files (honoring `--include`/`--exclude`/`--exclude-dir`) and
   feed each through the same matcher — where the GNU vs BSD divergence
   lives (see Portability).

## Variants — egrep, fgrep, and the wrapper story

The historical split (BRE vs "extended" vs literal) shipped as separate
binaries through Unix history. GNU grep merged the engines in the 1990s but
kept the names as wrappers, so decades of scripts kept working. The current
state, since upstream GNU grep 3.8 (2022):

- **Upstream**: since GNU grep 3.8 (2022) the wrappers print
  `egrep: warning: egrep is obsolescent; using grep -E` on every call.
- **Debian**: ships its *own* silent wrappers so existing scripts don't
  spam stderr. On this container (grep 3.11-4) they are literally:

  ```sh
  #!/bin/sh
  cmd=${0##*/}
  exec grep -E "$@"
  ```

  …**no warning printed**. Treat `egrep`/`fgrep` as deprecated spellings
everywhere, but do not expect a warning to tell you.
- **busybox grep**: no wrappers — applet aliases inside the multi-call
  binary; drops `-P`, `-z`, and most of the recursion filter family.
- **BSD/macOS grep**: same four names, separate FreeBSD implementation;
  `egrep` is a deprecated alias for `grep -E` there too.

Writing new code: use `grep -E` / `grep -F` / `grep -r` directly. Reading
old code: `egrep`/`fgrep` are safe to *read* as those exact equivalents.

## Options That Matter

The interview-relevant core, grouped by family; full per-flag syntax and
regex mechanics: [shell-track grep page](../../shell/grep.md).

### Pattern selection

| Option | Effect |
| --- | --- |
| `-G` | BRE (default) — `\|`, `\+` are extensions, `(` is literal |
| `-E` | ERE — `|`, `+`, `?`, `(…)` live; the `egrep` dialect |
| `-F` | literal strings, no metacharacters at all |
| `-P` | Perl regex; optional at build time; GNU-only in practice |
| `-e P` / `-f FILE` | multiple patterns; `-f` = one pattern per line |

### Matching and output

| Option | Effect |
| --- | --- |
| `-i` / `-v` / `-w` / `-x` | case-insensitive / invert / word / whole-line match |
| `-n` / `-o` / `-c` / `-l` / `-L` / `-q` | numbers / matches-only / count / list / inverse-list / silent |
| `-A n` `-B n` `-C n` | after/before/context line groups (`--` separator) |
| `--color=auto` | highlight; `auto` keeps pipes clean |

### Recursion and filtering (the GNU-vs-BSD fault line)

| Option | Effect |
| --- | --- |
| `-r` | recurse; follow symlinks only if named on the command line |
| `-R` | recurse and follow *all* symlinks (historically also `rgrep`) |
| `--include=GLOB` | only files matching the glob (e.g. `--include='*.c'`) |
| `--exclude[-dir]=GLOB` | skip matching files / directories |
| `-z` | NUL-separated "lines" — pair with `find -print0` (GNU-only) |

## Usage Patterns

```bash
# Code audit: find every TODO across a source tree, filtering by extension
grep -rn --include='*.[ch]' 'TODO\|FIXME' src/
```

```bash
# Silently answer "does this service log any errors?" — exit code is the answer
if grep -q 'ERROR' app.log; then echo "errors present"; fi
```

```bash
# Speed: 10k literal patterns against a big file — the -F engine, not regex
grep -F -f blocked-ips.txt access.log
```

```bash
# Check which pattern engine your build actually has before relying on -P
echo test | grep -P 't(?=e)' 2>&1 | grep -q 'not compiled' && echo "no PCRE"
```

```bash
# Read a wrapper to learn what a name means on *this* machine
cat "$(command -v egrep)"
```

```bash
# NUL-safe search over find results, filenames with spaces and newlines be damned
find . -type f -print0 | xargs -0 grep -l pattern
```

```bash
# Directory-wide search that skips vendored code
grep -rn pattern --exclude-dir=node_modules --exclude-dir=.git .
```

## Portability — GNU vs BSD vs busybox

| Behavior | GNU grep | BSD grep (macOS/FreeBSD) | busybox grep |
| --- | --- | --- | --- |
| `-r` symlink policy | only if named on the command line | historically follows all symlinks | does not follow |
| `-R` | follow all symlinks | same as `-r` | same as `-r` |
| `--include`/`--exclude` | yes | yes (adopted) | subset, build-dependent |
| `--exclude-dir` | yes | yes on modern builds | mostly absent |
| `-P` | optional, common on Linux | no | no |
| `-z` (NUL data) | yes | no | no |
| `-o`, `-L`, `-m`, `--color` | yes | yes | most |
| egrep/fgrep wrappers | Debian: silent; upstream 3.8+: warn | alias, deprecated | internal alias |

The safe portable core: `-E -F -G -i -n -v -l -c -q -r -e -f -A/-B/-C`.
Beyond that, test on the target platform — or push filtering into `find`
(stricter, documented semantics) and keep grep's flags minimal.

## Nuances and Gotchas

- **Exit 1 is a *successful negative*.** Under `set -e`, a bare `grep` that
  finds nothing kills the script — use `if grep -q …` or `|| true`. Exit 2
  is the real failure (unreadable file, bad pattern, no `-P` support).
- **`-q` and errors**: with `-q`, a found match still wins — exit 0 even if
  some files could not be read. Scripts get "match" even on partial I/O
  failure; add explicit error handling if that matters.
- **`egrep`/`fgrep` behavior differs by packaging** (warn vs silent — see
  Variants). Never depend on the warning appearing or not appearing.
- **Locale is a performance cliff.** In UTF-8 locales matching is
  table-driven per character; `LC_ALL=C grep …` is a routine 2–10x speedup
  for byte-oriented patterns, at the cost of UTF-8-aware `.` and classes.
- **Binary detection interrupts pipelines**: a NUL in the first block flips
  grep to `Binary file … matches`; `-a` forces text, `-I` skips binaries.
- **`--color=always` leaks ANSI codes into files and pipes**; use `auto` except in interactive aliases.
- **`grep -r` follows the symlinks *you* name but not the ones it finds** —
  unless you asked for `-R`. Looping filesystems (`-R /` reaching `/proc`
  back-edges) are a real footgun; scope the directory or exclude paths.
- **An empty pattern file matches everything**: `grep -f /dev/null file`
  selects every line (the empty disjunction matches), while a *nonexistent*
  pattern file is exit-2 trouble. Both are one-character accidents.
- **`--color=always` leaks ANSI codes into files and pipes**; use `auto`
  everywhere except interactive aliases.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | at least one line selected |
| 1 | no line selected — a normal, expected result, *not* an error |
| 2 | trouble: unreadable input, bad pattern, requested engine unavailable |

`-q` returns 0 on the first match and stops reading; `-v` inverts the
"selected" definition; `-L` exits 0 when files lacking matches exist.

## Related Commands

- [`find`](../../shell/find.md) — enumerate files with full control; pair
  with `grep -l` when `--include` globs are not enough.
- [`xargs`](../../shell/xargs.md) — feed grep file lists safely with
  `-print0`/`-0` (one grep invocation per batch, not per file).
- [regex syntax](../../shell/regex.md) — BRE vs ERE vs PCRE, class
  subtleties, anchors: the language these engines interpret.
- [grep deep dive](../../shell/grep.md) — flags, regexes, performance and alternatives (ripgrep et al.) in full.
- [Man pages](../../reference/man-pages.md) — reading `man grep` well,
  including the GNU texinfo manual behind it.
- [Part overview](../overview.md) — the other userland binary collections.

## Interview Questions

### Q: Why does GNU grep ship several pattern engines instead of one?

Because the three jobs have different cost models. `-F` asks "is this exact
string present?" — a Boyer–Moore-family matcher skips through the line in
bulk and is by far the fastest. BRE/ERE compile to a DFA-style matcher tuned
to scan whole files without backtracking explosions. `-P` trades speed for
expressive power (lookaround, captures). One dispatcher, one output layer,
several matcher back ends.

### Q: What happens when you type `egrep` today?

You run a shell wrapper, not a distinct binary. Since upstream grep 3.8 the
wrapper warns that egrep is obsolescent and execs `grep -E`; Debian keeps
silent wrappers (`exec grep -E "$@"`) so old scripts don't emit stderr
noise. The engines were merged decades ago; the names persist only for
script compatibility and are deprecated spellings everywhere.

### Q: You run `grep -r pattern /data` on Linux and the same command on a
macOS box and get different files listed. What do you check first?

Symlink policy. GNU `-r` follows symlinks only when they are named on the
command line; BSD grep historically follows all symlinks for `-r` and treats
`-R` as an alias. Files reached through directory symlinks appear in one
result set but not the other; switch to explicit `-R` (or
`find -L … | xargs grep -l`) for one defined behavior everywhere.

### Q: Why is `grep pattern bigfile` sometimes 5x slower in the afternoon
batch than at boot?

Locale. In a UTF-8 locale, matching is multi-byte-aware — comparisons go
through locale tables, and character classes and `.` change meaning. Setting
`LC_ALL=C` reverts to byte semantics: correct for ASCII patterns and
dramatically faster. The same effect explains why `grep -F` on a huge
alternation beats an ERE alternation of the same literals.

### Q: Design question: your CI greps a 50 GB log for 10,000 literal
tokens nightly. How do you make it fast?

Four levers: (1) `grep -F -f tokens.txt` so the Boyer–Moore-family engine
replaces regex simulation; (2) `LC_ALL=C` to avoid multi-byte overhead;
(3) restrict the scan surface with `--include`/`--exclude-dir` or a `find`
file list so unread bytes cost nothing; (4) a big `-F` pattern file is
already the Aho–Corasick-shaped case GNU grep optimizes for.

## References

- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/grep/)
- [Source — Debian sources](https://sources.debian.org/src/grep/)
- [Deep dive — shell track](../../shell/grep.md)
