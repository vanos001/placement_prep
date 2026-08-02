# SSTF Disk Scheduling

## Overview

**Shortest Seek Time First (SSTF)** selects the request that requires the least head movement from the current position. It's a greedy algorithm that minimizes immediate seek time at each step.

## Motivation

FCFS wastes seek time by serving requests in arrival order regardless of head position. SSTF addresses this by always choosing the closest pending request, which intuitively minimizes total seek time.

## Algorithm

```
1. At each step, find the pending request closest to the current head position
2. Move the head to that request and serve it
3. Repeat until all requests are served
```

## Detailed Example

```
Requests: 98, 183, 37, 122, 14, 124, 65, 67
Head starts at: 53

Step-by-step:
Position 53: Closest = 65 (distance 12) vs 37 (distance 16) → serve 65
Position 65: Closest = 67 (distance 2) → serve 67
Position 67: Closest = 37 (distance 30) vs 98 (distance 31) → serve 37
Position 37: Closest = 14 (distance 23) → serve 14
Position 14: Closest = 98 (distance 84) → serve 98
Position 98: Closest = 122 (distance 24) → serve 122
Position 122: Closest = 124 (distance 2) → serve 124
Position 124: Closest = 183 (distance 59) → serve 183

Service order: 65, 67, 37, 14, 98, 122, 124, 183
Total movement = 12 + 2 + 30 + 23 + 84 + 24 + 2 + 59 = 236 cylinders
```

```
Cylinder Map:
0         50        100       150       200
|---------|---------|---------|---------|
     ▲▲  ▲▲▲         ▲▲▲▲       ▲
     ││  │││         ││││       │
    14 37 53 65 67   98 122 124  183
       start ▲
             │
     Path: 53→65→67→37→14→98→122→124→183
     Head moves toward nearest request each time
```

## Simulation Code

```python
def sstf(requests, head):
    total_movement = 0
    order = []
    remaining = list(requests)
    
    while remaining:
        # Find closest request
        closest = min(remaining, key=lambda r: abs(r - head))
        distance = abs(closest - head)
        
        total_movement += distance
        order.append(closest)
        head = closest
        remaining.remove(closest)
    
    return order, total_movement

# Example
requests = [98, 183, 37, 122, 14, 124, 65, 67]
head = 53

order, movement = sstf(requests, head)
print(f"Service order: {order}")
print(f"Total head movement: {movement} cylinders")

# Output:
# Service order: [65, 67, 37, 14, 98, 122, 124, 183]
# Total head movement: 236 cylinders
```

## Comparison with FCFS

```
Same example: Requests [98, 183, 37, 122, 14, 124, 65, 67], Head at 53

FCFS:  53→98→183→37→122→14→124→65→67    = 640 cylinders
SSTF:  53→65→67→37→14→98→122→124→183    = 236 cylinders

SSTF is 2.7x better than FCFS in total seek time!
```

## The Starvation Problem

SSTF's major flaw is that it can cause **starvation**. If requests keep arriving near the current head position, distant requests will never be served.

```
Scenario: Head at track 50, continuous stream of requests near track 50

Time 1: Queue = [200, 51, 52]  → SSTF picks 51
Time 2: Queue = [200, 52, 53]  → SSTF picks 52
Time 3: Queue = [200, 53, 54]  → SSTF picks 53
...forever... request at track 200 NEVER served!

This is starvation — SSTF can indefinitely delay distant requests.
```

```
Visualization of starvation:

Track:  0        50        100       150       200
        |---------|---------|---------|---------|
                          ▲
                    Head stays here
                    (always finds something closer)
                              │
                              ▼
        Request at 200 waits FOREVER
```

## Analysis

| Metric | SSTF |
|--------|------|
| Fairness | ❌ Unfair — distant requests starve |
| Starvation | ⚠️ Yes — major problem |
| Seek optimization | ✅ Good — greedy minimization |
| Throughput | High — better than FCFS |
| Implementation | Simple — O(n) per request |
| Response time variance | High — nearby requests get fast service |

### Why SSTF Is Not Optimal

SSTF is greedy — it minimizes seek at each step but not globally. Consider:

```
Requests: 10, 20, 100
Head at: 50

SSTF: 50→20→10→100  = 30 + 10 + 90 = 130
Optimal: 50→20→10→100 or 50→100→20→10 = 90 + 80 = 170 (worse)
Actually SSTF is optimal here!

But consider: 10, 20, 30, 200
Head at: 50

SSTF: 50→30→20→10→200  = 20+10+10+190 = 230
Better: 50→10→20→30→200 = 40+10+10+170 = 230 (same here)

SSTF is often near-optimal but can be suboptimal in edge cases.
```

