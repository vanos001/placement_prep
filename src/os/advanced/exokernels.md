# Exokernels — Application-Level Resource Management

The MIT exokernel project (1994–2000) inverted the standard kernel contract: instead of a kernel that *implements* abstractions (files, sockets, page caches), the kernel only *multiplexes* raw hardware securely, and every abstraction is rebuilt inside an untrusted library operating system (libOS) linked into the application. The dividing line moves from "applications vs. abstractions" to "protection vs. management": the kernel decides *who may touch a physical page*, while the libOS decides *what a page is for*. This page covers the mechanism-level detail — secure bindings, Aegis's CPU/TLB/network multiplexing, XOK's exposed page tables — and the pragmatic reasons the architecture lost to monolithic Linux despite winning most benchmarks.

## The argument in one paragraph

The SOSP'95 paper's opening claim is that hardcoding abstractions (IPC, virtual memory, files) into the kernel is inappropriate for three reasons: it denies applications domain-specific optimizations, it discourages changing implementations of existing abstractions, and it restricts the flexibility of application builders since new abstractions cannot be added without kernel changes. The fix is not a microkernel (which preserves heavyweight *server* implementations) but an exokernel: a minimal kernel that securely exports all hardware through a low-level interface to untrusted libOSes. The measured headline: Aegis primitive operations (exception handling, protected control transfer) ran 10–100x faster than Ultrix on identical DECstation hardware, and application-level VM and IPC primitives were 5–40x faster than their Ultrix kernel counterparts.

## Three principles, three mechanisms

The paper reduces exokernel design to principles about what the kernel must *expose* rather than hide:

| Principle | What it means | Concrete example from the papers |
|-----------|---------------|----------------------------------|
| Expose allocation | libOSes request *specific physical* resources, never "a page" | Requesting physical page N to avoid direct-mapped cache conflicts with the working set |
| Expose names | Physical names + bookkeeping structures are visible | Freelists, disk arm positions, cached TLB entries readable by libOS code |
| Expose revocation | Revocation is a visible, staged protocol | "Please return a page" → deadline ("return one within 50 microseconds") → force |

The unifying mechanism is the **secure binding**: a protection primitive that decouples *authorization* (done once, at bind time) from *use* (checked cheaply, per access). The paper's three implementation techniques, from cheapest to most flexible:

```text
Technique              Bind time                    Access time
---------------------  ---------------------------  -------------------------------
1. Hardware mechanism  TLB entry loaded once        TLB hardware checks each access
2. Software cache      Kernel caches the binding    Compare cached copy (cheap)
3. Downloaded code     App code installed in kernel Filter runs per packet/event
```

Technique 3 is the most underappreciated today: Aegis multiplexed the network using **packet filters with dynamic code generation** — the kernel compiles the libOS's demultiplexing predicate into native code and runs it directly on packet arrival. Protocol semantics stay in the libOS; the kernel only understands the (safe) predicate language that answers "whose packet is this?" The paper frames packet filters as the canonical exokernel secure binding: complex semantics checked once at bind time, trivial ownership checks forever after.

## Aegis internals — the SOSP'95 prototype

Aegis ran on MIPS-based DECstations (DEC2100/3100/5000) and exported exactly five things: the processor, physical memory, the TLB, exceptions, and interrupts (plus the network via the packet-filter system). There are no files, no sockets, no processes — Aegis "has no page tables" of its own and does not map its own data structures, which is precisely why its fault path is short.

