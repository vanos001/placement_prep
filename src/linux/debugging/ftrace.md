# ftrace — Kernel Function Tracing

## Introduction

ftrace is the Linux kernel's built-in function tracer. Originally designed for tracing
kernel function calls, it has evolved into a comprehensive tracing framework that supports
function profiling, event tracing, interrupt latency measurement, and more. Unlike perf,
which focuses on sampling, ftrace provides detailed trace records for every event.

ftrace operates entirely within the kernel through the `tracefs` filesystem (typically
mounted at `/sys/kernel/debug/tracing` or `/sys/kernel/tracing`). It requires no
external tools for basic use — just `echo` and `cat` — though `trace-cmd` provides a
much more convenient interface.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Space                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  trace-cmd   │  │  KernelShark │  │  cat/echo        │  │
│  │  (frontend)  │  │  (GUI)       │  │  (direct access) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────────┘  │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
   ┌──────▼─────────────────▼─────────────────▼───────────────┐
   │                    tracefs filesystem                      │
   │              /sys/kernel/tracing/                          │
   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
   │  │ current_tracer│ │ set_event   │  │ trace_marker    │  │
   │  │ trace        │ │ per_cpu/cpu0│  │ trace_pipe      │  │
   │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
   └─────────┼────────────────┼──────────────────┼────────────┘
             │                │                  │
   ┌─────────▼────────────────▼──────────────────▼────────────┐
   │                   Tracing Infrastructure                   │
   │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
   │  │ Function     │  │ Event        │  │ Trace          │ │
   │  │ Tracer       │  │ Tracing      │  │ Output         │ │
   │  │              │  │ (tracepoints)│  │ (ring buffer)  │ │
   │  └──────────────┘  └──────────────┘  └────────────────┘ │
   │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
   │  │ kprobes       │  │ Histograms  │  │ Trace          │ │
   │  │ (dynamic)     │  │ (hist)      │  │ Instances      │ │
   │  └──────────────┘  └──────────────┘  └────────────────┘ │
   └─────────────────────────────────────────────────────────┘
```

## tracefs Filesystem

The tracefs filesystem is the primary interface to ftrace. Understanding its structure
is essential.

```bash
# Mount tracefs (usually auto-mounted)
sudo mount -t tracefs tracefs /sys/kernel/tracing

# Or check if it's already mounted
mount | grep tracefs
# tracefs on /sys/kernel/tracing type tracefs (rw,relatime)
# tracefs on /sys/kernel/debug/tracing type tracefs (rw,relatime)

# List key files
ls /sys/kernel/tracing/
```

### Key Files

| File | Purpose |
|------|---------|
| `current_tracer` | Read/set the active tracer |
| `trace` | Read the trace buffer |
| `trace_pipe` | Read and consume trace events (blocking) |
| `tracing_on` | Enable/disable tracing (1/0) |
| `buffer_size_kb` | Per-CPU ring buffer size |
| `set_event` | Enable/disable specific events |
| `trace_marker` | Write user messages into the trace |
| `available_tracers` | List available tracers |
| `available_filter_functions` | List traceable functions |
| `set_ftrace_filter` | Filter which functions to trace |
| `set_ftrace_pid` | Trace only specific PIDs |

## Function Tracer

The function tracer records every kernel function call. It's the original ftrace feature.

### Basic Function Tracing

```bash
# Check available tracers
cat /sys/kernel/tracing/available_tracers
# nop function function_graph wakeup wakeup_rt preemptirqsoff

# Enable function tracer
echo function > /sys/kernel/tracing/current_tracer

# Start tracing
echo 1 > /sys/kernel/tracing/tracing_on

# Let it run for a bit, then read the trace
cat /sys/kernel/tracing/trace | head -50

# Stop tracing
echo 0 > /sys/kernel/tracing/tracing_on
```

### Example Output

```
# tracer: function
#
#                              _-----=> irqs-off
#                             / _----=> need-resched
#                            | / _---=> hardirq/softirq
#                            || / _--=> preempt-depth
#                            ||| /     delay
#           TASK-PID   CPU#  ||||    TIMESTAMP  FUNCTION
#              | |       |   ||||       |         |
          <idle>-0     [000] d..1    45.123456: _raw_spin_lock_irqsave <-hrtimer_interrupt
          <idle>-0     [000] d..1    45.123457: ktime_get_update_offsets_now <-hrtimer_interrupt
          <idle>-0     [000] d..1    45.123458: __hrtimer_run_queues <-hrtimer_interrupt
          <idle>-0     [000] d..1    45.123459: _raw_spin_unlock_irqrestore <-hrtimer_interrupt
          <idle>-0     [000] ..s1    45.123460: tick_sched_timer <-__hrtimer_run_queues
          <idle>-0     [000] ..s1    45.123461: tick_do_update_jiffies64 <-tick_sched_timer
```

The flags column shows:
- `d` — interrupts disabled
- `.` — irqs enabled
- `s` — in softirq
- `h` — in hardirq
- `N` — need resched
- `.` — no preempt

### Filtering Functions

```bash
# Trace only specific functions
echo do_sys_open > /sys/kernel/tracing/set_ftrace_filter
echo function > /sys/kernel/tracing/current_tracer
echo 1 > /sys/kernel/tracing/tracing_on

# Trace multiple functions
echo "do_sys_open do_sys_openat2" > /sys/kernel/tracing/set_ftrace_filter

# Use wildcards
echo "sched_*" > /sys/kernel/tracing/set_ftrace_filter

# Exclude functions
echo "schedule" > /sys/kernel/tracing/set_ftrace_notrace

# List functions matching a pattern
cat /sys/kernel/tracing/available_filter_functions | grep "sched_"

# Clear filters
echo > /sys/kernel/tracing/set_ftrace_filter
echo > /sys/kernel/tracing/set_ftrace_notrace
```

### Per-PID Tracing

```bash
# Trace only a specific process
echo 1234 > /sys/kernel/tracing/set_ftrace_pid

# Trace current shell and children
echo $$ > /sys/kernel/tracing/set_ftrace_pid

