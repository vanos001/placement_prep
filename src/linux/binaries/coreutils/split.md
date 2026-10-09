# split — cut a file into size- or count-bounded pieces

## Overview

`split` divides one input file (or stdin) into fixed-shape pieces: every N lines, every N bytes, or N equal chunks. Pieces land on disk as `PREFIXaa`, `PREFIXab`, … (alphabetic), `PREFIX00`, `PREFIX01`, … (`-d`, numeric), or `PREFIX0`, `PREFIX1`… in hex (`-x`), and reassembly is a plain `cat` in suffix order. Where sibling `csplit` cuts at *content* boundaries (regexes, line numbers), `split` is deliberately blind to content — it is the tool for "make this 8 GB file shippable", "feed 32 workers one balanced chunk each", "compress a stream in pieces a pipeline stage can consume".

It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/split`, from upstream GNU coreutils. `split` is a POSIX utility (line- and byte-based modes, suffix-length control), so the core exists everywhere; the modern conveniences — `-n` chunk grammar, `--filter`, numeric/hex suffixes, `--additional-suffix`, `-t` — are GNU extensions.

You reach for it when a file must become many: size-limited transfers (mail gateways, FAT32, S3 multipart), parallel processing (split → per-chunk workers → recombine), memory-bounded pipelines, and test fixtures. It is often confused with `csplit` (content-driven splits) and with `head`/`tail -c` (extract one range instead of all pieces).

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/split` |
| First appeared / lineage | Early Unix/BSD heritage; GNU implementation in fileutils → coreutils |
| Standards | POSIX.1-2018 (`split`; `-l`/`-b`/`-a` core). `-n`, `--filter`, `-d`, `-x`, `-t`, `--additional-suffix` are GNU extensions |

## Synopsis

```
split [OPTION]... [FILE [PREFIX]]
```

Main forms:

```
split big.log                       # xaa, xab, ... 1000 lines each
split -l 10000 big.log part_        # part_aa.. 10000 lines each
split -b 100M image.iso img_        # img_aa.. 100 MiB each
split -n 8 -d data.bin chunk_       # 8 equal chunks, chunk_00..chunk_07
split -n l/4 -d access.log --filter='gzip > $FILE.gz' log_
```

With no `FILE`, or when `FILE` is `-`, input is read from standard input. Default prefix is `x` in the current directory; default piece size is 1000 lines.

## How It Works

### Naming: prefix + suffix + optional extra

Every piece is named PREFIX + SUFFIX. The suffix alphabet is selectable and the width via `-a N` (default 2):

```
   PREFIX      SUFFIX(-a)     --additional-suffix
   part_   +      aa       +        .log          →  part_aa.log
                      └─ -d → 00,01,02…   -x → 00..0f (hex) ─┘
```

Alphabetic suffixes are base-26 (`aa`…`zz` with `-a 2`, only 676 pieces); when they run out, split stops with `split: output file suffixes exhausted` and exit 1. Numeric (`-d`) and hex (`-x`) suffixes count from 0 and sort lexicographically as numbers *only because they are zero-padded* — which is exactly why `-d` matters for reassembly globs:

```bash
$ printf 'l1\nl2\nl3\nl4\nl5\nl6\nl7\n' > seven.txt
$ split -l 2 -d --additional-suffix=.log seven.txt log_
$ ls log_*
log_00.log  log_01.log  log_02.log  log_03.log
```

### Size modes: lines, bytes, whole-records

Three ways to bound a piece:

```bash
$ split -l 2 seven.txt part_            # 2 lines per piece → part_aa..part_ad
$ split -b 4 ten.bin chunk_             # 4 bytes per piece (mid-line cuts OK)
$ printf 'aaaa\nbbbb\ncccc\n' | split -C 8 --additional-suffix=.part - c_
$ wc -c c_*.part                        # whole lines, ≤ 8 bytes per piece
 5 c_00.part
 5 c_01.part
 5 c_02.part
```

- `-l N` counts records (lines); a final record without a trailing newline still counts as one.
- `-b N` cuts at byte N regardless of line boundaries — perfect for binary, destructive for text.
- `-C N` (`--line-bytes`) packs as many *whole* lines as fit in N bytes per piece — the text-safe byte cap.
- Size units follow coreutils conventions: `K,M,G,T,P,E,Z,Y,R,Q` (powers of 1024), `KB,MB,…` (powers of 1000), and binary prefixes like `KiB`/`MiB`.

