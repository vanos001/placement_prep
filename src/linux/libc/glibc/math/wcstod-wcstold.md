# `wcstod` / `wcstof` / `wcstofN` / `wcstofNx` / `wcstold` (3) - glibc

> Split from the chapter *glibc: arithmetic functions* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wchar.h` |
| Standards | ISO C90 Amendment 1 (`wcstod`); C99 (`wcstof`, `wcstold`); GNU (`wcstofN`, `wcstofNx` family, manual arith.texi lines 3103-3104) |
| Exported | `wcstod`/`wcstof`/`wcstold@@GLIBC_2.2.5`, `wcstof32`/`wcstof64`/`wcstof32x`/`wcstof64x@@GLIBC_2.27`, `wcstof128@@GLIBC_2.26` (nm, libc.so.6, host glibc 2.41) |
| Thread-safety | MT-Safe locale (manual safety note, arith.texi lines 3097-3098) |
| Ledger ID | GLIBC-wcstod, GLIBC-wcstof, GLIBC-wcstofN, GLIBC-wcstofNx, GLIBC-wcstold |

## Declaration and gates

```c
#include <wchar.h>

double      wcstod (const wchar_t *restrict nptr, wchar_t **restrict endptr);
float       wcstof (const wchar_t *nptr, wchar_t **endptr);   /* __USE_ISOC99 */
long double wcstold(const wchar_t *nptr, wchar_t **endptr);   /* __USE_ISOC99 */
```

`wcstod` is unconditionally declared at `/usr/include/wchar.h` lines
402-404; `wcstof`/`wcstold` sit in `#ifdef __USE_ISOC99` (lines
405-412). The `_FloatN`/`_FloatNx` names (`wcstof16`, `wcstof32`,
`wcstof64`, `wcstof128`, `wcstof32x`, `wcstof64x`, `wcstof128x`) need
`__GLIBC_USE (IEC_60559_TYPES_EXT) && __GLIBC_USE (ISOC23)` plus the
`__HAVE_FLOAT*` macros (lines 415-450). No standalone man page for
these names exists in the cached man-pages set; they are documented as
wide equivalents of [strtod](../../glibc/strings/atof-atoi-strtod-family.md).

## Semantics

The manual (node *Parsing of Floats*, arith.texi lines 3091-3110) makes
`wcstod`, `wcstof`, `wcstold`, `wcstofN` and `wcstofNx` equivalent in
nearly all aspects to `strtod`, `strtof`, `strtold`, `strtofN` and
`strtofNx` but handling wide character strings: optional wide
whitespace, optional sign, then a decimal or hexadecimal (`0x...p` plus a binary exponent)
floating-point number, with `inf`/`infinity` and `nan(chars)` forms
recognized. No conversion leaves a 0 return and `*endptr` set to
`nptr`; valid syntax out of range signals overflow/underflow per the
manual's *Math Error Reporting* rules. `wcstod` dates to Amendment 1 of
C90; `wcstof`/`wcstold` to C99 (arith.texi lines 3107-3110).

## Gotchas and portability

- The wide `wcstofN`/`wcstofNx` names are "not in any standard" and
  exist for completeness of the wide conversion family (manual,
  arith.texi lines 3103-3105); exported symbols are `wcstof32`, ...,
  and nm shows `wcstof32`/`wcstof64`/`wcstof32x` aliased to `wcstod`,
  `wcstof64x` to `wcstold` on this LP64 host.
- The decimal-point character and locale-dependent extra syntax follow
  the same locale rules as `strtod` (arith.texi lines 3023-3030).
- musl 1.2.5: only `wcstod`/`wcstof`/`wcstold` declared
  (`musl include/wchar.h` lines 96-98); the `_FloatN` forms are absent.

## References

- glibc manual: `arith.texi`, node *Parsing of Floats* (lines 2944-3131)
- headers: `/usr/include/wchar.h`
- man3: `strtod(3)` for the shared numeric syntax
- symbols: `nm -D --with-symbol-versions libc.so.6`
