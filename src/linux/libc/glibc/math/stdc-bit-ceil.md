# `stdc_bit_ceil` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_bit_ceil_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_bit_ceil_uc, GLIBC-stdc_bit_ceil_us, GLIBC-stdc_bit_ceil_ui, GLIBC-stdc_bit_ceil_ul, GLIBC-stdc_bit_ceil_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned char      stdc_bit_ceil_uc (unsigned char x);
unsigned short     stdc_bit_ceil_us (unsigned short x);
unsigned int       stdc_bit_ceil_ui (unsigned int x);
unsigned long int  stdc_bit_ceil_ul (unsigned long int x);
unsigned long long int stdc_bit_ceil_ull (unsigned long long int x);
stdc_bit_ceil (x);  /* type-generic macro, returns typeof(x) */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 786-797 of
`/usr/include/stdbit.h`. The generic macro (lines 798-802) expands to
`__builtin_stdc_bit_ceil` when present, otherwise to
`(__typeof (x)) stdc_bit_ceil_ull (x)`. With GCC >= 3.4 the
type-specific names are redefined as `__always_inline` macros over
`__bc*_inline`, each `x <= 1 ? 1 : 2 << (bit_width (x - 1) - 1)`
(lines 804-844).

## Semantics

The functions return the smallest integer power of two that is greater
than or equal to `x`; if that cannot be represented in the return type
they return zero (manual `stdbit.texi`, `stdc_bit_ceil` node). The
type-specific group returns the argument's own unsigned type, not
`unsigned int`; all are `__THROW __attribute_const__` (pure, never set
errno). Zero and one both round up to 1 (header `__bc*_inline`
short-circuits `x <= 1`). The generic macro accepts unsigned operands
of width 8, 16, 32 or 64, or with GCC 14.1+ builtins also
`unsigned __int128` and `unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- Overflow is a value, not UB: `stdc_bit_ceil_uc(200)` cannot express
  256 and returns 0 -- callers must treat 0 as "did not fit" (manual
  semantics).
- Classic allocation rounding primitive: `stdc_bit_ceil(n)` gives the
  next power-of-two size, but the `unsigned char`/`unsigned short`
  variants saturate quickly; size buffers in `size_t`/`ull`.
- The `x - 1` inside the shim means `x == 0` must never reach the
  shift path; the `x <= 1` guard (lines 806-809) exists for that.
- Signed operands are outside the C23 contract. musl 1.2.5 ships no
  `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 786-844
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