### `-n`: the chunk grammar

`-n/--number=CHUNKS` splits into a known number of pieces up front — the piece count is the input, not the derived result:

```
N        → N equal-size byte chunks (may cut lines; last piece smaller)
K/N      → write only chunk K of N to stdout
l/N      → N chunks that never split a line (sizes may differ)
l/K/N    → only chunk K of N, line-preserving
r/N      → N chunks, round-robin record distribution
r/K/N    → only round-robin chunk K to stdout
```

Verified shapes on a 7-line file:

```bash
$ split -n l/4 -d seven.txt lin_         # line-preserving, 4 chunks
$ wc -l lin_*
 2 lin_00
 2 lin_01
 2 lin_02
 1 lin_03
$ split -n r/3 -d seven.txt rr_          # round-robin: worker shards
$ for f in rr_*; do echo "$f: $(tr '\n' ' ' < $f)"; done
rr_00: l1 l4 l7
rr_01: l2 l5
rr_02: l3 l6
$ split -n l/2/4 seven.txt               # just chunk 2 of 4, to stdout
l3
l4
```

`-n N` (bare N) is byte-exact: a 10-byte file into `-n 3` yields 4+3+3. `-u/--unbuffered` makes `split -n r/...` push records to filters as they arrive instead of buffering — for live pipelines.

### `--filter`: pieces without touching disk

`--filter=COMMAND` runs a shell command per piece, with the piece's would-be filename in `$FILE` and the piece content on the command's stdin. The command can compress, upload, or discard the bytes — nothing is written unless the filter writes it. A failing filter is reported and its status propagates:

```bash
$ printf 'hello\nworld\nagain\nbye\n' > four.txt
$ split -l 2 --filter='gzip > $FILE.gz' four.txt gz_
$ zcat gz_aa.gz; zcat gz_ab.gz
hello
world
again
bye
$ split -l 1 --filter='exit 3' seven.txt f_
split: with FILE=xaa, exit 3 from command: exit 3
$ echo $?
3
```

### Reassembly is `cat`

Pieces are contiguous byte ranges in suffix order, so `cat` in sorted suffix order reconstructs the original exactly:

```bash
$ split -b 4 ten.bin ra_
$ cat ra_a* > reassembled.bin
$ cmp ten.bin reassembled.bin && echo IDENTICAL
IDENTICAL
```

The one trap is sort order: with 100+ pieces and default 2-char alphabetic suffixes, `cat part_*` still works while widths are equal — but suffix exhaustion or mixed widths break the glob order. Fixed-width numeric suffixes (`-d`, `-a N`) keep `cat` order == numeric order.

```
original ─► split ─► [aa][ab][ac]… ─► cat (sorted) ─► byte-identical original
              │
              └─ --filter: pieces become gzip/upload/… without disk files
```

## Options That Matter

### Sizing

| Option | Effect |
| --- | --- |
| `-l N` | N lines/records per piece (default 1000) |
| `-b SIZE` | SIZE bytes per piece (mid-record cuts; `100M`-style units) |
| `-C SIZE` | At most SIZE bytes per piece, never splitting a record |
| `-n CHUNKS` | Fixed piece count: `N`, `K/N`, `l/N`, `l/K/N`, `r/N`, `r/K/N` |
| `-e` | Elide empty pieces (with `-n`; a 3-line file into 10 chunks skips empties) |
| `-u` | Unbuffered copy input to output with `-n r/...` |

### Naming

| Option | Effect |
| --- | --- |
| `-a N` | Suffix length (default 2) |
| `-d` / `--numeric-suffixes[=FROM]` | Numeric suffixes from 0 (or FROM) |
| `-x` / `--hex-suffixes[=FROM]` | Hex suffixes from 0 (or FROM) |
| `--additional-suffix=S` | Append a literal extension, e.g. `.txt` |
| `PREFIX` | Positional: `split [FILE] PREFIX` (default `x`) |

### Plumbing

