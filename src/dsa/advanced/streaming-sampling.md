# Reservoir Sampling: Fair Coin Flips for Infinite Streams

A uniform sample of $k$ items is the most basic summary statistics can ask for, yet
on a stream it is genuinely hard. The naive fix, flipping a coin per item with
fixed probability $f$, gives a $\mathrm{Bin}(n, f)$ random sample size: memory is
unbounded in the tail and accuracy is unpredictable on any given run, which is
exactly what PostgreSQL's `BERNOULLI` table method does when it selects "individual
rows independently with the specified probability" [8]. The textbook alternative,
a simple random sample of exactly $k$ without replacement, needs $n$ before the
first draw, and a stream never provides $n$. Reservoir sampling removes both
defects: keep $k$ slots, touch each item once, and at every moment the reservoir
is a uniform $k$-subset of everything seen so far, in $O(k)$ memory and one pass.
[Ch 147](../chapters/ch147-streaming-algorithms.md) and
[Ch 179](../chapters/ch179-fisher-yates-reservoir.md) state Algorithm R at
interview depth; this page goes underneath that: the induction proof, the jump
distributions that make it fast, the bottom-k and weighted variants, coordinated
sampling, and the ways each breaks in production. See
[Streaming and Sublinear Algorithms](streaming-sublinear.md) for the sketches this
complements, and [SRE exemplars](../../sre/exemplars.md) for a production case
where a reservoir is deliberately *not* population-representative.

## 1. Algorithm R: One RNG Call per Item

Vitter's Algorithm R fills the reservoir with the first $k$ items, then for item
$i$ (counting from 1) draws a uniform integer $j \in [0, i)$ and replaces slot $j$
with the new item when $j < k$ [1]. Each arrival fights for a random slot with
probability $k/i$, and target slots are uniform, so no slot or item is privileged.

```text
reservoir k=5, item #13 arrives (items 1..12 seen so far)

slots:   [ a3 ][ b7 ][ x1 ][ q4 ][ m2 ]
                        ^ j = random(0..12)
 j in {0..4}: replace that slot        j in {5..12}: nothing changes
 j = 2 -> [ a3 ][ b7 ][ #13 ][ q4 ][ m2 ]   accepted (prob 5/13)
```

**Unbiasedness by induction.** After $t \geq k$ items, every item is in the
reservoir with probability $k/t$; the base case $t = k$ is the filled reservoir.
Item $t{+}1$ enters with probability $k/(t{+}1)$, and any incumbent is evicted
exactly when the newcomer draws its slot, probability
$(k/(t{+}1)) \cdot (1/k) = 1/(t{+}1)$, so it survives with probability $t/(t{+}1)$
and $P(\text{in reservoir at } t{+}1) = (k/t)\cdot t/(t{+}1) = k/(t{+}1)$, which
restores uniformity for old and new items alike. The proof uses only two
properties, acceptance probability $k/i$ and a uniform target slot, and every
variant below preserves both. The cost is one RNG call per item forever, even
though the answer stops caring about $n$ almost immediately.

## 2. Skipping Ahead: Vitter's Z and Li's L

The acceptance probability $k/i$ decays as the stream grows, so replacements
become rare and the per-item RNG call is almost always wasted. The fix is to
jump: compute how many items to skip before the next replacement. The gap $G$
between consecutive replacements follows from Algorithm R itself; after position
$t$, item $t{+}s$ accepts with probability $k/(t{+}s)$ and everything between
rejects, so for $s \geq 1$:

```text
P(G = s) = k/(t+s) * (1 - k/(t+1)) * ... * (1 - k/(t+s-1))
            <-- t+1 .. t+s-1 all reject --> <-- t+s accepts -->
```

For $t \gg k$ the product is nearly $(1 - k/t)^{s-1}$, so $G$ is approximately
geometric with success probability $k/t$ and one uniform draw produces the entire
skip. Both classic papers turn this into exact machinery: Vitter's Algorithm Z
samples the exact negative-hypergeometric gap law with a bounded-rejection
acceptance-rejection step [1][2], and Li's Algorithm L generates the gap in
expected constant time, giving total time $O(n(1 + \log(N/n)))$ for a sample of
size $n$ from a file of size $N$ [3]. RNG calls drop from $N$ to
$O(k(1 + \log(N/k)))$; with random access, the skipped items are never read.

## 3. Bottom-k: Order Statistics That Merge

