# Vector Databases & Approximate Nearest Neighbor Search

Vector databases are purpose-built for storing, indexing, and querying high-dimensional vector embeddings. This chapter covers the internals of approximate nearest neighbor (ANN) algorithms (HNSW, IVF, PQ, DiskANN), vector index maintenance, hybrid search, and the emerging landscape of AI-native and RAG databases.

## Why Vector Databases?

Modern ML models (sentence transformers, CLIP, OpenAI embeddings) map data — text, images, audio — into dense vectors of 128-4096 dimensions. Querying "find me similar items" becomes a **k-nearest-neighbor (k-NN)** search in this high-dimensional space.

```
Text:  "the cat sat on the mat"  → Embedding model → [0.12, -0.34, 0.56, ..., 0.78]  (768-dim)
Image: 🐱                        → CLIP model     → [0.11, -0.33, 0.58, ..., 0.75]  (768-dim)

Cosine similarity or L2 distance measures closeness.
```

**Exact k-NN** is O(n·d) per query (brute-force scan of all n vectors of dimension d). For billion-scale collections, this is too slow. **Approximate nearest neighbor (ANN)** algorithms trade a small recall loss for orders-of-magnitude speedup.

## ANN Algorithm Families

| Algorithm | Recall@10 (typical) | Build Time | Memory | Disk Support | Used In |
-----------|-------------------|------------|--------|-------------|----------|
| **Brute-force** | 100% | O(1) | O(n·d) | Yes | Small datasets |
| **IVF** | 90-99% | O(n·k·d) | O(n·d) | No (in-memory) | FAISS, Milvus |
| **IVF-PQ** | 85-95% | O(n·k·d + n·m·d/k) | O(n·m) | No | FAISS |
| **HNSW** | 95-99.9% | O(n·log(n)·M) | O(n·M) | No (in-memory) | Qdrant, Weaviate, pgvector |
| **DiskANN** | 90-98% | O(n·log(n)) | O(n) | Yes (SSD) | Azure AI Search |
| **ScaNN** | 95-99% | O(n·d) | O(n·d) | No | Google internal |

## HNSW Internals

### Hierarchical Navigable Small World (Malkov & Yashunin, 2018)

HNSW is a **multi-layer proximity graph** inspired by skip lists. Each vector is a node in the graph, with edges to its nearest neighbors. The graph has multiple layers; upper layers have fewer nodes and longer-range edges, enabling fast navigation.

```
Layer 2:    A -------- B                (few nodes, long edges)
            |          |
Layer 1:    A --- C -- B --- D          (medium)
            |  \ | /  |  \ |
Layer 0:    A-C-E-B-D-F-G-H-I-J        (all nodes, short edges)
```

### Parameters

| Parameter | Meaning | Typical Value | Effect |
-----------|---------|---------------|--------|
| **M** | Max edges per node (per layer) | 16-64 | Higher M → better recall, more memory |
| **ef_construction** | Beam width during index build | 200-500 | Higher → better graph quality, slower build |
| **ef_search** | Beam width during query | 50-200 | Higher → better recall, slower query |
| **max_level** | Number of layers | Auto-determined | Usually log₂(n) |

### Search Algorithm

```python
def hnsw_search(query, k, ef_search):
    # Phase 1: Greedy descent from top layer
    entry_point = graph.top_layer_entry
    for layer in range(max_layer, 0, -1):
        entry_point = greedy_search(query, entry_point, layer, 1)
    
    # Phase 2: Beam search on layer 0
    candidates = MinHeap()  # distance-sorted
    visited = Set()
    candidates.push(entry_point, distance(query, entry_point))
    
    while candidates is not empty:
        nearest = candidates.pop()
        if nearest.distance > candidates.kth_largest.distance:
            break  # all remaining candidates are farther
        for neighbor in graph[nearest][0]:  # layer 0
            if neighbor not in visited:
                visited.add(neighbor)
                d = distance(query, neighbor)
                candidates.push(neighbor, d)
    
    return candidates.top_k(k)
```

### Performance Characteristics

- **Query latency**: O(log n) graph traversal + O(ef_search × M) distance computations. For M=16, ef_search=100, n=1M: ~1600 distance computations (vs. 1M for brute force).
- **Memory**: Each edge stores a node ID (4-8 bytes). With M=16, memory per node is ~16 × 8 = 128 bytes for edges + d × 4 bytes for the vector. For 768-dim float32: 128 + 3072 = 3200 bytes/node.
- **Insert**: O(log n × M × d) — find entry point, greedy search to layer 0, connect to M nearest neighbors.

> **Interview Angle**: "Explain how HNSW works." — Describe the multi-layer skip-list-inspired graph, greedy descent, beam search on the bottom layer, and the key parameters (M, ef_construction, ef_search). Mention that HNSW is the dominant in-memory ANN algorithm, used by pgvector, Qdrant, and Weaviate.

