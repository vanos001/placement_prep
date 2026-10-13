# rtcwake — schedule an RTC alarm and suspend until it fires

## Overview

`rtcwake` chains two kernel operations into one command: it programs the
real-time clock (RTC) hardware alarm for a future point in time, then puts
the system into a sleep state (`standby`, `mem`, `disk`, `off`). When the
alarm fires, the platform resumes and `rtcwake`'s internal sleep returns,
so a script can run `rtcwake -m mem -s 900 && run-battery-test.sh` and
continue executing exactly at the moment of resume. It ships with the
`util-linux` package (Debian bookworm) at `/usr/sbin/rtcwake` and requires
root, because it writes to `/sys/class/rtc/*/wakealarm` and
`/sys/power/state`.

`rtcwake` is often confused with `hwclock` (reads or sets the RTC clock
itself — it never programs alarms nor suspends), with `systemctl suspend`
(suspends immediately, but has no built-in timed wake), and with `cron` or
`at` (which schedule *work*, not *wakeups*: a suspended machine will not
run cron until something wakes it, which is exactly the gap `rtcwake`
fills).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/sbin/rtcwake |
| First appeared / lineage | util-linux addition of the mid-2000s (2.13 era) |
| Standards | None — Linux RTC/ACPI specific |

## Synopsis

```
rtcwake [options] [-m mode] {-s seconds | -t time_t | --date timestamp}
```

Common one-line forms:

```
rtcwake -m mem -s 900              # suspend to RAM, wake in 15 minutes
rtcwake -n -s 60                   # dry run: print what would be done
rtcwake -m mem --date "2025-06-01 06:30:00"
rtcwake -m show                    # print the currently configured alarm
```

## How It Works

### Two independent kernel operations

`rtcwake` is a thin, root-only orchestrator. It performs these steps in
order:

1. Resolves the RTC device (default `/dev/rtc0`, override with `-d`).
2. Decides which clock domain the RTC runs in — UTC or local time. By
   default it reads `/etc/adjtime` (`-a`), whose third line says `UTC` or
   `LOCAL`; `-u` and `-l` override this.
3. Converts the requested wakeup time (`-s` seconds from now, `-t` an
   absolute `time_t`, or `--date` a human timestamp) into seconds since
   the epoch.
4. Writes that epoch value to `/sys/class/rtc/rtcN/wakealarm` (the kernel
   programs the hardware comparator).
5. Writes the requested mode to `/sys/power/state`, which suspends the
   system. `rtcwake` itself then sleeps inside the kernel call.
6. On resume — triggered by the RTC alarm line through ACPI — the kernel
   restores state, `rtcwake`'s sleep returns, and the process exits 0.

```
 rtcwake process                          kernel / hardware
 ─────────────────                        ──────────────────
 read /etc/adjtime ──┐
 compute epoch ──────┤
 write wakealarm ────┴────────────►  RTC alarm register programmed
 write mode ─────────────────────►  /sys/power/state = "mem"
                                    ... platform suspends ...
                                    RTC wall clock == alarm value
                                    RTC pulls the wake line (ACPI)
                                    ... platform resumes ...
 rtcwake exits 0  ◄──────────────   kernel restores process state
```

### Sleep modes

The `-m` mode names map to ACPI sleep states and to what the kernel
actually supports:

| Mode | Meaning |
| --- | --- |
| `standby` | ACPI S1, shallow and rarely used today |
| `mem` | Suspend to RAM (S3, or `s2idle` on modern laptops) |
| `disk` | Suspend to disk / hibernate (S4; needs working hibernation setup) |
| `off` | Power off (S5), wake from the alarm |
| `on` | Do not suspend; wait synchronously until the alarm time |
| `no` | Do not suspend and do not touch the alarm; print what would happen |
| `disable` | Cancel a previously programmed alarm |
| `show` | Print the current alarm configuration |

The default is `standby`. In practice nearly everyone uses `-m mem`.
Which modes are available is a kernel property:

```bash
$ cat /sys/power/state          # kernel-supported states
freeze mem disk
$ rtcwake --list-modes          # names this rtcwake build can pass
```

