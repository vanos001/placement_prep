# Hardware Prefetching: Designs, Metrics, and Failure Cases

The deep dive: prefetcher *designs* (stream buffers, reference prediction
tables, global history buffers), *feedback control*, the metrics used to
judge them, and a pointer-chasing case study. For the basics -- next-line vs
stride vs stream, prefetch distance, and the instruction-level software
hints -- see [Prefetching](../memory-hierarchy/prefetching.md); for Markov
prefetchers and a per-vendor hierarchy table see
[Advanced Memory Systems](memory-system-advanced.md).

## Prefetching Is a Prediction Problem

A DRAM access costs on the order of 200-400 core cycles; an L1 hit costs a
handful. An out-of-order core hides part of that gap by overlapping
independent misses, but only misses it has *discovered* -- discovery is
bounded by the reorder buffer and miss-status registers (MSHRs), which
sustain only a few dozen concurrent misses on a typical core. Prefetching
attacks the rest by fetching data the program has not touched yet. Every
prefetcher is a predictor with three levers: **what** to fetch, **when**
(distance ahead of use), and **how much** (degree: speculative lines per
trigger). A wrong lever costs bandwidth (useless prefetches), cache capacity
(pollution), or both, with no upside. The metrics below quantify that trade.

## Metrics: Accuracy, Coverage, Timeliness

Given a baseline run with prefetching disabled (`M0` demand misses) and an
enabled run (`M1` demand misses, `P` prefetches issued):

```text
accuracy  A = useful_prefetches / P
                    (useful = a demand access hits the line before eviction)
coverage  C = (M0 - M1) / M0
late rate L = late_prefetches / P
                    (late = demand arrives while the prefetch is in flight)
waste     W = 1 - A
```

The tension: raising the degree raises coverage but floods the memory
system, and extra traffic slows every other agent on the bus. A prefetcher
with A = 0.95 and C = 0.6 can still be a net loss if it doubles off-chip
traffic. Timeliness is the least-quoted metric: a perfectly accurate
prefetch issued two cycles before use is worth nothing. The feedback-directed
design below splits prefetch outcomes into four buckets -- good (used,
timely), late (used but arrived after the demand), useless (evicted unused),
wasted (evicted unused but displacing a hot line) -- and steers the
prefetcher from those counts.

## Design Lineage

### Stream Buffers (1980s)

The ancestor of hardware prefetching: on a miss, allocate a small FIFO of
the next K consecutive lines and fill them as bandwidth allows; a demand hit
in the buffer promotes the line into the cache and slides the window
forward. A.J. Smith's 1982 survey consolidated the lookahead literature and
remains the standard citation for the algorithmic menu. Jouppi's 1990 ISCA
paper showed that on-chip prefetch *buffers*, separate from the cache,
capture most streams without polluting the cache -- the reason modern
designs still stage prefetches in fill buffers instead of allocating blindly
into L1.

### Reference Prediction Tables (Chen and Baer)

The reference prediction table (RPT) made stride prefetching a per-stream
state machine. Each entry tracks a miss address, the last stride, and a
state (initial -> steady -> transient). Two consecutive equal strides move
the entry to steady, where it issues prefetches at `addr + degree * stride`
and updates on every access; a mismatched stride drops it back to transient.
This is the canonical meaning of "stride prefetcher" in vendor documents,
and it is what the simulation below implements. Its weaknesses follow from
its structure: finite tables evict live streams on conflicts, and entries
keyed on one load cannot express correlations *between* loads.

### Global History Buffers (Nesbit and Smith, HPCA 2004)

The global history buffer (GHB) replaces tables of entries with one FIFO of
recent miss addresses plus per-stream head pointers into it:

```text
FIFO (newest at right), one index register per stream:

  [ m21 m22 m23 | m11 m12 m13 m14 | m31 m32 ]     <- miss stream, FIFO
                   ^
                   head[stream A] = A's first miss in the buffer
  chain links: m11 -> m12 -> m13 -> m14   (built as entries arrive)

  on miss m13: walk chain -> prefetch m14 (plus stride extrapolation)
```

