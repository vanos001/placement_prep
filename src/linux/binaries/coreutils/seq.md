# seq — print a sequence of numbers

## Overview

`seq` prints arithmetic sequences: `seq 1 5` prints `1` through `5`, one per line. It is the standard shell-side source of loop counters, zero-padded filenames, repeat counts, and cheap numeric test data — the tool you reach for whenever a shell loop needs `for i in $(seq 1 10)` or a pipeline needs N lines of input.

On Debian and Ubuntu it ships in the `coreutils` package at `/usr/bin/seq`, from upstream GNU coreutils. The command descends from GNU shellutils (early 1990s) and has since been reimplemented by BusyBox, the BSDs, and macOS — but unlike its neighbors `wc`, `tee`, and `uniq`, it is **not** POSIX-standardized. Portable POSIX `sh` has no `seq` and no brace expansion; scripts that must run under `dash` use `while` loops or `awk` instead.

`seq` is often confused with two lookalikes. Bash brace expansion `{1..5}` expands in the shell before any command runs — no subprocess, but literal-only, no variables, no floats. And `awk` loops (`awk 'BEGIN{for(i=1;i<=5;i++) print i}'`) are fully general but verbose. Choosing between the three, and knowing where each breaks, is the interview core of this page.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 — User commands |
| Path | `/usr/bin/seq` |
| First appeared / lineage | GNU shellutils, early 1990s; BusyBox/BSD/macOS reimplementations since |
| Standards | None — not in POSIX.1-2018; de-facto standard across Linux, *BSD, macOS |

## Synopsis

```
seq [OPTION]... LAST
seq [OPTION]... FIRST LAST
seq [OPTION]... FIRST INCREMENT LAST
```

All three numeric arguments are parsed as floating point. Main forms:

```
seq 5                  # 1 2 3 4 5        (FIRST=1, INCREMENT=1)
seq 2 6                # 2 3 4 5 6        (INCREMENT defaults to 1)
seq 10 -2 2            # 10 8 6 4 2       (negative step counts down)
seq -w 1 10            # zero-padded to equal width
seq -s, 1 5            # 1,2,3,4,5        (custom separator)
seq -f '%05.1f' 1 2    # printf-style float formatting
```

With no FIRST, it defaults to 1. With no INCREMENT, it defaults to **1 even when LAST is smaller than FIRST** — a rule with an empty-output consequence shown below.

## How It Works

### Argument forms and the stop rule

`seq` reads its numeric arguments left to right and decides which form you mean by count: one number = LAST, two = FIRST and LAST, three = FIRST, INCREMENT, LAST. The sequence ends when the *next* step would jump past LAST:

```
$ seq 1 3 10            # 1, 4, 7 — next would be 10? 7+3=10 not > 10
1
4
7
10
$ seq 1 3 9
1
4
7                       # 7+3=10 > 9, so 10 never prints
```

Two consequences follow directly from the rule "omitted INCREMENT defaults to 1":

```
$ seq 10 1              # meant "count down"? nothing prints
$ echo $?
0
$ seq 5 1 10            # meant FIRST=5, LAST=10, step 1? got FIRST=5, INCREMENT=1, LAST=10
5
6
7
8
9
10
```

`seq 10 1` exits **0 with no output**: LAST < FIRST with a positive increment means an empty sequence, not an error. Counting down needs an explicit negative step (`seq 10 -1 1`), and a zero increment is a hard error:

```
$ seq 1 0 5
seq: invalid Zero increment value: '0'
$ echo $?
1
```

```
┌───────────────────────────── seq 1 3 10 ─────────────────────────────┐
│                                                                      │
│  current = FIRST (1)                                                 │
│     │                                                                │
│     ▼                                                                │
│  ┌──────────────┐   current > LAST? ── yes ──► stop (exit 0)         │
│  │ print current│        │                                           │
│  └──────┬───────┘        no                                          │
│         │            ▼                                               │
│         └─────── current += INCREMENT (3): 1 → 4 → 7 → 10 → stop     │
└──────────────────────────────────────────────────────────────────────┘
```

