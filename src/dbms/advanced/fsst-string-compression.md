# FSST: String Compression That Supports Random Access

In real-world databases a huge fraction of stored bytes is text: ERP systems and visual-analytics workloads keep much of their data in string columns, and users store URLs, emails, IP addresses, UUIDs, and non-integer surrogate keys as strings because that is the path of least resistance. The FSST paper (Boncz, Neumann, Leis, PVLDB 2020) observes that these strings are typically small — generally under 200 bytes, often under 30 — and that general-purpose compressors are a bad match for them: LZ4 needs kilobyte-scale inputs to pay off, while databases need to read, compare, and join individual string values. FSST (Fast Static Symbol Table) is a compression scheme built around that mismatch. It replaces frequently occurring substrings of up to 8 bytes with single-byte codes, using a static, shared symbol table, so that each string compresses and decompresses independently — and it beats LZ4 on compression factor and compression speed while decompressing just as fast.

This page dissects the format, the table-construction algorithm, and the measured trade-offs. It complements the format-level view in [columnar-formats.md](columnar-formats.md) (dictionary and RLE encodings at the page level), the storage-engine context in [column-stores.md](../storage/column-stores.md), and the query-execution angle in [late-materialization.md](late-materialization.md). For the index that often sits on top of such strings, see [adaptive-radix-tree.md](adaptive-radix-tree.md).

---

## Why strings need their own compressor

The default database answer to string bloat is a dictionary: map each distinct string to an integer, compress the code column with integer schemes. Dictionaries only pay when strings repeat fully — "similar but not equal" values (every URL with a different query string, every UUID) leave the dictionary untouched, and per-row-group dictionaries shrink it further. The strings inside the dictionary itself, which can still be the bulk of the data, are usually stored raw. Schemes that do compress them make trade-offs: Binnig et al.'s order-preserving dictionary truncates shared prefixes but needs long common prefixes to work, and Arz and Fischer's LZ78-based random-access dictionaries need over a microsecond — roughly 100 cycles per character — to decompress a short string.

Block compression has the opposite problem: it compresses well but destroys random access. Compressing a column of strings as one file is LZ4's best case, and the paper still shows FSST ahead; the moment blocks shrink, LZ4 collapses. The paper's block-size experiment on its `urls` data set shows the decay:

| LZ4 block size | 64K | 16K | 4K | 1K | 256 B | 64 B | 16 B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| compression factor | 2.73 | 2.45 | 2.03 | 1.59 | 1.14 | 0.78 | 0.46 |

The paper notes LZ4 suffers once blocks drop below ~27 KB; at 64-byte blocks — the size of a handful of short strings — the factor is 0.46, meaning the data *grew*. Compressing strings one at a time with LZ4 (its "line mode" in the paper) gives factors below 1, and zstd-generated dictionaries help the factor a bit while hurting compression speed very severely. PostgreSQL draws the line in the same place: its TOAST mechanism only compresses values larger than 2 KB with a simple LZ variant, leaving the much more common short strings uncompressed. A string compressor that works per string at line speed was missing; that is the gap FSST fills.

## Symbols, codes, and the escape hatch

FSST's vocabulary is deliberately tiny. A **symbol** is a byte sequence of length 1 to 8, aligned at byte boundaries. A **code** is one byte naming a symbol. Since one byte offers 256 values, the code table holds up to 255 real symbols plus one reserved value: code 255 is the **escape**, and it is followed in the compressed stream by the literal byte it stands for. Compression walks the input, repeatedly finds the longest symbol matching at the current position, and emits its code — or, when nothing matches, the escape pair. Decompression is the mirror image and needs nothing but two arrays: `sym[256]`, 256 eight-byte words (2,048 bytes) holding each symbol right-padded for fast unaligned stores, and `len[256]`, one byte per code. Each code costs one array read and one unaligned 8-byte store, which is why decoding runs at roughly 1-3 cycles per byte (~2 GB/s per core in the paper's evaluation) with no SIMD at all.

```text
input string: http://www.vldb.org        (19 raw bytes; toy table from the demo below)

 bytes:   h    t    t    p    :    /    /    w    w    w    .    v    l    d    b    .    o    r    g
 match:   [    ht   ]  [  tp  ] [  :/  ] [  /w  ] [  ww  ]    .     v     l     d   [  b. ] [ or ]   g
 codes:        2         7        5        26       0    103   147   112   111   69    11   115
          \____2-byte symbols____/    \______1-byte symbols______/  \_2-byte_/   \2-b/  1-byte

 output: 12 code bytes, each decoded independently by sym[code]/len[code]
         strings that are equal under the same table are byte-identical when compressed
```

