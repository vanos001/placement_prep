# RAG (Retrieval-Augmented Generation)

## Overview

RAG (Retrieval-Augmented Generation) enhances LLM responses by retrieving relevant documents from an external knowledge base before generating an answer. This solves two fundamental LLM limitations: **knowledge cutoff** (the model only knows what it was trained on) and **hallucination** (the model generates plausible but incorrect facts).

RAG is one of the most important production patterns for LLMs and a favorite interview topic.

## Why RAG?

```mermaid
graph TD
    PROBLEM[LLM Limitations]
    PROBLEM --> HC[Hallucination]
    PROBLEM --> KC[Knowledge Cutoff]
    PROBLEM --> PRIV[Private Data]

    HC --> RAG_S[RAG Solution]
    KC --> RAG_S
    PRIV --> RAG_S

    RAG_S --> GROUNDED[Grounded in retrieved facts]
    RAG_S --> CURRENT[Up-to-date information]
    RAG_S --> PRIVATE[Access to private docs]
```

| Approach | Pros | Cons |
|---|---|---|
| **Fine-tuning** | Model knows the domain | Expensive, needs retraining, can hallucinate |
| **RAG** | Always current, source-cited, cheaper | Retrieval quality limits answer quality |
| **Long context** | Simple, no retrieval needed | Expensive, "lost in the middle" problem |

## RAG Architecture

```mermaid
graph LR
    subgraph "Indexing (Offline)"
        DOC[Documents] --> CHUNK[Chunking]
        CHUNK --> EMBED[Embedding]
        EMBED --> VDB[(Vector DB)]
    end

    subgraph "Retrieval (Online)"
        Q[User Query] --> QEMBED[Query Embedding]
        QEMBED --> SEARCH[Vector Search]
        VDB --> SEARCH
        SEARCH --> RERANK[Reranking]
        RERANK --> TOP_K[Top-K Chunks]
    end

    subgraph "Generation"
        TOP_K --> PROMPT[Augmented Prompt]
        Q --> PROMPT
        PROMPT --> LLM[LLM]
        LLM --> ANSWER[Answer with Sources]
    end
```

## Document Chunking

### Why Chunk?

LLMs have limited context windows. Documents must be split into manageable pieces that:
- Fit within the context window
- Maintain semantic coherence
- Are small enough for precise retrieval

### Chunking Strategies

```mermaid
graph TD
    CS[Chunking Strategies]
    CS --> FIXED[Fixed-Size]
    CS --> SEMANTIC[Semantic]
    CS --> RECURSIVE[Recursive]
    CS --> STRUCTURE[Structure-Based]

    FIXED --> F1["Split every N tokens"]
    SEMANTIC --> S1["Split at topic boundaries"]
    RECURSIVE --> R1["Split by paragraphs → sentences → tokens"]
    STRUCTURE --> ST1["Split by headers, sections"]
```

| Strategy | How It Works | Best For |
|---|---|---|
| **Fixed-size** | Split every N tokens with overlap | Simple, fast |
| **Recursive** | Try paragraph → sentence → token splits | General purpose |
| **Semantic** | Embed and split when similarity drops | Topic-diverse docs |
| **Structure-based** | Split by headers, markdown sections | Structured documents |
| **Parent-child** | Small chunks for retrieval, return parent for context | Precision + context |

### Chunk Size Trade-offs

| Size | Precision | Context | Use Case |
|---|---|---|---|
| 100-256 tokens | High | Low | Factoid QA |
| 256-512 tokens | Good | Good | General QA |
| 512-1024 tokens | Moderate | High | Summarization |
| 1024+ tokens | Low | Very high | Long-form analysis |

**Overlap**: 10-20% overlap between chunks prevents information loss at boundaries.

## Embedding Models

Embedding models convert text into dense vectors for similarity search:

| Model | Dimensions | Max Tokens | Quality |
|---|---|---|---|
| **OpenAI text-embedding-3-small** | 1536 | 8191 | Good |
| **OpenAI text-embedding-3-large** | 3072 | 8191 | Excellent |
| **Cohere embed-v3** | 1024 | 512 | Excellent |
| **BGE-M3** | 1024 | 8192 | Excellent (multilingual) |
| **E5-mistral-7b** | 4096 | 32768 | State-of-art |
| **Nomic Embed** | 768 | 8192 | Good, open-source |

## Vector Databases

