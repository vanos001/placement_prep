# vDSO and vsyscall: Syscall-Free Fast Paths

Every `clock_gettime()` in a hot loop used to cost a full mode switch: user to
kernel, register save, the actual work, kernel back to user. On an x86-64 box
before mitigations that round trip was a few hundred cycles; with KPTI-style
page-table isolation and retpolines it can be several times worse. The kernel's
answer is to move the *reading* part of timekeeping into user space: a small
shared library - the vDSO - mapped by the kernel itself, which resolves
timestamps with no trap at all in the common case. This page covers how the
vDSO works mechanically, when it falls back to real syscalls, and why its
predecessor, the vsyscall page, became a hardening liability.

Related pages: [Fast I/O](../../advanced/fast-io.md) covers the broader
syscall-bypass landscape (io_uring, batching); [Page-Table Isolation](
../../performance/page-table-isolation.md) explains the mitigation that made
raw syscalls expensive enough for the vDSO to matter this much; the syscall
entry surface itself is described in [syscalls](../../../sysprog/syscalls.md).

## What the vDSO actually is

The vDSO ("virtual dynamic shared object") is an ELF shared object that the
kernel builds at boot and maps into every process at a randomized address. It
is not a file on disk. The dynamic linker discovers it through the auxiliary
vector entry `AT_SYSINFO_EHDR`, so glibc (or musl, or any runtime) can find it
without hard-coded addresses. The [vdso(7)] man page documents the contract:
the object exports versioned symbols such as
`__vdso_clock_gettime@LINUX_2.6`, and the C library's `clock_gettime()` simply
calls into it instead of issuing `syscall`.

Three design points matter for reasoning about performance:

1. **No privilege boundary is crossed on the fast path.** The vDSO reads the
   same seqlock-protected timekeeping data structures the kernel would, but
   they are exported to user space in a page with `vvar`-style mappings
   (architecturally, a `vvar` mapping next to the `vdso` mapping).
2. **It is per-architecture.** x86-64, arm64, powerpc, s390 and others each
   ship their own vDSO with different clocksource read instructions (rdtsc,
   the arm64 counter register, firmware-provided clocks on LPARs).
3. **It can degrade to a real syscall.** If the requested clock is not
   vDSO-capable, or the clocksource is unstable, the vDSO code performs the
   syscall itself; the caller neither knows nor cares.

## The clock_gettime fast path

The vDSO `clock_gettime` implementation is a small state machine over the
`vvar` page:

```text
  caller: clock_gettime(CLOCK_MONOTONIC, &ts)
     |
     v
  [vdso] read tk->seq (odd? retry)          <-- seqlock in the vvar page
     |                                          (writer = kernel timekeeper)
     v
  [vdso] is this vclock usable?             VDSO_CLOCKMODE_*
     |  yes: read TSC (rdtsc ordered)       no : jump to real syscall
     v
  [vdso] cycles = (tsc - base) * mult >> shift     (NTP-corrected mult)
     v
  [vdso] add offset base, normalize ns->s   (mult/shift, no division)
     |
     v
  [vdso] re-check seq (changed? retry)  -> write ts
```

The math is the same cycle-to-nanosecond conversion the kernel's timekeeping
code performs - a multiplicative scaling with `mult`/`shift` plus a base
offset - because user space must reproduce exactly the kernel's answer or the
seqlock comparison fails. `CLOCK_MONOTONIC`, `CLOCK_REALTIME`,
`CLOCK_MONOTONIC_COARSE` and `CLOCK_BOOTTIME` have vDSO paths on x86-64;
`CLOCK_MONOTONIC_RAW` gained one later, and coarse clocks are the cheapest of
all because they skip the TSC read entirely and return the cached coarse
values.

### When the fast path dies

The vDSO entry points check a per-clocksource "vDSO clockmode". If the TSC is
deemed unstable (the watchdog clocksource code detects skew between TSC and a
reference clock), the kernel switches the system clocksource to, say, HPET or
the ACPI PM timer. Those are MMIO devices; reading them from user space is not
possible, so the vDSO marks the clockmode unusable and every call becomes a
genuine syscall. The practical consequence is dramatic - polling loops that
read `CLOCK_MONOTONIC` at megahertz rates slow down by roughly an order of
magnitude when this happens, and the usual symptom in production is a latency
regression after a firmware or virtualization change, not a crash.

Virtualized guests complicate this further: kvmclock, the Hyper-V reference
TSC page and similar paravirt clocksources are designed specifically to be
vDSO-readable (the guest reads a shared memory page instead of trapping to the
hypervisor), so an enlightened guest keeps its fast path where an unenlightened
one would lose it.

## vgetrandom

