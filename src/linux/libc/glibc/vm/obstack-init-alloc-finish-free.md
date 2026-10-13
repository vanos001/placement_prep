# `obstack_init` / `obstack_alloc` / `obstack_finish` / `obstack_free` - glibc

> Split from the chapter *glibc: Virtual Memory Allocation And Paging* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `obstack.h` (no feature-test gate; the whole file is unconditional) |
| Standards | GNU extension (manual, *Obstacks*) |
| Exported | only `obstack_free@@GLIBC_2.2.5` as a callable symbol; `obstack_init`, `obstack_alloc`, `obstack_finish` are macros that inline to `_obstack_begin@@GLIBC_2.2.5` / `_obstack_newchunk@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | per-obstack only: manual safety notes mark the family `mtsrace:obstack-ptr`, AC-unsafe (`obstack.c`-backed macros, no man ATTRIBUTES table exists) |
| Ledger ID | GLIBC-obstack_init, GLIBC-obstack_alloc, GLIBC-obstack_finish, GLIBC-obstack_free |

## Declaration and gates

```c
#include <obstack.h>

/* obstack.h lines 228-231: macro over the real function */
#define obstack_init(h) \
  _obstack_begin ((h), 0, 0, (void *(*)(long))obstack_chunk_alloc, \
                  (void (*)(void *))obstack_chunk_free)

/* obstack.h lines 368-372 and 388-401 */
void *obstack_alloc(h, length);   /* obstack_blank + obstack_finish */
void *obstack_finish(h);          /* close the growing object */
void  obstack_free(h, obj);       /* also a real function in libc */
```

No `__USE_*` gate exists; `obstack.h` is standalone. Before `obstack_init`
the program must define `obstack_chunk_alloc` / `obstack_chunk_free`
(plain no-argument macros or functions; the manual warns macro definitions
with arguments will not work) -- typically `malloc` / `free`
(`/usr/include/obstack.h` lines 35-36, manual *Preparing for Using Obstacks*).

## Semantics

An obstack is a stack of objects packed into large *chunks* obtained via
`obstack_chunk_alloc`; chunks default to 4096 bytes and longer chunks are
used for oversized objects (manual, *Obstack Chunks*). `obstack_init`
initializes a `struct obstack` and allocates the first chunk; it always
returns 1 (older glibc returned 0 on allocation failure). If the chunk
allocator fails, `obstack_alloc_failed_handler` is called instead of
returning (obstack.h line 204; default action prints and exits with
`obstack_exit_failure`).

`obstack_alloc(h, n)` returns `n` uninitialized bytes, freed only by
`obstack_free`. `obstack_finish(h)` closes the currently growing object
and returns its final address; once finished, an object never moves again.
`obstack_free(h, obj)` frees `obj` and everything allocated after it;
`obstack_free(h, NULL)` frees the whole stack and leaves the obstack
uninitialized, so to keep the obstack usable pass the first object's
address instead (manual, *Freeing Obstack Objects*).

## Gotchas and portability

- The "functions" are macros. `nm` on libc shows no `obstack_init`,
  `obstack_alloc` or `obstack_finish` symbol -- only the internal
  `_obstack_begin` / `_obstack_newchunk` / `_obstack_free` workhorses plus
  the exported alias `obstack_free@@GLIBC_2.2.5` (the macro shadows it;
  gnulib builds can rename it via `__obstack_free`, obstack.h lines 57-62).
- Macro arguments may be evaluated many times: no side effects in the
  obstack pointer (obstack.h lines 24-25, manual *Obstack Functions*).
- `obstack_free(h, NULL)` does not just empty the stack, it invalidates it.
- musl 1.2.5: no obstack support at all -- no `obstack.h`, no symbols
  (`musl include/`, `src/` searched); code needs the gnulib copy.

## References

- glibc manual: `memory.texi`, nodes *Creating Obstacks*,
  *Preparing for Using Obstacks*, *Allocation in an Obstack*,
  *Freeing Obstack Objects*, *Obstack Functions and Macros*, *Obstack Chunks*
- headers: `/usr/include/obstack.h` (lines 228-231, 368-401)
- symbols: `nm -D --with-symbol-versions libc.so.6`
