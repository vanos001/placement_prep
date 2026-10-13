# `daddl` / `dsubl` / `dmull` / `ddivl` / `dsqrtl` / `dfmal` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `math.h` (declared via `bits/mathcalls-narrow.h`; no man page in the cached man-pages set) |
| Standards | TS 18661-1:2014 (manual, arith.texi lines 2318-2432) |
| Exported | `daddl`/`ddivl`/`dmull`/`dsubl@@GLIBC_2.28`, `dsqrtl`/`dfmal@@GLIBC_2.35` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety notes, arith.texi lines 2323-2327) |
| Ledger ID | GLIBC-daddl, GLIBC-ddivl, GLIBC-dfmal, GLIBC-dmull, GLIBC-dsqrtl, GLIBC-dsubl |

## Declaration and gates

```c
#include <math.h>

double daddl(long double x, long double y);
double dsubl(long double x, long double y);
double dmull(long double x, long double y);
double ddivl(long double x, long double y);
double dsqrtl(long double x);
double dfmal(long double x, long double y, long double z);
```

The `d##name##l` block sits in the same
`#if __GLIBC_USE (IEC_60559_BFP_EXT_C23)` region of
`/usr/include/math.h`: `_Mret_` = `double`, `_Marg_` = `long double`,
`__MATHCALL_NAME(name) = d ## name ## l` (lines 569-585), drawing the
six prototypes from `bits/mathcalls-narrow.h` lines 23-39. The gate is
set by `_GNU_SOURCE`, `__STDC_WANT_IEC_60559_BFP_EXT__` or C23 mode
(`bits/libc-header-start.h` lines 67-77). See
[fadd family](fadd-fsqrtl.md) for the `float`-returning counterparts.

## Semantics

Per the manual (node *Misc FP Arithmetic*, arith.texi lines 2318-2432):
`daddl` returns `x + y` rounded once to the return type of the function
without any intermediate rounding to the type of the arguments; the same
single-rounding contract holds for `dsubl` (`x - y`), `dmull` (`x * y`),
`ddivl` (`x / y`), `dsqrtl` (`sqrt(x)`) and `dfmal`
(`(x * y) + z`, with the product itself unrounded). Here the wide
computation is done in `long double` and the single rounding lands in
`double` -- the mirror image of the `f...l` names, which round into
`float`.

## Gotchas and portability

- The names read as "double result, long double arguments": prefix `d`
  selects the return type, trailing `l` the argument type.
- `dfmal` is the narrow fused multiply-add; the plain `fma` family
  (ISO C99, same argument and result type) and the TS 18661-3
  `fMfmafN` group are different ledger rows and different symbols.
- `tgmath.h` exposes generic narrowing macros under the same gate
  (`/usr/include/tgmath.h` lines 1123-1127).
- No man page exists for these names in the cached man-pages set.
- musl 1.2.5: absent from `musl include/math.h` (verified, 0 matches).

## References

- glibc manual: `arith.texi`, node *Misc FP Arithmetic* (lines 2091-2432)
- headers: `/usr/include/math.h`, `bits/mathcalls-narrow.h`,
  `bits/libc-header-start.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
