# `vprintf` / `vfprintf` / `vsnprintf` / `vdprintf` / `vasprintf` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

| Field | Value |
|---|---|
| ID | GLIBC-vprintf (group) |
| Header | `stdio.h` |
| Provenance | ISO C99 (introduced there, earlier GNU extensions, manual); POSIX.1-2008 (`vdprintf`); GNU (`vasprintf`) |
| Status | documented |

The `v...` family takes a `va_list` instead of `...` so user functions
can forward their own arguments. Target mapping:

| Function | Target | Return |
|---|---|---|
| `vprintf` | `stdout` | chars or negative |
| `vfprintf` | stream | chars or negative |
| `vsprintf` | string, unbounded | chars |
| `vsnprintf` | string, `size` bounded | would-be length |
| `vdprintf` | file descriptor | bytes or negative |
| `vasprintf` | malloc'd string via `*ptr` | length or negative |

**Notes** -- a `va_list` is consumed by one call; re-walking requires
`va_copy` (manual, *Variable Arguments Output Functions*). Use the `v`
form to wrap formatting behind logging functions; pair with the
`format(printf, 2, 0)`-style attributes for checking.
