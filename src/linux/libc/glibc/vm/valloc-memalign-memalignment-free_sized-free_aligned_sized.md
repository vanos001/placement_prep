# `valloc` / `memalign` / `memalignment` / `free_sized` / `free_aligned_sized` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `valloc`: `stdlib.h` lines 711-714, gated on `__USE_XOPEN_EXTENDED` (pre-XOPEN2K) or `__USE_MISC`, also `malloc.h` line 72; `memalign`: `malloc.h` line 67; `memalignment`, `free_sized`, `free_aligned_sized`: no header on this host (C23, not in glibc 2.41) |
| Standards | SVID/XPG (`valloc`); BSD/GNU (`memalign`); ISO C23 (`memalignment`, `free_sized`, `free_aligned_sized`) |
| Exported | `valloc@@GLIBC_2.2.5` (W), `memalign@@GLIBC_2.2.5` (W), `pvalloc@@GLIBC_2.2.5` (W); no `memalignment` / `free_sized` / `free_aligned_sized` symbols (nm, host glibc 2.41 -- the dev-tree NEWS lists them under Version 2.43) |
| Thread-safety | MT-Safe (`memalign`, per posix_memalign.3 ATTRIBUTES); `valloc`/`pvalloc` MT-Unsafe init (posix_memalign.3) |
| Ledger ID | GLIBC-valloc, GLIBC-memalign, GLIBC-memalignment, GLIBC-free_sized, GLIBC-free_aligned_sized |

## Declaration and gates

```c
#include <stdlib.h>
void *valloc(size_t size);   /* page-aligned; stdlib.h gate above */

#include <malloc.h>
void *memalign(size_t alignment, size_t size);   /* malloc.h:67 */
```

`memalignment` / `free_sized` / `free_aligned_sized` have no declaration
on this host: not in `stdlib.h`, `malloc.h`, or `bits/`, and no libc
symbol. The development-tree NEWS (Version 2.43 section) says: "The ISO
C23 memalignment function has been added" and "The ISO C23 functions
free_sized and free_aligned_sized are now supported in <stdlib.h>".

## Semantics

`valloc` allocates `size` bytes aligned to a page boundary (the header
comment in stdlib.h still reads "The storage cannot be freed" -- a fossil;
posix_memalign.3 NOTES states glibc allows `free` on it). `memalign`
allocates `size` bytes whose address is a multiple of `alignment`, which
must be a power of two; glibc's malloc normally returns 8/16-byte-aligned
memory, so these matter only for larger alignments (manual,
*Aligned Memory Blocks*). posix_memalign.3 adds that `memalign` "may not
check that the alignment argument is correct". The C23 trio completes the
family portably: `memalignment` reports an object's alignment, and
`free_sized`/`free_aligned_sized` free a malloc/aligned_alloc block with
its size (or size+alignment) supplied, closing the size/pointer-mismatch
class of bugs; all three are absent from host glibc 2.41 and from musl
1.2.5.

## Gotchas and portability

- `memalign` is obsolete; use `aligned_alloc` (C11) or `posix_memalign`
  (POSIX.1-2001) (manual, *Aligned Memory Blocks*).
- glibc `free` accepts memory from any of these (posix_memalign.3 NOTES);
  that is not portable -- some systems cannot free `memalign`/`valloc`
  blocks at all.
- `pvalloc` (rounds the size up to whole pages) exists in glibc but is not
  a ledger row of this page.
- musl 1.2.5: `valloc` and `memalign` present (`include/malloc.h` -- the
  7-function malloc.h with mallocng as the allocator); no
  `free_sized`/`free_aligned_sized`/`memalignment` anywhere.

## References

- man3: `posix_memalign.3` (covers `valloc`, `memalign`, `pvalloc`), `valloc.3` (`.so` link)
- glibc manual: `memory.texi`, node *Aligned Memory Blocks*; NEWS 2.43 section
- headers: `/usr/include/stdlib.h` (lines 706-725), `/usr/include/malloc.h` (lines 66-78)
- symbols: `nm -D --with-symbol-versions libc.so.6`
