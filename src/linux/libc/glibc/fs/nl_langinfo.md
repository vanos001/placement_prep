# `nl_langinfo` (3) - glibc

> Per-function page for the per-item locale accessor of the glibc Locale
> family; see the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. Pair with
> [setlocale-localeconv.md](./setlocale-localeconv.md).

| Field | Value |
|---|---|
| Header | `langinfo.h` (item constants); `nl_types.h` (`nl_item`) |
| Standards | X/Open (`nl_langinfo`); POSIX.1-2008 (`nl_langinfo_l`, gated `__USE_XOPEN2K8` in the header) |
| Exported | `nl_langinfo@@GLIBC_2.2.5`, `nl_langinfo_l@@GLIBC_2.3` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe locale (manual annotation; the returned pointer names constant strings inside the loaded locale data) |
| Ledger ID | GLIBC-nl_langinfo (researched row), GLIBC-nl_langinfo_l (researched) |

## Declaration and gates

```c
#include <langinfo.h>
#include <nl_types.h>

char *nl_langinfo(nl_item item);
char *nl_langinfo_l(nl_item item, locale_t locale);  /* __USE_XOPEN2K8 */
```

Selected X/Open items (manual table, abridged; the header carries the full
`langinfo.h` enum plus `_NL_*` GNU extensions such as `_NL_TIME_CODESET`):

| Items | Meaning |
|---|---|
| `CODESET` | coded character set of `LC_CTYPE` |
| `ABDAY_1..ABDAY_7`, `DAY_1..DAY_7` | weekday abbreviations / full names, Sunday first |
| `ABMON_1..ABMON_12`, `MON_1..MON_12` | month names as in a date |
| `ALTMON_1..ALTMON_12` | standalone month names, used by `%OB` in `strftime` |
| `AM_STR`, `PM_STR` | am/pm strings (may be empty) |
| `D_T_FMT`, `D_FMT`, `T_FMT`, `T_FMT_AMPM` | `strftime` format templates |
| `ERA`, `ERA_D_FMT`, `ERA_T_FMT`, `ERA_D_T_FMT` | era-based date rendering |
| `YESEXPR`, `NOEXPR` | `LC_MESSAGES` regexps for yes/no answers |

## Semantics

The manual's positioning: `localeconv` is portable but limited to numeric
and monetary fields, while `nl_langinfo` "lets the caller select what
information it requires", is fast to call repeatedly, and additionally
exposes `LC_TIME` and `LC_MESSAGES` data (node *The Elegant and Fast Way*).
The return value points into the locale data; the manual's safety commentary
records that it goes through `_nl_langinfo_l` with the current locale and
returns pointers into constant strings of the locale structures.

## Gotchas and portability

- `ALTMON_*` exist, but the manual notes `ABALTMON_*` (for `%Ob`) is not
  provided and suggests `_NL_ABALTMON_*` meanwhile.
- Item values are numeric and implementation-specific beyond the X/Open
  set; only same-build constants are meaningful.
- musl 1.2.5: `src/locale/langinfo.c` returns hard-coded C-locale strings
  for every item except `CODESET`, which is `"UTF-8"` or `"ASCII"` depending
  on the loaded ctype map - i.e., no localized data at all, matching the
  musl catalog's locale limits.

## References

- glibc manual: `locale.texi`, nodes *The Elegant and Fast Way*, *Locale
  Information*
- man3: `nl_langinfo.3`, `nl_langinfo_l.3`
- headers: `/usr/include/langinfo.h`, `/usr/include/nl_types.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
