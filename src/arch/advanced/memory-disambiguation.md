# Memory Disambiguation: The Store Buffer's Contract With Loads

Every other hazard in an out-of-order core is bounded by structures the
programmer can reason about from the ISA: registers rename cleanly, branch
mispredicts are bounded by the branch. Memory is different: a load and a
store that the compiler *knows* are independent, and two that it *knows*
alias, look identical to the hardware at decode time -- addresses are not
computed until execute, and 4 GiB of address space cannot be pattern-matched
by a CAM the size of a register file. Memory disambiguation decides, per
load, whether it may execute before older stores have resolved their
addresses: forward from the store buffer, read cache, or wait. This page
follows that machinery end to end -- forwarding rules, the memory-order
machine clear, alias predictors, 4K aliasing, and the lock-free implications
of x86's total store order.

For the surrounding pipeline (ROB, reservation stations, renaming) read
[Out-of-Order Execution](ooo-execution.md) -- its *Memory Disambiguation*
section is the five-minute version of this page. Register forwarding between
ALU ops is in [Data Forwarding](../pipelining/forwarding.md); coherence
protocols are in [Cache Coherence, Advanced](cache-coherence-advanced.md).

## Why the Store Buffer Exists

A store commits to the cache hierarchy only when it retires. Until then it
lives in the **store buffer**: a FIFO of pending stores, each holding
address, data, size, and the producing instruction, in program order. Three
jobs: (1) **retirement flow** -- a store frees its ROB slot at the head of
the reorder buffer before the data reaches L1; (2) **coalescing and burst
drain** -- consecutive stores to one line drain as a single transaction;
(3) **self-forwarding** -- loads from the same thread read buffered stores
immediately, at L1-like latency, before the cache ever sees them.

Recent big x86 cores hold on the order of 50-70 store-buffer entries
(reverse-engineered estimates; Agner Fog tabulates per-generation
capacities). The buffer is searched on **every** load: the load's address
is compared against all older unresolved stores -- a fully-associative CAM
lookup, which is why address-computation latency feeds directly into
dependence-check latency.

```text
         out-of-order core                    cache hierarchy
  +--------------------------------+        +----------------+
  |  load queue        store buffer |        |                |
  |  (younger loads   [ S3  a3 d3 ] |        |      L1D       |
  |   waiting on      [ S2  a2 d2 ] |------> |  (drains at    |
  |   addresses)      [ S1  a1 d1 ] | STLF   |   retirement)  |
  |         ^               |       |        |                |
  |         |  (1) compare  |       |        |                |
  |         |      v        |       |        |                |
  |  load executes? --+-----+       |        |                |
  |         |    hit: forward data     |        |                |
  |         |    miss: read L1D -------+------> |                |
  |         |             |            |        |                |
  |  retire head: store S1 drains to L1D-|------> |                |
  +--------------------------------+        +----------------+
```

## Forwarding Rules: Size, Alignment, Overlap

Store-to-load forwarding (STLF) succeeds when the load can be answered
unambiguously from buffered stores. The universal rule set, as documented
and measured across x86 families:

| Case (older store -> younger load)          | Forward? | Cost when refused     |
|---------------------------------------------|----------|-----------------------|
| Load fully inside one store, same size      | Yes      | --                    |
| Load strictly inside, different size,       | Yes      | --                    |
| aligned to the store (8B store, 4B load)    |          |                       |
| Load spans two buffered stores (merge)      | Rare     | stall until both      |
|                                             |          | stores commit         |
| Partial byte overlap only (load wider       | No       | stall until store     |
| than the store it touches)                  |          | drains                |
| Load/store low address bits differ          | Usually  | stall, or penalty     |
| (misaligned relative to the store)          | no       | cycles                |

The fast case costs about five cycles -- measurably *more* than an L1 hit.
Henry Wong's microbenchmark study measured, with load and store addresses
equal and 8-byte aligned:

| Processor    | L1 hit (cyc) | STLF "fast address" (cyc) |
|--------------|--------------|---------------------------|
| Yorkfield    | 3            | 5.0                       |
| Lynnfield    | 4            | 5.1                       |
| Sandy Bridge | 4            | 5.3                       |