The escape code is what makes the scheme robust. The paper gives three reasons to prefer escaping over Byte-Pair-style "use the unused byte values" tricks: an existing table can compress arbitrary unseen text (every byte has a fallback), table construction can run on a sample rather than the full corpus (escaped bytes absorb whatever the sample missed), and low-frequency bytes do not waste precious codes. Escapes are rare on in-domain data — otherwise the byte would have earned a symbol — so the branch in the decoder is well predicted, and the real implementation uses a branch-free 4-byte fast path when no 255 appears in the next word.

Two properties make this format database-friendly. First, **strings stay strings**: a compressed value is just a byte sequence, so existing varlena/string infrastructure, hash tables, and sort buffers work unchanged, only smaller. Second, **equality survives compression**: because coding is deterministic, two equal strings compressed under the same table are byte-equal, so joins, group-bys, and equality predicates — including comparisons against a constant, once the constant is compressed — run directly on codes. What does *not* survive is ordering and substring semantics: codes are assigned by frequency, not alphabet, and the paper explicitly leaves LIKE-pattern matching on compressed strings to future work (a follow-up workshop paper, Pop, Riedl, Neumann, DaMoN, has since built automata that run in the code domain). The result is a sharp boundary every engine integration has to respect:

| Operation on FSST-coded strings | Works without decoding? | Why |
| --- | --- | --- |
| Equality, group-by, distinct, IN | yes (same table) | coding is deterministic, so equal strings are byte-equal |
| Hash joins, hash aggregation | yes | codes are fixed-width bytes; hash on codes as on strings |
| Copying, shuffle, network exchange | yes (send the table) | compressed values are plain bytes; table is ~hundreds of bytes |
| Range predicates, ORDER BY, MIN/MAX | no | codes are frequency-ranked, not alphabetically ordered |
| LIKE, substring match | no (decode) | left to future work by the paper; DaMoN paper rebuilds automata over codes |

## Building the table: bottom-up, not top-down

The format is simple; finding a good table is the research problem. The obvious one-pass idea — count all substrings of length 1-8, rank them by *static gain* (frequency × length), keep the top 255 — fails because symbols overlap. In a URL corpus the 8-byte symbol `http://w` is promising, and so are `ttp://ww` and `tp://www` by the same metric, but none of them adds value once the other is chosen. Greedy longest-match encoding makes it worse: if both `"h` and `http://w` are symbols, the encoder consumes the `h` inside `<a href="http://...` first and never gets to use the big one. Counted frequency is an overestimate of realized value — the paper calls this the **dependency issue** — and even testing all tables is hopeless: choosing 255 symbols from the top 3,000 candidates leaves roughly 3000-choose-255, a number with 378 digits.

FSST instead grows a table the way nature does, by iterated selection under real conditions. Each generation compresses the training corpus on the fly with the current table and counts two things: how often each symbol is actually used, and how often each *pair of successive codes* occurs. Candidate symbols for the next generation are all previous symbols, all single bytes, all single-byte extensions, and every concatenation of an observed code pair (capped at 8 bytes); the top 255 by apparent gain survive. The paper's Figure 2 runs this on the 13-byte corpus `tumcwitumvldb` with toy limits (symbols ≤ 3 bytes, table ≤ 5):

```text
generation   surviving symbols (gain = length x realized count)      compressed size
   1         um(4) tu(4) wi(2) cw(2) mc(2)      <- all bigrams; input all escaped      26 B
   2         tum(6) tu(4) wit(3) mcw(3) vl(2)   <- observed code pairs become 3-byte symbols
   3         mvl cwi vld tum wit (each gain 3)  <- tu dies: "tum" eats its matches
   4         tum(6) cwi(3) vld(3) b(1)          <- converged                            5 B
             13 raw bytes -> 5 codes; mistakes of one generation are repaired in the next
```

Two engineering choices make this cheap. The table is trained on a **sample** — the released tooling uses 16 KB per 4 MB chunk, with the sample growing from 6% to 100% of that quota across the 5 generations, since frequent symbols are unlikely to be rare in a fair sample. And the first generations start from single bytes, which the algorithm keeps re-injecting so that a symbol lost to an over-greedy merge can regrow. Five generations reliably converge; the authors' earlier suffix-array construction produced *worse* tables (compression factor 1.97× vs 2.19× in the paper's variant-evolution table) at 74 cycles per byte of construction cost versus 0.83 in the final design. The table's footprint stays small — at most 8×255+255 bytes, typically a few hundred, since the average symbol is around two bytes — so a page or row-group can carry its own table, and finer granularity buys better factors at the price of tracking which table belongs to which string.

