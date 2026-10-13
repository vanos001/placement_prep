# `catopen` / `catgets` / `catclose` (3) - glibc

> Split from the chapter *glibc: Message Translation* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `nl_types.h` |
| Standards | X/Open portability guides; POSIX.1-2001/2008 (XSI, obsolescent) |
| Exported | `catopen@@GLIBC_2.2.5`, `catgets@@GLIBC_2.2.5`, `catclose@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `env` (`catopen`); MT-Safe (`catgets`, `catclose`) (`catopen(3)`, `catgets(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-catopen, GLIBC-catgets, GLIBC-catclose |

## Declaration and gates

```c
#include <nl_types.h>

#define NL_SETD 1         /* default set   (line 24) */
#define NL_CAT_LOCALE 1   /* XPG4 behavior (line 27) */

typedef void *nl_catd;    /* line 33 */

nl_catd catopen(const char *cat_name, int flag);         /* line 42 */
char *catgets(nl_catd catalog, int set, int number,
              const char *message);                      /* lines 46-48 */
int catclose(nl_catd catalog);                           /* line 50 */
```

No feature-test gate in `/usr/include/nl_types.h`; the trio is XSI
vocabulary.

## Semantics

`catopen` opens a compiled message catalog (built with `gencat`) and
returns a descriptor valid until `catclose` or `execve`; with
`NL_CAT_LOCALE` the language comes from the current `LC_MESSAGES`
locale, otherwise from `LANG`. A relative `cat_name` is resolved via
the `NLSPATH` environment variable with `%N` substitution, falling
back to an implementation-defined path (`catopen(3)`). `catgets`
fetches message `number` from `set`, returning the fourth argument as
the default when the catalog is not available; the text lives in an
internal buffer, so applications must copy it before modifying, and
the string is always NUL-terminated. `catclose` closes the catalog
and returns 0, or -1 (`catgets(3)`, manual node *The catgets
Functions*).

## Gotchas and portability

- glibc's own manual labels the X/Open catgets model the "lame" way
  and steers toward gettext; musl 1.2.5 nevertheless implements both
  (`src/locale/catgets.c`, plus a gettext/.mo runtime in
  `src/locale/dcngettext.c`).
- Descriptors can be invalidated when the `LC_MESSAGES` locale
  changes mid-run (`catopen(3)`).
- Failure reporting is thin: `catopen` returns `(nl_catd) -1` with
  `errno` from the underlying `open`; `catgets` silently returns the
  default string, so a wrong set/number looks like success.
- musl resolves catalogs without `NLSPATH` lookups; behavior differs
  on edge cases.

## Errors

`catopen`: whatever `open(2)` reports (`EACCES`, `ENOENT`, ...).
`catclose`: -1 on failure; `catgets` reports nothing.

## References

- glibc manual: `message.texi`, nodes *Message catalogs a la X/Open*,
  *The catgets Functions*
- man3: `catopen(3)`, `catgets(3)`
- headers: `/usr/include/nl_types.h`
- musl: `src/locale/catopen.c`, `catgets.c`, `catclose.c`