### Clock domains — the classic failure

The RTC ticks wall-clock time in *some* timezone, recorded in
`/etc/adjtime`. If the RTC keeps UTC (the normal Linux setup) but you ask
for a wakeup in local time, or vice versa, the machine wakes at the wrong
hour — typically off by the UTC offset. Recent `rtcwake` defaults to `-a`,
reading the domain from the adjust file, so the historical advice "always
pass `-u`" is outdated; verify instead:

```bash
$ tail -1 /etc/adjtime          # UTC or LOCAL
UTC
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-s, --seconds <sec>` | Wake this many seconds from now (relative). |
| `-t, --time <time_t>` | Wake at this absolute epoch value (UTC seconds). |
| `--date <timestamp>` | Wake at a human-readable date/time. |
| `-m, --mode <mode>` | Sleep state; default `standby`, usually `mem`. |
| `-a, --auto` | Read clock domain from the adjust file (default in recent util-linux). |
| `-l, --local` | RTC stores local time (override). |
| `-u, --utc` | RTC stores UTC (override). |
| `-A, --adjfile <file>` | Use another adjust file instead of `/etc/adjtime`. |
| `-d, --device <dev>` | RTC device to use (`rtc0`, `rtc1`, ...). |
| `-n, --dry-run` | Do everything except programming the alarm and suspending; prints the plan. |
| `--list-modes` | Print the suspend modes this build supports. |
| `-v, --verbose` | More diagnostics (device, computed alarm time). |

## Usage Patterns

```bash
# Suspend to RAM and wake in 15 minutes (root)
rtcwake -m mem -s 900
```

```bash
# Rehearse a wakeup without actually sleeping
rtcwake -n -m mem -s 900
# prints the device, the mode and the absolute alarm time it computed
```

```bash
# Wake at an absolute wall-clock time, then immediately run a job
rtcwake -m mem --date "2025-06-01 03:00:00" && /usr/local/bin/nightly-backup.sh
```

```bash
# Suspend 30 minutes after boot for a power-consumption lab
systemd-run --on-active=1800 rtcwake -m mem -s 3600
```

```bash
# Find out which sleep states this kernel/platform supports
cat /sys/power/state
rtcwake --list-modes
```

```bash
# Inspect and cancel a pending alarm
rtcwake -m show
rtcwake -m disable
```

```bash
# Run a workload right after resume, measuring cold-start behavior
rtcwake -m mem -s 60 && systemctl restart myservice && time curl -s localhost:8080
```

```bash
# Use the second RTC on boards that expose several (e.g. RTC vs. PMIC clock)
rtcwake -d rtc1 -m mem -s 300
```

```bash
# Cron entry: suspend now, wake at 03:00 for a backup window
# 0 22 * * * root rtcwake -m mem -t "$(date -d '05:00 tomorrow' +%s)"
```

```bash
# Force the clock domain when /etc/adjtime is missing or wrong
rtcwake -u -m mem -s 600
```

## Nuances and Gotchas

- **Root only.** Writing `/sys/power/state` and the wakealarm sysfs node
  requires root. As an unprivileged user you get an open/probe failure and
  exit status 1 — e.g. `rtcwake: /dev/rtc0: unable to find device` when the
  device node is absent.
- **Hardware support is not guaranteed.** The wake path needs ACPI RTC
  alarm support (`CONFIG_RTC_CLASS`, `CONFIG_PM`, ACPI wake events). Many
  VMs and some ARM boards cannot wake from `mem` at all; `-n` plus a short
  real test is the only reliable check on new hardware.
- **`-s`, `-t` and `--date` mean different things.** `-s` is relative,
  `-t` takes a raw epoch (which is timezone-independent), `--date` is
  parsed as a calendar time and therefore depends on the clock-domain
  decision. Mixing them up produces off-by-timezone alarms.
- **Clock-domain mismatch is the classic bug.** Symptom: the machine wakes
  consistently 2 or 3 hours (or 12) late/early. Check `tail -1
  /etc/adjtime` before blaming the tool.
