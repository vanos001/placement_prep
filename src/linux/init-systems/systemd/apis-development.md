# Programming Against systemd — sd_notify, sd-bus, sd-journal, Generators

## Overview

systemd is not just an init system you administer — it is a platform you
program against. The project ships a small, stable C library (`libsystemd`,
the `sd_*` API family) that lets a daemon declare readiness, receive sockets,
answer a software watchdog, write structured journal entries, and drive the
manager over D-Bus. Alongside the library sit two extension mechanisms that
need no code at all in the common case: the `org.freedesktop.systemd1`
D-Bus API (scriptable with `busctl`) and *generators* — small executables
that synthesize unit files at load time.

The unifying idea is *cooperation between daemon and supervisor*. SysVinit-era
daemons were black boxes: init guessed readiness from PID files and treated
silence as health. systemd's protocol makes the daemon a first-class
participant — it says "I am ready" (`READY=1`), "I am reloading"
(`RELOADING=1`), "still alive" (`WATCHDOG=1`), "keep these fds"
(`FDSTORE=1`) — and the manager turns each statement into unit state visible
in `systemctl`. This page is the developer's tour of those interfaces with
compilable snippets; the operational side of what they feed lives in
[service-units.md](./service-units.md),
[socket-activation.md](./socket-activation.md) and
[journald.md](./journald.md).

## The libsystemd Surface

All `sd_*` symbols live in one shared library with a stable ABI; headers are
under `/usr/include/systemd/`, and the pkg-config name is `libsystemd`:

```bash
cc -o myapp myapp.c $(pkg-config --cflags --libs libsystemd)
```

| Sub-API | Header | What it gives you | Flagship calls |
|---|---|---|---|
| sd-daemon | `sd-daemon.h` | Readiness, watchdog, fd passing/keeping | `sd_notify`, `sd_listen_fds`, `sd_booted` |
| sd-journal | `sd-journal.h` | Structured log writing + journal reading | `sd_journal_print`, `sd_journal_send`, `sd_journal_get_data` |
| sd-bus | `sd-bus.h` | D-Bus client/server (the bus systemd itself uses) | `sd_bus_call`, `sd_bus_match_signal` |
| sd-event | `sd-event.h` | epoll-based event loop: IO, timers, signals, children | `sd_event_default`, `sd_event_add_io`, `sd_event_loop` |
| sd-login | `sd-login.h` | Query logind state: sessions, seats, uids | `sd_session_is_active`, `sd_uid_get_sessions` |
| sd-id128 | `sd-id128.h` | 128-bit machine/app/invocation IDs | `sd_id128_get_machine` |
| sd-device | `sd-device.h` | Enumerate/inspect udev devices (modern libudev) | `sd_device_get_property_value` |

Two portability facts up front. First, `libsystemd` is Linux-only and
systemd-coupled, so portable software treats it as an *optional* dependency
(configure flag, or dlopen at runtime) and degrades gracefully — the guards
at the end of this page show the runtime checks. Second, the two wire
protocols underneath (`sd_notify` datagrams and the fd-passing environment
variables) are deliberately trivial and documented as stable interfaces, so
you can implement them in any language without the C library — the Python
snippet below proves it.

## sd_notify: The Readiness Protocol

### Transport

