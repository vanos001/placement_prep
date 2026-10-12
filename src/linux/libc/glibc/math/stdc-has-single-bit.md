# `stdc_has_single_bit` (3) - glibc

> Split from the glibc *Bit Manipulation* chapter (`stdbit.h`) into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdbit.h` (ISO C23 7.18, `/usr/include/stdbit.h`; `__STDC_VERSION_STDBIT_H__` `202311L` at line 36) |
| Standards | ISO C23 (7.18); out-of-line symbols since glibc 2.39 |
| Exported | `stdc_has_single_bit_uc/us/ui/ul/ull` all `@@GLIBC_2.39` (nm -D libc.so.6, host glibc 2.41); the unsuffixed generic name is a header macro, not a symbol |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual `stdbit.texi` safety annotation; no man3 page exists for stdbit) |
| Ledger ID | GLIBC-stdc_has_single_bit_uc, GLIBC-stdc_has_single_bit_us, GLIBC-stdc_has_single_bit_ui, GLIBC-stdc_has_single_bit_ul, GLIBC-stdc_has_single_bit_ull |

## Declaration and gates

```c
#include <stdbit.h>

bool stdc_has_single_bit_uc (unsigned char x);
bool stdc_has_single_bit_us (unsigned short x);
bool stdc_has_single_bit_ui (unsigned int x);
bool stdc_has_single_bit_ul (unsigned long int x);
bool stdc_has_single_bit_ull (unsigned long long int x);
bool stdc_has_single_bit (x);  /* type-generic macro */
```

No feature-test gate: C23 7.18 header (include guard lines 19-20), with
`stdbool.h` included so `bool` is `true`/`false` (lines 27-32). The
five out-of-line declarations sit at lines 621-632 of
`/usr/include/stdbit.h`. The generic macro (lines 633-640) expands to
`__builtin_stdc_has_single_bit` when present, otherwise to a
`ui`/`ull` width dispatch. Unlike the other families, the
type-specific names are redefined as inline macros unconditionally
(no compiler-version `#if`), over the `(__x ^ (__x - 1)) > __x - 1`
test (lines 642-674).

## Semantics

The functions return whether `x` has exactly one bit set to one
(manual `stdbit.texi`, `stdc_has_single_bit` node). This is the only
stdbit family returning `_Bool` rather than `unsigned int`; all are
`__THROW __attribute_const__` (pure, never set errno). A zero operand
returns false. The generic macro accepts unsigned operands of width 8,
16, 32 or 64, or with GCC 14.1+ builtins also `unsigned __int128` and
`unsigned _BitInt(n)` (manual chapter intro).

## Gotchas and portability

- This is the power-of-two test, but only for nonzero values: the
  header trick `(x ^ (x - 1)) > x - 1` (line 645) is false for 0, so no
  separate zero check is needed.
- Do not replace it with `(x & -x) == x` without also excluding 0 --
  that idiom reports true for 0; the C23 function does not.
- Return type is `bool`, so implicit conversions to `int` lose the
  "one or zero" clarity; comparisons should treat it as truth value.
- Signed operands are outside the C23 contract; the fallback macro does
  not diagnose. musl 1.2.5 ships no `stdbit.h` (absence verified).

## References

- glibc manual: `stdbit.texi`, chapter *Bit Manipulation*
- header: `/usr/include/stdbit.h` lines 19-20, 27-32, 621-674
- symbols: `nm -D --with-symbol-versions libc.so.6` (70 `stdc_*`, all GLIBC_2.39)
- musl 1.2.5: no `stdbit.h` in `include/` (absence verified)
