# `cimag` / `cimagf` / `cimagfN` / `cimagfNx` / `cimagl` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `complex.h` (prototypes via `bits/cmathcalls.h`) |
| Standards | ISO C99 (`cimag`, `cimagf`, `cimagl`); TS 18661-3:2015 (`cimagfN`, `cimagfNx` family) |
| Exported | `cimag@@GLIBC_2.2.5`, `cimagf@@GLIBC_2.2.5`, `cimagl@@GLIBC_2.2.5`, `cimagf32`/`cimagf64`/`cimagf32x`/`cimagf64x@@GLIBC_2.27`, `cimagf128@@GLIBC_2.26` (nm, libm.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe (`cimag(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-cimag, GLIBC-cimagf, GLIBC-cimagfN, GLIBC-cimagfNx, GLIBC-cimagl |

## Declaration and gates

```c
#include <complex.h>

double      cimag(double complex z);
float       cimagf(float complex z);
long double cimagl(long double complex z);
```

Declared like [cabs](cabs-cabsl.md): `cimag` at `bits/cmathcalls.h`
line 127 with a real return type (`__MATHDECL (_Mdouble_,cimag,...)`),
expanded for double/float/long double at `/usr/include/complex.h` lines
111/118/144 and for `_FloatN`/`_FloatNx` under
`__GLIBC_USE (IEC_60559_TYPES_EXT)` (lines 159-241). Link with `-lm`.

## Semantics

Returns the imaginary part of `z`, so that
`z = creal(z) + I * cimag(z)` (`cimag(3)` DESCRIPTION; manual node
*Operations on Complex*, arith.texi lines 2536-2543). Unlike most
complex functions this is a projection, not a computation: the return
type is the matching real type, not a complex type. First appeared in
glibc 2.1 (`cimag(3)` VERSIONS).

## Gotchas and portability

- GNU C has a separate `__imag__` operator with the same purpose;
  the man page records it as a gcc extension, and `complex.h` deliberately
  does not define an `imag` macro (`cimag(3)` NOTES).
- Because `I` is a macro (`complex.h` line 53), code that needs its own
  identifier `I` must `#undef I` first (manual, node *Complex Numbers*).
- `cimagfN`/`cimagfNx` are family notation; the exported names are
  `cimagf32`, `cimagf64`, `cimagf32x`, `cimagf64x`, `cimagf128`. nm shows
  `cimagf32`/`cimagf64`/`cimagf32x` aliased to `cimag` and `cimagf64x`
  to `cimagl` on this host.
- musl 1.2.5: `cimag`/`cimagf`/`cimagl` declared, and additionally as
  macros that pick the second element of a union view of the value
  (`#define cimag(x) __CIMAG(x, double)`, `musl include/complex.h`
  lines 104-112); `_FloatN` forms absent.

## References

- glibc manual: `arith.texi`, node *Operations on Complex* (lines 2528-2614)
- man3: `cimag(3)` (covers `cimagf`, `cimagl`)
- headers: `/usr/include/complex.h`, `bits/cmathcalls.h`
- symbols: `nm -D --with-symbol-versions libm.so.6`
