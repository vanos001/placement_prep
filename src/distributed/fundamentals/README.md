# Distributed Systems Fundamentals

## Overview

This section covers the foundational concepts and theoretical results that underpin all distributed systems. Understanding these fundamentals—CAP theorem, FLP impossibility, consistency models, and time/ordering—is essential for reasoning about distributed algorithms and system design.

## Topics

| Topic | Description |
|-------|-------------|
| [CAP Theorem](./cap.md) | The fundamental trade-off between consistency, availability, and partition tolerance |
| [FLP Impossibility](./flp.md) | Why deterministic consensus is impossible in asynchronous systems with one faulty process |
| [Consistency Models](./consistency.md) | The spectrum from strong to eventual consistency |
| [Time and Ordering](./time.md) | How to order events without a global clock |
| [Lamport Clocks](./lamport.md) | Logical clocks that capture happened-before relationships |
| [Vector Clocks](./vector-clocks.md) | Capturing causal dependencies across all nodes |

## Key Insight

Distributed systems are fundamentally harder than single-machine systems because:

1. **No global state** — Each node has its own view of the world
2. **No global clock** — Nodes can't perfectly synchronize time
3. **Partial failures** — Some nodes may fail while others continue
4. **Unreliable networks** — Messages can be lost, delayed, duplicated, or reordered

These constraints mean that many problems solvable on a single machine (like consensus) become provably impossible or extremely difficult in distributed settings.
