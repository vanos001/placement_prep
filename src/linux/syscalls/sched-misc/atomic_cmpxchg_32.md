# atomic_cmpxchg_32(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (m68k table only) |
| Since (kernel) | 2.6.34 (syscalls(2): "m68k only") |
| Man page | none (no man2/atomic_cmpxchg_32.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; sibling [atomic_barrier](atomic_barrier.md) |
| Ledger ID | SC-atomic_cmpxchg_32 |

## Purpose

atomic_cmpxchg_32() emulates a 32-bit compare-and-exchange for m68k cores without the CAS instruction (the 68020+ CAS is unavailable on the plain 68000 class): the kernel walks the caller's page tables, locks the page in place, and performs the compare-and-swap on the kernel side -- the implementation comment says it was "borrowed from ARM's implementation" (verified in arch/m68k/kernel/sys_m68k.c, fall 2026).

## Synopsis

```c
/* m68k private syscall; raw args land in A0/D2/D1 */
long syscall(SYS_atomic_cmpxchg_32, unsigned long *mem,
             unsigned long oldval, unsigned long newval);
```

## Arguments and behavior

`mem` is the 32-bit word to update, `oldval` the expected value, `newval` the replacement; the C wrapper signature in the source reads sys_atomic_cmpxchg_32(newval, oldval, d3, d4, d5, mem) -- the d3/d4/d5 slots exist to match the raw register convention (arch/m68k/kernel/sys_m68k.c:463, fetched 2026-10-17). The implementation loops: locate the PTE for mem, pin the page, compare and swap if equal.

## Return value and errors

Returns the old value found at *mem (caller compares against oldval to know whether the swap happened); a negated error on the raw path for faults on the target page.

## Flags and constants

None.

## Security and notes

Source-limited: the implementation was verified in the fetched source (including the borrowed-from-ARM comment); no man page exists. Performance and interruption characteristics are the interview angle: every failed CAS is a full syscall, and the page-pinning loop is why the ARM implementation it borrows from was itself replaced by native ll/sc pairs. Cross-reference: [atomic_barrier](atomic_barrier.md), [or1k_atomic](or1k_atomic.md), [futex](../process/futex.md).

## References

- Kernel source: arch/m68k/kernel/sys_m68k.c (sys_atomic_cmpxchg_32, torvalds/linux master, fetched 2026-10-17)
- man-pages syscalls(2) (atomic_cmpxchg_32(2), 2.6.34, m68k only)