(Agner Fog's microarchitecture document carries the same measurement
tradition per family, including which size/offset combinations forward on
Skylake-class and Zen-class cores; consult the current revision for a
specific generation.) When forwarding fails, the load waits for the store
to leave the buffer -- a drain-and-refetch costing roughly 10-25 cycles
depending on how far the store is from retirement. AMD's Bulldozer family
had a notorious corner: Wong measured 30+ cycles on *successful-looking*
forwards, a latency consistent with a full pipeline flush rather than data
movement.

The most common real-world forwarding failure is a **width or alignment
change between write and read-back**: writing a field as `uint64_t` and
reading it as two `uint32_t`s, or a lock-free producer storing a flag as
1 byte while the consumer spins with a 4-byte load. The fix costs nothing:
read back with the same width and alignment as the store.

## The Memory-Order Machine Clear

Suppose the store's address is not yet computed when a younger load reaches
the LSU. The core has two options. **Serialize**: hold the load until every
older store's address is known -- correct, but every pointer-chasing loop
pays store-buffer CAM latency in its critical path. Or **speculate**:
assume no alias, read L1 now; if an older store later resolves to the same
address and its data would have been consumed, the guess was wrong and must
be unwound.

The unwind mechanism is the **memory-order machine clear**
(`MC.MEMORY_ORDERING` in Intel's event taxonomy): younger instructions are
squashed, the offending load and everything after it re-executed -- costing
on the order of a branch mispredict, tens of cycles, *per violation*:

```text
program order:   S1: store [x] = 42        (address x not yet resolved)
                 I2, I3, ...               (independent work)
                 L9: load  r = [x]         (speculates: reads OLD value
                                            of x from L1 -- "no alias")
                    L9 retires early, value consumed by dependents

     S1 executes -> address x, data 42 enters store buffer
     L9's address matches S1, and L9 got the pre-store value
          |
          v
     machine clear: squash everything younger than the violation point,
     re-execute L9 (now forwards 42 from S1), replay dependents

     cost ~= branch-mispredict-class flush, repeated per violation
```

The asymmetry drives the design: a *correct* no-alias guess costs nothing,
so the heuristic is biased toward speculation, and the predictor's job is
to spot the rare recurring aliases before they cost flushes every iteration.

## Speculative Disambiguation: Predicting Alias

Early implementations split into two camps: conservative cores serialized
loads behind unresolved stores (MIPS R10000-style), the P6 chose
speculation plus replay. Making speculation *cheap* requires predicting,
per load, whether it historically conflicts -- memory dependence
prediction, canonically Intel's Store Sets (Chrysos & Emer, ISCA 1998):

```text
SSIT (store-set ID table, indexed by PC)    LDST (per-PC state, 2-bit)
  store PC -> set id a      load PC  -> [ last set id a | confidence ]
  store PC -> set id b      store PC -> [ last set id b | stride    ]

  violation (load executed before aliased store):
     load's and store's set ids merge -> both poll the same filter
     next iteration: load waits for the store's address -> short
     predictable stall, not a flush
```

Store Sets converts *repeat* offenders from machine clears into short
predictable stalls; first-time offenders still pay the flush. Stone,
Woolley and Frank later sharpened the identifier with address-indexed
disambiguation (comparing address bits, not only PCs).

**Memory renaming** -- treating buffered stores as renameable "memory
registers" so a load can be renamed to depend on a specific store entry,
eliminating the serial address compare -- has surfaced repeatedly in the
literature and in patents (Roth, Martin and Roth's NoSQ communication
mechanism, IEEE Micro 2007; US patent application 2014/0095814, "Memory
Renaming Mechanism in Microarchitecture"). No shipping x86 core documents
such a mechanism; what ships is the heuristic-plus-predictor scheme above.

### 4K Aliasing: A False Dependence With a Real Penalty

A special case deserves its own name because it is a performance bug, not
a correctness one. If a load's address differs from an older store's by an
exact multiple of 4096 bytes, their low 12 address bits are equal. Cores
that defer or make only partial the address comparison treat the pair as
*possibly* aliasing, imposing a pipeline block or dependence edge although
the full addresses differ:

```text
   store [0x7fff_1000]        load [0x7fff_2000]
          |                          |
          +---- bits 11:0 equal -----+
          = false dependence, penalty ~5-10 cycles (generation-dependent)
```

Classically this appeared where a destination buffer sits exactly 4096
bytes after a source buffer -- two large stack arrays, or a page-sized
element stride (the memcpy pattern Intel's optimization guidance has long
warned about). Agner Fog documents the effect and historical per-generation
penalties. Mitigations are layout-level: pad or realign so source and
destination low bits differ, avoid 4096-byte strides in hot loops, and
remember that two hot accesses can land 4 KiB apart by coincidence. The
counter `ld_blocks_partial.address_aliasing` counts these blocks directly.

## Worked Simulation: Forward Cost vs Clear Cost

The model below prices four store/load patterns on a serial critical path
(one load per iteration feeding the next store, so memory-op latency is
exposed). Parameters: base loop work 6 cycles; STLF hit 5 cycles (the
measured x86 fast case); forward-fail drain 12; machine clear 25; a 1-bit
per-load predictor that starts speculative and flips on any surprise.

```python
BASE = 6        # non-memory work per iteration (cycles)
STLF = 5        # store-to-load forward hit (measured x86 fast case)
DRAIN = 12      # forward refused: wait for the store to commit
CLEAR = 25      # memory-order machine clear (pipeline flush)

def run(ops, iters):
    """ops(i) yields 'stlf_hit' | 'forward_fail' | 'alias' | 'no_alias'.
    1-bit predictor per load: no_alias (speculate) <-> alias (serialize).
    Returns (total cycles, flush count)."""
    pred = "no_alias"
    total = flushes = 0
    for i in range(iters):
        op = ops(i)
        if op == "stlf_hit":
            cost = STLF
        elif op == "forward_fail":
            cost = DRAIN
        elif op == "alias":
            if pred == "no_alias":     # speculated past the store: wrong
                cost, flushes = CLEAR, flushes + 1
                pred = "alias"         # learn: serialize next time
            else:
                cost = STLF            # short stall, no flush
        else:                          # truly independent load
            if pred == "alias":        # over-caution: stall and re-learn
                cost, pred = STLF, "no_alias"
            else:
                cost = 0               # fully hidden under base work
        total += BASE + cost
    return total, flushes

iters = 1000
cases = [
    ("STLF hit (same width, aligned)", lambda i: "stlf_hit"),
    ("narrow load after wide store",   lambda i: "forward_fail"),
    ("recurring alias, predictor on",  lambda i: "alias"),
    ("alias/no-alias flip-flop",       lambda i: "alias" if i % 2 == 0
                                       else "no_alias"),
    ("independent (true no-alias)",    lambda i: "no_alias"),
]
print(f"{'pattern':32s} {'cycles':>7s} {'flushes':>8s} {'cyc/iter':>9s}")
for name, ops in cases:
    t, f = run(ops, iters)
    print(f"{name:32s} {t:7d} {f:8d} {t / iters:9.2f}")
```

Output (Python 3.12):

```text
pattern                           cycles  flushes  cyc/iter
STLF hit (same width, aligned)     11000        0     11.00
narrow load after wide store       18000        0     18.00
recurring alias, predictor on      11020        1     11.02
alias/no-alias flip-flop           21000      500     21.00
independent (true no-alias)         6000        0      6.00
```

Reading it: a recurring alias the predictor learns costs **one** flush --
25 cycles amortized over 1000 iterations, +0.02 per iteration -- after
which it is indistinguishable from the clean STLF hit. The flip-flop row
models a pattern that defeats a 1-bit predictor (addresses alternate
between alias and independence, so the predictor oscillates): a flush
every other iteration, 21 cycles/iter, sits between the two stable
policies. The width-mismatch row costs more than a learned alias *every
iteration* with zero flushes -- alignment discipline beats any predictor.
And true independence is free: the 6-cycle row is exactly the base work,
which is the entire argument for speculating.

## What x86 TSO Promises (and Lock-Free Code Gets For Free)

x86's memory model, formally specified as x86-TSO (Sewell et al., CACM
2010), is total store order: stores drain to coherence in program order,
and a thread always observes its own stores through the buffer. TSO's
distinctive allowance is precisely this page's speculation: a load may
read memory *before* an older store's address resolves, but the machine
clear makes the outcome as if it had not. Three consequences for lock-free
code:

- **No observable reordering between ordinary `mov`s on x86**: store-store
  and load-load ordering hold, load-store ordering holds except for the
  speculation above, which the clear repairs. The costs this page describes
  are performance costs, not correctness hazards -- your CAS loops cannot
  break, only slow down. Contrast ARM, where load-acquire/store-release do
  real ordering work (see
  [Memory Barriers](../../os/synchronization/memory-barriers.md) and
  [Lock-Free Structures](../../os/synchronization/lock-free.md)).
- **The store buffer litmus test**: one thread does `x=1; r1=y`, another
  `y=1; r2=x` -- both loads can observe 0, because each load reads memory
  while its own store sits in the buffer. The store buffer is not a
  coherent cache. Algorithms broken by this need `mfence` or `lock`-prefixed
  ops to drain the buffer, at full drain latency.
- **Forwarding width discipline matters most in flag protocols**: a
  producer writing a 1-byte flag that consumers poll as `int` forces the
  forward-fail path on every acquisition -- the 18-cycle row above, inside
  what should be a 5-cycle critical section.

Transient-execution attacks sharpened this picture: Spectre-style gadgets
*rely* on loads speculating past stores, with architectural state repaired
while microarchitectural state (cache lines) leaks -- the same machinery
viewed adversarially, covered in [Side-Channel Attacks](side-channels.md).

## Diagnosis: Counters and Symptoms

| Symptom (assembly-level)                 | Counter (Intel naming)               |
|------------------------------------------|--------------------------------------|
| Loads blocked waiting on older stores    | `ld_blocks.store_forward`            |
| 4K-aliasing false dependencies           | `ld_blocks_partial.address_aliasing` |
| Memory-order machine clears              | `machine_clears.memory_ordering`     |

```bash
perf stat -e ld_blocks.store_forward,ld_blocks_partial.address_aliasing,\
machine_clears.memory_ordering,instructions ./bench
```

A `machine_clears.memory_ordering` rate above ~1 per 100k instructions
usually means a recurring alias the predictor is not learning: look for a
hot load whose PC pollutes multiple store sets, or interleaved loops
sharing addresses. Sustained `ld_blocks.store_forward` with narrow loads
points at width-mismatched read-backs -- a source-level fix, not tuning.

## References

- [Agner Fog, "The Microarchitecture of Intel, AMD and VIA CPUs"](https://www.agner.org/optimize/microarchitecture.pdf) -- per-generation store buffer sizes, forwarding matrices, 4K aliasing penalties
- [Henry Wong, "Store-to-Load Forwarding and Memory Disambiguation in x86" (2014)](https://blog.stuffedcow.net/2014/01/x86-memory-disambiguation/) -- the measured forwarding/latency matrix quoted above
- Chrysos and Emer, "Memory Dependence Prediction Using Store Sets", ISCA 1998, [DOI 10.1145/279361.279378](https://doi.org/10.1145/279361.279378)
- Sewell et al., "x86-TSO: A Rigorous and Usable Programmer's Model for x86 Multiprocessors", CACM 2010, [DOI 10.1145/1785414.1785443](https://doi.org/10.1145/1785414.1785443)
- [Intel 64 and IA-32 SDM, Vol. 3, Ch. 11 "Memory Cache Control"](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html) (bot-blocked on automated probes; verified via search) -- memory-ordering machine clears, memory-type ordering rules
- Hennessy and Patterson, *Computer Architecture: A Quantitative Approach*, 6th ed., Appendix A (pipeline hazards and memory dependence, print)
