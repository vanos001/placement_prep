# `stdc_first_trailing_zero` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_first_trailing_zero_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_first_trailing_zero_uc, GLIBC-stdc_first_trailing_zero_us, GLIBC-stdc_first_trailing_zero_ui, GLIBC-stdc_first_trailing_zero_ul, GLIBC-stdc_first_trailing_zero_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_first_trailing_zero_uc (unsigned char x);
unsigned int stdc_first_trailing_zero_us (unsigned short x);
unsigned int stdc_first_trailing_zero_ui (unsigned int x);
unsigned int stdc_first_trailing_zero_ul (unsigned long int x);
unsigned int stdc_first_trailing_zero_ull (unsigned long long int x);
unsigned int stdc_first_trailing_zero (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20). The
five out-of-line declarations sit at lines 395-406 of
`/usr/include/stdbit.h`. The generic macro (lines 407-415) expands to
`__builtin_stdc_first_trailing_zero` when present, otherwise to a
`sizeof`-switch dispatch. With GCC >= 3.4 the type-specific names are
redefined as `__always_inline` macros over `__ftz*_inline`, each of
which is `x == all-ones ? 0 : 1 + __cto*_inline (x)` (lines 417-451).

## Semantics

The functions return the position of the least significant zero bit in
`x`, counting from the least significant bit of the argument type as 1;
they return 0 if there is no zero bit in `x` (manual `stdbit.texi`,
`stdc_first_trailing_zero` node). All variants return `unsigned int`;
all are `__THROW __attribute_const__` (pure, never set errno). The
generic macro accepts unsigned operands of width 8, 16, 32 or 64, or
with GCC 14.1+ builtins also `unsigned __int128` and
`unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- Positions are 1-based, unlike `__builtin_ctz` (0-based); the
  all-ones operand is the only input that yields the 0 sentinel
  (`__ftz64_inline`, lines 419-422).
- The inline identity is
  `x == all-ones ? 0 : 1 + stdc_trailing_ones(x)`; the complement trick
  means the narrow shims re-apply the `__pacify_uint8/16` casts before
  complementing (see `__cto8_inline`, lines 262-266).
- For bitmap allocators this is the "find first clear bit" primitive;
  remember the value is an ordinal, not a mask.
- Signed operands are outside the C23 contract; the fallback macro does
  not diagnose. musl 1.2.5 ships no `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 395-451, 262-266
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
