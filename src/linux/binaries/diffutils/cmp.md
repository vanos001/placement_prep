# cmp — byte-by-byte comparison and first-difference locator

## Overview

`cmp` compares two files byte by byte. Its contract is deliberately minimal: tell the caller whether the inputs are identical, and if not, report the offset of the *first* difference. It ships in the `diffutils` package (Debian bookworm: GNU diffutils 3.8) at `/usr/bin/cmp`. Because it never tries to interpret the bytes as text, it is the correct comparison tool for executables, images, firmware dumps, and any non-text payload, and it is also the cheapest way to answer "is this file identical to that one" for any file, since it stops at the first differing byte.

`cmp` is often confused with `diff` (which is line-oriented, content-aware, and wants text), with `md5sum`/`sha256sum` (which reduce whole files to one digest — good for distribution-wide verification, overkill for a single pairwise check), and with `test file1 -ef file2` (which checks inode identity, not content). Rule of thumb: two files, one verdict, one position → `cmp`; two text files and a readable report → `diff`; many files against a manifest → checksums.

| Field | Value |
| --- | --- |
| Package | diffutils (Debian bookworm: GNU diffutils 3.8) |
| Man section | 1 |
| Path | /usr/bin/cmp |
| First appeared | AT&T Unix Version 1 (1971) |
| Standards | POSIX.1-2018 (`cmp`) |

## Synopsis

```
cmp [OPTION]... FILE1 [FILE2 [SKIP1 [SKIP2]]]
```

Common one-line forms:

```
cmp a.bin b.bin              # first difference, human message
cmp -s a b                   # silent; the exit status is the answer
cmp -l a.bin b.bin           # list ALL differing bytes (octal)
cmp -n 1M img1.img img2.img  # compare only the first megabyte
```

A missing `FILE2` or the operand `-` reads standard input. `SKIP1`/`SKIP2` skip bytes at the start of each input (with multiplicative suffixes: `K`=1024, `M`=1048576, `kB`=1000, ...). GNU cmp extends the POSIX form with `-i SKIP1:SKIP2`.

## How It Works

### The comparison loop

`cmp` opens both inputs and walks them in lockstep, one buffer at a time, until it finds a byte pair that differs, reaches EOF on both, or hits the `-n` limit. On the first difference it reports and stops — cost is proportional to the position of the first difference, not to file size. That early-exit property is the whole point: two 4 GiB images that diverge in the first 100 bytes cost almost nothing to compare.

```
 FILE1  [b1][b2][b3][b4][b5][b6][b7][b8] ...
 FILE2  [b1][b2][b3][b4][b5][b6][b7][b8] ...
                     │
        first unequal byte (here: offset 6)
                     │
   default: print "differ: char 6, line 1", STOP, exit 1
   -b:      same message + octal values of both bytes
   -l:      keep going, one report line per differing byte
   -s:      print nothing at all, exit status only
```

Divergence has two flavors:

1. **Byte mismatch** — same offset, different value. Default message names the byte (1-based) and the current line:
   ```
   $ cmp x.bin y.bin
   x.bin y.bin differ: char 6, line 1
   ```
2. **EOF divergence** — one input is a proper prefix of the other:
   ```
   $ cmp short.bin y.bin
   cmp: EOF on short.bin after byte 5, in line 1
   ```
   This case matters more than it looks: a truncated download is identical to the original for its entire length, and only the EOF report distinguishes "prefix" from "equal". `cmp -s` still returns 1, so scripts detect truncation for free.

If the files are identical to the last byte, `cmp` prints nothing and exits 0. Identical-but-weird cases (same content, different names) behave identically — `cmp` has no interest in names.

### Reading the verbose reports

`-b` (`--print-bytes`) augments the first-difference message with the octal values and the printable characters of the two offending bytes:

```
$ cmp -b x.bin y.bin
x.bin y.bin differ: byte 6, line 1 is 145 e 106 F
```

`145` and `106` are **octal** (0o145 = 101 = `'e'`, 0o106 = 70 = `'F'`), followed by the printable characters when they exist. `--print-bytes` also extends the `-l` listing with these character columns.

`-l` (`--verbose`) does not stop at the first difference: it prints one line per differing byte, offset in decimal, values in octal:

```
$ cmp -l l1 l2
3 141 132
```

Read it as: byte 3, left file has 0o141 (`a`), right file has 0o132 (`Z`). Because it must find *all* differences, `-l` reads both files to the end — the early-exit optimization is off, which is exactly what you want for a full divergence census and exactly what you do *not* want on multi-gigabyte inputs unless you mean it.

Note the vocabulary: POSIX-style default output says **char**, GNU `-b` output says **byte**. Both count 1-based bytes of the input stream; nothing here is aware of encodings, so a "char" in the message is just a byte.

### Skips and limits

`SKIP1` and `SKIP2` position the comparison window inside each file — useful for headered formats (skip a fixed 512-byte header) or for comparing a file's tail against another file's head:

```
cmp -i 512 data_a.bin data_b.bin        # skip 512 bytes of BOTH
cmp -i 512:0 head_a.bin head_b.bin      # skip 512 of first, none of second
cmp -n 1K golden.bin candidate.bin      # compare at most 1024 bytes
```