| Database | Type | Key Feature |
|---|---|---|
| **Pinecone** | Managed | Easy to use, serverless |
| **Weaviate** | Self-hosted/Managed | Hybrid search, modules |
| **Qdrant** | Self-hosted/Managed | High performance, Rust |
| **Chroma** | Embedded | Simple, lightweight |
| **Milvus** | Self-hosted | Scalable, GPU support |
| **pgvector** | PostgreSQL extension | Existing PostgreSQL infra |
| **FAISS** | Library | Meta, CPU/GPU, not a DB |

### Similarity Metrics

```python
# Cosine similarity (most common)
sim(A, B) = (A · B) / (||A|| × ||B||)

# Euclidean distance
dist(A, B) = ||A - B||₂

# Dot product
sim(A, B) = A · B
```

Cosine similarity is preferred for normalized embeddings. Dot product is faster for pre-normalized vectors.

## Retrieval Strategies

### Dense Retrieval

Standard vector similarity search:

```python
query_embedding = embed_model.encode("What is RAG?")
results = vector_db.search(query_embedding, top_k=10)
```

### Sparse Retrieval (BM25)

Traditional keyword-based retrieval:

```python
from rank_bm25 import BM25Okapi
bm25 = BM25Okapi(corpus_tokens)
scores = bm25.get_scores(query_tokens)
```

### Hybrid Retrieval

Combine dense and sparse for best results:

```mermaid
graph LR
    Q[Query] --> DENSE[Dense Retrieval]
    Q --> SPARSE[Sparse Retrieval - BM25]
    DENSE --> FUSION[Reciprocal Rank Fusion]
    SPARSE --> FUSION
    FUSION --> RESULTS[Combined Results]
```

**Reciprocal Rank Fusion (RRF):**
```
RRF(d) = Σ 1/(k + rank_i(d))
```
where k=60 (typical constant) and rank_i is the rank in retrieval system i.

### Reranking

After initial retrieval, rerank results with a cross-encoder:

```mermaid
graph LR
    RETRIEVE["Retrieve top-50"] --> RERANK["Cross-encoder rerank"]
    RERANK --> TOP["Select top-5"]
```

| Reranker | Type | Quality |
|---|---|---|
| **Cohere Rerank** | API | Excellent |
| **BGE-Reranker** | Open-source | Very good |
| **Cross-encoder (ms-marco)** | Open-source | Good |
| **ColBERT** | Late interaction | Good, fast |

Cross-encoders are more accurate than bi-encoders because they see query and document together, but they're slower (can't pre-compute embeddings).

## Advanced RAG Patterns

### Query Transformation

```mermaid
graph TD
    Q[Original Query] --> REWRITE[Query Rewriting]
    Q --> HYDE[HyDE - Hypothetical Document]
    Q --> SUB[Sub-Question Decomposition]

    REWRITE --> R1["'How does Python GIL work?' → 'Python Global Interpreter Lock threading concurrency'"]
    HYDE --> H1["Generate hypothetical answer, then search for it"]
    SUB --> S1["Break into: 'What is GIL?', 'How does it affect threading?', 'Alternatives?'"]
```

### HyDE (Hypothetical Document Embeddings)

1. Ask the LLM to generate a hypothetical answer
2. Embed the hypothetical answer (not the query)
3. Search for documents similar to the hypothetical answer

**Why it works:** The hypothetical answer is in "document space" rather than "query space," leading to better retrieval.

### Agentic RAG

The LLM decides when and how to retrieve:

```mermaid
graph TD
    Q[User Query] --> AGENT[LLM Agent]
    AGENT --> DECIDE{Need retrieval?}
    DECIDE -->|Yes| RETRIEVE[Retrieve documents]
    DECIDE -->|No| DIRECT[Answer directly]
    RETRIEVE --> EVAL{Documents relevant?}
    EVAL -->|Yes| ANSWER[Generate answer]
    EVAL -->|No| REFORM[Reformulate query]
    REFORM --> RETRIEVE
```

## RAG Evaluation

| Metric | What It Measures |
|---|---|
| **Context Precision** | Are retrieved chunks relevant? |
| **Context Recall** | Did we retrieve all necessary information? |
| **Faithfulness** | Is the answer grounded in retrieved context? |
| **Answer Relevance** | Does the answer address the question? |

**Frameworks:** RAGAS, TruLens, DeepEval

## GraphRAG

