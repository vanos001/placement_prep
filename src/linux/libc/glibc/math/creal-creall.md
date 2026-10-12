# `creal` / `crealf` / `crealfN` / `crealfNx` / `creall` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `complex.h` (prototypes via `bits/cmathcalls.h`) |
| Standards | ISO C99 (`creal`, `crealf`, `creall`); TS 18661-3:2015 (`crealfN`, `crealfNx` family) |
| Exported | `creal@@GLIBC_2.2.5`, `crealf@@GLIBC_2.2.5`, `creall@@GLIBC_2.2.5`, `crealf32`/`crealf64`/`crealf32x`/`crealf64x@@GLIBC_2.27`, `crealf128@@GLIBC_2.26` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (`creal(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-creal, GLIBC-crealf, GLIBC-crealfN, GLIBC-crealfNx, GLIBC-creall |

## Declaration and gates

```c
#include <complex.h>

double      creal(double complex z);
float       crealf(float complex z);
long double creall(long double complex z);
```

Declared like [cimag](cimag-cimagl.md) with a real return type:
`__MATHDECL (_Mdouble_,creal,...)` at `bits/cmathcalls.h` line 130,
expanded for double/float/long double at `/usr/include/complex.h` lines
111/118/144 and for `_FloatN`/`_FloatNx` under
`__GLIBC_USE (IEC_60559_TYPES_EXT)` (lines 159-241). Link with `-lm`.

## Semantics

Returns the real part of `z`, so that
`z = creal(z) + I * cimag(z)` (`creal(3)` DESCRIPTION; manual node
*Operations on Complex*, arith.texi lines 2528-2535). The decomposition
pair `creal`/`cimag` plus `cabs`/`carg` covers the rectangular and polar
views of a complex number. First appeared in glibc 2.1 (`creal(3)`
VERSIONS).

## Gotchas and portability

- GNU C has a separate `__real__` operator with the same purpose; the
  man page records it as a gcc extension (`creal(3)` NOTES).
- `crealfN`/`crealfNx` are family notation; the exported names are
  `crealf32`, `crealf64`, `crealf32x`, `crealf64x`, `crealf128`. nm
  shows `crealf32`/`crealf64`/`crealf32x` aliased to `creal` and
  `crealf64x` to `creall` on this host.
- The imaginary-unit macro `I` and the `complex` keyword macro both live
  in this header, so `complex.h` changes the meaning of ordinary
  identifiers after inclusion (manual, node *Complex Numbers*).
- musl 1.2.5: `creal`/`crealf`/`creall` declared and additionally as
  macros `#define creal(x) ((double)(x))` etc. (`musl include/complex.h`
  lines 100-108); `_FloatN` forms absent.

## References

- glibc manual: `arith.texi`, node *Operations on Complex* (lines 2528-2614)
- man3: `creal(3)` (covers `crealf`, `creall`)
- headers: `/usr/include/complex.h`, `bits/cmathcalls.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
