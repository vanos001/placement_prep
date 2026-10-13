# `wordexp` / `wordfree` (3) - glibc

> Split from the chapter *glibc: Pattern Matching* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `wordexp.h` |
| Standards | POSIX.1-2001/2008 (XSI; man gate `_XOPEN_SOURCE`) |
| Exported | `wordexp@@GLIBC_2.2.5`, `wordfree@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `race:utent const:env env sig:ALRM timer locale` (`wordexp`); MT-Safe (`wordfree`) (`wordexp(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-wordexp, GLIBC-wordfree |

## Declaration and gates

```c
#include <wordexp.h>

typedef struct {              /* /usr/include/wordexp.h lines 41-46 */
    size_t we_wordc;          /* count of words */
    char **we_wordv;          /* list of expanded words */
    size_t we_offs;           /* slots to reserve in we_wordv */
} wordexp_t;

int wordexp(const char *restrict words, wordexp_t *restrict pwordexp,
            int flags);     /* lines 62-64 */
void wordfree(wordexp_t *wordexp);        /* lines 66-67 */
```

`wordexp.h` itself declares the pair unconditionally (it survives
`gcc -std=c99` preprocessing on this host); `wordexp(3)` still lists
`_XOPEN_SOURCE` as the conforming gate. Flag bits and return codes:
`WRDE_DOOFFS`/`WRDE_APPEND`/`WRDE_NOCMD`/`WRDE_REUSE`/`WRDE_SHOWERR`/
`WRDE_UNDEF` (lines 28-38) and `WRDE_NOSPACE`/`WRDE_BADCHAR`/
`WRDE_BADVAL`/`WRDE_CMDSUB`/`WRDE_SYNTAX` (lines 49-59).

## Semantics

`wordexp` performs the shell's expansion pipeline on the string
`words` -- tilde expansion, parameter substitution, command
substitution, arithmetic expansion, field splitting against `$IFS`,
wildcard expansion, quote removal -- and stores the resulting words in
`we_wordv`, NUL-terminated, counted in `we_wordc` (`wordexp(3)`).
`WRDE_DOOFFS` reserves `we_offs` leading NULL slots; `WRDE_APPEND`
grows a previous result; `WRDE_REUSE` reuses storage when
`wordfree` has not run; `WRDE_UNDEF` and `WRDE_NOCMD` turn undefined
variables and command substitution into errors. `wordfree` releases
the array and its strings. Failure returns one of the `WRDE_*` codes.

## Gotchas and portability

- Security: command substitution means `wordexp` executes `/bin/sh` on
  the caller's behalf -- `$(...)` and backquotes run real commands
  with the process's privileges. Never feed it untrusted input without
  `WRDE_NOCMD`, and audit error paths (`wordexp(3)` DESCRIPTION;
  `WRDE_CMDSUB` exists precisely to opt out).
- The string must not contain unescaped newline or `| & ; < > ( ) { }`
  outside substitution contexts, or `WRDE_BADCHAR`/`WRDE_SYNTAX`
  results.
- Thread-safety: `wordexp` reads the environment, locale, and utmp
  (`race:utent`), and is not signal-safe.
- musl 1.2.5 provides both functions (`musl src/misc/wordexp.c`),
  with a simpler shell-less implementation.

## References

- glibc manual: `pattern.texi` (wordexp mentions), `wordexp(3)`
- man3: `wordexp(3)`, `fnmatch(3)`, `glob(3)`
- headers: `/usr/include/wordexp.h`
- musl: `include/wordexp.h`, `src/misc/wordexp.c`
