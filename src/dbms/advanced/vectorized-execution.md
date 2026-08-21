# Vectorized Execution

Vectorized execution is the execution-engine design pattern used by every modern analytical database (ClickHouse, DuckDB, SingleStore, Apache Arrow Acero, and increasingly PostgreSQL with custom extensions). Each operator processes a batch of tuples per `next()` call rather than one tuple per call, reducing per-tuple overhead by 50-100× and exposing SIMD-friendly tight loops to the compiler. This page covers the batch model, the implementation patterns that make vectorization fast, and why the model is displacing the classical Volcano iterator model for analytical workloads.

## The Problem with the Volcano Iterator Model

The classical Volcano iterator model calls `next()` once per tuple:

```text
Plan: Filter(Scan(t), x > 5)
1M tuples:
  Scan.next()        ← virtual call
  Filter.next():
    child.next()     ← virtual call
    pred(t)          ← branch
  return tuple
```

Per tuple, the query executes 2 virtual function calls (each ~1 ns) plus a comparison (~1 ns) plus the branch (~1-3 ns). For 1 million tuples, that's ~5-10 ms of pure overhead. For 1 billion tuples (a small analytical query), that's 5-10 seconds of overhead alone — dominating the actual work.

The SIMD opportunity is also lost: a Volcano iterator processes one tuple at a time, but a SIMD register can process 8-16 tuples in a single instruction. The iterator model's per-tuple function call overhead prevents SIMD from being profitable.

## The Vectorized Model

A vectorized operator processes a batch (typically 1024-4096 tuples) per `next()` call:

```text
Plan: Filter(Scan(t), x > 5)
1M tuples in batches of 1024 = 976 batches
  Scan.next(batch)         ← one virtual call, returns 1024 tuples
  Filter.next(batch):
    child.next(batch)      ← one virtual call
    pred(batch)            ← SIMD: 8 tuples/instruction
    return batch (with filtered subset)
```

Per batch (1024 tuples), the query executes 2 virtual calls plus 128 SIMD instructions (1024 tuples / 8 per SIMD register). The virtual call overhead is amortized across 1024 tuples: ~2 ns/tuple instead of 2-5 ns/tuple.

## The Apache Arrow Columnar Layout

