# DRAM Controllers and Memory Scheduling

A CPU core issues a 64-byte load and the memory system answers in ~80 ns. What
happens in between is the memory controller's job: translate physical addresses
into {channel, rank, bank-group, bank, row, column}, track which DRAM row is
open in every bank, obey dozens of timing constraints, keep the cells
refreshed, and decide *which* queued request goes onto the command bus next.
That last decision — scheduling — is worth tens of percent of system
throughput, because DRAM is far cheaper to access when you ask for something it
already has open.

This page is the controller's-eye view. For cell physics and organization see
[DRAM](../memory-tech/dram.md); for DDR generations see
[DDR SDRAM](../memory-tech/ddr.md); [Advanced Memory
Systems](memory-system-advanced.md) has a survey-level scheduling FAQ — here we
go deeper into the policies, the timing math behind them, and a runnable
simulation. For what happens when rows are hammered instead of read, see
[RowHammer](rowhammer.md).

## One Command Bus, Many Constrained Banks

A DDR4 DRAM speaks a small command vocabulary: ACTIVATE (open a row into the
sense-amp row buffer), READ/WRITE (CAS: pick a column from the open row),
PRECHARGE (close the row). Commands share one bus; data shares another. Banks
operate independently — that is the parallelism a scheduler exploits — but
each transition is governed by fixed timing parameters. Values below are from
the Micron 16Gb DDR4 SDRAM datasheet (Rev. H), DDR4-3200 speed bin
(CL-nRCD-nRP = 22-22-22). Times are in nanoseconds and in DRAM clock cycles
(nCK, tCK = 0.625 ns):

| Parameter | Meaning | Datasheet value | Cycles (tCK) |
|---|---|---|---|
| tRCD | ACTIVATE -> CAS delay | 13.75 ns min | 22 |
| tCL (tAA) | CAS -> first data | 13.75 ns min | 22 |
| tRP | PRECHARGE period | 13.75 ns min | 22 |
| tRAS | ACTIVATE -> PRECHARGE min | 32 ns min | 52 |
| tRC | Row cycle time (tRAS + tRP) | 45.75 ns min | 74 |
| tCCD_S | CAS-to-CAS, different bank group | 4 nCK | 4 |
| tCCD_L | CAS-to-CAS, same bank group | max(4 nCK, 5 ns) | - |
| tREFI | Average refresh interval | 7.8 us (<=85 C), 3.9 us (85-95 C) | - |
| tRFC1 | Refresh cycle time (8Gb/16Gb) | 350 ns | 560 |

The three access costs fall out of this table directly. To a **closed** bank:
ACT (wait tRCD), CAS (data at tAA) -> data after tRCD + tAA = 27.5 ns, and the
bank is not ready for its *next* ACT until tRC = 45.75 ns has elapsed. To a
**row-buffer hit** (row already open): CAS only, data at tAA = 13.75 ns.
Closed-page misses therefore cost ~3.3x more bank-occupancy time than hits
(45.75/13.75) — the "2-3x cheaper" rule of thumb from the memory-access
scheduling literature [Rixner et al., ISCA 2000], consistent with the ~47 ns
vs ~14 ns figures quoted in [Advanced
Systems](memory-system-advanced.md).

## Row-Buffer Hit vs Miss: A Timeline

```text
Bank state: row R already open                 Bank state: row R closed

  0ns        13.75ns                              0ns   13.75  27.5    45.75ns
  |            |                                  |      |       |         |
  CAS========== data                              ACT----CAS------data  PRE
  ^ tAA only                                      |tRCD  |tAA     ^
  hit: one command, 13.75 ns (22 nCK) to data     +------+-------+ tRCD+tAA
                                                  miss: 27.5 ns to data,
                                                  bank busy until tRC = 45.75 ns
  Row conflict (row X open, want Y):
  CAS(X)... wait tRAS ... PRE(tRP) ACT(Y)(tRCD) CAS(Y)->data : worst case,
  up to tRAS + tRP + tRCD + tAA of bank occupancy for one transfer
```

Two consequences drive every scheduler design:

1. Reordering requests so that hits are adjacent on the bus is nearly free
   bandwidth — the data is already in the sense amps.
2. Leaving a row open is a bet that the next access to this bank wants the
   same row. Streams win big; pointer-chasing and random traffic pay the
   conflict penalty instead.

## Scheduling Policies: FCFS, FR-FCFS, and the Fairness Generations

