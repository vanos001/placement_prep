# Design Documents, RFCs, and ADRs

> The act of writing forces you to think. A design document is the cheapest way to find out you're wrong.

## 1. What Are Design Documents?

Design documents capture **technical decisions** before implementation. They exist to:

- Force clear thinking before writing code
- Enable **peer review** of architecture
- Create a **record** for future engineers
- Catch flawed assumptions early

### Types of Design Documents

| Type | Scope | Owner | Examples |
|------|-------|-------|----------|
| **Design Doc** | Feature or system | Tech lead / engineer | Google-style 1-pagers, Amazon 6-pagers |
| **RFC (Request for Comments)** | Broad change, often cross-team | Author + community | Rust RFCs, Python PEPs |
| **ADR (Architecture Decision Record)** | Single architectural decision | Any engineer | Kubernetes ADRs |

## 2. When to Write One

| Write One | Don't Bother |
|-----------|-------------|
| New system or service | Bug fixes |
| Cross-team dependency changes | Trivial refactors |
| Database schema migration | Internal implementation details |
| API design for external consumers | Adding a utility function |
| Changing an established pattern | One-off scripts |
| Anything that costs > 2 weeks of work | |

**Rule of thumb:** if the cost of being wrong exceeds the cost of writing the doc, write it.

## 3. Structure of a Good Design Doc

### Google-Style Template

```
1. Title and Authors
2. TL;DR (2-3 sentences)
3. Background and Motivation
4. Goals and Non-Goals
5. Proposed Design
   - Architecture diagram
   - Data model
   - API surface
   - Key algorithms
6. Alternatives Considered
7. Testing Plan
8. Monitoring and Observability
9. Rollout Plan
10. Open Questions
```

### Goals and Non-Goals (Critical Section)

Explicitly stating what you're **not** doing prevents scope creep and misaligned reviews.

```markdown
## Goals
- Support paginated listing of orders with consistent ordering
- Handle 10,000 QPS with p99 < 100ms

## Non-Goals
- Real-time order updates (use WebSocket service instead)
- Admin-facing UI (separate project)
- Migrating legacy order tables
```

### Alternatives Considered

This section demonstrates you've explored the design space:

```markdown
## Alternatives Considered

### Option A: Event sourcing
- **Pros:** Full audit trail, temporal queries
- **Cons:** Complexity, replay cost, team unfamiliarity
- **Rejected:** Complexity doesn't justify benefit for read-heavy workload

### Option B: CQRS with separate read store
- **Pros:** Optimized reads, independent scaling
- **Cons:** Eventual consistency, operational overhead
- **Rejected:** Our SLA requires strong consistency
```

## 4. RFC Process

RFCs are formal proposals for significant changes, widely used in open-source and large organizations.

### Lifecycle

```
Draft → Review → Final → Implemented → Archived
```

| Stage | What Happens | Duration |
|-------|-------------|----------|
| **Draft** | Author writes the RFC, gathers initial feedback | Days to weeks |
| **Review Period** | Community reviews, comments, proposes changes | 1-4 weeks |
| **Final Comment Period (FCP)** | Last call for objections | 3-10 days |
| **Accepted / Rejected** | Maintainer decides | — |
| **Implemented** | Code is written per the accepted RFC | Weeks to months |

### Notable RFC Systems

| Organization | Format | Examples |
|-------------|--------|----------|
| Rust | `rfcs/` repo, markdown with merge process | `async/await`, `non-lexical lifetimes` |
| Python | PEPs (Python Enhancement Proposals) | PEP 484 (type hints), PEP 572 (walrus operator) |
| IETF | Numbered RFC documents | HTTP/1.1 (RFC 7231), TCP (RFC 793) |
| Ethereum | EIPs | EIP-1559 (fee market change) |

## 5. Architecture Decision Records (ADRs)

ADRs capture **individual** architectural decisions — one decision per record. They are lightweight, timestamped, and immutable once accepted.

### ADR Format (Michael Nygard's template)

```markdown
# ADR-001: Use PostgreSQL as Primary Database

## Status
Accepted

## Context
We need a relational database for transactional workloads.
Options: MySQL, PostgreSQL, CockroachDB.

## Decision
We will use PostgreSQL 15 as our primary database.

## Consequences
- Positive: JSONB support, advanced indexing, strong community
- Negative: No horizontal sharding built-in (need Citus)
- Neutral: Team has PostgreSQL experience
```

### ADR vs Design Doc

| Aspect | ADR | Design Doc |
|--------|-----|------------|
| Scope | One decision | Full system/feature |
| Size | Short (paragraphs) | Long (pages) |
| Mutability | Immutable once recorded | Can be revised before approval |
| When | Any time a decision is made | Before building something significant |
| Number | Many (one per decision) | One per project/feature |

## 6. Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Writing the doc after the code | Enforce doc-first culture; block PRs without approved design |
| Vague problem statement | Quantify: "p99 latency is 2s" not "it's slow" |
| No diagram | Include an ASCII or C4 diagram — a picture is worth 1000 words |
| Ignoring non-goals | Always include non-goals to prevent scope creep |
| No alternatives | Shows you haven't thought critically — always list 2-3 options |
| Stale ADRs | Keep an ADR index; mark superseded decisions |

## Interview Questions

1. **When should you write a design document?**
   For any non-trivial feature: new services, API changes, database migrations, cross-team dependencies. The cost of being wrong should exceed the cost of writing the doc. Skip for bug fixes, trivial changes, and prototypes.

2. **What is the most important section of a design doc?**
   Goals and non-goals — they define scope and prevent scope creep. Without explicit non-goals, reviewers push for features outside the project's scope, and implementation bloats.

3. **What is the difference between an RFC and a design doc?**
   A design doc is for internal team decisions. An RFC is a formal proposal meant for broader review, often across an organization or community, with a structured review lifecycle.

4. **What is an ADR? How is it different from a design doc?**
   An Architecture Decision Record captures a single architectural decision permanently. It's short, immutable, and focused. A design doc covers an entire feature/system with multiple decisions. Projects accumulate many ADRs over time.

5. **How do you handle a disagreement during design review?**
   First, clarify if the disagreement is about goals or approach. If goals, escalate to stakeholders. If approach, prototype both options with benchmarks. Fall back to ADR: document the decision, the dissenting opinion, and move forward — you can always revisit.

6. **What makes a good alternatives section?**
   Each alternative should include: what it is, pros, cons, and why it was rejected. The rejected option should sound reasonable — if it sounds stupid, you haven't represented it fairly.

7. **How do you keep design docs from becoming stale?**
   Store them in version control alongside code. Link ADRs to the commits that implement them. During onboarding, review recent docs. Mark outdated ones as superseded, never delete.