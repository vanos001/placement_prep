# Queueing Theory Fundamentals

This chapter covers the mathematical foundations: arrival processes, service distributions, and the closed-form results for the most common queueing models.

## Arrival Processes

### The Poisson Process

The **Poisson process** is the default model for request arrivals. It assumes:

1. **Independent arrivals**: One arrival doesn't affect the probability of the next
2. **Stationary**: The arrival rate λ doesn't change over time
3. **Ordinary**: Two arrivals can't happen at exactly the same instant

The time between consecutive arrivals follows an **exponential distribution** with mean `1/λ`:

```
P(inter-arrival time ≤ t) = 1 - e^(-λt)
```

**Key property**: The exponential distribution is **memoryless**. The probability that you'll wait another 5ms is the same whether you've already waited 0ms or 500ms. This is what makes M/M/c models tractable.

**Is real traffic Poisson?** No, but it's often close enough for capacity planning. Real traffic has bursts, diurnal patterns, and correlations. For more accuracy, use simulation or measurement.

## Service Time Distributions

| Distribution | Notation | Mean | Variance | When It Applies |
|-------------|----------|------|----------|-----------------|
| **Exponential** | M | 1/μ | 1/μ² | Simple models, variable-length processing |
| **Deterministic** | D | 1/μ | 0 | Fixed-size packets, constant-time ops |
| **General** | G | 1/μ | σ² | Real systems (use measured variance) |

The **coefficient of variation** (C_v = σ / mean) captures how "spread out" service times are:

- C_v = 0: deterministic (all service times identical)
- C_v = 1: exponential (the M in Kendall's notation)
- C_v > 1: high variance (some requests much slower than others)

High C_v is a major source of tail latency. A few very slow requests create long queues that affect all subsequent requests.

## Utilization Factor

For a system with **c** servers, each with service rate μ:

```
ρ = λ / (c × μ)
```

- **ρ < 1**: System is stable (queue doesn't grow without bound)
- **ρ = 1**: System is at capacity (queue grows linearly)
- **ρ > 1**: System is overloaded (queue grows without bound, latency → ∞)

**Critical insight**: Latency is not linear in utilization. At ρ = 0.9, average queueing delay is 9× the average service time. At ρ = 0.99, it's 99×. This is why you should **never run production systems above ~70% utilization** if latency matters.

## Queue Discipline

How do you decide which waiting request gets served next?

| Discipline | Description | Use Case |
|-----------|-------------|----------|
| **FIFO** (FCFS) | First in, first out | Default for most systems, fair, predictable |
| **LIFO** | Last in, first out | Stack-based processing, some caches |
| **Priority** | Higher-priority requests served first | Premium vs. free tier, health checks |
| **Processor Sharing (PS)** | All requests served simultaneously at equal rate | Fair scheduling, CPU time-sharing |
| **Shortest Job First (SJF)** | Shortest processing time first | Minimizes average latency (needs oracle) |
| **Shortest Remaining Time** | SJF with preemption | Theoretically optimal, impractical |

**Priority queues** can cause **starvation** of low-priority requests under heavy load. Solution: use aging (gradually increase priority of waiting requests).

## M/M/1 Queue

The simplest and most instructive model: single server, Poisson arrivals, exponential service.

### Key Formulas

Given arrival rate λ, service rate μ, utilization ρ = λ/μ (where ρ < 1):

| Metric | Formula | Intuition |
|--------|---------|-----------|
| **Probability of zero items** | P₀ = 1 - ρ | The server is idle (1 - ρ) fraction of time |
| **Average items in system** | L = ρ / (1 - ρ) | Diverges as ρ → 1 |
| **Average items in queue** | L_q = ρ² / (1 - ρ) | Queue length grows quadratically |
| **Average time in system** | W = 1 / (μ - λ) | Includes service time |
| **Average wait in queue** | W_q = ρ / (μ - λ) | Pure waiting, no service |
| **Probability of n items** | Pₙ = (1-ρ)ρⁿ | Geometric distribution |

### Worked Example

A single-threaded API handler processes requests with average service time of 20ms (μ = 50 req/s). Traffic is 30 req/s (λ = 30).

```
ρ = λ/μ = 30/50 = 0.6

L     = 0.6 / (1 - 0.6)       = 0.6 / 0.4  = 1.5 items in system
L_q   = 0.6² / (1 - 0.6)      = 0.36 / 0.4 = 0.9 items in queue
W     = 1 / (50 - 30)         = 0.05s      = 50ms in system
W_q   = 0.6 / (50 - 30)       = 0.03s      = 30ms in queue
```

Now push utilization to 90% (λ = 45):

```
ρ = 0.9
L   = 0.9 / 0.1  = 9 items     (was 1.5)
W_q = 0.9 / 5    = 180ms       (was 30ms)
```

A 50% increase in load (30 → 45 req/s) caused a **6× increase** in queue wait time. This is the superlinear latency blowup.

## M/M/c Queue (Multi-Server)

With c identical servers, the formulas become more complex but follow the same principles.

The probability that all servers are busy (which determines if you queue or get served immediately):

```
       (cρ)^c / (c! × (1-ρ))
P(queue) = ───────────────────────
         Σ(k=0 to c-1) (cρ)^k/k! + (cρ)^c / (c! × (1-ρ))
```

Simplified metrics once you have P(queue):

```
W_q = P(queue) × (1 / (cμ - λ)) × (1 / c)
W   = W_q + 1/μ
L_q = λ × W_q
L   = λ × W
```

### Intuition

- **c = 1**: Reduces to M/M/1
- **c = ∞**: Every arrival gets its own server immediately (M/M/∞). No queueing, W_q = 0
- **Adding servers** has diminishing returns: going from 1→2 servers is more impactful than 10→11

## M/M/∞ Queue

Infinite servers means **no waiting**:

```
W_q = 0
W   = 1/μ  (just the service time)
L   = λ/μ = ρ × c  (but c = ∞, so L = λ/μ is finite)
```

This models **serverless / auto-scaling** where every request gets its own resource. The cost is maximum resource usage. In practice, you cap c at some maximum and queue beyond that.

## When Simple Models Break Down

Queueing theory models assume:

1. **Infinite buffer**: Real systems have bounded queues (TCP backlog, thread pool limits)
2. **Poisson arrivals**: Real traffic has bursts, flash crowds, diurnal patterns
3. **Independent service times**: Real systems have correlated loads (cache misses cascade)
4. **Single class of work**: Real systems mix fast reads and slow writes
5. **No failures**: Real servers crash, networks partition

**What to do**: Use queueing theory for **intuition and first-order estimates**, then validate with simulation or measurement. The Pollaczek-Khinchine formula extends M/G/1 to general service distributions, which is often more realistic.

### Pollaczek-Khinchine Formula (M/G/1)

For general service time with mean 1/μ and variance σ²:

```
W_q = (λ × σ² + λ/μ²) / (2 × (1 - ρ))
    = (λ × (σ² + 1/μ²)) / (2 × (1 - ρ))
    = ρ × (1 + C_v²) / (2 × μ × (1 - ρ))
```

When C_v = 1 (exponential), this reduces to the M/M/1 result. When C_v = 0 (deterministic), queue wait is halved. **High variance in service time is the enemy of low latency.**

## References

- Harchol-Balter, M. *Performance Modeling and Design of Computer Systems*, Ch. 2-4. Cambridge, 2013.
- Kleinrock, L. *Queueing Systems, Vol. 1: Theory*. Wiley, 1975.
- Gunther, N. *Guerrilla Capacity Planning*, Springer, 2007.

## Interview Questions

1. **Derive the average queue length for M/M/1. What happens when ρ → 1?**
2. **Why does latency increase superlinearly with utilization?**
3. **What is the memoryless property of the exponential distribution? Why does it matter for M/M/c models?**
4. **When would you use M/G/1 instead of M/M/1? What additional parameter do you need?**
5. **A server handles requests in exactly 10ms each (deterministic). How does queueing delay compare to an exponential server with the same mean?**
6. **What is the difference between L (items in system) and L_q (items in queue)?**
7. **Explain the Pollaczek-Khinchine formula in plain English. What does it tell us about service time variance?**
8. **When would M/M/∞ be a good model? What are the practical limitations?**
9. **What is a priority queue discipline, and what problem does it solve? What new problem does it create?**