# Advanced Benchmarking

Benchmarking is the foundation of performance engineering. A benchmark that is poorly designed, uncontrolled, or statistically unsound can lead to incorrect conclusions, wasted optimization effort, and wrong architectural decisions. This section covers rigorous benchmarking methodology, common pitfalls, statistical analysis, tooling, and profiling infrastructure.

## Benchmark Methodology

A rigorous benchmark is a **controlled experiment**: you change one variable (the system under test) while holding everything else constant. This means pinning CPU cores, disabling frequency scaling, isolating the process from other workloads, clearing page caches, and running multiple iterations. Each benchmark run should be repeatable — running it again should produce results within a small variance. Document every parameter: hardware model, kernel version, compiler flags, input size, number of threads, and environment variables.

## Microbenchmark Pitfalls

Microbenchmarks (measuring a single function or small code path) are especially treacherous. The compiler may eliminate the code you're measuring as dead code if the result is unused — you must use a volatile write or a black-box escape to prevent this. Loop-invariant code motion may hoist computations out of the measured loop. The JIT compiler (in Java, Go, V8) may not have compiled the hot path yet, or may de-optimize it mid-benchmark. Always inspect the generated assembly (`objdump -d` or `gcc -S`) to verify the benchmark body is what you think it is.

## Warm-Up and JIT Effects

JIT-compiled languages (Java, C#, Go, V8) require warm-up iterations before the code reaches steady-state performance. During warm-up, the interpreter runs the code, the JIT profiles it, and tiered compilation kicks in (C1 → C2 in HotSpot). A benchmark that includes warm-up iterations in its measurement will show artificially low throughput. Use frameworks like JMH (Java), `testing.B` (Go), or Criterion.rs (Rust) that handle warm-up and measurement phases automatically. For AOT-compiled languages (C, C++, Rust), warm-up is less of a concern but still matters for CPU frequency ramping and page cache population.

## Cache Effects

The first access to a data structure touches cold cache lines, causing cache misses (50-200 cycles on L3, 100+ ns on DRAM). Subsequent accesses hit warm caches (1-4 cycles). A benchmark that measures only the first access (cold cache) will show very different results from one that measures repeated accesses (warm cache). Both are valid depending on what you're modeling: cold-cache benchmarks model production scenarios where data is accessed rarely (e.g., user profile lookup by ID), while warm-cache benchmarks model hot-path operations (e.g., in-memory index traversal). Always report whether the benchmark is cold or warm, and measure both if the access pattern is ambiguous.

## CPU Frequency Scaling, Turbo Boost, and Thermal Throttling

Modern CPUs dynamically adjust their clock frequency based on workload, temperature, and power limits. A benchmark that runs a short burst may benefit from turbo boost (e.g., 5.0 GHz for a single-core workload) while a sustained benchmark may thermally throttle down to base frequency (e.g., 3.5 GHz). This can cause a 30-40% performance difference between a 1-second benchmark and a 60-second benchmark. Pin CPU frequency with `cpupower frequency-set -g performance` or the Intel P-State driver. Disable turbo boost in BIOS or via `/sys/devices/system/cpu/intel_pstate/no_turbo` for consistent results.

## NUMA Effects on Benchmarks

On multi-socket NUMA systems, the location of data relative to the CPU accessing it matters enormously. Cross-socket memory access adds ~40-80 ns latency compared to local socket access. If your benchmark allocates memory on one NUMA node and the benchmark thread runs on another, the results will include this NUMA penalty, which may not reflect the intended scenario. Use `numactl --cpunodebind=0 --membind=0` to pin both CPU and memory to the same node, or use `numactl --interleave=all` for spread allocation.

## Background Noise Isolation

Background processes (cron jobs, log rotation, other containers, kernel daemons) introduce variance into benchmarks. On a shared machine, this variance can be 5-20%. Isolation techniques include: CPU pinning with `taskset -c 2-5` or `cgroups` cpusets, disabling unnecessary services, running in a dedicated VM or bare-metal machine, and using `perf stat` to check for context switches and migrations during the benchmark. For critical measurements, run on a quiescent system with only the benchmark and the OS running.

## Statistical Significance

A single benchmark run is meaningless. Report at least: mean, median, standard deviation, and 95% confidence interval across 20+ runs. Use the Student's t-test to determine if a performance change is statistically significant (p < 0.05). Report effect size (Cohen's d) alongside p-values — a statistically significant 0.1% improvement with a large sample size is probably noise. Watch for bimodal distributions (e.g., warm vs cold cache mixed together) — use histograms or kernel density plots to visualize the distribution, not just summary statistics.

## Reproducibility

