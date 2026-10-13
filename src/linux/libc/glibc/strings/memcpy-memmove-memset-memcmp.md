# `memcpy` / `memmove` / `memset` / `memcmp` / `explicit_bzero` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (`explicit_bzero`: `string.h` under `__USE_MISC`, man pages also list `strings.h`) |
| Standards | ISO C / POSIX.1-2001 (`memcpy`, `memmove`, `memset`, `memcmp`); BSD/GNU (`explicit_bzero`) |
| Exported | `memcpy@@GLIBC_2.14` plus compat `memcpy@GLIBC_2.2.5`, `memmove@@GLIBC_2.2.5`, `memset@@GLIBC_2.2.5`, `memcmp@@GLIBC_2.2.5`, `explicit_bzero@@GLIBC_2.25`, fortified `__memcpy_chk@@GLIBC_2.3.4` etc. (nm, host glibc 2.41) |
| Thread-safety | MT-Safe all (`memcpy(3)`, `memmove(3)`, `memset(3)`, `memcmp(3)`, `bzero(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-memcpy, GLIBC-memmove, GLIBC-memset, GLIBC-memcmp, GLIBC-explicit_bzero |

## Declaration and gates

```c
#include <string.h>

void *memcpy(void *restrict dest, const void *restrict src, size_t n);
void *memmove(void *dest, const void *src, size_t n);
void *memset(void *s, int c, size_t n);
int   memcmp(const void *s1, const void *s2, size_t n);

void explicit_bzero(void *s, size_t n);   /* __USE_MISC; glibc 2.25 */
```

`explicit_bzero` sits in the `__USE_MISC` block of `string.h` next to
`#include <strings.h>` (`/usr/include/string.h` lines 461-474). The header
also declares the compiler-only helper `__memcmpeq` (same contract as
`memcmp`, return value only guaranteed nonzero, lines 67-81).

## Semantics

`memcpy` copies `n` bytes from `src` to `dest` and returns `dest`; the areas
must not overlap (`memcpy(3)`). `memmove` copies as though through a
temporary array that overlaps neither argument, so overlap is safe
(`memmove(3)`). `memset` fills `n` bytes with the byte value of `c` and
returns `s` (`memset(3)`). `memcmp` compares `n` bytes as `unsigned char`
and returns sign of the first difference; zero when `n` is zero
(`memcmp(3)`, manual *String/Array Comparison*). `explicit_bzero` performs
`bzero` semantics with a guarantee the compiler will not elide the write
(`bzero(3)`, manual *Erasing Sensitive Data*).

## Gotchas and portability

- Overlapping `memcpy` is undefined behavior, and glibc made that bite:
  a glibc 2.13 optimization on x86-64 reversed the copy direction, exposing
  long-latent application bugs; glibc 2.14 added a versioned symbol so old
  binaries keep a `memcpy` aliased to `memmove` (`memcpy(3)` NOTES). The
  version split is visible in nm output: `memcpy@@GLIBC_2.14` default,
  `memcpy@GLIBC_2.2.5` compat.
- `memset` via fortify transposition check: `bits/string_fortified.h`
  deliberately refers to nonexistent functions when the value/size arguments
  look transposed, to break the build for `memset(size, 0, n)` mistakes.
- Dead-store elimination: `memset` on an about-to-die object may be removed;
  `explicit_bzero` never is (`bzero(3)` NOTES, manual *Erasing Sensitive
  Data*). Even it does not scrub register copies and can momentarily force
  data from register to RAM; `volatile` makes this worse, not better.
- `memcmp` is not constant-time; `memcmp(3)` NOTES warns against comparing
  cryptographic secrets with it.
- `memcmp` over structs with padding holes compares indeterminate bytes;
  the manual recommends member-wise comparison (*String/Array Comparison*).
- musl 1.2.5: same ISO semantics; `explicit_bzero` present
  (`musl src/string/{memcpy,memmove,memset,memcmp,explicit_bzero}.c`).

## References

- glibc manual: `string.texi`, nodes *Copying Strings and Arrays*,
  *String/Array Comparison*, *Erasing Sensitive Data*
- man3: `memcpy(3)`, `memmove(3)`, `memset(3)`, `memcmp(3)`, `bzero(3)`
  (covers `explicit_bzero`)
- headers: `/usr/include/string.h`, `bits/string_fortified.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
