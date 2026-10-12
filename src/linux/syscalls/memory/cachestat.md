# cachestat(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 451 / 451 / 451 / 451 (hub) |
| Since (kernel) | 6.5 (hub; man page HISTORY "Linux 6.5"; worklog 1-b tag-probed absent 6.4 / present 6.5) |
| Man page | man2/cachestat.2 (man-pages 6.19, fetched from man7.org to source-cache/fetched/cachestat.2.txt; not in the sparse cache) |
| glibc wrapper | none (SYNOPSIS is the raw interface; call via syscall(2)) |
| Aliases covered | none |
| Ledger ID | SC-cachestat |

## Purpose

cachestat() reports the page cache occupancy of a file's bytes: for the
range `[.off, .off + .len]` of `cstat_range` it counts cached pages, dirty
pages, pages marked for writeback, evicted pages (previously cached, since
evicted), and recently evicted pages (reentry would indicate active use
under memory pressure). If `.len` is 0, the range runs from `.off` to end
of file. It is the per-file, range-aware alternative to mincore(2)
([mincore](mincore.md)), meant for application cache management (worklog
1-b verified the 6.5 since value and the struct layout).

## Synopsis

```c
#include <sys/mman.h>
struct cachestat_range {
    __u64 off;
    __u64 len;
};
struct cachestat {
    __u64 nr_cache;
    __u64 nr_dirty;
    __u64 nr_writeback;
    __u64 nr_evicted;
    __u64 nr_recently_evicted;
};
int cachestat(unsigned int fd, struct cachestat_range *cstat_range,
              struct cachestat *cstat, unsigned int flags);
```

## Arguments and behavior

`fd` names a file; the query uses its address_space mapping. `.off` and
`.len` must be non-negative; pages are counted over the byte range
inclusive of a partial last page. `flags` is reserved and must be 0.
The kernel walks the page cache under RCU (filemap_cachestat() in
mm/filemap.c), so counts are advisory: page state can change between the
scan and the return, and results may be slightly outdated (man CAVEATS).
Hugetlbfs files are not supported.

## Return value and errors

Zero on success; on failure -1 with `errno`: `EFAULT` (bad `cstat_range`
or `cstat`), `EINVAL` (nonzero flags), `EBADF` (bad fd), `EOPNOTSUPP`
(hugetlbfs file). The kernel source (mm/filemap.c, can_do_cachestat())
additionally returns `EPERM` when the file is neither open for writing
nor writable by the caller (the same reveal-policy comment as mincore);
the 6.19 man page does not list `EPERM` yet.

## Flags and constants

No flag constants: `flags` must be 0. The struct field types `__u64`
come from the kernel UAPI; userspace currently declares the structs
locally since no installed glibc header ships them (checked
/usr/include/linux).

## Security and notes

- Config gate `CONFIG_CACHESTAT_SYSCALL` (mm/filemap.c wraps
  SYSCALL_DEFINE4(cachestat) in `#ifdef`).
- i386, arm64-generic and arm32 share the x64 number 451 (post-4.3
  unified numbering; hub).
- write permission on the file (or open O_WRONLY, or owner/CAP) is the
  visibility check, mirroring mincore(2)'s "write access" rule (kernel
  comment in mm/filemap.c).
- Worklog 1-b correction: an earlier crossref note ("XR-209") said 6.1;
  the verified value is 6.5.

## References

- Man page (fetched): source-cache/fetched/cachestat.2.txt (man-pages 6.19).
- Kernel source: source-cache/fetched/master-mm-filemap.c
  (SYSCALL_DEFINE4(cachestat), filemap_cachestat, can_do_cachestat).
- Numbers/Since: hub [overview](overview.md); worklog Task 1-b.
