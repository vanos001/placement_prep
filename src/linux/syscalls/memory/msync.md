# msync(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 26 / 144 / 227 / 144 |
| Since (kernel) | 2.0 (hub value; the man page says the call was introduced in Linux 1.3.21) |
| Man page | man2/msync.2 (cached, dated 2021-03-22) |
| glibc wrapper | yes, in libc (`sys/mman.h`); no feature-test restrictions |
| Aliases covered | none |
| Ledger ID | SC-msync |

## Purpose

`msync()` flushes changes made through a memory mapping created by
`mmap(2)` back to the filesystem. Without it there is no guarantee that
modifications to a `MAP_SHARED` file mapping are written back before
`munmap(2)` is called. The call updates the part of the file corresponding
to `[addr, addr+length)`.

## Synopsis

```c
#include <sys/mman.h>
int msync(void *addr, size_t length, int flags);
```

## Arguments and behavior

`addr` must be a multiple of the page size. POSIX requires exactly one of
`MS_ASYNC` and `MS_SYNC`; Linux also accepts a call with neither, with
semantics currently equivalent to `MS_ASYNC`. `MS_ASYNC` schedules the
writeback and returns immediately -- since Linux 2.6.19 it is in fact a
**no-op** (commit 204ec841fbea, quoted in the man page) because the kernel
tracks dirty pages and flushes them itself. `MS_SYNC` waits for completion.
`MS_INVALIDATE` asks that other mappings of the same file be invalidated so
they pick up the fresh values.

## Return value and errors

0 on success; -1 with `errno` on failure. `EBUSY`: MS_INVALIDATE with a
memory lock (`mlock(2)` family) on the range. `EINVAL`: addr not
page-aligned; any bit other than MS_ASYNC | MS_INVALIDATE | MS_SYNC set;
MS_SYNC together with MS_ASYNC. `ENOMEM`: the indicated memory (or part of
it) was not mapped; the man page records that the call originally (1.3.21)
returned EFAULT here and switched to the POSIX ENOMEM in 2.4.19.

## Flags and constants

Values verified in glibc `bits/mman-linux.h`:

| Flag | Value | Note |
|---|---|---|
| MS_ASYNC | 1 | schedule writeback; no-op since 2.6.19 |
| MS_INVALIDATE | 2 | invalidate other mappings of the same file |
| MS_SYNC | 4 | synchronous writeback; wait for completion |

## Security and notes

- Only `MS_SYNC` gives a synchronous completion guarantee; `MS_ASYNC`
  returning means nothing reached the device. Portable code should always
  pass one of MS_SYNC / MS_ASYNC even though Linux tolerates neither.
- Timestamps: for file-backed mappings, `st_ctime`/`st_mtime` are updated
  after a mapped-region write and before a subsequent msync with MS_SYNC or
  MS_ASYNC (man mmap.2 "Timestamps changes").
- `msync()` does not push `MAP_PRIVATE` changes to the file; it is
  meaningful for `MAP_SHARED` file mappings only.
- Related: [mmap](mmap.md), [munmap](munmap.md), [mincore](mincore.md).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/msync.2`
  (including the 2.6.19 MS_ASYNC no-op note).
- Constants: `/usr/include/x86_64-linux-gnu/bits/mman-linux.h`
  (MS_ASYNC 1, MS_SYNC 4, MS_INVALIDATE 2).
- Numbers: hub [overview](overview.md); cached kernel syscall tables.
