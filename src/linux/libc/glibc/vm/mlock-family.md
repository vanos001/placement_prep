# `mlock` / `mlock2` / `mlockall` / `munlock` / `munlockall` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `sys/mman.h` (`mlock`/`munlock`/`mlockall`/`munlockall` unconditional, lines 101-117; `mlock2` in `bits/mman-shared.h` line 59 under `__USE_GNU`, pulled in via `bits/mman.h` -> `bits/mman-linux.h` -> `bits/mman-shared.h`) |
| Standards | POSIX.1b / POSIX.1-2001 (`mlock`, `munlock`, `mlockall`, `munlockall`); Linux (`mlock2`) |
| Exported | `mlock@@GLIBC_2.2.5`, `munlock@@GLIBC_2.2.5`, `mlockall@@GLIBC_2.2.5`, `munlockall@@GLIBC_2.2.5`, `mlock2@@GLIBC_2.27` (nm, host glibc 2.41) |
| Thread-safety | no ATTRIBUTES table in mlock.2; thin syscall wrappers without library state |
| Ledger ID | GLIBC-mlock, GLIBC-mlock2, GLIBC-mlockall, GLIBC-munlock, GLIBC-munlockall |

## Declaration and gates

```c
#include <sys/mman.h>

int mlock(const void *addr, size_t len);            /* sys/mman.h:103 */
int munlock(const void *addr, size_t len);          /* sys/mman.h:107 */
int mlockall(int flags);                            /* sys/mman.h:113 */
int munlockall(void);                               /* sys/mman.h:117 */

#ifdef __USE_GNU
int mlock2(const void *addr, size_t len, unsigned int flags);
#define MLOCK_ONFAULT 1U      /* bits/mman-shared.h:42 */
#endif

#define MCL_CURRENT 1         /* bits/mman-linux.h:129 */
#define MCL_FUTURE  2         /* bits/mman-linux.h:130 */
#define MCL_ONFAULT 4         /* bits/mman-linux.h:132 */
```

## Semantics

`mlock`/`mlock2`/`mlockall` lock pages into RAM so they are never swapped;
`munlock`/`munlockall` unlock (mlock.2). Locking is whole-page: every page
overlapping `[addr, addr+len)` is resident when the call succeeds and stays
until unlocked. `mlock2` adds `MLOCK_ONFAULT`: lock currently resident pages
and mark the range so later faults lock new pages too; flags 0 behaves as
`mlock` (mlock.2; kernel 4.4, glibc 2.27). `mlockall` locks the whole
address space: `MCL_CURRENT` for what is mapped now, `MCL_FUTURE` for
everything mapped later (heap and stack growth included); `MCL_ONFAULT`
(kernel 4.4) must be combined with one of those and defers locking to page
faults instead of pre-faulting. Locks die on `execve` (sys/mman.h comment, lines 110-112).

## Gotchas and portability

- `RLIMIT_MEMLOCK` caps the locked total; `EPERM` (needing `CAP_IPC_LOCK`)
  when unprivileged and over limit (mlock.2 ERRORS/NOTES).
- `MCL_FUTURE` is dangerous: every later `mmap`/stack growth must fit the
  limit or fail.
- Use cases: real-time jitter control and keeping secrets off swap
  (mlock.2 NOTES; suspend-to-disk still dumps RAM).
- Raw syscall page: [mlock](../../../syscalls/memory/mlock.md).
- musl 1.2.5: all five present (`include/sys/mman.h` lines 124-133;
  `src/linux/mlock2.c`).

## Errors

`ENOMEM` (range unmapped, or over `RLIMIT_MEMLOCK` since Linux 2.6.9),
`EPERM` (unprivileged caller needs `CAP_IPC_LOCK`), `EINVAL` (bad
`mlock2` flags) -- full list in mlock.2.

## References

- man2: `mlock.2` (covers mlock2/mlockall/munlock/munlockall), `mlock2.2` (`.so` link)
- headers: `/usr/include/x86_64-linux-gnu/sys/mman.h`, `bits/mman-shared.h`, `bits/mman-linux.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
