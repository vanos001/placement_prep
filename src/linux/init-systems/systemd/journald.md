# journald — Architecture, journalctl, and Structured Logging

## Overview

`systemd-journald` is a system-wide logging daemon that collects messages
from every available source — the kernel, classic syslog sockets, its own
native library API, the stdout/stderr of every service, and the audit
subsystem — and stores them in a single indexed, structured, binary journal.
Where syslog daemons parse free-form text lines and file them by facility,
journald stores each entry as a set of key=value *fields*: the message
itself plus automatically generated metadata (process, unit, boot, IDs),
which makes the journal queryable like a database instead of greppable like
a file. `journalctl(1)` is the query front end; no other tool should ever
read the journal files directly.

The daemon is intentionally *not* a syslog replacement in the forwarding
sense: it is the local collection and indexing layer. It can forward
messages to a classic syslog daemon (`ForwardToSyslog=`), to the kernel
buffer, to the console, or as wall messages, and in the other direction
rsyslog can either receive those forwarded messages on a socket or pull
entries itself with `imjournal`. This coexistence is why a Debian system
with rsyslog still has both `/var/log/syslog` (text files, written by
rsyslog) and `/var/log/journal/` (binary journal) — two views of the same
stream, and knowing which tool owns which file is a perennial interview
question.

This page covers the daemon's data model and storage, the trusted-field
naming rules, `journalctl` as a query language, coredump collection, and
the gotchas that bite in production (rate limiting, disk exhaustion,
containers). For the operator's-eye view and quick recipes, see
[admin/journald.md](../../admin/journald.md); for the C/python APIs
(`sd_journal_*`), see [apis-development](./apis-development.md).

## Sources and Pipeline

journald listens on several sockets simultaneously and tags each entry with
its transport (`_TRANSPORT` field):

