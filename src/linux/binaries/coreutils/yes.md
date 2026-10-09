# yes — output a string repeatedly until killed

## Overview

`yes` prints a string forever: by default the letter `y` on its own line,
or all of its arguments joined by spaces when given any. It never stops on
its own — it runs until its reader goes away (SIGPIPE), it is killed, or
it hits a write error. The tool exists for one purpose: feeding automated
answers into commands that ask interactive questions.

It ships in the Debian `coreutils` package at `/usr/bin/yes`, dates to
Unix v7, and is not POSIX-standardized (its behaviour is too trivial and
too dependent on pipeline conventions to standardize usefully). It is a
rare command whose man page is three lines long yet whose folklore —
output-speed benchmarks, SIGPIPE semantics, prompt-automation hazards —
fills interviews.

Modern package managers have grown `-y`/`--yes` flags that largely
superseded `yes |`, but the pattern still applies to older or third-party
installers, license prompts, and any program that reads stdin line by line.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/yes` |
| First appeared / lineage | Unix v7 (1979); in GNU coreutils |
| Standards | none — not in POSIX |

## Synopsis

```text
yes [STRING]...
```

```bash
yes                    # prints "y\n" forever
yes n                  # prints "n\n" forever — decline prompts
yes /dev/sda1          # answer multiple-choice prompts with a fixed line
yes "$(hostname)" | head -5
```

## How It Works

The program is a tight loop: build the output line once (arguments joined
with spaces, or `y`), then `write` it to stdout as fast as the consumer
allows. Two kernel behaviours shape everything about `yes`:

```text
                 ┌──────────────┐   full pipe buffer    ┌───────────┐
   yes  ──────▶  │ kernel pipe  │  ───────────────────▶ │ consumer  │
 (write loop)    │ (64 KiB)     │   consumer reads,     └───────────┘
                 └──────────────┘   buffer refills
   consumer exits ──▶ next write fails EPIPE ──▶ kernel sends SIGPIPE ──▶ yes dies
