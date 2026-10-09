# cat — concatenate files and print to standard output

## Overview

`cat` reads files (or standard input) in order and writes their bytes, unchanged, to standard output. Despite its reputation as "the command that prints files", its name and original purpose are **con**catenate: `cat a b c` produces exactly the byte stream of a followed by b followed by c. Printing a single file is the degenerate case.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/cat`, from upstream GNU coreutils. It is among the oldest surviving Unix programs: `cat` appears in the First Edition manual (1971) and descends directly from Ken Thompson and Dennis Ritchie's original PDP-7 utilities. The First Edition manual also contained an in-joke that survived in Unix folklore — cat's SEE ALSO reportedly pointed at a fictitious `toe(1)` described as "cat, with toes". Related to that era: POSIX still mandates a `-u` flag ("write bytes without delay as they are read"), a relic of when buffered `cat` corrupted byte streams fed to tape devices and early network transports like UUCP.

You reach for `cat` to concatenate, to feed a file into a pipeline (where it is sometimes awarded the tongue-in-cheek "useless use of cat" label — see below), to build files interactively with `cat > file`, and to dump file contents with visible whitespace and control characters via `-A`. It is often confused with `echo` (prints a string, not a file), `printf` (formatted output), and `tac` (same job, lines in reverse).

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/cat` |
| First appeared / lineage | Original Unix (PDP-7, 1969); First Edition manual 1971 |
| Standards | POSIX.1-2018 (`cat`, including `-u`), plus GNU extensions |

## Synopsis

```
cat [OPTION]... [FILE]...
```

Main forms:

```
cat file                    # print one file
cat a.txt b.txt > out.txt   # concatenate two files into a third
cat > notes.txt             # type into a file; Ctrl-D ends input
cat -A script.sh            # print with tabs/CR/line-ends visible
```

With no FILE, or when FILE is `-`, standard input is read once per `-`.

## How It Works

### The data path

`cat` is a filter with no logic between input and output: it opens each operand in sequence and copies bytes through a buffer to standard output, stopping early only on errors or signals. That is the entire contract — no interpretation, no transformation of content. Every flag it has only annotates or coalesces at line boundaries (`-n`, `-s`, `-b`) or re-renders bytes as printable text (`-v` family); the underlying stream is never parsed.

```
 input                    cat                    output
┌─────────┐   read()   ┌──────────────┐  write()   ┌───────────┐
│ file1   │ ─────────> │  byte buffer │ ─────────> │ stdout    │
│ file2   │            │ (no parsing) │            │ (fd 1)    │
│ '-'=stdin│           └──────────────┘            └───────────┘
└─────────┘     operands concatenated in argument order
```

### Concatenation is positional and byte-faithful

Operands are processed in argument order; output is their exact sequence of bytes. This makes `cat` the canonical tool for splicing file parts — split archives, chunked uploads, model files in parts — and for merging with stdin in the middle of the sequence using `-`:

```
$ printf 'head\n' > h; printf 'tail\n' > t
$ cat h - t <<< 'middle'
head
middle
tail
```

### The -v rendering family

The `-v` family changes how unprintable bytes are *displayed*, never the bytes themselves:

- `-v`, `--show-nonprinting`: control characters render as `^X` (e.g. `^A`), non-ASCII bytes as `M-X`.
- `-E`, `--show-ends`: newline renders as `$` at each line end.
- `-T`, `--show-tabs`: tab renders as `^I`.
- `-A`, `--show-all`: equivalent to `-vET` — the "why doesn't my file match" diagnostic.
- `-e`: equivalent to `-vE`; `-t`: equivalent to `-vT` (BSD-compatibility shorthand).

```
$ printf '\ttab\x01\r\n' | cat -A
^Itab^A^M$
```

### Numbering and squeezing

`-n` numbers every output line (right-aligned in a five-character field, then a tab), including blank lines; `-b` numbers only non-blank lines (implies `-n` semantics but skips empties). `-s` collapses runs of adjacent blank lines into a single blank line. These flags are line-oriented conveniences bolted onto a byte filter — which is why `cat -n` output cannot be un-numbered by `cat` itself and why combining `-s` with binary data is a corruption.

