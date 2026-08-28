# SSD FTL Internals: Mapping Tables, Garbage Collection, and the Over-Provisioning Trade

The SSD is the only common storage device that lies about its own geometry for
a living. The OS issues reads and writes to 512-byte or 4 KB *logical* block
addresses as if they were mutable sectors on a platter; underneath, the flash
translation layer (FTL) maintains the fiction — remapping every write to
never-before-programmed *physical* pages, recycling corpses of invalidated
data, and spreading wear so the drive outlives its warranty. This page takes
the FTL apart: the geometry that forces the remapping, the mapping-table
design space, garbage collection and the write-amplification/over-provisioning
trade (with a runnable simulator), wear leveling, TRIM, and the SLC-cache
tiering that shapes modern drive behavior. [SSD fundamentals](../ssd.md)
covers the device overview; here we go one layer down, quantitatively.

## Flash geometry: the asymmetry that creates the FTL

NAND flash is organized in **pages** (4–16 KB — the program/read unit) grouped
into **blocks** (typically 64–256 pages, e.g. a 2 MiB block of 128 × 16 KB
pages — the erase unit). Three properties define everything else:

1. **Programs must go to virgin pages.** A programmed page flips bits only
   from 1 → 0. Rewriting requires resetting them to 1 — an **erase** — which
   clears the *whole block*.
2. **Erase is slow and destructive.** Typical order: read ~50 µs, program
   ~300–900 µs, erase ~2–10 ms — and erase obliterates every other valid page
   in the block.
3. **Blocks wear out.** Each erase cycle degrades the oxide: TLC sustains
   ~1–3k P/E cycles, MLC ~3–10k, SLC ~50–100k. Every management decision is
   therefore also a wear decision.

An in-place overwrite of one 4 KB sector would require read-modify-erase-
rewrite of an entire multi-MB block — thousands of times slower than the
write it replaced. So the FTL redirects: every logical write lands on a fresh
physical page, the old copy becomes **invalid** ("stale"), and cleanup is
deferred to **garbage collection**.

```text
logical view (what the host sees)     physical reality (NAND)

LBA 1000 ─────► ?                     block 40: [P0 v][P1 v][P2 v][P3 STALE]
LBA 1001 ─────► ?                     block 41: [P0 v][P1 STALE][P2 v][P3 v]
LBA 1002 ─────► ?                     block 42: [P0 FREE ..... erase unit ....]
                                      block 43: [P0 v][P1 v][P2 STALE][P3 STALE]

FTL mapping table:  LBA -> (block, page)     v = valid, STALE = dead page
Rewrite LBA 1000: append page at block 42, mark old copy STALE, update map.
```

## Three mapping-table designs

The mapping table is the FTL's brain, and its RAM cost is the design axis:
one 8-byte entry per 4 KB page means 1 GB of DRAM per TB of flash if mapped
naively at page granularity.

| Design            | Table granularity              | RAM per TB          | Random read       | GC cost                                     |
|-------------------|--------------------------------|---------------------|-------------------|---------------------------------------------|
| Block-level       | one entry per block            | ~64–128 MB          | scan block (slow) | whole-block rewrite on any update (terrible) |
| Page-level        | one entry per page             | ~1–2 GB             | one lookup        | optimal (copy only live pages)               |
| Hybrid (BAST/FAST)| log blocks + data blocks       | ~100 MB             | usually 1 lookup  | good, but log-block churn on mixed workloads |
| DFTL (demand paged)| page-level, cached on demand  | tunable MB-scale    | 1 lookup + rare miss | page-level GC; map-table writes add WAF    |

