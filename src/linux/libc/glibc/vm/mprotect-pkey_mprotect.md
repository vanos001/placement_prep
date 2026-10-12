# `mprotect` / `pkey_mprotect` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/mman.h` (`mprotect` unconditional, line 81; `pkey_mprotect` in `bits/mman-shared.h` line 82 under `__USE_GNU`, reached via `bits/mman.h` -> `bits/mman-linux.h` -> `bits/mman-shared.h`) |
| Standards | POSIX.1-2001 (`mprotect`); Linux (`pkey_mprotect`) |
| Exported | `mprotect@@GLIBC_2.2.5`, `pkey_mprotect@@GLIBC_2.27` (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES table in mprotect.2; thin syscall wrappers without library state |
| Ledger ID | GLIBC-mprotect, GLIBC-pkey_mprotect |

## Declaration and gates

```c
#include <sys/mman.h>

int mprotect(void *addr, size_t len, int prot);   /* sys/mman.h:81 */

#define _GNU_SOURCE
#include <sys/mman.h>

int pkey_mprotect(void *addr, size_t len, int prot, int pkey);
#define PROT_NONE  0x0   /* bits/mman-linux.h:35 */
#define PROT_READ  0x1   /* bits/mman-linux.h:32 */
#define PROT_WRITE 0x2   /* bits/mman-linux.h:33 */
#define PROT_EXEC  0x4   /* bits/mman-linux.h:34 */
#define PROT_GROWSDOWN 0x01000000  /* bits/mman-linux.h:36 */
#define PROT_GROWSUP   0x02000000  /* bits/mman-linux.h:38 */
```

## Semantics

`mprotect` changes the access protection of the pages covering
`[addr, addr+len-1)`; `addr` must be page-aligned (mprotect.2). `prot` is
`PROT_NONE` or a mix of `PROT_READ`/`PROT_WRITE`/`PROT_EXEC`, plus the
Linux-only `PROT_GROWSDOWN`/`PROT_GROWSUP` which extend the change across
a downward/upward-growing mapping (stack). An access that violates the
protection raises `SIGSEGV` for the process. The kernel may not support
`PROT_EXEC` without `PROT_READ` on all architectures (header comment,
bits/mman-linux.h lines 28-30).

`pkey_mprotect` (kernel 4.9, glibc 2.27) does the same but additionally
assigns the protection key `pkey` -- obtained from `pkey_alloc` -- to the
range; the key's per-thread access rights (`PKEY_DISABLE_ACCESS` /
`PKEY_DISABLE_WRITE`) are then enforced by the CPU on top of `prot`
(mprotect.2; see the pkey family page). The raw syscall page is
[mprotect](../../../syscalls/memory/mprotect.md).

## Gotchas and portability

- `mprotect` is the portable spelling (POSIX); `pkey_mprotect` is
  Linux-only and hardware-dependent (x86 PKU and a few others).
- `mprotect` on a range obtained from `mmap` of a read-only file cannot
  grant `PROT_WRITE` (`EACCES`); W^X policies may also forbid `PROT_EXEC`.
- musl 1.2.5: `mprotect` present (`include/sys/mman.h` line 119); no
  `pkey_mprotect` declaration or symbols anywhere in the tree.

## Errors

`EACCES` (protection not grantable for that mapping), `EFAULT` (range not
mapped / kernel can't access), `EINVAL` (unaligned `addr` or bad `prot`;
for `pkey_mprotect`, an unallocated pkey), `ENOMEM` (range not covering
mapped pages in the caller's space) (mprotect.2 ERRORS).

## References

- man2: `mprotect.2` (covers `pkey_mprotect`; `pkey_mprotect.2` is a `.so` link)
- glibc manual: `memory.texi` (aligned/locking context), pkeys coverage in pkey_alloc.2
- headers: `/usr/include/x86_64-linux-gnu/sys/mman.h`, `bits/mman-shared.h`, `bits/mman-linux.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
