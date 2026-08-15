# Distributed RAG Systems

## Vector Database Scaling

Vector databases are the storage backbone of RAG systems, indexing embeddings for fast approximate nearest neighbor (ANN) search. At scale — billions of vectors, millions of queries per day — a single-node vector database is insufficient.

**Sharding strategies for vector databases:**

1. **Hash-based sharding**: Vectors are assigned to shards by hashing their ID. Simple but provides no locality — similar vectors may land on different shards, requiring cross-shard queries for top-K retrieval.
2. **Range-based sharding**: Vectors partitioned by a key (e.g., document ID, namespace). Preserves locality but can create hot spots.
3. **Graph-based sharding (HNSW partitioning)**: The HNSW index graph is split at natural cluster boundaries. Milvus and Weaviate use variants of this approach. Each shard owns a subgraph, and a routing layer determines which shards to query.

```
Client Query
    │
    ▼
┌───────────┐
│  Router   │──── Query Shard 1 (HNSW subgraph, vectors 0-500M)
│  (coordin-│──── Query Shard 2 (HNSW subgraph, vectors 500M-1B)
│   ator)   │──── Query Shard 3 (HNSW subgraph, vectors 1B-1.5B)
└───────────┘
    │
    ▼
Merge results, re-rank, return top-K
```

**Real systems and their scaling approaches:**

| System | Sharding | Replication | Max Scale | Annihilation Approach |
|--------|----------|-------------|-----------|---------------------|
| Milvus | Range + hash | Leader-follower | 10B+ vectors | IVF_FLAT, HNSW, DISKANN |
| Pinecone | Server-managed | Automatic | 10B+ | Proprietary ANN |
| Weaviate | Replication-based | Raft per shard | 100M+ per node | HNSW |
| Qdrant | Custom sharding | Raft consensus | 10B+ | HNSW |
| pgvector | Postgres partitioning | Streaming replication | ~100M (practical) | IVF_FLAT, HNSW |

**Write throughput** is often the bottleneck. Ingesting 1M documents with embeddings requires writing millions of high-dimensional vectors. Batching writes (e.g., 1,000–10,000 vectors per batch) and using async ingestion pipelines are essential. Milvus supports bulk insert from files in S3, which is 5–10x faster than individual inserts.

> **Interview Angle**: "How would you design a vector database that handles 100M documents with sub-50ms retrieval?" Key points: horizontal sharding with HNSW subgraphs, pre-warming replicas, caching frequent queries, using quantization (PQ/SQ) to reduce memory footprint.

## Distributed RAG Architecture

A production RAG system at scale is not a single retrieval call — it's a distributed pipeline with multiple stages, each potentially distributed across different services:

```
Query → [Query Router] → [Rewrite/Expansion] → [Retriever Pool]
                              │                      │
                              │              ┌───────┼───────┐
                              │              ▼       ▼       ▼
                              │           [VecDB]  [BM25]  [Knowledge Graph]
                              │              │       │       │
                              ▼              └───┬───┘───────┘
                        [Re-ranker] ◄────────┘
                              │
                              ▼
                        [Context Builder]
                              │
                              ▼
                        [LLM Generator]
                              │
                              ▼
                         Response
```

**Retriever distribution patterns:**

- **Fan-out retrieval**: Query multiple index backends (vector DB, keyword search, knowledge graph) in parallel, merge results. Reduces latency via parallelism but increases total compute.
- **Multi-stage retrieval**: First stage uses cheap ANN search (HNSW, IVF) to get top-100, second stage uses expensive cross-encoder re-ranking to get top-10. The first stage can be distributed; the second is typically single-node due to model size.
- **Recursive retrieval**: The initial retrieval results trigger additional retrievals (e.g., retrieve document metadata, linked documents). This creates a retrieval DAG that must be executed with appropriate timeouts and budgets.

## Multi-Tenant RAG

SaaS platforms serving RAG to many customers face multi-tenancy challenges:

1. **Data isolation**: Each tenant's documents must be logically (or physically) separated. Logical isolation uses metadata filtering (`WHERE tenant_id = X`) on a shared index. Physical isolation gives each tenant a separate index — stronger isolation but higher cost.
2. **Performance isolation**: A heavy query from tenant A should not degrade tenant B's latency. This requires per-tenant rate limiting, separate query queues, and potentially separate hardware for premium tenants.
3. **Index management**: Each tenant may have different embedding models, chunking strategies, and update frequencies. This makes shared infrastructure harder to optimize.

```
Multi-Tenant RAG Strategies:

  Shared Index + Metadata Filter:   ┌──────────────┐
  Low cost, moderate isolation      │ tenant_a: [v1,v2,v3]
                                    │ tenant_b: [v4,v5,v6]  ← filter on read
                                    │ tenant_c: [v7,v8,v9]  ← filter on read
                                    └──────────────┘

  Partitioned Index:                ┌────────┐ ┌────────┐ ┌────────┐
  Better isolation, medium cost     │tenant_a│ │tenant_b│ │tenant_c│
                                    │[v1,v2] │ │[v4,v5] │ │[v7,v8] │
                                    └────────┘ └────────┘ └────────┘

  Dedicated Instance:               ┌──────┐   ┌──────┐   ┌──────┐
  Strongest isolation, high cost    │ DB-A │   │ DB-B │   │ DB-C │
                                    │ (GPU)│   │ (GPU)│   │ (CPU)│
                                    └──────┘   └──────┘   └──────┘
```

**Pinecone Serverless** uses a namespace-based isolation model where each tenant's data lives in a namespace within a shared index, and queries are filtered at the storage layer. **Weaviate** supports multi-tenancy at the collection level with automatic tenant activation/deactivation to manage memory.

## RAG Consistency

RAG systems face a staleness problem: documents are updated in the source of truth, but the vector index may not reflect those changes for minutes or hours. This is a classic *eventual consistency* challenge.

**Consistency approaches:**

- **Synchronous indexing**: Every document update immediately triggers re-embedding and vector insertion. Provides strong consistency but adds latency to the write path and may overwhelm the embedding pipeline during bulk updates.
- **Async indexing with change data capture (CDC)**: A CDC pipeline (Debezium, Kafka Connect) captures document changes and feeds them to the embedding pipeline. Typical lag: seconds to minutes.
- **Read-through repair**: If a query retrieves a stale document, the system detects the version mismatch and triggers a refresh. Combines with a TTL-based cache for the document content.
- **Versioned embeddings**: Each embedding carries a version vector. During retrieval, the system can detect conflicts and choose to re-retrieve or use a cached result.

## RAG Caching and Semantic Caching

Caching is critical for RAG cost optimization — LLM generation is 10–100x more expensive than retrieval. Two complementary caching layers exist:

### Result Caching
Cache the final LLM response keyed by (query_hash, context_hash). Simple and effective for exact duplicate queries, but misses semantic duplicates ("What is X?" vs "Tell me about X").

### Semantic Caching
Cache responses keyed by the *semantic similarity* of the query. A new query is first embedded and compared against cached query embeddings. If the cosine similarity exceeds a threshold (e.g., 0.97), the cached response is returned without calling the LLM.

```
Semantic Cache Lookup:

  Incoming Query
       │
       ▼
  Generate Embedding (fast, ~1ms)
       │
       ▼
  ANN Search in Cache Index
       │
       ├── Hit (similarity > 0.97)
       │     └── Return cached response  [SAVE: ~$0.01 per query]
       │
       └── Miss
             └── Full RAG pipeline  [COST: ~$0.01–0.10 per query]
                   │
                   ▼
             Store (query_embedding, response) in cache
```

**Semantic cache implementation challenges:**
- **Threshold tuning**: Too high and you miss cache hits. Too low and you return incorrect answers.
- **Cache invalidation**: When source documents change, cached responses may become stale. This requires coupling the cache to the document update stream.
- **Cache index scaling**: The cache index itself is a vector database that needs scaling. GPTCache uses ChromaDB as its backend; production systems may use a dedicated cache layer.

