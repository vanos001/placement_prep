# `obstack_base` / `obstack_next_free` / `obstack_object_size` / `obstack_room` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `obstack.h` (no feature-test gate) |
| Standards | GNU extension (manual, *Status of an Obstack*) |
| Exported | none -- all four are macros; `obstack_base`/`obstack_next_free` read `struct obstack` fields directly, `obstack_room` too, and `obstack_memory_used` maps to `_obstack_memory_used@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | per-obstack only: `mtsrace:obstack-ptr` (reads of live fields; manual safety notes) |
| Ledger ID | GLIBC-obstack_base, GLIBC-obstack_next_free, GLIBC-obstack_object_size, GLIBC-obstack_room |

## Declaration and gates

```c
#include <obstack.h>

/* obstack.h lines 213, 221, 270-278 (GCC statement-expression forms) */
void *obstack_base(h);          /* ((void *) (h)->object_base) */
void *obstack_next_free(h);     /* ((h)->next_free)            */
int   obstack_object_size(h);   /* next_free - object_base     */
int   obstack_room(h);          /* chunk_limit - next_free     */
```

No `__USE_*` gate; `obstack.h` is unconditional.

## Semantics

These four macros report the state of the obstack while an object is
still growing (manual, *Status of an Obstack*):

- `obstack_base` returns the *tentative* address of the start of the
  growing object -- the address the object will have if you finish it
  now. If further growth outgrows the current chunk, `_obstack_newchunk`
  moves the object and the base changes.
- `obstack_next_free` returns the first free byte in the current chunk,
  i.e. the end of the growing object; with no object growing it equals
  `obstack_base`.
- `obstack_object_size` is the size of the growing object in bytes,
  defined as `obstack_next_free(h) - obstack_base(h)`. Call it *before*
  `obstack_finish`; after finishing it returns 0.
- `obstack_room` returns how many bytes can still be added safely in the
  current chunk -- the counterpart that makes the unchecked `*_fast`
  growth macros usable in batches (manual, *Extra Fast Growing Objects*).

## Gotchas and portability

- All four are field peeks into `struct obstack`, not function calls: they
  are free but also unsafe against concurrent growth on the same obstack.
- `obstack_base` is only tentative -- an object that forces a new chunk
  moves, so never persist the base before finishing.
- `obstack_object_size` after `obstack_finish` is 0, not the finished
  size; capture it before finishing.
- Taking their address is impossible (macros); `obstack_object_size` and
  `obstack_room` return `unsigned` under GCC.
- musl 1.2.5: absent (no `obstack.h` anywhere in the tree).

## References

- glibc manual: `memory.texi`, nodes *Status of an Obstack*,
  *Extra Fast Growing Objects*, *Growing Objects*
- headers: `/usr/include/obstack.h` (lines 213-225, 270-278)
- symbols: `nm -D --with-symbol-versions libc.so.6`