# Disable PID filtering (trace everything)
echo > /sys/kernel/tracing/set_ftrace_pid
```

## Function Graph Tracer

The function_graph tracer shows function call hierarchies with timing information,
similar to a call graph profiler. It's one of the most useful ftrace tracers.
From the [kernel ftrace documentation](https://docs.kernel.org/trace/ftrace.html),
the function_graph tracer records both function entry and return, building a complete
call tree with per-call duration.

### Basic Usage

```bash
echo function_graph > /sys/kernel/tracing/current_tracer
echo 1 > /sys/kernel/tracing/tracing_on
# ... do something ...
echo 0 > /sys/kernel/tracing/tracing_on
cat /sys/kernel/tracing/trace
```

### Example Output

```
# tracer: function_graph
#
# CPU  DURATION                  FUNCTION CALLS
# |     |   |                     |   |   |   |
 0)               |  do_sys_open() {
 0)   0.523 us    |    getname();
 0)               |    do_filp_open() {
 0)   0.157 us    |      path_init();
 0)               |      link_path_walk() {
 0)   0.089 us    |        walk_component();
 0)   0.076 us    |        walk_component();
 0)   1.234 us    |      }
 0)   0.098 us    |      do_open();
 0)   2.891 us    |    }
 0)   0.087 us    |    putname();
 0)   4.567 us    |  }
```

Reading the output:
- `+` — function is being entered (continued on next line)
- `}` — function returned
- Duration is shown in microseconds (us) or milliseconds (ms)
- Indentation shows call depth
- `/* comment */` markers indicate special events within a function
- Leaf functions (no children) show duration on the same line as `{`
- Parent functions show total duration on the `}` closing line

### Configuring Function Graph

```bash
# Set max depth of call graph
echo 5 > /sys/kernel/tracing/max_graph_depth

# Filter to specific functions only
echo do_sys_open > /sys/kernel/tracing/set_graph_function

# Clear filter (trace all functions)
echo > /sys/kernel/tracing/set_graph_function

# Show overhead (time not accounted for by children)
echo 1 > /sys/kernel/tracing/options/funcgraph-overhead

# Show process info (pid, command)
echo 1 > /sys/kernel/tracing/options/funcgraph-proc

# Show CPU info
echo 1 > /sys/kernel/tracing/options/funcgraph-cpu

# Show absolute time instead of relative
echo 1 > /sys/kernel/tracing/options/funcgraph-abstime

# Show interrupts (irqs-off, need-resched flags)
echo 1 > /sys/kernel/tracing/options/funcgraph-irqs

# Show duration in common units
echo 1 > /sys/kernel/tracing/options/funcgraph-duration
```

### Key Options

| Option | Description |
|--------|-------------|
| `funcgraph-overhead` | Show time overhead (duration - sum of children) |
| `funcgraph-proc` | Show process name/PID per entry |
| `funcgraph-cpu` | Show CPU number |
| `funcgraph-abstime` | Show absolute timestamp instead of relative |
| `funcgraph-irqs` | Show irq-disabled/need-resched flags |
| `funcgraph-duration` | Show duration of each function |
| `funcgraph-tail` | Show return value of functions |

### trace-cmd with function_graph

```bash
# Record function graph for a specific function
sudo trace-cmd record -p function_graph -g do_sys_openat2 sleep 1
trace-cmd report

# Record function graph for all scheduler functions
sudo trace-cmd record -p function_graph -g 'schedule*' sleep 1
trace-cmd report
```

## Event Tracing

Event tracing uses static tracepoints (pre-defined in the kernel source) to trace
specific events like scheduler activity, I/O operations, and more.

### Available Events

```bash
# List all available events
ls /sys/kernel/tracing/events/

# Events are organized by subsystem:
#   block/    - Block I/O events
#   ext4/     - ext4 filesystem events
#   irq/      - Interrupt events
#   kmem/     - Kernel memory events
#   net/      - Network events
#   sched/    - Scheduler events
#   signal/   - Signal events
#   syscalls/ - System call events
#   task/     - Task events

# List events in a subsystem
ls /sys/kernel/tracing/events/sched/

# Read event format
cat /sys/kernel/tracing/events/sched/sched_switch/format
# name: sched_switch
# ID: 283
# format:
#   field:unsigned short common_type;
#   field:unsigned char common_flags;
#   field:unsigned char common_preempt_count;
#   field:int common_pid;
#   field:char prev_comm[16];
#   field:pid_t prev_pid;
#   field:int prev_prio;
#   field:long prev_state;
#   field:char next_comm[16];
#   field:pid_t next_pid;
#   field:int next_prio;
```

### Enabling Events

```bash
# Enable a specific event
echo 1 > /sys/kernel/tracing/events/sched/sched_switch/enable

# Enable all events in a subsystem
echo 1 > /sys/kernel/tracing/events/sched/enable

# Enable all events (very noisy!)
echo 1 > /sys/kernel/tracing/events/enable

# Disable specific event
echo 0 > /sys/kernel/tracing/events/sched/sched_switch/enable

# Disable all events
echo 0 > /sys/kernel/tracing/events/enable

# Use set_event interface
echo "sched_switch sched_wakeup" > /sys/kernel/tracing/set_event
```

### Example: Tracing Scheduler Events

```bash
echo "sched_switch sched_wakeup" > /sys/kernel/tracing/set_event
echo 1 > /sys/kernel/tracing/tracing_on
sleep 1
echo 0 > /sys/kernel/tracing/tracing_on
cat /sys/kernel/tracing/trace
```

```
# tracer: nop
#
#                                TASK-PID   CPU#     TIMESTAMP  COMM            FUNCTION
#                                   | |       |        |         |                |
              cat-12345 [002]  1234.567890: sched_switch: prev_comm=cat prev_pid=12345 prev_prio=120 prev_state=S ==> next_comm=bash next_pid=1234 next_prio=120
            bash-1234  [002]  1234.567891: sched_wakeup: comm=cat pid=12345 prio=120 target_cpu=002
          <idle>-0     [000]  1234.567892: sched_switch: prev_comm=swapper/0 prev_pid=0 prev_prio=120 prev_state=R ==> next_comm=kworker/0:1 next_pid=15 prio=120
```

### Event Filtering

```bash
# Filter events by field values
echo "prev_pid == 1234" > /sys/kernel/tracing/events/sched/sched_switch/filter

# Complex filters
echo "prev_pid == 1234 || next_pid == 1234" > /sys/kernel/tracing/events/sched/sched_switch/filter

# String filter
echo 'prev_comm == "bash"' > /sys/kernel/tracing/events/sched/sched_switch/filter

