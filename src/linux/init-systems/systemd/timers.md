# Timer Units (systemd.timer)

## Overview

A `.timer` unit is systemd's replacement for cron, `at`, and `anacron`: it
describes *when* a unit (almost always a oneshot `.service`) should be
activated. Where cron has a single crontab grammar and an implicit "run in
an almost-empty environment, mail the output" model, timer units are plain
units — they participate in the dependency graph, inherit
`systemd.exec(5)` sandboxing and resource controls, log every run to the
journal under their own unit name, and can express both calendar schedules
("02:30 every Sunday") and monotonic schedules ("90 seconds after boot",
"one hour after the service last deactivated").

The design goal is not merely "cron with a different syntax". Timer units
solve the operational problems that make cron jobs unreliable in practice:
runs missed while the machine is off can be *caught up* (`Persistent=`,
which is exactly what anacron exists to do), thousands of identical jobs can
be spread out with a randomized delay instead of stampeding at 03:00, jobs
can be ordered after `network-online.target` instead of raced against it,
and every invocation — success, failure, and output — lands in
`journalctl -u <name>.service` instead of a mail spool nobody reads. The
trade-off is verbosity and a grammar (`systemd.time(7)`) that must be
learned once; `systemd-analyze calendar` exists to make that grammar
verifiable before it goes into production.

Anatomy is worth stating up front because it surprises people: a timer does
not run anything itself. It watches its schedule and *activates* another
unit — by default the `.service` with the same basename
(`backup.timer` triggers `backup.service`; `Unit=` overrides). The service
is a completely ordinary unit, so everything from
[service-units](./service-units.md) applies, including `Type=oneshot`,
`Condition*=` guards, and `Nice=`/`IOSchedulingClass=`.

## Monotonic Timers

Monotonic timers trigger relative to a clock that does not step (kernel
`CLOCK_MONOTONIC`-anchored bookkeeping inside the manager), so they are
immune to NTP corrections, manual date changes, and timezone edits. Five
directives exist, each anchored to a different starting point:

| Directive | Anchor |
|---|---|
| `OnActiveSec=` | When the *timer unit itself* is activated |
| `OnBootSec=` | When the machine booted; in containers the system manager maps this to `OnStartupSec=` |
| `OnStartupSec=` | When the *manager* started (system manager: early boot; user manager: login) |
| `OnUnitActiveSec=` | When the unit the timer activates was *last activated* |
| `OnUnitInactiveSec=` | When the unit the timer activates was *last deactivated* |

Multiple monotonic lines can be combined in one timer, and each takes a
time span value (`5min 20s`, `1h`, `90`). A classic hourly-with-warmup
pattern:

```ini
[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
AccuracySec=1s
```

This fires five minutes after boot, then once per hour — but "per hour"
means *an hour after the service was last activated*, not on the wall-clock
hour. After a reboot the phase resets, and a service that runs long shifts
every subsequent firing. That is the fundamental difference from cron: if
the schedule must land on wall-clock boundaries (02:30, top of the hour,
first Monday), you need a calendar timer. Monotonic timers are for
"intervals since some event", which is precisely what most maintenance jobs
actually want — and what makes them stable across suspend/resume and clock
steps, where crontabs historically misfire.

Note the anchor subtlety of `OnUnitActiveSec=`: the clock it measures is
the *triggered unit's* activation, not the timer's. If the service is
triggered by something else as well (a path unit, a manual `systemctl
start`), the timer's next elapse shifts accordingly — occasionally useful,
occasionally a bug source.

## Calendar Timers: the OnCalendar= Grammar

`OnCalendar=` uses the `systemd.time(7)` calendar grammar:

```
DayOfWeek Year-Month-Day Hour:Minute:Second
 Sun      2025-**-**   04:00:00        # every field may be a wildcard *
```

Every component accepts: a single value, a list (`Mon,Wed,Fri`), a range
(`Mon..Fri`, `01..07`), a repetition (`0/15` = every 15 starting at 0;
`1..10/2` = 1,3,5,7,9), or `*`. Either the time part or the date part may
be omitted entirely (missing time means `00:00:00`, missing date means
`*-*-*`), a missing seconds field means `:00`, and a date component may
use `~` to count from the *end* of the month (`*-02~03` = third-last day
of February; `Mon *-05~07/1` = the last Monday of May).

