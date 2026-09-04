# Full-Text Search in SQL

"Find documents mentioning *retry*, *retries*, or *retrying*, best match
first" is not a `LIKE '%retry%'` problem — that predicate can't use an
index (the [non-SARGability trap](../interview-problems/interview-traps.md)),
scores nothing, and misses every inflection. Full-text search (FTS) brings
an *inverted index* — the data structure behind Elasticsearch — inside the
relational engine: documents are parsed into terms, terms map to posting
lists of document IDs, and queries intersect those lists with ranking.
This page covers the mechanics (tokenization, postings, GIN/GiST indexes
in PostgreSQL), ranking (`ts_rank`, and why BM25 is the industry default),
fuzzy matching with trigrams, and the modern hybrid lexical + vector
pattern.

The engine-side (Elasticsearch) architecture is in
[Search Fundamentals](../../search/fundamentals.md) and
[Elasticsearch](../../search/elasticsearch.md); the GIN index internals
that make FTS fast are in [GIN](../indexing/gin.md).

## From documents to postings: the inverted index

```text
docs:                                  inverted index (term → doc list):
 1: "retry failed payments"            "retry"     → {1, 2}
 2: "retries are not retries"          "payment"   → {1, 3}
 3: "payment status"                   "retries"   → {2}   ← raw token
                                       ...
after stemming ("retries"→"retri"):    "retri"     → {1, 2}   ← merged
```

Three transformations define correctness and recall:

1. **Tokenization** splits text into terms and lowercases them — language-
   and config-dependent, so `to_tsvector('english', ...)` and
   `to_tsvector('simple', ...)` build *different indexes over the same
   text*; queries must use the same configuration or they silently match
   nothing (the FTS version of the encoding-mismatch bug).
2. **Stemming** folds inflections to a base form (`retries`, `retrying` →
   `retri`) so variants match; the cost is precision ("university" and
   "universe" share a stem).
3. **Stop words** (`the`, `is`) are dropped — index size and noise fall;
   exact-phrase semantics must then use positions (below).

PostgreSQL stores the parsed form in a `tsvector`; the query parses to a
`tsquery`; matching uses the `@@` operator:

```sql
ALTER TABLE articles ADD COLUMN search tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(title,'') || ' ' || coalesce(body,''))) STORED;
CREATE INDEX idx_articles_search ON articles USING gin (search);

SELECT title, ts_rank(search, query) AS score
FROM articles, to_tsquery('english', 'retry & (timeout | failure)') AS query
WHERE search @@ query
ORDER BY score DESC
LIMIT 20;
```

## Indexing: GIN vs GiST — the trade that interviews test

Both index types can serve `@@`; they differ in exactly the ways their
general pages predict:

| | GIN | GiST |
|---|---|---|
| Lookup speed | fast (direct posting lists) | slower (lossy traversal, rechecks) |
| Update cost | high (insert into many posting lists; `fastupdate` pending list softens then pays) | low (incremental insertion) |
| Size | larger | smaller |
| Best for | read-heavy FTS (the common case) | write-heavy, quickly-changing text |

The engineering decision is the same one as
[bitmap vs B-tree](../indexing/bitmap-index.md): pay on write or pay on
read. A feed of rarely-updated articles wants GIN; a live-comment table
with per-row searchability may prefer GiST or no FTS index at all
(bounded window scans).

## Ranking: ts_rank and the BM25 gap

`ts_rank` scores by term frequency and position weights — it has *no
corpus statistics*: a term appearing in every document ranks as high as a
rare one. Production search engines rank with **BM25** (Okapi), the
probabilistic ranking function that adds inverse document frequency (rare
terms matter) and document-length normalization (long documents do not win
by default) — the canonical reference is Robertson & Zaragoza's
[*The Probabilistic Relevance Framework: BM25 and Beyond*](https://doi.org/10.1561/1500000019).
PostgreSQL's `ts_rank_cd` adds cover-density (proximity of query terms),
which fixes "all terms present, far apart" ranking, but neither is BM25.

When lexical ranking quality is the product (site search, relevance
review), the production patterns are: rank in the database for the long
tail and re-rank the top-k with a dedicated engine; or move search to a
BM25 engine entirely and treat SQL as the system of record (the
[Elasticsearch](../../search/elasticsearch.md) split). Interviews accept
either — what they probe is whether you know `ts_rank` is *not* BM25 and
what BM25 adds.

## Fuzzy and prefix: trigrams

Stemming handles *morphology* ("retries"→"retry"), not *typos* ("rerty")
or partial words ("pag"). Trigram decomposition (every 3-char sliding
window) does both: `retries` → `ret, etr, tri, rie, ies`, and similarity
is overlap of trigram sets — indexable with the same GIN machinery:

```sql
CREATE EXTENSION pg_trgm;
CREATE INDEX idx_articles_title_trgm ON articles USING gin (title gin_trgm_ops);

SELECT title, similarity(title, 'retyr patments') AS sim
FROM articles
WHERE title % 'retyr patments'          -- fuzzy match
ORDER BY sim DESC LIMIT 10;
```

Trigrams also make `LIKE '%pag%'` index-servable (the trigram index prunes
candidates, then a recheck verifies) — the only general fix for
leading-wildcard predicates inside SQL. Costs: trigram indexes are large
(every 3-char window is a key) and similarity thresholds are heuristic —
tune per language, and note CJK text needs different n-gram sizes.

## Phrase, prefix, and websearch syntax

- **Phrases** (`to_tsquery('english', 'payment <-1> failed')` — at most one
  word between) rely on *positions* recorded in the tsvector; positions are
  also what `ts_rank_cd` uses.
- **Prefix matching** (`retri:*`) serves typeahead; combined with a GIN
  index it is the poor-man's autocomplete (the full treatment is in
  [Search Autocomplete](../../interview/system-design/real-world/search-autocomplete.md)).
