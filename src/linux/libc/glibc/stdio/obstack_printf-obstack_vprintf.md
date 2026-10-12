# `obstack_printf` / `obstack_vprintf` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdio.h` (under `__USE_GNU`; obstack allocation functions themselves live in `obstack.h` and are documented with the Obstacks chapter) |
| Standards | GNU only |
| Exported | `obstack_printf@@GLIBC_2.2.5`, `obstack_vprintf@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe race:obstack (manual @safety annotations: the obstack is not protected, callers must not share it between threads) |
| Ledger ID | GLIBC-obstack_printf, GLIBC-obstack_vprintf |

## Declaration and gates

```c
#include <stdio.h>

int obstack_printf(struct obstack *restrict obstack,
                   const char *restrict format, ...);
int obstack_vprintf(struct obstack *restrict obstack,
                    const char *restrict format, va_list args);
```

Both are in the `#ifdef __USE_GNU` block of `stdio.h` (lines 913-923),
right after a forward declaration of `struct obstack` so the header
does not need `<obstack.h>`.

## Semantics

They are `asprintf`-style formatted output into an obstack: the
converted characters are appended to the current growing object of
`obstack`, and the return value is the number of characters generated,
or negative on allocation failure (`asprintf` semantics; manual node
*Dynamically Allocating Formatted Output*). The data becomes a usable
object only after the caller grows/finishes it, e.g. with
`obstack_finish` (manual). `obstack_vprintf` is the `va_list` twin for
writing variadic wrappers.

## Gotchas and portability

- Nothing is null-terminated until the object is finished; take the
  pointer from `obstack_finish`, not from inside the obstack.
- The functions only allocate from the obstack; the surrounding
  obstack lifecycle (`obstack_init`, `obstack_free`) is documented with
  the Obstacks chapter -- the growth/finish calls are the ones this
  pair interleaves with.
- glibc-only: musl 1.2.5 has no obstack support at all (verified: no
  `obstack*` header or source in the musl tree), so these calls have no
  drop-in there; `open_memstream` is the usual substitute.
- Because they write into the obstack's current object, cancellation or
  allocation failure can leave a partially grown object behind.

## References

- glibc manual: `stdio.texi`, nodes *Dynamically Allocating Formatted
  Output*, *Variable Arguments Output*; `memory.texi` Obstacks chapter
- headers: `/usr/include/stdio.h`, `/usr/include/obstack.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
