# Milvus

Milvus is an open-source vector database, originally developed by Zilliz (2018) and donated to the LF AI & Data Foundation in 2019. It's the most widely-deployed open-source vector database for AI workloads: storing and searching dense vectors from embedding models. This page covers the architecture, the index types supported, the hybrid search (vector + scalar filter), and the comparison to other vector databases (Pinecone, Weaviate, Qdrant).

## The Architecture

Milvus has a shared-storage architecture:

```text
┌──────────────────────────────────────────────────────────────┐
│  Coordinator cluster (HA via Raft)                            │
│  - RootCoord (DDL/DML coordinator)                            │
│  - DataCoord (segment assignment)                             │
│  - QueryCoord (query planning)                               │
│  - IndexCoord (index building)                                │
└──────────────────────────────────────────────────────────────┘
        │                              │
        │ gRPC                          │ gRPC
        ▼                              ▼
┌────────────────────────┐    ┌────────────────────────────────┐
│ Worker nodes             │    │ Storage layer                     │
│ - QueryNode (search)     │    │ - S3 / MinIO / Azure Blob         │
│ - DataNode (insert)      │    │ - Etcd (metadata)                 │
│ - IndexNode (build)      │    └────────────────────────────────┘
└────────────────────────┘
```

The coordinators are stateless (state is in etcd); workers are also stateless (state is in object storage). This separation enables independent scaling of compute and storage.

## Data Organization: Segments

Milvus organizes data into **segments**, each holding a contiguous range of primary keys:

```text
Collection: documents (1M rows)
   ├── Segment 1: rows 0-99,999 (sealed, indexed)
   ├── Segment 2: rows 100,000-199,999 (sealed, indexed)
   ├── Segment 3: rows 200,000-299,999 (sealed, indexed)
   ├── ...
   └── Growing segment: rows 950,000-950,123 (currently being inserted)
```

- **Growing segments** are in-memory (inserted but not yet indexed). Vector search uses brute-force on these.
- **Sealed segments** are indexed (e.g., with HNSW). Vector search uses the index.

The "IndexCoord" periodically seals growing segments and triggers IndexNode to build the index. The transition from growing to sealed is transparent to queries.

## Index Types

Milvus supports multiple index types per collection:

| Index | Recall | Memory | Throughput | Use case |
|-------|-------:|--------:|-----------:|----------|
| FLAT | 100% | 100% | Low | Small collections, exact search |
| IVF_FLAT | 95% | 100% | High | Medium collections (<10M) |
| IVF_SQ8 | 90% | 25% | Higher | Memory-constrained |
| IVF_PQ | 80-90% | 5-10% | Very high | Billion-scale |
| HNSW | 99% | 200% | Very high | Medium collections, max recall |
| DISKANN | 95% | 0% (on-disk) | Medium | Large collections, low RAM |
| GPU_IVF_FLAT | 95% | 100% | Very high (GPU) | GPU-accelerated search |

The user picks an index per collection. Multiple indexes can coexist (for different collections).

## Hybrid Search: Vector + Scalar Filter

A pure vector search returns the K nearest neighbors. A hybrid search returns the K nearest neighbors that also match a scalar predicate:

```sql
-- Milvus DDL
CREATE COLLECTION documents (
    id INT64 PRIMARY KEY,
    embedding FLOAT_VECTOR 768,
    category VARCHAR 64,
    publish_date INT64
);

INSERT INTO documents (id, embedding, category, publish_date) VALUES
    (1, [...], 'science', 20240101),
    (2, [...], 'tech', 20240115);

-- Hybrid search
SELECT * FROM documents
SEARCH embedding TO [0.1, 0.5, ...]
WITH top_k = 10
WITH metric_type = COSINE
FILTER category = 'science' AND publish_date > 20240101;
```

The query execution:
1. Filter the segments by the scalar predicate (`category = 'science' AND publish_date > 20240101`).
2. Run the vector search on the filtered rows.

For high-selectivity filters (most rows match), this is just the vector search with a filter post-check. For low-selectivity filters (few rows match), the filter pre-check is critical to avoid wasted vector search work.

Milvus optimizes this with bitmaps per scalar attribute, intersected with the search results.

## The Cost Model

Milvus's query coordinator decides which segments to query on which QueryNode, based on:
- Segment size (load balance).
- Segment index type (IVF can run on any QueryNode; HNSW needs RAM).
- QueryNode resources (RAM, CPU, GPU availability).

For multi-tenant workloads, Milvus supports "partition keys" — a scalar column that determines which partition a row belongs to. Queries with a partition key filter are routed only to the relevant partition.

## Production Performance

Typical Milvus performance on a 4-node cluster (32-core CPU, 64 GB RAM each):
- Insert: 50K vectors/sec (768-dim).
- Query (top-10, HNSW): ~5 ms per query at 1000 QPS.
- Query (top-10, IVF_FLAT): ~2 ms per query at 5000 QPS.

For billion-scale, Milvus uses DISKANN (on-disk index) which trades latency for capacity: ~50 ms per query at 100 QPS for 1B vectors on a single node.

## Comparison to Other Vector DBs

| Aspect | Milvus | Pinecone | Weaviate | Qdrant |
|--------|--------|----------|-----------|--------|
| Open source | Yes (Apache 2.0) | No | Yes (BSD-3) | Yes (Apache 2.0) |
| Cloud-managed | Zilliz Cloud | Yes | Weaviate Cloud | Qdrant Cloud |
| Hybrid search | Yes | Yes | Yes | Yes |
| GPU acceleration | Yes (GPU_IVF_FLAT) | No | No | No |
| Index types | Many (FLAT, IVF, HNSW, DISKANN, etc.) | Few (proprietary) | HNSW | HNSW + scalar |
| Best for | Large-scale, GPU | Cloud-native simplicity | Schema-first | Lightweight, Rust-based |

For greenfield deployments needing scale and flexibility, Milvus is the common choice. For simple cloud-native deployments, Pinecone is easier. For Rust-based performance, Qdrant.

## Common Pitfalls

1. **Forgetting that indexes need to be built.** A growing segment isn't indexed; queries on growing segments are brute-force. Wait for the IndexCoord to seal and index.

2. **Forgetting that adding indexes consumes memory.** HNSW is 2× the vector data size. PLAN for memory accordingly.

3. **Forgetting that segments grow to a fixed size.** Milvus auto-segments at 512 MB by default. Manually tuning the segment size for the workload can improve query latency.

4. **Forgetting that DISKANN is for disk-resident data.** Don't use DISKANN for in-RAM workloads; HNSW is much faster.

5. **Forgetting that Milvus doesn't support frequent updates.** Milvus uses immutable sealed segments; updates require insert+delete. For frequently-updated data, use a different DB.

6. **Forgetting that hybrid search requires planning.** Without an index on the scalar column, the filter is a linear scan. Create scalar indexes on frequently-filtered columns.

## References

- [Milvus documentation](https://milvus.io/docs/overview.md)
- Wang et al., "[Milvus: A Purpose-Built Vector Data Management System](https://dl.acm.org/doi/10.1145/3448016)" (SIGMOD 2021)
- [Milvus GitHub repository](https://github.com/milvus-io/milvus)
- [Zilliz Cloud (commercial Milvus)](https://zilliz.com/)
- [Pinecone documentation](https://docs.pinecone.io/)
- [Weaviate documentation](https://weaviate.io/developers/weaviate)
- [Qdrant documentation](https://qdrant.tech/documentation/)
- [DISKANN paper](https://papers.nips.cc/paper/9527-rand-nsg-approximating-nearest-neighbors-in-graph-space.pdf) (NeurIPS 2019)
