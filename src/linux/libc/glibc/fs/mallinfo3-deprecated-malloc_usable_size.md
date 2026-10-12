# `mallinfo` (3) - glibc (mallinfo / mallinfo2 / mallopt / malloc_usable_size / malloc_info)

> Per-function page for the allocator statistics and tuning helpers (the
> VM-allocation statistics family); see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Core malloc
> lives in the strings/stdlib set (malloc-calloc-realloc-free page); this
> page is the introspection and knobs half.

| Field | Value |
|---|---|
| Header | `malloc.h` |
| Standards | SVID/XPG (`mallinfo`, `mallopt`); GNU (`mallinfo2`, `malloc_info`, `malloc_stats`, `malloc_trim`, `malloc_usable_size`) |
| Exported | `mallinfo@@GLIBC_2.2.5` (header marks it `__MALLOC_DEPRECATED`), `mallinfo2@@GLIBC_2.33` (NEWS 2.33: added "with larger field widths"), `mallopt@@GLIBC_2.2.5`, `malloc_usable_size@@GLIBC_2.2.5`, `malloc_info@@GLIBC_2.10` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe init/const:mallopt style annotations (manual marks `mallinfo2`/`mallopt` MT-Unsafe mtuinit with arena lock issues); stats read allocator state, so values can be stale under threads |
| Ledger ID | GLIBC-mallinfo (documented, grouped), GLIBC-mallinfo2, GLIBC-mallopt (documented, full), GLIBC-malloc_usable_size (documented, full), GLIBC-malloc_info (researched) |

## Declaration and gates

```c
#include <malloc.h>

struct mallinfo { int arena, ordblks, smblks, hblks, hblkhd,
                         usmblks, fsmblks, uordblks, fordblks, keepcost; };
struct mallinfo2 { size_t arena, ordblks, smblks, hblks, hblkhd,
                          usmblks, fsmblks, uordblks, fordblks, keepcost; };

struct mallinfo  mallinfo(void);    /* __MALLOC_DEPRECATED in malloc.h */
struct mallinfo2 mallinfo2(void);
int  mallopt(int param, int value);
size_t malloc_usable_size(void *ptr);
int  malloc_info(int options, FILE *fp);   /* XML dump to fp */
void malloc_stats(void);                   /* brief stderr summary */
int  malloc_trim(size_t pad);
```

## Semantics

`mallinfo`/`mallinfo2` return a snapshot of ptmalloc state: `arena`
(sbrk-allocated bytes), `hblks`/`hblkhd` (mmap count/bytes), `uordblks`/
`fordblks` (in-use/free chunk bytes), `keepcost` (releasable top chunk);
`smblks`, `fsmblks`, `usmblks` are unused or always 0 (manual, *Statistics
of Malloc*, plus `malloc.h` comments). `mallopt` tunes the allocator:
`M_TRIM_THRESHOLD`, `M_TOP_PAD`, `M_MMAP_THRESHOLD` (setting it disables
the dynamic 128 KiB threshold adaptation), `M_MMAP_MAX`, `M_PERTURB`,
`M_ARENA_TEST`, `M_ARENA_MAX`; each also has an `MALLOC_*_` environment
twin applied at startup (manual, *Malloc Tunable Parameters*). The tunable
machinery behind those variables is documented in the source tree's
`README.tunables`. `malloc_usable_size` reports the usable bytes of an
allocated chunk (header comment). `malloc_info` writes an XML description
of the allocator to a stream (man3).

## Gotchas and portability

- man3 `mallinfo.3`: deprecated "since the type used for the fields is too
  small" (32-bit `int` overflows past 2/4 GiB) and not all allocations are
  visible - prefer `malloc_info(3)`.
- `malloc_usable_size` invites overshoot bugs: writing past the requested
  size up to the usable size is legal only because glibc says so; treat the
  value as diagnostics material.
- musl 1.2.5: none of these exist except `malloc_usable_size` (musl
  `include/malloc.h` declares only it; no mallinfo/mallopt/malloc_info
  anywhere in `src/malloc/`, oldmalloc or mallocng) - a hard portability
  delta from the glibc surface.

## References

- glibc manual: `memory.texi`, nodes *Malloc Tunable Parameters*,
  *Statistics of Malloc*, *Summary of Malloc*; NEWS 2.33 (mallinfo2)
- man3: `mallinfo.3`, `mallinfo2.3`, `mallopt.3`, `malloc_info.3`,
  `malloc_usable_size.3`, `malloc_stats.3`
- headers: `/usr/include/malloc.h`; `source-cache/glibc-sparse/README.tunables`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
