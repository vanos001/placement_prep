# vsyslog(3) - glibc (vsyslog and the %m conversion)

> The `va_list` form of `syslog(3)`, and the `%m` errno conversion its format accepts (manual node *syslog; vsyslog*; man3 `syslog.3`).

| Field | Value |
|---|---|
| Header | `syslog.h` |
| Standards | BSD; `vsyslog` gated by `_DEFAULT_SOURCE` since glibc 2.19 (man3 feature-test note) |
| Exported | `vsyslog` `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | MT-Safe env locale (manual safety annotation); shares the syslog lock with `openlog`/`closelog` |
| Ledger ID | `GLIBC-vsyslog` (Grouped into the syslog entry, va_list form) |

## Declaration and gates

```text
void vsyslog(int facility_priority, const char *format, va_list arglist);
```

## Semantics

`vsyslog` "is functionally identical to syslog, with the BSD style variable length argument" (manual): same `/dev/log` submission path, same implicit `openlog` defaults, same `facility_priority` encoding. It exists so wrapper layers can forward their own `...` arguments:

```text
void log_err(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsyslog(LOG_ERR, fmt, ap);
    va_end(ap);
}
```

The format language is printf plus one extra conversion: the two-character sequence `%m` "will be replaced by the error message string strerror(errno)" (man3 `syslog.3`). The classic idiom from the manual's example is `... "Unable to make network connection to %s. Error=%m", host`. `errno` is read at format time, so capture it before any intermediate call clobbers it. The message needs no trailing newline; a newline is added if absent.

## Gotchas and portability

- `%m` is a GNU/BSD extension, not ISO C printf; portable wrappers must expand it themselves.
- musl contrast: musl's `syslog`/`vsyslog` (`src/misc/syslog.c`) format through `vsnprintf`, and `%m` is handled inside musl's `vfprintf` (`strerror(errno)` at line 597), so the same format works; musl truncates the assembled message to a 1024-byte buffer, while glibc assembles via `open_memstream` (visible in the manual's safety annotation) without a documented size cap.
- Cancel-safety differs: musl disables cancellation around the send; glibc's annotation does not claim that.

## References

- glibc manual node *syslog; vsyslog*; man3 `syslog.3`; header `syslog.h`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/misc/syslog.c`, `src/stdio/vfprintf.c`.
