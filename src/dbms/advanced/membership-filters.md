# Approximate Membership Filters: Cuckoo, Quotient, XOR, Binary Fuse

A Bloom filter answers "is `x` in set `S`?" with a one-sided error: never a
false negative, sometimes a false positive. Once you need that answer at
storage-engine speed, Bloom is the default answer, not the final one. This page
covers the filter families that replaced or augmented Bloom in real engines:
**cuckoo filters** (deletion, two-cache-line lookups), **quotient filters**
(sequential, disk-friendly layout), and **XOR / binary fuse filters** (static,
near the information-theoretic space bound). Everything here is about
*membership*. Counting and cardinality estimation are different problems with
different sketches -- see [Sketch Algorithms in Analytics](sketch-algorithms.md)
for HyperLogLog and Count-Min.

## Orientation: what "membership" buys you and what it does not

Every filter on this page stores a constant number of bits per key
(independent of key length) and supports `add(x)` and `contains(x)`, where
`contains` may say "maybe" for keys never added. What you give up: counts
(a Bloom filter cannot tell you *how many* times `x` was added), enumeration
(you cannot list the set back out), and exactness. When an interviewer asks
"why not just a hash set?", the answer is bits per key: a hash set costs 50+
bits per entry with pointers and load-factor slack; a filter costs 7-12.

## Bloom, in one paragraph

