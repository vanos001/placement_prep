# Cardinality Estimation

Every plan choice the optimizer makes rests on one number: how many rows come out
of each operator. Hash join vs nested loop, broadcast vs shuffle, memory grant
size, join order search pruning - all of it is driven by row counts nobody
actually knows until the query runs. This page is about where those numbers come
from, why they are wrong in predictable ways, and what modern engines do about it.

## Selectivity: the one primitive

Selectivity of a predicate is the fraction of rows it passes. Everything else is
arithmetic: estimated rows = input rows x selectivity. The classic rules:

| Predicate | Estimate | Breaks when |
|-----------|----------|-------------|
| col = v | freq(v) from MCV, else 1 / n_distinct | skew hides v below MCV threshold |
| col < c | histogram interpolation within bucket | bucket straddles a spike |
| col LIKE 'abc%' | range estimate on prefix | prefix shorter than histogram granularity |
| col LIKE '%abc%' | default constant | always; the data is uninformative |
| p1 AND p2 | sel1 x sel2 | p1 and p2 correlated |
| col1 = col2 (join) | 1 / max(NDV1, NDV2) | key distribution skewed |

PostgreSQL ships the fallback constants in `src/include/utils/selfuncs.h`:
`DEFAULT_EQ_SEL = 0.005` (equality with no stats), `DEFAULT_INEQ_SEL = 0.3333`
(a bare `<` or `>`), `DEFAULT_RANGE_INEQ_SEL = 0.005` (`a < x AND x < b` when
statistics punted), and `DEFAULT_NUM_DISTINCT = 200`. Note that 1/0.005 = 200:
the defaults are mutually consistent, which tells you how old and deliberate
they are. When a value appears in no MCV list and no histogram bucket can
resolve it, the engine quietly substitutes these numbers.

## What ANALYZE actually stores

PostgreSQL's `ANALYZE` samples about `300 x statistics_target` rows (30,000 at
the default target of 100) and writes per-column summaries into `pg_statistic`,
exposed read-only through `pg_stats`. Per column you get:

- `n_distinct`: distinct count. Positive = absolute count. Negative = a
  fraction of table rows, so `-1.0` means "every row unique" and scales with
  the table as it grows.
- `most_common_vals` + `most_common_freqs`: the MCV list - exact frequencies
  for the heavy hitters the sample could see.
- `histogram_bounds`: an **equi-depth** histogram over the values that are NOT
  in the MCV list - 100+ buckets, each holding roughly the same number of rows,
  so each bucket is one uniformity assumption instead of the whole domain.
- `correlation`: how closely physical row order matches column order; this
  feeds the index-scan I/O cost model, not row counts.

```text
column stats = MCV list (exact, heavy values)
             + equi-depth histogram (light values)

values:   [ 7 ][ 7 ][ 7 ][ 12 ][ 13 ][ 19 ][ 23 ][ 23 ][ 41 ]...
            \___ MCV: v=7, freq=0.31 ___/ \____ histogram buckets ____/
             stored as (value, freq)        bounds [13,19,23,41,...]
             selectivity = exact 0.31       each bucket ~equal row count,
                                            linear interpolation inside
```

The MCV/histogram split is the whole trick: skew is handled exactly where it is
visible, and the histogram's per-bucket uniformity assumption only applies to
the well-behaved remainder.

## The four classic failure modes

**1. Skew below the MCV threshold.** A value covering 0.4% of rows is far too
important to ignore but never makes the MCV list, so equality gets the
`1 / n_distinct` treatment. The demo below reproduces this exactly: a 109x
underestimate while the neighboring MCV value estimates within 1%.

**2. n_distinct = -1 lies after growth.** `ANALYZE` on a small table where the
sample happened to be all-distinct records `n_distinct = -1` (unique per row).
The table then grows into a 5-value status column with millions of rows. Every
equality estimate becomes `rows / (rows x 1.0) = 1` row, join estimates
collapse, and the optimizer nested-loops a million probes. The fix is manual:
`ALTER TABLE ... ALTER COLUMN ... SET (n_distinct = 5)`.

**3. Correlated predicates.** `WHERE city = 'Boston' AND state = 'MA'` - the
independence assumption multiplies 0.02 x 0.09, but real selectivity is ~0.02
since Boston implies MA. Each extra correlated clause compounds the error
multiplicatively. PostgreSQL's answer since v10 is `CREATE STATISTICS` extended
statistics: functional dependencies, per-column-group `ndistinct`, and MCV
lists over column combinations. Its built-in guardrail for the most common
correlation - a range pair on the same column - is exact arithmetic, not
multiplication: for `x > a AND x < b`, selectivity is `hi + lo - 1` where `hi`
and `lo` are the single-sided estimates, with clamps against roundoff (a
slightly negative result becomes 1e-10; a punted pair becomes the 0.005
default). Generic ANDs still multiply.