Old entries fall off the FIFO automatically, so GHB never thrashes the way a
fixed table does, and chains encode arbitrarily long patterns -- strides,
correlations, or pointer sequences -- depending on how the walk
extrapolates. The HPCA 2004 paper measured a GHB-based correlation
prefetcher improving performance by about 20% over a conventional
correlation prefetcher while cutting its memory traffic by roughly 90%, plus
around 6% over stride prefetching on their mix. GHB is still the standard
skeleton for irregular prefetchers (several later dependency-graph designs
in the Mittal 2016 survey build on it).

## Feedback-Directed Prefetching (Srinath et al., HPCA 2007)

Once a core has *several* prefetchers, something must arbitrate. The
feedback-directed approach samples the good/late/useless/wasted counters per
prefetcher and adjusts three knobs: aggressiveness (degree/distance -- up
when late prefetches dominate, down when useless ones do), confidence
threshold (demand more corroborating strides before firing), and a bandwidth
cap (stop issuing when off-chip traffic exceeds a budget). Srinath, Mutlu,
Kim, and Patt showed this eliminates the large negative performance impact
prefetching otherwise incurs on some benchmarks, at small monitoring cost.
Every modern design -- including vendors' current ML-assisted L2 prefetchers
-- is a feedback loop around this shape of telemetry, and the same events
are visible to software through performance counters (see
[Hardware Counters](../performance/counters.md)).

## Throttling and Pollution

- **Pollution**: a prefetched line evicted unused may evict a hot line on
  the way out. Classic fixes: insert prefetched lines at the LRU-oldest
  position, or bypass the cache for non-temporal streams.
- **Confidence throttling**: fire the degree-4 burst only after K
  corroborating strides, not 2.
- **Occupancy control**: track MSHR occupancy attributable to prefetches and
  yield to demand misses (demand-first allocation).
- **Page-crossing discipline**: prefetches must not fault or trigger
  page-table walks; implementations suppress them at page boundaries, which
  caps effective distance for strided struct layouts.

## Interaction with Out-of-Order Windows and MLP

Memory-level parallelism (MLP) is the number of misses concurrently in
flight. Without prefetching it is bounded by how fast the instruction window
discovers independent misses; a prefetcher both extends it (issues misses
the window has not reached, shortening the critical path from "miss, then
wait" to "hit") and threatens it (competes with demand misses for MSHRs,
fill buffers, and DRAM banks -- a runaway prefetcher can lower effective
MLP for real misses by filling structures with speculative traffic, the
operational argument for bandwidth caps). Wrong-path loads on mispredicted
branches feed the prefetcher unless filtered, training it on addresses the
program never touches.

## Software Hints

x86 exposes four locality hints via `PREFETCHh` / `_mm_prefetch` /
`__builtin_prefetch`:

```c
_mm_prefetch(p, _MM_HINT_T0);  /* into all levels, incl. L1       */
_mm_prefetch(p, _MM_HINT_T1);  /* all levels except L1            */
_mm_prefetch(p, _MM_HINT_T2);  /* all levels except L1 and L2     */
_mm_prefetch(p, _MM_HINT_NTA); /* non-temporal: minimal pollution */
```

All are hints: they never fault, and exact placement is
implementation-specific. Intel documents the temporal semantics of the hints
while stating that hardware prefetcher behavior is microarchitecture-specific
and not architecturally guaranteed. Software prefetch earns its keep exactly
where history-based predictors are weakest: pointer-chasing loops with a
known-ahead next pointer (below), and strided loops whose distance exceeds
the hardware degree.

## Case Study: Linked Lists and Graph Traversals

