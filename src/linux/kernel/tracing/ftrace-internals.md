# ftrace Internals — The Kernel's Built-in Tracer

## What ftrace Is (and Is Not)

ftrace is not one tool, it is a *framework* that lives in
`kernel/trace/`. Its name originally meant "function tracer" because the
framework's first user was a per-call recording of every kernel function,
but it has since absorbed event tracing, the tracepoint infrastructure,
histograms, kprobes/uprobes registration, and the trace ring buffer. When
people say "ftrace" they may mean any of: the in-kernel infrastructure, the
tracefs user interface, or the userland front-ends (`trace-cmd`,
KernelShark, `perf stat`).

The framework was merged in 2.6.27 (2008), based on the work of Steven
Rostedt. The current default mount point is `/sys/kernel/tracing/`
(symlinked from `/sys/kernel/debug/tracing` for backwards compatibility).

## The mcount/fentry Patching Mechanism

ftrace function tracing depends on the compiler inserting a no-op call at
the entry of every `notrace`-untagged function. On x86_64 with GCC, the
compiler emits `call __fentry__` (or, on older toolchains, `call mcount`)
as the very first instruction of every function. At boot, `__fentry__` is
patched to a 5-byte `nop` (`0f 1f 44 00 00`). When tracing is enabled for
a given function, ftrace replaces those 5 bytes with a `call
ftrace_caller`. The change uses `text_poke_bp()` so it is atomic with
respect to other CPUs executing the same instruction.

```
   Before enabling tracing           After enabling tracing
   ---------------------------------  ---------------------------------
   push %rbp                         push %rbp
   mov  %rsp, %rbp                   mov  %rsp, %rbp
   call __fentry__                   call ftrace_caller      <-- 5-byte patch
                                    ; on x86-64 with dynamic ftrace
   ...function body...               ...function body...
```

`ftrace_caller` runs the registered handlers, the most common of which is
`function_trace_call()`. It writes a record
(`struct ftrace_entry { u64 ip; u64 parent_ip; u64 flags; }`) into the
ring buffer and returns. The patched call adds roughly 100 ns per call,
which is acceptable in production but visible in microbenchmarks —
`CONFIG_PREEMPT_RT` configurations sometimes disable ftrace by default.

For finer control the kernel exposes a per-function table,
`/sys/kernel/tracing/available_filter_functions`, which is populated at
build time from `__start_mcount_loc`/`__stop_mcount_loc` linker sections.
Each entry is `(ip, flags)`. The user filters by writing function-name
patterns to `set_ftrace_filter` and `set_ftrace_notrace`.

## Architecture of the Framework

```
                user space
   --------------------------------------------------
   |  trace-cmd   KernelShark   cat /sys/kernel/tracing/...  |
   --------------------------------------------------
                ^
                | tracefs  (mount: /sys/kernel/tracing)
                v
   +-------------------------------------------------+
   | kernel/trace/                                   |
   |  ftrace.c           function tracer             |
   |  trace_functions.c  function_graph              |
   |  trace.c            ring buffer + events         |
   |  trace_output.c     fmt parsing                 |
   |  trace_events.c     tracepoints -> events       |
   |  trace_kprobe.c     kprobe events               |
   |  trace_uprobe.c     uprobe events               |
   |  trace_hwlat.c      hardware latency            |
   |  trace_mmiotrace.c  MMIO                        |
   |  trace_benchmark.c  microbenchmark             |
   |  trace_stack.c     stack traces                |
   |  tracing_map.c     histograms                  |
   +-------------------------------------------------+
                ^
                | per-function patches + ring buffer
                v
   +-------------------------------------------------+
   | instrumented kernel functions                   |
   +-------------------------------------------------+
```

## The Ring Buffer

Every trace record is stored in a per-CPU lockless ring buffer implemented
in `kernel/trace/ring_buffer.c`. Each CPU has its own buffer; the buffer
is divided into pages that are either `DATA`, `HEADER`, `PADDING`, or
`TIME_EXTEND`. Writers compose a record by reserving space, writing the
payload, and committing. The buffer supports nested writers (an NMI can
interrupt a writer and add another event safely).

```
   +---- per-CPU ring buffer ----+
   |  HEADER  |  DATA | DATA | PAD | TIME_EXTEND | DATA | ... |
   +------------------------------+
   ^reader                        ^writer
```

The reader side exposes records via `trace_pipe` (consumed when read)
and `trace` (snapshotted; non-destructive). The two behave differently:

- `cat trace` shows you the current contents of the buffer without
  consuming them; re-running it shows the same records plus new ones.
- `cat trace_pipe` is a *consumer*: each record is removed after being
  read; if nothing is writing, `cat` blocks (or returns EOF when
  `tracing_on` is 0).

## Tracer Types

`/sys/kernel/tracing/available_tracers` lists the loaded tracers; writing
one to `/sys/kernel/tracing/current_tracer` activates it. Common ones:

| Tracer            | Records                                                   |
|-------------------|-----------------------------------------------------------|
| `function`        | One record per kernel function entry.                     |
| `function_graph`  | Entry + return, with call/return indentation and timing. |
| `dl` / `wakeup`   | Tracks the highest-priority wake-up latency.             |
| `wakeup_rt`       | Same, with realtime tasks.                                |
| `hwlat`           | Detector for hardware-induced latencies (SMI, firmware). |
| `irqsoff`         | Longest IRQs-off periods.                                 |
| `preemptoff`      | Longest preemption-off periods.                           |
| `preemptirqsoff`  | Combined.                                                 |
| `mmiotrace`       | MMIO reads/writes, for reverse-engineering drivers.      |
| `branch`          | Branch profiler (if unlikely/likely annotations).        |
| `nop`             | Disables function tracing but keeps events.              |
| `blk`             | Block I/O events (block/, used by `blktrace`).           |

A representative `function_graph` output:

```
 3)   0.120 us    |  mutex_unlock();
 3)               |  vfs_write() {
 3)   0.040 us    |    inotify_inode_mark();
 3)   0.100 us    |    __sb_start_write();
 3)   1.200 us    |    do_writepages() {      <-- innermost level
 3)   0.080 us    |      mpage_writepage();
 3)   0.020 us    |      test_clear_page_writeback();
 3)   1.325 us    |    }
 3)   1.900 us    |  }
```

## Events and Tracepoints

`tracepoints` are static instrumentation points in the kernel, declared
with the `trace_<name>(args...)` macro and defined in
`include/trace/events/*.h`. ftrace exposes them under
`/sys/kernel/tracing/events/`. Each event has:

- An `enable` file (echo 1 to enable).
- A `filter` file with predicate syntax.
- A `format` file describing the binary layout of the record.

```
$ cat /sys/kernel/tracing/events/sched/sched_switch/format
name: sched_switch
ID: 21
format:
        field:unsigned short common_type;         offset:0;  size:2;  signed:0;
        field:unsigned char  common_flags;        offset:2;  size:1;  signed:0;
        field:unsigned char  common_preempt_count; offset:3;  size:1;  signed:0;
        field:int            common_pid;           offset:4;  size:4;  signed:1;

        field:char           prev_comm[16];        offset:8;  size:16; signed:1;
        field:pid_t          prev_pid;             offset:24; size:4;  signed:1;
        field:int            prev_prio;            offset:28; size:4;  signed:1;
        field:long           prev_state;           offset:32; size:8;  signed:1;

        field:char           next_comm[16];        offset:40; size:16; signed:1;
        field:pid_t          next_pid;            offset:56; size:4;  signed:1;
        ...
print fmt: "prev_comm=%s prev_pid=%d ..."
```

A tracepoint is essentially:

```c
/* kernel/sched/core.c */
static void __sched notrace __schedule(...)
{
    ...
    trace_sched_switch(prev, next);
    ...
}

/* include/trace/events/sched.h */
DECLARE_EVENT_CLASS(sched_wakeup_template,
    TP_PROTO(struct task_struct *p),
    TP_ARGS(p),
    TP_STRUCT__entry(
        __array(char,  comm,  TASK_COMM_LEN)
        __field(pid_t, pid)
        __field(int,   prio)
        __field(int,   target_cpu)
    ),
    TP_fast_assign(
        memcpy(__entry->comm, p->comm, TASK_COMM_LEN);
        __entry->pid        = p->pid;
        __entry->prio       = p->prio;
        __entry->target_cpu = task_cpu(p);
    ),
    TP_printk("comm=%s pid=%d prio=%d target_cpu=%d",
              __entry->comm, __entry->pid, __entry->prio, __entry->target_cpu)
);
```

Each `DECLARE_EVENT_CLASS`/`DEFINE_EVENT` pair emits a `trace_<name>`
inline and a `__tracepoint_<name>` static-key-protected callsite. When no
consumer attaches, the static key is OFF and the tracepoint is a single
`nop` (no overhead). When the first consumer attaches, the static key
turns ON, branching into the tracepoint call chain.

