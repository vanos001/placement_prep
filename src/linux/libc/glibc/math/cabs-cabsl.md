# `cabs` / `cabsf` / `cabsfN` / `cabsfNx` / `cabsl` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `complex.h` (prototypes via `bits/cmathcalls.h`) |
| Standards | ISO C99 (`cabs`, `cabsf`, `cabsl`); TS 18661-3:2015 (`cabsfN`, `cabsfNx` family) |
| Exported | `cabs@@GLIBC_2.2.5`, `cabsf@@GLIBC_2.2.5`, `cabsl@@GLIBC_2.2.5`, `cabsf32`/`cabsf64`/`cabsf32x`/`cabsf64x@@GLIBC_2.27`, `cabsf128@@GLIBC_2.26` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (`cabs(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-cabs, GLIBC-cabsf, GLIBC-cabsfN, GLIBC-cabsfNx, GLIBC-cabsl |

## Declaration and gates

```c
#include <complex.h>

double      cabs(double complex z);
float       cabsf(float complex z);
long double cabsl(long double complex z);
```

`complex.h` includes `bits/cmathcalls.h` three times for the three real
types (`/usr/include/complex.h` lines 109-144; `cabs` declared with
`__MATHDECL` at `bits/cmathcalls.h` line 112). The `_FloatN` / `_FloatNx`
forms (`cabsf32`, `cabsf64`, `cabsf32x`, `cabsf64x`, `cabsf128`, ...) come
from re-including the same file under
`__GLIBC_USE (IEC_60559_TYPES_EXT)` with `__CFLOAT32` etc. as the complex
type (`/usr/include/complex.h` lines 159-241). `cabsfN` / `cabsfNx` are
the manual's family notation (manual, arith.texi lines 1281-1284); the
linker names carry the real suffixes. Link with `-lm` (`cabs(3)`).

## Semantics

Returns the absolute value (modulus) of `z`:
`sqrt(creal(z)*creal(z) + cimag(z)*cimag(z))`
(manual, node *Absolute Value*). The manual says to use `cabs` instead of
the direct formula because it takes care to avoid losing precision and
may use hardware support; it is the complex analogue of `hypot`
(`cabs(3)` NOTES: the function is actually an alias for
`hypot(a, b)`). First appeared in glibc 2.1 (`cabs(3)` VERSIONS).

## Gotchas and portability

- The result is a real number, not complex; the return type follows the
  precision suffix (`cabs(3)`).
- `cabsfN`/`cabsfNx` never appear as symbol names: nm shows `cabsf32`,
  `cabsf64`, `cabsf32x`, `cabsf64x`, `cabsf128`. On this host
  `cabsf32`, `cabsf64`, `cabsf32x` share one address with `cabs`
  (weak aliases); `cabsf64x` shares one with `cabsl`.
- musl 1.2.5: only `cabs`/`cabsf`/`cabsl` are declared; the `_FloatN`
  family is absent (`musl include/complex.h` lines 72-74).

## References

- glibc manual: `arith.texi`, nodes *Absolute Value* (lines 1281-1301),
  *Complex Numbers*, *Operations on Complex*
- man3: `cabs(3)` (covers `cabsf`, `cabsl`)
- headers: `/usr/include/complex.h`, `bits/cmathcalls.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