A different family keeps the $k$ *smallest* values of $h(x)$ for a uniform hash
$h$ (or, weighted, the $k$ largest keys $u^{1/w}$ of Section 4). Because keys
totally order the universe, the sample is a deterministic function of which items
arrived, and that determinism buys three things Algorithm R cannot. First, a
bottom-$k$ sample of $n$ distinct items *is* a simple random sample of exactly
$k$: i.i.d. uniform keys make every $k$-subset equally likely to own the $k$
smallest keys, with none of the Binomial size variance of Bernoulli sampling.
Second, the sketch estimates $n$ for free: if $\theta$ is the $k$-th smallest key
then $\theta \sim \mathrm{Beta}(k, n{-}k{+}1)$, so $E[(k-1)/\theta] = n$ exactly
and the delta method gives relative standard error about $1/\sqrt{k-2}$, the KMV
estimator introduced for distinct counting by Bar-Yossef et al. [6]. Third, the
sketches compose: the bottom-$k$ of a union is the bottom-$k$ of merged keys, and
when two sketches share one hash function their samples are *coordinated*, so the
intersection of samples estimates the intersection of sets -- precisely what the
Apache DataSketches Theta Sketch Framework exploits for set expressions over
multiple streams in production [12], and why coordinated bottom-$k$ underlies
set-operation estimation while reservoir R's slots carry no order to merge.

```text
stream --> reservoir core --> exactly-k sample --> proportion / mean /
   ...       R | A-Res | b-k                        quantile queries
        keys = h(x) or u^(1/w); theta = k-th smallest -> n-hat = (k-1)/theta
        shared h(x) across sketches => coordinated set ops
```

| Method | Space | Sample size | RNG work | Weighted | Bonus |
|---|---|---|---|---|---|
| Bernoulli coin | $O(1)$ | $\mathrm{Bin}(n,f)$, random | $n$ draws | no | streaming $n$ via count/$f$ |
| Algorithm R | $O(k)$ | exactly $k$ | $n$ draws | no | simplest to state |
| Algorithm Z / L | $O(k)$ | exactly $k$ | $O(k(1{+}\log(N/k)))$ draws | no | jumps; seekable input skips reads |
| Bottom-k / KMV | $O(k)$ | exactly $k$ | $n$ hashes | no | $\hat{n} = (k-1)/\theta$; mergeable |
| A-Res | $O(k)$ | exactly $k$ | $n$ keys | yes, $\propto w$ | reduces to bottom-k |
| A-ExpJ | $O(k)$ | exactly $k$ | $O(k(1{+}\log(N/k)))$ keys | yes, $\propto w$ | weighted plus jumps |

## 4. Weighted Reservoirs: A-Res and A-ExpJ

Uniform sampling wastes effort when items carry importance: sampling log lines
uniformly overweights chatty debug hosts, and a 10x-repeated impression should
count 10x. Efraimidis and Spirakis gave the one-line fix: draw $u \sim U(0,1)$
and assign the key $K_i = u^{1/w_i}$, keeping the $k$ largest keys seen so far
[4]. The trick is that $K_i$ is not uniform: its CDF is $P(K_i \leq x) = x^{w_i}$
on $[0,1]$, a power distribution whose exponent is the weight. For $k = 1$ the
inclusion probability follows from one integral:

```text
P(i wins) = INTEGRAL_0^1  w_i * x^(w_i - 1) * PROD_{j != i} x^(w_j)  dx
          = w_i * INTEGRAL_0^1 x^(W - 1) dx     (W = w_1 + ... + w_m)
          = w_i / W
```

so the heaviest item wins exactly in proportion to its weight, and the paper's
general-$k$ argument extends this to the full reservoir as a weighted
without-replacement sample. A-Res costs one key per item; the same authors'
A-ExpJ keeps the largest keys in a priority queue and jumps the stream with
exponentially distributed gaps, mirroring Algorithm L [5]. Weighted selection
itself is much older, with Chao's 1982 unequal-probability plan as the
survey-statistics ancestor [7], but A-Res made it streamable in $O(k)$ memory.
Setting every $w_i$ equal collapses A-Res to plain bottom-$k$ on $u$, which shows
Algorithm R and the weighted family are two faces of the same idea.

## 5. Biases in Production: Partitions, Blocks, and Seeds

