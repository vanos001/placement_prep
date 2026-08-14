# Benchmarking

Benchmarking is the science of measuring performance with enough rigor that your results are **reproducible and meaningful**. Bad benchmarks are worse than no benchmarks — they give you false confidence in changes that don't help (or actively hurt).

## Microbenchmarks: Why They're Tricky

A microbenchmark measures a tiny piece of code in isolation. The problem: the real world is not isolated.

### The Dead Code Elimination Trap

```rust
// This benchmark is WRONG — the compiler optimizes the entire thing away
fn bench_addition(b: &mut Bencher) {
    b.iter(|| {
        let x = 1 + 2;  // result unused → compiler deletes it
    });
}

// Correct: use the result
fn bench_addition(b: &mut Bencher) {
    b.iter(|| {
        black_box(1 + 2)  // prevents optimization
    });
}
```

### Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| **No warmup** | First iterations are slow (JIT, caches cold) | Run warmup phase before measurement |
| **JIT compilation** | JVM/Go take time to optimize hot code | Use JMH (auto-warms), or `-gcflags=-l=4` in Go |
| **Cache warming** | First run is slow, subsequent fast | Measure steady-state, not first-run |
| **Timer resolution** | Sub-millisecond ops need `CLOCK_MONOTONIC` or `rdtsc` | Use language benchmarking frameworks |
| **OS noise** | Other processes steal CPU time | Pin cores, disable turbo boost, use `perf lock` |
| **Too few iterations** | High variance, no statistical significance | Use framework's automatic iteration count |
| **Including setup** | Measuring initialization + steady state | Separate setup from measurement loop |

## Language-Specific Microbenchmarking Tools

### Java: JMH (Java Microbenchmark Harness)

JMH is the **only** correct way to benchmark Java. It handles warmup, JIT, dead code elimination, and fork isolation.

```java
import org.openjdk.jmh.annotations.*;
import java.util.concurrent.TimeUnit;

@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@Warmup(iterations = 5, time = 1)
@Measurement(iterations = 10, time = 1)
@Fork(3)
@State(Scope.Thread)
public class HashMapBenchmark {
    private HashMap<Integer, String> map;

    @Setup
    public void setup() {
        map = new HashMap<>();
        for (int i = 0; i < 10_000; i++) {
            map.put(i, "value" + i);
        }
    }

    @Benchmark
    public String getExisting() {
        return map.get(5000);
    }
}
```

### Rust: Criterion

Criterion.rs provides statistical analysis, regression detection, and HTML reports out of the box.

```rust
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_vec_push(c: &mut Criterion) {
    c.bench_function("vec_push_1000", |b| {
        b.iter(|| {
            let mut v = Vec::new();
            for i in 0..1000 {
                v.push(i);
            }
            criterion::black_box(v);
        });
    });
}

criterion_group!(benches, bench_vec_push);
criterion_main!(benches);
```

### Go: Built-in Testing

```go
func BenchmarkConcat(b *testing.B) {
    b.Run("plus", func(b *testing.B) {
        for i := 0; i < b.N; i++ {
            s := ""
            for j := 0; j < 1000; j++ {
                s += "x"  // Bad: O(n²)
            }
        }
    })
    b.Run("strings_builder", func(b *testing.B) {
        for i := 0; i < b.N; i++ {
            var sb strings.Builder
            for j := 0; j < 1000; j++ {
                sb.WriteString("x")  // Good: O(n)
            }
        }
    })
}

# Run: go test -bench=. -benchmem
# -benchmem shows allocation counts and bytes
```

### Python: pytest-benchmark

```python
import pytest

def test_sort_list(benchmark):
    data = list(range(10000, 0, -1))
    benchmark(sorted, data)  # benchmark() runs it many times automatically

# Run: pytest --benchmark-only
```

## Statistical Significance

You cannot compare two numbers and declare a winner. Real systems have variance from OS scheduling, cache effects, and thermal throttling.

**Rules of thumb:**
- Run **at least 3 forks** (separate JVM/OS processes) to eliminate warmup bias
- Each fork runs **5-10 iterations**
- Use the framework's comparison: Criterion and JMH both compute confidence intervals
- A change is real only if the **confidence intervals don't overlap** and the **p-value < 0.05**

```bash
# Criterion example output:
# vec_push_1000    time:   [12.345 µs 12.456 µs 12.567 µs]
#                    change: [-2.3456% -1.2345% -0.1234%] (p = 0.01)
#                    Performance has improved.
```

## Load Testing

Microbenchmarks test isolated code. Load tests test your **entire system under realistic traffic patterns**.

| Tool | Language | Best For |
|------|----------|----------|
| **wrk** | C | Quick HTTP benchmarking, single-binary, low overhead |
| **k6** | Go/JS scriptable | Modern, scriptable, supports protocols beyond HTTP |
| **Locust** | Python | Python-based, programmatic scenario definition |
| **JMeter** | Java | Enterprise, GUI-based, protocol support (JDBC, JMS, etc.) |
| **vegeta** | Go | Constant-rate request pumping, easy pipelining |

### wrk Example

```bash
# 12 threads, 400 connections, 30 seconds
$ wrk -t12 -c400 -d30s http://localhost:8080/api/users

# Running 30s test @ http://localhost:8080/api/users
#   12 threads and 400 connections
#   Thread Stats   Avg      Stdev     Max   +/- Stdev
#     Latency    23.45ms   12.34ms 150.23ms   75.23%
#     Req/Sec     1.42k   345.21     2.10k    68.45%
#   Latency Distribution
#     50%   18.23ms
#     75%   29.45ms
#     90%   40.12ms
#     99%   85.67ms
#   1234567 requests in 30.00s, 456.78MB read
# Requests/sec:  41152.23
# Transfer/sec:     15.23MB/sec
```

## Interview Questions

1. **Why are microbenchmarks unreliable? What problems can they introduce?**
2. **How does JMH prevent dead code elimination in Java benchmarks?**
3. **You run a benchmark and get 10µs, then 8µs, then 12µs. How do you report this?**
4. **What's the difference between a microbenchmark and a load test? When would you use each?**
5. **How would you design a load test for an API that has both reads and writes?**
6. **What is the coordinated omission problem, and does `wrk` suffer from it?**
7. **How many iterations and forks do you typically need for a reliable benchmark? Why?**
8. **A team says "our new algorithm is 2× faster" based on a single run. What questions do you ask?**
