# RowHammer

DRAM cells are analog devices wearing a digital costume: each bit is a capacitor that leaks charge constantly, refreshed periodically by the memory controller. In 2014, Kim et al. proved something vendors had quietly known for months: **leakage is not confined to a cell's own refresh schedule**. Rapidly activating (opening and closing) a DRAM row accelerates charge leakage in *physically adjacent* rows - rows the attacker never touches - until their bits flip. This is RowHammer: a hardware reliability bug that violates the fundamental process-isolation assumption "memory I never access, I cannot affect." Every DDR3 chip tested in the original study was vulnerable, and the bug has since been turned into privilege escalations, browser exploits, network-triggerable attacks, and a read primitive.

## Where the rows actually live

A DRAM system is a hierarchy of independently addressable units:

```text
channel --- DIMM --- rank --- bank group --- bank
                                       |
     one bank: thousands of rows, each row = several KB of cells
     +--------------------------------------------+
     | row N-1   "aggressor"                       |
     | row N     "victim"   (never activated!)     |
     | row N+1   "aggressor"                       |
     +--------------------------------------------+
     ACT:  open a row into the bank's sense amplifiers (row buffer)
     PRE:  close it, precharging bit lines for the next activation
```

A core reads or writes a byte by first issuing ACT on its row (copying the whole row into the row buffer), then column accesses, then PRE. Between PRE and the next ACT on the same row, the cells hold their charge and leak, which is why the controller issues an auto-refresh for every row every 64 ms (32 ms above 85 C, or at doubled rate in 2x-refresh modes). Hammering is simply a tight loop of ACT/PRE cycles on chosen rows - roughly a million activation opportunities fit into one 64 ms refresh window per bank, and an attacker who hammer-runs needs only a slice of that budget. Note the asymmetry with normal workloads: locality-friendly code keeps one row open and streams columns, while a hammer pattern maximizes activations per unit time, which is exactly the signal counter-based mitigations try to detect. Also note the geometry: rows live inside banks, and disturbance is an intra-bank, physically-local effect - aggressor and victim must be neighbors in the same bank, so the attacker must first resolve the system's address mapping (which bits select channel, rank, bank group, bank, row) before any grooming is possible.

## The physics and the numbers

The dominant mechanisms are charge transfer between adjacent cells through the substrate and word-line coupling effects; the details differ across process nodes, which is exactly why some rows and some chips are far more fragile than others. Kim et al. (ISCA 2014) hammered 129 DDR3 modules: 110 (85%) produced bit flips, with the number of activations needed for a first flip (HCfirst) averaging about 139,500 within a 64 ms window on the modules they characterized - and some modules flipping after far fewer, on the order of tens of thousands of activations.

The budget math is what makes this an attack rather than a lab curiosity:

```text
one 64 ms refresh window, one bank:
  available  ~ 1.3M ACTs        (tRC ~ 45-50 ns per ACT/PRE cycle)
  needed     ~ 139K per aggressor row, average DDR3 case (Kim et al.)
  strategy   alternate rows N-1 and N+1 ("double-sided")
             -> ~650K ACTs each: completes in milliseconds of hammering
```

Double-sided hammering (aggressors on both sides of the victim) dominates single-sided because the victim sees leakage from both neighbors. Later generations did not fix the physics: Google's Half-Double result (2021) showed flips induced from a row *two* positions away with fewer hammers, i.e., the disturbance radius grows as cells shrink - and TRRespass (IEEE S&P 2020) found that TRR-equipped DDR4 parts from all three major DRAM vendors still flipped, with disturbance thresholds in the same troublesome range as pre-TRR DDR3 despite the mitigation being active. Newer generations tightened counter policies, but vendors treat exact per-generation thresholds as confidential, and published work (e.g., arXiv 2406.19094 on DDR5 RFM/PRAC) shows the protections trade performance against coverage rather than abolishing the physics.

## Inside the cell: why activation disturbs neighbors

A DRAM cell is one access transistor plus one capacitor, packed at densities that leave only nanometers of separation between neighbors. Activation drives the word line (the row select line) to a full VDD pulse, and that pulse couples capacitively into neighboring structures; simultaneously the sense amplifiers resolve bit-line voltages near the discrimination threshold, so even small amounts of parasitic charge transfer between cells - through substrate currents and shared structures - can push a marginal cell across the 0/1 boundary. A victim cell does not need to be accessed for any of this: its word line stays low, but its stored charge still leaks faster than the refresh clock compensates. Three consequences follow directly:

- Fragility is spatially irregular: manufacturing variation makes some rows flip orders of magnitude sooner than their neighbors, so exploits hunt for weak spots rather than averaging.
- Flips are mostly deterministic for a fixed pattern and fixed chip: the same hammer count on the same rows reproduces the same corruption, which is what makes exploitation reliable rather than statistical.
- Each process generation shrinks the capacitor and, empirically, the safety margin: the general trend of disturbance thresholds has been downward even as counter-based mitigations were added.

## From paper to privilege escalation

| Year | Milestone | What it changed |
| --- | --- | --- |
| 2012-2013 | Kim et al. brief DRAM vendors under NDA | Hardware bug known to industry pre-disclosure |
| 2014 | Kim et al., ISCA: "Flipping Bits in Memory Without Accessing Them" | Public, systematic evidence of DRAM disturbance |
| 2015 | Google Project Zero demos kernel-mode escalation on x86 | Flip a PTE bit, get write access to kernel memory; NaCl sandbox escape |
| 2016 | Drammer (USENIX Security): native Android attack on ARM | No privileged APIs needed; grooming via memory reclaim |
| 2018 | GLitch (NDSS): JavaScript attack via GPU shaders | Browser exploit on ARM Mali; Throwhammer (USENIX Security): remote triggering via RDMA |
| 2019 | RAMBleed (USENIX Security): RowHammer as a *read* side channel | Bits of an OpenSSH key leaked, not just corrupted; ECCploit (IEEE S&P): flips defeat ECC DDR3 |
| 2020 | TRRespass (IEEE S&P): systematic TRR bypass | Non-cyclic hammer patterns defeat DDR4 target row refresh |
| 2021 | Half-Double (Google disclosure) | Distance-2 disturbance; mitigation assumptions weaken further |
| DDR5 era | RFM, later PRAC standardized | Activation counting becomes visible/contractual; arms race continues |

Two disclosure details repay attention. First, the timeline shows a rare responsible-disclosure success: the fundamental result was shared with DRAM vendors roughly two years before publication, yet the mitigations TRR (and later RFM/PRAC) took DRAM-generation timescales to land, which is why software and platform workarounds dominated 2015-2020. Second, the venue progression tells you where the surface moved: architecture conferences for the hardware phenomenon, security conferences once exploitation became the question - the same migration Spectre and Meltdown followed.

## Attack anatomy: grooming, hammering, evading

The hammer loop is the easy part. A working exploit must solve three problems:

```c
/* canonical double-sided hammer, userspace view (Project Zero style) */
char *aggressor_a, *aggressor_b;   /* row-aligned addresses found by grooming */
for (;;) {
    *(volatile char *)aggressor_a = 1;   /* store miss: forces ACT on row N-1 */
    *(volatile char *)aggressor_b = 1;   /* store miss: forces ACT on row N+1 */
    /* lines flushed/evicted so the stores reach DRAM;
       repeat on the order of 100K-1M iterations per refresh window */
}
```

1. **Prowling / grooming** - get secret data into a row adjacent to attacker-controlled rows. With 2 MB transparent huge pages, the low 21 bits of virtual and physical address coincide, so spraying many huge pages and placing two allocations one row apart at a chosen offset puts the victim where the attacker wants it. User-space attackers find the physical layout statistically, by probing for flip locations with canary values.
2. **Hammering** - alternate ACT/PRE on the aggressor rows fast enough, for long enough, within a refresh window. Loads that hit the cache do not generate DRAM activations, so the attacker must flush (clflush), evict, or use non-temporal accesses on every hammer iteration.
3. **Evasiveness** - stay under detectors. Kernel mitigations and performance monitors look for dense same-row activation streams; JS exploits avoid huge pages and flush instructions by using eviction buffers and GPU shaders (GLitch); network attackers let the victim's own workload supply the timing (Throwhammer drives hammering rates through RDMA NICs without any local code execution).

Flipping a bit is privilege escalation when the bit is power: PTE flag bits (writable/present), SELinux/enforcement flags, or sandbox policy words. Flipping a bit in a GPU texture or a JIT-ed wasm page reaches browsers; flipping page-table entries reaches the kernel from a container.

## Reading instead of writing: RAMBleed

Corruption is not even required to steal data. RAMBleed (Kwong, Genkin, Gruss, Yarom, USENIX Security 2019) uses RowHammer flips on DDR4 protected only by *parity* (not full ECC) as a read oracle. Parity memory stores one extra bit per byte-ish group and recomputes it on every read; a silent flip makes the recomputed parity disagree, and the CPU reports a parity error - machine-check abort or corrected-error timing, depending on platform. The attack grooms a secret bit into a cell covered by a parity group the attacker can read, hammers the aggressors around it, and observes whether the read raises a parity error: error means the flip hit the secret bit, and a sequence of such probes with different aggressor pairs reveals the bit's value. The original demonstration leaked bits of an OpenSSH RSA key at a rate on the order of one bit every few seconds - catastrophically slow, and catastrophically sufficient for a long-term signing key.