A benchmark is reproducible if an independent party can run it and get the same results (within variance). This requires: documenting the full environment (hardware specs, OS, compiler/runtime versions), providing the exact build commands and configuration, open-sourcing the benchmark code, and using deterministic inputs (no random data, no time-dependent behavior). Tools like `perf` record environment metadata automatically. Container-based benchmarks (Docker) improve reproducibility by fixing the software environment.

## Benchmark Suites

| Suite | Domain | What It Measures | Key Metric |
|-------|--------|-----------------|------------|
| **SPEC CPU 2017** | CPU (integer/floating-point) | Compiler optimization, CPU pipeline, memory hierarchy | SPECratio |
| **SPEC jvm2008** | JVM | Java runtime performance (compiler, GC, threading) | ops/min |
| **TPC-C** | OLTP database | Transaction processing throughput under concurrency | tpmC |
| **TPC-H** | Analytical queries | Complex query performance on large datasets | QphH@Size |
| **TPC-DS** | Decision support | Multi-dimensional query patterns (more complex than TPC-H) | QphDS@Size |
| **YCSB** | NoSQL/KV stores | Core operations: read, write, scan, update | ops/sec |
| **lmbench** | OS/hardware | Memory latency, context switch, file system, network | latency/throughput |
| **fio** | Storage I/O | Sequential/random read/write, IOPS, bandwidth | IOPS, MB/s |
| **iperf3** | Network throughput | TCP/UDP bandwidth, jitter, packet loss | Gbps, pps |
| **wrk / wrk2** | HTTP | HTTP request throughput and latency | req/sec, p99 latency |
| **k6** | HTTP/load testing | Scriptable load tests, thresholds, metrics | req/sec, latency %ile |
| **stress-ng** | System stress | CPU, memory, I/O, network stress testing | ops/sec, errors |

## perf — Linux Performance Counters

`perf` (Linux `perf_events`) provides access to hardware performance counters (PMU) and kernel software tracepoints without code instrumentation. Use `perf stat` for high-level counter aggregation and `perf record`/`perf report` for sampling-based profiling. Key hardware counters: `cycles` (CPU cycles), `instructions` (retired instructions, for IPC), `cache-references`/`cache-misses` (L1/L2/L3), `branch-misses` (branch prediction accuracy), and `LLC-load-misses` (last-level cache). Use `perf top` for real-time hot-spot identification.

```bash
# High-level summary of hardware counters
perf stat -e cycles,instructions,cache-references,cache-misses,branch-misses ./my_app

# Profile with sampling (99 kHz, attribute to function + source line)
perf record -g -F 99 ./my_app
perf report --stdio

# Trace a specific function entry/exit
perf probe -x ./my_app 'process_request'
perf record -e probe_myapp:process_request
```

## Flame Graphs

Flame graphs, created by Brendan Gregg, visualize stacked function call traces where the x-axis is the proportion of CPU time (not time-ordered) and the y-axis is stack depth. The width of each bar represents the time spent in that function and its callees. They are generated from `perf record` output or DTrace/SystemTap/Java stack traces using the `FlameGraph` scripts (or `speedscope` for interactive viewing).

**Differential flame graphs** compare two profiles (before and after a change) and color-code functions: red for regressions (more time spent), blue for improvements (less time spent). This is the fastest way to identify what changed in a performance profile. Generate them with `difffolded.pl` from the FlameGraph tools, then render with `flamegraph.pl`.

> **Interview Angle**: "How do you know your optimization actually helped?" The right answer involves controlled benchmarking with warm-up, multiple runs, confidence intervals, and before/after flame graphs. Claims like "it's 2x faster" without methodology are red flags. Show you understand that benchmarking is a discipline, not a casual exercise.

## Practical Tips

1. **Always run the baseline first** — optimize against a measured baseline, not a guess.
2. **Use the right tool for the right level** — `perf stat` for overview, `perf record` for hot spots, microbenchmarks for specific functions, load generators for system-level.
3. **Verify with multiple tools** — if `perf` says a function is hot but your microbenchmark shows it's fast, investigate the discrepancy.
4. **Beware of measurement overhead** — `perf record` at 1 kHz adds ~0.1% overhead; at 10 GHz it can add 5-10%. For latency-sensitive benchmarks, use hardware counters only (`perf stat` without sampling).
5. **Automate** — script your benchmark runs, output parsing, and result comparison. Tools like `hyperfine`, `benchstat` (Go), and `criterion` (Rust) handle this.

## References

- Brendan Gregg's *Systems Performance* (2nd Ed.), Ch. 2 (Methodology) and Ch. 6 (CPUs)
- Brendan Gregg's Flame Graph site: https://www.brendangregg.com/flamegraphs.html
- `perf` man pages: `perf-stat(1)`, `perf-record(1)`
- SPEC CPU 2017: https://www.spec.org/cpu2017/
- TPC benchmarks: https://www.tpc.org/