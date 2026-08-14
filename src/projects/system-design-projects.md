# System Design Project Implementation Guides

Build fundamental infrastructure components from the ground up. These projects bridge the gap between theoretical system design interviews and practical engineering skills. Each project focuses on one core system and explores the design decisions, algorithms, and trade-offs involved.

Complements the ideas in [project-ideas.md](project-ideas.md) by providing deeper implementation guidance and interview-oriented discussion.

---

## 1. Design and Build a CDN (Content Delivery Network)

### What to Build
A simplified CDN with edge nodes that cache and serve static content, a routing layer that directs requests to the nearest edge, cache invalidation, and origin fetch on cache miss.

### Why It Matters
CDNs are the backbone of fast web delivery. Understanding how caching works at the edge — cache control, stale-while-revalidate, cache hierarchies — is essential for any backend engineer.

### Suggested Tech Stack
- **Language**: Go or Rust (low latency requirement)
- **Storage**: On-disk file cache with LRU eviction
- **Routing**: GeoIP-based or latency-based routing
- **Origin**: Simple HTTP file server
- **Protocol**: HTTP with standard cache headers (Cache-Control, ETag, Last-Modified)

### Architecture

```
Client ──► DNS (geo-routing) ──► Edge Node A (closest)
                                    │
                              ┌─────┴──────┐
                              │ Cache Hit? │
                              ├─ Yes → Serve from cache
                              └─ No  → Fetch from Origin
                                         → Store in cache
                                         → Serve to client
```

### Key Implementation Details

**Cache Key Design**:
```
key = SHA256(method + host + path + query_string)
```

**Cache Eviction**: LRU with max size limit. Track total cached size; evict least recently accessed when exceeding limit.

**Stale-While-Revalidate**:
```
Request arrives → Serve stale content immediately (if within SWR window)
                → Background revalidation from origin
                → Update cache with fresh content
```

**Cache Invalidation**:
- Time-based: TTL from Cache-Control headers
- Explicit: PURGE request from origin (API endpoint)
- Versioned URLs: `/assets/v2/app.js` (most reliable)

### Interview Discussion Points
- "Why cache at the edge instead of only at the application server?" → latency, bandwidth, origin protection
- "How do you handle dynamic content?" → don't cache, or use short TTL with stale-while-revalidate
- "What's the difference between CDN caching and browser caching?" → CDN serves all users, browser serves one user
- "How do you handle cache warming for popular content?" → pre-fetch on publish, or lazy populate on first request

### Difficulty: Hard | Estimated Time: 3–4 weeks

---

## 2. Design and Build a Load Balancer

### What to Build
A Layer 4 and Layer 7 load balancer that distributes traffic across multiple backend servers using configurable algorithms, performs health checks, handles connection draining, and supports TLS termination.

### Why It Matters
Load balancers are the entry point to every distributed service. Building one teaches you about connection management, TCP/HTTP protocols, and the trade-offs between different scheduling algorithms.

### Suggested Tech Stack
- **Language**: Go (`net` package for TCP, `net/http` for Layer 7)
- **Algorithms**: Round Robin, Weighted Round Robin, Least Connections, Consistent Hash
- **Health Checking**: Active (periodic probes) and passive (observe response codes)
- **TLS**: Go's `crypto/tls` for termination

### Architecture

```
                    ┌──────────────────┐
                    │   Load Balancer   │
                    │                  │
  Client ──►  L4/TCP│  ┌────────────┐  │
                    │  │ Algorithm   │  │
                    │  │ (Round Rob │  │
                    │  │  / Least   │  │
                    │  │  Conn)     │  │
                    │  └─────┬──────┘  │
                    │        │         │
                    │   ┌────┼────┐     │
                    │   ▼    ▼    ▼     │
                    │  B1   B2   B3     │
                    └──────────────────┘
```

### Implementation Roadmap
1. **Week 1**: TCP reverse proxy with round-robin (accept connection → connect to backend → bidirectional copy)
2. **Week 2**: Add multiple algorithms, connection pooling, configurable via YAML
3. **Week 3**: Active health checking (HTTP GET to `/health`), remove/add backends dynamically
4. **Week 4**: TLS termination, connection draining, metrics (requests, latency, errors)