- **`websearch_to_tsquery`** parses user input the way a search box does
  (`"quoted phrases"`, `-excluded`, or) — the safe default for untrusted
  query strings; `to_tsquery` on raw user input is a syntax-error oracle.

## Hybrid search: lexical meets vector

The modern production pattern — and the current interview favorite — is
**hybrid retrieval**: BM25-style lexical candidates *and*
[vector similarity](../../search/vector-search.md) candidates, fused into
one ranking (typically reciprocal rank fusion or a learned
[reranker](../../search/reranking.md)):

```text
query → lexical channel:  SQL FTS (GIN) → top-k₁ by ts_rank/BM25
      → vector channel:   pgvector/embeddings → top-k₂ by cosine
      → fusion (RRF):     score = Σ 1/(60 + rank_channel(d)) → top-k
```

The channels are complementary by construction: lexical nails exact terms,
codes, and names (where embeddings blur); vectors nail paraphrase and
intent (where exact terms miss). Running both in one database (PostgreSQL
+ GIN + pgvector) is the small-scale default; splitting them is the
scale answer — the architecture decision mirrors
[HTAP](../advanced/htap.md): one engine, two indexes, two cost profiles.

## Interview questions

1. **Why can't `LIKE '%retry%'` serve search, and what does FTS change?**
   No index can serve a leading wildcard without auxiliary structure; FTS
   inverts the data — terms → documents — so lookup is O(posting list),
   and adds stemming/position/ranking that substring matching cannot
   express.
2. **Your FTS index updates are the insert bottleneck. Options?** GIN
   update cost (posting-list churn; the pending list's deferred cost):
   batch updates, switch to GiST for write-heavy shapes, drop to a bounded
   indexed window, or move search off the OLTP table (CDC → search
   engine) — the [CDC pattern](../../data-engineering/debezium.md)
   applied to search.
3. **`ts_rank` ranks a common word's documents highest — why?** No IDF:
   term frequency in the document is measured, but the term's rarity in
   the corpus is not. Either re-rank top-k externally with BM25, or use a
   search engine for ranked retrieval; know the gap by name.
4. **How would you add "did you mean" to a SQL-backed search?** Trigram
   similarity against a dictionary of indexed terms (or titles),
   thresholded, ranked by similarity × document frequency; `pg_trgm`'s
   `%`/`similarity()` with a GIN trigram index is the local implementation.

## Key Takeaways

- FTS = inverted index inside SQL: tokenize + stem into tsvector, query as
  tsquery, index with GIN (read-heavy) or GiST (write-heavy).
- `ts_rank` lacks corpus statistics — BM25 (IDF + length normalization) is
  the ranking default elsewhere; know the gap and the re-rank pattern.
- Trigrams solve typos and leading wildcards; phrase and prefix search
  rely on stored positions; use `websearch_to_tsquery` for user input.
- Hybrid lexical + vector retrieval is the default modern architecture;
  fuse with RRF and keep both channels — they fail on disjoint inputs.

## Cross-References

- [GIN Index](../indexing/gin.md) — posting-list storage and update mechanics.
- [GiST Index](../indexing/gist.md) — the alternative index and its lossy traversal.
- [Search Fundamentals](../../search/fundamentals.md) — retrieval metrics and engine-side ranking.
- [Vector Search](../../search/vector-search.md) and [Reranking](../../search/reranking.md) — the hybrid pipeline's other half.
- [Search Autocomplete](../../interview/system-design/real-world/search-autocomplete.md) — prefix serving at scale.
- [Elasticsearch](../../search/elasticsearch.md) — the dedicated-engine alternative.

## References

- PostgreSQL Documentation, "[Text Search](https://www.postgresql.org/docs/current/textsearch.html)", "[Text Search Indexes](https://www.postgresql.org/docs/current/textsearch-indexes.html)", and "[pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html)" — tsvector/tsquery semantics, GIN/GiST guidance, trigram operators.
- S. Robertson, H. Zaragoza, "[The Probabilistic Relevance Framework: BM25 and Beyond](https://doi.org/10.1561/1500000019)", *Foundations and Trends in Information Retrieval* 3(4), 2009 — BM25's derivation and parameters.
- PostgreSQL Documentation, "[Text Search Type](https://www.postgresql.org/docs/current/datatype-textsearch.html)" — positional tsvector layout behind phrase queries and `ts_rank_cd`.
