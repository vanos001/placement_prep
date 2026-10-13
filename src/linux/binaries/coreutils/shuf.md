# shuf — random permutation and sampling of input lines

## Overview

`shuf` writes a random permutation of its input lines to standard output. It has three input modes: lines of a file (or stdin), arguments given with `-e`, and a numeric range given with `-i LO-HI`. Combined with `-n COUNT` it becomes a sampler: "give me 5 of these 10,000 lines, without repeats" is one command. With `-r` it samples *with* replacement — a bootstrap sampler — and with `--random-source=FILE` its entire permutation becomes reproducible.

It ships in the `coreutils` package (Debian bookworm) at `/usr/bin/shuf`, from upstream GNU coreutils. It is a GNU addition (mid-2000s, coreutils 6.x era), not POSIX: BSD/macOS base systems do not ship it, so portable scripts either guard for it or accept a coreutils dependency.

You reach for `shuf` when order should be random or a subset should be chosen uniformly: picking test cases, dealing quiz questions, generating throwaway sample data, choosing random ports/IDs from a range, or bootstrap-resampling a dataset. It is often confused with `sort -R` (see below — related goal, different semantics) and with ad-hoc bash tricks like `$RANDOM`-based index arithmetic, which are easy to get subtly non-uniform.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/shuf` |
| First appeared / lineage | GNU coreutils addition, 6.x era (mid-2000s); upstream GNU coreutils |
| Standards | Not POSIX; GNU coreutils convention |

## Synopsis

```
shuf [OPTION]... [FILE]
shuf -e [OPTION]... [ARG]...
shuf -i LO-HI [OPTION]...
```

Main forms:

```
shuf file.txt                    # permute all lines of file.txt
shuf -n 3 file.txt               # 3 lines chosen uniformly, no repeats
shuf -i 1-6                      # permute the numbers 1..6 (one die roll)
shuf -r -n 10 -e A B C           # 10 draws with replacement from A/B/C
shuf --random-source=seed.bin file   # deterministic permutation
```

With no `FILE`, or when `FILE` is `-`, input is read from standard input. Empty input produces empty output and exit 0.

## How It Works

### Input modes and the permutation

`shuf` reads its input as *records* — lines by default, NUL-delimited fields with `-z` — then emits all of them once, in a uniformly random order:

```
input records           internal reservoir            output (one permutation)
┌────────┐             ┌────────────────┐             ┌────────┐
│ alpha  │             │ shuffled array │             │ delta  │
│ bravo  │  ────────►  │ [d][a][c][b]   │  ────────►  │ alpha  │
│ charlie│             └────────────────┘             │ charlie│
│ delta  │                                           │ bravo  │
└────────┘                                           └────────┘
```

All three input modes produce the same record list:

```bash
$ printf 'alpha\nbravo\ncharlie\ndelta\n' | shuf
charlie
delta
alpha
bravo
$ shuf -e alpha bravo charlie delta        # same input as arguments
$ shuf -e $(printf 'alpha bravo charlie delta')   # word-splitting variant
$ seq 1 4 | shuf                           # same records via a generator
```

Records are taken literally: duplicates in the input are *distinct* records. `printf 'a\na\nb\n' | shuf` still outputs three lines — two of them `a`. `shuf` permutes records; it does not deduplicate (that is `sort -u`/`uniq` territory).

### `-n`: sampling without replacement

`-n/--head-count=COUNT` limits output to at most COUNT records. Because the internal permutation is drawn as needed, `-n K` on an N-line input is exactly "K uniformly chosen distinct lines" — sampling without replacement:

```bash
$ shuf -n 2 words.txt        # two different lines, order random
bravo
charlie
$ shuf -n 2 words.txt        # a different draw each run
charlie
alpha
```

Two edge behaviors worth knowing cold:

- COUNT is a *cap*, not a quota: `shuf -n 99 words.txt` on a 4-line file prints 4 lines, no error. `shuf -n 0` prints nothing.
- Recent GNU `shuf` combines `-n` with `-i LO-HI` without materializing the range: `shuf -i 0-2000000000 -n 3` answers instantly. *Without* `-n`, the whole range is generated in memory first — under a 2 GB virtual-memory cap, `shuf -i 0-2000000000` dies with `shuf: memory exhausted`.

### `-r`: sampling with replacement

`-r/--repeat` removes the "each record once" constraint: each output line is an independent uniform draw from the input. That is the bootstrap-resample primitive. It also means the output is infinite unless `-n` bounds it — `shuf -r words.txt` runs forever (piping into `head` only stops it via SIGPIPE):

```bash
$ shuf -r -n 4 -e A B        # 4 independent draws
A
A
B
A
```

### Determinism with `--random-source`

By default `shuf` draws entropy from the system's random source, so every run differs. `--random-source=FILE` replaces it with bytes from FILE, consumed as needed — the same source file with the same input and flags yields the identical permutation, byte for byte:

```bash
$ head -c 64 /dev/urandom > seed.bin
$ shuf --random-source=seed.bin -i 1-8
2
3
4
5
7
6
1
8
$ shuf --random-source=seed.bin -i 1-8    # again: identical output
2
3
4
5
7
6
1
8
```

The source is consumed as a byte stream: a source too small for the number of decisions fails with `shuf: 'seed': end of file` and exit 1 (observed for a 1-byte seed against a 30-line input). `/dev/zero` is a valid — and maximally reproducible — source for tests.

### `shuf` vs `sort -R`

Both "randomize", but they answer different questions:

```bash
$ printf 'x\ny\nx\nz\nx\nz\n' | sort -R      # duplicate keys clump together
y
z
z
x
x
x
$ printf 'x\ny\nx\nz\nx\nz\n' | shuf          # duplicates stay scattered
z
x
x
x
z
y
```

- `sort -R` sorts by a random hash *of the line content*: identical lines hash identically and therefore land adjacent. It also re-runs differently each time unless you pass `--random-source=FILE` (supported by GNU sort too).
- `shuf` permutes *records* regardless of content: duplicates scatter uniformly.
- For "shuffle a playlist/file list", either works; for "pick K of N" only `shuf -n K` is correct; for "unsort a sorted stream with many duplicates", `shuf` is the honest choice.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-e` | Treat each ARG as an input line (no file/stdin) |
| `-i LO-HI` | Treat each number LO..HI as an input line (inclusive range) |
| `-n COUNT` | Output at most COUNT lines (a cap, never a quota) |
| `-r` | Sampling with replacement; output unbounded without `-n` |
| `-o FILE` | Write the result to FILE instead of stdout |
| `--random-source=FILE` | Draw the randomness from FILE (reproducible permutations) |
| `-z` | NUL-delimit input records and output (pairs with `find -print0`/`xargs -0`) |

