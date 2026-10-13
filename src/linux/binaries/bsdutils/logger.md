# logger — emit syslog/journald entries from the shell

## Overview

`logger` writes a message into the system logging infrastructure. It is the shell-script author's front door to syslog: instead of opening `syslog(3)` from C, a script calls `logger -t myjob -p daemon.notice "backup finished"` and the message lands wherever the system logger sends it — journald, rsyslog, a central log host, or all three. It ships in the `bsdutils` package at `/usr/bin/logger` (upstream it is util-linux; the BSD name reflects its 4.3BSD origins).

You reach for `logger` whenever a non-interactive process needs to leave an auditable trace: cron jobs, systemd units, postinst scripts, network ifup hooks. It is often confused with `journalctl` (which *reads* the journal, never writes), `dmesg` (kernel ring buffer), and `systemd-cat` (systemd's alternative writer, which speaks the journal's native socket protocol rather than syslog). Inside the `logger` ecosystem the common confusion is protocol: the local `/dev/log` path and the remote `-n server` path use different default formats (see RFC 3164 vs RFC 5424 below).

| Field | Value |
| --- | --- |
| Package | bsdutils (Debian bookworm) |
| Man section | 1 |
| Path | /usr/bin/logger |
| First appeared | UC Berkeley, 1983 (4.3BSD era) |
| Standards | IEEE Std 1003.2 (POSIX.2); RFC 3164 / RFC 5424 for remote modes |

## Synopsis

```
logger [options] [message]
```

Common one-line forms:

```
logger "disk usage 91%"              # default: facility user, level notice
logger -p local0.warning -t webjob   # tagged, custom facility.level
logger -f /var/run/report            # log the contents of a file
some_cmd 2>&1 | logger -t somecmd    # stdin mode: each line = one message
logger -n loghost --rfc5424 "test"   # send to a remote syslog server
```

## How It Works

### Where the message actually goes

With no `-n`/`-u` options, `logger` writes the message as a datagram to the Unix socket `/dev/log`, which is owned by whatever provides the system log: `systemd-journald` on stock Debian, or `rsyslogd`/`syslog-ng` when installed. One datagram per line. The logger never rewrites the message content; everything downstream (facilities, filtering, storage) is the receiver's job.

```
shell script ──► logger ──► /dev/log (AF_UNIX DGRAM)
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
       systemd-journald                      rsyslogd
       (journal, /run/log)                   (files, /var/log/syslog,
            │                                 remote forwarding)
            ▼
       journalctl(1)
```

With `-n server`, `logger` switches to network syslog — UDP port 514 by default, TCP (`-T`, port 601 or `syslog-conn`) when forced — and, importantly, changes the default wire format to RFC 5424 (since util-linux 2.26). With `-u socket` you can point it at any other datagram socket.

### Failure behavior is quiet by design

