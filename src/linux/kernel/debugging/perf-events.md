# Linux perf Events — Performance Monitoring Interface

## Introduction

The `perf_event_open(2)` system call, merged in Linux 2.6.31
(September 2009) by Ingo Molnar and Thomas Gleixner, exposes the
kernel's performance monitoring counter (PMC) infrastructure to user
space. The same syscall serves performance counters (cycles,
instructions, cache misses), software counters (page faults,
context switches, sched migrations), kernel tracepoints, kprobes,
uprobes, and breakpoint events. The `perf(1)` command-line tool —
packaged in `tools/perf/` in the kernel tree — is the user-facing
frontend.

The unifying abstraction is the **event**: a counter you can read or
a stream of records you can sample from. Events can be per-thread,
per-CPU, or system-wide. They can be counted (just totals) or
sampled (records every N occurrences with a stack trace). Either
path opens the same fd and uses the same `mmap`d ring buffer for
sample delivery.

> **Man page:** perf_event_open(2) —
> <https://man7.org/linux/man-pages/man2/perf_event_open.2.html>
> **`perf(1)` man page:** <https://man7.org/linux/man-pages/man1/perf.1.html>
> **Wiki:** <https://perf.wiki.kernel.org/>
> **Kernel docs:** `tools/perf/Documentation/`,
> `Documentation/admin-guide/perf-security.rst`

## The perf_event_open() Syscall

The signature:

```c
#include <linux/perf_event.h>
#include <sys/syscall.h>
#include <unistd.h>

long perf_event_open(struct perf_event_attr *attr,
                     pid_t pid, int cpu, int group_fd,
                     unsigned long flags);
```

- `attr` describes *what* to measure.
- `pid` selects the target: `-1` for any process on this CPU,
  `0` for the calling process, a specific `pid` for that one.
- `cpu` selects the CPU: `-1` for "follow the process wherever it
  runs"; an integer for "this CPU only".
- `group_fd` lets you schedule events together so they are read
  atomically.
- `flags` includes `PERF_FLAG_FD_CLOEXEC`,
  `PERF_FLAG_PID_CGROUP`, etc.

The returned `fd` is the event. Reading 8 bytes from it returns the
current count. For sampling, `mmap` the fd and read events out of the
ring buffer.

The `perf_event_attr` struct (heavily abridged):

```c
struct perf_event_attr {
    __u32 type;            /* PERF_TYPE_HARDWARE, etc.       */
    __u32 size;
    __u64 config;          /* which counter inside `type`    */
    __u64 sample_period;   /* N:  interrupt every N events   */
    __u64 sample_type;     /* bitmask: what to record        */
    __u64 read_format;     /* how read() output is formatted */
    __u64 disabled:1,      /* start disabled                 */
          inherit:1,       /* children inherit               */
          pinned:1,        /* must be on this PMU             */
          exclusive:1,
          exclude_user:1,  /* count only kernel              */
          exclude_kernel:1,/* count only user                */
          exclude_hv:1,
          precise_ip:2,    /* 0=slack, 2=PEBS-required       */
           /* ... */;
};
```

## Event Types and the Catalog

The `type` field picks the source. Common values:

```
PERF_TYPE_HARDWARE    0   config = PERF_COUNT_HW_*
PERF_TYPE_SOFTWARE    1   config = PERF_COUNT_SW_*
PERF_TYPE_TRACEPOINT  2   config = tracepoint ID from /sys/kernel/tracing
PERF_TYPE_HW_CACHE    3   config encodes cache/op/result
PERF_TYPE_RAW         4   config = model-specific PMC code
PERF_TYPE_BREAKPOINT  5   config = 0; ptr in bp_addr field
PERF_TYPE_RAW (per-PMU)   config via /sys/bus/event_source/devices/<pmu>/
```

Hardware counters (a subset):