## Making the encoder fast

Decoding was free; encoding needed work. The naive `findLongestSymbol` loops over candidate symbols and branches on the first hit, which blocks SIMD. The implementation replaces it with a **lossy perfect hash** keyed on a symbol's first 3 bytes — 4,096 buckets, single multiplicative hash `x*2971215073 ^ (x>>15)`, collisions resolved by keeping the higher-gain symbol — plus a 64K-entry `shortCodes[A][B]` table answering "is there a 1- or 2-byte symbol for these two bytes?" in one lookup. A conditional move picks between the two answers; the branch-free scalar kernel runs at about 10 cycles per byte. The AVX-512 kernel then turns compression into a "meatgrinder": 512 string segments sorted longest-first, 8 lanes × 3-way unroll = 24 strings in flight, each lane's position packed into one 64-bit job word `[out:19][nr:9][end:18][cur:18]`, gather/scatter with speculative writes — about 200 cycles per iteration and 4.1 cycles per byte (~920 MB/s on the paper's i9-7900X), which the authors report as the fastest known string compression at the time. A per-table terminator byte (the corpus's least frequent byte) stops the kernel from running past string ends without branches. Decoding, by contrast, gains nothing from SIMD — it is already a stream of memory instructions. Two integration details round out the design. Since (de)compression keeps no state, FSST parallelizes trivially: bulk loaders can even give each thread its own table, stored in the block header. And an optional 0-terminated-string mode (for C-style APIs) spends code 0 on the zero byte, leaving 254 codes and slightly degrading the factor — the price of dropping into existing infrastructure unchanged.

## Demo: a toy symbol coder

