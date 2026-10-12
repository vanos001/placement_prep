# localtime(3) - glibc (localtime / gmtime, _r twins, tzset and TZ)

> Broken-down time conversion (manual nodes *Broken-down Time* and *Time Zone State*). The inverse conversion lives in [mktime-difftime](./mktime-difftime.md).

| Field | Value |
|---|---|
| Header | `time.h` |
| Standards | ISO C (`localtime`, `gmtime`), POSIX.1c (`_r`), POSIX.1 (`tzset`, `tzname`, `timezone`, `daylight`) |
| Exported | `localtime`, `gmtime`, `localtime_r`, `gmtime_r`, `tzset` all `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | `localtime`/`gmtime`: MT-Unsafe race:tmbuf, env, locale (static buffer); `_r`: MT-Safe env locale; `tzset`: MT-Safe env locale (manual safety annotations) |
| Ledger ID | `GLIBC-localtime` (Grouped FULL), `GLIBC-gmtime`, `_r` rows grouped, `GLIBC-tzset` (FULL) |

## Declaration and gates

```text
struct tm *localtime(const time_t *time);
struct tm *localtime_r(const time_t *time, struct tm *resultp);
struct tm *gmtime(const time_t *time);
struct tm *gmtime_r(const time_t *time, struct tm *resultp);
void tzset(void);
```

`struct tm` fields: `tm_sec` (0-60), `tm_min`, `tm_hour`, `tm_mday` (1-31, the only ordinal field), `tm_mon` (0-11), `tm_year` (years since 1900), `tm_wday`, `tm_yday`, `tm_isdst`, plus BSD-derived `tm_gmtoff` (seconds east of UTC) and `tm_zone` (manual, *Broken-down Time*).

## Semantics

`localtime` converts to the local zone, `gmtime` to UTC (`tm_gmtoff == 0`, `tm_zone == "UTC"`). Both return a pointer to a static `struct tm` that only they and their twins overwrite (manual). `localtime` additionally runs the time-zone state as if `tzset` had been called; `_r` variants write into `*resultp` and skip that guarantee. `tzset` re-reads the `TZ` environment variable and fills `tzname[2]`, `timezone` (seconds west, not DST-adjusted) and `daylight`. `TZ` formats: geographical (`America/New_York`), proleptic (`EST+5EDT,M3.2.0/2,M11.1.0/2`), colon form (`:/etc/localtime`, colon ignored by glibc), and - glibc extension - empty string means UTC; unset `TZ` defaults to `/etc/localtime` (manual, *TZ Variable*).

## Gotchas and portability

- The POSIX state variables are obsolescent and "specified only when TZ uses the proleptic format"; prefer `tm_gmtoff`/`tm_zone` (manual, *Time Zone State*).
- musl contrast: `src/time/localtime.c` is a static `struct tm` over `__localtime_r`, and `src/time/__tz.c` re-checks `TZ` on every conversion (cached `old_tz` comparison), searching `/usr/share/zoneinfo/`, `/share/zoneinfo/`, `/etc/zoneinfo/`; glibc caches zone state after `tzset`.

## References

- glibc manual nodes *Broken-down Time*, *TZ Variable*, *Time Zone State*; man3 `ctime.3` (aliases localtime/gmtime), `tzset.3`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41); musl 1.2.5 sources as cited.
