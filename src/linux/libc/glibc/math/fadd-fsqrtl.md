# `fadd` / `faddl` / `fsub` / `fsubl` / `fmul` / `fmull` / `fdiv` / `fdivl` / `fsqrt` / `fsqrtl` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `math.h` (declared via `bits/mathcalls-narrow.h`; no man page in the cached man-pages set) |
| Standards | TS 18661-1:2014 (manual, arith.texi lines 2318-2410) |
| Exported | `fadd`/`faddl`/`fsub`/`fsubl`/`fmul`/`fmull`/`fdiv`/`fdivl@@GLIBC_2.28`, `fsqrt`/`fsqrtl@@GLIBC_2.35` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (manual safety notes, arith.texi lines 2323-2327) |
| Ledger ID | GLIBC-fadd, GLIBC-faddl, GLIBC-fsub, GLIBC-fsubl, GLIBC-fmul, GLIBC-fmull, GLIBC-fdiv, GLIBC-fdivl, GLIBC-fsqrt, GLIBC-fsqrtl |

## Declaration and gates

```c
#include <math.h>

float fadd(double x, double y);            /* (double, double) -> float */
float faddl(long double x, long double y);
float fsub(double x, double y);
float fsubl(long double x, long double y);
float fmul(double x, double y);
float fmull(long double x, long double y);
float fdiv(double x, double y);
float fdivl(long double x, long double y);
float fsqrt(double x);
float fsqrtl(long double x);
```

All are inside `#if __GLIBC_USE (IEC_60559_BFP_EXT_C23)`
(`/usr/include/math.h` line 530): the `f##name` block lines 532-535 and
the `f##name##l` block lines 540-556 both include
`bits/mathcalls-narrow.h` (lines 23-39, `__MATHCALL_NARROW` of
add/div/fma/mul/sqrt/sub). The gate is defined in
`bits/libc-header-start.h` lines 67-77: on with `_GNU_SOURCE` or
`__STDC_WANT_IEC_60559_BFP_EXT__`, or in C23 mode. Preprocessing
`<math.h>` on this host shows no `fadd` under plain gnu17, but the
declaration appears with `_GNU_SOURCE` or `-std=c23` (verified with
`gcc -E`).

## Semantics

Per the manual (node *Misc FP Arithmetic*, arith.texi lines 2318-2410):
these functions return `x + y` (respectively `x - y`, `x * y`, `x / y`,
`sqrt(x)`), rounded once to the return type of the function without any
intermediate rounding to the type of the arguments. The `_l` names take
`long double` arguments and still return `float`. This gives a
wider-precision computation with a single rounding into `float`.

## Gotchas and portability

- Narrow operations are not aliases of the plain operators: plain
  `(float)(x + y)` on two floats rounds twice, once per operation.
- `tgmath.h` provides a generic macro `fadd` under the same gate
  (`/usr/include/tgmath.h` line 1124).
- The related TS 18661-3 mixed-type functions (`fMaddfN`, `fMxaddfNx`,
  ...) are separate ledger rows and separate symbols (`f32addf64`, ...).
- No man page exists for these names in the cached man-pages set.
- musl 1.2.5: absent from `musl include/math.h` (verified, 0 matches).

## References

- glibc manual: `arith.texi`, node *Misc FP Arithmetic* (lines 2091-2432)
- headers: `/usr/include/math.h`, `bits/mathcalls-narrow.h`,
  `bits/libc-header-start.h`, `/usr/include/tgmath.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
