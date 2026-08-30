# Prime+Probe: Last-Level Cache Attacks Without Shared Memory

Flush+Reload -- the subject of the companion page [Flush+Reload and Cache-Template Attacks](flush-reload.md) -- is the sharpest access-driven cache oracle, but it carries a hard precondition: attacker and victim must reach the same physical cache line through their own page tables. Prime+Probe deletes that precondition. The attacker fills ("primes") a set of its own cache lines that contend for one cache set of the shared last-level cache (LLC), lets the victim run, then re-accesses ("probes") those lines and times each one. A probe line that comes back slow was evicted, and on a quiet machine only the victim's congruent traffic can have evicted it. Because the two parties never share a byte of memory -- only a cache *set* -- the oracle works between processes, across privilege rings, between containers and virtual machines, and between SMT siblings on one physical core, and it needs no flush instruction at all. The price is moderate noise plus one genuinely hard engineering problem: constructing the address set that maps to exactly one cache set. That construction, the LLC-specific complications, and the defenses are this page's subject; the broad attack taxonomy lives in [Microarchitectural Attacks](microarch-attacks.md), and the transient-execution attacks that consume similar footprints live in [Side-Channel Attacks and Transient Execution](../../arch/advanced/side-channels.md).

## The Round: Prime, Victim, Probe

```text
one Prime+Probe round, per eviction set E (W lines congruent to one LLC set)
   attacker                                         victim (same core or not)
   --------                                         --------------------------
   PRIME    access all W lines of E  -> E occupies the W ways of the set
   [ victim runs ]  victim touches k >= 0 congruent lines of its own; with
                    the set full, each victim insert evicts an LRU E line
   PROBE    re-access the W lines of E one at a time, timing each:
               hit  (fast)  -> still resident since priming
               miss (slow)  -> evicted during the victim window
   verdict  eviction count (or summed probe time) encodes the victim's
            congruent touches on this set during the window
```

Three properties set the primitive's character. It is *set-granular*: the verdict concerns W ways of contention, not a single 64-byte line, so the attacker learns which slices of address space the victim's working set touched -- roughly a hundred coarse buckets per LLC slice -- rather than which instruction byte. It is *self-contained*: the probed memory belongs to the attacker, so nothing about the victim's page tables, sharing, or deduplication matters. And it is *unprivileged by construction*: plain loads do the priming and probing, which is why the attack survives in environments where CLFLUSH is throttled or trapped and where shared pages simply do not exist.

| Property            | Flush+Reload            | Prime+Probe                    |
|---------------------|-------------------------|--------------------------------|
| Shared memory       | required                | not required                   |
| Verdict granularity | one 64-byte line        | one cache set (W ways)         |
| Eviction sets       | not needed              | the core engineering problem   |
| Cross-VM reach      | only via page dedup     | via the shared LLC, natively   |

## Eviction Sets: The Core Construction Problem

Everything hinges on one address-algebra fact. A physical address splits into tag, set index, and line offset; two lines are *congruent* when their set-index bits (and, on sliced LLCs, their slice) match but their tags differ. Congruent lines contend for the same W ways, so any W+1 of them form an eviction set:

```text
physical address:  [ tag | set index | line offset ]
                          equal set-index bits => congruent: these lines
                          fight for one set; differing tags => distinct
                          lines, and the attacker may own every one of them

candidate pool: 64 attacker addresses, stride chosen to walk sets/tags
   [c0][c1][c2][c3] ... [c63]
        |  group elimination  |   (drop candidates the pool can spare)
        v
   [e0][e1][e2] ... [e7]      exactly W = 8 survivors, all congruent:
                              a minimal eviction set for an 8-way set
```

Real candidate pools are noisy: strides alias across the index bits, some candidates land in other sets, and on sliced LLCs some land in other slices. The classical repair is *group elimination*: repeatedly test whether a candidate collection still evicts, and drop the parts it can spare.

1. Build a test with a fixed outcome: normalize the target set by filling it with W private "scrubber" lines, load a known conflict line (it evicts one scrubber), touch the candidates, then re-time the conflict line. The conflict line survives if and only if the candidates contributed fewer than W congruent lines.
2. Split the candidate pool into groups. For each group, ask: does the pool minus this group still evict? If yes, the group is dead weight -- remove it permanently. When a full pass removes nothing, halve the group size and try again; at group size 1, only lines whose removal breaks eviction survive. Stop when W lines remain: a minimal eviction set.

