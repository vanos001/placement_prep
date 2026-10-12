# `abs` / `labs` / `llabs` / `imaxabs` / `div` / `ldiv` / `lldiv` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` (`imaxabs`, `imaxdiv`: `inttypes.h`) |
| Standards | ISO C89 (`abs`, `labs`, `div`, `ldiv`); C99 (`llabs`, `lldiv`, `imaxabs`, `imaxdiv`) |
| Exported | `abs@@GLIBC_2.2.5`, `labs@@GLIBC_2.2.5`, `llabs@@GLIBC_2.2.5`, `imaxabs@@GLIBC_2.2.5` (weak alias of `labs`), `div@@GLIBC_2.2.5`, `ldiv@@GLIBC_2.2.5`, `lldiv@@GLIBC_2.2.5`, `imaxdiv@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe, pure functions (`abs(3)`, `div(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-abs, GLIBC-labs, GLIBC-llabs, GLIBC-imaxabs, GLIBC-div, GLIBC-ldiv, GLIBC-lldiv, GLIBC-imaxdiv |

## Declaration and gates

```c
#include <stdlib.h>

int       abs(int j);        long labs(long j);
long long llabs(long long j);
typedef struct { int quot, rem; } div_t;
typedef struct { long quot, rem; } ldiv_t;
typedef struct { long long quot, rem; } lldiv_t;
div_t  div(int numer, int denom);
ldiv_t ldiv(long numer, long denom);
lldiv_t lldiv(long long numer, long long denom);   /* C99 gate _ISOC99_SOURCE */

#include <inttypes.h>
intmax_t imaxabs(intmax_t j);
imaxdiv_t imaxdiv(intmax_t numer, intmax_t denom);
```

`llabs`/`lldiv` are gated `__USE_ISOC99` in the installed header
(`/usr/include/stdlib.h` lines 971-976, 985-990); the alias pairs
`labs == imaxabs` and `ldiv == imaxdiv` are visible in nm as identical
addresses with `W` marking on the intmax names.

## Semantics

The absolute-value functions return the magnitude of `j` in the matching
integer type (`abs(3)`); all are `__attribute_const__` in the header. The
`div` family computes `numer / denom` and `numer % denom` together and
returns them in a `*_t` struct with members `quot` and `rem` (member order
unspecified per `div(3)`); the quotient is rounded toward zero and the
invariant `quot * denom + rem == numer` always holds (`div(3)`, manual
`arith.texi` *Integer Division*).

## Gotchas and portability

- `abs(INT_MIN)` is undefined: in two's complement the magnitude of the
  most negative value is not representable (`abs(3)` NOTES; manual
  *Absolute Value* states it plainly). Same trap for `labs(LONG_MIN)` and
  `llabs(LLONG_MIN)`.
- Division by zero, and any unrepresentable division result, is undefined
  behavior for the `div` family (manual *Integer Division*: "as in a
  division by zero").
- Why `div` exists: in ISO C the rounding of `/` for negative operands was
  implementation-defined; `div` pins the round-toward-zero semantics and
  the sign of the remainder follows the numerator. `div(-5, 3)` gives
  `quot == -1`, `rem == -2` (`div(3)` EXAMPLES). In GNU C `/` and `%`
  already round toward zero, so the manual calls these functions redundant
  under GCC but useful for exactness and single-instruction codegen.
- GCC treats `abs`/`labs`/`llabs`/`imaxabs` as builtins and may fold them
  (`abs(3)` NOTES), so a breakpoint on `abs` is unreliable.
- The master manual documents `uabs`/`ulabs`/`ullabs`/`umaxabs` as new in
  ISO C2Y (`arith.texi` *Absolute Value*); none are exported by this
  host's glibc 2.41 (nm), so treat them as unverified for this host.
- musl 1.2.5 keeps the same ISO semantics (trivial wrappers in
  `musl src/stdlib/abs.c`, `div.c`).

## References

- glibc manual: `arith.texi`, nodes *Integer Division*, *Absolute Value*
- man3: `abs(3)` (covers `labs`, `llabs`, `imaxabs`), `div(3)` (covers
  `ldiv`, `lldiv`, `imaxdiv`)
- headers: `/usr/include/stdlib.h`, `/usr/include/inttypes.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
