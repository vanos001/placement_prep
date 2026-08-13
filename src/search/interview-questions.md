# Search Engine Interview Questions

## Fundamentals

**Q: What is TF-IDF?**
A: TF (Term Frequency) = how often a term appears in a document. IDF (Inverse Document Frequency) = how rare a term is across all documents. TF-IDF = TF × IDF. High TF-IDF means the term is frequent in this document but rare overall — good discriminant.

**Q: What is BM25 and how does it improve on TF-IDF?**
A: BM25 (Best Match 25) improves TF-IDF with: (1) term frequency saturation (diminishing returns for repeated terms), (2) document length normalization (longer docs aren't unfairly favored), (3) tunable parameters (k1 for term frequency, b for length normalization).

**Q: What is the difference between stemming and lemmatization?**
A: Stemming chops word endings (running → run, better → bet via Lancaster; Porter/Snowball leave "better" unchanged). Lemmatization uses vocabulary and morphology to find the root form (better → good, running → run). Lemmatization is more accurate but slower.

## Elasticsearch

**Q: How does Elasticsearch scale horizontally?**
A: Through sharding. An index is split into shards distributed across nodes. Each shard is a Lucene index. Adding nodes allows more shards. Replicas provide HA and read scaling. Shard count is set at creation and can't be easily changed (use aliases).

**Q: What happens when you index a document?**
A: (1) Document is routed to a shard (hash of _id), (2) written to a shard's transaction log, (3) added to an in-memory buffer, (4) periodically flushed as a Lucene segment (refresh → searchable), (5) periodically committed to disk (flush → durable).

**Q: How do you handle relevance tuning?**
A: (1) Boost specific fields (`"title^2"` boosts title matches), (2) use function_score for custom scoring, (3) use `should` clauses for optional boosts, (4) use decay functions for geographic/date relevance, (5) use script_score for custom logic.

## References

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/)
- [Relevant Search — Turnbull & Berryman](https://www.manning.com/books/relevant-search)
