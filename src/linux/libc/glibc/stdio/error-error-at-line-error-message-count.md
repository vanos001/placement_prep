# `error` / `error_at_line` / `error_message_count` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-error (group) |
| Header | `error.h` |
| Provenance | GNU |
| Status | documented |

**Signature** -- `void error(int status, int errnum, const char *format,
...);` `void error_at_line(int status, int errnum, const char *fname,
unsigned int lineno, const char *format, ...);` plus globals `unsigned
int error_message_count;`, `int error_one_per_line;`, `void
(*error_print_progname)(void);`

**Semantics** -- the GNU Coding Standard printer. `error` flushes
`stdout`, then writes to `stderr`: program name (`program_invocation_name`
by default, or via the `error_print_progname` hook), `": "`, the
formatted message, and -- if `errnum` is nonzero -- `": "` plus
`strerror(errnum)`, newline-terminated (`error(3)`, manual, *Error
Messages*). Passing the error number *explicitly* fixes the classic
`perror` defect that `errno` may have been clobbered between failure and
report. If `status` is nonzero the process `exit`s with that status;
otherwise `error_message_count` increments. `error_at_line` inserts
`fname:lineno` after the program name for input-file diagnostics;
setting `error_one_per_line` nonzero suppresses consecutive duplicates
for the same file and line (only immediately adjacent repeats, manual).
The header decorates both with `format(printf, ...)` so GCC checks
arguments.

**Thread safety** -- `error` is MT-Safe; `error_at_line`'s
one-per-line state is unsynchronized (manual safety annotations).
