# Database Full-Text Search vs a Search Engine: Who Owns the Inverted Index?

## Overview

"Should search live in Postgres or in Elasticsearch?" is usually argued as a product-choice question, which invites feature checklists and marketing tables. The sharper question is mechanism-shaped: **a B-tree cannot answer "which documents contain all of these words?" because it indexes whole values, so something must invert the text into term-to-document mappings — and the real decision is who owns that inverted index, and what that ownership costs.** Keeping it inside the database means index maintenance rides the same transaction as the write; running a dedicated engine means every document is copied out of the database, analyzed differently, and made searchable on a delay. Both are legitimate; both have failure modes that only their mechanisms can explain.

This page runs the [handbook framework](./index.md) across the pair. The one-sentence preview: **database full-text search buys transactional consistency and one less system at the price of ranking depth and horizontal scale; a dedicated search engine buys BM25 tuning, aggregations, and horizontal read scaling at the price of a sync pipeline, eventual visibility, and a second storage engine to operate.** The honest middle — trigram indexes, `tsvector` columns with GIN, hybrid rank-and-filter queries — is not a compromise score but a set of specific mechanisms, and this page treats it that way. The comparison also doubles as a general lesson in index economics: an index is a materialized answer to a question, and the question "what words appear in this document?" materializes very differently from "what rows have this value?"

## Step 1: The Problem and Its Constraints

The abstract shape: users (or programs) query a text corpus — product titles, article bodies, log lines, support tickets — and expect results that match *and* rank well, fast. Constraints that decide where the inverted index should live:

- **Corpus size and growth.** Tens of thousands of documents and single-digit queries per second is a different universe from hundreds of millions with spiky read traffic; the second one stresses any single-node index, however clever.
- **Freshness.** Must a document be searchable in the same transaction that saved it (read-after-write), or is a second or two of indexing delay acceptable? This single constraint eliminates more architectures than any feature matrix.
- **Relevance quality.** Is "matches the terms" enough, or does ranking need term-frequency saturation, inverse-document-frequency weighting, field boosts, phrase proximity, and tunable scoring? Ranking is a feature with depth, not a checkbox.
- **Query shape.** Pure text? Text plus filters (facets, price ranges, geo)? Aggregations over matches ("counts per category for this query")? Aggregations change the engine conversation entirely.
- **Consistency jurisdiction.** Is search allowed to disagree with the database of record, ever? For a product catalog, eventual is usually fine; for "did my deletion propagate?", it may not be.
- **Operational budget.** Who runs the second system, its cluster upgrades, its reindexing, and the pipeline that keeps it in sync? A built-in index and a separate cluster are not equally easy to own.

## Step 2: The Mechanisms

### Full-text search inside the database

PostgreSQL's approach is representative: text is converted into a `tsvector` — a sorted list of lexemes produced by a configurable [text search configuration](https://www.postgresql.org/docs/current/textsearch-intro.html) (tokenizer, stopword list, stemmer) — and a query becomes a `tsquery` over those lexemes. The inverted index itself is a [GIN index](https://www.postgresql.org/docs/current/gin.html): a posting tree mapping each lexeme to the rows containing it. The mechanisms that matter:

- **Index maintenance is transactional.** The postings update commits (or rolls back) with the row. There is no sync pipeline, no reindex window in the normal case, and no read-after-write gap: a document committed is searchable in the next query. The cost shows up as write amplification and index bloat inside the database's own storage budget, where it competes with every other index for the same buffers and checkpoints.
- **Updates are not free at any size.** GIN's fast-update path accumulates postings in a pending list that merges into the tree when it overflows — usually amortized, occasionally a single INSERT that pays for the whole merge. High-frequency terms (the word "the", a status field indexed as text) grow posting lists proportionally to document frequency, which is why naive "index everything" schemes bloat.
- **Ranking is SQL-side.** `ts_rank` and its variants score with term frequency and normalization rules, executed against the posting sets; no idf is computed globally across the corpus by default, and proximity, phrase boosting, and learned ranking require extension work.
- **Scaling is the database's.** Vertical capacity, read replicas, and partitioning apply; there is no dedicated distributed query layer that shards the index and merges scores.

### The dedicated search engine

Elasticsearch (built on Lucene) is a distributed inverted index: documents are analyzed the same way in principle — tokenize, filter, stem — but the resulting index lives in immutable **segments** that merge in the background. Writes land in an in-memory buffer plus a translog; a **refresh** (roughly once a second by default) makes new documents visible to search. The mechanisms that matter:

- **Visibility is near-real-time, not transactional.** A successful index request does not mean searchable — the refresh interval does. Read-after-write is available as an explicit `refresh` call, paid for per call. Deletes are tombstones against segments until merges reclaim them, so update-heavy workloads carry deleted-document overhead between merges.
- **Scoring is BM25 with per-shard statistics.** Inverse document frequency is computed over shard-local statistics; a shard with unusual contents (or tiny shards on a small index) skews relevance until query-time global statistics are forced, at the cost of an extra round trip.
- **Aggregations are a first-class engine.** Doc values (column-oriented per-segment structures) make facet counts, histograms, and nested analytics over millions of matches a routine query shape — the analytical complement to the [column-store](./row-vs-column-stores.md) argument, embedded in the search engine.
- **Scale-out is architectural.** Shards distribute both the index and the query; replicas multiply read throughput; the cluster coordinates scatter-gather. The price is the cluster itself: node failure, rebalancing, shard planning, and the [sync pipeline](./app-events-vs-cdc.md) that copies documents out of the system of record.

