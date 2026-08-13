# Design a Search Engine

> **Difficulty:** ⭐⭐⭐⭐ | **Asked at:** Google, Amazon, Elasticsearch | **Time:** 45 minutes

## 🎯 Problem Statement

Design a search engine that:
- Crawls and indexes web pages or product catalog
- Returns relevant results for text queries in < 500ms
- Supports ranking, autocomplete, and spell correction
- Handles billions of documents

---

## Step 1: Requirements

### Functional Requirements
1. Full-text search across documents
2. Ranked results by relevance
3. Autocomplete / search suggestions
4. Spell correction ("Did you mean...?")
5. Filtering and faceted search
6. Support for Boolean queries (AND, OR, NOT)

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Search latency | < 500ms (p99) |
| Index freshness | < 1 minute for updates |
| Availability | 99.99% |
| Documents | Billions |
| Queries/sec | 100K+ |

---

## Step 2: High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        SEARCH ENGINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐     ┌──────────────┐     ┌───────────────────┐   │
│  │  Client  │────→│ Load Balancer│────→│   Query Service   │   │
│  └──────────┘     └──────────────┘     └────────┬──────────┘   │
│                                                  │              │
│                    ┌─────────────────────────────┼──────┐       │
│                    │                             │      │       │
│             ┌──────▼──────┐             ┌────────▼──────┐      │
│             │  Autocomplete│             │  Search Index │      │
│             │  Service    │             │  (Sharded)    │      │
│             └─────────────┘             └───────────────┘      │
│                                                                 │
│  ┌──────────┐     ┌──────────────┐     ┌───────────────────┐   │
│  │  Crawler │────→│  Indexer     │────→│  Index Storage    │   │
│  │          │     │  (Parse +    │     │  (Inverted Index) │   │
│  └──────────┘     │   Tokenize)  │     └───────────────────┘   │
│                   └──────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 3: Deep Dive

### Crawling (for web search)

```
Crawler Pipeline:
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Seed    │────→│  URL     │────→│  Fetcher │────→│  Parser  │
│  URLs    │     │  Queue   │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      ▲                                  │
                      │           ┌──────────┐           │
                      └───────────│  URL     │◄──────────┘
                                  │  Extractor│
                                  └──────────┘

Politeness:
├── Respect robots.txt
├── Rate limit per domain (1 req/sec)
├── User-agent identification
└── Crawl delay headers

Priority:
├── PageRank-based priority
├── Freshness (recrawl frequently changing pages)
└── Domain authority
```

### Inverted Index (Core Data Structure)

```
Forward Index (what we DON'T use):
  Doc1 → ["the", "cat", "sat", "on", "mat"]
  Doc2 → ["the", "dog", "sat", "on", "rug"]

Inverted Index (what we USE):
  "the" → [Doc1, Doc2]
  "cat" → [Doc1]
  "sat" → [Doc1, Doc2]
  "on"  → [Doc1, Doc2]
  "mat" → [Doc1]
  "dog" → [Doc2]
  "rug" → [Doc2]

With positions (for phrase queries):
  "sat" → [(Doc1, [2]), (Doc2, [2])]
  "on"  → [(Doc1, [3]), (Doc2, [3])]
```

```python
# Inverted Index Implementation
class InvertedIndex:
    def __init__(self):
        self.index = {}  # term → [(doc_id, [positions])]

    def add_document(self, doc_id, text):
        tokens = self.tokenize(text)
        for position, term in enumerate(tokens):
            if term not in self.index:
                self.index[term] = []
            # Add doc_id with position
            if not self.index[term] or self.index[term][-1][0] != doc_id:
                self.index[term].append((doc_id, [position]))
            else:
                self.index[term][-1][1].append(position)

    def search(self, query):
        terms = self.tokenize(query)
        if not terms:
            return []

        # Get posting lists for each term
        posting_lists = [self.index.get(term, []) for term in terms]

        # Intersect posting lists (AND query)
        result = set(posting_lists[0][i][0] for i in range(len(posting_lists[0])))
        for pl in posting_lists[1:]:
            result &= set(pl[i][0] for i in range(len(pl)))

        return list(result)

    def tokenize(self, text):
        return text.lower().split()
```

### TF-IDF Ranking

```
TF-IDF = Term Frequency × Inverse Document Frequency

Term Frequency (TF):
  TF(t, d) = (count of t in d) / (total terms in d)
  "cat" appears 3 times in 100-word doc → TF = 0.03

Inverse Document Frequency (IDF):
  IDF(t) = log(N / df(t))
  N = total documents, df(t) = documents containing t
  "the" in 1M docs out of 10M → IDF = log(10) = 1.0 (common, low weight)
  "quantum" in 100 docs out of 10M → IDF = log(100000) = 5.0 (rare, high weight)

Score(query, document) = Σ TF(t, d) × IDF(t) for each query term t
```

