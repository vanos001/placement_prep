# High Level Design (HLD) - Overview

## What is High Level Design?

High Level Design (HLD) is the process of designing the **architecture of a system** at a macro level. It focuses on how major components interact, how data flows through the system, and how the system meets its non-functional requirements like scalability, availability, and reliability.

In an HLD interview, you're expected to design a complete system from scratch — think Twitter, Uber, or a URL shortener — by making architectural decisions and justifying trade-offs.

## HLD vs LLD

| Aspect | High Level Design (HLD) | Low Level Design (LLD) |
|--------|------------------------|----------------------|
| **Scope** | System-wide architecture | Individual components/classes |
| **Abstraction** | Services, databases, queues | Classes, methods, interfaces |
| **Focus** | Scalability, availability, trade-offs | OOP principles, design patterns |
| **Diagram** | Architecture / block diagrams | UML class / sequence diagrams |
| **Example** | "Use a message queue between services" | "Implement Observer pattern for event dispatch" |
| **Audience** | System architects, Dev leads | Developers, code reviewers |
| **Decisions** | SQL vs NoSQL, monolith vs microservices | Factory vs Builder, abstract class vs interface |

### When to Use What

- **HLD**: Product manager asks "How would you build Instagram?"
- **LLD**: Engineering lead asks "How would you design the notification module's class structure?"

In practice, both are needed. HLD comes first to establish the blueprint; LLD follows to define implementation details.

## What Interviewers Expect in HLD

### 1. Requirements Clarification (2-3 minutes)
Before designing anything, clarify:
- **Functional requirements**: What does the system do?
- **Non-functional requirements**: Scale, latency, availability, consistency
- **Constraints**: Budget, existing infrastructure, compliance

### 2. Estimation & Capacity Planning (2-3 minutes)
- Daily active users (DAU)
- QPS (Queries Per Second)
- Storage requirements
- Bandwidth

### 3. High-Level Architecture (5-10 minutes)
- Draw major components (services, databases, caches, queues)
- Show data flow between components
- Identify APIs at a high level

### 4. Deep Dive (10-15 minutes)
- Database schema and selection rationale
- Caching strategy
- Load balancing approach
- How to handle failures

### 5. Trade-offs & Alternatives
- Always discuss what you chose and why
- Mention alternatives you considered
- Acknowledge limitations of your design

## Core Pillars of HLD

```
┌─────────────────────────────────────────────┐
│              High Level Design              │
├──────────┬──────────┬──────────┬────────────┤
│Scalabili │ Availabi │ Consiste │ Security   │
│ty        │ lity     │ ncy      │            │
├──────────┼──────────┼──────────┼────────────┤
│Load      │ Failover │ CAP      │ Auth/N     │
│Balancing │ DR       │ theorem  │ Encryption │
│Sharding  │ Redundan │ Eventual │ Rate       │
│Caching   │ cy       │ vs Strong│ Limiting   │
└──────────┴──────────┴──────────┴────────────┘
```

## Common HLD Interview Problems

| Problem | Key Concepts |
|---------|-------------|
| URL Shortener | Hashing, DB design, caching |
| Twitter/Instagram | Fan-out, feeds, media storage |
| WhatsApp/Messenger | WebSockets, message ordering |
| Uber/Lyft | Geospatial indexing, matching |
| Netflix/YouTube | CDN, encoding, recommendations |
| Dropbox/Drive | Chunking, deduplication, sync |
| Web Crawler | BFS/DFS, politeness, dedup |
| Notification System | Priority queues, delivery tracking |
| Rate Limiter | Token bucket, sliding window |
| Distributed Cache | Consistent hashing, replication |

## Interview Tips

1. **Start with requirements** — never jump straight to architecture
2. **Draw diagrams** — always sketch while explaining
3. **Think out loud** — interviewers want to see your reasoning process
4. **Start simple, then scale** — begin with a monolith, then decompose
5. **Use real numbers** — "1 million users × 10 requests/day ≈ 12 QPS"
6. **Acknowledge trade-offs** — there's no perfect design
7. **Mention specific technologies** — "Redis for caching" not just "a cache"
8. **Consider failure modes** — what happens when X goes down?
9. **Don't over-engineer** — match complexity to requirements
10. **Practice with a timer** — 35-45 minutes is typical

## How to Prepare

1. **Learn fundamentals**: Study each topic in this section thoroughly
2. **Practice problems**: Design 2-3 systems per week
3. **Mock interviews**: Practice with peers or use platforms like Excalidraw
4. **Read engineering blogs**: How Netflix, Uber, and Meta built their systems
5. **Understand trade-offs**: For every decision, know the alternatives

## Next Steps

Start with [Scalability Fundamentals](./scalability.md) to understand the foundation every HLD discussion builds upon, then work through each topic systematically.

---

*Each page in this section includes real-world examples, architecture diagrams, and interview-specific guidance.*

## Cross-References

- [System Design Framework](../framework.md)
- [LLD Overview](../lld/README.md)
- [Estimation](../estimation.md)
- [Latency Numbers](../latency-numbers.md)