The script below builds a miniature of this idea, and it is honest about its limits: it is **not** FSST. It uses one static-gain pass over a fixed 26-string corpus (the paper's algorithm iterates five generations on a sample), symbols of at most 2 bytes (FSST allows 8), and a 192-code budget with code 255 as escape. It encodes and decodes every corpus string, reports the compression ratio, and contrasts the naive static-gain prediction against the realized saving — the dependency issue, caught live.

```python
# TOY MODEL of the FSST idea - NOT the real FSST algorithm. The paper's FSST uses
# 255 symbols of length 1-8 bytes, iterative bottom-up table construction on a
# 16KB sample, lossy perfect hashing and AVX512 encoding. This toy keeps only the
# core vocabulary: a frequency-derived table of 1- and 2-byte symbols, one code
# byte per symbol, code 255 = escape, greedy longest-match, stateless per-string
# coding against a shared immutable table.
from collections import Counter

CORPUS = [
    "http://www.vldb.org", "http://www.wikipedia.org", "http://in.tum.de",
    "http://cwi.nl", "https://www.uni-jena.de", "https://github.com/cwida/fsst",
    "http://reference.data.gov.uk", "https://fr.wikipedia.org/wiki/Main_Page",
    "www.uni-jena.de/index.html", "www.wikipedia.org/portal",
    "Customer#000010485", "Customer#000020917", "Customer#000033721",
    "nal braids nag carefully", "deposits nag furiously",
    "theodolites nag across the packages", "quietly final foxes nag",
    "RUSSEL_BALONIER", "ROELAND_PARK", "PURITAN_AVENUE",
    "xnj_14@hotmail.com", "petere@example.org", "boncz@cwi.nl",
    "leis@uni-jena.de", "neumann@in.tum.de", "alice@wikipedia.org",
]
BUDGET, ESCAPE = 192, 255        # codes 0..191 name symbols; 255 escapes a raw byte

byte_c, pair_c = Counter(), Counter()
for s in CORPUS:
    b = s.encode()
    byte_c.update(b)
    pair_c.update(zip(b, b[1:]))
# static gain pass: 2-byte symbols by occurrence count (each match saves 1 byte
# vs raw), then the most frequent bytes as 1-byte symbols (they save nothing vs
# raw but avoid paying the 2-byte escape pair)
pairs = [p for p, c in sorted(pair_c.items(), key=lambda kv: (-kv[1], kv[0])) if c >= 2]
pairs = pairs[:BUDGET - 64]
singles = [b for b, c in sorted(byte_c.items(), key=lambda kv: (-kv[1], kv[0]))][:64]
pcode = {p: i for i, p in enumerate(pairs)}
scode = {b: len(pairs) + i for i, b in enumerate(singles)}

def encode(s):
    b, out, i = s.encode(), bytearray(), 0
    while i < len(b):
        p = (b[i], b[i + 1]) if i + 1 < len(b) else None
        if p is not None and p in pcode: out.append(pcode[p]); i += 2   # longest first
        elif b[i] in scode:              out.append(scode[b[i]]); i += 1
        else:                            out.extend((ESCAPE, b[i])); i += 1
    return bytes(out)

def decode(c):
    out, i = bytearray(), 0
    while i < len(c):
        code = c[i]
        if code == ESCAPE: out.append(c[i + 1]); i += 2
        else:
            out.extend(bytes(pairs[code]) if code < len(pairs)
                       else bytes([singles[code - len(pairs)]])); i += 1
    return bytes(out)

raw = sum(len(s.encode()) for s in CORPUS)
comp = sum(len(encode(s)) for s in CORPUS)
esc_all = 2 * raw                                  # counterfactual: escape every byte
events = [code for s in CORPUS for code in encode(s)]
n_bg = sum(1 for c in events if c < len(pairs))
n_esc = sum(1 for c in events if c == ESCAPE)
static = 2 * sum(c for p, c in pair_c.items() if p in pcode) \
       + sum(c for b, c in byte_c.items() if b in scode)
demo = encode(CORPUS[0])
print(f"corpus: {len(CORPUS)} strings, {raw} raw bytes, avg {raw/len(CORPUS):.1f} B/string")
print(f"table : {len(pairs)} 2-byte symbols + {len(singles)} 1-byte symbols "
      f"= {len(pairs)+len(singles)} of {BUDGET} codes (code {ESCAPE} = escape)")
print(f"sizes : all-escape baseline {esc_all} B -> toy-FSST {comp} B "
      f"(ratio raw/compressed {raw/comp:.2f}x, ~{8*comp/raw:.1f} bits per char)")
print(f"gains : static-gain prediction saves {static} B vs all-escape, "
      f"realized saves {esc_all-comp} B (overestimate = dependency issue)")
print(f"coding: {n_bg} bigram matches, {n_esc} escaped bytes; "
      f"e.g. 'w.' is counted {pair_c[(119,46)]}x but 'ww' always consumes it first")
print(f"sample: '{CORPUS[0]}' ({len(CORPUS[0])} B) -> {len(demo)} codes {list(demo)}")
print(f"verify: decode(encode(x)) == x for all corpus strings: "
      f"{all(decode(encode(s)) == s.encode() for s in CORPUS)}")
u = "zzz-42-quux@some-unknown-host.example/path"
ue = encode(u)
print(f"unseen: '{u}' ({len(u)} B) -> {len(ue)} codes, round trip "
      f"{decode(ue) == u.encode()}, ratio {len(u)/len(ue):.2f}x (escape-heavy, still lossless)")
```

Real output (executed, Python 3.12):

```text
corpus: 26 strings, 540 raw bytes, avg 20.8 B/string
table : 99 2-byte symbols + 60 1-byte symbols = 159 of 192 codes (code 255 = escape)
sizes : all-escape baseline 1080 B -> toy-FSST 340 B (ratio raw/compressed 1.59x, ~5.0 bits per char)
gains : static-gain prediction saves 1262 B vs all-escape, realized saves 740 B (overestimate = dependency issue)
coding: 200 bigram matches, 0 escaped bytes; e.g. 'w.' is counted 5x but 'ww' always consumes it first
sample: 'http://www.vldb.org' (19 B) -> 12 codes [2, 7, 5, 26, 0, 103, 147, 112, 111, 69, 11, 115]
verify: decode(encode(x)) == x for all corpus strings: True
unseen: 'zzz-42-quux@some-unknown-host.example/path' (42 B) -> 36 codes, round trip True, ratio 1.17x (escape-heavy, still lossless)
```

Read the output as three results. Round-trip is exact for all 26 strings and for the unseen URL, which is the random-access and robustness story in one line: every string is coded against the shared table independently, and anything unfamiliar degrades gracefully into escape pairs instead of failing. The 1.59× ratio (~5 bits per character) is respectable for bigram-only coding but sits far below FSST's 2.28× — the gap is precisely the machinery the toy omits (symbols up to 8 bytes, five adaptive generations, a trained sample). And the static-gain line shows the dependency issue quantitatively: the naive prediction overstates the realized saving by 70%, with `w.` as the live specimen — counted five times, never used once, because the greedy encoder's `ww` match always gets there first.

## What the measurements say

The paper evaluates on **dbtext**, a contributed 23-column corpus of real string data (URLs, emails, names, wiki text, genome fragments, TPC-H comments). It compares against LZ4 in three regimes — whole files, shrunken blocks, and individual strings — and all numbers below are from the paper's Tables 1 and 4:

| Metric (dbtext, 8 MB file mode, avg of 23 columns) | LZ4 | FSST |
| --- | --- | --- |
| Compression factor | 1.70× (1.14× hex … 3.08× c_name) | 2.28× (1.63× wiki … 3.84× c_name) |
| Compression speed | 608 MB/s | 977 MB/s |
| Decompression speed | 1,857 MB/s | 1,942 MB/s |
| Random access to one string | no — whole block | yes — per string, stateless |

The honest footnotes matter as much as the averages. FSST's factor edge is 34% on average, but LZ4 *wins* the `urls` column (2.77× vs 2.16×) because long-range repetition across an 8 MB file is exactly what LZ77 is for; fully sorting the corpus text lifts LZ4 to 2.07×, still short of FSST, which is indifferent to that localized similarity. Outside text, the picture inverts: on the Silesia corpus FSST compresses text files 10% better but binaries 25% worse than LZ4, and large XML/JSON files land 2-2.5× worse — JSON should be shredded into typed columns before any of this (the paper points to Snowflake's internal columnization as the model). Speed is a wash on decompression and a clear win on compression thanks to the AVX-512 kernel.

