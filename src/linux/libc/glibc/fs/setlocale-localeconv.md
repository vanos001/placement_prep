# `setlocale` / `localeconv` (3) - glibc

> Per-function page for locale selection and the ISO C locale-data snapshot;
> see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. The per-item
> accessor `nl_langinfo` has its own page
> [nl_langinfo.md](./nl_langinfo.md).

| Field | Value |
|---|---|
| Header | `locale.h` |
| Standards | ISO C (`setlocale`, `localeconv`, `struct lconv`, `LC_*`); X/Open (`LC_MESSAGES` category) |
| Exported | `setlocale@@GLIBC_2.2.5`, `localeconv@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `setlocale` MT-Unsafe const:locale env (it mutates the global locale; manual annotation and commentary: uses of the global locale are unguarded, so do not call it once threads run); `localeconv` MT-Unsafe race:localeconv (static buffer) |
| Ledger ID | GLIBC-setlocale (documented, grouped), GLIBC-localeconv (documented, grouped) |

## Declaration and gates

```c
#include <locale.h>

char *setlocale(int category, const char *locale);
struct lconv *localeconv(void);
/* category: LC_ALL LC_COLLATE LC_CTYPE LC_MONETARY LC_NUMERIC
             LC_TIME LC_MESSAGES (XOPEN) */
```

## Semantics

Every ISO C program starts in the `"C"` locale; to honor the environment a
program must call `setlocale(LC_ALL, "")` itself (manual, *Setting the
Locale*). With a NULL `locale` the function queries and returns the current
name for `category`; the returned string can be overwritten by later calls,
so copy it (manual). The environment lookup order is `LC_ALL`, then the
individual `LC_*` variable, then `LANG` (manual, *Locale Categories*). An
invalid name returns NULL and leaves the locale unchanged (manual). Locale
names follow XPG syntax `language[_territory[.codeset]][@modifier]`; the
only portable names are `"C"`, `"POSIX"` (its alias) and `""` (manual,
*Standard Locales*, *Locale Names*). `LC_ALL` query results can be composite
names like `LC_CTYPE=en_US.UTF-8;LC_TIME=...` encoding a per-category mix
(manual, *Locale Names*). `localeconv` returns a `struct lconv` holding the
`LC_NUMERIC` and `LC_MONETARY` formatting fields (`decimal_point`,
`thousands_sep`, `currency_symbol`, `*_sign_posn`, ...); only
`localeconv` and `setlocale` may overwrite it (manual, *The Lame Way to
Locale Data*).

## Gotchas and portability

- Composite `LC_ALL` strings are a glibc serialization detail; the manual
  says only its own format round-trips.
- A slash-leading locale name resolves relative to `LOCPATH` in glibc,
  whereas POSIX suggests absolute resolution - divergence documented in the
  manual's *Locale Names* portability note. `LOCPATH` is ignored for
  privileged programs.
- musl 1.2.5: `src/locale/setlocale.c` accepts only the built-in `C`,
  `POSIX`, `C.UTF-8`/`UTF-8` style names and a `;`-separated composite for
  `LC_ALL`; `src/locale/localeconv.c` returns one fixed `posix_lconv`
  structure, so monetary/numeric fields never change with the environment.

## References

- glibc manual: `locale.texi`, nodes *Effects of Locale*, *Locale
  Categories*, *Setting the Locale*, *Standard Locales*, *Locale Names*,
  *The Lame Way to Locale Data*
- man3: `setlocale.3`, `localeconv.3`
- headers: `/usr/include/locale.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
