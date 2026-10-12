# `stdc_trailing_ones` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_trailing_ones_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_trailing_ones_uc, GLIBC-stdc_trailing_ones_us, GLIBC-stdc_trailing_ones_ui, GLIBC-stdc_trailing_ones_ul, GLIBC-stdc_trailing_ones_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_trailing_ones_uc (unsigned char x);
unsigned int stdc_trailing_ones_us (unsigned short x);
unsigned int stdc_trailing_ones_ui (unsigned int x);
unsigned int stdc_trailing_ones_ul (unsigned long int x);
unsigned int stdc_trailing_ones_ull (unsigned long long int x);
unsigned int stdc_trailing_ones (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 225-236 of
`/usr/include/stdbit.h`. The generic macro (lines 237-241) expands to
`__builtin_stdc_trailing_ones` when present, otherwise it simply calls
the `_ull` variant (trailing bits need no widening). With GCC >= 3.4
the type-specific names are redefined as `__always_inline` macros over
`__cto*_inline`, each `__ctz*_inline` applied to the bitwise complement
(lines 243-277).

## Semantics

The functions count the number of trailing (least significant) one bits
in `x`, starting from the least significant bit of the argument type
(manual `stdbit.texi`, `stdc_trailing_ones` node). All variants return
`unsigned int`; all are `__THROW __attribute_const__` (pure, never set
errno). No special case at zero: a zero operand returns 0, an all-ones
operand returns the type width. The generic macro accepts unsigned
operands of width 8, 16, 32 or 64, or with GCC 14.1+ builtins also
`unsigned __int128` and `unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- Complement symmetry: `stdc_trailing_ones(x)` equals
  `stdc_trailing_zeros(~x)`; the inline layer implements it exactly so
  (`__cto64_inline` computes `__ctz64_inline (~__x)`, lines 245-248).
- The narrow shims must mask the complement back to the operand width
  before counting; the header uses the `__pacify_uint8/16` casts
  (lines 44-53) to silence `-Wconversion` on older compilers
  (`__cto8_inline`, lines 262-266).
- Signed operands are outside the C23 contract and the fallback macro
  does not diagnose.
- musl 1.2.5 ships no `stdbit.h` (absence verified in `musl/include/`);
  this family plus its thirteen siblings exist only in glibc 2.39+ and
  C23 toolchains.

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 44-53, 225-277
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