### BM25 (Improved Ranking)

```
BM25(D, Q) = Σ IDF(qi) × [f(qi, D) × (k1 + 1)] / [f(qi, D) + k1 × (1 - b + b × |D|/avgdl)]

Where:
  f(qi, D) = term frequency of qi in document D
  |D| = document length
  avgdl = average document length
  k1 = 1.2 (term saturation parameter)
  b = 0.75 (length normalization parameter)

Why BM25 > TF-IDF:
  - Handles document length normalization
  - Term saturation (diminishing returns for repeated terms)
  - Industry standard (used by Elasticsearch, Solr)
```

### Query Processing

```
Query: "best programming language for beginners"

Step 1: Tokenize → ["best", "programming", "language", "beginners"]

Step 2: Lookup posting lists
  "best"        → [Doc5, Doc12, Doc45, ...]
  "programming" → [Doc3, Doc5, Doc8, ...]
  "language"    → [Doc5, Doc45, Doc100, ...]
  "beginners"   → [Doc5, Doc50, ...]

Step 3: Intersect (AND) → [Doc5, ...]

Step 4: Score each document using BM25

Step 5: Sort by score, return top K

Optimization: Skip Lists
  Posting lists use skip pointers for faster intersection
  [Doc1, Doc5, Doc10, Doc15, Doc20, ...]
       ↑           ↑           ↑
    skip to    skip to     skip to
```

### Autocomplete

```
Approach 1: Trie-based
┌─────────────────────────────────────┐
│              Trie                   │
│              root                   │
│            / | \                    │
│           p  q  r                   │
│          /   |   \                  │
│         y    u    e                 │
│        /     |     \                │
│       t      e     a               │
│      /       |      \              │
│     h        r      d              │
│    /         |       \             │
│   o          y       i             │
│  /                         \       │
│ n                          n       │
│                              g     │

"py" → python
"qu" → query, queue, quest
"re" → reading, real, react

Each node stores top-K popular completions
```

```
Approach 2: Prefix-based with Cache
├── Pre-compute popular prefix → results mapping
├── Store in Redis with TTL
├── Prefix "how" → ["how to code", "how to cook", ...]
└── Update periodically based on search logs
```

### Sharding Strategy

```
Document-Based Sharding:
├── Each shard contains a subset of documents
├── Query goes to ALL shards (scatter-gather)
├── Merge results from all shards
└── Problem: Every query hits all shards

Term-Based Sharding:
├── Each shard contains a subset of terms
├── Query goes to only relevant shards
├── Problem: Uneven shard sizes (common words)
└── Problem: Multi-term queries span many shards

Recommended: Document-Based with Routing
├── Shard by document_id hash
├── Replicate each shard 3x for availability
├── Use consistent hashing for shard placement
└── Query coordinator merges results from all shards
```

### Spell Correction

```
Approach: Edit Distance + Frequency

1. Compute edit distance between query and dictionary words
2. Return corrections sorted by:
   a. Edit distance (closer = better)
   b. Word frequency (more common = better)

Edit Distance Operations:
├── Insert: "helo" → "hello"
├── Delete: "helllo" → "hello"
├── Replace: "helli" → "hello"
└── Transpose: "hlelo" → "hello"

Implementation:
  - Pre-compute edit distance-1 and distance-2 for common words
  - Store in hash map: {"helo": ["hello"], "pythn": ["python"]}
  - Check map on query, suggest if match found
```

---

## Step 4: Trade-offs

### Index Freshness vs Query Performance
| Approach | Freshness | Performance |
|----------|-----------|-------------|
| Real-time indexing | Immediate | Slower queries (more segments) |
| Batch indexing (hourly) | Delayed | Faster queries (optimized index) |
| Hybrid | Good | Good |

### Memory vs Disk for Index
| Storage | Latency | Cost | Capacity |
|---------|---------|------|----------|
| In-memory | < 1ms | High | Limited |
| SSD | < 10ms | Medium | Large |
| HDD | < 100ms | Low | Very large |

**Recommendation:** Hot index in memory, cold index on SSD.

## 🔗 Cross-References

- [Key-Value Store](./kv-store.md) — Storage engine for index data
- [Architecture Concepts](../../cheatsheets/architecture.md) — Sharding, replication
- [DBMS Questions](../dbms-questions.md) — Indexing strategies
- [Coding Patterns](../coding/patterns.md) — Trie implementation