## Integration notes

The paper's own end-to-end integration is in **Umbra** (CIDR 2020): each string is compressed individually and decompressed as late as possible, with equality predicates evaluated directly on codes. On TPC-H SF10 with 20 threads, geometric-mean query time went from 57 ms uncompressed (59 ms with LZ4) to 53 ms with FSST; the LIKE-heavy Q13 cost 3% (LZ4: 9%), and Q19 — heavy on compressible string columns — ran 30% *faster* under FSST. The string pool shrank from 4.1 GB uncompressed to 1.5 GB with LZ4 and 0.69 GB with FSST, inflated by Umbra inlining sub-12-byte strings; the worst case, a join over artificially padded string key columns, carried a 14% overhead, of which decompression itself was only 9%.

Production adoption followed the paper's integration recipe. The DuckDB storage documentation lists Fast Static Symbol Table (FSST) among the compression algorithms of its storage format, alongside dictionary, RLE, bit-packing, and ALP — FSST covers what dictionary encoding cannot: high-cardinality string columns. The paper also prescribes composition with dictionaries rather than replacement: de-duplicate the column, then FSST-compress the unique strings in the dictionary. Granularity is a tunable: symbol tables are small enough that a table per page or per row-group is feasible, and finer granularity buys better factors at the cost of tracking which table belongs to which string. Finally, the reference implementation ships **FSST12**, a 12-bit-code variant with 4,096 symbols and no escape (the first 256 codes are the single bytes themselves); it needs 1.5× longer symbols for the same ratio, costs ~8 KB on disk / 32 KB in memory per table, and is aimed at less focused distributions such as JSON and XML.

## Interview questions

**Q: LZ4 achieves a similar decompression speed. Why does that not make it good enough for a column store's string columns?**
Because decompression speed is only comparable when LZ4 is allowed its best case — multi-kilobyte blocks. A column store needs individual strings for selection pushdown, hash joins, aggregations, and index probes; compressing at that granularity puts LZ4 below 1.0× (expansion) per the paper's line-mode experiment, and 64-byte blocks reach only 0.46×. Restoring reasonable factors requires blocking ~1,000 values together, and then every selective query pays for decompressing values it will discard — the paper's selectivity experiment shows FSST's output rate flat while block-LZ4 degrades linearly. FSST matches LZ4's decompression speed *and* keeps per-string access, so the block mode's one advantage disappears.

**Q: Why reserve code 255 as an escape instead of coding into the byte values that never occur in the data, as Byte Pair compression does?**
Three reasons, all structural. First, unseen data: a table built from unused-byte analysis can only encode bytes it anticipated, while escaping gives every byte a fallback, so any string compresses losslessly under any table. Second, sampling: with escapes, the table can be built from a 16 KB sample per 4 MB chunk, since whatever the sample missed is handled by escape pairs — Byte-Pair-style coding would need the full corpus to know which bytes are "free". Third, economics: escaping does not burn codes on rare bytes, so all 255 symbol slots go to high-gain symbols, and the escaped byte would have been in the table anyway if it were common — which is also why the decoder's escape branch predicts well.

