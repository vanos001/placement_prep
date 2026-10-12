# time(3) - glibc (time_t, its width, and the 2038 problem)

> The simple calendar-time type and the function that reads the clock (manual chapter *Date and Time*, nodes *Time Basics*, *Time Types*, *Getting the Time*). Higher-resolution clocks: [gettimeofday-settimeofday](./gettimeofday-settimeofday-getres.md) and `clock_gettime(2)`.

| Field | Value |
|---|---|
| Header | `time.h` (`time`, `time_t`), `sys/time.h` (`struct timeval`) |
| Standards | ISO C (`time_t` is opaque), POSIX.1 (seconds since the epoch) |
| Exported | `time` `GLIBC_2.2.5`, implemented as an IFUNC (nm symbol type `i` on host glibc 2.41) |
| Thread-safety | MT-Safe, AS-Safe, AC-Safe (manual safety annotation; "This function cannot fail") |
| Ledger ID | `GLIBC-time` (FULL entry) |

## Declaration and gates

```text
time_t time(time_t *result);
```

## Semantics

POSIX defines `time_t` as an integer counting seconds since 1970-01-01 00:00:00 UTC, ignoring leap seconds; ISO C only promises an arithmetic type whose values have no mandated meaning, and the manual points at `difftime` as the only portable arithmetic (see [mktime-difftime](./mktime-difftime.md)). `time` stores the same value in `*result` when that is not NULL. The manual: glibc guarantees `time_t` is **signed** and all functions behave on negative values; it uses the same clock as `clock_gettime(CLOCK_REALTIME_COARSE)` where available, else `CLOCK_REALTIME`.

## Gotchas and portability (width and Y2038)

- Width is a compile-time contract: POSIX.1-2024 requires `time_t` to be at least 64 bits; on glibc it "is 64 bits wide on all platforms ... except that it is 32 bits wide on a few older platforms unless you define `_TIME_BITS` to 64" (manual, *Time Types*).
- `_TIME_BITS=64` needs `_FILE_OFFSET_BITS=64` too, uses 64-bit-time syscalls on kernels above 5.1, and otherwise falls back to legacy 32-bit syscalls (`__USE_TIME64_REDIRECTS` renames declarations like `clock_gettime` to `__clock_gettime64`) (manual, *Feature Test Macros*, `_TIME_BITS`).
- The manual is explicit: 32-bit `time_t` "stops working in the year 2038"; that is the Y2038 boundary.
- musl contrast: `include/alltypes.h.in` line 12 is `TYPEDEF _Int64 time_t;`, so musl 1.2.5 builds a 64-bit `time_t` on every architecture; delta tracked in the [musl catalog](../../musl/overview.md).

## References

- glibc manual nodes *Time Basics*, *Time Types*, *Getting the Time*; man3 `time_t.3` (alias page for `system_data_types.7`, not cached locally).
- Header `time.h`; `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); glibc NEWS 2.40 for the utmp/lastlog unsigned switch.
