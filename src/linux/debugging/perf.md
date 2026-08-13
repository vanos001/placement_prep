# perf — Linux Performance Profiling

## Introduction

`perf` (Performance Counters for Linux) is the standard Linux profiling and tracing tool.
It provides a framework for hardware and software performance counters, enabling deep
analysis of CPU behavior, cache misses, branch mispredictions, context switches, and
much more. Unlike strace, perf has extremely low overhead because it uses hardware
Performance Monitoring Units (PMUs) and kernel-level sampling.

perf is the Swiss Army knife of Linux performance analysis. It can do statistical
profiling, trace events, measure hardware counters, generate flame graphs, and
record/replay execution. Brendan Gregg has called it "the best tool for the job"
for CPU profiling on Linux.

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  User Space                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │perf stat │  │perf record│  │perf trace    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │          │
└───────┼──────────────┼───────────────┼──────────┘
        │              │               │
   ┌────▼──────────────▼───────────────▼─────────┐
   │              perf_event_open()               │
   │         (system call interface)              │
   └──────────────────┬──────────────────────────┘
                      │
   ┌──────────────────▼──────────────────────────┐
   │              perf_events subsystem            │
   │  ┌─────────┐  ┌──────────┐  ┌────────────┐ │
   │  │ HW PMU  │  │ SW Events│  │ Tracepoints│ │
   │  │ Counters│  │          │  │            │ │
   │  └─────────┘  └──────────┘  └────────────┘ │
   └──────────────────┬──────────────────────────┘
                      │
   ┌──────────────────▼──────────────────────────┐
   │           Hardware / Kernel                  │
   │  ┌─────────┐  ┌──────────┐  ┌────────────┐ │
   │  │ CPU PMU │  │  Cache   │  │ Branch     │ │
   │  │ (Intel/ │  │ Subsystem│  │ Predictor  │ │
   │  │  AMD)   │  │          │  │            │ │
   │  └─────────┘  └──────────┘  └────────────┘ │
   └─────────────────────────────────────────────┘
```

## Prerequisites

```bash
# Install perf
# Debian/Ubuntu:
sudo apt install linux-tools-$(uname -r) linux-tools-common

# RHEL/Fedora:
sudo dnf install perf

# Arch:
sudo pacman -S perf

# Verify installation
perf version

# Check available events
perf list
```

### Kernel Configuration

Some features require specific kernel config options:

```bash
# Check if perf_event support is available
ls /proc/sys/kernel/perf_event_paranoid
cat /proc/sys/kernel/perf_event_paranoid
# 0 = root-only, 1 = user access, 2 = no access, -1 = all access

# For unprivileged users (development machines)
sudo sysctl -w kernel.perf_event_paranoid=-1

# Allow kernel symbol resolution
sudo sysctl -w kernel.kptr_restrict=0
```

## perf stat — Statistical Counting

`perf stat` counts events without recording samples. It's the fastest way to get
a performance overview.

### Basic Usage

```bash
# Count default events for a command
perf stat ./myprogram

# Count events for a running process
perf stat -p 1234 sleep 5

# Count events system-wide
perf stat -a sleep 5

# Repeat measurements for statistical confidence
perf stat -r 5 ./myprogram
```

### Example Output

```
$ perf stat ./myprogram

 Performance counter stats for './myprogram':

          1,234.56 msec  task-clock                #    0.998 CPUs utilized
               123      context-switches           #   99.630 /sec
                 5      cpu-migrations             #    4.050 /sec
             8,456      page-faults                #    6.850 K/sec
     4,567,890,123      cycles                     #    3.700 GHz
     2,345,678,901      instructions               #    0.51  insn per cycle
       456,789,012      branches                   #  370.005 M/sec
        12,345,678      branch-misses              #    2.70% of all branches
       234,567,890      cache-references           #  190.000 M/sec
        23,456,789      cache-misses               #   10.000% of all cache refs

       1.236789012 seconds time elapsed
       1.123456789 seconds user
       0.112345678 seconds sys
```

Key metrics:
- **insn per cycle (IPC)**: < 1.0 often indicates memory stalls
- **branch-misses**: > 5% suggests poor branch prediction
- **cache-misses**: > 5% of cache-references suggests memory-bound code
- **context-switches**: High counts suggest excessive blocking

### Selecting Events

```bash
# List all available events
perf list

# List hardware events
perf list hw

# List software events
perf list sw

# List cache events
perf list cache

# Count specific events
perf stat -e cycles,instructions,cache-misses,cache-references ./myprogram

# Count custom events
perf stat -e L1-dcache-load-misses,L1-dcache-loads ./myprogram

