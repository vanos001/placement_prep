# Late Materialization in Columnar Engines

A row store never asks *when* to assemble tuples: its heap scan emits full
rows, so every operator sees slot-oriented tuples. A column store must
decide: stitch referenced columns into whole tuples at the scan (early
materialization), or assemble rows once, near the top of the plan (late
materialization).

## Definitions: early vs late materialization

- **Early materialization**: values for every column a (sub)plan references
  are assembled into complete tuples at or below the scan operator. Each
  downstream operator - filters, joins, aggregates - carries full-width
  rows. This is the only choice for a row store, whose heap pages
  interleave column values a few dozen to a few hundred bytes apart, so
  reading one attribute drags in the whole row.
- **Late materialization**: each operator carries a **position list**
  (tuple IDs into the table) plus references to the column chunks those
  positions index. Columns a given operator does not need are never read.
  Tuples are reconstructed once - at the final projection, a sort, a
  pipeline break - or never, when an aggregate folds values directly.

Two subtleties keep the definitions honest. Materialization is
per-pipeline, not per-query: X100 and VectorWise rebuild thin tuples at
pipeline breaks while staying positional within each pipeline. And "early"
is relative: stitching four columns at the scan is earlier than deferring
reconstruction to the projection - both later than a heap row scan.

## Position lists through the operator tree

Late materialization changes what operators pass, not just what they read.
A filter consumes a flat chunk plus positions and emits a shorter position
list; a fetch operator binds positions back to column values only where
needed. The same plan under both policies:

```text
Plan: SELECT sum(out1), sum(out2) FROM t WHERE p1 AND p2
      N = 100M rows, q = p1 selectivity, s = combined selectivity

LATE (positional pipeline)            EARLY (slot tuples)
--------------------------            --------------------
      HashAgg(out1, out2)                   HashAgg
        ^ s x N tuples, 2 cols (8 B)        ^ s x N full tuples (64 B)
      Fetch out1,out2 by position         Filter2: p2
        ^ s x N positions + chunks         ^ q x N full tuples
      Filter2: p2 on fetched values       Filter1: p1
        ^ q x N positions + chunks         ^ N full tuples
      Fetch p2 for survivors              Scan (heap)
        ^ q x N positions                  ^ all 20 columns interleaved
      Filter1: p1 on flat p1 chunk
        ^ N positions + chunks
      Scan: p1, p2 chunks only
        ^ N x 4 B flat values per column
```

Every arrow on the left carries `(position list, chunk reference)` pairs;
every arrow on the right carries whole rows. The payload columns `out1`
and `out2` are touched exactly once, for the `s x N` surviving positions,
at the fetch just below the aggregate.

## What late materialization wins

- **Wide schemas, narrow queries.** A query touching 4 columns of a 20
  column, 64 B/row table skips the other 48 B/row entirely; nothing reads
  or buffers them.
- **Low selectivity filters.** Few positions survive the predicates, so
  the one-time stitch at the top touches a handful of values, while the
  early path has already pushed full rows through every operator.
- **Cache-friendly scans.** Predicates evaluate over flat, contiguous
  arrays - sequential loads, full SIMD lanes, happy prefetchers - instead
  of walking interleaved row images.
- **Compression-aware execution.** RLE and dictionary-encoded chunks let a
  predicate emit positions directly from runs or codes (below), and
  untouched columns are never decompressed at all.

## What it costs, and when early materialization wins

- **Re-binding positions to rows.** Any operator that needs a whole row -
  hash join output with wide payloads, DISTINCT over many columns, row-wise
  UDFs, UPDATE/DELETE - becomes a materialization point. A hash join build
  on full rows must materialize its payload columns up front; the probe
  side emits position pairs that someone must stitch back together.
- **Indirection overhead.** Position-list bookkeeping runs through every
  operator, and gathering values by position is data-dependent random
  access that defeats sequential prefetch. At 100% selectivity the late
  path in the model below pays position plus gather traffic on every row.
- **Operator complexity.** Each operator needs a positional and a row-wise
  variant, and the optimizer must place fetch (stitching) operators.

Early materialization wins when: selectivity is high *and* the query
references most of the row width (the crossover below); the query is a
point lookup via a secondary index (tens of rows - just fetch rows); or
the workload is row-oriented (OLTP updates, `SELECT *`, exports).

## Engine implementations

