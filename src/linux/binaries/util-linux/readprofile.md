# readprofile — read kernel profiling counters from /proc/profile

## Overview

`readprofile` reads the kernel's timer-tick function profiler: a kernel booted with `profile=N` (and built with profiling support) accumulates one counter per small chunk of kernel text in `/proc/profile`; `readprofile` maps those counters back to symbols using `System.map` and prints a hottest-functions report. It ships in the `util-linux` package at `/usr/sbin/readprofile`.

Honest framing for modern readers: this is the *pre-perf* kernel profiler. On contemporary kernels you would use `perf record`/`perf report` (PMU-based, userspace-inclusive, KASLR-aware), ftrace, or `/proc/kallsyms`-based tooling; distro kernels rarely boot with `profile=` and the mechanism survives mainly in legacy, embedded, and exam contexts. Understanding it is still a good interview exercise in how kernel sampling works: a timer interrupt records the EIP, counters are per-address-range, and symbolization is a userspace job.

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/readprofile |
| First appeared | Linux 2.4 era (early 2000s) |
| Standards | Linux-specific (`/proc/profile`); not POSIX |

## Synopsis

```
readprofile [options]
```

Main one-line forms:

```
readprofile -i                     # sanity check: sampling step and buffer info
readprofile | sort -rn | head      # hottest kernel functions
readprofile -m /boot/System.map-$(uname -r) -v   # explicit map, verbose columns
sudo readprofile -r                # reset all counters
```

## How It Works

### The kernel side

Booting with `profile=N` allocates a counter array over kernel text: one counter per 2^N bytes (`profile=2` → a counter per 4 bytes, the traditional choice). On each timer tick the kernel increments the counter covering the interrupted EIP if it lands in kernel text. The array is exported as `/proc/profile`, a flat array of native-long counters.

```
kernel text:  |func A ............|func B ....|func C ....|
counters:     [  ][  ][  ][  ][  ] [  ][  ][  ] [  ][  ][  ]
                     ▲ tick lands here → counter[addr >> N]++
```

Older (2.2/2.4-era) kernels additionally required the kernel itself to be compiled with `-pg`/mcount instrumentation for function-granular profiling; the boot-parameter tick sampler is the shape that survived. If `/proc/profile` does not exist, the kernel was built without profiling support or not booted with `profile=` — there is nothing for the tool to read (verified locally: a stock container kernel has no `/proc/profile`).

### From counter to symbol, precisely

The kernel-side pieces have names: `profile=` is parsed by `profile_setup()`, which sets `prof_shift`; the buffer `prof_buffer` is allocated with `prof_len = (_etext - _stext) >> prof_shift` entries covering kernel text, bounded by the linker symbols `_stext`/`_etext`. On each timer tick, `profile_tick(CPU_PROFILING)` → `profile_hit()` increments `prof_buffer[(pc - _stext) >> prof_shift]` when the interrupted PC lands in kernel text. `/proc/profile` is that array read out as native words; writing to it (what `-r` does) zeroes the counters. Nothing in the kernel knows symbols at tick time — one increment per tick, no locks beyond that — which is why the design was cheap enough to leave enabled, and why all symbolization was deferred to userspace with System.map.

### The userspace side

`readprofile` slurps `/proc/profile`, reads a symbol map (`/boot/System.map` or `/boot/System.map-$(uname -r)` by default, `-m` to override), aggregates counters per symbol range, and prints:

```
boot (profile=N)                runtime                       userspace
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│ prof_buffer[prof_len]│   │ timer tick → PC      │   │ readprofile          │
│ one word per 2^N B   │←─│ prof_buffer[i]++     │←─│ /proc/profile + map  │
│ of kernel text       │   │ (kernel text only)   │   │ → per-symbol report  │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
        exported as /proc/profile (array of native words; write = reset)
```

The mapping step is address-range containment: readprofile loads System.map into a symbol table and assigns each counter bucket to the symbol whose `[start, next_start)` range contains it; buckets outside any known range still sum into the total but go unattributed. That is why map version-matching is existential — symbols move between kernel builds, and a mismatched map does not fail loudly, it silently attributes ticks to the wrong neighbors.

