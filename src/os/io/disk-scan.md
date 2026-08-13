# SCAN Disk Scheduling (Elevator Algorithm)

## Overview

The **SCAN algorithm** (also called the **Elevator Algorithm**) moves the disk head in one direction, servicing all requests in its path, until it reaches the end of the disk. Then it reverses direction and services requests on the way back. Like an elevator in a building — it goes up serving all floors, then comes back down.

## Motivation

SSTF minimizes seek time but can starve distant requests. SCAN fixes this by guaranteeing that every request is eventually served — the head sweeps across the entire disk, so no request can be skipped indefinitely.

## Algorithm

```
1. Head starts moving in a direction (e.g., toward higher cylinders)
2. Service all requests in the current direction, in order
3. When the head reaches the end of the disk (cylinder 0 or max), reverse direction
4. Service all requests in the new direction
5. Repeat until all requests are served
```

## Detailed Example

```
Requests: 98, 183, 37, 122, 14, 124, 65, 67
Head starts at: 53, moving toward higher cylinders
Disk size: 200 cylinders (0-199)

Step-by-step:
1. Moving UP: service requests at 65, 67, 98, 122, 124, 183
2. Reach end (199), reverse direction
3. Moving DOWN: service requests at 37, 14

Service order: 65, 67, 98, 122, 124, 183, 37, 14
Total movement = (199-53) + (199-14) = 146 + 185 = 331 cylinders
```

```
Cylinder Map:
0         50        100       150       200
|---------|---------|---------|---------|
 ▲        ▲▲▲ ▲▲▲▲▲▲▲▲▲▲▲▲▲          ▲
 │        │││ │││││││││││││          │
14       37 53 65 67    98 122 124   183  199
         start ▲                     ▲    ▲
               │                     │    │
     Path: 53→65→67→98→122→124→183→199→37→14
               ──── UP ────►   ◄── DOWN ────
```

## Simulation Code

```python
def scan(requests, head, disk_size=200, direction='up'):
    total_movement = 0
    order = []
    
    # Sort requests
    sorted_reqs = sorted(requests)
    
    # Split into two groups based on head position
    left = [r for r in sorted_reqs if r < head]   # Requests to the left
    right = [r for r in sorted_reqs if r >= head]  # Requests to the right
    
    if direction == 'up':
        # Go up first, then down
        for r in right:
            total_movement += abs(r - head)
            order.append(r)
            head = r
        # Reach end of disk
        if right:  # Only if we went up
            total_movement += abs(disk_size - 1 - head)
            head = disk_size - 1
        # Go down
        for r in reversed(left):
            total_movement += abs(r - head)
            order.append(r)
            head = r
    else:
        # Go down first, then up
        for r in reversed(left):
            total_movement += abs(r - head)
            order.append(r)
            head = r
        if left:
            total_movement += abs(0 - head)
            head = 0
        for r in right:
            total_movement += abs(r - head)
            order.append(r)
            head = r
    
    return order, total_movement

# Example
requests = [98, 183, 37, 122, 14, 124, 65, 67]
head = 53

order, movement = scan(requests, head)
print(f"Service order: {order}")
print(f"Total head movement: {movement} cylinders")

# Output:
# Service order: [65, 67, 98, 122, 124, 183, 37, 14]
# Total head movement: 331 cylinders
```

## Comparison with Other Algorithms

```
Same example: Requests [98, 183, 37, 122, 14, 124, 65, 67], Head at 53

FCFS:  53→98→183→37→122→14→124→65→67    = 640 cylinders
SSTF:  53→65→67→37→14→98→122→124→183    = 236 cylinders
SCAN:  53→65→67→98→122→124→183→37→14    = 331 cylinders (to edge)
LOOK:  53→65→67→98→122→124→183→37→14    = 299 cylinders (doesn't go to edge)

SCAN is slightly worse than SSTF but provides fairness guarantees.
LOOK (optimized SCAN) is comparable to SSTF.
```

## SCAN's Unfairness Problem

While SCAN prevents starvation, it has a **service time asymmetry**:

```
Requests near the middle of the disk get served more often than those at the edges.

Example: Head sweeps 0→200→0→200...
- Track 100 is visited TWICE per full cycle (going up and coming down)
- Track 10 is visited ONCE per full cycle (only when going down)
- Track 190 is visited ONCE per full cycle (only when going up)

This means middle tracks get 2x the service of edge tracks!
```

```
Service frequency by position:

Frequency
    ▲
  2 │        ╱╲
    │       ╱  ╲
    │      ╱    ╲
  1 │     ╱      ╲
    │    ╱        ╲
    │   ╱          ╲
    └──┴────────────┴──► Cylinder
      0    100    200
      Edge  Middle  Edge

Middle cylinders get better service than edges.
```

This unfairness led to the development of C-SCAN, which provides more uniform service times.

## Real-World Relevance

### Linux Elevator

The original Linux I/O scheduler was literally called the "elevator":

```bash
# Linux 2.4 used the Linus Elevator (simple SCAN)
# Linux 2.6 introduced deadline and CFQ schedulers
# Modern Linux uses mq-deadline, BFQ, kyber

# The elevator concept persists in all Linux I/O schedulers
# Requests are sorted by sector number (SCAN-like) and merged
```

### Disk Firmware