Pointer chasing defeats prefetchers by construction: the address of
`node->next` lives *inside* the line being fetched, so the next miss cannot
be issued until the current one returns. The traversal is a serial
dependence chain of memory latencies -- MLP pinned at 1 regardless of core
width:

```text
node A (line X)          node B (line Y)          node C (line Z)
+---------------+        +---------------+        +---------------+
| data  | next =Y|-.      | data  | next =Z|-.      | data  | next =...
+---------------+ |      +---------------+ |      +---------------+
                  '-> X arrives -> deref next'-> Y arrives -> ...
timeline: every hop pays a full memory latency; nothing to overlap
```

No amount of history helps a *first* traversal: the address sequence is
data, not a pattern. Graph workloads show both faces of this. CSR-style
adjacency scans stream neighbors contiguously -- sequential prefetching
handles them well. Frontier-based BFS/DFS gathers chase pointers and
collapse to latency-bound walks (why graph engines obsess over reordering,
blocking, and push/pull direction switching). Two mitigations exist.
*Layout*: nodes from a pool allocator in traversal order give spatial
locality the prefetcher's job; the simulation's list trace shows a stride
prefetcher correctly staying silent (+0.00% -- the permutation is
unlearnable). *Software k-ahead prefetch*: while processing node i, prefetch
`i->next->next` -- the standard pointer-chasing benchmark trick, legal
whenever you can dereference ahead safely.

## What a Modern x86 Core Actually Ships

Intel's Optimization Reference Manual describes, for recent client cores, a
pair of L2 prefetchers: an **L2 streamer** detecting ascending sequential
access and fetching ahead across multiple tracked streams, and an **L2
spatial prefetcher** that, on a miss to one 64-byte line of a 128-byte
aligned pair, brings in both halves. L1 typically adds next-line and/or
IP-indexed stride detection. Exact counts, degrees, and trigger conditions
change per generation and are not architecturally documented; treat precise
claims about a specific SKU's prefetcher internals as reverse-engineered and
tune with counters rather than folklore.

## Worked Simulation: Stride Prefetcher, Three Traces

The sim models a 32 KiB, 8-way L1 (64 sets x 8 ways, 64 B lines, LRU) with a
single-entry RPT-style detector: stride armed by two equal miss deltas,
degree 4, disarmed on a mismatched delta. Timing is idealized -- a prefetch
completes before the next demand access -- so coverage and pollution can be
read directly:

```python
import random

SETS, WAYS, DEGREE = 64, 8, 4      # 32 KiB L1D, 64 B lines, prefetch degree


class Cache:
    def __init__(self):
        self.sets = [dict() for _ in range(SETS)]   # line -> stamp
        self.t = self.d_hits = self.d_misses = 0
        self.pf_issued = self.pf_useful = 0

    def _fill(self, line, pf):
        self.t += 1
        s = self.sets[line % SETS]
        if len(s) >= WAYS:
            victim = min(s, key=s.get)
            del s[victim]
            pf.pop(victim, None)    # evicted before use: prefetch wasted
        s[line] = self.t

    def demand(self, line, pf):
        s = self.sets[line % SETS]
        self.t += 1
        if line in s:
            s[line] = self.t
            self.d_hits += 1
            if line in pf:
                self.pf_useful += 1
                del pf[line]
            return True
        self.d_misses += 1
        self._fill(line, pf)
        return False

    def prefetch(self, line, pf):
        if line in self.sets[line % SETS]:
            return                      # already resident: wasted issue
        self.pf_issued += 1
        pf[line] = True
        self._fill(line, pf)


def run(lines, active):
    c, pf, last, stride = Cache(), {}, (None, None), None
    for ln in lines:
        if c.demand(ln, pf) or not active:
            continue
        delta = None if last[0] is None else ln - last[0]
        if delta is not None and delta == last[1] and delta != 0:
            stride = delta              # two equal deltas: (re)arm
        elif stride is not None and delta != stride:
            stride = None               # pattern broken: stay quiet
        last = (ln, delta)
        if stride is not None:
            for d in range(1, DEGREE + 1):
                c.prefetch(ln + d * stride, pf)
    return c


rng = random.Random(42)
perm = list(range(8192))
random.Random(7).shuffle(perm)
chase, cur = [], 0
for _ in range(8192):
    chase.append(cur)
    cur = perm[cur]
traces = [("stride 256 B scan", [i * 4 for i in range(65536)]),
          ("random (512 KiB)", [rng.randrange(0, 8192) for _ in range(65536)]),
          ("linked-list chase", chase)]
print(f"{'trace':20s} {'base hit%':>9s} {'pf hit%':>8s} {'delta':>7s} "
      f"{'coverage%':>9s} {'pf issued':>9s} {'useful':>7s} {'accuracy%':>9s}")
for name, tr in traces:
    base, pf = run(tr, False), run(tr, True)
    cov = 100.0 * (base.d_misses - pf.d_misses) / base.d_misses
    acc = 100.0 * pf.pf_useful / pf.pf_issued if pf.pf_issued else 0.0
    bh = 100.0 * base.d_hits / (base.d_hits + base.d_misses)
    ph = 100.0 * pf.d_hits / (pf.d_hits + pf.d_misses)
    print(f"{name:20s} {bh:9.2f} {ph:8.2f} {ph - bh:+7.2f} {cov:9.2f} "
          f"{pf.pf_issued:9d} {pf.pf_useful:7d} {acc:9.2f}")
```

