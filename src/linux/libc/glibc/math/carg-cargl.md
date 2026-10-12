# `carg` / `cargf` / `cargfN` / `cargfNx` / `cargl` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `complex.h` (prototypes via `bits/cmathcalls.h`) |
| Standards | ISO C99 (`carg`, `cargf`, `cargl`); TS 18661-3:2015 (`cargfN`, `cargfNx` family) |
| Exported | `carg@@GLIBC_2.2.5`, `cargf@@GLIBC_2.2.5`, `cargl@@GLIBC_2.2.5`, `cargf32`/`cargf64`/`cargf32x`/`cargf64x@@GLIBC_2.27`, `cargf128@@GLIBC_2.26` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (`carg(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-carg, GLIBC-cargf, GLIBC-cargfN, GLIBC-cargfNx, GLIBC-cargl |

## Declaration and gates

```c
#include <complex.h>

double      carg(double complex z);
float       cargf(float complex z);
long double cargl(long double complex z);
```

Declared by the same `bits/cmathcalls.h` expansions as [cabs](cabs-cabsl.md):
double at `/usr/include/complex.h` line 111, float at 118, long double at
144 (`carg` at `bits/cmathcalls.h` line 115); `_FloatN`/`_FloatNx` forms
under `__GLIBC_USE (IEC_60559_TYPES_EXT)` (`complex.h` lines 159-241).
Link with `-lm` (`carg(3)`).

## Semantics

Returns the argument (phase angle) of `z`: the angle in the complex plane
between the positive real axis and the line through zero and `z`,
measured in the range [-pi, pi] (`carg(3)` RETURN VALUE). The manual
(node *Operations on Complex*, arith.texi lines 2562-2580) adds that
`carg` has a branch cut along the negative real axis, and
`tan(carg(z)) = cimag(z) / creal(z)` (`carg(3)`). Together with `cabs`
it converts to polar form: `z = r * cexp(I * a)` with `r = cabs(z)`,
`a = carg(z)` (`carg(3)` DESCRIPTION). First appeared in glibc 2.1
(`carg(3)` VERSIONS).

## Gotchas and portability

- The branch cut on the negative real axis means the sign of a zero
  imaginary part decides which side of pi the result lands on; the man
  page and manual state the cut but not per-implementation results.
- `cargfN`/`cargfNx` are family notation; the exported names are
  `cargf32`, `cargf64`, `cargf32x`, `cargf64x`, `cargf128`. On this host
  `cargf32`, `cargf64`, `cargf32x` alias `carg`; `cargf64x` aliases
  `cargl` (nm).
- musl 1.2.5: only `carg`/`cargf`/`cargl` declared
  (`musl include/complex.h` lines 84-86); `_FloatN` forms absent.

## References

- glibc manual: `arith.texi`, node *Operations on Complex*
- man3: `carg(3)` (covers `cargf`, `cargl`)
- headers: `/usr/include/complex.h`, `bits/cmathcalls.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