## IVF (Inverted File Index)

### Architecture

IVF (Jegou et al., 2011) partitions the vector space into **V clusters** using k-means, then builds a **per-cluster inverted index**. At query time, only the `nprobe` nearest clusters are searched.

```
Build:
1. Run k-means with V centroids on all vectors
2. Assign each vector to its nearest centroid
3. Store: {centroid → [list of vectors in this cluster]}

Query:
1. Find nprobe nearest centroids to the query
2. Search all vectors in those nprobe clusters (brute-force)
3. Return top-k from combined results
```

```
V=4 centroids, nprobe=2:
  Query Q → nearest centroids: C1, C3
  Search all vectors in cluster C1 and C3 → top-k
  Skip clusters C2, C4
```

### Parameters

| Parameter | Effect | Tradeoff |
-----------|--------|----------|
| **V** (nlist) | Number of clusters | Higher V → finer partitioning, more memory for centroids |
| **nprobe** | Clusters searched per query | Higher nprobe → better recall, slower query |

Typical: V=√n, nprobe=8-64. For 1M vectors, V=1000, nprobe=32 searches ~32K vectors (3.2% of data).

## Product Quantization (PQ)

### Idea

PQ (Ge et al., 2008) compresses vectors by **splitting** each d-dimensional vector into m subvectors, each quantized independently:

```
Original vector (d=128, m=4):
  [v0..v31 | v32..v63 | v64..v95 | v96..v127]
   sub-0      sub-1      sub-2      sub-3

Each sub-vector is quantized to one of 256 centroids (8 bits):
  sub-0 → code 142  (closest of 256 centroids)
  sub-1 → code 7
  sub-2 → code 203
  sub-3 → code 51

Compressed: 128 floats × 4 bytes = 512 bytes → 4 bytes (1 byte per sub-vector)
Compression ratio: 128x
```

### PQ Distance Computation

Distance is approximated using a **precomputed lookup table**:

```python
def pq_distance(query, pq_code, codebooks, m):
    # Precompute: for each sub-space, distance from query sub-vector to all 256 centroids
    # lookup_table[m][256] — computed once per query
    dist = 0
    for i in range(m):
        dist += lookup_table[i][pq_code[i]]
    return dist
```

The lookup table is O(m × 256 × 4) bytes = small enough for L1/L2 cache. PQ distance computation is O(m) additions instead of O(d) — **128x faster** for d=128, m=4.

### IVF-PQ

Combining IVF with PQ: first use IVF to narrow to `nprobe` clusters, then use PQ to approximate distances within those clusters. This is the standard configuration in **FAISS** for billion-scale search.

## DiskANN

### The Problem with In-Memory ANN

HNSW and IVF keep all vectors in memory. For billion-scale collections with 768-dim vectors, this requires ~3TB of RAM — prohibitively expensive.

### DiskANN (Jayaram Subramanya et al., SIGMOD 2019)

DiskANN builds an **HNSW-like graph** optimized for SSD access:

1. **Vamana graph**: A disk-friendly proximity graph (similar to HNSW layer 0) with degree bounded by **R** (typically 64-128).
2. **PQ-compressed vectors on disk**: Full-precision vectors are replaced by PQ codes on SSD. Centroid tables are memory-resident.
3. **Memory-resident metadata**: Only the graph structure (node → neighbor list) and PQ centroid tables are in memory (~30-40 bytes/vector).
4. **SSD-aware access**: Search follows graph edges, fetching PQ-compressed vectors from SSD. Prefetching hides SSD latency.

```
Memory: graph (R neighbors × 4B) + PQ lookup tables
SSD: PQ-compressed vectors (4-16 bytes per vector)

For 1B vectors, d=768, m=96 (96 sub-vectors, ~8 bytes per vector):
  Memory: 1B × (128 × 4 + 96 × 256 × 4) ≈ 100 GB (graph + centroids)
  SSD: 1B × 8 bytes = 8 GB
```

DiskANN achieves **sub-5ms QPS** for billion-scale search on a single server with NVMe SSD. It is used in **Azure AI Search**.

## Vector Index Maintenance

Real-world vector databases must handle **inserts, deletes, and updates**:

| Challenge | HNSW | IVF | DiskANN |
-----------|------|-----|----------|
| **Insert** | O(log n × M × d) — connect to neighbors | Add to cluster, periodic re-cluster | Insert into Vamana graph |
| **Delete** | Mark as deleted (tombstone), periodic compaction | Remove from cluster list | Tombstone + periodic rebuild |
| **Bulk load** | Build graph incrementally | Bulk k-means, batch assign | Bulk graph construction |
| **Recall degradation** | Gradual (new nodes may have suboptimal connections) | Significant (cluster drift) | Moderate |