| Schedule | OnCalendar= | Notes |
|---|---|---|
| Every 15 minutes | `*:0/15` | minutes 0, 15, 30, 45 — *not* cron's `*/15` |
| 04:00 every Sunday | `Sun *-*-* 04:00:00` | `Sun *-*-* 04:00` also parses |
| First of the month | `*-*-01 00:00:00` | this is exactly the `monthly` shortcut |
| Last day of the month | `*-*~01 00:00:00` | one day counted back from month end |
| Last Friday of the month | `Fri *-*~07/1 12:00:00` | tilde + weekday + repetition |
| Business hours, hourly | `Mon..Fri *-*-* 09..17:00:00` | 09:00 through 17:00 on weekdays |
| Once a year | `annually` (`*-01-01 00:00:00`) | named shortcuts below |
| 03:00 pinned to UTC | `*-*-* 03:00:00 UTC` | timezone suffix, IANA names work |

Named shortcuts cover the cron classics and a few extras: `minutely`,
`hourly`, `daily`, `midnight`, `weekly`, `monthly`, `quarterly`,
`semi-annually`, `annually`/`yearly`. They are pure syntax sugar —
`systemd-analyze calendar daily` prints the normalized form — but they
make unit files self-documenting and reviewable.

Two timezone facts matter. First, calendar expressions evaluate in the
*local* timezone and follow DST transitions; a 02:30 job stays at 02:30
local time across summer/winter, and an IANA suffix (`Europe/Berlin`,
`America/New_York`) pins the schedule to a zone independent of the host's
current zone. Second, suffixing `UTC` removes DST from the equation
entirely — the pragmatic choice for "same interval always" jobs like
certificate renewal, and one of the cleanest answers to the old cron
"my job ran twice / not at all on DST night" class of bugs.

Never trust a calendar expression you have not evaluated. `systemd-analyze
calendar` parses the expression, shows its normalized form and the next
elapses:

```text
$ systemd-analyze calendar "Mon..Fri *-*-* 09:00:00"
  Normalized form: Mon..Fri *-*-* 09:00:00
    Next elapse: Mon 2025-06-09 09:00:00 CEST
       (in UTC): Mon 2025-06-09 07:00:00 UTC
      From now: 1 day 3h left
$ systemd-analyze calendar --iterations=5 weekly
```

A mistyped expression fails here with a parse error instead of silently
never firing in production — use it in code review, in CI for unit-file
linting, and whenever a timer "does not seem to run".

## Timer Options That Do the Heavy Lifting

| Directive | Default | Effect |
|---|---|---|
| `Persistent=` | `no` | Store last-trigger timestamp on disk; on activation, fire immediately if a scheduled elapse was missed (only meaningful for `OnCalendar=`) |
| `AccuracySec=` | `1min` | Fire anywhere within the window `[t, t+AccuracySec]`; the manager coalesces wakeups inside the window |
| `RandomizedDelaySec=` | `0` | Add a uniformly random 0..value delay to each elapse |
| `FixedRandomDelay=` | `no` (v247+) | Make the random delay deterministic per machine/manager/timer instead of per firing |
| `Unit=` | same-basename `.service` | Which unit to activate |
| `WakeSystem=` | `no` | Elapsing timer resumes the system from suspend (RTC alarm; system manager only) |
| `RemainAfterElapse=` | `yes` | Keep the timer loaded (and queryable) after it elapsed and the triggered unit deactivated |
| `OnClockChange=` / `OnTimezoneChange=` | `no` (v242+) | Trigger the unit when CLOCK_REALTIME jumps / the timezone changes |

`Persistent=yes` is the anacron killer. The timestamp is stored in
`/var/lib/systemd/timers/stamp-<unit>`; when the timer activates after
downtime, the manager compares the stored stamp against the schedule and
triggers the service once if any elapse was missed. Three caveats worth
memorizing: it applies *only* to `OnCalendar=` timers (a monotonic
"1h after boot" schedule has no missed elapses by definition); the
catch-up run is subject to `RandomizedDelaySec=` like any other; and the
stamp file can be inspected or removed — `systemctl clean --what=state
<timer>.timer` resets the timestamp, the documented way to stop a
"Persistent" timer from immediately catching up after you deliberately
disabled it for a week.

`AccuracySec=` deserves a paragraph because it embodies a design stance.
The default 1-minute window means a 02:30 job fires *some time between
02:30 and 02:31* — the manager deliberately groups expirations of many
timers into shared wakeups to batch CPU wakeups and save power. Jobs that
need precision set `AccuracySec=1s` (or `1us`); jobs that only need "nightly"
can set `AccuracySec=1h` and let the scheduler pack them together.
`RandomizedDelaySec=` then handles the *cross-machine* thundering herd
(thousands of hosts hitting the same mirror at 02:30), while
`AccuracySec=` handles the *same-machine* wakeup stampede. For fleet-wide
de-centralization, `FixedRandomDelay=yes` derives one stable offset per
machine from the machine ID, so each host keeps the same nightly phase
across reboots while different hosts differ — the pattern used by
certificate renewers that must avoid synchronized mass renewal.

