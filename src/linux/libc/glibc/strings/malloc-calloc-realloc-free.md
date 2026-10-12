# `malloc` / `calloc` / `realloc` / `free` / `reallocarray` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` |
| Standards | ISO C89 / POSIX.1-2001 (`malloc`, `calloc`, `realloc`, `free`); OpenBSD/FreeBSD origin (`reallocarray`) |
| Exported | `malloc@@GLIBC_2.2.5`, `calloc@@GLIBC_2.2.5` (weak), `realloc@@GLIBC_2.2.5`, `free@@GLIBC_2.2.5`, `reallocarray@@GLIBC_2.26` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`malloc(3)` ATTRIBUTES); arenas + internal mutexes |
| Ledger ID | GLIBC-malloc, GLIBC-calloc, GLIBC-realloc, GLIBC-free, GLIBC-reallocarray |

## Declaration and gates

```c
#include <stdlib.h>

void *malloc(size_t size);                    /* __attribute_alloc_size__((1)) */
void *calloc(size_t nmemb, size_t size);      /* __attribute_alloc_size__((1,2)) */
void *realloc(void *ptr, size_t size);        /* __attribute_alloc_size__((2)) */
void  free(void *ptr);
void *reallocarray(void *ptr, size_t nmemb, size_t size); /* __USE_MISC */
```

The `__attribute_alloc_size__` annotations shown are in the installed
header (`/usr/include/stdlib.h` lines 672-701) and are what GCC's
`-Walloc-size` and object-size analysis consume. `reallocarray` gate
history per `malloc(3)`: `_DEFAULT_SOURCE` since glibc 2.29,
`_GNU_SOURCE` before; first exported in glibc 2.26.

## Semantics

`malloc` returns `size` bytes of *uninitialized*, suitably aligned memory;
size 0 returns a unique freeable pointer (`malloc(3)`). `calloc` allocates
`nmemb * size` bytes zeroed and **fails safely on multiplication overflow**
(`malloc(3)` calloc section). `realloc` grows or shrinks a block,
preserving content up to the smaller of old and new sizes; `realloc(NULL,
size)` is `malloc(size)`, `realloc(ptr, 0)` is `free(ptr)` on glibc; on
failure the original block is untouched (`malloc(3)`). `free` releases a
block; `free(NULL)` is a no-op. All return `NULL` with `errno` set
(usually `ENOMEM`) on failure; sizes over `PTRDIFF_MAX` are rejected since
glibc 2.30 (`malloc(3)` VERSIONS).

## Gotchas and portability

- Allocator internals: glibc's allocator derives from ptmalloc/dlmalloc,
  carves chunks from per-thread arenas, and serves very large requests
  with `mmap` (default dynamic `MMAP_THRESHOLD` around 128 kB, tunable
  via `mallopt`) (`malloc(3)` NOTES, manual `memory.texi` *GNU
  Allocator*). `malloc` returns 8-byte (16 on 64-bit) alignment, so
  over-aligned types need the aligned-allocation family (manual
  *Aligned Memory Blocks*).
- Linux overcommit: non-`NULL` from `malloc` does not guarantee the pages
  are really available; the OOM killer may strike later (`malloc(3)`
  NOTES).
- Zero-size behavior is glibc-specific; portable code must tolerate
  `NULL` without `errno` for zero requests (`malloc(3)` "Nonportable
  behavior").
- `free` preserves `errno` since glibc 2.33 (`malloc(3)` VERSIONS); cleanup
  paths may rely on that on modern glibc only.
- Replacing malloc: glibc allows interposing the four core functions, but
  a replacement must reproduce the documented `errno`, size-zero, and
  overflow semantics (`malloc(3)` NOTES); POSIX and ISO C do not sanction
  replacement at all.
- musl 1.2.5 uses the mallocng allocator (size-class tables in
  `musl src/malloc/mallocng/malloc.c`); see the musl catalog for deltas.

## References

- glibc manual: `memory.texi`, nodes *The GNU Allocator*, *Basic
  Allocation*, *Freeing after Malloc*, *Changing Block Size*
- man3: `malloc(3)` (covers `free`, `calloc`, `realloc`, `reallocarray`)
- header: `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
