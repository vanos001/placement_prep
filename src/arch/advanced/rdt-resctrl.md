# Intel RDT and Linux resctrl: Partitioning the Last-Level Cache

## The neighbor the scheduler cannot see

A two-socket server funnels every workload through two resources no kernel
scheduler controls: the per-socket last-level cache and the DRAM channels
behind it. CFS/EEVDF schedules CPU *time*, cgroups cap *memory*, qdiscs shape
*packets* -- but a streaming scan or a batch job rewrites the L3 eviction
pattern and saturates DIMM channels, and your OLTP p99 pays the bill. The
[noisy neighbors](../../cloud/noisy-neighbors.md) page catalogs this
interference from the production side -- taxonomy, diagnosis, tenancy ladder
-- and stops where the hardware starts. This page is the hardware half:
**Intel Resource Director Technology (RDT)** -- cache allocation (CAT),
memory bandwidth allocation (MBA), monitoring (CMT/MBM) -- and the Linux
**resctrl** filesystem that drives it. AMD implements the same interface as
AMD Platform Quality of Service; Arm's MPAM feeds the same resctrl interface
through its own driver.

RDT is silicon-enumerated (CPUID leaf 0x10; cpuinfo flags `cat_l3`,
`cqm_llc`, `mba`), so it is bare-metal territory -- clouds expose it only
where you own the host (see
[bare-metal clouds](../../cloud/bare-metal-clouds.md)). The interference tax
was priced before the silicon: Q-Clouds (EuroSys 2010); CAT reached
production in the Xeon E5-2600 v3 generation (Herdrich et al., HPCA 2016).

## Classes of service: the bitmask model

RDT's abstraction is the **class of service (CLOS)**: a small integer -- the
CLOSID, one per allocation class, often 16 on Intel server parts -- riding on
every memory request a logical CPU issues, driving two independent namespaces:

```text
      resctrl schemata file              hardware (SDM vol.3, ch.17)
   db:    L3:0=ff00     MB:0=70     batch: L3:0=00ff     MB:0=40
               |
               |  echo $pid > tasks  ->  kernel writes CLOSID+RMID into
               v                         IA32_PQR_ASSOC for that logical CPU
   CLOSID 1 (db)    --->  way mask 1111111100000000  CBM=ff00, MB ~70%
   CLOSID 2 (batch) --->  way mask 0000000011111111  CBM=00ff, MB ~40%
   every LLC access is tagged:  CLOSID -> which ways may hold/evict my lines
                                RMID   -> whose occupancy/bandwidth counters
```

Allocation is a **capacity bitmask (CBM)**: one bit per L3 way, `1` = "this
class may allocate here." Monitoring uses a separate namespace, the **RMID**:
a CLOSID decides where lines may go, an RMID decides whose counters light up.
[Side channels](./side-channels.md) notes the security flip: partitioned ways
shrink the prime+probe surface -- when they are real and tight.

## The resctrl filesystem

One mount produces the whole control plane (options: `cdp`, `cdpl2`,
`mba_MBps`, `debug`):