GNU also accepts `-i SKIP:SKIP2` as one option, and suffixes like `K`, `M`, `G` (binary) or `kB`, `MB` (decimal). POSIX only specifies the two positional skip operands; the `-i` spelling is GNU.

### Where cmp sits among comparison tools

| Question | Tool | Cost |
| --- | --- | --- |
| Are these two files bit-identical? Where do they first diverge? | `cmp` | O(first difference) |
| Which lines of these text files changed? | `diff` | O(size), text only |
| Which of these 500 files changed since the manifest? | `sha256sum` + diff of manifests | O(total size), reusable |
| Do these two paths refer to the same data? | `test a -ef b` (stat) | O(1), inode-level only |

### The silent contract

`-s` (`--quiet`, `--silent`) suppresses all output, including error messages for unreadable files; the exit status carries everything. This is the form used in scripts, init checks, and Makefiles — and the one that interacts badly with `set -e` if you forget that exit 1 is the *expected* "different" answer.

```
$ cmp -s x.bin x.bin; echo $?    # 0
$ cmp -s x.bin y.bin; echo $?    # 1
$ cmp -s x.bin /nope; echo $?    # 2 (trouble) — message also suppressed
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-b`, `--print-bytes` | Print octal values + printable chars of differing bytes. |
| `-l`, `--verbose` | List every differing byte: decimal offset, octal values; no early exit. |
| `-n LIMIT`, `--bytes=LIMIT` | Compare at most LIMIT bytes (suffixes: `K`, `M`, `G`, ...). |
| `-i SKIP`, `--ignore-initial=SKIP` | Skip first SKIP bytes of both inputs (GNU). |
| `-i SKIP1:SKIP2` | Skip SKIP1 bytes of FILE1 and SKIP2 of FILE2 (GNU). |
| `-s`, `--quiet`, `--silent` | Print nothing; exit status is the only output. |
| `SKIP1 SKIP2` (positional) | POSIX spelling of the two per-file skip values. |

There are no content-interpretation flags: no case folding, no whitespace tolerance, no text mode. Bytes are bytes — that is cmp's identity next to its siblings.

## Usage Patterns

```bash
# Verify a copy operation actually copied (content, not just name)
cmp important.tar.gz /backup/important.tar.gz && echo backup-ok
```

```bash
# Boolean equality check in a script; 1 is "different", 2 is trouble
if cmp -s golden.bin candidate.bin; then
  echo "bit-identical"
fi
```

```bash
# Locate the first divergence between two firmware images
cmp firmware-v1.bin firmware-v2.bin
# firmware-v1.bin firmware-v2.bin differ: char 1048577, line 8007
```

```bash
# Decode the first differing bytes (octal + characters)
cmp -b firmware-v1.bin firmware-v2.bin
```

```bash
# Census of ALL differing bytes (mind: reads both files fully)
cmp -l disk.img.dd disk.img.copy | wc -l
```

```bash
# Sanity-check only the first megabyte of a flash dump (header region)
cmp -n 1M expected-header.bin device-dump.bin
```

```bash
# Compare file bodies past a fixed 512-byte header
cmp -i 512:512 image-a.img image-b.img
```

```bash
# Is a file empty? /dev/null as the reference input
cmp -s data.db /dev/null || echo "data.db has content"
```

```bash
# Compare a command's output against a saved capture
cmp -s <(systemctl is-active nginx) <(printf 'active\n') && echo running
```

```bash
# Detect truncated downloads: prefix files report EOF, not equality
cmp -s partial.zip full.zip || echo "incomplete or corrupted"
```

```bash
# How far do two large logs agree before diverging? (1-based byte offset)
cmp journal-a.log journal-b.log 2>&1 | head -1
```

```bash
# Feed one input from stdin: compare generated data against a golden file
./gen-config | cmp - golden.conf && echo "generator matches golden"
```

```bash
# Count how many bytes two almost-identical archives differ in,
# after skipping their 34-byte gzip headers (GNU -i form)
cmp -l -i 34:34 old.tgz new.tgz | wc -l
```

```bash
# Fail a CI step when the build output drifted from the reference build
cmp -s artifacts/release.tar.zst reference/release.tar.zst \
  || { echo "non-reproducible build"; exit 1; }
```

```bash
# Pair up diffs and cmps: report differing text files from a tree sweep
for f in /etc/*.conf; do
  cmp -s "$f" "/var/backups/$(basename "$f")" || echo "changed: $f"
done
```

## Nuances and Gotchas

