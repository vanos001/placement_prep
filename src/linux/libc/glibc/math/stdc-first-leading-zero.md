# `stdc_first_leading_zero` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_first_leading_zero_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_first_leading_zero_uc, GLIBC-stdc_first_leading_zero_us, GLIBC-stdc_first_leading_zero_ui, GLIBC-stdc_first_leading_zero_ul, GLIBC-stdc_first_leading_zero_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_first_leading_zero_uc (unsigned char x);
unsigned int stdc_first_leading_zero_us (unsigned short x);
unsigned int stdc_first_leading_zero_ui (unsigned int x);
unsigned int stdc_first_leading_zero_ul (unsigned long int x);
unsigned int stdc_first_leading_zero_ull (unsigned long long int x);
unsigned int stdc_first_leading_zero (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 279-290 of
`/usr/include/stdbit.h`. The generic macro (lines 291-299) expands to
`__builtin_stdc_first_leading_zero` when present, otherwise to a
`sizeof`-switch dispatch. With GCC >= 3.4 the type-specific names are
redefined as `__always_inline` macros over `__flz*_inline`, each of
which is `1 + __clo*_inline (x)` with an all-ones short-circuit
(lines 301-335).

## Semantics

The functions return the position of the most significant zero bit in
`x`, counting from the most significant bit of the argument type as 1;
they return 0 if there is no zero bit in `x` (manual `stdbit.texi`,
`stdc_first_leading_zero` node). All variants return `unsigned int`;
all are `__THROW __attribute_const__` (pure, never set errno). The
generic macro accepts unsigned operands of width 8, 16, 32 or 64, or
with GCC 14.1+ builtins also `unsigned __int128` and
`unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- Positions are 1-based, unlike `__builtin_clz` (0-based); porting code
  must adjust the index before using it as a shift amount.
- The no-such-bit case returns 0, which collides with the 1-based
  "first position" numbering: 0 is a sentinel, not a position.
- The inline identity is
  `x == all-ones ? 0 : 1 + stdc_leading_ones(x)` (`__flz64_inline`,
  lines 303-306), so an all-ones operand is the only way to get 0.
- Signed operands are outside the C23 contract; the fallback macro does
  not diagnose. musl 1.2.5 ships no `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 279-335
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