**4. Sampling noise itself.** With a 30k-row sample, a value present in 0.1% of
rows appears ~30 times - fine. A value present 5 times in the table appears
maybe once, maybe never. MCV frequencies and histogram bucket weights carry
sampling error of roughly sqrt(freq/n_sample); tight range estimates (like
"last 5 minutes") also suffer because they sit in a bucket edge that has
physically moved since the last `ANALYZE`. Stale statistics are not a special
case - they are the steady state; autovacuum's analyze triggers are a
compromise, not a guarantee.

## Join cardinality

The textbook formula for an equality join is:

```text
|R join S| = |R| x |S| / max(V(R,a), V(S,b))
```

where V is the distinct count of the join key. The max is because containment
of key sets is assumed: the smaller key domain is presumed to be a subset of
the larger. Three ways this breaks:

- **Fanout skew**: a foreign key where one value (order of a wholesale
  customer) covers 90% of rows, but `n_distinct` says 1,000. The formula
  predicts |R|/1000 per joining row; reality is 0.9 x |R| for that one value.
- **The -1 disaster**: if either side has `n_distinct = -1` on the join key,
  V grows with the table and estimates shrink toward 0 - the classic
  "nested loop on a huge join" incident.
- **Cross-correlated keys**: the formula assumes key sets align; for
  partitioned or sharded data where ranges barely overlap, it overestimates.

Modern engines short-circuit this with declarative referential integrity:
PostgreSQL's planner checks for foreign key constraints first
(`get_foreign_key_join_selectivity` in `costsize.c`) and estimates an FK join
as exactly one match per outer row instead of trusting NDVs.

## Beyond heuristics

- **Query-time sampling**: Oracle's dynamic sampling (levels 0-11) scans a
  slice of hard tables at parse time when existing statistics look thin;
  engines like Snowflake and BigQuery lean on runtime table metadata plus
  sketch-based approximations instead of per-column histograms.
- **Learned models**: the MSCN network (Kipf et al., CIDR 2019) encodes a query
  plan as sets of tables/predicates/join conditions and predicts join
  cardinality end-to-end, beating percentile-based heuristics on correlated
  joins. Marcus and Papaemmanouil's plan-structured networks predict physical
  operator costs, which subsumes cardinality. Both papers report errors 10x
  lower than classical estimation on their benchmarks - and both face the same
  production problem: the model silently rots when the data distribution
  shifts, and unlike `ANALYZE` there is no refresh command. Hybrid designs
  (model + guardrails that fall back to classical estimates on drift) are the
  current pragmatic answer.

## Demo: mini-ANALYZE on skewed data

A faithful miniature of the PostgreSQL scheme - sample 300 x target rows, MCV
for values heavier than one histogram bucket, equi-depth histogram for the
rest, linear interpolation within buckets:

```python
import math
import random

random.seed(42)

N = 100_000
vals = []
for _ in range(N):
    r = random.random()
    if r < 0.10:
        vals.append(100.0)                    # hot value: 10% of all rows
    elif r < 0.104:
        vals.append(55.0)                     # warm value: 0.4%, below MCV radar
    else:
        vals.append(math.exp(random.gauss(3.0, 1.0)))   # lognormal body

# --- ANALYZE phase (mirrors PostgreSQL's approach) -------------------------
target = 100
B = 50                                            # histogram bucket count
sample = random.choices(vals, k=300 * target)     # 300 * statistics_target

# MCV: PG keeps the most frequent sampled values; a value that out-freqs a
# whole equi-depth bucket (len(sample)/B) cannot be represented by the
# histogram, so it goes into most_common_vals instead.
freq = {}
for v in sample:
    freq[v] = freq.get(v, 0) + 1
mcv_thresh = len(sample) / B
mcv = {v: c / len(sample) for v, c in freq.items() if c >= mcv_thresh}

# Equi-depth histogram over the remaining (non-MCV) values: B buckets,
# each holding ~len(rest)/B sampled rows
rest = sorted(v for v in sample if v not in mcv)
step = max(1, len(rest) // B)
bounds = [rest[i * step] for i in range(B) if i * step < len(rest)]
bounds.append(rest[-1])
nbuckets = len(bounds) - 1
# bucket occupancy converted from sample rows to full-table rows
rows_per_bucket = N * len(rest) / (nbuckets * len(sample))

ndv_rest = len(set(rest))
nonmcv_rows = 1.0 - sum(mcv.values())

print(f"rows={N}  sample={len(sample)}  MCV values={len(mcv)}  "
      f"hist buckets={nbuckets}  ndv(rest)~{ndv_rest}")
top_mcv = sorted(mcv.items(), key=lambda kv: -kv[1])[:4]
print(f"top MCV: {[(round(v,1), round(f,4)) for v, f in top_mcv]}")

def est_range(lo, hi):
    s = sum(f for v, f in mcv.items() if lo <= v <= hi)          # MCV exact
    if hi < bounds[0] or lo > bounds[-1]:
        return s * N
    i = max(0, next((k for k in range(nbuckets) if bounds[k + 1] >= lo), nbuckets - 1))
    frac_sum = 0.0
    while i < nbuckets and bounds[i] <= hi:
        bl, bh = bounds[i], bounds[i + 1]
        overlap = min(hi, bh) - max(lo, bl)
        frac_sum += max(0.0, overlap) / (bh - bl) if bh > bl else 0.0
        i += 1
    return s * N + frac_sum * rows_per_bucket

def est_eq(v):
    if v in mcv:
        return mcv[v] * N
    return (nonmcv_rows / ndv_rest) * N          # 1/n_distinct assumption

def actual(lo, hi):
    return sum(1 for v in vals if lo <= v <= hi)

queries = [
    ("eq  v=100.0 (hot MCV)",        100.0, 100.0),
    ("eq  v=55.0  (warm, non-MCV)",    55.0,  55.0),
    ("eq  v=42.0 (absent value)",     42.0,  42.0),
    ("range v < 10",                  -1.0,  10.0),
    ("range 10 <= v <= 40",           10.0,  40.0),
    ("range 20 <= v <= 22 (tight)",   20.0,  22.0),
    ("range v >= 95 (incl. spike)",   95.0,  1e18),
]
print(f"\n{'predicate':<28}{'estimated':>11}{'actual':>9}{'ratio':>8}")
for label, lo, hi in queries:
    if lo == hi:
        e = est_eq(lo)
    else:
        e = est_range(lo, hi)
    a = actual(lo, hi)
    ratio = e / a if a else float('inf')
    print(f"{label:<28}{e:>11.0f}{a:>9}{ratio:>8.2f}")
```

```text
rows=100000  sample=30000  MCV values=1  hist buckets=50  ndv(rest)~23184
top MCV: [(100.0, 0.1007)]

predicate                     estimated   actual   ratio
eq  v=100.0 (hot MCV)             10070    10076    1.00
eq  v=55.0  (warm, non-MCV)           4      436    0.01
eq  v=42.0 (absent value)             4        0     inf
range v < 10                      21445    21579    0.99
range 10 <= v <= 40               46124    45839    1.01
range 20 <= v <= 22 (tight)        3538     3398    1.04
range v >= 95 (incl. spike)       15590    15525    1.00
```

Read the table like an `EXPLAIN ANALYZE` row estimate diff: ranges on the
smooth body land within a few percent (equi-depth interpolation works), the MCV
value is exact, and the two equality estimates on non-MCV values show the
n_distinct failure from both sides - 109x under on a real value, a nonzero
guess on an absent one.

## Interview takeaways

- When `EXPLAIN ANALYZE` shows estimated vs actual rows off by orders of
  magnitude, the diagnosis order is: stale stats, correlated columns, skew
  below MCV resolution, then `n_distinct` from a small-table analyze.
- `default_statistics_target` trades plan time and `pg_statistic` space for
  histogram resolution; raising it fixes misestimates on irregular columns
  without touching queries.
- A plan can be 100% "correct" given its estimates and still catastrophic -
  the bug is in the stats, not the join algorithm.
- Extended statistics (`CREATE STATISTICS`) exist precisely because the
  independence assumption is the default, and it is almost always wrong on
  dimensionally related columns.

## References

- PostgreSQL: [Statistics Used by the Planner](https://www.postgresql.org/docs/current/planner-stats.html)
- PostgreSQL: [pg_statistic catalog](https://www.postgresql.org/docs/current/catalog-pg-statistic.html)
- Kipf et al., [Learned Cardinalities: Estimating Correlated Joins with Deep Learning](https://arxiv.org/abs/1809.00677) (MSCN, CIDR 2019)
- Marcus & Papaemmanouil, [Plan-Structured Deep Neural Network Models for Query Performance Prediction](https://arxiv.org/abs/1902.00132)
- CMU 15-721: [Cost Models and Cardinality Estimation lecture notes (Pavlo)](https://15721.courses.cs.cmu.edu/spring2020/slides/22-costmodels.pdf)