**FCFS** — serve requests in arrival order. Simple and starvation-free, but a
row-conflicting request head-of-line-blocks the bus while its PRE/ACT chain
runs, even when a row hit to another bank is ready *right now*.

**FR-FCFS (First-Ready, First-Come-First-Served)** — row hits to currently
open rows go first (oldest first); only when no hit is pending does the oldest
miss proceed. Zuravleff and Robinson patented this in 1997 ("Controller for a
Synchronous DRAM That Maximizes Throughput by Allowing Memory Requests and
Commands to Be Issued Out of Order", US Patent 5,630,096 — a patent, not a
conference paper, despite how often it gets miscited). It is the default in
most general-purpose controllers because on mixed traces the hit fraction is
high and serving hits first directly raises bus utilization. The cost: a
hit-heavy neighbor can starve a stream that always misses — pure throughput
logic, completely fairness-blind.

**Fairness-aware schedulers** fix that. TCM (Mutlu & Moscibroda, MICRO 2007,
doi 10.1109/MICRO.2007.21) classifies requests by stall-time criticality and
memory-issue urgency and shuffles priority between applications. ATLAS
(Parallelism-Aware Batch Scheduling, same authors, ISCA 2008,
doi 10.1109/ISCA.2008.7) forms batches of requests chosen to exploit
bank-level parallelism, so a low-parallelism thread is not stuck behind a
high-parallelism one. The pattern to remember: *throughput* policies rank
requests by readiness; *fairness* policies rank by how much the ranking
decision costs the loser, measured in stall time.

**Pairing with prefetchers** complicates the readiness ranking. A prefetch
that hits in the row buffer is the cheapest access the controller will ever
issue; a prefetch miss that evicts a demand hit's row is expensive pollution.
Prefetch-Aware DRAM Controllers (Lee, Mutlu, Narasiman, Patt, MICRO 2008,
doi 10.1109/MICRO.2008.4771791) split queued requests into demand misses,
prefetch misses, useful prefetch hits, and useless prefetches, prioritizing
demand traffic and timely prefetches, and can feed back to the prefetcher
("these lines are never touched — stop or shrink the stream"). Design-side
metrics (accuracy, coverage, timeliness) live in [Hardware
Prefetching](hardware-prefetching.md); the scheduler is where they get
*enforced*.

## Bank Groups, Write Turnaround, and the Refresh Tax

**Bank groups** (DDR4: 16 banks as 4 groups of 4; DDR5 widens to 8 groups
under JESD79-5) exist because internal prefetch stayed at 8n while I/O speed
kept climbing. Same-group CAS commands pay tCCD_L (max(4 nCK, 5 ns) at
DDR4-2400 in the Micron table) while different-group commands need only
tCCD_S (4 nCK) — a scheduler that rotates across bank groups feeds the bus
faster than one that hammers one group. The read/write boundary is similar:
turning the data bus around idles it, and a write cannot closely follow a read
to the same bank group (tWTR_S vs tWTR_L). Controllers therefore **batch
writes into a drain**: collect writes while serving reads, then switch
direction once and flush the write queue — trading a little write latency for
a lot of bus utilization.

**Refresh** is the tax on all of this. Cells leak, so every tREFI interval the
controller issues REF, which blocks *every* bank for tRFC1 = 350 ns. With the
datasheet intervals that is 350/7800 = 4.5% of all bank time at <=85 C, and
because the refresh window doubles above 85 C (tREFI 3.9 us), it becomes
350/3900 = ~9% — the classic "refresh steals ~8-10% of bandwidth" figure for
DDR4-class parts in the extended temperature range. DDR4 also added Fine
Granularity Refresh (1x/2x/4x modes, on-the-fly switching) and lets the
controller postpone REF up to 9x tREFI, i.e. schedule refreshes into idle
gaps. Research went further: RAIDR (Liu et al., ISCA 2012,
doi 10.1109/ISCA.2012.6237001) exploits retention variance to refresh weak
rows more often and strong rows less; Chang et al. (HPCA 2014,
doi 10.1109/HPCA.2014.6835946) parallelize refresh with per-bank accesses.
Modern ECC controllers also interleave RFM (refresh management) commands after
activation thresholds — the RowHammer connection is covered in
[RowHammer](rowhammer.md).

## FR-FCFS vs FCFS on a Mixed Trace

The simulator implements a 4-bank open-row controller with the DDR4-3200
timings above: banks run PRE/ACT chains in parallel, the CAS data bus is
shared, and the trace mixes sequential streams (row hits), a random bank
(conflicts), and a mixed bank.

