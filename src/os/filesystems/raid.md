# RAID (Redundant Array of Independent Disks)

## Overview

**RAID** combines multiple physical disks into a single logical unit to improve **performance** (parallelism), **reliability** (redundancy), or both. RAID was originally proposed in 1987 by Patterson, Gibson, and Katz at UC Berkeley. The "I" originally stood for "Inexpensive" but is now "Independent."

## RAID Levels

### RAID 0 — Striping

Data is split across disks in stripes.

```
Disk 0: [A0] [A2] [A4] [A6]
Disk 1: [A1] [A3] [A5] [A7]

File A: A0→A1→A2→A3→A4→A5→A6→A7
```

| Property | Value |
|----------|-------|
| Min disks | 2 |
| Usable capacity | 100% |
| Fault tolerance | None (1 disk failure = total loss) |
| Read performance | Excellent (parallel) |
| Write performance | Excellent (parallel) |

**Use case**: Temporary data, scratch space, where speed matters more than safety.

### RAID 1 — Mirroring

Every block is duplicated on two (or more) disks.

```
Disk 0: [A0] [A1] [A2] [A3]
Disk 1: [A0] [A1] [A2] [A3]  ← identical copy
```

| Property | Value |
|----------|-------|
| Min disks | 2 |
| Usable capacity | 50% (2-way mirror) |
| Fault tolerance | 1 disk failure (2-way) |
| Read performance | Good (read from either) |
| Write performance | Moderate (write to both) |

**Use case**: OS boot disks, critical data.

### RAID 5 — Striping with Distributed Parity

Data and parity are striped across all disks. Parity is distributed (not on a single disk).

```
Disk 0: [D0] [D1] [D4] [P2]
Disk 1: [D2] [P0] [D5] [D6]
Disk 2: [P1] [D3] [P3] [D7]

P0 = D0 ⊕ D2    (parity for stripe 0)
P1 = D0 ⊕ D1    (parity for stripe 1)
P2 = D4 ⊕ D5    (parity for stripe 2)
P3 = D6 ⊕ D7    (parity for stripe 3)
```

| Property | Value |
|----------|-------|
| Min disks | 3 |
| Usable capacity | (n-1)/n |
| Fault tolerance | 1 disk failure |
| Read performance | Excellent |
| Write performance | Moderate (read-modify-write for parity) |

**Write penalty**: Every write requires reading old data + old parity, computing new parity, writing new data + new parity. This is called the **RAID-5 write hole** (partially addressed by RAID-Z and journaling).

### RAID 6 — Double Distributed Parity

Two independent parity calculations (P and Q) using Reed-Solomon codes.

```
Disk 0: [D0] [D1] [D4] [Q2]
Disk 1: [D2] [P0] [P2] [D6]
Disk 2: [P1] [D3] [D5] [P3]
Disk 3: [Q0] [Q1] [D7] [Q3]

P = XOR parity
Q = Reed-Solomon parity (can recover from 2 failures)
```

| Property | Value |
|----------|-------|
| Min disks | 4 |
| Usable capacity | (n-2)/n |
| Fault tolerance | 2 disk failures |
| Read performance | Excellent |
| Write performance | Slower than RAID-5 (two parity computations) |

### RAID 10 — Mirrored Stripes

RAID 1 + RAID 0: Stripe across mirrored pairs.

```
Mirror 0:           Mirror 1:
Disk 0: [A0][A2]   Disk 2: [A1][A3]
Disk 1: [A0][A2]   Disk 3: [A1][A3]

File A: A0→A1→A2→A3
```

| Property | Value |
|----------|-------|
| Min disks | 4 |
| Usable capacity | 50% |
| Fault tolerance | 1 disk per mirror pair |
| Read performance | Excellent |
| Write performance | Good |

**Use case**: Databases, high-performance applications.

## Comparison Table

| RAID | Min Disks | Capacity | Fault Tolerance | Read | Write | Use Case |
|------|-----------|----------|-----------------|------|-------|----------|
| 0 | 2 | 100% | None | ★★★ | ★★★ | Scratch space |
| 1 | 2 | 50% | 1 disk | ★★ | ★★ | Boot drives |
| 5 | 3 | (n-1)/n | 1 disk | ★★★ | ★★ | General storage |
| 6 | 4 | (n-2)/n | 2 disks | ★★★ | ★ | Archive, backup |
| 10 | 4 | 50% | 1 per pair | ★★★ | ★★★ | Databases |

## Parity Calculation

### XOR Parity (RAID 5)

```
Given data blocks D0, D1, D2:
  Parity P = D0 ⊕ D1 ⊕ D2

Recovery (if D1 is lost):
  D1 = D0 ⊕ D2 ⊕ P
```

### Reed-Solomon (RAID 6)

Uses Galois Field arithmetic to compute two independent parity values (P and Q). Can recover from any 2 disk failures simultaneously.

## RAID 5 Write Hole

**Problem**: During a stripe write, if power is lost after writing new data but before writing new parity, the parity is inconsistent.

```
Before crash:
  D0=10, D1=20, P = 10⊕20 = 30

Write D0=15:
  Write D0=15  ✓  (committed)
  Write P = 15⊕20 = 27  ✗  (crash!)

After crash:
  D0=15, D1=20, P=30  ← P is wrong!
  If D1 fails, recovery: D1 = 15⊕30 = 17 (WRONG! Should be 20)
```