## Step 3: Complexity, Guarantees, and Failure Modes

| Property | Database full-text (e.g., Postgres FTS) | Dedicated engine (e.g., Elasticsearch) |
|----------|------------------------------------------|----------------------------------------|
| Index ownership | Same engine as the data; one storage budget | Separate cluster; documents copied out of the source |
| Write path | Index update commits with the row | Buffer + translog, searchable after refresh |
| Read-after-write | Guaranteed within the transaction | Not by default; explicit refresh or wait ~1s |
| Consistency vs system of record | None needed — it *is* the record | Eventually consistent; drift is the pipeline's failure mode |
| Scoring | Term frequency + normalization; global idf absent by default | BM25 with tunable depth; shard-local idf skew |
| Aggregations/facets | Possible but awkward; not the optimizer's home turf | Native, column-backed, designed for it |
| Fuzzy/phrase/proximity | Available with extensions and care | First-class query types |
| Scaling model | Vertical + replicas; partitioning by hand | Shards + replicas, scatter-gather built in |
| Operational surface | One system to back up, tune, upgrade | Two systems plus the sync pipeline and reindexing |
| Characteristic failure | GIN bloat and pending-list merge cliffs; planner surprises | Sync drift, refresh-visible staleness, shard-hotspotting |

The **consistency jurisdiction** deserves the arrow drawn. The database index cannot disagree with the table — it is updated by the same commit — so its failure modes are performance failures: bloat, merge cliffs, slow plans. The separate engine's failure modes are *truth* failures: the sync job behind, the reindex that was forgotten after a mapping change, the deleted document still surfacing in results. A team choosing the engine is choosing to operate a pipeline whose correctness is silent — search works, returns plausible results, and drifts. That is why mature setups treat reindexing as a routine operation with aliases and zero-downtime cutover rather than an emergency.

## Step 4: When Each Wins

| Condition | Choice | Why |
|-----------|--------|-----|
| Corpus up to a few million rows, moderate query load | Database FTS | Transactional index, zero extra infrastructure, joins with relational data for free |
| Search must agree with the transaction (read-after-write, no drift) | Database FTS | Same-commit visibility; a sync pipeline cannot make this promise |
| Relevance is a product feature (tuning, boosting, faceting at scale) | Search engine | BM25 depth, analyzers per field, aggregation engine |
| Large corpus, spiky read load, sub-100 ms p99 | Search engine | Sharded index and replica read scaling |
| Search over data that lives in many tables/services | Search engine | Denormalized documents indexed once, queried in one place |
| Log/metric analytics over high write volume | Search engine | Segment-based writes absorb ingest; aggregations answer the questions |
| No ops capacity for a second cluster | Database FTS | The hidden cost is the pipeline and the cluster, not the license |

**Database FTS wins** for the long middle of applications: e-commerce catalogs at small scale, documentation search, admin panels, "search" as one query among hundreds — where joins, transactions, and one operational surface dominate and relevance tuning needs are modest. **A dedicated engine wins** when search becomes a workload of its own: relevance iteration as a product discipline, analytical facets over matches, corpus growth past what one node serves, or federated text from many sources. **The honest hybrid** is a staged path: start in the database, watch the metrics that mark the boundary (p99 under load, index bloat growth, relevance complaints), and move the text workload out when evidence — not fashion — crosses it, using the database of record as the reindexing source of truth forever after.

## Step 5: Edge Cases and Counterexamples

- **The GIN pending-list cliff.** Fast-update GIN absorbs posting changes into a pending list bounded by `gin_pending_list_limit`; when it fills, the *inserting transaction* pays for the merge. A workload that inserted calmly for weeks suddenly shows one write taking seconds — the merge — and operations adds a CPU upgrade instead of a tuning change. Disabling fastupdate trades the cliff for per-write cost; the mechanism, not the setting name, explains which workload should choose which.
- **BM25's shard-local idf.** An index with 12 shards over 50,000 documents computes idf per shard; a term rare on one shard but common corpus-wide ranks wrong. The textbook fix (`dfs_query_then_fetch`) issues an extra round trip to gather global statistics — correctness paid in latency, on every query. The deeper lesson: distributed scoring inherits distributed-statistics problems, and small corpora — where the dedicated engine is least needed — suffer it most.
- **The save-that-search-cannot-find.** A user saves an edit, immediately searches for it, and nothing comes back: the document is in the buffer, the refresh has not run, and the UI promised transactional semantics the pipeline never had. Either the client refreshes explicitly (paying per-write), or the UI learns to represent "indexed soon" — a product decision forced by a mechanism.
- **The dual-write drift that no one noticed.** Application code writes Postgres then Elasticsearch; a deploy adds an error path that skips the second write "temporarily"; search keeps working against stale documents for weeks. The durable fixes are structural, not vigilant: CDC from the WAL as the single copy path, or the database as an authority the engine rebuilds from — the [outbox and CDC](./app-events-vs-cdc.md) territory.
- **The `LIKE '%term%'` that an index cannot serve.** A leading wildcard defeats B-trees entirely; the trigram (`pg_trgm`) index — a different decomposition of text into overlapping triples — restores index-assisted substring search inside the database. The middle ground is real, and it is a mechanism, not a compromise: the index materializes a different question ("which strings share trigrams?") with different costs.

