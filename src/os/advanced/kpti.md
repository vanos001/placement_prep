# Kernel Page Table Isolation (KPTI)

> Before January 2018, user and kernel page tables happily coexisted in
> one CR3: the kernel mapped everywhere, and user pages were simply
> marked non-executable/unprivileged. Meltdown showed that on Intel
> CPUs (and some ARM cores) a faulting load's *speculative* successor
> instructions could read kernel memory through those stale mappings
> faster than the permission check could catch up. KPTI removes the
> mappings entirely: user CR3 has almost no kernel in it, so there is
> nothing to leak. This page covers the mechanism, the price, and the
> PCID trick that shrinks the price.

## The Bug in One Paragraph

Meltdown (CVE-2017-5754, Lipp et al., 2018) exploits the window between
a faulting load's *speculative execution* and its *retirement*. On the
affected CPUs the load from a kernel address issued in user mode —
which will ultimately fault — still forwards its fetched value to
subsequent dependent instructions during speculation. The dependency
chain in the classic exploit:

```text
 ; u = *(kernel_addr)        <- faults, but speculates a value
 ; y = page[u >> 12 & 0xff]  <- dependent load, no fault, caches a line
 ; ... fault retires, y never architecturally committed ...
 ; attacker times access to the 4096 probe pages:
 ;   the one page fetched during speculation is fast -> u's byte value
```

The permission violation is only enforced at retirement; the transient
load already updated the cache. Timing the 256 candidate probe pages
then recovers the byte. Three prerequisites: a stale kernel mapping
reachable from user CR3, an out-of-order engine that forwards past the
fault, and a timing oracle (Flush+Reload). KPTI eliminates the first
prerequisite — with kernel pages absent from the user table, the
transient load fetches nothing.

## What KPTI Actually Changes

x86-64 Linux splits the address space into two page tables:

```text
  USER CR3 (installed while running user code)
  +--------------------------------------+
  | user text/data/heap/stack            |
  | cpu_entry_area (entry trampoline)    |  <- the ONLY kernel-side
  | per-CPU TSS/GDT mirrors (read-only)  |     mappings userspace sees
  +--------------------------------------+

  KERNEL CR3 (installed while running kernel code)
  +--------------------------------------+
  | all of USER CR3's user mappings      |  (so copyin/copyout work)
  | full kernel image + modules          |
  | linear map of all RAM                |
  +--------------------------------------+
```

Implications worth being able to state precisely:

- **Every syscall/interrupt/exception and every return** switches CR3.
  Before KPTI these events only switched privilege rings; now they also
  swap the root of the page-table hierarchy, flushing non-global TLB
  entries unless PCID makes the swap cheap (below).
- The kernel is entered via a **trampoline** in `cpu_entry_area`: the
  CPU pushes pt_regs on a stack that must be mapped in user CR3, and
  only *that* minimal region is, so the kernel can boot its own page
  table safely.
- **Global pages (the `PGE` bit)** are the one TLB exception: kernel
  pages marked global survive CR3 switches. Under KPTI, kernel-image
  mappings are *not* global in user CR3 (there are none) and are marked
  non-global in kernel CR3 where possible, so that the switch back to
  user does not leak entries.
- ARM (ARMv8.2+ with PAN) and AMD (SMEP + stronger permission-check
  ordering) were unaffected by Meltdown and ship KPTI off by default;
  the Kconfig `PAGE_TABLE_ISOLATION` defaults on for x86-64 Intel.

## The Price, and PCID

The naive cost of KPTI is a full TLB flush per mode switch. Syscall-
heavy workloads (nginx TLS termination, Redis, DNS) measured 5-30%
regressions in early 2018 depending on CPU and workload; the range was
driven mostly by whether the CPU supported **PCID** (Process-Context
Identifiers).

PCID tags each TLB entry with the 12-bit CR3 value's low bits, so a CR3
switch does not necessarily flush entries — entries of the *other*
PCID survive. The kernel therefore:

1. Assigns distinct PCIDs to the user and kernel address spaces
   (kernel ASI = the user PCID + 1 in current Linux).
2. On switch to kernel, uses `PCPU`-cached target CR3 values; no
   software TLB invalidation is needed at all.
3. Marks kernel-only data non-global so PCID is what isolates it, and
   flushes both PCIDs only on real unmap operations.

On pre-PCID CPUs (older Core 2 era, some Atom), KPTI falls back to
`INVPCID`/full flushes — that is where the 5-30% regressions lived, and
why the same patch that hurt Skylake servers (PCID present) could cost
20%+ on older boxes.

```text
 syscall without KPTI:            syscall with KPTI (PCID):
   sysenter/syscall                 syscall
   ring switch                      ring switch
   (no CR3 change)                  CR3 = kernel_pcid        <- ~cheap w/ PCID
   run kernel                       run kernel
   sysret                           CR3 = user_pcid
                                    sysret
```

## Disable Knobs and Reality Check

- Boot: `nopti` (or `pti=off`) disables; `pti=on` forces.
- Runtime: `/sys/devices/system/cpu/vulnerabilities/meltdown` reports
  the mitigation state. Distro kernels since 4.15 carry it.