Most systems mitigate degradation with **background index rebuilds** (periodic re-indexing) and **graph pruning** (removing dead nodes and re-routing edges).

## Hybrid Search

Hybrid search combines **vector similarity** with **keyword/scalar filtering**:

```sql
-- Find similar documents that also match a keyword
SELECT * FROM documents
WHERE embedding <-> '[0.1, -0.3, ...]' < 0.5  -- vector distance
  AND body ILIKE '%machine learning%'            -- keyword filter
  AND created_at > '2024-01-01'                  -- scalar filter
ORDER BY embedding <-> '[0.1, -0.3, ...]'
LIMIT 20;
```

**Implementation strategies**:

1. **Post-filtering**: Run ANN search first, then apply filters. Simple but may return fewer than k results if many candidates are filtered out.
2. **Pre-filtering**: Apply scalar filters first (via B-tree or bitmap index), then run ANN on the filtered subset. Correct but expensive if the filter is highly selective.
3. **HNSW with metadata**: Some systems (Qdrant, Weaviate) store metadata alongside HNSW nodes and prune during search. This is an approximation.
4. **Two-stage**: Use a fast ANN to get top-1000 candidates, then re-rank with keyword BM25 scores using a weighted combination (e.g., `score = α × vector_sim + (1-α) × bm25`).

## Vector Query Optimization

Vector queries involve a unique cost model compared to traditional SQL:

- **Cost of distance computation**: O(d) per comparison, where d is dimensionality. PQ reduces this to O(m).
- **I/O cost**: DiskANN queries involve SSD reads (100μs each). HNSW queries are pure in-memory.
- **Selectivity of pre-filters**: Scalar filters can reduce the candidate set dramatically.

Optimizers for vector databases (emerging area) consider:
- Whether to use PQ compression or full-precision distance
- How many clusters to probe (nprobe) based on filter selectivity
- Whether to scan or use the index for low-selectivity filters

## AI-Native Databases & RAG

### RAG Database Architecture

Retrieval-Augmented Generation (RAG) pipelines require a database that:
1. Stores document chunks with their embeddings
2. Supports fast vector similarity search (top-k retrieval)
3. Returns the original text alongside the similarity scores
4. May support metadata filtering (source, date, topic)

```
User Query → Embedding → Vector DB (top-k chunks) → LLM Prompt → Answer
                              ↓
                    [chunk_1, chunk_3, chunk_7]
                    + metadata filtering by tenant/source
```

### Multimodal Databases

Multimodal databases handle **multiple embedding types** (text, image, audio) in a unified system:

- **Weaviate**: Supports OpenAI, CLIP, and custom models. Each object can have multiple vector embeddings.
- **Zilliz/Milvus**: Multi-vector support with heterogeneous indexing strategies per vector field.
- **pgvector (PostgreSQL)**: Stores vectors as array columns with IVF-HNSW or HNSW index. Leverages PostgreSQL's transactional guarantees.

### Vector Database Comparison

| System | Index Types | Filtering | Distributed | SQL | Transactional |
--------|------------|-----------|-------------|-----|---------------|
| **pgvector** | IVF-Flat, HNSW | PostgreSQL WHERE | No (extension) | Full PostgreSQL | Full ACID |
| **Qdrant** | HNSW | Payload filtering | Yes (sharding) | Custom API | No |
| **Weaviate** | HNSW | GraphQL filters | Yes (replication) | GraphQL/REST | No |
| **Milvus** | IVF, HNSW, DiskANN | Scalar filtering | Yes (cloud-native) | Custom API | No |
| **Pinecone** | Proprietary ANN | Metadata filters | Managed | REST API | No |
| **ChromaDB** | HNSW | Where clauses | No | Python API | No |
| **Elasticsearch** (kNN) | HNSW | Full ES query DSL | Yes | Full ES DSL | Eventual |

> **Interview Angle**: "Compare HNSW, IVF, and DiskANN for vector search." — HNSW is the best in-memory ANN with high recall. IVF-PQ is good for large-scale with compression. DiskANN enables billion-scale search on SSD. For RAG workloads with < 10M vectors, pgvector or ChromaDB suffices; for > 100M, consider Milvus or Qdrant.

## References

- Malkov, Y. & Yashunin, D. "Efficient and Robust Approximate Nearest Neighbor Search Using Hierarchical Navigable Small World Graphs." IEEE TPAMI, 2018.
- Jayaram Subramanya, S. et al. "DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node." NeurIPS, 2019.
- Johnson, J. et al. "Billion-scale Similarity Search with GPUs." IEEE TBD, 2021. (FAISS)
- Ge, T. et al. "Optimized Product Quantization." IEEE TPAMI, 2014.