**Solutions:**
1. **RAID-Z (ZFS)**: Writes full stripes atomically with COW
2. **Battery-backed write cache (BBWC)**: Completes writes after power restore
3. **Journaling RAID controllers**: Log writes before applying
4. **mdadm write-intent bitmap**: Tracks in-progress writes

## Hardware vs. Software RAID

| Aspect | Hardware RAID | Software RAID |
|--------|--------------|---------------|
| Controller | Dedicated RAID card (LSI, Dell PERC) | OS kernel (mdadm, ZFS) |
| CPU usage | Offloaded to controller | Uses host CPU |
| Cache | Battery-backed DRAM cache | Host RAM |
| Performance | Consistent | Depends on CPU load |
| Cost | $200-1000+ | Free |
| Flexibility | Limited to controller features | Full OS features |
| Recovery | Controller-dependent | Standard tools |

### Linux Software RAID (mdadm)

```bash
# Create RAID 5
mdadm --create /dev/md0 --level=5 --raid-devices=3 /dev/sd{b,c,d}

# Check status
cat /proc/mdstat
mdadm --detail /dev/md0

# Add hot spare
mdadm --add /dev/md0 /dev/sde

# Remove failed disk
mdadm --fail /dev/md0 /dev/sdc
mdadm --remove /dev/md0 /dev/sdc

# Grow RAID (add disk)
mdadm --grow /dev/md0 --raid-devices=4 --add /dev/sde
```

## RAID-Z (ZFS)

ZFS solves the write hole with variable-width stripes and COW:

```
RAID-Z1 (3 disks):
  Stripe 1: [D0][D1][P0]     ← full stripe, 2 data + 1 parity
  Stripe 2: [D2][P1]         ← partial stripe, 1 data + 1 parity
  Stripe 3: [D3][D4][D5][P2] ← full stripe, 3 data + 1 parity
```

**Key difference**: Stripe width varies per write. No partial stripe updates = no write hole.

## Nested RAID Levels

| Level | Description | Capacity | Fault Tolerance |
|-------|-------------|----------|-----------------|
| RAID 01 | Stripe of mirrors | 50% | 1 per mirror |
| RAID 10 | Mirror of stripes | 50% | 1 per mirror |
| RAID 50 | Stripe of RAID 5 | (n-s)/n | 1 per RAID-5 set |
| RAID 60 | Stripe of RAID 6 | (n-2s)/n | 2 per RAID-6 set |

## Interview Questions

**Q1: What is the RAID 5 write hole and how is it solved?**

The write hole occurs when a crash happens between writing new data and updating parity, leaving them inconsistent. Solutions: (1) RAID-Z writes full stripes atomically via COW, (2) battery-backed write cache ensures writes complete after power restore, (3) write-intent bitmap tracks in-progress writes for replay.

**Q2: When would you choose RAID 10 over RAID 5?**

RAID 10 is better for write-heavy workloads (databases) because it doesn't have the parity calculation overhead. RAID 5 has a write penalty (read-modify-write for every write). RAID 10 also rebuilds faster after a failure (just copy the mirror) vs. RAID 5 (read all disks to reconstruct). RAID 5 is better for capacity (only lose 1/n vs. 50%).

**Q3: How does RAID 6 differ from RAID 5 and when is it needed?**

RAID 6 uses two independent parity values (P and Q) so it can survive 2 simultaneous disk failures. RAID 5 can only survive 1. RAID 6 is recommended for large arrays (4+ disks) where the probability of a second failure during rebuild is non-trivial. The trade-off is more write overhead and 2 disks of capacity loss.

**Q4: What is the difference between hardware and software RAID?**

Hardware RAID uses a dedicated controller with its own CPU and cache. Software RAID (mdadm, ZFS) uses the host CPU. Hardware RAID provides consistent performance and battery-backed cache but costs more and locks you into the controller. Software RAID is free, flexible, and can use advanced features (checksums, COW) but uses host resources.

**Q5: Why does ZFS's RAID-Z not have a write hole?**

RAID-Z uses COW: writes go to new locations, never overwrite. Full stripes are written atomically within a transaction group. There's no state where data is updated but parity isn't, because the entire stripe either exists (committed) or doesn't (discarded). Additionally, checksums detect any corruption.

## Common Mistakes

- Using RAID 0 for important data — no redundancy
- Using RAID 5 with large disks — rebuild time increases, second failure risk during rebuild
- Mixing hardware RAID with ZFS — ZFS needs direct disk access for checksums
- Thinking RAID replaces backups — RAID protects against disk failure, not deletion, corruption, or disasters
- Not monitoring RAID health — silent disk failures can compound

## Summary

- RAID combines disks for performance and/or redundancy
- RAID 0 (striping) for speed, RAID 1 (mirroring) for safety, RAID 5/6 for balance
- RAID 10 combines mirroring + striping for best of both
- RAID 5 write hole: parity inconsistency on crash; solved by RAID-Z, BBWC, or journaling
- Hardware RAID uses dedicated controllers; software RAID uses OS
- RAID is not a backup — use it with regular backups

## Cross-References

- [ZFS](zfs.md) — RAID-Z implementation
- [Disk Scheduling](../io/disk-scheduling.md) — I/O across multiple disks
- [Disk Allocation](disk-allocation.md) — block allocation across RAID
- [Journaling](journaling.md) — write hole mitigation