When a unit with `Type=notify` starts, the manager creates a Unix datagram
socket and passes its address in the environment variable `NOTIFY_SOCKET` —
either a filesystem path (`/run/systemd/notify`) or an *abstract namespace*
socket written with the `@` convention (`@/run/systemd/notify`, where the
`@` stands for the kernel's leading NUL byte). The daemon sends one datagram
of newline-separated `KEY=VALUE` fields; no reply, no framing. `NotifyAccess=`
controls who may send: `main` (default, the main PID only), `exec` (main plus
`Exec*` children), or `all` (any process in the unit's cgroup — required when
a wrapper script notifies from a subshell).

### Message fields

| Field | Meaning | Pairs with |
|---|---|---|
| `READY=1` | "Initialized and serving" — the unit enters `active` | `Type=notify` |
| `STATUS=...` | Free-form progress line shown verbatim in `systemctl status` | any time |
| `MAINPID=1234` | "This is my real main PID" — for daemons that fork after start | needs `NotifyAccess` allowing the sender |
| `WATCHDOG=1` | Watchdog ping — "alive" | `WatchdogSec=` |
| `STOPPING=1` | "Stop request received, shutting down" — unit enters `deactivating` | `Type=notify` |
| `RELOADING=1` | "Reload begun; state momentarily inconsistent" | `Type=notify-reload` (v253+) |
| `READY=1` (again) | "Reload finished" — paired after `RELOADING=1` | `Type=notify-reload` |
| `FDSTORE=1` | "Keep these fds for me" across restarts | `FileDescriptorStoreMax=` |
| `FDNAME=xyz` | Name for a stored fd, retrievable via socket activation | `FDSTORE=1` |
| `BARRIER=1` | Force ordering of previously sent datagrams | multi-message sequences |
| `ERRNO=13` | Numeric errno accompanying a failure report | failure paths |

### Pairing with Type=notify

`Type=notify` redefines "started": the start job completes not on fork or
`ExecStart` exit, but on the first `READY=1` datagram. This is the difference
between "the binary launched" and "the service works" — a database replaying
40 seconds of WAL holds its ordering edges for exactly those 40 seconds, so
dependents start only when the service is usable. The failure mode is
symmetric: a daemon that never sends `READY=1` holds its start job until
`TimeoutStartSec=` expires and the unit fails with `Result=timeout`.
`Type=notify-reload` extends the contract to reloads — `systemctl reload`
then waits for the post-`RELOADING=1` `READY=1`, so "reload finished" means
"new config is actually serving".

### The watchdog handshake

Set `WatchdogSec=10s` and the manager exports `WATCHDOG_USEC=10000000`; the
daemon must send `WATCHDOG=1` at least twice per interval (every ~5 s here),
typically from its event loop. A missed ping is not a polite restart: the
manager sends **SIGABRT** — deliberately, so a core dump is captured — and
`Restart=on-abort`/`on-watchdog` can react differently than to clean exits.
The rationale: a wedged mainloop cannot run signal handlers or cleanup code,
so the most useful recovery is an abort with post-mortem evidence
(`Result=watchdog` in `systemctl show`). The half-interval rule absorbs
scheduler jitter so one late ping is not fatal.

### A minimal pure-Python implementation

The protocol is small enough to implement without libsystemd — this is the
entire client:

```python
import os
import socket


def sd_notify(message: str) -> None:
    addr = os.getenv("NOTIFY_SOCKET")
    if not addr:
        return                      # not under systemd: clean no-op
    if addr.startswith("@"):
        addr = "\0" + addr[1:]      # abstract namespace socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.connect(addr)
    sock.send(message.encode())
```

Usage: `sd_notify("READY=1")` after initialization, `sd_notify("STATUS=45
percent done")` for progress, `sd_notify("WATCHDOG=1")` on a timer,
`sd_notify("STOPPING=1")` in a SIGTERM handler. The guard clause is the
portability discipline of the whole page: the same code runs under SysVinit,
runit, OpenRC, a container entrypoint or a developer shell, silently doing
nothing when `NOTIFY_SOCKET` is absent. For shell cases, `systemd-notify(1)`
sends the same datagram from a script (`systemd-notify --ready --status="Index
rebuilt"`); because the *script* then sends it, such units need
`NotifyAccess=all` — with the default `main` the datagram is silently
dropped.

## Socket Activation API Recap

Socket activation (full mechanics in
[socket-activation.md](./socket-activation.md)) hands the daemon already-bound
listening sockets as inherited file descriptors. The contract is two
environment variables: `LISTEN_FDS` (how many) and `LISTEN_PID` (which PID
they belong to — checked so a forked child cannot steal its parent's
sockets). Descriptors start at 3 (`SD_LISTEN_FDS_START`), in the order
defined by the matching `.socket` unit:

```c
#include <stdio.h>
#include <systemd/sd-daemon.h>

int main(void) {
    int n = sd_listen_fds(1);            /* 1: unset env vars after reading */
    if (n < 0) { perror("sd_listen_fds"); return 1; }
    for (int i = 0; i < n; i++) {
        int fd = SD_LISTEN_FDS_START + i;   /* == 3, 4, 5 ... */
        /* accept(2)/poll(2) on fd as if you had bound it yourself */
        printf("inherited listening fd %d\n", fd);
    }
    return 0;
}
```

The payoff: the manager bound the socket early (`sockets.target`), so the
daemon can start late without dropping a connection (kernel backlog queued
it), privileged ports need no capability in the daemon, and restarts are
zero-downtime when combined with `FDSTORE=1` — the daemon passes
connection fds back on stop and receives them again on start. `n == 0` means
"not socket-activated — bind your own", not failure; the `1` argument clears
the environment after reading so a later `exec` cannot re-inherit fds.

## The Journal API

### Writing structured entries

`sd_journal_print` is syslog-with-priorities; `sd_journal_send` is the
interesting one — arbitrary `FIELD=value` pairs become indexed, queryable
journal fields alongside the trusted fields (`_PID`, `_UID`, `_COMM`,
`_SYSTEMD_UNIT`, ...) the journal adds itself:

```c
#include <systemd/sd-journal.h>

sd_journal_print(LOG_INFO, "processed %d requests", n);

sd_journal_send("MESSAGE=cache warmed", "PRIORITY=6",
                "REQUESTS=%d", n, "APP=myapp", NULL);
```

Your fields become filter targets: `journalctl APP=myapp REQUESTS=...` — no
log-parsing regexes. Conventions worth honoring: `MESSAGE=` is the
human-readable line, `PRIORITY=` uses syslog numbers 0–7, custom fields are
upper-case and namespaced. The shell equivalent is `systemd-cat`
(`echo hi | systemd-cat -t myapp -p info`), which speaks the same protocol.

### Reading the journal natively

The read API is a cursor-based iterator over match lists:

```c
#include <stdio.h>
#include <systemd/sd-journal.h>

int main(void) {
    sd_journal *j;
    if (sd_journal_open(&j, SD_JOURNAL_LOCAL_ONLY) < 0) return 1;

    sd_journal_add_match(j, "_SYSTEMD_UNIT=nginx.service", 0);
    sd_journal_seek_tail(j);
    sd_journal_previous_skip(j, 10);        /* last 10 matching entries */

    while (sd_journal_next(j) > 0) {
        const char *d;
        size_t l;
        if (sd_journal_get_data(j, "MESSAGE", (const void **)&d, &l) == 0)
            printf("%.*s\n", (int)(l - 8), d + 8);   /* strip "MESSAGE=" */
    }
    sd_journal_close(j);
    return 0;
}
```

`add_match` narrows with AND across calls (OR via `add_disjunction`),
`seek_head`/`seek_tail` position the cursor, `next`/`previous` step, and
`sd_journal_wait(j, timeout)` blocks for new entries — that is how
`journalctl -f` is implemented. The lesson: do not scrape `/var/log/syslog`;
the native API gives typed, indexed access to the same data the CLI uses,
including on machines with no classic syslog files at all.

## sd-event: The Event Loop

`sd-event` is a thin wrapper around epoll: IO, timers, signals, child
processes and exit handlers in one priority-ordered loop. A minimal but
complete skeleton:

```c
#include <signal.h>
#include <systemd/sd-event.h>

static int on_io(sd_event_source *s, int fd, uint32_t revents, void *userdata) {
    return 0;   /* drain fd, do work; return non-zero to exit the loop */
}

int main(void) {
    sd_event *e = NULL;
    sd_event_default(&e);                               /* or sd_event_new() */
    sd_event_add_io(e, NULL, 0 /* your fd */, EPOLLIN, on_io, NULL);
    sd_event_add_signal(e, NULL, SIGTERM, NULL, NULL);  /* clean loop exit */
    sd_event_loop(e);
    sd_event_unref(e);
    return 0;
}
```

Why not roll your own epoll loop? Because the supervisor integration points —
watchdog pings, `RELOADING`/`STOPPING` handling, socket-activated fd arrival
— all want a slot in the same loop, and `sd-event`'s priority model encodes
"drain sockets before timer housekeeping" declaratively. It is also the loop
systemd's own daemons run. Projects with an existing loop (libuv, GLib,
asio) simply keep it and drive `sd_notify`/watchdog pings from a timer
callback — sd-event is a convenience, not a prerequisite.

