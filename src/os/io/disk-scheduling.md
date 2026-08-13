# Disk Scheduling

## Overview

Disk scheduling is the process of deciding the order in which pending disk I/O requests should be serviced. Since disk access involves physical head movement (seeking), the order in which requests are served can dramatically affect total seek time and overall throughput.

## Motivation

On a mechanical hard disk drive (HDD), the read/write head must physically move to the correct track (cylinder), wait for the disk to rotate to the correct sector, and then transfer data. The **seek time** (moving the head) is the dominant cost — typically 3-15ms for a full stroke.

If requests arrive at tracks 10, 50, 30, 90, and the head is at track 20:
- Serving in arrival order: 20→10→50→30→90 = |10|+|40|+|20|+|60| = 130 tracks
- Serving optimally: 20→10→30→50→90 = |10|+|20|+|20|+|40| = 90 tracks

The scheduling algorithm can make a significant difference!

### Why Not Just Use SSDs?

SSDs have no moving parts and near-uniform access times, so disk scheduling matters less. However:
- Many systems still use HDDs (bulk storage, data centers)
- Even SSDs benefit from I/O merging and reordering
- The I/O scheduler in Linux also handles request merging, which helps SSDs
- Understanding disk scheduling is a classic OS interview topic

## Disk Geometry

```
                    Platter
              ┌─────────────────┐
              │    ┌───────┐    │
              │    │       │    │
    Track 0 ──│───►│ ═════ │◄───│── Outer edge
    Track 1 ──│───►│ ═════ │    │
    Track 2 ──│───►│ ═════ │    │
    ...       │    │   ▲   │    │
    Track N ──│───►│ ═════ │◄───│── Inner edge
              │    │       │    │
              │    │  Arm  │    │
              │    └───┬───┘    │
              │        │        │
              │   Spindle       │
              └─────────────────┘

Key Terms:
- Platter: Physical disk surface
- Track: Concentric circle on platter (same radius)
- Cylinder: Set of tracks at same position across all platters
- Sector: Arc segment of a track (smallest addressable unit, typically 512B or 4KB)
- Seek: Moving the head arm to the correct track
- Rotational latency: Waiting for the sector to rotate under the head
- Transfer time: Reading/writing the data

Access Time = Seek Time + Rotational Latency + Transfer Time
```

## Disk Scheduling Algorithms

| Algorithm | Full Name | Fairness | Starvation? | Optimality |
|-----------|-----------|----------|-------------|------------|
| [FCFS](disk-fcfs.md) | First-Come First-Served | ✅ Fair | No | Poor |
| [SSTF](disk-sstf.md) | Shortest Seek Time First | ❌ Unfair | Yes | Good |
| [SCAN](disk-scan.md) | Elevator Algorithm | ✅ Reasonable | No | Good |
| [C-SCAN](disk-cscan.md) | Circular SCAN | ✅ Better | No | Good |
| [LOOK](disk-look.md) | LOOK (modified SCAN) | ✅ Reasonable | No | Good |
| [C-LOOK](disk-look.md) | Circular LOOK | ✅ Better | No | Good |

### Visual Comparison

```
Head starts at track 50, requests: 95, 15, 35, 70, 10
Direction: toward higher tracks

FCFS:    50 → 95 → 15 → 35 → 70 → 10  (total movement: 45+80+20+35+60 = 240)
SSTF:    50 → 35 → 15 → 10 → 70 → 95  (total movement: 15+20+5+60+25 = 125)
SCAN:    50 → 70 → 95 → 35 → 15 → 10  (total movement: 20+25+60+20+5 = 130)
C-SCAN:  50 → 70 → 95 → 10 → 15 → 35  (total movement: 20+25+85+5+20 = 155)
LOOK:    50 → 70 → 95 → 35 → 15 → 10  (same as SCAN here, doesn't go to edge)
```

## Linux I/O Schedulers

Linux has evolved through several I/O schedulers:

### Historical Schedulers
- **Linus Elevator** (2.4): Simple merge and sort
- **Deadline** (2.6): Per-request deadlines, prevents starvation
- **Anticipatory** (2.6): Pauses briefly after read to exploit locality
- **CFQ** (Completely Fair Queue): Per-process queues, time-sliced

### Modern Schedulers
- **BFQ** (Budget Fair Queueing): Fair allocation for interactive workloads
- **mq-deadline**: Multi-queue aware deadline scheduler (default on many distros)
- **Kyber**: Token-based, low latency for fast devices (NVMe)
- **none**: No scheduling — for fast NVMe where scheduling overhead > benefit

```bash
# View current scheduler
cat /sys/block/sda/queue/scheduler
# [mq-deadline] bfq none

# Change scheduler
echo bfq | sudo tee /sys/block/sda/queue/scheduler

# View I/O scheduler parameters
ls /sys/block/sda/queue/iosched/
# For mq-deadline: read_expire write_expire fifo_batch writes_starved
```

## Real-World Considerations

### Request Merging

Before scheduling, the OS merges adjacent I/O requests:

```
Before merging:
  Read sectors 100-109
  Read sectors 110-119
  Read sectors 500-509

After merging:
  Read sectors 100-119  (merged adjacent reads)
  Read sectors 500-509

This reduces the number of disk operations.
```

```bash
# View I/O statistics including merges
iostat -x 1
# Device  r/s    w/s   rMerge wMerge  ...
# sda     100.0  50.0   20.0   10.0   ...
```

### Elevator Merging in Linux

```bash
# The block layer maintains a request queue sorted by sector number
# New requests are inserted in sector order and merged with neighbors

# View request queue settings
cat /sys/block/sda/queue/nr_requests  # Max queue depth (typically 128)
cat /sys/block/sda/queue/max_sectors_kb  # Max request size
```

