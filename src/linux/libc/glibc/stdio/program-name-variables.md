# Program-name variables - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Variable | Header | Meaning |
|---|---|---|
| `program_invocation_name` | `errno.h` (`_GNU_SOURCE`) | Full `argv[0]` as invoked; set up by libc before `main` (manual, *Error Messages*). |
| `program_invocation_short_name` | `errno.h` (`_GNU_SOURCE`) | Same with everything up to the last slash removed. |

GNU extension; on non-GNU libcs save `argv[0]` yourself (manual). These
are what `error()` and `warn()` print.