| Option | Effect |
| --- | --- |
| `--filter=COMMAND` | Pipe each piece to COMMAND with `$FILE` set; filter exit status propagates |
| `-t SEP` | Record separator character (single char; `'\0'` for NUL) |
| `--verbose` | Print `creating file 'xaa'` as each piece opens |

Bad sizes are rejected up front: `split -l 0` → `split: invalid number of lines: '0'`, exit 1; `split -t ab` → `split: multi-character separator 'ab'`.

## Usage Patterns

```bash
# Make an ISO shippable through a 2 GiB channel, reassemble later
split -b 2G -d big.iso big.iso.part-
# ... on the receiving side:
cat big.iso.part-* > big.iso
```

```bash
# Split a log into 10k-line pieces with self-describing names
split -l 10000 -d --additional-suffix=.log access.log access.log.
```

```bash
# Parallel gzip: one worker per piece, no intermediate files
split -n 8 --filter='gzip -1 > $FILE.gz' -d dump.sql dump.sql.gz.
```

```bash
# Balanced line-preserving chunks for 4 parallel analyzers
split -n l/4 -d events.jsonl events.
```

```bash
# Process just the second quarter in a pipeline (no temp files)
split -n l/2/4 huge.csv | analyzer --quarter2
```

```bash
# Round-robin sharding: each worker gets every 4th record
split -n r/4 -u -d --filter='worker > worker-$FILE.out' - stream_ 
```

```bash
# Text-safe byte caps: whole lines only, ≤ 64 KiB per piece
split -C 64K -d messages.txt msg_
```

```bash
# Split stdin from tar without a temp file (chunked archive upload)
tar -czf - project/ | split -b 500M -d - project.tar.gz.
```

```bash
# NUL-delimited records (filenames with newlines survive)
find . -name '*.tmp' -print0 | split -t '\0' -l 1000 -d - batch_
```

```bash
# CSV split on comma-delimited "records" instead of lines
split -t ',' -l 100 -d wide.csv wide.
```

```bash
# Watch the pieces as they are created
split -l 1 --verbose seven.txt dbg_
```

```bash
# Suffix headroom: expect ~20000 pieces → 5-digit numeric suffixes
split -l 500 -d -a 5 huge.log piece-
```

## Nuances and Gotchas

- **Default output litters the cwd as `xaa`, `xab`…** and a second `split` run *overwrites* existing pieces without asking. Always pass an explicit PREFIX in scripts; treat bare `split file` as an interactive-only shortcut.
- **`-b` and bare `-n N` can cut lines mid-record.** Byte-exact chunks are what you want for binaries and chunk counts, and what corrupts text processing. Use `-n l/N` or `-C` when records must survive intact.
- **Suffix exhaustion is a real failure mode.** Alphabetic base-26 gives 676 pieces at `-a 2`; more input dies with `output file suffixes exhausted` (exit 1) after filling the namespace. Size the suffix first (`-d -a 5`).
- **Lexicographic order is the reassembly contract.** `cat part_*` relies on the shell glob sorting suffixes the same way split generated them. Mixed suffix widths (`-a 1` overflow into `aa`) or unpadded numerics break it; fixed-width `-d` suffixes are the safe default.
- **`--filter` substitutes `$FILE` textually, then hands the result to the shell** — so `gzip > "$FILE.gz"` and `gzip > $FILE.gz` both work, but anything you expect split to "add" (like the piece name when `$FILE` is absent) does not happen: the command simply reads the piece on stdin. And a failing filter aborts the split and propagates the exit status (verified: `exit 3` from the filter → split exits 3 with `split: with FILE=xaa, exit 3 from command`).
- **`-t` takes exactly one character.** Multi-character separators are rejected; for NUL use the literal two-character spelling `'\0'`. `-t` changes both how records are counted (`-l`, `-n l/`, `r/`) and what a "line" means.
- **`-e` only applies to `-n` mode.** Line/byte mode always writes the final short piece (a legitimate part of the data); with `-n`, empty chunks can appear when the input is smaller than the chunk count, and `-e` suppresses exactly those.
- **POSIX portability subset.** POSIX split guarantees `-a`, `-b`, `-l` and alphabetic suffixes only. `-n`, `--filter`, `-d`, `-x`, `-t`, `--additional-suffix` are GNU; busybox implements a subset with its own gaps. Keep critical scripts in the POSIX core or require GNU coreutils explicitly.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | All pieces written (or filtered) successfully |
| 1 | Usage or I/O failure: bad size/chunks, unwritable target, suffix exhaustion, multi-char `-t` |
| filter's status | With `--filter`, a failing COMMAND aborts the split and split exits with that status (e.g. 3) |

