# Parallel Sorting

Sorting is the canonical parallel-algorithms case study because it is the simplest task where the naive parallelization loses to the sequential library. This page walks the theory (work/span), the two algorithms that actually matter (parallel merge and sample sort), and a measured implementation using shared memory - ending with the honest observation that in CPython, beating `sorted()` is nearly impossible, and why that fact generalizes to every language with a C-tuned standard library.

## Work and Span: The Vocabulary

For a parallel algorithm, count two costs: **work** `T1` (total operations, what one processor does) and **span** `T-infinity` (the longest dependency chain, what infinite processors do). Parallelism is `T1 / T-infinity`; with `P` processors, runtime is bounded below by both `T1/P` and `T-infinity` (this pairing is Brent's theorem in scheduling terms). A good parallel sort has work close to sequential `O(n log n)` and span far below it.

Parallel mergesort: splitting is trivial; the merge is the problem. A sequential merge has span `O(n)` - the entire last level serializes - so total span stays `O(n)`, work/span parallelism is a feeble `O(log n)`, and nothing scales. The fix is *parallel merging*: to merge sorted halves A and B, take the median position in A, binary-search its insertion point in B, and recurse on both halves *independently* (two subproblems with disjoint output ranges). This drops merge span to `O(log^2 n)`, giving:

```
parallel mergesort:  T1 = O(n log n)   T-inf = O(log^2 n)   parallelism = O(n / log^2 n)
```

For n = 4 million, that predicts parallelism in the tens of thousands - far more than any real core count, meaning mergesort is *latency-optimal* in theory. Theory's favorite algorithm, however, is nobody's production favorite, and the next section explains why.

## Sample Sort: What Production Actually Uses

Parallel mergesort's weakness is memory behavior and load balance on real hardware: merges have poor locality, and fixed splitting assumes uniform costs. Sample sort replaces merging with *partitioning*:

```
            input (any order)
                 |
   [p0] [p1] [p2] [p3]   pivots from global samples
   /      |     |     \
 bucket0 bucket1 bucket2 bucket3     every element of bucket i <= every
   |      |      |      |            element of bucket i+1
 local  local  local  local
 sort   sort   sort   sort
   \      |     |     /
        concatenate (already globally ordered)
```

The mechanics: (1) each worker samples O(p log n) elements from its chunk; (2) a common set of p-1 *pivots* (splitters) is chosen from the pooled samples; (3) every worker partitions its chunk into p buckets by binary search; (4) bucket i of all workers is concatenated and sorted - possibly in parallel - by whoever owns bucket i. Because buckets are pivot-delimited, concatenating the sorted buckets yields the globally sorted array with **no merge step at all**.

Balance comes from the sampling: with random samples, bucket sizes concentrate around n/p (Chernoff-style tails), so no worker gets a whale bucket. This is why sample sort, not mergesort, is what PBBS benchmarks, C++ parallel-mode extensions, and Spark's `sortByKey` (RangePartitioner - literally sampled range bounds) all use. Radix sort variants compete when keys are fixed-width integers (GPU sorting is almost entirely radix for this reason - no comparisons, perfect coalescing), but comparison-based sample sort is the general-purpose answer.

## A Real Implementation: Shared Memory or Bust

The engineering lesson that separates a toy from production code: *the data must not move*. A naive Python multiprocessing sort that pickles 4M-element chunks to workers and pickles results back spends more time serializing than sorting. The version below uses `multiprocessing.shared_memory`: workers generate, count, scatter, and sort *in place*, and only control metadata (samples, counts, offsets) crosses process boundaries:

```python
# 4-process sample sort of 4M floats via multiprocessing.shared_memory.
# All payload data lives in shared memory; IPC carries only samples/counts.
# The sequential "pure-python pipeline" does identical phases in one process.
import multiprocessing as mp, random, statistics, time

pivots = [0.25, 0.5, 0.75]     # replaced after phase 1
_SHM = {}

def _shm_init(name_in, name_out, n):
    from multiprocessing import shared_memory
    _SHM['in'] = shared_memory.SharedMemory(name=name_in)
    _SHM['out'] = shared_memory.SharedMemory(name=name_out)
    _SHM['in_buf'] = _SHM['in'].buf.cast('d')
    _SHM['out_buf'] = _SHM['out'].buf.cast('d')

def _sample_segment(args):
    lo, hi = args
    return _SHM['in_buf'][lo:hi: max(1, (hi - lo) // 256)].tolist()

def _gen_into_shm(args):
    seed, lo, hi = args
    rng = random.Random(seed)
    buf = _SHM['in_buf']
    for i in range(lo, hi):
        buf[i] = rng.random()

def _count_buckets(args):
    lo, hi, pivots = args
    import bisect
    buf = _SHM['in_buf']
    counts = [0] * (len(pivots) + 1)
    for i in range(lo, hi):
        counts[bisect.bisect_left(pivots, buf[i])] += 1
    return counts

def _scatter(args):
    lo, hi, pivots, offsets = args
    import bisect
    pos = list(offsets)
    ib, ob = _SHM['in_buf'], _SHM['out_buf']
    for i in range(lo, hi):
        b = bisect.bisect_left(pivots, ib[i])
        ob[pos[b]] = ib[i]
        pos[b] += 1

def _sort_segment(args):
    import array
    lo, hi = args
    ob = _SHM['out_buf']
    seg = array.array('d', sorted(ob[lo:hi]))
    ob[lo:hi] = seg

def sort_demo():
    from multiprocessing import shared_memory
    n = 4_000_000
    procs = 4
    chunk = n // procs
    shm_in = shared_memory.SharedMemory(create=True, size=n * 8)
    shm_out = shared_memory.SharedMemory(create=True, size=n * 8)
    def pure_python_pipeline(pv):
        import bisect
        data = [0.0] * n
        for s in range(procs):
            rng = random.Random(s)
            data[s * chunk:(s + 1) * chunk] = [rng.random() for _ in range(chunk)]
        counts = [0] * procs
        for x in data:
            counts[bisect.bisect_left(pv, x)] += 1
        pos = [sum(counts[:b]) for b in range(procs)]
        out = [0.0] * n
        for x in data:
            b = bisect.bisect_left(pv, x)
            out[pos[b]] = x
            pos[b] += 1
        for b in range(procs):
            s = pos[b] - counts[b]
            out[s:s + counts[b]] = sorted(out[s:s + counts[b]])
        return out
    try:
        t0 = time.perf_counter()
        with mp.Pool(procs, initializer=_shm_init,
                     initargs=(shm_in.name, shm_out.name, n)) as pool:
            pool.map(_gen_into_shm, [(s, s * chunk, (s + 1) * chunk) for s in range(procs)])
            data = list(shm_in.buf.cast('d'))
            pieces = pool.map(_sample_segment, [(s * chunk, (s + 1) * chunk) for s in range(procs)])
            samples = sorted(x for p in pieces for x in p)
            pivots = [samples[k2 * len(samples) // procs] for k2 in range(1, procs)]
            count_lists = pool.map(_count_buckets,
                                   [(s * chunk, (s + 1) * chunk, pivots) for s in range(procs)])
            bucket_sizes = [sum(count_lists[s][b] for s in range(procs)) for b in range(procs)]
            bucket_start = [sum(bucket_sizes[:b]) for b in range(procs)]
            # worker s writes bucket b at bucket_start[b] + same-bucket counts of
            # EARLIER workers (transposing this into earlier buckets is the bug)
            offs = [[bucket_start[b] + sum(count_lists[s2][b] for s2 in range(s))
                     for b in range(procs)] for s in range(procs)]
            pool.map(_scatter, [(s * chunk, (s + 1) * chunk, pivots, offs[s])
                                for s in range(procs)])
            pool.map(_sort_segment, [(bucket_start[b], bucket_start[b] + bucket_sizes[b])
                                     for b in range(procs)])
            par = list(shm_out.buf.cast('d'))
        t_par = time.perf_counter() - t0
        t1 = time.perf_counter(); seq = sorted(data); t_seq_c = time.perf_counter() - t1
        t1 = time.perf_counter(); seq2 = pure_python_pipeline(pivots); t_seq_py = time.perf_counter() - t1
        print(f"n={n:,} procs={procs} (shared memory, zero payload IPC)")
        print(f"sequential C sorted()           : {t_seq_c:6.3f} s")
        print(f"sequential pure-python pipeline : {t_seq_py:6.3f} s")
        print(f"parallel pipeline (4 workers)   : {t_par:6.3f} s")
        print(f"speedup vs pure-python pipeline : {t_seq_py / t_par:5.2f}x")
        print(f"speedup vs C sorted()           : {t_seq_c / t_par:5.2f}x  <- Amdahl in action")
        print("par==seq:", par == seq, "| seq2==seq:", seq2 == seq)
    finally:
        shm_in.close(); shm_in.unlink()
        shm_out.close(); shm_out.unlink()

if True:
    sort_demo()
```

Output (measured on a 4-core container; absolute times vary, ratios are the point):

```text
n=4,000,000 procs=4 (shared memory, zero payload IPC)
sequential C sorted()           :  1.197 s
sequential pure-python pipeline :  2.935 s
parallel pipeline (4 workers)   :  2.604 s
speedup vs pure-python pipeline :  1.13x
speedup vs C sorted()           :  0.46x  <- Amdahl in action
par==seq: True | seq2==seq: True
```

## Reading the Numbers Honestly

The parallel pipeline is *correct* and only 1.1x faster than one process doing identical work, and 0.45x the speed of C `sorted()`. Three forces produce this, and each one is a permanent fact of parallel programming:

1. **Amdahl's law on the control path.** Sampling, pivot selection, offsets, and pool startup are serial; the per-element Python loops (generate, bisect, scatter) dominate and are parallelized, but `sorted()` itself is C code - the fastest phase is the one that parallelizes least well from Python. The 0.45x line is the whole lesson: parallelism is relative to the *implementation quality of the sequential baseline*, not to a textbook work count.
2. **Interpreter overhead per element.** The scatter loop executes 4M interpreted iterations with attribute lookups; the C sort executes the same work in compiled code. Languages matter: the identical algorithm in C++ with `std::sort` on 4 cores would beat single-core `std::sort` by 3-3.8x, which is exactly what PBBS and Intel's parallel-mode benchmarks report.
3. **Memory bandwidth.** Scatter is a random-ish write pattern across 32 MB of buffers; four cores contend for the same DRAM channels. Near `n * sizeof(key)` = L3 size x several, bandwidth - not cores - becomes the ceiling, which is why sample sort's cache-friendliness (sequential bucket writes, then independent sorts) is a bigger real-world win than its span.

The transferable takeaways: partition by sampled pivots so no merge phase exists; keep payload in shared memory and ship metadata; expect bandwidth and the sequential baseline's implementation quality - not core count - to decide the outcome. And the theory still matters: `T1 = O(n log n)` with `T-infinity = O(log n)`-ish is what makes the algorithm *able* to scale once you move to a language where the constants stop drowning the asymptotics.

## References

- Guy Blelloch and Bruce Maggs, "Parallel Algorithms" (CMU lecture notes - work/span, parallel merge): <https://www.cs.cmu.edu/~guyb/papers/BM13.pdf>
- Problem Based Benchmark Suite (PBBS) - comparison sort specification and reference implementations: <https://github.com/cmuparlay/pbbsbench>
- Sanders, Mehlhorn, Dietzfelbinger, "Sequential and Parallel Sorting" (Encyclopedia of Parallel Computing - sample sort and splitter selection): <https://link.springer.com/referenceworkentry/10.1007/978-0-387-09766-4_77>
- cppreference, "Execution policies" (std::sort par/par_unseq semantics): <https://en.cppreference.com/w/cpp/algorithm/execution_policy>
- Apache Spark, RangePartitioner (sampling-based range bounds behind sortByKey): <https://spark.apache.org/docs/latest/api/java/org/apache/spark/Partitioner.html>
