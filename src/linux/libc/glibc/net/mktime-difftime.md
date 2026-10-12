# mktime(3) - glibc (mktime, timegm, timelocal, difftime)

> Broken-down time back to `time_t`, and elapsed-time arithmetic (manual nodes *Broken-down Time* and *Calculating Elapsed Time*).

| Field | Value |
|---|---|
| Header | `time.h` |
| Standards | `mktime`, `difftime`: ISO C; `timegm` standardized by C23 but GNU on older systems; `timelocal` GNU |
| Exported | `mktime`, `difftime` `GLIBC_2.2.5`; `timegm`, `timelocal` same (nm, host glibc 2.41) |
| Thread-safety | `mktime`: MT-Safe env locale (calls `tzset` internally); `difftime`: MT-Safe, AS-Safe, AC-Safe (manual safety annotations) |
| Ledger ID | `GLIBC-mktime` (FULL), `GLIBC-difftime` (FULL), `GLIBC-timegm`/`GLIBC-timelocal` (time misc table rows) |

## Declaration and gates

```text
time_t mktime(struct tm *brokentime);
time_t timegm(struct tm *brokentime);
time_t timelocal(struct tm *brokentime);
double difftime(time_t end, time_t begin);
```

## Semantics

`mktime` is the local-zone inverse of `localtime`. It **normalizes** `*brokentime`: fields may be wildly out of range on entry (manual: "it's permissible for these components to have unnormalized values"), `tm_wday`, `tm_yday`, `tm_gmtoff` and `tm_zone` are ignored on input and recomputed on output. It calls `tzset` first, so `TZ` and `tm_isdst` decide the offset; `tm_isdst` positive/zero/negative selects DST, no DST, or unknown. Unrepresentable results return `(time_t)(-1)` and leave the structure unmodified - the classic ambiguity with a legitimate timestamp of -1 must be resolved by pre-clearing `errno` or testing the round trip. `timegm` is the UTC inverse of `gmtime` and ignores the zone entirely; `timelocal` is a mnemonic alias of `mktime`. `difftime` returns `end - begin` as `double`; on POSIX systems direct subtraction works, but `difftime` avoids overflow "even if end and begin are so far apart that a simple subtraction would overflow" (manual, *Calculating Elapsed Time*), which is why ISO C makes it the portable way to compare `time_t` values of unspecified encoding.

## Gotchas and portability

- `timegm` portability trick, per the manual: save `TZ`, set `TZ=UTC`, call `mktime`, restore.
- glibc provides no `struct timespec`/`timeval` subtraction helper; the manual shows hand-rolled code for that.
- musl implements `timegm` in `src/time/timegm.c` with the same semantics (delta verified in the [musl catalog](../../musl/overview.md)).

## References

- glibc manual nodes *Broken-down Time*, *Calculating Elapsed Time*; man3 `mktime.3`, `difftime.3`, `timegm.3`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41).
