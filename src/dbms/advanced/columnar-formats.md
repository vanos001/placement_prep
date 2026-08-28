# Columnar Formats: Parquet, ORC, Arrow, and the Lakehouse Layer

Row-oriented storage answers "fetch this record"; columnar storage
answers "aggregate that column over a billion rows" - and modern
analytics lives on the second answer. The format is also a contract:
Parquet files encode not just values but *statistics* (min/max per row
group) that let a query engine skip 99% of the bytes without reading
them, and encodings (dictionary, RLE, delta) that shrink text columns
10x before compression even starts. This page walks the Parquet layout
top to bottom, contrasts ORC and the Arrow in-memory story, and covers
the lakehouse metadata layer (Iceberg/Delta) that turned folders of
files into transactional tables.

Execution context: [vectorized execution](./vectorized-execution.md)
consumes these formats batch-at-a-time (which is why Arrow exists),
[execution engines](./execution-engines.md) decide when column pruning
pays, and [sketch algorithms](./sketch-algorithms.md) ride on the same
stats pages for approximate queries.

## Parquet layout, top to bottom

```text
  Parquet file
  +------------------------------------------------------------------+
  | row group 0            (typically 128MB-1GB uncompressed)         |
  |   column chunk: colA   (all of colA for these rows)               |
  |     page: dictionary | page: data (RLE/dict/delta encoded)        |
  |     page: statistics (min, max, null count)                       |
  |   column chunk: colB   ...                                        |
  | row group 1  ...                                                  |
  | footer: schema, encodings, offset index, column/row-group stats   |
  +------------------------------------------------------------------+
```

The key structural decisions:

- **Row groups** are the unit of parallelism and pruning: engines skip
  whole groups whose min/max can't satisfy the predicate.
- **Column chunks** group one column's bytes contiguously - the actual
  I/O locality win; a SUM(colA) reads only colA chunks.
- **Pages** (~1MB) are the compression unit, each carrying optional
  statistics; the **offset index** in the footer lets engines seek to
  individual pages inside a chunk (page-level skipping).
- **Encodings stack**: dictionary-encode distinct values, RLE the
  repetition/definition levels and low-cardinality runs, delta-encode
  sorted numerics - then feed the page to snappy/zstd. Text logs with
  1% distinct values routinely land at 10-20x raw.

## ORC vs Parquet vs Arrow, honestly

| dimension        | Parquet                  | ORC                     | Arrow (in memory)        |
|------------------|--------------------------|-------------------------|--------------------------|
| unit             | row group / column chunk | stripe / column         | record batch / column    |
| predicate index  | min/max stats, page index| bloom filters + row index| (none - not a file format for that) |
| ACID/lakehouse   | via Iceberg/Delta layer  | via Hive ACID (legacy)  | n/a                      |
| ecosystem center | Spark/DuckDB/Snowflake exchange | Hive/Presto heritage | zero-copy interchange between engines |
| nested data      | Dremel repetition/definition levels | similar, different encoding | validity bitmaps + offsets |

Arrow is not a competitor: it is the *in-memory* representation files
get decoded into, standardized so engines exchange batches without
serialization. The end-to-end scan path is: file bytes -> page decode ->
arrow arrays -> vectorized operators - and the format's design choices
(stat placement, encoding choice) are what make the first two stages
cheap.

## The lakehouse layer: Iceberg and Delta

Files on S3 have no transactions. Iceberg/Delta/Hudi add a metadata
tree above them: snapshot manifests list data files, commits are
atomic pointer swaps, and time travel is "read the manifest from
snapshot N". What that buys: ACID writes with optimistic concurrency,
schema/Partition evolution without rewrite, and engine-agnostic
consistency. The cost model shifts: the table becomes *copy-on-write*
(for read-optimized snapshots) or *merge-on-read* (delta files compacted
later) - the compaction-vs-read-amplification dial every lakehouse
operator ends up tuning. The classic operational failure is small-file
proliferation: streaming ingests at 1-minute cadence create millions of
KB-scale files; manifests bloat, planning takes minutes, and the fix is
compaction jobs - the LSM story in warehouse clothing (see
[lsm-tree-deep](../../storage/advanced/lsm-tree-deep.md)).

## The demo: encodings and pruning, end to end

