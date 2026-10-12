# wordexp(3) - glibc (wordexp / wordfree, WRDE flags)

> POSIX.2 shell-style word expansion inside a library call (manual chapter *Pattern Matching*, section *Word Expansion*). Security-sensitive: it runs the shell's substitution machinery, including command execution.

| Field | Value |
|---|---|
| Header | `wordexp.h` |
| Standards | POSIX.2 (XSI option in POSIX.1-2018) |
| Exported | `wordexp`, `wordfree` both `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `wordexp`: MT-Unsafe race:utent, const:env (man3 ATTRIBUTES; tilde expansion touches utmp); `wordfree`: MT-Safe |
| Ledger ID | `GLIBC-wordexp`, `GLIBC-wordfree` (regex/wordexp table rows) |

## Declaration and gates

```text
int wordexp(const char *words, wordexp_t *pwordexp, int flags);
void wordfree(wordexp_t *pwordexp);
```

`wordexp_t`: `we_wordc` (count), `we_wordv` (NULL-terminated vector), `we_offs` (input-only: leading NULL slots under `WRDE_DOOFFS`) (manual, *Calling Wordexp*).

## Semantics

`wordexp` performs the shell's expansion stages in order: tilde expansion; variable substitution (`$FOO`), command substitution (`` `cmd` `` and `$(cmd)`), arithmetic expansion; field splitting (`IFS`); wildcard expansion (via `glob`); quote removal (manual, *Expansion Stages*). Returns 0 or a `WRDE_*` code: `WRDE_BADCHAR` (unquoted `| & ; < > ( ) { }` or newline), `WRDE_BADVAL` (undefined variable with `WRDE_UNDEF`), `WRDE_CMDSUB` (command substitution with `WRDE_NOCMD`), `WRDE_NOSPACE` (partial results may be stored), `WRDE_SYNTAX` (also covers arithmetic division by zero and overflow). Flags: `WRDE_APPEND`, `WRDE_DOOFFS`, `WRDE_REUSE` (refill a previous vector; refetch `we_wordv` afterwards), `WRDE_SHOWERR` (let command-substitution children inherit stderr; default is a discard stream), `WRDE_NOCMD`, `WRDE_UNDEF`. `wordfree` frees the vector and its strings, not the `wordexp_t` object itself (man3).

## Gotchas and portability

- **Execute-before-parse hazard**: command substitution spawns the named commands. Anything user-controlled reaching `wordexp` without `WRDE_NOCMD` is remote code execution; `WRDE_NOCMD` makes the attempt a `WRDE_CMDSUB` error instead (manual, *Flags for Wordexp*).
- Unquoted shell-metacharacters are hard errors, not shell semantics (man3, *The string argument*).
- musl contrast: musl 1.2.5 implements `wordexp` in `src/misc/wordexp.c` by forking and `execl("/bin/sh", "sh", "-c", ...)` with the expansion output captured through a pipe; under `WRDE_NOCMD` it scans the string first and returns `WRDE_CMDSUB` on any unquoted `$(` or backtick instead of spawning. glibc's implementation strategy is not described in the cached sources - the manual documents only the observable semantics; glibc honors `WRDE_NOCMD` by returning `WRDE_CMDSUB`.

## References

- glibc manual nodes *Expansion Stages*, *Calling Wordexp*, *Flags for Wordexp*; man3 `wordexp.3`; header `wordexp.h`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/misc/wordexp.c`.
