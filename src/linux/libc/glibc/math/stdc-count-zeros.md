# `stdc_count_zeros` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_count_zeros_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_count_zeros_uc, GLIBC-stdc_count_zeros_us, GLIBC-stdc_count_zeros_ui, GLIBC-stdc_count_zeros_ul, GLIBC-stdc_count_zeros_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_count_zeros_uc (unsigned char x);
unsigned int stdc_count_zeros_us (unsigned short x);
unsigned int stdc_count_zeros_ui (unsigned int x);
unsigned int stdc_count_zeros_ul (unsigned long int x);
unsigned int stdc_count_zeros_ull (unsigned long long int x);
unsigned int stdc_count_zeros (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 511-522 of
`/usr/include/stdbit.h`. The generic macro (lines 523-529) expands to
`__builtin_stdc_count_zeros` when present, otherwise it widens to
`_ull` and subtracts the unused high bytes. With GCC >= 3.4 the
type-specific names are redefined as `__always_inline` macros over
`__cz*_inline`, each `width - __builtin_popcount` (lines 531-565).

## Semantics

The functions count the number of zero bits in `x` (manual
`stdbit.texi`, `stdc_count_zeros` node). All variants return
`unsigned int`; all are `__THROW __attribute_const__` (pure, never set
errno). There is no special case at zero: a zero operand returns the
full type width, an all-ones operand returns 0. The generic macro
accepts unsigned operands of width 8, 16, 32 or 64, or with GCC 14.1+
builtins also `unsigned __int128` and `unsigned _BitInt(n)` (manual
chapter intro).

## Gotchas and portability

- Counting zeros of the operand equals counting ones of the complement,
  but the width matters: `__cz8_inline` computes `8 - popcount(x)`
  (lines 551-553), so the answer is always relative to the argument
  type, not the promoted type.
- The `ul` inline again branches on `__WORDSIZE` (lines 559-563); on
  64-bit targets `unsigned long` and `unsigned long long` share the
  64-bit shim.
- Do not widen by hand before calling: `stdc_count_zeros((unsigned
  long long) x)` counts the newly added high zeros too and differs from
  the `_uc` result.
- Signed operands are outside the C23 contract; the fallback macro does
  not diagnose. musl 1.2.5 ships no `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 511-565
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