# Clear filter
echo 0 > /sys/kernel/tracing/events/sched/sched_switch/filter
```

## kprobes — Dynamic Tracing

kprobes allow you to dynamically insert tracepoints at almost any kernel function
address. They are the foundation for dynamic kernel tracing.

### How Kprobes Work

When a kprobe is registered, the kernel:
1. Saves a copy of the probed instruction
2. Replaces the first byte(s) with a breakpoint instruction (e.g., `int3` on x86)
3. When the breakpoint fires, the CPU's registers are saved and control passes to the kprobe handler
4. The original instruction is single-stepped (from the copied instruction, not in-place)
5. The post-handler runs, then execution continues at the instruction after the probe

This mechanism works for virtually any kernel instruction, though some code regions are blacklisted (e.g., the kprobe infrastructure itself, interrupt entry/exit paths).

### Types of Probes

```
┌─────────────────────────────────────────────┐
│ Kernel Function: do_sys_open()               │
│                                             │
│ Entry:  ┌──────────┐                        │
│         │ kprobe    │ ← triggered on entry   │
│         └──────────┘                        │
│         ... function body ...                │
│ Return: ┌──────────┐                        │
│         │ kretprobe │ ← triggered on return  │
│         └──────────┘                        │
└─────────────────────────────────────────────┘
```

### Kprobe Jump Optimization

On x86 with `CONFIG_OPTPROBES=y`, kprobes can replace breakpoint instructions with jump instructions for lower overhead. The optimization process:

1. A safety check verifies the probe region is safe for replacement
2. A "detour" buffer is prepared with: register save → handler call → register restore → original instruction → jump back
3. After `synchronize_rcu()`, the breakpoint is replaced with a `jmp` to the detour buffer
4. This reduces probe-hit overhead from ~1µs (int3 trap) to ~0.1µs (direct jump)

Jump optimization is not possible when:
- The probe has a post_handler
- Other instructions in the optimized region are probed
- The probe region spans multiple functions
- The kernel is compiled with `CONFIG_PREEMPT=y`

### Kretprobes (Return Probes)

Kretprobes fire when a function returns. The mechanism:
1. A kprobe at function entry saves the return address and replaces it with a trampoline
2. When the function returns, control goes to the trampoline
3. The user's return handler runs with access to the return value
4. The saved return address is restored

The `maxactive` field controls how many concurrent invocations can be probed (default: `max(10, 2*NR_CPUS)`). Setting it too low causes missed probes (tracked in `nmissed`).

### Using kprobes with tracefs

```bash
# Add a kprobe at do_sys_open
echo 'p:myprobe do_sys_open filename=+0(%si):string flags=%dx' > /sys/kernel/tracing/kprobe_events

# Enable the probe
echo 1 > /sys/kernel/tracing/events/kprobes/myprobe/enable

# Read trace
cat /sys/kernel/tracing/trace_pipe

# Add a kretprobe (return probe)
echo 'r:myretprobe do_sys_open ret=$retval' > /sys/kernel/tracing/kprobe_events

# Enable
echo 1 > /sys/kernel/tracing/events/kprobes/myretprobe/enable

# List all kprobes
cat /sys/kernel/tracing/kprobe_events

# Remove a probe
echo '-:myprobe' >> /sys/kernel/tracing/kprobe_events
echo '-:myretprobe' >> /sys/kernel/tracing/kprobe_events
```

### kprobe Argument Syntax

```bash
# Register arguments (x86-64 ABI)
# %di, %si, %dx, %cx, %r8, %r9  (first 6 args)
# %ax (return value)

# Fetch a string argument
echo 'p:myprobe do_sys_open filename=+0(%si):string' > /sys/kernel/tracing/kprobe_events

# Fetch an integer argument
echo 'p:myprobe do_sys_open flags=%dx' > /sys/kernel/tracing/kprobe_events

# Fetch memory at address
echo 'p:myprobe do_sys_open filename=+0(%si):string flags=%dx:x32' > /sys/kernel/tracing/kprobe_events

# Fetch stack pointer
echo 'p:myprobe do_sys_open stack=%bp:x64' > /sys/kernel/tracing/kprobe_events
```

## Kprobe-based Event Tracing (from kernel docs)

The following details are drawn from the official [Kprobe-based Event Tracing](https://docs.kernel.org/trace/kprobetrace.html) documentation by Masami Hiramatsu.

### Overview

Kprobe-based events are similar to tracepoint-based events but are based on kprobes (kprobe and kretprobe). They can probe wherever kprobes can probe — all functions except those with `__kprobes`/`nokprobe_inline` annotation and those marked `NOKPROBE_SYMBOL`. Unlike tracepoint-based events, kprobe events can be **added and removed dynamically, on the fly**.

Enable with `CONFIG_KPROBE_EVENTS=y`.

### Synopsis of kprobe_events

```
p[:[GRP/][EVENT]] [MOD:]SYM[+offs]|MEMADDR [FETCHARGS]  : Set a probe
r[MAXACTIVE][:[GRP/][EVENT]] [MOD:]SYM[+0] [FETCHARGS]  : Set a return probe
p[:[GRP/][EVENT]] [MOD:]SYM[+0]%return [FETCHARGS]       : Set a return probe
-:[GRP/][EVENT]                                          : Clear a probe

