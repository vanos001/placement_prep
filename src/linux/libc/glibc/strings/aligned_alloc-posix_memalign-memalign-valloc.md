# `aligned_alloc` / `posix_memalign` / `memalign` / `valloc` / `pvalloc` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` (`aligned_alloc`, `posix_memalign`, `valloc`); `malloc.h` (`memalign`, `pvalloc`, plus `valloc`) |
| Standards | C11 (`aligned_alloc`); POSIX.1-2001/2008 (`posix_memalign`); legacy 3.0BSD/SunOS (`valloc`, `memalign`); GNU (`pvalloc`) |
| Exported | `aligned_alloc@@GLIBC_2.16` (weak), `posix_memalign@@GLIBC_2.2.5` (weak), `memalign@@GLIBC_2.2.5` (weak), `valloc@@GLIBC_2.2.5` (weak), `pvalloc@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`aligned_alloc`, `memalign`, `posix_memalign`); MT-Unsafe init (`valloc`, `pvalloc`) per `posix_memalign(3)` ATTRIBUTES |
| Ledger ID | GLIBC-aligned_alloc, GLIBC-posix_memalign, GLIBC-memalign, GLIBC-valloc, GLIBC-pvalloc |

## Declaration and gates

```c
#include <stdlib.h>

int   posix_memalign(void **memptr, size_t alignment, size_t size); /* _POSIX_C_SOURCE >= 200112L */
void *aligned_alloc(size_t alignment, size_t size);                 /* _ISOC11_SOURCE */
void *valloc(size_t size);                                          /* legacy, page size */

#include <malloc.h>
void *memalign(size_t alignment, size_t size);
void *pvalloc(size_t size);                                         /* GNU */
```

Gates per `posix_memalign(3)` SYNOPSIS and `/usr/include/malloc.h` lines
67-78 (`valloc` also appears in `stdlib.h` under the legacy gate
`(defined __USE_XOPEN_EXTENDED && !__USE_XOPEN2K) || __USE_MISC`).

## Semantics

`posix_memalign` allocates `size` bytes whose address is a multiple of
`alignment`, which must be a power of two *and* a multiple of
`sizeof(void *)`; it returns 0 on success or an error number on failure,
does **not** set `errno`, and leaves `*memptr` unmodified on failure
(`posix_memalign(3)`; the memptr rule was standardized in POSIX.1-2008
TC2). `aligned_alloc` is C11 and takes the arguments in the opposite
order; POSIX-era wording adds that `size` should be a multiple of
`alignment` (`posix_memalign(3)`). `memalign` is the obsolete ancestor
(power-of-two alignment, may not validate it); `valloc` aligns to
`sysconf(_SC_PAGESIZE)`; `pvalloc` additionally rounds the size up to a
page multiple (`posix_memalign(3)`). None of them zero the memory.

## Gotchas and portability

- Choose by standard: `aligned_alloc` for C11 portability, `posix_memalign`
  for POSIX; `memalign`/`valloc`/`pvalloc` are legacy
  (`posix_memalign(3)` CONFORMING TO).
- Freeability: POSIX guarantees `posix_memalign` memory is `free(3)`-able;
  on other systems `memalign`/`valloc` memory can be unfreeable because
  they align a `malloc` result by hand. The glibc implementation allows
  `free` on memory from *any* of these functions (`posix_memalign(3)`
  NOTES).
- `posix_memalign`'s return-value convention is inverted relative to every
  other call here: zero is success, the error value (e.g. `EINVAL`,
  `ENOMEM`) is the return, and `errno` is untouched (`posix_memalign(3)`
  RETURN VALUE/ERRORS).
- C11 `aligned_alloc` vs glibc: the "size multiple of alignment"
  restriction is the ISO wording; glibc accepts other sizes in practice,
  but portable C11 code must respect it (`posix_memalign(3)`
  DESCRIPTION).
- Plain `malloc` already returns 8-byte (16 on 64-bit) aligned blocks
  (manual `memory.texi` *Aligned Memory Blocks*), so this family is only
  needed for larger alignments: page-sized device I/O buffers, SIMD
  alignment, `max_align_t` overrides.
- musl 1.2.5 implements `aligned_alloc`, `posix_memalign`, `memalign`,
  `valloc` in `src/malloc/` (mallocng backend for the aligned paths,
  `src/malloc/mallocng/aligned_alloc.c`).

## References

- glibc manual: `memory.texi`, node *Aligned Memory Blocks*
- man3: `posix_memalign(3)` (covers all five via `.so` aliases
  `aligned_alloc.3`, `memalign.3`, `valloc.3`)
- headers: `/usr/include/stdlib.h`, `/usr/include/malloc.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
