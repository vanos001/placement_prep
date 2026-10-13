# numfmt — human-readable number conversion, both directions

## Overview

`numfmt` reformats numbers: it converts raw machine-friendly values (like
`1048576`) into human-readable ones (`1.0M`) and back again, optionally
rewriting only selected fields of each line. It is the scripting glue between
tools that print byte counts (`du --block-size=1`, `df -B1`, `ls` parsed
columns) and reports that people actually read — and, unlike eyeballing
`du -h` output, its output is machine-sortable and reversible.

It ships in Debian's `coreutils` package at `/usr/bin/numfmt`. It is a pure
GNU invention (added to coreutils in the 8.21 era, 2013), has no POSIX
standard and no BSD/macOS equivalent by default, which is worth stating in
portable scripts. You reach for it in pipelines and reports; it is often
confused with `sort -h` (which *orders* human-suffixed numbers instead of
converting them) and with awk one-liners doing hand-rolled division.

| Field | Value |
|---|---|
| Package | `coreutils` (Debian bookworm) |
| Section (man) | 1 (User commands) |
| Path | `/usr/bin/numfmt` |
| First appeared / lineage | GNU coreutils 8.21 era (2013) |
| Standards | None — GNU extension |

## Synopsis

```
numfmt [OPTION]... [NUMBER]...
```

Main forms:

```
numfmt --to=iec 1048576                 # 1.0M  (bytes → IEC)
numfmt --from=iec 2M                    # 2097152  (IEC → bytes)
numfmt --to=iec-i --suffix=B 2097152    # 2.0MiB
df -B1 | numfmt --header --field=4 --to=iec
```

## How It Works

Every invocation picks one conversion direction. `--to=UNIT` scales *down*
(takes a raw number, produces a compact value with a suffix); `--from=UNIT`
scales *up* (takes a suffixed value, produces a raw number). The suffix
system is the core of the tool:

| UNIT | Meaning | `1048576` → | `2M` → |
|---|---|---|---|
| `none` | no scaling; pass through | `1048576` | invalid |
| `si` | powers of 1000 (`k M G T P E Z Y`) | `1.1M` | `2000000` |
| `iec` | powers of 1024 (`K M G T P E Z Y`) | `1.0M` | `2097152` |
| `iec-i` | powers of 1024, IEC names (`Ki Mi Gi`) | `1.0Mi` | `2097152` |
| `auto` | input side: suffixed numbers are scaled (SI for `K`, IEC for `Ki`), bare numbers pass through | — | — |

Verified round trips:

```bash
$ numfmt --to=iec 1048576
1.0M
$ numfmt --from=iec 2M
2097152
$ numfmt --to=iec-i --suffix=B 2097152
2.0MiB
$ numfmt --from=auto 5K; numfmt --from=auto 5Ki
5000
5120
```

`numfmt` is field-aware, which is what makes it a *pipeline* tool rather than
a calculator: `--field=N` converts only field N of each input line, `-d X`
sets a single-character delimiter instead of whitespace, and `--header[=N]`
passes the first N lines through untouched. Fields other than the selected
ones are copied verbatim — and never parsed, so text like `sda1` is fine.

```bash
$ printf 'a b 1000\nc d 1048576\n' | numfmt --field 3 --to=iec
a b 1000
c d    1.0M
```

Note the automatic padding: when an input field is followed by whitespace,
`numfmt` pads converted output so columns stay aligned (see `--padding`).

Only *numbers* are transformed. With `--from=none` (the default input mode)
the tool still parses its input as a number when converting for `--to`;
anything that is not a valid number aborts by default:

```bash
$ numfmt --to=iec abc
numfmt: invalid number: 'abc'        # exit status 2
$ numfmt --invalid=ignore --to=iec abc 1000
abc 1000                             # rc 0, garbage in garbage out
```

`numfmt` reads operands or standard input only — it has no file arguments, so
the file must come from a redirect or a pipe. Lines whose selected field is
missing are passed through unchanged with exit status 0, which makes silent
column drift possible in long pipelines.

## Options That Matter

| Option | Effect |
|---|---|
| `--to=UNIT` / `--from=UNIT` | Scale down / up using `none`, `si`, `iec`, `iec-i`, `auto` |
| `--to-unit=N` / `--from-unit=N` | Custom unit size, e.g. `--to-unit=8` to convert bits→bytes semantics |
| `--field=FIELDS` | Convert only these fields (default 1); supports ranges like `1-3` |
| `-d, --delimiter=X` | Single-character field delimiter (default whitespace) |
| `--header[=N]` | Pass first N lines through unconverted (default 1 when given) |
| `--suffix=S` | Append S to output; also accepted (optional) on input |
| `--padding=N` | Pad output to N chars; positive right-aligns, negative left-aligns |
| `--format=FMT` | printf-style float format around the converted value (e.g. `%9f`) |
| `--round=METHOD` | `up`, `down`, `from-zero` (default), `towards-zero`, `nearest` |
| `--invalid=MODE` | Invalid-input behavior: `abort` (default), `fail`, `warn`, `ignore` |
| `--grouping` | Locale digit grouping (`1,000,000`) — a no-op in the C/POSIX locale |
| `-z, --zero-terminated` | NUL instead of newline as line delimiter |

## Usage Patterns

```bash
# Human-readable du output, but from byte-exact data you can still sort
du -B1 /var/log/* | sort -rn | numfmt --to=iec | head
```

```bash
# Same for df: keep the header row untouched
df -B1 | numfmt --header --field 2-4 --to=iec
```

```bash
# Convert a human-suffixed value back to bytes for arithmetic
BLOCKS=$(( $(numfmt --from=iec 1.5G) / 4096 ))
```