```
$ printf 'a\n\n\nb\n' | cat -n
     1  a
     2
     3
     4  b
$ printf 'a\n\n\nb\n' | cat -b
     1  a

     2  b
```

### The "useless use of cat" debate, fairly stated

The critique (coined by Randal L. Schwartz as **UUOC** on comp.unix.shell) targets `cat file | grep x` where `grep x file` works directly: one extra process, one extra copy through a pipe, one extra thing in `ps`. The defense has three legitimate legs:

1. **Concatenation is cat's job** — `cat a b | grep x` cannot be rewritten without `grep ... a b` changing match-annotation behavior (filenames prefixed, context headers per file).
2. **Readability** — pipelines read left to right; `cat file | ...` puts the data source first, which matters in long pipelines and when editing them.
3. **Uniformity in scripts** — when the source may be a file or stdin, `cat "$1" | ...` and `cat "$1" - | ...` (data in the middle) are simpler than juggling redirection.

The honest engineering position: for a single small input, the cost is negligible and it is a style choice; in a hot loop over gigabytes, dropping the extra process is measurable. Interviewers mostly want you to know *both* sides and when the extra process actually costs something.

## Options That Matter

| Option | Effect |
|---|---|
| `-A`, `--show-all` | Equivalent to `-vET`: show nonprinting, `$` at line ends, `^I` for tabs |
| `-b`, `--number-nonblank` | Number non-blank output lines (overrides `-n`) |
| `-e` | Equivalent to `-vE` (BSD shorthand) |
| `-E`, `--show-ends` | Print `$` at the end of each line |
| `-n`, `--number` | Number all output lines |
| `-s`, `--squeeze-blank` | Collapse repeated blank lines into one |
| `-T`, `--show-tabs` | Print tabs as `^I` |
| `-t` | Equivalent to `-vT` |
| `-u` | (POSIX) Write without delay; a no-op in GNU cat, accepted for compatibility |
| `-v`, `--show-nonprinting` | Render control chars as `^X` and non-ASCII as `M-X` |

## Usage Patterns

```bash
# Reassemble a split archive (cat's original purpose)
cat model.tar.gz.part-* > model.tar.gz
```

```bash
# Merge files with stdin spliced in the middle
cat header.txt - footer.txt < body.txt > final.txt
```

```bash
# Diagnose invisible garbage in a config file (tabs, CR-LF, control chars)
cat -A /etc/crontab | head
```

```bash
# Check whether a "text" file has DOS line endings
cat -A windows.csv | head -3      # '^M$' at line ends means CRLF
```

```bash
# Create a small file from the terminal without an editor
cat > /etc/apt/sources.list.d/local.list <<'EOF'
deb http://mirror.example/debian bookworm main
EOF
```

```bash
# Append terminal input to an existing log while working
cat >> session.log
```

```bash
# Concatenate CSV shards, then process once downstream
cat shard-*.csv | grep -v '^#' | wc -l
```

```bash
# Number lines for a diff discussion (GNU cat, not nl's fancier formatting)
cat -n app.py | sed -n '40,60p'
```

```bash
# Squeeze blank spam out of a paste before saving
cat -s pasted.txt > cleaned.txt
```

```bash
# Pipe several files with byte-exact output into a checksum
cat part1 part2 part3 | sha256sum
```

## Nuances and Gotchas