**Events.** A processor environment (Aegis's equivalent of a process structure) holds four contexts, one per event kind: exceptions, interrupts, protected control transfers, and address translations. Every resource consumption is attached to an environment, because revocation exceptions must be deliverable to the resource's owner. Timer interrupts deliver *user-specified* interrupt handlers with interrupts re-enabled — the application does its own context switching, which is how ExOS could implement scheduler activations-style user-level threading on top of raw time slices.

**CPU as a linear vector.** Aegis represents the processor as a vector whose elements are time slices, allocated like physical pages. Position encodes ordering and an approximate upper bound on when the slice runs: a scientific libOS allocates contiguous slices (fewer context switches), an interactive one allocates equidistant slices (latency). Fairness is enforced by an excess-time counter: an application that overruns its slice forfeits subsequent ones, and if the counter crosses a threshold Aegis destroys the environment. This is absolute-time accounting — the kernel guarantees *when* a slice runs, the libOS decides *who* runs in it.

**TLB multiplexing.** The Aegis interface includes exactly the primitives needed for the libOS to drive the hardware TLB: insert mapping, delete virtual address, install context identifier, and enable/disable the FPU. Measured exception-dispatch cost, the number that made the paper famous:

```text
Event        DEC2100          DEC3100        DEC5000/125
             Ultrix   Aegis   Ultrix  Aegis  Ultrix  Aegis
overflow     208.0    2.8     151.0   2.1    130.0   1.5     (microseconds)
protection   238.0    3.0     177.0   2.3    154.0   1.5
```

**Why the fault path is short.** Because Aegis maps nothing of itself, a TLB miss handler does not need the careful register-preservation dance Ultrix requires to survive faults through the syscall path. The exception context is a program counter plus a pointer to a physical register-save region — dispatch is two stores and a jump.

## XOK and ExOS — the x86 generation

The second-generation system (SOSP'96/TOCS'97 evaluation) moved to Intel x86: **XOK** is the exokernel, **ExOS** the libOS providing an extensible UNIX personality. Per the project's own summary, gcc, perl, apache, tcsh, and telnet compile and run unmodified on ExOS, at least matching OpenBSD and FreeBSD.

Mechanisms that matter at interview depth:

- **Exposed page tables.** Xok exposes the libOS's page tables to it directly; ExOS scans its own page tables (e.g., to implement fork's copy-on-write) instead of making per-page kernel calls. On the SOSP'95 MIPS design this was an inverted page table (IPT) — one entry per physical frame — with the libOS filling hardware TLB entries directly; the kernel validates ownership at TLB-fill time and caches validated entries (software TLB = cache of secure bindings).
- **Predicates.** Xok's kernel-downloaded functions (the dynamic packet-filter descendant) wake processes on matching network events; predicate evaluation is compiled and runs until the application exits or re-downloads.
- **Cheetah.** A web server that exploits the whole stack: a file system and TCP implementation customized for HTTP traffic (merged file cache, retransmission pool, knowledge-based packet merging). Measured result: a factor-of-eight improvement over FreeBSD-class servers; on the x86 XOK/ExOS stack, Cheetah outperformed NCSA and Harvest by 8x and IIS on Windows NT Enterprise Edition by 3–4x. The SOSP'96 paper's broader finding matters more than the single number: unmodified UNIX applications ran comparably or better on Xok/ExOS than on FreeBSD/OpenBSD — extensibility did not cost the common case.

```text
Traditional kernel                Exokernel
+--------------------------+      +--------------------------+ +--------------------------+
|  File system, sockets,   |      |  libOS (ExOS / Cheetah)  | |  libOS #2 (different     |
|  TCP, VM policy (fixed)  |      |  FS, TCP, VM policy      | |  policies, same kernel)  |
+--------------------------+      +--------------------------+ +--------------------------+
|  Kernel: everything      |      |  Exokernel: secure       |
|  protection + policy     |      |  multiplexing only       |
+--------------------------+      +--------------------------+
              |                                  |  (physical page / TLB / slot grants)
              v                                  v
+--------------------------+      +--------------------------+
|       Hardware           |      |       Hardware           |
+--------------------------+      +--------------------------+
```

## The revocation dialogue and the abort protocol