```
  <total ticks> total                                ← summary line

 ticks    symbol            address        (default order: symbol address)
 ...
```

`-v` reorganizes into a verbose table (raw address, percentage per symbol), `-a` prints symbols with zero counts too, `-b` prints per-bin counts instead of symbol sums, `-s` prints individual counters *within* a function, and `-i` reports the sampling step and buffer dimensions without needing a map. The map must correspond to the running kernel; `-n` disables the tool's byte-order auto-detection for cross-endian (embedded) map files.

### Reset and calibration

`-r` zeroes all counters (root) — the standard pattern is reset → run workload → read. On 2.4-era kernels `-M <mult>` calibrated the sampling multiplier (written back into `/proc/profile`) when the timer tick rate made counts misleading; it is meaningless on modern kernels.

### The profile= arithmetic

The knob's cost is easy to compute. For a kernel with ~20 MiB of text:

```
profile=2 → one counter per 4 B  → 5,242,880 counters × 8 B ≈ 40 MiB RAM
profile=4 → one counter per 16 B → 1,310,720 counters × 8 B ≈ 10 MiB RAM
profile=8 → one counter per 256 B → coarse, but cheap
```

Counters are native words, and the tradeoff is direct: smaller steps isolate functions, larger steps bucket neighbors together (a bucket can straddle two symbols, and readprofile then attributes the whole bucket to the earlier one). The tool's `-b`/`-s` modes let you inspect buckets rather than symbol sums, which is how you notice that straddling.

### Snapshots and diffing