## The mitigation arms race

| Layer | Mechanism | Why it is not the end of the story |
| --- | --- | --- |
| DRAM (DDR4) | TRR: in-DRAM activation counters trigger extra refreshes of likely victim rows | Counter policies are vendor-secret heuristics; TRRespass non-cyclic patterns evade them |
| DRAM (DDR4 option) | pTRR: proactive refresh of neighbor rows at a fixed rate | Constant throughput/power cost; a fixed policy, not adaptive |
| DRAM + controller (DDR5) | RFM: controller counts activations per bank; on threshold, issues same-bank-group (RFMsb) or all-bank (RFMab) refresh; newer spec updates add PRAC per-row counters with alert signaling | Policy lives partly in host controller/device firmware; evaluation work shows residual risk and overhead tradeoffs |
| Platform | 2x refresh rate, randomized row-to-physical mapping, background scrubbing | Power cost; scrubbing limits how long a flip survives, not whether it happens |
| ECC | SECDED corrects single-bit flips; combined with scrubbing blunts single-shot attacks | Multi-bit flips within one word can survive; ECCploit showed flips can be steered into check-bit positions on DDR3 |
| Software | Heap isolation/padding of sensitive pages, disabling huge pages, blocking flush instructions, detector heuristics | Performance cost; partial coverage (GPU/network paths bypass userspace assumptions) |

The DDR5 generation deserves a closer look because it changes *who counts what*. DDR4's TRR keeps its counters inside the DRAM die, behind an opaque vendor policy: the memory controller cannot see activations per row, cannot audit the policy, and cannot tell whether the counters can be evaded. DDR5's RFM moves the counting into the memory controller, which tracks activation rates per bank (and per bank group) and, on crossing a threshold, issues a same-bank-group or all-bank RFM command so the DRAM spends a refresh cycle protecting likely victims. The newer PRAC refinement pushes precision the other way - per-row activation counters inside the DRAM with explicit alert signaling to the controller - which closes most pattern-evasion routes (you cannot confuse a counter that counts *your exact row*) at the cost of more in-DRAM state and signaling. What remains is policy: thresholds set conservatively cost performance under hammer-like workloads (some workloads see refresh overhead percentages rise measurably), thresholds set loosely leave margin for weak rows, and a determined attacker can still spend the RFM budget to make a machine spend its time refreshing - a denial-of-service channel if not a corruption one.

ECC deserves a special note for interviewers' favorite question: "ECC fixes RowHammer, right?" No - it changes the economics. SECDED corrects one flipped bit per word and detects two, so single random flips become invisible; but hammering flips *clusters* of bits deterministically, and ECCploit demonstrated flips aimed at positions that survive or exploit correction. ECC plus scrubbing is a strong practical mitigation, not a proof. Full ECC on modern server DDR5 raises the bar further: flips must align with check-bit positions, scrubbers correct what does land, and the demonstrated ECC-beating techniques target older DDR3-era topologies rather than current server stacks.

Failure modes of the mitigations themselves are worth naming, because defense-in-depth that fails silently is worse than none:

- A TRR/RFM policy tuned for a benchmark suite can leave weak rows unprotected at temperature extremes (thresholds drift with heat, and 2x-refresh modes change the window math).
- Scrubbing that corrects flips without alerting converts a detected attack into free attack retries - correction telemetry must be monitored, not just consumed.
- Disabling huge pages cluster-wide without measuring often just moves grooming into reclaim-timing attacks (Drammer-style), trading exploit precision for a workload slowdown.
- Activation-rate detectors in the kernel see only the CPU's view: GPU, DMA, and RDMA traffic can hammer without ever crossing a host-side software threshold.

## What CXL and disaggregated memory change

CXL.memory devices put DRAM behind a device-side memory controller and, in pooling deployments, share physical DRAM across tenants that the host never sees directly. Four consequences for RowHammer exposure:

- **Accounting moves.** DDR5 RFM/PRAC assumes the entity counting activations sees them. With device-attached DRAM, activation counting and refresh management must be implemented correctly in the CXL device or switch firmware; the host's counters no longer cover that DRAM by themselves.
- **Tenancy gets finer.** Pooled DRAM means consecutive physical rows may serve different tenants over time, recreating the co-residency conditions that cloud providers spent years suppressing on host memory.
- **The clock slows, the budget remains.** CXL adds on the order of a hundred-plus nanoseconds of latency per access, which lowers the achievable ACT rate - but even degraded rates leave far more activations available per 64 ms window than double-sided thresholds require.
- **State resets.** Activation counters, TRR tables, and RFM budgets are volatile state; a device reset, hot-remove, or error recovery path that clears them without refreshing protected rows hands an attacker a window in which the hammering they did before the reset is forgotten.

Disaggregation is thus a new attack surface, not a mitigation; device vendors must prove their RFM-equivalent policies, and cloud operators must treat pool controllers as security-critical components. The right mental model: RowHammer exposure follows wherever DRAM lives, not wherever the CPU's memory controller looks.

## Reasoning about exposure as an operator

When an interviewer (or an auditor) asks whether *your* platform is exposed, walk this checklist rather than reciting CVE numbers:

- **DRAM generation and mitigation mode**: DDR4-TRR (opaque, historically bypassable), DDR5 with RFM enabled, DDR5 with PRAC negotiated, or HBM/HBM3 stacks whose disturbance behavior and mitigation story differ from commodity DIMMs.
- **ECC topology**: full SECDED with patrol scrubbing vs link-parity only; scrub interval vs attacker persistence.
- **Allocator posture**: are transparent or explicit huge pages granted to untrusted tenants (grooming precision), and can untrusted code execute flush or eviction primitives (clflush availability, JS/WASM eviction attacks)?
- **Co-tenancy**: same-socket VMs sharing banks; container workloads sharing a host's physical pages.
- **Attached memory**: CXL devices and their firmware's activation accounting and reset behavior.

Each item either closes a link in the attack chain (grooming, hammer rate, flip persistence, victim placement) or admits it. The interesting engineering is that no single link is fatal to the attacker - defense is about forcing the chain to span assumptions the attacker cannot satisfy simultaneously.

## Interview lens

- *Why does "I never touched that memory" fail?* Isolation is enforced by address decoding, not physics; activation currents disturb neighbor rows regardless of what the CPU's MMU says.
- *Why is TRR bypassable while ordinary refresh is not?* Ordinary refresh is unconditional; TRR is a probabilistic prediction of victims from activation counters. Any predictor can be fed misleading evidence - hence non-cyclic patterns.
- *Write vs read: why is the read side scarier?* Corruption attacks must flip exactly the right bit; RAMBleed-class attacks only need a reliable timing oracle to exfiltrate, slowly, high-value secrets.
- *How would you harden a fleet?* DDR5 with PRAC/RFM enabled and validated, ECC with aggressive scrubbing, huge-page throttling for untrusted workloads, detector heuristics on activation rates, and per-device (CXL) refresh-management audits.
- *Why did it take a year between the ISCA paper and a working privilege escalation?* The gap is engineering, not physics: mapping virtual to physical layout, grooming the heap so a chosen victim bit neighbors attacker rows, and turning a probabilistic flip rate into a repeatable primitive all took creative systems work - a pattern since repeated for nearly every microarchitectural attack.
- *How does RowHammer differ from Spectre-class attacks?* Spectre abuses architectural side effects of speculative execution and dies with the microarchitectural state; RowHammer abuses an analog property of the DRAM cells and survives cache flushes, reboots of the CPU's speculation machinery, and even works from GPU or network contexts. Different hardware layer, different mitigation owner: branch predictors are a core design problem, refresh management is a DRAM-standard problem. (See `security/advanced/microarch-attacks.md` for the transient-execution family.)

## References

For DRAM organization basics (banks, refresh, timings) see `arch/memory-tech/dram.md`; the transient-execution attack family is covered in `security/advanced/microarch-attacks.md`.

- Kim et al., "Flipping Bits in Memory Without Accessing Them: An Experimental Study of DRAM Disturbance Errors", ISCA 2014 - <https://dl.acm.org/doi/10.1145/2678373.2665726>
- TRRespass project page (VUSec, IEEE S&P 2020) - <https://www.vusec.net/projects/trrespass/>
- GLitch project page (VUSec, NDSS 2018) - <https://www.vusec.net/projects/glitch/>
- RAMBleed project site (USENIX Security 2019) - <https://rambleed.com/>
- "Understanding the Security Benefits and Overheads of Emerging Industry Solutions to DRAM Read Disturbance" (DDR5 RFM/PRAC analysis) - <https://arxiv.org/abs/2406.19094>