## Related Commands

- [`csplit`](./csplit.md) — content-driven splits (regex/line-number patterns) where boundaries live in the data.
- [`cat`](./cat.md) — the reassembly half of every split workflow.
- [`head`](./head.md) / [`tail`](./tail.md) — extract a single leading/trailing range instead of all pieces.
- [`dd`](./dd.md) — seek/read one arbitrary byte range; the manual alternative to `split -n K/N`.
- [`numfmt`](./numfmt.md) — humanize the piece sizes split reports in scripts.
- [`wc`](./wc.md) — count lines first so `-l`/`-n` targets are chosen deliberately.
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [xargs](../../shell/xargs.md) — the other half of fan-out processing: feed pieces to parallel workers.

## Interview Questions

### Q: How do you split a 10 GB file into 1 GB pieces and guarantee lossless reassembly?

`split -b 1G -d big.iso big.iso.part-` then `cat big.iso.part-* > big.iso`. Losslessness follows from two properties: pieces are contiguous byte ranges, and `-d`'s zero-padded suffixes sort lexicographically in generation order, so the glob expands in the right sequence. Verify with `cmp` or a checksum (`sha256sum`) end-to-end. If the receiver's shell is the risk, name pieces so *string* sort is unambiguous — never unpadded numerics.

### Q: What is the difference between `split -n 8 file` and `split -n l/8 file`?

`-n 8` produces 8 byte-exact equal chunks — the boundaries can fall inside a line, which is fine for binary data and wrong for line-oriented processing. `l/8` ("lines") still produces up to 8 chunks but never splits a record, so chunk sizes differ slightly. A follow-up worth knowing: `l/2/8` streams only the second chunk to stdout, enabling per-chunk pipelines without temp files.

### Q: When do you choose `split --filter` over writing pieces to disk?

Whenever the piece is an intermediate: compression (`gzip > $FILE.gz`), upload, encryption, or feeding a worker — disk I/O and namespace churn disappear, and the filter's exit status propagates so a failed piece fails the split. Two cautions: `$FILE` is substituted literally by split (write `> $FILE.gz`, not `> "$FILE.gz"`), and filters run sequentially as each piece completes, so parallelism must come from the filter command itself.

### Q: A script does `split -l 1000 data.csv` and later `cat x?? | process`. Which failure do you predict first?

The bare default prefix `x` collides with any other `x??` files in the cwd and gets silently overwritten on re-runs; and once the piece count exceeds 676 (`-a 2` alphabetic limit) split aborts with `output file suffixes exhausted`, leaving a partial dataset. The robust version pins a namespaced prefix, numeric zero-padded suffixes sized for the worst case, and a real extension: `split -l 1000 -d -a 4 --additional-suffix=.csv data.csv data.csv.part-`.

### Q: How would you shard a stream across four identical workers so each record goes to exactly one of them?

`split -n r/4 -d --filter='worker > /dev/null' - shard_` — the round-robin grammar (`r/N`) distributes records one per chunk in turn, each worker seeing every fourth record. Unlike `l/N` (contiguous blocks), round-robin balances skew: a hot region of the input does not land on a single worker. `-u` makes the distribution unbuffered for live streams, and `r/K/N` lets you reprocess just one shard.

### Q: Why is `split` in POSIX while so many of its useful flags are GNU extensions?

POSIX fixed the 1980s interface: line and byte splitting with alphabetic suffixes — the parts every vendor had implemented identically. The chunk grammar (`-n`), filters, and alternative suffix alphabets came later from GNU, where pipelines got big enough to need them. The practical interview answer: treat `-l`/`-b`/`-a` as portable, feature-detect or require GNU coreutils for the rest, and know that `csplit` carries the POSIX *content*-splitting flag set.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/split.1.en.html)