GRP      : Group name (default: "kprobes")
EVENT    : Event name (auto-generated if omitted)
MOD      : Module name containing SYM
SYM[+offs] : Symbol + offset for probe placement
MAXACTIVE  : Max concurrent instances for return probes
```

### Fetch Arguments

Each probe can have up to **128 arguments**:

| Syntax | Description |
|--------|-------------|
| `%REG` | Fetch register REG |
| `@ADDR` | Fetch memory at ADDR (kernel address) |
| `@SYM[+\|-offs]` | Fetch memory at SYM + offset |
| `$stackN` | Fetch Nth entry of stack (N ≥ 0) |
| `$stack` | Fetch stack address |
| `$argN` | Fetch Nth function argument (N ≥ 1, entry probe only, best effort) |
| `$retval` | Fetch return value (return probe only, best effort) |
| `$comm` | Fetch current task comm |
| `+\|-OFFS(FETCHARG)` | Fetch at offset from FETCHARG |
| `\IMM` | Store immediate value |
| `NAME=FETCHARG` | Name the argument |
| `FETCHARG:TYPE` | Cast to type |

### Supported Types

| Type | Description |
|------|-------------|
| `u8/u16/u32/u64` | Unsigned integers |
| `s8/s16/s32/s64` | Signed integers |
| `x8/x16/x32/x64` | Hexadecimal |
| `char` | Character value |
| `string` | Null-terminated kernel string |
| `ustring` | Null-terminated user-space string |
| `symbol` | Pointer as symbol+offset |
| `symstr` | Symbol+offset as string (for filtering) |
| `%pd/%pD` | VFS dentry/file name |
| `b<w>@<o>/<c>` | Bitfield: width @ offset / container-size |
| `<type>[N]` | Array of N elements |

### Function Arguments at kretprobe

Function arguments can be accessed at kretprobe using `$arg<N>` fetcharg. This is useful to record function parameters and return values at once, and trace differences in structure fields.

### Per-Probe Event Filtering

Each probe event has its own directory under `tracing/events/kprobes/<EVENT>/` with:

- **`enable`** — Write 1/0 to enable/disable
- **`format`** — Shows the event format
- **`filter`** — Write filtering rules
- **`id`** — Event ID
- **`trigger`** — Install trigger commands (stacktrace, snapshot, etc.)

### Event Profiling

Check probe hit counts via `/sys/kernel/tracing/kprobe_profile`:
```bash
cat /sys/kernel/tracing/kprobe_profile
# myprobe  1234  0    (hits  misses)
# myretprobe  5678  2
```

### Kernel Boot Parameter

Add and enable kprobe events at boot time:
```
kprobe_event=p:myprobe,do_sys_open,dfd=%ax,filename=%dx,flags=%cx
```
(Parameters are comma-delimited instead of space-delimited.)

### User Memory Access

Kprobe events support user-space memory access via:
- **`u` prefix on dereference**: `+u4(%si)` reads from user-space address in `%si + 4`
- **`ustring` type**: `+0(%si):ustring` reads a user-space string

### Example: Tracing do_sys_open

```bash
# Set kprobe on do_sys_open
echo 'p:myprobe do_sys_open dfd=%ax filename=%dx flags=%cx mode=+4($stack)' > /sys/kernel/tracing/kprobe_events

# Set kretprobe
echo 'r:myretprobe do_sys_open $retval' >> /sys/kernel/tracing/kprobe_events

# Enable both
echo 1 > /sys/kernel/tracing/events/kprobes/myprobe/enable
echo 1 > /sys/kernel/tracing/events/kprobes/myretprobe/enable

# Trace
echo 1 > /sys/kernel/tracing/tracing_on
# ... do something ...
echo 0 > /sys/kernel/tracing/tracing_on
cat /sys/kernel/tracing/trace
# <...>-1447 [001] 1038282.286875: myprobe: (do_sys_open+0x0/0xd6) dfd=3 filename=7fffd1ec4440 flags=8000 mode=0
# <...>-1447 [001] 1038282.286915: myretprobe: (sys_open+0x1b/0x1d <- do_sys_open) $retval=3

# Clear all probes
echo > /sys/kernel/tracing/kprobe_events
# Or selectively
echo '-:myprobe' >> /sys/kernel/tracing/kprobe_events
```

## uprobes — User-Space Dynamic Tracing

From `docs.kernel.org/trace/uprobetracer.html`, uprobes are the user-space counterpart of kprobes. They allow dynamic insertion of tracepoints at any instruction in user-space executables and libraries.

### How Uprobes Work

When a uprobe is registered at an offset in a user-space binary:
1. The kernel replaces the instruction at that offset with a breakpoint (e.g., `int3` on x86)
2. When the process hits the breakpoint, control passes to the uprobe handler
3. The original instruction is single-stepped, then execution continues
4. Return probes (uretprobes) work by replacing the return address with a trampoline

### Setting Up Uprobes

The uprobe interface expects the user to **calculate the offset** of the probe point in the object file (not the runtime virtual address):

```bash
# Find the offset of a function in a binary
objdump -T /bin/bash | grep main
# 00000000000a1b20 g   DF .text  0000000000000123  Base  main

# Set a uprobe at that offset
echo 'p:myprobe /bin/bash:0xa1b20' > /sys/kernel/tracing/uprobe_events

# Set a return probe (uretprobe)
echo 'r:myretprobe /bin/bash:0xa1b20' > /sys/kernel/tracing/uprobe_events

# Enable the probe
echo 1 > /sys/kernel/tracing/events/uprobes/myprobe/enable

# Read events
cat /sys/kernel/tracing/trace_pipe
```

### Uprobe Synopsis

```
p[:[GRP/][EVENT]] PATH:OFFSET [FETCHARGS]  : Set a uprobe
r[:[GRP/][EVENT]] PATH:OFFSET [FETCHARGS]  : Set a return uprobe (uretprobe)
-:[GRP/][EVENT]                             : Clear uprobe event

PATH:   Path to executable or library
OFFSET: Byte offset of probe point in the file
```

### Fetching Arguments

Uprobes can fetch data from:

| Syntax | Description |
|--------|-------------|
| `%REG` | Fetch register value |
| `@ADDR` | Fetch memory at address (must be in userspace) |
| `@+OFFSET` | Fetch memory at offset from probed file |
| `$stackN` | Fetch Nth stack entry |
| `$retval` | Fetch return value (uretprobe only) |
| `$comm` | Current task name |
| `+OFFS(FETCHARG)` | Fetch at offset from another fetcharg |
| `\IMM` | Store an immediate value |

Supported types: `u8/u16/u32/u64`, `s8/s16/s32/s64`, `x8/x16/x32/x64`, `string`, and bitfields (`b<width>@<offset>/<container>`).

### Uprobe Example: Tracing bash

```bash
# Find offset of zfree in /bin/zsh
cat /proc/$(pgrep zsh)/maps | grep /bin/zsh | grep r-xp
# 00400000-0048a000 r-xp 00000000 08:03 130904 /bin/zsh

objdump -T /bin/zsh | grep zfree
# 0000000000446420 g DF .text  0000000000000012 Base zfree

# Offset = 0x46420 (function offset in file)
echo 'p:zfree_entry /bin/zsh:0x46420 %ip %ax' > /sys/kernel/tracing/uprobe_events
echo 'r:zfree_exit /bin/zsh:0x46420 %ip %ax' >> /sys/kernel/tracing/uprobe_events

