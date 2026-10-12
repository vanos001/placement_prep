# syslog(3) - glibc (openlog / syslog / closelog / setlogmask)

> The BSD syslog(3) API that submits messages to the system logger over the `/dev/log` Unix socket (manual chapter *Syslog*).

| Field | Value |
|---|---|
| Header | `syslog.h` |
| Standards | BSD origin, POSIX.1-2001+ for `syslog`/`openlog`/`closelog`/`setlogmask`; `LOG_PERROR` not in POSIX.1-2001/2008 (man3) |
| Exported | `openlog`, `syslog`, `closelog`, `setlogmask` all `GLIBC_2.2.5` (nm, host glibc 2.41); `vsyslog` has its own page [vsyslog and %m](./vsyslog-%m.md) |
| Thread-safety | MT-Safe; internal state is lock-guarded (`openlog`/`closelog` AS-Unsafe lock, AC-Unsafe lock fd per manual annotations); `syslog` MT-Safe env locale |
| Ledger ID | `GLIBC-syslog` (FULL grouped entry), `GLIBC-openlog`/`GLIBC-closelog`/`GLIBC-setlogmask` (Grouped) |

## Declaration and gates

```text
void openlog(const char *ident, int option, int facility);
void syslog(int facility_priority, const char *format, ...);
void closelog(void);
int  setlogmask(int mask);
```

Options: `LOG_PERROR` (copy to stderr), `LOG_CONS` (console fallback), `LOG_PID` (append PID), `LOG_NDELAY` (connect now; historically inverted sense), `LOG_ODELAY` (no-op for compatibility). Facilities `LOG_USER` (default), `LOG_DAEMON`, `LOG_MAIL`, `LOG_AUTH`, `LOG_AUTHPRIV`, `LOG_CRON`, `LOG_FTP`, `LOG_LOCAL0..7`, ...; priorities `LOG_EMERG` ... `LOG_DEBUG` (manual, *openlog*, *syslog; vsyslog*).

## Semantics

`openlog` sets the ident string, options and default facility. The manual is explicit about the connection: it "tries to open it and connect it as a stream socket. If that doesn't work, it tries ... as a datagram socket. The socket has the Close on Exec attribute." - the path is `/dev/log`, served by syslogd (manual, *Overview of Syslog*). `syslog` opens the connection implicitly if needed (ident = program name from argv[0], facility `LOG_USER`, options off) and keeps it open; on send failure it closes and retries on the next call. `facility_priority` is `LOG_MAKEPRI(facility, priority)` or a bare priority, which selects the default facility. `setlogmask` gates submission before any socket traffic: the mask argument has one bit per priority, built with `LOG_MASK(pri)` or `LOG_UPTO(pri)`; bits on mean that priority is logged, bits off mean discarded, and each call replaces the previous mask (manual, *setlogmask*). The logmask exists independently of open/closed connections - it differs from syslogd configuration in that blocked messages are never submitted at all. `closelog` closes the socket and drops the stored `ident` reference.

## Gotchas and portability

- **`ident` pointer retention**: glibc keeps the pointer; "you must not free the memory that ident points to" and shared libraries must `closelog()` before unload (manual, *openlog*).
- `LOG_KERN == 0` means "use the default facility"; user processes cannot emit kernel messages through this API (manual).
- On systemd systems `/dev/log` is owned by systemd-journald, which forwards to classic syslog daemons per configuration (environment fact; not verified from the cached sources here).
- musl contrast: `src/misc/syslog.c` uses `SOCK_DGRAM|SOCK_CLOEXEC` only, **copies** `ident` into a 32-byte buffer, and builds the `<pri>` + `%b %e %T` timestamp header itself; glibc's socket is stream-first with a datagram fallback.

## References

- glibc manual chapter *Syslog* (all nodes); man3 `syslog.3`/`openlog.3`; header `syslog.h`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/misc/syslog.c`.