```python
#!/usr/bin/env python3
"""FR-FCFS vs FCFS on a mixed DRAM trace (row hits + row conflicts + streams).

Timings in DRAM clock cycles (nCK, tCK = 0.625 ns at DDR4-3200), per the
Micron 16Gb DDR4 SDRAM datasheet (Rev. H): tRCD = tCL = tRP = 22 nCK
(13.75 ns), tRAS = 52 nCK (32 ns), tRC = tRAS + tRP = 74 nCK (45.75 ns),
tCCD = 4 nCK (BL8 burst on the data bus).
Reads-only trace served by an open-row controller with 4 independent banks;
each bank may run its PRE/ACT chain in parallel, the CAS data bus is shared.
"""
import random

tRCD, tCL, tRP, tRAS, tCCD = 22, 22, 22, 52, 4
tRC = tRAS + tRP
NB = 4  # banks

class Bank:
    def __init__(self):
        self.row = None          # open row id
        self.act_ok = 0          # earliest next ACT (respects tRC)
        self.cas_ready = None    # time CAS may issue for armed request
        self.req = None          # armed request

def serve_all(reqs, policy):
    banks = [Bank() for _ in range(NB)]
    queues = [[] for _ in range(NB)]     # per-bank FIFO of arrived requests
    bus_free = 0                         # data bus free at (tCCD spaced CAS)
    hits = [0]                           # served as row-buffer hits
    arrivals = sorted(reqs, key=lambda r: r.arr)
    t, done, ai = 0, {}, 0
    while ai < len(arrivals) or any(queues) or any(b.req for b in banks):
        while ai < len(arrivals) and arrivals[ai].arr <= t:      # admit arrivals
            queues[arrivals[ai].bank].append(arrivals[ai]); ai += 1
        # arm idle banks: start PRE/ACT chains as early as possible
        for b in range(NB):
            if queues[b] and banks[b].req is None:
                r = queues[b][0]
                start = max(t, banks[b].act_ok)
                if banks[b].row == r.row:                      # row hit
                    banks[b].cas_ready = start
                elif banks[b].row is None:                     # idle: ACT + tRCD
                    banks[b].cas_ready = start + tRCD
                else:                                          # conflict: PRE + ACT
                    banks[b].cas_ready = start + tRP + tRCD
                banks[b].req = r
        # schedule one CAS when the bus is free
        if bus_free <= t:
            armed = [b for b in range(NB) if banks[b].req]
            ready = [b for b in armed if banks[b].cas_ready <= t]
            if not ready:                       # all chains still running
                cands = [banks[b].cas_ready for b in armed]
                if ai < len(arrivals): cands.append(arrivals[ai].arr)
                t = max(t + 1, min(cands))
                continue
            if policy == "FCFS":                # oldest overall; HoL blocking
                pick_b = min(armed, key=lambda b: banks[b].req.arr)
                cas = max(t, banks[pick_b].cas_ready)
            else:                               # FR-FCFS: row hits first
                pool = [b for b in ready
                        if banks[b].row == banks[b].req.row] or ready
                pick_b = min(pool, key=lambda b: banks[b].req.arr)
                cas = t
            bk = banks[pick_b]; r = bk.req
            if bk.row == r.row: hits[0] += 1
            bus_free = cas + tCCD
            finish = cas + tCL + tCCD
            done[r.id] = finish
            queues[pick_b].remove(r)
            if bk.row != r.row:                 # an ACT happened in this chain
                bk.act_ok = (cas - tRCD) + tRAS + tRP   # ACT + tRC before next ACT
            bk.row = r.row
            bk.req = None; bk.cas_ready = None
            t = max(t + 1, bus_free - tCCD)
        else:
            t += 1
    return done, hits[0]

class Req:
    __slots__ = ("id", "arr", "bank", "row")
    def __init__(self, i, arr, bank, row):
        self.id, self.arr, self.bank, self.row = i, arr, bank, row

def trace(seed=7, n=400):
    rng = random.Random(seed)
    rows, reqs, t = [0] * NB, [], 0
    pattern = [0, 0, 2, 1, 0, 1, 3, 0]   # 5/8 streams, 1/8 random, 1/8 mixed
    for i in range(n):
        # bursty arrivals: tight bursts of 8, then a lull (~75% bus load)
        t += rng.randrange(80, 200) if i % 8 == 0 else rng.randrange(8, 24)
        b = pattern[i % len(pattern)]
        if b in (0, 1):                  # streams: usually same row -> hits
            rows[b] += rng.randrange(100) < 8
        elif b == 2:                     # random -> row conflicts
            rows[b] = rng.randrange(64)
        else:                            # mixed: repeats + jumps
            rows[b] += rng.choice([0, 0, 0, 7, -7, 40])
        reqs.append(Req(i, t, b, rows[b] % 64))
    return reqs

reqs = trace()
print(f"trace: 400 reads, {NB} banks, tCK=0.625 ns DDR4-3200 timings")
res = {}
for policy in ("FCFS", "FR-FCFS"):
    d, nhits = serve_all(reqs, policy)
    res[policy] = d
    lat = {r.id: d[r.id] - r.arr for r in reqs}
    avg = sum(lat.values()) / len(lat)
    grp = lambda bs: sum(lat[r.id] for r in reqs if r.bank in bs) \
          / sum(1 for r in reqs if r.bank in bs)
    print(f"{policy:8s} avg {avg:5.1f} cyc ({avg*0.625:4.1f} ns) | "
          f"streams {grp((0, 1)):5.1f} | random {grp((2,)):5.1f} | "
          f"mixed {grp((3,)):5.1f} | row-hit% {100 * nhits / 400:4.1f} | "
          f"makespan {max(d.values())} cyc")
l_f, l_r = (sum(d[r.id] - r.arr for r in reqs) for d in (res["FCFS"], res["FR-FCFS"]))
print(f"FR-FCFS total waiting-time reduction vs FCFS: {100 * (1 - l_r / l_f):.1f}%")
```

