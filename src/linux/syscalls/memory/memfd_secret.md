# memfd_secret(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 447 / 447 / - / - |
| Since (kernel) | 5.14 |
| Man page | man2/memfd_secret.2 IS present in the cached tree (source-cache/man-pages-sparse/man2/memfd_secret.2, 157 lines) -- the task brief's "no man page" premise does not match this cache; the config-gate claims below are additionally sourced from mm/secretmem.c and mm/Kconfig as instructed |
| glibc wrapper | none (man page: glibc provides no wrapper; use syscall(2)) |
| Aliases covered | none |
| Ledger ID | SC-memfd_secret |

## Purpose

`memfd_secret()` creates an anonymous RAM-based file whose pages are
removed from the kernel's direct map: the physical memory is mapped only by
the page tables of processes holding the file descriptor, so even the
kernel cannot casually read the region (pointers into it must not be passed
to system calls). It targets secret-key storage with stronger isolation
than ordinary anonymous memory: locked like `mlock(2)` (never swapped),
charged against `RLIMIT_MEMLOCK`, populated lazily on fault.

## Synopsis

```c
#include <sys/syscall.h>   /* SYS_memfd_secret */
#include <unistd.h>
int syscall(SYS_memfd_secret, unsigned int flags);
```

## Arguments and behavior

`flags` may contain `FD_CLOEXEC` (the `O_CLOEXEC` value) to drop the region
on `execve(2)`. The returned descriptor is `O_RDWR` with `O_LARGEFILE`,
refers to a zero-length anonymous file sized afterwards with
`ftruncate(2)`, and follows the usual fork/exec rules. Attach the region
with `mmap(2)` on the descriptor.

## Return value and errors

New file descriptor on success; -1 with `errno` on failure. Errors:
`EINVAL` (unknown flag bits), `EMFILE` (per-process and system-wide fd
limits), `ENOMEM` (insufficient memory), and -- key for the gate story --
`ENOSYS` when the syscall is not implemented on the architecture (man) or
is disabled at runtime (mm/secretmem.c: `if (!secretmem_enable ||
!can_set_direct_map()) return -ENOSYS;`).

## Flags and constants

- `FD_CLOEXEC` / `O_CLOEXEC`: the only documented flag. The kernel defines
  `SECRETMEM_FLAGS_MASK` so local flags cannot collide with the global
  `fcntl.h` `O_CLOEXEC` bit (mm/secretmem.c BUILD_BUG_ON).
- No `SECRETMEM_*` UAPI constants beyond that mask; no glibc header
  exposure (no wrapper, no bits/ definitions -- checked this session).

## Security and notes

- Config gate (`mm/Kconfig`, fetched from torvalds master this session):
  `config SECRETMEM` -- `default y`,
  `bool "Enable memfd_secret() system call" if EXPERT`,
  `depends on ARCH_HAS_SET_DIRECT_MAP`.
- Runtime gate (`mm/secretmem.c`, master): module parameter
  `secretmem.enable` (default 1, mode 0400); ENOSYS when off or when
  `can_set_direct_map()` is false.
- Accounting: pages charged against `RLIMIT_MEMLOCK`
  (`page_limit = rlimit(RLIMIT_MEMLOCK) >> PAGE_SHIFT` in
  `__secretmem_account_pages()`); allocations are `__GFP_ZERO`.
- Numbering: x64/i386 447 (both `common` in the cached x86 tables). The
  generic table gates the row to the special `memfd_secret` ABI
  (CONFIG_SECRETMEM), and the arm32 table carries only the comment
  "# 447 reserved for memfd_secret" -- matching the hub's g64/arm "-".
- Since 5.14 matches worklog Task 1-b (hub value; kernel tag-probed then).
- Region pages are inaccessible to the kernel itself and cannot back
  `read(2)`/`write(2)` targets (man + source intent).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/memfd_secret.2`
  (primary semantic source; contradicts the task-brief "no man page"
  assumption -- noted above).
- Fetched kernel sources (this session, torvalds master):
  `source-cache/fetched/master-mm-secretmem.c` (SYSCALL_DEFINE1,
  secretmem_enable param, RLIMIT_MEMLOCK accounting, ENOSYS gate),
  `source-cache/fetched/master-mm-Kconfig` (SECRETMEM stanza).
- Numbers/Since: hub [overview](overview.md); cached syscall tables.
