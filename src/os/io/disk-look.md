# LOOK and C-LOOK Disk Scheduling

## Overview

**LOOK** and **C-LOOK** are optimized versions of SCAN and C-SCAN respectively. Instead of moving the head to the physical end of the disk, they only go as far as the last request in the current direction. This eliminates unnecessary movement and improves performance.

## Motivation

SCAN and C-SCAN waste seek time by moving to the physical edge of the disk even when there are no requests there. In practice, the disk edge is rarely the location of the last request. LOOK/C-LOOK fix this by "looking" to see if there are more requests before deciding to reverse or jump back.

## LOOK Algorithm

```
1. Head moves in one direction, servicing all requests in its path
2. When no more requests exist in the current direction, reverse
3. Service all requests in the new direction
4. Repeat until all requests are served
```

### Example

```
Requests: 98, 183, 37, 122, 14, 124, 65, 67
Head starts at: 53, moving toward higher cylinders

LOOK:
1. Moving UP: service 65, 67, 98, 122, 124, 183
2. No more requests above 183 → reverse
3. Moving DOWN: service 37, 14

Service order: 65, 67, 98, 122, 124, 183, 37, 14
Total movement = (183-53) + (183-14) = 130 + 169 = 299 cylinders

Compare with SCAN:
SCAN: 53→65→67→98→122→124→183→199→37→14 = 331 cylinders
LOOK: 53→65→67→98→122→124→183→37→14      = 299 cylinders

LOOK saves 32 cylinders by not going to 199!
```

```
Cylinder Map:
0         50        100       150       200
|---------|---------|---------|---------|
 ▲        ▲▲▲ ▲▲▲▲▲▲▲▲▲▲▲▲▲
 │        │││ │││││││││││││
14       37 53 65 67    98 122 124   183
         start ▲                     ▲
               │                     │
     ──── UP ──────────────────►     │
                         ◄── DOWN ───┘

LOOK stops at 183 (last request), not 199 (disk edge).
```

## C-LOOK Algorithm

```
1. Head moves in one direction, servicing all requests in its path
2. When no more requests in current direction, jump to the lowest request
3. Continue sweeping in the same direction
4. Repeat
```

### Example

```
Requests: 98, 183, 37, 122, 14, 124, 65, 67
Head starts at: 53, moving toward higher cylinders

C-LOOK:
1. Moving UP: service 65, 67, 98, 122, 124, 183
2. No more requests above 183 → jump to lowest (14)
3. Continue UP: service 14, 37

Service order: 65, 67, 98, 122, 124, 183, 14, 37
Total movement = (183-53) + (183-14) + (37-14) = 130 + 169 + 23 = 322 cylinders

Compare with C-SCAN:
C-SCAN: 53→65→67→98→122→124→183→199→0→14→37 = 382 cylinders
C-LOOK: 53→65→67→98→122→124→183→14→37        = 322 cylinders

C-LOOK saves 60 cylinders by not going to 199 and 0!
```

```
Cylinder Map:
0         50        100       150       200
|---------|---------|---------|---------|
▲         ▲▲▲ ▲▲▲▲▲▲▲▲▲▲▲▲▲
│         │││ │││││││││││││
14       37 53 65 67    98 122 124   183
 ▲       start ▲                      ▲
 │             │                      │
 │   ──── UP ──────────────────────►  │
 └──────────── (jump back) ◄──────────┘

C-LOOK jumps from 183 directly to 14, skipping 199 and 0.
```

## Simulation Code

```python
def look(requests, head, direction='up'):
    total_movement = 0
    order = []
    sorted_reqs = sorted(requests)
    
    right = [r for r in sorted_reqs if r >= head]
    left = [r for r in sorted_reqs if r < head]
    
    if direction == 'up':
        for r in right:
            total_movement += abs(r - head)
            order.append(r)
            head = r
        for r in reversed(left):
            total_movement += abs(r - head)
            order.append(r)
            head = r
    else:
        for r in reversed(left):
            total_movement += abs(r - head)
            order.append(r)
            head = r
        for r in right:
            total_movement += abs(r - head)
            order.append(r)
            head = r
    
    return order, total_movement

def clook(requests, head):
    total_movement = 0
    order = []
    sorted_reqs = sorted(requests)
    
    right = [r for r in sorted_reqs if r >= head]
    left = [r for r in sorted_reqs if r < head]
    
    for r in right:
        total_movement += abs(r - head)
        order.append(r)
        head = r
    
    if left:
        # Jump to lowest request (not to 0)
        total_movement += abs(head - left[0])
        head = left[0]
        for r in left:
            total_movement += abs(r - head)
            order.append(r)
            head = r
    
    return order, total_movement

# Examples
requests = [98, 183, 37, 122, 14, 124, 65, 67]
head = 53

print("LOOK:", look(requests, head))
print("C-LOOK:", clook(requests, head))

# LOOK: ([65, 67, 98, 122, 124, 183, 37, 14], 299)
# C-LOOK: ([65, 67, 98, 122, 124, 183, 14, 37], 322)
```

