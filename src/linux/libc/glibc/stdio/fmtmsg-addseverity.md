# `fmtmsg` / `addseverity` (3) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the
> per-function layout; see the [method page](../../../interface-encyclopedia.md)
> and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `fmtmsg.h` (`addseverity` under `__USE_MISC`; `fmtmsg` unconditional) |
| Standards | XPG4.2 / POSIX.1-2001 (`fmtmsg`); GNU/SVID (`addseverity`) |
| Exported | `fmtmsg@@GLIBC_2.2.5`, `addseverity@@GLIBC_2.2.5` (weak) (nm, host glibc 2.41) |
| Thread-safety | `fmtmsg`: glibc >= 2.16 MT-Safe, glibc < 2.16 MT-Unsafe (`fmtmsg(3)` ATTRIBUTES); `addseverity`: manual safety notes (lock/alloc caveats) |
| Ledger ID | GLIBC-fmtmsg, GLIBC-addseverity |

## Declaration and gates

```c
#include <fmtmsg.h>

int fmtmsg(long classification, const char *label, int severity,
           const char *text, const char *action, const char *tag);

int addseverity(int severity, const char *string);   /* __USE_MISC */
```

`fmtmsg` is declared unconditionally in `/usr/include/fmtmsg.h` (lines
94-96); `addseverity` is in its `#ifdef __USE_MISC` block (lines 97-101).
The header also defines the `MM_HARD`/`MM_SOFT`/... classification bits,
severities `MM_NOSEV`-`MM_INFO`, the `MM_NULL*` dummy arguments and the
return codes `MM_OK`/`MM_NOTOK`/`MM_NOMSG`/`MM_NOCON` (lines 27-88).

## Semantics

`fmtmsg` writes a structured message to stderr and/or the console as
selected by the classification bits (`MM_PRINT`, `MM_CONSOLE` plus one
source, detector and recoverability value each). The stderr layout is
`label: severity-string: text` followed by `TO FIX: action tag` for the
non-omitted fields; `MM_NULL*` arguments drop fields (`fmtmsg(3)`,
manual *Printing Formatted Messages*). It returns `MM_OK`, `MM_NOMSG`
(stderr failed), `MM_NOCON` (console failed) or `MM_NOTOK` (total
failure or bad parameters). `addseverity` registers an integer severity
level (values above the five built-ins) printed as `string`; passing a
null `string` removes the class, and the built-in classes can be
neither overridden nor removed (manual, *Adding Severity Classes*).

## Gotchas and portability

- `MSGVERB` (colon-separated keywords `label`, `severity`, `text`,
  `action`, `tag`) suppresses stderr fields; `SEV_LEVEL`
  (`severity-keyword,level,printstring`, level > 4) adds classes via
  the environment -- glibc extension, not XPG (`fmtmsg(3)` ENVIRONMENT).
- The label must be two colon-separated parts of at most 10 and 14
  characters (`fmtmsg(3)`).
- musl 1.2.5: `fmtmsg` present (`musl src/misc/fmtmsg.c`), but
  `addseverity` is absent (verified: no declaration or source).

## References

- glibc manual: `stdio.texi`, nodes *Formatted Messages*,
  *Printing Formatted Messages*, *Adding Severity Classes*
- man3: `fmtmsg(3)` (covers `addseverity`)
- headers: `/usr/include/fmtmsg.h`
- symbols: `nm -D --with-symbol-versions libc.so.6`
