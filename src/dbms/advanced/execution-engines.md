# Advanced Execution Engines

The execution engine is the runtime that turns a query plan into actual data processing. This chapter covers the evolution from row-at-a-time Volcano iterators to modern vectorized, JIT-compiled, morsel-driven engines, plus the columnar encodings that make them fast.

## Volcano Iterator Model (Row-at-a-Time)

The classic Volcano model (Graefe, 1990) processes data **one tuple at a time**. Each operator implements a `next()` method that returns the next tuple.

```python
class HashJoin:
    def open(self):
        self.build_hash_table(self.left_child)
        self.right_child.open()
    
    def next(self):
        while True:
            r = self.right_child.next()   # one tuple at a time
            if r matches in self.ht:
                return joined_tuple(r)
    
    def close(self):
        self.right_child.close()
```

**Problems**: Massive per-tuple overhead — virtual function dispatch (branch misprediction), poor cache locality (tuple spans multiple cache lines), no opportunity for SIMD. Modern CPUs can execute billions of operations/second, but the Volcano model typically achieves < 1% of peak CPU throughput.

## Vectorized Execution

### Batch Processing

Vectorized execution (first in MonetDB/X100, then adopted by ClickHouse, DuckDB, Velox, Arrow) processes **batches of tuples** (typically 64–1024) at a time. Each operator's `next()` returns a *vector* (a columnar batch) rather than a single tuple.

```python
class VectorizedHashJoin:
    def next_batch(self, batch_size=1024):
        right_batch = self.right_child.next_batch(batch_size)
        # Probe with entire batch at once
        probe_keys = right_batch["join_col"]
        matches = self.ht.batch_probe(probe_keys)  # vectorized lookup
        return build_result_batch(right_batch, matches)
```

**Benefits**:
- Amortizes virtual dispatch overhead across batch_size tuples
- Enables tight inner loops that compilers can optimize aggressively
- Natural fit for columnar storage — batches are already column-oriented
- Enables SIMD instructions for filter, arithmetic, and comparison operations

### Columnar Execution Model

In a columnar engine, each operator works on one or more *vectors* (typed arrays) at a time:

```
Filter:   [10, 25, 3, 42, 17, 8, 31]  →  [25, 42, 31]   (WHERE x > 20)
Project:  [25, 42, 31]  →  [50, 84, 62]              (SELECT x * 2)
```

Comparison of execution models:

| Aspect | Volcano (row-at-a-time) | Vectorized | Compiled (JIT) |
|--------|------------------------|------------|----------------|
| Dispatch overhead | Per-tuple (high) | Per-batch (low) | None (inlined) |
| Cache locality | Poor (row-oriented) | Good (column batches) | Excellent (fusion) |
| SIMD potential | None | High (batch ops) | Maximal |
| Branch prediction | Hard (virtual calls) | Good (tight loops) | Excellent (compiled) |
| Startup latency | Low | Low | High (compile time) |
| Used in | PostgreSQL, MySQL | ClickHouse, DuckDB, Velox | HyPer/Umbra, SQL Server Hekaton |

## SIMD in Database Execution

### SIMD Scan Example

A column scan with AVX2 can compare 256 bits (8 × 32-bit integers) per instruction:

```c
// Pseudocode: vectorized filter WHERE age > 30
__m256i threshold = _mm256_set1_epi32(30);
__m256i result = _mm256_cmpgt_epi32(_mm256_loadu_si256(data), threshold);
uint32_t mask = _mm256_movemask_ps(_mm256_castsi256_ps(result));
// mask bits tell us which elements pass the filter
```

ClickHouse processes 16 int32 values per AVX2 instruction for filter predicates, achieving **10-50x speedup** over scalar loops for scan-heavy workloads.

### SIMD-Accelerated Operations

- **Comparison/Filter**: `_mm256_cmpgt_epi32`, `_mm256_cmpeq_epi8`
- **Aggregation**: Horizontal SIMD reduction (sum, min, max) using `_mm256_add_epi32` + `_mm256_hadd_epi32`
- **Hash computation**: SIMD-parallel CRC32 or MurmurHash for hash join build/probe
- **String operations**: SIMD-accelerated LIKE pattern matching, collation comparisons

## JIT Compilation & Code Generation

### The Idea

Instead of interpreting a query plan through a generic operator tree, the engine **compiles the query into native machine code** at runtime. This eliminates all interpretation overhead: no virtual dispatch, no generic branching, tight CPU pipeline utilization.

### HyPer/Umbra (Now Umbra)

