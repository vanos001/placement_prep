# Transient-Execution Attacks: Spectre, Meltdown, and the Co-Design Problem

The architectural contract of a modern out-of-order core is "wrong-path state is invisible": when a mispredicted branch or a faulting load is squashed, every register it touched is rolled back and the instruction, for all software-visible purposes, never ran. Transient-execution attacks break the *microarchitectural* half of that contract. A transient instruction never commits its architectural effects, but the cache lines it touched, the buffers it filled, and the predictor entries it trained all survive the squash — and a second, slower program can read those footprints. Spectre showed this is exploitable when the attacker supplies the *gadget*; Meltdown showed it is exploitable even when the victim supplies *no* cooperation at all.

This page treats the leak as an architecture/OS co-design problem, which is exactly how the mitigations landed. The ISA owns none of the leaked state; the kernel owns the privilege boundary but not the microarchitecture; so the fixes had to be split four ways — microcode (IBRS, SSBD, MD_CLEAR), compiler and build tooling (retpoline, LFENCE, LVI-CFI), kernel text and page tables (KPTI, `array_index_nospec()`, RSB stuffing), and per-process policy (`prctl(PR_SET_SPECULATION_CTRL)`). The cache oracles that convert footprints into bytes are the subject of [Flush+Reload](flush-reload.md) and [Prime+Probe](prime-probe.md); the wide survey of microarchitectural attacks including RowHammer and TEE compromises is [Microarchitectural Attacks](microarch-attacks.md).

## The Three Ingredients Every Transient Leak Needs

Every published variant, from the 2018 wave through the 2025 ones, composes the same three ingredients:

1. **A wrong-path window.** Some mechanism makes the core execute instructions that will never commit: a poisoned branch target (BTB/RSB), a mispredicted direction (PHT), a store-to-load disambiguation bet, a faulting or helper-aborted load, or a transactional abort. The window length — cycles until the mistake resolves — bounds how much can execute transiently.
2. **Secret-bearing microarchitectural state.** The window's loads must ingest a secret: a kernel page (Meltdown, L1TF), an enclave page (Foreshadow), an out-of-bounds array element pulled in by a gadget (Spectre), or residue left in a store buffer, fill buffer, or load port by whoever ran last (MDS, TAA).
3. **A covert channel.** The ingested value must leave a *measurable* footprint before the squash. The standard construction is a dependent load `probe[v * LINE]`: the secret byte `v` selects which of 256 cache lines gets warmed, and a flush+reload scan recovers `v` by timing.

```text
one Spectre-v2-style round: poison -> transient window -> squash -> reload
  attacker                             core front end                 cache
  --------                             --------------                 -----
  train BTB entry 0x1000 -> 0x2000     (warm-up branches, no commits
                                        into the gadget's secret path)
  clflush all 256 probe lines
  call victim guard @0x1000
                 fetch guard           BTB HIT (poisoned): target 0x2000
                 fetch gadget @0x2000  WRONG PATH, core cannot know yet
                       |                 -> transient window OPENS
                 load  data[idx]       secret byte v enters the pipeline
                 load  probe[v*LINE]   line for v filled ---------->  HOT
                       |
  guard resolves: idx >= size           window CLOSES, gadget squashed
                 architectural regs rolled back; v never existed
                                              line for v: STILL HOT
  reload probe lines one by one:
        hit  ~5 cycles  -> only line v
        miss ~50 cycles -> the other 255
  argmin over candidates  =>  v recovered
```

Nothing in the architectural state discriminates this round from a clean run; only the cache differs. That asymmetry — rollback that is complete for registers but absent for caches and buffers — is the whole bug, and no ISA revision has yet closed it.

## A Taxonomy of the Poisoned-Resource Family

The family is best organized by *what makes the core go wrong* and *what state the secret is sampled from*. The kernel's own documentation ([spectre.rst](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/spectre.rst), [mds.rst](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/mds.rst)) and the spectre-meltdown-checker CVE table use the same split; every CVE below was verified against fetched kernel docs and the checker's README.

