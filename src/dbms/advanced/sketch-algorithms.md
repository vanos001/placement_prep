# Sketch Algorithms in Analytics Engines

Analytics dashboards hide a quiet trade: the queries users actually run --
distinct visitors, p99 latency, top talkers -- are the ones exact engines
serve worst. Sketches answer them with fixed memory and a *known* error
bound. This page covers the four sketches every analytics stack ships --
HyperLogLog, Count-Min, t-digest/KLL, Theta -- with storage/accuracy numbers
and the systems that run them. Streaming-model theory (lower bounds, AMS,
Misra-Gries) lives in
[Streaming Algorithms](../../dsa/chapters/ch147-streaming-algorithms.md) and
[Streaming and Sublinear Techniques](../../dsa/advanced/streaming-sublinear.md);
survey context is in [Approximate Query Processing & Privacy](approximate-privacy.md).

## Why COUNT(DISTINCT) and p99 break at scale

Three failure shapes, all common interview material:

- **Exact distinct sets grow without bound.** 10^8 distinct user IDs per day
  is gigabytes of hash set, and `GROUP BY country` multiplies it; sorting for
  dedup turns an O(1)-scan aggregate into a blocking O(n log n) pipeline.
- **Percentiles from fixed histograms are lies under skew.** Equal-width
  buckets over 0-10s latencies leave the true p99 anywhere inside one bucket;
  SLO math needs tail resolution exactly where uniform buckets are coarsest.
- **Set algebra does not compose over estimates.** `uv(A and B)` is not
  derivable from `uv(A)` and `uv(B)` alone; subtracting two +-2% estimates of
  nearly-equal quantities produces noise, not an answer.

Each sketch below is a different contract: mergeable counts (HLL), one-sided
frequency bounds (Count-Min), tail-accurate ranks (t-digest, KLL),
intersections (Theta).

## HyperLogLog: registers and the harmonic mean

HLL (Flajolet, Fusy, Gandouet, Meunier; AOFA 2007) hashes every element to a
64-bit value split into a register index (top `p` bits) and a payload, and
keeps per register the **maximum position of the first 1-bit** ever seen in
the payload -- a "we saw a 1-in-2^k rarity" witness.

```text
hash = 77d1...b2e4   (64 bits)
  idx: 010000110100     rest: 1101000100...
       (12 bits ->      rank = position of first 1 in rest = 1
        register        register[idx] = max(register[idx], 1)
        #3268)

registers (m = 2^12 = 4096, 6 bits each):
[ 0 0 0 ... 3 ... 0 0 ]     only maxima are kept
             ^ register 3268 witnessed rarity 2^-3
```

The estimate is a scaled harmonic mean of `2^register` values:
`E = alpha_m * m^2 / sum_j 2^-M[j]` with `alpha_m = 0.7213/(1 + 1.079/m)`.
Harmonic means are dominated by the *small* register values, which tames the
variance and yields the `1.04/sqrt(m)` relative standard error. Two
corrections finish the algorithm:

- **Linear counting** for small cardinalities: if `E <= 2.5*m` and some
  registers are zero, use `m * ln(m/zeros)` (the raw estimator is biased
  there).
- **Sparse encoding**: until a few hundred registers are touched, store
  `(idx, rank)` pairs in a sorted list -- Redis starts small HLLs at a few
  hundred bytes before promoting them to the dense 12 KB layout.

Merging is per-register `max`: associative and commutative, so HLLs merge
across shards, days, and nodes. What is impossible: intersection --
HLL(A intersect B) is not recoverable from two sketches.

## Count-Min: one-sided error by construction

Count-Min (Cormode & Muthukrishnan, 2005) is a `d x w` counter array with `d`
independent hash functions; updates add 1 to one counter per row, and a query
for item `a` returns `min over rows of row[hash_i(a)]`. Collisions only ever
add *other* items' counts, so every row overestimates and the minimum can
only help. With `w = ceil(e/eps)` columns and `d = ceil(ln(1/delta))` rows,
`estimate <= a + eps*N` with probability `1 - delta` -- and it **never
underestimates**, a contract sampling cannot give. For eps = 1%, delta = 1%:
272 columns x 5 rows of 32-bit counters, about 5.4 KB regardless of stream
length.

Production uses: heavy hitters (Count-Min plus a small candidate heap),
anomaly/abuse detection, and the **inner-product trick** -- `sum_i A[i]*B[i]`
is estimable from two sketches with a one-sided flavor, which is how engines
approximate join sizes without touching data twice. One sharp edge: naive
subtraction (deletions) breaks the one-sided story; use conservative updates.

