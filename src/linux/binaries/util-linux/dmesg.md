# dmesg — print or control the kernel ring buffer

## Overview

`dmesg` dumps (and controls) the kernel's *ring buffer*: the circular, in-memory
log where the kernel writes boot messages, hardware events, driver diagnostics,
OOM kills, filesystem errors, and anything printed with `printk`. On every
Linux system it is the first tool you reach for when hardware misbehaves, a
driver spams errors, or the OOM killer fires — and one of the few that works
even when userspace is mostly broken, because it talks to the kernel directly.

Debian bookworm ships it in the `util-linux` package at `/usr/bin/dmesg`
(man section 1). It can read the buffer through `/dev/kmsg` (the modern
interface), through the `syslog(2)`/`klogctl(3)` syscall (force with `-S`), or
from a saved file (`-F`/`-K`). It also *controls* logging: clear the buffer
(`-C`), enable/disable console echoing of messages (`-E`/`-D`), and set which
severities are echoed to the console (`-n`).

Do not confuse it with `journalctl -k` (systemd's persisted, indexed copy of
the same kernel messages), with `/var/log/kern.log` (syslog's file), or with
`dmesg` on BSD (similar spirit, different plumbing).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Section (man) | 1 |
| Path | /usr/bin/dmesg |
| Lineage | BSD heritage; Linux implementation in util-linux (klogctl/dev/kmsg) |
| Standards | None — Linux-specific logging interfaces (syslog(2), /dev/kmsg) |

## Synopsis

```
dmesg [options]
```

The five mutually-exclusive control forms:

```
dmesg --clear                 # -C: wipe the ring buffer
dmesg --read-clear [options]  # -c: print everything, then clear
dmesg --console-level <lvl>   # -n: set console log level
dmesg --console-on            # -E: echo messages to console again
dmesg --console-off           # -D: stop echoing messages to console
```

## How It Works

### The kernel ring buffer

Every `printk()` in kernel code formats a message tagged with a *log level*
(0-7) and a *facility* (kernel, daemon, user, …). Messages are appended to a
fixed-size circular buffer (set at boot by `log_buf_len=`, otherwise by kernel
config; typically megabytes). When the buffer fills, **oldest messages are
overwritten** — `dmesg` is a window, not an archive. That is the core reason
`journalctl -k` exists: persistence.

```
 write side                          read side
 printk() ──► ┌───────────────────────────┐ ──► dmesg (user)
              │  ●●●●●●●●●●●●●●●  head    │      journalctl -k (systemd)
              └───────────────────────────┘      /proc/kmsg → syslogd (klogd)
                 tail ── wraps & overwrites ──►  cat /dev/kmsg (raw binary stream)
```

Access paths, in order of preference for modern dmesg:

1. **`/dev/kmsg`** — a seekable, record-oriented stream; each record carries
   its own facility/level/timestamp. This is why modern `dmesg` can `--follow`
   and decode per-line metadata.
2. **`syslog(2)` / `klogctl(3)`** — the classic interface (`-S` forces it);
   requires sizing the receive buffer (`-s`), which is why old `dmesg` scripts
   fiddled with buffer sizes.
3. **Files** — `-F file` reads a text log captured elsewhere; `-K file` reads a
   `/dev/kmsg`-format binary dump.

### Timestamps: four ways to see the same message

The default timestamp is **seconds since kernel start** — deliberately, because
the wall clock is not trustworthy during early boot:

```bash
$ dmesg | head -2
[    0.000000] Linux version 5.x ...
[    0.012345] ACPI: ...

$ dmesg --time-format iso        # wall clock, microsecond precision
2025-01-01T10:15:30,123456+00:00 Linux version 5.x ...

$ dmesg -T                       # human ctime; warned as "may be inaccurate!"
[Wed Jan  1 10:15:30 2025] Linux version 5.x ...

$ dmesg -e                       # reltime: local time + delta per line
[Jan 1 10:15 +0.000123] Linux version 5.x ...
```

`-T`/`iso` convert monotonic boot time to wall clock using the *current* clock —
after suspend/resume or NTP corrections they are approximations, which the man
page says outright. `-d` adds per-line deltas; `-t` drops timestamps entirely.

### Levels and facilities

Every message has a severity (syslog numbering) and a facility. `-x` decodes
them inline; `-l` and `-f` filter on them:

```bash
$ dmesg -x | tail -1
kern  :info  : [ 1804.663665] kata-agent (163): drop_caches: 2

$ dmesg -l err,crit,alert,emerg          # only real problems
$ dmesg -f daemon -l warn,err            # facility AND level
$ dmesg -k | tail -3                     # -k: kernel facility only
$ dmesg -u                               # userspace messages (rare on Linux)
```

| Level | Name | Typical meaning |
| --- | --- | --- |
| 0-2 | emerg, alert, crit | system is dead / about to be |
| 3 | err | error condition |
| 4 | warning | recoverable problem |
| 5 | notice | normal but significant |
| 6 | info | informational (default console chatter) |
| 7 | debug | debug-level |

### Console behavior: the -n/-D/-E family

The kernel can *echo* messages to the physical console as they are printed.
Whether a message is echoed is decided by comparing its level against
`console_loglevel`: only messages **more severe** than the threshold appear.
`-n 1` silences almost all console spam (but everything still lands in the ring
buffer); `-n 8` echoes everything; `-D`/`-E` switch the echo off/on wholesale.
This is the same knob as `sysctl kernel.printk`, exposed as a command.

### Following the buffer

```bash
dmesg -w          # --follow: tail -f for the kernel
dmesg -w -l err   # only errors, live
dmesg -W          # --follow-new: print only messages arriving after start
```

`--follow` first prints the whole buffer, then streams; `--follow-new` skips the
history. This works thanks to `/dev/kmsg`'s readable record stream — a good
interview detail: the *file* is the API, `dmesg` is one of its clients.

### Access control

Unprivileged `dmesg` may be denied (`Operation not permitted`) when
`kernel.dmesg_restrict=1` — the man page documents exactly this failure. The
capability involved is `CAP_SYSLOG`. Debian traditionally allows unprivileged
dmesg; hardened setups and some containers restrict it, which surprises
people whose scripts read `dmesg` on customer machines.

```bash
sysctl kernel.dmesg_restrict      # 0 = anyone may read, 1 = privileged only
```

## Options That Matter

| Option | Effect |
| --- | --- |
| `-w`, `--follow` | Keep printing new messages (tail -f for the kernel) |
| `-W`, `--follow-new` | Follow, but skip pre-existing messages |
| `-l <list>`, `-f <list>` | Filter by levels / facilities (e.g. `-l err,warn`, `-f daemon`) |
| `-x`, `--decode` | Prefix each line with readable `facility:level:` |
| `-T` / `-e` / `-d` / `-t` | Human timestamps / reltime+delta / per-line delta / no timestamps |
| `--time-format <fmt>` | `delta`, `reltime`, `ctime`, `notime`, `iso`, `raw` |
| `--since` / `--until` | Time-window filtering |
| `-C` / `-c` | Clear buffer / print then clear |
| `-D` / `-E` / `-n <lvl>` | Console echo off / on / set console log level |
| `-k` / `-u` | Only kernel / only userspace messages |
| `-S` / `-s <size>` | Force syslog(2) path / set its buffer size |
| `-F <file>` / `-K <file>` | Read a text log / a kmsg-format dump instead of the kernel |
| `-r`, `--raw` | Raw buffer contents, no decoding |
| `-p`, `--force-prefix` | Repeat timestamp/facility on every line of multi-line messages |
| `-H`, `--human` | Human mode: pager-friendly, relative times, level coloring |
| `-J`, `--json` | JSON output for tooling |

## Usage Patterns

```bash
# First look at a misbehaving machine: what is the kernel complaining about?
dmesg -l err,warn | tail -30
```

```bash
# Live debugging while replugging a USB device
sudo dmesg -w
```

```bash
# Did the OOM killer fire? (classic incident question)
dmesg -T | grep -i -E 'out of memory|oom-killer|killed process'
```

```bash
# Extract messages since this morning in wall-clock terms
dmesg -T --since "2025-06-01 08:00:00" | less
```

```bash
# Decode facility/level for a bug report
dmesg -x -T | tail -50
```

```bash
# Silence console spam without losing the log (run from boot scripts)
sudo dmesg -n 1
```

```bash
# Read a captured buffer from a crashed machine (serial console capture)
dmesg -F /var/capture/kern.log -x | less
```

```bash
# Clear the buffer before reproducing a problem, then read just the fresh part
sudo dmesg -C; # ... reproduce ...; dmesg -T | less
```

```bash
# Machine-readable output for a monitoring script
dmesg --json | jq .                 # inspect the JSON structure once, then filter
```

```bash
# Compare with the persisted view under systemd
journalctl -k -b --no-pager | tail -30
```

## Nuances and Gotchas

- **The buffer is circular.** Old messages vanish when new ones arrive; a
  problem noticed hours later may already be gone. For anything you must not
  lose, journal/syslog is the archive, `dmesg` is the live window.
- **`-T` lies after suspend/resume.** Wall-clock conversion uses the current
  clock; the man page itself flags ctime/iso as potentially inaccurate. For
  forensics prefer `--time-format iso` on a freshly booted machine — or better,
  the journal's own timestamps.
- **Permission denied is a feature.** `kernel.dmesg_restrict=1` (or missing
  `CAP_SYSLOG` in a container) yields EPERM; scripts should test readability
  rather than assume.
- **`-C` is irreversible.** There is no undo for clearing the ring buffer; if
  the journal is not capturing kernel messages, the evidence is gone.
- **Console level vs buffer.** `dmesg -n 1` changes only what is *echoed to the
  console*; the buffer still gets everything. People who "lost messages" after
  `-n 1` did not lose them — they are in the buffer (unless rotated out).
- **`-w` without /dev/kmsg degrades.** On exotic systems lacking `/dev/kmsg`,
  following falls back to polling via syslog(2); timestamps and facility
  decoding may be coarser. The `-S` flag documents the divide.
- **Userspace messages are rare but real.** Programs can write to `/dev/kmsg`;
  `-u` shows them, `-k` hides them. Tools like `tuned`/boot tooling occasionally
  leave markers there.
- **Container caveat.** In many containers there is no `/dev/kmsg` and the
  sysctl is namespaced or hidden; `dmesg` can be empty or fail entirely even
  though the host kernel is chatty.

## Exit Status

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Failure — typically `EPERM` from `dmesg_restrict` (see syslog(2)), bad options, or I/O error |

## Related Commands

- [`overview`](./overview.md) — index of all util-linux collection pages
- [systemd](../../admin/systemd.md) — journalctl -k as the persistent, searchable view of the same messages
- [process-management](../../admin/process-management.md) — the OOM killer events dmesg is most often asked about
- [internals](../../internals.md) — where printk, the log buffer and console levels live

## Interview Questions

### Q: Where do kernel messages live and what does dmesg read from?

The kernel appends every printk to a fixed-size circular buffer in kernel
memory (sized by `log_buf_len`/config, wraps and overwrites the oldest). Modern
dmesg reads the `/dev/kmsg` record stream; the legacy path is the
`syslog(2)`/`klogctl(3)` interface (`-S`). systemd's journald and syslog
daemons consume the same data and persist it; `dmesg` itself is a live window
that is wiped at reboot.

### Q: Why are dmesg timestamps in seconds-since-boot, and when is -T dangerous?

The early kernel cannot trust the wall clock (it is set later by userspace), so
printk stamps messages with monotonic boot time. `-T`/`iso` convert using the
*current* system clock, which breaks after suspend/resume or clock jumps — the
man page explicitly warns about this. Use default timestamps for boot-phase
analysis and the journal for wall-clock forensics.

### Q: A user reports "dmesg: read kernel buffer failed: Operation not permitted". Explain.

`kernel.dmesg_restrict=1` (or container capability stripping) denies unprivileged
reads; the fix is running under a user with `CAP_SYSLOG` (root) or relaxing the
sysctl. This is a deliberate hardening feature documented in dmesg(1)'s exit
status discussion — and a common reason scripts break on hardened hosts.

### Q: How do you make the kernel quieter on the console without losing logs?

The console echo threshold is `console_loglevel`: `dmesg -n 1` (or
`kernel.printk`) lets only emergency-class messages through to the console,
while the ring buffer and journal continue to receive everything. `-D` disables
echoing entirely and `-E` re-enables. The distinction between echo level and
buffer contents is the point of the question.

### Q: How would you investigate a suspected OOM kill with dmesg?

Run `dmesg -T | grep -iE 'oom|out of memory|killed process'` to find the killer
report: the kernel logs the victim's pid/uid, total-vm/rss and a memory-state
dump, which tells you whether memory pressure or a cgroup limit triggered it,
and which process died. Follow with `-w` if the pattern is recurring, and
cross-check the persistent copy via `journalctl -k` since the ring buffer will
eventually rotate the evidence away.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/dmesg.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
