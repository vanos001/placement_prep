# `catgets` / `catopen` (3) - glibc

> Per-function page for the X/Open message-catalog family; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. The GNU
> gettext alternative is documented on
> [gettext-dcgettext-dngettext.md](./gettext-dcgettext-dngettext.md).

| Field | Value |
|---|---|
| Header | `nl_types.h` (`nl_catd`, `NL_SETD`, `NL_CAT_LOCALE`, all three functions) |
| Standards | X/Open (manual: "Message catalogs a la X/Open"); XSI-era legacy kept for compatibility - the manual itself contrasts it with the Uniforum approach it prefers for free software |
| Exported | `catopen`/`catgets`/`catclose` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `catopen` MT-Safe env (reads `NLSPATH`/locale environment); `catgets` and `catclose` MT-Safe/AS-Safe/AC-Safe annotations differ: `catgets` fully safe, `catclose` AS-Unsafe heap AC-Unsafe mem (manual annotations) |
| Ledger ID | GLIBC-catopen, GLIBC-catgets, GLIBC-catclose (researched rows, catgets group) |

## Declaration and gates

```c
#include <nl_types.h>

nl_catd catopen(const char *cat_name, int flag);   /* flag: 0 or NL_CAT_LOCALE */
char *catgets(nl_catd catalog, int set_id, int msg_id, const char *s);
int catclose(nl_catd catalog);
/* nl_catd is an opaque descriptor; on this host typedef void *nl_catd. */
```

## Semantics

`catopen` locates and loads the catalog named `cat_name` and returns an
opaque handle, or `(nl_catd) -1` with `errno` set (manual). Unless the name
contains a slash (then `NLSPATH` is bypassed and the path is taken verbatim,
which the manual calls non-portable), the search path comes from `NLSPATH`
as a printf-like template: `%N` catalog name, `%L` current locale, `%l`/`%t`
`%c` language/territory/codeset parts, `%%` literal percent; default
`prefix/share/locale/%L/%N:...`. With `NL_CAT_LOCALE` the locale is the
`LC_MESSAGES` selection; with flag 0 the legacy `$LANG` is used (manual).
`catgets` indexes by unique `(set, message)` number pairs and returns the
translation, or the default string `s` when the tuple is missing; `catclose`
frees the catalog, returning 0 or -1 with `EBADF` (manual). Errors listed:
`EBADF` (no such catalog) and `ENOMSG` (set/message tuple absent).

## Gotchas and portability

- Detecting failure of `catgets` requires pointer comparison with the
  default string (manual example); errno is best-effort.
- The number-key scheme forces the programmer to keep a running registry of
  set/message IDs across the project - the coordination burden the manual
  describes before introducing gettext.
- musl 1.2.5: `src/locale/catopen.c` mmaps the gencat file (magic
  `0xff88ff89`, size cross-check) and `catgets.c` binary-searches the
  mmap, setting `ENOMSG` on misses - a compact XSI implementation.

## References

- glibc manual: `message.texi`, nodes *Message catalogs a la X/Open*, *The
  catgets Functions*, *The message catalog files*, *The gencat program*
- man3: `catgets.3`, `catopen.3`
- headers: `/usr/include/nl_types.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
