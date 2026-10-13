# date — print or set the system date and time

## Overview

`date` prints the current (or any) date and time in almost any format you can
describe, converts between timestamps and human-readable time, parses
surprisingly loose natural-language date strings, and — with the right
privileges — sets the system clock. It is the standard tool for timestamps in
scripts: log file suffixes, directory names for backups, epoch arithmetic,
ISO 8601 output, and "what was last Tuesday?" queries.

Debian ships it in the `coreutils` package at `/usr/bin/date`. It is
POSIX-standardized, but the POSIX surface is only a fraction of what GNU
date does: `-d` natural-language parsing, `%N` nanoseconds, `--rfc-3339`,
`--debug`, and the whole relative-dates grammar ("next friday", "3 hours
ago", "@1700000000") are GNU extensions. That split is the source of the
most notorious portability trap in shell scripting (GNU vs BSD `date`),
covered in Nuances.

Date work looks trivial and is not: time zones, DST transitions, leap years,
and locale-dependent formats each bite scripts regularly. This page covers
the format grammar, the parsing grammar, epoch math, and the portability
discipline that keeps timestamp code correct across systems.

| Field | Value |
| --- | --- |
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 |
| Path | `/usr/bin/date` on modern Debian/Ubuntu |
| First appeared / lineage | 1st Edition UNIX (1971); GNU version since the 1980s |
| Standards | POSIX.1-2018 (`date`) |

## Synopsis

```
date [OPTION]... [+FORMAT]
date [-u|--utc|--universal] [MMDDhhmm[[CC]YY][.ss]]
```

Main forms:

```bash
date                          # default locale format
date '+%Y-%m-%d %H:%M:%S'     # arbitrary format string
date -d 'next friday' +%A     # parse a string, print with format
date -u --rfc-3339=seconds    # UTC, RFC 3339
date -d @1700000000           # epoch → human
date 1009123026               # SET the clock (root; MMDDhhmmCCYY)
```

Everything beginning with `+` is the output format; without it, `date`
prints the default representation. The second synopsis line sets the clock
and is rarely used now that NTP exists.

## How It Works

### Output pipeline

```
  requested time ──► struct tm ──► format string ──► stdout
 (now, -d/-f/-r/       (calendar     (%-specifiers
  @epoch, -s)           fields:       consumed left
                        Y M D H S     to right; unknown
                        tz offsets)   %x sequences are
                                      an error in GNU date)
```

`date` first establishes *which* moment to render — usually now, but `-d`
STRING, `-f` FILE, `-r` FILE (a file's mtime), or an `@epoch` operand can
name another. It then renders that moment through a `strftime(3)`-style
format, honoring `TZ` and `LC_TIME` from the environment.

### Format specifiers that matter

| Spec | Meaning | Example (2026-10-09 09:30:49 UTC) |
| --- | --- | --- |
| `%Y` / `%m` / `%d` | year / zero-padded month / day | `2026` `10` `09` |
| `%H` / `%M` / `%S` | hour / minute / second (24h) | `09` `30` `49` |
| `%F` | full date, `%Y-%m-%d` | `2026-10-09` |
| `%T` | full time, `%H:%M:%S` | `09:30:49` |
| `%s` | seconds since epoch (UTC-based) | `1791538249` |
| `%N` | nanoseconds (GNU) | `066479693` |
| `%A` / `%a` | weekday full / abbreviated | `Friday` / `Fri` |
| `%B` / `%b` | month full / abbreviated | `October` / `Oct` |
| `%j` | day of year (001-366) | `282` |
| `%V` / `%G` | ISO 8601 week / ISO week-year | use together |
| `%Z` / `%z` | zone name / numeric offset | `UTC` / `+0000` |
| `%D` | `%m/%d/%y` — ambiguous, avoid | `10/09/26` |
| `%%` / `%n` / `%t` | literal `%` / newline / tab | |

Padding and case modifiers compose with any specifier — the underrated part
of the grammar:

```bash
date +%-d          # 9      (no zero padding)
date +%_d          # ' 9'   (space padded)
date +%010s        # zero-pad epoch to width 10
date +%^A          # FRIDAY (upper case)
date +%#A          # fRIDAY (swap case; rarely wanted)
```

### The `-d` parsing grammar (GNU)

GNU date parses a dialect of its own — not ISO, not English — with these
load-bearing behaviors:

```bash
date -d 'now'
date -d 'yesterday' +%F                 # 2026-10-08
date -d 'next friday' +%F               # 2026-10-16
date -d 'last week' +%F                 # 2026-10-02
date -d '3 hours ago' +%H:%M            # 06:30
date -d '2026-10-09 +3 days' +%F        # 2026-10-12
date -d '2026-10-09 +1 month' +%F       # 2026-11-09
date -d '@1700000000'                   # Tue Nov 14 22:13:20 UTC 2023
date -d '2026-11-08T09:30:00-04:00' +%s # ISO input with offset works
```

Rules worth memorizing:

- Relative items (`+3 days`, `next fri`, `2 years ago`) compose left to
  right onto the base time; `+1 month` clamps day-of-month rather than
  skipping into the next month when the target month is shorter.
- A bare time like `next friday` uses **midnight** as the starting time —
  `date --debug` makes this explicit, which is why `date -d tomorrow +%H`
  prints `00`.
- `@N` is the only reliable way to feed an epoch; raw digit strings are
  parsed as dates (`20261009` = Y-M-D, `0930` = a time!) and are a classic
  silent-corruption bug.
- DST-sensitive zones make `+24 hours` differ from `+1 day`; on spring-
  forward days `+1 day` can produce 23:00 the next day, while `tomorrow`
  keeps the same wall clock. Prefer the word form when you mean calendar
  days.

`--debug` annotates every parse step — invaluable for CI tests:

```bash
$ date --debug -d 'next friday' +%F
date: parsed day part: next/first Fri (day ordinal=1 number=5)
date: input timezone: system default
date: warning: using midnight as starting time: 00:00:00
date: new start date: 'next/first Fri' is '(Y-M-D) 2026-10-16 00:00:00'
...
2026-10-16
```

### ISO 8601 / RFC 3339 / RFC 5322 output

```bash
date -I                     # 2026-10-09              (ISO 8601, date)
date -Iseconds              # 2026-10-09T09:30:49+00:00
date -Ins                   # ...with nanosecond precision
date --rfc-3339=seconds     # 2026-10-09 09:30:49+00:00
date --rfc-3339=date        # 2026-10-09
date -R                     # Fri, 09 Oct 2026 09:31:13 +0000  (RFC 5322 email)
```

For machine-readable output prefer `--rfc-3339=seconds` or explicit
`+%Y-%m-%dT%H:%M:%S%z` — the space in RFC 3339 GNU output is a quirk
(RFC 3339 itself allows a space by mutual agreement, but other consumers
expect `T`).

### Epoch math

The epoch (`%s`) is time-zone independent — it counts UTC seconds — which
makes it the only safe currency for comparing and storing time. Round trips
and arithmetic:

```bash
now=$(date +%s)
later=$((now + 86400))          # integer seconds; no date needed for math
date -u -d "@$later" '+%F %T'   # convert back
date -u -d @0                   # Thu Jan  1 00:00:00 UTC 1970
date +%s -d '2026-12-31 23:59:59'
```

Two properties make this the robust pattern: `%s` ignores `TZ` (an epoch is
an absolute instant), and the shell does the integer arithmetic, so no
locale or zone parsing is involved. Only when *rendering* do you reattach a
zone.

### Time zone overrides

`date` honors the `TZ` environment variable per invocation:

```bash
TZ=UTC date +%F_%T              # 2026-10-09_09:30:49
TZ=America/New_York date +%F_%T%z   # 2026-10-09_05:30:49-0400 (EDT)
TZ=Asia/Tokyo date +%H:%M       # 18:30
```

The POSIX `TZ` *string* syntax has a sign trap:

```bash
TZ=UTC-5 date +%Z_%H:%M         # EST_14:31 — "UTC-5" means FIVE WEST OF... no:
                                # POSIX is west-positive, so UTC-5 = UTC+5!
```

`TZ=UTC-5` is 5 hours **ahead** of UTC. For real zones always use IANA names
(`America/New_York`) from `tzdata`; use `TZ=UTC` (the name, not the string)
when you mean UTC.

### Setting the clock

`date -s '2026-10-09 12:00:00'` or the positional `MMDDhhmm[[CC]YY][.ss]`
form sets the system clock — root only, and on systemd systems the
recommended spelling is `timedatectl set-time`. In containers `date -s`
fails with `Operation not permitted` because the CAP_SYS_TIME capability is
not granted; scripts intended to run there must not assume clock-setting
works.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-d`, `--date=STRING` | Render the time described by STRING instead of now (GNU grammar) |
| `-f`, `--file=FILE` | Like `-d`, one date string per line (batch conversion) |
| `-r`, `--reference=FILE` | Render FILE's modification time |
| `-s`, `--set=STRING` | Set the system clock to STRING (root) |
| `-u`, `--utc` | Render (or set) in UTC regardless of `TZ` |
| `-I[FMT]`, `--iso-8601[=FMT]` | ISO 8601: `date`, `hours`, `minutes`, `seconds`, `ns` |
| `--rfc-3339=FMT` | RFC 3339: `date`, `seconds`, `ns` |
| `-R`, `--rfc-email` | RFC 5322 date header format |
| `--debug` | Annotate how `-d` parsed its input (stderr) |
| `--resolution` | Print the clock resolution, e.g. `0.000000001` |

Only one of `-d`, `-f`, `-r`, `--resolution` may be given per invocation.

## Usage Patterns

```bash
# Timestamped backup directory
backup=/srv/backups/$(date +%F)/db-$(date +%H%M%S).sql.gz
```

```bash
# Log line with ISO timestamp, UTC always
echo "$(date -u +%FT%TZ) job finished" >> /var/log/myjob.log
```

```bash
# Expiry check: is the file older than 7 days?
created=$(date +%s -r /srv/uploads/big.bin)
[ $(( $(date +%s) - created )) -gt 604800 ] && echo stale
```

```bash
# Filename-safe timestamp incl. nanoseconds for uniqueness
ts=$(date +%Y%m%dT%H%M%S%N)
```

```bash
# Report deadline: 30 days from now, human format
date -d "+30 days" '+%A %d %B %Y'
```

```bash
# Convert every epoch in a file to ISO lines
grep -oE '^[0-9]{10}$' epochs.txt | date -f - '+%FT%T%z'
```

```bash
# First day of current month
date -d "$(date +%Y-%m-01)" +%F
```

```bash
# Last day of previous month (cron-style workaround)
date -d "$(date +%Y-%m-01) - 1 day" +%F
```

```bash
# Render a mtime in UTC for a manifest
tar tf pkg.tar | while read f; do date -u -r "$f" +%FT%TZ; done
```

```bash
# Portable "yesterday" that works on GNU and BSD
date -u -d "$(date -u +%Y-%m-%d) -1 day" +%F   # GNU
date -u -v-1d +%F                              # BSD (note: -v, different flag)
```

```bash
# elapsed time of a command using epoch deltas
start=$(date +%s); do_work; echo "took $(( $(date +%s) - start ))s"
```

```bash
# cron guard: only run on the last day of the month
[ "$(date -d tomorrow +%-d)" = "1" ] && /usr/local/bin/monthly.sh
```

## Nuances and Gotchas

- **GNU vs BSD is the big one.** BSD/macOS `date` has no GNU `-d` grammar:
  `-d` there sets DST display, adjustments use `-v` (`date -v-1d`),
  input needs `-f` with a format, and `--rfc-3339` is absent. Any script
  using `date -d 'yesterday'` breaks on macOS. Portable strategies: epoch
  arithmetic + `+%s`/`-d @N` (still GNU-only for the *parse*), a fixed
  set of formats, or shipping GNU coreutils. Test on both before claiming
  portability.
- **`%N` is GNU-only** and not zero-cost deterministic on all systems; on
  kernels without a fine clock it can be zeros. Never use `%N` as an
  entropy source.
- **`date -d tomorrow` starts at midnight.** `date -d 'tomorrow' +%A` is
  fine, but `date -d 'tomorrow 12:00'` re-parses the *whole* string — the
  words compose, so keep base and adjustment in one string or use
  `--debug` to verify what was meant.
- **Epoch `%s` is zone-independent; formatting is not.** `date +%s` under
  any `TZ` returns the same value, but `date +%F` does not — mixing them in
  one pipeline is how "the backup says yesterday" bugs happen around
  midnight in non-UTC zones. Decide the zone once, with `-u` or `TZ=`.
- **`TZ=UTC-5` means UTC+5.** POSIX `TZ` strings count hours *west* as
  positive. Almost every real bug comes from mixing the string syntax with
  the IANA syntax; use IANA names only.
- **DST math:** `+24 hours` and `+1 day` differ on transition days; so do
  `date -d '+1 month'` results in different zones. Store instants as
  epochs, store *calendar* concepts as calendar strings, never the reverse.
- **Locale leakage:** `%A`, `%B`, `%c`, `%x` are locale-dependent. Scripts
  parsing `date` output must set `LC_ALL=C` first — or better, only parse
  `%s`/ISO output that never changes.
- **`MMDDhhmm` set form is order-inverted to human memory** (month first!)
  and a typo silently corrupts the clock. Prefer `timedatectl` or NTP.
- **Setting the clock in containers fails** (`Operation not permitted`) —
  date cannot help with time skew in containers; the host clock wins.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Success (printed a date or set the clock) |
| 1 | Failure: unparseable `-d`/`-f` input, invalid format string, clock-set denied |

`date -d 'feb 29'` exits 1 with `date: invalid date 'feb 29'` — validating
user date input through a throwaway `date -d` parse is a legitimate,
documented pattern.

## Related Commands

- [`overview`](./overview.md) — collection hub for the GNU Coreutils pages
- [`env`](./env.md) — sibling launcher tool; `TZ=... date` and `env TZ=... date` are the same operation spelled two ways
- [bash](../../shell/bash.md) — arithmetic `$(( ))` and command substitution rules that epoch-math scripts rely on
- `touch -d`, `timedatectl`, `hwclock` — consumers and administrators of the same time concepts (no pages in this collection)

## Interview Questions

### Q: Why is `date +%s` the recommended currency for comparing timestamps in scripts, and what does it deliberately throw away?

`%s` is seconds since the epoch in UTC, an absolute instant: it is immune to
time zone, DST, and locale, so differences are plain integer subtraction in
`$(( ))`. What it throws away is calendar meaning — 86400 is not always
"tomorrow" across DST, and `%s` cannot represent the civil notion "Oct 9"
without re-rendering in a chosen zone. The professional pattern is: compare
and store epochs, render calendar strings only at the edges, and know which
you are holding.

### Q: Explain the GNU vs BSD `date` portability trap and name two strategies that survive both.

GNU `date -d 'yesterday'`, `%N`, `--rfc-3339`, and the relative-dates grammar
do not exist on BSD/macOS, where `-d` means "adjust DST display" and
adjustments are `-v-1d`. Strategies: (1) restrict yourself to formats
POSIX defines and do arithmetic with `+%s` plus shell math, accepting you
cannot parse arbitrary English dates portably; (2) detect and branch
(`date -v 2>/dev/null && BSD || GNU`); (3) require GNU coreutils (document
the dependency, or vendor busybox whose `date` is closer to GNU in some
respects). The unforgivable option is testing only on Linux and shipping.

### Q: A script computes `date -d "+1 day"` at 23:30 in a zone about to fall back to standard time. What wall-clock and instant interpretations are involved?

`+1 day` on a civil calendar adds one day to the wall-clock fields, so the
result at 23:30 the previous evening is 23:30 the next day — which, after
the fall-back hour is repeated, is 25 real hours later. `+24 hours`
instead adds exactly 86400 seconds to the instant, yielding 22:30 wall
clock the next day. Neither is "wrong"; they answer different questions.
The lesson: choose the semantic (calendar day vs elapsed time) and use
`--debug` to confirm which grammar was applied.

### Q: Why does `date -d 20261009` not give October 9th, and what does GNU actually do with it?

A pure digit string is parsed as a date in `YYYYMMDD` form — 20261009 *does*
decode to 2026-10-09 — but `date -d 0930` parses as "9:30" today, and
8-digit strings like `17915382` are parsed as year 1791, month 53
(invalid → error, or silently clamped depending on the string). The
`@N` prefix is the only unambiguous way to pass an epoch, and prefixed
ISO strings are the only unambiguous way to pass civil dates. `--debug`
exists precisely to audit these parses.

### Q: How would you make a "run on the last day of the month" guard in cron with date, and why is it structured that way?

Cron has no "last day" field, so the idiom is to run on day 28–31 and have
the job test whether *tomorrow* is the 1st:
`[ "$(date -d tomorrow +%-d)" = 1 ] && monthly.sh`. The logic is inverted
deliberately: at 23:59 on the true last day, "tomorrow" is the 1st in every
month, and `%-d` avoids a zero-padded `01` string-comparison trap. The
job must also be idempotent, since cron firing on the 28th–31st means the
guard runs (and correctly declines) most days.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/date.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
- [POSIX 2018 spec](https://pubs.opengroup.org/onlinepubs/9699919799/)
