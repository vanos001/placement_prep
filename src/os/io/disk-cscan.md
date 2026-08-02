# C-SCAN Disk Scheduling

## Overview

**Circular SCAN (C-SCAN)** is a variant of the SCAN algorithm that provides more uniform wait times. Instead of reversing direction at the end of the disk, the head returns to the beginning without servicing any requests, then sweeps forward again.

## Motivation

SCAN has an unfairness problem: cylinders in the middle of the disk get visited twice per cycle (once going up, once going down), while edge cylinders get visited only once. C-SCAN fixes this by always scanning in the same direction, treating the cylinders as a circular list.

## Algorithm

```
1. Head moves in one direction (e.g., toward higher cylinders)
2. Service all requests in the current direction
3. When the head reaches the end, jump back to cylinder 0 (without servicing)
4. Continue sweeping in the same direction
5. Repeat
```

## Detailed Example

```
Requests: 98, 183, 37, 122, 14, 124, 65, 67
Head starts at: 53, moving toward higher cylinders
Disk size: 200 cylinders (0-199)

Step-by-step:
1. Moving UP: service requests at 65, 67, 98, 122, 124, 183
2. Reach end (199), jump to 0 (no service during jump)
3. Continue UP: service requests at 14, 37

Service order: 65, 67, 98, 122, 124, 183, 14, 37
Total movement = (199-53) + (199-0) + (37-0) = 146 + 199 + 37 = 382 cylinders
```

```
Cylinder Map:
0         50        100       150       200
|---------|---------|---------|---------|
▲         ▲▲▲ ▲▲▲▲▲▲▲▲▲▲▲▲▲           ▲
│         │││ │││││││││││││           │
14       37 53 65 67    98 122 124   183  199
 ▲       start ▲                      ▲    ▲
 │             │                      │    │
 │   ──── UP ──────────────────►   ───┘    │
 └── (jump back, no service) ──────────────┘

Always moving RIGHT (upward), wrapping around at the edge.
```

## Simulation Code

```python
def cscan(requests, head, disk_size=200):
    total_movement = 0
    order = []
    
    sorted_reqs = sorted(requests)
    
    # Split into right (>= head) and left (< head)
    right = [r for r in sorted_reqs if r >= head]
    left = [r for r in sorted_reqs if r < head]
    
    # Service right requests first
    for r in right:
        total_movement += abs(r - head)
        order.append(r)
        head = r
    
    # Jump to end, then to beginning
    if left:  # Only if there are requests on the left
        total_movement += abs(disk_size - 1 - head)  # Go to end
        total_movement += disk_size - 1               # Jump to 0
        head = 0
        
        # Service left requests
        for r in left:
            total_movement += abs(r - head)
            order.append(r)
            head = r
    
    return order, total_movement

# Example
requests = [98, 183, 37, 122, 14, 124, 65, 67]
head = 53

order, movement = cscan(requests, head)
print(f"Service order: {order}")
print(f"Total head movement: {movement} cylinders")

# Output:
# Service order: [65, 67, 98, 122, 124, 183, 14, 37]
# Total head movement: 382 cylinders
```

## SCAN vs C-SCAN Comparison

```
Same example: Requests [98, 183, 37, 122, 14, 124, 65, 67], Head at 53

SCAN:   53→65→67→98→122→124→183→37→14    = 331 cylinders
C-SCAN: 53→65→67→98→122→124→183→14→37    = 382 cylinders

C-SCAN has more total movement, but more uniform service times.
```

### Service Time Uniformity

```
SCAN service frequency:
Track:  0     50    100    150    200
        |─────|─────|─────|─────|
Freq:   1     2     2      2     1   (middle gets 2x)

C-SCAN service frequency:
Track:  0     50    100    150    200
        |─────|─────|─────|─────|
Freq:   1     1     1      1     1   (uniform!)

C-SCAN treats the disk as a circular list, giving equal service to all regions.
```

## When C-SCAN Is Better Than SCAN

```
Scenario: Heavy load with requests uniformly distributed

SCAN:
- Middle cylinders: avg wait = T/2 (served every half-cycle)
- Edge cylinders: avg wait = T (served every full-cycle)
- Wait time variance: HIGH

C-SCAN:
- All cylinders: avg wait ≈ T (served every full-cycle)
- Wait time variance: LOW
- More predictable latency

For databases and real-time systems, C-SCAN's uniform latency is preferable.
```

## C-SCAN vs C-LOOK

C-SCAN always moves to the physical end of the disk before jumping back. **C-LOOK** optimizes this by only going to the last request in the current direction:

```
C-SCAN: 53→65→67→98→122→124→183→199→0→14→37
C-LOOK: 53→65→67→98→122→124→183→14→37

C-LOOK saves the movement to 199 and from 0, resulting in less total movement.
C-LOOK is almost always preferred over C-SCAN.
```

## Interview Questions

### Beginner