# Verify registered events
cat /sys/kernel/tracing/uprobe_events
# p:uprobes/zfree_entry /bin/zsh:0x00046420 arg1=%ip arg2=%ax
# r:uprobes/zfree_exit /bin/zsh:0x00046420 arg1=%ip arg2=%ax
```

### Event Profiling

```bash
# Check probe hit counts
cat /sys/kernel/tracing/uprobe_profile
# /bin/zsh  zfree_entry  1234
# /bin/zsh  zfree_exit   1234
```

### Dynamic Events Interface

Uprobes can also be registered via `/sys/kernel/tracing/dynamic_events` (unified interface for kprobes, uprobes, and tracepoints):

```bash
# Add via dynamic_events
echo 'p:uprobes/myprobe /bin/bash:0xa1b20' > /sys/kernel/tracing/dynamic_events

# Clear all dynamic events
echo > /sys/kernel/tracing/dynamic_events
```

### Uprobes vs kprobes

| Feature | kprobes | uprobes |
|---------|---------|--------|
| Target | Kernel functions | User-space executables/libraries |
| Offset | Kernel symbol address | File offset (from objdump) |
| Interface | `kprobe_events` | `uprobe_events` |
| Return probes | kretprobes | uretprobes |
| Permissions | Root only | Root only |
| Use case | Kernel debugging | Application tracing |

### Using Uprobes with bpftrace

bpftrace provides a convenient high-level interface for uprobes:

```bash
# Trace a user-space function
bpftrace -e 'uprobe:/bin/bash:readline { printf("readline: %s\n", ustack); }'

# Trace function entry and return
bpftrace -e '
uprobe:/lib/x86_64-linux-gnu/libc.so.6:malloc
{
    @start[tid] = nsecs;
}
uretprobe:/lib/x86_64-linux-gnu/libc.so.6:malloc
/@start[tid]/
{
    $dur = nsecs - @start[tid];
    @us = hist($dur / 1000);
    delete(@start[tid]);
}
'

# Count calls to a specific function
bpftrace -e 'uprobe:/usr/bin/python3:_PyEval_EvalFrameDefault { @[comm] = count(); }'
```

---

## Trace-cmd — User-Friendly Frontend

`trace-cmd` is a command-line tool that wraps ftrace, providing a much more convenient
interface.

### Installation

```bash
# Debian/Ubuntu
sudo apt install trace-cmd

# RHEL/Fedora
sudo dnf install trace-cmd

# Arch
sudo pacman -S trace-cmd
```

### Basic Usage

```bash
# Record a trace
sudo trace-cmd record -e sched_switch -e sched_wakeup sleep 1

# Read the trace
trace-cmd report | head -50

# Record function graph
sudo trace-cmd record -p function_graph -g do_sys_open sleep 1
trace-cmd report

# Record function tracer
sudo trace-cmd record -p function -l "sched_*" sleep 1
trace-cmd report

# Record with specific events
sudo trace-cmd record -e block:block_rq_issue -e block:block_rq_complete dd if=/dev/zero of=/tmp/test bs=1M count=100

# Record all scheduler events
sudo trace-cmd record -e sched sleep 5
trace-cmd report | head -100
```

### trace-cmd Example Session

```bash
$ sudo trace-cmd record -p function_graph -g do_sys_openat2 cat /dev/null
  Plugin 'function_graph'
  Hit Ctrl^C to stop recording

$ trace-cmd report | head -30
# CPU  DURATION                  FUNCTION CALLS
# |     |   |                     |   |   |   |
 1)               |  do_sys_openat2() {
 1)   0.452 us    |    getname();
 1)               |    do_filp_open() {
 1)   0.123 us    |      path_init();
 1)               |      link_path_walk() {
 1)   0.067 us    |        walk_component();
 1)   0.789 us    |      }
 1)   0.089 us    |      do_open();
 1)   2.123 us    |    }
 1)   0.078 us    |    putname();
 1)   3.456 us    |  }
```

### trace-cmd Stream (Live Tracing)

```bash
# Stream events in real-time
sudo trace-cmd stream -e sched_switch

# Stream with function graph
sudo trace-cmd stream -p function_graph -g do_sys_open

# Stream to file
sudo trace-cmd stream -e sched_switch > trace_output.txt
```

### trace-cmd Profile

```bash
# Profile function calls
sudo trace-cmd profile -p function -l "sched_*" sleep 5
trace-cmd report --profile

# Output:
#  Function                               Hit      Time        Avg         s^2
#  --------                               ---      ----        ---         ---
#  schedule                               5234    12.345ms     2.358us     1.234us
#  schedule_timeout                        123     1.234ms     10.032us    5.678us
#  __schedule                              5234    11.111ms     2.123us     0.987us
```

## Histograms (hist triggers)

ftrace histograms allow you to build in-kernel histograms of events without
exporting individual trace records.

### Basic Histogram

```bash
# Create a histogram of sched_switch events by next_comm
echo 'hist:key=next_comm:val=hitcount:sort=hitcount.desc' > \
    /sys/kernel/tracing/events/sched/sched_switch/trigger

# Enable the event
echo 1 > /sys/kernel/tracing/events/sched/sched_switch/enable

# Wait for data collection
sleep 5

# Read the histogram
cat /sys/kernel/tracing/events/sched/sched_switch/hist

# Output:
# { next_comm: bash                          } hitcount:        234
# { next_comm: kworker/0:1                   } hitcount:        156
# { next_comm: cat                           } hitcount:         89
# { next_comm: swapper/0                     } hitcount:         45
# Totals:
#   Hits: 524
#   Entries: 4
#   Dropped: 0

# Remove the trigger
echo '!hist:key=next_comm:val=hitcount:sort=hitcount.desc' > \
    /sys/kernel/tracing/events/sched/sched_switch/trigger
```

### Advanced Histograms

```bash
# Histogram with multiple keys
echo 'hist:key=next_comm,next_pid:val=hitcount' > \
    /sys/kernel/tracing/events/sched/sched_switch/trigger

# Histogram with latency measurement
echo 'hist:key=next_comm:val=lat:lat=hitcount' > \
    /sys/kernel/tracing/events/sched/sched_wakeup/trigger

# Histogram with buckets (log2)
echo 'hist:key=bytes_req:val=hitcount:buckets=8' > \
    /sys/kernel/tracing/events/kmem/kmalloc/trigger

# Conditional histogram
echo 'hist:key=next_comm:val=hitcount:if prev_pid==1234' > \
    /sys/kernel/tracing/events/sched/sched_switch/trigger

