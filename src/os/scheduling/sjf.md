# Shortest Job First (SJF)

## Overview

**SJF (Shortest Job First)** selects the process with the smallest burst time (execution time). It's provably optimal for minimizing average waiting time, but requires knowing burst times in advance.

> **Interview one-liner:** "SJF picks the shortest job next — it's optimal for average waiting time but can starve long jobs and requires burst time prediction."

## Types

| Type | Description | Preemptive? |
|------|-------------|-------------|
| **SJF (Non-preemptive)** | Once a process starts, it runs to completion | No |
| **SRTF (Shortest Remaining Time First)** | Preempts if a new process has shorter remaining time | Yes |

## SJF Example (Non-preemptive)

| Process | Arrival | Burst |
|---------|---------|-------|
| P1 | 0 | 6 |
| P2 | 2 | 8 |
| P3 | 3 | 7 |
| P4 | 5 | 3 |

### Gantt Chart

```
Time:  0     6  9     16      24
       |--P1--|P4|--P3--|--P2--|
       [0    6][6 9][9  16][16 24]
```

At t=0: Only P1 available → P1 runs (6 units)
At t=6: P2(8), P3(7), P4(3) available → P4 runs (shortest = 3)
At t=9: P2(8), P3(7) available → P3 runs (shortest = 7)
At t=16: P2(8) available → P2 runs

### Calculations

| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|---------|---------|-------|------------|------------|---------|
| P1 | 0 | 6 | 6 | 6 | 0 |
| P2 | 2 | 8 | 24 | 22 | 14 |
| P3 | 3 | 7 | 16 | 13 | 6 |
| P4 | 5 | 3 | 9 | 4 | 1 |

```
Average Waiting Time = (0 + 14 + 6 + 1) / 4 = 5.25
```

### FCFS Comparison

If FCFS (P1→P2→P3→P4):
```
Average Waiting Time = (0 + 4 + 11 + 17) / 4 = 8.0
```

SJF: 5.25 vs FCFS: 8.0 — SJF is 34% better!

## SRTF (Preemptive SJF)

If a new process arrives with a shorter remaining time, the current process is preempted.

| Process | Arrival | Burst |
|---------|---------|-------|
| P1 | 0 | 8 |
| P2 | 1 | 4 |
| P3 | 2 | 9 |
| P4 | 3 | 5 |

### Gantt Chart (SRTF)

```
Time:  0 1   5     10    18    26
       |P|P2-|---P4--|---P1--|---P3--|
       |1|[1 5][5  10][10  18][18  26]
```

- t=0: P1 arrives, runs (remaining: 8)
- t=1: P2 arrives (remaining: 4) < P1 (remaining: 7) → preempt P1, run P2
- t=5: P2 done. P1(7), P3(9), P4(5) → run P4 (shortest)
- t=10: P4 done. P1(7), P3(9) → run P1
- t=18: P1 done. P3(9) → run P3

### SRTF Calculations

| Process | Arrival | Burst | Completion | Turnaround | Waiting |
|---------|---------|-------|------------|------------|---------|
| P1 | 0 | 8 | 18 | 18 | 10 |
| P2 | 1 | 4 | 5 | 4 | 0 |
| P3 | 2 | 9 | 26 | 24 | 15 |
| P4 | 3 | 5 | 10 | 7 | 2 |

```
Average Waiting Time = (10 + 0 + 15 + 2) / 4 = 6.75
```

## Optimality Proof (SJF)

**Theorem:** SJF minimizes average waiting time among all non-preemptive algorithms.

**Proof sketch (exchange argument):**
1. Consider any schedule where a longer job runs before a shorter one
2. Swapping them reduces the waiting time of the shorter job by the burst time of the longer job
3. The longer job's waiting time increases by the burst time of the shorter job
4. Since short_burst < long_burst, the swap reduces total waiting time
5. By induction, the optimal schedule has jobs in shortest-first order

## Burst Time Prediction

Since burst times aren't known in advance, we use **exponential averaging**:

```
τ(n+1) = α · t(n) + (1 - α) · τ(n)

Where:
  τ(n+1) = predicted burst for next CPU burst
  t(n)    = actual burst of the nth burst
  τ(n)    = predicted burst for the nth burst
  α       = smoothing factor (0 ≤ α ≤ 1)
```

```python
def predict_burst(actual_bursts, alpha=0.5):
    """Predict burst times using exponential averaging"""
    predictions = [actual_bursts[0]]  # First prediction = first actual
    
    for i in range(1, len(actual_bursts)):
        predicted = alpha * actual_bursts[i-1] + (1 - alpha) * predictions[-1]
        predictions.append(predicted)
    
    return predictions

# Example
actual = [6, 4, 7, 3, 5]
predictions = predict_burst(actual, alpha=0.5)
# [6, 5.0, 4.5, 5.75, 4.375]
```

| α value | Behavior |
|---------|----------|
| α = 0 | τ(n+1) = τ(n) — never changes (stuck on initial guess) |
| α = 1 | τ(n+1) = t(n) — last actual burst (reactive) |
| α = 0.5 | Balanced (common choice) |

## Starvation Problem

SJF can **starve** long processes:

```
Short jobs keep arriving:
[Short 1] [Short 2] [Short 3] ... [Long job: 100ms]

The long job may never get CPU if short jobs keep coming!
```

