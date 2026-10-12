# getcpu(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 309 / 318 / 168 / 345 (cached kernel tables; hub agrees) |
| Since (kernel) | 2.6.19 for x86-64 and i386 (man VERSIONS); hub agrees |
| Man page | man2/getcpu.2 (local cache, dated 2021-03-22) |
| glibc wrapper | getcpu@@GLIBC_2.29 (nm -D on glibc 2.41; man page agrees: wrapper added in glibc 2.29) |
| Aliases covered | none |
| Ledger ID | SC-getcpu |

## Purpose

getcpu() identifies the CPU and NUMA node the calling thread is currently running on, writing small integers to cpu and node (either may be NULL to skip). The result is current only at call time: without a fixed sched_setaffinity(2) mask the scheduler may migrate the thread at any moment, so callers must treat the value as advisory. The intended uses are per-CPU data structures and NUMA placement optimizations.

## Synopsis

```c
#include <sched.h>
int getcpu(unsigned int *cpu, unsigned int *node);
```

## Arguments and behavior

| Argument | Behavior |
|---|---|
| cpu | Receives the CPU id; NULL skips. |
| node | Receives the NUMA node id; NULL skips. |

The raw kernel slot has a third argument, struct getcpu_cache *tcache, a caller-allocated thread-local cache: it was honored before Linux 2.6.24 and is now ignored and must be NULL (the glibc wrapper passes none).

## Return value and errors

Returns 0 on success; -1 with errno: EFAULT (arguments point outside the address space).

## Flags and constants

No flag arguments.

## Security and notes

- The kernel makes a best effort to make the call fast; on some architectures it is implemented in the vDSO, so the "syscall" may not trap at all (sched_getcpu(3) is the usual C library front door).
- Any thread may call it; there is no capability or privilege gate.

## References

- man2/getcpu.2 in the cached man-pages tree (dated 2021-03-22).
- [Syscalls ledger](../ledger.md) row SC-getcpu; kernel tables in source-cache/kernel.
- Siblings: [sched_setaffinity](sched_setaffinity.md); [Domain hub](overview.md).
