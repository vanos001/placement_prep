# Roaring Bitmaps: Compressed Set Algebra for Query Engines

Every filter hit, postings list, and deletion marker in an analytics engine is the same object: a set of 32/64-bit row ids that must support membership tests, AND/OR/ANDNOT against sibling sets, sorted iteration, and compact storage. A plain bitset does all four at a fixed cost of N/8 bytes -- even when three of every four bits are zero. A sorted array is tiny but makes unions painful and membership O(log n). Roaring bitmaps win by splitting each id in half and picking the cheapest storage per half (Chambi, Lemire, Kaser; *Software: Practice and Experience*, 2016). The C reference implementation [CRoaring](https://github.com/RoaringBitmap/CRoaring) and the [wire-format spec](https://github.com/RoaringBitmap/RoaringFormatSpec) are the anchors every port (Java, Go, Rust, Python) interoperates with. [Execution Engines](execution-engines.md) introduces them in one paragraph; this page goes a level deeper: the container math, the pairwise algebra, and the on-disk format.

## Two levels: 16-bit key, 16-bit container

Roaring never hashes. A 32-bit id splits at a fixed position: the high 16 bits select a container from a sorted key array (binary search), the low 16 bits are the value stored *inside* that container. That is the opposite bet from hash tables ([Ch 7: Hashing](../../dsa/chapters/ch07-hashing.md)): no hash function, no collisions, and numeric order survives, so range scans and sorted output cost nothing extra.

```text
id 0x0001CAFE  =  (key 0x0001, low 0xCAFE)

key array (sorted, binary-searched):
   key 0x0000 -> container #0
   key 0x0001 -> container #1   holds low values ... 0xCAFE, 0xCAFF, ...
   key 0x0002 -> container #2
```

Three consequences: at most 65,536 containers and a key array small enough to stay cache-resident, so container lookup is a handful of comparisons; ops touch only keys both operands share, so an AND that overlaps in 10 keys does exactly 10 container ops; iteration walks keys in order, then values in order, so sorted output is free.

## Three containers and the 4096 tie point

| Container | Encoding                       | Size            | Sweet spot              |
| --------- | ------------------------------ | --------------- | ----------------------- |
| array     | sorted uint16 values           | 2 B x card      | card <= 4096, scattered |
| bitmap    | 1024 x 64-bit words            | 8,192 B fixed   | card > 4096 (dense)     |
| run       | (start, length-1) uint16 pairs | 2 + 4 B x runs  | long sorted ranges      |

The 4096 boundary is not a magic constant; it is the exact crossover of the first two encodings:

```text
array cost(card)  = 2 x card bytes              (one 16-bit slot per value)
bitmap cost(card) = 1024 words x 8 B = 8192 B   (65,536-bit container)
2 x card = 8192   =>   card* = 4096
```

Below 4096 values the sorted array is strictly smaller; above it the 8 KB bitmap wins no matter how the bits fall. Equivalently: a bitmap container holds 65,536 bits and each array slot costs 16 bits, so the tie sits at 65,536 / 16 = 4096. Implementations convert an array to a bitmap the moment insertion pushes past the tie point, and the serialized format mirrors it: per the format spec, a descriptive-header cardinality "up to and including 4096" decodes as an array container, anything above as a bitset container.

## Pairwise algebra: merge, compute, repair

A binary op never restructures the whole bitmap. It merge-joins the two sorted key lists; each shared key gets a container-pairwise op, and keys held by only one side are passed through (OR, ANDNOT-left) or dropped (AND).

| Op     | array,array         | bitmap,bitmap      | run,run                  |
| ------ | ------------------- | ------------------ | ------------------------ |
| AND    | 2-pointer, O(k1+k2) | 1024 word ANDs     | interval overlap O(r1+r2) |
| OR     | merge, may promote  | 1024 word ORs      | interval merge O(r1+r2)  |
| ANDNOT | 2-pointer skip      | 1024 (a AND NOT b) | interval subtract        |

Mixed array x bitmap pairs are bit-probe variants: AND keeps array values whose bit is set (O(k)), OR copies the 8 KB bitmap and sets k bits, ANDNOT either probes the bitmap per array value or clears k bits in a copy.

Each pair result is then **repaired**: re-normalized to the cheapest container type. This is where container-type transitions come from -- bitmap AND bitmap whose survivors drop to 4096 or fewer demotes to an array; array OR array whose merge exceeds 4096 promotes to a bitmap; bitmap OR bitmap can only grow, so it always stays bitmap. In-place behavior matters just as much: bitmap containers AND/OR/ANDNOT by writing words into one operand's buffer -- 1024 word ops independent of cardinality, which is why dense intersections are so cheap -- while array and run results allocate fresh (small) buffers. CRoaring stacks constant-factor tricks on top, e.g. lazy AND defers the popcount and repair until the cardinality is actually read.

## The wire format, straight from the spec

The [official spec](https://github.com/RoaringBitmap/RoaringFormatSpec) fixes a little-endian, random-access layout:

```text
cookie header       4 B: 12346 (no runs)  or  12347 | (size-1) << 16
  [run flags]       (size+7)/8 B, bit i = container i is a run   (12347 only)
  [size]            4 B container count                          (12346 only)
descriptive header  4 B per container: key:16 | (cardinality-1):16
offset header       4 B per container: byte offset from stream start
                    (always for 12346; for 12347 only when size >= 4)
containers          array: 2 x card B | bitset: exactly 8192 B
                    run: 2 + 4 x runs B -- pairs of (start, length-1)
```

Four points worth remembering: the descriptive header alone reveals every container's key, cardinality and type before any payload is read, so planners can estimate selectivity and skip containers without materializing them; the offset header enables seek-into-the-middle deserialization (load one container lazily), and when the run cookie is set with fewer than NO_OFFSET_THRESHOLD = 4 containers the offsets are omitted entirely; runs store `start` then `length - 1`, so values 11,12,13,14,15 become the pair (11, 4), and an empty bitmap is just the 8-byte 12346 cookie; finally, the same logical bitmap has two legal serializations (run cookie with no run containers vs the legacy cookie), so load-then-store can change the byte size -- the spec flags this explicitly so byte-exact test suites do not trip.

## Runs: when ranges beat bits

A run container collapses consecutive values into (start, length) pairs, and `runOptimize()` (CRoaring, Java) rewrites dense containers into runs wherever the byte math wins. The IDEAS '16 paper (Chambi, Lemire, Godin et al., doi:10.1145/2938503.2938515) showed Druid's dictionary-encoded columns emit filter bitmaps full of long runs; Lucene's [RoaringDocIdSet](https://lucene.apache.org/core/9_0_0/core/org/apache/lucene/util/RoaringDocIdSet.html) serves the same pattern for doc-id blocks; Delta Lake deletion vectors serialize as roaring bitmaps (the `RoaringBitmapArray` format in the Delta [protocol doc](https://github.com/delta-io/delta/blob/master/PROTOCOL.md)) because deleted rows cluster by insert order.

The trade has sharp edges. Within one 65,536-value key space, the dense range 0..40,999 costs 6 B as a single run vs 8,192 B as a bitmap -- but 32,768 alternating values become 32,768 runs, roughly 131 KB, 16x *worse* than the bitmap they replaced. That is why run conversion is opt-in per container, never a global policy.

## How it compares

| Structure      | 1k of 1M ids | 1M of 1M ids        | Membership       | AND with a peer      |
| -------------- | ------------ | ------------------- | ---------------- | -------------------- |
| plain bitset   | 128 KB       | 128 KB              | O(1)             | 1M/64 word ops       |
| sorted array   | 4 KB         | 4 MB (32-bit ids)   | O(log n)         | merge O(n)           |
| roaring bitmap | 2-4 KB       | ~8 KB per 65k block | O(log 4096)/O(1) | container-pairwise   |

Versus older word-aligned RLE schemes (WAH, EWAH, Concise), roaring keeps containers individually addressable -- binary search lands on one small structure instead of scanning a compressed stream -- and its kernels are branch-light and vectorizable. Qualitatively, CRoaring on one core runs unions/intersections over millions of ids in single-digit milliseconds, with AVX2/AVX-512 bitmap-container kernels pushing bitmap-AND/OR into the billions-of-elements-per-second range (hardware dependent; see the SPE paper's measurements and the CRoaring benchmarks).

## Who runs it, and who doesn't

- **Lucene**: `RoaringDocIdSet` represents query/filter result sets and join outputs (link above).
- **Druid**: every dictionary-encoded string column carries a bitmap inverted index; filters evaluate as bitmap algebra -- see the [filter docs](https://druid.apache.org/docs/latest/querying/filters.html) and the [Specialized Databases](../specialized-databases.md) Druid section.
- **ClickHouse**: low-cardinality keys and set-aggregation internals ([Execution Engines](execution-engines.md)).
- **Delta Lake**: deletion vectors (row-level DELETE/MERGE) are serialized roaring bitmaps read back at scan time (protocol link above).
- **Pilosa** ([github](https://github.com/pilosa/pilosa)): a database whose only index structure is the bitmap -- roaring end to end.
- **Not Parquet/Spark row-group pruning**: Parquet prunes row groups via min/max statistics and optional bloom filters per the parquet-format spec; Spark core builds no roaring indexes. The nearest real usage in that ecosystem is Delta's deletion vectors above. An interview answer claiming "Parquet prunes row groups with roaring" is wrong as of 2026.

## Demo: containers, pairwise ops, type transitions

The mini implementation below mirrors the real design: 16-bit low keys over 32-bit ints, array/bitmap containers, the 4096 tie point, pairwise AND/OR/ANDNOT with repair, and merge-join over container keys.

```python
# Mini Roaring: 32-bit ids -> 16-bit key + 16-bit low value; one container
# per key: 'array' (sorted list, card <= 4096) or 'bitmap' (1024 x 64-bit
# words = 8 KB). AND/OR/ANDNOT run container-pairwise; results are repaired
# to the cheapest container type (promote/demote at the 4096 tie point).
# Scope: same-type pairs (array x array, bitmap x bitmap); mixed pairs are
# a bit-probe variant discussed in the text.

LIMIT, WORDS, MASK = 4096, 1024, (1 << 64) - 1
W = {'word': 0, 'pop': 0, 'unpack': 0, 'merge': 0}   # work counters

class Cont:
    def __init__(self, vals):
        vals = sorted(set(vals))
        if len(vals) > LIMIT:                        # promote above tie point
            self.kind, self.vals, self.words = 'bitmap', None, [0] * WORDS
            for v in vals:
                self.words[v >> 6] |= 1 << (v & 63)
        else:
            self.kind, self.vals, self.words = 'array', vals, None
    def card(self):
        return len(self.vals) if self.kind == 'array' \
            else sum(bin(w).count('1') for w in self.words)
    def nbytes(self):                                # wire size per the spec
        return len(self.vals) * 2 if self.kind == 'array' else WORDS * 8

def repair(words):
    """Normalize a bitmap-container result to its cheapest form."""
    W['pop'] += WORDS
    pop = sum(bin(w).count('1') for w in words)
    if pop == 0:
        return None
    if pop > LIMIT:
        c = Cont.__new__(Cont)
        c.kind, c.vals, c.words = 'bitmap', None, words
        return c
    vals, W['unpack'] = [], W['unpack'] + pop        # demote bitmap -> array
    for j, w in enumerate(words):
        while w:
            b = w & -w
            vals.append((j << 6) | (b.bit_length() - 1))
            w ^= b
    return Cont(vals)

def arr_op(a, b, kind):
    if kind == 'or':                                 # real impls: 2-way merge
        out = sorted(a + b)
        W['merge'] += len(out)
        return out
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):                 # two-pointer walk
        W['merge'] += 1
        if a[i] == b[j]:
            if kind == 'and':
                out.append(a[i])
            i, j = i + 1, j + 1
        elif a[i] < b[j]:
            if kind == 'andnot':
                out.append(a[i])
            i += 1
        else:
            j += 1
    return out

def pairwise(x, y, kind):
    """One container pair; absent keys are handled in Roaring.binary."""
    if x.kind == 'array' and y.kind == 'array':
        out = arr_op(x.vals, y.vals, kind)
        return Cont(out) if out else None
    W['word'] += WORDS                               # bitmap x bitmap
    if kind == 'and':
        return repair([p & q for p, q in zip(x.words, y.words)])
    if kind == 'or':
        return repair([p | q for p, q in zip(x.words, y.words)])
    return repair([p & ~q & MASK for p, q in zip(x.words, y.words)])

class Roaring:
    def __init__(self, ints=()):
        groups = {}
        for x in ints:
            groups.setdefault(x >> 16, set()).add(x & 0xFFFF)
        self.c = {k: Cont(v) for k, v in groups.items()}
    @staticmethod
    def binary(a, b, kind):
        for k in W:
            W[k] = 0
        ka, kb, out, i, j = sorted(a.c), sorted(b.c), {}, 0, 0
        while i < len(ka) or j < len(kb):            # merge join over keys
            if i < len(ka) and j < len(kb) and ka[i] == kb[j]:
                r = pairwise(a.c[ka[i]], b.c[kb[j]], kind)
                if r is not None:
                    out[ka[i]] = r
                i, j = i + 1, j + 1
            elif i < len(ka) and (j >= len(kb) or ka[i] < kb[j]):
                if kind in ('or', 'andnot'):         # one-sided key: share it
                    out[ka[i]] = a.c[ka[i]]
                i += 1
            else:
                if kind == 'or':
                    out[kb[j]] = b.c[kb[j]]
                j += 1
        r = Roaring()
        r.c = out
        return r

def show(tag, r):
    cs = ", ".join(f"key {k}:{c.kind}({c.card()})" for k, c in sorted(r.c.items()))
    nb = 4 * len(r.c) + sum(c.nbytes() for c in r.c.values())
    print(f"{tag:<9} [{cs or 'empty'}]  card={sum(c.card() for c in r.c.values())}"
          f"  wire~{nb} B")

a = Roaring(range(0, 20000, 3))                  # multiples of 3
b = Roaring(range(0, 20000, 2))                  # evens
show("A (x3)", a)
show("B (x2)", b)
c = Roaring.binary(a, b, 'and')
print(f"A AND B    work: {W['word']} word-ANDs + {W['pop']} popcount-words"
      f" + {W['unpack']} unpacked bits")
show("A AND B", c)
show("A ANDNOT B", Roaring.binary(a, b, 'andnot'))
show("A OR B", Roaring.binary(a, b, 'or'))
g = Roaring([7] + list(range(100000, 100500)))   # keys 0 and 1, both arrays
show("E OR C", Roaring.binary(g, c, 'or'))       # key 0 computed pairwise,
                                                 # key 1 passes through
h = Roaring(range(100, 4100))                    # 4000 values -> array
i2 = Roaring(range(2000, 4400))                  # 2400 values -> array
show("G OR H", Roaring.binary(h, i2, 'or'))      # merged card 4300 > 4096
show("G AND H", Roaring.binary(h, i2, 'and'))
```

Real output:

```text
A (x3)    [key 0:bitmap(6667)]  card=6667  wire~8196 B
B (x2)    [key 0:bitmap(10000)]  card=10000  wire~8196 B
A AND B    work: 1024 word-ANDs + 1024 popcount-words + 3334 unpacked bits
A AND B   [key 0:array(3334)]  card=3334  wire~6672 B
A ANDNOT B [key 0:array(3333)]  card=3333  wire~6670 B
A OR B    [key 0:bitmap(13333)]  card=13333  wire~8196 B
E OR C    [key 0:array(3335), key 1:array(500)]  card=3835  wire~7678 B
G OR H    [key 0:bitmap(4300)]  card=4300  wire~8196 B
G AND H   [key 0:array(2100)]  card=2100  wire~4204 B
```

## References

1. RoaringBitmap, "RoaringFormatSpec: specification of the compressed-bitmap Roaring formats" -- https://github.com/RoaringBitmap/RoaringFormatSpec
2. CRoaring (C/C++ reference implementation) -- https://github.com/RoaringBitmap/CRoaring
3. S. Chambi, D. Lemire, O. Kaser, "Better bitmap performance with Roaring bitmaps", Software: Practice and Experience, 2016. doi:10.1002/spe.2325
4. S. Chambi, D. Lemire, R. Godin, K. Boukhalfa, C. R. Allen, F. Yang, "Optimizing Druid with Roaring bitmaps", IDEAS '16. doi:10.1145/2938503.2938515
5. Apache Lucene, `RoaringDocIdSet` API docs -- https://lucene.apache.org/core/9_0_0/core/org/apache/lucene/util/RoaringDocIdSet.html
