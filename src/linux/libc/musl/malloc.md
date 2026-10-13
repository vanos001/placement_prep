# musl: malloc

| Field | Value |
|---|---|
| musl version | 1.2.5 (WHATSNEW) |
| Key source files | `src/malloc/mallocng/{malloc.c,meta.h,free.c,realloc.c,aligned_alloc.c,malloc_usable_size.c}`, `src/malloc/{calloc.c,realloc.c,memalign.c,posix_memalign.c,reallocarray.c,replaced.c}` |
| glibc counterpart pages | [malloc/calloc/realloc/free](../glibc/strings/malloc-calloc-realloc-free.md), [aligned_alloc/posix_memalign/memalign/valloc](../glibc/strings/aligned_alloc-posix_memalign-memalign-valloc.md), [mallinfo3 / malloc_usable_size](../glibc/fs/mallinfo3-deprecated-malloc_usable_size.md), [mcheck/mtrace/memusage](../glibc/fs/mcheck-mtrace-memusage.md) |
| Ledger | MUSL-family-malloc row; ledger-musl.md header family `malloc.h` (7) |

## Implementation notes

mallocng became the default allocator in 1.2.1 (WHATSNEW, "major changes").
It is size-class based: `src/malloc/mallocng/malloc.c` defines 48 size classes
and `meta.h` the `struct group` / `struct meta` records. Each group holds many
slots with per-slot 16-byte UNIT framing; 4-byte IB (internal bound) marks
framing so free can validate the pointer, and metadata pages are mprotected
and salted with `get_random_secret()` to frustrate heap corruption forging.
`MMAP_THRESHOLD` is 131052 (`meta.h`); 1.2.4 dropped MADV_FREE use (WHATSNEW).
There is no environment-driven tuning at all: `rg getenv src/malloc/` finds
nothing, so `MALLOC_ARENA_MAX` and the `MALLOC_*` variables are ignored.
`malloc_usable_size` returns the nominal size of the slot
(`mallocng/malloc_usable_size.c`).

## Deltas vs glibc (verified)

- No `mallopt`, `mallinfo`, `mallinfo2`, `pvalloc`, `malloc_info`, or
  `malloc_stats` anywhere in `include/` or `src/` (rg); glibc 2.41 libc.so.6
  exports `mallopt`, `mallinfo`, `mallinfo2@@GLIBC_2.33`, `malloc_info@@GLIBC_2.10`
  (nm -D). No arenas: one global context (`struct malloc_context`, `meta.h`)
  vs glibc ptmalloc per-thread arenas capped by `M_ARENA_MAX`.
- `aligned_alloc` accepts any power-of-two alignment, alignment >= 2^31*UNIT
  rejected as ENOMEM (`mallocng/aligned_alloc.c`).
- `free` preserves errno (1.2.3 WHATSNEW, POSIX-future).
- Interposable: `src/malloc/replaced.c` supports a replaced allocator.

## Porting notes

Code calling `mallopt`/`mallinfo` or setting `MALLOC_*` env tuning compiles
nowhere and runs untuned here; `malloc_usable_size` results differ in
rounding. Debug tooling (mcheck/mtrace) has no musl side; use valgrind or
mallocng's own consistency checks (unverified which builds enable them).
