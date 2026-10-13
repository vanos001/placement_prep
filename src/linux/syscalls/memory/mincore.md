# mincore(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 27 / 218 / 232 / 219 |
| Since (kernel) | 2.4 (hub value; man VERSIONS says "available since Linux 2.3.99pre1 and glibc 2.2") |
| Man page | man2/mincore.2 (cached, dated 2021-03-22) |
| glibc wrapper | yes; _DEFAULT_SOURCE since glibc 2.19 (_BSD_SOURCE || _SVID_SOURCE before) |
| Aliases covered | none |
| Ledger ID | SC-mincore |

## Purpose

`mincore()` reports whether pages of the calling process's virtual memory
are resident in RAM, i.e. whether referencing them would cause a disk
access (major fault). Typical uses: probing cache state before deciding on
`madvise(MADV_WILLNEED)`, and implementing `fincore(1)`-style tools. The
result is only a snapshot -- unlocked pages can come and go at any moment,
and `vec` may be stale before the call returns.

## Synopsis

```c
#include <sys/mman.h>
int mincore(void *addr, size_t length, unsigned char *vec);
```

## Arguments and behavior

`addr` must be a page-size multiple; `length` is effectively rounded up to
a page multiple. `vec` needs at least `(length + PAGE_SIZE - 1) /
PAGE_SIZE` bytes. On return, the least significant bit of each byte is set
if the corresponding page is resident and clear otherwise; the other bits
are undefined and reserved. The page size comes from
`sysconf(_SC_PAGESIZE)`.

## Return value and errors

0 on success; -1 with `errno` on failure. `EAGAIN`: kernel temporarily out
of resources. `EFAULT`: `vec` invalid. `EINVAL`: addr not a page-size
multiple. `ENOMEM`: `length` exceeds `TASK_SIZE - addr` (possible with a
negative length reinterpreted as huge unsigned; 2.6.11 and earlier returned
EINVAL), or the range contains unmapped memory.

## Flags and constants

None. The only constant involved is the residency bit: bit 0 (LSB) of each
`vec` byte, per the man page's DESCRIPTION. No `MINCORE_*` flags exist in
the kernel UAPI or in the glibc headers used for this repo (verified this
session).

## Security and notes

- Historical bug (man BUGS): before kernel 2.6.21, mincore returned wrong
  information for `MAP_PRIVATE` mappings and for nonlinear mappings made
  with `remap_file_pages(2)`.
- No capability is required and no Kconfig gate applies (none is documented
  in the man page).
- `mlock(2)`-locked pages are guaranteed resident, so mincore is most
  useful for the unlocked remainder of a mapping.
- Cross-links: [mmap](mmap.md), [madvise](madvise.md) (WILLNEED/PAGEOUT
  pairing), [mlock](mlock.md) (forcing residency).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/mincore.2`
  (DESCRIPTION incl. vec semantics, ERRORS, VERSIONS, BUGS).
- Numbers: hub [overview](overview.md); cached kernel syscall tables
  (x64 27, i386 218, generic 232, arm 219).
- Header check: no MINCORE_* constants in installed `sys/mman.h` or
  `bits/mman-*` headers (verified this session).