Internally everything is a `long double`: `seq 1e10` is fine, and no integer-overflow traps exist. The price is float formatting (below).

### Default output format

The format is chosen from the inputs: if FIRST, INCREMENT, and LAST are all fixed-point decimal numbers, the format is `%.PRECf` where PREC is the maximum precision seen; otherwise `%g`:

```
$ seq 3                 # all integers → %.0f
1
2
3
$ seq 0.5 1.5           # one decimal → %.1f
0.5
1.5
$ seq 1e9 1e9 3e9       # scientific input → %g output
1e+09
2e+09
3e+09
```

### -w: equal width, not printf

`-w`/`--equal-width` pads every number with leading zeros to the width of the *widest* value (LAST, plus any decimal part of INCREMENT):

```
$ seq -w 8 12
08
09
10
11
12
$ seq -w 0 0.1 0.3      # decimals of INCREMENT count too
0.0
0.1
0.2
0.3
$ seq -w -2 2           # sign counts toward width
-2
-1
00
01
02
```

`-w` and `-f` are mutually exclusive:

```
$ seq -w -f '%05.1f' 1 2
seq: format string may not be specified when printing equal width strings
```

### -f: printf-style float format

`-f FORMAT` applies a `printf` format to each number. The catch from the float internals: the format must suit a `double` — exactly one of `%f`, `%e`, `%g` (with flags/width/precision). `%d` is rejected, even for integer sequences:

```
$ seq -f '%d' 1 3
seq: format '%d' has unknown %d directive
$ echo $?
1
$ seq -f '%04.0f' 1 3   # zero-pad via float directives
0001
0002
0003
$ seq -f 'worker%02g' 1 3
worker01
worker02
worker03
```

When you *can* use `%d`-style padding on pure integers, `-w` is the simpler choice; when you need prefixes, decimals, or scientific output, `-f` is the only tool.

### -s: the separator

`-s STRING` replaces the default newline separator. The string may be empty or multi-character; the final number is still followed by one newline:

```
$ seq -s, 1 5 | od -c | head -1
0000000   1   ,   2   ,   3   ,   4   ,   5  \n
$ seq -s ' -> ' 1 3
1 -> 2 -> 3
$ seq -s '' 1 5         # concatenate digits
12345
```

### Floating-point behavior and endpoints

GNU `seq` compensates for binary-float rounding when stepping through decimals, so expected endpoints appear:

```
$ seq 0 0.1 0.3 | tail -1
0.3                     # included, not 0.30000000000000004 or 0.2999...
$ seq 1 0.1 1.1 | tail -1
1.1
```

Compare with the naive awk loop `awk 'BEGIN{for(i=0;i<=0.3;i+=0.1)print i}'`, where accumulated `0.1+0.1+0.1` compares unequal to `0.3` and the endpoint is skipped. `seq` is the safer decimal stepper — but it is still binary arithmetic underneath, so don't use it for money; use integers of cents.

## Options That Matter

| Option | Effect |
|---|---|
| `-f, --format=FORMAT` | printf-style format for each number; must fit a `double` (`%f`/`%e`/`%g` family); mutually exclusive with `-w` |
| `-s, --separator=STRING` | string printed between numbers (default `\n`); may be empty or multi-char |
| `-w, --equal-width` | zero-pad all numbers to the width of the widest; ignored if `-f` is used (error) |
| `--help`, `--version` | usage / version (GNU extensions, harmless) |

That is the entire flag set — `seq` has no input files, no recursion, no filtering. Its complexity lives in the three-argument numeric grammar, not in options.

## Usage Patterns

```bash
# Classic C-style shell loop (word-split output, safe for pure digits)
for i in $(seq 1 5); do echo "pass $i"; done
```

```bash
# Zero-padded batch directories: dir01 .. dir12
seq -w 1 12 | xargs -I{} mkdir dir{}
```

```bash
# Prefix + padding via format (no -w allowed with -f)
seq -f 'node-%02g' 1 8
```