A Bloom filter is an `m`-bit array plus `k` hash functions; insert sets `k`
bits, lookup checks them, FPR `~ 0.6185^(m/n)`, optimal `k = (m/n)ln2`, and
space-optimal cost is `1.44 log2(1/eps)` bits per key. No deletion (clearing a
shared bit creates false negatives), `k` random memory accesses per lookup, and
the bit array grows incrementally. The bit-level math, the exact filter formats
RocksDB ships (blocked / full / partitioned / Ribbon), and compaction
interactions are owned by [Bloom Filters in Storage
Engines](../../storage/bloom-filters.md); how filter quality degrades as
compaction rewrites SSTs is covered in [LSM Tree Deep Dive -- Bloom Filter
Degradation During
Compaction](../../storage/advanced/lsm-tree-deep.md#bloom-filter-degradation-during-compaction).
The rest of this page assumes that baseline and builds past it.

## Cuckoo filters: fingerprints with two homes

A cuckoo filter (Fan, Andersen, Kaminsky, Mitzenmacher; NSDI '14, extended at
CoNEXT 2014) is a bucketized hash table of *fingerprints*. Instead of storing
the key it stores an `f`-bit hash of the key, and each fingerprint gets two
candidate buckets:

```text
key x -> i1 = h1(x) mod m            i2 = i1 XOR hash(fp(x)) mod m   (m = 2^p buckets)
          |                                |
          v                                v
        +----+----+----+----+            +----+----+----+----+
  i1    | fpA| fpB| fpC|    |    i2      | fpD|    | fpE| fpF|
        +----+----+----+----+            +----+----+----+----+
  insert x: try i1, then i2. Both full -> evict a random fingerprint
  from one of them and push it to ITS alternate home; repeat up to a
  kick limit. Lookup checks both buckets; delete clears one fp copy.
```

Three ideas make this practical:

- **Partial-key cuckoo hashing.** Bucket `i2` must be computable from `i1` and
  the fingerprint alone (the key is unavailable during eviction). Setting
  `i2 = i1 XOR hash(fp)` does it: the fingerprint is simultaneously the stored
  data *and* the routing information. This is why `m` must be a power of two --
  XOR has to stay inside the index space and be an exact involution, so
  `alt(alt(i1)) = i1`. For general cuckoo-hashing mechanics (two choices,
  eviction chains, why bucket size 4 works), see [Cuckoo and Robin Hood
  Hashing](../../dsa/chapters/ch105-cuckoo-robin-hood-hashing.md).
- **Sizing math.** A lookup probes `2b` fingerprints (2 buckets x `b` slots),
  so FPR `~ 2b/2^f` and `f = log2(1/eps) + log2(2b)`; with `b = 4` that is
  `log2(1/eps) + 3` bits. Fingerprints occupy `n/load` slots, so bits/key is
  `f/load`. At 1% FPR, `b = 4`, 95% load: `f = 10`, about 10.5 bits/key.
- **Deletion, for real.** `delete(x)` recomputes `fp(x)`, checks both buckets,
  clears one matching copy. That is the headline feature Bloom lacks --
  provided you only delete keys you actually inserted (see gotchas below).

Space-wise, cuckoo only beats space-optimal Bloom at small FPRs: solve
`(log2(1/eps) + 3)/0.95 < 1.44 log2(1/eps)` and the crossover lands near
`eps ~ 0.4%`. Below that, cuckoo wins; at 1% it is roughly a wash (10.5 vs
9.6 bits/key) but with deletion and better locality (two cache lines, not `k`
scattered bits).

## Quotient filters: sort the hashes, stream from disk

The quotient filter (Bender et al., "Don't Thrash: How to Cache Your Hash on
Flash", PVLDB 2012) takes one `p`-bit hash and splits it: the high `log2(m)`
bits are the *quotient* (the slot index), the low `r` bits are the *remainder*
(the stored fingerprint, `r ~ log2(1/eps)`). Entries live in slot order -- i.e.
**sorted by hash value** -- so remainders sharing a quotient sit in one
contiguous *run*, and three metadata bits per slot (`is_occupied`,
`is_continuation`, `is_shifted`) encode where runs begin, end, and overlap into
*clusters*. What that buys:

- **Sequential access only.** A lookup scans one cluster forward; no random
  jumps. On disk or SSD that is the difference between one streaming read and
  a seek per probe -- the paper's whole point ("cache your hash on flash").
- **Deletion** (clear the slot, fix metadata bits) and **no insert failures**
  until the table is genuinely full.
- **The cost:** bits/key is `(log2(n/load) + log2(1/eps) + 3)/load` -- the
  quotient bits live in the slot position, so the slot array must be large
  enough to address them and space *grows with log n*. For `n = 10^6`, 90%
  load, 1% FPR: `(20.0 + 7 + 3)/0.9 ~ 33` bits/key, several times a cuckoo
  filter. Past ~90% load, clusters merge and lookups degrade toward linear
  scans. Mainline engines mostly picked Bloom/Ribbon or the XOR family; the
  quotient filter's lasting influence is the hash-sorted-slot idea (it
  resurfaces in vector quotient filters and the lineage behind binary fuse
  constructions).

## XOR filters: membership as a solvable linear system

XOR filters (Graf and Lemire, ACM JEA 2020) build on Dietzfelbinger and Pagh's
Bloomier-filter idea: give each key a `k`-bit fingerprint and build three
arrays `A1, A2, A3` (total capacity `c ~ 1.23n` slots, three nearly equal
segments, three hash functions over consecutive ranges) such that:

```text
A1[h1(x)] XOR A2[h2(x)] XOR A3[h3(x)] == fp(x)   (always, for x in S)
A1[h1(y)] XOR A2[h2(y)] XOR A3[h3(y)] != fp(y)   (w.p. 1 - 2^-k, for y not in S)
```

That is a random system of `n` XOR equations over `1.23n` unknowns, solved
offline by peeling (repeatedly removing variables that appear in exactly one
equation -- a Gaussian-elimination shortcut over GF(2)). Construction can fail
(small probability at the 1.23 density); you simply retry with a new seed.
Because the FPR is a single fingerprint comparison, `k = ceil(log2(1/eps))`
bits suffice -- no `+3` cuckoo tax and no 44% Bloom tax. The paper's framing:
the information-theoretic lower bound is `log2(1/eps)` bits per key (Broder and
Mitzenmacher); Bloom uses 44% more than that, XOR filters ~23% more. At 1% FPR:
7-bit fingerprints x 1.23 `~ 8.6` bits/key; with 8-bit fingerprints, 9.84
bits/key at `~0.4%` FPR (compressible to 9.23 by keeping a bitmap of occupied
slots). The trade: **fully static** -- no incremental insert, a changed set
means a rebuild.

## Binary fuse filters: construct in one pass, no peeling

Binary fuse filters (Graf and Lemire, ACM JEA 2022) keep the XOR-filter query
shape but replace peeling with a *direct, segmented construction* inspired by
Dietzfelbinger and Walzer: the arrays are built in a fixed sequence without a
global solve, construction is more than twice as fast as XOR-filter
construction, and storage drops to within **13%** of the lower bound (an
8%-of-bound variant exists at slightly slower queries) -- versus 23% for XOR
and 44% for Bloom. Same constraints as XOR: static set, `k = ceil(log2(1/eps))`
fingerprint bits, a few array reads per query. At 1% FPR that is about 7.5
bits/key. The production fit is natural for immutable files: RocksDB-style
engines build one filter per SST, and Pebble (CockroachDB's Go storage engine)
ships the FastFilter Go library, which slots straight into that model.

## Static vs dynamic: the decision that picks your filter

- **Set grows online (memtable, live service):** Bloom (any hash), cuckoo
  (deletes needed), quotient (deletes + no-fail inserts). XOR/binary fuse are
  disqualified -- they are built over a *known, finished* key set.
- **Immutable artifact (SST file, Parquet row group, frozen vocabulary):**
  binary fuse > XOR > Ribbon > Bloom on space; build time and library support
  decide. Static filters tolerate full rebuilds because the artifact itself is
  rewritten wholesale.
- **Deletion required:** cuckoo or quotient (or counting Bloom at ~4x space).
- **Weak/adversarial hashes:** Bloom is least demanding; XOR/binary fuse can
  fail construction and retry with a new seed; cuckoo needs the partial-key
  fingerprint property.
- **Memory hierarchy matters more than bits:** quotient (sequential) or cuckoo
  (2 cache lines) vs Bloom's `k` scattered probes.

## Construction math cheat-sheet

| filter | fingerprint bits | bits/key formula | at 1% FPR | over lower bound |
| --- | --- | --- | --- | --- |
| Bloom (optimal) | none (bits set) | `1.44 log2(1/eps)` | 9.6 | 44% |
| Cuckoo (b=4) | `log2(1/eps) + 3` | `f / load` | 10.5 @ 95% load | ~58% |
| Quotient | `r = log2(1/eps)` + 3 meta | `(log2(n/load) + r + 3)/load` | ~33 (n=1e6, 90%) | grows with log n |
| XOR | `ceil(log2(1/eps))` | `1.23 k` | 8.6 (1.23 x 7) | ~23% asymp. (29.6% at k=7) |
| Binary fuse | `ceil(log2(1/eps))` | `~1.13 k` | ~7.5 | ~13% (8% variant) |
| Ribbon (RocksDB) | block-coded | measured | ~7 (wiki, 1% FPR) | ~5% |

Lower-bound reference: `log2(1/eps)` bits per key. Bloom/XOR/binary-fuse
overheads are from the Graf-Lemire papers; cuckoo and quotient rows are the
derivations above; Ribbon's ~7 bits/key at 1% FPR is from the RocksDB wiki
(`NewRibbonFilterPolicy(9.9)`).

## Head-to-head

| filter | bits/key @ 1% | build | lookup | delete | hash needs | verified real-world use |
| --- | --- | --- | --- | --- | --- | --- |
| Bloom | 9.6 | O(n), online | k random reads | no (counting: ~4x space) | k independent hashes | RocksDB SST filters; Apache Parquet per-column bloom blocks |
| Cuckoo | 10.5 | O(1) amortized, online, can fail >95% load | 2 bucket reads | yes | fp hash + bucket hash; m = 2^p | Redis Stack RedisBloom `CF.ADD`/`CF.EXISTS` |
| Quotient | ~33 (n-dep.) | online, sequential writes | cluster scan | yes | one hash split into q and r | flash-KV research lineage (PVLDB'12); rare in mainline engines |
| XOR | 8.6 | offline peel, retry on failure | 3 reads | no | 3 hash fns | Pebble (CockroachDB), Databend, nDPI -- via FastFilter libs |
| Binary fuse | ~7.5 | offline direct, ~2x faster than XOR | 3-4 reads | no | 3-4 hash fns; static set only | FastFilter C/Go libs (`PopulateBinaryFuse8`); MatrixOne |

Every "use" cell above is checkable today: the [RocksDB
wiki](https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter) (Bloom and
Ribbon policies, per-SST), the [Parquet bloom filter
spec](https://github.com/apache/parquet-format/blob/master/BloomFilter.md),
[RedisBloom cuckoo filter
commands](https://redis.io/docs/latest/develop/data-types/probabilistic/cuckoo-filter/),
and the [FastFilter Go library
README](https://github.com/FastFilter/xorfilter), which lists Pebble, Databend,
nDPI, MatrixOne, and the Oracle Coherence client as consumers.

## Lab: measuring a hand-rolled cuckoo filter

The only way to trust the math above is to run it. Below: a from-scratch cuckoo
filter (4-slot buckets, 2 candidate buckets, partial-key eviction, 500-kick
limit), 30,000 inserted keys, 30,000 disjoint absent probes, 1% FPR target.

```python
# Hand-rolled cuckoo filter: 4-slot buckets, 2 candidate buckets,
# partial-key cuckoo eviction. Measures FPR and bits/key vs theory.
import hashlib
import math
import random


class CuckooFilter:
    def __init__(self, n_expected, eps, max_kicks=500):
        self.b = 4                                                  # slots per bucket
        self.f = math.ceil(math.log2(1.0 / eps)) + math.ceil(math.log2(2 * self.b))
        self.mask = (1 << self.f) - 1
        self.m = 1                                                  # buckets: power of 2 (paper rule)
        while self.m * self.b < n_expected / 0.94:
            self.m *= 2
        self.slots = [0] * (self.m * self.b)                        # 0 = empty
        self.max_kicks = max_kicks
        self.rng = random.Random(7)

    def _fp(self, key):
        fp = int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big") & self.mask
        return fp if fp != 0 else 1                                 # 0 is reserved for "empty"

    def _alt(self, i, fp):
        h = int.from_bytes(hashlib.blake2b(fp.to_bytes(2, "big"), digest_size=8).digest(), "big")
        off = h & (self.m - 1)
        return i ^ (off if off != 0 else 1)                         # i2 = i1 XOR hash(fp)

    def insert(self, fp, i1):
        for kicks in range(self.max_kicks):
            base = i1 * self.b
            for s in range(self.b):
                if self.slots[base + s] == 0:
                    self.slots[base + s] = fp
                    return kicks
            j = base + self.rng.randrange(self.b)                   # full bucket: evict one
            fp, self.slots[j] = self.slots[j], fp
            i1 = self._alt(i1, fp)
        raise RuntimeError("insert failed after %d kicks" % self.max_kicks)

    def contains(self, fp, i1):
        base2 = self._alt(i1, fp) * self.b
        return fp in self.slots[i1 * self.b:i1 * self.b + self.b] or \
               fp in self.slots[base2:base2 + self.b]


def main():
    n, eps = 30000, 0.01
    cf = CuckooFilter(n, eps)
    inserts = kicks_total = failures = 0
    for i in range(n):
        key = b"user:%d" % i
        fp, i1 = cf._fp(key), int.from_bytes(hashlib.blake2b(b"i1" + key, digest_size=8).digest(), "big") & (cf.m - 1)
        try:
            kicks_total += cf.insert(fp, i1)
            inserts += 1
        except RuntimeError:
            failures += 1
    load = inserts / (cf.m * cf.b)
    hits = sum(1 for i in range(n) if cf.contains(cf._fp(b"user:%d" % i),
               int.from_bytes(hashlib.blake2b(b"i1" + b"user:%d" % i, digest_size=8).digest(), "big") & (cf.m - 1)))
    fp_hits = sum(1 for i in range(n) if cf.contains(cf._fp(b"ghost:%d" % i),
                  int.from_bytes(hashlib.blake2b(b"i1" + b"ghost:%d" % i, digest_size=8).digest(), "big") & (cf.m - 1)))
    bits_per_key = cf.f * cf.m * cf.b / n
    print("fingerprint f = %d bits, buckets m = %d (%d slots)" % (cf.f, cf.m, cf.m * cf.b))
    print("inserted %d/%d, insert failures: %d, total kick hops: %d" % (inserts, n, failures, kicks_total))
    print("achieved load factor: %.4f" % load)
    print("true-member lookups found: %d/%d (no false negatives allowed)" % (hits, n))
    print("false positives: %d / %d absent probes -> measured FPR = %.4f" % (fp_hits, n, fp_hits / n))
    print("theory FPR ~ 8 fingerprints probed / 2^f = %.4f" % (8.0 / (1 << cf.f)))
    print("measured bits/key = f * m * b / n = %.2f" % bits_per_key)
    print("theory bits/key = f / load = %.2f" % (cf.f / load))
    print("Bloom optimum at same 1%% FPR: log2(1/eps)/ln2 = %.2f bits/key" % (math.log2(1 / eps) / math.log(2)))


if __name__ == "__main__":
    main()
```

Output (verbatim run):

```text
fingerprint f = 10 bits, buckets m = 8192 (32768 slots)
inserted 30000/30000, insert failures: 0, total kick hops: 21953
achieved load factor: 0.9155
true-member lookups found: 30000/30000 (no false negatives allowed)
false positives: 223 / 30000 absent probes -> measured FPR = 0.0074
theory FPR ~ 8 fingerprints probed / 2^f = 0.0078
measured bits/key = f * m * b / n = 10.92
theory bits/key = f / load = 10.92
Bloom optimum at same 1% FPR: log2(1/eps)/ln2 = 9.59 bits/key
```

Read three things out of the run:

1. **The FPR math holds.** 0.0074 measured vs 0.0078 predicted: FPR is set by
   `f` alone (8 fingerprints probed, `2^-10` each), not by table fullness --
   but only because insertion stopped at 91.6% load.
2. **Power-of-two sizing is a real tax.** 30,000 keys need ~7,980 buckets; the
   `m = 2^p` rule rounds to 8,192, so load drops to 0.9155 and bits/key lands
   at 10.92 instead of the ideal 10.5. Size `n` (or shard filters) accordingly.
3. **Kicks are cheap but finite.** ~0.73 eviction hops per insert on average,
   zero failures at 91.6% load -- and exactly why production sizing targets
   <= 95% load at `b = 4`: the failure cliff is sharp, not gradual.

## Gotchas examiners love

- **Deleting a key that was never inserted** can evict a *different* key's
  identical fingerprint and later cause a false negative. Cuckoo deletion is
  only sound for known members (same discipline as counting-Bloom decrements).
- **Duplicate fingerprints:** `add(x)` twice fills two slots, but `delete(x)`
  removes one copy, and the filter cannot tell "x twice" from "x plus a
  colliding key". For deletable multisets, keep a small counter per fingerprint.
- **"Cuckoo is always smaller than Bloom" is false at common FPRs.** It wins
  below roughly 0.4% FPR (at `b = 4`, 95% load); at 1% it is slightly *bigger*
  -- you are paying for deletion and locality. The XOR family is what actually
  beats Bloom on space at 1%.
- **Static filters need static sets.** Binary fuse construction assumes the
  whole key set up front; a growing set means periodic full rebuilds -- fine
  for immutable SSTs, wrong for memtables.
- **Quotient filters die politely:** no insert failures, but past ~90% load
  clusters stretch and lookups trend toward linear scans -- a degradation
  story, not a cliff.

## Paper trail

1. Bin Fan, David G. Andersen, Michael Kaminsky, Michael Mitzenmacher. *Cuckoo
   Filter: Practically Better Than Bloom.* ACM CoNEXT 2014.
   <https://doi.org/10.1145/2674005.2674994> (earlier version: USENIX NSDI '14).
2. Michael A. Bender, Martin Farach-Colton, Rob Johnson, Russell Kraner,
   Bradley Kuszmaul, Dzejla Medjedovic, Pablo Montes, Pradeep Shetty, Andrew
   Spillane, Erez Zadok. *Don't Thrash: How to Cache Your Hash on Flash.*
   Proceedings of the VLDB Endowment 5(11), 2012.
   <https://doi.org/10.14778/2350229.2350275>
3. Thomas Mueller Graf, Daniel Lemire. *Xor Filters: Faster and Smaller Than
   Bloom and Cuckoo Filters.* ACM Journal of Experimental Algorithmics 25,
   2020. <https://doi.org/10.1145/3376122> (arXiv:1912.08258).
4. Thomas Mueller Graf, Daniel Lemire. *Binary Fuse Filters: Fast and Smaller
   Than Xor Filters.* ACM Journal of Experimental Algorithmics 27, 2022.
   <https://doi.org/10.1145/3510449> (arXiv:2201.01174).
5. RocksDB wiki. *RocksDB Bloom Filter* (Bloom and Ribbon filter policies,
   per-SST behavior, Ribbon at ~7 bits/key for 1% FPR).
   <https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter>
