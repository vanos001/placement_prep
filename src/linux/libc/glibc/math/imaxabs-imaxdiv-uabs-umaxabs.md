# `imaxabs` / `imaxdiv` / `uabs` / `ulabs` / `ullabs` / `umaxabs` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `inttypes.h` (`imaxabs`, `imaxdiv`, `umaxabs`); `stdlib.h` (`uabs`, `ulabs`, `ullabs` -- per the manual, not yet on this host) |
| Standards | C99 (`imaxabs`, `imaxdiv`); ISO C2Y (`uabs`, `ulabs`, `ullabs`, `umaxabs`, manual arith.texi line 1261) |
| Exported | `imaxabs@@GLIBC_2.2.5` (weak alias of `labs`), `imaxdiv@@GLIBC_2.2.5` (nm, libc.so.6); `uabs`/`ulabs`/`ullabs`/`umaxabs` not exported by host glibc 2.41 |
| Thread-safety | MT-Safe (`abs(3)`, `div(3)` ATTRIBUTES -- `imaxabs(3)`/`imaxdiv(3)` are `.so` links to them) |
| Ledger ID | GLIBC-imaxabs, GLIBC-imaxdiv, GLIBC-uabs, GLIBC-ulabs, GLIBC-ullabs, GLIBC-umaxabs |

## Declaration and gates

```c
#include <inttypes.h>

intmax_t imaxabs(intmax_t n);
typedef struct { intmax_t quot, rem; } imaxdiv_t;
imaxdiv_t imaxdiv(intmax_t numer, intmax_t denom);

/* ISO C2Y family, documented in the manual, not yet in host headers: */
unsigned int       uabs(int n);              /* stdlib.h */
unsigned long      ulabs(long n);            /* stdlib.h */
unsigned long long ullabs(long long n);      /* stdlib.h */
uintmax_t          umaxabs(intmax_t n);      /* inttypes.h */
```

`imaxabs`/`imaxdiv` are unconditionally declared in
`/usr/include/inttypes.h` (lines 351 and 354; `imaxdiv_t` typedef lines
331-345). The C2Y unsigned family appears in the manual with exactly
the signatures above (arith.texi lines 1237-1244, 1248-1256) but is
absent from both `/usr/include/stdlib.h` and `/usr/include/inttypes.h`
on this host (grep verified), and from `nm -D libc.so.6`.

## Semantics

`imaxabs` returns the absolute value of its `intmax_t` argument
(`abs(3)`, which covers `imaxabs` via link). As with `abs`, the absolute
value of the most negative integer is undefined; the manual adds that
using `uabs` avoids that two's-complement hazard for `int`
(arith.texi lines 1257-1261). `imaxdiv` computes quotient and remainder
at once: the result `r` satisfies `r.quot*denominator + r.rem == numerator`,
quotient rounded toward zero, remainder taking the sign of
the numerator; division by zero is undefined behavior (manual, node
*Integer Division*, arith.texi lines 146-152, 256-268). `imaxdiv` was
added in C99 (arith.texi line 265).

## Gotchas and portability

- `imaxabs` is a weak alias of `labs` on this LP64 host (nm shows both
  at one address) -- true wherever `intmax_t` is `long`.
- The four unsigned names are the only rows on this page whose glibc
  2.41 support is manual-only: no header declaration and no exported
  symbol; treat code using them as forward-looking C2Y.
- musl 1.2.5: `imaxabs`/`imaxdiv` present (`musl include/inttypes.h`
  lines 16-17); the unsigned family is absent (verified). The
  [abs/div page](../../glibc/strings/abs-labs-llabs-imaxabs-div.md)
  covers the `int`/`long`/`long long` siblings.

## References

- glibc manual: `arith.texi`, nodes *Absolute Value* (lines 1223-1270),
  *Integer Division* (lines 128-268)
- man3: `abs(3)` (covers `imaxabs`), `div(3)` (covers `imaxdiv`)
- headers: `/usr/include/inttypes.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
