# `tmpfile` / `mkstemp` / `tmpnam` (3) - glibc

> Per-function page for the temporary-file family; see the
> [method page](../../../interface-encyclopedia.md) and the
> [glibc ledger](../../ledger-glibc.md) for coverage status. The stdio family
> documents the same group at
> [../stdio/tmpfile-tmpnam-mkstemp-mkdtemp.md](../stdio/tmpfile-tmpnam-mkstemp-mkdtemp.md)
> (status/1-h covered it there); this page adds the obsolete-marking history
> and the SVID name generators.

| Field | Value |
|---|---|
| Header | `stdio.h` (`tmpfile`, `tmpnam`, `tmpnam_r`, `tempnam`); `stdlib.h` (`mktemp`, `mkstemp`, `mkdtemp`) |
| Standards | ISO C (`tmpfile`, `tmpnam`); POSIX.1-2008 marks `tmpnam` obsolete (man `tmpnam.3`); SVID (`tempnam`, `P_tmpdir`); BSD/OpenBSD (`mkstemp`, `mkdtemp` - "from OpenBSD", manual); Unix (`mktemp`) |
| Exported | `tmpfile`/`tmpnam`/`tmpnam_r`/`tempnam`/`mktemp`/`mkstemp`/`mkdtemp` all `@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `tmpfile` reentrant (manual); `tmpnam(NULL)` MT-Unsafe race:tmpnam/!result (static buffer); `tempnam` reentrant (mallocs); `mkstemp`/`mkdtemp` MT-Safe (manual annotations) |
| Ledger ID | GLIBC-tmpfile (group), GLIBC-tmpnam, GLIBC-tempnam, GLIBC-mktemp, GLIBC-mkstemp, GLIBC-mkdtemp (documented) |

## Declaration and gates

```c
#include <stdio.h>
#include <stdlib.h>

FILE *tmpfile(void);                              /* "wb+", auto-unlinked */
char *tmpnam(char *result);                       /* L_tmpnam buffer */
char *tmpnam_r(char *result);                     /* GNU, NULL in/NULL out */
char *tempnam(const char *dir, const char *prefix);
char *mktemp(char *template);                     /* template, no create */
int mkstemp(char *template);                      /* fd, O_EXCL, 0600 */
char *mkdtemp(char *template);                    /* dir, 0700, OpenBSD */
```

## Semantics

`tmpfile` creates an unnamed binary update file that is deleted when closed
or at program termination - the manual's safe default. The `mktemp`-style
functions rewrite the trailing `XXXXXX` of `template` in place, so string
constants are forbidden (manual). `mkstemp` also opens the file `O_EXCL`
with mode `0600`; creation is race-free by construction because the name
cannot be claimed between generation and open (manual). `mkdtemp` creates a
mode-`0700` directory and returns the name or NULL with `errno` (`EINVAL`
for a template not ending in `XXXXXX`), and "directory creation always works
like open with O_EXCL" (manual). `tmpnam` only *generates* a name; with a
NULL argument it returns an internal static string (manual: non-reentrant).

## Gotchas and portability

- The name-generation functions (`tmpnam`, `tmpnam_r`, `tempnam`, `mktemp`)
  share the same security hole the manual and `tmpnam.3` describe: another
  process can create the name first; open with `O_EXCL` or, better, use
  `tmpfile` or `mkstemp`. POSIX.1-2008 marks `tmpnam` obsolete.
- `tempnam` directory order: `$TMPDIR` (skipped for SUID/SGID programs for
  security), then `dir`, then `P_tmpdir`, then `/tmp`; the result is
  malloc'd and must be freed (manual).
- `TMP_MAX` is a lower bound on distinct `tmpnam` names, never less than 25
  (manual); glibc's own limit is far higher.
- musl 1.2.5: `src/temp/mkstemp.c` funnels into `__mkostemps`, with name
  randomization in `src/temp/__randname.c`.

## References

- glibc manual: `filesys.texi`, node *Temporary Files*
- man3: `tmpfile.3` alias, `tmpnam.3`, `mkstemp.3`, `mkdtemp.3`, `tempnam.3`
- headers: `/usr/include/stdio.h`, `/usr/include/stdlib.h`
- symbols: `nm -D --with-symbol-versions /lib/x86_64-linux-gnu/libc.so.6`