# Count with group (events counted simultaneously)
perf stat -e '{cycles,instructions}' -e '{cache-references,cache-misses}' ./myprogram

# Multiplexing events (when more events than counters)
perf stat -e cycles:instructions:cache-misses ./myprogram
```

### Common Event Groups

```bash
# Frontend vs Backend bound (Intel)
perf stat -e '{idq_uops_not_delivered.core,stalled_cycles_frontend}' \
         -e '{cpu_clk_unhalted.thread,stalled_cycles_backend}' ./myprogram

# Memory hierarchy
perf stat -e L1-dcache-load-misses,L1-dcache-loads \
         -e LLC-load-misses,LLC-loads \
         -e dTLB-load-misses,dTLB-loads ./myprogram

# Branch prediction
perf stat -e branch-misses,branches \
         -e branch-load-misses,branch-loads ./myprogram
```

## perf record — Sampling

`perf record` captures samples at regular intervals, recording the instruction pointer
and call stack for later analysis.

### Basic Usage

```bash
# Record with default settings (cycles event, 4000 Hz)
perf record ./myprogram

# Record with custom frequency
perf record -F 999 ./myprogram       # 999 Hz (avoid round numbers)

# Record with call graph
perf record -g ./myprogram           # DWARF-based call graph

# Record with frame pointers (if available)
perf record --call-graph fp ./myprogram

# Record with LBR (Last Branch Record) — Intel only
perf record --call-graph lbr ./myprogram

# Record system-wide
perf record -a -g sleep 10

# Record specific events
perf record -e cache-misses -g ./myprogram

# Record specific process
perf record -p 1234 -g sleep 10

# Record with CPU filtering
perf record -C 0,1 ./myprogram       # Only CPUs 0 and 1

# Record with instruction pointer sampling
perf record -e instructions -c 10000 ./myprogram  # Every 10000 instructions
```

### Advanced Recording Options

```bash
# Record with dwarf callgraph (best for optimized code)
perf record -g --call-graph dwarf,16384 ./myprogram
# 16384 = stack dump size (default 8192, increase for deep stacks)

# Record with both user and kernel callchains
perf record -g -a ./myprogram

# Record with timestamp
perf record -g --timestamp ./myprogram

# Record with sample weight (for memory access profiling)
perf record -e ldlat-loads --weight ./myprogram

# Record with BPF-based stack traces
perf record -g --bpf-event ./myprogram

# Record specific tracepoints with call stacks
perf record -e 'sched:sched_switch' -g -a sleep 5

# Record with switch-output (split output on signal)
perf record --switch-output -a sleep 60
# Creates perf.data.1, perf.data.2, etc.

# Record with compression
perf record -z ./myprogram

# Record with branch sampling (Intel LBR)
perf record -b ./myprogram  # Record taken branches

# Record with Intel Processor Trace (full execution trace)
perf record -e intel_pt// -a sleep 5
```

### Output File

```bash
# Default output: perf.data
ls -la perf.data

# Custom output file
perf record -o myprofile.data ./myprogram

# Compress output
perf record -z ./myprogram
```

## perf report — Analyzing Samples

```bash
# Interactive report
perf report

# Report from specific file
perf report -i myprofile.data

# Text output (non-interactive)
perf report --stdio

# Sort by different keys
perf report --sort=dso                    # By shared library
perf report --sort=symbol                 # By function
perf report --sort=comm                   # By process name
perf report --sort=pid                    # By PID

# Show call graph
perf report --call-graph

# Show with source line info
perf report --stdio -g none,0,caller,count
```

### Interactive Report Navigation

In the interactive `perf report`:

```
Overhead  Shared Object      Symbol
  35.00%  myprogram          [.] compute_matrix
  20.00%  libc.so.6          [.] __memcpy_avx2
  15.00%  myprogram          [.] main
  10.00%  libc.so.6          [.] malloc
   8.00%  myprogram          [.] free_matrix
   5.00%  [kernel]           [k] clear_page
   4.00%  myprogram          [.] init_matrix
   3.00%  libc.so.6          [.] free
```

- Press `Enter` on a symbol to see annotated source/assembly
- Press `a` to annotate a function (show per-line overhead)
- Press `/` to search for a symbol
- Press `?` for help

### Annotated Source

```bash
# Generate annotated source
perf annotate --stdio compute_matrix