## Step 6: Decision Framework

1. **Does search need transactional agreement with the data of record?** Yes → in-database FTS; no pipeline can honestly promise what a commit does.
2. **Is the corpus and load small enough that one node serves it with headroom?** Yes → in-database FTS; the second cluster's cost exceeds its ranking benefit.
3. **Is relevance a product differentiator needing tuning, boosting, per-field analyzers?** Yes → dedicated engine; scoring depth is where it pays rent.
4. **Do queries need heavy aggregations/facets over matches?** Yes → dedicated engine; doc values and its aggregation engine are native.
5. **Is the corpus growing past single-node serving, or federated from many sources?** Yes → dedicated engine with CDC from the source of truth.
6. **Default in doubt:** database FTS with a `tsvector` column, GIN index, and ranked queries; instrument p99 latency, bloat, and relevance complaints; migrate the text workload to a dedicated engine when a metric crosses the line, keeping the database as the reindex source.

## Interview Questions

1. **Why can't a B-tree serve "documents containing all these words"?** A B-tree indexes whole values in sorted order and answers prefix/range/point questions; the full-text question needs a mapping from each term to every document containing it — an inverted index with posting lists per analyzed lexeme. The analysis step (tokenize, stem, stopwords) is what makes two systems that both "have indexes" incomparable on features.
2. **A search result shows a document the user deleted minutes ago. Walk the failure.** The delete committed in the database; the removal event to the search engine failed or lagged; the tombstone/refresh cycle had not propagated. This is a truth failure specific to index ownership separation — the in-database index cannot have this bug because its postings commit with the row.
3. **What exactly does the refresh interval buy, and what does it cost?** It batches index writes into immutable segments, which is what makes Lucene writes cheap and searches fast; the cost is a window where committed documents are invisible, plus explicit-refresh costs when read-after-write is required. Tuning it is trading write amortization against visibility latency.
4. **Why does BM25 rank differently on small sharded indexes?** Idf statistics are computed per shard at query time; with few documents per shard, shard-local frequencies diverge from corpus frequencies and scores skew. Forcing distributed frequency statistics fixes accuracy at the cost of an extra round trip per query.
5. **When is staying in the database the *wrong* answer despite a small corpus?** When relevance iteration is core to the product (ranking experiments, custom analyzers), when heavy aggregation over matches is on every page, or when the search corpus is federated from services that do not share a database — the sync cost is then justified by capability, not scale.

## Key Takeaways

- The fork is **who owns the inverted index**: the database commits postings with the row (consistency for free, ranking depth and scale-out bounded), or a dedicated engine owns analyzed segments (scoring depth, aggregations, shards — plus a sync pipeline whose drift is silent).
- Visibility semantics are mechanism consequences: transactional read-after-write inside the database; refresh-interval near-real-time in the engine, with explicit refresh as the paid escape hatch.
- Each side's signature failure differs in kind: the database fails performance (bloat, merge cliffs); the engine fails truth (drift, staleness).
- The middle ground is real mechanisms — trigram indexes for substring search, tsvector plus GIN as a serious default — not a watered-down engine.
- Migrate on metrics, not fashion: relevance iteration, aggregation load, and corpus growth are the lines; the database of record remains the reindex source either way.

## Cross-References

- [Row vs Column Stores: Why-Not Handbook](./row-vs-column-stores.md) — the sibling layout-economics fork: which physical structure is cheap at which access shape.
- [Database Choices: Why-Not Handbook](./database-choices.md) — the workload-to-engine mapping this page's Step 4 table plugs into.
- [App Events vs CDC: Why-Not Handbook](./app-events-vs-cdc.md) — the outbox/CDC machinery that makes the sync pipeline trustworthy.
- [Search and the Inverted Index: Connection Atlas](../connection-atlas/search-inverted-index.md) — the dependency web linking analyzers, postings, and ranking.
- [Database Indexes: Follow-up Tree](../followup-tree/database-indexes.md) — the escalation ladder for index questions from B-tree upward.
- [Full-Text Search](../../dbms/sql/full-text-search.md) — the practical SQL-side mechanics: tsvector, tsquery, ranking functions.
- [Search Engine Internals](../../dbms/nosql/search-engine-internals.md) — segment, merger, and shard mechanics behind the dedicated engine.
- [GIN Index](../../dbms/indexing/gin.md) — the posting-tree structure and pending-list behavior behind the cliff edge case.
- [Search](../../interview/system-design/search.md) — the design-interview application of this comparison.
- [Why-Not Handbook](./index.md) — the framework and sibling comparisons.
