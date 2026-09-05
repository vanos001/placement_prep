# Search Fundamentals

A search system turns a query into ranked documents. The core pipeline is
**analyze, index, retrieve, score, and present**. Search quality is not only a
storage problem: tokenization, language, ranking, freshness, evaluation, and
user intent all matter.

## The inverted index

An inverted index maps a term to the documents and positions where it occurs:

```text
"distributed" → doc-2: [4, 19], doc-8: [2]
"systems"    → doc-2: [5], doc-3: [11, 42]
```

A query analyzer applies normalization, tokenization, stemming or lemmatization,
stop-word rules, synonyms, and language-specific handling. The index may store
term frequency, document frequency, positions, offsets, and stored fields.

## Retrieval and ranking

### TF-IDF intuition

A term is useful when it appears often in one document but not in every document.
Term frequency rewards repetition; inverse document frequency downweights common
terms. Modern systems commonly use BM25 or a learned ranker rather than raw
TF-IDF.

### BM25 intuition

BM25 balances term frequency saturation, inverse document frequency, and document
length normalization. Tune parameters against a labeled evaluation set rather
than assuming defaults are optimal for every corpus.

### Candidate and rerank stages

A production search path often has two stages:

1. **Candidate retrieval:** fast inverted-index or vector retrieval returns a
   few hundred candidates.
2. **Reranking:** a more expensive model or feature computation selects the
   top results.

This separates recall from precision and keeps expensive ranking bounded.

## Query processing

- Parse operators, phrases, filters, fields, and user syntax.
- Normalize spelling, case, punctuation, and language.
- Retrieve candidates with term, prefix, phrase, or vector strategies.
- Apply access-control filters before presenting results.
- Score and rerank using text, freshness, popularity, personalization, and
  business rules.
- Highlight evidence and expose why a result matched when possible.

Search must not leak documents through snippets, autocomplete, vector neighbors,
or cached result pages when the user lacks authorization.

## Index lifecycle

Indexing is usually asynchronous. A document may be accepted by the source of
truth before it becomes searchable. Track indexing lag, failed documents,
segment merges, deleted-document cleanup, shard health, and schema/analyzer
versions.

A safe reindex plan uses a new index, backfills it, validates recall and
latency, then switches an alias or routing pointer. Avoid changing an analyzer
in place when old and new tokens would be incompatible.

## Evaluation

Offline evaluation needs labeled queries or judgments. Useful measures include:

- **Precision@k:** fraction of the top k results judged relevant.
- **Recall@k:** relevant results retrieved in the top k.
- **MRR:** rewards the position of the first relevant result.
- **NDCG:** handles graded relevance and position discounts.
- **Latency and freshness:** quality is not useful if results are too slow or
  stale.

Online metrics such as click-through rate can be biased by ranking position.
Use interleaving, randomized experiments, abandonment, reformulation, and
human judgments to avoid optimizing only for clicks.

## Postings compression: why every listing is a delta

A search engine over 10 million documents cannot afford raw 32-bit doc IDs
in every postings list. The enabling observation is structural, not
statistical: a postings list is *sorted*, so adjacent entries are close
together. The Stanford IR handbook states it directly: "The key idea is
that the gaps between postings are short, requiring a lot less space than
20 bits to store. In fact, gaps for the most frequent terms such as the and
for are mostly equal to 1. But the gaps for a rare term that occurs only
once or twice in a collection... have the same order of magnitude as the
docIDs." [1] Hence **delta (gap) encoding**: store the first doc ID in
full, then `doc[i] − doc[i−1]` — tiny numbers for frequent terms, docID-like
numbers for rare ones, and different codes fit each regime.