# Output:
#  Percent |  Source code & Disassembly
# ---------+--------------------------
#          :  int compute_matrix(double *A, double *B, double *C, int n) {
#          :  {
#    5.23 :    mov    (%rdi),%rax
#   30.15 :    vmulpd (%rsi),%ymm0,%ymm1     ← hot instruction
#   15.40 :    vaddpd (%rdx),%ymm1,%ymm2
#    8.12 :    vmovupd %ymm2,(%rdx)
#          :  }
```

### Report Filtering and Aggregation

```bash
# Filter by symbol
perf report --stdio --symbol-filter=compute_matrix

# Filter by DSO (shared library)
perf report --stdio --dso=libc.so.6

# Filter by thread
perf report --stdio --tid=1234

# Filter by CPU
perf report --stdio --cpu=0

# Show only kernel symbols
perf report --stdio --kallsyms=/proc/kallsyms

# Aggregate by parent function
perf report --stdio --parent=some_function

# Show percentage relative to a specific function
perf report --stdio --symbol-filter=main -g fractal,0.5,caller

# Output as call tree
perf report --stdio --call-graph callee

# Output as flat profile with call graph info
perf report --stdio -g none,0,caller,count
```

## Flame Graphs

Flame graphs visualize call stacks, making it easy to identify performance bottlenecks.
They were invented by Brendan Gregg.

### Generating Flame Graphs

```bash
# Record with call graph
perf record -g -F 999 ./myprogram

# Generate flame graph (requires FlameGraph tools)
git clone https://github.com/brendangregg/FlameGraph.git
perf script | ./FlameGraph/stackcollapse-perf.pl | ./FlameGraph/flamegraph.pl > flame.svg

# Or using perf's built-in flame graph support (newer kernels)
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Differential flame graph (compare two profiles)
# Record baseline
perf record -g -F 999 -o perf-baseline.data ./myprogram_optimized
perf script -i perf-baseline.data | stackcollapse-perf.pl > baseline.folded

# Record optimized
perf record -g -F 999 -o perf-optimized.data ./myprogram_optimized
perf script -i perf-optimized.data | stackcollapse-perf.pl > optimized.folded

# Generate differential
difffolded.pl baseline.folded optimized.folded | flamegraph.pl > diff.svg
```

### Flame Graph Anatomy

```
Width = percentage of time in that call stack
Height = call depth (deeper = more nested)

            ┌──────────────────────────────────────┐
            │              main (100%)              │
            ├──────────────┬───────────────────────┤
            │  compute()   │    io_read()          │
            │   (70%)      │     (30%)             │
     ┌──────┴──────┬──────┴───┬──────────┐
     │ matrix_mul()│ add_row()│ read()   │
     │   (60%)     │  (10%)   │ (30%)    │
  ┌──┴──┐    ┌────┴───┐
  │load()│    │memcpy()│
  │(40%) │    │ (10%)  │
  └──────┘    └────────┘

Narrow = fast, Wide = hot, Color = random (or differential: red=more, blue=less)
```

### Interpreting Flame Graphs

- **Wide bars**: Functions consuming the most CPU time
- **Deep stacks**: Deeply nested call chains (potential for optimization)
- **Plateaus**: Functions where time is spent (leaf functions)
- **In differential mode**: Red = more samples, Blue = fewer samples

## perf trace — System Call Tracing

`perf trace` is like strace but with much lower overhead. It uses the `raw_syscalls`
tracepoint instead of ptrace.

```bash
# Trace system calls
perf trace ./myprogram

# Trace with call stacks
perf trace -g ./myprogram

# Trace specific syscalls
perf trace -e read,write ./myprogram

# Trace with duration filter
perf trace --duration 10 ./myprogram  # Only syscalls > 10ms

# Trace a specific process
perf trace -p 1234

# Summary statistics
perf trace -s ./myprogram
```

### perf trace Summary Output

```
$ perf trace -s ./myprogram
myprogram (12345), 2345 events, 99.8%

   syscall            calls  errors  total       min       avg       max      stddev
                                     (msec)    (msec)    (msec)    (msec)        (%)
   --------------- --------  ------ -------- --------- --------- ---------  --------
   read              10000      0    123.456     0.001     0.012     1.234     15.00
   write              5000      0     67.890     0.002     0.013     0.987     12.00
   open               1000      0     12.345     0.005     0.012     0.500      8.00
   close              1000      0      1.234     0.001     0.001     0.010      2.00
   mmap                500      0      3.456     0.002     0.006     0.100      5.00
