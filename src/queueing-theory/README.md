# Queueing Theory

Queueing theory is the mathematical study of waiting lines. It provides formal models to predict latency, throughput, and resource utilization in systems where requests contend for shared resources. Every time a request waits for a database connection, a thread, or a CPU core, it enters a queue — and queueing theory tells you what happens next.

## Why Software Engineers Should Care

You don't need to solve differential equations daily, but queueing theory gives you:

- **Intuition** for why latency explodes near 100% utilization (it's not linear)
- **Formulas** for sizing resources (thread pools, connection pools, queue depths)
- **Vocabulary** for system design discussions (utilization, arrival rate, service time)
- **Models** for capacity planning that go beyond "let's add more machines"

The core insight: **as utilization approaches 100%, latency goes to infinity**. This is not a software bug — it's mathematics.

## Kendall's Notation

Queueing models are described using Kendall's notation **A/S/c/K/N/D**:

| Symbol | Meaning | Common Values |
|--------|---------|---------------|
| **A** | Arrival process | M (Markovian/Poisson), D (Deterministic), G (General) |
| **S** | Service time distribution | M (Exponential), D (Constant), G (General) |
| **c** | Number of servers | 1, 2, ..., ∞ |
| **K** | System capacity (max items) | ∞ (default), or finite |
| **N** | Population size (possible arrivals) | ∞ (default), or finite |
| **D** | Queue discipline | FIFO (default), LIFO, PRI, PS |

The most common models:

| Model | Meaning | Real-World Analog |
|-------|---------|-------------------|
| **M/M/1** | Poisson arrivals, exponential service, 1 server | Single-threaded request handler |
| **M/M/c** | Same, but c parallel servers | c-thread worker pool |
| **M/M/∞** | Infinite servers (no queueing) | Serverless auto-scaling |
| **M/D/1** | Deterministic (constant) service time | Fixed-size packet processing |
| **M/G/1** | General service time distribution | Most real systems |

## Core Terminology

| Term | Symbol | Definition |
|------|--------|------------|
| **Arrival rate** | λ (lambda) | Average requests arriving per second |
| **Service rate** | μ (mu) | Average requests a single server can handle per second |
| **Utilization** | ρ (rho) | Fraction of time the server is busy: ρ = λ / (c × μ) |
| **Average number in system** | L | Including those being served and waiting |
| **Average number in queue** | L_q | Only those waiting |
| **Average time in system** | W | Wait time + service time ("sojourn time") |
| **Average wait in queue** | W_q | Time spent waiting before service starts |

## Little's Law

Little's Law is the most fundamental result in queueing theory, and it applies to **any** stable system:

```
L = λ × W
```

- **L**: average number of items in the system
- **λ**: average arrival rate
- **W**: average time an item spends in the system

Rearranged: `W = L / λ` or `λ = L / W`

### Example: Sizing a Thread Pool

A service receives λ = 1000 requests/sec. Average processing time (service time) is 50ms, so W ≈ 50ms = 0.05s.

```
L = λ × W = 1000 × 0.05 = 50
```

On average, 50 requests are in the system at any time. So you need **at least 50 threads**. In practice, add headroom for variance: 60-75 threads.

## Real-World Applications

| System | Queue Model | What You Optimize |
|--------|------------|-------------------|
| **Load balancer** | M/M/c (c = backend servers) | Number of backends, queue depth before 503 |
| **Database connection pool** | M/M/c (c = max connections) | Pool size, timeout settings |
| **Request queue (RabbitMQ)** | M/M/c (c = consumers) | Consumer count, prefetch count |
| **Thread pool** | M/M/c (c = threads) | Core/max pool size, rejection policy |
| **TCP backlog** | M/M/c/K (finite buffer) | `somaxconn`, `tcp_max_syn_backlog` |
| **Serverless** | M/M/∞ (ideal) or M/M/c with auto-scaling | Scale-to-zero, cold start latency |

## Topics in This Section

| Topic | Description |
|-------|-------------|
| [Fundamentals](fundamentals.md) | Poisson processes, M/M/1 and M/M/c formulas, queue disciplines |
| [Applied Systems](applied-systems.md) | Connection pools, thread pools, load balancers, backpressure |
| [Interview Questions](interview-questions.md) | Curated questions from beginner to advanced |

## References

- Kleinrock, L. *Queueing Systems*, Volumes 1-2. Wiley, 1975.
- Harchol-Balter, M. *Performance Modeling and Design of Computer Systems*. Cambridge, 2013. [free preprint chapters](https://www.cs.cmu.edu/~harchol/PerformanceModeling/)
- Gunther, N. *Analyzing Computer System Performance with Perl::PDQ*. Springer, 2005.
- Wikipedia: [Queueing theory](https://en.wikipedia.org/wiki/Queueing_theory)

## Interview Questions

1. **What is Little's Law? Give a practical example of using it.**
2. **What happens to latency as utilization approaches 100% in an M/M/1 queue?**
3. **How would you size a database connection pool for a service with 500 QPS and 10ms average query time?**
4. **What is Kendall's notation? Explain M/M/c.**
5. **Why can't you achieve 100% utilization in a queueing system without infinite latency?**