| Engine | Policy | Mechanism |
|---|---|---|
| MonetDB/X100 | Late within pipelines | Vectorized primitives over flat arrays; thin tuples rebuilt at pipeline breaks |
| VectorWise | Late | X100 lineage; positional intermediate results, late tuple reconstruction |
| C-Store | Late | Sorted columns per projection; join indexes bind positions across sort orders |
| ClickHouse | Column-oriented blocks | PREWHERE reads filter columns first, then fetches other columns for passing rows |
| DuckDB | Late per row group | Row-group storage + vectorized scans; filters narrow selections before other columns are processed |
| Snowflake | Pruning at micro-partitions | Columnar micro-partitions with min/max metadata; unreferenced columns never read |

- **MonetDB/X100** (CIDR 2005) runs vectorized primitives (~100-1000
  values from one column) over positional intermediates, rebuilding tuples
  only where the plan needs them. **VectorWise** (Actian, its commercial
  successor) kept the model; the SIGMOD 2008 study by Abadi et al. analyzed
  early vs late materialization across layouts and fed VectorWise's engine.
- **C-Store** (VLDB 2005) stores each projection as sorted columns and
  reconstructs logical rows on demand, using join indexes to bind positions
  across projections with different sort orders.
- **ClickHouse** exposes the idea as a two-stage filter: `PREWHERE`
  evaluates cheap, selective conditions on their own columns, then reads
  the remaining `WHERE` columns only for rows that passed - trading one
  extra column read for skipping the rest.
- **DuckDB** pairs row-group storage with vectorized execution: scans
  evaluate predicates over vectors and carry selection vectors forward, so
  payload columns are materialized only for the surviving fraction.
- **Snowflake** prunes whole micro-partitions via per-column min/max
  metadata before any column is scanned, then reads only referenced
  columns - pruning composes with, but is not, materialization policy.

## Zone maps, encodings, and position lists

- **Zone maps / min-max pruning.** Per-row-group min/max metadata prunes
  before the scan reads data pages (ClickHouse MergeTree granules, Snowflake
  micro-partitions); survivors become the initial position list. Pruning is
  free under both policies, but only late also skips unreferenced columns.
- **RLE.** A chunk stored as `(value, start, length)` runs answers `value =
  c` with run-level tests, emitting position ranges without touching
  per-row data - positions fall out of the encoding itself.
- **Dictionary encoding.** The predicate runs over dictionary codes; the
  matching codes' positions form the output list, and payload columns stay
  encoded and unread - encodings and late materialization compound.

## A cost model for the stitching decision

The script prices the plan above two ways: early, a slot-oriented engine
reading all 20 columns and pushing 64 B tuples through both filters and
the aggregate; late, two flat 4 B predicate columns, 4 B positions through
the filters, and one gather of the payload columns for survivors.

```python
# Cost model: bytes moved per query, early vs late materialization.
# SELECT sum(out1), sum(out2) FROM t WHERE p1 AND p2
# Table: 20 columns, 100,000,000 rows, 64 B/row; p1, p2, out1, out2 are
# 4 B columns. Each filter passes sqrt(s) of its input; s = combined sel.

import math

N, ROW = 100_000_000, 64   # rows, bytes per full row
PRED, PAY, POS = 4, 4, 4   # bytes: predicate value, payload value, position
GB = 1e9


def early(s):
    """Slot-oriented row engine: full 64 B tuples at every stage."""
    q = math.sqrt(s)                  # per-stage selectivity
    return N * ROW * (1 + 1 + q + s)  # scan + filter1 + filter2 + aggregate


def late(s):
    """Positional engine: flat predicate columns, threaded positions,
    payload columns gathered once for surviving positions."""
    q = math.sqrt(s)
    return (2 * N * PRED              # scan p1, p2 as flat arrays
            + POS * N * (1 + q)       # positions through filter1
            + q * N * (PRED + POS)    # fetch p2 values for survivors
            + POS * N * (q + s)       # positions through filter2
            + s * N * (2 * PAY + POS + 2 * PAY)  # gather + stitch tuples
            + s * N * 2 * PAY)        # aggregate over 2 x 4 B tuples


print("Early vs late materialization: bytes moved per query")
print("Table: 20 columns x 100,000,000 rows, 64 B/row; query touches 4 columns")
print("Query: SELECT sum(out1), sum(out2) FROM t WHERE p1 AND p2")
print()
print("combined sel |   early GB |    late GB | late/early")
print("-------------+------------+------------+-----------")
for s in (0.001, 0.01, 0.1, 1.0):
    e, l = early(s), late(s)
    print(f"{s:>10.1%} | {e / GB:>10.2f} | {l / GB:>10.2f} | {e / l:>8.1f}x")

e_lo, l_lo, e_hi, l_hi = early(0.001), late(0.001), early(1.0), late(1.0)
print()
print("Wide 64 B row: late wins at every modeled selectivity; the advantage")
print(f"erodes from {e_lo / l_lo:.1f}x at 0.1% selectivity to {e_hi / l_hi:.1f}x at 100%,")
print("because position-list and gather traffic grow with s while the early")
print("path keeps paying full row width.")

# Crossover for a narrow table with ONLY the 4 referenced columns (8 B/row):
# early = 8*N*(2 + q + s); late = N*(12 + 16*q + 32*s), q = sqrt(s).
# Equal when 8*(2 + x + x^2) = 12 + 16*x + 32*x^2, x = sqrt(s)
#   -> 6*x^2 + 2*x - 1 = 0  ->  x = (sqrt(7) - 1) / 6
x = (math.sqrt(7) - 1) / 6
print()
print("Narrow 8 B row (only referenced columns exist): crossover at")
print(f"s = {x * x:.1%}. Below it late wins; above it early stitching wins,")
print("since every surviving row pays position-list plus gather overhead.")
```