```

First, **pipe backpressure**: if the consumer reads slowly or not at all,
the 64 KiB pipe buffer fills and `yes` blocks inside `write` — idle at ~0%
CPU, not spinning. Second, **SIGPIPE as designed termination**: when the
consumer exits, the next write fails with `EPIPE` and the kernel delivers
`SIGPIPE`, whose default action kills the process. Dying silently by
SIGPIPE is not a bug in `yes`; it is the mechanism every Unix pipe consumer
relies on.

```bash
$ yes | head -3
y
y
y
$ yes | head -1 > /dev/null; echo "${PIPESTATUS[0]}"   # bash: inspect producer status
141
```

Exit status 141 is `128 + 13` (`SIGPIPE`), and in normal pipelines it is
invisible because the shell reports the *last* command's status (`head`'s
0). `set -o pipefail` exposes it — a detail that explains mysterious
pipeline failures in scripts with pipefail enabled.

Because the loop is so small, `yes` became the traditional
write-throughput benchmark. Recent GNU coreutils generations rewrote the
output path (bigger buffer, vectorized copying), and on modern hardware
`yes > /dev/null` saturates memory bandwidth at rates measured in gigabytes
per second — a folk benchmark, not a meaningful storage metric, since
`/dev/null` discards everything and nothing touches disk.

## Options That Matter

| Option | Effect |
|---|---|
| (no options) | `yes` has no operational flags; any arguments become the repeated string |
| `STRING...` | Multiple arguments are printed joined by single spaces, newline after each line |

`yes --help` works normally (it is not `true`); the tool's surface is its
operand list. An empty string argument (`yes ''`) prints empty lines
forever — occasionally useful as a heartbeat generator for test pipelines.

## Usage Patterns

```bash
# Auto-answer an installer that prompts y/n (legacy packages without -y)
yes | ./vendor-install.sh
```

```bash
# Auto-decline: answer every prompt with 'n' (safe dry-run probe)
yes n | dpkg --configure -a --force-confold 2>&1 | head
```

```bash
# Answer a specific fixed line, e.g. accepting a serial number prompt
yes /dev/sdb | ./legacy-restore-tool
```

```bash
# Generate test data: 10 MiB of 'A' without touching /dev/zero
yes A | head -c 10M > sample.txt
```

```bash
# Heartbeat lines for a parser test harness
yes '2026-07-01 INFO ok' | head -n 100000 | wc -l
```

```bash
# Benchmark write throughput (folklore: GB/s on modern hardware)
time yes > /dev/null
```

```bash
# Demonstrate backpressure: yes is blocked, not spinning, once the pipe fills
yes | (sleep 2; cat) & sleep 0.3; ps -o stat= -C yes   # state T/t or S when blocked
```

```bash
# Feed a fixed-size stdin to a program that expects input
yes | timeout 5 ./menu-driven-tool
```

## Nuances and Gotchas

- **`set -o pipefail` makes `yes |` pipelines report 141.** The producer
  *always* dies by SIGPIPE in a well-formed pipeline; pipefail simply makes
  the shell admit it. Condition on the *consumer's* status, or tolerate 141
  explicitly, rather than "fixing" yes.
- **The yes-side CPU myth.** With a live consumer, `yes` is I/O-bound: it
  blocks when the pipe is full. CPU spikes happen only when the consumer
  reads continuously (a `while read` loop) — the cost is the consumer's,
  not yes's.
- **Prompt automation is fragile.** `yes` answers *every* question
  identically; installers that ask "erase this disk? [y/N]" after "continue?
  [y/N]" cannot be trusted to a blanket `yes`. Prefer the program's own
  non-interactive flags (`-y`, `DEBIAN_FRONTEND=noninteractive`) whenever
  they exist.
- **Locale and argument joining.** Arguments are joined with single
  spaces; a multi-word answer like `yes continue anyway` prints
  `continue anyway`, which may or may not match what the program expects
  — test the exact prompt line before automating it.
- **It never exits on its own.** Forgotten `yes` background jobs block on a
  full pipe forever; `timeout 10 yes | ...` bounds them (the consumer then
  sees EOF/SIGPIPE per its own handling).
- **SIGPIPE inheritance quirks**: a child that ignores or blocks SIGPIPE
  (some daemons) turns `EPIPE` into a visible error instead of death —
  irrelevant for yes itself but the reason `yes | daemon` can produce
  error spam.

## Exit Status

| Status | Meaning |
|---|---|
| 141 (128+13) | Killed by SIGPIPE — the normal end of every `yes |` pipeline |
| 0 | Only if stdout closed cleanly without SIGPIPE (rare) |
| 125/126/127-style statuses do not apply; write errors produce a diagnostic and nonzero status |

The exit status is almost never observed because the shell reports the last
pipeline member; check `${PIPESTATUS[0]}` (bash) to see it.

## Related Commands

- [`timeout`](./timeout.md) — bounds unbounded producers like yes.
- [`true`](./true.md) — the other zero-work coreutils utility: exit 0 once vs lines forever.
- [`stdbuf`](./stdbuf.md) — pipe buffering mechanics that govern how fast the consumer sees yes's output.
- [coreutils collection](./overview.md) — sibling GNU coreutils pages.

## Interview Questions

### Q: Why does `yes | head -3` terminate cleanly instead of running forever, and what is yes's exit status?

`head` reads three lines and exits. The next `write` from yes fails with
EPIPE because the read end is closed, and the kernel delivers SIGPIPE,
whose default disposition terminates the process — status 141 (128+13).
The pipeline's reported status is `head`'s 0 because shells report the last
member; `PIPESTATUS[0]` under pipefail would reveal the 141. This
SIGPIPE-on-consumer-exit contract is the designed termination path for all
pipe producers.

### Q: Does `yes | slow-consumer` burn CPU? Explain the pipe mechanics.

No — once the kernel's 64 KiB pipe buffer fills, `yes` blocks inside
`write(2)` and sleeps until the consumer drains data; it consumes ~0% CPU
while blocked. CPU usage only becomes visible with a consumer that reads
continuously, and then the relevant cost is in the consumer's syscall
handling. The backpressure blocking, not busy looping, is why a forgotten
background `yes` is harmless.

### Q: Why did coreutils spend effort making `yes` fast, and why is the benchmark misleading?

`yes` is the minimal write-loop, so it became the folk benchmark for
write(2) throughput, and recent coreutils generations optimized its buffer
handling (gigabytes per second on modern hardware). The number measures
memory-copy and syscall costs to `/dev/null` — no disk, no consumer
parsing — so it says nothing about real pipeline or storage performance.
It is a kernel/libc microbenchmark wearing a command's clothes.

### Q: What are the risks of `yes | apt-get install ...`-style automation?

A blanket answer cannot distinguish harmless confirmations from
destructive ones — the same `y` that accepts a package accepts an "erase
this partition?" prompt later. Non-interactive installs should use the
program's own contract (`-y`, environment switches like
`DEBIAN_FRONTEND=noninteractive`, config-file answers with
`--force-confold`), reserving `yes |` for tools that genuinely lack one —
and then only after auditing every question the tool can ask.

### Q: How would you generate exactly 10 MiB of test data with yes, and why use it over /dev/zero?

`yes A | head -c 10M > sample.txt`. `/dev/zero` produces NUL bytes, which
compress perfectly and can hide parser bugs; `yes` produces real newline-
delimited, patterned text that exercises line-oriented consumers and
compresses realistically. The combination of an unbounded producer and a
bounded consumer (`head -c`) is the general idiom for synthetic test data
streams.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/yes.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
