# `stdc_bit_width` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_bit_width_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_bit_width_uc, GLIBC-stdc_bit_width_us, GLIBC-stdc_bit_width_ui, GLIBC-stdc_bit_width_ul, GLIBC-stdc_bit_width_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_bit_width_uc (unsigned char x);
unsigned int stdc_bit_width_us (unsigned short x);
unsigned int stdc_bit_width_ui (unsigned int x);
unsigned int stdc_bit_width_ul (unsigned long int x);
unsigned int stdc_bit_width_ull (unsigned long long int x);
unsigned int stdc_bit_width (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 676-687 of
`/usr/include/stdbit.h`. The generic macro (lines 688-692) expands to
`__builtin_stdc_bit_width` when present, otherwise it simply calls the
`_ull` variant. With GCC >= 3.4 the type-specific names are redefined
as `__always_inline` macros over `__bw*_inline`, each
`width - __clz*_inline (x)` (lines 694-728).

## Semantics

The functions return the minimum number of bits needed to store `x`,
not counting leading zero bits; if `x` is zero they return zero
(manual `stdbit.texi`, `stdc_bit_width` node). All variants return
`unsigned int`; all are `__THROW __attribute_const__` (pure, never set
errno). Equivalently the result is the position of the most significant
set bit counted from 1, i.e. `64 - clz` for the 64-bit shim
(`__bw64_inline`, lines 695-699). The generic macro accepts unsigned
operands of width 8, 16, 32 or 64, or with GCC 14.1+ builtins also
`unsigned __int128` and `unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- Zero returns 0, so the result doubles as a "is nonzero" test; but
  converting to a shift count needs care because 0 is not a valid
  position for `1 << width`.
- `stdc_bit_width(x)` equals `stdc_first_leading_one(x)` for nonzero
  `x` (both are `1 + clz` in the inline layer) and differs only at 0,
  where both return 0.
- It is the inverse of `stdc_bit_floor`: `bit_floor` returns
  `1 << (bit_width - 1)` for nonzero `x` (header `__bf64_inline`,
  lines 749-753).
- Signed operands are outside the C23 contract; the fallback macro does
  not diagnose. musl 1.2.5 ships no `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 676-728
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