# Histogram with timestamps
echo 'hist:key=next_comm:val=ts0:ts0=common_timestamp.usecs' > \
    /sys/kernel/tracing/events/sched/sched_switch/trigger
```

## trace_marker — User-Space Annotations

`trace_marker` allows user-space programs to write messages into the kernel trace
buffer, enabling correlation of user events with kernel activity.

```bash
# Write a marker
echo "Starting computation" > /sys/kernel/tracing/trace_marker

# In a program:
# fd = open("/sys/kernel/tracing/trace_marker", O_WRONLY);
# write(fd, "checkpoint: data loaded\n", 24);
```

### Example: Correlating User and Kernel Events

```bash
# Enable scheduler events
echo 1 > /sys/kernel/tracing/events/sched/sched_switch/enable
echo function_graph > /sys/kernel/tracing/current_tracer
echo 1 > /sys/kernel/tracing/tracing_on

# Write markers from user space
echo "=== START ===" > /sys/kernel/tracing/trace_marker
./myprogram
echo "=== END ===" > /sys/kernel/tracing/trace_marker

echo 0 > /sys/kernel/tracing/tracing_on
cat /sys/kernel/tracing/trace | grep -A5 -B5 "START\|END"
```

## Trace Instances

Trace instances create separate trace buffers, allowing independent tracing
of different subsystems.

```bash
# Create an instance
sudo mkdir /sys/kernel/tracing/instances/myinstance

# Configure the instance
echo function_graph > /sys/kernel/tracing/instances/myinstance/current_tracer
echo sched_switch > /sys/kernel/tracing/instances/myinstance/set_event
echo 1 > /sys/kernel/tracing/instances/myinstance/tracing_on

# Read the instance trace
cat /sys/kernel/tracing/instances/myinstance/trace

# Remove the instance
sudo rmdir /sys/kernel/tracing/instances/myinstance
```

## KernelShark — GUI Visualization

KernelShark is a graphical front-end for ftrace traces.

```bash
# Install
sudo apt install kernelshark

# Record a trace
sudo trace-cmd record -e sched -e block sleep 5

# Open in KernelShark
kernelshark trace.dat
```

KernelShark provides:
- Timeline view of all CPUs
- Per-task timelines
- Event filtering
- Function graph visualization
- Latency markers
- Search and bookmarks

## Ftrace Tracers Reference

| Tracer | Description |
|--------|-------------|
| `nop` | No tracing (default) |
| `function` | Trace kernel function calls |
| `function_graph` | Hierarchical function call graph with timing |
| `wakeup` | Trace task wakeup latency (max) |
| `wakeup_rt` | Trace RT task wakeup latency |
| `preemptoff` | Trace preemption disabled regions |
| `irqsoff` | Trace interrupts disabled regions |
| `preemptirqsoff` | Combine preemptoff and irqsoff |
| `blk` | Block I/O tracing |
| `mmiotrace` | Memory-mapped I/O tracing |
| `hwlat` | Hardware latency detection |

## Best Practices

1. **Use `trace-cmd` instead of raw tracefs** — it handles setup/teardown cleanly
2. **Use instances for parallel traces** — isolate different trace targets
3. **Use histograms for statistics** — avoid flooding the trace buffer with individual events
4. **Filter aggressively** — ftrace can generate massive amounts of data
5. **Use function_graph for timing** — function tracer only shows call frequency
6. **Use trace_marker for correlation** — correlate user-space actions with kernel events
7. **Save traces with `trace-cmd record`** — for later analysis and sharing
8. **Use KernelShark for visualization** — timelines are easier to read than text

## ftrace Key Files (from docs.kernel.org)

The kernel documentation at `docs.kernel.org/trace/ftrace.html` provides a comprehensive reference for all ftrace control files. Here are the most important ones:

### Control and Output Files

| File | Description |
|------|-------------|
| `current_tracer` | Set/display the active tracer. Changing it clears the ring buffer. |
| `available_tracers` | List tracers compiled into the kernel. |
| `tracing_on` | Enable/disable writing to the ring buffer (1/0). Does not stop tracing overhead. |
| `trace` | Read the trace buffer (static, non-consuming). Use `O_TRUNC` to clear. |
| `trace_pipe` | Read and consume trace events (blocking, sequential). Unlike `trace`, each read consumes data. |
| `trace_options` | Control output format (timestamps, stack traces, etc.). |
| `options/` | Directory with per-option files (write 1/0 to enable/disable). |
| `tracing_max_latency` | Record max latency. New max only recorded if greater than this value (µs). |
| `tracing_thresh` | Only record latency traces when latency exceeds this threshold (µs). |

### Buffer Configuration

| File | Description |
|------|-------------|
| `buffer_size_kb` | Per-CPU ring buffer size (in KB). Displayed per-CPU if sizes differ. |
| `buffer_total_size_kb` | Total combined size of all CPU buffers. |
| `buffer_subbuf_size_kb` | Sub-buffer size. Events cannot exceed sub-buffer size. Changing it stops tracing and discards data. |
| `buffer_percent` | Watermark for waking blocked readers (0=any data, 50=half full, 100=completely full). |
| `free_buffer` | On close, ring buffer is resized to minimum. Useful for cleanup. |

### Function Filtering

| File | Description |
|------|-------------|
| `set_ftrace_filter` | Limit function tracing to listed functions. Supports index numbers and wildcards. |
| `set_ftrace_notrace` | Exclude functions from tracing. Takes precedence over filter. |
| `set_ftrace_pid` | Trace only listed PIDs. With `function-fork` option, children inherit tracing. |
| `set_ftrace_notrace_pid` | Ignore listed PIDs. Takes precedence over `set_ftrace_pid`. |
| `set_event_pid` | Filter event tracing to listed PIDs. |
| `available_filter_functions` | List of all traceable functions. |

### Per-CPU Control

| File | Description |
|------|-------------|
| `tracing_cpumask` | Hex mask controlling which CPUs are traced. |
| `per_cpu/cpuN/` | Per-CPU directories with `trace`, `trace_pipe`, and `buffer_size_kb`. |

### Trace Options

Key options (set via `options/` directory or `trace_options` file):

| Option | Effect |
|--------|--------|
| `print-parent` | Show parent function in function tracer |
| `sym-offset` | Show symbol + offset instead of just symbol |
| `verbose` | Show detailed event format |
| `bin` | Binary output format |
| `stacktrace` | Include stack trace with each event |
| `trace_printk` | Allow `trace_printk()` output |
| `function-fork` | Children inherit parent's ftrace PID filter |

### Filter Commands

ftrace supports advanced filter commands:

```bash
# Enable an event and set a filter with a command
echo 'prev_pid == 1234' > /sys/kernel/tracing/events/sched/sched_switch/filter