Output (Python 3.11, deterministic seed — verify by rerunning):

```text
trace: 400 reads, 4 banks, tCK=0.625 ns DDR4-3200 timings
FCFS     avg  54.0 cyc (33.8 ns) | streams  49.6 | random  72.3 | mixed  62.4 | row-hit% 73.8 | makespan 12122 cyc
FR-FCFS  avg  41.6 cyc (26.0 ns) | streams  35.4 | random  69.2 | mixed  51.3 | row-hit% 73.8 | makespan 12122 cyc
FR-FCFS total waiting-time reduction vs FCFS: 22.9%
```

Read the result carefully. Row-hit rate is identical (73.8%) under both
policies — reordering does not change which rows the *trace* touches; it
changes how long requests wait *behind* conflicting chains. FCFS's
head-of-line blocking parks the whole bus whenever the oldest request sits on
a bank that can only reach its next row via a full tRC cycle (74 nCK here);
FR-FCFS slips ready hits through in the gap and cuts total waiting time by
~23%. Streams gain most (49.6 -> 35.4 cycles); the random bank gains least in
relative terms (72.3 -> 69.2) — its requests are the ones doing the waiting
either way, which is exactly the starvation pressure that motivated TCM and
ATLAS.

## Row-Buffer Awareness Above the Controller

The controller schedules what the OS hands it, and conventional 4 KiB
anonymous pages scatter consecutive pages across banks and channels,
destroying row-buffer locality before the controller sees a request. Levers
that push row-buffer awareness up the stack: channel/bank **partitioning** at
page-allocation time (Muralidhara et al., MICRO 2011,
doi 10.1145/2155620.2155664, maps each application's pages to a channel
subset, cutting interference); huge pages, which concentrate contiguous
addresses into fewer row activations; and cache **page coloring** extended
from cache ways to DRAM banks. None are default in mainline Linux — the
address mapping is a fixed hardware hash — but the levers matter again in the
CXL era, where a device-side controller ([CXL Memory
Pooling](cxl-memory-pooling.md)) may schedule very differently from the
integrated one.

## References

1. Micron Technology, 16Gb DDR4 SDRAM datasheet (Rev. H) — timing parameters, refresh modes, speed bins: <https://www.micron.com/products/memory/dram-components/ddr4-sdram>
2. W. Zuravleff, T. Robinson — US Patent 5,630,096, FR-FCFS scheduling (1997): <https://patents.google.com/patent/US5630096A/en>
3. S. Rixner et al., "Memory Access Scheduling", ISCA 2000: <https://doi.org/10.1145/339647.339668>
4. O. Mutlu, T. Moscibroda, "Parallelism-Aware Batch Scheduling (ATLAS)", ISCA 2008: <https://doi.org/10.1109/ISCA.2008.7>
5. J. Liu et al., "RAIDR: Retention-Aware Intelligent DRAM Refresh", ISCA 2012: <https://doi.org/10.1109/ISCA.2012.6237001>
