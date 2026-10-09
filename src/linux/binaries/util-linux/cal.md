# cal — print a calendar

## Overview

`cal` prints a calendar for a month or a year in the traditional grid
layout, and its sibling `ncal` prints the same data in FreeBSD's side-by-side
layout with a few extra features. Despite living in this util-linux
collection, it is *not* util-linux upstream: Debian ships it in the `ncal`
package, which carries the BSD `ncal` code (part of FreeBSD's bsdmainutils
lineage) — the same tool the BSDs ship as `cal`/`ncal`. Both Debian binaries
are one program family: `ncal` is the real binary, `cal` selects the
traditional layout (switchable at runtime with `-C`/`-N`).

You reach for it constantly and non-fatally: check which weekday a date
falls on, lay out a release schedule across months, get day-of-year
numbers for logs, week numbers for EU business calendars, or the date of
Easter. It is often confused with `date` (prints one date, formats
arbitrary, cannot show a grid) and with GUI calendar widgets. For
interview trivia it is famous for one output: `cal 9 1752`.

| Field | Value |
| --- | --- |
| Package | ncal (Debian bookworm; not util-linux) |
| Man section | 1 |
| Path | /usr/bin/cal and /usr/bin/ncal |
| First appeared | BSD cal (1970s); ncal (FreeBSD, 1994) |
| Standards | BSD heritage; locale-aware via LC_TIME |

## Synopsis

```
cal [-31jy] [-A num] [-B num] [-d yyyy-mm] [[month] year]
cal [-jy] [-A num] [-B num] [-d yyyy] [year]
ncal [-C] [-A num] [-B num] [-hjJpwy] [-s country_code] [[month] year]
ncal [-A num] [-B num] [-hJeu] [-d yyyy-mm] [month] [year]
```

Main one-line forms:

```
cal                    # current month, today highlighted
cal 2026               # whole year
cal 9 1752             # the famous Gregorian-switch month
cal -3                 # previous, current, next month
ncal -e                # date of Easter (western) this year
```

Arguments are positional: `cal 9 2026` is September 2026; a single number
in 1..9999 is a year. `-d yyyy-mm` forces the displayed month without
positional parsing (useful in scripts).

## How It Works

### Layouts: cal vs ncal

```
$ cal 9 1752                       $ ncal 9 1752
   September 1752                       September 1752
Su Mo Tu We Th Fr Sa              We  1  2 14 15 16
       1  2 14 15 16              Th 17 18 19 20 21 22 23
17 18 19 20 21 22 23              Fr 24 25 26 27 28 29 30
24 25 26 27 28 29 30              Sa -- -- -- -- -- --
```

`cal` renders the grid users expect; `ncal` lists days vertically per
weekday and adds features (Easter dates, country-specific calendar
switches, week numbers were ncal-first). `-C` forces cal layout from an
ncal invocation, `-N` the reverse — same binary, switched style.

The 1752 output above is not a bug: it shows the Julian-to-Gregorian
switch in the British Empire, where Wednesday 2 September 1752 was
followed by Thursday 14 September 1752. Eleven days simply do not exist
that month; BSD cal renders the historical truth, and interviewers love
asking why.

### Which month gets displayed

Selection is positional, with fallbacks:

```
cal                 # today's month
cal 2026            # all twelve months of 2026
cal 8 2026          # August 2026
cal -d 2026-08      # same, script-friendly, no positional ambiguity
cal -d 2026         # whole year, script-friendly
```

Ranges around the selection come from `-A`/`-B`:

```
cal -B 1 -A 1       # July, August, September (if today is in August)
cal -3              # shorthand for exactly that
cal -A 2            # today's month plus the next two
```

`-A`/`-B` compose with any base month, including `-d` and explicit
`month year` arguments, and may be used together. In `-y` mode they
extend the year view with surrounding months.

### Week numbers, day-of-year, locale

```
$ cal -w            # week numbers as an extra row/footer in cal layout
$ ncal -w           # week numbers in the left margin (ncal layout)
$ cal -j            # day-of-year (Julian day) numbering:
       August 2026
 Fr 212 213 214 ... # every day shows its 1-based position in the year
$ LC_ALL=C cal      # English names, Sunday first (locale-dependent otherwise)
```

The first weekday and all names come from `LC_TIME`; on a locale-less
system the BSD default (Sunday first, English) applies. `-m` requests
Monday first, `-s cc` applies a country's historical Julian→Gregorian
switch date (ncal).

## Options That Matter

| Option | Effect |
| --- | --- |
| (no args) | Current month, today highlighted |
| `[[month] year]` | Positional month (1-12 or name) and/or year (1-9999) |
| `-d yyyy-mm` | Display the given month (or `-d yyyy` the year); script-safe |
| `-3` | Previous, current, and next month together |
| `-A num` | Also display `num` months *after* the selected one |
| `-B num` | Also display `num` months *before* the selected one |
| `-y` | Display the whole year |
| `-j` | Day-of-year (Julian) numbering instead of day-of-month |
| `-w` | Print week numbers |
| `-h` | Disable highlighting of today |
| `-m` | Start weeks on Monday (cal layout) |
| `-e` | (ncal) display the date of Easter (western) |
| `-J` | (ncal) display the date of Orthodox Easter |
| `-s cc` | (ncal) country code for historical calendar switch |
| `-C` / `-N` | Force cal / ncal layout regardless of program name |