Each test costs a few hundred loads, and halving keeps the number of passes logarithmic, so construction is fast when candidates are good -- on real hardware, milliseconds to seconds with huge-page-backed candidates. The subtle part is step 1 in reverse: the test needs a *conflict line or scrubber set the attacker controls* in the target set, which is why candidate generation, not the elimination loop, is where attacks live or die.

## LLC Complications: Slices, Huge Pages, and Physical Layout

**Slice hashing.** Modern Intel LLCs are physically distributed: a mesh of slices, each a slice-local set-associative cache, with a *secret hash of the physical address* selecting the slice. An attacker who ignores the hash must build eviction sets against the union of slices and accepts diluted signal; the strong approach replicates the hash. The functions were reverse-engineered from observed collision behavior -- Liu et al.'s IEEE S&P 2015 RSA attack included the reversal as part of its toolchain, and Mao et al. (HPCA 2018) showed the reversal can be refreshed dynamically when microcode or generations change it. The attacker's working unit is therefore "one set of one slice": W = ways per slice, with the slice function in hand.

**Huge pages.** The set-index bits below the page offset are free: for a 4 KiB page the attacker controls bits 0-11, which covers LLCs with up to 64 sets per slice-union. Deeper LLCs index with bits 12-16, unknowable from a 4 KiB mapping -- so attackers mmap 2 MiB pages, where the low 21 physical bits equal the virtual offset and every line's set is a calculation, not a guess. Transparent huge pages, `MAP_HUGETLB`, and allocator alignment all serve here; conversely, denying attackers huge-page backing is a real (if awkward) mitigation.

**Page-table tricks.** `/proc/self/pagemap` once handed unprivileged users their own physical frame numbers; the kernel now zeroes those bits for unprivileged readers, so attackers fall back to layout knowledge: huge-page offsets, known kernel/object placement, or simply over-provisioning candidates and letting group elimination sort congruence from noise. The elimination loop tolerates unknown bits -- it costs more candidates, not a different algorithm.

## The Attack Loop and the Timer Problem

The steady-state loop is prime, yield (or spin on a sibling thread), probe, repeat -- thousands of rounds per second, with the victim's secret-dependent activity bracketed by scheduling or by the victim's own request loop. The verdict statistic is the eviction count or the summed probe time per round; published attacks threshold it exactly like the F+R threshold discussed on the companion page.