## Quantiles: t-digest vs KLL

Rank queries (p50/p99/p99.9) are where fixed histograms die.

- **t-digest** (Dunning) compresses observations into centroids, merging
  aggressively near the median and finely at the tails. Error is **relative
  to the rank's distance from the center**, so p99.9 stays sharp while p50 is
  sloppy by design. Cost: merges are lossy and mildly order-dependent -- two
  digests built in different insertion orders differ slightly, which
  complicates replicated aggregation.
- **KLL** (Karnin, Lang, Liberty, FOCS 2016) is a merge tree of sorted
  samples with probabilistic compaction: **additive normalized rank error**
  (default k=200 gives 1.65% per Apache DataSketches), near-optimal
  `O((1/eps) log log(1/eps))` space, and exact, order-independent merges.

| Property | t-digest | KLL | fixed histogram |
|---|---|---|---|
| Error contract | relative, best at tails | additive rank error, uniform | bucket width |
| p99.9 quality | excellent | good | poor |
| p50 quality | coarse by design | good | good |
| Merge determinism | order-dependent, lossy | exact, order-independent | lossless |
| Memory driver | compression parameter | k (e.g. 200) | bucket count |
| Typical home | app metrics (Prometheus-family, Elasticsearch) | engines via DataSketches (Druid, Spark, PostgreSQL ext) | everything else |

Rule of thumb: monitoring request-latency p99s -> t-digest; engine-side
`approx_percentile` over stored data -> KLL or DDSketch-style structures.

## Theta sketches: set operations beyond counts

Theta sketches (Apache DataSketches, built on classic threshold sampling from
Bar-Yossef et al.) keep a uniform *sample of the distinct universe*: keys
whose hash falls below a threshold `theta` are retained exactly. Because the
retained entries are real keys, **intersection and difference become set
operations over retained keys** -- `A intersect B` is "keys surviving in
both", with error from the sampling rate. HLL cannot do this at any price;
"users who hit page A *and* page B" is the canonical Theta workload, at tens
of KB (default 4096-entry table) rather than HLL's few KB.

## Storage vs accuracy

| Sketch | Typical config | Memory | Error contract | Answers |
|---|---|---|---|---|
| HLL | m = 4096 registers | 3 KB dense | 1.62% relative (1.04/sqrt(m)) | distinct count |
| HLL (Redis) | 16384 registers | 12 KB | 0.81% relative (docs) | distinct count |
| HLL sparse | under ~1k distinct so far | bytes to ~1 KB | same as dense | distinct count |
| Count-Min | 272 x 5, 32-bit | 5.4 KB | one-sided +1% of N at 99% conf | frequency, heavy hitters |
| KLL | k = 200 | a few KB | 1.65% normalized rank error | any quantile, CDF, rank |
| t-digest | compression 100 | a few KB | relative, tail-weighted | any quantile |
| Theta | 4096-entry table | tens of KB | about 1.6% on set results | counts, intersect, diff |

## Where these run in production

- **Redis**: `PFADD`/`PFCOUNT`/`PFMERGE` are HLL end to end; the official
  docs specify "up to 12 KB of memory" and "a standard error rate of 0.81%".
  Usage patterns: [Redis Advanced Patterns](../../redis/advanced-patterns.md).
- **Trino/Presto**: `approx_distinct()` (HLL), `approx_percentile()`
  (quantile/t-digest families), plus DataSketches HLL and Theta function
  families in Trino.
- **BigQuery**: `APPROX_COUNT_DISTINCT`, `APPROX_QUANTILES`, `APPROX_TOP_COUNT`
  in standard SQL -- all sketch-backed.
- **Apache DataSketches**: the reference library (HLL, Theta, KLL, frequent
  items) embedded in Druid, Spark, Hive, PostgreSQL extensions.

## Runnable: a 3 KB HLL in 60 lines

Deterministic (splitmix64-style mixing, standard library only): estimates
four synthetic cardinalities with `m = 4096` registers, then checks that
merging two half-sketches reproduces the single-run estimate.

