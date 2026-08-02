# FCFS Disk Scheduling

## Overview

**First-Come First-Served (FCFS)** is the simplest disk scheduling algorithm. Requests are served in the exact order they arrive in the queue, with no reordering or optimization.

## Motivation

FCFS is the baseline algorithm — it's fair, simple, and requires no computation. It serves as a comparison point for more sophisticated algorithms. While it doesn't optimize seek time, it guarantees that no request will starve.

## Algorithm

```
1. Requests arrive and are added to a FIFO queue
2. Head moves to serve the first request in the queue
3. After serving, head moves to the next request
4. Repeat until queue is empty
```

## Detailed Example

```
Requests: 98, 183, 37, 122, 14, 124, 65, 67
Head starts at: 53
Disk size: 200 cylinders (0-199)

Head movement:
53 → 98  → 183 → 37  → 122 → 14  → 124 → 65  → 67
     +45  +85   -146  +85   -108  +110  -59   +2

Total movement = 45 + 85 + 146 + 85 + 108 + 110 + 59 + 2 = 640 cylinders
```

```
Cylinder Map:
0         50        100       150       200
|---------|---------|---------|---------|
    ▲   ▲       ▲       ▲   ▲       ▲
    │   │       │       │   │       │
   14  53→37   65→67   98  122→124  183
       start

Head path (arrows show direction changes):
53 ──► 98 ──► 183 ◄── 37 ──► 122 ◄── 14 ──► 124 ◄── 65 ──► 67

Many direction reversals! This is the problem with FCFS.
```

## Simulation Code

```python
def fcfs(requests, head):
    total_movement = 0
    order = []
    
    for request in requests:
        total_movement += abs(request - head)
        order.append(request)
        head = request
    
    return order, total_movement

# Example
requests = [98, 183, 37, 122, 14, 124, 65, 67]
head = 53

order, movement = fcfs(requests, head)
print(f"Service order: {order}")
print(f"Total head movement: {movement} cylinders")

# Output:
# Service order: [98, 183, 37, 122, 14, 124, 65, 67]
# Total head movement: 640 cylinders
```

## Analysis

| Metric | Value |
|--------|-------|
| Fairness | ✅ Perfect — FIFO order |
| Starvation | ✅ None — every request served |
| Seek optimization | ❌ None — ignores head position |
| Direction changes | Many — random jumps |
| Throughput | Low — poor locality |
| Implementation | Trivial |

### When FCFS Works Well

- **Light load**: Few requests, so reordering provides little benefit
- **Uniform distribution**: Requests spread evenly, no pattern to exploit
- **Fairness critical**: When response time variance matters more than throughput

### When FCFS Fails

- **Heavy load**: Queue builds up, random movements waste seek time
- **Locality**: If requests cluster in nearby cylinders, FCFS wastes the opportunity
- **Mixed workload**: Sequential + random requests get interleaved randomly

## Comparison with Other Algorithms

```
Same example: Requests [98, 183, 37, 122, 14, 124, 65, 67], Head at 53

FCFS:  53→98→183→37→122→14→124→65→67    = 640 cylinders
SSTF:  53→65→67→37→14→98→122→124→183    = 236 cylinders
SCAN:  53→37→14→0→65→67→98→122→124→183  = 236 cylinders (to edge)
LOOK:  53→37→14→65→67→98→122→124→183    = 226 cylinders

FCFS is 2.7x worse than SSTF in this example!
```

## Real-World Relevance

FCFS is rarely used as a standalone disk scheduler in production, but:
- It's the default behavior when no scheduler is configured
- It's used as a component within more complex schedulers
- It's the baseline for comparison in academic studies
- Linux's `none` scheduler (for NVMe) is close to FCFS with merging

```bash
# On NVMe drives, Linux often uses "none" scheduler
cat /sys/block/nvme0n1/queue/scheduler
# [none] mq-deadline kyber bfq

# NVMe doesn't need seek optimization, so FCFS-like behavior is fine
```

## Interview Questions

### Beginner

**Q: How does FCFS disk scheduling work?**
A: FCFS serves requests in the order they arrive. The head moves to the first request, serves it, then moves to the next, and so on. It's like a queue at a bank — first in, first served. No optimization is done based on head position.

**Q: What are the advantages and disadvantages of FCFS?**
A: Advantages: Simple, fair (no starvation), easy to implement. Disadvantages: Poor performance under heavy load, no seek optimization, many head direction changes, low throughput compared to SCAN or SSTF.

### Intermediate

**Q: In what scenario does FCFS outperform SSTF?**
A: When requests are uniformly distributed and the load is light, FCFS may perform comparably to SSTF. FCFS also outperforms SSTF when SSTF causes starvation — if there's a continuous stream of requests near the head, SSTF will starve distant requests while FCFS will eventually serve them.

**Q: Why is FCFS rarely used as a production disk scheduler?**
A: Under heavy load, FCFS causes excessive seek time due to random head movement. Real workloads often have locality (related requests arrive close together), and FCFS doesn't exploit this. More sophisticated algorithms (SCAN, deadline, CFQ) provide significantly better throughput while maintaining reasonable fairness.

### FAANG-Level

**Q: You're designing an I/O scheduler for a database server. The DBA argues that FCFS is best because it's "fair." How would you respond?**

A: Fairness in FCFS means FIFO ordering, but this doesn't translate to good user experience. Consider:

1. **Latency**: FCFS can result in long waits for nearby requests if a distant request is ahead in the queue. SCAN/LOOK would serve nearby requests quickly.

2. **Throughput**: FCFS causes random head movement, reducing IOPS by 2-3x compared to SCAN under heavy load. This means ALL requests take longer.

3. **True fairness**: Fairness should mean proportional service time, not FIFO order. A deadline-based scheduler provides per-request deadlines, ensuring every request is served within a bounded time — this is true fairness.

4. **Better approach**: Use BFQ or mq-deadline with per-process weights. The database gets higher priority (lower latency), while background tasks get fair bandwidth allocation. This provides both better performance AND better fairness.

```
FCFS "fairness":
  Request A (track 100): arrives first, served first
  Request B (track 10): arrives second, served second
  Head at track 90 → moves to 100 → moves to 10
  Both get "fair" FIFO order but terrible seek time

Deadline scheduler fairness:
  Request A (track 100): deadline = now + 5ms
  Request B (track 10): deadline = now + 5ms
  Head at track 90 → serves B (track 10) then A (track 100)
  Both served within deadline, lower total seek
```

## Common Mistakes

1. **Confusing FCFS fairness with good performance**: FCFS is fair in ordering but unfair in service time (nearby requests get faster service than distant ones in other algorithms).
2. **Forgetting about request merging**: Even FCFS schedulers merge adjacent requests. Pure FCFS without merging is almost never used.
3. **Ignoring rotational latency**: FCFS optimizes neither seek nor rotation. Modern schedulers (deadline) consider both.

## Summary

| Property | FCFS |
|----------|------|
| Strategy | Serve in arrival order |
| Fairness | Perfect (FIFO) |
| Starvation | None |
| Seek optimization | None |
| Throughput | Low |
| Implementation | Trivial |
| Best for | Light load, fairness-critical |
| Worst for | Heavy load, mixed workloads |

## Cross-References

- [Disk Scheduling Overview](disk-scheduling.md) — Comparison of all algorithms
- [SSTF](disk-sstf.md) — The next step up from FCFS
- [SCAN](disk-scan.md) — The elevator algorithm
- [LOOK](disk-look.md) — Optimized SCAN