| Class | Variant | CVE | Wrong-path trigger | State sampled |
|-------|---------|-----|--------------------|---------------|
| ingest | Spectre v1 (Bounds Check Bypass) | CVE-2017-5753 | mispredicted bounds branch (PHT) | OOB array element |
| ingest | Spectre v1 swapgs | CVE-2019-1125 | swapgs/segment-base confusion | kernel pointers |
| ingest | Spectre v2 (Branch Target Injection) | CVE-2017-5715 | poisoned BTB target | gadget-selected loads |
| ingest | SpectreRSB | none assigned | RSB underfill / undermining | gadget-selected loads |
| ingest | Spectre v4 (SSB) | CVE-2018-3639 | store-to-load disambiguation | overwritten store data |
| direct | Meltdown-US (v3) | CVE-2017-5754 | faulting privileged load | kernel pages via L1D |
| direct | Meltdown-3a | CVE-2018-3640 | system-register read fault | privileged MSR bits |
| direct | L1TF / Foreshadow | CVE-2018-3615/3620/3646 | PTE present-bit / reserved-bit fault | L1D under stale PTE |
| sample | MDS: MSBDS/MFBDS/MLPDS/MDSUM | CVE-2018-12126/12130/12127; CVE-2019-11091 | buffer-sampling gadget | store buffer, fill buffer, load ports |
| sample | TAA (ZombieLoad v2) | CVE-2019-11135 | TSX transactional abort | fill buffers |
| inject | LVI | CVE-2020-0551 | stale buffer value re-injected into load | attacker-chosen gadget inputs |
| ingest | Retbleed | CVE-2022-29900 (AMD) / CVE-2022-29901 (Intel) | `ret` misprediction via BPB/RSB | gadget-selected loads |
| ingest | SRSO (Inception) | CVE-2023-20569 | untrained `ret` aliasing BTB entry | gadget-selected loads |

Two classes deserve the contrast spelled out. **Ingest-class** (all Spectres, Retbleed, SRSO) needs the victim to *execute attacker-shaped speculation*: the attacker poisons a predictor, and the victim's own code contains or speculatively reaches a gadget that turns a secret into an address. **Direct/sample-class** (Meltdown, L1TF, MDS, TAA) needs no victim gadget: a faulting load forwards privileged data before the fault lands, or a sampling gadget drains a shared internal buffer. That is why Meltdown-family fixes had to live in page tables and microcode, while Spectre-family fixes had to live in compilers, binaries, and gadget hygiene. The ingest class keeps growing — Retbleed turned the *return* predictor into the poisoned resource, and it is deep-dived in [Retbleed](../../linux/debugging/retbleed.md) (retpoline actually *amplifies* it on AMD Zen); SRSO (CVE-2023-20569) is its AMD successor handled by safe-RET untraining, per the kernel's [srso.rst](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/srso.rst).

## Mitigations: Who Pays, Where

