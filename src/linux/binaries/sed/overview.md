# sed — GNU sed: the stream-editor collection

## Overview

`sed` is the stream editor: it reads text record by record, runs a small
program over each record, and writes the result — non-interactively, in a
pipeline, at line speed. The Debian package `sed` is as minimal as packages
get: **one binary** at `/usr/bin/sed`, the GNU info manual, a FAQ, and one
legendary example script (`dc.sed` — an entire `dc` calculator implemented
in the sed language). You reach for sed when a transformation is too
structured for `tr`/`cut` but too small to open an editor or write a script:
substitutions across many files, deletions by pattern or line range,
in-place config edits under version control.

| Field | Value |
| --- | --- |
| Package | `sed` (Debian; GNU sed everywhere, busybox applet on embedded) |
| Section | 1 |
| Path | `/usr/bin/sed`; `/bin/sed` is the usrmerge symlink |
| This container | GNU sed 4.9-2, Debian 13 (trixie) |
| First appeared | Bell Labs, 1974 (Lee McMahon); GNU sed since 1989 |
| Standards | POSIX `sed`; `-E` standardized in POSIX Issue 8 (2024); `-z`, `-s`, `-i` semantics are GNU territory |

The command language (addresses, `s///`, hold-space commands) has decades of
depth and is *not* re-taught here — the shell track's combined page is the
deep reference: **[sed & awk in the shell track](../../shell/sed-awk.md)**.
This page adds the package-level view: what GNU sed ships, how its two-buffer
mechanics behave at the edges, where GNU, BSD and busybox diverge, and the
`-i` portability trap that has bitten two generations of scripters.

## Package inventory

`dpkg -L sed` (verified on this container) puts remarkably little on disk:

| File | Role |
| --- | --- |
| `/usr/bin/sed` | the only binary; everything else is documentation |
| `/usr/share/info/sed.info.gz` | full GNU manual (the real reference) |
| `/usr/share/doc/sed/examples/dc.sed` | a complete `dc` calculator written in sed — the language's party trick |
| `/usr/share/doc/sed/sedfaq.txt.gz` | the historical sed FAQ |

No `sedd`, no wrappers, no aliases: unlike grep's package there are no
compatibility entry points, because sed never split into named variants. The
feature drift lives *inside* the binary (see Variants and portability below).

## Synopsis

```
sed [OPTION]... {script-only-if-no-other-script} [input-file]...
sed -n 's/pattern/replacement/p' file          # print only changed lines
sed -i.bak -e 'cmd1' -e 'cmd2' file...         # in-place with .bak backup
sed -E -f script.sed file...                   # ERE script from a file
sed -z 's/\n//' file                           # NUL-separated records
```

## How It Works — two buffers and a cycle

Every sed run is the same loop; the whole command language is a way to hook
into these two buffers:

```
        each record (line, or NUL-chunk under -z)
                          │
                          ▼
   ┌──────────────── pattern space (working copy) ────────────────┐
   │  addresses select  →  commands edit  →  end of script        │
   │        hold space = scratch register (h/H/g/G/x swap it)     │
   └──────────────────────────────────────────────────────────────┘
                          │
                          ▼
   print pattern space + "\n"  (unless -n;  p/P print again;  D loops)
```

Package-level behaviors worth being able to demonstrate:

1. **`-z` changes the record separator, not the matcher.** With `-z`,
   records are NUL-delimited, so `\n` becomes ordinary data and
   `sed -z 's/\n/N/g'` genuinely joins lines (verified here). But a NUL
   byte itself is **never matchable**: even under `-z`, `y/\x00/;/`
   silently does nothing (verified) because sed's buffers are C strings.
   For NUL bytes use `tr` — sed cannot reach them.
2. **Files are one continuous stream by default.** `$` means "last line of
   the whole input": two one-line files piped through `sed -n '$='` print
   `2`. Add `-s` and each file becomes its own stream — `$=` prints `1`
   and `1` (both verified). This is why per-file logic (`$s/…/…/`,
   `$=`, `$a footer`) needs `-s` on GNU sed.
3. **`-i` is create-temp-then-rename.** The "in-place" edit replaces the
   file with a new inode: symlinks become regular files, hardlinks split,
   and the directory (not the file) needs write permission. GNU's
   `--follow-symlinks` restores the linked-file edit; an explicit `-i.bak`
   suffix gives you the safety net.
4. **`q`/`Q` set the exit code.** GNU sed's `q75` exits with 75, `Q42`
   with 42 (both verified) — a way to signal from inside a script. Note
   the edge: on empty input the cycle never runs, so `q75` still exits 0.

## Variants — the same editor, three feature sets

GNU, BSD (macOS) and busybox sed share the POSIX core (`s`, `d`, `p`, `y`,
addresses, `-n`, `-e`, `-f`) and diverge in the same places grep does:

| Behavior | GNU sed | BSD/macOS sed | busybox sed |
| --- | --- | --- | --- |
| ERE flag | `-r` (historic) and `-E` (since 4.8) | `-E` only | `-r` and `-E` |
| `-i` suffix | optional: `-i` or `-i.bak` | **mandatory**: `-i ''` for none | `-i[SUFFIX]` |
| `-s` (separate files) | yes | no | no |
| `-z` (NUL records) | yes | no | no |
| `-u` unbuffered | yes | yes | no |
| `--posix` mode | yes | no | no |
| `\xHH`, `\L`/`\U` escapes | yes | no (literal escapes needed) | partial |
| GNU commands (`e`, `F`, `R`, `T`) | yes | no | no |

**The `-E`/`-r` history in one line**: `-r` is the GNU spelling from the
1990s, `-E` is the BSD spelling that POSIX Issue 8 (2024) adopted, and GNU
sed 4.8+ accepts both — so `-E` is the spelling to write in new code, `-r`
is what you will meet in old scripts.

## The `-i` portability trap

The single most-quoted sed portability bug, worth understanding precisely:

```
GNU sed:      sed -i 's/a/b/' file      # -i with NO suffix; next arg is the script
BSD sed:      sed -i 's/a/b/' file      # -i REQUIRES a suffix argument:
                                        #   suffix = "s/a/b/", script = "file" — chaos
```

Portable spellings, in order of preference:

```bash
sed -i.bak 's/a/b/' file          # one token, works everywhere, keeps a backup
sed -i'' 's/a/b/' file            # GNU; BSD needs -i '' (two tokens) — not portable
tmp=$(mktemp) && sed 's/a/b/' file > "$tmp" && mv "$tmp" file   # bulletproof
```

Interview-worthy corollary: because of that rename, a `sed -i` run on a
read-only file succeeds anyway if you can write the *directory* — and the
replaced file inherits new ownership if you were root editing a user's file.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-n` | suppress default print; pair with `p` (the dry-run-friendly mode) |
| `-e CMD` / `-f FILE` | script from arguments / from a file (reusable logic) |
| `-i[SUFFIX]` | edit in place via temp+rename; SUFFIX keeps a backup per file |
| `-E` / `-r` | ERE syntax (`+ ? | ( )` unescaped); prefer `-E` (POSIX) |
| `-z` | NUL-separated records — pair with `find -print0`, GNU-only |
| `-s` | treat files as separate streams (`$`, `=`, `N` behave per file) |
| `-u` | unbuffered — for `tail -f | sed -u` live transforms |
| `--posix` | disable GNU extensions — compatibility check, see gotcha below |
| `--follow-symlinks` | GNU: let `-i` edit through symlinks instead of replacing them |
| `--sandbox` | GNU: forbid `e`/`r`/`w`/`R`/`W` — run untrusted scripts safely |

Command-level depth (`s///` flags, `y`, `a/i/c`, address ranges, hold-space
programming) lives in the [shell-track sed & awk page](../../shell/sed-awk.md).

## Usage Patterns

```bash
# Config edit with a dated backup — the portable in-place idiom
sed -i.$(date +%F).bak 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
```

```bash
# Dry-run first: review, then commit the edit
sed 's/old.example.com/new.example.com/g' nginx.conf > /tmp/cand && diff nginx.conf /tmp/cand
```

```bash
# Rewrite a hostname across a tree, keeping one backup per file
find /etc/nginx -name '*.conf' -exec sed -i.bak 's/old.example.com/new/g' {} +
```

```bash
# NUL-record pipeline: find paths, sed sees whole records, spaces survive
find . -type f -print0 | sed -z 's|^\./||' | xargs -0 -r echo
```

```bash
# Per-file line counts in one process — -s makes $ mean "last line of each file"
sed -s -n '$=' *.csv
```

```bash
# Live-stream transformation (e.g. scrub secrets) — -u keeps latency flat
tail -f app.log | sed -u 's/password=[^ ]*/password=REDACTED/g'
```

```bash
# Strip ANSI color codes from a captured log (GNU \x escape)
sed 's/\x1b\[[0-9;]*m//g' colored.log
```

```bash
# Which sed am I on? GNU prints its version and "Packaged by Debian"
sed --version | head -1
```

## Nuances and Gotchas

- **`sed -i` without an explicit suffix is unportable** (GNU ok, BSD
  destroyed script — see the trap section). In shared scripts: `-i.bak`, or
  temp-file-plus-`mv`, never bare `-i`.
- **`-i` breaks links and needs directory write permission** — it replaces
  the file by rename. Editing a symlinked config silently *unlinks* the
  symlink; editing a read-only file in a writable directory *succeeds*.
