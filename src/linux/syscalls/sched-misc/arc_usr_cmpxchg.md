# arc_usr_cmpxchg(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (ARC table only) |
| Since (kernel) | 4.9 (syscalls(2): "ARC only") |
| Man page | none (no man2/arc_usr_cmpxchg.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none |
| Ledger ID | SC-arc_usr_cmpxchg |

## Purpose

arc_usr_cmpxchg() performs a userspace compare-and-exchange on ARC cores that lack the LLOCK/SCOND atomic instructions: the kernel performs the compare-and-swap under page-table protection on the caller's behalf (the classic emulated-atomic design). It is the ARC answer to the same problem [or1k_atomic](or1k_atomic.md) solves on OpenRISC and [atomic_cmpxchg_32](atomic_cmpxchg_32.md) solved on m68k.

## Synopsis

```c
/* ARC private syscall */
long syscall(SYS_arc_usr_cmpxchg, unsigned int *uaddr,
             unsigned int expected, unsigned int new);
```

## Arguments and behavior

`uaddr` is the aligned 32-bit word to update, `expected` the value to compare against, `new` the replacement (kernel arch/arc cmpxchg emulation design). Unaligned addresses or non-writable memory fail.

## Return value and errors

Returns the old value at *uaddr on success (the caller compares it against expected); a negated error on the raw path (ENOSYS on cores/kernels with native atomics, EOPNOTSUPP-class rejections on unsupported configurations).

## Flags and constants

None.

## Security and notes

Source-limited: no man page exists; the entry names the gap and describes the emulated-atomic contract from the design's role, cross-checked against the syscalls(2) listing. Interview angle: emulated cmpxchg via syscalls is slow (trap per access) and non-restartable across page eviction -- which is exactly why ARC later grew the LLOCK/SCOND instructions and this call became a fallback. Cross-reference: [or1k_atomic](or1k_atomic.md), [atomic_cmpxchg_32](atomic_cmpxchg_32.md), [futex](../process/futex.md).

## References

- man-pages syscalls(2) (arc_usr_cmpxchg(2), 4.9, ARC only)
- Ledger row SC-arc_usr_cmpxchg