Until recently the vDSO family was all about time. The 6.11 kernel added
`vgetrandom()` (series covered by LWN in mid-2024), which maps per-task
_random_state_ areas into the vvar space and lets `getrandom()` be served
entirely in user space, reseeding from the kernel RNG only occasionally. The
mechanics differ from clock_gettime because there is shared *mutable* state:
each thread gets a state block, and the vDSO code must be careful about forks
(states are invalidated across `fork()`) and about `madvise(MADV_DONTNEED)`
destroying the shared pages. The takeaway pattern generalizes: a vDSO function
is a user-space routine with kernel-maintained inputs; anything the kernel must
control gets exported as read-mostly shared state.

## The vsyscall page: the predecessor and its failure mode

Before the vDSO there was the vsyscall page - a *fixed* page at
`0xffffffffff600000` containing a handful of stubs (`gettimeofday`,
`time`, `getcpu`). Being fixed-address, it predates widespread ASLR and
remained unrandomized, which turned it into a renaissance for ROP: the page is
mapped into *every* process at a known address with executable semantics, so
an attacker needing a `syscall` gadget - even for a process that never calls
`gettimeofday` - could find one there. Kernel hardening responded in three
modes (selectable with the `vsyscall=` parameter and defaults that have been
tightening across distros):

| mode      | behavior                                            | exploit posture          |
|-----------|-----------------------------------------------------|--------------------------|
| `xonly`   | page is execute-only; traps emulate each call       | gadget bytes unreadable  |
| `emulate` | every access traps; kernel emulates fully            | readable, slow, deprecated |
| `none`    | page absent; legacy binaries receive SIGSEGV         | attack surface removed   |

The [LWN article on vsyscalls and the vDSO] describes the transition and the
emulation breakage for old static binaries. The vsyscall story is the reason
the vDSO exists in its modern randomized form: same goal - avoid the mode
switch - with none of the fixed-address baggage. The x86-64 memory-layout
documentation in the kernel tree records both mappings; [LWN's piece on
implementing virtual system calls] walks through the vDSO-side machinery.

## Measured cost structure

The demo below models the per-call cost of reading a timestamp four ways:
vDSO on the TSC path, vDSO after clocksource fallback, raw syscall with and
without entry mitigations, and legacy vsyscall emulation. The cycle constants
are literature-grounded order-of-magnitude figures (rdtsc on modern cores,
syscall/sysret entry costs, mitigation multipliers), not measurements of this
machine - the point is the *structure* of the comparison, which matches the
5-10x vDSO wins routinely reported in latency-sensitive code.

```python
#!/usr/bin/env python3
"""Deterministic cost model: timestamp reads via vDSO vs raw syscall vs
legacy vsyscall. Constants are literature-grounded cycle counts, converted
at a 3.0 GHz TSC clock. Pure stdlib; no real timing calls."""

GHZ = 3.0
NS_PER_CYCLE = 1000 / (GHZ * 1000)          # 1 cycle at 3 GHz = 0.333 ns

# Model components (cycles, from entry/exit cost studies and TSC docs):
TSC_READ        = 26    # rdtsc / rdtscp on modern x86-64
VDSO_MATH       = 64    # seqlock read + mult/shift + timespec normalization
SYSCALL_PLAIN   = 250   # syscall + sysret entry/exit, no mitigations
SYSCALL_MITIG   = 700   # same path with retpoline + KPTI-style mitigations
FALLBACK_EXTRA  = 200   # clocksource chip access (HPET MMIO / ACPI PM timer)
VSYSCALL_TRAP   = 500   # #PF-style trap into the kernel for vsyscall=emulate


def ns(cycles):
    return cycles * NS_PER_CYCLE


paths = [
    ("vDSO clock_gettime (TSC path)",        TSC_READ + VDSO_MATH),
    ("vDSO fallback (HPET via syscall)",     SYSCALL_MITIG + FALLBACK_EXTRA),
    ("raw clock_gettime, mitigations on",    SYSCALL_MITIG),
    ("raw clock_gettime, no mitigations",    SYSCALL_PLAIN),
    ("legacy vsyscall, emulate mode",        VSYSCALL_TRAP + SYSCALL_PLAIN),
]

print(f"Model: x86-64 at {GHZ:.1f} GHz, per-call cost of a timestamp read")
print(f"{'path':<38} {'cycles':>7} {'ns':>8}")
for name, cyc in paths:
    print(f"{name:<38} {cyc:>7} {ns(cyc):>8.1f}")

print()
print("Aggregate: a poller that reads CLOCK_MONOTONIC 1,000,000 times")
CALLS = 1_000_000
vdso, syscall = ns(TSC_READ + VDSO_MATH), ns(SYSCALL_MITIG)
print(f"  vDSO  : {CALLS:,} calls x {vdso:.1f} ns  = {CALLS*vdso/1e9:6.2f} s wall")
print(f"  syscall: {CALLS:,} calls x {syscall:.1f} ns = {CALLS*syscall/1e9:6.2f} s wall")
print(f"  saved  : {CALLS*(syscall-vdso)/1e9:.2f} s "
      f"({syscall/vdso:.1f}x -- matches the ~5-10x vDSO win reported in practice)")

print()
print("Clocksource instability: what happens when the TSC watchdog barks")
print("  clocksource switch TSC -> HPET moves every read off the TSC path;")
print("  the vDSO entry sees VDSO_CLOCKMODE_NONE and falls back internally")
print(f"  to a real syscall: {ns(TSC_READ + VDSO_MATH):.0f} ns -> "
      f"{ns(SYSCALL_MITIG + FALLBACK_EXTRA):.0f} ns per read "
      f"({(SYSCALL_MITIG+FALLBACK_EXTRA)/(TSC_READ+VDSO_MATH):.1f}x slower)")
print()
print("vsyscall modes (fixed page 0xffffffffff600000, never randomized):")
print(f"  xonly : exec-only page, calls trap+emulate ~ {ns(VSYSCALL_TRAP):.0f} ns + work")
print(f"  emulate: every access traps; reads are served by the kernel")
print(f"  none  : SIGSEGV for anything still calling into the legacy page")
```

