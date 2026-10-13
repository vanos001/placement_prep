# `conj` / `conjf` / `conjfN` / `conjfNx` / `conjl` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `complex.h` (prototypes via `bits/cmathcalls.h`) |
| Standards | ISO C99 (`conj`, `conjf`, `conjl`); TS 18661-3:2015 (`conjfN`, `conjfNx` family) |
| Exported | `conj@@GLIBC_2.2.5`, `conjf@@GLIBC_2.2.5`, `conjl@@GLIBC_2.2.5`, `conjf32`/`conjf64`/`conjf32x`/`conjf64x@@GLIBC_2.27`, `conjf128@@GLIBC_2.26` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (`conj(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-conj, GLIBC-conjf, GLIBC-conjfN, GLIBC-conjfNx, GLIBC-conjl |

## Declaration and gates

```c
#include <complex.h>

double complex      conj(double complex z);
float complex       conjf(float complex z);
long double complex conjl(long double complex z);
```

Declared like [cabs](cabs-cabsl.md) but with a complex return type:
`__MATHCALL (conj, ...)` at `bits/cmathcalls.h` line 118, expanded for
double/float/long double at `/usr/include/complex.h` lines 111/118/144,
and for `_FloatN`/`_FloatNx` under `__GLIBC_USE (IEC_60559_TYPES_EXT)`
(lines 159-241). Link with `-lm`.

## Semantics

Returns the complex conjugate of `z`: the value obtained by negating the
imaginary part, `conj(a + bi) = a + -bi` (`conj(3)` DESCRIPTION; manual
node *Operations on Complex*, arith.texi lines 2544-2556). The conjugate
turns division by a complex number into multiplication by the conjugate
of the denominator, and `cabs(z) = csqrt(z * conj(z))` (`conj(3)`).
First appeared in glibc 2.1 (`conj(3)` VERSIONS).

## Gotchas and portability

- Negating the imaginary part negates a signed zero too, so
  `conj(inf + 0.0i)` is `inf - 0.0i`; the manuals document only the
  algebraic rule, not zero-sign behavior.
- `conjfN`/`conjfNx` are family notation; exported names are `conjf32`,
  `conjf64`, `conjf32x`, `conjf64x`, `conjf128`. nm shows `conjf32`,
  `conjf64`, `conjf32x` aliased to `conj` and `conjf64x` to `conjl`
  on this host.
- musl 1.2.5: only `conj`/`conjf`/`conjl` declared
  (`musl include/complex.h` lines 92-94); `_FloatN` forms absent.

## References

- glibc manual: `arith.texi`, node *Operations on Complex* (lines 2528-2614)
- man3: `conj(3)` (covers `conjf`, `conjl`)
- headers: `/usr/include/complex.h`, `bits/cmathcalls.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