`WakeSystem=` wires the timer to the RTC (`timerfd` on the suspend clock +
`wakealarm`), letting a suspended laptop wake for a backup. It does *not*
re-suspend afterwards, requires privileges, and is meaningless without
suspend support — mention it in interviews as the mechanism behind
"scheduled wakeups", not as a job scheduler.

## Which Unit Gets Triggered, and Transient Timers

By default `foo.timer` activates `foo.service`; `Unit=bar.service`
overrides. Both units are ordinary files created like any other
(see [unit-files](./unit-files.md)); the timer is the unit you `enable`,
typically `WantedBy=timers.target`:

```ini
# /etc/systemd/system/cleanup.timer
[Timer]
OnCalendar=daily
Persistent=yes

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/cleanup.service
[Service]
Type=oneshot
ExecStart=/usr/local/bin/cleanup.sh
```

Timer pairs do not have to be installed at all — `systemd-run(1)` creates
*transient* timer/service pairs from the command line, which is the
modern `at` and a stopgap `cron` replacement:

```bash
# one-shot reminder in 45 minutes (transient .timer + .service)
systemd-run --on-active=45min --unit=tea-reminder \
    /usr/bin/notify-send "tea"

# recurring cleanup, transient but persistent across the manager's life
systemd-run --on-calendar="*:0/15" --unit=tmp-sweep \
    --timer-property=AccuracySec=1s /usr/local/bin/sweep

# schedule for later boot: transient units vanish on restart unless made permanent
systemd-run --on-calendar="2025-12-31 23:59:00" --collect --wait \
    /usr/local/bin/newyear.sh
```

`--on-active`/`--on-calendar` map directly onto the monotonic and calendar
directives above; `--timer-property=` attaches any timer option to the
transient unit. `--wait` blocks until the run finishes (exec-like
semantics), `--collect` garbage-collects the failed unit afterwards. For
scripted or API-driven scheduling this is the same machinery
`StartTransientUnit` on the D-Bus API drives — see
[apis-development](./apis-development.md) for that layer.

## Observability: list-timers, journal, properties

```text
$ systemctl list-timers --all
NEXT                        LEFT  LAST PASSED  UNIT                    ACTIVATES
Mon 2025-06-09 02:30:12 CET 6h left - -          logrotate.timer         logrotate.service
Mon 2025-06-09 09:00:00 CET 6h left Sun ... 23h man-db.timer            man-db.service
```

The columns answer the operational questions at a glance: `NEXT`/`LEFT`
for what is coming, `LAST`/`PASSED` for what happened (`-` means never ran
— the classic symptom of a timer enabled but never triggered, or a
`Persistent=` timer whose stamp was removed), `UNIT` for the timer and
`ACTIVATES` for the unit it will start (this column is how `Unit=`
overrides and timer-to-service mismatch become visible). `--all` includes
inactive/transient timers; without it, list-timers shows only loaded,
active timers.

Deeper verification:

```bash
systemctl show backup.timer -p NextElapseUSecRealtime -p LastTriggerUSec
journalctl -u backup.service --since today        # the actual job output
journalctl -u backup.timer                        # "Timer elapsed" lines
journalctl -t systemd --grep "backup"             # manager-side activation log
```

When a timer "did not fire", the diagnosis order is: (1) is the timer
active and loaded (`systemctl status backup.timer` — an enabled-but-not-
active timer schedules nothing); (2) what does `NextElapseUSecRealtime`
say (a `Persistent=no` timer freshly started shows the *next* schedule,
not a catch-up); (3) did the service fail its `Condition*=` guards — the
timer fires, the service is *skipped* (`Condition check resulted in ...
being skipped` in the journal), which looks exactly like "the job did not
run" but is a service property; (4) for calendar math, reproduce with
`systemd-analyze calendar`; (5) inspect the stamp file
`/var/lib/systemd/timers/stamp-<unit>` (mtime = last persistent trigger)
and reset state with `systemctl clean --what=state` if a deliberate
disable should not trigger a catch-up. Distinguish carefully between
"timer elapsed" (journal, from the manager) and the *service's* result —
the timer's only job is activation; a failing `ExecStart=` is a service
problem visible in `-u <service>` and `systemctl status`.

