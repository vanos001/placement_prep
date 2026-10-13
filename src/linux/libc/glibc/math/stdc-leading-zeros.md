# `stdc_leading_zeros` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_leading_zeros_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_leading_zeros_uc, GLIBC-stdc_leading_zeros_us, GLIBC-stdc_leading_zeros_ui, GLIBC-stdc_leading_zeros_ul, GLIBC-stdc_leading_zeros_ull |

## Declaration and gates

```c
#include <stdbit.h>

unsigned int stdc_leading_zeros_uc (unsigned char x);
unsigned int stdc_leading_zeros_us (unsigned short x);
unsigned int stdc_leading_zeros_ui (unsigned int x);
unsigned int stdc_leading_zeros_ul (unsigned long int x);
unsigned int stdc_leading_zeros_ull (unsigned long long int x);
unsigned int stdc_leading_zeros (x);  /* type-generic macro */
```

No feature-test gate: `stdbit.h` is the C23 7.18 header, guarded only by
its own include guard (lines 19-20), and pulls in `stdbool.h` and
`size_t` (lines 32-34). The five out-of-line declarations sit at lines
55-66. The generic macro (lines 67-73) expands to
`__builtin_stdc_leading_zeros` when the compiler has it; otherwise it
widens the operand to `unsigned long long` and subtracts the unused high
bytes. When GCC >= 3.4 builtins exist the header additionally redefines
the five type-specific names as `__always_inline` macros over
`__clz8/16/32/64_inline` (lines 75-109), shadowing the extern functions.

## Semantics

The functions count the number of leading (most significant) zero bits
in `x`, starting from the most significant bit of the argument type; if
`x` is zero they return the width of the type in bits (manual
`stdbit.texi`, `stdc_leading_zeros` node). Every variant returns
`unsigned int` regardless of operand width, and all are
`__THROW __attribute_const__` (pure, never set errno). The generic macro
accepts any unsigned operand of width 8, 16, 32 or 64; with GCC 14.1+
`__builtin_stdc_leading_zeros` it also accepts `unsigned __int128` and
`unsigned _BitInt(n)` where the target supports them (manual chapter
intro).

## Gotchas and portability

- `stdc_leading_zeros(0)` is the full type width, unlike
  `__builtin_clz` which is undefined for 0; the inline shims keep the
  guarantee (`__clz64_inline` returns 64 for 0, line 79).
- Signed operands are outside the C23 contract and the fallback macro
  does not diagnose; a negative signed value converts to a huge unsigned
  value and returns 0.
- The type-specific names become macros on GCC builds, so the exported
  out-of-line symbols are normally only called by non-GCC or pre-3.4
  compilers; the 70 `GLIBC_2.39` copies exist for that case.
- musl 1.2.5 ships no `stdbit.h` at all (absence verified in
  `musl/include/`), so this interface is a portability cliff between the
  libcs.

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 32-36, 55-109
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
