# System Design Interview Preparation

> *"System design interviews test your ability to build real systems, not just solve puzzles."*

## 🎯 What System Design Interviews Test

System design interviews evaluate your ability to **architect large-scale distributed systems**. Unlike coding interviews, there's no single "correct" answer — interviewers want to see your **thought process** and **trade-off analysis**.

```
┌─────────────────────────────────────────────────────────┐
│           SYSTEM DESIGN EVALUATION CRITERIA             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Problem Exploration (15%)                           │
│     ├── Requirements gathering                          │
│     ├── Scope definition                                │
│     └── Constraints identification                      │
│                                                         │
│  2. High-Level Design (25%)                             │
│     ├── Component identification                        │
│     ├── Data flow                                       │
│     └── API design                                      │
│                                                         │
│  3. Deep Dive (35%)                                     │
│     ├── Database schema                                 │
│     ├── Algorithm selection                             │
│     ├── Scaling strategies                              │
│     └── Bottleneck resolution                           │
│                                                         │
│  4. Trade-offs & Communication (25%)                    │
│     ├── Pros/cons of decisions                          │
│     ├── Alternative approaches                          │
│     └── Clear articulation                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 📖 In This Section

| Design | Difficulty | Key Concepts |
|--------|-----------|--------------|
| [Design Framework](./framework.md) | — | Universal approach to any system design question |
| [URL Shortener](./url-shortener.md) | ⭐⭐ | Hashing, database, caching, analytics |
| [Chat System](./chat.md) | ⭐⭐⭐ | WebSockets, message queues, presence, delivery |
| [News Feed](./news-feed.md) | ⭐⭐⭐ | Fan-out, ranking, caching, real-time updates |
| [Rate Limiter](./rate-limiter.md) | ⭐⭐ | Algorithms, distributed systems, Redis |
| [Key-Value Store](./kv-store.md) | ⭐⭐⭐ | Consistency, replication, partitioning |
| [Search Engine](./search.md) | ⭐⭐⭐⭐ | Crawling, indexing, ranking, NLP |
| [Video Streaming](./video-streaming.md) | ⭐⭐⭐⭐ | CDN, encoding, adaptive bitrate, recommendations |
| [Notification System](./notifications.md) | ⭐⭐⭐ | Multi-channel, delivery guarantees, prioritization |
| [Distributed File System](./dfs.md) | ⭐⭐⭐⭐ | Chunking, replication, consistency, GFS/HDFS |

## 📊 System Design Concepts Map

```
┌─────────────────────────────────────────────────────────┐
│              SYSTEM DESIGN CONCEPTS                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SCALING                                                │
│  ├── Horizontal Scaling (more machines)                 │
│  ├── Vertical Scaling (bigger machines)                 │
│  ├── Load Balancing (distribute traffic)                │
│  └── Auto-scaling (dynamic capacity)                    │
│                                                         │
│  DATA                                                    │
│  ├── SQL vs NoSQL                                       │
│  ├── Sharding (partition data)                          │
│  ├── Replication (copy data)                            │
│  ├── Caching (Redis, Memcached)                         │
│  └── CDN (static content)                               │
│                                                         │
│  COMMUNICATION                                          │
│  ├── REST API (synchronous)                             │
│  ├── Message Queue (async)                              │
│  ├── WebSockets (real-time)                             │
│  ├── gRPC (internal services)                           │
│  └── GraphQL (flexible queries)                         │
│                                                         │
│  RELIABILITY                                            │
│  ├── Redundancy (no single point of failure)            │
│  ├── Failover (automatic recovery)                      │
│  ├── Circuit Breaker (prevent cascading failures)       │
│  └── Retry with Backoff                                 │
│                                                         │
│  CONSISTENCY                                            │
│  ├── Strong Consistency (linearizable)                  │
│  ├── Eventual Consistency (BASE)                        │
│  ├── CAP Theorem                                        │
│  └── Consensus (Raft, Paxos)                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## 🎓 When to Use What

### Database Selection
```
SQL (PostgreSQL, MySQL):
├── Structured data with relationships
├── ACID transactions required
├── Complex queries (JOINs)
└── Examples: User accounts, orders, financial data

NoSQL - Document (MongoDB):
├── Flexible schema
├── Nested/hierarchical data
├── Rapid development
└── Examples: Content management, user profiles

NoSQL - Key-Value (Redis, DynamoDB):
├── Simple lookups by key
├── High throughput, low latency
├── Caching, session storage
└── Examples: Cache, session, shopping cart

NoSQL - Wide Column (Cassandra, HBase):
├── Time-series data
├── Write-heavy workloads
├── High availability
└── Examples: Metrics, logs, IoT data

NoSQL - Graph (Neo4j):
├── Relationship-heavy data
├── Social networks
├── Recommendation engines
└── Examples: Friend connections, fraud detection
```

### Communication Pattern Selection
```
REST API:
├── Client-server communication
├── CRUD operations
├── Stateless, cacheable
└── Use: Public APIs, web apps

gRPC:
├── Internal service communication
├── High performance, streaming
├── Strongly typed (protobuf)
└── Use: Microservice-to-microservice

WebSocket:
├── Real-time bidirectional
├── Persistent connection
├── Low latency
└── Use: Chat, live updates, gaming

Message Queue (Kafka, RabbitMQ):
├── Async processing
├── Decoupling services
├── Buffering load spikes
└── Use: Event processing, task queues
```

## ⏱️ Time Management (45-minute interview)

```
┌─────────────────────────────────────────────┐
│       SYSTEM DESIGN TIME ALLOCATION         │
├─────────────────────────────────────────────┤
│  Requirements & Scope         5 min (11%)   │
│  High-Level Design           10 min (22%)   │
│  Deep Dive Components        20 min (44%)   │
│  Trade-offs & Wrap-up        10 min (22%)   │
└─────────────────────────────────────────────┘
```

## 🔗 Cross-References

- [Design Framework](./framework.md) — Start here for the universal approach
- [Coding Patterns](../coding/patterns.md) — Algorithm-level patterns
- [Architecture Questions](../arch-questions.md) — Architecture interview questions
- [Cheatsheets](../../cheatsheets/architecture.md) — Quick reference for architecture concepts