## Usage Patterns

```bash
# What weekday is the deadline?
cal 3 2027
```

```bash
# Sprint planning across the quarter, centered on today
cal -B 1 -A 2
```

```bash
# Full-year wall calendar for the terminal
cal -y | less
```

```bash
# EU-style view: week numbers, weeks start Monday (ncal layout is Monday-first)
ncal -w
# same idea in the classic grid layout
cal -m -w
```

```bash
# Map syslog day-of-year entries (Jul 15 = 196) onto a grid
cal -j 7 2026
```

```bash
# Script: how many days does a given month have?
cal -h -d 2028-02 | awk 'NF {d=$NF} END {print d}'
```

```bash
# Easter date for this year (ncal feature, no network needed)
ncal -e
```

```bash
# Render a specific month for a report, no "today" pollution
cal -h -d 2026-11
```

```bash
# The interview classic — see the missing eleven days
cal 9 1752
```

```bash
# Force cal layout from scripts that call ncal internally
ncal -C 5 2026
```

```bash
# Batch: calendar for every month of a project year into a file
{ for m in 1 2 3 4 5 6 7 8 9 10 11 12; do cal $m 2027; done; } > plan2027.txt
```

## Nuances and Gotchas

- **Wrong year parse.** `cal 25` is year 25, not "next month". The parser
  treats one argument in 1..9999 as a year; two arguments as `month year`.
  Use `-d yyyy-mm` in scripts to avoid the ambiguity entirely.
- **Highlighting depends on the terminal.** Today is highlighted via
  escape sequences; piped output drops it (and `-h` disables it). Old
  script outputs pasted into reports sometimes carry stray escape bytes —
  run with `-h` when the output is machine-consumed.
- **1752 is intentional.** Days 3-13 of September 1752 are missing in all
  BSD-lineage cal implementations, honoring the British calendar reform.
  Anything that "fixes" this is not cal.
- **Week numbers are ISO-ish but locale-shaped.** `-w` numbers weeks per
  the locale's convention; do not present them as ISO-8601 week numbers
  without checking — week 1 boundaries differ across conventions.
- **Debian package history.** It moved from `bsdmainutils` to its own
  `ncal` package in bookworm; on older Debian releases `apt install
  bsdmainutils` was the way. The binary is *not* from util-linux even
  though it often sits next to util-linux tools.
- **ncal-only features stay ncal-only** unless `-C` is used to borrow the
  layout: Easter dates, `-s cc`, and week-number placement differ. A
  script calling `cal -e` fails; call `ncal -e` (or check the man page of
  your exact version).
- **Empty operand edge:** `cal 0` errors (year 0 does not exist);
  `cal 13 2026` errors; both exit nonzero with a usage message.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Calendar displayed |
| 1 | Usage error: invalid month/year, malformed `-d`, or unknown option |

## Related Commands

- [util-linux overview](./overview.md) — the other binaries in this collection (cal lives here in the book, not upstream)
- [Command reference](../../reference/commands.md) — where one-line tools like cal fit in the daily toolkit

## Interview Questions

### Q: Why does `cal 9 1752` skip from the 2nd to the 14th?

September 1752 is when the British Empire adopted the Gregorian calendar:
the day after Wednesday 2 September (Julian) was Thursday 14 September
(Gregorian), deleting eleven days. BSD cal (and its Debian descendant)
deliberately renders the historical switch, and this output is the
canonical example of software preserving a calendar fact instead of
"correcting" it.

### Q: What is the difference between cal and ncal, and when does it matter?

They are one program family from the BSD ncal code with two layouts: cal
draws the familiar grid, ncal draws vertical weekday columns and adds
features — Easter dates (-e/-J), country calendar-switch handling (-s),
and week numbers in the margin. Scripts that need those features must call
ncal; -C/-N switch layouts explicitly when one invocation must render
both styles.

### Q: How do -A and -B differ from -3?

`-3` is exactly one month before plus one after. `-A`/`-B` take a count
and compose with each other and with any selected month (`-d 2026-08 -B 2
-A 1`), giving arbitrary ranges around any base — which `-3` cannot
express. For scheduling scripts that always render a quarter regardless
of today's date, `-A/-B` with `-d` is the robust combination.

### Q: How would you reliably extract the number of days in a month in a shell script?

`cal -h -d 2028-02 | awk 'END {print $NF}'` — take the last field of the
last (non-empty) line of the month grid. It avoids depending on `date -d`
GNU extensions and works on any BSD-lineage cal. The `-h` matters when
the output is parsed rather than displayed.

### Q: Is cal locale-aware? What changes under a different LC_TIME?

Yes: weekday and month names, and the default first day of the week, come
from LC_TIME; `-m` forces Monday-first and `-s` (ncal) applies
country-specific historical switches. That is also the gotcha: scripts
parsing the grid assume Sunday-first English headers, which breaks under
de_DE.UTF-8 — set `LC_ALL=C` before parsing.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/ncal/cal.1.en.html)
- [Package page — packages.debian.org](https://packages.debian.org/bookworm/ncal)