GraphRAG (Microsoft, 2024) augments vector retrieval with knowledge graph traversal:

```mermaid
graph TD
    DOC[Documents] --> NER[Entity Extraction]
    NER --> KG[Knowledge Graph]
    KG --> COMM[Community Detection]
    COMM --> SUMMARY[Community Summaries]
    
    Q[User Query] --> LOCAL[Local Search: Entity → Graph → Context]
    Q --> GLOBAL[Global Search: Community Summaries → Answer]
    LOCAL --> LLM[LLM]
    GLOBAL --> LLM
```

**Why GraphRAG?**
- Vector RAG retrieves chunks by similarity, missing multi-hop relationships
- "Which suppliers are connected to Company X?" requires graph traversal
- GraphRAG builds a knowledge graph from documents, extracts entities and relationships
- Supports both local (entity-focused) and global (theme-focused) queries

**When to use GraphRAG:**
- Documents have rich entity relationships (legal, financial, medical)
- Multi-hop questions are common
- You need explainable retrieval paths
- Pure vector search misses cross-document connections

## CRAG (Corrective RAG)

CRAG (Yan et al., 2024) adds a self-correction step to the RAG pipeline:

```mermaid
graph TD
    Q[Query] --> RETRIEVE[Retrieve Documents]
    RETRIEVE --> EVAL{Evaluator}
    EVAL -->|Correct| USE[Use documents directly]
    EVAL -->|Incorrect| WEB[Web search fallback]
    EVAL -->|Ambiguous| REFINED[Refine + decompose query]
    REFINED --> RETRIEVE
    USE --> GENERATE[Generate answer]
    WEB --> GENERATE
```

**Key innovation:** A lightweight evaluator scores retrieved documents. If documents are irrelevant, the system falls back to web search or reformulates the query. This prevents the LLM from generating answers based on poor retrieval.

## Context Window Management

With many retrieved chunks, managing the context window becomes critical:

### The "Lost in the Middle" Problem

Liu et al. (2023) showed that LLMs pay less attention to information in the middle of long contexts:

```mermaid
graph LR
    subgraph "Attention Distribution"
        HIGH1[High attention - start]
        LOW[Low attention - middle]
        HIGH2[High attention - end]
    end
```

**Mitigations:**
- Place the most important chunks at the beginning and end
- Limit the number of retrieved chunks (5-10 is typical)
- Use reranking to ensure the best chunks are in top positions
- Summarize chunks before inserting into context

### Context Window Budget

| Context Window | Usable for Retrieved Context | RAG Chunks (512 tokens each) |
|---|---|---|
| 4K | ~2K tokens | ~4 chunks |
| 8K | ~5K tokens | ~10 chunks |
| 32K | ~24K tokens | ~48 chunks |
| 128K | ~100K tokens | ~195 chunks |
| 1M+ | ~800K tokens | ~1500 chunks |

**More chunks ≠ better answers.** Beyond 10-15 chunks, retrieval noise degrades quality. Use reranking and filtering to keep only high-quality context.

## Production RAG Patterns

### Naive vs Production RAG

| Aspect | Naive RAG | Production RAG |
|---|---|---|
| Chunking | Fixed-size, no overlap | Semantic/recursive, with overlap |
| Retrieval | Dense only | Hybrid (dense + BM25) |
| Reranking | None | Cross-encoder reranker |
| Query handling | Direct query | Query rewriting, HyDE, decomposition |
| Evaluation | Manual spot-checks | RAGAS metrics, automated testing |
| Observability | None | Logging, tracing, feedback loops |
| Caching | None | Embedding cache, response cache |

### RAG Evaluation Framework

```mermaid
graph TD
    EVAL[RAG Evaluation]
    EVAL --> RET[Retrieval Quality]
    EVAL --> GEN[Generation Quality]
    EVAL --> END[End-to-End]

    RET --> PREC[Context Precision]
    RET --> REC[Context Recall]
    RET --> MRR[MRR@K]

    GEN --> FAITH[Faithfulness]
    GEN --> REL[Answer Relevance]
    GEN --> CORR[Correctness]

    END --> SAT[User Satisfaction]
    END --> TASK[Task Completion]
```

**RAGAS Metrics:**
- **Context Precision**: Of retrieved chunks, how many are relevant?
- **Context Recall**: Of all relevant information, how much was retrieved?
- **Faithfulness**: Is every claim in the answer supported by retrieved context?
- **Answer Relevance**: Does the answer address the actual question?

