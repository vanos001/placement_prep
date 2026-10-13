# `regcomp` / `regexec` / `regerror` / `regfree` (3) - glibc

> Split from the chapter *glibc: Pattern Matching* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `regex.h` (`REG_STARTEND` under `__USE_GNU`) |
| Standards | POSIX.1-2001/2008 (`REG_STARTEND` is a BSD extension) |
| Exported | `regcomp@@GLIBC_2.2.5`, `regexec@@GLIBC_2.3.4` plus compat `regexec@GLIBC_2.2.5`, `regerror@@GLIBC_2.2.5`, `regfree@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe `locale` (`regcomp`, `regexec`); MT-Safe `env` (`regerror`); MT-Safe (`regfree`) (`regex(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-regcomp, GLIBC-regexec, GLIBC-regerror, GLIBC-regfree |

## Declaration and gates

```c
#include <regex.h>

int regcomp(regex_t *restrict preg, const char *restrict regex,
            int cflags);                                   /* lines 679-681 */
int regexec(const regex_t *restrict preg, const char *restrict string,
            size_t nmatch, regmatch_t pmatch[restrict],
            int eflags);                                   /* lines 683-687 */
size_t regerror(int errcode, const regex_t *restrict preg,
                char *restrict errbuf, size_t errbuf_size); /* lines 689-691 */
void regfree(regex_t *preg);                               /* line 693 */
```

The four prototypes are unconditional in `/usr/include/regex.h`.
Compile flags: `REG_EXTENDED` (line 310), `REG_ICASE` (314),
`REG_NEWLINE` (319), `REG_NOSUB` (323); exec flags: `REG_NOTBOL`
(333), `REG_NOTEOL` (336); `REG_STARTEND` (340) is `__USE_GNU`-gated
BSD vocabulary.

## Semantics

`regcomp` translates `regex` into a pattern buffer; on failure it
returns an error *code* (not -1) from the `REG_*` error set, and
`regerror` maps such a code into a printable string, returning the
buffer size it needs. `regexec` matches a NUL-terminated string against
the buffer and returns 0 or `REG_NOMATCH`; unless the buffer was
compiled with `REG_NOSUB`, it fills `pmatch[0..nmatch-1]` with
`regmatch_t { regoff_t rm_so, rm_eo }` offsets -- `pmatch[0]` is the
whole match, `pmatch[i]` the i-th parenthesized group, so N groups need
`nmatch >= N+1`, and unused entries hold -1 (`regex(3)`, manual *POSIX
Regexp Compilation*). `regfree` releases the buffer's allocations.

## Gotchas and portability

- `regcomp` failing is an error code, never -1 with `errno`; forgetting
  that is the classic portability bug.
- Without `REG_EXTENDED` the pattern is parsed as Basic Regular
  Expression syntax (`regex(3)`).
- `REG_STARTEND` matches a delimited range -- embedded NUL bytes and no
  `strlen` on big buffers -- but is not POSIX; it stays outside musl.
- glibc split `regexec` into a new symbol version at 2.3.4; old
  binaries keep `regexec@GLIBC_2.2.5` (visible in nm output).
- `REG_EEND` and `REG_ESIZE` are glibc extras, not POSIX.2.
- musl 1.2.5 provides the POSIX four (`musl src/regex/regcomp.c`,
  `regexec.c`, `regerror.c`; TRE-based).

## References

- glibc manual: `pattern.texi`, nodes *POSIX Regexp Compilation*,
  *Flags for POSIX Regexps*, *Matching POSIX Regexps*
- man3: `regex(3)`, `regex(7)`
- headers: `/usr/include/regex.h`
- musl: `src/regex/`
