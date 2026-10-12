# `strsignal` / `psignal` / `sigdescr_np` / `sigabbrev_np` (3) - glibc

> Split from the chapter *glibc: strings, ctype and stdlib arithmetic* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `string.h` (`psignal`: `signal.h`) |
| Standards | POSIX.1-2008 (`strsignal`, `psiginfo`); BSD (`psignal`); GNU (`strsignal` origin, `sigdescr_np`, `sigabbrev_np`) |
| Exported | `strsignal@@GLIBC_2.2.5`, `psignal@@GLIBC_2.2.5`, `sigdescr_np@@GLIBC_2.32` (weak), `sigabbrev_np@@GLIBC_2.32`; compat-only `sys_siglist@GLIBC_2.2.5`, `sys_siglist@GLIBC_2.3.3` (nm, host glibc 2.41) |
| Thread-safety | `strsignal`: MT-Unsafe race:strsignal locale; `psignal`: MT-Safe locale; `sigdescr_np`, `sigabbrev_np`: MT-Safe (`strsignal(3)`, `psignal(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-strsignal, GLIBC-psignal, GLIBC-sigdescr_np, GLIBC-sigabbrev_np |

## Declaration and gates

```c
#include <string.h>
char *strsignal(int sig);                /* __USE_XOPEN2K8 in string.h */
const char *sigdescr_np(int sig);        /* __USE_GNU */
const char *sigabbrev_np(int sig);       /* __USE_GNU */

#include <signal.h>
void psignal(int sig, const char *s);    /* _DEFAULT_SOURCE since 2.19 */
```

Gate history per `strsignal(3)`/`psignal(3)` SYNOPSIS: `strsignal`
`_POSIX_C_SOURCE >= 200809L` (glibc 2.10-2.31), `_GNU_SOURCE` before;
`psignal` `_DEFAULT_SOURCE` since glibc 2.19, `_BSD_SOURCE || _SVID_SOURCE`
before.

## Semantics

`strsignal` returns a message describing signal `sig`, localized via
`LC_MESSAGES`; the string is valid only until the next `strsignal` call and
must not be modified (`strsignal(3)`, manual `signal.texi` *Signal
Messages*). `psignal` prints `s: <description>` to `stderr`, omitting the
prefix when `s` is NULL or empty (`psignal(3)`). `sigdescr_np` returns the
untranslated description ("Hangup") and `sigabbrev_np` the abbreviation
("INT"); both return `NULL` for invalid signal numbers and point to storage
that lives for the whole program (`strsignal(3)`, manual *Signal Messages*).

## Gotchas and portability

- `strsignal` keeps per-thread state but falls back to a shared static
  buffer if TSD allocation fails; the manual marks it
  `mtasurace:strsignal` and lists `asucorrupt`/`ascuheap` hazards
  (`signal.texi` *Signal Messages* safety block). Signal handlers should
  prefer the `_np` pair, which the manual marks plain MT-Safe/AS-safe.
- `sigdescr_np`/`sigabbrev_np` are glibc 2.32 additions (NEWS under
  *Version 2.32*: "sigdescr_np does not translate the returned string"),
  introduced to replace the deprecated `sys_siglist` array.
- `sys_siglist` is gone as a *default* symbol since glibc 2.32
  (`strsignal(3)` VERSIONS cites glibc commit b1ccfc061feee9ce6); nm on this
  host confirms only non-default compat versions remain
  (`sys_siglist@GLIBC_2.2.5`, `@GLIBC_2.3.3`).
- Invalid signal numbers: `strsignal` returns an "unknown signal" message
  on Linux; some systems return `NULL` instead (`strsignal(3)` RETURN
  VALUE).
- `psignal` writes to `stderr`, so it is neither async-signal-safe nor
  suitable inside signal handlers that must not touch stdio
  (`psignal(3)` ATTRIBUTES: MT-Safe locale only).
- musl 1.2.5 provides `strsignal` (`musl src/string/strsignal.c`) but not
  the `_np` pair (absent from `musl include/string.h`).

## References

- glibc manual: `signal.texi`, subsection *Signal Messages*
- man3: `strsignal(3)` (covers `sigdescr_np`, `sigabbrev_np` via `.so`
  alias `sigdescr_np.3`), `psignal(3)`
- headers: `/usr/include/string.h`, `/usr/include/signal.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