**Evaluation code example:**
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

result = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision],
)
print(result)
```

## Interview Questions

### Q1: Explain the RAG pipeline and its components.
**Answer:** RAG has three phases:
1. **Indexing**: Documents are chunked, embedded into vectors, and stored in a vector database
2. **Retrieval**: The user query is embedded, similar chunks are found via vector search, optionally reranked
3. **Generation**: Retrieved chunks are inserted into the prompt alongside the query, and the LLM generates an answer grounded in the retrieved context

Key components: chunking strategy, embedding model, vector database, retrieval method (dense/sparse/hybrid), reranker, and the LLM.

### Q2: What is the difference between dense and sparse retrieval?
**Answer:**
- **Sparse retrieval (BM25)**: Matches keywords. Fast, interpretable, but misses semantic similarity ("car" won't match "automobile")
- **Dense retrieval**: Uses embedding vectors. Captures semantic similarity but may miss exact keyword matches
- **Hybrid**: Combines both using RRF or other fusion methods. Best of both worlds in practice

### Q3: How do you handle chunking for documents with tables and images?
**Answer:**
- **Tables**: Extract as markdown/HTML, keep as separate chunks with surrounding context. Some embedding models handle structured data better
- **Images**: Use multimodal embedding models (CLIP) or describe images with a vision model, then embed the description
- **Mixed content**: Structure-aware chunking that respects document boundaries (headers, sections)
- **Parent-child chunks**: Small chunks for precise retrieval, but return the parent section for full context

### Q4: What is HyDE and when is it useful?
**Answer:** HyDE (Hypothetical Document Embeddings) generates a hypothetical answer to the query, then uses that answer (not the query) for retrieval. It works because queries and documents are in different semantic spaces — a question and its answer are different. The hypothetical answer is closer to actual documents in embedding space. Useful when queries are short or ambiguous, but adds latency (extra LLM call).

### Q5: How do you evaluate RAG quality?
**Answer:** Key metrics:
- **Context Precision/Recall**: Retrieval quality (are we finding the right chunks?)
- **Faithfulness**: Is the answer grounded in retrieved context (not hallucinated)?
- **Answer Relevance**: Does the answer address the question?
- **End-to-end**: Human evaluation, task completion rate

Tools: RAGAS framework, TruLens, manual evaluation on a golden test set.

## Common Mistakes

- ❌ Chunks too large (dilutes relevant information) or too small (loses context)
- ❌ No overlap between chunks (information at boundaries is lost)
- ❌ Using only dense retrieval (missing exact keyword matches)
- ❌ No reranking (initial retrieval may not be optimal)
- ❌ Not evaluating retrieval separately from generation
- ❌ Ignoring the "lost in the middle" problem with many retrieved chunks

## Summary

RAG grounds LLM outputs in retrieved external knowledge, reducing hallucination and enabling access to current/private data. The pipeline involves chunking, embedding, retrieval (dense/sparse/hybrid), reranking, and generation. Advanced patterns like HyDE, query transformation, and agentic RAG improve quality. GraphRAG adds knowledge graph traversal for multi-hop reasoning. CRAG adds self-correction for retrieval quality. Production RAG requires hybrid search, reranking, evaluation (RAGAS), and observability. The "lost in the middle" problem means chunk ordering matters — place important chunks at start and end. More chunks isn't always better; 5-10 high-quality chunks outperform 50 noisy ones.

## References

1. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks", NeurIPS 2020
2. Gao et al., "Retrieval-Augmented Generation for Large Language Models: A Survey", 2024
3. Edge et al., "From Local to Global: A Graph RAG Approach to Query-Focused Summarization" (Microsoft), 2024
4. Yan et al., "Corrective Retrieval Augmented Generation" (CRAG), 2024
5. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts", 2023
6. Es et al., "RAGAS: Automated Evaluation of Retrieval Augmented Generation", 2023
7. Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond", 2009
8. Luan et al., "Sparse, Dense, and Attentional Representations for Text Retrieval", 2021

## Cross-References

- [Embeddings →](embeddings.md) How text is vectorized
- [Prompt Engineering →](prompt-engineering.md) Constructing the augmented prompt
- [Agent Planning →](../../ml/agents/planning.md) Agentic RAG patterns
- [Evaluation →](evaluation.md) Measuring LLM quality
