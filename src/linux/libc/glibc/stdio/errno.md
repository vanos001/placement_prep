# `errno` - glibc

> Split from the chapter *glibc: stdio and Formatted I/O* into the per-function layout; see the [method page](../../../interface-encyclopedia.md) and the [glibc ledger](../../ledger-glibc.md) for coverage status.

## Family C -- Error Reporting

| Field | Value |
|---|---|
| ID | GLIBC-errno |
| Header | `errno.h` |
| Provenance | ISO C (object); the TLS realization is glibc-specific |
| Status | documented |

**What it is** -- installed `errno.h` defines `extern int *__errno_location
(void);` and `#define errno (*__errno_location ())`: a modifiable
lvalue backed by thread-local storage, so each thread has its own error
code. The manual documents `errno` as `volatile int` and notes ISO C
allows exactly this macro expansion (manual, *Checking for Errors*);
code that needs the address of the object takes `&errno` or calls
`__errno_location` directly. `E*` constants are macros in the same
header, all distinct except `EAGAIN == EWOULDBLOCK`.

**When it is set** -- only on failure is meaningful: the initial value
at startup is `0`, and the manual warns that many functions may set
`errno` to an unspecified nonzero value on *success*, so testing
`errno != 0` is never a correct error check; test the function's return
first (manual). Correct discipline for functions whose success value can
equal the failure value -- the manual names `sqrt` and `atan`;
`strtol` is the classic case (`strtol.3`: `0`, `LONG_MAX`, `LONG_MIN`
are legitimate returns, `ERANGE`/`EINVAL` disambiguate) -- is
`errno = 0;` immediately before the call and an `errno` check
immediately after, with nothing library-side in between.

**Signal interaction** -- a handler should save and restore `errno`
(manual). glibc's own cancellation-safe wrappers follow that rule.
