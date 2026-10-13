# `nl_langinfo` / `rpmatch` (3) - glibc

> Split from the chapter *glibc: Locales* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `langinfo.h` (`nl_langinfo`); `stdlib.h` (`rpmatch`, under `__USE_MISC`) |
| Standards | POSIX.1-2001/2008 (`nl_langinfo`; `_l` twin since POSIX.1-2008); SVID/GNU (`rpmatch`) |
| Exported | `nl_langinfo@@GLIBC_2.2.5`, `nl_langinfo_l@@GLIBC_2.3`, `rpmatch@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `locale` all three (`nl_langinfo(3)`, `rpmatch(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-nl_langinfo, GLIBC-nl_langinfo_l, GLIBC-rpmatch |

## Declaration and gates

```c
#include <langinfo.h>

char *nl_langinfo(nl_item item);                       /* line 661 */
char *nl_langinfo_l(nl_item item, locale_t locale);    /* line 669 */

#include <stdlib.h>

int rpmatch(const char *response);                     /* line 1088 */
```

`nl_langinfo` is unconditional in `/usr/include/langinfo.h`; the
`_l` twin needs `_POSIX_C_SOURCE >= 200809L` (`nl_langinfo(3)`).
`rpmatch` sits in the `__USE_MISC` block of `/usr/include/stdlib.h`
(line 1085-1089): `_DEFAULT_SOURCE` (glibc >= 2.19), formerly
`_SVID_SOURCE` (`rpmatch(3)`).

## Semantics

`nl_langinfo` is the "elegant" per-item locale query over
`localeconv`'s single blob: given an `nl_item` such as `CODESET`,
`D_T_FMT`, `T_FMT`, `RADIXCHAR`, `YESEXPR`/`NOEXPR`, `CRNCYSTR`, it
returns the string the current global locale assigns to that element
(`nl_langinfo(3)`, manual node *The Elegant and Fast Way*). The
returned pointer may be overwritten by later locale changes or calls,
so copy anything to be kept. `nl_langinfo_l` queries an explicit
locale object instead. `rpmatch` classifies a yes/no answer
internationally: responses matching `^[Yy]` are always affirmative
(1), `^[Nn]` always negative (0), anything else is matched against
the locale's `YESEXPR`/`NOEXPR` regular expressions from `LC_MESSAGES`
(`rpmatch(3)`).

## Gotchas and portability

- The return value points into locale storage: not a stable buffer,
  not owned by the caller (`nl_langinfo(3)`).
- `rpmatch` returns -1 for unrecognized answers -- always handle it
  rather than treating nonzero as "yes".
- `rpmatch` is a glibc/SVID extension: musl 1.2.5 has `nl_langinfo`
  (`src/locale/langinfo.c`) but no `rpmatch` (verified absence in
  `include/stdlib.h` and `src/`).

## References

- glibc manual: `locale.texi`, nodes *The Elegant and Fast Way*,
  *Yes-or-No Questions*
- man3: `nl_langinfo(3)`, `rpmatch(3)`
- headers: `/usr/include/langinfo.h`, `/usr/include/stdlib.h`
- musl: `src/locale/langinfo.c`