| Source | Socket / path | `_TRANSPORT=` |
|---|---|---|
| Kernel messages | `/dev/kmsg` (`ReadKMsg=`, on by default in the default namespace) | `kernel` |
| Classic syslog clients | `/run/systemd/journal/dev-log` (journald binds `/dev/log`'s role) | `syslog` |
| Native API (`sd_journal_print`/`sd_journal_send`) | `/run/systemd/journal/socket` (datagram) | `journal` |
| Service stdout/stderr | per-service stream sockets connected by the manager | `stdout` |
| Kernel audit | `systemd-journald-audit.socket` (netlink AUDIT) | `audit` |

The stdout/stderr path deserves detail because it is invisible: every
service's standard streams are connected by the manager to a stream socket
into journald (unless a unit overrides `StandardOutput=`/`StandardError=` to
`journal+console`, `null`, a file, or `socket`). Stream data is split into
records at newline and NUL bytes; a line longer than `LineMax=` (default
48K) is force-split into multiple records. This is why a chatty daemon that
prints binary garbage or huge lines still produces bounded journal entries,
and why `LineMax=` exists as a tunable in `journald.conf`.

```text
 kernel ──/dev/kmsg──┐
 audit  ──netlink────┤
 syslog ──/dev/log───┼──► systemd-journald ──► indexed journal files
 native ──dgram sock─┤         │  ▲
 stdio  ──stream─────┘         ▼  │
                          forwarders  rate limiter
                        (syslog/kmsg/console/wall)
```

Forwarding is optional and independent of storing: `ForwardToSyslog=`
writes to the `/run/systemd/journal/syslog` socket that rsyslog's `imuxsock`
reads; `ForwardToKMsg=` injects back into `/dev/kmsg`; `ForwardToConsole=`
echoes to a console; `ForwardToWall=` sends wall broadcasts to logged-in
users. Defaults have shifted across releases (upstream's current man page
describes wall as the only default-on forward; Debian builds have
historically kept syslog forwarding enabled so rsyslog works out of the
box) — the reliable way to know is to read `journald.conf(5)` *for your
release* and check `journalctl -o short -u systemd-journald` at boot.

## Entry Model and Field Naming

An entry is a set of `FIELD=value` pairs. Three naming classes determine who
wrote the field and how much you can trust it:

- **`_`-prefixed fields are trusted.** journald generates them itself from
  kernel credentials and its own knowledge; a client *cannot* spoof them.
  This is the security property that makes queries like `_UID=0` or
  `_SYSTEMD_UNIT=nginx.service` reliable evidence.
- **All-uppercase fields (no underscore) are well-known fields that are
  "safe" to forward** to other journal implementations — `MESSAGE`,
  `PRIORITY`, `SYSLOG_IDENTIFIER`, `SYSLOG_PID`, and so on. Clients set
  them; journald may normalize them.
- **Anything else is client-supplied arbitrary metadata** (lowercase or
  mixed case), free-form custom fields like `REQUEST_ID=abc123`.

Fields with two leading underscores (`__CURSOR`, `__REALTIME_TIMESTAMP`,
`__MONOTONIC_TIMESTAMP`) are added by journald at ingestion, immutable, and
excluded from matching in some tool paths.

Core fields worth memorizing:

| Field | Meaning |
|---|---|
| `MESSAGE` | The human-readable text |
| `PRIORITY` | 0–7: emerg, alert, crit, err, warning, notice, info, debug |
| `SYSLOG_FACILITY` | Classic syslog facility number (kern, daemon, mail, …) |
| `SYSLOG_IDENTIFIER` | Sender tag (syslog "tag"; defaults to `_COMM` for native loggers that skip it) |
| `SYSLOG_PID` | Client-supplied PID (untrusted counterpart of `_PID`) |
| `_PID`, `_UID`, `_GID` | Trusted process credentials at send time |
| `_COMM`, `_EXE`, `_CMDLINE` | Trusted process name, binary path, full command line |
| `_SYSTEMD_UNIT`, `_SYSTEMD_USER_UNIT` | Unit that produced the entry |
| `_SYSTEMD_SLICE`, `_SYSTEMD_INVOCATION_ID` | Slice and per-run invocation ID |
| `_BOOT_ID`, `_MACHINE_ID`, `_HOSTNAME` | Boot, machine, host identity |
| `_TRANSPORT` | `stdout`, `syslog`, `kernel`, `journal`, `audit` |
| `_SOURCE_REALTIME_TIMESTAMP` | Client-claimed timestamp; `__REALTIME_TIMESTAMP` is the ingestion truth |
| `__MONOTONIC_TIMESTAMP` | Monotonic clock at ingestion (pairs with `_BOOT_ID`) |

The trusted/untrusted split has a direct query consequence: filtering on
`_PID=` answers "which process *actually* logged this" while `SYSLOG_PID=`
answers "what the process claimed". In incident forensics only `_`-fields
are evidence; the same logic underlies why log-forwarding pipelines should
preserve them.

## Storage: Volatile vs Persistent, Rotation, Vacuuming

`Storage=` in `journald.conf` selects among `volatile` (only
`/run/log/journal`, tmpfs), `persistent` (`/var/log/journal`, falling back
to `/run` during early boot), `none` (forwarding only), and the default
`auto`: persistent *if* `/var/log/journal` exists, volatile otherwise. The
directory's existence is the switch — distributions ship it pre-created, and
`mkdir /var/log/journal && systemctl restart systemd-journald` (or better,
`systemctl force-reload`/reboot so `systemd-tmpfiles-setup` applies
permissions) migrates a machine to persistent logging. Under `auto`, boot
entries land in `/run` first and are flushed to `/var` once it is mounted
writable — that flush is what `journalctl --flush` forces manually.

The journal is stored as a set of files per machine and boot:
`system.journal` (active) plus archived `@<hex-id>.journal` files.
**journald manages its own rotation and deletion — never put journal files
in logrotate(8).** Rotation and vacuuming are governed by `journald.conf`:

| Option | Default | Meaning |
|---|---|---|
| `SystemMaxUse=` | 10% of the filesystem | Cap on total persistent journal size |
| `SystemKeepFree=` | 15% of the filesystem | Leave this much free regardless of `SystemMaxUse=` |
| `SystemMaxFileSize=` | 1/8 of `SystemMaxUse=`, capped at 128M | Size at which a journal file rotates (so ~7 archives coexist) |
| `SystemMaxFiles=` | 100 | Maximum number of kept files |
| `MaxFileSec=` | 1 month | Time-based rotation of the active file |
| `MaxRetentionSec=` | 0 (off) | Delete archives older than this |
| `Compress=` | on | Compress objects > 512 bytes (XZ/LZ4/ZSTD per build) |
| `Seal=` | on (with keys) | Forward Secure Sealing if `journalctl --setup-keys` was run |

(`Runtime*` twins of the size options apply to `/run/log/journal`.) The two
bounds interact: the daemon targets `min(SystemMaxUse=, filesystem_free −
SystemKeepFree=)`, which is why a journal on a small `/var` shrinks itself
aggressively and why "the journal ate my disk" reports usually trace to a
misread of `SystemKeepFree=`. Manual intervention is rarely needed but
exists:

```bash
journalctl --disk-usage                 # total size of archived+active
journalctl --vacuum-size=500M           # shrink archives to 500M
journalctl --vacuum-time=2week          # drop archives older than 2 weeks
journalctl --vacuum-files=5             # keep at most 5 archive files
journalctl --rotate                     # force rotation now
```

Vacuuming only deletes *archived* files, never the active one — rotate
first if you need an immediate shrink. Do not logrotate these files; doing
so corrupts the index and races the daemon.

## Forwarding, Sealing, and Integrity

Beyond the four forwarders, two integrity features matter for compliance
stories. **Forward Secure Sealing (FSS)** makes tampering detectable even
for an attacker with the disk: `journalctl --setup-keys` generates a
sealing key plus verification keys (with `--interval=` controlling how much
history a leaked verification key covers); from then on entries are sealed
and `journalctl --verify` proves the archived files were not altered
retroactively. `Seal=` defaults to on *when keys exist*. `journalctl
--verify` also works without FSS to check file structure integrity — a
useful step after a crash or when a "journal file corrupted" message
appears.

The syslog coexistence question comes up in every interview about logging
architecture. Two integration modes exist: (1) journald *pushes* to
`/run/systemd/journal/syslog` and rsyslog reads it with `imuxsock` — low
overhead, but the flow loses journald's structured fields; (2) rsyslog
*pulls* structured entries with `imjournal` and maps fields itself — more
faithful, higher overhead (it re-reads journal files with a state file).
The same trade-off (transport fidelity vs processing cost) recurs in every
log pipeline design; journald's field model is what makes the faithful
option possible at all.

## journalctl: the Query Language

### Filtering

```bash
journalctl -b                          # this boot
journalctl -b -1                       # previous boot
journalctl --list-boots                # boot index, ID, first/last timestamp
journalctl -u nginx.service            # by unit (repeatable: -u a -u b)
journalctl _SYSTEMD_USER_UNIT=app.service   # user-manager units
journalctl -p err..warning             # priority range (names or 0..7)
journalctl -p 3                        # err and more severe
journalctl -t sshd                     # by SYSLOG_IDENTIFIER
journalctl -k                          # kernel messages (dmesg equivalent)
journalctl _PID=1234                   # trusted PID match
journalctl MESSAGE_ID=fc2e22bc6ee647b6b90729ab34a250b1   # specific event type
journalctl -S -1h                      # since one hour ago (--since)
journalctl -S "2024-01-01 12:00:00" -U "2024-01-02"      # explicit window
journalctl --since yesterday --until today
journalctl -f                          # follow new entries, like tail -F
journalctl --grep "oom|segfault"       # PCRE2 on MESSAGE (journalctl --grep)
```

Field matches combine with AND within one command; `MESSAGE_ID=` matching
is how catalogued, well-defined events (e.g. systemd's own
unit-failure/oom messages with documented IDs) are located precisely.
`--grep` requires a build with PCRE2 and applies to the message after other
filters, which keeps it fast.

### Output modes and field extraction

```bash
journalctl -o short                    # classic syslog-like (default)
journalctl -o short-iso-precise        # ISO timestamps with microseconds
journalctl -o short-monotonic          # monotonic time, pairs with -k
journalctl -o verbose                  # every field of every entry
journalctl -o json-pretty              # one JSON object per entry
journalctl -o export                   # export format for journal-importer
journalctl -o cat                      # MESSAGE only, no metadata
journalctl -F _SYSTEMD_UNIT            # list distinct values of a field
journalctl -N                          # list all field names present
```

Two timestamp subtleties cause endless confusion: the default `short` mode
prints *local* time in a locale-independent abbreviated form with no offset
shown, while `short-iso` includes the UTC offset (`+02:00`) — so scripts
comparing logs across timezones should use `-o short-iso`. And
`--since`/`--until` parse timestamps in the *local* timezone (append `UTC`
to pin). `--disk-usage`, `--rotate`, `--sync` (asks the daemon to flush
outstanding data — the programmatic equivalent of `SIGRTMIN+1`),
`--flush` (move `/run` entries to `/var`), `--header` (raw file header:
sizes, offsets, field counts) round out the maintenance verbs.

Machines beyond the local one: `journalctl --machine=.host` scopes
explicitly, `--machine=.container/<name>` or `--machine=.vm/<name>` reads a
registered container/VM's journal via `systemd-machined`, and `--root=`/
`--directory=`/`--file=` operate on mounted or copied journals — the
standard way to inspect a dead system's disk or a SupportConfig bundle.

## Coredumps: systemd-coredump and coredumpctl

With the `systemd-coredump` component (Debian package of the same name),
the kernel's `core_pattern` pipes crashing processes to
`systemd-coredump(8)`, which stores the core (compressed, size-capped) in
`/var/lib/systemd/coredump` and metadata as a journal entry with a
well-known `MESSAGE_ID`. The interactive `ulimit -c` ritual is irrelevant
for services: the manager applies `LimitCORE=` per unit and
`DefaultLimitCORE=` globally, and `coredump.conf(5)` governs storage
(`Storage=` — `none`, `journal` (metadata + tiny cores), `external`),
`ProcessSizeMax=`, `ExternalSizeMax=`, `JournalSizeMax=`, `MaxUse=`,
`KeepFree=`. Setting `ProcessSizeMax=0` (or `Storage=none`) disables
coring entirely.

```bash
coredumpctl list                       # all recorded crashes
coredumpctl list pidgin                # filter by program
coredumpctl info 12345                 # metadata + stack of one crash
coredumpctl dump -o /tmp/core          # extract the core file
coredumpctl gdb 12345                  # load core into gdb with symbols
```

`coredumpctl gdb` is the killer feature: it resolves the executable and
debug symbols automatically, turning "my service died with signal 11" into
a backtrace in one command. The crash metadata is a journal entry, so
`journalctl MESSAGE_ID=<coredump-id>` or `journalctl -t systemd-coredump`
correlates crashes with the surrounding log context of the same second.

## Logging from Programs and Scripts

C via the native API — one call for a plain message, one for structured
entries with arbitrary custom fields:

```c
#include <systemd/sd-journal.h>

sd_journal_print(LOG_INFO, "connection from %s", peer);          /* printf-style */

sd_journal_send("MESSAGE=upload failed for user %s", user,      /* structured */
                "PRIORITY=%d", LOG_ERR,
                "REQUEST_ID=%s", rid,
                "BYTES=%zu", n,
                NULL);
```

`sd_journal_send` entries appear in `journalctl -o verbose` with the custom
fields (`REQUEST_ID=`, `BYTES=`) queryable directly
(`journalctl REQUEST_ID=abc123`) — this is the "structured logging" pitch:
fields are first-class, not a parsed afterthought. Python has the same
power via `systemd.journal.send("msg", REQUEST_ID=rid, PRIORITY=4)`;
shell scripts get it from `systemd-cat`:

```bash
myjob 2>&1 | systemd-cat -t myjob -p info       # tag + default priority
echo "disk almost full" | systemd-cat -p warning -t diskmon
```

`MESSAGE_ID=` (a 128-bit random ID per *event type*) ties entries to the
message catalog so `journalctl` can render explanations; generating stable
IDs per event class (`systemd-id128 new`) is the recommended practice for
services that want machine-filterable events — see
[apis-development](./apis-development.md) for the full API treatment.

## Gotchas and Production Realities

**Rate limiting — the "Suppressed N messages" mystery.** journald applies
a per-service rate limit: with defaults, more than 10000 messages in 30s
and everything beyond the burst is dropped until the interval ends, with
one journal line summarizing the loss:

```text
systemd-journald[1]: Suppressed 8312 messages from nginx.service
```

That line is the answer to "why is the log full of gaps". The knobs are
`RateLimitIntervalSec=` and `RateLimitBurst=` in `journald.conf` (or
per-unit `LogRateLimitIntervalSec=`/`LogRateLimitBurst=` in
`systemd.exec(5)`). Chatty daemons under a debug flood hit this before
disk pressure is visible; raising the burst is often the wrong fix — fix
the log spam, or the limiter is doing exactly its job.

**Disk exhaustion behavior.** With `Storage=persistent` and a full
filesystem, the `SystemKeepFree=`/`RuntimeKeepFree=` bounds make journald
vacuum itself down — but a journal *already* at its floor plus an external
process filling `/var` pushes journald to drop or degrade; knowing
`journalctl --disk-usage` and the vacuum verbs (above) is the recovery
path. Conversely, a system booted with a missing/unwritable `/var/log/
journal` silently logs to `/run` and *loses everything on reboot* — the
"my logs are empty after reboot" classic; check `Storage=` and the
directory, and `journalctl --flush` after fixing.

**Containers.** A container usually runs its own journald or none at all;
entries collected on the host are attributed via the container's
machine-id, and nested journals from several machines merge in the host's
view — which is why the same timestamp can appear duplicated and why
`journalctl --machine=<name>` / `-b` scoping matters in multi-boot and
container-heavy hosts. A container image that wants its own persistent
journal must ship `/var/log/journal` *and* a unique `/etc/machine-id`
generated at first boot, or journald refuses persistent storage (identical
machine-ids across containers is the classic cause).

**High-volume audit transport.** With `audit=1` and verbose audit rules,
the `_TRANSPORT=audit` stream can dwarf everything else; filter it out
(`journalctl -p 3` or explicit field matches) rather than raising rate
limits globally.

**stdout of `Type=oneshot` scripts.** Stream-splitting at `LineMax=` means
a script printing a 100K JSON line produces two records; consumers should
log structured fields via `systemd-cat`/native API instead of giant single
lines.

## Interview Questions

### Q: What makes a journal field trusted, and why does the naming convention matter for security?

Fields whose names begin with `_` are generated by journald itself from
kernel-provided credentials (`_PID`, `_UID`, `_COMM`, `_EXE`,
`_SYSTEMD_UNIT`, `_BOOT_ID`); clients cannot set them, so a query on them
is evidence about the actual sender. Uppercase-only names (`MESSAGE`,
`SYSLOG_IDENTIFIER`) are well-known fields a client supplies, considered
safe to forward to other systems; everything else is arbitrary client
metadata. The convention lets you write queries like `_UID=0
_SYSTEMD_UNIT=sshd.service` that cannot be spoofed by the logging process,
which is the property plain-text syslog lacks (its tag and PID are
client-claimed).

### Q: Why must you not put /var/log/journal in logrotate, and what is the correct sizing mechanism?

Journal files are indexed binary files whose header records offsets,
object counts and checksums; truncating or moving them out from under the
daemon corrupts the index and loses data. journald rotates on its own
schedule (`SystemMaxFileSize=`, default 1/8 of `SystemMaxUse=` capped at
128M, `MaxFileSec=` default one month) and vacuums to
`min(SystemMaxUse=, free − SystemKeepFree=)`. Operational control is
`journalctl --disk-usage`, `--vacuum-size/-time/-files`, and the
`journald.conf` options — not logrotate; treat the journal like a database,
not a text log.

### Q: What exactly does Storage=auto do, and how do you migrate a volatile-only machine to persistent logging?

`auto` (the default) behaves like `persistent` if `/var/log/journal`
exists and like `volatile` otherwise — the directory is the switch.
Migration: `mkdir /var/log/journal`, restart journald (`systemctl restart
systemd-journald`; tmpfiles.d rules then set ownership/mode), and optionally
`journalctl --flush` to move the current `/run` boot entries into the new
persistent store. If the directory is absent at boot, early entries land in
`/run/log/journal` and are flushed to `/var` when it becomes writable —
which is also the failure mode when `/var` never mounts.

### Q: A service's logs show "Suppressed 8312 messages". What happened and what do you change?

journald's per-service rate limit (defaults: `RateLimitIntervalSec=30s`,
`RateLimitBurst=10000`) dropped everything beyond the burst within the
window and recorded the count. Options: fix the upstream spam (usually
correct), raise the per-unit `LogRateLimitIntervalSec=`/
`LogRateLimitBurst=` in the service, or raise the global pair in
`journald.conf`. Note the limit is per-service, so one noisy daemon does
not starve others — and that suppressing a debug flood is often the system
protecting itself, not a bug.

