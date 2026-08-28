# Memory Cgroup Internals: The Charge Path

This page follows a memory allocation through the memcg (memory controller) machinery
inside the kernel: how a folio gets charged to a cgroup, what actually happens at
`memory.high` and `memory.max`, how OOM is scoped to a group, and where the auxiliary
accounting (slab, socket, dirty) hooks in. It is deliberately a page about kernel
mechanics — the `mm/memcontrol.c` implementation — not about the cgroup v2 file
interface. The interface, controllers, and systemd integration live in
[cgroup v2](cgroup-v2-internals.md); global reclaim mechanics live in
[page reclaim](reclaim.md); the global OOM killer lives in [oom-killer](oom-killer.md).

## The Accounting Object: Folios and Object Cgroups

The unit of accounting is the folio (the modern form of `struct page` for multi-page
units). Two pointers tie a folio to its cgroup:

- `folio->memcg_data` — either a direct `mem_cgroup *` (user pages) or an
  `obj_cgroup *` with a low bit set (kernel memory: slab, vmalloc, percpu).
- Every `mem_cgroup` hangs off the css (cgroup subsystem state) of the v2 hierarchy,
  so a charge walks the same tree systemd built.

Per-cgroup LRU lists are not separate lists bolted onto the memcg: each node's
`pglist_data` hosts a `lruvec`, and each memcg-per-node pair has its own lruvec with
the usual anon/file × active/inactive lists. Global reclaim walks cgroups; memcg
reclaim walks one cgroup's lruvecs. This is why a container's page cache can be
reclaimed without touching its neighbors', and why [page cache](page-cache.md)
pressure is per-tenant.

## The Charge Path

Every instantiation of user memory — a page fault mapping anon memory, a page cache
read filling a folio, a `read()` into a private buffer — passes through one funnel:

```text
 alloc folio                     mmap fault / readahead / GUP pin
      |                                        |
      v                                        v
 __mem_cgroup_charge(folio, mm, gfp)     get_mem_cgroup_from_mm()
      |                                        |
      v                                        |
 charge_memcg(folio, memcg, gfp)  <-----------+
      |
      +--> try_charge_memcg(memcg, gfp, nr_pages)      the limit loop
      |        |
      |        +--> page_counter_try_charge()  walks memcg AND ALL ANCESTORS
      |        |        (charges propagate up: a child's pages bill the parent)
      |        +--> over limit?  mem_cgroup_reclaim()  (sw Retriable: retry)
      |        +--> still over?   mem_cgroup_oom()      (only at memory.max)
      |
      +--> commit_charge(folio, objcg)     publish the pointer
      +--> memcg1_commit_charge            add to per-memcg lruvec list
```

Three properties of this path explain most production behavior:

1. **Charges are hierarchical.** `page_counter_try_charge()` walks up the ancestor
   chain, so a child cgroup cannot exceed the sum of limits above it, and a parent's
   `memory.current` includes every descendant's usage.
2. **Charging is batched.** Successful charges refill a per-CPU stock of
   `MEMCG_CHARGE_BATCH` (64) pages; the counter is touched once per batch, not once
   per page. Draining the stock (context switch, stock pressure) reconciles it.
3. **Failure is at the top.** The over-limit decision happens in
   `try_charge_memcg()`, and *which* limit was crossed (high vs max) decides
   everything downstream.

## memory.high vs memory.max: Two Enforcement Regimes

The two limits share a file-format but enforce with different machinery:

| Aspect | `memory.high` | `memory.max` |
|---|---|---|
| Kernel reaction | reclaim + allocator throttling | reclaim, then memcg OOM |
| Where enforced | `reclaim_high()` + `__mem_cgroup_handle_over_high()` | `try_charge_memcg()` retry loop |
| OOM killer | never | `mem_cgroup_oom()` → `out_of_memory()` |
| Sleep mechanism | `schedule_timeout_killable(penalty_jiffies)` | reclaim retries, then OOM |
| Max single stall | 2 s (`MEMCG_MAX_HIGH_DELAY_JIFFIES = 2*HZ`) | unbounded (until OOM/reclaim) |
| Event counter | `high` in `memory.events` | `max`, `oom`, `oom_kill` |
| Survives without swap | yes (file pages drop) | only if reclaimable memory exists |

The high-throttle penalty is the interesting part. `calculate_high_delay()` computes
the overage ratio in 20-bit fixed point, then derives a jiffy penalty:

```text
overage        = (usage - high) << 20 / high          MEMCG_DELAY_PRECISION_SHIFT
penalty_jiffies = (overage^2 * HZ) >> 20 >> 14        MEMCG_DELAY_SCALING_SHIFT
```

Quadratic in the overage: 1% over `high` sleeps ~6 jiffies, 18% over hits the 2 s
clamp. The kernel's own documentation table in `mm/memcontrol.c` (for
`high = 100M`, `HZ = 1000`) lists `101M → 6`, `102M → 25`, `105M → 159`,
`110M → 639`, `118M → 2000` — and the demo below reproduces those numbers from the
formula. Sleeping is skipped entirely for penalties at or below `HZ/100`.

`memory.max` is a different beast: reclaim gets `MAX_RECLAIM_RETRIES` attempts, and
if usage still exceeds the limit, `try_charge_memcg()` returns failure. For
`GFP_KERNEL` allocations that failure is the memcg OOM path — with
`__GFP_RETRY_MAYFAIL` the caller gets `-ENOMEM` and decides itself (that is what
makes `mmap()` fail cleanly instead of killing the container).

## OOM Inside a Cgroup

Memcg OOM is the global [oom-killer](oom-killer.md) scoped by a `select_bad_process`
run whose candidate set is the cgroup's task tree:

- The victim is chosen inside the cgroup; badness scoring matches the global rules
  (rss + swap + pgtables), with children summing into parents.
- `memory.oom.group = 1` (a v2 knob since 5.4) widens the kill: after choosing a
  victim task, `mem_cgroup_get_oom_group()` walks the victim's ancestors and picks
  the *highest* memcg with `oom.group` set; every process in that group is killed.
  Container runtimes set this so a dead worker doesn't leave a half-alive pod.
- `memory.oom.kill_disable = 1` swaps the kill for a wakeup on `cgroup.events`
  (`oom` field) — the userspace-actor model used by systemd-oomd-style supervisors.
- Every transition bumps counters in `memory.events`: `oom` (OOM path entered),
  `oom_kill` (a kill happened), plus per-local variants in `memory.events.local`.

A subtlety worth knowing: a task in an unkillable state (`TASK_UNINTERRUPTIBLE` on
a stuck IO) can hold a cgroup in OOM indefinitely; the kernel's `task_is_dying()`
bail-out exists so exiting tasks don't spin in fruitless high-reclaim, but max-OOM
has no such escape — that's why "SIGKILL doesn't work but the process is in D
state" is a classic container-incident signature.

## Swap and the Second Counter

`memory.current` counts charged pages *including* ones in swap; `swap.current`
counts swap slots. On swap-out, `__mem_cgroup_try_charge_swap()` charges the swap
counter up front; if `memory.swap.max` is exhausted the charge fails, the
`swap_max`/`swap fail` event fires, and the folio simply stays in RAM — reclaim
silently loses its only escape valve for anon pages. This makes
`memory.swap.max = 0` a *noop for allocation but a trap for reclaim*: anon-heavy
workloads under `max` pressure go straight from high-throttle to OOM because
reclaim cannot evict anon. If you want compressed-but-not-disk swap, that is
[zram](zram.md) and [zswap](zswap.md) territory; the counter semantics are the same.

## Beyond Page Charges: Slab, Sockets, Dirty Pages

- **Slab/kernel memory.** v1 exposed `memory.kmem` as a separate counter; v2 charges
  kernel memory into the single `memory` counter through `obj_cgroup`s. Since the
  5.9 slab controller rework, SLUB keeps per-memcg *shared* slab pools (one kmem_cache
  per original cache, deduplicated via a per-memcg cache tree), so a container's
  dentry/inode/task objects are billed without exploding the number of caches.
  `memory.stat`'s `kernel` (formerly `slab`) line is the place to watch.
