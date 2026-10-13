# remap_file_pages(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 216 / 257 / 234 / 253 (hub) |
| Since (kernel) | 2.6 (hub; remap_file_pages.2 VERSIONS: "appeared in Linux 2.5.46"; glibc support 2.3.3) |
| Man page | man2/remap_file_pages.2 (cached, dated 2021-03-22) |
| glibc wrapper | yes, in libc since glibc 2.3.3 (man VERSIONS); needs _GNU_SOURCE |
| Aliases covered | none |
| Ledger ID | SC-remap_file_pages (ledger status: researched brief) |

## Purpose

remap_file_pages() creates a nonlinear file mapping: inside one
MAP_SHARED mmap(2) ([mmap](mmap.md)) mapping, calls rearrange which
file pages appear at which addresses, one file page may appear at
several addresses. The point was avoiding extra VMAs on 32-bit systems;
that use case does not exist on 64-bit (remap_file_pages.2).

## Synopsis

```c
#define _GNU_SOURCE
#include <sys/mman.h>
int remap_file_pages(void *addr, size_t size, int prot,
                     size_t pgoff, int flags);
```

## Arguments and behavior

`addr` identifies the mapping and is the destination; `pgoff` (pages)
and `size` select the file region. `addr`/`size` should be page
multiples (kernel rounds both down); `prot` must be 0; only MAP_NONBLOCK
of the mmap-style flags is honored. Since 2.6.23 nonlinear mappings are
created only on in-memory filesystems (tmpfs, hugetlbfs, ramfs).

## Return value and errors

0 on success; -1 with `errno`: `EINVAL` (addr is not a MAP_SHARED
mapping; or addr, size, prot or pgoff invalid).

## Flags and constants

MAP_NONBLOCK (see the [mmap](mmap.md) flag table).

## Security and notes

- Deprecated since 3.16; since 4.0 implemented as slower in-kernel
  emulation (commits cited in the man page). Still shipped; the man page
  tells remaining users to migrate.
- Brief page per worklog 1-b split; ledger status `researched`.

## References

- Cached man page: source-cache/man-pages-sparse/man2/remap_file_pages.2.
- Numbers/Since: hub [overview](overview.md); ledger SC-remap_file_pages.