```text
# mount -t resctrl resctrl -o cdp /sys/fs/resctrl
/sys/fs/resctrl/
|-- info/L3/        num_closids cbm_mask min_cbm_bits shareable_bits
|                   sparse_masks     <- non-contiguous CBMs supported?
|-- info/L3_MON/    num_rmids  mon_features: llc_occupancy, mbm_total/local_bytes
|-- info/MB/        min_bandwidth bandwidth_gran delay_linear thread_throttle_mode
|-- schemata  tasks  cpus ...     <- DEFAULT (root) group: all tasks, all ways
|-- db/                           <- mkdir creates a CTRL_MON group
|   |-- schemata  tasks  cpus  mode  size
|   `-- mon_groups/txn/           <- MON group: monitoring only
|       `-- llc_occupancy  mbm_total_bytes  mbm_local_bytes
`-- batch/                        <- another CTRL_MON group
```

Three facts make it click. **Everything is a directory**: `mkdir db` creates
a resource group and the kernel assigns it a CLOSID (and an RMID); mkdir
fails when either is exhausted. **Everything is a file write**: allocation is
`echo "L3:0=ff00;1=ff00" > schemata`; monitoring is
`cat mon_groups/txn/llc_occupancy`. **Membership is explicit**: PIDs go to
`tasks` (or CPU bitmasks to `cpus`); anything unassigned runs in the default
group. Every write updates `info/last_cmd_status` (`ok`, or the exact
failure -- `mask f7 has non-consecutive 1-bits`). A group's `mode` file takes
`shareable`, `exclusive`, or `pseudo-locksetup`: cache pseudo-locking is real
-- resctrl can pin a fixed region into ways nothing else allocates.

## Allocation vs monitoring

| Feature | Divides | Unit | resctrl surface | cpuinfo flag |
|---|---|---|---|---|
| CAT (L3/L2) | LLC or L2 ways | capacity bitmask per class | `L3:0=ff00` in schemata | `cat_l3` |
| MBA | DRAM bandwidth | percent of max, in `bandwidth_gran` steps | `MB:0=70` in schemata | `mba` |
| CMT | LLC occupancy | bytes per RMID | `llc_occupancy` in MON groups | `cqm_llc` |
| MBM | DRAM traffic | bytes/s, total and local, per RMID | `mbm_total_bytes` / `mbm_local_bytes` | `cqm_mbm_*` |

Features are orthogonal -- a part may ship monitoring without allocation.
Newer extensions: BMEC (configurable MBM events), ABMC (assignable counters,
AMD), SMBA (throttling *slow* memory -- the CXL-tier traffic that
[CXL memory pooling](./cxl-memory-pooling.md) parks behind tiering), and
`io_alloc` (way carve-outs for device DMA -- where
[DPU and SmartNIC](./dpu-smartnic-offload.md) traffic lands in your LLC).

## Worked example: isolating the OLTP database

32 MiB, 16-way LLC. The database runs pinned to CPUs 16-31; batch analytics
lives on CPUs 0-15 and must stop hurting the database:

```text
# mount -t resctrl resctrl /sys/fs/resctrl
# mkdir /sys/fs/resctrl/db
# echo "L3:0=ff00" > /sys/fs/resctrl/db/schemata    # top 8 ways
# echo "MB:0=70"   >> /sys/fs/resctrl/db/schemata   # at most 70% bandwidth
# echo 1623        >  /sys/fs/resctrl/db/tasks
# mkdir /sys/fs/resctrl/db/mon_groups/txn
# cat /sys/fs/resctrl/db/mon_groups/txn/mbm_local_bytes
```

Batch stays in the default group. Before writing more schemata, check what
those CBMs do to the cache -- the checker models the three groups exactly as
the way-partitioning hardware sees them:

```python
# CBM (capacity bitmask) checker: does this schemata actually isolate?
# One 16-way L3 (2 MiB per way, 32 MiB) as resctrl's info/L3 + schemata describe it.
WAY_BITS, WAY_BYTES, MIN_CBM_BITS, SPARSE_OK = 16, 2 << 20, 2, False
SCHEMATA = {                # the "L3:0=<cbm>" line of each CTRL_MON group
    "db":      0xFF00,      # OLTP database: top half of the ways
    "batch":   0x00FF,      # batch analytics: bottom half
    "default": 0x00FF,      # root group left open on the bottom half
}
def valid(mask):
    s = f"{mask:0{WAY_BITS}b}".lstrip("0")        # ignore zeros above bit 0
    if mask & ~((1 << WAY_BITS) - 1): return "bits beyond way range"
    if not SPARSE_OK and "01" in s:       # kernel last_cmd_status wording
        return "non-consecutive 1-bits"
    return "ok" if bin(mask).count("1") >= MIN_CBM_BITS else "below min_cbm_bits"
names = sorted(SCHEMATA); mib = WAY_BYTES >> 20
print(f"L3 partition check: {WAY_BITS} ways x {mib} MiB = {WAY_BITS*mib} MiB"
      f"  (min_cbm_bits={MIN_CBM_BITS}, sparse_masks={int(SPARSE_OK)})")