## sd-bus and org.freedesktop.systemd1

Everything `systemctl` does is a D-Bus method call on the well-known name
`org.freedesktop.systemd1`, object path `/org/freedesktop/systemd1`,
interface `org.freedesktop.systemd1.Manager`. The methods you will actually
use, with busctl type signatures:

| Method | Signature | Returns |
|---|---|---|
| `StartUnit` / `StopUnit` / `RestartUnit` | `s` name, `s` mode (`replace`, `fail`, `isolate`, ...) | `o` job object path |
| `GetUnit` | `s` name | `o` unit object path |
| `ListUnits` | — | array of unit structs (name, load/active/sub state, job info) |
| `StartTransientUnit` | `s` name, `s` mode, `a(sv)` properties, `a(sa(sv))` aux | `o` job |
| `Subscribe` / `Unsubscribe` | — | enables signal delivery to this client |

Signals: `JobNew(u id, o job, s unit)` and `JobRemoved(u id, o job, s unit,
s result)` — the manager's completion feed behind `systemctl --wait` and
every orchestrator built on systemd. Per-unit objects expose `ActiveState`
(`active`/`activating`/`inactive`/`deactivating`/`failed`/`reloading`),
`SubState` (`running`, `dead`, `auto-restart`, ...), `Result` (same
vocabulary as `systemctl show -p Result`) and `ExecMainPID`. Unit object
paths escape the dot: `nginx.service` becomes
`/org/freedesktop/systemd1/unit/nginx_2eservice`.

