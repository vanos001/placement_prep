# madvise(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 28 / 219 / 233 / 220 |
| Since (kernel) | 2.4 |
| Man page | man2/madvise.2 (cached, dated 2021-03-22; documents advice up to MADV_PAGEOUT / Linux 5.4) |
| glibc wrapper | yes, in libc; _DEFAULT_SOURCE since glibc 2.19 (_BSD_SOURCE before) |
| Aliases covered | none (process_madvise is a separate syscall, not in this domain's hub) |
| Ledger ID | SC-madvise |

## Purpose

`madvise()` gives the kernel advice about an address range so it can choose
better read-ahead, caching, reclaim, and huge-page behavior. Most values
are performance hints, but several Linux extensions change semantics
(`MADV_DONTNEED`, `MADV_FREE`, `MADV_REMOVE`, `MADV_DONTFORK`,
`MADV_WIPEONFORK`). POSIX does not specify `madvise()`; it specifies
`posix_madvise(3)` with the `POSIX_MADV_*` subset instead.

## Synopsis

```c
#include <sys/mman.h>
int madvise(void *addr, size_t length, int advice);
```

## Arguments and behavior

`addr` must be page-aligned; Linux allows `length` = 0. Unmapped parts of
the range are ignored by the Linux implementation, but the call still
reports `ENOMEM`. `MADV_DONTNEED` discards the range's contents (later
accesses repopulate from the file for shared mappings, or zero-fill for
private anonymous); `MADV_FREE` (4.5) lazily frees private anonymous pages
unless rewritten first.

## Return value and errors

0 on success; -1 with `errno` on failure. Documented errors: `EACCES`
(MADV_REMOVE on a non-shared-writable range), `EAGAIN`, `EBADF` (mapping is
not a file), `EINVAL` (bad addr/length; unknown advice; DONTNEED/REMOVE
over locked, hugetlb, or VM_PFNMAP pages; MERGEABLE/UNMERGEABLE without
CONFIG_KSM; FREE/WIPEONFORK on non-private-anonymous ranges), `EIO`
(WILLNEED would exceed the RSS limit), `ENOMEM` (unmapped range; WILLNEED
paging-in failed), `EPERM` (MADV_HWPOISON without CAP_SYS_ADMIN).

## Flags and constants

Values verified in installed glibc headers (`bits/mman-linux.h`; the whole
block is guarded by `#ifdef __USE_MISC`):

| Advice | Value | Since | Note / config gate |
|---|---|---|---|
| MADV_NORMAL | 0 | 2.4 | default treatment |
| MADV_RANDOM | 1 | 2.4 | disable readahead |
| MADV_SEQUENTIAL | 2 | 2.4 | aggressive readahead |
| MADV_WILLNEED | 3 | 2.4 | will need soon |
| MADV_DONTNEED | 4 | 2.4 | changes semantics; no locked/hugetlb/PFNMAP |
| MADV_FREE | 8 | 4.5 | lazy free, private anonymous only |
| MADV_REMOVE | 9 | 2.6.16 | punch hole in backing store; shared+writable |
| MADV_DONTFORK | 10 | 2.6.16 | exclude child after fork |
| MADV_DOFORK | 11 | 2.6.16 | undo MADV_DONTFORK |
| MADV_MERGEABLE | 12 | 2.6.32 | KSM; CONFIG_KSM required |
| MADV_UNMERGEABLE | 13 | 2.6.32 | undo KSM; CONFIG_KSM required |
| MADV_HUGEPAGE | 14 | 2.6.38 | THP; CONFIG_TRANSPARENT_HUGEPAGE |
| MADV_NOHUGEPAGE | 15 | 2.6.38 | no THP; CONFIG_TRANSPARENT_HUGEPAGE |
| MADV_DONTDUMP | 16 | 3.4 | exclude from core dump |
| MADV_DODUMP | 17 | 3.4 | undo MADV_DONTDUMP |
| MADV_WIPEONFORK | 18 | 4.14 | zero for child; private anonymous only |
| MADV_KEEPONFORK | 19 | 4.14 | undo MADV_WIPEONFORK |
| MADV_COLD | 20 | 5.4 | deactivate pages (nondestructive) |
| MADV_PAGEOUT | 21 | 5.4 | reclaim (swap out / write back) |
| MADV_POPULATE_READ | 22 | header only in cache | man gap; value from glibc header (5.14 era) |
| MADV_POPULATE_WRITE | 23 | header only in cache | man gap; value from glibc header (5.14 era) |
| MADV_DONTNEED_LOCKED | 24 | header only in cache | man gap; value from glibc header (5.18 era) |
| MADV_COLLAPSE | 25 | header only in cache | man gap; value from glibc header (6.1 era) |
| MADV_HWPOISON | 100 | 2.6.32 | CAP_SYS_ADMIN; CONFIG_MEMORY_FAILURE; test-only |

Kernel-side "ifdef'd" availability (man DESCRIPTION/ERRORS):
MADV_MERGEABLE/UNMERGEABLE fail with EINVAL unless `CONFIG_KSM`;
MADV_HUGEPAGE/NOHUGEPAGE unless `CONFIG_TRANSPARENT_HUGEPAGE`; MADV_HWPOISON
(and MADV_SOFT_OFFLINE, 2.6.33, in the man page but not in the glibc header
block) only with `CONFIG_MEMORY_FAILURE`. Since 3.18 the syscall itself is
optional via `CONFIG_ADVISE_SYSCALLS`.

## Security and notes

- MADV_HWPOISON injects artificial memory corruption: CAP_SYS_ADMIN only,
  may SIGBUS and unmap the page; for testing error handling only.
- MADV_DONTNEED on a shared mapping discards the caller's dirty pages
  (data loss footgun) and fails on locked or hugetlb pages.
- MADV_WIPEONFORK keeps PRNG seeds and secrets out of forked children;
  MADV_DONTDUMP keeps them out of core dumps (overrides
  `/proc/[pid]/coredump_filter`).
- Kernel-side `process_madvise(2)` (pidfd-targeted, 5.10+) is a different
  syscall, out of scope here.

## References

- Cached man page: `source-cache/man-pages-sparse/man2/madvise.2`.
- Constants and `#ifdef __USE_MISC` guard:
  `/usr/include/x86_64-linux-gnu/bits/mman-linux.h`.
- Numbers: hub [overview](overview.md); cached kernel syscall tables.
- Worklog Task 1-b: MADV_* values verified against the same headers.
