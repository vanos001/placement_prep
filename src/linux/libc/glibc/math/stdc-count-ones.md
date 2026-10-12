# `stdc_count_ones` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_count_ones_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_count_ones_uc, GLIBC-stdc_count_ones_us, GLIBC-stdc_count_ones_ui, GLIBC-stdc_count_ones_ul, GLIBC-stdc_count_ones_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_count_ones_uc (unsigned char x);
unsigned int stdc_count_ones_us (unsigned short x);
unsigned int stdc_count_ones_ui (unsigned int x);
unsigned int stdc_count_ones_ul (unsigned long int x);
unsigned int stdc_count_ones_ull (unsigned long long int x);
unsigned int stdc_count_ones (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 567-578 of
`/usr/include/stdbit.h`. The generic macro (lines 579-583) expands to
`__builtin_stdc_count_ones` when present, otherwise it simply calls the
`_ull` variant (population count needs no width adjustment). With
GCC >= 3.4 the type-specific names are redefined as `__always_inline`
macros over `__co*_inline`, each a direct `__builtin_popcount` /
`__builtin_popcountll` call (lines 585-619).

## Semantics

The functions count the number of one bits in `x` (manual
`stdbit.texi`, `stdc_count_ones` node). All variants return
`unsigned int`; all are `__THROW __attribute_const__` (pure, never set
errno). There is no special case at zero: a zero operand returns 0, an
all-ones operand returns the type width. The generic macro accepts
unsigned operands of width 8, 16, 32 or 64, or with GCC 14.1+ builtins
also `unsigned __int128` and `unsigned _BitInt(n)` (manual chapter
intro).

## Gotchas and portability

- This is the C23 name for popcount; the parity with
  `stdc_count_zeros` is fixed by construction:
  `stdc_count_zeros(x) == width - stdc_count_ones(x)` (header
  `__cz64_inline` computes `64 - popcount`, lines 533-536).
- On x86-64 the popcount builtin may lower to the `popcnt` instruction
  only when the compiler enables it; otherwise a table or SWAR sequence
  is emitted. The functions stay pure either way.
- The odd/even check `stdc_count_ones(x) & 1` is a parity test; do not
  confuse it with `stdc_has_single_bit`.
- Signed operands are outside the C23 contract; the fallback macro does
  not diagnose. musl 1.2.5 ships no `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 567-619, 533-536
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