| Mitigation | Targets | Mechanism | Rough cost | Linux knob / artifact |
|------------|---------|-----------|------------|------------------------|
| Retpoline | Spectre v2 | indirect branches converted to `ret`-based trampolines the BTB cannot poison | small on most parts; SKL needs call-depth tracking | `spectre_v2=retpoline`, `-mretpoline` (Google retpoline FAQ) |
| IBRS / eIBRS | v2, Retbleed (Intel) | MSR-restricted speculation; eIBRS is hardware-mode | IBRS costly, eIBRS near-free | sysfs `Mitigation: Enhanced IBRS` |
| IBPB | cross-privilege prediction bleed | serializing flush of branch predictors | per-context-switch | sysfs `IBPB: conditional / always-on` |
| STIBP | SMT sibling poisoning | per-thread predictor restriction | SMT throughput | sysfs `STIBP: ...` |
| LFENCE + `array_index_nospec()` | v1-style bounds bypass | data-dependency fence; mask `idx` to `idx < size` | per-site codegen | [nospec.h](https://raw.githubusercontent.com/torvalds/linux/master/include/linux/nospec.h) |
| KPTI | Meltdown-US | split user/kernel page tables | syscall + TLB pressure | `pti=on`; see [Page Table Isolation](../../linux/performance/page-table-isolation.md) |
| VERW buffer clearing (MD_CLEAR) | MDS, TAA, MMIO stale data | microcode clears fill/store buffers on ring transitions | per-transition | `mds=full,nosmt`, `tsx_async_abort=full` |
| PTE inversion + L1D flush | L1TF | non-present PTEs point at invalid PFNs; flush L1D on VM entry | VM-entry cost | `l1tf=full` |
| SSBD | Spectre v4 | disable speculative store bypass, per thread or per task | context-switch heavy | `spec_store_bypass_disable=`, `prctl` (below) |
| RSB stuffing / call-depth tracking | RSB underflow, Retbleed (SKL) | overwrite RSB (32 loops) or count calls (SKL counter) | small | `CONFIG_MITIGATION_CALL_DEPTH_TRACKING`, `RSB_CLEAR_LOOPS=32` |

The masking pattern deserves its own sentence because it is the one mitigation ordinary code can apply without microcode or privileges. Linux's `array_index_mask_nospec()` (from [nospec.h](https://raw.githubusercontent.com/torvalds/linux/master/include/linux/nospec.h)) computes, in branchless arithmetic, a mask of all ones when `index < size` and zero otherwise, so the *speculative* index is clamped even though the architectural comparison still happens exactly as before — the transient path can only ever touch a valid element, so there is no OOB secret to ingest. The build-time complement is objtool: the kernel's [objtool.txt](https://raw.githubusercontent.com/torvalds/linux/master/tools/objtool/Documentation/objtool.txt) documents retpoline validation ("ensures that all indirect calls go through retpoline thunks"), return-thunk validation and *untraining* validation (the SRSO safe-RET discipline), and straight-line-speculation checks — i.e., the kernel audits its own text so that gadgets cannot survive a rebuild.

Mitigations also interact, and the interactions are documented rather than folkloric. The boot-option table states that on TAA-affected CPUs `mds=off` alone is ignored: you must pass `tsx_async_abort=off` too, because the VERW clearing path is shared. And Spectre v4 chose a *per-process* control instead of a global one, because SSBD's cost made a blanket-on policy unacceptable for seccomp-sandboxed workloads: `prctl(PR_SET_SPECULATION_CTRL, PR_SPEC_STORE_BYPASS, ...)` with `PR_SPEC_PRCTL` marking per-task controllability ([spec_ctrl.rst](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/userspace-api/spec_ctrl.rst)).

## The Kernel's Contract: sysfs, prctl, and Boot Parameters

The kernel exposes the whole mitigation state in one read-only interface. The file names below are verified against both the ABI documentation and `drivers/base/cpu.c` — including one naming trap: the SRSO file is **`spec_rstack_overflow`**, not `srso`, matching the doc filename but not the acronym.

```text
/sys/devices/system/cpu/vulnerabilities/
  meltdown  spectre_v1  spectre_v2  spec_store_bypass  l1tf  mds
  tsx_async_abort  itlb_multihit  srbds  mmio_stale_data  retbleed
  spec_rstack_overflow  gather_data_sampling  reg_file_data_sampling
  indirect_target_selection  tsa  vmscape  old_microcode  ghostwrite
```

Each file renders strings like `Mitigation: Retpolines`, `Mitigation: Enhanced IBRS`, `IBPB: conditional`, `STIBP: conditional`, or `Mitigation: usercopy/swapgs barriers and __user pointer sanitization` (the v1 string, verbatim from spectre.rst). Boot parameters select policy per bug: `spectre_v2=retpoline|ibrs|eibrs|auto`, `spectre_bhi=` (Branch History Injection), `spec_store_bypass_disable=off|on|prctl|seccomp`, `mds=full,nosmt`, `l1tf=full`, `tsx_async_abort=full,nosmt`, `retbleed=auto,nosmt`; the `mitigations=auto,nosmt` umbrella expands to the per-bug defaults listed in kernel-parameters.txt. This interface is also where [ASLR](../../linux/kernel/memory/aslr.md) meets transient execution: KASLR's entropy only holds if the predictor-poisoning class is mitigated, since a v2 gadget can speculatively walk the kernel image one cache line at a time.

## Detecting Exposure: spectre-meltdown-checker

The [spectre-meltdown-checker](https://github.com/speed47/spectre-meltdown-checker) script is the de-facto audit tool: it inspects CPUID/MSR exposure of each mitigation (SPEC_CTRL, ARCH_CAPABILITIES, SSBD, RDCL_NO), the running kernel's compiled-in protections, and microcode version, then prints a per-CVE verdict matrix whose CVE↔name mapping matches the taxonomy table above. Two habits make its output trustworthy: run it after a microcode update *and* a reboot (IBRS/SSBD are set at boot), and read the per-variant detail lines rather than the green/red summary — a system can be "Vulnerable" for MDS variants that its threat model does not care about (same-socket attackers) while being fully covered for the ones it does.

## A Worked Simulation (Educational)

The demo below is an **educational simulation** — an abstract, cycle-quantized model of a small out-of-order core, not a real microarchitecture and not a working exploit. It models the three ingredients directly: a poisoned BTB entry opens a wrong-path window; a gadget ingests an out-of-bounds secret byte and warms the covert line `probe[v]`; the squash rolls back architectural state but not the cache; a flush+reload scan recovers `v` by latency argmin. A second run hardens the gadget with the `array_index_nospec` mask and shows the leak collapse into a constant line.

```python
# Educational simulation of transient execution + Flush+Reload disclosure.
# Abstract, cycle-quantized model of a tiny out-of-order core: wrong-path
# instructions run inside the branch-resolution window, architectural state
# is squashed at resolve, but cache lines warmed on the wrong path stay hot.
# NOT a real microarchitecture; cycle numbers are illustrative, not measured.
LINE = 256                 # covert channel: one cache line per candidate byte
HIT, MISS = 5, 50          # reload latency model (cycles): hit vs miss
PUBLIC_SIZE = 16
SECRET = b"SPE"
DATA = bytearray(b".\x90" * (PUBLIC_SIZE + 256))   # public prefix + filler
DATA[100:100 + len(SECRET)] = SECRET               # secret lives out of bounds

def transient_round(byte_off, harden):
    """Poison BTB -> transient gadget run -> squash. Returns (events, hot val)."""
    idx = 100 + byte_off                       # attacker-supplied OOB index
    # array_index_mask_nospec (linux/nospec.h): all-ones iff idx < size else 0
    mask = 0xFF if idx < PUBLIC_SIZE else 0x00
    tidx = (idx & mask) if harden else idx     # harden = gadget masks its index
    val = DATA[tidx]
    ev = [(1,  "FETCH pc=0x1000 guard       BTB poisoned -> gadget 0x2000"),
          (2,  "FETCH pc=0x2000 gadget      transient window opens"),
          (3,  "ISSUE load data[%d]" % tidx),
          (6,  "RDY   value = 0x%02x" % val),
          (7,  "ISSUE load probe[0x%02x]    covert line = value" % val),
          (9,  "RDY   covert line 0x%02x cached" % val),
          (10, "RESOLVE guard: idx=%d >= size=%d -> wrong path" % (idx, PUBLIC_SIZE)),
          (10, "SQUASH 5 transient instrs   (arch state untouched)")]
    return ev, val                             # wrong-path footprint: line val

def flush_reload(val):
    """Attacker scans all 256 candidate lines by latency, takes the argmin."""
    lat = sorted((HIT if c == val else MISS, c) for c in range(LINE))
    (t1, c1), (t2, _) = lat[0], lat[1]
    return c1, t1, t2

print("=== transient-execution simulator (abstract educational model) ===")
print()
print("Run 1: branch-target poisoning, gadget WITHOUT index masking")
print("ground-truth secret bytes: %s  ('%s')" %
      (" ".join("%02x" % b for b in SECRET), SECRET.decode()))
print()
rec1 = []
for i in range(len(SECRET)):
    ev, val = transient_round(i, harden=False)
    c1, t1, t2 = flush_reload(val)
    rec1.append(c1)
    if i == 0:
        print("byte 0 event trace (cycles):")
        for cyc, what in ev:
            print("  c%2d  %s" % (cyc, what))
        print("  c%2d  cache: line 0x%02x stays HOT (microstate outlives squash)"
              % (10, val))
    print("byte %d: argmin line 0x%02x in %d cyc (runner-up %d cyc) -> '%s' %s"
          % (i, c1, t1, t2, chr(c1),
             "MATCH" if c1 == SECRET[i] else "no-match"))
r1 = "".join(chr(c) for c in rec1)
print('recovered "%s" == ground truth "%s": %s   (3/3 bytes in 3 rounds)'
      % (r1, SECRET.decode(), r1 == SECRET.decode()))
print()
print("Run 2: same attack, gadget hardened with array-index masking (nospec)")
rec2 = []
for i in range(len(SECRET)):
    ev, val = transient_round(i, harden=True)
    c1, t1, t2 = flush_reload(val)
    rec2.append(c1)
    print("byte %d: argmin line 0x%02x in %d cyc -> '%s' != '%s'  MISMATCH"
          % (i, c1, t1, chr(c1), chr(SECRET[i])))
r2 = "".join(chr(c) for c in rec2)
print('recovered "%s" == ground truth "%s": %s'
      % (r2, SECRET.decode(), r2 == SECRET.decode()))
print("covert line 0x%02x (public element 0) is constant -> leaks zero secret bits"
      % rec2[0])
```

```
=== transient-execution simulator (abstract educational model) ===

Run 1: branch-target poisoning, gadget WITHOUT index masking
ground-truth secret bytes: 53 50 45  ('SPE')

byte 0 event trace (cycles):
  c 1  FETCH pc=0x1000 guard       BTB poisoned -> gadget 0x2000
  c 2  FETCH pc=0x2000 gadget      transient window opens
  c 3  ISSUE load data[100]
  c 6  RDY   value = 0x53
  c 7  ISSUE load probe[0x53]    covert line = value
  c 9  RDY   covert line 0x53 cached
  c10  RESOLVE guard: idx=100 >= size=16 -> wrong path
  c10  SQUASH 5 transient instrs   (arch state untouched)
  c10  cache: line 0x53 stays HOT (microstate outlives squash)
byte 0: argmin line 0x53 in 5 cyc (runner-up 50 cyc) -> 'S' MATCH
byte 1: argmin line 0x50 in 5 cyc (runner-up 50 cyc) -> 'P' MATCH
byte 2: argmin line 0x45 in 5 cyc (runner-up 50 cyc) -> 'E' MATCH
recovered "SPE" == ground truth "SPE": True   (3/3 bytes in 3 rounds)

Run 2: same attack, gadget hardened with array-index masking (nospec)
byte 0: argmin line 0x2e in 5 cyc -> '.' != 'S'  MISMATCH
byte 1: argmin line 0x2e in 5 cyc -> '.' != 'P'  MISMATCH
byte 2: argmin line 0x2e in 5 cyc -> '.' != 'E'  MISMATCH
recovered "..." == ground truth "SPE": False
covert line 0x2e (public element 0) is constant -> leaks zero secret bits
```

The leak is 3/3 bytes with no architectural trace; the masked run recovers only the constant public element 0 on every round, which is the signature defenders actually look for — a probe result that never varies with the input.

## Interview Questions

1. **Why can't the squash (rollback) undo a transient-execution leak?** Rollback restores *architectural* state — registers, flags, PC — because those are what the ISA promises. Cache lines, store/fill buffers, and predictor state are microarchitectural and are deliberately *not* rolled back (performance); they are shared, timing-visible, and survive into the attacker's slice of time. Every mitigation strategy in the tables above works by attacking one ingredient: shrink the window (eIBRS, SSBD), empty the state (VERW, KPTI, RSB stuffing), or break the channel (masking so no secret-bearing line is ever warmed).

2. **Retpoline was the 2018 fix for Spectre v2. Why was it not the end of the story?** It protects only the resource it rewrites — indirect branches. Retbleed showed `ret` itself could be made to mispredict via RSB underfill and BPB aliasing, so retpoline-converted code on AMD Zen walked straight into the poisoned return path (the kernel then needed RSB stuffing and safe-RET; see [Retbleed](../../linux/debugging/retbleed.md)). And Skylake's shallow RSB meant a stuffed RSB underflowed into the BTB anyway, which is why the kernel grew call-depth tracking (`CONFIG_MITIGATION_CALL_DEPTH_TRACKING`) rather than trusting the thunk alone.

3. **Why does Spectre v4 get a per-process `prctl` while Meltdown got a global page-table split?** SSBD's mitigation cost lands on every speculative window of every thread, and only some processes (seccomp sandboxes, JS interpreters) face an attacker who can exploit v4 — so the kernel exposes `PR_SET_SPECULATION_CTRL` with `PR_SPEC_STORE_BYPASS`, and `PR_SPEC_PRCTL` reports that per-task control is available; the sandbox toggles it around untrusted code. Meltdown's exposure was every kernel page mapped in user mode, a single global fact, so a one-time global restructure (KPTI) was the cheaper, safer point in the design space — see [Page Table Isolation](../../linux/performance/page-table-isolation.md).

4. **LVI is described as "unmitigable" for enclaves. What makes it categorically worse than MDS?** MDS leaks whatever the buffer happens to hold — the enclave only has to keep secrets out of shared buffers. LVI *injects*: a stale buffer value becomes the *result* of an enclave load, so the enclave itself, running in constant-time style, does the attacker's gadget work for it and uses the injected value to build a covert channel. Clearing buffers (VERW) helps, but the enclave must additionally re-verify every load with CFI and LFENCE discipline — the compiler-flag path (`-mlvi-cfi`) discussed in [Intel SGX](../../cryptography/intel-sgx.md), where Foreshadow/LVI/SGAxe collectively reset SGX's security story.

## Related Pages

- [Retbleed](../../linux/debugging/retbleed.md) — the return-predictor leak and its Linux mitigations in depth
- [Page Table Isolation](../../linux/performance/page-table-isolation.md) — KPTI/KAISER mechanics and overhead
- [Intel SGX](../../cryptography/intel-sgx.md) — enclave-side impact: Foreshadow, LVI, SGAxe
- [ASLR](../../linux/kernel/memory/aslr.md) — why predictor leaks erode KASLR entropy
- [Kernel Hardening](../../linux/security/hardening.md) — sysfs vulnerability reporting and hardening checklist
- [Microarchitectural Attacks](microarch-attacks.md) — the wide survey (RowHammer, TEEs)
- [Flush+Reload](flush-reload.md) and [Prime+Probe](prime-probe.md) — the disclosure oracles
- [Side-Channel Resistant Cryptography](side-channel-resistant.md) — constant-time discipline

## References

1. Spectre official disclosure site — CVE assignments (CVE-2017-5753, CVE-2017-5715): https://spectreattack.com/
2. Meltdown official disclosure site (CVE-2017-5754): https://meltdownattack.com/
3. Kocher, Horn, Fogh, Genkin, Gruss, Haas, Hamburg, Lipp, Mangard, Prescher, Schwarz, Yarom, "Spectre Attacks: Exploiting Speculative Execution," IEEE S&P 2019, DOI 10.1109/SP.2019.00002 (verified via Crossref): https://doi.org/10.1109/SP.2019.00002
4. Lipp et al., "Meltdown: Reading Kernel Memory from User Space," USENIX Security 2018: https://www.usenix.org/conference/usenixsecurity18/presentation/lipp
5. Linux kernel Documentation, hw-vuln/spectre (CVE-2017-5753/5715, CVE-2019-1125; sysfs strings): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/spectre.rst
6. Linux kernel Documentation, hw-vuln/mds (CVE-2018-12126/12127/12130, CVE-2019-11091): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/mds.rst
7. Linux kernel Documentation, hw-vuln/l1tf (CVE-2018-3615/3620/3646): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/l1tf.rst
8. Linux kernel Documentation, hw-vuln/tsx_async_abort (CVE-2019-11135): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/tsx_async_abort.rst
9. Linux kernel Documentation, hw-vuln/srso (CVE-2023-20569): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/hw-vuln/srso.rst
10. Linux kernel Documentation, userspace-api/spec_ctrl (PR_SET_SPECULATION_CTRL, PR_SPEC_STORE_BYPASS, PR_SPEC_PRCTL): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/userspace-api/spec_ctrl.rst
11. Linux kernel ABI docs, sysfs-devices-system-cpu (vulnerabilities file names): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/ABI/testing/sysfs-devices-system-cpu
12. Linux kernel drivers/base/cpu.c (sysfs attr table; `spec_rstack_overflow` naming): https://raw.githubusercontent.com/torvalds/linux/master/drivers/base/cpu.c
13. Linux kernel Documentation, admin-guide/kernel-parameters (spectre_v2=, spectre_bhi=, mds=, l1tf=, spec_store_bypass_disable=): https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/kernel-parameters.txt
14. Linux kernel include/linux/nospec.h (`array_index_nospec`, `array_index_mask_nospec`): https://raw.githubusercontent.com/torvalds/linux/master/include/linux/nospec.h
15. Linux kernel arch/x86/include/asm/nospec-branch.h (RSB_CLEAR_LOOPS=32, call-depth tracking): https://raw.githubusercontent.com/torvalds/linux/master/arch/x86/include/asm/nospec-branch.h
16. Linux kernel tools/objtool documentation (retpoline/return-thunk/SLS validation): https://raw.githubusercontent.com/torvalds/linux/master/tools/objtool/Documentation/objtool.txt
17. Retbleed project page, ETH Zurich (CVE-2022-29900, CVE-2022-29901): https://comsec.ethz.ch/research/microarch/retbleed/
18. LVI project page (CVE-2020-0551, Intel INTEL-SA-00334): https://lviattack.eu/
19. Google, "Retpoline: a software construct for preventing branch-target-injection": https://support.google.com/faqs/answer/7625886
