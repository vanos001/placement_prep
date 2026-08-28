# The M/M/1 Queue and Little's Law

The **M/M/1** queue — single server, Poisson arrivals, exponential service times, infinite buffer, FIFO discipline — is the simplest non-trivial queueing system. Almost every closed-form result in queueing theory either reduces to an M/M/1 special case or borrows its proof technique. Despite its simplicity, the M/M/1 model captures the single most important phenomenon in capacity planning: **latency grows without bound as utilization approaches 100%**, and the growth is highly non-linear.

This chapter derives the steady-state distribution, the headline performance metrics, and Little's Law — the only queueing-theory result that holds in *any* stable system, regardless of arrival or service distribution.

## The Poisson Arrival Process (the first "M")

A stochastic process {N(t), t ≥ 0} counting arrivals is a **Poisson process** with rate λ if:

1. **Independent increments**: N(t) − N(s) is independent of N(s') for s' ≤ s < t.
2. **Stationary increments**: The distribution of N(t+s) − N(t) depends only on s.
3. **Ordinary**: P(N(t+h) − N(t) ≥ 2) = o(h) as h → 0 (no simultaneous arrivals).
4. **Probability of one arrival in h**: P(N(t+h) − N(t) = 1) = λh + o(h).

From these axioms follows that the **inter-arrival times** X_1, X_2, … are **i.i.d. exponential** with rate λ:

```
f_X(t) = λ e^{-λt} ,     t ≥ 0
E[X] = 1/λ ,  Var[X] = 1/λ²
```

and the count N(t) has the Poisson distribution:

```
P(N(t) = n) = (λt)^n e^{-λt} / n!  ,  E[N(t)] = λt
```

**Memoryless property**: P(X > s + t | X > s) = P(X > t). The exponential forgets how long you've already waited. This is what makes M/M/1 (and M/M/c) tractable — the residual arrival and service times are always fresh exponentials, and the system state at any instant fully characterises the future.

## Exponential Service (the second "M")

The single server processes one request at a time; the service time S ~ Exp(μ) with mean 1/μ. The parameter μ is the **service rate** (requests per second the server can complete when busy). The exponential assumption is strong (real services rarely have C_v = 1) but — as we show at the end with the Pollaczek-Khinchine formula — it is exactly the high-variance case, so M/M/1 metrics are a **pessimistic upper bound** on queueing delay for any service distribution with the same mean.

## Stability and Utilization

Let λ be the arrival rate and μ the service rate. Define the **traffic intensity** (a.k.a. utilization):

```
ρ = λ / μ
```

- If ρ < 1, the queue is **positive recurrent** (stable), and a stationary distribution exists.
- If ρ = 1, the queue is **null recurrent**: it returns to any state infinitely often but with infinite mean recurrence time.
- If ρ > 1, the queue is **transient**: it drifts to infinity almost surely.

**Throughout this chapter we assume ρ < 1.**

## The Steady-State Distribution P_n

Let P_n(t) be the probability of n customers in the system at time t. The birth-death process for M/M/1 has:

```
Birth rate (state n → n+1):    λ_n = λ      for all n ≥ 0
Death rate (state n → n-1):    μ_n = μ      for all n ≥ 1
```

Setting the global-balance equations (flow into state n = flow out of state n) and solving for the steady-state distribution P_n = lim_{t→∞} P_n(t), we get the **detailed-balance** equations:

```
λ P_0 = μ P_1
λ P_n = μ P_{n+1}   for n ≥ 0
```

Iterating, P_n = (λ/μ)^n · P_0 = ρ^n · P_0. Normalising over n = 0, 1, 2, …:

```
Σ_{n=0}^∞ P_n = P_0 · Σ ρ^n = P_0 / (1 - ρ) = 1
=> P_0 = 1 - ρ

=>   P_n = (1 - ρ) ρ^n     (n ≥ 0)
```

So the number of customers in an M/M/1 system in steady state has a **geometric distribution** with parameter 1 − ρ. The probability of an empty system is 1 − ρ (the server is idle that fraction of the time). The probability of n ≥ N customers is ρ^N (heavy-tailed as ρ → 1).

## Headline Performance Metrics

From the distribution, the four core metrics follow by direct computation:

### Average number in system (L)

```
L = Σ_{n=0}^∞ n · P_n = (1-ρ) · Σ n ρ^n = (1-ρ) · ρ/(1-ρ)² = ρ / (1-ρ)
```

### Average number in queue (L_q)

The number in queue when n customers are present is max(0, n−1). So:

```
L_q = Σ_{n=1}^∞ (n-1) P_n = L - ρ = ρ² / (1-ρ)
```

(Equivalently, the server is busy with probability ρ, contributing ρ customers in service on average.)

### Average time in system (W) — by Little's Law

Applying L = λW (proved below) directly to the whole system:

```
W = L / λ = ρ / (λ (1 - ρ)) = 1 / (μ - λ)
```

This is the **sojourn time**: time from arrival to departure, including service.

### Average wait in queue (W_q)

```
W_q = W - 1/μ = 1/(μ - λ) - 1/μ = ρ / (μ - λ) = λ / (μ (μ - λ))
```

Or, by Little's Law applied to the queue alone: L_q = λ · W_q ⇒ W_q = L_q / λ = ρ² / (λ (1-ρ)).

### Summary

```
P_n = (1 - ρ) ρ^n             (steady-state distribution)
P_0 = 1 - ρ                   (idle probability)
L   = ρ / (1 - ρ)             (mean number in system)
L_q = ρ² / (1 - ρ)            (mean queue length)
W   = 1 / (μ - λ)             (mean sojourn time)
W_q = ρ / (μ - λ)             (mean waiting time)
```

## Worked Example

A single-threaded API server processes requests with mean service time 20 ms (μ = 50 req/s). Arrival rate λ = 30 req/s. So ρ = 30/50 = 0.6.

```
L   = 0.6 / 0.4 = 1.5 requests in system
L_q = 0.36 / 0.4 = 0.9 requests in queue
W   = 1 / 20 = 0.050 s = 50 ms sojourn
W_q = 0.6 / 20 = 0.030 s = 30 ms queue wait
```

Push load up to ρ = 0.9 (λ = 45 req/s):

```
L   = 0.9 / 0.1 = 9.0  (6× increase for 50% more load)
W_q = 0.9 / 5 = 0.180 s = 180 ms   (6× increase)
```

The **non-linear blow-up**: latency is proportional to 1/(1−ρ). A 50% increase in load (ρ: 0.6 → 0.9) produces a 6× increase in queueing latency. At ρ = 0.99, W_q = 0.99 × 50 = 49.5 ms × 1/0.01 = ~4950 ms — 165× the queue wait at ρ = 0.6.

## Little's Law: L = λW

### The Statement

**Theorem (Little, 1961; Stidham, 1974 generalisation).** *For any queueing system in statistical equilibrium — with arbitrary arrival process, arbitrary service time distribution, arbitrary scheduling discipline, arbitrary topology — the long-run time-average number of customers L in the system equals the long-run arrival rate λ times the long-run average time W each customer spends in the system:*

```
L = λ W
```

The result is **distribution-free**. It applies to M/M/1, M/G/c, GI/G/∞, fork-join networks, multi-class systems, and even seemingly-pathological cases like LCFS-PR.

### Proof (sketch)

Let a_i be the arrival time of customer i (i = 1, 2, …), d_i the departure time, and S_i = d_i − a_i its sojourn time. Define:

- N(t) = number of customers in system at time t = (number of arrivals ≤ t) − (number of departures ≤ t).
- A(t) = total area under N(t) from 0 to T = ∫_0^T N(t) dt.

By Fubini's theorem, this area also equals the sum over all customers i of the time they spent inside the system during [0, T]:

```
A(T) = Σ_i [max(0, min(d_i, T) - max(a_i, 0))]
```

(Each customer contributes their overlap with [0, T].) Dividing by T:

```
(1/T) A(T) = (1/T) Σ_i S_i^{(T)}
```

where S_i^{(T)} is the truncated sojourn time. As T → ∞, the left side → L (the time-average number in system), and the right side → λ · W (number of arrivals per unit time = λ, times the average sojourn per arrival = W). The argument works for any stationary ergodic process and any service discipline that preserves customer identities.

**The key technical subtlety** is showing that the truncation effects vanish as T → ∞ (which requires only λW < ∞, i.e., finite mean sojourn). Stidham's 1974 paper formalises this rigorously.

### Why Little's Law is everywhere

- **Capacity planning**: Given λ (request rate) and W (target response time), L = λW tells you the average occupancy of the system — i.e., the resource size you need.
- **Profiling**: If you observe L = 50 in-flight requests and λ = 1000/s, then W = 50/1000 = 50 ms — the average request latency, *without instrumenting individual requests*.
- **USL (Universal Scalability Law)**: Little's Law applied to a contention-limited system gives the throughput-vs-load curve.

### Little's Law applied to sub-systems

The same law applies to any sub-region of the system, allowing you to "pull metrics apart":

| Application | L  | λ | W |
|-------------|----|---|---|
| Whole system | items in flight | arrival rate | sojourn time |
| Queue only | L_q | arrival rate | W_q (wait in queue) |
| Server only | ρ = λ/μ (busy fraction) | arrival rate | 1/μ (service time) |
| Database pool | active connections | query rate | query latency |

Verify the queue + server split for M/M/1: L_q + L_server = ρ²/(1−ρ) + ρ = (ρ² + ρ − ρ²) / (1−ρ) = ρ/(1−ρ) = L. ✓

## M/M/c: Multi-Server Extension

For c parallel identical servers and Poisson arrivals (rate λ) and exponential service (rate μ per server), the steady-state distribution is:

```
         (cρ)^n / n!
P_n = ───────────────────── × P_0     for 0 ≤ n ≤ c
         1

         (cρ)^n / (c! · c^(n-c))
P_n = ────────────────────── × P_0    for n ≥ c
         1
```

with ρ = λ / (c μ) (per-server utilization), and:

```
              1
P_0 = ────────────────────────────────────────────────────────
       Σ_{k=0}^{c-1} (cρ)^k / k!  +  (cρ)^c / (c! (1 - ρ))
```

The probability an arrival must wait (the **Erlang C** probability) is the probability that all c servers are busy:

```
              (cρ)^c / (c! (1 - ρ))
P_wait = ─────────────────────────────────────────────────────
          Σ_{k=0}^{c-1} (cρ)^k/k! + (cρ)^c/(c! (1-ρ))
```

Then:

```
W_q = P_wait × 1 / (cμ - λ)
L_q = λ W_q
W   = W_q + 1/μ
L   = L_q + λ/μ = L_q + cρ
```

M/M/1 is the special case c = 1; M/M/∞ is the limit c → ∞ (no waiting, W_q = 0).

## M/G/1: The Pollaczek-Khinchine Formula

For Poisson arrivals, **general service distribution** with mean 1/μ and variance σ², single server:

```
                    λ σ²   ρ²
W_q = ────────────── + ──────────
       2 (1 - ρ)        2 μ (1 - ρ)

= ρ (1 + C_v²) / (2 μ (1 - ρ))
```

where C_v = σ·μ is the coefficient of variation of service time.

**Special cases**:

| Distribution | C_v | W_q |
|--------------|------|-----|
| M (exponential) | 1 | ρ / (μ (1 - ρ)) — matches M/M/1 ✓ |
| D (deterministic) | 0 | ρ / (2 μ (1 - ρ)) — half the M/M/1 wait |
| H_2 (hyper-exponential) | > 1 | worse than M/M/1 |

**Key engineering insight**: queueing delay scales with **(1 + C_v²)**. Cutting service-time variance in half is as effective as halving utilization. This is why batch-processing schedulers (which produce deterministic per-task service times) achieve much better tail latency than fair-share schedulers in the same load regime.

## M/M/1 with Bounded Buffer (M/M/1/K)

If the buffer can hold K customers (system capacity K+1 including the one in service), the steady-state distribution becomes the truncated geometric:

```
            (1 - ρ) ρ^n
P_n = ──────────────────── ,   n = 0, 1, …, K (when ρ ≠ 1)
       1 - ρ^(K + 1)

P_block = P_K = (1 - ρ) ρ^K / (1 - ρ^(K+1))     (Erlang loss)
```

For ρ = 1 exactly, the distribution is uniform: P_n = 1/(K+1).

This model is the right one for sizing TCP `somaxconn`, thread-pool rejection queues, and any real system with bounded backpressure.

## Where M/M/1 Breaks Down

1. **Non-Poisson arrivals**: real traffic has diurnal patterns, flash crowds, and bursty self-similar structure (Paxson & Floyd 1995). For these, MMPP (Markov-modulated Poisson process) or batch-Poisson models are more accurate.
2. **Non-exponential service**: most backends have heavy-tailed service distributions (a few pathological queries dominate). Use M/G/1 (Pollaczek-Khinchine) or simulate.
3. **Finite buffers**: real queues reject; use M/M/1/K or M/M/c/K.
4. **Multi-class workloads**: priority, fair-share, or class-based queues need priority queueing analysis (e.g., M/M/1 with preemptive resume has per-class wait formulas involving the residual-busy-period distribution).
5. **Network effects**: in tandem queues (M/M/1 → M/M/1 → …), departure processes are not Poisson (Burke's theorem says they are for the first node only if arrivals are Poisson, but real arrival streams with feedback loops break this).

## References

1. Kleinrock, L. *Queueing Systems, Volume 1: Theory*. Wiley, 1975. ISBN 0-471-49110-X. — The classical reference; Chapter 2 covers M/M/1, Chapter 3 Little's Law, Chapter 4 multi-server systems.
2. Little, J. D. C. *A Proof for the Queuing Formula L = λW*. Operations Research, 9(3):383–387, 1961. — [JSTOR](https://www.jstor.org/stable/167570)
3. Stidham, S. *A Last Word on L = λW*. Operations Research, 22(2):417–421, 1974. — The rigorous generalisation. [JSTOR](https://www.jstor.org/stable/170514)
4. Gross, D., Shortle, J., Thompson, J., Harris, C. *Fundamentals of Queueing Theory*, 5th ed. Wiley, 2018. — Chapters 1–3.
5. Harchol-Balter, M. *Performance Modeling and Design of Computer Systems*. Cambridge University Press, 2013. Free preprint chapters: [https://www.cs.cmu.edu/~harchol/PerformanceModeling/](https://www.cs.cmu.edu/~harchol/PerformanceModeling/)
6. Pollaczek, F. *Über eine Aufgabe der Wahrscheinlichkeitstheorie I–II*. Mathematische Zeitschrift, 32:64–100, 729–750, 1930.
7. Khintchine, A. Y. *Mathematical Theory of Queueing*. Trudy Mat. Inst. Steklov, 49, 1955.
8. Kingman, J. F. C. *The single server queue in heavy traffic*. Proc. Cambridge Philos. Soc., 57:902–904, 1961. — The heavy-traffic approximation, fundamental to understanding ρ → 1.
9. Paxson, V., Floyd, S. *Wide-area traffic: A failure of Poisson modeling*. IEEE/ACM Transactions on Networking, 3(3):226–244, 1995. — [https://ee.lbl.gov/papers/wan-poisson-tnet95.pdf](https://ee.lbl.gov/papers/wan-poisson-tnet95.pdf)
10. Wikipedia: [M/M/1 queue](https://en.wikipedia.org/wiki/M/M/1_queue), [Little's Law](https://en.wikipedia.org/wiki/Little%27s_law), [Pollaczek-Khinchine formula](https://en.wikipedia.org/wiki/Pollaczek%E2%80%93Khinchine_formula).

## Interview Questions

1. Derive P_n = (1−ρ) ρ^n from the birth-death balance equations. Where does the requirement ρ < 1 enter?
2. Show that L_q = L − ρ and L = ρ/(1−ρ). Why is the server-busy fraction exactly ρ?
3. Prove Little's Law from first principles. What are the precise assumptions, and which are removable?
4. A single-server system has λ = 100 req/s and average service time 8 ms. Compute L, W, W_q. At what utilization does queueing delay become > 10× the service time?
5. State the Pollaczek-Khinchine formula. Explain the (1 + C_v²) factor — what is its engineering implication for tail latency?
6. How does M/M/c differ from c parallel M/M/1 systems each handling 1/c of the load? Why is pooling better?
7. What happens in M/M/1 as ρ → 1? What does Kingman's heavy-traffic approximation say about the queue length distribution in this limit?
8. The first "M" in M/M/1 is the **exponential distribution**, but it is often described as "memoryless". State the memoryless property and explain why it makes the analysis tractable.