# Enable a trigger (stacktrace on event)
echo 'stacktrace' > /sys/kernel/tracing/events/sched/sched_switch/trigger

# Conditional traceoff (stop tracing when condition met)
echo 'traceoff:prev_pid==1234' > /sys/kernel/tracing/events/sched/sched_switch/trigger

# Snapshot trigger (take snapshot on event)
echo 'snapshot:prev_pid==1234' > /sys/kernel/tracing/events/sched/sched_switch/trigger
```

## Event Tracing Reference

The kernel documentation at `docs.kernel.org/trace/events.html` provides comprehensive coverage of the event tracing infrastructure. Here are the key details beyond what's covered in the Event Tracing section above.

### Event Format Files

Every trace event has a `format` file describing each field. This is essential for parsing binary traces and writing filters:

```bash
cat /sys/kernel/tracing/events/sched/sched_switch/format
# name: sched_switch
# ID: 283
# format:
#   field:unsigned short common_type; offset:0; size:2;
#   field:unsigned char common_flags; offset:2; size:1;
#   field:unsigned char common_preempt_count; offset:3; size:1;
#   field:int common_pid; offset:4; size:4;
#   field:int common_tgid; offset:8; size:4;
#   field:char prev_comm[16]; offset:12; size:16;
#   field:pid_t prev_pid; offset:28; size:4;
#   field:int prev_prio; offset:32; size:4;
#   field:long prev_state; offset:36; size:8;
#   field:char next_comm[16]; offset:44; size:16;
#   field:pid_t next_pid; offset:60; size:4;
#   field:int next_prio; offset:64; size:4;
```

### Advanced Event Filtering

Event filters support rich expressions:

```bash
# Numeric operators: ==, !=, <, <=, >, >=, &
# String operators: ==, !=, ~ (glob)

# Filter by PID and CPU
echo "prev_pid == 1234 || next_pid == 1234" > /sys/kernel/tracing/events/sched/sched_switch/filter

# String glob matching
echo 'prev_comm ~ "*sh"' > /sys/kernel/tracing/events/sched/sched_switch/filter

# Filter user-space string pointers
echo 'filename.ustring ~ "password"' > /sys/kernel/tracing/events/syscalls/sys_enter_openat/filter

# Filter by function address
echo 'call_site == security_prepare_creds' > /sys/kernel/tracing/events/kmalloc/filter

# CpuMask filtering
echo 'target_cpu & CPUS{17-42}' > /sys/kernel/tracing/events/sched/sched_wakeup/filter
```

### Boot-Time Event Tracing

Enable events at boot for early-boot debugging:

```
# Kernel command line
trace_event=sched_switch,sched_wakeup
trace_event=block:*  # All block subsystem events
```

### Trigger Actions

Events can trigger actions when matched:

```bash
# Stacktrace on event
echo 'stacktrace' > /sys/kernel/tracing/events/sched/sched_switch/trigger

# Snapshot on event
echo 'snapshot:prev_pid==1234' > /sys/kernel/tracing/events/sched/sched_switch/trigger

# Stop tracing when condition met
echo 'traceoff:prev_pid==1234' > /sys/kernel/tracing/events/sched/sched_switch/trigger

# Enable hist trigger for histogram collection
echo 'hist:key=next_comm:val=hitcount:sort=hitcount.desc' > /sys/kernel/tracing/events/sched/sched_switch/trigger

# Remove trigger
echo '!stacktrace' > /sys/kernel/tracing/events/sched/sched_switch/trigger
```

### Event Subsystems

Common subsystems and their events:

| Subsystem | Key Events | Purpose |
|-----------|-----------|--------|
| `sched` | `sched_switch`, `sched_wakeup`, `sched_process_exec` | Scheduler activity |
| `block` | `block_rq_issue`, `block_rq_complete` | Block I/O |
| `ext4` | `ext4_da_write_begin`, `ext4_es_lookup_extent` | ext4 filesystem |
| `kmem` | `kmalloc`, `kfree`, `mm_page_alloc` | Kernel memory allocation |
| `net` | `net_dev_xmit`, `netif_receive_skb` | Network packets |
| `irq` | `irq_handler_entry`, `softirq_entry` | Interrupt handling |
| `syscalls` | `sys_enter_*`, `sys_exit_*` | System calls |

## hwlat_detector — Hardware Latency Detector

The `hwlat_detector` is a special-purpose ftrace tracer that detects large system latencies caused by hardware or firmware behavior, independent of Linux itself. From the kernel documentation at `docs.kernel.org/trace/hwlat_detector.html`:

> *"The code was developed originally to detect SMIs (System Management Interrupts) on x86 systems, however there is nothing x86 specific about this patchset."*

SMIs are not serviced by the Linux kernel — they are set up and serviced by BIOS code, usually for thermal management and fan control. Sometimes SMI handlers spend an inordinate amount of time (measured in milliseconds), which is catastrophic for latency-sensitive workloads.

### How It Works

The hwlat detector works by:
1. **Hogging a CPU** with interrupts disabled for a configurable period
2. **Polling the CPU Time Stamp Counter (TSC)** continuously
3. **Looking for gaps** in the TSC data — any gap indicates the polling was interrupted by an SMI or hardware hiccup

Since interrupts are disabled during polling, only an SMI, NMI, or hardware event could cause a gap.

### Usage

```bash
# Enable the hwlat detector
$ echo hwlat > /sys/kernel/tracing/current_tracer

# Set the threshold (µs) — only report latencies above this
$ echo 10 > /sys/kernel/tracing/tracing_thresh

# Configure the detector
$ echo 500000 > /sys/kernel/tracing/hwlat_detector/width    # Spin time (µs)
$ echo 1000000 > /sys/kernel/tracing/hwlat_detector/window  # Total period (µs)