### Key Challenges
- **Bidirectional proxy**: use `io.Copy` in two goroutines for each connection
- **Connection draining**: mark backend as "draining", allow existing connections to complete, reject new ones
- **Sticky sessions**: consistent hash on client IP, or cookie-based affinity

### Interview Discussion Points
- "L4 vs L7 load balancing — when to use which?" → L4 for raw throughput, L7 for HTTP-aware routing
- "How does least connections work?" → maintain active connection count per backend, pick the lowest
- "What is connection draining and why is it important?" → graceful removal without dropping active requests
- "How would you make this highly available?" → active-active pair with VRRP, or anycast routing

### Difficulty: Hard | Estimated Time: 3 weeks

---

## 3. Design and Build a Message Queue

### What to Build
A persistent message queue with topics, consumer groups, at-least-once delivery, message ordering within partitions, offset tracking, and a dead-letter queue. This is essentially building a simplified Kafka.

### Why It Matters
Message queues are the connective tissue of distributed systems. Building one forces you to solve durable storage, consumer coordination, and delivery guarantees — problems that exist in every event-driven system.

### Suggested Tech Stack
- **Language**: Go or Java
- **Storage**: Append-only log files (inspired by Kafka) with memory-mapped I/O
- **Protocol**: Custom TCP binary protocol or HTTP
- **Consumer Coordination**: Simple leader election or static assignment

### Architecture

```
Producer ──► Broker ──► Topic (log file)
                          │
                     ┌────┴────┐
                     ▼         ▼
               Partition 0  Partition 1
                     │         │
               ┌─────┼─────┐   │
               ▼     ▼     ▼   ▼
             C1     C2    C3  C4
           (Group A)    (Group B)
```

### Key Data Structures

**Append-Only Log**:
```
Offset 0: [Message 1 headers] [Message 1 body]
Offset 1: [Message 2 headers] [Message 2 body]
Offset 2: [Message 3 headers] [Message 3 body]
...
```

**Consumer Offset Tracking**:
```
Group A:
  Partition 0 → committed offset: 5
  Partition 1 → committed offset: 3
```

### Implementation Roadmap
1. **Week 1**: File-based append-only log with read by offset, write API
2. **Week 2**: Topics with partitions, producer API (partition assignment via key hashing)
3. **Week 3**: Consumer groups, offset tracking, consumer rebalancing
4. **Week 4**: Dead-letter queue, retention (time or size-based), consumer lag monitoring

### Interview Discussion Points
- "Why append-only logs instead of random-access databases?" → sequential I/O is 100x faster than random I/O on disk
- "At-least-once vs. exactly-once — what's the difference?" → exactly-once requires idempotent consumers or transactional writes
- "How do you handle consumer rebalancing?" → assign partitions to consumers, redistribute when consumers join/leave
- "What is consumer lag and why does it matter?" → lag = difference between latest offset and committed offset; high lag means consumer is falling behind

### Difficulty: Very Hard | Estimated Time: 4–6 weeks

---

## 4. Design and Build a Simple Database Engine

### What to Build
A minimal relational database engine that supports:
- Table creation with typed columns (INT, STRING)
- Row insertion and retrieval
- B-tree index for primary key lookups
- SQL parser for basic SELECT, INSERT, WHERE clauses
- ACID transactions with write-ahead logging (WAL)

### Why It Matters
Understanding how databases work under the hood makes you dramatically better at using them. You'll understand why indexes help, why N+1 queries are slow, and what transactions actually do.

### Suggested Tech Stack
- **Language**: C, Rust, or Go (C is traditional for DBs, Rust for safety, Go for productivity)
- **Storage**: Custom page-based storage (4KB pages, inspired by SQLite)
- **Index**: B-tree implementation for primary key
- **Parsing**: Hand-written recursive descent parser for SQL
- **Concurrency**: Reader-writer locks for table-level locking

### Architecture

```
SQL Query ──► Parser ──► AST ──► Query Planner ──► Executor
                                                    │
                                              ┌─────┴─────┐
                                              ▼           ▼
                                          B-Tree      Heap
                                         (Index)    (Row Data)
                                              │           │
                                              └─────┬─────┘
                                                    ▼
                                              Disk Pages
                                              + WAL
```

### Implementation Roadmap
1. **Week 1**: Page-based storage engine (read/write 4KB pages to file), row serialization
2. **Week 2**: B-tree index for primary key (insert, search, range scan)
3. **Week 3**: SQL tokenizer + parser → AST for INSERT and SELECT with WHERE
4. **Week 4**: WAL for crash recovery, basic transaction support (BEGIN, COMMIT, ROLLBACK)