### busctl by example

```bash
$ busctl call org.freedesktop.systemd1 /org/freedesktop/systemd1 \
    org.freedesktop.systemd1.Manager StartUnit "ss" nginx.service replace
o "/org/freedesktop/systemd1/job/4471"

$ busctl get-property org.freedesktop.systemd1 \
    /org/freedesktop/systemd1/unit/nginx_2eservice \
    org.freedesktop.systemd1.Unit ActiveState SubState
s  "active"
s  "running"

$ busctl monitor org.freedesktop.systemd1     # stream JobNew/JobRemoved
```

The `call` line is the exact translation of `systemctl start nginx.service`:
destination, path, interface, method, signature `"ss"` (two strings),
arguments. The returned job path plus `JobRemoved`'s `result` argument
(`done`, `failed`, `skipped`, ...) give the asynchronous outcome.
`busctl introspect` on any unit path lists every property and method — the
fastest way to learn what is tunable without restarting.

### The polkit gate

Privileged manager calls are authorized by polkit, not by D-Bus policy alone:
`org.freedesktop.systemd1.manage-units` (start/stop/restart),
`manage-unit-files` (enable/mask) and `set-property`. Root is allowed
implicitly, interactive users get an `auth_admin` prompt (hence "Authentication
required to manage system services" in GUI toolbars), and headless automation
either runs as root, is granted the action via a polkit rule, or uses
`systemctl --user` against the user manager. One authorization point serving
root, operators and user sessions is the design feature — D-Bus fundamentals
in [dbus (admin)](../../admin/dbus.md).

## Transient Units and systemd-run

A *transient unit* is created through the manager API at runtime, exists only
in memory, and disappears when it finishes. `systemd-run` is its CLI,
`StartTransientUnit` its API — the supported way to say "run this under
supervision, with constraints, without writing a file":

```bash
# One-shot with a CPU cap; wait for completion, propagate exit status
systemd-run --unit=benchmark --property=CPUQuota=50% --wait sleep 60

# Run a backup in a scope sharing your shell's cgroup (no new service unit)
systemd-run --scope -p MemoryMax=200M tar czf /tmp/backup.tgz /data

# Calendar-scheduled transient: timer + service pair, garbage-collected after run
systemd-run --on-calendar="Mon *-*-* 02:00:00" --unit=cleanup --collect /usr/local/bin/cleanup.sh
```

Flag semantics: `--unit` names the unit (else an auto `run-rXXXXXX.service`);
`--scope` runs the command in a `.scope` inside your current cgroup instead
of a supervised service; `--property=` accepts anything from
`systemd.exec(5)`; `--on-calendar` creates a transient `.timer` instead of an
immediate start; `--wait` blocks and propagates the exit status; `--collect`
garbage-collects the unit after it stops instead of leaving a `failed` corpse.
Typical uses: ad-hoc resource-capped jobs on shared boxes, CI orchestration,
sandboxed one-shot experiments. Transients report `is-enabled: transient` and
leave no trace in unit search paths — that state's place in the vocabulary is
tabulated in [systemctl-cli.md](./systemctl-cli.md).

## Generators

### What they are and when they run

A generator is a small executable run once, synchronously, at unit-load time
(manager start and every `daemon-reload`), before units are parsed. It may
write unit files and symlink trees into three directories passed as argv —
the slots encode precedence intent:

| argv | Directory | Precedence rule |
|---|---|---|
| `$1` | `/run/systemd/generator` | Normal output: used only when no native unit file of that name exists |
| `$2` | `/run/systemd/generator.early` | Early output: overrides native units, but admin files in `/etc` still win |
| `$3` | `/run/systemd/generator.late` | Late output: overridden by any native unit of the same name |

The flagship example is built in: `systemd-fstab-generator` reads `/etc/fstab`
(plus `root=`/`fstab=` kernel cmdline) at every load and emits `.mount`,
`.swap` and `.automount` units. An entry with `x-systemd.automount` becomes an
`.automount` unit that mounts on first access; `noauto` entries skip
`local-fs.target` membership. That is why fstab *is* unit configuration —
regenerated every load — and `systemctl cat var-lib-backup.mount` shows the
synthesized file.

### A complete tiny generator

This pattern ships a debug-getty unit only when the kernel cmdline asks for
it — common in appliance images:

```bash
#!/bin/sh
# /usr/lib/systemd/system-generators/demo-debug-gen
# argv: $1 normal output dir | $2 early | $3 late
set -eu
out="$1"
mkdir -p "$out"

grep -q "demo.debugshell" /proc/cmdline || exit 0

cat > "$out/demo-debug.service" <<'EOF'
[Unit]
Description=Demo debug shell on tty9
DefaultDependencies=no
Conflicts=shutdown.target
Before=shutdown.target
After=sysinit.target
[Service]
ExecStart=/sbin/getty 38400 tty9
[Install]
WantedBy=getty.target
EOF

mkdir -p "$out/getty.target.wants"
ln -sf ../demo-debug.service "$out/getty.target.wants/demo-debug.service"
```

Install it mode 755, root-owned, then `daemon-reload`; the unit appears (and
`systemctl cat demo-debug.service` shows it) only on boots with the cmdline
flag. Generator rules: run fast (they serialize the unit-load path), be
idempotent (they re-run on every reload), write only into the three given
directories, never talk to the manager or the bus, exit 0 even when producing
nothing. Note the generated unit re-declares its shutdown edges because it
uses `DefaultDependencies=no` — the contract covered in
[targets-runlevels.md](./targets-runlevels.md), now from the producing side.
Per-user generators run from `~/.config/systemd/user-generators` and write
under `/run/user/$UID/systemd/generator*`.

## Portability Guards

Software that must run under systemd *and* elsewhere follows a short
checklist, all visible in the snippets above:

- **`NOTIFY_SOCKET` unset means no-op.** `sd_notify` returns 0 without
  sending; hand-rolled implementations (like the Python one) guard
  explicitly. A missing supervisor is never an error.
- **`sd_listen_fds` returning 0 is normal** — not socket-activated, so bind
  your own sockets; only negative values are real errors.
- **Optional linking.** Build with `pkg-config libsystemd` when present, or
  `dlopen("libsystemd.so")` at runtime, or vendor the ~30-line `sd_notify`
  equivalent; the same binary then serves systemd and non-systemd hosts.
- **Detect the manager, not the distro.** `sd_booted()` (checks
  `/run/systemd/system`) is the supported probe; testing for `/bin/systemctl`
  is the anti-pattern.
- **Watchdog is opt-in per unit.** Ping only when `WATCHDOG_USEC` appears in
  the environment, so one binary works with or without `WatchdogSec=`.

The philosophical point: these protocols are *offers*, not requirements. A
daemon implementing them degrades to ordinary behavior on any other init
system — exactly why they achieved adoption in portable software while the
rest of systemd stayed admin-facing.

## Interview Questions

### Q: What does Type=notify add over Type=forking, and how does the daemon participate?

`Type=forking` guesses readiness from a PID file and the parent's exit;
`Type=notify` replaces guessing with an explicit protocol. The manager passes
a Unix datagram socket address via `NOTIFY_SOCKET` (an abstract-namespace
`@/run/systemd/notify` by default); the daemon sends `READY=1` when genuinely
serving, and the start job completes at that moment — so ordering edges wait
for real readiness, not a fork. The daemon can also stream `STATUS=` progress
into `systemctl status`, hand over `MAINPID=`, bracket reloads with
`RELOADING=1`/`READY=1` (`Type=notify-reload` makes `systemctl reload`
synchronous), and send `STOPPING=1` on shutdown. Cost: a few lines of daemon
code, or `systemd-notify` in a wrapper with `NotifyAccess=all`.

### Q: Explain the watchdog handshake and why a missed ping raises SIGABRT.

With `WatchdogSec=10s`, the manager exports `WATCHDOG_USEC=10000000` and
expects `WATCHDOG=1` datagrams at least twice per interval — every ~5 s —
typically from the daemon's event loop. A missed ping means the process is
wedged, and a wedged mainloop cannot execute signal handlers or cleanup
code, so graceful stop is pointless; the manager sends **SIGABRT** instead
of SIGKILL specifically so a core dump is captured (`Result=watchdog` in
`systemctl show`), giving post-mortem evidence, while
`Restart=on-abort`/`on-watchdog` encodes a distinct restart policy. The
half-interval recommendation absorbs scheduling jitter so one late ping is
not fatal.

### Q: Why does the socket activation protocol include LISTEN_PID, and what does sd_listen_fds(1) do with the environment?

`LISTEN_FDS` says how many inherited descriptors exist, but nothing prevents
the daemon from forking; without ownership checks a child could consume its
parent's passed sockets. `LISTEN_PID` names the exact PID the manager handed
them to, and `sd_listen_fds` ignores the variables unless it matches the
caller's PID — closing the fork-confusion hole. With argument `1`, the
function also unsets `LISTEN_FDS`/`LISTEN_PID` after reading, so a later
`exec` cannot re-inherit them. Descriptors start at 3
(`SD_LISTEN_FDS_START`) in the order the `.socket` unit defines.

### Q: When do generators run, and what is the precedence of their output?

Generators run synchronously at unit-load time — at manager start and every
`daemon-reload` — receiving three output directories: normal
(`/run/systemd/generator`, used only when no native unit of that name
exists), early (`generator.early`, overrides native units but loses to admin
files in `/etc`), and late (`generator.late`, overridden by any native
unit). They must be fast, idempotent, and write only into those directories.
The flagship is `systemd-fstab-generator`, which turns `/etc/fstab` into
`.mount`/`.swap`/`.automount` units at every load — why fstab edits need no
unit files, and why `systemctl cat` on a generated unit reveals synthesized
configuration.

### Q: What is a transient unit and when would you choose systemd-run over a unit file?

A transient unit is created through the manager API (`StartTransientUnit` /
`systemd-run`), lives only in manager memory, and is garbage-collected when
done (`--collect`) — no file on disk, no `daemon-reload`, gone after reboot.
Choose it for ad-hoc supervised work: resource-capped one-shots
(`systemd-run --scope -p MemoryMax=200M ...`), calendar-triggered temporary
jobs (`--on-calendar` builds a transient timer+service pair), CI steps that
need supervision semantics, sandboxed experiments (`--pty --property=
PrivateTmp=yes`). Choose a unit file when the service is a permanent citizen
needing enablement, ordering against other files, drop-ins or version
control. `list-units` shows transients alongside real ones and `is-enabled`
reports the `transient` state.

### Q: Which systemd interfaces are documented as stable for third-party software?

The command surfaces (`systemctl`, `journalctl`), the unit-file grammar, the
`org.freedesktop.systemd1` D-Bus API (methods, signals, properties), and the
library protocols: `sd_notify` readiness/watchdog datagrams, the
`LISTEN_FDS`/`LISTEN_PID` socket-activation contract, and the journal's
native read/write API. Everything else — internal state files, cgroup layout
details, load-path subtleties — can change between releases. That is why a
daemon integrating via `sd_notify` and socket activation stays correct
across major systemd upgrades while one scraping `/run/systemd/` internals
breaks.

## References

- [sd_notify(3) — the readiness/watchdog protocol](https://www.freedesktop.org/software/systemd/man/latest/sd_notify.html)
- [sd_listen_fds(3) — socket activation fd retrieval](https://www.freedesktop.org/software/systemd/man/latest/sd_listen_fds.html)
- [sd-journal(3) — journal write and read API](https://www.freedesktop.org/software/systemd/man/latest/sd-journal.html)
- [sd-bus(3) — D-Bus library overview](https://www.freedesktop.org/software/systemd/man/latest/sd-bus.html)
- [sd-event(3) — event loop API](https://www.freedesktop.org/software/systemd/man/latest/sd-event.html)
- [systemd.generator(7) — generator contract, directories, precedence](https://www.freedesktop.org/software/systemd/man/latest/systemd.generator.html)
- [systemd-notify(1) — send notifications from scripts](https://www.freedesktop.org/software/systemd/man/latest/systemd-notify.html)
- [systemd-run(1) — transient units from the CLI](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html)
- [org.freedesktop.systemd1(5) — the manager D-Bus API](https://www.freedesktop.org/software/systemd/man/latest/org.freedesktop.systemd1.html)
- [sd_notify(3) — Debian bookworm mirror](https://manpages.debian.org/bookworm/libsystemd-dev/sd_notify.3.en.html)
- [sd-bus(3) — Debian bookworm mirror](https://manpages.debian.org/bookworm/libsystemd-dev/sd-bus.3.en.html)
- [sd-journal(3) — Debian bookworm mirror](https://manpages.debian.org/bookworm/libsystemd-dev/sd-journal.3.en.html)
- [sd_listen_fds(3) — Debian bookworm mirror](https://manpages.debian.org/bookworm/libsystemd-dev/sd_listen_fds.3.en.html)
- [sd-event(3) — Debian bookworm mirror](https://manpages.debian.org/bookworm/libsystemd-dev/sd-event.3.en.html)
- [systemd.generator(7) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.generator.7.en.html)
- [systemd-notify(1) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd-notify.1.en.html)
- [systemd-run(1) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd-run.1.en.html)
- [Socket activation — L. Poettering's design write-up](http://0pointer.de/blog/projects/socket-activation.html)
- [systemd for developers I — the original integration tour](http://0pointer.de/blog/projects/systemd-for-developers-1.html)

## Cross-References

- [Socket activation](./socket-activation.md) — the `.socket` unit mechanics behind LISTEN_FDS and FDSTORE.
- [Service units](./service-units.md) — Type=notify, NotifyAccess, WatchdogSec and the lifecycle the protocol feeds.
- [Journal and journald](./journald.md) — where sd_journal entries land and how journalctl queries them.
- [cgroups and resource control](./cgroups-resource-control.md) — the cgroup properties --property and set-property manipulate.
- [Unit files](./unit-files.md) — the search paths generators write into and the drop-in layering they interact with.
- [D-Bus (admin)](../../admin/dbus.md) — the message bus underneath org.freedesktop.systemd1 and busctl.
- [systemd internals (admin)](../../admin/systemd-internals.md) — the manager internals the D-Bus API exposes.
- [SysVinit to modern init migration](../sysvinit/migration-modern.md) — what changes for daemons adopting these interfaces.
- [Init system comparison](../comparison.md) — which families offer equivalent programming APIs.
- [init-systems hub](../README.md) — section overview and reading order.
