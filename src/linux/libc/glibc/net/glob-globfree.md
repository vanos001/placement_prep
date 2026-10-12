# glob(3) - glibc (glob / globfree, GLOB flags, tilde, GLOB_ALTDIRFUNC)

> Filename-pattern expansion the way the shell does it (manual chapter *Pattern Matching*, section *Globbing*). Single-string matching is [fnmatch](./fnmatch.md).

| Field | Value |
|---|---|
| Header | `glob.h` |
| Standards | POSIX.2 (`glob`, `globfree`, the standard flags); `GLOB_*` GNU extensions per the manual's *More Flags* node; `glob64` GNU |
| Exported | `glob` default `GLIBC_2.27` with compat `@GLIBC_2.2.5`; `glob64` same pair; `globfree`, `globfree64` `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `glob`: MT-Unsafe race:utent, env, sig:ALRM, timer, locale; `globfree`: MT-Safe (man3 ATTRIBUTES) |
| Ledger ID | `GLIBC-glob` (Grouped FULL), `GLIBC-glob64`, `GLIBC-globfree`, `GLIBC-globfree64` (Grouped rows) |

## Declaration and gates

```text
int glob(const char *pattern, int flags,
         int (*errfunc)(const char *epath, int eerrno), glob_t *pglob);
void globfree(glob_t *pglob);
```

`glob_t` carries `gl_pathc`, `gl_pathv` (NULL-terminated word vector), `gl_offs`, and under `GLOB_ALTDIRFUNC` the hooks `gl_opendir`, `gl_readdir`, `gl_closedir`, `gl_stat`, `gl_lstat` (manual, *Calling Glob*).

## Semantics

`glob` expands `pattern` against the filesystem, allocating each result string and the vector; results are sorted alphabetically unless `GLOB_NOSORT`. Standard flags: `GLOB_APPEND` (append to a previous result; never cache `gl_pathv` across calls, it can move), `GLOB_DOOFFS` (reserve `gl_offs` leading NULL slots), `GLOB_ERR` (abort on unreadable directory, otherwise consult `errfunc(path, errno)`: nonzero return aborts), `GLOB_MARK` (append `/` to directories), `GLOB_NOCHECK` (return the pattern itself when nothing matches), `GLOB_NOESCAPE` (backslash is literal), `GLOB_NOSORT`. GNU flags: `GLOB_BRACE` (csh `{a,b}` expansion), `GLOB_TILDE`/`GLOB_TILDE_CHECK` (expand `~` and `~user` via `getlogin`/`getpwnam`; the CHECK form fails with `GLOB_NOMATCH` instead of leaving the pattern), `GLOB_NOMAGIC`, `GLOB_ONLYDIR` (a hint only, callers must still filter), `GLOB_PERIOD`, `GLOB_ALTDIRFUNC` (use the caller's directory functions - the hook virtual filesystems sit on). Returns 0, `GLOB_NOSPACE`, `GLOB_ABORTED`, or `GLOB_NOMATCH`; on error partial results stay in `*pglob`. `globfree` releases the vector and strings.

## Gotchas and portability

- glibc 2.27 rewrote `glob` to sync with gnulib; the symbol version pair `GLIBC_2.2.5`/`GLIBC_2.27` in nm reflects that.
- musl contrast: musl 1.2.5 implements `glob` in `src/regex/glob.c` with the POSIX flags plus `GLOB_PERIOD`, `GLOB_TILDE`, `GLOB_TILDE_CHECK`; its `include/glob.h` does not define `GLOB_BRACE`, `GLOB_ALTDIRFUNC`, `GLOB_NOMAGIC`, `GLOB_ONLYDIR` or `GLOB_MAGCHAR` at all.

## References

- glibc manual nodes *Calling Glob*, *Flags for Globbing*, *More Flags for Globbing*; man3 `glob.3`.
- Header `glob.h`; `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/misc/glob.c`.
