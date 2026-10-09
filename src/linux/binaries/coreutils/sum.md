# sum — Legacy BSD/System V file checksums

## Overview

`sum` prints a small, non-cryptographic checksum and a block count for each input file (or stdin). It is a fossil from early Unix with two personalities: the BSD algorithm (the default in GNU coreutils, 16-bit checksum over 1K blocks) and the System V algorithm (`-s`, 16-bit checksum over 512-byte blocks). Neither offers cryptographic value; both exist today for compatibility with decades-old scripts and data conventions.

On Debian and Ubuntu the binary ships in the `coreutils` package at `/usr/bin/sum`. Both algorithms predate the modern checksum family by many years — the BSD form goes back to the earliest BSD releases, the SysV form to AT&T System V — and POSIX deliberately standardized the *successor* instead: `cksum` (a CRC-32-based checksum with a POSIX-defined output), which is what portable scripts should reach for. `sum` remains installed because removing it breaks old toolchains; new code should treat it as a last resort.

Reach for `sum` when an ancient workflow or a piece of retrocomputing documentation demands it — verifying files restored from old archives, replicating a 1980s-90s transfer protocol's parity checks — or when you need the cheapest possible error detection. For anything else, the ladder is: `cksum` (portable, non-cryptographic) → [`md5sum`](./md5sum.md) (legacy integrity) → [`sha256sum`](./sha256sum.md) (the modern default).

It is often confused with `cksum` (different algorithm and output, POSIX), with `cksum -o sum`-style compatibility options in newer coreutils, and with [`b2sum`](./b2sum.md)-family tools that share nothing with it except the word "checksum".

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — user commands |
| Path | `/usr/bin/sum` |
| First appeared / lineage | BSD `sum` (early BSD) and System V `sum` (AT&T), 1970s-80s Unix |
| Standards | Not POSIX; POSIX standardized `cksum` as its replacement |

## Synopsis

```
sum [OPTION]... [FILE]...
```

```bash
sum file                         # BSD algorithm (default), 1K blocks
sum -r file                      # same BSD algorithm, spelled explicitly
sum -s file                      # System V algorithm, 512-byte blocks
sum - < stream                   # checksum standard input
```

With no `FILE`, or when `FILE` is `-`, standard input is read. Output is two fields: the 16-bit checksum and the block count.

## How It Works

### Two algorithms, one binary

Both algorithms accumulate the input bytes into a 16-bit word with wrap-around addition, then fold in the carry bits ("checksum" in the oldest sense of the word):

```
byte stream ──► 16-bit wrap-around sum ──► fold carries ──► print 5-digit checksum + block count
                     │
        BSD (-r): 1 KiB blocks, rotate-accumulate variant
        SysV (-s): 512-byte blocks, plain 16-bit sum, byte-swap folding
```

- **BSD mode (`-r`, the GNU default):** sums bytes into a 16-bit accumulator with right-rotation between bytes, reporting per 1 KiB block counts. Historic quirk: BSD sum used 1024-byte blocks, GNU follows that.
- **SysV mode (`-s`/`--sysv`):** a plain modulo-2^16 byte sum with byte-swapped addition, reporting 512-byte blocks.

Both algorithms are five lines of code, which is exactly why they survive so well in documentation — any language can reproduce them. The BSD one, run over `x\ny\n` in Python, reproduces the tool's `00088` exactly:

```bash
$ python3 -c "data=b'x\\ny\\n'; c=0
for b in data:
    c = (c >> 1) + ((c & 1) << 15)   # rotate the 16-bit accumulator right
    c = (c + b) & 0xffff             # add the byte, keep 16 bits
print(c)"
88                                     # = the 00088 that sum prints
```

The rotation is what makes BSD sum sensitive to *where* bytes sit in the stream — `ab` and `ba` rotate differently — while the SysV variant is a pure running total (`120+10+121+10 = 261`), which is why byte reordering leaves it unchanged.

Neither is order-sensitive in any useful cryptographic sense: reordering bytes, padding, or crafting input can trivially produce identical checksums. They detect *transmission damage* (dropped/corrupted bytes on a noisy line) and nothing else. That was the 1970s threat model — and it is exactly why the tools survive in tape-archive and legacy-transfer documentation.

### The 16-bit ceiling, in numbers