## Complete Comparison

```
Requests: [98, 183, 37, 122, 14, 124, 65, 67], Head at 53

Algorithm  Order                                    Movement  Fairness
─────────  ───────────────────────────────────────  ────────  ────────
FCFS       98, 183, 37, 122, 14, 124, 65, 67       640       Fair
SSTF       65, 67, 37, 14, 98, 122, 124, 183       236       Unfair
SCAN       65, 67, 98, 122, 124, 183, 37, 14       331       Good
C-SCAN     65, 67, 98, 122, 124, 183, 14, 37       382       Best
LOOK       65, 67, 98, 122, 124, 183, 37, 14       299       Good
C-LOOK     65, 67, 98, 122, 124, 183, 14, 37       322       Best

LOOK is the best overall for this example!
```

## Why LOOK Is Almost Always Preferred Over SCAN

```
SCAN always goes to disk edge:
  Head at 50, last request at 100, disk has 1000 cylinders
  SCAN: 50 → 100 → 1000 → 0 → ... (wastes 900 cylinders!)

LOOK stops at last request:
  LOOK: 50 → 100 → ... (stops at 100, reverses)

The savings can be enormous when the disk is large but
requests are clustered in a small region.
```

## Real-World Relevance

### Linux I/O Schedulers

```bash
# Linux's mq-deadline scheduler uses LOOK-like behavior
# Requests are sorted by sector number (LOOK ordering)
# The scheduler doesn't force movement to disk edges

# The "elevator" in Linux is really a LOOK variant:
# - Requests sorted by sector
# - Head moves in one direction
# - Reverses when no more requests in current direction
# - Merges adjacent requests

# View I/O scheduler behavior
echo 1 | sudo tee /sys/block/sda/queue/iosched/writes_starved
```

### SSD Considerations

```bash
# For SSDs, LOOK/C-LOOK provide minimal benefit over SCAN
# because there's no physical head movement
# But request merging (which LOOK does) still helps

# NVMe drives often use "none" scheduler (no LOOK at all)
cat /sys/block/nvme0n1/queue/scheduler
# [none]
```

## Interview Questions

### Beginner

**Q: What is the difference between SCAN and LOOK?**
A: SCAN moves the head to the physical end of the disk before reversing. LOOK only moves to the last request in the current direction, then reverses. LOOK avoids unnecessary movement to empty disk regions, making it more efficient.

**Q: When would LOOK and SCAN produce the same result?**
A: When the last request in each direction happens to be at the disk edge (cylinder 0 or max). In practice, this is rare, so LOOK almost always outperforms SCAN.

### Intermediate

**Q: Compare LOOK and C-LOOK. Which provides better fairness?**
A: C-LOOK provides better fairness (uniform service times) because it always scans in the same direction. LOOK has the same unfairness as SCAN — middle cylinders get served more often. However, LOOK has lower total seek time than C-LOOK because C-LOOK includes a "jump back" from the highest to lowest request.

**Q: Why is LOOK preferred over SSTF despite SSTF having lower total seek time in many cases?**
A: SSTF can starve distant requests. LOOK provides SCAN-like fairness guarantees (no starvation) while being nearly as efficient as SSTF. The slight increase in total seek time is worth the guarantee that every request will be served.

### FAANG-Level

**Q: Design a disk scheduler that dynamically chooses between LOOK and C-LOOK based on the workload.**

A:

```
Adaptive LOOK/C-LOOK Scheduler:

Observation:
- LOOK is better when requests are clustered (less jump-back overhead)
- C-LOOK is better when requests are spread uniformly (better fairness)

Algorithm:
1. Track request distribution:
   - Maintain a histogram of request positions over last N requests
   - Calculate coefficient of variation (CV) of positions

2. Decision logic:
   if (CV > threshold_high):  # Clustered
       use LOOK  (exploit locality, bidirectional is fine)
   elif (CV < threshold_low): # Uniform
       use C-LOOK (uniform service matters more)
   else:
       use LOOK  (default, lower overhead)

3. Dynamic adjustment:
   - Monitor average wait time per cylinder region
   - If edge cylinders have significantly worse wait times:
       switch to C-LOOK
   - If middle cylinders have similar wait times to edges:
       stay with LOOK (more efficient)

4. Implementation:
   ┌─────────────────────────────────────────┐
   │          Request Stream                  │
   │              │                           │
   │              ▼                           │
   │    ┌──────────────────┐                  │
   │    │ Distribution     │                  │
   │    │ Analyzer         │                  │
   │    │ (histogram, CV)  │                  │
   │    └────────┬─────────┘                  │
   │             │                            │
   │      ┌──────┴──────┐                     │
   │      ▼             ▼                     │
   │   LOOK          C-LOOK                   │
   │   (clustered)   (uniform)                │
   └─────────────────────────────────────────┘

5. Real-world mapping:
   - Linux's BFQ scheduler uses heuristics to detect sequential vs random
   - Sequential → batch (C-LOOK-like)
   - Random → priority (LOOK-like)
   - This is essentially the same idea
```

**Q: Given a disk with 10,000 cylinders, head at position 2000, and requests at [1500, 2500, 3000, 8000, 9000, 500], calculate total head movement for LOOK and C-LOOK (initial direction: up). Which would you choose and why?**

A:

```
LOOK (direction: up):
Requests: 1500, 2500, 3000, 8000, 9000, 500
Sorted right (>= 2000): 2500, 3000, 8000, 9000
Sorted left (< 2000): 1500, 500

Service order: 2500, 3000, 8000, 9000, 1500, 500
Movement:
  2000→2500 = 500
  2500→3000 = 500
  3000→8000 = 5000
  8000→9000 = 1000
  9000→1500 = 7500
  1500→500  = 1000
  Total = 15,500

C-LOOK (direction: up):
Service order: 2500, 3000, 8000, 9000, 500, 1500
Movement:
  2000→2500 = 500
  2500→3000 = 500
  3000→8000 = 5000
  8000→9000 = 1000
  9000→500  = 8500 (jump back)
  500→1500  = 1000
  Total = 16,500

LOOK: 15,500 cylinders
C-LOOK: 16,500 cylinders

Choose LOOK because:
1. Lower total movement (15,500 vs 16,500)
2. Requests are clustered in two groups (500-1500 and 2500-9000)
3. LOOK's bidirectional sweeping handles this well
4. C-LOOK's uniform service isn't needed here (only 6 requests)

If the load were heavier and requests more uniform, C-LOOK would be preferable.
```

## Common Mistakes

1. **Confusing LOOK with SCAN**: LOOK doesn't go to disk edge; SCAN does. This is the key difference.
2. **Forgetting LOOK is bidirectional**: LOOK reverses at the last request, not at the disk edge. Don't assume it always goes to the edge.
3. **Assuming C-LOOK always outperforms LOOK**: For clustered workloads, LOOK is better. C-LOOK is better for uniform distributions.
4. **Not considering the jump cost in C-LOOK**: The jump from highest to lowest request isn't free. If the requests are far apart, this jump can be expensive.
5. **Ignoring the initial direction**: The starting direction affects which requests are served first and total movement. Some implementations choose the direction with more pending requests.

## Summary

| Property | LOOK | C-LOOK |
|----------|------|--------|
| Strategy | Reverse at last request | Jump to lowest, same direction |
| Based on | SCAN | C-SCAN |
| Disk edge movement | No | No |
| Service direction | Bidirectional | Unidirectional |
| Fairness | Good | Excellent (uniform) |
| Total movement | Lower than SCAN | Lower than C-SCAN |
| Best for | Clustered workloads | Uniform workloads |
| Implementation | Moderate | Moderate |

## Cross-References

- [Disk Scheduling Overview](disk-scheduling.md) — Comparison of all algorithms
- [SCAN](disk-scan.md) — LOOK is the optimized SCAN
- [C-SCAN](disk-cscan.md) — C-LOOK is the optimized C-SCAN
- [SSTF](disk-sstf.md) — Greedy alternative
- [FCFS](disk-fcfs.md) — Baseline comparison


## Cross References

- [SCAN](disk-scan.md)
- [C-SCAN](disk-cscan.md)
- [Disk Scheduling Overview](disk-scheduling.md)
