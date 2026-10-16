# atomic_barrier(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (m68k table only) |
| Since (kernel) | 2.6.34 (syscalls(2): "m68k only") |
| Man page | none (no man2/atomic_barrier.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; sibling [atomic_cmpxchg_32](atomic_cmpxchg_32.md) |
| Ledger ID | SC-atomic_barrier |

## Purpose

atomic_barrier() is the m68k memory-barrier syscall: a userspace-reachable barrier point added in 2.6.34 so that userspace atomic libraries on m68k could order memory accesses without inline instructions. The kernel implementation is disarmingly small -- arch/m68k/kernel/sys_m68k.c defines it with the comment "no code needed for uniprocs" and returns 0 (verified in the fetched source, fall 2026). On uniprocessor m68k Linux the barrier is a no-op; on SMP-capable m68k targets it exists as the hook point for stronger ordering.

## Synopsis

```c
/* m68k private syscall */
long syscall(SYS_atomic_barrier);
```

## Arguments and behavior

No arguments.

## Return value and errors

Always returns 0 (sys_atomic_barrier body, arch/m68k/kernel/sys_m68k.c:580, torvalds/linux master fetched 2026-10-17).

## Flags and constants

None.

## Security and notes

Source-limited: the kernel body was verified (the quote above is from the fetched source); no man page exists. The design point for interviews: barbing through a syscall is expensive (context entry is itself a barrier on many cores) -- which is why this exists as a correctness fallback rather than a performance primitive. Cross-reference: [atomic_cmpxchg_32](atomic_cmpxchg_32.md), [membarrier](../memory/membarrier.md), [futex](../process/futex.md).

## References

- Kernel source: arch/m68k/kernel/sys_m68k.c (sys_atomic_barrier, torvalds/linux master, fetched 2026-10-17)
- man-pages syscalls(2) (atomic_barrier(2), 2.6.34, m68k only)