- **Sockets.** TCP/UDP send and receive buffers charge through the same objcg path
  (`memory.stat`'s `sock` line). A chatty socket with a memory.max'd cgroup feels
  it as `send()` blocking when the socket memory pressure kicks in — per-cgroup
  TCP pressure mirrors the global `tcp_mem` machinery.
- **Dirty and writeback.** Dirty page *accounting* is per-memcg (lruvec state:
  `file_dirty`, `file_writeback` in `memory.stat`), while dirty *throttling* flows
  through cgroup writeback: each inode's writeback context (`wbc`) is bound to the
  cgroup that dirtied it, so one tenant's `dd` cannot commandeer another tenant's
  bandwidth budget (the enforcement side lives in the io controller and
  [writeback](writeback.md)).

## Reading memory.stat Without Lying to Yourself

| Field group | What it tells you | Misread to avoid |
|---|---|---|
| `anon`, `file` | live anonymous vs page-cache folios | `file` includes cache shared with the host; it is not "waste" |
| `kernel` (slab/kmem) | dentry, inode, task structs, sockets buffers | grows with *inode count*, not heap; leaks show here |
| `pagetables` | page-table pages of member processes | high `pagetables` + high `anon` = maybe too many tiny mmaps |
| `shmem` | tmpfs pages, also counted in `file` | tmpfs cannot be reclaimed — it swaps or nothing |
| `file_dirty` / `file_writeback` | dirtying vs flushing in flight | nonzero `file_writeback` forever = throttled disk, not memcg bug |
| `pgscan` / `pgsteal` | reclaim scans vs reclaims per lruvec | pgscan » pgsteal = scanning waste (refault thrash) |
| `workingset_refault_*` | pages evicted then re-needed | nonzero-and-rising = working set exceeds limit, honestly |

The `memory.events` file is the operational fire alarm: `high` climbing means
throttling is already happening (latency is being paid), `max` means charges
failed, `oom_kill` means processes died. Alerting on `high` rate is the earliest
honest signal a container is under-sized — before PSI stalls show up in
[psi](../../processes/psi.md) tail latencies.

## Production Failure Modes

| Symptom | Mechanism | First diagnostic |
|---|---|---|
| Latency spikes to ~2 s under memory pressure | `memory.high` quadratic throttle sleeping in charge path | `memory.events high` counter climbing |
| Container killed with all processes, not one | `memory.oom.group = 1` ancestor walk | kernel log `Memory cgroup out of memory: Killed...oom-kill:...` |
| OOM despite free RAM on the host | cgroup-local limit; host memory irrelevant to memcg OOM | compare `memory.current` vs `memory.max`, not free(1) |
| Anon workload OOMs with `swap.max=0` | reclaim can't evict anon; max → OOM with no softening | `memory.events oom` immediately after `max` |
| `memory.current` stuck high after churn | dying memcgs / objcg release races (a long tail of 5.x fixes) | `cgroup.stat nr_dying_descendants` growing |
| fork loop OOMs host, not cgroup | fork charges are tiny per-task; only `pids.max` stops process storms | `pids.events max` — pair memory and pids limits |
| `memory.max = 0` "delete mode" hangs | writes try to reclaim everything; OOM kills are the finisher | expect `oom_kill`s; use with `oom.group` deliberately |
| Leak suspicion in `kernel` stat | historically real (kmem uncharge bugs); today usually genuine retention | `/sys/kernel/slab/*/` per-cache accounting, `memory.stat` deltas |

The "emptying" workflow has no v2 `force_empty` file (that was v1's
`memory.force_empty`): you set `memory.max` low, optionally `memory.reclaim` an
amount (5.19+), and let reclaim + OOM do the rest. If you need a guaranteed-empty
group, kill the tasks first — charging keeps the group alive as long as pages are
pinned by live processes.

## Demo: High Throttling and the Max Wall

The script reproduces the kernel's own `calculate_high_delay` table from
`mm/memcontrol.c`, then simulates a charge/reclaim timeline with the real batch
size, retry count, and event counters:

```python
#!/usr/bin/env python3
"""Deterministic model of the memcg v2 charge path: memory.high throttling
(penalty formula lifted verbatim from mm/memcontrol.c) and memory.max
enforcement (reclaim retries -> memcg OOM)."""
HZ = 1000                    # jiffies per second assumed by the kernel table
PRECISION_SHIFT = 20         # MEMCG_DELAY_PRECISION_SHIFT
SCALING_SHIFT = 14           # MEMCG_DELAY_SCALING_SHIFT
MAX_HIGH_DELAY_JIFFIES = 2 * HZ
MIN_MEANINGFUL_JIFFIES = HZ // 100
SWAP_CLUSTER_MAX = 32        # pages per reclaim attempt (mm: SWAP_CLUSTER_MAX)
MEMCG_CHARGE_BATCH = 64      # include/linux/memcontrol.h (64-bit kernel)
MAX_RECLAIM_RETRIES = 12     # mm/internal.h


def calculate_overage(usage, high):
    if usage <= high:
        return 0
    high = max(high, 1)
    return ((usage - high) << PRECISION_SHIFT) // high


def calculate_high_delay(nr_pages, max_overage):
    """penalty_jiffies = overage^2 * HZ >> 20 >> 14, scaled by batch."""
    if not max_overage:
        return 0
    penalty = (max_overage * max_overage * HZ) >> PRECISION_SHIFT
    penalty >>= SCALING_SHIFT
    return penalty * nr_pages // MEMCG_CHARGE_BATCH


def handle_over_high(usage, high, nr_pages):
    """__mem_cgroup_handle_over_high(): reclaim, then sleep the penalty."""
    overage = calculate_overage(usage, high)
    penalty = calculate_high_delay(nr_pages, overage)
    penalty = min(penalty, MAX_HIGH_DELAY_JIFFIES)
    if penalty <= MIN_MEANINGFUL_JIFFIES:
        return 0
    return penalty


def reclaim_attempt(lru, swap_pages, swap_max, stats):
    """One do_try_scan: free up to SWAP_CLUSTER_MAX pages from the tail.
    File pages are freed outright; anon pages must fit under swap_max."""
    freed = 0
    while lru and freed < SWAP_CLUSTER_MAX:
        kind, _ = lru[-1]
        if kind == "file":
            lru.pop()
        else:
            if swap_pages + 1 > swap_max:
                stats["swap_max_fail"] += 1
                break
            lru.pop()
            swap_pages += 1
            stats["swapped_out"] += 1
        freed += 1
    return freed, swap_pages


def simulate(batches, high, mx, swap_max):
    lru, swap_pages, stats = [], 0, {"high": 0, "max": 0, "oom": 0,
                                     "swap_max_fail": 0, "swapped_out": 0}
    penalty_total = 0
    for b in range(1, batches + 1):
        charge = MEMCG_CHARGE_BATCH
        for i in range(charge):                     # charge_memcg(): 1 page at a time
            lru.append(("file" if (b + i) % 5 == 0 else "anon", (b, i)))
        usage = len(lru) + swap_pages
        if usage > high:                            # memory.high: reclaim + throttle
            stats["high"] += 1
            while len(lru) + swap_pages > high:
                freed, swap_pages = reclaim_attempt(lru, swap_pages, swap_max, stats)
                if not freed:
                    break
            usage = len(lru) + swap_pages
            penalty_total += handle_over_high(usage, high, charge)
        usage = len(lru) + swap_pages
        if usage > mx:                              # memory.max: hard wall
            stats["max"] += 1
            for retry in range(MAX_RECLAIM_RETRIES):
                if len(lru) + swap_pages <= mx:
                    break
                freed, swap_pages = reclaim_attempt(lru, swap_pages, swap_max, stats)
                if not freed:
                    break
            if len(lru) + swap_pages > mx:          # mem_cgroup_oom(): kill a task
                stats["oom"] += 1
                for _ in range(MEMCG_CHARGE_BATCH):  # victim's batch is freed
                    if lru:
                        lru.pop()
            usage = len(lru) + swap_pages
        print(f"batch {b:2d}: usage={len(lru):4d}p swap={swap_pages:3d}p "
              f"(resident+swap={len(lru)+swap_pages:4d}p / max={mx}p)")
    print(f"\npenalty accrued at memory.high: {penalty_total} jiffies "
          f"(= {penalty_total/HZ:.2f} s of charge stalls)")
    print("memory.events equivalent: "
          + " ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    print("A) calculate_high_delay table reproduction (high=100M, HZ=1000)")
    print("   usage  raw_jiffies  slept   (kernel doc table: 101M->6, 102M->25,")
    print("                                 105M->159, 110M->639, 118M->2000; the")
    print("                                 code skips sleeps of <= HZ/100 = 10)")
    for over in (0, 1, 2, 5, 10, 18):
        usage = (100 + over) * 1024 * 1024
        high = 100 * 1024 * 1024
        nr = MEMCG_CHARGE_BATCH
        raw = calculate_high_delay(nr, calculate_overage(usage, high))
        p = min(handle_over_high(usage, high, nr), MAX_HIGH_DELAY_JIFFIES)
        print(f"   {100+over:3d}M  {raw:8d}  {p:6d}")
    print("\nB) charge/reclaim simulation (high=768p max=1024p swap.max=512p, 24 batches)")
    simulate(batches=24, high=768, mx=1024, swap_max=512)
```

Output (the Part A rows match the table embedded in the kernel's own comment; note
118M computes 2073 raw and sleeps the 2000-jiffy clamp):

```text
A) calculate_high_delay table reproduction (high=100M, HZ=1000)
   usage  raw_jiffies  slept   (kernel doc table: 101M->6, 102M->25,
                                 105M->159, 110M->639, 118M->2000; the
                                 code skips sleeps of <= HZ/100 = 10)
   100M         0       0
   101M         6       0
   102M        25      25
   105M       159     159
   110M       639     639
   118M      2073    2000

B) charge/reclaim simulation (high=768p max=1024p swap.max=512p, 24 batches)
batch  1: usage=  64p swap=  0p (resident+swap=  64p / max=1024p)
batch  2: usage= 128p swap=  0p (resident+swap= 128p / max=1024p)
batch  3: usage= 192p swap=  0p (resident+swap= 192p / max=1024p)
batch  4: usage= 256p swap=  0p (resident+swap= 256p / max=1024p)
batch  5: usage= 320p swap=  0p (resident+swap= 320p / max=1024p)
batch  6: usage= 384p swap=  0p (resident+swap= 384p / max=1024p)
batch  7: usage= 448p swap=  0p (resident+swap= 448p / max=1024p)
batch  8: usage= 512p swap=  0p (resident+swap= 512p / max=1024p)
batch  9: usage= 576p swap=  0p (resident+swap= 576p / max=1024p)
batch 10: usage= 640p swap=  0p (resident+swap= 640p / max=1024p)
batch 11: usage= 704p swap=  0p (resident+swap= 704p / max=1024p)
batch 12: usage= 768p swap=  0p (resident+swap= 768p / max=1024p)
batch 13: usage= 512p swap=256p (resident+swap= 768p / max=1024p)
batch 14: usage= 256p swap=512p (resident+swap= 768p / max=1024p)
batch 15: usage= 320p swap=512p (resident+swap= 832p / max=1024p)
batch 16: usage= 384p swap=512p (resident+swap= 896p / max=1024p)
batch 17: usage= 447p swap=512p (resident+swap= 959p / max=1024p)
batch 18: usage= 511p swap=512p (resident+swap=1023p / max=1024p)
batch 19: usage= 511p swap=512p (resident+swap=1023p / max=1024p)
batch 20: usage= 511p swap=512p (resident+swap=1023p / max=1024p)
batch 21: usage= 511p swap=512p (resident+swap=1023p / max=1024p)
batch 22: usage= 510p swap=512p (resident+swap=1022p / max=1024p)
batch 23: usage= 510p swap=512p (resident+swap=1022p / max=1024p)
batch 24: usage= 510p swap=512p (resident+swap=1022p / max=1024p)

penalty accrued at memory.high: 18221 jiffies (= 18.22 s of charge stalls)
memory.events equivalent: high=12 max=6 oom=6 swap_max_fail=18 swapped_out=512
```

Read the timeline like a `memory.events` forensics log: batches 13–14 pay the
high-throttle penalty and swap 512 pages out; once `swap.max` saturates
(`swap_max_fail` climbing), reclaim cannot evict anon pages, so batches 18–24 hit
the max wall repeatedly and the OOM path fires — exactly the
"swap.max=0 anon trap" from the failure-modes table, only visible if you watch
both `swap` and `max` events.

## Related Pages

- [cgroup v2](cgroup-v2-internals.md) — the file interface, controllers, systemd
- [Page reclaim](reclaim.md) — the LRU/workingset machinery memcg reclaim calls into
- [The OOM killer](oom-killer.md) — global selection vs cgroup-scoped selection
- [Slab allocator](slab-allocator.md) — what `obj_cgroup`-charged SLUB pools are
- [PSI](../../processes/psi.md) — the pressure stalls high-throttle sleep feeds
- [Containers and cgroups v2](../../containers/cgroups-v2.md) — runtime-side view

## References

1. [Control Group v2 — kernel admin guide (memory controller section)](https://docs.kernel.org/admin-guide/cgroup-v2.html)
2. [mm/memcontrol.c — charge path, `try_charge_memcg()`, `calculate_high_delay()` with the penalty table](https://raw.githubusercontent.com/torvalds/linux/master/mm/memcontrol.c)
3. [Roman Gushchin, "The new slab memory controller" — LWN, June 2020](https://lwn.net/Articles/798605/)
4. [Memory Resource Controller (cgroup v1 memcg doc) — for the v1-era `kmem`/`force_empty` contrast](https://docs.kernel.org/admin-guide/cgroup-v1/memory.html)
5. [Johannes Weiner, "The memory pressure meter" PSI background — LWN](https://lwn.net/Articles/759781/)