### Key Concepts to Implement
- **Page format**: page header (page number, type, free space offset) + cell data
- **B-tree node format**: page type (leaf/internal), key count, parent pointer, cells
- **WAL format**: sequence of (transaction_id, operation_type, before_image, after_image)
- **Crash recovery**: replay WAL from last checkpoint

### Interview Discussion Points
- "Why B-tree over hash index?" → range queries, ordered scans, prefix searches
- "What is a page and why 4KB?" → matches OS page size, minimizes disk seeks
- "How does WAL enable atomicity?" → write to WAL before data file; on crash, replay WAL
- "How would you add MVCC?" → multiple versions per row, read timestamps, garbage collection

### Difficulty: Very Hard | Estimated Time: 6–8 weeks

---

## 5. Design and Build a Search Engine

### What to Build
A full-text search engine that crawls web pages, builds an inverted index, supports TF-IDF ranking, handles boolean queries (AND, OR, NOT), and provides a search API with relevance scoring.

### Why It Matters
Search is fundamental to the web and to most applications. Building one teaches you about inverted indexes, text processing, ranking algorithms, and the challenges of operating at web scale.

### Suggested Tech Stack
- **Language**: Python (for rapid prototyping) or Go (for performance)
- **Crawler**: HTTP requests with rate limiting, URL deduplication via Bloom filter
- **Index**: In-memory inverted index (or disk-based with segment files)
- **Ranking**: TF-IDF with cosine similarity
- **API**: REST endpoint for search queries

### Architecture

```
Seed URLs ──► Crawler ──► Downloader ──► Text Processor
                                              │
                                     ┌────────┼────────┐
                                     ▼        ▼        ▼
                                  Tokenize Stem  Stop
                                  Words     Words Words
                                     │
                                     ▼
                              Inverted Index
                              ┌─────────────────────────┐
                              │ "database" → [doc1, doc3, doc7]│
                              │ "engine"   → [doc1, doc5]     │
                              │ "search"   → [doc1, doc2, doc4]│
                              └─────────────────────────┘
                                     │
                                     ▼
                              TF-IDF Scorer
                                     │
                                     ▼
                              Search Results API
```

### Key Algorithms

**TF-IDF (Term Frequency - Inverse Document Frequency)**:
```
TF(term, doc) = count(term in doc) / total_terms_in_doc
IDF(term) = log(total_docs / docs_containing_term)
Score = TF * IDF
```

**Inverted Index Structure**:
```python
class InvertedIndex:
    def __init__(self):
        self.index: Dict[str, Dict[int, List[int]]] = {}
        # term → { doc_id: [position_1, position_2, ...] }

    def add_document(self, doc_id: int, text: str):
        tokens = self.tokenize(text)
        for pos, token in enumerate(tokens):
            if token not in self.index:
                self.index[token] = {}
            if doc_id not in self.index[token]:
                self.index[token][doc_id] = []
            self.index[token][doc_id].append(pos)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        # Parse query, compute TF-IDF for each candidate doc, rank
        ...
```

### Interview Discussion Points
- "What is an inverted index and why is it used for search?" → maps terms to documents, enables fast lookup
- "How does TF-IDF work?" → term frequency rewards frequent terms, IDF penalizes common terms
- "How do you handle spelling mistakes?" → fuzzy matching (edit distance), phonetic algorithms, or query expansion
- "How would you scale to billions of documents?" → sharded index, segment-based architecture (like Lucene)
- "What is a Bloom filter and where is it used in this system?" → URL deduplication in the crawler (probabilistic, memory-efficient)

### Difficulty: Hard | Estimated Time: 3–4 weeks

---

## Project Selection Guide

| Your Goal | Recommended Projects |
|---|---|
| Deep systems understanding | #4 Database Engine, #3 Message Queue |
| Web infrastructure knowledge | #1 CDN, #2 Load Balancer, #5 Search Engine |
| Interview prep (limited time) | #2 Load Balancer (3 weeks, high ROI) |
| Maximum challenge | #4 Database Engine (hardest, most rewarding) |
| Portfolio breadth | Build #1 CDN + #5 Search Engine (complementary skills) |