Revocation is where "protection without management" gets hard, and the papers are explicit about the staged protocol. Stage 1: the kernel asks the libOS to give up a resource; a well-behaved libOS keeps its resources in a quickly-walkable structure (the paper suggests a simple vector of owned pages) so it can pick a victim, write it out, and update its page-table entries that name the relinquished physical page. Stage 2: the request becomes imperative — return a page within a deadline (50 microseconds in the paper's example). Stage 3 (the abort protocol): a recalcitrant libOS has its secure bindings broken *by force*. The kernel never needs to understand file systems or caches to take a page back; it only needs to invalidate the bindings that named that page. The libOS's reward for cooperating is choice: it decides *which* instance of the resource to relinquish (visible revocation), preserving physical-name locality.

## Why it lost to Linux anyway

The architecture never shipped as a mainstream OS, and the SOSP'96 paper's own "lessons" section is the best evidence of why:

1. **User-level page tables are complex.** The paper flags this directly: migrating page-table management into libOS code made ExOS complicated, and the win (kernel-free TLB misses) was increasingly matched by hardware as x86 gained cheaper TLB refill paths. Complexity moved, but did not shrink.
2. **Every application ships its own OS.** Without a standard libOS, "application-level specialization" fragments into N competing libraries. ExOS existed so that *unmodified* UNIX apps would work — which quietly concedes that compatibility, not specialization, is what users buy.
3. **The N-benchmark fallacy.** Cheetah's 8x came from a web server whose authors wrote a file system and TCP for HTTP. The equivalent investment for every major application never materialized, and monolithic kernels absorbed the obvious general-purpose optimizations (zero-copy sendfile, page clustering) that closed most of the gap for everyone else.
4. **Ecosystem gravity.** Drivers, debuggers, and distributors standardized on POSIX kernels. An exokernel distribution must bootstrap all of that per-libOS.
5. **Hardware moved toward the same ends.** AMD-V/VT-x, IOMMUs, and eventually DPDK/SPDK gave applications near-raw resource control *without* abandoning the Linux driver base — achieving the performance goal with different protection machinery.

The honest interview answer: exokernels lost as products but won as ideas — packet filters became BPF/eBPF (the [eBPF deep dive](../../os/kernel-advanced/ebpf-deep.md)), application-level resource management became DPDK/SPDK and io_uring's registered resources ([io_uring internals](../../os/kernel/io-uring.md), [DPDK internals](./dpdk.md)), in-kernel safe-programmable drivers reappeared as XDP ([XDP](../../linux/kernel/networking/xdp.md)), and the libOS concept was reborn as unikernels (see [unikernels](./unikernels.md)). The survey-level comparison in [kernel architectures](./kernel-architectures.md) covers where exokernels sit among monolithic/micro/multikernel designs; here the takeaway is the mechanism inventory: bind-time authorization, visible revocation, and downloaded code.

## Worked model — secure bindings for memory

The demo below is a miniature of the Aegis/XOK memory multiplexing loop: the application writes its own PTEs (kernel not involved), the kernel validates ownership only at TLB-fill (bind) time, stamps validated entries into its cache, detects later application edits by comparing stamps, and runs a revocation with the abort protocol.

```python
# Model of Aegis-style "secure bindings" for virtual memory:
# applications fill their own (inverted) page-table entries; the kernel
# validates + stamps them at bind time, caches stamped entries, and detects
# later modification at TLB-fill time. Includes visible revocation + abort.
ASID_APP = 7

class Exokernel:
    def __init__(self):
        self.frame_owner = {}        # pfn -> asid (kernel-owned frame table)
        self.pte_cache = {}          # vpn -> (pfn, prot, asid, stamp) kernel-stamped copy
        self.stamp = 0               # monotonic stamp, bumped on each validation
        self.stats = {"validations": 0, "stamps": 0, "revalidations": 0,
                      "tlb_fills": 0, "protection_faults": 0, "revocations": 0}

    def grant_frames(self, asid, pfns):
        for pfn in pfns:
            self.frame_owner[pfn] = asid

    # ---- application-side PTE write (kernel not in the loop) ----
    def app_write_pte(self, asid, app_ptes, vpn, pfn, prot):
        app_ptes[vpn] = (pfn, prot)          # app edits its OWN table
        if self.pte_cache.get(vpn, (None,))[0] == pfn:
            del self.pte_cache[vpn]          # stale stamped copy must be dropped

    # ---- kernel validation at TLB-fill (bind) time ----
    def tlb_fill(self, asid, app_ptes, vpn):
        self.stats["tlb_fills"] += 1
        if vpn not in app_ptes:
            return "FAULT: no PTE"
        pfn, prot = app_ptes[vpn]
        cached = self.pte_cache.get(vpn)
        if cached and cached[0] == pfn and cached[1] == prot and cached[2] == asid:
            self.stats["revalidations"] += 1   # unchanged since stamp: no recheck
            return f"TLB <- {vpn:#06x} -> {pfn:#06x} {prot} (cache hit, stamp {cached[3]})"
        self.stats["validations"] += 1
        if self.frame_owner.get(pfn) != asid:
            self.stats["protection_faults"] += 1
            return f"PROTECTION FAULT: {vpn:#06x} -> {pfn:#06x} owned by asid {self.frame_owner.get(pfn)}"
        self.stamp += 1
        self.pte_cache[vpn] = (pfn, prot, asid, self.stamp)
        self.stats["stamps"] += 1
        return f"TLB <- {vpn:#06x} -> {pfn:#06x} {prot} (validated + stamped #{self.stamp})"

    # ---- visible revocation with abort protocol ----
    def revoke(self, asid, app_ptes, pfn, deadline_us=50):
        self.stats["revocations"] += 1
        if self.frame_owner.get(pfn) == asid:
            del self.frame_owner[pfn]
            for vpn, (p, prot) in list(app_ptes.items()):
                if p == pfn:
                    del app_ptes[vpn]           # libOS relocates the page
            for vpn in [v for v, c in self.pte_cache.items() if c[0] == pfn]:
                del self.pte_cache[vpn]
            return f"revoked {pfn:#06x}: libOS relocated mappings (deadline {deadline_us}us met)"
        return f"revoked {pfn:#06x}: nobody held it"

k = Exokernel()
k.grant_frames(ASID_APP, [0x2100, 0x2101, 0x2102])
k.grant_frames(99, [0x3000])                     # another address space owns 0x3000
app = {}                                          # app-visible page table

print("== app fills its own PTEs (kernel not in the loop) ==")
k.app_write_pte(ASID_APP, app, 0x0040, 0x2100, "RW")
k.app_write_pte(ASID_APP, app, 0x0041, 0x2101, "RW")
k.app_write_pte(ASID_APP, app, 0x0042, 0x3000, "RW")   # forged entry -> foreign frame
print("== TLB fills: validate + stamp ==")
print(k.tlb_fill(ASID_APP, app, 0x0040))
print(k.tlb_fill(ASID_APP, app, 0x0041))
print(k.tlb_fill(ASID_APP, app, 0x0040))         # unchanged: software-TLB cache hit
print(k.tlb_fill(ASID_APP, app, 0x0042))         # forged: caught at bind time
print("== app edits a stamped PTE (detection on next fill) ==")
k.app_write_pte(ASID_APP, app, 0x0041, 0x2102, "RO")
print(k.tlb_fill(ASID_APP, app, 0x0041))
print("== revocation: kernel takes 0x2100 back, abort protocol relocates ==")
print(k.revoke(ASID_APP, app, 0x2100))
print(k.tlb_fill(ASID_APP, app, 0x0040))
print("== kernel stats ==", k.stats)
```

Real output:

```text
== app fills its own PTEs (kernel not in the loop) ==
== TLB fills: validate + stamp ==
TLB <- 0x0040 -> 0x2100 RW (validated + stamped #1)
TLB <- 0x0041 -> 0x2101 RW (validated + stamped #2)
TLB <- 0x0040 -> 0x2100 RW (cache hit, stamp 1)
PROTECTION FAULT: 0x0042 -> 0x3000 owned by asid 99
== app edits a stamped PTE (detection on next fill) ==
TLB <- 0x0041 -> 0x2102 RO (validated + stamped #3)
== revocation: kernel takes 0x2100 back, abort protocol relocates ==
revoked 0x2100: libOS relocated mappings (deadline 50us met)
FAULT: no PTE
== kernel stats == {'validations': 4, 'stamps': 3, 'revalidations': 1, 'tlb_fills': 6, 'protection_faults': 1, 'revocations': 1}
```

Reading the trace: the forged PTE (`0x0042 -> 0x3000`) is caught without any understanding of *why* the libOS wanted it — the kernel only knows frame ownership. The cache hit on `0x0040` shows why exokernel protection is cheap: after one validation, every subsequent access is a comparison. The edit to `0x0041` invalidates the stamp, forcing revalidation — that is the software-cache technique from the table above.

## Interview questions

1. **"What problem do secure bindings solve?"** They let the kernel protect resources without understanding them: authorization happens once at bind time using primitives the hardware enforces (TLB entries, ownership tags, predicates), so access-time checks are constant-cost comparisons instead of policy evaluations.
2. **"How did Aegis make exception dispatch 10–100x faster than Ultrix?"** It refuses to map its own state and has no page tables, so an exception context is just a PC plus a physical register-save area; there is no fault-through-syscall register dance. Measured dispatch: 1.5–3.0 µs on DECstations vs. 130–238 µs for Ultrix.
3. **"If exokernels benchmark so well, why did they disappear?"** The specialization wins required per-application libOS engineering (Cheetah's 8x needed a custom FS+TCP for HTTP); the compatibility path (ExOS reimplementing UNIX) recreated the generic kernel inside a library; hardware (VT-x/AMD-V, IOMMU) and kernel-bypass frameworks later delivered app-level resource control without leaving the Linux ecosystem.
4. **"Where does Aegis's CPU scheduling let the application win?"** Time slices are a linear vector allocated like pages, so position encodes deadlines: contiguous slices minimize context-switch overhead for batch work, equidistant slices maximize responsiveness — an allocation-time policy decision no monolithic kernel exposes to its applications.

## References

1. D. R. Engler, M. F. Kaashoek, J. O'Toole Jr., "Exokernel: An Operating System Architecture for Application-Level Resource Management," SOSP '95. DOI: [10.1145/224056.224076](https://doi.org/10.1145/224056.224076) (Crossref-verified).
2. M. F. Kaashoek, D. R. Engler, G. R. Ganger, et al., "Application performance and flexibility on exokernel systems," SOSP '96. DOI: [10.1145/268998.266644](https://doi.org/10.1145/268998.266644) (Crossref-verified; XOK/ExOS on x86, Cheetah evaluation).
3. MIT PDOS, "MIT Exokernel Operating System" project page — XOK/ExOS status, unmodified-app compatibility list, Cheetah vs. NCSA/Harvest/IIS numbers: <https://pdos.csail.mit.edu/exo/> (HTTP 200).
4. MIT 6.828 course reading copy of the SOSP '95 paper (PDF): <https://pdos.csail.mit.edu/6.828/2019/readings/engler95exokernel.pdf> (HTTP 200).
5. MIT 6.828 exokernel lecture FAQ (instructor notes on the paper, incl. the inverted-page-table discussion): <https://pdos.csail.mit.edu/6.828/2019/lec/faq-exokernel.txt> (HTTP 200).
