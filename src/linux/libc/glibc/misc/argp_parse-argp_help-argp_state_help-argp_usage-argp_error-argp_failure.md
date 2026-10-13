# `argp_parse` / `argp_help` / `argp_state_help` / `argp_usage` / `argp_error` / `argp_failure` (3) - glibc

> Split from the chapter *glibc: Argp* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| Header | `argp.h` (GNU-specific header; no feature-test gate needed) |
| Standards | GNU extension -- glibc-only |
| Exported | `argp_parse@@GLIBC_2.2.5`, `argp_help@@GLIBC_2.2.5`, `argp_state_help@@GLIBC_2.2.5`, `argp_usage@@GLIBC_2.2.5`, `argp_error@@GLIBC_2.2.5`, `argp_failure@@GLIBC_2.2.5` (all weak `W` in nm, host glibc 2.41) |
| Thread-safety | Not stated: no man ATTRIBUTES table exists for argp; manual safety comments absent (`argp.texi`) |
| Ledger ID | GLIBC-argp_parse, GLIBC-argp_help, GLIBC-argp_state_help, GLIBC-argp_usage, GLIBC-argp_error, GLIBC-argp_failure |

## Declaration and gates

```c
#include <argp.h>          /* /usr/include/argp.h */

typedef error_t (*argp_parser_t)(int key, char *arg,
                                 struct argp_state *state);  /* lines 113-115 */

extern error_t argp_parse(const struct argp *restrict argp,
                          int argc, char **restrict argv,
                          unsigned flags, int *restrict arg_index,
                          void *restrict input);             /* lines 370-375 */
extern void argp_help(const struct argp *restrict argp,
                      FILE *restrict stream, unsigned flags,
                      char *restrict name);                  /* lines 439-443 */
extern void argp_state_help(const struct argp_state *restrict state,
                            FILE *restrict stream,
                            unsigned int flags);             /* lines 456-459 */
extern void argp_usage(const struct argp_state *state);      /* line 464 */
extern void argp_error(const struct argp_state *restrict state,
                       const char *restrict fmt, ...);       /* lines 472-475 */
extern void argp_failure(const struct argp_state *restrict state,
                         int status, int errnum,
                         const char *restrict fmt, ...);     /* lines 482-486 */
```

`argp.h` compiles under `gcc -std=c99` with no feature macro (verified
on this host); being a GNU header, it simply does not exist outside
glibc -- musl 1.2.5 ships neither `argp.h` nor any argp source
(verified absence).

## Semantics

`argp_parse` drives the whole command line: each option dispatches to
a parser callback that returns `0`, `ARGP_ERR_UNKNOWN`, or an error;
on completion it returns `0` or the parser's error. It can print help
and exit unless `ARGP_NO_HELP` is set (`argp.h` lines 366-369).
`argp_help` prints a formatted usage/help text for an argp to `stream`
under `ARGP_HELP_*` flags (lines 408-434); `argp_state_help` is its
in-parser variant, honoring the state's flags. `argp_usage` emits the
standard usage message. `argp_error` reports a parsing error with a
printf-style suffix and a "Try ... --help" hint; `argp_failure`
reports a runtime failure with `errnum` -- both exit with the program
name prefix unless `ARGP_NO_EXIT`/`ARGP_NO_ERRS` inhibit them
(`argp.h` comments; manual *Argp Helper Functions*). The exit status
defaults to `EX_USAGE` via `argp_err_exit_status` (lines 402-406).

## Gotchas and portability

- The helpers "may or may not exit": callers must be prepared for
  return and propagate an error (`argp.h` lines 448-454).
- glibc-only: musl lacks argp entirely, so portable code needs a
  getopt(3) fallback or a bundled argp copy.
- `argp_parse` allocates and calls `exit` paths -- watch it in
  long-running daemons embedding option parsing.

## References

- glibc manual: `argp.texi`, nodes *Argp*, *Argp Helper Functions*,
  *Argp Help*, *Argp Flags*
- header: `/usr/include/argp.h`
- symbols: `nm -D libc.so.6` (weak `W` bindings)
- musl: no `argp.h`, no `src/argp` (verified absence)