## Triggers and Filters

Beyond `enable`, an event can have *triggers* — actions that fire when
the event fires. Examples:

```bash
# Enable another tracer when a specific event happens
echo 'traceoff if prev_pid == 1234' > events/sched/sched_switch/trigger

# Snapshot the buffer (capture the trace up to this point)
echo 'snapshot' > events/sched/sched_process_fork/trigger

# Stop tracing after N hits
echo 'traceoff if next_pid == 1234' > events/sched/sched_switch/trigger

# Stack traces
echo 'stacktrace' > events/sched/sched_switch/trigger
```

Triggers are implemented in `kernel/trace/trace_events_trigger.c`. The
syntax is `action[ if predicate]` and supports `enable_event`, `disable_event`,
`traceoff`, `traceon`, `stacktrace`, `snapshot`, `hist`.

## Histograms (hist trigger)

The `hist` trigger builds a streaming histogram of event fields. It is the
in-kernel equivalent of an `awk | sort | uniq -c` pipeline:

```bash
# Per-pid syscall count
echo 'hist:keys=common_pid:vals=hitcount' \
    > /sys/kernel/tracing/events/raw_syscalls/sys_enter/trigger

cat /sys/kernel/tracing/events/raw_syscalls/sys_enter/hist

# output:
# { common_pid:       1234 }  hitcount:        142
# { common_pid:       5678 }  hitcount:         95
# ...
```

Composite keys and stacked histograms are supported:

```bash
# Two-level: syscall id, then pid
echo 'hist:keys=id,common_pid:vals=hitcount:sort=id' \
    > events/raw_syscalls/sys_enter/trigger
```

The implementation is in `kernel/trace/trace_events_hist.c`. Internally
each unique key is a hash table entry; per-key values are atomic. The
verifier-equivalent here is the histogram *parser*, which compiles the
user's expression into a `hist_trigger_data` structure used to interpret
the event record at run time.

## Filters

Filters are predicates over the event fields expressed as
`field OP value` joined by `&&` / `||`:

```bash
echo 'prev_pid == 1234 && next_comm == bash' \
    > /sys/kernel/tracing/events/sched/sched_switch/filter
```

The parser in `kernel/trace/trace_events_filter.c` walks the AST and
generates a small bytecode interpreter (`filter_pred_fn_t` callbacks) so
each event hit evaluates quickly without re-parsing.

## Instances

Each `trace_array` corresponds to a *tracefs instance* with its own
buffers, tracers, events, and options. The "top" instance at
`/sys/kernel/tracing` is one of them. Creating a new instance is a
mkdir:

```bash
mkdir /sys/kernel/tracing/instances/foo
ls /sys/kernel/tracing/instances/foo
# available_events  buffer_size_kb  events  set_event  trace  trace_pipe ...
```

The new instance has its own ring buffer, its own filters, and its own
`current_tracer`. The kernel side is `trace_array_create()` in
`kernel/trace/trace.c`. The instance is destroyed by `rmdir`. This is the
mechanism `perf record -e sched:*` and bpftrace use to isolate their
trace streams.

## Snapshots

The snapshot mechanism swaps the active ring buffer with a secondary
"max" buffer. You can trigger it manually (`echo 1 > snapshot`) or on
demand via a trigger (`echo 'snapshot' > events/sched/.../trigger`). The
swap is atomic: ongoing writers see the buffer swap but never lose
events because the writer never crosses into the wrong half.

```bash
echo 1 > /sys/kernel/tracing/snapshot      # take a snapshot
cat /sys/kernel/tracing/snapshot          # read it
echo 0 > /sys/kernel/tracing/snapshot     # clear and re-enable
```

## tracefs Layout

