# `cproj` / `cprojf` / `cprojfN` / `cprojfNx` / `cprojl` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `complex.h` (prototypes via `bits/cmathcalls.h`) |
| Standards | ISO C99 (`cproj`, `cprojf`, `cprojl`); TS 18661-3:2015 (`cprojfN`, `cprojfNx` family) |
| Exported | `cproj@@GLIBC_2.2.5`, `cprojf@@GLIBC_2.2.5`, `cprojl@@GLIBC_2.2.5`, `cprojf32`/`cprojf64`/`cprojf32x`/`cprojf64x@@GLIBC_2.27`, `cprojf128@@GLIBC_2.26` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (`cproj(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-cproj, GLIBC-cprojf, GLIBC-cprojfN, GLIBC-cprojfNx, GLIBC-cprojl |

## Declaration and gates

```c
#include <complex.h>

double complex      cproj(double complex z);
float complex       cprojf(float complex z);
long double complex cprojl(long double complex z);
```

Declared like [conj](conj-conjl.md) with a complex return type:
`__MATHCALL (cproj, ...)` at `bits/cmathcalls.h` line 121, expanded for
double/float/long double at `/usr/include/complex.h` lines 111/118/144,
and for `_FloatN`/`_FloatNx` under `__GLIBC_USE (IEC_60559_TYPES_EXT)`
(lines 159-241). Link with `-lm`.

## Semantics

Projects a point of the plane onto the Riemann sphere, the one-point
compactification of the complex plane (`cproj(3)` DESCRIPTION). Every
finite `z` projects to itself; every complex infinite value projects to
a single value, positive infinity on the real axis. The manual
(node *Operations on Complex*, arith.texi lines 2591-2614) states that
values with an infinite imaginary part are projected to positive
infinity on the real axis even if the real part is NaN, and if the real
part is infinite the result is equivalent to
`INFINITY + I * copysign (0.0, cimag (z))`. First appeared in glibc 2.1
(`cproj(3)` VERSIONS).

## Gotchas and portability

- `cproj` is the standard-approved way to turn every infinity into one
  canonical infinity before division-like operations; feeding NaN
  components through it is exactly what it exists for.
- glibc 2.11 and earlier implemented a different (stereographic)
  projection instead (`cproj(3)` NOTES) -- behavior changed silently
  between glibc versions.
- `cprojfN`/`cprojfNx` are family notation; exported names are
  `cprojf32`, `cprojf64`, `cprojf32x`, `cprojf64x`, `cprojf128`. nm
  shows `cprojf32`/`cprojf64`/`cprojf32x` aliased to `cproj` and
  `cprojf64x` to `cprojl` on this host.
- musl 1.2.5: only `cproj`/`cprojf`/`cprojl` declared
  (`musl include/complex.h` lines 96-98); `_FloatN` forms absent.

## References

- glibc manual: `arith.texi`, node *Operations on Complex* (lines 2528-2614)
- man3: `cproj(3)` (covers `cprojf`, `cprojl`)
- headers: `/usr/include/complex.h`, `bits/cmathcalls.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
