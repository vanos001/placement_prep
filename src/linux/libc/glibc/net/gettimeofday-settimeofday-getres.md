# gettimeofday(3) - glibc (gettimeofday / settimeofday, the vDSO path)

> Microsecond wall-clock get/set from BSD (manual node *Getting the Time* / *Setting and Adjusting the Time*). The modern replacement is `clock_gettime(2)`; syscall-level entries live in [Signals and Time syscalls](../../../syscalls/signals-time/overview.md).

| Field | Value |
|---|---|
| Header | `sys/time.h` |
| Standards | BSD origin; POSIX.1-2024 removed `gettimeofday`, glibc keeps it (manual portability note) |
| Exported | `gettimeofday`, `settimeofday` `GLIBC_2.2.5` (nm, host glibc 2.41); `gettimeofday` is an IFUNC (nm symbol type `i`) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotations) |
| Ledger ID | `GLIBC-gettimeofday`, `GLIBC-settimeofday` (time misc rows; `getres` companions `clock_getres`/`timespec_getres` in the same family) |

## Declaration and gates

```text
int gettimeofday(struct timeval *tp, void *tzp);
int settimeofday(const struct timeval *tp, const void *tzp);
struct timeval { time_t tv_sec; long tv_usec; };   /* sys/time.h */
```

## Semantics

`gettimeofday` stores seconds + microseconds since the epoch in `*tp` and "cannot fail, and its return value is always 0" (manual). The `tzp` argument is vestigial: "On some historic systems, if tzp was not a null pointer, information about a system-wide time zone would be written to *tzp. This feature is obsolete and not supported on GNU systems. You should always supply a null pointer." `settimeofday` with non-NULL `tzp` fails with `EINVAL` on glibc ("it is not possible to set the current time and the current time zone in the same call"); with NULL `tzp` it equals `clock_settime(CLOCK_REALTIME)` at microsecond precision and needs privilege (`EPERM`) (manual, node *Setting and Adjusting the Time*). The clock is "close to, but not necessarily in lock-step with" the clocks of `time` and `clock_gettime(CLOCK_REALTIME)` (manual).

## Gotchas and portability

- vDSO: man2 `gettimeofday.2` ("C library/kernel differences") states an implementation of `gettimeofday` is provided in the vDSO; on the host nm the symbol is an IFUNC, which is how glibc selects the vDSO path at startup. `time(2)` and `clock_gettime(2)` have the same arrangement.
- Prefer `clock_gettime(CLOCK_REALTIME, ...)` or `timespec_get(TIME_UTC)` in new code (manual portability note).
- musl `src/time/gettimeofday.c` wraps `clock_gettime(CLOCK_REALTIME)` (delta visible in the musl 1.2.5 tree).

## References

- glibc manual nodes *Getting the Time*, *Setting and Adjusting the Time*; man2 `gettimeofday.2`, `settimeofday.2`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 `src/time/gettimeofday.c`.
