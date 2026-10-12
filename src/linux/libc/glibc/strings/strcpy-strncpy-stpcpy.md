# `strcpy` / `strncpy` / `stpcpy` / `stpncpy` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` |
| Standards | ISO C (`strcpy`, `strncpy`); POSIX.1-2008 (`stpcpy`, `stpncpy`); GNU origins |
| Exported | `strcpy@@GLIBC_2.2.5`, `strncpy@@GLIBC_2.2.5`, `stpcpy@@GLIBC_2.2.5`, `stpncpy@@GLIBC_2.2.5`; fortified `__strcpy_chk@@GLIBC_2.3.4`, `__strncpy_chk@@GLIBC_2.3.4` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (ATTRIBUTES in `strcpy(3)`, `stpcpy(3)`, `stpncpy(3)`) |
| Ledger ID | GLIBC-strcpy, GLIBC-strncpy, GLIBC-stpcpy, GLIBC-stpncpy |

## Declaration and gates

```c
#include <string.h>

char *strcpy(char *restrict dest, const char *restrict src);
char *strncpy(char *restrict dest, const char *restrict src, size_t n);
char *stpcpy(char *restrict dest, const char *restrict src);   /* __USE_XOPEN2K8 */
char *stpncpy(char *restrict dest, const char *restrict src, size_t n);
```

`stpcpy`/`stpncpy` are declared in `string.h` under `__USE_XOPEN2K8`
(`/usr/include/string.h` lines 476-502); the gate history per `stpcpy(3)` is
`_POSIX_C_SOURCE >= 200809L` since glibc 2.10, `_GNU_SOURCE` before.

## Semantics

`strcpy` copies `src` including the terminating null byte into `dest`, which
must be large enough; the strings may not overlap (`strcpy(3)`). It returns
`dest`. `strncpy` copies at most `n` bytes: if `src` is shorter than `n` it
pads the destination with null bytes up to a total of `n`; if there is no null
byte in the first `n` bytes of `src` the result in `dest` is **not**
null-terminated (`strcpy(3)`, manual *Truncating Strings* node). `stpcpy`
returns a pointer to the terminating null it wrote, allowing chained copies
(`stpcpy(3)` BUGS still warns the function can overrun `dest`). `stpncpy`
always writes exactly `n` bytes and returns `dest + n` when the result is not
terminated, else a pointer to the first written null (`stpncpy(3)`, manual
*Truncating Strings*).

## Gotchas and portability

- The `strncpy` null-padding trap: with
  `strncpy(buf, str, sizeof(buf))` the buffer is terminated only if `str`
  fits; otherwise the last byte holds source data. `strcpy(3)` NOTES gives the
  forced-termination idiom
  `if (buflen > 0) { strncpy(buf, str, buflen - 1); buf[buflen - 1] = '\0'; }`.
- The zero-padding behavior is a feature, not a bug, for fixed-width records
  (the intended use per `strcpy(3)` NOTES: fixed-length buffers whose unused
  bytes must be zeroed, e.g. before writing to media); as a string function it
  is needlessly O(n) on the pad.
- Buffer overruns with `strcpy` are undefined behavior; `strcpy(3)` BUGS calls
  the overflow "a favorite cracker technique".
- `_FORTIFY_SOURCE` maps these calls to `__builtin___strcpy_chk` /
  `__builtin___strncpy_chk`, backed by `__strcpy_chk` / `__strncpy_chk`
  symbols at `GLIBC_2.3.4` (`bits/string_fortified.h`, nm).
- `strlcpy`: the cached `strcpy(3)` (2021) says "not present in glibc and is
  not standardized by POSIX", but glibc 2.38 NEWS announces the addition of
  `strlcpy`/`strlcat` ("derived from OpenBSD, expected to be added to a future
  POSIX version"), and this host's `string.h` declares both under
  `__USE_MISC`. The manual's *Truncating Strings* node (master tree) marks
  them POSIX.1-2024.
- musl 1.2.5 ships `strlcpy`/`strlcat` in `string.h` unconditionally
  (`musl include/string.h` lines 86-87).

## References

- glibc manual: `string.texi`, nodes *Copying Strings and Arrays*,
  *Truncating Strings*
- man3: `strcpy(3)`, `stpcpy(3)`, `stpncpy(3)`
- headers: `/usr/include/string.h`, `bits/string_fortified.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