## Timers vs cron: a comparison table

| Aspect | cron / anacron | systemd timer |
|---|---|---|
| Schedule grammar | 5-field crontab, terse, unforgiving | `systemd.time(7)`, verbose, `systemd-analyze calendar`-verifiable |
| Environment | Minimal: `SHELL=/bin/sh`, short `PATH`, `%` must be escaped | Full unit environment: `Environment=`, `EnvironmentFile=`, `WorkingDirectory=`, sandboxing |
| Output/logging | Mailed to local user (often unread) | Per-unit journal: `journalctl -u name.service` |
| Missed runs | anacron for daily-class jobs, else lost | `Persistent=yes`, built in, timestamp per unit |
| Dependencies | None; `@reboot` hack, sleep-and-pray for network | Full dependency graph: `After=network-online.target`, `RequiresMountsFor=` |
| Load spreading | Manual `sleep N &&` in the command | `AccuracySec=`, `RandomizedDelaySec=`, `FixedRandomDelay=` |
| Per-user jobs | crontab per user | `systemctl --user` timers + `loginctl enable-linger` for headless users |
| Precision | Minute resolution | Second (calendar) / nanosecond (monotonic spans) |
| Clock changes | Jobs can be skipped/repeated around DST | Monotonic timers immune; calendar timers zone-pinnable via suffix |
| Introspection | Grep crontabs across /var/spool, /etc | `systemctl list-timers`, `systemctl show`, unified state |

The remaining cron advantages are brevity and universality — a one-line
crontab is faster to type than two unit files, and cron exists on systems
without systemd (see [cron](../../admin/cron.md) for the classic
semantics, `/etc/cron.*` spool layout, and the anacron model in detail).
But note what the table implies for interviews: "cron job missed because
the box was down" and "cron mailed root and nobody saw it" are both
one-line answers with `Persistent=yes` and the journal.

## Real-World Examples

### Nightly backup with catch-up and load spreading

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Nightly backup

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=yes
RandomizedDelaySec=30min
AccuracySec=1s

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/backup.service
[Unit]
RequiresMountsFor=/backups
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
Nice=19
IOSchedulingClass=idle
ExecStart=/usr/local/bin/backup.sh
TimeoutStartSec=6h
```

Read the design: `Persistent=yes` makes a powered-off laptop catch up at
next boot; `RandomizedDelaySec=30min` keeps a fleet from hammering the
backup server at exactly 02:30; `AccuracySec=1s` opts out of the default
1-minute coalescing because the start time matters; the service carries
the *dependencies* (`network-online.target` instead of cron's hope that
the interface is up) and the politeness settings (`Nice=19`,
`IOSchedulingClass=idle`) that cron deployments usually achieve with a
`nice`/`ionice` prefix; `TimeoutStartSec=` bounds a hung rsync.

### Hourly log cleanup

```ini
[Timer]
OnBootSec=15min
OnUnitActiveSec=1h