HyPer (Neumann & Kemper, 2011) pioneered JIT-compiled query execution in a database. It uses **LLVM** to compile query plans into x86 machine code:

```
Query: SELECT sum(price * quantity) FROM lineitem WHERE shipdate > '2024-01-01'

Compiled pseudo-assembly (simplified):
  mov rax, [col_price + offset]
  imul rax, [col_quantity + offset]
  add rsi, rax            ; accumulate sum
  cmp [col_shipdate], '2024-01-01'
  jle skip
  ; ... emit result
skip:
  add offset, 8
  loop
```

The compiled code runs at near-C++ speed, achieving **billions of tuples/second** for simple aggregations.

### Code Generation Techniques

| Technique | Description | System |
|-----------|-------------|--------|
| **LLVM IR generation** | Emit LLVM intermediate representation, let LLVM optimize + JIT | HyPer/Umbra | 
| **Expression JIT** | Compile only expressions (predicates, arithmetic) into native code | PostgreSQL 12+ (JIT for expressions) |
| **Terra/LuaJIT** | Use LuaJIT for hot-path compilation | (Research prototypes) |
| **Subexpression elimination** | During JIT, detect and eliminate redundant computations across operators | Umbra |
| **Operator fusion** | Merge adjacent operators (filter + project + aggregate) into a single tight loop | ClickHouse (partial), Umbra |

### Operator Fusion

Operator fusion eliminates materialization boundaries between operators by compiling them into a single function:

```
Before fusion:          After fusion:
Filter → Project → Agg    [filter_check AND project_transform AND agg_accumulate]
  (3 batches/intermediates)    (1 tight loop, no intermediate allocations)
```

This dramatically reduces memory traffic and cache misses. DuckDB and Umbra both perform operator fusion.

## Morsel-Driven Parallelism

### The Model

Morsel-driven execution (Leis et al., VLDB 2014; implemented in **Umbra**) splits work into small units called **morsels** (e.g., 64K tuples). Workers pull morsels from a shared work pool using a **work-stealing** scheduler.

```
Query Plan:
  Scan → Filter → HashJoin(Build, Probe) → Aggregate

Morsel assignment (4 workers, table of 256K rows):
  Worker 0: rows 0-64K      (morsel 0)
  Worker 1: rows 64K-128K   (morsel 1)
  Worker 2: rows 128K-192K  (morsel 2)
  Worker 3: rows 192K-256K  (morsel 3)
  
When Worker 0 finishes, it steals morsel 4 from the pool...
```

**Advantages over traditional parallelism**:
- **Load balancing**: No static partitioning — fast workers get more morsels
- **Cache-awareness**: Morsel size tuned to fit in L2/L3 cache
- **Adaptive**: Can adjust parallelism degree at runtime based on CPU load
- **Scheduling flexibility**: Build side of hash join can be parallelized differently than probe side

### Pipelined vs. Materialized Execution

| Aspect | Pipelined | Materialized |
|--------|-----------|-------------|
| Data flow | Tuple/batch streams through operators | Operators write to intermediate storage |
| Memory | Low (no intermediates) | High (spills to disk or large buffers) |
| Parallelism | Limited (pipeline stages) | High (independent sub-plans) |
| Blocking ops | Hard (sort, hash join build) | Natural |
| Used in | Volcano, vectorized engines | Spark, traditional map-reduce |

### Late vs. Early Materialization

In columnar engines, **early materialization** reconstructs full tuples early in the pipeline. **Late materialization** keeps data in columnar form as long as possible, only assembling tuples at the final output stage.

```
Early:  [col_a][col_b][col_c] → reconstruct tuples → filter → project → output
Late:   [col_a] → filter → [col_b] → project → [result_cols] → assemble tuples → output
```

Late materialization reduces memory bandwidth by never reading or processing columns that are not needed. It is especially beneficial when queries touch few columns of wide tables. C-Store/Vertica and MonetDB use late materialization.

## Columnar Encodings

### Dictionary Encoding

Replace column values with integer codes pointing into a dictionary:

```
Original:  ['USA', 'CAN', 'USA', 'MEX', 'CAN', 'USA']
Dictionary: ['USA'=0, 'CAN'=1, 'MEX'=2]
Encoded:   [0, 1, 0, 2, 1, 0]  (8-bit codes if < 256 unique values)
```

Group-by and equality comparisons become integer operations. Memory savings: O(unique_values × value_size) + O(n × code_size). ClickHouse uses dictionary encoding extensively for low-cardinality columns.

### Run-Length Encoding (RLE)