## LLM Request Routing and Model Load Balancing

### LLM Request Routing
In systems serving multiple models or multiple versions of the same model, a routing layer directs requests to appropriate backends:

- **Model-based routing**: Route based on the requested model name. Simple but requires clients to know which model to use.
- **Capability-based routing**: A classifier determines the query type (code, creative writing, factual Q&A) and routes to the best-suited model. For example, code queries go to a code-specialized model.
- **Cost-based routing**: Route simple queries to cheaper/smaller models, complex queries to larger models. Uses a confidence scoring mechanism — if a small model's answer confidence is low, escalate to the larger model.
- **Latency-based routing**: Route to the backend with the shortest estimated queue time. Requires real-time queue depth monitoring.

### Model Load Balancing

LLM load balancing differs from traditional HTTP load balancing because request cost varies enormously — a single 4K-token generation request uses 100x more GPU time than a 32-token request. Simple round-robin or least-connections balancing creates imbalanced GPU utilization.

**Token-aware load balancing** tracks the estimated token budget of each queued request and assigns new requests to the backend with the smallest total pending token budget:

```python
# Token-aware load balancing pseudocode
class TokenAwareBalancer:
    def select_backend(self, request, backends):
        estimated_tokens = estimate_tokens(request)
        best = min(backends, key=lambda b: b.pending_tokens + estimated_tokens)
        best.pending_tokens += estimated_tokens
        return best
```

## Inference Queues and Token-Level Scheduling

### Inference Queues
LLM inference backends have limited batch capacity. An inference queue decouples request arrival from GPU execution. Key design decisions:

- **Priority queuing**: Premium users get priority over free-tier. Requires careful design to prevent starvation of low-priority requests.
- **Timeout-based admission**: Requests that wait too long are rejected (fast-fail) rather than queued indefinitely.
- **Queue depth-based autoscaling**: When the queue exceeds a threshold, signal the autoscaler to add more GPU replicas.

### Token-Level Scheduling
Advanced inference engines like vLLM and TGI implement **iteration-level scheduling** (also called continuous batching or dynamic batching). Rather than waiting for all requests in a batch to complete before starting new ones, the scheduler can add/remove requests at each token generation step.

This is fundamentally different from static batching:

```
Static Batching:              Continuous Batching:
  Time →                      Time →
  Req A: [████████]          Req A: [████████]
  Req B: [    ████████]      Req B: [    ████████]
  Req C: [        ████████]  Req C: [        ████████]
  GPU idle:    ▓▓▓           Req D: [            ████████]
  (waiting for B,C to finish)    (D starts immediately when batch slot opens)

  ▓ = wasted GPU time         No wasted GPU time between requests
```

**Token-level scheduling** enables significantly higher throughput because the GPU is never waiting for the longest request in a batch to finish before accepting new work. The trade-off is slightly higher scheduling overhead per iteration and more complex memory management for the KV cache.

## Comparison: RAG Caching Strategies

| Strategy | Hit Rate | Consistency | Complexity | Best For |
|----------|----------|-------------|------------|----------|
| Exact-match cache | Low (10-20%) | Strong | Low | FAQ bots, repeated queries |
| Semantic cache | Medium (30-50%) | Medium | Medium | Customer support, documentation |
| Prompt-result cache | High (50-70%) | Weak | Low | Template queries with variables |
| Embedding-response cache | Medium | Weak | High | General purpose, cost-sensitive |

## Key Takeaways

1. **Vector DB scaling is a distributed systems problem** — sharding, replication, and query routing are non-trivial at billion-vector scale.
2. **Semantic caching is the highest-ROI optimization** for RAG systems, potentially cutting LLM costs by 30-50%.
3. **Multi-tenant RAG requires choosing your isolation level** — shared index (cheap), partitioned (balanced), or dedicated (strong).
4. **Continuous batching is table stakes** for any serious inference deployment — static batching wastes 20-40% of GPU cycles.
5. **Token-aware load balancing** outperforms connection-based balancing because LLM requests have wildly different costs.