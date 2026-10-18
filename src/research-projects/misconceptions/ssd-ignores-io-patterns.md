# "SSDs make I/O patterns irrelevant"

## Overview

This page examines the claim that flash storage retired the old wisdom about
I/O access patterns: if random reads cost roughly the same as sequential
reads, the argument goes, database layouts, file formats, and index choices
no longer need to care about locality. The claim is half right, and the
wrong half is expensive. Random *reads* genuinely got cheap on flash. Random
*writes* still pay — through erase-block geometry, flash translation layers,
garbage collection, and write amplification — `fsync` remains the unit of
durability, and the read-amplification-versus-write-amplification trade
between B-trees and LSM-trees is, if anything, *more* visible on flash than
it was on disk. This page states the claim fairly and works the numbers.

## The Claim, Stated Fairly

The strongest common form of the claim is: "An SSD does not care whether you
read or write randomly or sequentially, so data layout is a solved problem —
any index, any row order, any write pattern performs the same. The HDD-era
advice about sequential I/O and locality is obsolete." Stated this way, the
claim is not a caricature; it is the reasonable extrapolation of two facts
everyone has experienced: SSDs show no seek noise, and the old "defragment
your disk" rituals are dead.

The claim deserves its fairness because the kernel is real. On a hard disk,
a 4 KiB random read pays a seek plus rotational delay — single-digit
milliseconds of pure geometry — while a sequential read pays it once per
run. On an NVMe SSD there is no mechanical head to move, and the device can
serve many reads in parallel across flash channels. For read-dominated
workloads the pattern penalty collapsed from two orders of magnitude to a
small constant. The question is whether the write path honestly compresses
to "irrelevant".

## Verdict

**Incomplete.** The claim is true in the read regime and false in the write
regime: random writes still cost multiples of sequential writes on sustained
workloads, `fsync` still bounds commit durability, and layout choices still
change real performance by several times — the claim omits the preconditions
that void it.

## Why People Believe It

The kernel of truth is threefold. First, the read side really did collapse:
a typical NVMe device serves a 4 KiB random read at queue depth 1 in tens of
microseconds, versus roughly 5–10 ms of seek-plus-rotation on a hard disk —
a ratio near 100× in favor of flash (magnitudes from public device
documentation, not a new measurement). Second, the visible symptoms
disappeared: files no longer fragment into seek storms, and copying many
small files no longer audibly thrashes. Third, flash marketing and even
some documentation emphasize "no moving parts", which reads as "no
mechanics, therefore no geometry, therefore no patterns."

What disappears in compression is NAND's write asymmetry: reads address any
page directly, but writes can only *program* empty pages, and pages can only
be erased in blocks far larger than a page. That asymmetry is intrinsic to
the medium, not an implementation detail, and everything expensive on the
write path follows from it.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Random I/O is as cheap as sequential" | Random reads: near-cheap within device parallelism. Random writes: still several times slower sustained |
| "The device hides everything" | The FTL hides geometry from the *interface*, not physics from the *cost model* — erase blocks, GC, and write amplification are billed to your workload |
| "Durability is automatic" | `fsync` (or equivalent) remains the durability boundary; the FTL never promises your data survived an unflushed write |
| "Layout no longer matters" | Read amplification vs write amplification still trades off; B-tree vs LSM is a flash-era decision, not a disk-era relic |
| "Planners know this" | PostgreSQL's planner still prices random access higher (`random_page_cost` default 4.0 vs `seq_page_cost` 1.0) — a documented acknowledgment that pattern still costs |

The correct sentence: "Flash removed the mechanical penalty from random
*reads*; it did not remove the asymmetry between programming pages and
erasing blocks. Sequential still wins, writes still pay, and the durability
unit is still the flush."

## Where It Breaks

**Sustained random writes: the erase-block arithmetic.** NAND pages are
programmed individually but erased in blocks orders of magnitude larger
(commonly hundreds of KiB). Overwriting a 4 KiB page in place is
impossible; the flash translation layer (FTL) writes the new version
elsewhere, marks the old page stale, and periodically garbage-collects by
copying live pages out of worn blocks before erasing them. A random
overwrite workload turns this into a multiplier — write amplification
(WAF = NAND bytes written per logical byte written) — that vendor
documentation typically places around 2–5 for random-write mixes and worse
for the hostile ones (JEDEC's JESD218 endurance standard is built around
this reality). Do the arithmetic: a workload writing 200 MB/s of 4 KiB
records at WAF 4 is programming 800 MB/s of NAND, consuming endurance
4× faster and contending for the same channels your reads want. The pattern
you chose at the API did not become irrelevant; it became a bill.

**The burst-then-cliff illusion.** Consumer and client drives absorb writes
into a fast pseudo-SLC cache and fold it into TLC storage later. The
"Benchmark results: 2 GB/s!" number is the cache. Write past it — copying a
200 GB dataset onto a 1 TB drive whose fold cache is a few tens of GB
(typical magnitudes, flagged as reasoning from published vendor behavior) —
and sustained throughput drops to a fraction of the headline number,
*worst* for random patterns that force the most GC during the fold. Workloads
sized against the cache number discover the pattern dependence the claim
denied.

**fsync is still the durability unit.** The FTL may remap, cache, and delay
— it may not reorder durability away. A commit is durable when the flush
completes, and the flush cost is the transaction rate ceiling for
group-of-one commits: at ~1 ms per flush, a serially committing process tops
out near 1,000 commits/s; batching 64 commits per flush raises the ceiling
into the tens of thousands (reasoning arithmetic, not a benchmark). This is
why crash-recovery design — write-ahead logging, group commit, checksummed
pages — survived the flash transition unchanged: the file system journal and
the database WAL still exist to turn an unreliable write path into an
ordered durability contract.