print(f"\n{'group':9}{'schemata':12}{'cbm':8}{'ways':>4}{'capacity':>10}  validity")
for n in names:
    m, w = SCHEMATA[n], bin(SCHEMATA[n]).count("1")
    print(f"{n:9}{'L3:0='+format(m,'x'):12}0x{m:04x} {w:>3}  {w*mib:>4} MiB   {valid(m)}")
print("\npairwise shared ways:")
ov = {}
for i, a in enumerate(names):
    for b in names[i+1:]:
        n = bin(SCHEMATA[a] & SCHEMATA[b]).count("1")
        ov[a, b] = n
        print(f"  {a:8} x {b:8}: {n:>2}  -> {'SHARED' if n else 'exclusive'}")
own = [[n for n in names if SCHEMATA[n] & (1 << w)] for w in range(WAY_BITS)]
cont = sum(len(o) > 1 for o in own)
LET  = {"db": "D", "batch": "B", "default": "r"}
cell = lambda o: " *" if len(o) > 1 else (" " + LET[o[0]] if o else " -")
print("\nway# " + " ".join(f"{w:>2}" for w in range(WAY_BITS)))
print("own  " + " ".join(cell(o) for o in own))
print("     (D=db  B=batch  r=default  *=multiple owners)")
iso = [n for n in names if all(v == 0 for (a, b), v in ov.items() if n in (a, b))]
print(f"\ncontested ways: {cont}/{WAY_BITS} = {cont/WAY_BITS:.0%} of the LLC ({cont*mib} MiB)")
print(f"verdict: isolated groups: {', '.join(iso) or 'none'}; every other pair still collides")
```

Output (real run):

```text
L3 partition check: 16 ways x 2 MiB = 32 MiB  (min_cbm_bits=2, sparse_masks=0)

group    schemata    cbm     ways  capacity  validity
batch    L3:0=ff     0x00ff   8    16 MiB   ok
db       L3:0=ff00   0xff00   8    16 MiB   ok
default  L3:0=ff     0x00ff   8    16 MiB   ok

pairwise shared ways:
  batch    x db      :  0  -> exclusive
  batch    x default :  8  -> SHARED
  db       x default :  0  -> exclusive

way#  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15
own   *  *  *  *  *  *  *  *  D  D  D  D  D  D  D  D
     (D=db  B=batch  r=default  *=multiple owners)