**Per-partition reservoirs skew toward small partitions.** A distributed job that
runs a size-$k$ reservoir per partition and concatenates the results produces a
*stratified* sample with $k$ slots per stratum, not a uniform sample. With ten
equal sub-reservoirs, a shard holding 1% of the data receives 10% of the union's
slots, so a class concentrated in small shards is overweighted by up to the
ratio of shard sizes. Spark is careful here: `RDD.takeSample(withReplacement=false)`
runs `SamplingUtils.reservoirSampleAndCount` per partition and tracks the counts
the naive version discards, then rebalances across partitions [9][10], while the
SQL side offers `DataFrame.sample` (row fraction with a seed) and `sampleBy`
(per-stratum fractions). Hand-rolled `mapPartitions` reservoirs do none of this;
the mergeable fix is coordinated bottom-$k$ on a shared hash.

**Block-level sampling inherits physical clustering.** PostgreSQL's `SYSTEM`
method picks whole heap pages, which the docs admit is "significantly faster than
the BERNOULLI method when small sampling percentages are specified" but "may
return a less-random sample of the table as a result of clustering effects" [8].
Rows inserted together carry correlated timestamps, users, or states, so a page
sample can silently estimate the *recent* table rather than the table; prefer
`BERNOULLI` when row-level unbiasedness matters and `REPEATABLE` when it must be
reproducible. The same seed discipline applies to Spark's `seed` arguments, where
reusing one fixed seed across correlated jobs silently correlates your samples.
A reservoir is also uniform over items, not over time: point it at a bursty log
and the answer is "representative of all history", not "representative of now";
recency needs windowed or decayed variants, and a stratified-by-design reservoir,
one per tenant or shard, is a different estimator entirely -- the exact trap
documented for exemplar sampling in [SRE exemplars](../../sre/exemplars.md).

## 6. Demo: One Stream, Two Samplers

The script seeds `random` (42), builds a 10,000-item stream that is 70% red /
20% green / 10% blue, and runs Algorithm R plus weighted A-Res with weights red
1.0 / green 2.5 / blue 7.0, whose implied proportions are 36.84 / 26.32 / 36.84.
For $k = 400$ the expected sampling error of a uniform reservoir is about
$\sqrt{p(1-p)/k} \approx 2.3$ percentage points per class, so both reservoirs
should land within roughly one standard error of their ground truths.

```python
import bisect
import random

random.seed(42)

# synthetic stream: 70% red, 20% green, 10% blue, shuffled into one pass order
STREAM = ["red"] * 7000 + ["green"] * 2000 + ["blue"] * 1000
random.shuffle(STREAM)
TRUE = {"red": 70.0, "green": 20.0, "blue": 10.0}
WEIGHT = {"red": 1.0, "green": 2.5, "blue": 7.0}
W_TOTAL = sum(WEIGHT[c] * STREAM.count(c) for c in WEIGHT)
WT = {c: 100.0 * WEIGHT[c] * STREAM.count(c) / W_TOTAL for c in WEIGHT}

def algorithm_r(stream, k):
    # Vitter's R: item i (1-based) replaces a uniform slot with probability k/i
    res = list(stream[:k])
    for i in range(k, len(stream)):
        j = random.randint(0, i)  # i+1 items seen so far; slots are 0..k-1
        if j < k:
            res[j] = stream[i]
    return res

def a_res(stream, k):
    # Efraimidis-Spirakis A-Res: keep the k largest keys u**(1/w)
    kept = []
    for item in stream:
        key = random.random() ** (1.0 / WEIGHT[item])
        if len(kept) < k:
            bisect.insort(kept, (key, item))
        elif kept[0][0] < key:
            kept.pop(0)
            bisect.insort(kept, (key, item))
    return [item for _, item in kept]

def show(name, sample, truth):
    print(name)
    for c in ("red", "green", "blue"):
        p = 100.0 * sample.count(c) / len(sample)
        print("  %-5s %6.2f%%   (%+5.2f pp vs %.2f%%)" % (c, p, p - truth[c], truth[c]))

print("stream: 10000 items, truth red 70.0% green 20.0% blue 10.0%, reservoir k=400")
print()
show("Algorithm R (uniform reservoir):", algorithm_r(STREAM, 400), TRUE)
print()
print("A-Res weights red=1.0 green=2.5 blue=7.0 -> expected red %.2f%% green %.2f%% blue %.2f%%"
      % (WT["red"], WT["green"], WT["blue"]))
show("A-Res weighted reservoir:", a_res(STREAM, 400), WT)
```

Real output:

```text
stream: 10000 items, truth red 70.0% green 20.0% blue 10.0%, reservoir k=400

Algorithm R (uniform reservoir):
  red    68.50%   (-1.50 pp vs 70.00%)
  green  19.50%   (-0.50 pp vs 20.00%)
  blue   12.00%   (+2.00 pp vs 10.00%)

A-Res weights red=1.0 green=2.5 blue=7.0 -> expected red 36.84% green 26.32% blue 36.84%
A-Res weighted reservoir:
  red    36.25%   (-0.59 pp vs 36.84%)
  green  26.25%   (-0.07 pp vs 26.32%)
  blue   37.50%   (+0.66 pp vs 36.84%)
```