[Install]
WantedBy=timers.target
```

The monotonic pair means "15 minutes after boot, then hourly after each
run" — phase-free, immune to clock steps, and it never stacks runs: while
the oneshot service is executing, the elapse is not lost but the *next*
activation is measured from when it last finished. This is essentially
what `systemd-tmpfiles-clean.timer` ships (`OnBootSec=15min`,
`OnUnitActiveSec=1d`).

### Certificate renewal

```ini
[Timer]
OnCalendar=daily UTC
Persistent=yes
RandomizedDelaySec=1h
FixedRandomDelay=yes
```

UTC pinning removes DST from the equation; the fixed random delay gives
this machine one permanent phase offset so a fleet renews spread out yet
predictably — the pattern behind the ACME-renewal timers that ship in
modern distributions (`certbot-renew.timer` and equivalents). Note the
hierarchy of shipped timers on a Debian system — `apt-daily.timer`,
`apt-daily-upgrade.timer`, `dpkg-db-backup.timer`, `man-db.timer`,
`e2scrub_all.timer`, `fstrim.timer`, `logrotate.timer` — is itself the
best reading list: `systemctl cat` any of them to see the idioms above in
production trim.

## Interview Questions

### Q: Why does a timer with Persistent=yes only catch up for calendar schedules?

`Persistent=` stores the last-trigger *timestamp* and, on activation,
compares it against the schedule to detect missed elapses. Detection
requires knowing which wall-clock times were scheduled while the machine
was off — a property of `OnCalendar=` expressions. A monotonic schedule
(`OnBootSec=`, `OnUnitActiveSec=`) defines its elapses relative to events
that happen after boot, so there is nothing to catch up: the first elapse
recalculates naturally. That is also why monotonic timers are the right
tool for interval maintenance and calendar timers for deadlines.

### Q: What do AccuracySec and RandomizedDelaySec actually control, and how do they differ?

`AccuracySec=` (default 1min) widens each firing into a window and lets
the manager coalesce expirations inside it — a power optimization that
trades precision; a job "scheduled" for 02:30 fires between 02:30 and
02:31. `RandomizedDelaySec=` adds a uniformly random 0..N delay on top of
the scheduled time, *per firing* (or per machine with `FixedRandomDelay=`),
to de-synchronize jobs across machines or firings. Precision →
`AccuracySec=1s`; fleet spreading → `RandomizedDelaySec=`; both compose,
and the random delay applies even to `Persistent=` catch-up runs.

### Q: A cron job ran at 02:30 and the machine was off. How do timers fix this, and what resets the catch-up?

With `Persistent=yes` the timer writes a stamp to
`/var/lib/systemd/timers/stamp-<unit>` on each trigger; on the next
activation the manager sees a missed calendar elapse and runs the service
immediately (subject to `RandomizedDelaySec=`). The stamp is ordinary
state: inspect its mtime to see the last trigger, and clear it with
`systemctl clean --what=state <timer>.timer` when a deliberate outage
should *not* produce a surprise catch-up run — a detail people hit after
re-enabling a backup timer that had been off for a month.

### Q: Where do timer units beat cron for environment and dependency handling?

A cron process gets a minimal environment (`SHELL=/bin/sh`, a short
`PATH`) and no dependency context; scripts paper over this with absolute
paths, `source /etc/profile`, and sleep loops. A timer-activated service
is a full unit: `Environment=`/`EnvironmentFile=`, `WorkingDirectory=`,
`User=`, sandboxing from `systemd.exec(5)`, plus graph dependencies —
`After=network-online.target` (with `Wants=`) for network jobs,
`RequiresMountsFor=/backups` for storage. Every run is journalled under
its own unit name, replacing cron's mail-with-nobody-reading failure mode.

### Q: How do you schedule per-user background jobs that must run even when the user is logged out?

With user managers: create the `.timer`/`.service` pair under
`~/.config/systemd/user/`, `systemctl --user enable --now`, and enable
lingering — `loginctl enable-linger alice` — so the user manager starts at
boot and survives logout. Without lingering the user manager (and its
timers) dies with the last session. `OnStartupSec=` in a user timer is
anchored to the *user manager's* start, which is the per-user equivalent
of `@reboot`.

### Q: How would you debug "my timer never fired" end to end?

Check in order: (1) `systemctl status foo.timer` — enabled is not active;
enable *and* start (or reboot). (2) `systemctl list-timers --all` and
`systemctl show foo.timer -p NextElapseUSecRealtime` for the computed
elapse; `LAST/PASSED = -` means never triggered. (3) Validate the
expression with `systemd-analyze calendar` — a parse error fails the timer
load. (4) Check the *service*: `Condition*=` skips log
"Condition check resulted in ... being skipped"; the timer fired, the job
declined. (5) Journal the manager side (`journalctl -u foo.timer`,
"Timer elapsed") versus the job side (`-u foo.service`). (6) For
catch-up logic, inspect the stamp file and remember `Persistent=` only
applies to `OnCalendar=` schedules.

## References

- https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- https://manpages.debian.org/bookworm/systemd/systemd.timer.5.en.html
- https://manpages.debian.org/bookworm/systemd/systemd.time.7.en.html
- https://manpages.debian.org/bookworm/systemd/systemd-analyze.1.en.html
- https://manpages.debian.org/bookworm/systemd/systemd-run.1.en.html

## Cross-References

- [unit-files.md](./unit-files.md) — where `.timer`/`.service` files live and how they are enabled.
- [service-units.md](./service-units.md) — writing the oneshot services timers activate.
- [systemctl-cli.md](./systemctl-cli.md) — `list-timers`, `start`, `clean` in day-to-day operation.
- [journald.md](./journald.md) — reading per-unit run output with journalctl.
- [admin/cron.md](../../admin/cron.md) — the cron/anacron model timers replace, crontab syntax and spool layout.
- [comparison.md](../comparison.md) — scheduling across init systems.
- [admin/systemd.md](../../admin/systemd.md) — operator view of shipped timers on a running system.