A 16-bit checksum space has 65,536 values. For random inputs the birthday math is unforgiving: among N files, the chance that at least two share a checksum is about `1 - exp(-N(N-1)/2/65536)`. At N = 300 files that is already ~50% — a coin flip that two of them "verify" identically by chance. Crafted collisions are worse: reordering bytes defeats SysV mode entirely, and a short appended suffix (three bytes suffice in practice) steers the BSD accumulator back to any target value. The numbers explain the tool's historical niche: one tape, one transfer, one comparison — never a corpus.

The same math is why modern replacement choices scale the way they do: CRC-32 (`cksum`) gives ~11,000 expected collisions across 10 million files; 128-bit MD5 makes accidental collisions negligible but is broken against adversaries; SHA-256 is the default answer for both scales.

### The compatibility ladder: `cksum -a bsd` and `-a sysv`

Recent GNU coreutils folded both legacy algorithms into `cksum` as algorithm selectors, with byte-identical output — including the zero-padding and block-count conventions:

```bash
$ printf 'x\ny\n' | sum        ; printf 'x\ny\n' | cksum -a bsd
00088     1
00088     1
$ printf 'x\ny\n' | sum -s     ; printf 'x\ny\n' | cksum -a sysv
261 1
261 1
```

That equivalence is the modern exit path: a script can keep parsing the legacy two-field format while migrating the tooling to one binary. It also means the algorithms are now documented in one place — [`cksum`](./cksum.md) — and `sum` survives as the historical spelling.

### Output formats differ by mode

The two modes also print differently, which breaks naive parsing across modes:

```bash
$ printf 'x\ny\n' | sum
00088     1
$ printf 'x\ny\n' | sum -s
261 1
```

BSD mode zero-pads the checksum to five digits and uses a wide column; SysV mode prints bare numbers. Both then print the block count: 1 KiB blocks in BSD mode, 512-byte blocks in SysV mode. `sum file` where `file` is empty prints `00000     0` (BSD) — a legitimate use as a cheap emptiness probe, though `wc -c` (see [`wc`](./wc.md)) is clearer.

### There is no check mode

Unlike the [`md5sum`](./md5sum.md) family, `sum` has no `-c` verification protocol, no manifest format, no digest-list conventions. Verification is DIY: capture the output, re-run, compare the strings. That single omission explains most of its decline — the checksum-file workflow that made md5sum/sha256sum operationally central simply does not exist here.

## Options That Matter

| Option | Effect |
|---|---|
| `-r` | BSD algorithm: 16-bit rotate-add checksum, 1 KiB block count (the GNU default) |
| `-s`, `--sysv` | System V algorithm: plain 16-bit sum, 512-byte block count, unpadded output |

That is the entire manual. `sum --help` fits on one screen — by contrast the modern family shares a page-worth of options through `md5sum`'s interface (documented in [`md5sum`](./md5sum.md)).

## Usage Patterns

```bash
# Legacy verification: same command, compare numbers by eye or test
sum oldtape.img
```

```bash
# System V flavor for scripts written on AT&T systems
sum -s vendor.bios
```

```bash
# Cheap spot check that a transfer produced identical bytes
sum a.tar | awk '{print $1}' > a.sum
sum b.tar | awk '{print $1}' | cmp - a.sum
```

```bash
# Emptiness probe on a pipe (checksum 00000, zero blocks)
lsof -p $$ 2>/dev/null | sum - | awk '{print $1, $2}'
```

```bash
# Cross-check a restored archive against the number recorded in an old README
sum -s README.data
```

```bash
# Demonstrate why it's not integrity: SysV sum ignores byte order (toy)
printf 'ab' | sum -s | awk '{print $1}'; printf 'ba' | sum -s | awk '{print $1}'
```

```bash
# Cross-check a legacy number with the modern front-end (identical output)
sum archive.img | awk '{print $1}'
cksum -a bsd archive.img | awk '{print $1}'
```

```bash
# Checksum a stream without a temp file (also: the cheap tar integrity probe)
tar -cf - dir/ | sum -
```

```bash
# Sweep a directory in both modes; pin the mode or the columns lie
sum -r *.bak | sort -n
sum -s *.bak | sort -n
```

```bash
# Block-count column as a rough size check: 1 KiB units in BSD mode
head -c 1500 /dev/urandom > blob && sum blob | awk '{print $2}'   # 2 blocks
```

## Nuances and Gotchas

