# `err` / `errx` / `warn` / `warnx` (verr, verrx, vwarn, vwarnx) - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-err (group) |
| Header | `err.h` |
| Provenance | BSD |
| Status | documented |

**Signature** -- `void err(int status, const char *format, ...);` `void
errx(int status, const char *format, ...);` `void warn(const char
*format, ...);` `void warnx(const char *format, ...);` plus `va_list`
forms `verr`, `verrx`, `vwarn`, `vwarnx`.

**Semantics** -- BSD shorthand built on the same output discipline:
prefix `program_invocation_short_name`, `": "`, the formatted message,
and for the non-`x` variants `": "` plus `strerror(errno)` -- `err` then
exits with `status` (even `0`), `warn` returns (manual, *Error
Messages*). Equivalences from the manual: `warn` is roughly
`error(0, errno, ...)` and `err` roughly `error(status, errno, ...)`
with the `error` globals untouched; `warnx`/`errx` omit the errno text
(`errx(status, 0, ...)` shape). Implicit `errno` use means the call must
come before anything clobbers it. The manual advises preferring
`error`/`error_at_line`; the BSD set exists for portability with
4.4BSD-derived code (`err(3)`).