## Real-World Relevance

SSTF is rarely used directly because of starvation, but the concept appears in:
- **I/O scheduler request selection**: Linux's deadline scheduler uses closest-request selection as a component
- **Network routing**: Shortest-path routing has similar starvation issues
- **Disk firmware**: Some disk firmware uses SSTF-like logic internally

```bash
# Linux doesn't have a pure SSTF scheduler, but mq-deadline
# uses proximity as a factor in request ordering

# The elevator (SCAN) concept was invented specifically to fix SSTF's starvation
```

## Interview Questions

### Beginner

**Q: How does SSTF differ from FCFS?**
A: FCFS serves requests in arrival order; SSTF serves the closest request first. SSTF reduces total seek time by always choosing the nearest pending request. However, SSTF can cause starvation of distant requests, while FCFS is always fair.

**Q: Can SSTF starve requests? Give an example.**
A: Yes. If the head is at track 50 and requests keep arriving at tracks 48-52, a request at track 200 will never be served because there's always a closer request. The distant request starves indefinitely.

### Intermediate

**Q: Is SSTF optimal? Why or why not?**
A: SSTF is a greedy algorithm — it minimizes seek time at each step but not necessarily globally. It's often near-optimal but can be suboptimal when the optimal path requires temporarily moving away from the nearest request. The true optimal solution is the Traveling Salesman Problem (NP-hard), so SSTF is a practical approximation.

**Q: How would you modify SSTF to prevent starvation?**
A: Several approaches:
1. **Aging**: Increase the priority of requests as they wait. After a threshold, force service regardless of distance.
2. **SCAN with SSTF**: Use SSTF within a single sweep direction (like LOOK).
3. **Deadline**: Assign deadlines to requests and serve the one closest to its deadline.
4. **Hybrid**: Use SSTF for recent requests but periodically insert a "fairness sweep" that serves the oldest request.

### FAANG-Level

**Q: SSTF is a greedy algorithm. Can you prove that SSTF's total seek time is at most twice the optimal?**

A: This is actually **not** true in general. SSTF can perform arbitrarily worse than optimal in pathological cases:

```
Requests: 0, 1000
Head at: 500

SSTF: 500→0→1000 = 500 + 1000 = 1500
Optimal: 500→0→1000 or 500→1000→0 = 1500 (same)

But with more requests, SSTF can be suboptimal.
However, SSTF IS a 2-approximation for the metric TSP on a line
(1D), because the line metric satisfies the triangle inequality.

Proof sketch for 1D:
- Let OPT = optimal total movement
- SSTF always moves to the nearest unvisited point
- On a line, the nearest point is always within the convex hull
- Each SSTF move is ≤ corresponding OPT move (by triangle inequality)
- Total SSTF ≤ 2 × OPT

This is because on a line, the optimal tour visits points in sorted order
(except possibly wrapping around), and SSTF's greedy choice is always
within the span of the remaining points.
```

In practice, disk scheduling is 1D (cylinder numbers), so SSTF provides reasonable approximation guarantees. However, starvation is the real issue, not optimality.

## Common Mistakes

1. **Confusing "closest" with "next in sequence"**: SSTF finds the closest by absolute distance, not by sequential order.
2. **Ignoring starvation**: SSTF's theoretical performance is good, but starvation makes it impractical for production systems.
3. **Not considering rotation**: SSTF minimizes seek time but ignores rotational latency. Two requests at the same cylinder may have different rotational delays.
4. **Assuming SSTF is always better than FCFS**: Under light load with few requests, the difference is negligible. FCFS's simplicity may be preferable.

## Summary

| Property | SSTF |
|----------|------|
| Strategy | Serve closest request first |
| Fairness | Unfair (starvation risk) |
| Starvation | Yes — distant requests can starve |
| Seek optimization | Good (greedy) |
| Throughput | Better than FCFS |
| Implementation | Simple (find min distance) |
| Best for | Light load, bounded queue |
| Worst for | Heavy load with mixed distances |

## Cross-References

- [Disk Scheduling Overview](disk-scheduling.md) — Comparison of all algorithms
- [FCFS](disk-fcfs.md) — Baseline comparison
- [SCAN](disk-scan.md) — SCAN fixes SSTF's starvation problem
- [LOOK](disk-look.md) — Optimized SCAN variant