Range parsing rejects anything that is not `LO-HI` with `LO <= HI`: `shuf -i 5-3` → `shuf: invalid input range: '5-3'`, exit 1. GNU `shuf -o` may name the input file itself (the input is read before the output is written) — an in-place shuffle one-liner.

## Usage Patterns

```bash
# Shuffle the order of test cases for a runner
find tests -name '*.t' | sort | shuf > /tmp/test-order.txt
```

```bash
# Pick 3 winners uniformly from a participant list
shuf -n 3 participants.txt
```

```bash
# Two fair dice
shuf -i 1-6 -n 2
```

```bash
# Random IDs from a range, no repeats (e.g. coupon codes)
shuf -i 10000000-99999999 -n 5
```

```bash
# Bootstrap resample of 1000 rows (duplicates expected)
shuf -r -n 1000 observations.csv > bootstrap.csv
```

```bash
# Shuffle 5 of the top-1M words in a dictionary for a vocab quiz
head -n 1000000 /usr/share/dict/words | shuf -n 5
```

```bash
# Shuffle arguments, not files (deal roles to players)
shuf -e assassin doctor detective bystander
```

```bash
# Filename-safe shuffle: NUL-delimited end to end
find . -maxdepth 1 -type f -print0 | shuf -z | xargs -0 -I{} process {}
```

```bash
# Reproducible shuffles for a test suite: pin the random source
shuf --random-source=fixtures/seed.bin -n 10 cases.txt > sample.txt
```

```bash
# In-place shuffle of a file (GNU: -o may name the input)
shuf -o playlist.txt playlist.txt
```

```bash
# Random ordering inside a Makefile check target
check: ; @for t in $$(cat test-order.txt); do ./run $$t || exit 1; done
```

```bash
# Coin flip
shuf -n 1 -e heads tails
```

## Nuances and Gotchas