```
PERF_COUNT_HW_CPU_CYCLES        cycles           (tick of CPU clock)
PERF_COUNT_HW_INSTRUCTIONS      instructions     (retired inst.)
PERF_COUNT_HW_CACHE_REFERENCES  cache-references (any level)
PERF_COUNT_HW_CACHE_MISSES      cache-misses
PERF_COUNT_HW_BRANCH_INSTRUCTIONS branch-instructions
PERF_COUNT_HW_BRANCH_MISSES     branch-misses
PERF_COUNT_HW_BUS_CYCLES        bus-cycles
PERF_COUNT_HW_STALLED_CYCLES_FRONTEND  stalled-cycles-frontend
PERF_COUNT_HW_STALLED_CYCLES_BACKEND   stalled-cycles-backend
PERF_COUNT_HW_REF_CPU_CYCLES    ref-cycles       (always at nominal rate)
```

Software counters (always available, kernel-maintained):

```
PERF_COUNT_SW_CPU_CLOCK        cpu-clock        (ns of CPU time)
PERF_COUNT_SW_TASK_CLOCK        task-clock       (ns on task)
PERF_COUNT_SW_PAGE_FAULTS       page-faults
PERF_COUNT_SW_CONTEXT_SWITCHES  context-switches
PERF_COUNT_SW_CPU_MIGRATIONS    cpu-migrations
PERF_COUNT_SW_PAGE_FAULTS_MIN   minor-faults
PERF_COUNT_SW_PAGE_FAULTS_MAJ   major-faults
PERF_COUNT_SW_ALIGNMENT_FAULTS   alignment-faults
PERF_COUNT_SW_EMULATION_FAULTS  emulation-faults
PERF_COUNT_SW_BPF_OUTPUT        bpf-output       (BPF perf_event output)
```

Hardware cache counters pack `cache_id`, `op_id`, `result_id` into a
single 64-bit `config`. The encoding, from `perf_event_open(2)`, is:

```
{ cache_id << 0 | op_id << 8 | result_id << 16 }
```

where:

```
cache_id  : PERF_COUNT_HW_CACHE_L1D, L1I, LL, DTLB, ITLB, BPU, NODE
op_id     : PERF_COUNT_HW_CACHE_READ, WRITE, PREFETCH
result_id : PERF_COUNT_HW_CACHE_RESULT_ACCESS, MISS
```

For example, L1-dcache-load-misses is
`L1D << 0 | READ << 8 | MISS << 16`.

## The CLI Tool: `perf`

The `perf(1)` tool is the workhorse. The two everyday subcommands
are `perf stat` (counts only) and `perf record` (samples).

### Counting: `perf stat`

```
$ perf stat -- sleep 1

 Performance counter stats for 'sleep 1':

              1.20 msec task-clock                #   0.001 CPUs utilized
                 1      context-switches         #   833.333 /sec
                 0      cpu-migrations           #     0.000 /sec
                51      page-faults              #  42.500 K/sec
           257,832      cycles                    # 214.860 MHz
           165,914      instructions              #   0.64  insn per cycle
            32,114      branches                  #  26.762 M/sec
             2,114      branch-misses             #   1.760 M/sec
       1.001464893 seconds time elapsed
```

For a program under test:

```
$ perf stat -e cycles,instructions,cache-misses,branch-misses \
            -- ./my_bench
```

For a longer catalog:

```
$ perf stat -a -e 'cache*' -- sleep 5
```

The `-a` measures *all* CPUs system-wide. The glob is expanded
against `/sys/bus/event_source/devices/cpu/events/`.

### Sampling: `perf record`

```
# 999 Hz, kernel + user stacks, call graphs:
$ perf record -F 999 -ag -- ./my_bench
[ perf record: Woken up 14 times to write data ]
[ perf record: Captured and wrote 3.521 MB perf.data ]

# Or, sample on cache-misses with a 10000-event period:
$ perf record -e cache-misses -c 10000 -- ./my_bench
```

Sample frequency vs sample period: with `-F 999` the kernel tries
to deliver a sample 999 times per second (it auto-adjusts the period
between events). With `-c 10000` the period is fixed at 10000
events per sample, regardless of frequency.

For accurate call graphs, `-g` selects the unwind mode:

| `-g` arg       | Method                              | Pros / cons              |
|----------------|-------------------------------------|--------------------------|
| (default)      | fp                                  | fast, fails on -fomit-fp |
| `dwarf`        | DWARF (.debug_info)                 | accurate, large samples  |
| `lbr`          | Intel Last Branch Record            | accurate, limited depth  |

