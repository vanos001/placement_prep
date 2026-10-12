# `strfry` / `memfrob` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (both under `__USE_GNU`) |
| Standards | GNU extensions, unique to glibc (`strfry(3)`, `memfrob(3)` CONFORMING TO; manual Portability Notes) |
| Exported | `strfry@@GLIBC_2.2.5` (strong), `memfrob@@GLIBC_2.2.5` (strong) (nm, host glibc 2.41) |
| Thread-safety | MT-Safe both (`strfry(3)`, `memfrob(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strfry, GLIBC-memfrob |

## Declaration and gates

```c
#define _GNU_SOURCE
#include <string.h>

char  *strfry(char *string);
void  *memfrob(void *s, size_t n);
```

Both live in the `__USE_GNU` block of `/usr/include/string.h` (gate line
517): `strfry` at lines 522-523, `memfrob` at lines 525-527. The man
pages record the same `_GNU_SOURCE` requirement, and the manual's
`@standards{GNU, string.h}` agrees. There is no `_l` or bounded variant
of either.

## Semantics

`strfry` performs an in-place shuffle of `string`: each character is
swapped to a random position within the substring starting at its own
position - Fisher-Yates, per the manual, so the result is an unbiased
anagram. It returns `string` itself and, notably, leaves every global
random number generator undisturbed because it seeds from its own
state (manual, *Shuffling Bytes*). `memfrob` reversibly obfuscates
`length` bytes at `mem` by XORing each with the fixed byte 0x2A (42,
binary 00101010); running it a second time restores the original. Both
functions return their first argument (`strfry(3)`, `memfrob(3)`,
manual *Obfuscating Data*).

## Gotchas and portability

- Neither is a security primitive: the manual's *Obfuscating Data* node
  says the memfrob result "still bears a clear relationship to the
  original" (Rot13-grade obfuscation, no key) and points real
  encryption at a crypto library; `memfrob(3)` says the same ("suitable
  only for hiding strings").
- Distinguishing erase from obfuscate: the manual routes *erasing* to
  `explicit_bzero` and *reversible obfuscation* to `memfrob`
  (*Shuffling Bytes* intro) - `strfry` destroys data by permutation and
  is listed as a destroy-adjacent oddity, not a wipe.
- Both mutate in place and are GNU-only: musl 1.2.5 has neither (no
  `strfry.c`/`memfrob.c` under `musl src/string/`, no declarations in
  `musl include/string.h`).

## References

- glibc manual: `string.texi`, nodes *Shuffling Bytes*,
  *Obfuscating Data*, *Erasing Sensitive Data* (cross-references)
- man3: `strfry(3)`, `memfrob(3)`
- header: `/usr/include/string.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