```python
# Demo: toy HyperLogLog with 2^12 registers, deterministic splitmix64-style hashing.
# Estimates distinct counts for synthetic cardinalities, checks mergeability.
import math

MASK64 = (1 << 64) - 1
P = 12                      # 2^12 = 4096 registers
M = 1 << P
B = 64 - P                  # bits left for rank computation

def h64(x):                 # deterministic 64-bit mix (splitmix64 finalizer)
    z = (x + 0x9E3779B97F4A7C15) & MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
    return z ^ (z >> 31)

class ToyHLL:
    def __init__(self):
        self.reg = [0] * M

    def add(self, x):
        h = h64(x)
        idx = h >> B                      # top P bits pick the register
        rest = h & ((1 << B) - 1)         # low 52 bits
        rank = B - rest.bit_length() + 1  # position of first 1-bit, 1-based
        if rank > self.reg[idx]:
            self.reg[idx] = rank

    def count(self):
        alpha = 0.7213 / (1.0 + 1.079 / M)
        est = alpha * M * M / sum(2.0 ** (-r) for r in self.reg)
        zeros = self.reg.count(0)
        if est <= 2.5 * M and zeros > 0:  # small-range fix: linear counting
            est = M * math.log(M / zeros)
        return est

    def merge(self, other):
        h = ToyHLL()
        h.reg = [max(a, b) for a, b in zip(self.reg, other.reg)]
        return h

print(f"registers m={M}  theoretical SE = 1.04/sqrt(m) = {1.04 / M ** 0.5 * 100:.2f}%")
print(f"dense storage: {M} registers x 6 bits = {M * 6 // 8} bytes")
print()
print(f"{'true n':>9} | {'estimate':>9} | {'rel err':>7}")
print("-" * 34)
for n in (1_000, 10_000, 100_000, 1_000_000):
    h = ToyHLL()
    for x in range(n):                    # n distinct values
        h.add(x * 2 + 1)
    est = h.count()
    print(f"{n:>9} | {est:>9.0f} | {abs(est - n) / n * 100:>6.2f}%")

# mergeability: union estimate from merged halves == single-run estimate
a, b, direct = ToyHLL(), ToyHLL(), ToyHLL()
for x in range(0, 600_000, 2):
    a.add(x * 3); direct.add(x * 3)
for x in range(1, 600_000, 2):
    b.add(x * 3); direct.add(x * 3)
print()
print(f"true union size          : 600000")
print(f"merged halves estimate   : {a.merge(b).count():.0f}")
print(f"single-run estimate      : {direct.count():.0f}")
```

Real output (Python 3.12; errors vary with the hash choice but sit near the
1.62% design point):

```text
registers m=4096  theoretical SE = 1.04/sqrt(m) = 1.62%
dense storage: 4096 registers x 6 bits = 3072 bytes

   true n |  estimate | rel err
----------------------------------
     1000 |      1012 |   1.24%
    10000 |     10365 |   3.65%
   100000 |     99130 |   0.87%
  1000000 |    991527 |   0.85%

true union size          : 600000
merged halves estimate   : 614162
single-run estimate      : 614162
```

Two honest imperfections: 10000 lands at 3.65% (about 2.3 sigma -- sketches
give *distributions*, not per-run promises), and the 1000 case only works
because linear counting takes over below `2.5*m`.

## How interviewers probe this

- "Why can't two HLLs be intersected?" -- Register maxima lose key identity;
  the harmonic mean of a difference of estimates has error comparable to the
  estimates themselves.
- "A Count-Min answer for a rare item is 3x its true count -- bug?" -- No: a
  collision absorbed `eps*N`; widen `w`, or use conservative updates /
  heavy-hitter structures when rare-item precision matters.
- "p99.9 per datacenter per hour, merged later, reproducibly." -- KLL
  (order-independent merges) rather than t-digest.

## References

1. Flajolet, Fusy, Gandouet, Meunier - HyperLogLog: the analysis of a near-optimal cardinality estimation algorithm (AOFA 2007): <http://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf>
2. Cormode & Muthukrishnan - An improved data stream summary: the count-min sketch and its applications (J. Algorithms 2005): <https://sites.google.com/site/countminsketch/>
3. Karnin, Lang, Liberty - Optimal Quantile Approximation in Streams (FOCS 2016, the KLL sketch): <https://arxiv.org/abs/1603.05346>
4. Apache DataSketches - KLL sketch documentation (default k=200, 1.65% rank error): <https://datasketches.apache.org/docs/KLL/KLLSketch.html>
5. Redis - HyperLogLog data type (12 KB, 0.81% standard error): <https://redis.io/docs/latest/develop/data-types/probabilistic/hyperloglogs/>
