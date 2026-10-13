# `obstack_grow` / `obstack_copy` / `obstack_blank` / `obstack_1grow` (+ `_fast` variants) - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `obstack.h` (no feature-test gate) |
| Standards | GNU extension (manual, *Growing Objects*) |
| Exported | none -- all twelve are macros; the growth paths inline to `_obstack_newchunk@@GLIBC_2.2.5` when a new chunk is needed (nm, host glibc 2.41) |
| Thread-safety | per-obstack only: `mtsrace:obstack-ptr`, AC-unsafe (manual safety notes) |
| Ledger ID | GLIBC-obstack_grow, GLIBC-obstack_grow0, GLIBC-obstack_copy, GLIBC-obstack_copy0, GLIBC-obstack_blank, GLIBC-obstack_blank_fast, GLIBC-obstack_1grow, GLIBC-obstack_1grow_fast, GLIBC-obstack_int_grow, GLIBC-obstack_int_grow_fast, GLIBC-obstack_ptr_grow, GLIBC-obstack_ptr_grow_fast |

## Declaration and gates

```c
#include <obstack.h>

void obstack_grow(h, data, size);        /* copy size bytes in */
void obstack_grow0(h, data, size);       /* ... plus a NUL (not counted) */
void obstack_blank(h, size);             /* size uninitialized bytes */
void obstack_1grow(h, c);                /* one byte */
void obstack_ptr_grow(h, data);          /* sizeof(void*) bytes */
void obstack_int_grow(h, data);          /* sizeof(int) bytes */
void obstack_1grow_fast(h, c);           /* no room check */
void obstack_ptr_grow_fast(h, data);     /* no room check */
void obstack_int_grow_fast(h, data);     /* no room check */
void obstack_blank_fast(h, size);        /* no room check */
```

Under GCC every macro expands to a statement expression computing its
arguments once (`obstack.h` lines 268-385); a portable plain-C fallback
sits at lines 413-505.

## Semantics

Growth macros append to the *currently growing object* (started implicitly
by the first growth after a `obstack_finish`). Each first checks
`obstack_room` and calls `_obstack_newchunk` when the current chunk is too
small, then advances `next_free`. The `0` variants append one extra zero
byte not included in `size` -- the way to build strings. `obstack_copy`
and `obstack_copy0` are `obstack_grow`/`obstack_grow0` followed by
`obstack_finish` (obstack.h lines 374-384). The `ptr_`/`int_` variants
store one pointer / one `int`.

The `_fast` variants skip the room check entirely: `obstack_1grow_fast`
is literally `*((h)->next_free)++ = (achar)` and `obstack_blank_fast` is
`next_free += n` (obstack.h lines 254-256). The caller must have verified
with `obstack_room` that the chunk can absorb the data (manual,
*Extra Fast Growing Objects*).

## Gotchas and portability

- `_fast` growth past the chunk limit corrupts the heap with no check at
  all; check `obstack_room` in batches, not per call, or the fast path
  buys nothing.
- `obstack_ptr_grow`/`obstack_int_grow`/`*_fast` assume the growing object
  is suitably aligned for a pointer/int (obstack.h lines 325-327 comment).
- Sizes are `int` in the classic prototypes -- not `size_t`.
- The `*_fast` and `_blank_fast` macros are also defined outside the GNU-C
  block, so they work with non-GCC compilers; the checking variants use
  statement expressions there.
- musl 1.2.5: absent (no `obstack.h` anywhere in the tree).

## References

- glibc manual: `memory.texi`, nodes *Growing Objects*,
  *Extra Fast Growing Objects*
- headers: `/usr/include/obstack.h` (lines 254-385, 413-505)
- symbols: `nm -D --with-symbol-versions libc.so.6`
