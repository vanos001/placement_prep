# `popen` / `pclose` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-popen (group) |
| Header | `stdio.h` |
| Provenance | POSIX.2, SVID, BSD |
| Status | documented |

**Signature** -- `FILE *popen(const char *command, const char *mode);`
`int pclose(FILE *stream);`

**Semantics** -- `popen` creates a pipe, forks, and runs `command` via
`/bin/sh -c` (`popen(3)`); mode `"r"` reads the child's
stdout (child inherits the caller's stdin), `"w"` writes its stdin.
glibc since 2.9 accepts mode letter `e` to set `FD_CLOEXEC` on the
descriptor. The stream is block buffered by default (`popen(3)`) --
flush before relying on the child seeing data. `pclose` flushes, closes,
waits for the child as `waitpid` does, and returns the raw wait status
(`popen(3)` documents it as the `wait4(2)` status) -- decode with the
`WIFEXITED`/`WEXITSTATUS` macros, and note the child may also die by
signal. Closing a `popen` stream with `fclose` instead of `pclose`
leaves a zombie; `pclose` on a non-`popen` stream is undefined.

**Security** -- the command string is *shell* input: metacharacters and
word splitting apply, so interpolating user data enables command
injection. `execv`-style `posix_spawn` or `fork`+`exec` with `pipe(2)`
is the fix when no shell syntax is actually needed (manual, *Pipe to a
Subprocess*, contrasts the raw pipe+fork+dup2+exec recipe).

**References** -- `man3/popen.3`; glibc manual *Pipe to a Subprocess*;
example `manual/examples/popen.c`.
