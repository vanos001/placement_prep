# Redis Persistence Deep Dive

## Overview

Redis offers two complementary persistence mechanisms: **RDB** (point-in-time snapshots) and **AOF** (append-only log). This document covers their internal mechanics at a level needed for production tuning and interview answers.

> **Relation to other docs:** For a quick comparison table, see [patterns-and-internals.md](./patterns-and-internals.md).

## RDB Snapshots

### Fork and Copy-on-Write (COW)

RDB snapshots use the operating system's `fork()` system call combined with **copy-on-write** semantics:

```
Parent (Redis Server)          Child (RDB Writer)
┌──────────────────┐         ┌──────────────────┐
│ Shared Memory    │◄────────│ Shared Memory    │
│ (page table      │  fork() │ (same virtual    │
│  initially      │         │  pages)          │
│  identical)      │         │                  │
└──────────────────┘         └──────────────────┘
        │                            │
   Write to page X              Read page X
        │                            │
        ▼                            │
   OS allocates new page         Reads original
   (COW trigger)                 page (unchanged)
```

**Why COW matters:** After `fork()`, parent and child share the same physical memory pages. When the parent modifies a page, the OS creates a private copy for the parent (copy-on-write). The child continues reading the original pages. This means the child can write a consistent snapshot without blocking the parent.

**The fork() latency problem:** On large Redis instances (e.g., 64 GB), `fork()` can take 100ms-1s because the OS must copy the parent's page table. During this time, Redis is **completely blocked** (single-threaded). Mitigations:

- Keep `used_memory` < total RAM (avoid swapping during fork)
- Use `save` triggers that fire before memory gets too large
- Linux: `THP_DISABLE=1 redis-server` (disable transparent huge pages — THP makes fork much slower because fewer, larger pages must be tracked)

### save vs bgsave

| Command | Behavior | Blocking? |
---------|----------|-----------|
| `SAVE` | Synchronous snapshot in main thread | **Yes** — blocks all clients |
| `BGSAVE` | Fork child process for snapshot | **Briefly** — only during `fork()` |

`BGSAVE` is the standard. `SAVE` is only used when the parent is the child's replica and the master sends `SYNC`. Never use `SAVE` on a production master.

### save Configuration

```
save 900 1      # BGSAVE if ≥1 change in 900s
save 300 10     # BGSAVE if ≥10 changes in 300s
save 60 10000   # BGSAVE if ≥10K changes in 60s
```

With all three rules, Redis uses the most permissive trigger. Modern recommendation: disable automatic saves (`save ""`) and use external cron with `redis-cli BGSAVE` or a managed service's backup scheduling.

## AOF (Append-Only File)

### AOF Format

The AOF file contains Redis protocol commands, one per line:

```
*3           # 3 arguments follow
$3           # first argument is 3 bytes
SET          # the command
$5           # second argument is 5 bytes
mykey        # the key
$7           # third argument is 7 bytes
myvalue      # the value
```

This is the same format Redis uses on the wire (RESP protocol), which means AOF files are directly replayable by Redis.

### fsync Policies

| Setting | Behavior | Data Loss | Performance |
---------|----------|-----------|-------------|
| `always` | `fsync` on every write | **None** (if disk works) | Lowest (~few hundred writes/sec) |
| `everysec` (default) | `fsync` once per second via background thread | Up to **1 second** | High (thousands to tens of thousands writes/sec) |
| `no` | `fsync` deferred to OS (every ~30s) | Up to **30 seconds** | Highest |

**How `everysec` works internally:**

1. Client write arrives → Redis appends to AOF buffer (in-memory)
2. Redis writes the buffer to the kernel's file buffer (write syscall, no fsync)
3. A background thread calls `fsync` every second
4. If Redis crashes after step 2 but before step 3's `fsync`, up to 1 second of writes is lost
5. Redis tracks the last fsync'd offset; if the previous fsync is still in progress, it delays the next write to avoid fsync pile-up

### AOF Rewrite

Over time, the AOF grows because it logs every write (including counter increments: `INCR counter` logged 1000 times = 1000 lines). **AOF rewrite** compacts the AOF by rewriting it from the current in-memory state:

```
Before rewrite:
  SET counter 1
  INCR counter          → SET counter 2
  INCR counter          → SET counter 3
  DEL temp_key
  SET temp_key "new"   → SET temp_key "new"
  (100K lines)

After rewrite:
  SET counter 3
  SET temp_key "new"
  (2 lines)
```

