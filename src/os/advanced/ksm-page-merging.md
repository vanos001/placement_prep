# KSM Page Merging: Content-Keyed Trees, Fault Paths, and Side Channels

Kernel Same-page Merging (KSM) scans registered anonymous memory, finds 4 KiB pages with byte-identical contents, and collapses each duplicate group onto a single write-protected frame. Merged into Linux 2.6.32 (2009, Red Hat; Izik Eidus, Andrea Arcangeli, Chris Wright) for VDI overcommit, it is simultaneously a memory saver, a CPU cost-model exercise, and a published timing side channel. This page is the design deep-dive: the two content-keyed red-black trees, the ksmd scan loop, the COW fault path, rmap/swap interactions, UKSM's reengineering, and the dedup-timing attack literature. The sysfs cookbook and ops-side tuning live in the companion page [linux/kernel/memory/ksm.md](../../linux/kernel/memory/ksm.md).

## Why dedup needs two trees, not one

The naive design - a sorted index of page contents - breaks because KSM does not own the pages it indexes: any owner can write at any time, invalidating the sort order. KSM's answer ([mm/ksm design doc](https://docs.kernel.org/mm/ksm.html)) is a pair of red-black trees plus a volatility filter:

- **Stable tree**: holds every merged page (a "KSM page"), keyed by content. Its pages are write-protected, so the order cannot rot, and the tree is never flushed. Each node carries the reverse-mapping items (`ksm_rmap_item`s) for the VMAs sharing that frame.
- **Unstable tree**: holds not-yet-merged candidates, also keyed by content. Their contents are *not* write-protected, so the tree is corruptible by design and is flushed and rebuilt after every full scan pass.
- **Checksum filter**: a page may enter the unstable tree only if its checksum (`calc_checksum()`, xxhash over the full page) is unchanged since its previous visit, so frequently written pages never enter the ordering at all (counted as `pages_volatile`).

```text
   stable tree (RB, keyed on page bytes, never flushed)
   +---------------------------------------------------+
   | node = ksm_stable_node   <-- page->mapping        |
   |   +-- rmap_item list: (mm,addr) x N sharers       |
   |   +-- "chain" of "dups" once N hits max_page_     |
   |        sharing (default 256)                      |
   +---------------------------------------------------+
   unstable tree (RB, keyed on page bytes, flushed per pass)
   +---------------------------------------------------+
   | rmap_item -> (mm,addr), oldchecksum unchanged     |
   +---------------------------------------------------+
          ksmd cursor: one global struct ksm_scan
          mm_slot -> address -> rmap_list -> seqnr
```

Three choices here are unusual and worth naming. **The key is the content itself**: tree descent uses `memcmp_pages()`, not a stored hash; the xxhash checksum exists only as a change detector, so no hash-collision handling is needed at merge time because equality is proven byte-wise. **The unstable tree is allowed to be wrong**: a mid-scan write can leave a node where its new content no longer belongs; the red-black property is maintained by *color*, not key order, so a corrupted tree still has bounded height - it may miss matches, but never blow up, until the next flush. **The stable tree is never speculatively pruned**: stale entries are cleaned only when the sharing limit is hit, on the `stable_node_chains_prune_millisecs` timer (default 2000 ms).

| Property | Stable tree | Unstable tree |
|---|---|---|
| Contents | merged (write-protected) pages | stable-looking candidates |
| Key | page bytes via memcmp | page bytes via memcmp |
| Lifetime | never flushed | rebuilt after each full pass |
| Corruption policy | N/A (write-protected) | tolerated; color keeps balance |
| Insert rule | on byte-exact match | only if checksum unchanged |

## The ksmd scan loop and its knobs