```bash
# Generate quick test data: 1000 lines of fixed size
seq 1 1000 | awk '{print $0, "padding..."}' > test.txt
```

```bash
# Repeat a string N times (seq as a pure counter)
seq 5 | xargs -I{} printf 'chunk'
```

```bash
# Unbounded loop replacement (seq 0 inf never ends; kill with Ctrl-C)
seq 0 inf | while read -r n; do do_work "$n"; done
```

```bash
# Comma-separated argument list for a command
./render --frames "$(seq -s, 1 5)"
```

```bash
# Countdown with a negative step
seq 10 -1 1 | while read -r n; do echo "$n..."; sleep 1; done
```

```bash
# Zip two sequences into columns with paste
paste <(seq 1 3) <(seq 10 3 18)
```

```bash
# Enforce an iteration budget in a script that polls a service
for attempt in $(seq 1 30); do curl -fsS "$URL" && break; sleep 1; done
```

## Nuances and Gotchas

- **The two-argument form is FIRST LAST, not FIRST STEP LAST.** `seq .1 .2` does *not* step by 0.1 — increment defaults to 1, so it prints only `0.1`. This is the single most common `seq` bug; the three-argument form `seq 0.1 0.1 0.2` is what people meant.
- **Wrong-direction ranges exit 0 with no output.** `seq 10 1` prints nothing and succeeds. Combined with `for i in $(seq 10 1)`, a loop body silently never runs. Counting down needs the explicit negative increment, and if your bounds come from variables, a swapped pair fails silently — assert `first <= last` before looping when the order is data-driven.
- **`%d` is invalid in `-f`.** Because numbers are doubles internally, `seq -f '%03d' 1 5` aborts with "unknown %d directive" (exit 1). Use `%03.0f` or drop `-f` and use `-w`.
- **`-w` and `-f` are mutually exclusive** — "format string may not be specified when printing equal width strings". Do padding inside the format (`%04.0f`) or with `-w`, never both.
- **`-w` pads to the width of LAST, which changes if bounds are variables.** `seq -w 1 "$n"` gives 3-digit output only when `n` is three digits; hardcoded-width expectations (`sprintf`-style `001`) need `-f '%03.0f'`.
- **Not POSIX.** `seq` is absent from POSIX.1-2018; a strict `#!/bin/sh` under `dash` still has it on Debian (it's a separate binary, not a builtin), but minimal containers (Alpine + busybox `seq`) and some proprietary Unices may lack it or lack `-f`. BusyBox `seq` supports `-w`/`-s` but historically not `-f`. For maximal portability use `awk 'BEGIN{for(...)}'`.
- **Don't capture huge sequences into shell variables.** `files=$(seq 1 1000000)` builds a million-word string, then expands it through the shell's argv. `seq 1 1000000 | xargs -n1 ...` streams in constant memory. Brace expansion `{1..1000000}` has the same argv blow-up, earlier — at expansion time.
- **Locale and the decimal point.** Input and output use `.` as the decimal point regardless of locale (coreutils numeric parsing is locale-independent). Scripts parsing `seq` output needn't worry about comma-decimal locales — but the same is *not* true of all tools around it.
- **Empty-sequence semantics vs `perror` reflexes.** Scripts that treat "no output" as failure (e.g. feeding `seq` into `mapfile` and testing `$?`) get exit 0 from `seq 10 1`; the failure is semantic, not signaled. Exit 1 appears only for parse errors, zero increment, bad format, or write errors (disk full on a huge `-s`-joined line, for instance).

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Sequence printed, including the empty sequence (e.g. `seq 10 1`) |
| 1 | Invalid argument (non-numeric, NaN, zero increment), invalid `-f` format, `-w` with `-f`, or a write error |

## Related Commands

- [`overview`](./overview.md) — GNU Coreutils collection hub.
- [`numfmt`](./numfmt.md) — the inverse direction: format raw byte/number output for humans.
- [`factor`](./factor.md) — the other coreutils number tool: prime factorization.
- [`printf`](./printf.md) — where `-f`-style formatting normally lives; the `%.0s` repeat trick.
- [`paste`](./paste.md) — merges `seq` streams side-by-side (see the zip example).
- [`head`](./head.md) — bounds an infinite `seq 0 inf` stream.
- [Bash](../../shell/bash.md) — brace expansion `{a..b}` vs `seq`: when the shell expands and when a process does.

## Interview Questions

### Q: What does `seq 10 1` print, and what does that tell you about the argument grammar?

Nothing, with exit status 0. Two arguments mean FIRST and LAST; with no INCREMENT the default is 1 even when LAST < FIRST, so the range is empty by the stop rule. Counting down requires the explicit negative increment `seq 10 -1 1`. The deeper point: `seq` has no sign intuition — the increment's sign, not the bounds' order, decides direction, and an empty sequence is a success, not an error.

### Q: Why does `seq -f '%03d' 1 5` fail, and what are the two correct fixes?

`seq` computes with `long double` internally and feeds each number to `printf` as a double, so the format must be a float-family directive; `%d` is rejected at startup with exit 1. Fix 1: use a float directive with zero decimals, `-f '%03.0f'`. Fix 2: skip `-f` and use `-w`, which zero-pads to the width of the largest number. The failure mode is friendly (immediate, loud), but scripts that embed the format from configuration hit it at runtime, not at review time.

### Q: Compare `for i in $(seq 1 1000000)`, `{1..1000000}`, and `seq 1 1000000 | xargs -n1 ...` for a million iterations.

The first two both materialize a million words in shell memory (and, when passed to a command, through argv) — `{1..1000000}` does it even before a command exists, purely at expansion time; both risk "argument list too long" and sluggish startup. The `seq | xargs` form streams: constant memory, chunked invocation, works in POSIX `sh` where brace expansion doesn't exist. For pure in-shell counting, a `while` loop with an arithmetic counter avoids the word list entirely; `seq` pipelines win when the numbers feed downstream tools.

### Q: A script loops with `for i in $(seq "$a" "$b")` and the body sometimes never executes. Diagnose.

Two-argument form means FIRST and LAST with INCREMENT defaulting to 1 — so whenever `b < a`, the sequence is empty and `seq` exits 0. Typical trigger: `b` is derived from a file size or count that came back 0. Fixes: pass an explicit increment (`seq "$a" 1 "$b"` doesn't help — that's three-arg with INCREMENT=1, same empty result; the real fix is validating `a <= b`), invert bounds for the down case (`seq "$a" -1 "$b"` when `a > b`), or restructure with a `while [ "$i" -le "$b" ]` arithmetic loop where the guard is visible. The interview point is that silent empty success is the failure signature to recognize.

### Q: Why is `seq` absent from POSIX, and what do you use instead in a strictly portable script?

`seq` was a GNU addition that predates standardization efforts and never entered the spec, unlike its `coreutils` peers `wc`, `tee`, and `uniq`. In portable `sh` you use either a `while` loop with `i=$((i+1))` arithmetic (works everywhere, clunky for floats), or `awk 'BEGIN { for (i = 1; i <= N; i++) print i }'` — which also handles floats, padding via `printf`, and arbitrary stepping in one process. The trade-off to articulate: `seq` is one short subprocess with streaming semantics; the awk equivalent is equally portable and more expressive but embeds a language snippet in your shell.

### Q: How does `seq 0 0.1 0.3` reliably include the 0.3 endpoint when naive floating-point loops don't?

GNU `seq` steps in `long double` and compensates the accumulated rounding against the LAST bound, so the final value is emitted rather than skipped by a `0.1+0.1+0.1 != 0.3` comparison — the same trap that makes `awk 'BEGIN{for(i=0;i<=0.3;i+=0.1)}'` print only up to 0.2. The general lesson (interviewers want this): never trust accumulated floating-point iteration counts; either step by integers and scale once (`seq 0 3 | awk '{printf "%.1f\n", $1/10}'`), or use tools that anchor the endpoint, and treat decimal loops in binary floats as off-by-one-prone by default.

## References

- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/seq.1.en.html)