### Solution: Aging

Increase priority of waiting processes over time:

```python
def effective_priority(base_priority, wait_time, aging_rate=0.1):
    return base_priority - (wait_time * aging_rate)
    # Lower number = higher priority
```

## Implementation

```python
def sjf_non_preemptive(processes):
    """SJF (non-preemptive)"""
    processes.sort(key=lambda x: x[1])  # Sort by arrival
    n = len(processes)
    completed = [False] * n
    current_time = 0
    results = []
    
    for _ in range(n):
        # Find shortest available job
        min_burst = float('inf')
        min_idx = -1
        for i in range(n):
            if not completed[i] and processes[i][1] <= current_time:
                if processes[i][2] < min_burst:
                    min_burst = processes[i][2]
                    min_idx = i
        
        if min_idx == -1:  # No process available, advance time
            current_time = min(p[1] for i, p in enumerate(processes) if not completed[i])
            continue
        
        pid, arrival, burst = processes[min_idx]
        waiting = current_time - arrival
        turnaround = waiting + burst
        
        results.append({
            'pid': pid, 'waiting': waiting, 'turnaround': turnaround
        })
        
        current_time += burst
        completed[min_idx] = True
    
    return results
```

## Interview Questions

### Beginner

**Q1: What is SJF scheduling?**  
A: SJF selects the process with the shortest CPU burst time. It can be preemptive (SRTF) or non-preemptive. It minimizes average waiting time but may starve long processes.

**Q2: Is SJF optimal?**  
A: Yes, SJF is provably optimal for minimizing average waiting time among non-preemptive algorithms. SRTF is optimal among all algorithms (preemptive and non-preemptive).

### Intermediate

**Q3: What is the difference between SJF and SRTF?**  
A: SJF is non-preemptive — once a process starts, it runs to completion. SRTF is preemptive — if a new process arrives with a shorter remaining time, it preempts the current process. SRTF has lower average waiting time but higher overhead.

**Q4: How do you predict burst times?**  
A: Use exponential averaging: τ(n+1) = α·t(n) + (1-α)·τ(n). The OS keeps a history of past bursts and predicts the next one. α=0.5 is common. The first burst is often estimated or assumed.

**Q5: What is the starvation problem in SJF?**  
A: If short processes keep arriving, a long process may never get the CPU. Its waiting time grows without bound. Solution: aging — gradually increase the priority of waiting processes.

### FAANG-Level

**Q6: Prove that SJF minimizes average waiting time.**  
A: Exchange argument: Consider an optimal schedule S that is not SJF. Then there exist adjacent jobs i, j where burst(i) > burst(j) but i runs before j. Swap i and j: j's waiting decreases by burst(i), i's waiting increases by burst(j). Net change = burst(j) - burst(i) < 0 (since burst(i) > burst(j)). So swapping improves the schedule, contradicting optimality of S. By induction, the optimal schedule must be SJF.

**Q7: How does the Linux CFS approximate SJF behavior?**  
A: CFS uses virtual runtime (vruntime). Processes that run less accumulate less vruntime and get priority. Short jobs (that sleep a lot) have low vruntime and get scheduled sooner, similar to SJF. Nice values adjust the rate of vruntime accumulation — a process with nice -20 accumulates vruntime slower, getting more CPU (approximating SJF for important processes).

**Q8: Design a scheduler that combines SJF optimality with fairness.**  
A: **Multilevel Feedback Queue with SJF within levels:** 1) MLFQ separates interactive (I/O-bound) and CPU-bound processes, 2) Within each queue, use SJF for optimal waiting time, 3) Aging prevents starvation in lower queues, 4) Processes that use their full quantum move to a lower queue (longer time quantum, lower priority), 5) Processes that voluntarily yield move to a higher queue (interactive behavior). This approximates SJF while preventing starvation and supporting interactive workloads.

## Common Mistakes

1. **Forgetting arrival times:** SJF with all-at-once arrival is trivial. With staggered arrivals, you must check which processes are available.
2. **Confusing SJF with SRTF:** SJF is non-preemptive, SRTF is preemptive. Results differ.
3. **Ignoring starvation:** SJF can starve long jobs. Always mention aging as a solution.
4. **Assuming burst times are known:** In practice, burst times are predicted. Mention exponential averaging.

## Summary

| Property | SJF (Non-preemptive) | SRTF (Preemptive) |
|----------|---------------------|-------------------|
| Preemption | No | Yes |
| Optimality | Optimal avg wait (non-preemptive) | Optimal avg wait (all algorithms) |
| Starvation | Yes (long jobs) | Yes (long jobs) |
| Burst knowledge | Required (predicted) | Required (predicted) |
| Overhead | Low | Higher (preemption checks) |

## Cross-References

- [FCFS](./fcfs.md) - Simpler alternative
- [Round Robin](./round-robin.md) - Fair alternative
- [Priority](./priority.md) - Related starvation issue
- [Multilevel Feedback](./multilevel-feedback.md) - Practical SJF approximation
- [Linux CFS](./linux-cfs.md) - How Linux approximates fairness
- [Metrics](./metrics.md) - Evaluating scheduling performance


## Cross References

- [FCFS](fcfs.md)
- [Priority Scheduling](priority.md)
- [Scheduling Metrics](metrics.md)
- [CPU Architecture](../../arch/cpu/README.md)
