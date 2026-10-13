# strftime(3) - glibc (strftime / strftime_l / strptime format overview)

> Formatting and parsing broken-down time (manual nodes *Formatting Calendar Time* and *Low-Level Time String Parsing*).

| Field | Value |
|---|---|
| Header | `time.h` |
| Standards | ISO C (`strftime`), POSIX.1 (`strftime_l`), XPG4 (`strptime`); `_`/`-`/`0`/`^` flags are glibc extensions |
| Exported | `strftime` `GLIBC_2.2.5`; `strftime_l` `GLIBC_2.3`; `strptime` `GLIBC_2.2.5` (nm, host glibc 2.41) |
| Thread-safety | All three MT-Safe env locale (manual safety annotations); `strftime` runs `tzset` as a side effect |
| Ledger ID | `GLIBC-strftime` (FULL), `GLIBC-strftime_l` (strftime row), `GLIBC-strptime` (FULL) |

## Declaration and gates

```text
size_t strftime(char *s, size_t size, const char *template, const struct tm *brokentime);
size_t strftime_l(char *s, size_t size, const char *template,
                  const struct tm *brokentime, locale_t locale);
char *strptime(const char *s, const char *fmt, struct tm *tp);
```

## Semantics

`strftime` copies ordinary characters and expands `%` conversions from `brokentime` in the current locale. Specifier groups (manual table, abridged):

| Specifiers | Meaning |
|---|---|
| `%a %A %b %B %h %p %P` | weekday, month, AM/PM names (locale) |
| `%c %x %X %r` | locale date, time, combinations |
| `%d %e %m %y %Y %C %g %G` | day, month, year fields |
| `%H %I %k %l %M %S %s` | hour, minute, second, epoch seconds |
| `%j %u %w %U %V %W` | day-of-year, weekday, week numbers |
| `%n %t %%` | newline, tab, literal `%` |
| `%z %Z` | UTC offset (+hhmm), zone abbreviation |

GNU flags: `_` (space pad), `-` (no pad), `0` (zero pad), `^` (uppercase); modifiers `E`/`O` pick locale alternative forms. Returns the character count excluding the terminating NUL; **0 means the buffer was too small and the array contents are undefined** - but an empty result is also legal (e.g. `%p` in 24-hour locales), so test `buf[0]` as the manual's example shows. With `s == NULL` glibc returns the would-be length (GNU behavior documented in the manual). `strptime` parses `s` per `fmt` (same specifiers; `_ - 0 ^` flags rejected) and returns a pointer past the last consumed byte, NULL on mismatch; fields the format never touched are left unchanged, except `tm_wday`/`tm_yday` which are recomputed (manual).

## Gotchas and portability

- The zero-return ambiguity is the top strftime trap; see the manual's `buf[0]` idiom.
- musl's `strftime` lives in `src/time/strftime.c` and its `strptime` in `src/time/strptime.c` with the same core specifiers (delta tracked in the [musl catalog](../../musl/overview.md)).

## References

- glibc manual nodes *Formatting Calendar Time*, *Parsing Date and Time*; man3 `strftime.3`, `strptime.3`.
- `nm -D --with-symbol-versions` on libc.so.6 (glibc 2.41).