If nothing is listening on `/dev/log`, recent `logger` still exits 0 — matching the historical `openlog(3)` behavior of not reporting lost messages. This is deliberate (so boot-time scripts don't fail before syslog is up) and regularly surprises people:

```bash
$ logger -t demo "hello book"      # no syslog daemon in this container
$ echo $?                          # exits 0, message silently dropped
0
$ logger --socket-errors=on -t demo "forced errors"
logger: socket /dev/log: No such file or directory
$ echo $?
1
```

`--socket-errors=auto` (the default) enables error reporting only when it detects systemd as PID 1. Use `on` in test harnesses, `off` when you want the silent behavior guaranteed.

### Priority: facility × 8 + level

`-p` accepts either a `facility.level` pair or a bare decimal. The numeric priority is `facility × 8 + level`, which is why RFC captures start with angle-bracket numbers:

| Level | # | Facility | # |
| --- | --- | --- | --- |
| emerg | 0 | kern | 0 |
| alert | 1 | user | 1 |
| crit | 2 | mail | 2 |
| err | 3 | daemon | 3 |
| warning | 4 | auth | 4 |
| notice | 5 | syslog | 5 |
| info | 6 | lpr, news, uucp, cron | 6–9 |
| debug | 7 | authpriv, ftp | 10, 11 |
| | | local0 … local7 | 16 … 23 |

So `user.notice` = 1×8+5 = `<13>`, and `local3.info` = 19×8+6 = `<158>`:

```bash
$ logger -n 127.0.0.1 -P 1514 --udp -p local3.info -t cronjob "nightly done"
# datagram received:
<158>1 2026-10-09T16:38:00.553875+00:00 ws1 cronjob - - [timeQuality tzKnown="1" isSynced="0"] nightly done
```

Two decode rules worth memorizing: `kern` cannot be generated from userspace — `logger -p kern.err` is silently logged as `user.err` — and the deprecated level synonyms `warn`, `error`, `panic` map to `warning`, `err`, `emerg`. The default priority is `user.notice` (`<13>`); the default tag is the username.

### RFC 5424 vs RFC 3164 on the wire

The two real datagrams below were captured by a UDP listener (`logger -n 127.0.0.1 -P 1514 --udp`, once with `--rfc3164`):

```
# RFC 5424 (default for -n remote):  PRI VERSION TIMESTAMP HOST APP PROCID MSGID SD MSG
<13>1 2026-10-09T16:37:45.449499+00:00 ws1 demo - - [timeQuality tzKnown="1" isSynced="0"] udp rfc5424 default

# RFC 3164 (--rfc3164, the "BSD syslog protocol"):  PRI TIMESTAMP HOST TAG: MSG
<13>Oct  9 16:37:45 ws1 demo: udp bsd style
```

RFC 5424 gives you an ISO-8601 timestamp with microseconds and timezone, an explicit version field, a structured-data block, and room for message IDs. RFC 3164 is the old BSD format that countless legacy collectors still expect; its 1 KiB size cap is what `logger` enforces by default (`-S` raises it). The `--rfc5424=notime,nohost` form minimizes the header for privacy or deduplication:

```
<13>1 - - demo - - - minimized header
```

### Structured data (RFC 5424 SD elements)

`--sd-id` opens a named element and `--sd-param` adds `name="value"` pairs to the element declared before it; `--msgid` fills the MSGID field. All three are silently ignored unless `--rfc5424` is in effect:

```bash
$ logger -n loghost -P 514 --rfc5424 --msgid BACKUP \
    --sd-id audit@32473 --sd-param job='"backup"' \
    -t demo "structured"
# on the wire (captured by a UDP listener on the receiving host):
<13>1 2026-10-09T16:37:53.806489+00:00 ws1 demo - BACKUP [timeQuality tzKnown="1" isSynced="0"][audit@32473 job="backup"] structured
```

User-defined element IDs (anything not `timeQuality`, `origin`, `meta`) must carry an `@digits` enterprise suffix. The quotation marks around parameter values are part of the protocol, hence the escaped quoting.

### stdin mode and --prio-prefix

Without a message argument and without `-f`, `logger` logs standard input, one line per message. `--prio-prefix` lets each input line carry its own `<N>` priority prefix; a bare number in angle brackets is interpreted as `facility×8+level`:

```bash
$ printf '<134>line-with-prefix\nplain-line\n' | logger -n 127.0.0.1 -P 1515 --udp --prio-prefix -t preftest
# both datagrams arrived as <134> — the prefix from the first line stuck
# for the prefix-less second line (observed with util-linux 2.41; the man
# page says the -p default applies, so do not rely on this)
```

`--prio-prefix` never affects a message passed as a command-line argument, and `-f file` cannot be combined with a message argument.

### --journald: native journal fields

`--journald` bypasses syslog emulation and submits structured journald fields, one `FIELD=value` pair per line, read from stdin or `--journald=file`:

```bash
$ logger --journald <<end
MESSAGE_ID=67feb6ffbaf24c5cbec13c008dd72309
MESSAGE=The dogs bark, but the caravan goes on.
DOGS=bark
CARAVAN=goes on
end
$ journalctl DOGS=bark --output json-pretty   # all fields visible
```

In this mode all other options are ignored — `-p` and `-t` do nothing. Priority must be passed as a numeric `PRIORITY` field in the input, and repeating `MESSAGE=` appends lines to the message body (for other fields, repetition creates an array).

## Options That Matter

| Option | Effect |
| --- | --- |
| `-p, --priority PRIO` | `facility.level` or decimal; default `user.notice` |
| `-t, --tag TAG` | APP-NAME/tag field; default is the username |
| `-i` / `--id[=ID]` | log logger's PID / the given ID (recommended: `--id=$$`) |
| `-f, --file FILE` | log every line of FILE (mutually exclusive with a message) |
| `-e, --skip-empty` | drop empty lines in `-f`/stdin mode |
| `-s, --stderr` | also echo the message to stderr |
| `-S, --size SIZE` | max message size; default 1 KiB (RFC 3164 legacy) |
| `-n, --server HOST` | send to a remote syslog server; RFC 5424 becomes the default |
| `-P, --port PORT` | remote port (UDP default 514, TCP 601/syslog-conn) |
| `-T, --tcp` / `-d, --udp` | force stream or datagram transport |
| `--octet-count` | RFC 6587 octet-count framing (for TCP receivers that need it) |
| `-u, --socket SOCK` | write to this Unix socket instead of `/dev/log` |
| `--rfc3164` / `--rfc5424[=SNIP]` | choose wire protocol; SNIP = notime, notq, nohost |
| `--sd-id` / `--sd-param` / `--msgid` | RFC 5424 structured data and MSGID (need `--rfc5424`) |
| `--prio-prefix` | honor a per-line `<N>` priority on stdin/file input |
| `--journald[=FILE]` | native journald fields mode; other options ignored |
| `--no-act` | do everything except delivering the message (dry run) |
| `--socket-errors on/off/auto` | surface Unix-socket delivery failures |

### Exit-status-relevant behavior groups

Delivery semantics differ per target: the `/dev/log` path can silently drop (unless `--socket-errors=on`); the `-n` remote path reports connection errors; `--journald` fails hard on malformed field lines.

## Usage Patterns

```bash
# Standard cron-job idiom: tag identifies the job, level carries severity
logger -t nightly-backup -p daemon.notice "backup started"
```

```bash
# Correlate several messages from one script run with the script's PID
logger --id=$$ -t deploy -p daemon.info "step 1: pulling images"
```

```bash
# Capture a command's output into syslog, line by line
rsync -a /data/ /mnt/nas/ 2>&1 | logger -t rsync-nas
```

```bash
# Log a file but skip the blank padding lines
logger -f /var/run/upgrade-report.txt -e -t upgrader
```

```bash
# Dry-run a complex invocation and see exactly what would be logged
logger --no-act -s --rfc5424 --sd-id x@42 --sd-param k='"v"' "msg"
```

```bash
# Verify a remote collector end-to-end (firewall, port, template parsing)
logger -n logs.example.com -P 514 --udp --rfc5424 -t connectivity "ping $(hostname)"
```

```bash
# Legacy collector that only speaks BSD syslog over TCP with octet counting
logger -n oldloghost -T -P 514 --octet-count --rfc3164 -t legacy "still alive"
```

```bash
# Structured journald entry that journalctl can find by ID
logger --journald <<end
MESSAGE_ID=9d1a4c1e2f7e4e9a8d3c0b6a5f4e3d2c
MESSAGE=Cache flush completed
PRIORITY=6
OBJECT=memcache
end
```

```bash
# Per-line priorities from a pipeline (134 = local0.info)
awk '{ if ($1 == "FAIL") print "<131>" $0; else print "<134>" $0 }' scan.txt \
  | logger --prio-prefix -t scanner
```

```bash
# Long messages: raise the cap and let the receiver decide
logger --size 8KiB -t dbdump "$(cat /tmp/dump-summary.json)"
```

```bash
# Emit to stderr too, so a cron mail-out and syslog both show it
logger -s -p daemon.warning -t watchdog "disk 95% full"   # also on stderr
```

```bash
# Test what a bogus priority does before shipping the script
logger -p 999 "x"      # -> logger: unknown priority name: 999 (exit 1)
```

## Nuances and Gotchas

- **Silent drops are the default.** With no listener on `/dev/log`, `logger` exits 0 and the message is gone (verified: exit 0 with no `/dev/log`; the error only surfaced when `-s` was used). In test contexts pass `--socket-errors=on`, or wrap critical logging in `[ -S /dev/log ]` checks.
- **`-d` is "UDP only", not "structured data".** Structured data is `--sd-id`/`--sd-param`. `-d` conflicts conceptually with `-D` in some other tools; double-check before scripting.
- **`kern` facility is a lie from userspace.** `logger -p kern.err` is re-tagged `user.err`. Programs that genuinely need kernel-originated messages use `/dev/kmsg` (`dmesg`), not syslog.
- **Two defaults hinge on `-n`.** Locally the payload is a raw datagram whose format the receiver defines; remotely, RFC 5424 is the default since util-linux 2.26 while `--rfc3164` must be requested. A script tested against journald may look fine and parse badly on a legacy collector.
- **`--prio-prefix` stickiness.** In the capture above, a prefix-less line after a `<134>` line was sent as `<134>` again, not as the `-p` default. Treat per-line priority as "sticky from the last prefix seen" unless you emit a prefix on every line.
- **`--journald` ignores `-p`, `-t`, `--rfc*`.** If your journald entry shows the wrong severity or tag, fix the `PRIORITY`/`SYSLOG_IDENTIFIER` fields in the input, not the command line.
- **Message size caps.** 1 KiB default (`-S` to change); receivers commonly truncate 4 KiB+ silently. Multiline command output becomes *many* syslog messages — one per line — which can flood a collector; pre-join with `tr '\n' ' '` when one entry is wanted.
- **Quoting and leading dashes.** A message starting with `-` needs `--`: `logger -- "-weird tag content"`. Tags and messages pass through whatever quoting the shell does; `logger` itself does no expansion.
- **Portability.** BusyBox `logger` supports a small subset (no `--rfc5424`, no `--journald`); BSD `logger` lacks the journald and SD options by definition. Scripts that must run on appliances should stick to `-p`, `-t`, `-f`, `-s`.
- **`--id` and socket credentials.** journald may overwrite the logged PID with the *real* sender PID from socket credentials; `--id` only sticks when run by root and the PID exists.

## Exit Status

| Status | Meaning |
| --- | --- |
| 0 | Message accepted for delivery (note: local socket drops may still be silent) |
| >0 | Error: unknown priority name, unreadable `-f` file, failed remote/journal connection (verified: `logger -p 999` → 1) |

`logger(1)` documents only "exits 0 on success, and >0 if an error occurs"; the observed errors exit 1.

## Related Commands

- [`./overview.md`](./overview.md) — the bsdutils collection hub and packaging rationale.
- [`./script.md`](./script.md) — the other "leave a trace" tool: records sessions instead of syslog lines.
- [`../util-linux/dmesg.md`](../util-linux/dmesg.md) — kernel ring buffer, the one log `logger` cannot feed.
- [`../../admin/systemd.md`](../../admin/systemd.md) — journald architecture: where `--journald` entries land and how to query them.
- [`../../reference/commands.md`](../../reference/commands.md) — quick command reference including the logging one-liners.

## Interview Questions

### Q: What does `-p local0.info` compile to on the wire, and why?

Facility `local0` is 16 and level `info` is 6, so the PRI value is 16×8+6 = 134 and RFC 5424/3164 frames start with `<134>`. The PRI field is a single integer that packs both dimensions; parsers split it back with `/8` and `%8`. Being able to do this conversion on a whiteboard is the standard "do you actually know syslog" check.

### Q: A cron script calls `logger` and you find nothing in the logs, yet the script exits 0. What happened and how do you debug it?

Most likely nothing is listening on `/dev/log` (journald crashed, or the job runs in a container/namespace without it) and `logger`'s default `--socket-errors=auto` treated the drop as success. Re-run the failing step with `logger --socket-errors=on -s` to force error reporting and mirror the payload on stderr; also check whether the job's tag is being filtered out by a receiver-side rule.

### Q: When would you choose `logger --journald` over plain `logger`?

When you need first-class journal fields rather than a flattened syslog line: `MESSAGE_ID` for catalog-style queries, custom fields like `OBJECT=` searchable via `journalctl OBJECT=memcache`, and multi-line messages without splitting into one syslog message per line. The cost is lock-in to systemd and losing every other `logger` option, since `--journald` ignores them.

### Q: Explain the difference between RFC 3164 and RFC 5424 as it affects a `logger` deployment.

RFC 3164 is the BSD-era format: PRI, a coarse `Oct 9 16:37:45` timestamp without year or timezone, and a `tag:` prefix — plus the 1 KiB cap `logger` still defaults to. RFC 5424 adds a version field, ISO-8601 timestamps with microseconds and timezone, MSGID, and structured-data elements, and relaxes the size limit. `logger` uses 5424 by default only for remote (`-n`) transport since util-linux 2.26; local `/dev/log` delivery is receiver-defined, so a collector that expects 3164 needs `--rfc3164` explicitly.

### Q: Why can a script log as `local7.debug` but not as `kern.debug`?

The kernel facility is reserved for kernel-originated messages; from userspace, `logger` transparently converts `kern` to `user`. The syslog receiver trusts the transport: `/dev/log` credentials can only come from a process, and only the kernel writes to `/dev/kmsg`. Design your scheme around `local0`–`local7` for application categories.

### Q: What does `--octet-count` change?

Framing on TCP. Without it, `logger` uses RFC 6587 *non-transparent* framing (octet stuffing with a trailing newline); with it, each message is prefixed with its length, e.g. `<13>7 message`, which unambiguous framing requires when messages contain newlines. UDP needs no framing at all — one datagram, one message — which is why the option matters only for `-T` remote delivery.

## References

- [Man page(1) — manpages.debian.org](https://manpages.debian.org/bookworm/bsdutils/logger.1.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/bsdutils/)
