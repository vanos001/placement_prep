# Queueing Theory: Interview Questions

Curated questions organized by difficulty. Aim to answer each in 2-3 minutes for interview conditions.

## Beginner

1. **What is Little's Law? State the formula and define each variable.**

   > L = λ × W. L = average number of items in the system, λ = arrival rate, W = average time in the system. Applies to any stable system.

2. **What does utilization (ρ) represent? What happens when ρ ≥ 1?**

   > Utilization is the fraction of time the server is busy. When ρ ≥ 1, the arrival rate exceeds the service capacity, and the queue grows without bound.

3. **Explain M/M/1 in Kendall's notation.**

   > Poisson (Markovian) arrivals, exponential (Markovian) service times, 1 server. The simplest non-trivial queueing model.

4. **A coffee shop serves 10 customers/hour on average, with each taking 5 minutes. What is the utilization?**

   > λ = 10/hr, μ = 12/hr (1/5min × 60), ρ = 10/12 = 0.83.

5. **Why is the exponential distribution's memoryless property important in queueing theory?**

   > It makes the math tractable. The remaining service time distribution is the same regardless of how long service has already taken, which enables closed-form solutions.

## Intermediate

6. **A web service handles 500 req/s with an average response time of 100ms. How many requests are in the system on average (L)? What's the minimum pool size?**

   > L = 500 × 0.1 = 50. Minimum pool size is 50. With variance, target 60-75.

7. **You push a single-threaded server from 60% to 90% utilization. How much does average latency increase?**

   > M/M/1: W = 1/(μ-λ). At ρ=0.6: W = 1/(μ - 0.6μ) = 1/(0.4μ) = 2.5/μ. At ρ=0.9: W = 1/(0.1μ) = 10/μ. Latency increases 4×.

8. **What is the difference between M/M/1 and M/D/1? Which has lower average latency?**

   > Same arrival process, but M/D/1 has deterministic (constant) service time. M/D/1 has lower queueing delay because there's no variance in service time. By the Pollaczek-Khinchine formula, M/D/1 has exactly half the queueing delay of M/M/1.

9. **How would you use queueing theory to decide between scaling up (bigger machine) vs. scaling out (more machines)?**

   > If the bottleneck is a single resource (one DB), scale up. If work can be parallelized across independent servers, scale out. For M/M/c, adding servers c reduces utilization and queueing delay. Compare the cost-per-throughput of both approaches.

10. **What is a priority queue? What problem does it solve, and what problem does it introduce?**

    > Higher-priority requests get served first, reducing latency for critical operations. The problem is starvation: under heavy load, low-priority requests may never get served. Solution: aging (increase priority over time).

## Advanced

11. **A microservice makes 20 parallel calls to downstream services, each with p99 = 200ms. What is the effective p99 of the composed request? How would you improve it?**

    > P(all ≤ 200ms) = 0.99^20 ≈ 0.818. So effective p99 > 200ms — you need each service at a much stricter SLO. To improve: add timeouts with fallbacks (e.g., cached data), reduce fan-out, or batch calls.

12. **Design a backpressure mechanism for a high-throughput log pipeline where the consumer (disk writer) is slower than the producer (application logs).**

    > Use a bounded ring buffer between producer and consumer. When the buffer is 80% full, signal the producer to throttle (reduce log verbosity, sample). When 100% full, drop logs (or apply a sampling policy). Monitor the buffer fill level as a metric.

13. **Explain the Pollaczek-Khinchine formula's implications for service time variance. How does this relate to tail latency?**

    > W_q ∝ (1 + C_v²). Higher service time variance directly increases queueing delay. A few very slow requests (high C_v) disproportionately affect everyone else's latency by creating longer queues. To reduce tail latency: reduce variance (timeouts, circuit breakers, avoiding unbounded operations).

14. **When would you model a system as M/G/1 rather than M/M/1? What additional data do you need, and how would you collect it?**

    > Use M/G/1 when service times don't follow an exponential distribution (which is most real systems). You need the mean and variance of service times. Collect by instrumenting your service to record per-request processing times, then compute σ² from the distribution.

15. **A service has a thread pool of 200 threads but runs on 8 cores. Under heavy load, throughput is lower than with 50 threads. Explain using queueing theory.**

    > With 200 threads on 8 cores, you have massive context switching overhead. Each CPU time slice is split among 25 threads (200/8). The effective service rate μ decreases due to context switching, which increases ρ and queueing delay. The system is spending more time switching threads than doing useful work. This is the difference between the theoretical queueing model (which ignores context switch cost) and reality.

## Common Traps

- **Confusing arrival rate with service rate**: λ is requests *arriving*, μ is requests *completing* per server.
- **Ignoring variance**: Average service time isn't enough. A system with 10ms average and 1ms std dev behaves very differently from 10ms average and 50ms std dev.
- **Assuming M/M/1 for everything**: Real systems have bounded queues, correlated arrivals, and multi-class work.
- **Forgetting the "stable system" requirement**: Little's Law and M/M/1 formulas assume ρ < 1. If the system is overloaded, the formulas give nonsense.
- **Sizing for average instead of tail**: A pool sized for average load will overflow during spikes. Always size for the load you need to handle, not the load you expect.