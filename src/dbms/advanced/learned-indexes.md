# Learned Indexes

Learned indexes are a class of database index structures that use machine learning models (typically neural networks or piecewise-linear functions) to predict the location of a key, instead of using traditional tree or hash data structures. Introduced by Kraska et al. in 2018 (SIGMOD 2018 paper "The Case for Learned Index Structures"), they can be 2-3× smaller and faster than B-trees for in-memory workloads with skewed key distributions. This page covers the model, the cumulative error concept, the hybrid approach (model + tree), and the production implementations.

## The Insight

A B-tree index is essentially a function: given a key K, return the disk location (or row pointer) of K. The B-tree implements this function with O(log N) comparison operations.

If we could fit a function `f(K) → position` that's faster to evaluate than the B-tree traversal, we'd save the comparison cost. The function need not be exact — it needs to estimate the position, and the B-tree (or linear search) handles the correction.

For sorted data with known distribution, a learned model can predict the position with much less work:

```text
For uniformly distributed keys in [0, 1M]:
  position(K) = K  (linear)
  Error: 0 (perfect prediction)

For Zipfian-distributed keys (heavy head, long tail):
  A piecewise-linear function with 1000 segments fits the CDF.
  position(K) ≈ PLF(K) ± 100 (the linear segment's granularity)
  Error: 100 (need a linear search of 200 entries around the prediction)
```

## The Model

A learned index has three components:

1. **The model**: `f(K) → position`, where `position` is the predicted location in the underlying sorted array.
2. **The error bound**: `|position_actual - f(K)| <= ε`, where ε is the model's maximum prediction error.
3. **The local search**: given `f(K)` and ε, search the range `[f(K) - ε, f(K) + ε]` for the actual position.

The model can be:
- A **piecewise-linear function** (simplest, fastest to evaluate).
- A **neural network** (more expressive, slower to evaluate).
- A **histogram** (interpolated).
- A **decision tree** (for skewed distributions).

## Cumulative Error and Hierarchical Models

The original Kraska paper uses a 2-level model:
- **Top model**: a small neural network (1 hidden layer, ~32 neurons) that outputs a "rough" position prediction with large error.
- **Bottom models**: one per "region" of the keyspace, each a more precise model for that region's keys.

```text
Top model:
  Input: K
  Output: region R and position p (with error ±1000)

Bottom model (R):
  Input: K
  Output: refined position (with error ±100)
```

This is the recursive structure: top model is the "root" of a B-tree, bottom models are the "leaves". The depth can be larger than 2 for very large datasets.

The advantage over B-trees: each model is much smaller (a few KB) than the equivalent B-tree node (~16 KB), and the inference is faster (matrix multiply + comparison vs. tree traversal).

## Hybrid Learned Indexes