- KVM guests: KPTI is also needed *inside* guests on affected CPUs; the
  hypervisor's own EPT is a separate isolation layer but does not stop
  guest-user reading guest-kernel via Meltdown.
- The 2018-era guidance "turn off KPTI on AMD" became moot for most
  users because the mitigation cost shrank with PCID-aware scheduling
  fixes; today the flag matters mostly for benchmarks and embedded.

One subtlety that still matters for interviewers: KPTI mitigates
Meltdown, **not** Spectre. Spectre (CVE-2017-5753/0002) uses *legally
mapped* memory and needs retpoline/IBRS/eIBRS-style branch-target
mitigations instead. A candidate who says "KPTI fixed the CPU security
crisis" is confusing the two.

## Worked Demo: The Flush+Reload Oracle

The demo simulates the oracle itself, not the hardware: a "cache" is a
dict; a speculatively-fetched probe page is recorded; timing is the
dict's hit/miss table. It shows exactly which probe page lights up for
a leaked byte and why the attacker needs only timing, not values.

```python
# Flush+Reload oracle mechanics (deterministic simulation).
# 256 probe "pages"; a cache hit is recorded as latency 1, miss as 100.
# Speculation is modeled as: the dependent load's line gets cached even
# though the faulting load never retires.

cache = set()                       # lines currently in cache

def flush_all():
    cache.clear()

def timed_read(page_idx):
    return 1 if page_idx in cache else 100

def speculative_run(leaked_byte):
    """Emulate: faulting load yields `leaked_byte`; the dependent
    probe-load of page[leaked_byte] caches that line transiently."""
    cache.clear()
    cache.add(leaked_byte)          # transient cache fill
    # fault retires here; architectural state has no register result

# attacker: flush the oracle, run the gadget once, time all 256 pages
flush_all()
speculative_run(leaked_byte=0x41)   # kernel byte value 65 ('A')

hits = [idx for idx in range(256) if timed_read(idx) < 10]
print("fast pages:", hits)
if len(hits) == 1:
    print(f"recovered byte: {hits[0]:#04x} = {chr(hits[0])!r}")
print("latency profile sample:", [timed_read(i) for i in range(0, 4)])
```

Real output:

```text
fast pages: [65]
recovered byte: 0x41 = 'A'
latency profile sample: [100, 100, 100, 100]
```

Exactly one probe page is fast — the one whose index equals the leaked
byte. Under KPTI the speculative dependent load never reaches a valid
PTE, `speculative_run` would cache nothing, and every probe stays at
miss latency. The real attack adds noise (prefetching, interrupts), so
practical exploits repeat and rank the timings — the oracle, though, is
this one.

## Interview Questions

1. Why does KPTI not mitigate Spectre v1/v2? (Spectre abuses mappings
   that are legitimately reachable in the current context; no page
   table split helps. Branch-target control mitigations do.)
2. What is the `cpu_entry_area`, and why must it be mapped in user CR3?
   (The CPU pushes exception frames before any kernel code runs; those
   stacks/TSS/GDT must be reachable under the user CR3 or the CPU
   cannot even enter the kernel to install the kernel CR3.)
3. Why does PCID make KPTI nearly free on Skylake-era servers?
   (Entries from both address spaces coexist, tagged; the CR3 write
   switches tags without flushes.)
4. Why are kernel-image pages in the kernel CR3 marked non-global?
   (So the switch back to user CR3 does not carry kernel TLB entries
   into the user context where a transient access could still see them
   on non-PCID hardware.)
5. You are performance-tuning a syscall-heavy service on an old Intel
   server: what are the first three things to check? (pti state via
   sysfs, PCID support in /proc/cpuinfo, and the actual syscall cost
   delta with `pti=off` in a controlled benchmark.)

## References

- Lipp, M., Schwarz, M., Gruss, D., et al. *Meltdown: Reading Kernel
  Memory from User Space*. USENIX Security '18 (CACM 2020 version:
  https://doi.org/10.1145/3357033, verified via Crossref; original:
  https://meltdownattack.com/meltdown.pdf, probed 200)
- Kocher, P. et al. *Spectre Attacks: Exploiting Speculative
  Execution*. IEEE S&P '18 (arXiv:1801.01207, probed 200).
- Linux kernel docs: `Documentation/x86/pti.rst` —
  https://docs.kernel.org/arch/x86/pti.html (probed 200)
- LWN: Corbet, J. *Kernel page table isolation*. December 2017.
  https://lwn.net/Articles/741878/ (probed 200)
- LWN: Corbet, J. *Kernel page-table isolation merged*. December 2017
  (covers the PCID-based optimization). https://lwn.net/Articles/742404/
  (probed 200)

## Cross-References

- [Kernel page tables and EPT](./virtualization.md) — the normal CR3
  lifecycle KPTI interrupts.
- [TLB shootdowns](./tlb-shootdowns.md) — how PCID changes flush
  semantics in general, not just for KPTI.
- [Exploit mitigations](../../security/advanced/exploit-mitigations.md) —
  the defensive landscape around speculative-execution bugs.
