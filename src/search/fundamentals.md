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

## Cross-references

- [Vector Search](./vector-search.md)
- [Elasticsearch](./elasticsearch.md)
- [Search interview questions](./interview-questions.md)
- [Information retrieval in system design](../interview/system-design/search.md)
- [Probabilistic Data Structures](../interview/system-design/probabilistic-data-structures.md)
- [Data Quality](../data-engineering/data-quality.md)

## References

- [Stanford Introduction to Information Retrieval](https://nlp.stanford.edu/IR-book/)
- [Elasticsearch text analysis](https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis.html)
- [Lucene scoring](https://lucene.apache.org/core/)
- [TREC evaluation resources](https://trec.nist.gov/)