**Q: What is the difference between SCAN and C-SCAN?**
A: SCAN reverses direction at the end of the disk and services requests on the way back. C-SCAN returns to the beginning without servicing and sweeps forward again. C-SCAN provides more uniform wait times because every cylinder is visited once per cycle, while SCAN visits middle cylinders twice.

**Q: Why does C-SCAN have more total head movement than SCAN?**
A: C-SCAN includes the "return trip" from the end to the beginning without servicing. This adds up to `disk_size - 1` extra movement. SCAN avoids this by servicing on the return trip.

### Intermediate

**Q: In what scenarios would you prefer C-SCAN over SCAN?**
A: When uniform response time is important — for example, in a database server where all queries should have similar latency. C-SCAN ensures that cylinders at the edges don't get worse service than those in the middle. Also useful when the disk load is heavy and requests are uniformly distributed across cylinders.

**Q: How does C-SCAN relate to a circular buffer?**
A: Both treat the data structure as circular. C-SCAN treats the cylinder range as a circular list (wrapping from max back to 0), just as a circular buffer wraps from the end back to the beginning. The head always moves forward, wrapping around at the edges.

### FAANG-Level

**Q: Prove that C-SCAN provides more uniform service times than SCAN.**

A:

Let the disk have cylinders 0 to D-1. Let the head sweep at constant speed v.

**SCAN analysis:**
- A full cycle is: 0 → D-1 → 0 (or D-1 → 0 → D-1)
- Time for full cycle: 2D/v
- Cylinder at position p (0 < p < D-1):
  - Visited going up: time = p/v
  - Visited going down: time = (2D - p)/v
  - Service interval: min(p, D-p)/v
- Cylinder at position D/2 (middle): service interval = D/(2v)
- Cylinder at position 0 or D-1: service interval = D/v
- **Ratio of best to worst: 2:1**

**C-SCAN analysis:**
- A full cycle is: 0 → D-1 → jump → 0 → D-1
- Time for full cycle: 2D/v (including return jump)
- Every cylinder at position p: service interval = D/v
- **Ratio of best to worst: 1:1**

C-SCAN provides perfectly uniform service intervals, while SCAN provides 2x better service to middle cylinders.

```
Service interval as function of cylinder position:

Interval
    ▲
  D │── SCAN (edges) ──────────────
    │        ╲                ╱
D/2 │── SCAN (middle) ─────
    │
    │── C-SCAN (all) ──────────────
    └──────────────────────────────► Cylinder
      0         D/2           D-1

SCAN: V-shaped (middle gets 2x better)
C-SCAN: Flat (uniform)
```

**Q: A storage system uses C-SCAN. The disk has 10,000 cylinders and the head moves at 1ms per cylinder. Requests arrive at 100 per second, uniformly distributed. What is the average wait time for a request?**

A:
- Full C-SCAN cycle: 10,000 cylinders × 1ms = 10,000ms = 10s
- Requests per cycle: 100/s × 10s = 1000 requests
- Average wait time: half a cycle = 5,000ms = 5s

With SCAN, edge requests would wait up to 10s while middle requests wait ~2.5s. C-SCAN gives all requests ~5s average wait.

To reduce wait time: decrease cycle time (faster disk, fewer cylinders) or reduce load.

## Common Mistakes

1. **Forgetting the return jump**: C-SCAN's return from end to beginning adds `disk_size - 1` movement. Don't forget to include this in calculations.
2. **Confusing C-SCAN with C-LOOK**: C-SCAN goes to the physical disk end; C-LOOK only goes to the last request. C-LOOK is almost always better.
3. **Assuming C-SCAN is always better than SCAN**: For workloads skewed toward the middle of the disk, SCAN's bidirectional sweeping may be more efficient.
4. **Not considering the jump cost**: In real systems, the "jump" from end to beginning isn't free — the head must physically move back. Some implementations optimize by not moving to the exact edge.

## Summary

| Property | C-SCAN |
|----------|--------|
| Strategy | Sweep one direction, jump back, repeat |
| Fairness | Excellent (uniform service) |
| Starvation | No |
| Seek optimization | Good |
| Service uniformity | Perfect (all cylinders equal) |
| Total movement | Higher than SCAN (includes return jump) |
| Implementation | Moderate |
| Best for | Heavy load, uniform distribution, fairness-critical |
| Worst for | Light load, clustered requests |

## Cross-References

- [Disk Scheduling Overview](disk-scheduling.md) — Comparison of all algorithms
- [SCAN](disk-scan.md) — Bidirectional variant
- [C-LOOK](disk-look.md) — Optimized C-SCAN
- [LOOK](disk-look.md) — Optimized SCAN (related)


## Cross References

- [SCAN](../os/io/disk-scan.md)
- [LOOK](../os/io/disk-look.md)
- [Disk Scheduling Overview](../os/io/disk-scheduling.md)
- [HDD](../storage/hdd.md)
