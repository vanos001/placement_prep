# or1k_atomic(2) (OpenRISC)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (OpenRISC table only) |
| Since (kernel) | 3.1 (syscalls(2): "OpenRISC 1000 only") |
| Man page | none (no man2/or1k_atomic.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-or1k_atomic |

## Purpose

or1k_atomic() provides userspace atomic operations for OpenRISC 1000 cores that lack native atomic instructions: compare-and-swap and exchange implemented by the kernel on the caller's behalf (the same emulated-atomic design as [atomic_cmpxchg_32](atomic_cmpxchg_32.md) on m68k and [arc_usr_cmpxchg](arc_usr_cmpxchg.md) on ARC). The entry point is verified in the OpenRISC entry assembly: `ENTRY(sys_or1k_atomic)` at arch/openrisc/kernel/entry.S:1229 (fetched 2026-10-17).

## Synopsis

```c
/* OpenRISC syscall; operation codes select cmpxchg/xchg */
long syscall(SYS_or1k_atomic, int op, unsigned long *uaddr,
             unsigned long oldval, unsigned long newval);
```

## Arguments and behavior

`op` selects the operation; `uaddr` the aligned 32-bit target; `oldval`/`newval` the compare-and-exchange operands (kernel OpenRISC atomic emulation).

## Return value and errors

Returns the previous value at *uaddr (the caller judges swap success); a negated error for faults or unsupported operation codes.

## Flags and constants

Operation-code constants are private to the OpenRISC ABI (entry.S dispatch).

## Security and notes

Source-limited: the entry point was verified in the fetched assembly; no man page exists. Interview angle: OpenRISC later gained hardware atomics, demoting this syscall to fallback -- the same arc ARC followed with LLOCK/SCOND. Cross-reference: [atomic_cmpxchg_32](atomic_cmpxchg_32.md), [arc_usr_cmpxchg](arc_usr_cmpxchg.md), [futex](../process/futex.md).

## References

- Kernel source: arch/openrisc/kernel/entry.S (ENTRY(sys_or1k_atomic)), torvalds/linux master, fetched 2026-10-17
- man-pages syscalls(2) (or1k_atomic(2), 3.1, OpenRISC only)