**Q: Explain the dependency issue. Why did counting substring frequencies and taking the top 255 fail, and what does the iterative algorithm do differently?**
Static gain — frequency × length measured on the raw text — assumes symbols compete for independent matches, but symbols overlap and greedy longest-match encoding serializes them: `http://w`, `ttp://ww`, `tp://www` all claim the same occurrences, and a short symbol like `"h` can steal a byte that would have enabled a high-value long symbol. The demo makes this concrete: `w.` is counted 5 times but never matched once, and naive prediction overstates savings by 70%. The bottom-up algorithm sidesteps estimation entirely by *measuring*: each generation compresses the corpus with the current table, records which symbols and which code pairs actually occur, and selects the next generation's top 255 from those realized counts, with concatenations of observed pairs as new candidates and single bytes constantly re-injected so mistakes can be undone. The authors tried suffix-array-based correction first and it produced strictly worse tables.

**Q: You have a column of semi-structured JSON blobs. Should the engine FSST-compress it as-is?**
Probably not directly. The paper measures FSST at 2-2.5× *worse* than LZ4 on large XML/JSON files: their repetitive structure favors long-range block matching over a 255-symbol table, and the byte budget is wasted re-encoding attribute names. The engine should shred the JSON first — parse the structure, store each frequent attribute in its own typed internal column (the Snowflake pattern the paper cites), drop the repeated names, and then FSST the resulting string values. FSST12, the 4,096-symbol variant, exists for exactly this distribution and does better than FSST8 on JSON/XML, but it pays with 16× larger tables and needs 1.5× longer symbols to match FSST8's ratio, so shredding remains the first move.

## References

1. P. Boncz, T. Neumann, V. Leis. "FSST: Fast Random Access String Compression." PVLDB 13(11): 2649-2661, 2020. [doi:10.14778/3407790.3407851](https://doi.org/10.14778/3407790.3407851) — open PDF: <https://www.vldb.org/pvldb/vol13/p2649-boncz.pdf>
2. FSST reference implementation (MIT-licensed C/C++, includes FSST12 and the dbtext corpus): <https://github.com/cwida/fsst>
3. C.-G. Pop, A. Riedl, T. Neumann. "Compression-Aware LIKE: Matching Patterns in the FSST Domain." Proc. 22nd Int. Workshop on Data Management on New Hardware (DaMoN). [doi:10.1145/3789237.3809128](https://doi.org/10.1145/3789237.3809128)
4. J. Arz, J. Fischer. "Lempel–Ziv-78 Compressed String Dictionaries." Algorithmica 80(7): 2012-2047, 2018. [doi:10.1007/s00453-017-0348-7](https://doi.org/10.1007/s00453-017-0348-7)
5. C. Binnig, S. Hildenbrand, F. Färber. "Dictionary-Based Order-Preserving String Compression for Main Memory Column Stores." SIGMOD 2009. [doi:10.1145/1559845.1559877](https://doi.org/10.1145/1559845.1559877)
6. M. Zukowski, S. Héman, N. Nes, P. Boncz. "Super-Scalar RAM-CPU Cache Compression." ICDE 2006. [doi:10.1109/ICDE.2006.150](https://doi.org/10.1109/ICDE.2006.150)
7. T. Neumann, M. J. Freitag. "Umbra: A Disk-Based System with In-Memory Performance." CIDR 2020. [dblp entry](https://dblp.org/rec/conf/cidr/NeumannF20.html)
8. [PostgreSQL TOAST](https://www.postgresql.org/docs/current/storage-toast.html) — the >2 KB threshold that leaves short strings uncompressed
9. [DuckDB storage format: compression algorithms](https://duckdb.org/docs/current/internals/storage.html) — FSST listed among DuckDB's supported encodings
10. [Columnar Formats: Parquet, ORC, Arrow](columnar-formats.md) — sibling page: dictionary and RLE encodings at the file-format layer
11. [Adaptive Radix Tree](adaptive-radix-tree.md) — sibling page: index lookups over strings, the point-access case FSST keeps cheap
12. [Late Materialization in Columnar Engines](late-materialization.md) — sibling page: deferring work the scan can defer, decompression included