- **`-r` without `-n` never terminates.** With replacement enabled there is no natural end; `shuf -r file` is an infinite stream. Script it only behind `-n` (or an intentional `| head`, which stops it via SIGPIPE).
- **`-n` is "at most", not "exactly".** COUNT above the input size silently yields the whole input. If you need an error when the pool is too small for the sample size, check `wc -l` first — `shuf` will not warn.
- **Huge `-i` ranges need `-n` (or memory).** Without `-n`, `shuf` builds the entire range in RAM; a 2-billion-number range needs far more than a laptop wants to give. With `-n`, recent GNU coreutils streams the range and stays flat.
- **Duplicates are distinct records.** `shuf` never deduplicates; three identical input lines can all be drawn. And unlike `sort -R`, it never groups equal lines — that is the design difference, not a bug in either tool.
- **`--random-source` fails hard when exhausted** (`shuf: 'seed': end of file`, exit 1) and its consumption pattern is an implementation detail: the same seed reproduces a permutation only for the same coreutils build, same input, and same flags. Treat it as a test fixture, not a stable interface.
- **`shuf` is a game/sampling tool, not a key generator.** The default source is the system RNG, but `shuf`'s contract is a permutation of lines, not cryptographic output; for key material use `openssl rand`/`head -c N /dev/random`.
- **Portability.** Not POSIX; absent from macOS/BSD base installs (install GNU coreutils, where it may arrive as `gshuf` via package managers) and from older minimal/busybox images. Scripts may need a fallback (e.g. `sort -R` where only GNU sort exists).
- **Empty input is not an error**: `printf '' | shuf` → no output, exit 0. Combined with a typo'd glob (`shuf *.log` when none exist) the failure is silent — quote and count inputs in CI contexts.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Permutation (or sample) written successfully, including empty input |
| 1 | Any failure: unreadable input, invalid `-i` range, `--random-source` exhausted or unreadable |

## Related Commands

- [`sort`](./sort.md) — `-R` is the content-hash "unsort"; `shuf` is the record permutation and the sampler.
- [`seq`](./seq.md) — generates the ranges `shuf -i` can also produce, plus floats and formatted sequences.
- [`tail`](./tail.md) — `head-count` on a shuffled stream vs. deterministic first/last N.
- [`wc`](./wc.md) — count the pool before sampling so `-n` cannot silently exceed it.
- [`head`](./head.md) — fixed prefix selection; pairs with `shuf` for "random order, then take the first K".
- [Collection overview](./overview.md) — the GNU Coreutils chapter hub.
- [find](../../shell/find.md) — produces the file lists `shuf` loves to randomize.

## Interview Questions

### Q: How would you select 100 random lines from a 10-million-line file, and why not `sort | head`?

`shuf -n 100 bigfile.txt`. The naive `shuf bigfile | head -n 100` permutes all ten million lines first; `-n` lets recent GNU shuf stop after drawing 100. `sort -R | head` is worse: it hashes every line and does a full sort. If `shuf` is unavailable, the fallback is reservoir sampling in `awk` — which is exactly the algorithm GNU shuf uses internally for the `-n` + range case.

### Q: What is the difference between `shuf -r` and plain `shuf`?

Plain `shuf` is a permutation: every input record appears exactly once, so `-n K` samples without replacement. `-r` makes each output line an independent draw with replacement — duplicates appear, and the stream is infinite unless `-n` bounds it. Interviewers probe this because `-r -n K` is precisely a bootstrap resample, a common data-analysis task.

### Q: You must produce the same "random" order on every CI run to make a flaky test reproducible. How?

`--random-source=FILE` with a committed seed file: `shuf --random-source=seed.bin -i 1-1000`. The same seed, input, and flags reproduce the permutation byte-for-byte; a too-small seed file fails loudly with `'seed': end of file`. Note the caveat that the consumption pattern is not a guaranteed interface across coreutils versions — pin the tool version in the CI image if the order must survive upgrades.

### Q: Why does `shuf -i 0-4294967295 -n 3` succeed but `shuf -i 0-4294967295` blow up memory?

With `-n`, GNU shuf samples incrementally (reservoir/Floyd-style) and never materializes the range. Without `-n` it must generate every number in the range into memory before emitting anything — four billion entries, gigabytes of RAM. The design lesson: `shuf`'s memory profile depends on the mode, and "generate a permutation" and "sample K of N" are different operations under the hood.

### Q: Your shuffle of a log file produced all duplicate lines adjacent, and a colleague blamed shuf. What actually happened?

They used `sort -R`. GNU sort's random sort hashes line *content*, so identical lines get identical keys and cluster together; `shuf` permutes records, scattering duplicates. Both are defensible behaviors, but only `sort -R` groups; if the file had many duplicate lines, the clustering is the tell. The fix is choosing the tool that matches the intended semantics — record-level shuffling means `shuf`.

### Q: Is `shuf` secure enough for generating passwords or tokens?

No. Its contract is uniform permutation of input records for sampling and ordering; it neither promises nor documents cryptographic output, and `--random-source` explicitly lets you weaken the entropy. For secrets, read bytes directly from the kernel RNG (`openssl rand -hex 32`, `head -c 32 /dev/urandom`). The interview point is knowing that "uses randomness" and "cryptographically secure" are different claims.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/shuf.1.en.html)
