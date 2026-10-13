# `isalpha` / `isdigit` / `isspace` / `tolower` / `toupper` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `ctype.h` |
| Standards | ISO C (`isalnum` ... `isxdigit`, `tolower`, `toupper`); C99 (`isblank`); SVID/BSD, POSIX-obsolete (`isascii`, `toascii`, `_tolower`, `_toupper`) |
| Exported | `isalpha@@GLIBC_2.2.5`, `isdigit@@GLIBC_2.2.5`, `isspace@@GLIBC_2.2.5`, `tolower@@GLIBC_2.2.5`, `toupper@@GLIBC_2.2.5`, plus `_tolower`, `_toupper`, `isascii`, `toascii`, `__ctype_b_loc@@GLIBC_2.3` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe (`isalpha(3)` ATTRIBUTES); results depend on the thread's `LC_CTYPE` locale |
| Ledger ID | GLIBC-isalpha, GLIBC-isdigit, GLIBC-isspace, GLIBC-tolower, GLIBC-toupper, GLIBC-isascii, GLIBC-toascii |

## Declaration and gates

```c
#include <ctype.h>

int isalnum(int c);  int isalpha(int c);  int iscntrl(int c);
int isdigit(int c);  int isgraph(int c);  int islower(int c);
int isprint(int c);  int ispunct(int c);  int isspace(int c);
int isupper(int c);  int isxdigit(int c); int isblank(int c); /* C99 */
int tolower(int c);  int toupper(int c);

int isascii(int c);  int toascii(int c);      /* __USE_MISC || __USE_XOPEN */
int _tolower(int c); int _toupper(int c);     /* macros, no range check */
```

glibc implements the classification functions through a per-thread table
fetched by `__ctype_b_loc()`: arrays of 384 entries indexable by any
`unsigned char` value [0,255], by `EOF` (-1), and by signed `char` values
[-128,-1) (`/usr/include/ctype.h` comment lines 63-84). The `_IS*` bit enum
on lines 46-60 defines the 12 classes.

## Semantics

Each `is*` predicate returns nonzero iff `c` is in the named class for the
current locale, and zero otherwise; every one accepts `EOF` and returns
zero for it (`isalpha(3)`, manual `ctype.texi` *Classification of
Characters*). `tolower`/`toupper` map case when possible and return the
argument unchanged otherwise (`ctype.texi` *Case Conversion*). `isascii`
tests the 7-bit range; `toascii` masks with `0x7f` (`ctype.h` macros
`__isascii`/`__toascii`, lines 99-100).

## Gotchas and portability

- The argument rule: `c` must be an `unsigned char` value or `EOF`. A plain
  `char` on signed-char machines sign-extends high-bit bytes into negative
  values outside the required domain; `isalpha(3)` NOTES prescribes
  `toupper((unsigned char) c)`. glibc additionally tolerates signed values
  -128..-2 as an extension, which the manual flags as bug-prone
  (`ctype.texi`, lines 68-73).
- Locale dependence: in the "C" locale `isalpha` is exactly
  `isupper || islower`, and `isspace` is exactly the six characters space,
  `\f`, `\n`, `\r`, `\t`, `\v`; other locales add letters and spacing
  (`isalpha(3)`, `ctype.texi`). POSIX.1-2008 marks `isascii` obsolete as
  unusable in localized programs (`isalpha(3)` CONFORMING TO).
- `_tolower`/`_toupper` skip the range check entirely (`ctype.h` lines
  228-229): calling them with anything but the exact opposite-case letter is
  undefined; SVID heritage only.
- glibc optimizes `is*`/`to*` to macros/inline expansions over the
  `__ctype_*_loc` tables when optimizing (`ctype.h` `__isctype`,
  `__tobody`).
- musl 1.2.5 uses arithmetic implementations with no locale table and
  supports only "C" and "C.UTF-8" in `setlocale`
  (`musl src/ctype/isalpha.c`: `((unsigned)c|32)-'a' < 26`;
  `src/locale/setlocale.c` line 27), so C-locale behavior is the portable
  baseline there.

## References

- glibc manual: `ctype.texi`, nodes *Classification of Characters*,
  *Case Conversion*
- man3: `isalpha(3)` (all `is*`), `tolower(3)`/`toupper(3)` via `ctype` family
- header: `/usr/include/ctype.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