- **`disk` mode needs hibernation configured.** Suspend-to-disk requires a
  resume-capable swap area and `resume=` kernel parameters; `rtcwake -m
  disk` on a box without that setup just fails or does a plain poweroff.
- **`rtcwake` returns after resume**, so `rtcwake ... && cmd` is the
  intended idiom for post-resume work. If the machine is woken early by a
  power button or network wake, `rtcwake` still returns and your script
  proceeds earlier than planned.
- **systemd installs sleep hooks** (`/usr/lib/systemd/system-sleep/`) that
  run on every suspend/resume regardless of who initiated it; `rtcwake`
  suspensions are not special in that respect.
- **BusyBox ships its own smaller `rtcwake`** with the same core flags
  (`-s`, `-t`, `-m`, `-d`, `-l`/`-u`); embedded initramfs images may get
  the BusyBox variant, whose diagnostic output differs.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Alarm programmed and (for real modes) resume completed; also success for `show`/`no`. |
| non-zero (1 observed) | Any failure: no RTC device, permission denied, unsupported mode, unparseable date. |

The man page documents no detailed code table; script against 0 vs
non-zero.

## Related Commands

- [`hwclock`](./hwclock.md) — read/set the RTC clock itself; same clock-domain logic (`/etc/adjtime`).
- [`dmesg`](./dmesg.md) — kernel messages document the suspend/resume cycle.
- [systemd](../../admin/systemd.md) — `systemctl suspend`, sleep hooks and timers interact with manual suspend cycles.
- [util-linux overview](./overview.md) — collection hub for the other util-linux pages.

## Interview Questions

### Q: How does rtcwake know whether the RTC stores UTC or local time?

It reads `/etc/adjtime` (the third line, `UTC` or `LOCAL`) — that is the
`-a/--auto` default in recent util-linux. `-u` and `-l` force a domain,
which is useful when the adjust file is missing or wrong. Getting this
wrong is the classic "wakes at the wrong hour" bug, because the alarm
register is compared against hardware wall-clock time, not epoch time.

### Q: You need a machine to sleep for 30 minutes and then run a test script immediately. How?

`rtcwake -m mem -s 1800 && test.sh` — `rtcwake` blocks in the suspend
syscall and returns as the platform resumes, so the shell continues
sequentially at wake time. If the box may also be woken by other wake
sources (WoL, power button), the script should validate elapsed time
before trusting the run.

### Q: What is the difference between `-s`, `-t` and `--date`?

`-s` is relative seconds from now; `-t` is an absolute `time_t` (epoch
seconds, timezone-independent — good for computing with `date +%s`);
`--date` is a calendar timestamp parsed against the RTC's clock domain.
They are mutually exclusive and `-s` is the safest for scripts because no
timezone reasoning is involved.

### Q: Why might rtcwake -m mem fail on a machine that suspends fine with the power button?

`rtcwake` writes `/sys/power/state` itself and requires a functional RTC
alarm wake source. A GUI session may suspend through systemd/logind using
the same state but the platform may lack ACPI alarm wake support, the
`wakealarm` sysfs node may be missing, or the kernel may only support
`freeze` (s2idle) while you asked for a mode the firmware does not wire
up. Diagnose with `-n`, `rtcwake --list-modes` and `cat
/sys/power/state`.

### Q: What are the special modes `no`, `on`, `disable` and `show` for?

`no` is a rehearsal: compute and print everything, change nothing. `on`
keeps the machine awake and busy-waits until the alarm time — useful to
test the alarm path without suspend. `disable` cancels a pending alarm
(leftover alarms cause surprise wakeups). `show` prints the currently
configured alarm, which is how you verify what a previous run programmed.

### Q: Where does the actual wake signal come from?

The kernel writes the requested epoch into the RTC's alarm registers; the
RTC chip pulls its alarm line when its wall-clock time matches, and ACPI
turns that into a platform wake event. The CPU resume path restores the
suspended image (RAM) or the hibernation image (swap), then the woken
`rtcwake` process finishes its sleep and exits.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/rtcwake.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