Output (Python 3.12):

```text
trace                base hit%  pf hit%   delta coverage% pf issued  useful accuracy%
stride 256 B scan         0.00    57.14  +57.14     57.14     37448   37448    100.00
random (512 KiB)          6.15     6.15   +0.00      0.00        16       0      0.00
linked-list chase         0.00     0.00   +0.00      0.00        24       0      0.00
```

Reading it: the stride scan's hit rate is exactly 4/7 -- after each burst,
the covered hits *skip* miss deltas, so the detector disarms and needs two
fresh misses to re-arm; a design that keeps stream entries alive across
covered hits sustains closer to 80%. Accuracy is 100%, so every extra byte
paid for itself (about 37k prefetch fills on top of 13k demand misses, a
~3x traffic multiplier -- only worth it because the baseline was pure
misses). On the random trace the detector almost never fires (16 stray
issues, zero useful) and the 6.15% baseline -- roughly the 32 KiB/512 KiB
capacity ratio -- is untouched. The list trace earns exactly nothing, as the
dependence-chain analysis predicts: the hardware is correct to stay quiet,
and only layout or software k-ahead prefetch changes the outcome.

## Failure Modes Checklist

- Trusting vendor prefetcher folklore instead of measuring useful/useless
  prefetch counters for your workload.
- Software prefetches placed too close (arrive late) or too far (evicted
  first): distance must cover latency divided by loop-body time.
- Prefetching across page boundaries expecting fault-free behavior.
- Multithreaded code: prefetching lines another core is about to invalidate
  (coherence turns your prefetch into traffic).
- Assuming prefetch behavior survives a microcode or SKU change.

## References

- [Intel 64 and IA-32 Architectures Software Developer's Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html) -- prefetch hint semantics, Vol. 3A cache chapters
- [Smith, "Cache Memories", ACM Computing Surveys, 1982](https://doi.org/10.1145/356887.356892)
- [Nesbit and Smith, "Data Cache Prefetching Using a Global History Buffer", HPCA 2004](https://doi.org/10.1109/HPCA.2004.10030)
- [Srinath, Mutlu, Kim, Patt, "Feedback Directed Prefetching", HPCA 2007](https://doi.org/10.1109/HPCA.2007.346185)
- [Mittal, "A Survey of Recent Prefetching Techniques for Processor Caches", ACM CSUR 2016](https://arxiv.org/abs/1508.04187)