For sorted or nearly-sorted columns, RLE compresses repeated values:

```
Original: [5, 5, 5, 5, 8, 8, 3]
RLE:     [(5, 4), (8, 2), (3, 1)]  → 6 values instead of 7
```

RLE shines for columns with long runs (time series, sorted foreign keys). Aggregation on RLE-encoded data is O(runs) not O(n).

### Bit-Packing

If a column's values fit in k < 32 bits, pack multiple values per machine word:

```
Values: [3, 7, 1, 5]  (fit in 3 bits each)
Packed (32-bit word): 00000111 01100011 00000101
                       ^3    ^7  ^1    ^5
```

4 values per 32-bit word instead of 1 — **4x compression** with simple bit-shift extraction. Parquet uses bit-packing (via `BYTE_STREAM_SPLIT` encoding) for integer columns.

### Zone Maps

Zone maps store min/max statistics for blocks of column data:

```
Block 0 (rows 0-999):   min=10, max=50
Block 1 (rows 1000-1999): min=55, max=90
Block 2 (rows 2000-2999): min=15, max=45

Query: WHERE value > 60
→ Skip block 0 (max=50 < 60) and block 2 (max=45 < 60)
→ Only scan block 1
```

Zone maps are a lightweight form of **data skipping**. Parquet stores them as `ColumnChunk` min/max in metadata. ClickHouse and DuckDB both use zone maps (called "min-max index" in ClickHouse) to skip row groups and granules.

### Roaring Bitmaps

Roaring bitmaps (Chambi et al., 2016) are a compressed bitmap data structure that supports fast set operations (AND, OR, NOT) on large sparse/dense sets. They adaptively choose between three container types based on population count:

| Container Type | When Used | Storage | Operations |
|---------------|-----------|---------|------------|
| **Array** (sorted) | ≤ 4096 elements in 2^16 range | 2 bytes × count | Binary search |
| **Bitmap** (64-bit words) | > 4096 elements in 2^16 range | 8 KB fixed | SIMD bitwise ops |
| **Run container** | Long consecutive runs | var-length (start, length pairs) | Interval arithmetic |

Roaring bitmaps are used for:
- **Bitmap indexes** in databases (clickhouse, infobright)
- **Inverted indexes** in search engines
- **Distinct counting** and set membership
- **ClickHouse** uses Roaring bitmaps internally for `groupArray`, `uniqExact`, and low-cardinality type operations

The key advantage: set intersection (AND) on two Roaring bitmaps uses **SIMD bitwise AND** on bitmap containers (achieving ~1 billion keys/second), binary search intersections on array containers, and interval arithmetic on run containers.

> **Interview Angle**: "Compare vectorized vs. JIT-compiled execution engines." — Cover dispatch overhead, SIMD utilization, operator fusion, startup cost tradeoffs, and name real systems (DuckDB = vectorized, Umbra = JIT, ClickHouse = vectorized + SIMD).

## Comparison of Modern Execution Engines

| System | Execution Model | SIMD | JIT | Parallelism | Columnar Encoding |
|--------|----------------|------|-----|-------------|-------------------|
| **PostgreSQL** | Volcano (row-at-a-time) | No | Expression JIT (12+) | Process-based | No (row store) |
| **ClickHouse** | Vectorized | Extensive (AVX2/AVX-512) | No | Thread-per-query + block-level | Dict, RLE, delta, bit-pack |
| **DuckDB** | Vectorized | Yes (SIMD scans, hash) | Expression JIT | Task-based (morsel-like) | Dict, RLE, const, string |
| **Umbra** | JIT-compiled (LLVM) | Via LLVM auto-vectorization | Full query JIT | Morsel-driven | PAX, zone maps |
| **Velox** (Meta) | Vectorized | Yes | No | Task-based | Dict, RLE, bit-pack, boolean |
| **SQL Server Hekaton** | Compiled (native SPs) | Partial | Natively compiled procedures | Thread-pool | Varies (row-store engine) |

## References

- Leis, V. et al. "Morsel-Driven Parallelism: A NUMA-Aware Query Execution Framework." VLDB, 2014.
- Neumann, T. & Kemper, A. "Unnesting Arbitrary Queries." BTW, 2011. (HyPer)
- Kersten, M.L. et al. "The Vectorwise Data Processing Engine." DASEDA, 2011.
- Zukowski, M. et al. "MonetDB/X100: Hyper-Pipelining Query Execution." CIDR, 2005.
- Chambi, S. et al. "Better Bitmap Performance with Roaring Bitmaps." Software: Practice and Experience, 2016.