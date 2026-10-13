# `gettext` / `dgettext` / `dcgettext` / `ngettext` (3) - glibc

> Per-function page for the GNU (Uniforum) message-translation family; see
> the [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. The X/Open
> `catgets` rival API is on [catgets-catopen.md](./catgets-catopen.md).

| Field | Value |
|---|---|
| Header | `libintl.h` (declarations unconditional on this host) |
| Standards | The manual tags the family `POSIX-1.2024, libintl.h` (master manual); historically GNU/Sun Uniforum ("There never was a real standard defined", manual) |
| Exported | `gettext`, `dgettext`, `dcgettext`, `ngettext`, `dngettext`, `dcngettext`, `textdomain`, `bindtextdomain`, `bind_textdomain_codeset` all `@@GLIBC_2.2.5` (nm, host glibc 2.41; weak `W` symbols) |
| Thread-safety | MT-Safe env (they read environment variables); `textdomain`/`bindtextdomain` AS-Unsafe lock/heap AC-Unsafe lock/mem (manual annotations) |
| Ledger ID | GLIBC-gettext, GLIBC-dgettext, GLIBC-dcgettext, GLIBC-ngettext, GLIBC-dngettext, GLIBC-dcngettext, GLIBC-textdomain, GLIBC-bindtextdomain (documented rows) |

## Declaration and gates

```c
#include <libintl.h>

char *gettext(const char *msgid);
char *dgettext(const char *domainname, const char *msgid);
char *dcgettext(const char *domainname, const char *msgid, int category);
char *ngettext(const char *msgid1, const char *msgid2,
               unsigned long int n);
char *dngettext(const char *domain, const char *msgid1,
                const char *msgid2, unsigned long int n);
char *dcngettext(const char *domain, const char *msgid1,
                 const char *msgid2, unsigned long int n, int category);
char *textdomain(const char *domainname);
char *bindtextdomain(const char *domainname, const char *dirname);
```

## Semantics

The message *string itself is the key*: `gettext` looks up `msgid` in the
current message catalogs and returns the translation, or `msgid` unchanged
(manual, *Translation with gettext*). `dgettext` names a domain; `dcgettext`
adds the locale category, for which the manual says `LC_MESSAGES` is the
only sensible value and `LC_ALL` must not be used. `ngettext` selects a
plural form using translator rules stored in the catalog header
(`Plural-Forms:` entry); with no catalog it returns `msgid1` when `n == 1`,
else `msgid2` (manual, *Advanced gettext functions*). `textdomain` sets the
default domain (initially `messages`; NULL queries; empty string resets)
and `bindtextdomain` binds a domain to the directory whose hierarchy holds
`dir/locale/LC_category/domain.mo` (manual, *Locating gettext catalog*).

## Gotchas and portability

- The `char *` return is "an anachronism": never modify the returned string
  (manual, all three lookup functions).
- `gettext` does not modify `errno` - the manual motivates it with
  `printf(gettext("...%m\n"))`; detect missing catalogs only by comparing
  the result against the argument.
- Constant `msgid` translations are cached by the implementation (manual:
  "This optimization is actually implemented").
- The manual documents `LANGUAGE` (locale.texi vindex) as the GNU extension
  for a user preference list; catalog *file* placement is
  `bindtextdomain`'s job. No `TEXTDOMAIN`/`TEXTDOMAINDIR` variables appear
  in the cached manual or headers - not claimed here.
- musl 1.2.5: implements the family in `src/locale/` (`textdomain.c` has
  `gettext` as `dgettext(0, msgid)`; `dcngettext.c` + `__mo_lookup` read
  `.mo` files); `bind_textdomain_codeset.c` rejects non-UTF-8 with `EINVAL`
  and returns NULL.

## References

- glibc manual: `message.texi`, nodes *The Uniforum approach*, *Translation
  with gettext*, *Locating gettext catalog*, *Advanced gettext functions*
- headers: `/usr/include/libintl.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
