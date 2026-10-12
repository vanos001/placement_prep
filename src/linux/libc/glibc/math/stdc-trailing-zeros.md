# `stdc_trailing_zeros` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_trailing_zeros_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_trailing_zeros_uc, GLIBC-stdc_trailing_zeros_us, GLIBC-stdc_trailing_zeros_ui, GLIBC-stdc_trailing_zeros_ul, GLIBC-stdc_trailing_zeros_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_trailing_zeros_uc (unsigned char x);
unsigned int stdc_trailing_zeros_us (unsigned short x);
unsigned int stdc_trailing_zeros_ui (unsigned int x);
unsigned int stdc_trailing_zeros_ul (unsigned long int x);
unsigned int stdc_trailing_zeros_ull (unsigned long long int x);
unsigned int stdc_trailing_zeros (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 167-178 of
`/usr/include/stdbit.h`. The generic macro (lines 179-187) expands to
`__builtin_stdc_trailing_zeros` when present, otherwise to a
`sizeof`-switch that dispatches to the matching `_uc/_us/_ui/_ull`
function. With GCC >= 3.4 the type-specific names are redefined as
`__always_inline` macros over `__ctz8/16/32/64_inline` (lines 189-223).

## Semantics

The functions count the number of trailing (least significant) zero
bits in `x`, starting from the least significant bit of the argument
type; if `x` is zero they return the width of the type in bits (manual
`stdbit.texi`, `stdc_trailing_zeros` node). All variants return
`unsigned int`; all are `__THROW __attribute_const__` (pure, never set
errno). The generic macro accepts unsigned operands of width 8, 16, 32
or 64, or with GCC 14.1+ builtins also `unsigned __int128` and
`unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- `stdc_trailing_zeros(0)` is the full type width, unlike
  `__builtin_ctz` which is undefined for 0; each inline shim handles it
  explicitly (`__ctz64_inline` returns 64 for 0, line 193).
- The dispatch-by-`sizeof` fallback rounds any unusual type down to the
  matching width function; operand types other than the five unsigned
  integer types of width 8/16/32/64 are outside the C23 contract.
- Because the trailing end needs no widening, this family's inline
  shims are the only ones where `_uc` through `_ull` all keep an
  explicit zero check rather than reusing a wider function.
- musl 1.2.5 ships no `stdbit.h` (absence verified in `musl/include/`);
  pair with a feature check before using in portable code.

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 167-223
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