- **Exit 1 is success.** "Inputs differ" is a normal answer, encoded as status 1; 0 means identical, 2 means trouble (missing file, I/O error). Under `set -e` a bare `cmp a b` aborts on the first legitimate difference. Write `if cmp -s ...` or `cmp ... || true` with intent.
- **`-s` hides trouble too.** A missing or unreadable file also exits nonzero with no message — a script can confuse "files differ" with "file missing". Check readability separately when the distinction matters.
- **Offsets are 1-based; values are octal in `-b`/`-l`.** Scripts that feed `cmp -l` offsets into `dd`/`head -c` must subtract 1. And `141` in the listing is octal, not decimal — a classic misread.
- **"char" ≠ character.** The default message says *char* for historical reasons; cmp counts raw bytes, knows nothing of UTF-8, and a multibyte character differing shows up as one byte position with nonsense "characters" in `-b` output.
- **`-l` disables the early exit.** On huge, very different inputs `-l | wc -l` can be exponentially slower than a plain `cmp`. If the question is "how different", sample first with `-n`.
- **EOF case is the truncation detector.** Two files can be "identical" for their whole common length yet not identical; only the `EOF on ... after byte N` message (and exit 1) reveals it. Never substitute a head-truncated checksum comparison for cmp.
- **cmp vs diff for text.** cmp reports *one* byte; diff reports a *structural* summary. A one-character typo in a 10k-line file costs diff one hunk and costs cmp 2 bytes of information — but for binaries diff gives up entirely (`Binary files ... differ`).
- **cmp vs checksums.** cmp is O(first difference) for a single pair; checksums are O(size) once per file but reusable across a whole set. Comparing two 5 GiB files by `sha256sum` when you could have used `cmp -s` reads them fully twice as often as needed.
- **Skips are not symmetric by default.** `cmp -i N a b` skips N bytes of *both* files; the per-file split needs `-i N:M` (GNU) or the positional `SKIP1 SKIP2` form. Mixing the two spellings is a common scripting bug.
- **Portability.** POSIX defines `-l`, `-s`, and the positional skips; `-b`, `-n`, and `-i` are GNU extensions (BSD cmp implements most of them; BusyBox cmp implements `-s`, `-l`, `-n` — check before relying on `-b` in minimal environments).

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Inputs are identical (within the compared range). |
| 1 | Inputs differ (byte mismatch or EOF on one input). |
| 2 | Trouble: missing/unreadable file, I/O error, bad usage. |

## Related Commands

- [`diff`](./diff.md) — line-oriented comparison and patch generation for text.
- [`diff3`](./diff3.md) — three-way merge; there is no binary three-way in diffutils, so binary merges need cmp-level diagnostics or manual reconstruction.
- [`sdiff`](./sdiff.md) — side-by-side text comparison and interactive merge.
- [Collection overview](./overview.md) — how the four diffutils binaries divide the work.
- [`find`](../../shell/find.md) — locate candidate files to compare in bulk.
- [Part overview](../overview.md) — all userland binary collections.

## Interview Questions

### Q: When would you reach for cmp instead of diff, and what does cmp do that diff cannot?

Any time the inputs are not text, or the question is binary equality rather than structural change. cmp walks raw bytes, stops at the first difference, and reports its 1-based offset — diff on binaries only prints "Binary files ... differ" with no position. cmp also detects the prefix/EOF case (truncated file), which diff treats as just "differ".

### Q: What are cmp's exit codes and what is the classic scripting mistake around them?

0 = identical, 1 = different, 2 = trouble. The mistake is treating 1 as an error — under `set -e`, or in pipelines without `||`, a legitimately different pair aborts the script. The second mistake is using `-s` and then conflating "different" (1) with "missing/unreadable" (2), since `-s` suppresses the diagnostic that distinguishes them.

### Q: `cmp -l a b` prints `300 141 132`. What does that mean and what are the units?

Byte (offset) 300 — 1-based, decimal — differs: file a contains octal 141 (decimal 97, ASCII `a`), file b contains octal 132 (decimal 90, ASCII `Z`). Offsets are decimal but byte *values* are octal in cmp's verbose output; feeding the offset straight into a 0-based tool like `dd skip=` is off by one.

### Q: How can cmp prove that a downloaded file is truncated rather than corrupted?

If the partial file is a strict prefix of the original, a byte-comparison finds no mismatched byte and runs into EOF: `cmp: EOF on partial.zip after byte N, in line L`, exit 1. That EOF report is distinct from the `differ: char N` message of a mid-file corruption. Checksums can also reveal it (digest differs), but cmp localizes the condition as "prefix" without a second full read of the small file.

### Q: Why is `cmp -s` preferable to `diff -q` inside a performance-sensitive loop over large binary files?

`cmp -s` stops reading at the first differing byte, so the cost is proportional to the position of the first divergence. `diff -q` also short-circuits on binary content, but on *text* inputs it must line up and hash content before concluding inequality, and its exit contract (still 0/1) gives no byte position for follow-up. For pure equality on large blobs, cmp is the minimal-work answer; for "which lines changed", diff is.

### Q: Two 4 GiB files differ somewhere in the first kilobyte, and you also want to know how many bytes differ in total. What is the cost profile of the tools you could use?

A plain `cmp` finishes almost immediately (early exit). `cmp -l | wc -l` reads both 4 GiB inputs completely — necessary if you truly need the full census, otherwise wasteful. `sha256sum` on each file also reads everything and answers only "not identical". The staged approach — quick `cmp` first, full `-l` census only if needed — matches how the tool was designed to be used.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/diffutils/cmp.1.en.html)
- [Source — Debian sources](https://sources.debian.org/src/diffutils/)