```text
Model: x86-64 at 3.0 GHz, per-call cost of a timestamp read
path                                    cycles       ns
vDSO clock_gettime (TSC path)               90     30.0
vDSO fallback (HPET via syscall)           900    300.0
raw clock_gettime, mitigations on          700    233.3
raw clock_gettime, no mitigations          250     83.3
legacy vsyscall, emulate mode              750    250.0

Aggregate: a poller that reads CLOCK_MONOTONIC 1,000,000 times
  vDSO  : 1,000,000 calls x 30.0 ns  =   0.03 s wall
  syscall: 1,000,000 calls x 233.3 ns =   0.23 s wall
  saved  : 0.20 s (7.8x -- matches the ~5-10x vDSO win reported in practice)

Clocksource instability: what happens when the TSC watchdog barks
  clocksource switch TSC -> HPET moves every read off the TSC path;
  the vDSO entry sees VDSO_CLOCKMODE_NONE and falls back internally
  to a real syscall: 30 ns -> 300 ns per read (10.0x slower)

vsyscall modes (fixed page 0xffffffffff600000, never randomized):
  xonly : exec-only page, calls trap+emulate ~ 167 ns + work
  emulate: every access traps; reads are served by the kernel
  none  : SIGSEGV for anything still calling into the legacy page
```

## Operational checklist

- **Latency regression after firmware/BIOS updates** on bare metal, or after a
  hypervisor upgrade in guests: check `sysctl kernel.timekeeping` state via
  `/sys/devices/system/clocksource/clocksource0/` - an `available_clocksource`
  list that no longer has `tsc` in `current_clocksource` means every vDSO
  timestamp is now a syscall. The common root causes are unstable TSC across
  sockets (need `tsc=perfect` evidence or invariant-TSC support) and nested
  virtualization disabling TSC enlightenment.
- **`vsyscall=none` breaking legacy binaries**: static binaries from old
  toolchains call into the legacy page directly. Containers inheriting a
  hardened host kernel will show SIGSEGV in unrelated startup code; the fix is
  a rebuild, not re-enabling vsyscall.
- **Benchmark hygiene**: anything that benchmarks syscall-heavy code should
  assert which path `clock_gettime` is taking (vDSO vs syscall), or the noise
  floor of the timing method can exceed the thing being measured. Coarse
  clocks are a legitimate cheap substitute where nanosecond precision is not
  required.
- **Where this does not apply**: cross-node distributed clocks are a different
  problem entirely - see [hybrid logical clocks](
  ../../../distributed/advanced/hybrid-logical-clocks.md) and [clocks and
  ordering](../../../distributed/advanced/clocks-ordering.md).

## References

1. [vdso(7) - Linux manual page](https://man7.org/linux/man-pages/man7/vdso.7.html)
   - the user-facing contract: AT_SYSINFO_EHDR, symbol versions, portability.
2. [LWN: On vsyscalls and the vDSO](https://lwn.net/Articles/446528/) - the
   vsyscall removal saga, emulation modes, and why the fixed page had to go.
3. [LWN: Implementing virtual system calls](https://lwn.net/Articles/615809/)
   - vDSO construction mechanics, mapping and entry conventions.
4. [LWN: getrandom() in the vDSO](https://lwn.net/Articles/978601/) and
   [the follow-up](https://lwn.net/Articles/983186/) - the vgetrandom design
   and its shared-state complications.
5. [x86-64 memory map documentation](https://docs.kernel.org/arch/x86/x86_64/mm.html)
   - where the vsyscall page and vDSO sit in the canonical address layout.