```

## Hardware Counters and PMU

### Performance Monitoring Unit (PMU)

Modern CPUs include a PMU with dedicated hardware counters that can count events
without any software overhead:

```
┌────────────────────────────────────────────┐
│                 CPU Core                    │
│  ┌─────────────────────────────────────┐  │
│  │  Pipeline                           │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐  │  │
│  │  │Fetch│→│Decode│→│Exec │→│Write│  │  │
│  │  └─────┘ └─────┘ └─────┘ └─────┘  │  │
│  │      ↑         ↑        ↑          │  │
│  └──────┼─────────┼────────┼──────────┘  │
│         │         │        │              │
│  ┌──────▼─────────▼────────▼──────────┐  │
│  │  PMU Counters (4-8 per core)        │  │
│  │  ┌──────┐┌──────┐┌──────┐┌──────┐  │  │
│  │  │cycles││instr ││cache ││branch│  │  │
│  │  │      ││      ││miss  ││miss  │  │  │
│  │  └──────┘└──────┘└──────┘└──────┘  │  │
│  └─────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

### Key Hardware Events

| Event | Description | Good For |
|-------|-------------|----------|
| `cycles` | CPU clock cycles | Overall time |
| `instructions` | Retired instructions | IPC calculation |
| `cache-references` | Last-level cache accesses | Memory subsystem |
| `cache-misses` | LLC misses | Memory-bound detection |
| `branch-instructions` | Retired branches | Branch prediction |
| `branch-misses` | Mispredicted branches | Branch-heavy code |
| `L1-dcache-load-misses` | L1 data cache misses | Hot data analysis |
| `L1-icache-load-misses` | L1 instruction cache misses | Code size issues |
| `dTLB-load-misses` | Data TLB misses | Large working sets |
| `iTLB-load-misses` | Instruction TLB misses | Large code footprints |
| `stalled-cycles-frontend` | Frontend stalls | Fetch/decode bottleneck |
| `stalled-cycles-backend` | Backend stalls | Execution bottleneck |

### Intel-Specific Events

```bash
# UOPS delivered
perf stat -e idq_uops_not_delivered.core ./myprogram

# Memory bandwidth (Intel)
perf stat -e uncore_imc/cas_count_read/ ./myprogram

# Intel PT (Processor Trace) — full execution trace
perf record -e intel_pt// ./myprogram
perf script --itrace=i10us --ns
```

### AMD-Specific Events

```bash
# AMD IBS (Instruction-Based Sampling)
perf record -e ibs_op// ./myprogram
perf record -e ibs_fetch// ./myprogram

# AMD-specific cache events
perf stat -e ls_dmnd_fills_from_sys.lcl_l2 ./myprogram
```

## Advanced perf Features

### perf probe — Dynamic Tracing

Add custom tracepoints at any kernel or user function:

```bash
# Add a probe at kernel function
sudo perf probe --add do_sys_open

# Add a probe with arguments
sudo perf probe --add 'do_sys_open filename:string flags:%di'

# Add a probe at user function
perf probe -x ./myprogram --add 'compute_matrix:size'

# List probes
sudo perf probe -l

# Record with probe
sudo perf record -e probe:do_sys_open -aR sleep 1

# Remove probes
sudo perf probe --del do_sys_open
sudo perf probe --del -x ./myprogram compute_matrix
```

### perf bench — Kernel Benchmarks

```bash
# Sched scheduler benchmarks
perf bench sched messaging
perf bench sched pipe

# Memory benchmarks
perf bench mem memcpy
perf bench mem memset

# NUMA benchmarks
perf bench numa mem

# futex benchmarks
perf bench futex hash
perf bench futex wake
```

### perf top — Real-Time Profiling

```bash
# Real-time CPU profiling
sudo perf top

# With call graphs
sudo perf top -g

# Specific event
sudo perf top -e cache-misses

# Specific process
sudo perf top -p 1234
```

### perf kvm — Virtual Machine Profiling

```bash
# Record KVM guest
perf kvm stat record

# Report KVM events
perf kvm stat report

# Guest-side profiling
perf kvm --guest stat record
```

### perf lock — Lock Contention Analysis

```bash
# Record lock events
sudo perf lock record ./myprogram

# Report lock statistics
perf lock report

# Content
#              Name    acquired  contended  total wait (ns)   max wait (ns)
#   ──────────────── ────────── ────────── ───────────────── ──────────────
#   rwsem:map_lock        1000        123          1,234,567         98,765
#   mutex:global           500         45            456,789         12,345
```

### perf sched — Scheduler Analysis

```bash
# Record scheduler events
sudo perf sched record sleep 5

# Latency report
sudo perf sched latency

# Time histogram
sudo perf sched timehist

# Map of CPU usage
sudo perf sched map
```

### perf mem — Memory Access Profiling