ksmd is a single kernel thread (`ksm_do_scan()`) driven by one global cursor: it walks mm slots, then VMAs, then candidate addresses, visiting `pages_to_scan` pages per cycle and sleeping `sleep_millisecs` between cycles ([admin guide](https://docs.kernel.org/admin-guide/mm/ksm.html)). The defaults are deliberately conservative; a full sweep of a large workload at defaults takes weeks, so deployments tune them.

| Knob (`/sys/kernel/mm/ksm/`) | Default | Meaning / trap |
|---|---|---|
| `pages_to_scan` | 100 | pages per cycle; doubles as CPU throttle |
| `sleep_millisecs` | 20 | sleep between cycles; sets convergence latency |
| `merge_across_nodes` | 1 | 0 = per-NUMA-node tree pairs; change needs `run=2` unmerge first |
| `run` | 0 | 0 stop (keep merges), 1 run, 2 stop and unmerge everything |
| `use_zero_pages` | 0 | merge all-zero pages to the shared zero page |
| `max_page_sharing` | 256 | dedup ceiling per frame; bounds O(N) rmap walks |
| `smart_scan` (6.7+) | 1 | skip pages that failed to dedup before (`pages_skipped`) |
| `advisor_mode` (6.8+) | none | `scan-time` auto-tunes `pages_to_scan` (CPU cap 70%) |
| `stable_node_chains_prune_millisecs` | 2000 | stale dup-pruning frequency |

Registration is per-VMA via `madvise(MADV_MERGEABLE)` or per-process via `prctl(PR_SET_MEMORY_MERGE)` (Linux 6.4+). THP interplay: KSM wants order-0 pages, so it splits transparent huge pages found in the scan path (`split_huge_page()` in mm/ksm.c) - enabling KSM on THP-backed heaps quietly converts them back to 4 KiB pages.

## Merge path and the write-protect fault path

Merging two candidates is a three-step dance under page lock, with mmu-notifier invalidations for virtualized users:

```text
 ksmd: write_protect_page(A)         ksmd: replace_page(A -> B)
       - clear pte write bit               - repoint pte A to new KSM page
       - flush TLB range                   - drop ref on A
       - mark dirty (reclaim may           - A freed to allocator
         treat it as cold)           B becomes a KSM page; the stable
                                     tree gains one node.
```

The interesting path is the *first write* by any sharer - the write-protect fault is the unmerge mechanism. `handle_pte_fault` sees a present, write-protected PTE and calls `do_wp_page`; `wp_page_copy` allocates a fresh anonymous page, copies the KSM frame's content, and repoints the faulting PTE (other sharers keep mapping the KSM frame, so sharing drops by one); the `rmap_item` for that (mm, addr) is retired, and if the page stabilizes again, ksmd re-merges it from scratch.

Foreign writers take a second path: `get_user_pages()` with `FOLL_FORCE|FOLL_WRITE` (ptrace, `process_vm_writev`) cannot service writes into a write-protected KSM frame, so `break_ksm()` walks the range and injects a real write fault (`handle_mm_fault` with `FAULT_FLAG_WRITE`) to force the same COW. ksmd itself uses the identical machinery (`break_cow()`) when a checksum shows a merged page's twin has drifted. Note the asymmetry: **merging is batch and slow; unmerging is per-fault and immediate** - workloads that write merged pages pay fault + copy + full rescan each time.

## rmap, swap, and migration interplay

A KSM frame is an anonymous page whose `page->mapping` points at its stable tree node instead of an anon_vma. Consequences:

- **rmap walks are bespoke** (`rmap_walk_ksm`): migration, compaction, NUMA balancing, and swap all find sharers by walking the stable node's rmap items - O(number of sharers), capped by `max_page_sharing`. High sharing makes dedup cheap but every migration of that frame slower; the chain-of-dups scheme keeps tree lookup O(log n) while spreading the linear walk across frames.
- **Swap-out keeps sharing; swap-in breaks it.** A KSM frame sits in the swapcache like any anon page; when reclaim swaps it, all sharers get swap entries against one slot. Swapping *back in* always produces a private copy (the `KSM_SWPIN_COPY` vmstat), so swap churn silently erodes dedup and pushes work back onto ksmd.
- **Reclaim is encouraged**: merged pages are marked dirty on creation precisely so page reclaim will consider them swappable.

## UKSM: reengineering the scan

[UKSM (Ultra KSM, Nai Xia)](https://github.com/dolohow/uksm) is the best-known out-of-tree rewrite of the scanner. Its thesis: tree mechanics are not the bottleneck - visiting pages is. Its changes:

- **Full-system scan with no madvise contract**: all anonymous VMAs become candidates automatically.
- **Rich-area detection**: duplicate-dense regions get full scan speed; poor regions are sampled at a low rate.
- **Cheaper per-page probing**: a faster hash plus x86-optimized 4-byte-aligned `memcmp`; the author's benchmark quotes 627-2445 MB/s scans of duplicate-free regions and 477-923 MB/s merges.
- **Thrashing-area avoidance**: VMAs whose pages keep breaking out of the stable tree are demoted, generalizing the per-page checksum filter to per-area policy.

In-tree, the same ideas arrived gradually: `smart_scan` (6.7) skips previously-unmergeable pages, the scan-time advisor (6.8) closes the control loop around `pages_to_scan`, and [DAMON](../../linux/kernel/memory/damon.md) supplies the access-pattern telemetry an adaptive deduplicator really wants.

## Security: memory deduplication as a timing oracle

Merging gives an attacker a physical, cross-tenant equality oracle: if a page I control has the same bytes as a page I cannot read, KSM merges them, and the latency of the next access (or of the dedup itself) reveals the equality.

- [Suzaki et al., EuroSec 2011](https://doi.org/10.1145/1972551.1972552) demonstrated cross-VM memory disclosure through KSM: a guest writes a guess (a version string, a pointer value), KSM's merge latency confirms it, and repetition leaks secrets byte-group by byte-group.
- [Bosman et al., "Dedup Est Machina", IEEE S&P 2016](https://www.vusec.net/projects/dedup-est-machina/) turned dedup into a full exfiltration and exploitation channel from JavaScript: dedup supplies the cross-context flush+reload building block that same-origin isolation was supposed to deny, and a Rowhammer flip in a deduplicated frame then crosses the last privilege boundary (flip mechanics: [rowhammer](../../arch/advanced/rowhammer.md)). Microsoft's fix was to disable memory deduplication by default in Windows 10 (CVE-2016-3272).

| Mitigation | Mechanism | Cost |
|---|---|---|
| Disable KSM on untrusted co-tenancy | no dedup, no oracle | lost overcommit |
| Per-VM content randomization | identical secrets no longer byte-equal | breaks most dedup |
| Fake merges / dedup fuzzing (Lindemann, ACSAC 2024, [DOI](https://doi.org/10.1109/acsac63791.2024.00043)) | dedup latency no longer implies equality | scan CPU, latency noise |
| Merge only zero pages | oracle restricted to a public value | tiny savings |

One-line summary: **dedup converts a confidentiality boundary into a latency signal.** Any design merging on content across a trust boundary inherits this - KSM, Windows dedup, dedup filesystems.

## Free page reporting: the balloon's other direction

Classic virtio-balloon works host-to-guest: the host inflates the balloon, the guest allocates and holds pages, freeing them to the host. Free page reporting (Alexander Duyck, Linux 5.7, [mm doc](https://docs.kernel.org/mm/free_page_reporting.html)) is guest-to-host: when the guest frees sufficiently large contiguous ranges, it reports them to the host before reuse; the host can zero, dedup, or reallocate them, then hands them back. The relationship to KSM is complementary: KSM mines *identical live* memory, free page reporting returns *free* memory before fragmentation hides it. VDI deployments typically run both.

## When KSM wins and when it loses

| Workload | Outcome | Why |
|---|---|---|
| VDI fleets (many same-OS guests) | big win | OS pages, runtimes, libraries byte-equal across guests |
| JVM/managed heaps at rest | good win | class metadata, interned strings, headers repeat; hot gen-0 churn needs `sleep_millisecs` headroom |
| Idle container overlays | good win | identical base-image pages across pods |
| Crypto, randomized allocators | lose + risk | unique content never merges; merged keys become an oracle |
| Hot written heaps | lose | fault + copy + rescan per write; checksum filter excludes most pages anyway |
| Swap-churny tenants | lose | every swap-in is a private copy (`KSM_SWPIN_COPY`) |
| NUMA-latency-sensitive HPC | lose | merged frame may live on the wrong node unless `merge_across_nodes=0` |

Rule of thumb: KSM pays when **(identical-page fraction) x (saved bytes) > (scan CPU + fault tax + security risk)** - a statement the demo below turns into numbers.

## Demo: savings saturate, scan cost does not

The simulation mirrors KSM's algorithm on synthetic memory: 1500 pages, 25% converging onto VDI templates and JVM-style header groups over time, plus 10% permanently "hot" pages. The scan-rate knob (`pts` = pages_to_scan per cycle, fixed 400-cycle budget, sleep 20 ms) trades convergence speed against total memory read by ksmd. `MB/GB` is time-integrated savings per gigabyte actually read.

```python
# KSM-style dedup: savings vs scan-rate cost. Pure stdlib; pages are
# synthetic 4096-byte anonymous pages scanned by a ksmd-like cursor.
import random, zlib
PAGE, N, CYCLES = 4096, 1500, 400
random.seed(20260814)

class P:
    def __init__(s, i):
        s.i, s.content, s.crc, s.oldcrc = i, random.randbytes(PAGE), None, None
        s.crc = s.oldcrc = zlib.crc32(s.content)
        s.born = random.randint(0, 60)
        s.stab = max(s.born + 5, int(random.gauss(30, 10)))
        s.snap, s.hot = None, random.random() < 0.10
        s.canon, s.group = s, []          # merge-group bookkeeping

pages = [P(i) for i in range(N)]
for p in pages[120:495]:                  # 375 VDI pages -> 120 base templates
    p.snap = random.choice(pages[:120]).i
for g in range(60):                       # 60 JVM-style groups of 6 pages
    pages[855 + g].stab = min(pages[855 + g].stab, 20)
    for k in range(6):
        pages[495 + 6 * g + k].snap = pages[855 + g].i

def tick(t):                              # memory evolves with time
    for p in pages:
        if t == p.stab and p.snap is not None and t >= p.born:
            p.content = pages[p.snap].content           # boot converges
            p.crc = zlib.crc32(p.content)
        elif p.hot and t >= p.born and t % 7 == p.i % 7:
            p.content = random.randbytes(PAGE)          # thrash: keep writing
            p.crc = zlib.crc32(p.content)

def run(pts, st):                         # one ksmd configuration
    stable, unstable, cur, vis, saved = {}, {}, 0, 0, 0
    for t in range(CYCLES):
        tick(t)
        for _ in range(pts):
            p = pages[cur]; cur = (cur + 1) % N
            if cur == 0 and unstable: unstable.clear()  # sweep end: flush
            if t < p.born: continue
            vis += 1; st["read"] += PAGE
            ch = p.oldcrc != p.crc; p.oldcrc = p.crc
            if ch and p.group:                       # fault on canonical
                for q in p.group: q.canon = q
                st["brk"] += len(p.group); saved -= PAGE * len(p.group)
                p.group = []
            elif ch and p.canon is not p:            # fault on sharer
                p.canon.group.remove(p); p.canon = p
                st["brk"] += 1; saved -= PAGE
            if ch or p.canon is not p or p.group: continue
            if p.content in stable:
                c = stable[p.content]
                if c is not p and c.content == p.content:
                    c.group.append(p); p.canon = c
                    st["mrg"] += 1; saved += PAGE; continue
            if p.content in unstable:
                q = unstable[p.content]
                if q is not p and q.content == p.content:
                    stable[p.content] = p; p.group.append(q); q.canon = p
                    st["mrg"] += 1; saved += PAGE; continue
            unstable[p.content] = p
        st["int"] += saved
    return vis, saved

mb = lambda b: b / 1048576
print(f"KSM dedup vs scan rate (N={N} pages, {CYCLES} cycles, sleep=20 ms)")
hdr_str = (f"{'pts':>5} {'sweeps':>6} {'visits':>7} {'read_MB':>8} "
           f"{'merges':>6} {'breaks':>6} {'avg_MB':>7} {'end_MB':>7} {'MB/GB':>6}")
print(hdr_str)
print("-" * len(hdr_str))
for pts in (40, 160, 600, 1500):
    for p in pages: p.canon, p.group, p.oldcrc = p, [], p.crc
    st = {"read": 0, "mrg": 0, "brk": 0, "int": 0}
    vis, end = run(pts, st)
    print(f"{pts:>5} {vis/N:>6.1f} {vis:>7d} {mb(st['read']):>8.0f} "
          f"{st['mrg']:>6d} {st['brk']:>6d} {mb(st['int']/CYCLES):>7.2f} "
          f"{mb(end):>7.2f} {mb(st['int'])/(mb(st['read'])/1024):>6.1f}")
print()
print("Savings saturate near 2.4 MB (375 VDI + 300 JVM-header groups, less")
print("thrash losses); scan cost keeps climbing - the case for smart_scan.")
```

Real output (this exact script, run locally):

```text
KSM dedup vs scan rate (N=1500 pages, 400 cycles, sleep=20 ms)
  pts sweeps  visits  read_MB merges breaks  avg_MB  end_MB  MB/GB
------------------------------------------------------------------
   40    9.9   14787       58    610      0    1.81    2.38 12841.7
  160   39.5   59202      231    623     13    2.15    2.38 3803.9
  600  148.0  222010      867    710    100    2.17    2.38 1026.2
 1500  370.0  555057     2168    741    131    2.18    2.38  411.7

Savings saturate near 2.4 MB (375 VDI + 300 JVM-header groups, less
thrash losses); scan cost keeps climbing - the case for smart_scan.
```

Every rate reaches the same ~2.38 MB ceiling - dedup is a *saturation* resource - but the slowest rate arrives ~4x later while reading 37x less memory. Past ~600 pages/cycle, extra scans mostly re-read immutable merged frames (what `smart_scan` skips) and merge then break thrash-prone hot pages (the `breaks` column - the cost `advisor_mode` and UKSM's thrashing-area avoidance exist to suppress).

## Interview angles

- Why two trees? What does a single content-keyed tree do the moment an owner writes one byte into a mid-tree node?
- A write fault on a KSM page costs more than a plain COW fault: enumerate the extra work and connect it to the `breaks` column of the demo's high-rate rows.
- A tenant asks you to enable KSM in a multi-tenant pool: name the attack (with citation) and the mitigations you would price first.

## References

1. Kernel admin guide, "Kernel Samepage Merging": <https://docs.kernel.org/admin-guide/mm/ksm.html>
2. Kernel mm design doc (Eidus/Dickins, 2009), stable/unstable tree + rmap internals: <https://docs.kernel.org/mm/ksm.html>
3. K. Suzaki, K. Iijima, T. Yagi, C. Artho, "Memory deduplication as a threat to the guest OS", EuroSec 2011, <https://doi.org/10.1145/1972551.1972552>
4. E. Bosman, K. Razavi, H. Bos, C. Giuffrida, "Dedup Est Machina: Memory Deduplication as an Advanced Exfiltration Channel", IEEE S&P 2016, <https://www.vusec.net/projects/dedup-est-machina/>
5. UKSM patchset (Nai Xia), README with design + benchmark figures: <https://github.com/dolohow/uksm>

Further reading: LWN on the original proposals (["/dev/ksm: dynamic memory sharing"](https://lwn.net/Articles/306704/), ["KSM tries again"](https://lwn.net/Articles/330589/)). Related pages: [memory-internals](./memory-internals.md), the COW machinery in [cow](../virtual-memory/cow.md), KSM in a container-memory Q&A in [virtual-memory/README](../virtual-memory/README.md).
