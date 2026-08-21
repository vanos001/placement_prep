# Flame Graphs

A flame graph is a visualization of profiled software, showing where CPU time is spent as a hierarchical "flame" of stacked function calls. Introduced by Brendan Gregg at Netflix in 2011, flame graphs have become the standard visualization for CPU profiles, lock contention profiles, and memory allocation profiles. This page covers the structure, the variant types (CPU, off-CPU, memory, differential), and the production tooling (perf, async-profiler, eBPF).

## The Structure

A flame graph is a stacked bar chart of call stacks:

```text
          ┌─────────┐
          │   h()   │  ← top of stack (currently executing)
          ├─────────┤
          │   g()   │  ← called by h
          ├─────────┤
          │   f()   │  ← called by g
          ├─────────┤
          │  main() │  ← bottom of stack
          └─────────┘

Width = % of CPU time spent in this stack
```

Each box is a function. The width is proportional to the time spent in that function (including its callees). The vertical axis is the call stack depth; the top is the currently executing function.

A flame graph shows many call stacks side by side, with their widths summed:

```text
┌──────────────────────────────────────────────────────────────┐
│                       main()                                  │
├──────────────────────┬───────────────────────────────────────┤
│       parse()        │              route()                   │
├──────────┬───────────┴───────────────┬───────────────────────┤
│ read()  │  parse_json()              │  handle_request()      │
│         │                            │                        │
│         ├───────────────────────────┐│                       │
│         │  lex_token()              ││                       │
│         │  (hot path, this needs    ││                       │
│         │   optimization)            ││                       │
└─────────┴───────────────────────────┴┴───────────────────────┘
```

A wide bar at the top of the flame (like `lex_token()` in the example) is the "hot path" — the function that's called most often and where optimization will pay off most.

## Generating a Flame Graph

The general pipeline:

```text
1. Profile the application (sample the call stack N times per second).
2. Aggregate the samples into a "folded" format.
3. Render the folded data as an SVG flame graph.
```

### Step 1: Profiling

Multiple profilers produce different output formats:

**perf (Linux, system-wide)**:
```bash
# Sample at 999 Hz (avoid lockstep with the application's frequency)
perf record -F 999 -p <pid> -g -- sleep 30

# The -g flag records call graphs (DWARF-based by default).
# For frame-pointer-based (faster):
perf record -F 999 -p <pid> --call-graph fp -- sleep 30
```

**async-profiler (Java)**:
```bash
# Profile a Java process for 30 seconds
./asprof -d 30 -f profile.html <pid>

# The HTML output is an interactive flame graph.
```

**eBPF (bpftrace, modern alternative)**:
```bash
# Profile with stack traces
bpftrace -e 'profile:hz:99 { @[ustack] = count(); }' -p <pid>
```

### Step 2: Folding

For perf, the `stackcollapse` script converts raw perf data to folded:

```bash
# Convert perf.data to folded format
perf script | stackcollapse-perf.pl > out.folded

# out.folded contains lines like:
#   main;f;g;h 100
#   main;route;handle_request 50
```

Each line is a call stack (semicolon-separated) and a sample count.

### Step 3: Rendering

```bash
# Generate the SVG flame graph
flamegraph.pl out.folded > flame.svg
```

Open `flame.svg` in a browser; it's interactive (click to zoom, hover for details).

## Flame Graph Variants

### CPU Flame Graph (the original)

Shows on-CPU time — where the CPU was actively executing the application's instructions.

```bash
# perf record samples while the CPU is in user or kernel mode
perf record -F 999 -p <pid> -a -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > cpu.svg
```

Hot paths (wide bars) are where CPU optimization helps.

### Off-CPU Flame Graph

Shows off-CPU time — where the application was blocked on I/O, locks, or sleep.

```bash
# Use eBPF to trace sched_switch (when the task goes off-CPU)
bpftrace -e 'tracepoint:sched:sched_switch { @[ustack] = count(); }' -p <pid>
```

Off-CPU flame graphs reveal latency bottlenecks — long waits for database queries, locks, or filesystem I/O. The total time (off-CPU) often dominates over CPU time.

### Memory Flame Graph

Shows memory allocations — where the application allocates the most bytes.

```bash
# Use the heap profiler (jemalloc's jeprof, or gperftools)
LD_PRELOAD=libprofiler.so.0 CPUPROFILE=mem.prof ./myapp

# Generate a flame graph of allocations
jeprof --svg ./myapp mem.prof > mem.svg
```