LBR is the gold standard on Intel: the CPU records the last ~16
branches in hardware, so the kernel can reconstruct the call path
without unwinding. Very low overhead.

### Reporting: `perf report` and flame graphs

`perf record` writes `perf.data`. To get an annotated, sortable
TUI:

```
$ perf report
```

But the canonical *visualization* is the flame graph, à la Brendan
Gregg. The flow:

```
$ perf record -F 99 -ag -- sleep 30
$ perf script -g nf > out.stacks        # folded stacks, one per line
   -- or --
$ perf script > out.perf-script        # perf-script format
$ git clone https://github.com/brendangregg/FlameGraph
$ FlameGraph/stackcollapse-perf.pl out.perf-script | \
  FlameGraph/flamegraph.pl > out.svg
```

A folded stack line looks like:

```
my_bench;do_work;process_one;memcpy 2345
my_bench;do_work;process_two;parse;strtol 890
```

Each line is `path;path;...;leaf count`. `flamegraph.pl` produces an
SVG where width is the count (a proxy for CPU time) and height is
the stack depth. Hot paths stick out as wide plateaus.

For differential profiling (regressions):

```
$ perf record -o old.data -- ./bench
# ... change something ...
$ perf record -o new.data -- ./bench
$ perf diff old.data new.data
```

## Tracepoints

Tracepoints are static instrumentation points the kernel exposes via
`/sys/kernel/tracing/events/`. They cover essentially every
subsystem — sched, irq, net, ext4, syscalls, you name it.

```
$ ls /sys/kernel/tracing/events/sched/
enable              sched_kthread_stop          sched_process_hgr         sched_switch ...
filter
$ perf list 'sched:*'
  sched:sched_kthread_stop              [Tracepoint event]
  sched:sched_kthread_stop_ret          [Tracepoint event]
  sched:sched_process_exec              [Tracepoint event]
  sched:sched_process_fork              [Tracepoint event]
  sched:sched_process_wait              [Tracepoint event]
  sched:sched_switch                    [Tracepoint event]
  ...
```

Each tracepoint has a `format` file describing its argument layout.
perf can record them as events:

```
$ perf record -e sched:sched_switch -e sched:sched_process_fork -a -- sleep 5
$ perf script
# Shows every context switch with prev/next task and pid, every fork.
```

Tracepoints are *cheap* when not enabled — they compile down to a
single `static_branch` test that the JIT flips to a `nop` until
something attaches.

## The `mmap`d Ring Buffer

For sampling and tracepoint streaming, the fd from
`perf_event_open()` is `mmap`ed:

```c
struct perf_event_mmap_page *base;
base = mmap(NULL, 2 * MMAP_PAGES + 1, PROT_READ | PROT_WRITE,
            MAP_SHARED, fd, 0);
```

The first page (`base`) is the **metadata page** — a `struct
perf_event_mmap_page` with `data_head` and `data_tail` indices into
the ring buffer (the remaining pages). Producers (the kernel) update
`data_head`; consumers (user space) read up to `data_head` and then
update `data_tail` to release space. This lockless,
single-producer / single-consumer ring is what `perf record` reads
from.

A simplified reader loop:

```c
void drain(struct perf_event_mmap_page *hdr,
           void *buf, size_t pgsize)
{
    uint64_t head = __atomic_load_n(&hdr->data_head,
                                    __ATOMIC_ACQUIRE);
    uint64_t tail = hdr->data_tail;
    while (tail != head) {
        struct perf_event_header *eh =
            buf + (tail % (pgsize * 2));
        /* dispatch on eh->type:
           PERF_RECORD_SAMPLE, PERF_RECORD_COMM, ... */
        tail += eh->size;
    }
    __atomic_store_n(&hdr->data_tail, tail, __ATOMIC_RELEASE);
}
```

This is the shape of any custom perf consumer — `libperf`, `perfmap`,
the Parca agent, pyroscope, Vector's hostmetrics — all of them.

## Hardware-Counter Reality: Multiplexing