- **`cat file` when you meant `cat file > file` truncates the file first** — and even the correct-looking incantation is broken: redirection truncates before cat reads it, producing an empty file. To transform in place, write to a temp and `mv`. Countless "my file is now empty" incidents end at this line.
- **`-n`/`-b`/`-s` are line-oriented** and will mangle binary data (squeeze runs, reformat counts) — they also change bytes, so `cat -n a | cmp - a` fails. Numbering for byte-faithful purposes belongs to `nl`/`sed` equally, but feeding `-A`-style views into anything downstream is a bug.
- **`-A` output is not the data.** `^I`, `$`, and `M-` sequences are rendering; piping `cat -A` output onward bakes those six-character sequences into real bytes. Use `-A` for eyes only.
- **Exit status with multiple files:** `cat a missing b` still prints what it can and exits 1 — scripts checking `$?` catch the failure, but partial output has already been produced downstream. Guard input existence if downstream must be atomic.
- **`cat` is not `echo`.** `cat "$VAR"` treats `$VAR` as a *filename*; to print a variable use `printf '%s\n' "$VAR"` or `echo "$VAR"`. Confusing the two is a classic injection/bug vector when the variable is user-controlled.
- **UUOC has a real cost only at scale.** One extra process per pipeline element is noise in a one-shot script; in a loop processing hundreds of MB, `grep x file` beats `cat file | grep x` measurably (no pipe context switches, no extra exec).
- **Buffering folklore:** GNU `cat` writes with full buffering when stdout is a file and flushes per read when interactive; `-u` exists in POSIX for tools that needed unbuffered output (tape, UUCP-era transports) and is accepted-but-ignored by GNU. Do not rely on `cat -u` for real-time streaming semantics in portable scripts.
- **Locale note:** `cat` is byte-oriented and locale-independent — one of the few tools where `LC_ALL` never changes behavior. The `-v` family renders non-ASCII as `M-X` regardless of the terminal's charset.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | All operands processed successfully |
| 1 | At least one failure: unreadable operand, read/write error |

When multiple operands are given, `cat` continues past failures; the exit status reports the overall result, not the first error.

## Related Commands

- [`tac`](./overview.md) — cat reversed; prints files line-by-line backwards (covered in the collection overview).
- [`head`](./head.md) — first N lines/bytes of the same byte stream.
- [`tail`](./tail.md) — last N lines/bytes, plus live following.
- [`cksum`](./cksum.md) — byte-faithful digests of what `cat` concatenates.
- [`nl`](./overview.md) — the dedicated line-numbering filter with richer formatting than `cat -n`.
- [`overview`](./overview.md) — GNU Coreutils collection hub.

## Interview Questions

### Q: Why is it called cat, and what is its actual primary function?

Short for concatenate. Its primary function is joining operand byte streams in argument order onto stdout — printing a single file is the special case of one operand. The design (zero transformation between read and write) is what makes it safe for splicing binary parts and for feeding arbitrary bytes into checksums.

### Q: What does `cat -A` show you, and name a concrete debugging use?

`-A` is `-vET`: control characters as `^X` sequences, non-ASCII as `M-X`, tabs as `^I`, and each newline as `$`. The classic use is finding why two "identical" files differ: DOS line endings (`^M$`), trailing tabs in Makefiles (where a space instead of tab breaks the build), invisible control characters pasted from a PDF, or a file that lacks a final newline.

### Q: Someone runs `cat ~/.bashrc | sort > ~/.bashrc` and their file is now empty or wrong. Explain the failure and the fix.

The shell sets up redirection before the pipeline runs: `> ~/.bashrc` truncates the file first, so cat reads (part of) an empty file. Even when ordering were kind, the pipeline races itself. The fix is a two-step pattern: `sort ~/.bashrc > ~/.bashrc.tmp && mv ~/.bashrc.tmp ~/.bashrc`, or use `sponge` from moreutils. The general rule is never to read and write the same file in one pipeline.

### Q: When is `cat file | grep pattern` actually justified rather than "useless"?

Three solid cases: concatenating multiple files where per-filename headers from grep would pollute matches (`cat a b | grep x`); when the data source alternates between files and stdin and you want one uniform pipeline; and when the file argument is really a prefix of several positional operands you want streamed together. For a single file the direct `grep pattern file` is strictly cheaper — one fewer process and one fewer pipe — so the justified cases are the ones where cat is doing its named job.

### Q: What is the difference between `cat -n` and `cat -b`, and when would you use neither?

`-n` numbers every output line including blanks; `-b` numbers only non-blank lines (and overrides `-n`). Neither should be used when byte fidelity matters: both insert characters and change byte counts, so the output can no longer `cmp` against the input. For anything downstream that cares about content (checksums, rejoining split files), run plain `cat` and do numbering in the display layer (`nl`, `less -N`, editor gutter).

### Q: Why does POSIX still require a -u flag for cat?

Historical buffering semantics: implementations once buffered output, which corrupted byte streams written to devices and block-oriented transports (tape drives, UUCP links) that needed bytes without delay. POSIX keeps `-u` ("write without delay") so scripts from that era keep working; GNU cat accepts it as a no-op. It is a good interview example of a standard flag that outlived its hardware.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/cat.1.en.html)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
