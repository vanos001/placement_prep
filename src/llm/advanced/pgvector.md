# PGVector

pgvector is an open-source PostgreSQL extension for storing and searching dense vectors, developed by Andrew Kane (ankane) since 2021. It's the simplest way to add vector search to an existing PostgreSQL database, making PostgreSQL a viable vector database for small-to-medium workloads (<10M vectors). This page covers the index types (IVFFlat, HNSW), the trade-offs vs. dedicated vector DBs (Milvus, Qdrant), and the production use cases.

## The Use Case

For applications that already use PostgreSQL, adding a dedicated vector DB (Milvus, Qdrant) adds operational complexity: another service to deploy, monitor, and back up. pgvector lets you store vectors in the same database as your other data, with SQL queries that join vector search with scalar queries.

```sql
-- Add the extension
CREATE EXTENSION vector;

-- Create a table with a vector column
CREATE TABLE documents (
    id BIGSERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(768),  -- 768-dimensional vector
    category TEXT,
    created_at TIMESTAMP
);

-- Insert vectors
INSERT INTO documents (content, embedding, category, created_at) VALUES
    ('The capital of France is Paris.', '[0.1, 0.2, ...]', 'geography', NOW());

-- Vector search with filter
SELECT id, content, embedding <=> '[0.5, 0.6, ...]' AS distance
FROM documents
WHERE category = 'geography' AND created_at > '2026-01-01'
ORDER BY embedding <=> '[0.5, 0.6, ...]'
LIMIT 10;
```

The `<=>` operator is cosine distance; `<->` is L2 distance; `<#>` is inner product.

## The Index Types

### IVFFlat

```sql
CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

IVFFlat partitions the vector space into 100 lists (Voronoi cells). At query time, the search probes the `n_probes` (default 1, configurable) nearest lists.

- Build time: ~10 minutes for 1M vectors.
- Memory: 1× the vector data.
- Query latency: ~5 ms for 1M vectors with `n_probes=10`.
- Recall: 90-95%.

### HNSW

```sql
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

HNSW builds a hierarchical graph. At query time, the search traverses the graph.

- Build time: ~30 minutes for 1M vectors.
- Memory: 2× the vector data (graph edges).
- Query latency: ~1-2 ms for 1M vectors.
- Recall: 99%.

HNSW is the recommended choice for most workloads since pgvector 0.5.0 (2023). IVFFlat is faster to build and uses less memory, but slower at query time.

## Performance Comparison to Milvus

For 1M 768-dim vectors, HNSW index:

| DB | Insert time | Query latency (top-10) | Memory | Recall |
|----|-------------:|------------------------:|--------:|-------:|
| pgvector (PostgreSQL 16) | ~30 min | 2 ms | 4 GB | 99% |
| Milvus 2.4 | ~30 min | 1 ms | 4 GB | 99% |
| Qdrant 1.5 | ~30 min | 1 ms | 4 GB | 99% |

At 1M scale, the differences are small. At 10M scale, pgvector's HNSW slows down (10 ms vs. Milvus's 2 ms) because PostgreSQL's planner doesn't fully optimize for vector queries.

## Hybrid Search

pgvector's strength: hybrid search via SQL JOIN:

```sql
-- Find similar documents, filtered by user's permissions
SELECT d.id, d.content
FROM documents d
JOIN user_permissions up ON up.category = d.category
WHERE up.user_id = 42
ORDER BY d.embedding <=> '[0.5, 0.6, ...]'
LIMIT 10;

-- Vector search + full-text search
SELECT d.id, d.content,
       (d.embedding <=> '[0.5, ...]') * 0.7 + 
       (ts_rank(d.tsv, query) * 0.3) AS combined_score
FROM documents d
WHERE d.tsv @@ query
ORDER BY combined_score
LIMIT 10;
```

This is impossible in dedicated vector DBs (which don't have full-text search built in). pgvector's RAG use cases benefit from this hybrid capability.

## Production Use Cases

### RAG for Small Datasets

For RAG with <100K documents, pgvector is ideal: simple to deploy, queries fast enough (~5 ms), and the hybrid search combines well with PostgreSQL's other features.

```python
import psycopg2
from openai import OpenAI

db = psycopg2.connect("...")
openai = OpenAI()

def rag_query(question, k=5):
    # Embed the question
    embedding = openai.embeddings.create(input=question, model="text-embedding-3-small").data[0].embedding
    
    # Vector search
    cur = db.cursor()
    cur.execute("""
        SELECT content FROM documents
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (str(embedding), k))
    contexts = [row[0] for row in cur.fetchall()]
    
    # Generate answer
    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Answer based on the context."},
            {"role": "user", "content": f"Context: {contexts}\n\nQuestion: {question}"},
        ],
    )
    return response.choices[0].message.content
```

### Recommendation

For user-item recommendation: store user and item embeddings in pgvector, query for "items similar to what this user liked".

### Semantic caching

For LLM response caching: embed the prompt, query pgvector for similar past prompts, return the cached response if the similarity is high.

## When to Migrate to a Dedicated Vector DB

pgvector's limits (typical for PostgreSQL on a single node):
- ~10M vectors per table (HNSW).
- ~100 QPS sustained.
- ~50 GB of vector data per table.

Beyond these, a dedicated vector DB (Milvus, Qdrant) is better:
- Milvus: for billion-scale, multi-node, GPU acceleration.
- Qdrant: for Rust-based performance, simpler deployment.
- Pinecone: for cloud-managed, no operational overhead.

## Common Pitfalls

1. **Forgetting to set `maintenance_work_mem` for index builds.** HNSW build needs ~5× the vector data size in memory. Set `maintenance_work_mem = 4GB` for large builds.

2. **Forgetting to vacuum after large deletes.** pgvector's indexes don't auto-rebalance on delete. Periodic `VACUUM` reclaims space.

3. **Forgetting that HNSW doesn't support updates well.** Updating a row's vector requires removing and re-inserting the index entry. For frequently-updated vectors, consider an insert-only table with a "latest version" pointer.

4. **Forgetting to enable parallel query.** PostgreSQL can parallelize the HNSW search across CPU cores. Set `max_parallel_workers_per_gather = 4` for parallel search.

5. **Forgetting to verify recall with EXPLAIN ANALYZE.** PostgreSQL's planner may not use the HNSW index if it estimates the table is small. Check `EXPLAIN ANALYZE` to confirm the index is used.

6. **Forgetting that pgvector is a PostgreSQL extension.** Backups, replication, and HA are handled by PostgreSQL, not separately. Use the existing backup/HA infrastructure.

## References

- [pgvector GitHub repository](https://github.com/pgvector/pgvector)
- [pgvector documentation](https://github.com/pgvector/pgvector#installation)
- Andrew Kane, "[pgvector: Open-source vector similarity search for Postgres](https://ankane.org/pgvector)" (blog post, 2021)
- [PostgreSQL: Working with pgvector](https://www.postgresql.org/about/news/pgvector-0-7-0-released/)
- [pgvector vs Milvus comparison](https://hunterheilmil.com/posts/pgvector-milvus)
- [Supabase: pgvector in production](https://supabase.com/docs/guides/ai/vector-columns)
- [TimescaleDB: pgvector + time-series for AI](https://www.timescale.com/blog)
- [LWN: pgvector for vector search (2023)](https://lwn.net/Articles/931856/)