Algorithm R lands within one standard error of the 70/20/10 truth, and A-Res
within half of one of the weight-implied truth: one stream, reweighted by Section 4.

## 7. Interview Q&A

**Q: Ten partitions each keep a 40-slot reservoir. Why isn't the concatenation a uniform sample of 400?**
A: Each partition's reservoir is uniform *within* that partition, so the
concatenation is a stratified sample with equal per-stratum weight: a 100-item
shard contributes as many slots as a 10,000-item shard, and any class concentrated
in small shards is overweighted by up to the ratio of shard sizes. Fix it the way
Spark's `takeSample` does, by tracking per-partition counts and re-sampling
proportionally, or switch to bottom-$k$ on a hash shared across partitions, which
merges by key order with no counts needed.

**Q: Show that key u^(1/w) wins with probability w/W when keeping the largest key.**
A: If $u \sim U(0,1)$ then $K = u^{1/w}$ has CDF $P(K \leq x) = x^w$ on $[0,1]$.
The probability item $i$ owns the maximum is the integral from Section 4,
$w_i/W$; the Efraimidis-Spirakis paper extends the argument to the
general-$k$ reservoir [4].

**Q: Why does bottom-k beat a Bernoulli coin for distinct-count estimation?**
A: With $\theta$ the $k$-th smallest hash, $\hat{n} = (k-1)/\theta$ is exactly
unbiased and has relative standard error about $1/\sqrt{k-2}$ at a *fixed* sketch
size [6]. A Bernoulli sketch's distinct count is $\mathrm{Bin}(n, f)$: you pay
the binomial variance of the count on top of the order statistics, and its memory
footprint is itself a random variable. Fixed size is what makes accuracy
guarantees, and SLAs built on them, meaningful.

## References

1. J. S. Vitter, "Random sampling with a reservoir," *ACM Transactions on Mathematical Software* 11(1):37-57, 1985. <https://doi.org/10.1145/3147.3165>
2. J. S. Vitter, "Faster methods for random sampling," *Communications of the ACM* 27(7):703-718, 1984. <https://doi.org/10.1145/358105.893>
3. K.-H. Li, "Reservoir-sampling algorithms of time complexity $O(n(1 + \log(N/n)))$," *ACM Transactions on Mathematical Software* 20(4):481-493, 1994. <https://doi.org/10.1145/198429.198435>
4. P. S. Efraimidis and P. G. Spirakis, "Weighted random sampling with a reservoir," *Information Processing Letters* 97(5):181-185, 2006. <https://doi.org/10.1016/j.ipl.2005.11.003>
5. P. S. Efraimidis, "Weighted random sampling over data streams," in *Algorithms, Probability, Networks, and Games* (LNCS 9295), pp. 183-195, 2015. <https://doi.org/10.1007/978-3-319-24024-4_12>
6. Z. Bar-Yossef, T. S. Jayram, R. Kumar, D. Sivakumar, and L. Trevisan, "Counting distinct elements in a data stream," *RANDOM 2002* (LNCS 2483), pp. 1-10, 2002. <https://doi.org/10.1007/3-540-45726-7_1>
7. M. T. Chao, "A general purpose unequal probability sampling plan," *Biometrika* 69(3):653-656, 1982. <https://doi.org/10.1093/biomet/69.3.653>
8. PostgreSQL documentation, "SELECT" (TABLESAMPLE clause: BERNOULLI, SYSTEM, REPEATABLE). <https://www.postgresql.org/docs/current/sql-select.html>
9. Apache Spark API docs, `pyspark.sql.DataFrame.sample`. <https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/api/pyspark.sql.DataFrame.sample.html>
10. Apache Spark source, `org.apache.spark.util.random.SamplingUtils` (per-partition reservoir with counts). <https://github.com/apache/spark/blob/master/core/src/main/scala/org/apache/spark/util/random/SamplingUtils.scala>
11. Apache DataSketches, "Reservoir Sampling Java." <https://datasketches.apache.org/docs/Sampling/ReservoirSamplingJava.html>
12. Apache DataSketches, "Theta Sketches" (coordinated sampling for set expressions). <https://datasketches.apache.org/docs/Theta/ThetaSketches.html>