### Q: How do you get a backtrace from a service that died with SIGSEGV last night?

If systemd-coredump is installed, the crash was piped through
`core_pattern` and recorded: `coredumpctl list` shows the crash with
timestamp/PID/signal, `coredumpctl info` prints the journal metadata and
stack, and `coredumpctl gdb <pid-or-time>` loads the exact core with the
right executable and symbols. Size and retention are `coredump.conf(5)`
matters (`ProcessSizeMax=`, `MaxUse=`), not `ulimit -c` — services get
their `RLIMIT_CORE` from `LimitCORE=`/`DefaultLimitCORE=`, and the pipe
mechanism bypasses the old shell ritual entirely.

### Q: How does journald coexist with rsyslog — what are the two integration modes and their trade-offs?

Push mode: `ForwardToSyslog=` writes entries to
`/run/systemd/journal/syslog`, which rsyslog's `imuxsock` reads — cheap
and simple, but only the formatted text crosses, losing structured fields.
Pull mode: rsyslog's `imjournal` reads the journal files directly and maps
the structured fields (`_PID`, `_SYSTEMD_UNIT`, custom fields) into
rsyslog templates — faithful but with measurable overhead (polling,
state-file bookkeeping). Knowing both, and that `journalctl` and
`/var/log/syslog` are two views of one stream, is the expected answer.