**LSM vs B-tree: the trade that flash made sharper.** A B-tree updates
pages in place — a random-write pattern that the FTL converts into write
amplification, plus write-ahead-log traffic on top. An LSM-tree converts
random writes into sequential appends and pays instead in read
amplification and compaction — trading the medium's expensive direction
for its cheap one. O'Neil et al. designed the LSM-tree in 1996 for disk,
but its core bet — batch random writes into sequential ones — maps onto
flash's write asymmetry so well that flash-era engines made LSM a
first-class choice. If patterns truly did not matter, B-tree versus LSM
would be a coin flip; engine documentation treats it as the central design
decision.

## Practical Implications

- Benchmark sustained random *writes*, not cached bursts, before sizing a
  write-heavy service; read the WAF your workload induces where the vendor
  exposes it.
- Keep the fsync accounting: per-commit flush cost bounds your commit rate;
  group commit and WAL batching are still the levers they were on disk.
- For append-heavy or random-write-heavy paths, prefer designs that turn
  writes sequential (LSM engines, append-only files, segmented logs) or
  batch them (buffer pools, change buffering).
- Do not "optimize away" sequential layout work: columnar formats,
  partition ordering, and clustered indexes still pay rent on flash,
  especially for scans and prefetch-friendly reads.
- Capacity and over-provisioning are performance features: leaving free
  space lowers the GC tax; a nearly-full SSD is a slow SSD.
- Leave planner cost models enabled: if patterns were irrelevant,
  `random_page_cost` tuning would be pointless — it is not.

## Interview Questions

### If SSDs have no seek time, why does sequential I/O still beat random I/O?

Sequential still wins because flash writes cannot overwrite pages in place;
they program pages and erase large blocks, forcing the FTL to relocate data
and garbage-collect. Random writes maximize relocation and stale-page churn
(write amplification), and sequential reads still benefit from internal
parallelism and prefetch. A strong answer separates the read regime (where
random got cheap) from the write regime (where the asymmetry remains).

### What is write amplification, and where does the multiplier come from?

WAF is NAND bytes written divided by logical bytes written. Sources: FTL
garbage collection copying live pages before erasing, no-in-place-update
relocation, and fold operations from pseudo-SLC caches into denser storage.
At WAF 4, a 200 MB/s logical write rate programs 800 MB/s of NAND —
consuming endurance 4× faster. Vendor documentation typically shows 2–5 for
random-write mixes.

### Your engine team proposes switching an index from B-tree to LSM on NVMe hardware. What flash-specific reasoning supports and opposes it?

Supports: LSM converts random in-place updates into sequential appends,
playing to flash's cheap direction and reducing WAF for write-heavy mixes.
Opposes: compaction adds its own background write traffic and read
amplification; read-heavy workloads may pay more than the WAF they save.
The decision still hinges on the read/write mix and amplification budgets —
which is exactly why the "patterns are irrelevant" claim fails.

## Key Takeaways

- Flash collapsed the cost of random *reads*; it did not collapse the
  asymmetry between programming pages and erasing blocks.
- Random writes still cost multiples of sequential writes once caches are
  exhausted; WAF (typically 2–5) is the multiplier your pattern chose.
- `fsync` remains the durability unit; WAL, group commit, and crash
  recovery survived the SSD transition unchanged.
- LSM vs B-tree is the read-amplification-versus-write-amplification trade,
  sharpened — not retired — by flash.
- "No moving parts" removed one penalty, not the physics: pattern still
  bills, and the planner still knows it.

## Cross-References

- [Follow-up Tree: Database Indexes](../followup-tree/database-indexes.md)
  — the B-tree vs LSM escalation chain this claim tries to retire
- [Why-Not Handbook: Crash Recovery](../why-not-handbook/crash-recovery.md)
  — why the durability unit outlived the disk
- [LSM-Trees](../../dbms/internals/lsm-trees.md) — the log-structured
  mechanism described by O'Neil et al., in the repo's own treatment
- [Indexing Strategy](../../dbms/indexing-strategy.md) — layout decisions
  that still price locality
- [Journaling File Systems](../../os/filesystems/journaling.md) — the
  file-system side of the durability contract
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- M. Rosenblum and J. K. Ousterhout. *The Design and Implementation of a
  Log-Structured File System*. SOSP 1991 — the origin of trading random
  writes for sequential ones.
- P. O'Neil, E. Cheng, D. Gawlick, and E. O'Neil. *The Log-Structured
  Merge-Tree (LSM-Tree)*. Acta Informatica, 1996 — the write-batching
  data structure whose bet this page maps onto flash.
- JEDEC. *JESD218 — Solid-State Drive (SSD) Requirements and Endurance Test
  Method* — the endurance workloads that formalize write amplification,
  cited by standard number.
- PostgreSQL documentation. *Planner Cost Constants* — `random_page_cost`
  default 4.0 versus `seq_page_cost` 1.0.
  <https://www.postgresql.org/docs/current/runtime-config-query.html>
- Linux man-pages project. *fsync(2)* — "synchronize a file's in-core state
  with storage device": the interface that defines the durability boundary
  this page relies on.
  <https://man7.org/linux/man-pages/man2/fsync.2.html>
