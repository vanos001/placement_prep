# Flush+Reload and Cache-Template Attacks: Timing as a Side Channel

Flush+Reload (F+R) turns the most mundane latency difference in a computer -- a cache hit versus a cache miss -- into a high-resolution oracle for "which line of shared memory did the victim touch?" Because the primitive reads no victim data, touches no victim registers, and leaves no architectural trace, it became the reference example of a microarchitectural timing side channel and the disclosure gadget at the heart of Spectre-class attacks. This page is the mechanism deep dive for the Flush+Reload family, presented at the level used in the academic literature: what the attack needs, what CLFLUSH actually does, how the hit/miss verdict is computed, and how defenders shut it down. The broad taxonomy and the transient-execution attacks that consume this oracle live in [Side-Channel Attacks and Transient Execution](../../arch/advanced/side-channels.md); the constant-time coding discipline that removes the leakable footprints lives in [Side-Channel Resistant Cryptography](side-channel-resistant.md).

## The Oracle in One Round

```text
one Flush+Reload round, per probe address in a page shared with the victim
   attacker                                        victim (same physical line)
   --------                                        ---------------------------
   clflush probe   --invalidate line from EVERY-->   line absent from every level
                     level of the coherence domain   of the hierarchy; dirty
                                                     data written back to memory
   [ wait / yield ]  ... victim executes code that touches the line, refilling
                         it in the shared cache
   t0 = rdtscp()
   load   probe          HIT: line present in shared cache -> fast
   t1 = rdtscp()
   delta = t1 - t0
   verdict: delta < T*  -> "hit"  (victim touched the line)
            delta >= T* -> "miss" (victim did not)
```

Three properties make this oracle unusually strong among timing channels. It is *line-granular*: the verdict concerns one 64-byte cache line, not a cache set or an algorithm phase. It is *low-noise*: hit and miss latencies separate by tens of cycles with single-cycle-scale spreads, enabling millions of reliable readings per second. And it needs *no eviction sets*: the probe set is the victim's own code and data, aliased into the attacker's address space by the OS, so the hard part of access-driven attacks -- building address sets that map to one cache set -- disappears entirely.

## Shared Memory: The Load-Bearing Requirement

F+R works only if attacker and victim can reach the same physical cache line through their own page tables. Where that sharing comes from is therefore the whole threat model:

```text
who shares lines with the victim?
  shared libraries (libc, libcrypto, interpreter internals) -> always, same host
  file-backed page cache (mmap of shared files)             -> always, same host
  JIT/bytecode metadata, font and image tables              -> always, same host
  memory deduplication (KSM in KVM hosts, cloud page dedup) -> only if enabled
  container image layers / read-only binaries               -> config-dependent
no shared line -> no Flush+Reload signal (Prime+Probe still applies)
```

Deduplication deserves special attention because it manufactures sharing that did not exist architecturally: a hypervisor that collapses byte-identical pages across tenants hands every tenant a physical, timing-visible equality oracle. The Linux KSM design and its attack literature are covered in [KSM Page Merging](../../os/advanced/ksm-page-merging.md); the classic public-cloud demonstration is Zhang et al. (CCS 2012), who extracted private keys from a co-resident VM once page dedup was switched on.

Prime+Probe is the necessary fallback where pages cannot be shared; attacker and victim then communicate only through a shared cache *index* -- the attacker primes the set and measures which of its own lines got evicted. That is strictly harder to set up (eviction sets) and noisier, which is why the two techniques are complements, not competitors:

| Primitive    | Shared memory? | Needs eviction set? | Verdict granularity | Relative noise |
|--------------|----------------|---------------------|---------------------|----------------|
| Flush+Reload | required       | no                  | single cache line   | very low       |
| Prime+Probe  | not required   | yes                 | cache set           | moderate       |
| Evict+Time   | not required   | yes                 | victim execution    | higher         |
| Flush+Flush  | required       | no                  | single cache line   | very low       |