```bash
# Normalize mixed user input: accepts 5K, 5Ki, 5000 alike
SIZE=$(numfmt --from=auto "$1")
```

```bash
# Byte counts with an explicit binary unit and suffix for documentation
numfmt --to=iec-i --suffix=B 3145728        # 3.0MiB
```

```bash
# Metric units for a capacity report, rounding up so capacities read safely
numfmt --to=si --round=up 999900            # 1.0M
```

```bash
# Convert a column inside a TSV without touching the rest
printf 'id\tbytes\tname\n7\t1048576\timg.png\n' | numfmt --header --field=2 --to=iec
```

```bash
# /proc/meminfo style values with a fixed suffix column for logging
grep MemAvailable /proc/meminfo | awk '{print $2}' | numfmt --to=iec --suffix=B
```

```bash
# Left-pad a small table so converted values form a column (negative padding)
numfmt --to=iec-i --suffix=B --padding=-12 1048576 2097152
```

```bash
# Convert block counts into bytes with a custom unit size
numfmt --from-unit=512 --from=none 100      # 100 × 512 = 51200
```

```bash
# NUL-delimited value lists (safe when values travel with other data)
printf '%s\0' 1000 2048000 | numfmt -z --to=iec | tr '\0' '\n'
```

## Nuances and Gotchas

- **`K` is 1000 or 1024 depending on the unit — decide explicitly.** `si`
  treats `K` as 1000, `iec` as 1024, and `iec-i` also renames to `Ki`. The
  bare word "megabyte" in a shell script is exactly the ambiguity this tool
  exists to remove; hard-code the unit in scripts.
- **`auto` means "SI suffix, or IEC if the `i` is there"** — `5K` → 5000,
  `5Ki` → 5120. That is the right behavior for parsing *user* input, but it
  will quietly misread `du -h` style values if you assume IEC; use
  `--from=iec` for those.
- **No file operands.** `numfmt file` silently treats `file` as a string to
  (not) convert; forgetting the `<` or `|` produces a no-op exit 0, not an
  error. Check with `--invalid=fail` when input must be numeric.
- **`--invalid` default is `abort` (exit 2)** — one bad line in a stream kills
  the conversion. Use `--invalid=warn`/`ignore` for mixed logs, but then
  validate that the untouched lines are really acceptable to your consumer.
- **Rounding surprises:** the default is `from-zero` (away from zero), so
  1048577 → `1.1M` with `--to=iec` (verified). Capacity reports often want
  `--round=up`; billing often wants `--round=down`.
- **`--grouping` is locale-dependent and inert under `LC_NUMERIC=C/POSIX`** —
  most servers never produce `1,000,000` even with the flag. Set the locale
  deliberately or format with `printf "%'d"`.
- **Padding is automatic when whitespace follows the field** and can surprise
  diff-based tests; pin `--padding=1` (no padding) for byte-stable output.
- **Not portable:** absent from BSD/macOS base systems and busybox. Scripts
  that must run there need an awk fallback or a vendored copy.

## Exit Status

| Code | Meaning |
|---|---|
| 0 | Success (lines with missing/extra fields pass through untouched) |
| 2 | Invalid number under the default `--invalid=abort`, or a serious error |

## Related Commands

- [`sort`](./sort.md) — `sort -h` orders human-suffixed numbers; numfmt converts them
- [`od`](./od.md) — when "human readable bytes" becomes "what are these bytes actually"
- [`overview`](./overview.md) — the coreutils collection hub

## Interview Questions

### Q: What is the difference between numfmt --to=iec and --to=si?

The suffix base: `iec` scales by 1024 (`2M` = 2097152) while `si` scales by
1000 (`2M` = 2000000); `iec-i` is IEC with unambiguous names (`Mi`). Disk and
RAM tools in GNU userland speak 1024 semantics (`du -h`, `sort -h`), while
network and marketing figures speak 1000. Choosing wrong is a systematic ~5%
error per suffix step.

### Q: How do you make du output that is both human-readable and sort-able?

`du -B1 | sort -rn | numfmt --to=iec`. The trick is ordering the pipeline:
sort on exact byte counts, convert to human units last. Doing `du -h | sort`
reorders by lexicographic suffixes and puts `10K` after `2G`; `sort -h` on
`du -h` output works too, but the numfmt variant keeps a single conversion
step and composes with `--header`/`--field`.

### Q: A script accepts sizes from users like "500M" or "2GiB" — how does numfmt help?

`numfmt --from=auto` normalizes suffixed input: SI suffixes (`K`,`M`,`G`) go
by 1000, IEC suffixes (`Ki`,`Mi`,`Gi`) by 1024, and bare numbers pass through.
Combined with `--invalid=fail` and an `--suffix` echo, it gives you one line of
validated, unit-explicit parsing instead of a regex-plus-case tree.

### Q: What does numfmt do with non-numeric input by default, and why does that matter in pipelines?

With default `--invalid=abort` it errors with "invalid number" and exits 2 on
the first bad line, which fails fast but takes down the whole pipeline on one
junk line — a real problem when scanning logs. `--invalid=warn`/`ignore` pass
bad lines through unchanged, trading strictness for resilience; scripts that
consume the output must then tolerate non-numeric fields.

### Q: Why does numfmt have no file arguments, and what is the practical consequence?

It is a strict stdin/stdout filter like the rest of the coreutils text family.
The consequence is that forgetting the redirect (`numfmt --to=iec file`
instead of `numfmt --to=iec < file`) produces exit 0 with the filename echoed
through — a silent bug. Defense-in-depth: `--invalid=fail` plus checking that
the output actually converted.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/coreutils/numfmt.1.en.html)
- [Source — GitHub mirror](https://github.com/coreutils/coreutils)
- [Source — Debian sources](https://sources.debian.org/src/coreutils/)
