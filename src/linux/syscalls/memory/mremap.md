# mremap(2)

| Field | Value |
|---|---|
| Numbers (x64 / i386 / arm64-generic / arm32) | 25 / 163 / 216 / 163 |
| Since (kernel) | 2.0 |
| Man page | man2/mremap.2 (cached, dated 2021-03-22) |
| glibc wrapper | yes; _GNU_SOURCE; glibc did not expose MREMAP_FIXED or the fifth argument before glibc 2.4 |
| Aliases covered | none |
| Ledger ID | SC-mremap |

## Purpose

`mremap()` expands or shrinks an existing virtual memory mapping, optionally
relocating it. It re-points page-table entries rather than copying pages,
which is how glibc implements an efficient `realloc(3)` for large blocks,
and powers the `MREMAP_DONTUNMAP` userfaultfd/GC relocation tricks.

## Synopsis

```c
#define _GNU_SOURCE
#include <sys/mman.h>
void *mremap(void *old_address, size_t old_size, size_t new_size,
             int flags, ... /* void *new_address */);
```

## Arguments and behavior

`old_address` must be page-aligned. With `old_size` = 0 and a shareable
(`MAP_SHARED`) mapping, mremap creates a *new* mapping of the same pages of
size `new_size` (requires MREMAP_MAYMOVE). The optional fifth argument
`new_address` is required by `MREMAP_FIXED` and gives the page-aligned
destination. Locks from `mlock(2)` survive resize/relocation; population
of the new area is best effort and never fails the call.

## Return value and errors

Returns a pointer to the new virtual memory area; `MAP_FAILED`
(`(void *) -1`) with `errno` on failure. `EAGAIN`: growing a locked segment
would exceed `RLIMIT_MEMLOCK`. `EFAULT`: bad address in the old range (or
mixed mapping types). `EINVAL` (man's enumerated list): old_address not
page-aligned; unknown flag bits; `new_size` = 0; new range overlapping the
old; FIXED/DONTUNMAP without MAYMOVE; DONTUNMAP on non-private-anonymous
pages or with `old_size != new_size`; old_size = 0 without a shareable
mapping (since 4.14 -- earlier kernels silently created an unrelated
private mapping, man BUGS). `ENOMEM`: no room to expand in place without
MAYMOVE, or the new mapping cannot be created.

## Flags and constants

Values verified in glibc `bits/mman-shared.h` (`#ifdef __USE_GNU`) and
kernel `include/linux/mman.h`:

| Flag | Value | Since | Meaning |
|---|---|---|---|
| MREMAP_MAYMOVE | 1 | 2.0 | kernel may relocate the mapping if it cannot grow in place |
| MREMAP_FIXED | 2 | 2.3.31 | move to exact `new_address` (mmap MAP_FIXED analog); clobbers what is there; requires MAYMOVE |
| MREMAP_DONTUNMAP | 4 | 5.7 | move but keep source mapped (zero-fill or userfaultfd on later access); requires MAYMOVE |

**There is no `MREMAP_MUSTMOVE` flag.** The fixed-address flag is
`MREMAP_FIXED`; no constant named MREMAP_MUSTMOVE exists in the kernel UAPI,
in glibc `bits/mman-shared.h`, or in `include/linux/mman.h`, and the man
page never mentions one (verified in this repo's sources; also stated in
worklog Task 1-b). Likewise the `MADV_*` constants belong to
[madvise](madvise.md), not to mremap.

## Security and notes

- Moving a mapping invalidates absolute pointers into the old location;
  offsets relative to the mapping start stay valid.
- MREMAP_FIXED silently unmaps anything at the destination -- the same
  clobbering hazard as `mmap(MAP_FIXED)`.
- MREMAP_DONTUNMAP works only on private anonymous mappings and leaves the
  source range faulting; pair it with `userfaultfd(2)` for non-cooperative
  fault handling or GC (man use-case section).
- Linux-specific; not portable. Locked segments keep their locks but the
  total locked amount may change (RLIMIT_MEMLOCK accounting).

## References

- Cached man page: `source-cache/man-pages-sparse/man2/mremap.2`
  (DESCRIPTION, ERRORS, BUGS, NOTES).
- Constants: `/usr/include/x86_64-linux-gnu/bits/mman-shared.h`;
  `/usr/include/linux/mman.h` (MREMAP_MAYMOVE 1, MREMAP_FIXED 2,
  MREMAP_DONTUNMAP 4; no other MREMAP_* names).
- Numbers: hub [overview](overview.md); cached kernel syscall tables.
- Worklog Task 1-b: MREMAP_MUSTMOVE-nonexistence finding reused here.