- **`--posix` fails silently, not loudly.** Under `--posix`, a GNU extension
  like `s/a\|b/X/` no longer matches — the script *runs* and selects
  nothing (verified). A compatibility check must diff outputs, not just
  check the exit code.
- **NUL bytes are unreachable** even with `-z` (verified no-op on
  `y/\x00/;/`); `\xHH` escapes themselves are GNU extensions, so the ANSI
  stripping example above needs a literal escape byte on BSD.
- **Exit 0 is not "did something".** sed exits 0 when the script ran, even
  if no `s` command matched anything. 1 is a script syntax error, 2 is an
  unreadable input file (both verified); deliberate exits come from `q N`.
- **Locale sensitivity**: `y///`, ranges like `[a-z]`, and case folding
  follow the locale; a Turkish locale can make `s/I/i/` surprises. Byte
  precision = `LC_ALL=C`.
- **`&` in the replacement is the whole match** — forgetting to escape it
  inside paths like `s|/etc|&/backup|` is benign there, but an unescaped
  `&` in IP-address rewrites duplicates the match. Use `\&` for a literal.
- **Greediness is per-match, not per-flag**: `s/<.*>//` eats from the first
  `<` to the *last* `>` on the line; the non-greedy fix is a negated class
  (`s/<[^>]*>//g`) — there is no lazy quantifier in POSIX sed.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | script completed — *including* "nothing matched" |
| 1 | invalid command syntax (parse error before any input) |
| 2 | an input file could not be opened/read |
| N | GNU: whatever `q N` or `Q N` says (0–255); empty input never reaches `q` |

## Related Commands

- [sed & awk deep dive](../../shell/sed-awk.md) — the command language,
  hold-space patterns, and awk side of the pair, in full.
- [regex syntax](../../shell/regex.md) — BRE vs ERE as sed consumes them,
  including the `\|`-style GNU deviations `--posix` disables.
- [`bash`](../../shell/bash.md) — process substitution and loops for
  dry-run-then-apply edit patterns.
- [`find`](../../shell/find.md) — the file-selection half of every bulk
  `sed -i` operation (`-exec … {} +` beats `| xargs` on safety).
- [Man pages](../../reference/man-pages.md) — sed's info manual is the
  authoritative text; `man sed` is the cheat sheet.
- [Part overview](../overview.md) — the other userland binary collections.

## Interview Questions

### Q: Explain the pattern space and the hold space, and give one command
that shows the difference.

The pattern space is the working copy of the current record; every command
operates on it and it is what gets printed. The hold space is a scratch
register that survives across the script but is never printed. `G` appends
the hold space to the pattern space — the classic one-liner `sed '$!G'`
double-spaces a file because on every line except the last it appends the
(empty) hold space, adding a newline.

### Q: Why is `sed -i` considered unportable, and how do you write an
in-place edit that works on GNU, BSD and busybox?

BSD sed takes the `-i` suffix as a *mandatory argument*, so a GNU-style
`sed -i 's/a/b/' file` makes BSD treat the script as the suffix and the
filename as the script. The portable spellings are `-i.bak` (one token,
supported by GNU, BSD and busybox, with the bonus of a backup) or the
explicit temp-file-plus-`mv` pattern. Bare `-i` with no suffix only works
where you know it's GNU.

### Q: What does `sed -z` actually change, and what problem does it *not*
solve?

`-z` switches the record separator from newline to NUL, so records align
with `find -print0` output and newlines become ordinary data you can match
and delete (`sed -z 's/\n//'` joins a file). It does *not* make NUL bytes
matchable: sed's buffers are C strings, so `y/\x00/;/` is a silent no-op
even under `-z`. Byte-level NUL work belongs to `tr`.

### Q: What is the difference between running `sed -n '$=' f1 f2` with and
without `-s`?

Without `-s`, sed treats the files as one concatenated stream, so `$` is
the last line of the *last* file and you get a single number (`2` for two
one-line files). With `-s`, each file is its own stream — per-file logic
like `$=`, `$s/…/…/`, or `$a footer` applies to each file independently
(`1` and `1`). `-s` is a GNU extension; BSD sed has no equivalent, so
portable scripts loop over files instead.

### Q: Your team's sed one-liner works on Linux but matches nothing under
`sed --posix`. What class of feature did you probably use, and why doesn't
it error?

GNU extensions that parse as ordinary syntax: escaped alternation (`\|`),
`\+`/`\?` quantifiers, `\xHH` escapes, or GNU command modifiers. Under
`--posix` they are treated literally — the pattern still *compiles*, so
sed exits 0 and simply selects nothing. The safe compatibility test is a
diff of outputs against known-good input, not the exit status.

## References

- [Man page index — manpages.debian.org](https://manpages.debian.org/bookworm/sed/)
- [Source — Debian sources](https://sources.debian.org/src/sed/)
- [Deep dive — shell track](../../shell/sed-awk.md)
