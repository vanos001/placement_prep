# Vector Search

Vector search retrieves items by semantic or learned similarity rather than
only exact lexical overlap. A model maps text, images, code, or other objects
to vectors; an approximate nearest-neighbor index finds candidates; filters and
reranking produce the final result.

## Retrieval pipeline

```mermaid
flowchart LR
    Q["Query"] --> E["Embedding model"]
    E --> V["Query vector"]
    V --> ANN["ANN index"]
    ANN --> C["Candidate vectors"]
    C --> F["Metadata and access filters"]
    F --> R["Rerank"]
    R --> O["Results with evidence"]
```

A vector index is not a replacement for a keyword index. Hybrid search often
combines lexical recall, vector recall, filters, and a learned or rule-based
reranker.

## Similarity and normalization

Common similarity functions include cosine similarity, dot product, and squared
Euclidean distance. If vectors are normalized, cosine similarity and dot
product are closely related. Match the index metric to the embedding model and
training objective; do not normalize blindly.

Document the embedding model, dimension, normalization, chunking policy,
metadata filters, and distance interpretation. Changing any of these can make
old vectors incompatible or silently reduce recall.

## Approximate nearest-neighbor indexes

### HNSW

Hierarchical Navigable Small World graphs connect vectors at multiple layers.
Search descends from sparse upper layers into a dense bottom layer. `M`,
construction effort, and search parameter `efSearch` trade memory, build time,
recall, and query latency.

### IVF

Inverted File indexes cluster vectors into partitions. Query-time search visits
only selected clusters. `nlist` and `nprobe` trade index size and recall.

### Product quantization

PQ compresses vectors by quantizing subspaces. It reduces memory and improves
cache behavior at the cost of distance approximation; rerank candidates with
full-precision vectors when quality matters.

### Disk-oriented indexes

DiskANN-style or paged graph indexes trade random memory for SSD access. They
are useful when the vector corpus exceeds RAM, but tail latency, compaction,
replication, and SSD endurance become design concerns.

## Filtering and hybrid retrieval

Apply tenant and authorization filters before returning candidates. A vector
nearest neighbor without an access-control filter is a data leak.

Hybrid retrieval options include:

- Weighted lexical plus vector scores.
- Reciprocal rank fusion.
- Lexical retrieval for exact identifiers and vector retrieval for concepts.
- Reranking a union of lexical and ANN candidates.
- Metadata prefilters when the index supports them; postfilters can return too
  few results when the candidate pool is small.

## Retrieval-augmented generation

In RAG, vector search retrieves context for a generator. Quality depends on
chunk boundaries, metadata, query rewriting, hybrid retrieval, reranking,
context limits, and citation/evidence handling—not just the embedding model.

Measure retrieval separately from generation:

- Recall@k and context recall.
- Context precision and duplicate rate.
- Answer faithfulness to retrieved evidence.
- Answer relevance and task completion.
- Latency, token cost, and index freshness.

## Operations

- Version embeddings and keep a reproducible re-index path.
- Monitor index build failures, vector dimension mismatches, deleted items,
  query latency, recall samples, and filter selectivity.
- Keep source IDs and evidence metadata with every vector.
- Use deterministic chunk IDs so updates replace old chunks instead of creating
  duplicates.
- Partition by tenant or collection when isolation and lifecycle differ.
- Test adversarial and out-of-domain queries; high similarity is not proof of
  truth.

## Interview questions

**Why is vector search approximate?**

Exact nearest-neighbor search scans every vector and becomes expensive at
scale. ANN indexes reduce work by exploring a subset while targeting an
acceptable recall/latency trade-off.

**HNSW versus IVF?**

HNSW uses a navigable graph and often gives strong recall/latency in memory;
IVF partitions the space and can combine with quantization and disk-oriented
storage. Choose based on corpus size, update pattern, memory, and workload.

**Why use hybrid search?**

Lexical search is strong for exact names, identifiers, and rare terms; vector
search is strong for semantic similarity. Their failure modes differ, so fusion
usually improves robustness.

**Why can a good embedding still give bad RAG answers?**

The query may be poorly formed, chunks may split context, filters may remove
evidence, reranking may be weak, or the generator may ignore retrieved text.
Evaluate each stage separately.

## Cross-references

- [Search Fundamentals](./fundamentals.md)
- [Elasticsearch](./elasticsearch.md)
- [RAG](../llm/llm-serving/rag.md)
- [Vector Databases](../llm/llm-serving/vector-databases.md)
- [Probabilistic Data Structures](../interview/system-design/probabilistic-data-structures.md)
- [Data Quality](../data-engineering/data-quality.md)

## References

- [FAISS documentation](https://faiss.ai/)
- [HNSW paper](https://arxiv.org/abs/1603.09320)
- [Elasticsearch vector search](https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search.html)
- [Milvus ANN concepts](https://milvus.io/docs/index.md)
- [Stanford Information Retrieval book](https://nlp.stanford.edu/IR-book/)