## CLFLUSH Semantics, Precisely

The flush half of the oracle is one instruction, and its exact contract matters both to attackers calibrating and to defenders reasoning about exposure. Per the Intel SDM entry for CLFLUSH:

- It *invalidates from every level of the cache hierarchy in the cache coherence domain* the line containing the addressed byte; if the line is dirty at any level, the data is written back to memory. This is why F+R works against the shared LLC even when attacker and victim run on different cores.
- It may be used at any privilege level and behaves like a byte *load* for permission checking: it faults on unmapped addresses, it is allowed on execute-only segments, and like a load it sets the accessed bit, not the dirty bit, in page tables.
- It is *not* a serializing instruction. Executions of CLFLUSH are ordered with respect to each other, to writes, to locked read-modify-write instructions, and to fence instructions -- but *not* with respect to speculative fetches or PREFETCHh, and not with respect to CLFLUSHOPT or CLWB. Speculative hardware is free to re-cache the line before, during, or after the flush.

The folk description of CLFLUSH as "an implicit fence" is thus half right: it is ordered against ordinary writes and fences, which is what makes a `flush -> fence -> time` sequence meaningful, but nothing stops the line from being speculatively pulled back. The reload half is bracketed by construction instead: code times it against RDTSCP or `LFENCE; RDTSC` so the measurement window around the load is deterministic.

The optimized successors keep the invalidation semantics and relax ordering for performance:

| Instruction | Introduced for | Invalidation behavior | Ordering notes (SDM) |
|-------------|----------------|-----------------------|----------------------|
| CLFLUSH     | SSE2-era       | line, all levels, writeback | ordered with writes, locked RMW, fences |
| CLFLUSHOPT  | Skylake-era    | line, all levels, writeback | ordered with fences, locked RMW; with older writes to the flushed line only |
| CLWB        | persistent-memory era | writeback without invalidate | can be promoted to invalidate by a following CLFLUSHOPT |

For the oracle, the two invalidate forms are interchangeable as the flush half; CLFLUSHOPT exists mainly so that producers of clean writeback traffic -- kernels, filesystems, persistent-memory runtimes -- stop paying CLFLUSH's full ordering against unrelated stores.

## From Latencies to Verdicts: Choosing the Threshold

The verdict line `delta < T*` hides the only statistics in the attack. Hit and miss latencies are distributions, not constants, and `T*` is machine-specific: it depends on the cache levels involved, prefetcher behavior, SMT interference, and frequency scaling. Practitioners calibrate by measuring both distributions on the target and picking the boundary that minimizes classification error -- which lands at the equal-density crossing of the two distributions, not at a midpoint guess. The following simulation is a pure-stdlib *model* of that calibration step; the latencies are synthetic Gaussian draws, not real measurements:

```python
# Flush+Reload timing-separation MODEL (not real measurements).
# Synthetic hit/miss latency samples from Gaussian models; sweep thresholds
# to find the one that minimizes classification error. Pure stdlib.
import math
import random
import statistics

random.seed(486)

N_PER_CLASS = 100_000
HIT_M, HIT_SD = 210.0, 8.0          # model parameters (cycles)
MISS_M, MISS_SD = 280.0, 14.0

hits = [random.gauss(HIT_M, HIT_SD) for _ in range(N_PER_CLASS)]
misses = [random.gauss(MISS_M, MISS_SD) for _ in range(N_PER_CLASS)]

# Coarse ASCII histogram: 12-cycle row bins shared by both populations.
LO, HI, ROW = 170, 338, 12
rows = (HI - LO) // ROW
hrow = [0] * rows
mrow = [0] * rows
for x in hits:
    hrow[min(rows - 1, max(0, int((x - LO) // ROW)))] += 1
for x in misses:
    mrow[min(rows - 1, max(0, int((x - LO) // ROW)))] += 1
peak = max(hrow + mrow)
print("latency histogram (MODEL; 100k hit + 100k miss samples; H=hit, M=miss)")
for i in range(rows):
    print(("  %3d-%3d | H %-30s M %-30s" % (
        LO + i * ROW, LO + (i + 1) * ROW - 1,
        "#" * round(30 * hrow[i] / peak), "*" * round(30 * mrow[i] / peak))).rstrip())

hit_mean = statistics.mean(hits)
miss_mean = statistics.mean(misses)
print("measured hit mean  : %.2f cycles (model N(%.0f, %.0f))" % (hit_mean, HIT_M, HIT_SD))
print("measured miss mean : %.2f cycles (model N(%.0f, %.0f))" % (miss_mean, MISS_M, MISS_SD))

# Optimal threshold: sweep 0.25-cycle boundaries and keep the value that
# minimizes total misclassifications (classify x < T as hit, x >= T as miss).
best_t, best_err = None, None
t = 220.0
while t <= 260.0:
    err = sum(x >= t for x in hits) + sum(x < t for x in misses)
    if best_err is None or err < best_err:
        best_t, best_err = t, err
    t += 0.25

fp = sum(x < best_t for x in misses) / N_PER_CLASS   # miss read as hit
fn = sum(x >= best_t for x in hits) / N_PER_CLASS    # hit read as miss
print("sweep 220..260 cycles -> optimal threshold T* = %.2f" % best_t)
print("total misclassified  : %d of %d (%.4f%%)" % (best_err, 2 * N_PER_CLASS, 100 * best_err / (2 * N_PER_CLASS)))
print("FP rate at T* (miss read as hit) : %.6f" % fp)
print("FN rate at T* (hit read as miss) : %.6f" % fn)

# Analytic check: equal-prior crossing of the two Gaussian densities.
g = lambda x, m, s: math.exp(-((x - m) ** 2) / (2 * s * s)) / s
lo_x, hi_x = HIT_M, MISS_M
for _ in range(80):
    mid = (lo_x + hi_x) / 2
    if g(mid, HIT_M, HIT_SD) > g(mid, MISS_M, MISS_SD):
        lo_x = mid
    else:
        hi_x = mid
print("analytic equal-density crossing  : %.2f (Bayes boundary, equal priors)" % ((lo_x + hi_x) / 2))
print("separation (miss_mean - hit_mean)/hit_sd = %.1f hit-sigmas" % ((miss_mean - hit_mean) / HIT_SD))
```

Output (verbatim run of the script above):

```text
latency histogram (MODEL; 100k hit + 100k miss samples; H=hit, M=miss)
  170-181 | H                                M
  182-193 | H #                              M
  194-205 | H ################               M
  206-217 | H ############################## M
  218-229 | H #########                      M
  230-241 | H                                M
  242-253 | H                                M **
  254-265 | H                                M *******
  266-277 | H                                M ****************
  278-289 | H                                M ******************
  290-301 | H                                M **********
  302-313 | H                                M ***
  314-325 | H                                M
  326-337 | H                                M
measured hit mean  : 210.00 cycles (model N(210, 8))
measured miss mean : 279.99 cycles (model N(280, 14))
sweep 220..260 cycles -> optimal threshold T* = 236.25
total misclassified  : 143 of 200000 (0.0715%)
FP rate at T* (miss read as hit) : 0.000980
FN rate at T* (hit read as miss) : 0.000450
analytic equal-density crossing  : 236.34 (Bayes boundary, equal priors)
separation (miss_mean - hit_mean)/hit_sd = 8.7 hit-sigmas
```

Two details are worth internalizing. The empirical sweep lands at 236.25 cycles while the naive midpoint of the means would be 245: because the miss distribution is wider (14 vs 8 cycles), the optimal boundary sits closer to the hit mean, and a midpoint guess inflates the error severalfold. The residual FP/FN rates are also not noise to ignore: at millions of probes per second, even a 0.1% error rate must be absorbed by repetition and majority voting -- exactly how published attacks reach reliable bit recovery. Real hardware adds correlated noise (interrupts, SMT siblings, prefetching) that this model omits; the countermeasure is the same, more trials.