contested ways: 8/16 = 50% of the LLC (16 MiB)
verdict: isolated groups: db; every other pair still collides
```

Read it the way the tags would. `db` owns eight ways (16 MiB) that batch
lines cannot evict -- that is the isolation. The bottom half is *contested*:
batch and the default group share ways 0-7, so neither is protected, and the
default group's residents (page cache, kernel, daemons) still collide with
analytics. Fix: a third group for batch plus a tighter default mask
(`L3:0=000f` shrinks the contested span to four ways). A CBM grants
*permission to allocate*; capacity accounting is popcount arithmetic, and the
mask is the state.

## What the silicon does

Per logical CPU, the kernel programs `IA32_PQR_ASSOC` with that CPU's
{CLOSID, RMID} pair; core and LLC paths tag each request as it lands in the
shared cache. Occupancy counters track tagged lines per RMID (CMT), MBM sums
tagged request traffic into total/local rates, and CAT way masks gate which
sets may allocate. Monitoring is approximate: freed RMIDs sit in limbo until
their occupancy drains, counts trail task migrations, and MBA throttles
requests with a delay-based response (`delay_linear` is informational), not a
per-class bandwidth meter.

## Pitfalls

- **Non-contiguous CBMs.** Many parts require consecutive 1s
  (`sparse_masks=0`); the kernel rejects `f7` outright, and `echo` errors are
  easy to miss unless you check `last_cmd_status`. Respect `min_cbm_bits`.
- **MBA percentages shift.** Values round up to `bandwidth_gran` steps, and a
  class's "10%" is not absolute (one thread at 10% and four threads at 10%
  pull different totals; `thread_throttle_mode=max` clamps SMT siblings). The
  `mba_MBps` mount option enables the software controller (`mba_sc`): a
  feedback loop reading MBM counters that holds actual bandwidth under the
  value you wrote.
- **CDP halves classes.** With `-o cdp`, L3 splits into `L3DATA`/`L3CODE`
  resources with independent masks; each class consumes a code+data pair, so
  usable CLOSIDs halve (SDM vol.3, ch.17). Worth it only when instruction
  pollution is a measurable share of the interference.
- **Ways are not bandwidth.** CAT bounds occupancy and eviction, not refill
  rate -- a tenant inside its own ways can still saturate DIMMs; MBA caps
  requests, not residency. They compose because they throttle different axes.

## Interview lens

- *What does a CLOSID give you that cgroups do not?* Cgroup weights schedule
  time; they cannot stop a running thread's lines from evicting yours. A
  CLOSID bounds residency itself -- the interference channel, not the rate.
- *DB p99 spikes; you have bare metal and resctrl. Walk the fix.* Measure
  first (MON group: `llc_occupancy`, `mbm_local_bytes`), then partition (L3
  mask for the DB class, MB cap for batch), then verify: `last_cmd_status`,
  re-read counters, compare p99. Partitioning before measuring is guessing.
- *Why can't CAT alone fix a bandwidth hog?* Its unit is ways, not requests --
  a hog inside its own ways still issues at full rate. MBA throttles requests;
  the two bound orthogonal quantities (see the table above).
- *What breaks with CDP, and when is pseudo-locking worth it?* CDP halves the
  CLOSID budget; pseudo-locking (`mode=pseudo-locksetup`) trades a permanent
  way set for deterministic cache latency on a small hot region -- provided
  the CBM is contiguous.

## References

1. Linux kernel, resctrl filesystem and interface documentation:
   https://docs.kernel.org/filesystems/resctrl.html (probed; pseudo-locking
   sections and `last_cmd_status` examples quoted above)
2. Linux kernel, MPAM (arm64) documentation:
   https://docs.kernel.org/arch/arm64/mpam.html ("Partitioning policy can be
   set using the schemata file in resctrl")
3. Intel 64 and IA-32 Architectures SDM, Volume 3, Chapter 17: Platform
   Resource-Based Inventory / Intel RDT (order number 325384; IA32_PQR_ASSOC
   in Volume 4). No stable public URL; section numbers drift between editions.
4. Herdrich et al., "Cache QoS: From concept to reality in the Intel Xeon
   processor E5-2600 v3 product family", HPCA 2016:
   https://doi.org/10.1109/HPCA.2016.7446102 (Crossref-verified)
5. Govindan et al., "Q-Clouds: Managing Performance Interference Effects for
   QoS-Aware Clouds", EuroSys 2010:
   https://doi.org/10.1145/1755913.1755938 (Crossref-verified)

---

## Worklog

Task ID: 64-4
Probed: https://docs.kernel.org/filesystems/resctrl.html (200, primary; older
arch/x86/resctrl.html path 404 -- doc moved), mpam.html (200),
resctrl.rst at raw.githubusercontent.com (200, same doc's source),
doi.org/10.1109/HPCA.2016.7446102 (302), Crossref API for both DOIs
(verified), intel.com RDT manual (403 bot-blocked, not cited), DDG/Bing for
the SDM ch.17 title (nothing usable).
Stage: resctrl facts (CLOS, CBM, min_cbm_bits, sparse_masks, CDP, mba_sc,
last_cmd_status, pseudo-locking, AMD QoS naming, SMBA/ABMC) doc-confirmed;
MPAM line sourced from the live arm64 doc; CBM checker demo run, output
pasted byte-exact; cross-links (noisy-neighbors production view,
side-channels, cxl-memory-pooling, dpu-smartnic-offload, bare-metal-clouds)
all resolve; qa_page clean.