**Variable-byte (VB) codes** are the workhorse: 7 gap bits + 1 continuation
bit per byte, so gaps ≤ 127 cost one byte and most others two. The
handbook's Reuters-RCV1 experiment compressed the index to 116 MB, "a more
than 50% reduction," concluding that "for most IR systems variable byte
codes offer an excellent tradeoff between time and space." [1] **Bitwise
codes** go finer: an Elias γ code splits gap *g* into a unary *length*
(⌊log₂ g⌋) and an *offset* (g's low bits), costing `2⌊log₂ g⌋ + 1` bits —
within a factor of two of the ⌊log₂ g⌋-bit lower bound — and δ codes shrink
the length prefix. γ wins for very frequent terms (gaps of 1–3 cost 1–5
bits vs VB's flat 8) and loses at mid-range gaps; production engines
mostly pick byte- or word-aligned, SIMD-friendly schemes (p-for-delta,
Simple-family) because decode throughput, not size, is the binding
constraint. For bitmap encodings of low-cardinality filter fields, see
[Roaring Bitmaps](../dbms/advanced/roaring-bitmaps.md).

**A computed example** (python3, this session): *N* = 10,000,000 documents,
*df* = 100,000 (term in 1% of the corpus), doc IDs uniform at random, so
the mean gap is exactly N/df = 100.

```text
raw 4-byte doc IDs:   400,000 bytes (391 KB)
variable-byte:        127,948 bytes (125 KB) → 10.24 bits/gap, 3.13× smaller
γ-coded:              146,927 bytes (143 KB) → 11.75 bits/gap, 2.72× smaller
```

72% of gaps fit one VB byte. Rerun with *df* = 1,000,000 (mean gap 10):
VB 8.0 bits/gap vs γ 5.70 — the expected crossover, bitwise winning only
for frequent postings. The rule of thumb holds: **1–2 bytes per posting
instead of 4**.

**Why compression also speeds queries.** A postings walk is
bandwidth-bound: cost is dominated by moving bytes into CPU cache. A 3×
smaller list is 3× likelier to sit in page cache and 3× fewer bytes to
decode per posting — which is why Lucene ships compression by default and
why SIMD group decoding is a core codec feature, not a footnote.

**Skipping.** AND-intersecting a rare term's 500 postings with a common
term's 2,000,000 naively walks the long list — 2M steps, nearly all failed
comparisons. A **skip list** adds jump-ahead pointers so the intersection
leaps ahead instead of stepping: skip pointers are "effectively shortcuts
that allow us to avoid processing parts of the postings list that will not
figure in the search results," and they "only help[] for AND queries, not
for OR queries." [1] Pairing the rare list with binary probes into the
common one costs ~500·log₂(2,000,000) ≈ 10,500 steps — 0.5% of the naive
scan (computed this session). Placement is a genuine tradeoff, in the
handbook's words: "More skips means shorter skip spans, and that we are
more likely to skip. But it also means lots of comparisons to skip
pointers, and lots of space storing skip pointers"; its practical heuristic
is √P evenly spaced skips for a list of length P. Skips are built at
indexing time and degrade under heavy updates — one more reason search
engines prefer immutable segments plus merges over in-place editing.

## Ranking math: TF-IDF to BM25, worked

The preceding intuition section hides the algebra; the algebra is the
interview. Start from **TF-IDF**: weight(term *t*, doc *d*) = tf(*t*, *d*) ×
idf(*t*), with idf = log(N/df) — a term that appears in df of N documents
gets weight log(N/df), so ubiquitous terms score ≈ 0 and rare terms score
high. TF-IDF's failure modes are well understood: raw tf grows without
bound (a 10× longer document wins for no semantic reason), and long
documents are penalized only implicitly and inconsistently.

**BM25** (Okapi BM25, from the TREC-3 Okapi system; the canonical treatment
is Robertson & Zaragoza [2]) fixes both with two dampening terms per score:

```text
score(q, d) = Σ_t∈q  idf(t) · tf(t,d)·(k1 + 1) / ( tf(t,d) + k1·(1 − b + b·|d|/avgdl) )
```

where |d| is the document length and avgdl the corpus average. Lucene's
javadoc describes the two knobs in one line each: "k1 — Controls non-linear
term frequency normalization (saturation)" and "b — Controls to what degree
document length normalizes tf values", with defaults k1 = 1.2 and b = 0.75
(Elasticsearch documents the same defaults [4]). *Saturation*: the tf
component → (k1+1) as tf → ∞, so the 8th occurrence of a term adds much
less than the 2nd — matching the observed diminishing returns of term
repetition that raw TF-IDF ignores. *Length normalization*: the factor
`(1 − b + b·|d|/avgdl)` rescales tf by how much longer than average the
document is; b = 1 applies full normalization, b = 0 none, and the default
b = 0.75 hedges because "longer than average" sometimes means "more
thorough", not "more padded". Lucene's actual idf is a smoothed Robertson–
Sparck Jones variant, "log(1 + (docCount − docFreq + 0.5)/(docFreq + 0.5))",
which floors negative idf for terms appearing in over half the corpus [3].

**Worked example** (computed with python3 this session — every number below
is from that run). Corpus of three documents; query term *replication*;
k1 = 1.2, b = 0.75, idf = ln(N/df):

```text
docs: D1 "replication lag monitoring"                      |d|=3, tf=1
      D2 "replication replication streaming replication lag"|d|=5, tf=3
      D3 "database indexing and query optimization basics"  |d|=6, tf=0

N=3, df=2 → idf = ln(3/2) = 0.4055;  avgdl = 14/3 = 4.6667

D1: tf-component = 1·(2.2) / (1 + 1.2·(0.25 + 0.75·0.6429)) = 2.20/1.8786 = 1.1711
    score(D1) = 0.4055 · 1.1711 = 0.4748
D2: tf-component = 3·(2.2) / (3 + 1.2·(0.25 + 0.75·1.0714)) = 6.60/4.2643 = 1.5477
    score(D2) = 0.4055 · 1.5477 = 0.6276
D3: score = 0 (term absent)
```

Note what the formula did: D2 wins because tf = 3 beats tf = 1, but not 3× —
saturation compresses the advantage. D1's short length *boosted* its tf
component (its denominator 1.8786 < tf itself), while D2's above-average
length shrank it. The same run swept tf: the component rises 1.17 → 1.55 →
1.96 → 2.15 → 2.20 for tf = 1, 3, 10, 50, 10⁶ — asymptoting at k1+1 = 2.2 —
and, at fixed tf = 1 for D1, scores move 0.4055 (b=0) → 0.4748 (b=0.75) →
0.5036 (b=1) as length normalization strengthens.

**Why BM25 became the default.** It is robust with no per-corpus training:
two parameters with sane defaults, monotone in tf and idf, saturating by
construction, hard to break with skew. BM25F extends it to structured
fields; learning-to-rank and cross-encoder systems (see
[Reranking](./reranking.md)) sit *on top* of BM25 candidate generation
rather than replacing it, because a lexical prefilter is what bounds the
expensive stage's fan-in. A candidate-retrieval stack that ships BM25 today
is not legacy engineering; it is the recall layer that learned rankers
assume exists.

## Incremental indexing and the LSM connection

The "index lifecycle" section described reindexing as a batch discipline;
here is the engine machinery underneath it. A document update never edits a
postings list in place. New text is analyzed into an **in-memory buffer**,
which periodically drains into a small **immutable segment** — a
self-contained inverted index. Elasticsearch's docs define the vocabulary:
"A segment is similar to an inverted index, but the word index in Lucene
means 'a collection of segments plus a commit point'." [5]

This is the **LSM-tree pattern** — memtable → immutable sorted run →
background merge — transplanted from key-value stores to postings (the full
compaction architecture and write-amplification math are in
[LSM Trees](../dbms/internals/lsm-trees.md)). What changes for search: a
segment carries its own dictionary, postings, and doc values, and reads are
always multi-segment — every query probes all live segments and merges
their result heaps, so segment count is a first-order latency variable.

**Deletes are tombstones, not deletions.** Deleting writes a mark (Lucene's
*live docs* bitset — same role as an LSM tombstone or `.del` file) saying
"not this doc ID in this segment"; the bytes stay until a merge rewrites
the segment without them. Elasticsearch states the cycle plainly:
"Segments... are immutable. Smaller segments are periodically merged into
larger segments to keep the index size at bay and to expunge deletes." [6]
Derived consequences: update = delete + insert, so churning workloads
accumulate deleted bytes fast; filtered-out docs still cost query work
until reclaimed; and Lucene's TieredMergePolicy makes reclaim rate a merge
*cost input* — favoring "merges with lower skew, smaller size and those
reclaiming more deletes", capping the deleted share (deletesPctAllowed
default 20%), and refusing to build segments beyond maxMergedSegmentMB
(default 5 GB), which can strand deletes inside huge segments. [7]

**Merge policy: tiered.** TieredMergePolicy "merges segments of
approximately equal size, subject to an allowed number of segments per
tier," deliberately separating "how many segments are merged at once...
from how many segments are allowed per tier," and "does not over-merge
(i.e. cascade merges)." [7] Versus log-merge: tiered merges *non-adjacent*
segments of similar size — lower write amplification, slightly more small
segments (worse read amplification). Elasticsearch layers operations on
top: a dedicated merge pool where "smaller merges are prioritized over
larger ones, across all shards on the node," merging "disk IO throttled so
that bursts... are smoothed out," and a disk-space guard so that "no new
merge tasks are scheduled for execution when the available disk space is
low" — every merge needs temporary headroom equal to its inputs. [6]

**Near-real-time search and the visibility nuance.** Nothing above requires
the new segment to hit disk. Elasticsearch writes it to the filesystem page
cache and opens it for search *before* any durable commit: "The new segment
is written to the filesystem cache first (which is cheap) and only later is
it flushed to disk (which is expensive)... Lucene allows new segments to be
written and opened, making the documents they contain visible to search
without performing a full commit." The act is a **refresh** — "by default,
Elasticsearch periodically refreshes indices every second, but only on
indices that have received one search request or more in the last 30
seconds." [5] That yields a three-tier visibility ladder: *acknowledged*
(request accepted, in translog) < *searchable* (refreshed, page cache) <
*durably committed* (translog fsync + Lucene commit), with the gaps between
tiers configurable (`refresh_interval`, translog durability). The
interview-grade nuance: a document can be lost in a crash *after being
searchable*, so "did my write return 200?", "could a query see it?", and
"will it survive power loss?" are three different questions with three
different guarantees — the acknowledgment-vs-durability spectrum of group
commit, in a search engine.

## Interview questions

**Why does a search engine need an inverted index?**

It avoids scanning every document for every term. The index maps query terms to
candidate documents, then scoring and filtering operate on a smaller set.

**Why can adding stemming reduce quality?**

It can improve recall by matching related word forms but may conflate terms
with different meanings. Test language-specific analyzers against representative
queries.

**What is the difference between recall and precision?**

Recall asks how many relevant items were retrieved; precision asks how many
retrieved items are relevant. Candidate retrieval favors recall, while reranking
and presentation improve precision.

**(mid) Design the spell-correction ("did you mean") component for a search
engine. What's stored, when is it built, and how does it answer in
single-digit milliseconds?**
Expected: build a correction index offline from the same analyzed corpus —
term → document frequency (optionally n-gram/phonetic keys) — not from
query logs alone (tail vocabulary, privacy filtering). At query time:
generate candidates within edit distance 1–2 (bk-tree, length-partitioned
dictionary, or precomputed delete-1 variants à la SymSpell for O(1)
lookup), rank by a probability model — df (or query-log frequency) weighted
by edit distance — and trigger only when the typed term's df is
suspiciously low, so rare-but-real terms are never "corrected." Rubric:
junior proposes Levenshtein against a list; mid justifies the data
structure and the trigger threshold; senior separates index-built
candidates from query-log priors and corrects per token with bigram
plausibility instead of whole-phrase edit distance.

**Why should an AND-intersection process the rarest term first — and what
breaks if you don't?**
Expected: intersections shrink monotonically, so the cost model is
"process terms in order of increasing document frequency" so that "all
intermediate results must be no bigger than the smallest postings list" —
the handbook's standard heuristic [8]. Starting from the
common term's 2M postings walks 2M entries before knowing anything;
starting from the 500-posting rare list either walks only those 500
(probing the other lists per candidate via skip pointers/skips) or
generates a tiny working set that bounds every later step. Our computed
example: ~10,500 probed steps vs 2,000,000 — 0.5%. What breaks otherwise:
tail latency on poly-shard fan-outs (every shard repeats the mistake),
and the working-set blowup makes intermediate result caches useless.
Bonus points: document-frequency ordering is a per-shard decision, so a
term rare in shard A can be common in shard B — engines typically rely on
global statistics with a freshness lag, and skews there show up as
per-shard latency variance.

**Your team reindexes a 2 TB index into a new one and every night the
cluster's indexing throughput collapses for ~40 minutes. Diagnosis?**
Expected: a **merge storm**. The reindex generates thousands of tiny
segments; TieredMergePolicy must compact them, and each merge rewrites
bytes equal to its inputs — with maxMergedSegmentMB = 5 GB, the tail of
merges is I/O heavy by construction. Elasticsearch's own mitigations are
the answer menu: merge auto-throttling ("to balance the use of hardware
resources between merging and other activities like search" [6]),
`index.merge.scheduler.max_thread_count` (lower it on spinning disks),
bigger `refresh_interval` during backfill (fewer, larger segments), the
disk-space guard [6], and scheduling reindexes off-peak. Rubric: junior
blames "indexing is slow"; mid names merges and throttling; senior explains
the write-amplification arithmetic (log-structured systems rewrite all
data, logarithmically many times), ties it to
[LSM compaction](../dbms/internals/lsm-trees.md), and proposes measurable
guards (merge-time SLO, disk watermark alerts, segment-count dashboards).

## Cross-references

- [Vector Search](./vector-search.md)
- [Elasticsearch](./elasticsearch.md)
- [Search interview questions](./interview-questions.md)
- [Information retrieval in system design](../interview/system-design/search.md)
- [Probabilistic Data Structures](../interview/system-design/probabilistic-data-structures.md)
- [Data Quality](../data-engineering/data-quality.md)
- [Reranking and Hybrid Fusion](./reranking.md) — the precision stage that sits on top of BM25 candidate generation
- [HNSW](./hnsw.md) — the ANN index that competes for the candidate-generation slot in hybrid retrieval
- [Full-Text Search in SQL](../dbms/sql/full-text-search.md) — inverted indexes inside the relational engine (PostgreSQL FTS, GIN)
- [GIN Index](../dbms/indexing/gin.md) — posting-list structure for SQL full-text search
- [LSM Trees](../dbms/internals/lsm-trees.md) — the compaction architecture that segment-based search indexing mirrors

## References

- [Stanford Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/) — Manning, Raghavan & Schütze; fetched this session, including the [Postings file compression](http://nlp.stanford.edu/IR-book/html/htmledition/postings-file-compression-1.html), [Variable byte codes](http://nlp.stanford.edu/IR-book/html/htmledition/variable-byte-codes-1.html), [Gamma codes](http://nlp.stanford.edu/IR-book/html/htmledition/gamma-codes-1.html), [Skip pointers](http://nlp.stanford.edu/IR-book/html/htmledition/faster-postings-list-intersection-via-skip-pointers-1.html), [Processing Boolean queries](http://nlp.stanford.edu/IR-book/html/htmledition/processing-boolean-queries-1.html), and [Okapi BM25](http://nlp.stanford.edu/IR-book/html/htmledition/okapi-bm25-a-non-binary-model-1.html) chapters (all fetched in full; quoted sentences verbatim).
- Robertson, S.; Zaragoza, H. "The Probabilistic Relevance Framework: BM25 and Beyond." *Foundations and Trends in Information Retrieval* 4(1–2), pp. 1–174, 2009. DOI: [10.1561/1500000019](https://doi.org/10.1561/1500000019) — Crossref-verified (title/authors/venue/volume) this session.
- [Apache Lucene Core](https://lucene.apache.org/core/) — project homepage, fetched this session. [BM25Similarity javadoc](https://lucene.apache.org/core/10_5_1/core/org/apache/lucene/search/similarities/BM25Similarity.html) (Lucene 10.5.1) — defaults k1 = 1.2, b = 0.75, parameter descriptions, and idf "Implemented as log(1 + (docCount − docFreq + 0.5)/(docFreq + 0.5))" quoted verbatim; [TieredMergePolicy javadoc](https://lucene.apache.org/core/10_5_1/core/org/apache/lucene/index/TieredMergePolicy.html) — tiered-merge description, maxMergedSegmentMB "Default is 5 GB", deletesPctAllowed "Default value is 20", merge-cost description quoted verbatim.
- Elasticsearch documentation, [Near real-time search](https://www.elastic.co/guide/en/elasticsearch/reference/current/near-real-time.html) — segment/commit-point definition, filesystem-cache-first segment writes, refresh definition and default 1s refresh quoted verbatim — and [Merge scheduling](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-merge.html) — immutability/expunge-deletes, dedicated merge pool, IO throttling, disk-space guard quoted verbatim. [Similarity settings](https://www.elastic.co/guide/en/elasticsearch/reference/current/index-modules-similarity.html) — BM25 `k1`/`b` defaults. [Text analysis](https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis.html) (analyzer chain referenced by the "The inverted index" section above). All fetched in full this session.
- [TREC evaluation resources](https://trec.nist.gov/) — fetched this session (live at time of citation).