## Cache-Template Attacks: Automating the Probe Set

Knowing the mechanism is not enough; an attacker must also discover *which* lines of a megabyte-scale shared library leak, given some victim behavior of interest. Cache-template attacks (Gruss, Maurice, and Mangard, USENIX Security 2015) made that step systematic and gave the technique pair in this page's title its second name:

1. **Trigger.** Repeatedly induce the victim behavior of interest (a keystroke, a packet arrival, a file open) while the spy holds candidate probe sets.
2. **Template.** For every line of the shared pages, record how strongly the F+R time series correlates with the trigger. Lines that light up in lockstep form the template for that behavior.
3. **Monitor.** Run the probes continuously against the template; each occurrence of the behavior is now an event readable from another process.

The defensive reading is the important half: any code path a secret can steer -- a table lookup indexed by key material, a branch over user input that touches different lines -- leaves a fingerprint this procedure finds automatically, without hand-reversing the binary.

## Three Case Studies in the Literature

**AES T-tables, to practice (IEEE S&P 2011).** Osvik, Shamir, and Tromer had already defined the access-driven menu in their CT-RSA 2006 analysis of AES -- Evict+Time, Prime+Probe, and the flush-based reload variant -- together with countermeasures that still frame the field. Gullasch, Bangerter, and Krenn turned the flush-based variant into a near-real-time full-key-recovery attack on AES-128 with compressed tables: it needed neither the ciphertext nor plaintext statistics, ran from an unprivileged account, and synchronized on the OS scheduler (via a deliberately induced scheduler-DoS trick) to time reloads with high precision. It is the canonical demonstration that the oracle is a practice-grade threat, not a lab curiosity.

**RSA exponent bits (USENIX Security 2014).** Yarom and Falkner carried F+R across cores onto the shared L3 and used it to monitor the RSA exponentiation inside GnuPG 1.4.13, recovering on average 96.7% of the secret-key bits from a single signature or decryption round, both between unrelated processes and between virtual machines: the exponent-dependent pattern of modular multiplications leaks the key bit by bit. The authors' fixed-pattern replacement for the leaky exponentiation became the template for the fix, and Bernstein et al. later formalized the same story for sliding-window exponentiation in GMP's `mpz_powm` ("Sliding right into disaster," CHES 2017). The standing lesson: crypto and bignum libraries inherited from general-purpose computing are not side-channel resistant until audited (see [Side-Channel Resistant Cryptography](side-channel-resistant.md)).

**Cross-VM (CCS 2012) and the stealth variant (DIMVA 2016).** Zhang, Juels, Reiter, and Ristenpart showed F+R working between virtual machines on public IaaS by using memory deduplication to manufacture the shared pages -- the result that turned "disable cross-tenant dedup" into standard cloud hardening. Gruss, Maurice, Wagner, and Mangard then demonstrated a variant that never reloads at all: Flush+Flush relies only on the *execution time of the flush instruction itself*, which differs depending on whether the line is cached. It performs no memory accesses, so it evades detectors that watch a spy's cache hits and misses.

## Mitigations

The defense stack maps one-to-one onto the attack's requirements:

- **Constant-time code.** Remove secret-dependent memory footprints so the lines the victim touches do not encode secrets. This is the only defense that works even where sharing cannot be removed, and it is the discipline of [Side-Channel Resistant Cryptography](side-channel-resistant.md). Table-based AES was the poster child: OpenSSL's move away from secret-dependent T-table lookups (and eventually to AES-NI hardware instructions) retired the 2011-era attack surface wholesale.
- **Stop manufacturing sharing.** Disable cross-tenant memory deduplication -- KSM for tenant workloads, and the analogous Windows feature Microsoft disabled by default after the 2016 dedup attacks (see [KSM Page Merging](../../os/advanced/ksm-page-merging.md)). Shared libraries and the page cache are architectural; dedup is a configuration choice.
- **Page-table isolation.** KPTI, the Meltdown mitigation (mechanics in [KPTI](../../os/advanced/kpti.md)), removes kernel-only pages from the user page tables, taking the kernel's code and data out of a user-mode spy's probe space. It does nothing about user-to-user sharing on the same host and is not a substitute for crypto hygiene.
- **Cache partitioning.** Intel CAT-style way partitioning blunts Prime+Probe by guaranteeing private capacity. It does not stop F+R: CLFLUSH invalidates the physical line across the whole coherence domain regardless of which partition owns the way, and a shared line stays shared.
- **Flush instruction hygiene.** CLFLUSHOPT and CLWB reduce the *performance* cost of legitimate flushing but are equivalent flush primitives from the attack's point of view -- there is no instruction-level "safe flush" to prefer. Practical hardening is environmental: hardened platforms restrict unprivileged access to high-resolution timers and cache-monitoring performance events precisely because both feed this attack class.

## Detection: What a Defender Can Measure

F+R leaves no architectural trace, so detection is necessarily statistical, and the Flush+Flush paper's own evaluation maps the terrain. Detectors counting a *spy's* cache references and misses fail against Flush+Flush by construction (it causes neither), but the same paper observes that with both F+R and Flush+Flush the *victim* experiences an elevated last-level-cache miss rate -- the spy's flushes keep evicting the victim's working set. Practical signals include:

- Elevated LLC miss rates in a process that should be cache-resident, measured from the victim's own hardware counters or through [eBPF/perf tooling](../../linux/kernel/tracing/ebpf-verifier.md).
- Flush-loop behavior: most PMUs expose no direct CLFLUSH-retired counter, but flush-heavy code shows up as abnormally low instructions-per-cycle paired with LLC miss bursts, and Flush+Flush's tell is precisely a sustained high rate of flush instructions.
- Timer-hardening tripwires: code that repeatedly measures sub-microsecond intervals while issuing cache-eviction-scale memory traffic is doing something ordinary workloads do not.

The same statistical logic runs in reverse for the code side: dudect-style testing compares the timing distributions of a function under fixed versus random secrets and flags leakage before deployment. And when a novel cache-timing technique appears -- as has happened repeatedly since 2006 -- the responsible path is coordinated disclosure to the affected implementers (OS, crypto library, hypervisor) so mitigations and detections ship before details do.

## Common Misconceptions

- **"Flush+Reload needs an inclusive LLC."** It needs a cache level shared by both parties where the victim's fill is observable; many modern LLCs are non-inclusive and the oracle survives, because the attacker's reload simply hits the line the victim's access brought in. Inclusivity matters more for Prime+Probe eviction logic.
- **"CLFLUSH is serializing."** It is not: it is ordered against writes, locked read-modify-write operations, and fences, but speculative fetches can re-cache the line at any time.
- **"The threshold is a universal constant."** It is a property of one machine, one cache level, and one measurement idiom; published attacks calibrate per target.
- **"Dedup is a hardware feature."** In the cloud attacks it is an administrator configuration (memory deduplication), which is why it has a clean organizational fix.
- **"F+R is only about cryptography."** Cache-template results include keystrokes and user-interface events; any secret-steered memory footprint leaks.

## Interview Angle

*"Why is Flush+Reload both the most precise and the most restricted cache attack?"* Precision comes from the shared-line requirement: the attacker addresses exactly the lines the victim executes, with hit/miss separation of tens of cycles, and needs no eviction sets. Restriction comes from the same requirement: without shared pages -- no dedup, no shared library mapped into the spy's address space -- the attack produces nothing, and the attacker falls back to Prime+Probe, trading granularity and noise for independence from sharing.

