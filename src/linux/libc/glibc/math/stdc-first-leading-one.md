# `stdc_first_leading_one` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_first_leading_one_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_first_leading_one_uc, GLIBC-stdc_first_leading_one_us, GLIBC-stdc_first_leading_one_ui, GLIBC-stdc_first_leading_one_ul, GLIBC-stdc_first_leading_one_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_first_leading_one_uc (unsigned char x);
unsigned int stdc_first_leading_one_us (unsigned short x);
unsigned int stdc_first_leading_one_ui (unsigned int x);
unsigned int stdc_first_leading_one_ul (unsigned long int x);
unsigned int stdc_first_leading_one_ull (unsigned long long int x);
unsigned int stdc_first_leading_one (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 337-348 of
`/usr/include/stdbit.h`. The generic macro (lines 349-357) expands to
`__builtin_stdc_first_leading_one` when present, otherwise to a
`sizeof`-switch dispatch. With GCC >= 3.4 the type-specific names are
redefined as `__always_inline` macros over `__flo*_inline`, each of
which is `x == 0 ? 0 : 1 + __clz*_inline (x)` (lines 359-393).

## Semantics

The functions return the position of the most significant one bit in
`x`, counting from the most significant bit of the argument type as 1;
they return 0 if there is no one bit in `x` (manual `stdbit.texi`,
`stdc_first_leading_one` node). All variants return `unsigned int`; all
are `__THROW __attribute_const__` (pure, never set errno). The generic
macro accepts unsigned operands of width 8, 16, 32 or 64, or with
GCC 14.1+ builtins also `unsigned __int128` and `unsigned _BitInt(n)`
(manual chapter intro).

## Gotchas and portability

- Positions are 1-based and 0 is the "none" sentinel, so a zero operand
  and "no bit found" share the value 0; check the operand separately if
  the distinction matters.
- Relation to other families: for nonzero `x`,
  `stdc_first_leading_one(x) == stdc_bit_width(x)`; both are
  `1 + clz` in the inline layer (`__flo64_inline`, lines 361-364).
- Using the result directly as a shift count is wrong by one; convert
  to a 0-based index first.
- Signed operands are outside the C23 contract; the fallback macro does
  not diagnose. musl 1.2.5 ships no `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 337-393
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
