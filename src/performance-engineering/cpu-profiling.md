# CPU Profiling

CPU profiling answers one question: **where is my program spending its CPU time?** This is the first tool you reach for when a service is CPU-bound or when you simply don't know what's slow.

## Sampling vs. Instrumentation Profiling

| Aspect | Sampling | Instrumentation |
|--------|----------|---------------|
| **Mechanism** | Periodically interrupts and inspects call stacks | Inserts counting code at every function entry/exit |
| **Overhead** | Low (~1-5%) | Higher (10-100×) |
| **Accuracy** | Statistical (approximation) | Exact counts |
| **Best for** | Finding hot spots in production | Precise call counts, recursive functions |
| **Limitation** | May miss very short-lived functions | Can't profile code you can't modify (e.g., libraries without symbols) |

Sampling is preferred for production profiling because the low overhead means you can profile under real load without significantly distorting results.

## Flame Graphs

Flame graphs, created by **Brendan Gregg**, are the single most effective visualization for CPU profiling data.

```
How to read a flame graph:

  ┌─────────────────────────────────────────┐
  │          main()                         │  ← root (100% of CPU time)
  │  ┌──────────────┐  ┌─────────────────┐  │
  │  │ process()    │  │ handleIO()     │  │  ← top-level callees
  │  │ ┌──────────┐  │  │                 │  │
  │  │ │ parse()  │  │  │                 │  │  ← deeper calls
  │  │ │ ┌──────┐ │  │  │                 │  │
  │  │ │ │token │ │  │  │                 │  │  ← leaf (CPU is burning here)
  │  │ │ └──────┘ │  │  │                 │  │
  │  │ └──────────┘  │  │                 │  │
  │  └──────────────┘  └─────────────────┘  │
  └─────────────────────────────────────────┘

  Width  = proportion of CPU time in that function
  Height = call stack depth
  Color  = usually random (no semantic meaning); some tools color by module
```

**Reading rules:**
- Look for the **widest towers** — these consume the most CPU.
- The **top of each tower** is where CPU is actually being spent (leaf functions).
- If a function spans the full width of the graph, it's on every call path — optimizing it helps everything.

## Linux `perf`

`perf` is the standard Linux profiling tool. It uses hardware performance counters (PMU) for near-zero overhead sampling.

### `perf stat` — High-Level Summary

```bash
$ perf stat ./my_server

 Performance counter stats for './my_server':

      3,241.52 msec  task-clock           #    0.998 CPUs utilized
            12      context-switches     #    3.701 /sec
             1      cpu-migrations       #    0.308 /sec
         4,521      page-faults          #    1.395 K/sec
 9,876,543,210      cycles               #    3.046 GHz
 7,654,321,098      instructions         #    0.775  insn per cycle  ← IPC! Low = CPU-bound, stalls
   123,456,789      cache-references     #   38.099 M/sec
    12,345,678      cache-misses         #   10.008 % of all cache refs

    3.247812345 seconds time elapsed
```

Key metric: **Instructions Per Cycle (IPC)**. Low IPC (< 1.0) often means cache misses or branch mispredictions. High IPC (> 2.0) means the CPU is executing efficiently.

### `perf record` + `perf report` — Detailed Profiles

```bash
# Record CPU profile for a specific PID
$ perf record -p <PID> -g -- sleep 30

# Record with call graph (dwarf unwinding for accurate stacks)
$ perf record -g --call-graph dwarf -p <PID>

# View the report (interactive TUI)
$ perf report

# Generate a flame graph (using Brendan Gregg's scripts)
$ perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

## Language-Specific Tools

### Java

| Tool | Type | Use Case |
|------|------|----------|
| **Java Flight Recorder (JFR)** | Low-overhead continuous | Production monitoring, event-based |
| **async-profiler** | Sampling | Modern, supports Java + native, generates flame graphs |
| **visualvm / jvisualvm** | GUI | Development-time inspection |
| **JMH** | Microbenchmarking | Rigorous method-level benchmarks |

```bash
# async-profiler: generate flame graph in 30 seconds
$ ./profiler.sh -d 30 -f flame.svg <pid>

# JFR: start recording
$ jcmd <pid> JFR.start name=profiling duration=60s filename=recording.jfr
```

### Python

| Tool | Type | Notes |
|------|------|-------|
| **py-spy** | Sampling | No code changes, supports flame graphs |
| **cProfile** | Instrumentation | Built-in, exact counts |
| **line_profiler** | Line-level | Per-line timing inside functions |
| **PyInstrument** | Sampling | Low overhead, async-friendly |

```bash
# py-spy: top-like live view
$ py-spy top --pid <pid>

# py-spy: generate flame graph
$ py-spy record -o flame.svg --pid <pid> --duration 30

# cProfile
$ python -m cProfile -s cumtime my_script.py
```

### Go

| Tool | Type | Notes |
|------|------|-------|
| **pprof** | Both | Built into runtime, HTTP endpoint |
| **go tool trace** | Tracing | Execution tracer, not a profiler |
| **benchstat** | Analysis | Statistical comparison of benchmark results |

```go
// In your server:
import _ "net/http/pprof"
// Then: go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30

// Generate flame graph:
// go tool pprof -http=:8080 http://localhost:6060/debug/pprof/profile
```

### Rust

| Tool | Type | Notes |
|------|------|-------|
| **perf** | Sampling | Works with debug symbols (`-g`) |
| **criterion** | Microbenchmarking | Statistical rigor built-in |
| **tracy** | Tracing/profiling | Real-time, frame-level profiling |
| **samply** | Sampling | Modern flame graph viewer (`cargo samply record -- my-binary`) |

```bash
# Build with debug info
$ cargo build --release

# Profile with perf
$ perf record -g ./target/release/my_app
$ perf report

# Or use samply for nicer flame graphs
$ cargo install samply
$ samply record ./target/release/my_app
```

## Common CPU Bottlenecks

| Bottleneck | Symptoms | Typical Fix |
|-----------|----------|-------------|
| **Cache misses** | Low IPC, high `cache-misses` in perf stat | Data structure reorganization, padding, better access patterns |
| **Branch misprediction** | High `branch-misses`, irregular control flow | Branchless code, lookup tables, sort data before processing |
| **Lock contention** | High `sys_futex` in perf, threads waiting | Reduce lock scope, use lock-free structures, sharding |
| **Syscall overhead** | High `cpu-migrations`, many `sys_enter` | Batch syscalls, use `io_uring`, buffer I/O |
| **JIT warmup** | Slow initial requests in JVM/Python | Warmup runs, JIT pre-compilation (e.g., ` GraalVM native-image`) |
| **GC pressure** | CPU spikes correlating with heap usage | Reduce allocations, tune GC, use object pools |

## Interview Questions

1. **What's the difference between sampling and instrumentation profiling? When would you choose each?**
2. **How do you read a flame graph? What does the width of a stack frame represent?**
3. **You run `perf stat` and see IPC of 0.5. What does that tell you? What would you investigate next?**
4. **How would you profile a Java application running in a container with limited CPU?**
5. **What is async-profiler and why is it preferred over `jstack` for production Java profiling?**
6. **How does `pprof` in Go work under the hood?**
7. **A service has 80% CPU but low throughput. Walk me through your diagnosis.**
8. **How would you detect and diagnose lock contention as a CPU bottleneck?**