Pure learned indexes are difficult to maintain under updates (the model's error bound becomes invalid). Hybrid approaches combine the learned model with a traditional index:

1. **Learned model + B-tree for corrections**: the model predicts the approximate position; a small B-tree corrects the prediction. The B-tree is much smaller than a full B-tree.

2. **Learned model + buffer for inserts**: the model is read-only; inserts go to a small buffer (e.g., a B-tree or LSM-tree). When the buffer fills, the model is rebuilt with the new data.

3. **PGM-Index** (Ferragina & Vinciguerra, 2020): a piecewise-linear model with a layered structure similar to a B-tree. Updates are handled by inserting into a small "side index" that's periodically merged into the main model.

## Production Implementations

### PGM-Index

The PGM-Index (Piecewise Geometric Model) is a C++ library implementing learned indexes with piecewise-linear models. It supports:
- Point queries (find a key).
- Range queries (find all keys in [a, b]).
- Updates (inserts, deletes) via a buffer + rebuild approach.

```cpp
#include "pgm_index.hpp"
PGMIndex<int64_t> index;

index.construct(keys, n);
auto it = index.lower_bound(42);
```

Benchmark: PGM-Index is ~2.5× smaller than a B+ tree on integers, with comparable lookup time.

### ALEX

ALEX (Adaptive Learned Index, Ding et al., 2020) is a learned index designed for read-write workloads. It uses a hybrid structure: a learned model per "node" plus a **gapped array** leaf layout (slots with gaps so inserts shift a few keys instead of rebuilding pages).

ALEX's design choices:
- The model is piecewise-linear with a tunable segment count.
- Inserts go to a small gapped array; the model is rebalanced periodically.
- Deletes are tombstones (lazy deletion).

### What actually ships (the verifiable set)

Published, verifiable deployments of learned indexes are rarer than the papers suggest. Kraska's original work came out of Google Research, and Google has described learned models inside its own storage stacks, but the specific systems above this line are the ones with public documentation. When evaluating vendor claims about learned indexes, ask which of these are documented: model retraining policy, the error bound at lookup time, and what happens to tail latency when a segment's distribution drifts.

## When Learned Indexes Help

- **Skewed key distributions**: heavy head (e.g., a counter, an auto-increment ID) where most queries hit the recent values.
- **In-memory workloads**: the model fits in CPU cache; tree nodes do not.
- **Read-heavy workloads**: the model is read-only; updates require a rebuild.
- **Numeric keys**: the model can interpolate; string keys need encoding first.

## When Learned Indexes Don't Help

- **Uniform key distributions**: a B-tree's comparison-based approach is already optimal; the learned model adds overhead.
- **Write-heavy workloads**: the model rebuild is expensive.
- **High-cardinality string keys**: encoding + model inference can be slower than B-tree traversal.
- **Disk-backed indexes**: the model's locality doesn't help; the bottleneck is disk I/O.

## The ML Community's Skepticism

The original Kraska paper claimed 2-3× speedups, but follow-up work found:
- On real workloads (not synthetic), the speedup is 1.2-1.5×, not 2-3×.
- The model training cost can dominate for short-lived indexes.
- B-trees are extremely well-tuned in production (cache-optimized, SIMD comparisons); competing with them is hard.

The realistic view: learned indexes are a niche optimization for specific workloads (in-memory, skewed, numeric), not a general B-tree replacement.

## Common Pitfalls

1. **Assuming the model is always faster.** For small indexes (< 10K keys), a B-tree is faster (model has setup overhead).

2. **Forgetting the local search cost.** The model predicts the position with some error; the local search (e.g., binary search over ε entries) is real work. If ε is large, the local search dominates.

3. **Forgetting that updates break the model.** A learned model trained on data D has a specific error bound. After inserting K new keys, the model's error bound is invalid; you must rebuild or use a hybrid approach.

4. **Comparing to a poorly-tuned B-tree.** Production B-trees have SIMD comparison, prefetching, and cache-friendly layouts. A "naive B-tree" comparison is unfair.

5. **Forgetting that ML inference is not free.** A 32-neuron MLP is ~5 µs to evaluate on a CPU. A B-tree traversal of depth 4 is ~50 ns (with cache hits). For small indexes, the B-tree wins.

## References

- Kraska et al., "[The Case for Learned Index Structures](https://dl.acm.org/doi/10.1145/3183713.3183736)" (SIGMOD 2018)
- Ferragina & Vinciguerra, "[The PGM-index: a fully-dynamic compressed learned index with provably worst-case update time](https://vldb.org/pvldb/vol13/p1162-ferragina.pdf)" (PVLDB 13(8), 2020)
- Ding et al., "[ALEX: An Updatable Adaptive Learned Index](https://dl.acm.org/doi/10.1145/3318464.3380516)" (SIGMOD 2020)
- Galakatos et al., "[Fitting Trees: A Data-Aware Index Structure](https://www.cs.cmu.edu/~huanrao/papers/sigmod19.pdf)" (SIGMOD 2019)
- [PGM-Index GitHub](https://github.com/gvinciguerra/PGM-index)
- [Marcus et al., "Benchmarking Learned Indexes"](https://db.in.tum.de/~radler/beyond_b_trees.pdf) (Datenbank-Spektrum 2020)
- [The Case Against Learned Indexes (Viktor Leis, 2020)](https://www.cs.cit.tum.de/~leis/)
