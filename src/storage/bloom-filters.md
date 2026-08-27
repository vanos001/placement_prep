# Bloom Filters in Storage Engines

Every point lookup in an LSM-tree database has to answer one question before touching a block: "could this key be in this SST file?" A Bloom filter answers it with zero I/O and a tunable false-positive rate. At one billion keys spread over hundreds of SSTs, this one data structure is the difference between ~1 data-block read per lookup and hundreds. This page covers the bit-level math, the exact filter formats RocksDB ships (blocked, full, partitioned, Ribbon), deletion-capable variants (counting, cuckoo, quotient), the configuration knobs that move read amplification, and how filters survive compaction. For the generic data-structure treatment see [Probabilistic Data Structures](../interview/system-design/probabilistic-data-structures.md); this page stays strictly on the storage-engine side.

## Bit Array, k Hashes, and the Two Invariants

A Bloom filter is an array of `m` bits plus `k` independent hash functions `h1..hk`, each mapping a key to one of `m` positions.

- **Insert(key):** set bits at all `k` positions.
- **Contains(key):** return "maybe yes" if all `k` positions are set, "definitely no" otherwise.

Two invariants hold and explain everything else:

1. **No false negatives.** Insertion only flips bits 0 -> 1 and never clears them. If `x` was inserted, its `k` positions are all 1, so `Contains(x)` can never say "no". This is why storage engines may safely *skip* a file on a "no" but must still search it on a "yes".
2. **False positives are the only error.** An absent key can collide with bits left by *other* keys. The probability of that is the false-positive rate (FPR):

```
FPR  p = (1 - e^(-k*n/m))^k          n = inserted keys, m = bits
optimal k* = (m/n) * ln(2)            (each probe equally likely 1/2)
minimum p  = (1/2)^(ln2 * m/n) = 0.6185^(m/n)
```

The form `0.6185^(m/n)` makes sizing trivial: cost scales linearly with the key count, error decays exponentially with bits-per-key.

| bits/key (m/n) | optimal k | minimum FPR | meaning in practice |
| -------------- | --------- | ----------- | ------------------- |
| 6              | 4         | 5.6%        | cheap, many wasted block reads |
| 8              | 6         | 2.2%        | Cassandra default territory |
| 10             | 7         | 0.82%       | RocksDB default `bloom_bits_per_key=10` |
| 16             | 11        | 0.046%      | RocksDB `format_version=5` sweet spot |
| 20             | 14        | 0.0061%     | rare; index hot paths only |

Sizing at billion-key scale: `1e9 keys * 10 bits/key = 10^10 bits = 1.25 GB` of filter bits, or `2 GB` at 16 bits/key. Engines cannot hold that per-SST set in the block cache by default, which is exactly why the memory-placement variants below exist. Note the FPR itself does not depend on `n` separately -- only on the ratio `m/n` -- so a 1M-key file and a 1B-key file at 10 bits/key have the same per-file FPR.

## Where the Filter Sits in the Read Path

```text
 point lookup "key=k1"
        |
        v
 memtable (real skiplist search)
        |
        v
 for each SST, newest -> oldest (L0 all files; L1+ one file per level):
        |
        +---> [ per-SST Bloom filter, in block cache ]
        |            |
        |            +-- "definitely no"  --> skip file (0 I/O)  ~~99.2% of probes @10 bpk
        |            +-- "maybe yes"      --> binary-search index block
        |                                        |
        |                                        v
        |                                  read 4 KB data block (1 I/O), binary search inside
        |
        v
 stop at first exact match (point reads never merge)
```

Read-amplification arithmetic for an absent key probed against `F` files at FPR `p`: expected wasted data-block reads `= F * p`. Concretely, 20 files probed:

| filters probed (F) | FPR  | wasted reads per 1000 absent lookups |
| ------------------ | ---- | ------------------------------------ |
| 20                 | 10%  | 2000                                 |
| 20                 | 1%   | 200                                  |
| 20                 | 0.1% | 20                                   |
| 100                | 0.1% | 100                                  |

Without filters the cost is `F` block reads *per lookup*, so a 1% filter already cuts absent-key I/O ~100x; the remaining `F*p` term is what the format work below attacks.

## One Hash Instead of k: Kirsch-Mitzenmacher

`k` independent hash functions are expensive to compute. Kirsch and Mitzenmacher (ESA 2006) showed that simulating them from two 64-bit hashes is within a small constant factor of optimal:

```
h_i(key) = (h1(key) + i * h2(key)) mod m        for i = 0 .. k-1
```

One fingerprint pass yields both hashes; each probe is one add + one multiply. Two practical failure modes:

- **Degenerate h2.** If `h2(key) == 0`, all `k` probes hit the same bit and the key's effective `k` collapses to 1, inflating FPR for that key. Fix: force `h2 |= 1` (odd) or add `i` to the mix.
- **32-bit fingerprints degrade at scale.** The original RocksDB full filter used 32-bit hashing and "would have degraded FP rates with millions of keys in a single filter"; the reworked implementation (`format_version >= 5`) uses 64-bit hashing and "easily scales to many billions of keys in a single filter" (RocksDB wiki). At 1B keys a 32-bit hash space is simply too collision-rich.

RocksDB stores filters inside the SST, so the hash choice is frozen at file-build time; a reader must honor whatever format the file used.

## Filter Formats in RocksDB: Blocked, Full, Partitioned

RocksDB has shipped three physical layouts, plus the Ribbon successor. All live in the `FilterBlock` region of the block-based table (see [SSTable Format](./sstable.md)).

| property | blocked (legacy) | full filter | partitioned | Ribbon filter |
| -------- | ---------------- | ----------- | ----------- | ------------- |
| filter granularity | per ~2 KB data block | 1 per whole SST | per key-range partition | 1 per whole SST (or partition) |
| CPU-cache behavior | not cache-aligned; misses on every probe | probe bits confined to 1 cache line | 1 cache line within partition | designed for space, not locality |
| block-cache footprint per op | tiny | whole filter (GB-scale files hurt) | bounded per partition | whole filter |
| hash width (pre-v5 vs v5) | 32-bit | 32-bit; 64-bit from `format_version=5` | same as full | 64-bit |
| notes | index loaded anyway, so savings shrank | default; < 0.1% FPR at 16 bpk | mitigates cache-thrash "cliff", higher avg CPU | ~7 bpk at 1% FPR |

Key facts from the RocksDB wiki, with consequences:

- The old blocked format's per-block filters "could result into a lot of cache misses during lookup" and the index block was consulted regardless, so the full filter replaced it: one filter per file, built so all probes for a key fall in a single cache line ("essentially sharding the bloom space", with only a small FPR effect).
- The pre-v5 full-filter implementation "could not get an FP rate better than about 0.1%, even at 100 bits/key"; the new one (RocksDB 6.6.0, `format_version=5`) reaches below 0.1% at only 16 bits/key. Migrating a fleet to v5 is a free ~2x filter-space win at equal FPR.
- Partitioned filters use the same block format as full filters "but use many filter blocks per SST file partitioned by key range". Average CPU per filter query rises (range lookup first); worst-case block-cache load per operation drops, which smooths the "cliff" where one large filter's eviction causes a tail-latency spike. This is the standard fix for filter-related p99 regressions on large SSTs.
- Ribbon filters (arXiv 2103.02515) are the current default recommendation for new files: `NewRibbonFilterPolicy(9.9)` targets the same ~1% FPR as Bloom at roughly 7 bits/key. Construction costs more temporary memory (~231 vs ~74 bits/key) and needs ~50 files of accumulation to break even, which matters for churn-heavy workloads.
- Learned filters (hash + model) are a separate research line, covered in [Storage Engines](../storage/advanced/storage-engines.md).

## Deletion-Capable Variants: Counting, Cuckoo, Quotient

Standard Bloom filters cannot delete: clearing shared bits creates false negatives, violating invariant 1. Storage systems that must retract membership (dedup stores dropping refcounts, KV tombstone compaction, network dedup caches) use:

**Counting Bloom filter (CBF).** Replace each bit with an `n`-bit counter (typically 4 bits, 4x the space; most counters sit at 0 or 1). Delete decrements counters. Failure mode: counter saturation at 15 with 4 bits silently breaks deletability -- the reason the classic 1998 summary-cache design only supports increments safely when insertions dominate deletions. Engines avoid CBF on the hot path; they rebuild filters at compaction instead of mutating them.