Block-level mapping was the 1990s answer for small cards ([Intel's original
FTL spec](https://www.scribd.com/doc/72886477/Flash-Disks-Understanding-the-Flash-Translation-Layer-FTL-Specification)
described it) and dies on random writes: updating one sector rewrites a whole
block. Page-level gives perfect behavior but a DRAM-sized table. Production
drives historically shipped **hybrids** — a small page-mapped *log* region
absorbs recent writes, then is merged back into block-mapped data regions
(BAST and its refinement FAST). [DFTL](https://doi.org/10.1145/1508244.1508271)
moved the industry to demand-paged page-level mapping: keep the hot tail of
the table in limited RAM, page the rest in and out of flash, accepting
occasional extra reads and map-table write amplification.

## Garbage collection: victim selection and the cost of a copy

When the supply of free pages runs low, the FTL picks **victim blocks**,
copies their still-valid pages to the log, and erases them. Two decisions
dominate:

- **Which victim?** *Greedy* picks the block with the fewest valid pages —
  maximum space reclaimed per unit of copying. *Cost-benefit* (the classic
  ATC'08 baseline) weights reclaim benefit against copy cost and block age,
  trading a little immediacy for wear and map-update smoothing.
- **What does it cost?** Reclaiming a block with `v` valid pages of `P`
  costs `v` physical writes (plus 1 erase). Those writes compete with
  application traffic — this is exactly the mechanism behind the sudden
  latency spikes when a drive stalls to GC.

The **write amplification factor** is the invoice:

```text
        physical page writes            app writes + GC copy writes
WAF =  -----------------------  =  --------------------------------------
         logical page writes                 app writes
```

## The over-provisioning trade

**Over-provisioning (OP)** is physical capacity beyond the user-visible
capacity — the striping slack GC needs to work. More OP → more freely
selected victims → less copying → lower WAF and longer life, at the price of
silicon you paid for but cannot address. The simulator below runs a
log-structured greedy FTL over a uniform-random 4 KB workload (the worst
case), for OP from 7% (typical client) to 28% (typical enterprise), and
compares measured WAF against the naive `1/op` bound that assumes every
victim holds `1−op` valid pages — greedy's order-statistics advantage beats
that bound handily:

```python
"""Greedy-GC FTL simulator: write amplification vs over-provisioning.

Model: log-structured FTL over B blocks of P pages. User LBAs live in a
(1-op) fraction of physical pages (op = over-provisioning). App writes are
4 KB, uniform-random over the LBA space (the GC worst case). When free
blocks drop below a watermark the FTL reclaims the victim with the FEWEST
valid pages, copies its valid pages to the log, and erases it.

WAF = physical page writes / logical (app) page writes.
Seed fixed -> identical output on every run.
"""
import random

B, P = 512, 128            # blocks, pages per block
WRITES = 300_000           # logical 4KB writes per run
WATERMARK = 4              # keep at least this many free blocks


def run(op, seed=42):
    rng = random.Random(seed)
    user = int(B * (1 - op)) * P                 # logical address space size
    blocks = [[None] * P for _ in range(B)]      # page -> LBA or None
    valid = [0] * B                              # per-block valid-page count
    fwd = {}                                     # lba -> (block, page)
    free = list(range(int(B * (1 - op)), B))     # never-written pool
    cur, pg = -1, P                              # current open block, page ptr
    phys_writes = 0
    victims = []
    in_gc = False                                # no nested GC during copies

    def append(lba):
        """Write one page to the log (app write or GC copy)."""
        nonlocal cur, pg, phys_writes
        if pg == P:
            if not in_gc:
                while len(free) < WATERMARK and gc_once():
                    pass
            cur, pg = free.pop(0), 0
        blocks[cur][pg] = lba
        valid[cur] += 1
        fwd[lba] = (cur, pg)
        pg += 1
        phys_writes += 1

    def gc_once():
        """Reclaim the min-valid sealed block; False if only full blocks remain."""
        nonlocal in_gc
        cand = [i for i in range(B) if i != cur and i not in free]
        v = min(cand, key=lambda i: valid[i])
        if valid[v] == P:                        # nothing reclaimable yet
            return False                         # defer: no slack to mine
        victims.append((v, valid[v]))
        entries = [(j, lba) for j, lba in enumerate(blocks[v])
                   if lba is not None]
        for j, lba in entries:
            fwd.pop(lba, None)                   # old location dies
        blocks[v] = [None] * P                   # erase BEFORE reuse
        valid[v] = 0
        free.append(v)                           # back of the queue
        in_gc = True
        for j, lba in entries:
            append(lba)                          # copy = one physical write
        in_gc = False
        return True

    for _ in range(WRITES):
        lba = rng.randrange(user)
        old = fwd.get(lba)
        if old is not None:                      # invalidate previous copy
            blocks[old[0]][old[1]] = None
            valid[old[0]] -= 1
        append(lba)

    return phys_writes / WRITES, victims[-5:]


print(f"greedy GC, B={B} blocks x P={P} pages, uniform 4KB writes, seed=42")
print(f"{'OP%':>4} {'WAF (sim)':>10} {'naive 1/op bound':>18}")
for op in (0.07, 0.11, 0.14, 0.20, 0.28):
    waf, v = run(op)
    print(f"{op*100:4.0f} {waf:10.2f} {1/op:18.2f}")
print()
print("last five victims (block id, valid pages copied) at OP=28%, steady state:")
_, v = run(0.28)
for blk, n in v:
    print(f"  block {blk:3d}: {n:3d}/{P} valid copied")
```

```text
greedy GC, B=512 blocks x P=128 pages, uniform 4KB writes, seed=42
 OP%  WAF (sim)   naive 1/op bound
   7       3.98              14.29
  11       3.12               9.09
  14       2.75               7.14
  20       2.24               5.00
  28       1.75               3.57

last five victims (block id, valid pages copied) at OP=28%, steady state:
  block 241:  65/128 valid copied
  block 343:  64/128 valid copied
  block 353:  64/128 valid copied
  block 253:  64/128 valid copied
  block 405:  64/128 valid copied
```

Reading the victim trace: at 28% OP the greedy FTL finds victims holding only
~64 of 128 valid pages, so reclaiming one costs half a block of copying —
WAF ≈ 1.75. Drop OP to 7% and victims improve slower than demand grows:
WAF approaches 4, i.e. every 1 GB you write makes the NAND absorb ~4 GB.
Agrawal et al. measured the same curve shape on real controller designs
([ATC 2008](https://dl.acm.org/doi/10.5555/1404014.1404019)) and drew the
practical consequence: workload, OP, and mapping design must be chosen
*together*, because the same drive can span 5× WAF across workloads.

## Wear leveling: static, dynamic, and the cold-data problem

Erase cycles are the budget; wear leveling spends it evenly.

- **Dynamic wear leveling** falls out of log-structured writing: hot writes
  naturally spread across free blocks. It only rotates *hot* blocks.
- **Static wear leveling** migrates *cold* data — the root filesystem image
  parked in one block since installation — so dormant blocks join the
  rotation. The trigger is usually a max-erase-count delta between the
  youngest and oldest blocks; the cost is relocating cold pages nobody was
  going to touch, which is why drives do it lazily and in the background.

Hot/cold separation interacts with GC itself: mixing a hot 10% LBA range
with a cold 90% range makes victims cheap (hot blocks die fast), but *all-*
cold or *all*-hot uniform workloads deny greedy GC its leverage. Key-value
stores built on flash ([FlashStore](https://www.vldb.org/pvldb/vldb2010/papers/R29.pdf))
exploited this deliberately — choosing evictions and layouts to keep GC cost
predictable rather than merely minimizing drive-level WAF.

## TRIM/discard: telling the FTL what it may forget

Without help, the FTL cannot know that a deleted file's pages are dead — the
host filesystem still "owns" those LBAs. **TRIM** (ATA) / **DSM Deallocate**
(NVMe, see [NVMe](../nvme.md)) / `UNMAP` (SCSI) pass that information down:
subsequent GC can skip copying pages it now knows are garbage. Without TRIM,
steady-state random writes after deletions behave as if every dead page were
live — WAF creeps toward the `1/op` bound. On Linux,
[fstrim(8)](https://man7.org/linux/man-pages/man8/fstrim.8.html) batches this
weekly from fstab's `discard` mount-time sibling; the
[block I/O path](../../linux/storage/block-io.md) carries it as REQ_OP_*
commands down the stack. Two caveats worth quoting in interviews:
TRIM is a *hint* — drives may defer or ignore it; and on thin-provisioned
SAN arrays, UNMAP doubles as capacity reclamation, changing the economics
entirely (see [block storage](../block-storage.md)).

## SLC cache tiers and the write cliff

Modern TLC/QLC drives fake fast writes by programming part of the NAND in
**SLC mode** (one bit per cell instead of 3–4): far more durable and much
faster to program. A burst lands in the SLC cache at ~hundreds of MB/s to
GB/s; then the controller folds it down to TLC in the background. Two
consequences:

1. **The write cliff.** Outlast the SLC cache (or fill it on a nearly-full
   drive) and throughput drops to the raw TLC program rate plus GC — often
   3–10× slower. Sustained-copy benchmarks expose it; bursty office
   workloads never see it.
2. **Fold amplification.** SLC→TLC migration is itself a copy pass, so the
   cache trades peak latency for background WAF — which is why capacity-fill
   state and cache size appear in enterprise drive datasheets.

This is also why "random 4 KB writes destroy throughput": random writes (a)
defeat locality so every victim is expensive, (b) thrash the mapping cache in
DFTL-style designs, and (c) fill the SLC tier faster than folding drains it.
The fix at the *system* level is to stop issuing random small writes at all —
sequentialize in software (log-structured stores, [LSM compaction](../lsm-compaction.md),
or [LSM trees](../../dbms/internals/lsm-trees.md)), batch into erase-block-sized
runs, or push the log into zones ([ZNS](./zns-zoned-storage.md)) where the
host owns GC outright.

## Numbers worth memorizing

| Quantity                        | Typical value                | Why it matters                          |
|---------------------------------|------------------------------|-----------------------------------------|
| Page size (program/read unit)   | 4–16 KB                      | read-modify granularity; alignment      |
| Block size (erase unit)         | 64–256 pages (2–6 MiB)       | GC copy quantum; why small writes hurt  |
| Read / program / erase latency  | ~50 µs / ~0.5 ms / ~5 ms     | 100:1 program:read, 1000:1 erase:read   |
| P/E endurance (TLC / MLC / SLC) | ~1–3k / ~3–10k / ~50–100k    | drives the entire wear-leveling story   |
| Client vs enterprise OP         | ~7% vs ~14–28%               | the WAF lever you can actually turn     |
| WAF, uniform random @ 7% OP     | ~4 (greedy, 128-page blocks) | why "fill the drive and it crawls"      |

## Interview lens

- **Why can't SSDs update in place?** Program pages 1→0 only; reset requires
  a block-wide erase. Everything else follows from this one sentence.
- **Where does the mapping table live, and how big is it?** Per-page mapping
  is ~1–2 GB/TB; DFTL keeps a hot window in RAM, hybrid designs keep a log
  region. Follow-up: what does a map miss cost? An extra flash read.
- **What happens when you copy 200 GB onto a half-full consumer TLC drive?**
  SLC cache absorbs the burst, then folds in background; sustained rate
  collapses to TLC+GC speed. The datasheet number is the burst, not the cliff.
- **Why does TRIM improve WAF if it deletes no data?** It converts
  "unknown, must copy" pages into known-garbage pages GC can skip — victims
  get cheaper without any OP change.
- **Why do ZNS drives exist?** They hand the log-structured append-only
  discipline to the host, deleting the FTL's GC, mapping, and replication
  redundancy — the endgame of the reasoning above.

## Where this connects

- [SSDs](../ssd.md) — the overview layer this page quantifies; [NVMe](../nvme.md)
  for DSM/TRIM and flush semantics.
- [ZNS / zoned storage](./zns-zoned-storage.md) — moving GC into the host.
- [LSM compaction](../lsm-compaction.md) — the workload shape that keeps FTLs
  cheap by writing sequentially at erase-block granularity.
- [Block I/O](../../linux/storage/block-io.md) and the
  [NVMe driver](../../linux/kernel/drivers/nvme.md) — where discard and flush
  commands originate in the kernel.

## References

1. Agrawal, Arpaci-Dusseau, Arpaci-Dusseau, "Design Tradeoffs for SSD
   Performance", USENIX ATC 2008 — <https://dl.acm.org/doi/10.5555/1404014.1404019>
   (ACM DL blocks scripted fetches with HTTP 403; existence and metadata
   verified via web search during writing)
2. Gupta, Kim, Urgaonkar, "DFTL: a Flash Translation Layer Employing
   Demand-based Selective Caching of Page-level Address Mappings", ASPLOS
   2009, DOI 10.1145/1508244.1508271 (crossref-verified) — <https://doi.org/10.1145/1508244.1508271>
3. Debnath, Sengupta, Li, Lilja, Du, "FlashStore: High Throughput Persistent
   Key-Value Store", PVLDB 3(1), 2010, DOI 10.14778/1920841.1921015 (crossref-
   verified) — <https://www.vldb.org/pvldb/vldb2010/papers/R29.pdf>
4. `fstrim(8)` man page, Linux man-pages project — <https://man7.org/linux/man-pages/man8/fstrim.8.html>
5. Intel Corporation, "Understanding the Flash Translation Layer (FTL)
   Specification", 1998 (original block-mapping FTL; primary source mirrored
   on document repositories — retrieved via search, direct host no longer
   online)