For SIMD to work, data must be in columnar layout (one column's values contiguous in memory). The Apache Arrow specification codifies this layout:

```text
Batch of 4 tuples:
  Tuple 1: {id=1, name='Alice', age=30, score=4.5}
  Tuple 2: {id=2, name='Bob',   age=25, score=3.2}
  Tuple 3: {id=3, name='Cara',  age=40, score=4.8}
  Tuple 4: {id=4, name='Dan',   age=35, score=3.9}

Arrow layout (columnar):
  id array:    [1, 2, 3, 4]                         ← 4 × int32 = 16 bytes
  name array: ['Alice', 'Bob', 'Cara', 'Dan']      ← 4 × string, length+ptr
  age array:   [30, 25, 40, 35]                     ← 4 × int32 = 16 bytes
  score array: [4.5, 3.2, 4.8, 3.9]                ← 4 × float64 = 32 bytes
```

The columnar layout lets a filter `age > 28` scan only the `age` array, loading 32 bytes into 4 SIMD lanes and producing a 4-bit mask in one instruction.

## A Vectorized Filter Implementation

```c
// Vectorized filter on age > 28, producing a selection vector
void filter_age_gt_28(const int32_t* ages, int n, int* sel_out, int* sel_len) {
    const __m256i threshold = _mm256_set1_epi32(28);
    int out_idx = 0;
    int i = 0;
    
    // SIMD loop: 8 ints at a time
    for (; i + 8 <= n; i += 8) {
        __m256i v = _mm256_loadu_si256((__m256i*)(ages + i));
        __m256i mask = _mm256_cmpgt_epi32(v, threshold);
        // mask has 1s in lanes where v > threshold
        unsigned int bits = _mm256_movemask_epi8(mask);
        // each byte of mask is 0xFF or 0x00; movemask produces 32 bits
        // For int32 comparisons, we want every 4th bit
        bits &= 0x01010101u * 0xFF;  // isolate bit per int32
        // Alternatively, compress the mask:
        while (bits) {
            int idx = __builtin_ctz(bits) / 4;
            sel_out[out_idx++] = i + idx;
            bits &= bits - 1;
        }
        // Easier: use _mm256_compress_epi32 in AVX-512
    }
    
    // Scalar tail
    for (; i < n; i++) {
        if (ages[i] > 28) sel_out[out_idx++] = i;
    }
    *sel_len = out_idx;
}
```

The selection vector `sel_out` is an array of indices into the original batch that passed the filter. Subsequent operators read from the original batch using `sel_out` rather than copying the data.

## Selection Vectors vs. Materialization

Two patterns for representing a filtered batch:

1. **Selection vector** (DuckDB, ClickHouse): store indices of surviving tuples. Pros: no copying, compact (4 bytes per surviving tuple). Cons: downstream operators must look up via the index, slightly complicating code.

2. **Materialized batch** (PostgreSQL vectorized executor, Apache Arrow with "filter" kernels): copy surviving tuples into a new batch. Pros: simpler downstream code. Cons: extra memory traffic.

DuckDB's benchmarks show selection vectors are ~10-20% faster than materialized batches for typical filter-then-project queries, because they avoid the copy. For aggregations, materialized is sometimes faster because of better cache locality.

## The Vectorized Hash Join

A vectorized hash join processes the build side in batches:

```c
// Build phase: insert each batch of right-side tuples into the hash table
HashJoin::open() {
    while (right_child.next(right_batch)) {
        for (int i = 0; i < right_batch.size; i++) {
            hash_table.insert(right_batch[i].key, right_batch[i]);
        }
    }
}

// Probe phase: for each batch of left-side tuples, look up
HashJoin::next(batch_out) {
    if (!left_child.next(left_batch)) return 0;
    
    // Vectorized hash computation
    __m256i keys = _mm256_loadu_si256(left_batch.keys);  // 8 keys at a time
    __m256i hashes = hash_8_keys(keys);  // SIMD hash
    
    // Vectorized hash table lookup
    for (int lane = 0; lane < 8; lane++) {
        int h = _mm256_extract_epi32(hashes, lane);
        Entry* e = hash_table.lookup(h, left_batch.keys[lane]);
        if (e) {
            // emit (left, right) tuple to output
            emit_to_batch(batch_out, left_batch, lane, e->value);
        }
    }
    return batch_out.size;
}
```

The vectorized hash join achieves 5-10× the throughput of the classical tuple-at-a-time hash join, primarily due to:
- Fewer branch mispredictions (SIMD has fewer branches).
- Better cache utilization (one hash table walk per batch, not per tuple).
- Fewer function calls.

## Vectorized Aggregation

```c
// Vectorized sum over a column
double sum_doubles(const double* values, int n) {
    __m512d acc = _mm512_setzero_pd();
    int i = 0;
    for (; i + 8 <= n; i += 8) {
        __m512d v = _mm512_loadu_pd(values + i);
        acc = _mm512_add_pd(acc, v);
    }
    double result = _mm512_reduce_add_pd(acc);
    for (; i < n; i++) result += values[i];
    return result;
}

// Group-by aggregation: maintain a hash table of (group_key -> aggregate)
void group_by_sum(const int32_t* keys, const double* values, int n,
                  HashTable* ht) {
    // Hash 8 keys at a time, then look up each in the HT
    for (int i = 0; i < n; i += 8) {
        __m256i k = _mm256_loadu_si256(keys + i);
        __m256i h = hash_8_keys(k);
        
        // For each lane, look up the group in the hash table
        for (int lane = 0; lane < 8; lane++) {
            int key = _mm256_extract_epi32(k, lane);
            int hash = _mm256_extract_epi32(h, lane);
            GroupEntry* g = ht->lookup_or_insert(hash, key);
            g->sum += values[i + lane];
            g->count++;
        }
    }
}
```

ClickHouse reports 100+ million rows/sec for simple group-by-sum queries on a single core, due primarily to vectorization.

## JIT Compilation vs. Vectorization

The two competing approaches to high-performance analytical execution:

| Approach | Description | When it's faster |
|----------|-------------|-------------------|
| Vectorized interpretation | Pre-compiled kernels operate on batches. Compiler auto-vectorizes the kernels. | When queries are short or the data is small (compilation overhead dominates for small queries). |
| JIT compilation | Generate and compile specialized code for each query. The compiled code has no interpretation overhead. | When queries are large or repetitive (compilation cost is amortized). |

Hybrid approaches (e.g., DuckDB's "volcano-style vectorized interpretation with JIT-compiled inner loops") combine the best of both. Apache Spark's Photon engine, SingleStore, and HyPer all use JIT for the inner loops while keeping the iterator structure for control flow.

## Pipelined Execution

Vectorized operators compose naturally. A plan like:

```text
SELECT region, SUM(amount) FROM sales WHERE amount > 100
GROUP BY region ORDER BY SUM(amount) DESC LIMIT 10
```

Is executed as:

```text
TopN(SortLimit(
  HashAgg(
    Filter(
      Scan(sales),
      amount > 100
    ),
    group_by=region,
    agg=SUM(amount)
  ),
  order_by=SUM(amount) DESC,
  limit=10
))
```

Each operator processes batches, calling `next()` on its child. The pipeline is:

```text
Scan: emits batches of (region, amount) tuples.
Filter: emits batches with amount > 100.
HashAgg: builds hash table, then emits batches of (region, SUM(amount)).
SortLimit: maintains a top-10 heap, emits batches of (region, SUM(amount)) sorted.
TopN: passes through.
```

The "pipeline breaker" is `HashAgg` (must consume the entire input before producing output). Operators before the breaker are pipelined; the breaker materializes its output.

## Adaptive Batch Sizes

The optimal batch size depends on:
- L1 cache size (smaller batches fit; typical: 32 KB L1d, 1024 tuples × 32 bytes).
- TLB pressure (larger batches cause TLB misses if they span many pages).
- SIMD width (AVX2: 8 × int32; AVX-512: 16 × int32).
- Operator-specific factors (sort prefers larger batches for cache locality; hash join prefers smaller for build-side memory).

Production engines use 1024-4096 tuples per batch as a sweet spot. DuckDB uses 2048; ClickHouse uses up to 65536 in some operators. PostgreSQL's vectorized executor (when enabled) uses 1024.

## Common Pitfalls

1. **Mixing column types in a single batch.** A batch with mixed types (e.g., a tuple with `int32` and `string`) breaks SIMD. Process each column separately.

2. **Forgetting the selection vector on the output side.** A filter that produces 100 surviving tuples out of 1024 should pass a 100-tuple selection vector downstream, not a 1024-tuple batch with 924 nulls. The nulls waste cache and memory bandwidth.

3. **Treating vectorized and tuple-at-a-time as interchangeable.** They are not. A 1-tuple-per-`next()` operator that consumes a vectorized batch must be rewritten to emit batches; otherwise, the per-tuple overhead returns.

4. **Ignoring memory layout.** A columnar batch with a pointer-chasing layout (e.g., one `std::string` per tuple) defeats SIMD. Use a fixed-width column or a dictionary-encoded + offset layout.

5. **Compiling with the wrong flags.** Vectorized code requires `-O3 -march=native` (or the equivalent). Default `-O2` is too conservative for SIMD loops; `-O0` disables them entirely.

## References

- [MonetDB/X100: Hyper-Pipelined Query Execution](https://www.cs.cmu.edu/~kapil sigmod/x100.pdf) (CIDR 2005) — the original vectorized execution paper
- [The Complete Vectorized Execution Story](https://duckdb.org/2022/03/13/duckdb-internal-3.html) (DuckDB blog, 2022)
- [Apache Arrow: Computational Columnar In-Memory Format](https://arrow.apache.org/docs/format/Columnar.html)
- [ClickHouse: Vectorized Execution](https://clickhouse.com/blog/clickhouse-100x-faster-queries-with-asyncio)
- [HyPer: Combining Vectorized Execution and JIT](http://hyper-db.de/downloads/papers/haapamaki_vldb_2014.pdf) (VLDB 2014)
- [Apache Spark Photon engine](https://databricks.com/blog/2022/06/28/introducing-photon.html)
- [Apache Arrow Acero](https://arrow.apache.org/docs/cpp/acero.html)