# Read detected latencies
$ cat /sys/kernel/tracing/trace
```

Default configuration: `width=500000` (500ms spin) and `window=1000000` (1s period). The detector spins for 500ms, sleeps for 500ms, and repeats. Minimum sleep between periods is 1ms.

### Configuration Files

| File | Description |
|------|-------------|
| `hwlat_detector/width` | Time to spin with CPUs held (µs) |
| `hwlat_detector/window` | Total sampling period (µs) |
| `hwlat_detector/mode` | Thread migration mode |
| `tracing_thresh` | Minimum latency to report (µs, default 10) |
| `tracing_max_latency` | Maximum observed hardware latency (µs) |
| `tracing_cpumask` | CPUs to move the hwlat thread across |

### Thread Modes

The detector thread can migrate across CPUs in different modes:

- **`none`**: Do not force migration
- **`round-robin`**: Migrate across CPUs in `tracing_cpumask` each window (default)
- **`per-cpu`**: Create one thread per CPU in `tracing_cpumask`

```bash
# Set per-CPU mode
$ echo per-cpu > /sys/kernel/tracing/hwlat_detector/mode

# Restrict to specific CPUs
$ echo 0-3 > /sys/kernel/tracing/tracing_cpumask
```

### Important Notes

- **Never use in production** — it disables interrupts on a CPU for extended periods
- Intended for manual diagnosis of hardware/firmware latency issues
- If `tracing_thresh` was 0 when hwlat was started, it resets to 0 when another tracer takes over
- The last `tracing_thresh` value is saved and restored if hwlat is restarted

For full details, see [Hardware Latency Detector — docs.kernel.org](https://docs.kernel.org/trace/hwlat_detector.html).

## Boot-Time Tracing

ftrace supports tracing during kernel boot via kernel command-line parameters. This is essential for debugging early-boot issues that occur before userspace is available and tracefs can be mounted.

### Kernel Command-Line Parameters

```bash
# Enable specific events at boot
trace_event=sched_switch,sched_wakeup
trace_event=block:*                    # All block subsystem events
trace_event=irq:*                      # All IRQ events

# Set a tracer at boot
trace_buf_size=4M                      # Ring buffer size per CPU
trace_options=overwrite                # Enable overwrite option

# Function tracing at boot
ftrace=function                        # Enable function tracer
ftrace_filter=do_sys_open*             # Filter to specific functions
ftrace_notrace=*lock*                  # Exclude lock functions

# Boot-time kprobe events
kprobe_event=p:myprobe,do_sys_open,filename=%si

# Combine for comprehensive boot tracing
trace_event=sched_switch,sched_wakeup,irq:* ftrace_filter=sched_*
```

### Boot Trace Analysis Workflow

```bash
# 1. Add trace parameters to kernel command line (GRUB)
# Edit /etc/default/grub:
# GRUB_CMDLINE_LINUX="trace_event=sched_switch trace_buf_size=8M"

# 2. Boot with modified command line
# sudo update-grub && reboot

# 3. After boot, read the trace buffer
cat /sys/kernel/tracing/trace > /tmp/boot_trace.txt

# 4. Or use trace-cmd to read
cat /sys/kernel/tracing/per_cpu/cpu0/trace > /tmp/cpu0_boot_trace.txt

# 5. Analyze with KernelShark
kernelshark /tmp/boot_trace.txt
```

### Early Boot Considerations

- **Buffer size**: Set `trace_buf_size` large enough (default 1KB per CPU is too small for boot tracing; use 4M-16M)
- **Overwrite mode**: Use `trace_options=overwrite` to keep the most recent events if the buffer fills
- **Function tracing overhead**: Boot-time function tracing adds significant overhead; use `ftrace_filter` to limit scope
- **`trace_event` vs `ftrace`**: `trace_event` enables specific tracepoints (lower overhead); `ftrace=function` traces all function calls (very verbose)
- **Boot delay measurement**: Use `initcall_debug` alongside tracing to correlate init function timing with scheduler events

### Example: Tracing Boot-Time Scheduler Activity

```bash
# Kernel command line:
trace_event=sched_switch,sched_wakeup,sched_process_fork
trace_buf_size=8M
trace_options=overwrite

# After boot:
cat /sys/kernel/tracing/trace | head -100
#           <idle>-0     [000]  0.000000: sched_switch: prev_comm=swapper/0 ...
#           <idle>-0     [000]  0.001234: sched_wakeup: comm=init pid=1 ...
#              init-1     [000]  0.002345: sched_process_fork: comm=init pid=1 child_comm=... child_pid=2
```

### Example: Tracing Initcall Timing

```bash
# Kernel command line:
initcall_debug
trace_event=initcall:* ftrace_filter=*_initcall*
trace_buf_size=4M

# After boot, correlate initcall durations with kernel log
dmesg | grep initcall
# [    0.123456] calling  pci_driver_init+0x0/0x100 @ 1
# [    0.125678] initcall pci_driver_init+0x0/0x100 returned 0 after 2134 usecs
```

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [ftrace - Function Tracer — docs.kernel.org](https://docs.kernel.org/trace/ftrace.html) — Official ftrace documentation (comprehensive file reference, options, filter commands)
- [Kprobe-based Event Tracing — docs.kernel.org](https://docs.kernel.org/trace/kprobetrace.html) — Official kprobe event tracing reference
- [ftrace Documentation](https://www.kernel.org/doc/html/latest/trace/ftrace.html)
- [trace-cmd man page](https://man7.org/linux/man-pages/man1/trace-cmd.1.html)
- [KernelShark](https://kernelshark.org/)
- [Steven Rostedt's ftrace tutorial](https://lwn.net/Articles/370423/)
- [Kernel documentation: Kprobes](https://docs.kernel.org/trace/kprobes.html) — Full kprobe/kretprobe reference and internals
- [Brendan Gregg's ftrace page](https://www.brendangregg.com/blog/2014-07-01/perf-ftrace.html)
- [Hardware Latency Detector — docs.kernel.org](https://docs.kernel.org/trace/hwlat_detector.html)
- [Event Tracing Documentation](https://docs.kernel.org/trace/events.html) — Official event tracing reference (format files, filters, triggers, boot options)
- [Boot-time tracing](https://docs.kernel.org/trace/boottime.html) — Kernel command-line trace parameters for early-boot debugging
- [Uprobe-tracer documentation — docs.kernel.org](https://docs.kernel.org/trace/uprobetracer.html) — User-space uprobe-based event tracing

## Related Topics

- [eBPF](./ebpf.md) — Programmable tracing with BPF
- [perf](./perf.md) — Sampling-based profiling
- [Kernel Debugging](./kernel-debugging.md) — KGDB, KDB, crash
- [GDB](./gdb.md) — Source-level debugging