```text
Early vs late materialization: bytes moved per query
Table: 20 columns x 100,000,000 rows, 64 B/row; query touches 4 columns
Query: SELECT sum(out1), sum(out2) FROM t WHERE p1 AND p2

combined sel |   early GB |    late GB | late/early
-------------+------------+------------+-----------
      0.1% |      13.01 |       1.25 |     10.4x
      1.0% |      13.50 |       1.39 |      9.7x
     10.0% |      15.46 |       2.03 |      7.6x
    100.0% |      25.60 |       6.00 |      4.3x

Wide 64 B row: late wins at every modeled selectivity; the advantage
erodes from 10.4x at 0.1% selectivity to 4.3x at 100%,
because position-list and gather traffic grow with s while the early
path keeps paying full row width.

Narrow 8 B row (only referenced columns exist): crossover at
s = 7.5%. Below it late wins; above it early stitching wins,
since every surviving row pays position-list plus gather overhead.
```

Reading the table: with a wide row late dominates at every selectivity
because 48 of 64 B per row are never touched; the advantage erodes with
rising selectivity but never disappears. The crossover appears only when
the row holds little else: at 8 B/row, bookkeeping and gathers lose above
~7.5% combined selectivity - so stitch placement is an optimizer decision.

## Interview probes

- Walk `SELECT a, sum(b) FROM t WHERE c > 10 GROUP BY a` on a column store:
  what does each operator pass - values, positions, or tuples - and where
  is the single stitch point?
- Why must PREWHERE take *cheap and selective* conditions? What stays out?
- `SELECT *` over 100M rows after a 0.5% filter: does late materialization
  still help, and where does the answer flip as the filter fraction grows?

## See also

- [Columnar Formats](./columnar-formats.md) - on-disk layouts and encodings that position lists index into.
- [Vectorized Execution](./vectorized-execution.md) - the batch model that X100/DuckDB-style positional operators run inside.
- [Execution Engines](./execution-engines.md) - materialization policy across iterator, vectorized, and compiled engines.
- [Column Stores](../storage/column-stores.md) - storage-level column layout basics that this page assumes.
- [ClickHouse](../../data-engineering/clickhouse.md) - engine internals of the PREWHERE/WHERE two-stage filter described above.

## References

1. Zukowski, Heman, Boncz. "MonetDB/X100: A Hyper-Pipelined Query Execution Engine." CIDR 2005. https://cidrdb.org/cidr2005/papers/P19.pdf
2. Stonebraker, Abadi, Batkin, et al. "C-Store: A Column-oriented DBMS." VLDB 2005. https://www.vldb.org/conf/2005/papers/p553-stonebraker.pdf
3. Abadi, Myers, DeWitt, Madden. "Column-Stores vs. Row-Stores: How Simulation Makes it Easy to Get the Best of Both Worlds." SIGMOD 2008 (materialization-policy analysis behind VectorWise-style engines).
4. ClickHouse documentation. "PREWHERE." https://clickhouse.com/docs/sql-reference/statements/select/prewhere
5. ClickHouse documentation. "MergeTree" (primary key granules, minmax indexes). https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree
6. DuckDB documentation. "Storage Internals" (row groups, segments). https://duckdb.org/docs/stable/internals/storage
7. Snowflake documentation. "Understanding Micro-partitions" (min/max pruning). https://docs.snowflake.com/en/user-guide/tables-micro-partitions