Many HDD controllers implement SCAN-like algorithms in firmware:
- The disk's internal controller reorders commands from the host
- This provides SCAN-like optimization transparently
- The host OS may send requests in any order; the disk optimizes internally

```bash
# Some disks support command queuing (NCQ/TCQ)
# The disk firmware reorders queued commands using SCAN-like logic
# This is transparent to the OS

# Check NCQ support
cat /sys/block/sda/queue/rotational  # 1 for HDD, 0 for SSD
cat /sys/block/sda/device/queue_depth  # NCQ queue depth (typically 32)
```

## Interview Questions

### Beginner

**Q: How does SCAN differ from SSTF?**
A: SSTF always picks the closest request, which can starve distant requests. SCAN moves in one direction, serving all requests in its path, then reverses. This guarantees every request is eventually served. SCAN prevents starvation at the cost of slightly higher seek time than SSTF.

**Q: Why is SCAN called the "elevator algorithm"?**
A: Like an elevator that goes up stopping at each floor, then comes back down, SCAN moves the disk head in one direction servicing all requests, then reverses. The analogy is direct: floors = cylinders, direction = up/down.

### Intermediate

**Q: What is the unfairness problem in SCAN, and how does C-SCAN address it?**
A: SCAN serves middle cylinders more frequently than edge cylinders because the head passes through the middle on both the up and down sweeps. C-SCAN fixes this by only servicing requests in one direction — after reaching the end, the head returns to the start without servicing, then sweeps forward again. This gives every cylinder equal service frequency.

**Q: Calculate the total head movement for SCAN with requests [20, 40, 60, 80] and head at 50 moving toward 0.**
A:
- Direction: toward 0 (down)
- Service: 40, 20 (going down)
- Reach 0, reverse
- Service: 60, 80 (going up)
- Movement: (50-40) + (40-20) + (20-0) + (60-0) + (80-60) = 10+20+20+60+20 = 130

### FAANG-Level

**Q: Prove that SCAN's total head movement is bounded by 2 × (disk_size - 1) regardless of the number of requests.**

A: In the worst case, SCAN moves from one end of the disk to the other:
- Maximum distance in one direction: `disk_size - 1` (from 0 to max or max to 0)
- The head makes at most one full sweep in each direction
- Total maximum movement = 2 × (disk_size - 1)

This is independent of the number of requests. Even with 1 million requests, SCAN can't move more than 2 × (disk_size - 1) cylinders.

Formal proof:
```
Let d = disk_size - 1 (maximum cylinder number)
Let h = starting head position

Case 1: Moving toward max first
- Movement to max: d - h
- Movement back to 0: d
- Total: 2d - h ≤ 2d

Case 2: Moving toward 0 first
- Movement to 0: h
- Movement back to d: d
- Total: h + d ≤ 2d

In both cases, total movement ≤ 2d = 2 × (disk_size - 1)
```

This bounded movement property makes SCAN predictable and suitable for real-time systems where worst-case latency matters.

**Q: Design a disk scheduler that combines SSTF's efficiency with SCAN's fairness guarantees.**

A:

```
Hybrid SSTF-SCAN Scheduler:

1. Divide requests into "near" and "far" groups:
   - Near: within threshold T of current head position
   - Far: beyond threshold T

2. Use SSTF for near requests (exploit locality)
3. Use SCAN for far requests (prevent starvation)

4. Aging mechanism:
   - Track wait time for each request
   - If any request waits > W milliseconds, move it to "near" group
   - This forces SSTF to service it soon

Algorithm:
while (pending requests):
    age all requests (increase priority)
    if (any request aged beyond threshold):
        service oldest aged request (prevents starvation)
    elif (near requests exist):
        service closest near request (SSTF)
    else:
        service next far request in SCAN direction

This combines:
- SSTF's locality exploitation for nearby requests
- SCAN's guaranteed progress for distant requests
- Aging prevents indefinite starvation

Real-world: Linux's mq-deadline scheduler implements something similar:
- Read requests get shorter deadlines than writes
- Starved requests get priority boost
- Proximity is a factor in ordering
```

## Common Mistakes

1. **Forgetting to reverse direction at disk edge**: SCAN must reach the end of the disk (not just the last request). Use LOOK to optimize this.
2. **Confusing SCAN with LOOK**: SCAN goes to the physical end of the disk; LOOK only goes to the last request in that direction. LOOK is almost always better.
3. **Assuming SCAN is always better than SSTF**: For light loads with few requests, SSTF may perform better since SCAN's extra movement to the disk edge adds unnecessary seek time.
4. **Ignoring the initial direction**: The starting direction affects performance. Some implementations choose the direction with more requests.

## Summary

| Property | SCAN |
|----------|------|
| Strategy | Sweep in one direction, reverse at edge |
| Fairness | Good (no starvation) |
| Starvation | No — all requests eventually served |
| Seek optimization | Good (sequential sweep) |
| Service asymmetry | Middle > edges |
| Throughput | Good |
| Implementation | Moderate |
| Best for | Moderate to heavy load |
| Worst for | Requests clustered at edges |

## Cross-References

- [Disk Scheduling Overview](disk-scheduling.md) — Comparison of all algorithms
- [FCFS](disk-fcfs.md) — Baseline comparison
- [SSTF](disk-sstf.md) — Greedy alternative
- [C-SCAN](disk-cscan.md) — Fixes SCAN's unfairness
- [LOOK](disk-look.md) — Optimized SCAN (doesn't go to edge)