```python
#!/usr/bin/env python3
"""Parquet-style column page: dictionary + RLE encoding, min/max stats,
and a predicate-pushdown simulation showing which row groups get skipped.

Column: 'status' over 3 row groups (values: ok, retry, failed, timeout).
Deterministic; no external libraries."""


def rle_encode(values):
    runs = []
    for v in values:
        if runs and runs[-1][0] == v:
            runs[-1][1] += 1
        else:
            runs.append([v, 1])
    return runs


ROW_GROUPS = {
    # 3 row groups of 40 rows each
    "rg0": ["ok"] * 38 + ["retry"] * 2,
    "rg1": ["retry"] * 10 + ["ok"] * 20 + ["failed"] * 10,
    "rg2": ["failed"] * 5 + ["timeout"] * 35,
}

print("=== A. per-row-group dictionary + RLE encoding ===")
total_plain, total_enc = 0, 0
for rg, values in ROW_GROUPS.items():
    plain = len(values) * 8                     # 8-byte strings, fixed-width
    distinct = sorted(set(values))
    dict_ids = {d: i for i, d in enumerate(distinct)}
    ids = [dict_ids[v] for v in values]
    runs = rle_encode(ids)
    # dict page: len(distinct) * 8 bytes; data page: 1 byte id + 1 byte count per run
    enc = len(distinct) * 8 + sum(2 for _ in runs)
    total_plain += plain
    total_enc += enc
    print(f"  {rg}: plain={plain:>4}B  dict({len(distinct)})+rle({len(runs)} runs)="
          f"{enc:>4}B  ratio={plain/enc:4.1f}x")
print(f"  total: plain={total_plain}B encoded={total_enc}B "
      f"({total_plain/total_enc:.1f}x)")

print()
print("=== B. min/max statistics pruning (predicate: status = 'ok') ===")
# For categorical columns the 'min/max' pair is really the distinct set
# stored in stats; an engine skips groups whose stats exclude 'ok'.
for rg, values in ROW_GROUPS.items():
    distinct = sorted(set(values))
    can_skip = "ok" not in distinct
    print(f"  {rg}: distinct={distinct} -> "
          f"{'SKIP (no ok)' if can_skip else 'READ'}")
skipped = sum(1 for v in ROW_GROUPS.values() if "ok" not in set(v))
print(f"  engine reads {len(ROW_GROUPS) - skipped}/3 row groups "
      f"({100 * (len(ROW_GROUPS) - skipped) / len(ROW_GROUPS):.0f}% of the scan)")

print()
print("=== C. what stats CANNOT prune: correlated predicates ===")
print("  predicate: status = 'failed' AND latency > 100ms")
print("  status stats prune rg0/rg1; latency stats live in a DIFFERENT")
print("  column's chunk - cross-column selectivity needs page-level joins")
print("  of the two chunk's matching rows (or per-page correlated stats).")
```

```text
=== A. per-row-group dictionary + RLE encoding ===
  rg0: plain= 320B  dict(2)+rle(2 runs)=  20B  ratio=16.0x
  rg1: plain= 320B  dict(3)+rle(3 runs)=  30B  ratio=10.7x
  rg2: plain= 320B  dict(2)+rle(2 runs)=  20B  ratio=16.0x
  total: plain=960B encoded=70B (13.7x)

=== B. min/max statistics pruning (predicate: status = 'ok') ===
  rg0: distinct=['ok', 'retry'] -> READ
  rg1: distinct=['failed', 'ok', 'retry'] -> READ
  rg2: distinct=['failed', 'timeout'] -> SKIP (no ok)
  engine reads 2/3 row groups (67% of the scan)

=== C. what stats CANNOT prune: correlated predicates ===
  predicate: status = 'failed' AND latency > 100ms
  status stats prune rg0/rg1; latency stats live in a DIFFERENT
  column's chunk - cross-column selectivity needs page-level joins
  of the two chunk's matching rows (or per-page correlated stats).
```

## Interview probes

- A Parquet file has 500 row groups; a query filters on a column whose
  stats live per row group: walk the exact I/O sequence with and without
  the offset index.
- Why does Dremel-style repetition/definition level encoding matter for
  nested data, and what does a NULL list cost vs a NULL scalar?
- Iceberg commits are pointer swaps on metadata: what isolation anomaly
  can two concurrent writers hit, and which Iceberg mechanism resolves
  it?
- Your streaming ingest produces 5M files/day: name the failure mode
  three ways (planner, manifest, S3 LIST) and the compaction profile
  that fixes each.

## References

1. [Parquet format specification](https://parquet.apache.org/docs/) -
   row groups, pages, encodings, and the Dremel-level nesting model.
2. [Apache Arrow format](https://arrow.apache.org/docs/format/Columnar.html)
   - the in-memory columnar standard: buffers, validity bitmaps, flight
   interchange.
3. [Apache Iceberg documentation](https://iceberg.apache.org/docs/latest/)
   - snapshot/manifest metadata layering, partition evolution, time
   travel.
4. [Vectorized execution (this repo)](./vectorized-execution.md) - the
   consumer side of the format: why batches and decoded arrays matter.
