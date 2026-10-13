# `strcmp` / `strncmp` / `strcasecmp` / `strncasecmp` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (`strcasecmp`, `strncasecmp`: `strings.h`; also `string.h` under `_DEFAULT_SOURCE`) |
| Standards | ISO C / POSIX.1-2001 (`strcmp`, `strncmp`); 4.4BSD / POSIX.1-2001 (`strcasecmp`, `strncasecmp`) |
| Exported | `strcmp@@GLIBC_2.2.5`, `strncmp@@GLIBC_2.2.5`, `strcasecmp@@GLIBC_2.2.5`, `strncasecmp@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`strcmp`); MT-Safe locale (`strcasecmp`, per `strcasecmp(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strcmp, GLIBC-strncmp, GLIBC-strcasecmp, GLIBC-strncasecmp |

## Declaration and gates

```c
#include <string.h>
int strcmp(const char *s1, const char *s2);
int strncmp(const char *s1, const char *s2, size_t n);

#include <strings.h>       /* POSIX home of the case-insensitive pair */
int strcasecmp(const char *s1, const char *s2);
int strncasecmp(const char *s1, const char *s2, size_t n);
```

`strings.h` declares the case-insensitive pair unconditionally
(`/usr/include/strings.h` lines 115-121); `string.h` re-declares them only
when `_DEFAULT_SOURCE` is set for historical 4.4BSD compatibility
(`strcasecmp(3)` NOTES). Locale-taking twins `strcasecmp_l`/`strncasecmp_l`
live in `strings.h` under `__USE_XOPEN2K8`.

## Semantics

`strcmp` compares `s1` and `s2` byte-by-byte as `unsigned char` values and
ignores the locale (`strcmp(3)`); `strncmp` compares at most the first `n`
bytes. All four return an integer less than, equal to, or greater than zero
as `s1` orders before, equal to, or after `s2`. `strcasecmp` performs the
same comparison ignoring case; `strncasecmp` bounds it to `n` bytes
(`strcasecmp(3)`).

## Gotchas and portability

- The magnitude of a nonzero result is unspecified by the standards.
  `strcmp(3)` NOTES quotes POSIX: only the *sign* is defined, and records that
  glibc, like most implementations, returns the arithmetic difference of the
  first differing bytes (e.g. `'C' - '\0'` = 67 for `strcmp("ABC", "AB")`).
  Never write `abs(strcmp(a,b)) == 1` style logic.
- Unsigned comparison matters: `strcmp` with a high-bit byte compares as
  unsigned (`strcmp(3)` example `./string_comp $'\201' A` yields 64), so
  sign-extended `char` ordering surprises do not happen, but negative `char`
  arithmetic in your own comparators can.
- Locale: `strcasecmp` results are unspecified outside the POSIX locale
  unless you use the `_l` variants; `strcasecmp(3)` NOTES quotes POSIX.1-2008
  on exactly this. For locale-aware *collation* (not case folding), the
  proper pair is `strcoll`/`strxfrm` (manual *Collation Functions* node).
- `strcasecmp` lives in `strings.h`, not `string.h`, in strict POSIX mode;
  forgetting the include breaks `_POSIX_C_SOURCE`-only builds.
- Equality testing is the common case: the manual (*String/Array
  Comparison*) recommends the `!strcmp(s1, s2)` idiom.

## References

- glibc manual: `string.texi`, node *String/Array Comparison*
- man3: `strcmp(3)` (covers `strncmp`), `strcasecmp(3)`
- headers: `/usr/include/string.h`, `/usr/include/strings.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