### SSD vs HDD Scheduling

```
HDD (Mechanical):
- Seek time dominates (3-15ms)
- Scheduling order matters a lot
- Sequential >> Random
- SCAN/LOOK algorithms help significantly

SSD (Solid State):
- No seek time (uniform access ~0.1ms)
- Scheduling order matters less
- Random ≈ Sequential (for small I/O)
- Focus on parallelism and queue depth
- "none" scheduler often optimal for NVMe
```

## Interview Questions

### Beginner

**Q: Why do we need disk scheduling?**
A: On mechanical disks, the physical head movement (seeking) is the most expensive part of an I/O operation. By reordering pending requests intelligently, we can minimize total head movement, reducing average access time and increasing throughput. Without scheduling, random head movement would severely degrade performance.

**Q: What is seek time and why is it the dominant cost?**
A: Seek time is the time for the disk arm to move the read/write head to the correct track (cylinder). It's typically 3-15ms for a full stroke on HDDs, while rotational latency is 2-8ms and transfer time is microseconds. Since seek involves physical movement of the arm assembly, it's the slowest component.

### Intermediate

**Q: Compare SCAN and C-SCAN. When would you prefer one over the other?**
A:
- **SCAN**: Head moves in one direction servicing requests, then reverses. Requests in the middle get better service than those at the edges (head visits middle tracks twice per full sweep).
- **C-SCAN**: Head moves in one direction servicing requests, then jumps back to the start without servicing. Provides more uniform wait times since the head always scans in the same direction.

Prefer C-SCAN when uniform response time is important (e.g., a database server). Prefer SCAN when the workload is skewed toward the middle of the disk.

**Q: Why is SSTF not used in practice despite being simple and effective?**
A: SSTF can cause **starvation** — if requests keep arriving near the current head position, distant requests may never be served. For example, if the head is at track 50 and requests keep coming at tracks 45-55, a request at track 200 will wait indefinitely. SCAN/LOOK algorithms avoid this by guaranteeing every request is eventually served.

### FAANG-Level

**Q: Design an I/O scheduler for a storage system serving both a database (random reads, latency-sensitive) and a log archiver (sequential writes, throughput-sensitive). How would you balance fairness and performance?**

A:

```
Design: Multi-Class Priority Scheduler with Bandwidth Reservation

1. Request Classification:
   - Classify by process/cgroup: database → HIGH, archiver → LOW
   - Detect access pattern: sequential → batch, random → prioritize

2. Scheduling Algorithm:
   - HIGH class gets strict priority (latency-sensitive)
   - LOW class gets guaranteed minimum bandwidth (e.g., 20%)
   - Within each class: deadline-based ordering

3. Request Merging:
   - Merge sequential requests aggressively (helps archiver)
   - Don't delay random requests for merging (helps database)

4. Implementation:
   ┌─────────────────────────────────────────┐
   │           Request Queue                  │
   │  ┌──────────┐  ┌──────────────────┐     │
   │  │ HIGH Q   │  │ LOW Q            │     │
   │  │ (deadline│  │ (CFQ-like,       │     │
   │  │  sorted) │  │  time-sliced)    │     │
   │  └────┬─────┘  └───────┬──────────┘     │
   │       │                │                 │
   │       ▼                ▼                 │
   │    Dispatch      Dispatch (if budget     │
   │    immediately   allows, 20% minimum)    │
   └─────────────────────────────────────────┘

5. Anti-starvation:
   - LOW class always gets at least 20% of disk time
   - HIGH class can use up to 80% when busy
   - Token bucket limits HIGH class burst to prevent LOW starvation

6. Real-world mapping:
   - Use cgroups I/O controller (blkio) for classification
   - BFQ scheduler supports per-cgroup weights
   - ionice command: database gets class 1 (realtime), archiver gets class 2 (best-effort)
```

## Common Mistakes

1. **Assuming disk scheduling is irrelevant for SSDs**: While seek time is zero, request merging and prioritization still matter. NVMe controllers have their own internal scheduling.
2. **Forgetting about rotational latency**: Even within the same track, you must wait for the sector to rotate under the head. SSTF/SCAN optimize seek but not rotation.
3. **Ignoring request merging**: The scheduler doesn't just reorder; it also merges adjacent requests. This is a huge performance win.
4. **Starving background I/O**: Aggressive foreground prioritization can starve background tasks (backup, replication). Use bandwidth reservation.
5. **Using the wrong scheduler**: Don't use CFQ/BFQ on NVMe drives — the overhead exceeds the benefit. Use `none` or `mq-deadline`.

## Summary

| Aspect | Key Point |
|--------|-----------|
| Purpose | Minimize seek time, maximize throughput |
| Dominant cost | Seek time (3-15ms on HDD) |
| FCFS | Fair but no optimization |
| SSTF | Optimal but starvation risk |
| SCAN/LOOK | Good balance of performance and fairness |
| C-SCAN/C-LOOK | More uniform service times |
| Linux modern | mq-deadline, BFQ, Kyber, none |
| SSDs | Scheduling less critical; focus on queue depth |

## Cross-References

- [FCFS](disk-fcfs.md) — First-Come First-Served detailed analysis
- [SSTF](disk-sstf.md) — Shortest Seek Time First
- [SCAN](disk-scan.md) — Elevator algorithm
- [C-SCAN](disk-cscan.md) — Circular SCAN
- [LOOK / C-LOOK](disk-look.md) — Optimized SCAN variants
- [Buffering](buffering.md) — How buffered requests interact with scheduling


## Cross References

- [FCFS](disk-fcfs.md)
- [SSTF](disk-sstf.md)
- [SCAN](disk-scan.md)
- [Disk Allocation](../filesystems/disk-allocation.md)
- [HDD](../../storage/hdd.md)
