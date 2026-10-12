# `clearenv` / `getsubopt` (3) - glibc

> Split from the chapter *glibc: Program Basics* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `stdlib.h` (both; `clearenv` under `__USE_MISC`, `getsubopt` under `__USE_XOPEN_EXTENDED` / `__USE_XOPEN2K8`) |
| Standards | SVID (`clearenv`); X/Open, POSIX.1-2008 (`getsubopt`) |
| Exported | `clearenv@@GLIBC_2.2.5`, `getsubopt@@GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Unsafe `const:env` (`clearenv`); MT-Safe (`getsubopt`) (`clearenv(3)`, `getsubopt(3)` ATTRIBUTES) |
| Ledger ID | GLIBC-clearenv, GLIBC-getsubopt |

## Declaration and gates

```c
#include <stdlib.h>

int clearenv(void);     /* __USE_MISC block, lines 800-804 */

int getsubopt(char **restrict optionp, char *const *restrict tokens,
              char **restrict valuep);   /* lines 1096-1100 */
```

Gates per the man pages: `clearenv` needs `_DEFAULT_SOURCE` (glibc
>= 2.19; before that `_SVID_SOURCE`/`_BSD_SOURCE`); `getsubopt` needs
`_XOPEN_SOURCE >= 500` or `_POSIX_C_SOURCE >= 200809L` (`clearenv(3)`,
`getsubopt(3)`).

## Semantics

`clearenv` discards every name-value pair by setting the global
`environ` to NULL; afterwards `putenv`/`setenv` rebuild the
environment. It returns zero on success, nonzero on failure
(`clearenv(3)`). `getsubopt` splits the comma-separated suboption
list pointed to by `*optionp` -- typically the argument of a
`getopt(3)` `-o`-style option, e.g. `ro,name=xyz` -- against a
NULL-terminated `tokens` array. For the first unprocessed suboption
it returns the matching token index; a `name=value` pair sets
`*valuep` to the value substring (the first `=` and the following
comma are overwritten with NUL bytes, so the input string is
destroyed); a recognized bare name sets `*valuep` to NULL. Unknown
suboptions return -1 with `*valuep` holding the whole `name[=value]`
text, and `*optionp` always advances to the rest of the string
(`getsubopt(3)`, manual node *Suboptions*).

## Gotchas and portability

- `clearenv` leaks: the old strings are not freed. Direct
  `environ = NULL` is the equivalent; some environments treat that as
  sufficient (`clearenv(3)` NOTES).
- `clearenv` was proposed for POSIX.1 but not adopted -- it remains
  per-platform vocabulary (comment above the declaration in
  `/usr/include/stdlib.h`).
- `getsubopt` mutates its input in place; keep a copy if the option
  string is needed again.
- musl 1.2.5: `clearenv` (`src/env/clearenv.c`) and `getsubopt`
  (`src/misc/getsubopt.c`) both present.

## Errors

`clearenv` returns nonzero on failure but sets no documented errno;
`getsubopt` reports via its return value, not `errno`.

## References

- glibc manual: `startup.texi`, nodes *Environment Access*,
  *Suboptions*
- man3: `clearenv(3)`, `getsubopt(3)`
- headers: `/usr/include/stdlib.h`
- musl: `src/env/clearenv.c`, `src/misc/getsubopt.c`
