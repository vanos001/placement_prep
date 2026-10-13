# regcomp(3) - glibc (regcomp / regexec / regerror / regfree)

> POSIX.2 regular expressions (manual chapter *Pattern Matching*, section *Regular Expression Matching*). glibc also ships the older GNU `re_comp`/`re_exec` interface; only the POSIX interface is documented here, as the manual does.

| Field | Value |
|---|---|
| Header | `regex.h` |
| Standards | POSIX.2 (tracked by POSIX.1-2018); `REG_STARTEND` is a glibc extension |
| Exported | `regcomp`, `regerror`, `regfree` `GLIBC_2.2.5`; `regexec` default `GLIBC_2.3.4` with compat `@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `regcomp`, `regexec`, `regerror`, `regfree`: MT-Safe locale (manual safety annotations) |
| Ledger ID | `GLIBC-regcomp`, `GLIBC-regexec`, `GLIBC-regerror`, `GLIBC-regfree` (regex table rows) |

## Declaration and gates

```text
int regcomp(regex_t *restrict compiled, const char *restrict pattern, int cflags);
int regexec(const regex_t *restrict compiled, const char *restrict string,
            size_t nmatch, regmatch_t matchptr[restrict], int eflags);
size_t regerror(int errcode, const regex_t *restrict compiled,
                char *restrict buffer, size_t length);
void regfree(regex_t *compiled);
```

Compile flags: `REG_EXTENDED` (ERE instead of BRE), `REG_ICASE`, `REG_NOSUB`, `REG_NEWLINE` (`^`/`$`/`.`/`[^...]` become line-sensitive). Exec flags: `REG_NOTBOL`, `REG_NOTEOL`, and glibc's `REG_STARTEND` (`regex.h`: match `string[start..end)` via a `regmatch_t`-like pair). `regmatch_t` holds `rm_so`/`rm_eo` offsets; `regex.h` types `regoff_t` as `ssize_t` to satisfy the POSIX.1-2008 "at least as wide as ssize_t" rule (header comment).

## Semantics

`regcomp` translates `pattern` into `*compiled` for fast matching and stores the subexpression count in `compiled->re_nsub`; with `REG_NOSUB` subexpression tracking is omitted and `regexec` may be called with `nmatch == 0`/NULL. `regcomp` returns 0 or a `REG_*` error code (`REG_BADPAT`, `REG_EBRACK`, `REG_EPAREN`, `REG_EBRACE`, `REG_BADBR`, `REG_BADRPT`, `REG_ECOLLATE`, `REG_ECTYPE`, `REG_EESCAPE`, `REG_ESUBREG`, `REG_ERANGE`, `REG_ESPACE` - manual table). `regexec` returns 0 on match, `REG_NOMATCH` (not really an error) or `REG_ESPACE`; subexpression offsets land in `matchptr[0]` = whole match, `[1..]` = groups, `-1` offsets for groups that did not participate (manual, *Regexp Subexpressions*). `regerror` renders any code into `buffer` and returns the length actually needed; `regfree` releases the compiled object.

## Gotchas and portability

- "You must match the regular expression with the same set of current locales that were in effect when you compiled" (manual, *Matching POSIX Regexps*).
- musl implements `regcomp`/`regexec` in `src/regex/regcomp.c` with the same POSIX surface, no `REG_STARTEND` (delta noted in the [musl catalog](../../musl/overview.md)).

## References

- glibc manual section *Regular Expression Matching*; man3 `regex.3`, `regcomp.3`; header `regex.h`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/regex/`.