A CPU has a fixed number of PMU slots per event type (e.g. 4 general
slots on Skylake, plus 3 fixed slots for cycles / instructions /
ref-cycles). Open more events than slots and the kernel **time
multiplexes**: each event is on for a slice of time, scaled by a
`time_enabled / time_running` ratio. The ratio is reported per event
in `perf stat` output if you ask with `-v`:

```
$ perf stat -v -e cycles,instructions,cache-misses,branch-misses \
            -e L1-dcache-load-misses,LLC-load-misses -- ./bench
   ... opens 6 events on a 4-slot PMU ...
   cycles: 1234567 1000000000     (counted / time_enabled_ns)
   cache-misses: 890 250000000    (ran only 25% of the time)
```

If you see a `time_running` much less than `time_enabled`, your
event was multiplexed. Narrow the event set or use cgroup-scoped
events.

## sysctls and Permissions

The kernel gates access via `/proc/sys/kernel/perf_event_paranoid`:

```
-1   Allow all (root can read other users' samples)
 0   Disallow raw and tracepoint samples for unprivileged
 1   Disallow CPU events for unprivileged
 2   Disallow kernel-level events for unprivileged
 3   Disallow perf for unprivileged entirely        (default since ~5.10)
 4   Disallow perf for all but kernel debuggers
```

`/proc/sys/kernel/perf_event_max_sample_rate` caps the sample rate
a non-privileged user can request. `perf_event_mlock_kb` caps the
amount of `mlock`ed ring buffer a user may have.

`CAP_PERFMON` (added 5.8) bypasses `perf_event_paranoid`, useful for
production monitoring agents that need to run unprivileged but
trusted.

## A Worked Workflow

A small but real bug-hunt session, narrated:

1. **"Why is my service 30% slower after the refactor?"**

   ```
   perf record -F 99 -g -- ./service &  # background
   wrk -t4 -c100 http://localhost:8080  # load
   kill %1; perf report
   ```

2. **Top of the report shows 40% of samples in `mutex_lock`.** That
   is suspicious — we thought we removed the mutex contention. Look
   at the call path under it. It goes
   `worker::run -> handle_request -> get_session -> sessions.lock()`.

3. **Switch to a finer probe.** Suspect the session map:

   ```
   perf record -e sched:sched_switch -ag -- sleep 10
   perf script | head
   ```

   Lots of off-CPU time on the `worker` threads. That fits.

4. **Use off-CPU profiling.** In modern perf:

   ```
   perf record -e sched:sched_switch -ag -- sleep 30
   perf script | stackcollapse-perf.pl | flamegraph.pl > off.svg
   ```

   The off-CPU flame shows the lock acquisition as the hot path.

5. **Fix the lock, re-bench.** `perf diff old.data new.data` shows
   the `mutex_lock` samples down 95%, and `wrk` reports the 30%
   gain back.

The point is not the flame graph per se; it is that perf gives
you *both* the on-CPU profile (where time is spent executing) and,
with tracepoint-driven off-CPU analysis, where time is spent
*waiting*. You need both.

## References

1. **`perf_event_open(2)` man page** —
   <https://man7.org/linux/man-pages/man2/perf_event_open.2.html>
2. **`perf(1)` man page** —
   <https://man7.org/linux/man-pages/man1/perf.1.html>
3. **Official perf wiki** —
   <https://perf.wiki.kernel.org/>
4. **Brendan Gregg's perf guide (canonical reference for
   flamegraph-style workflows)** —
   <https://www.brendangregg.com/perf.html>
5. **Brendan Gregg's "perf examples"** —
   <https://www.brendangregg.com/perf.html#sect1>
   (also his book *Systems Performance*, Addison-Wesley 2014, Ch. 6)
6. **`tools/perf/Documentation/` source** —
   <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/tools/perf/Documentation>
7. **`Documentation/admin-guide/perf-security.rst`** —
   <https://www.kernel.org/doc/html/latest/admin-guide/perf-security.rst>
8. **LWN: "What is perf?" (Vince Weaver, 2010)** —
   <https://lwn.net/Articles/433494/> and the long-form follow-up
   series <https://lwn.net/Articles/420223/>
9. **Flame graph tool** —
   <https://github.com/brendangregg/FlameGraph>
10. **`libperf` (the C API that wraps `perf_event_open`)** —
   <https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/tools/lib/perf>