`-p` reads any saved buffer copy, so the workflow is snapshot-based: copy `/proc/profile` before and after a workload, symbolize both, and diff per symbol. Because the buffer layout depends only on the kernel text layout and `prof_shift`, snapshots from one boot compare cleanly — a before/after profiler that predates perf by a decade.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-m`, `--mapfile <file>` | Symbol map (defaults: `/boot/System.map`, `/boot/System.map-$(uname -r)`) |
| `-p`, `--profile <file>` | Counter file (default `/proc/profile`) |
| `-i`, `--info` | Print sampling step/buffer info and exit |
| `-v`, `--verbose` | Verbose table: addresses and percentages |
| `-a`, `--all` | Include symbols with zero counts |
| `-b`, `--histbin` | Individual histogram-bin counts |
| `-s`, `--counters` | Individual counters within each function |
| `-r`, `--reset` | Zero all counters (root only) |
| `-M`, `--multiplier <n>` | 2.4-era sampling-rate calibration |
| `-n`, `--no-auto` | Disable byte-order auto-detection of the map file |

## Usage Patterns

```bash
# 1. Boot with profiling (grub edit or kernel cmdline): profile=2
#    then verify the interface came up
sudo readprofile -i
```

```bash
# 2. Reset, reproduce the problem, read the top offenders
sudo readprofile -r
./reproduce_load.sh
sudo readprofile -v | sort -rn | head -20
```

```bash
# 3. Explicit map for the running kernel (multi-kernel /boot)
sudo readprofile -m /boot/System.map-$(uname -r)
```

```bash
# 4. See every symbol, even untouched ones (coverage-style view)
sudo readprofile -a -v
```

```bash
# 5. Fine-grained: where inside the function do ticks land?
sudo readprofile -s
```

```bash
# 6. Dump counters from a saved kernel for offline analysis
sudo cp /proc/profile /tmp/prof.snap
readprofile -p /tmp/prof.snap -m /boot/System.map-$(uname -r)
```

```bash
# 7. Cross-endian embedded map on an x86 host
readprofile -m vmlinux.map.arm -n
```

```bash
# 8. Before/after comparison of a suspected regression (same boot, same map)
sudo cp /proc/profile /tmp/prof.before
./workload.sh
sudo cp /proc/profile /tmp/prof.after
sudo readprofile -p /tmp/prof.before -m /boot/System.map-$(uname -r) | sort > /tmp/pb
diff /tmp/pb <(sudo readprofile -p /tmp/prof.after | sort) | sort -k1 -rn | head
```

```bash
# 9. Coverage view: which symbols never recorded a tick?
sudo readprofile -a | awk '$1 == 0 {print $2}'
```

```bash
# 10. Reset before each measurement run in a benchmark harness
sudo readprofile -r && ./bench.sh && sudo readprofile -v | sort -rn | head -5
```

```bash
# 11. Confirm the environment first: step size, buffer dims, cmdline flag
sudo readprofile -i; grep -o 'profile=[0-9]*' /proc/cmdline
```

```bash
# 12. Where inside a function do the ticks land? (per-counter detail)
sudo readprofile -s | head -20
```

```bash
# 13. Read counters from a snapshot with the byte-order detection off
readprofile -p /tmp/prof.snap -n | sort -rn | head
```

## Nuances and Gotchas

- **KASLR kills the map.** Modern kernels randomize text addresses at boot; a static `/boot/System.map` no longer matches `/proc/profile` addresses. `/proc/kallsyms` (root) reflects the runtime layout — one of the concrete reasons `perf` replaced readprofile.
- **Sampling bias.** Ticks land only where the CPU was at interrupt time: short functions are undercounted, idle time is not attributed to code, and userspace time does not appear at all. It answers "where does *kernel* time go", coarsely.
- **Needs the right kernel.** `/proc/profile` missing means profiling support was not compiled in or `profile=` was not passed; there is no error recovery — check with `readprofile -i` and `grep profile= /proc/cmdline`.
- **Permissions.** `/proc/profile` is root-readable; everything meaningful (including `-r`) needs root.
- **Counter granularity trade-off.** `profile=2` costs a counter per 4 bytes of text (several MB of RAM on large kernels); larger N shrinks memory but buckets neighboring functions together.
- **No call graphs.** Flat PC sampling only — no stacks, no callers. That gap is exactly what `perf record -g` and ftrace fill.
- **Byte order auto-detection** (`-n` to disable) exists because people profiled cross-built kernels; on native systems the default is fine and `-n` is only for exotic cross-reading.
- **Modules are invisible.** The counter array spans only core kernel text (`_stext`..`_etext`); time spent in loadable modules (drivers, filesystems) never increments a bucket. A workload dominated by a module shows almost nothing — a classic misreading that perf (which covers modules) fixed.
- **One array, all CPUs.** SMP ticks from every CPU increment the same buffer; there is no per-CPU or per-task view, and interrupt time is folded into whatever PC was interrupted. Aggregate-only results are inherent, not a tool bug.
- **Counts are ticks, not seconds.** A bucket value is "timer ticks observed here"; at HZ=100 on four CPUs, the whole buffer gains at most ~400 per second. Convert to time only as rough magnitude — or switch to perf, which reports real event counts.
- **`profile=` is boot-time only.** There is no sysfs toggle; enabling it means editing the bootloader configuration and rebooting. In emergency triage on production boxes, that reboot cost is exactly why people reach for perf/eBPF instead.
- **The map must match *this boot*.** Rebuilding or installing a kernel package changes System.map; keeping old maps around means the wrong one can be picked up silently. `-m /boot/System.map-$(uname -r)` is the defensive spelling.

## Exit Status

The man page documents no dedicated exit-code table; conventionally:

| Code | Meaning |
| --- | --- |
| 0 | Report printed / reset done |
| 1 | Error: `/proc/profile` missing, unreadable map, permissions, usage error |

## Related Commands

- [`overview`](./overview.md) — hub page of the util-linux collection.
- [`internals`](../../internals.md) — timer interrupts, kernel text layout, and symbolization context.
- [`process-management`](../../admin/process-management.md) — where per-process time accounting (utime/stime) ends and kernel-wide sampling begins.

## Interview Questions

### Q: How did kernel function profiling work before perf, end to end?

Boot with `profile=N`: the kernel allocates one counter per 2^N bytes of kernel text and increments the counter covering the interrupted EIP on each timer tick, exporting the array as `/proc/profile`. `readprofile` reads that array, maps address ranges to symbols via a version-matched `System.map`, and aggregates per function. It was flat PC sampling of kernel text only — no stacks, no userspace, timer-biased — which is precisely the feature list perf (PMU events, call graphs, dwarf/unwind, userspace) was built to replace.

### Q: Why does readprofile break on modern kernels, and what replaces each broken piece?

Two structural breaks: KASLR randomizes kernel text per boot, so static `System.map` addresses no longer match `/proc/profile` counters (`/proc/kallsyms` shows the runtime addresses); and distro kernels stopped booting with `profile=` since the data rate and bias are poor. `perf record`/`perf report` handle both: PMU-based sampling with runtime symbolization, call graphs, and userspace coverage. For pure kernel questions today: `perf`, ftrace/`trace-cmd`, or bpftrace.

### Q: What are the statistical pitfalls of tick-based profiling?

Sampling only observes the instruction pointer at timer interrupts, so it measures where time *accumulates* in long-running loops and systematically undercounts short hot functions that finish between ticks; idle CPUs attribute nothing; SMP merges all CPUs into one array; and interrupts inflate the tick count of the interrupted context. Modern mitigations (higher-frequency PMU sampling, on-CPU perf events, per-CPU buffers) exist precisely because of these biases — a good answer names undercounting, idle blindness, and granularity.

### Q: You find /proc/profile missing on a production box. What are your hypotheses?

The kernel was built without profiling support, or without `profile=` on the command line (check `/proc/cmdline`), or you are in a container/namespace where the host kernel simply never enabled it — `/proc/profile` is global kernel state, not per-namespace. In practice: this kernel was never intended for readprofile; use perf/ftrace if profiling is the goal, or boot the box once with `profile=2` for a legacy-format capture.

### Q: Why was the profiling data a flat array in /proc/profile rather than per-symbol counters?

Tick-time cost and dependency ordering. A flat array makes the per-tick work a single increment — no symbol table in the kernel, no allocation proportional to symbol count, no need for the symbol subsystem to exist before profiling starts. Reading `/proc/profile` as raw memory also made the data trivially scriptable and snapshot-comparable. The design defers all expensive work (symbolization, aggregation) to userspace — the same division perf keeps, with a much richer data plane (per-CPU ring buffers, PMU events) instead of one shared array.

### Q: Compare readprofile's sampling model with perf's at the mechanism level.

Both sample PCs, and almost everything else differs. Sampling source: fixed-rate timer tick vs programmable PMU overflow interrupts (any event, not just time). Storage: one shared array indexed by address vs per-CPU ring buffers with timestamps and callchains. Context: kernel text only vs kernel/user/both, with mmap-aware symbolization. Bias: timer ticks cluster in long loops and sleep time vanishes vs event-based sampling with configurable frequency. That list is essentially the justification for perf's existence — a strong interview answer names at least three of the contrasts.

### Q: How would you answer "which kernel functions dominate my workload" on a modern distro kernel?

`perf record -e cycles:k -a -- sleep 30` then `perf report --sort=symbol` reproduces readprofile's question with runtime kallsyms symbolization (KASLR-proof) and per-symbol/per-line views; add `-g` for call graphs, which readprofile never had. For targeted questions, ftrace function-graph traces a specific function and bpftrace one-liners count hits on named symbols. Mentioning readprofile's specific failure modes — KASLR map mismatch, module blindness, timer bias — is how you justify the replacement rather than assert it.

### Q: What does readprofile -i tell you, and when is it the first command to run?

It reads only the interface metadata — the sampling step (`1 << prof_shift`) and buffer dimensions — without needing a symbol map. As a first command it answers the two most common setup questions in one shot: does `/proc/profile` exist at all (profiling enabled), and at what granularity. Pair it with `grep profile= /proc/cmdline` to separate "kernel lacks support" from "booted without the parameter" — the distinction decides whether a reboot can fix your missing profiler.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/readprofile.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
