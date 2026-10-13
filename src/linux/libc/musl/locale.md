# musl: locale

| Field | Value |
|---|---|
| musl version | 1.2.5 (WHATSNEW) |
| Key source files | `src/locale/{setlocale.c,locale_map.c,newlocale.c,uselocale.c,localeconv.c,iconv.c,dcngettext.c,catgets.c,langinfo.c}`, `src/ctype/isalpha.c` (and sibling `is*_` files) |
| glibc counterpart pages | [setlocale/localeconv](../glibc/fs/setlocale-localeconv.md), [nl_langinfo](../glibc/fs/nl_langinfo.md), [gettext family](../glibc/fs/gettext-dcgettext-dngettext.md), [catgets](../glibc/fs/catgets-catopen.md), [ctype isX](../glibc/strings/ctype-isalpha-isdigit-toLower.md), [isX_l variants](../glibc/strings/isalpha-l-variants.md) |
| Ledger | MUSL-family-locale / -iconv / -libintl / -langinfo / -ctype rows; ledger-musl.md `locale.h` (6), `iconv.h` (3), `libintl.h` (9), `langinfo.h` (2), `ctype.h` (29) |

## Implementation notes

Out of the box only C/POSIX and C.UTF-8 exist. `__get_locale`
(`src/locale/locale_map.c`) resolves `LC_ALL`, then the per-category variable,
then `LANG`; a name is builtin (`C`, `C.UTF-8`, `POSIX`) or must be found as a
file under `MUSL_LOCPATH` (skipped for setuid; there is no compiled-in default
path). The musl-locales add-on project supplies those files (Adelie Linux
repo, git.adelielinux.org/adelie/musl-locales). `setlocale` serializes LC_ALL
as `;`-joined parts (`src/locale/setlocale.c`). A gettext runtime exists:
`dcngettext.c` maps `.mo` files per bound domain and `pleval.c` evaluates
plural forms; catgets is implemented too (`catgets.c`).

## Deltas vs glibc (verified)

- `iconv` converts only between charsets compiled into a fixed table
  (`src/locale/iconv.c`: UTF-8/16/32, UCS2, ASCII, EUC-JP, SHIFT_JIS,
  ISO-2022-JP, GB18030/GBK/GB2312, BIG5, EUC-KR, plus `codepages.h` legacy
  pages). glibc loads runtime gconv modules; this host ships 256 under
  /usr/lib/x86_64-linux-gnu/gconv.
- `ctype.h` `_l` functions ignore their locale argument: `__isalpha_l`
  returns `isalpha(c)` (`src/ctype/isalpha.c`), same pattern for the family.
- No full locale data: collation/monetary/numeric behavior is C-locale only;
  `strcoll`/`strxfrm` compare bytes (`src/locale/strcoll.c`, `strxfrm.c`).
- `newlocale` returns shared builtin locale objects when possible
  (`src/locale/newlocale.c`).

## Porting notes

Programs expecting working `setlocale(LC_ALL, "")` behavior beyond C/UTF-8
(sorting, money, dates) need the musl-locales files and still get far less
than glibc's locales. `iconv_open` for a charset outside the table fails
with errno EINVAL (`src/locale/iconv.c`); gconv-dependent transliteration
has no equivalent.