Timers are the practical bottleneck outside native code. Native attackers use `rdtsc`/`rdtscp` (or `clock_gettime`) with single-cycle-ish resolution. JavaScript is harsher: `performance.now()` is clamped and jittered by browsers -- on the order of 5 microseconds with cross-origin isolation and 100 microseconds without -- which blurs a hit/miss gap of tens of cycles. The standard responses are amplification (repeat the victim's secret-dependent operation or average thousands of rounds so a single eviction still moves the mean) and *timerless* variants, where the spy derives a clock from the machine itself: a contention or self-eviction loop whose iteration count timestamps the probe, no OS timer consulted. Timer hardening raises the cost of the attack; it does not delete the channel.

## What Leaks

- **RSA exponent bits.** Liu et al.'s "Last-Level Cache Side-Channel Attacks Are Practical" (IEEE S&P 2015) is the landmark: with slice hashes replicated and eviction sets built cross-core and cross-VM (KVM), the square-and-multiply schedule of GnuPG-style RSA was readable set by set, and full keys were recovered across virtual machine boundaries -- the demonstration that Prime+Probe is a cloud-grade threat, not a same-process curiosity.
- **AES T-tables.** Osvik, Shamir, and Tromer's 2006 analysis defined this playbook: the first-round table lookups indexed by secret key bytes light up specific sets, and the paper's Evict+Time and Prime+Probe oracles -- plus its countermeasure catalogue -- still frame the field. Where F+R would need the victim's tables mapped shared, Prime+Probe reads the same leak through set contention alone.
- **Co-location and cross-VM recon.** Co-tenancy is itself a secret: interference measured on primed sets tells a tenant whether someone else shares the LLC. Maurice et al. (NDSS 2017) built robust cache covert channels across cloud VMs on top of this, with SSH keystrokes carried over the channel -- the recon and exfiltration half of the cloud threat model.
- **Set-level vs line-level contrast.** F+R answers "was this exact line touched?" for lines in shared pages; Prime+Probe answers "was one of these W ways touched?" for any victim pages, private or shared -- strictly weaker per reading, strictly broader in reach.

## A Worked Simulation: Eviction Sets and the Oracle

The model below is pure stdlib. It simulates a 64-set x 8-way LRU cache where every access returns a synthetic latency (hit ~ N(15, 2), miss ~ N(200, 12) "cycles"), offers group elimination a noisy pool of 64 candidates of which only 8 are truly congruent, then runs the full Prime+Probe oracle: prime two eviction sets, run an opaque victim pattern, probe, and classify which pattern ran.

```python
# Prime+Probe MODEL, pure stdlib: W-way set-associative cache, group
# elimination, prime/probe oracle over two victim patterns. Latencies are
# synthetic model values (hit ~ N(15,2), miss ~ N(200,12)), not hardware data.
import random
from collections import OrderedDict
random.seed(1337)
SETS, WAYS = 64, 8              # 64 sets x 8 ways; addresses are line numbers
SET_A, SET_B = 13, 40           # two cache sets the attacker primes
THRESH = 100.0                  # hit/miss boundary (cycles, model units)
cache = [OrderedDict() for _ in range(SETS)]   # per-set LRU: oldest first

def time_access(line):
    """Access one line; return its latency. Hit/miss decided by sim state."""
    s = cache[line % SETS]
    if line in s:
        s.move_to_end(line)
        return 15.0 + random.gauss(0, 2)
    s[line] = None
    if len(s) > WAYS:
        s.popitem(last=False)
        return 200.0 + random.gauss(0, 12)
    return 15.0 + random.gauss(0, 2)

def probe(line):
    """Non-destructive probe: time the line without refilling it on miss."""
    if line in cache[line % SETS]:
        return 15.0 + random.gauss(0, 2)
    return 200.0 + random.gauss(0, 12)
def evicts(cands, conflict):
    """Timing-only eviction test: normalize the conflict line's set to exactly
    WAYS private scrubber lines, load `conflict`, then the candidates; the
    conflict line survives iff candidates contributed < WAYS congruent lines."""
    scrub = [100 * SETS + conflict % SETS + i * SETS for i in range(WAYS)]
    for c in scrub:                             # reset the target set
        time_access(c)
    time_access(conflict)                       # conflict evicts one scrubber
    for c in cands:                             # candidate traffic
        time_access(c)
    return time_access(conflict) > THRESH       # re-time the conflict line

def group_elimination(cands, conflict):
    """Shrink cands to a minimal eviction set: drop groups whose removal
    keeps the set evicting; halve the group size when a pass removes nothing."""
    S, g, passes = list(cands), 4, []
    while len(S) > WAYS:
        passes.append(g)                        # group size used by this pass
        removed, i = False, 0
        while i < len(S):
            group = S[i:i + g]
            rest = S[:i] + S[i + g:]
            if rest and evicts(rest, conflict):
                S, removed = rest, True
            else:
                i += len(group)
        if not removed:
            if g == 1:
                break
            g //= 2
    return S, passes

# Candidate pool: only 8 of 64 addresses truly share set A; the rest are noise.
cands = [(i + 1) * SETS + SET_A for i in range(8)]         # congruent, stride 64
cands += [k * SETS + (1 + k % (SETS - 1)) for k in range(56)]   # noise, other sets
random.shuffle(cands)
conflict = SET_A               # a known line inside the target set

E1, passes = group_elimination(cands, conflict)
print("cache model      : %d sets x %d ways, LRU; set index = line %% %d" % (SETS, WAYS, SETS))
print("candidates       : %d offered (8 congruent to set %d, 56 noise)" % (len(cands), SET_A))
print("group elimination: %d -> %d lines, group sizes tried %s" % (len(cands), len(E1), passes))
print("sim ground truth : %d of %d selected lines map to set %d"
      % (sum(1 for c in E1 if c % SETS == SET_A), len(E1), SET_A))

E2, _ = group_elimination([i * SETS + SET_B for i in range(1, 17)], 3 * SETS + SET_B)
victim = {"T-table pass": [9 * SETS + SET_A, 11 * SETS + SET_A],   # hits set 13
          "idle loop   ": [5 * SETS + SET_B]}                      # hits set 40

def prime_probe_round(pattern):
    """One full Prime+Probe round; the spy sees only probe latencies."""
    for c in E1: time_access(c)                    # PRIME both eviction sets
    for c in E2: time_access(c)
    for v in victim[pattern]: time_access(v)       # VICTIM runs (opaque)
    p1 = [probe(c) for c in E1]                   # PROBE: re-time own lines
    p2 = [probe(c) for c in E2]
    return p1, p2

p1, p2 = prime_probe_round("T-table pass")
e1 = sum(1 for t in p1 if t > THRESH)
e2 = sum(1 for t in p2 if t > THRESH)
print("sample round     : set %d -> %d/%d evicted, set %d -> %d/%d evicted"
      % (SET_A, e1, len(E1), SET_B, e2, len(E2)))
print("observed pattern : '%s'" % ("T-table pass" if e1 > e2 else "idle loop").strip())

# 400 rounds, 200 per pattern; collect every probe latency + sim ground truth.
times, evicted, right = [], [], 0
for rep in range(200):
    for pat in ("T-table pass", "idle loop   "):
        p1, p2 = prime_probe_round(pat)
        e1 = sum(1 for t in p1 if t > THRESH)
        e2 = sum(1 for t in p2 if t > THRESH)
        right += (("T-table pass" if e1 > e2 else "idle loop   ") == pat)
        for t in p1 + p2:
            times.append(t)
            evicted.append(t > THRESH)
print("classification   : %d/400 rounds correct (%.1f%%)" % (right, 100.0 * right / 400))

LO, HI, ROW, W = 0, 240, 30, 34
rows = (HI - LO) // ROW
mrow, erow = [0] * rows, [0] * rows
for t, ev in zip(times, evicted):
    r = min(rows - 1, int((t - LO) // ROW))
    (erow if ev else mrow)[r] += 1
peak_m, peak_e = max(max(mrow), 1), max(max(erow), 1)
print("probe histogram  : M=still cached (hit), E=evicted (miss), each class "
      "scaled to its own peak; %d probes" % len(times))
for i in range(rows):
    line = "  %3d-%3d | M %-34s E %-34s" % (
        LO + i * ROW, LO + (i + 1) * ROW - 1,
        "#" * round(W * mrow[i] / peak_m), "*" * round(W * erow[i] / peak_e))
    print(line.rstrip())
```

Output (verbatim run of the script above):

```text
cache model      : 64 sets x 8 ways, LRU; set index = line % 64
candidates       : 64 offered (8 congruent to set 13, 56 noise)
group elimination: 64 -> 8 lines, group sizes tried [4, 4, 2, 2, 1]
sim ground truth : 8 of 8 selected lines map to set 13
sample round     : set 13 -> 2/8 evicted, set 40 -> 0/8 evicted
observed pattern : 'T-table pass'
classification   : 400/400 rounds correct (100.0%)
probe histogram  : M=still cached (hit), E=evicted (miss), each class scaled to its own peak; 6400 probes
    0- 29 | M ################################## E
   30- 59 | M                                    E
   60- 89 | M                                    E
   90-119 | M                                    E
  120-149 | M                                    E
  150-179 | M                                    E **
  180-209 | M                                    E **********************************
  210-239 | M                                    E **********
```

Read the run against the theory. Group elimination took 64 noisy candidates to exactly 8 survivors, and every survivor maps to the target set -- the algorithm recovered congruence from contention timings alone, with no address-bit peeking. The sample round shows the oracle's native resolution: the victim's two T-table lines evicted 2 of 8 primed lines in set 13, while the untouched set 40 reported zero -- per-line eviction counts, not just a binary "touched" bit. The histogram shows why a threshold works: the still-cached and evicted populations separate by two orders of magnitude, the same bimodal structure the F+R page calibrates, just at set granularity. Real hardware degrades every step -- aliasing noise, pseudo-LRU instead of strict LRU, prefetcher and SMT interference, clamped timers -- which published attacks absorb with repetition, not with different physics.

## Countermeasures

- **Cache partitioning.** Intel CAT (part of RDT) assigns cores to Classes of Service with dedicated ways per slice; Linux exposes it through `resctrl`. A partitioned victim has ways a spy's lines cannot enter, so primed sets in the spy's partition stop observing the victim's traffic. Partitioning attacks the *channel capacity* directly, but configuration matters: partitions too coarse to separate tenants, or shared classes, restore the leak (see the [Intel RDT Software Developer Manual](https://www.intel.com/content/www/us/en/developer/articles/manual/intel-rdt-software-developer-manual.html)).
- **Page coloring.** The software analog: the OS allocates physical pages by "color" -- the set-index bits -- so processes land in disjoint sets. Effective in closed kernels and real-time systems; general-purpose kernels struggle because the page cache, THP, and migrators ignore coloring.
- **Constant-time code is necessary but not sufficient.** Constant-time discipline removes secret-dependent *line* usage, and for leaks confined to page-offset bits that is enough. But the set index also includes physical bits above the offset: if secret-dependent control selects between page-aligned objects, the touched *sets* differ while every individual access is textbook constant-time. Defense has to cover allocation placement (single buffer, fixed color) or partitioning, not just data-flow discipline -- the broader constant-time playbook is in [Side-Channel Resistant Cryptography](side-channel-resistant.md).
- **Set randomization.** Scrambled indexing (CEASER-style: a keyed hash remaps addresses to sets, rekeyed periodically) invalidates built eviction sets on each rekey. Treat it as hardening with a lifetime: keys carry limited entropy, and remapping has latency and refresh costs; evaluations of successors such as CEASER-S exist precisely because static scrambling delays rather than stops determined attackers.
- **Kill the sharing and the layout knowledge.** Disable SMT across trust boundaries (siblings share the LLC port and, on some designs, slice-adjacent capacity), keep cross-tenant memory dedup off, restrict `pagemap`, and consider denying attacker-controlled huge pages in multi-tenant environments -- each removes a link from the candidate-generation chain.

## Common Misconceptions

- **"Prime+Probe needs an inclusive LLC."** It needs a shared level where the victim's fills allocate and can evict the spy's primed lines; many modern LLCs are non-inclusive and the attack persists, because victim data still allocates in the shared slice.
- **"Huge pages are mandatory."** They make candidate generation trivial; nothing stops an attacker from offering millions of ordinary-page candidates and letting group elimination find congruence empirically.
- **"It is only a cloud attack."** Same-core SMT siblings, containers on one host, and user/kernel boundaries are all within reach; the VM demos are memorable, not exclusive.
- **"CAT fixes everything."** Way partitioning blunts Prime+Probe but does nothing to Flush+Reload (CLFLUSH invalidates across the coherence domain regardless of classes), and misconfigured or over-subscribed classes leak.

## Interview Angle

*"Why does Prime+Probe work where Flush+Reload fails, and what does it cost?"* Flush+Reload's verdict rides on a shared physical line, so dedup-disabled clouds, private pages, and cross-VM boundaries starve it. Prime+Probe's verdict rides on a shared cache *set*, which exists whenever the hardware is shared at all -- so it reaches VMs and containers natively. The cost: line-level precision collapses to set-level, noise rises, and the attacker must first solve the eviction-set problem -- candidate generation, slice hashing, group elimination -- which is real engineering, not a one-liner.

## References

1. F. Liu, Y. Yarom, Q. Ge, G. Heiser, and R. B. Lee, "Last-Level Cache Side-Channel Attacks Are Practical," IEEE Symposium on Security and Privacy 2015, DOI 10.1109/SP.2015.43. https://doi.org/10.1109/SP.2015.43
2. D. A. Osvik, A. Shamir, and E. Tromer, "Cache Attacks and Countermeasures: The Case of AES," CT-RSA 2006; preprint https://eprint.iacr.org/2005/271
3. Y. Yarom and K. Falkner, "FLUSH+RELOAD: a High Resolution, Low Noise, L3 Cache Side-Channel Attack," USENIX Security 2014; preprint https://eprint.iacr.org/2013/448
4. C. Maurice et al., "Hello from the Other Side: SSH over Robust Cache Covert Channels in the Cloud," NDSS 2017, DOI 10.14722/ndss.2017.23294. https://doi.org/10.14722/ndss.2017.23294
5. K. Mao et al., "Off the Path Beat with the Hammer: Cross-Privilege Cache Attack on Modern Processors," IEEE HPCA 2018 -- LLC slice-hash reversal under adversarial control.
6. Intel Resource Director Technology (Intel RDT) Software Developer Manual -- CAT/CDP/CMT programming interface. https://www.intel.com/content/www/us/en/developer/articles/manual/intel-rdt-software-developer-manual.html
7. M. Schwarz, M. Lipp, and D. Gruss, "Fantastic Timers and Where to Find Them: High-Resolution Timing Attacks in JavaScript," ACM CCS 2017 -- timers and amplification where the platform clamps clocks.

## Cross-References

- [Flush+Reload and Cache-Template Attacks](flush-reload.md) -- the companion deep dive: the shared-line oracle this page relaxes, CLFLUSH semantics, and threshold calibration.
- [Microarchitectural Attacks](microarch-attacks.md) -- the survey view of Spectre/Meltdown-class and cache-channel attacks, with Prime+Probe in context.
- [Side-Channel Resistant Cryptography](side-channel-resistant.md) -- the constant-time discipline, and its limits for set-index footprints.
- [Side-Channel Attacks and Transient Execution](../../arch/advanced/side-channels.md) -- the hardware-side taxonomy: where LLC oracles sit among side channels and transient-execution gadgets.
