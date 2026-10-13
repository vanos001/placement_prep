# `mseal` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | none on this host -- no `mseal` declaration exists in glibc 2.41 headers (`sys/mman.h`, `bits/mman-shared.h` searched); glibc's wrapper ships only in the development tree (NEWS, Version 2.43 section) |
| Standards | Linux-specific (kernel 6.10); glibc wrapper: development tree only on this snapshot |
| Exported | none -- `nm -D libc.so.6` lists no `mseal` symbol on host glibc 2.41; `SYS_mseal` exists in `bits/syscall.h` line 1063 |
| Thread-safety | n/a on this host (no wrapper); the raw syscall is stateless |
| Ledger ID | GLIBC-mseal |

## Declaration and gates

```c
/* no header declaration on host glibc 2.41; until the wrapper ships:
   raw syscall (number 462 on x86-64, arm64, i386 per the syscall page) */
#define _GNU_SOURCE
#include <sys/syscall.h>   /* SYS_mseal, bits/syscall.h:1063 */
#include <unistd.h>

int rc = syscall(SYS_mseal, addr, len, 0UL);
/* future glibc (NEWS "Version 2.43"): int mseal(void *addr, size_t len,
   unsigned long flags); */
```

Host status verified: `/usr/include/x86_64-linux-gnu/sys/mman.h` and its
`bits/` includes declare no `mseal`; `nm -D libc.so.6` has no `mseal`.

## Semantics

No wrapper on this host; the kernel behavior is (raw syscall -- the
future glibc wrapper follows the same contract):

`mseal` seals a virtual-memory range: afterwards the kernel rejects with
`EPERM` the mm syscalls that would change the range's attributes or
layout -- `munmap`, `mprotect`/`pkey_mprotect`, `mremap`, attribute-changing
`mmap`, and the destructive `madvise` behaviors (`MADV_DONTNEED`,
`MADV_FREE`, `MADV_DONTNEED_LOCKED`, `MADV_WIPEONFORK`, `MADV_DONTFORK`)
(kernel `mm/mseal.c`, `Documentation/userspace-api/mseal.rst`; full write-up
in [mseal(2)](../../../syscalls/memory/mseal.md), which is source-sourced
because man-pages has no mseal.2). `flags` must be 0; the start address
must be page-aligned inside allocated VMAs with no gap. Sealing is
idempotent and there is no unseal: the range stays sealed until the
process exits or `execve`. The goal is exploit mitigation -- a stray
pointer write can no longer make `.text` writable or remap trusted memory.

## Gotchas and portability

- Kernel 6.10+ and 64-bit kernels only; `ENOSYS` elsewhere.
- glibc 2.41 (this host): no wrapper -- plan for `syscall(2)` or guard a
  weak prototype; the development NEWS lists mseal under Version 2.43.
- musl 1.2.5: no declaration in `include/sys/mman.h`, nothing in `src/`.
- Cross-ref: [memory syscalls overview](../../../syscalls/memory/overview.md).

## Errors

`EINVAL` (flags nonzero, unaligned start, overflow), `ENOMEM` (start/end
unallocated or a gap in the range), `ENOSYS` (kernel without mseal,
32-bit kernels); later modifying calls on the sealed range fail with
`EPERM` (mseal.rst via the syscall page).

## References

- glibc source snapshot: `NEWS`, Version 2.43 section ("On Linux, the
  mseal function has been added...")
- syscall page: [mseal](../../../syscalls/memory/mseal.md) (mm/mseal.c + mseal.rst)
- headers: `/usr/include/x86_64-linux-gnu/bits/syscall.h` (line 1063)
- symbols: `nm -D --with-symbol-versions libc.so.6`