*"A cloud tenant asks to enable KSM to save memory. What do you tell them?"* That deduplication is a published timing-oracle primitive ([KSM Page Merging](../../os/advanced/ksm-page-merging.md) has the attack chain and references), that the mitigation is keeping dedup off across trust boundaries, and that the memory savings must be weighed against a demonstrated attack class, not a theoretical one.

## References

1. Y. Yarom and K. Falkner, "FLUSH+RELOAD: a High Resolution, Low Noise, L3 Cache Side-Channel Attack," USENIX Security Symposium, 2014. https://www.usenix.org/conference/usenixsecurity14/technical-sessions/presentation/yarom
2. D. Gruss, C. Maurice, and S. Mangard, "Cache Template Attacks: Automating Attacks on Inclusive Last-Level Caches," USENIX Security Symposium, 2015. https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/gruss
3. D. A. Osvik, A. Shamir, and E. Tromer, "Cache Attacks and Countermeasures: The Case of AES," CT-RSA 2006, Springer LNCS, DOI 10.1007/11605805_1; preprint https://eprint.iacr.org/2005/271
4. S. Gullasch, E. Bangerter, and S. Krenn, "Cache Games -- Bringing Access-Based Cache Attacks on AES to Practice," IEEE Symposium on Security and Privacy, 2011, DOI 10.1109/SP.2011.22; preprint https://eprint.iacr.org/2010/594
5. D. Gruss, C. Maurice, K. Wagner, and S. Mangard, "Flush+Flush: A Fast and Stealthy Cache Attack," DIMVA 2016, Springer LNCS, DOI 10.1007/978-3-319-40667-1_14; PDF https://gruss.cc/files/flushflush.pdf
6. Y. Zhang, A. Juels, M. K. Reiter, and T. Ristenpart, "Cross-VM Side Channels and Their Use to Extract Private Keys," ACM CCS, 2012, DOI 10.1145/2382196.2382230
7. P. C. Kocher, "Timing Attacks on Implementations of Diffie-Hellman, RSA, DSS, and Other Systems," CRYPTO 1996, Springer LNCS, DOI 10.1007/3-540-68697-5_9
8. Intel 64 and IA-32 Architectures SDM, CLFLUSH / CLFLUSHOPT instruction entries (text mirrored at https://www.felixcloutier.com/x86/clflush and https://www.felixcloutier.com/x86/clflushopt)
9. W.-M. Hu, "Reducing Timing Channels with Fuzzy Time," Journal of Computer Security, 1992, DOI 10.3233/jcs-1992-13-404 -- early timing-channel mitigation work predating the cache-attack era.
10. D. J. Bernstein, J. Breitner, D. Genkin, L. Groot Bruinderink, N. Heninger, T. Lange, C. van Vredendaal, and Y. Yarom, "Sliding Right into Disaster: Left-to-Right Sliding Windows Leak," CHES 2017. https://sidechannels.cr.yp.to/slidingright/slidingright-20170628.pdf

## Cross-References

- [Side-Channel Attacks and Transient Execution](../../arch/advanced/side-channels.md) -- taxonomy, Spectre/Meltdown, and how this page's oracle feeds transient attacks.
- [Side-Channel Resistant Cryptography](side-channel-resistant.md) -- the constant-time programming discipline that removes leakable footprints.
- [Exploit Mitigations and Memory Safety](exploit-mitigations.md) -- where microarchitectural hardening sits among OS-level defenses.
- [KSM Page Merging](../../os/advanced/ksm-page-merging.md) -- the deduplication mechanism that manufactures shared pages, with its own attack literature.
- [KPTI](../../os/advanced/kpti.md) -- page-table isolation and its own Flush+Reload oracle demo for transient execution.
- [Rowhammer](../../arch/advanced/rowhammer.md) -- the sibling DRAM-level microarchitectural attack, sometimes chained with cache oracles; [Persistent Memory](../../storage/persistent-memory.md) shows CLWB/CLFLUSHOPT in their intended writeback-ordering role.
