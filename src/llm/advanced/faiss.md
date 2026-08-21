# FAISS

FAISS (Facebook AI Similarity Search) is an open-source library for efficient similarity search of dense vectors, developed by Facebook AI Research (now Meta AI) since 2017. It's the most widely-used library for vector similarity search, with implementations in C++ (with Python bindings) and GPU acceleration. This page covers the index types (flat, IVF, HNSW, PQ), the trade-offs between recall and throughput, and the production use cases (RAG, recommendation, deduplication).

## Why FAISS Exists

Neural networks produce dense vectors (typically 768-1536 dimensions) that represent the semantic content of inputs (text, images, audio). To find "the most similar items" in a database, you need to:

1. Embed each database item into a vector.
2. Embed the query.
3. Find the K database vectors closest to the query vector (via cosine similarity or L2 distance).

The naive approach: linear scan, computing distance from query to every database vector. For a 1M-vector database with 768-dim vectors, that's 768M operations per query — too slow.

FAISS builds an index structure that sub-linearly finds the K nearest neighbors.

## The Index Types

### Flat (exact)

A flat index stores all vectors; the query computes distance to every vector. This is O(N × D) per query for N vectors of D dimensions.

- **IndexFlatL2**: L2 (Euclidean) distance.
- **IndexFlatIP**: inner product (cosine similarity, if vectors are normalized).

For 1M vectors, 768 dims: ~2 ms per query on a CPU with SIMD, ~50 µs on a GPU.

Pros: 100% recall. Cons: doesn't scale beyond ~1M vectors on a single machine.

### IVF (Inverted File)

IVF partitions the vector space into Voronoi cells via k-means clustering:

1. Cluster the database vectors into k centroids (default k = sqrt(N)).
2. Each database vector is assigned to its nearest centroid.
3. At query time, find the k nearest centroids; search only the vectors in those cells.

```text
1M vectors → 1000 centroids (k = sqrt(1M))
Per query:
  - Find 8 nearest centroids (probe = 8).
  - Search ~8 cells × 1000 vectors each = 8000 vectors.
  - O(8000 × D) instead of O(1M × D). 125× speedup.
```

The trade-off: if the query's nearest neighbor is in a cell not probed, it's missed. The "recall" (fraction of true nearest neighbors found) depends on `nprobe`:

- `nprobe=1`: ~50% recall, very fast.
- `nprobe=8`: ~95% recall, ~10× faster than flat.
- `nprobe=64`: ~99% recall, ~3× faster than flat.

### HNSW (Hierarchical Navigable Small World)

HNSW is a graph-based index. Each vector is a node; edges connect "near" vectors. The query traverses the graph, jumping between near neighbors.

```text
Graph structure:
  Layer 2: a few "hub" vectors, connected.
  Layer 1: more vectors, connected to layer 2 hubs.
  Layer 0: all vectors, connected to nearby vectors.

Query: start at layer 2 hub. Greedily move to the closest neighbor on layer 2.
  Move to layer 1. Greedily move to the closest neighbor.
  Move to layer 0. Greedily move to the closest neighbor. Return K nearest.
```

HNSW's recall is typically 95-99% at high throughput. It's the default for many vector DBs (Milvus, Pinecone, Weaviate).

The cost: HNSW indexes are large (each vector needs ~M edges, default M=32). For 1M vectors, the index is ~150 MB plus the 768-dim float vectors (3 GB).

### PQ (Product Quantization)

PQ compresses vectors to reduce memory:

1. Split each 768-dim vector into 8 sub-vectors of 96 dims each.
2. For each sub-vector, train a codebook of 256 centroids via k-means on the database's sub-vectors.
3. Replace each sub-vector with the ID of its nearest centroid (1 byte instead of 384 bytes).

```text
Original: 768 × 4 bytes = 3 KB per vector
PQ-compressed: 8 bytes per vector (8 sub-vectors × 1 byte each)
Compression ratio: 384×
```

The trade-off: PQ's distance computation is approximate (using the codebook's precomputed distances). Recall drops to ~80-90% for high compression.