**Cuckoo filter** (Fan et al., CoNEXT 2014). A bucketized hash table of `f`-bit fingerprints with 2 candidate buckets per fingerprint and 4 (usually) slots per bucket; insertion evicts occupants to their alternate bucket, like partial-key cuckoo hashing. Deletion removes one fingerprint copy -- safe because the fingerprint is a hash of the key, so it is re-derivable at delete time. Space is competitive or better below ~3% FPR (~`1.05 * log2(1/p) * 2` bits per key at 2 buckets vs Bloom's `1.44 * log2(1/p)`), and lookups touch at most 2 cache lines.

**Quotient filter** (Bender et al., PVLDB 2012). Split the hash into a high `q` bits (the quotient, selecting a slot) and low `r` bits (the remainder, the stored fingerprint). Slots are *sorted by hash*, so probes stay cache- and disk-local with no random access; three metadata bits per slot encode run/cluster structure. It supports deletion and resizing (unlike Bloom), and unlike cuckoo filters it never fails to insert until genuinely full -- but occupancy past ~90% makes clusters long and lookups slow. Designed explicitly for hashing "on flash", which is why LSM-adjacent systems (e.g., a prior generation of storage-dedup indexes) picked it.

| property | Bloom | counting Bloom | cuckoo | quotient |
| -------- | ----- | -------------- | ------ | -------- |
| false negatives | never | never | never | never |
| delete | no | yes (4x space) | yes | yes |
| bits/key at ~1% FPR | ~9.6 | ~38 (4-bit ctr) | ~9-12 | ~10-12 + 3 meta |
| lookup cache lines | k (or 1 full filter) | k | 2 | 1 (sequential run) |
| insert failure mode | none until m exhausted | counter overflow | eviction loop may fail (~95% load) | none until full, then slow |
| resize in place | no | no | no | yes (with remap) |

## Configuration Effects on Point-Lookup Read Amplification

RocksDB options turn filter theory into read-amp outcomes. The knobs interact; the wrong combination silently disables the filter you think you have.

| option | effect | read-amp consequence |
| ------ | ------ | -------------------- |
| `bloom_bits_per_key` (default 10) | sets FPR of new files | 10 -> ~1%, 16 -> ~0.05%; wasted reads `F*p` scale linearly |
| `format_version >= 5` | new 64-bit filter impl | enables 16 bpk economics; fixes billion-key degradation |
| `partition_filters=true` (+ two-level index) | partitions full filter | caps block-cache bytes per op; trades avg CPU for p99 |
| `cache_index_and_filter_blocks` | filters cached in block cache vs private heap | if false, filters are pinned outside the cache and cannot thrash; if true, cold filters evict and probes re-read the SST footer |
| `optimize_filters_for_memory=true` | rounds filter sizes up to allocator size classes, spending the padding on lower FPR | jemalloc-style ~10% internal fragmentation becomes free accuracy |
| `whole_key_filtering` (default true) | hash of the full key in the filter | turning it off with a `prefix_extractor` set means *prefix* filters only -- smaller but higher FPR |
| prefix blooms | hashes of `prefix_extractor` output; usable in `Seek`, not just `Get` | helps range scans that share prefixes; note: with both whole-key and prefix set, point lookups check the whole-key filter and skip the prefix one |

Two arithmetic examples. (1) A column-family read of an absent user key against 50 files at 1% FPR wastes `50 * 0.01 = 0.5` data-block reads per lookup -- if your p50 latency includes one 4 KB read, half your absent-key reads are doubling. (2) Switching those files to v5/16 bpk drops it to `50 * 0.0005 = 0.025`, but the filters now total ~2 GB per TB of data; without `partition_filters` a block-cache flush wave that evicts large filters brings the F back as *footer + filter* re-reads, which shows up as tail latency, not average.

## Interaction With Compaction

Filters are per-SST artifacts, so compaction is the only time they change:

- **Rebuild, never mutate.** Every compaction output gets a fresh filter built from the merged iterator's keys. Because the builder re-derives bits from keys, an output with the same bits-per-key setting has the same FPR *regardless of how many inputs merged into it* -- merging four 1M-key files into one 4M-key file at 10 bpk keeps ~1%, since `m` grew with `n`. Filters degrade only when a size cap silently lowers bits-per-key on big outputs.
- **Write amplification on the filter itself:** each output key re-hashes once; at 10 bpk that is ~10 GB of filter bits rewritten per TB compacted -- negligible vs data rewrites, but visible in builder CPU (the reason Ribbon's heavier construction "could also slow peak write rates").
- **Tombstones and hot files:** a filter says "maybe yes" for any key whose bits are shared, including keys deleted long ago; until a full compaction physically drops the tombstone and the data, absent-key probes keep paying `p` on every file whose range covers the key. Level-count and file-count (see [LSM Compaction](./lsm-compaction.md)) therefore set `F` in `F*p`, and filter tuning cannot fix a file-count problem.
- **`optimize_filters_for_memory` interacts with partitioning:** it accumulates rounding credit across files/partitions, so very small partitions (aggressive `partition_filters`) reduce how much padding each filter gets.

## Measured: Kirsch-Mitzenmacher Filter vs Theory (1M Keys)

The runnable check below implements a Bloom filter with KM double hashing (one BLAKE2b fingerprint -> `h1`, odd `h2`), inserts 1M keys at 10 bits/key (optimal k=7), then measures the real FPR on 1M absent keys, plus a sweep at 6 and 16 bits/key on smaller loads.

```python
import hashlib, math, random, time

class Bloom:
    """Bloom filter with Kirsch-Mitzenmacher double hashing."""
    def __init__(self, n, bits_per_key):
        self.m = n * bits_per_key
        self.bits = bytearray((self.m + 7) // 8)
        self.k = max(1, round(bits_per_key * math.log(2)))
    def _probes(self, key):
        h = hashlib.blake2b(key, digest_size=8).digest()
        h1 = int.from_bytes(h[:4], "little")
        h2 = int.from_bytes(h[4:], "little") | 1  # odd: kills h2==0 degenerate
        for i in range(self.k):
            yield (h1 + i * h2) % self.m
    def add(self, key):
        for pos in self._probes(key):
            self.bits[pos >> 3] |= 1 << (pos & 7)
    def __contains__(self, key):
        return all((self.bits[pos >> 3] >> (pos & 7)) & 1 for pos in self._probes(key))

def trial(n, q, bpkey, rng):
    bf = Bloom(n, bpkey)
    k = max(1, round(bpkey * math.log(2)))
    theory = (1 - math.exp(-k / bpkey)) ** k
    for _ in range(n):
        bf.add(rng.randbytes(16))
    fp = sum(rng.randbytes(16) in bf for _ in range(q))
    return k, theory, fp

rng = random.Random(42)
n, q = 1_000_000, 1_000_000
t0 = time.time()
k, theory, fp = trial(n, q, 10, rng)
mb = (n * 10 + 7) // 8 // 1024 // 1024
print(f"main: n={n:,} bits/key=10 k={k} filter={mb} MiB")
print(f"  theoretical FPR {theory*100:.3f}%   measured {fp/q*100:.3f}%"
      f"   ({fp:,} FP in {q:,} absent-key probes)")
for bpkey in (6, 16):
    k2, th2, fp2 = trial(300_000, 300_000, bpkey, rng)
    print(f"sweep: bits/key={bpkey:<2} k={k2:<2} theory {th2*100:.3f}%  measured {fp2/300000*100:.3f}%")
print(f"elapsed {time.time()-t0:.1f}s")
```

Output from an actual run in this environment:

```text
main: n=1,000,000 bits/key=10 k=7 filter=1 MiB
  theoretical FPR 0.819%   measured 0.843%   (8,427 FP in 1,000,000 absent-key probes)
sweep: bits/key=6  k=4  theory 5.606%  measured 5.598%
sweep: bits/key=16 k=11 theory 0.046%  measured 0.050%
elapsed 8.1s
```

Measured FPR tracks theory closely at every setting: 0.843% vs 0.819% at the production-default 10 bits/key. The 16 bits/key case shows the finite-sample effect storage teams see in production FPR dashboards -- with only ~150 false positives in 300k probes, a handful of collisions moves the relative number by ~9%, which is why RocksDB publishes measured FPR curves rather than only the closed form. Note the whole filter for 1M keys is 1 MiB; the same structure at 1B keys is ~1.2 GB, which is where partitioned filters and Ribbon's 7-bits-per-key density start to matter.

## Failure Modes Checklist

- Filters evicted from block cache (`cache_index_and_filter_blocks=true`, no pinning): F is unchanged but every "maybe yes" and every filter miss re-reads the SST -- symptoms are footer-read storms, not data-block storms.
- Both `whole_key_filtering` and a `prefix_extractor` configured: point lookups exercise only the whole-key filter; teams that assume prefix filtering is active on `Get` are measuring a filter that is not running.
- Pre-`format_version=5` files at billions of keys: 32-bit hashing silently inflates FPR; v4 fleets show FPR creep as single files grow even at fixed bits-per-key.
- Cuckoo filter insertion into a ~95%-full table: eviction loops can fail outright -- sizing cuckoo filters needs the same headroom discipline as hash tables, not Bloom-style density math.
- Deletion against a plain Bloom filter (custom code): bits cleared for a shared position create false negatives, i.e., lost data during lookup -- the single worst bug this structure can cause.

## References

- Bloom, "Space/Time Trade-offs in Hash Coding with Allowable Errors", CACM 13(7), 1970 - <https://dl.acm.org/doi/10.1145/362686.362692>
- Kirsch & Mitzenmacher, "Less Hashing, Same Performance: Building a Better Bloom Filter", ESA 2006 - <https://doi.org/10.1007/11841036_42>
- RocksDB wiki, "RocksDB Bloom Filter" (formats, `format_version=5`, partitioned filters, Ribbon) - <https://github.com/facebook/rocksdb/wiki/RocksDB-Bloom-Filter>
- Fan, Andersen, Kaminsky, Mitzenmacher, "Cuckoo Filter: Practically Better Than Bloom", CoNEXT 2014 - <https://doi.org/10.1145/2674005.2674994>
- Bender et al., "Don't Thrash: How to Cache Your Hash on Flash" (quotient filter), PVLDB 5(11), 2012 - <https://doi.org/10.14778/2350229.2350275>