```bash
# Record memory access patterns (Intel PEBS)
sudo perf mem record ./myprogram

# Report memory access
perf mem report --sort=mem,sym,dso

# NUMA analysis
perf mem report --sort=mem,sym --data-type
```

## Building from perf.data

```bash
# Record
perf record -g -F 999 ./myprogram

# View event list
perf script

# Convert to other formats
perf script --header > trace.txt
perf script --itrace=i10us -F time,comm,pid,tid,ip,sym > detailed.txt

# Generate histograms
perf report --stdio --sort=dso,symbol -g none
```

## Perf + eBPF Integration

Modern perf integrates with eBPF for advanced tracing:

```bash
# BPF-based latency histogram
sudo perf record -e 'syscalls:sys_enter_read' -aR sleep 5

# Using perf with BPF scripts
sudo perf record -e 'sched:sched_switch' -a --switch-output -g sleep 5
```

## Performance Analysis Methodology

### The USE Method (Brendan Gregg)

For every resource, check:
- **U**tilization: How busy is it?
- **S**aturation: Is work queuing up?
- **E**rrors: Are there any errors?

```bash
# CPU Utilization
perf stat -a -e cycles,instructions sleep 5

# CPU Saturation (context switches, migrations)
perf stat -a -e context-switches,cpu-migrations sleep 5

# Memory Saturation
perf stat -a -e cache-misses,LLC-load-misses sleep 5

# Disk I/O (via tracepoints)
perf stat -a -e 'block:block_rq_issue','block:block_rq_complete' sleep 5
```

### Top-Down Performance Analysis (Intel)

```
                    Pipeline Slots
                   ┌──────────────┐
                   │   Total      │
                   ├──────┬───────┤
             Frontend      Backend
             Bound          Bound
                   │              │
            ┌──────┴──┐    ┌─────┴────┐
            │Fetch    │    │Execution │
            │Bound    │    │Bound     │
            └─────────┘    └──────────┘

perf stat -M TopdownL1 ./myprogram
perf stat -M TopdownL2 ./myprogram
```

## Common perf Workflows

### Finding Hot Functions

```bash
perf record -g -F 999 ./myprogram
perf report --sort=symbol --stdio | head -30
```

### Finding Cache Misses

```bash
perf record -e cache-misses -g ./myprogram
perf report --stdio | head -30
```

### Finding Branch Mispredictions

```bash
perf record -e branch-misses -g ./myprogram
perf report --stdio | head -30
```

### Comparing Optimizations

```bash
# Baseline
perf stat -r 5 ./myprogram_old
perf record -g -o old.data ./myprogram_old

# Optimized
perf stat -r 5 ./myprogram_new
perf record -g -o new.data ./myprogram_new

# Compare
perf diff old.data new.data
```

## Best Practices

1. **Use `-F 999` not `-F 1000`** — avoid aliasing with periodic operations
2. **Use `-g` for call graphs** — without it, you only see leaf functions
3. **Run multiple times with `-r`** — for statistical confidence
4. **Disable turbo boost for stable measurements** — `echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo`
5. **Pin CPU frequency** — `cpupower frequency-set -f 3.0GHz`
6. **Use `perf stat` before `perf record`** — get the big picture first
7. **Generate flame graphs** — visual analysis is faster than reading tables
8. **Use `perf trace` instead of `strace`** — lower overhead for syscall tracing

## References

- [The Linux Kernel Documentation](https://docs.kernel.org/)
- [LWN.net - Linux and free software news](https://lwn.net/)
- [GNU Project Documentation](https://www.gnu.org/doc/doc.html)
- [GNU Manuals](https://www.gnu.org/manual/manual.html)
- [Free Software Directory](https://directory.fsf.org/wiki/Main_Page)
- [Planet GNU](https://planet.gnu.org/)
- [Free Software Books](https://www.gnu.org/doc/other-free-books.html)

- [perf Wiki](https://perf.wiki.kernel.org/index.php/Main_Page)
- [Brendan Gregg's perf page](https://www.brendangregg.com/perf.html)
- [perf Examples](https://www.brendangregg.com/perf.html)
- [Intel PMU](https://perfmon-events.intel.com/)
- [FlameGraph](https://github.com/brendangregg/FlameGraph)
- [Linux perf tutorial](https://developer.android.com/topic/performance/tracing)

## Related Topics

- [eBPF](./ebpf.md) — Programmable kernel tracing and observability
- [ftrace](./ftrace.md) — Kernel function tracing
- [strace](./strace-ltrace.md) — System call tracing (higher overhead)
- [GDB](./gdb.md) — Source-level debugging and rr record/replay
