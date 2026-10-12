# munmap(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 11 / 91 / 215 / 91 |
| Since (kernel) | 1.0 |
| Man page | man2/munmap.2 is a roff `.so` alias of man2/mmap.2 (cached); the munmap material lives in mmap.2's `munmap()` section |
| glibc wrapper | yes, in libc (`sys/mman.h`); no feature-test restrictions |
| Aliases covered | none (split from [mmap](mmap.md), which the hub lists under one family row) |
| Ledger ID | SC-munmap |

## Purpose

`munmap()` deletes the mappings for the specified address range; further
references inside the range generate invalid memory references (`SIGSEGV`).
It is the teardown half of the `mmap()` pair, used by allocators, loaders,
and `mremap()` users. The whole address space is unmapped automatically at
process termination, while closing the underlying file descriptor does
**not** unmap anything.

## Synopsis

```c
#include <sys/mman.h>
int munmap(void *addr, size_t length);
```

## Arguments and behavior

`addr` must be a multiple of the page size; `length` need not be. All pages
containing part of `[addr, addr+length)` are unmapped and afterwards raise
`SIGSEGV` on access. It is **not** an error if the range contains no mapped
pages. For hugetlb mappings both `addr` and `length` must be multiples of
the huge page size (man mmap.2, huge-page section). Unmapping the middle of
an existing mapping splits it in two, which counts against the process's
maximum number of mappings.

## Return value and errors

0 on success; -1 with `errno` on failure, "probably to EINVAL" per the man
page. Documented conditions: `EINVAL` (addr not page-aligned), `ENOMEM`
(splitting a mapping would exceed the maximum number of mappings).

## Flags and constants

None; exactly two arguments, no flags.

## Security and notes

- Unmapping removes any memory locks on the range (man mlock.2 NOTES).
- Without `msync(MS_SYNC)` first, dirty `MAP_SHARED` file pages are not
  guaranteed to reach the file (man msync.2 opening paragraph).
- A `munmap()` in the observed process emits `UFFD_EVENT_UNMAP` to a
  registered non-cooperative `userfaultfd(2)` monitor (since 4.11).
- Related: [mmap](mmap.md) (creation), [mremap](mremap.md) (resize/move),
  [brk](brk.md) (the heap break is a separate mechanism; munmap does not
  move it).

## References

- Cached man pages: `source-cache/man-pages-sparse/man2/munmap.2`
  (verified one-line `.so man2/mmap.2` alias) and `man2/mmap.2`
  (`munmap()` section, ERRORS, huge-page notes).
- Numbers: cached `syscall_64.tbl` (11), `syscall_32.tbl` (91),
  `syscall_generic.tbl` (215), `syscall_arm.tbl` (91); hub
  [overview](overview.md).