- **Not interchangeable with `cksum`.** Different algorithm (CRC-32), different output (unpadded CRC, byte count), POSIX-standardized. `cksum` is the portable successor; `sum` output is meaningful only to other `sum` runs with the same mode.
- **Mode changes both the number *and* the meaning of the second column.** BSD counts 1 KiB blocks, SysV counts 512-byte blocks; scripts that parse the block count must pin the mode.
- **Checksums are 16 bits.** Two random files collide with probability 1/65536 — and crafted collisions are trivial. This is error *detection*, not identification. Interview one-liner: `sum` answers "was the tape readable?", never "is this the same file?".
- **No manifest protocol.** Any "verify with sum" workflow is hand-rolled string comparison; portability between BSD and SysV modes, or across block-size conventions, is not guaranteed.
- **busybox and other implementations historically diverged.** Default mode and block-size conventions varied by Unix flavor; the `-r`/`-s` spellings are the only thing POSIX-adjacent about the tool. When reproducing a documented legacy checksum, match the mode exactly.
- **The block count is not a byte count.** BSD mode reports 1 KiB blocks, SysV mode 512-byte blocks — both rounded up — so the second column is neither comparable across modes nor equal to file size. Use `wc -c` (see [`wc`](./wc.md)) when bytes matter.
- **Exit 0 says nothing about corruption.** The only failure sum reports is an unreadable input; a damaged-but-readable file still exits 0, and the *printed value* is the entire verdict. Scripted verification therefore means capturing output and comparing strings — there is no `-c`, no `--status`, no manifest grammar to lean on.
- **Reproduce it anywhere.** Both algorithms are a handful of lines (see the Python walkthrough above), so legacy checksums in vendor docs can be re-derived when no `sum` binary is available — a portability property no modern digest shares with it.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Checksums computed successfully for all inputs |
| 1 | An input could not be opened or read |

There are no verification, formatting, or strictness modes to influence the code — the tool's entire contract is one line per input plus a read failure exit.

## Related Commands

- [`md5sum`](./md5sum.md) — the family anchor with a real manifest/`-c` protocol; the immediate upgrade path.
- [`sha256sum`](./sha256sum.md) — the modern default for integrity checking.
- [`wc`](./wc.md) — byte/line counting when you want a completeness probe rather than a checksum.
- [`b2sum`](./b2sum.md) — modern fast hashing with tunable digest length.
- [`overview`](./overview.md) — collection hub for the GNU Coreutils binaries.

## Interview Questions

### Q: What does `sum` actually compute, and what threat model is it for?

A 16-bit wrap-around additive checksum (with rotation in BSD mode) plus a block count — an error-*detection* code from the era of noisy serial lines and tapes. It answers "did transmission damage this byte stream?", not "could someone have crafted this input?". Collisions are trivial to construct and common by chance (1/65536). For identification or integrity against adversaries, use `cksum` at minimum, realistically the [`sha256sum`](./sha256sum.md) family.

### Q: Why did POSIX standardize `cksum` instead of `sum`?

Because `sum` had fragmented: BSD and SysV shipped different algorithms, block sizes, and output formats, so a POSIX `sum` would have blessed one incompatible tradition. `cksum` sidestepped the fight with a fresh POSIX-defined CRC-32 and a fixed output format (`<crc> <byte-count> <name>`), giving scripts a single portable contract. The lesson — standardize the successor when the incumbent has forked — is the reason `sum` survives only as a compatibility fossil.

### Q: A 1990s runbook says "verify the backup with `sum` and compare to the recorded number." What do you check before trusting a match?

Three things. Mode: BSD vs SysV numbers are unrelated, and the runbook must match the flag used (`-s` or default). Scope: a 16-bit match says the file is *plausibly* intact — equal-length, equal-sum inputs collide easily, so treat it as corruption detection only. And provenance: the recorded number must come from the same convention (block size differences even change the second column). If the data matters today, re-baseline it with a real digest alongside the legacy check.

### Q: Why would `sum` ever still be installed on a modern distro?

Backward compatibility, plain and simple. Decades of scripts, vendor runbooks, retrocomputing workflows, and data-convention documents reference it; removing it costs nothing to keep and breaks those quietly. Coreutils carries it alongside `cksum`'s `-o` compatibility modes so old checksum records remain reproducible — a small maintenance cost for uninterrupted operational history.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/sum.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
