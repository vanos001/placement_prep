# xtensa(2) (Xtensa)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | -- / -- / -- / -- (Xtensa table only) |
| Since (kernel) | 2.6.13 (syscalls(2): "Xtensa only") |
| Man page | none (no man2/xtensa.2 in the man-pages 6.19 HTML set fetched 2026-10-17) -- source-limited by construction |
| glibc wrapper | no wrapper (no such symbol exported by glibc 2.41, nm -D); invoke via syscall(2) |
| Aliases covered | none; table neighbor [spill](spill.md) |
| Ledger ID | SC-xtensa |

## Purpose

xtensa() is the Xtensa platform multiplexer for operations the early cores lacked hardware for -- in the arch's own sources it hosts the emulated atomic operations (cmpxchg-style sequences) and platform-specific services, the same emulated-atomic role [or1k_atomic](or1k_atomic.md) plays on OpenRISC and [arc_usr_cmpxchg](arc_usr_cmpxchg.md) on ARC. The arch's syscall.c also hosts xtensa_shmat/xtensa_fadvise64_64 wrappers (verified present in the fetched arch/xtensa/kernel/syscall.c, fall 2026), while the SYS_xtensa slot itself carries the multiplexed platform operations.

## Synopsis

```c
/* Xtensa syscall */
long syscall(SYS_xtensa, int op, ...);
```

## Arguments and behavior

Operation-dependent: the multiplexer dispatches on `op` (emulated atomics and platform services per the Xtensa ABI notes); the arch file also carries the xtensa_shmat shmem wrapper documented above.

## Return value and errors

Per-operation; a negated error for unknown ops (the entry predates structured error contracts -- the gap this entry names).

## Flags and constants

Operation codes are private to the Xtensa ABI.

## Security and notes

Source-limited: the syscall.c contents were verified (xtensa_shmat/xtensa_fadvise64_64 present); the SYS_xtensa multiplexer's command set was not fully fetched this round. Cross-reference: [spill](spill.md), [or1k_atomic](or1k_atomic.md), [arc_usr_cmpxchg](arc_usr_cmpxchg.md).

## References

- Kernel source: arch/xtensa/kernel/syscall.c (torvalds/linux master, fetched 2026-10-17)
- man-pages syscalls(2) (xtensa(2), 2.6.13, Xtensa only)