**Rewrite process (BGREWRITEAOF):**

1. Redis forks a child process (same COW mechanism as BGSAVE)
2. Child writes the current dataset as minimal AOF commands to a temporary file
3. Meanwhile, the parent accumulates new writes in an AOF rewrite buffer
4. When child finishes, parent appends the rewrite buffer to the temporary file
5. Atomic rename: `temp.aof` → `appendonly.aof`

This ensures no data is lost during the rewrite.

## Mixed Persistence (RDB + AOF)

Available since Redis 4.0 (`aof-use-rdb-preamble yes`):

```
AOF file structure with mixed persistence:
+-------------------+
| RDB snapshot      |  ← Compact binary format (fast reload)
| (partial state)   |
+-------------------+
| AOF incremental   |  ← Only writes since the snapshot
| (RESP commands)   |
+-------------------+
```

Benefits:
- **Fast restart**: The RDB portion is loaded in O(N) binary format, much faster than replaying AOF commands
- **Low data loss**: AOF commands after the snapshot capture recent writes
- **Smaller files**: The RDB preamble replaces potentially thousands of AOF lines

Restart with mixed persistence:
1. Load the RDB preamble (binary, fast)
2. Replay the AOF incremental commands (small, since they start from the recent snapshot)

## Comparison Table

| Aspect | RDB | AOF | Mixed (RDB+AOF) |
--------|-----|-----|-----------------|
| **Durability** | Minutes of potential loss | 1 second (`everysec`) | 1 second |
| **Restart speed** | Very fast (binary) | Slow (replay commands) | Fast (binary preamble + small AOF) |
| **File size** | Compact | Large (grows until rewrite) | Moderate |
| **Write overhead** | None during normal ops | Appends every write | Appends every write |
| **Fork overhead** | Yes (during BGSAVE) | Yes (during rewrite) | Yes (during rewrite, preamble is RDB) |
| **Best for** | Backups, disaster recovery | Durability, audit log | Production (best of both) |

## Interview Questions

**Q: Explain how Redis RDB snapshots work with fork() and copy-on-write.**
A: Redis calls `fork()`, creating a child process that shares the parent's memory pages via the OS page table. When the parent modifies a page (due to a client write), the OS triggers copy-on-write: it allocates a new page for the parent, leaving the child's copy unchanged. The child writes all shared pages to an RDB file, producing a consistent snapshot. The only blocking time is the `fork()` call itself (copying the page table), which can be 100ms+ on large instances.

**Q: What is the difference between AOF `always` and `everysec` fsync policies?**
A: With `always`, Redis calls `fsync()` synchronously on every write before acknowledging the client — zero data loss but limits throughput to a few hundred writes/sec. With `everysec` (default), Redis writes to the kernel buffer on every write (fast), and a background thread calls `fsync` once per second — up to 1 second of data loss but throughput of tens of thousands of writes/sec.

**Q: How does AOF rewrite work without blocking writes?**
A: Redis forks a child process that writes the current dataset to a temporary AOF file. During the rewrite, the parent continues accepting writes and accumulates them in a rewrite buffer. When the child finishes, the parent appends the buffer contents to the temp file and atomically renames it over the old AOF file. The atomic rename ensures the AOF is always in a consistent state.

**Q: Why should you disable transparent huge pages (THP) for Redis?**
A: THP causes the OS to use 2MB pages instead of 4KB pages. During `fork()`, the page table must be copied — with THP, there are fewer but much larger entries, making the copy slower. More critically, any write during COW triggers a 2MB page copy instead of a 4KB copy, causing memory spikes and latency jitter. Redis logs a warning at startup if THP is enabled.

**Q: Your Redis instance uses 50GB of memory. BGSAVE takes 2 seconds. How do you fix this?**
A: (1) Disable THP (`echo never > /sys/kernel/mm/transparent_hugepage/enabled`). (2) Increase `save` intervals to reduce BGSAVE frequency. (3) Ensure `used_memory_rss` < physical RAM (no swap). (4) Consider switching to managed Redis (ElastiCache, Redis Cloud) where persistence is handled off-process. (5) Use `info memory` to check fragmentation — high fragmentation makes fork more expensive. (6) Enable `activedefrag` to reduce fragmentation.

## References

- [Redis Persistence](https://redis.io/docs/management/persistence/)
- [AOF Rewrite Internals](https://redis.io/docs/management/persistence/#aof-rewrite)
- Redis source: `rdb.c`, `aof.c`