```
/sys/kernel/tracing/
├── available_tracers         # function function_graph wakeup_rt hwlat ...
├── current_tracer            # write here to switch
├── tracing_on                # global enable (1/0)
├── trace                     # current buffer (non-destructive)
├── trace_pipe                # streaming buffer (destructive)
├── trace_marker              # userspace can write annotations
├── set_event                 # bulk event enable/disable
├── set_ftrace_filter         # functions to trace
├── set_ftrace_notrace        # functions to skip
├── set_event_pid             # filter by PID
├── set_ftrace_pid            # PID filter for function tracer
├── buffer_size_kb            # per-CPU buffer size
├── per_cpu/
│   └── cpu0/
│       ├── trace             # per-CPU buffer
│       ├── trace_pipe
│       ├── trace_pipe_raw    # binary raw
│       ├── snapshot
│       └── stats
├── events/                   # one directory per subsystem
│   ├── sched/
│   │   ├── sched_switch/
│   │   │   ├── enable
│   │   │   ├── filter
│   │   │   ├── format
│   │   │   ├── trigger
│   │   │   └── hist
│   │   └── ...
│   └── ...
├── instances/                # user-created trace arrays
│   └── foo/                  # has the same shape as /sys/kernel/tracing
├── snapshot                  # snapshot buffer
├── options/                  # per-tracer knobs (print-parent, etc.)
├── trace_clock                # choose clock source (local/global/x86-tsc)
└── available_filter_functions
```

## trace-cmd: The Convenience Layer

Direct tracefs use is verbose; `trace-cmd` is the standard wrapper.

```bash
# List tracers
trace-cmd list -t

# Record 5 seconds of function tracing, filtered to tcp_*
trace-cmd record -p function -l 'tcp_*' -- sleep 5

# Show the result
trace-cmd report > trace.txt

# Save as binary
trace-cmd extract -o trace.dat

# Open in KernelShark
kernelshark trace.dat
```

`trace-cmd record` writes raw records to a packed format (`trace-cmd.dat`,
v7+) that KernelShark reads for interactive analysis. The format is
documented in `Documentation/trace-cmd/trace-cmd.faq` of the trace-cmd
repo.

## trace_marker: Userspace → Kernel

```c
#include <fcntl.h>
#include <unistd.h>

int fd = open("/sys/kernel/tracing/trace_marker", O_WRONLY);
write(fd, "my-app: request 1234 start\n", 27);
/* ... do work ... */
write(fd, "my-app: request 1234 done\n", 26);
```

The kernel appends a `print:` event into the ring buffer interleaved with
the in-kernel trace. This is the standard way to correlate userspace
metrics with kernel trace events. perfetto, trace-cruncher, and crosvm all
use it.

## Performance Considerations

- Function tracing adds ~100 ns per call site (the 5-byte patch). On a
  modern x86_64 server running a busy syscall workload, enabling
  `function_graph` for `vfs_*` shows ~3–7% system time increase.
- Filtering on function-name regex is done in kernel by
  `ftrace_match_record()`, so the patching decision is once-per-function
  rather than per-call.
- `set_event_pid` / `set_ftrace_pid` filters at the *record* path; they
  still pay the patch overhead but skip the ring buffer write.
- The ring buffer's per-CPU nature means a writer on CPU3 does not contend
  with a writer on CPU5; but the *reader* (e.g. `trace-cmd report`) must
  merge per-CPU streams by timestamp.
- `trace_clock=global` enables a globally monotonic timestamp (more
  expensive than per-CPU `local` clock); only needed for cross-CPU
  ordering analysis.

## References

- Linux kernel docs, "ftrace — Function Tracer" — https://docs.kernel.org/trace/ftrace.html
- Linux kernel docs, "Event Tracing" — https://docs.kernel.org/trace/events.html
- Linux kernel docs, "Histograms" — https://docs.kernel.org/trace/histogram.html
- Linux kernel docs, "trace-cmd" project page — https://www.trace-cmd.org/
- `kernel/trace/trace.c` source — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/trace/trace.c
- `kernel/trace/ring_buffer.c` — https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/kernel/trace/ring_buffer.c
- `Documentation/trace/ftrace.rst` — https://docs.kernel.org/trace/ftrace.html
- LWN: "Function tracing with ftrace" (Steven Rostedt, 2012) — https://lwn.net/Articles/370759/
- LWN: "ftrace: The history of the kernel tracer" — https://lwn.net/Articles/370899/
- LWN: "Function graph tracing with ftrace" — https://lwn.net/Articles/371060/
- `trace-cmd(1)` man page — https://man7.org/linux/man-pages/man1/trace-cmd.1.html
- Steven Rostedt, "Tracepoints, ftrace, and the Linux kernel" (Korea Linux Forum 2015) — slides at https://blog.linuxplumbersconf.org/
- KernelShark source — https://git.kernel.org/pub/scm/utils/trace-cmd/kernel-shark.git/
- libtraceevent — https://git.kernel.org/pub/scm/utils/trace-cmd/libtraceevent.git/
- "Using the TRACE_EVENT() macro" (Steven Rostedt, LWN) — https://lwn.net/Articles/379903/
