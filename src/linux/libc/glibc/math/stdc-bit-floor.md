# `stdc_bit_floor` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_bit_floor_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_bit_floor_uc, GLIBC-stdc_bit_floor_us, GLIBC-stdc_bit_floor_ui, GLIBC-stdc_bit_floor_ul, GLIBC-stdc_bit_floor_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned char      stdc_bit_floor_uc (unsigned char x);
unsigned short     stdc_bit_floor_us (unsigned short x);
unsigned int       stdc_bit_floor_ui (unsigned int x);
unsigned long int  stdc_bit_floor_ul (unsigned long int x);
unsigned long long int stdc_bit_floor_ull (unsigned long long int x);
stdc_bit_floor (x);  /* type-generic macro, returns typeof(x) */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 730-741 of
`/usr/include/stdbit.h`. The generic macro (lines 742-746) expands to
`__builtin_stdc_bit_floor` when present, otherwise to
`(__typeof (x)) stdc_bit_floor_ull (x)`. With GCC >= 3.4 the
type-specific names are redefined as `__always_inline` macros over
`__bf*_inline`, each `x == 0 ? 0 : 1 << (bit_width - 1)` with explicit
casts back to the operand type (lines 748-784).

## Semantics

The functions return the largest integer power of two that is less than
or equal to `x`; if `x` is zero they return zero (manual `stdbit.texi`,
`stdc_bit_floor` node). Unlike the counting families this group returns
the argument's own unsigned type (`unsigned char` through
`unsigned long long int`), not `unsigned int`; all are
`__THROW __attribute_const__` (pure, never set errno). The generic
macro accepts unsigned operands of width 8, 16, 32 or 64, or with
GCC 14.1+ builtins also `unsigned __int128` and `unsigned _BitInt(n)`
(manual chapter intro).

## Gotchas and portability

- Return type follows the operand: `stdc_bit_floor(300u)` is 256, but
  the `_uc` variant saturates inside `unsigned char` -- values above
  255 cannot be expressed there, so prefer a width that fits.
- Zero maps to zero, not to 1; the "floor of the floor" is not the
  identity at 0 and this is the documented C23 behavior.
- The header keeps the intermediate shift in the operand width
  (`__bf8_inline`, lines 768-773) and applies the `__pacify_uint8`
  casts (lines 44-53) to keep `-Wconversion` quiet.
- Signed operands are outside the C23 contract. musl 1.2.5 ships no
  `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 44-53, 730-784
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
