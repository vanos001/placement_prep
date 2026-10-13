# `stdc_leading_ones` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_leading_ones_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_leading_ones_uc, GLIBC-stdc_leading_ones_us, GLIBC-stdc_leading_ones_ui, GLIBC-stdc_leading_ones_ul, GLIBC-stdc_leading_ones_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_leading_ones_uc (unsigned char x);
unsigned int stdc_leading_ones_us (unsigned short x);
unsigned int stdc_leading_ones_ui (unsigned int x);
unsigned int stdc_leading_ones_ul (unsigned long int x);
unsigned int stdc_leading_ones_ull (unsigned long long int x);
unsigned int stdc_leading_ones (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header, include guard at lines 19-20 of
`/usr/include/stdbit.h`. The five out-of-line declarations sit at lines
111-122. The generic macro (lines 123-129) uses
`__builtin_stdc_leading_ones` when available; the fallback shifts the
operand left by the unused bytes so the sign-extension-free count lands
in a `ull` leading-ones call. With GCC >= 3.4 the type-specific names
are redefined as `__always_inline` macros over `__clo*_inline`, each of
which is just `__clz*_inline` applied to the bitwise complement
(lines 131-165).

## Semantics

The functions count the number of leading (most significant) one bits
in `x`, starting from the most significant bit of the argument type
(manual `stdbit.texi`, `stdc_leading_ones` node). All variants return
`unsigned int` whatever the operand width; all are
`__THROW __attribute_const__` (pure, never set errno). There is no
zero special case: a zero operand simply returns 0, an all-ones operand
returns the type width. The generic macro accepts unsigned operands of
width 8, 16, 32 or 64, or with GCC 14.1+ builtins also
`unsigned __int128` and `unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- Complement symmetry: `stdc_leading_ones(x)` equals
  `stdc_leading_zeros(~x)`; the header literally implements it that way
  (`__clo64_inline` computes `__clz64_inline (~__x)`, lines 133-136).
- Signed operands are outside the C23 contract and the fallback macro
  does not diagnose.
- The `ul` inline selects `__clo64_inline` only when `__WORDSIZE == 64`;
  on 32-bit targets `unsigned long` is 32 bits and the 32-bit shim is
  used (lines 159-163).
- musl 1.2.5 ships no `stdbit.h` (absence verified in `musl/include/`);
  C23 bit utilities must be hand-rolled there.

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 111-165
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