Useful for finding memory leaks and high-memory allocations.

### Differential Flame Graph

Compares two profiles — typically before and after an optimization.

```bash
# Diff two folded files
difffolded.pl before.folded after.folded > diff.folded
flamegraph.pl diff.folded > diff.svg
```

The differential shows where time was added or removed. Red bars = regression (more time); green bars = improvement (less time).

## Production Use Cases

### Performance Regression Analysis

When a new commit slows down the application:

```bash
# Profile before the commit
git checkout HEAD~1
perf record -F 999 -p <pid> -g -- sleep 30
perf script | stackcollapse-perf.pl > before.folded

# Profile after the commit
git checkout HEAD
perf record -F 999 -p <pid> -g -- sleep 30
perf script | stackcollapse-perf.pl > after.folded

# Diff
difffolded.pl before.folded after.folded | flamegraph.pl > diff.svg
```

The diff shows the exact functions that got slower.

### Hot Path Identification

For a slow request, identify the hot path:

```bash
# Sample the request handler
perf record -F 999 -p <pid> -g -- sleep 30

# Generate the flame graph
perf script | stackcollapse-perf.pl | flamegraph.pl > hot.svg
```

The widest top-of-stack bar is the hot function. Optimize it first.

### Production Profiling at Scale

Continuous profiling with flame graphs:
- **Pixie**: eBPF-based, profiles all services in a Kubernetes cluster.
- **Parca**: continuous profiling with multi-language support.
- **Pyroscope**: continuous profiling with storage backend (S3).

These tools collect profiles continuously, aggregate them, and provide flame graphs for any time range.

## Production Tooling

### perf (Linux standard)

- Pros: kernel support, low overhead.
- Cons: requires `CAP_SYS_ADMIN` or `CAP_PERFMON`; frame-pointer-based stacks require `-fno-omit-frame-pointer` at compile time.

### async-profiler (Java)

- Pros: low overhead, integrates with HotSpot JVM.
- Cons: Java-only.

### eBPF (bpftrace, bcc)

- Pros: kernel-level, captures both user and kernel stacks, supports tracepoints and kprobes.
- Cons: requires root or specific capabilities; newer than perf.

### Language-Specific Profilers

- Python: `cProfile` + `pyprof2calltree` + `qcachegrind`. Or `py-spy` for sampling-based (no GIL issues).
- Go: `pprof` (built-in). Generates SVGs directly.
- Rust: `cargo flamegraph` (uses `perf` under the hood).

## Common Pitfalls

1. **Forgetting to compile with frame pointers.** Many distributions (especially C++ with `-O2`) omit frame pointers, making stack walking unreliable. Either compile with `-fno-omit-frame-pointer` or use DWARF-based unwinding (`--call-graph=dwarf` in perf).

2. **Forgetting that flame graphs show samples, not exact time.** A function shown with 10% might really have 8% or 12%; the sampling introduces noise. Use more samples for accuracy.

3. **Forgetting that off-CPU is often more important than CPU.** For I/O-bound workloads, the CPU is mostly idle; the bottleneck is the I/O wait. Use off-CPU flame graphs.

4. **Forgetting to handle Java's interpreted vs. JIT-compiled code.** The JIT compiler inlines functions; the call stack may not match the source code. Use async-profiler with `--event=itimer` to sample Java stacks correctly.

5. **Forgetting that flame graphs can be misleading for very deep stacks.** A stack of 100 frames doesn't fit on screen; the rendering becomes unclear. Filter to the top N frames or use the "reverse" flame graph (where the X-axis is the leaf, not the root).

6. **Forgetting to disable JIT warmup before profiling.** The JIT compiler re-optimizes during warmup; profiling during warmup gives misleading results. Profile after the application is warmed up.

## References

- Brendan Gregg, "[The Flame Graph](http://www.brendangregg.com/flamegraphs.html)" (2011)
- [FlameGraph GitHub repository](https://github.com/brendangregg/FlameGraph)
- [perf examples](https://www.brendangregg.com/perf.html)
- [async-profiler GitHub](https://github.com/async-profiler/async-profiler)
- [bpftrace: DTrace for Linux](https://github.com/iovisor/bpftrace)
- [Pixie: Continuous profiling](https://github.com/pixie-io/pixie)
- [Parca: Continuous profiling](https://github.com/parca-dev/parca)
- [LWN: Flame graphs (2015)](https://lwn.net/Articles/603715/)