## References

- https://www.freedesktop.org/software/systemd/man/latest/systemd-journald.service.html
- https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html
- https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- https://www.freedesktop.org/software/systemd/man/latest/sd-journal.html
- https://www.freedesktop.org/software/systemd/man/latest/systemd-coredump.html
- https://www.freedesktop.org/software/systemd/man/latest/coredumpctl.html
- https://manpages.debian.org/bookworm/systemd/systemd-journald.8.en.html
- https://manpages.debian.org/bookworm/systemd/journald.conf.5.en.html
- https://manpages.debian.org/bookworm/systemd/journalctl.1.en.html
- https://manpages.debian.org/bookworm/libsystemd-dev/sd-journal.3.en.html
- https://manpages.debian.org/bookworm/systemd-coredump/systemd-coredump.8.en.html
- https://manpages.debian.org/bookworm/systemd-coredump/coredumpctl.1.en.html
- http://0pointer.de/blog/projects/journalctl.html

## Cross-References

- [boot-process.md](./boot-process.md) — when journald starts relative to other units and why early boot logs are volatile.
- [service-units.md](./service-units.md) — `StandardOutput=`/`StandardError=` and per-unit log rate limits.
- [systemctl-cli.md](./systemctl-cli.md) — pairing `systemctl status` output with journal queries.
- [timers.md](./timers.md) — timers as the largest consumers of per-unit journal logging.
- [admin/journald.md](../../admin/journald.md) — operator recipes: disk cleanup, persistent setup, filtering.
- [admin/logging.md](../../admin/logging.md) — the wider logging landscape (rsyslog, syslog-ng) around the journal.
- [comparison.md](../comparison.md) — logging models across init systems.