IVF + PQ (IVFPQ) is the standard for billion-scale vector search: IVF for partitioning, PQ for compression. Recall: ~80-90%; throughput: ~10K queries/sec on a single CPU.

## The GPU Implementation

FAISS has a GPU implementation that achieves 10-100× the throughput of CPU:

- GPU IVF: 100K queries/sec on a single GPU (vs 10K on a 32-core CPU).
- GPU Flat: 10K queries/sec for 1M-vector databases.

The GPU uses tensor cores for the batched distance computation, similar to matrix multiply.

## Production Use Cases

### RAG (Retrieval-Augmented Generation)

The most common FAISS use case: store embeddings of documents, retrieve relevant chunks for LLM context.

```python
import faiss
import numpy as np

# Build the index
dim = 768
index = faiss.IndexFlatIP(dim)
embeddings = np.random.rand(1_000_000, dim).astype('float32')  # 1M doc embeddings
index.add(embeddings)

# Query
query_embedding = np.random.rand(1, dim).astype('float32')
distances, ids = index.search(query_embedding, k=5)
# ids[0] = the 5 most similar document IDs
```

For RAG with 1M docs: ~2 ms per query on CPU. Add 50 ms for the LLM generation, total ~50 ms per RAG query.

### Image dedup

FAISS for finding near-duplicate images: embed each image with a CNN, find images with distance < threshold.

### Recommendation

FAISS for finding similar users or items: embed each user/item, find K-nearest for collaborative filtering.

## Production Tuning

For a 10M-vector database with 768-dim embeddings:

```python
# Choose index based on recall/latency trade-off
if recall_needed == "exact":
    index = faiss.IndexFlatIP(dim)  # ~50 ms per query, 30 GB memory
elif recall_needed == "high" (95%+):
    index = faiss.IndexHNSWFlat(dim, 32)  # ~2 ms per query, 35 GB memory
elif recall_needed == "medium" (90%):
    quantizer = faiss.IndexFlatL2(dim)
    index = faiss.IndexIVFPQ(quantizer, dim, 1000, 8, 8)  # ~1 ms per query, 1 GB memory
```

The recommended approach: start with HNSW for small databases (<1M), switch to IVFPQ for larger.

## Common Pitfalls

1. **Forgetting to normalize vectors for cosine similarity.** Inner product (IP) is cosine similarity only if vectors are L2-normalized. Otherwise, IP is biased by vector magnitudes.

2. **Setting `nprobe` too low for IVF.** Default `nprobe=1` gives ~50% recall. Raise to 8-32 for production.

3. **Forgetting to train the index.** IVF and PQ indexes need to be trained on a representative sample of the data. Don't add vectors without training.

4. **Forgetting that PQ's recall depends on the data distribution.** PQ works well for uniformly-distributed data; for heavily-clustered data, it's worse.

5. **Forgetting that HNSW's parameter `efConstruction` affects index build time.** Higher `efConstruction` = better recall but slower build. Default 100; use 200+ for high-recall applications.

6. **Forgetting that FAISS indexes are not designed for frequent updates.** Adding to a Flat is fast; adding to IVF requires re-balancing (slow). Use IndexIDMap2 to wrap IVF and add/delete efficiently.

## References

- Johnson, Douze, Jégou, "[Billion-scale similarity search with GPUs](https://arxiv.org/abs/1702.08734)" (arXiv 2017) — FAISS paper
- [FAISS GitHub repository](https://github.com/facebookresearch/faiss)
- [FAISS documentation and tutorials](https://faiss.ai/)
- Malkov & Yashunin, "[Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs](https://arxiv.org/abs/1603.09320)" (2018) — HNSW paper
- Jégou et al., "[Product Quantization for Nearest Neighbor Search](https://hal.inria.fr/inria-00514462/document)" (TPAMI 2011) — PQ paper
- [FAISS on GPU benchmarks](https://github.com/facebookresearch/faiss/wiki/Comparing-the-different-indexes)
