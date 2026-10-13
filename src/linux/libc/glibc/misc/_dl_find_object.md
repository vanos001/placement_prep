# `_dl_find_object` (3) - glibc

> Split from the ledger chapter *dynlink* into the per-function layout;
> see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `dlfcn.h` (prototype line 225 and `struct dl_find_object` lines 203-221, both inside `__USE_GNU`; per-target macros from `bits/dl_find_object.h`) |
| Standards | GNU extension (manual, node *Dynamic Linker Introspection*) |
| Exported | `_dl_find_object@@GLIBC_2.35` (`T` in nm, host glibc 2.41; new in glibc 2.35) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `@safety`, `dynlink.texi` line 681), with a `dlclose` concurrency caveat (lines 707-714) |
| Ledger ID | GLIBC-_dl_find_object |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <dlfcn.h>

struct dl_find_object {
  unsigned long long int dlfo_flags;
  void *dlfo_map_start;      /* beginning of mapping containing address */
  void *dlfo_map_end;        /* end of mapping */
  struct link_map *dlfo_link_map;
  void *dlfo_eh_frame;       /* exception handling data of the object */
  /* dlfo_eh_dbase / dlfo_eh_count only where the target macros say so */
};

int _dl_find_object (void *address, struct dl_find_object *result);
```

Unlike every `dlopen`-family function, this one keeps the
implementation-reserved `__` prefix in its documented name. The
declaration and the struct live in the `__USE_GNU` block of `dlfcn.h`
(gate at line 30, block ends line 227). On x86-64
`DLFO_STRUCT_HAS_EH_DBASE` is 0 (bits header line 24), on other targets
it adds `dlfo_eh_dbase`; `DLFO_STRUCT_HAS_EH_COUNT` is 0 (line 28) and
`DLFO_EH_SEGMENT_TYPE` is `PT_GNU_EH_FRAME` (line 29).

## Semantics

On success it returns 0 and fills `*result` describing the loaded
object that contains `address` (a code or data address); on failure it
returns -1. On success the address lies in `[dlfo_map_start,
dlfo_map_end)`. `dlfo_eh_frame` points at the object's unwinding data
-- for DWARF targets the in-memory `PT_GNU_EH_FRAME` segment; an object
without unwinding information still yields 0 with a null
`dlfo_eh_frame` (manual `dynlink.texi` lines 679-705). `dlfo_flags`
bit zero (`DLFO_FLAG_SFRAME`) signals SFrame stack data (lines 618-620,
722-725). This is the primitive an exception-handling unwinder uses to
find `PT_GNU_EH_FRAME` without walking `/proc/self/maps` or the link
map chain itself; the manual states the function exists so unwinding
consumers can locate that data (lines 698-702).

## Gotchas and portability

- Concurrent or subsequent `dlclose` of the containing object invalidates
  `dlfo_eh_frame` and `dlfo_link_map`; the caller must keep `address`
  valid by convention (manual lines 707-714).
- Struct layout is target-dependent (`dlfo_eh_dbase`, `dlfo_eh_count`);
  never serialize it.
- On architectures with function descriptors, no descriptor decoding is
  attempted; the reported object may be the descriptor's (lines 686-691).
- musl 1.2.5 has no `_dl_find_object` (grep over `musl/include/`
  returns nothing; absence verified).

## Errors

-1 when no loaded object contains `address`; no `errno` value is
specified (manual lines 682-684).

## References

- glibc manual: `dynlink.texi`, node *Dynamic Linker Introspection*,
  `_dl_find_object` section
- headers: `/usr/include/dlfcn.h`, `/usr/include/link.h`,
  `/usr/include/x86_64-linux-gnu/bits/dl_find_object.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
- musl 1.2.5: absent from `include/` (absence verified)
