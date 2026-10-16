# memory_ordering(2) (SPARC64)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (SPARC64 table only) |
| Since (kernel) | 2.2 (syscalls(2) lists it under the SPARC family; ledger since 2.2) |
| Man page | none (no man2/memory_ordering.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; sibling [kern_features](kern_features.md) |
| Ledger ID | SC-memory_ordering |

## Purpose

memory_ordering() sets the calling thread's SPARC memory-ordering mode: the verified implementation validates `model < 3` and rewrites the TSTATE_MM field of the saved processor state -- `regs->tstate = (regs->tstate & ~TSTATE_MM) | (model << 14);` (arch/sparc/kernel/sys_sparc_64.c:684, torvalds/linux master fetched 2026-10-17). The model selects between Total Store Order (the SPARC default) and the Relaxed Memory Order (RMO) mode introduced with sun4v, letting per-thread code opt into the weaker (faster) ordering with explicit barriers.

## Synopsis

```c
/* SPARC64 syscall */
long syscall(SYS_memory_ordering, unsigned long model);
```

## Arguments and behavior

One argument: the ordering model (0 = TSO, 2 = RMO per the SPARC v9 encoding; anything >= 3 fails). The change applies to the calling thread's TSTATE memory-model bits and takes effect on return to userspace (verified source).

## Return value and errors

0 on success; -EINVAL when model >= 3 (verified source); the call does not exist on non-sparc kernels.

## Flags and constants

TSTATE_MM (the 2-bit memory-model field in the SPARC v9 TSTATE register) is the object being set.

## Security and notes

Source-limited: implementation verified in the fetched source; no man page exists. Interview angle: a syscall that flips a CPU memory model per thread is almost unheard of outside SPARC -- the modern analogue is architecture default plus explicit fence instructions (or the x86 TSO-by-hardware design). Cross-reference: [kern_features](kern_features.md), [membarrier](../memory/membarrier.md), [atomic_barrier](atomic_barrier.md).

## References

- Kernel source: arch/sparc/kernel/sys_sparc_64.c (SYSCALL_DEFINE1(memory_ordering)), torvalds/linux master, fetched 2026-10-17
- Ledger row SC-memory_ordering

