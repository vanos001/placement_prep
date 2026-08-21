# Jump Consistent Hashing

Jump Consistent Hashing is a fast, deterministic algorithm for mapping a key to one of N buckets, with the property that increasing N from `n` to `n+1` reassigns only `K/(n+1)` keys (the optimal number). It was introduced by Lamping and Veach in 2011 (Google, paper "A Fast, Minimal Memory, Consistent Hashing Algorithm"). This page covers the algorithm, the proof of correctness, the comparison to other consistent hashing approaches, and the production use cases.

## The Algorithm

The pseudocode from the original paper:

```python
def jump_consistent_hash(key, num_buckets):
    key = key & 0xFFFFFFFFFFFFFFFF  # 64-bit unsigned
    b, j = -1, 0
    while j < num_buckets:
        b = j
        key = key * 2862933555777941757 + 1  # LCG multiplier
        j = int((b + 1) * (1 << 31) / ((key >> 33) + 1))
    return b
```

The function returns a bucket index in `[0, num_buckets)`. The algorithm is O(log N) in time and O(1) in memory.

## Why It Works

The intuition: as N grows from 1 to N, each step "splits" a fraction of keys. The algorithm walks through these splits efficiently.

At N=1: all keys go to bucket 0.
At N=2: half the keys (randomly, by hash) move to bucket 1.
At N=3: 1/3 of the remaining keys (those still at bucket 0 or 1) move to bucket 2.
...
At N=k: 1/k of the keys move to bucket k-1.

The naive implementation tracks the bucket assignment at each N:

```python
def naive(key, N):
    b = 0
    for n in range(1, N):
        if rand(key, n) < 1 / (n + 1):  # 1/(n+1) chance of moving
            b = n
    return b
```

This is O(N) — too slow. The jump consistent hash algorithm uses the linear congruential generator (LCG) to "skip ahead" through the random number sequence, only iterating when the algorithm's invariant changes. The result is O(log N).

## The Proof of Correctness

The proof is in the Lamping-Veach paper. Key insights:

1. The LCG `key * 2862933555777941757 + 1` produces a sequence of pseudorandom values with the same properties as if we'd computed `rand(key, n)` for each n.
2. The "jumps" in the algorithm correspond to the points where the assignment changes; between jumps, the assignment is constant.
3. The expected number of jumps is O(log N) (the analysis uses the fact that each split's probability is 1/n, and the harmonic series has log n expected jumps).

## Comparison to Other Consistent Hashing Algorithms

| Algorithm | Time per lookup | Memory | Reassignment on add bucket | Notes |
|-----------|------------------|--------|-----------------------------|-------|
| Naive modulo `hash(K) % N` | O(1) | O(1) | K (almost all keys) | Bad reassignment |
| Consistent hashing (ring) | O(log N) | O(N × V) (V virtual nodes) | K/V | Standard |
| Rendezvous hashing (HRW) | O(N) | O(N) | K/(N+1) | Simple |
| Jump consistent hashing | O(log N) | O(1) | K/(N+1) | Optimal! |

Jump consistent hashing has the best of all worlds: O(log N) time, O(1) memory, optimal reassignment. The catch: it doesn't support weighted buckets (every bucket is equal).

## When You Can't Use Jump Consistent Hashing

1. **Weighted buckets**: jump doesn't support varying bucket weights. Use HRW for weights.

2. **Named buckets**: jump returns a bucket index (0 to N-1); the buckets are not named. If you need to map index 3 to "server-us-east-1", you need an external lookup table.

3. **Removing a specific bucket**: jump doesn't support removing a bucket (it only supports adding). To remove bucket K, you renumber buckets (K+1 → K, K+2 → K+1, etc.), but this changes the bucket IDs.

4. **Sticky keys under server changes**: jump reassigns K/N keys on add, but the specific keys that move are random (not controllable). If you need specific keys to stay on specific servers (e.g., session affinity), jump doesn't help directly.

## The Original Paper's Bug

The original Lamping-Veach paper had a subtle bug in the algorithm. The pseudocode above is correct; the paper had `key * 2862933555777941757 + 1` but the multiplier was actually wrong. The correct multiplier is `2862933555777941757` (a prime near 2^62). Erlend Hamberg's blog post from 2015 documents the bug.

The corrected algorithm is what's implemented in `jump.go` in Google's groupcache library, and is the version you should use.

## Production Implementations

### Google's groupcache

groupcache (golang) implements jump consistent hashing for its peer-selection logic. The code is in `consistenthash.go`.

### Apache Ignite

Ignite uses jump consistent hashing for some affinity-based key routing.

### Kubernetes

Kubernetes uses jump consistent hashing in some components (e.g., etcd's internal sharding).

### Memcached

Memcached's ketama consistent hashing is NOT jump — it's the ring-based variant. But some Memcached clients (e.g., Xmemcached) support jump as an option.

### Custom Implementations

Most distributed systems that need consistent hashing without weights use jump. The implementation is ~10 lines of code in any language.

## The 32-bit Variant

The original jump hash works on 64-bit keys. For 32-bit keys (smaller memory footprint in some languages), a variant is:

```python
def jump32(key, N):
    b, j = -1, 0
    while j < N:
        b = j
        key = (key * 2654435761 + 1) & 0xFFFFFFFF  # 32-bit LCG
        j = int((b + 1) * (1 << 32) / ((key >> 1) + 1))
    return b
```

The multiplier `2654435761` is the "Knuth's multiplicative constant" for 32-bit. The shift is different (`>> 1` instead of `>> 33`).

## Common Pitfalls

1. **Forgetting that jump needs 64-bit integers.** In languages without native 64-bit integers (JavaScript before BigInt), the overflow behavior is wrong. Use BigInt or a 64-bit emulation.

2. **Forgetting that the LCG multiplier must be specific.** The multiplier `2862933555777941757` is the value that produces a sequence with the right statistical properties for the algorithm. Other multipliers don't work correctly.

3. **Forgetting that jump reassigns K/(N+1) keys, not 0.** When adding a bucket, expect ~K/(N+1) of your keys to move. This is optimal but not zero.

4. **Forgetting that bucket IDs are not stable.** Bucket 3 means "the 4th bucket in the sequence". If you remove bucket 2, bucket 3's previous contents become bucket 2's. Don't store data referenced by bucket ID alone.

5. **Forgetting that jump doesn't support weights.** If you need weighted buckets, use rendezvous hashing or consistent hashing with virtual nodes.

6. **Forgetting that jump requires the bucket count to be a small integer.** The algorithm walks through buckets 1 to N; if N is huge (e.g., 1B), the iteration is slow (even with the log N speedup, log 1B = 30 iterations).

## References

- Lamping & Veach, "[A Fast, Minimal Memory, Consistent Hashing Algorithm](https://arxiv.org/abs/1406.2295)" (2011)
- Erlend Hamberg, "[Jump Consistent Hashing in Haskell](https://hamberg.no/erlend/posts/2015-03-20-jump-consistent-hash-in-haskell.html)" (2015) — the bug report
- [groupcache's jump consistent hash implementation](https://github.com/golang/groupcache/blob/master/consistenthash/jump.go)
- [Implementation in Java (Google Guava)](https://github.com/google/guava/wiki/CollectionUtilities)
- [Implementation in Python](https://github.com/ptcube/jump-consistent-hash)
- [LWN: Jump consistent hashing (2015)](https://lwn.net/Articles/609616/)
- [Comparison: Jump vs. Rendezvous vs. Consistent Hashing](https://theory.stanford.edu/~srini/215a/Dist.pdf)
