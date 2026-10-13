# systemctl — Command Reference and Operational Patterns

## Overview

`systemctl` is the single client binary for talking to a systemd manager — the
system instance running as PID 1, a per-user instance (`systemctl --user`), or
a remote/container instance (`--host`, `--root`, `-M`). It is a thin D-Bus
client: almost every verb is translated into method calls on
`org.freedesktop.systemd1`, which is why `systemctl` works identically over
SSH with `--host` and why a hung manager shows up as a hung `systemctl`
rather than a fast error. Everything it reports comes from the manager's
in-memory state, not from disk — a distinction that matters after manual
edits or crashes.

The command's surface is large but not arbitrary: verbs fall into a small
number of functional families (lifecycle, enablement, query, manager-level),
and nearly every family shares the same option grammar. Learning the taxonomy
beats memorizing flags, because options compose: `--now` attaches to
enablement verbs, `--all`/`--state=`/`-t` filter query verbs, `--runtime` and
`--root` control where enablement and property changes land.

This page is the operational reference for that surface. Unit-file syntax
lives in [unit-files.md](./unit-files.md), per-type directives in
[service-units.md](./service-units.md), the dependency algebra behind
`list-dependencies` in [dependency-management.md](./dependency-management.md),
and journal plumbing for the debugging recipes in
[journald.md](./journald.md).

## Lifecycle Verbs

Lifecycle verbs submit jobs to the manager's transaction queue. They are
asynchronous by default: `systemctl start foo` returns once the job is
*queued*, not once the unit reports `active` — add `--wait` if a script needs
the synchronous form. The verbs and their exact semantics:

| Verb | What it does | Notes |
|---|---|---|
| `start` | Queue a start job; pulls in dependencies per the unit graph | No-op if already active; fails if the graph cannot be built |
| `stop` | Queue a stop job (`ExecStop`, `SIGTERM`, `TimeoutStopSec`, `SIGKILL`) | Does not stop dependent units (see [dependency-management.md](./dependency-management.md)) |
| `restart` | Stop (if needed) then start, as one job | The verb for config changes |
| `reload` | Send the reload signal/command (`ExecReload`) without restarting | Fails if the unit defines no `ExecReload`; never restarts the process |
| `reload-or-restart` | `reload` where possible, otherwise `restart` | `try-reload-or-restart` tolerates no-`ExecReload` units |
| `try-restart` | Restart only if the unit is currently active | Silently does nothing otherwise — the idempotent restart for cron jobs |
| `kill` | Send an arbitrary signal to the unit's cgroup (`--signal=`, `--kill-whom=`) | Bypasses the unit's normal kill logic; `--kill-whom=all` includes children |
| `clean` | Remove the unit's runtime/cache/state directories (`RuntimeDirectory=` etc.) | `--what=runtime`; stop the unit first |
| `freeze` / `thaw` | Cgroup-freeze and resume all processes of a unit (v248+) | Inspect a racing daemon without killing it |

Two verbs deserve emphasis. `reload` picks up a config change for a
well-behaved daemon while keeping the process, sockets and connections alive —
and its existence is a property of the *unit*: without `ExecReload=` it is an
error, hence the `reload-or-restart` fallback. `freeze`/`thaw` cgroup-freeze a
unit's processes so you can inspect a wedged or racing daemon without a
restart — a recent (v248) feature worth knowing by name.

## Enablement Verbs

Enablement verbs manipulate *unit files and symlinks on disk* — they change
what the manager will pull in at boot, not what is running now. The split
between "running" and "enabled" is the most common newcomer confusion:
`enable` starts nothing unless `--now` is given, and `start` survives no
reboot.

| Verb | Mechanism | Effect |
|---|---|---|
| `enable` | Symlinks in the `[Install] WantedBy=` target's `.wants` dirs, preferring `/etc` | Persistent across reboots; prints every link created |
| `enable --now` | `enable` plus a queued start job | The one-liner for "install and run" |
| `enable --runtime` | Symlinks under `/run/systemd/system/...` | Lost at reboot; handy for tests |
| `disable` | Remove those symlinks (and `Alias=` links) | Does not stop the unit |
| `reenable` | `disable` then `enable` | Re-derives links after changing `WantedBy=` |
| `preset` | Apply `/etc/systemd/system-preset/*.preset` policy | What distribution installers run; `preset-all` covers every unit |
| `mask` | Symlink the unit name to `/dev/null` (in `/etc`, or `/run` with `--runtime`) | The manager refuses to load the unit *at all*, even as a dependency — the strongest off-switch |
| `unmask` | Remove the `/dev/null` link | Does not re-enable; a masked-then-disabled unit stays disabled |
| `link` | Symlink a unit file from an arbitrary path (e.g. `/opt/app/foo.service`) into the search path | Makes a file outside the standard dirs loadable |
| `revert` | Delete admin overrides (drop-ins under `/etc`) and enablement links for the unit | Restores the vendor version — the undo button for `edit`/`set-property` |

### is-enabled State Values

`systemctl is-enabled foo` prints a single token describing the on-disk
situation — a compact map of the unit-file loading machinery:

| State | Meaning |
|---|---|
| `enabled` | `[Install]` symlinks exist persistently (under `/etc`) |
| `enabled-runtime` | Symlinks exist under `/run` only — gone after reboot |
| `linked` / `linked-runtime` | Unit file symlinked into the search path via `link`, but no enablement links (often: no `[Install]` section) |
| `alias` | The unit is an alias symlink pointing at another unit |
| `masked` / `masked-runtime` | Name is a symlink to `/dev/null`; the manager refuses to load it |
| `static` | Unit file exists, no `[Install]` section — startable only explicitly or as a dependency, never `enable`d |
| `generated` | A generator created the unit at load time (fstab translation, SysV wrapper); file lives under `/run/systemd/generator` |
| `transient` | Created at runtime via the API (`systemd-run`); exists only in manager memory |
| `indirect` | Not enabled itself, but listed in an enabled unit's `[Install] Also=` |
| `disabled` | No enablement symlinks — starts only when pulled in by something else |

`static` and `generated` surprise most people: template units (`foo@.service`)
are static because `[Install]` symlinks name *instances*, and every SysV init
script reports `generated` via `systemd-sysv-generator` — so `is-enabled`
output on a hybrid Debian box mixes both worlds.

## Query Verbs

Query verbs are read-only and script-safe; output ranges from human-oriented
(`status`) to machine-oriented (`show`, JSON with `-o json`):

| Verb | Reports | Key flags |
|---|---|---|
| `status [PATTERN...]` | Load/active/sub state, `Main PID`, cgroup tree, last 10 journal lines | `-l` (full lines), `-n 50` (more log lines), `--no-pager` |
| `is-active` / `is-failed` | Exit-code oriented check: prints the state, exits 0/3 | Ideal for monitoring probes |
| `show [PATTERN...]` | Every manager property as `Key=Value` (100+ keys) | `-p ExecMainStatus,Result` for exact fields |
| `cat PATTERN...` | The unit file as the manager sees it: fragment plus all drop-ins merged | The truth after generators and drop-ins |
| `list-units` | Loaded units in memory with load/active/sub states | `-t service`, `--state=failed`, `--all` for inactive |
| `list-unit-files` | Files on disk plus `is-enabled` state — the boot-time inventory | `--state=enabled,static` |
| `list-jobs` | The transaction queue: job id, unit, verb, state (waiting/running) | First stop for "why is start hanging" |
| `list-dependencies UNIT` | The dependency tree of a unit | `--reverse` shows *who depends on me*; `--plain` flattens |
| `list-sockets` | Socket units with listening addresses and the service each spawns | The socket-activation control panel |
| `list-timers` | Timer units: last and next trigger, and the unit activated | `--all` includes inactive timers |
| `list-machines` | Local host plus registered VMs/containers | `-M` targets any of them |

`show` versus `status`: `status` renders a curated view, `show` dumps the
property database it is built from. When a service fails, the two properties
that name the cause are `Result` (`success`, `protocol`, `timeout`,
`exit-code`, `signal`, `core-dump`, `watchdog`, `start-limit`, `oom-kill` on
newer releases) and `ExecMainStatus` (the numeric exit code or signal).
`cat` shows the merged result of vendor files, admin drop-ins and generator
output — it answers "why does the manager think this unit says
`Restart=always`?" in one command.

## Manager-Level Verbs

The last family acts on the manager itself rather than individual units:

| Verb | Effect |
|---|---|
| `daemon-reload` | Re-read all unit files, drop-ins and generator output (next section) |
| `daemon-reexec` | Re-execute the manager binary — rebootstrap PID 1 in place after upgrading systemd |
| `get-default` / `set-default TARGET` | Read/rewire `/etc/systemd/system/default.target`; affects future boots only |
| `isolate TARGET` | Start the target, stop everything not in its tree (runtime mode switch) |
| `rescue` / `emergency` | Isolate `rescue.target` / `emergency.target` — single-user shells via `sulogin` |
| `halt` / `poweroff` / `reboot` | Ordered shutdown paths; `--force` skips job machinery |
| `soft-reboot` (v254+) | Restart userspace only; the kernel keeps running |
| `set-property NAME.KEY=VALUE` | Persistently (or `--runtime`) change a runtime-adjustable property — writes a drop-in |
| `set-environment` / `show-environment` | Manager environment block inherited by all spawned units |

`isolate` is the modern `telinit`: it switches the machine between target
trees, and its dangers (stopping everything the new target does not want,
wall messages unless `--no-wall`, `AllowIsolate=yes` required) are dissected
in [targets-runlevels.md](./targets-runlevels.md). `set-property` is the
supported live-tuning path — it persists a drop-in rather than doing raw
cgroupfs writes the manager would fight over (see
[cgroups-resource-control.md](./cgroups-resource-control.md)).

## What daemon-reload Actually Does — and When You Need It

`systemctl daemon-reload` asks the manager to rebuild its in-memory
configuration: it re-reads every unit file and drop-in from all search paths
and re-runs all generators (`systemd-fstab-generator` translating
`/etc/fstab`, `systemd-sysv-generator` wrapping legacy scripts, plus custom
ones). It does **not** restart, stop or signal any process: running units
keep their current configuration until they are next (re)started, and a
reload after editing `ExecStart=` changes nothing about the running daemon.

You need it after any change the manager loads as configuration: editing or
adding unit files or drop-ins under `/etc/systemd/system` or
`/run/systemd/system`; editing `/etc/fstab` (mount and swap units are
generated at load time); adding/removing SysV init scripts or packages that
ship unit files (normally handled by package scriptlets, but needed in
containers and hand-rolled images). You do *not* need it for changes the
process re-reads itself (an app config file — send `systemctl reload`
instead), for `EnvironmentFile` contents (read at next start), or for
`set-property` changes (applied immediately).

The failure mode of forgetting a reload is subtle and interview-worthy: the
unit runs fine, `systemctl cat` shows your new drop-in on disk, but the
manager still executes the old `ExecStart` — the next `restart` then
surprises you by applying a config you "changed" hours ago. Configuration
management tools model this correctly with a handler that flushes
`daemon-reload` before any restart task.

## Key Global Options

Options come before the verb and compose across families:

| Option | Applies to | Effect |
|---|---|---|
| `--user` | All verbs | Talk to the per-user manager instead of the system one; needs `$XDG_RUNTIME_DIR` |
| `--all` / `-a` | Query verbs | `list-units --all` includes inactive units |
| `--failed` | Query verbs | Shorthand for failed services; the first command after an incident |
| `--now` | Enablement verbs | Combine enable/disable with an immediate start/stop job |
| `--runtime` | Enablement + `set-property` | Make the change in `/run` only — evaporates at reboot |
| `--no-block` | Lifecycle verbs | Submit the job and return without waiting for completion |
| `--job-mode=MODE` | Lifecycle verbs | Control collision behavior with already-queued jobs (next section) |
| `--root=PATH` | Enablement/query verbs | Operate on an offline sysroot (image building) without a running manager |
| `--host=USER@HOST` / `-H` | All verbs | Run against a remote manager over SSH |
| `-M NAME` | All verbs | Target a container/VM registered with machined, or `user@UID` |
| `-t TYPE` / `--state=STATE` | Query verbs | Filter by unit type and state; comma lists work |
| `--no-wall` | isolate/shutdown verbs | Suppress the wall broadcast to logged-in users |

`--no-block` matters beyond scripting convenience: a *blocking*
`systemctl start` from inside a unit's own `ExecStartPre` can deadlock the
transaction queue — the job cannot complete while the manager waits on you.
`--no-block` (or `--job-mode=ignore-dependencies` in rescue scenarios) breaks
that cycle.

## Jobs and --job-mode

Every lifecycle verb becomes a *job* — a `(unit, verb)` pair with a state
machine (`waiting` → `running` → done) — installed into the manager's
transaction. Two jobs on the same unit with the same verb deduplicate; a
start and a stop job on the same unit is a collision resolved by the mode:

| Mode | On collision |
|---|---|
| `replace` (default) | The new job replaces any queued job for the unit |
| `fail` | The new job fails immediately if a conflicting job exists — the race detector |
| `replace-irreversibly` | Like `replace`, but also beats running jobs; what shutdown uses |
| `isolate` | Start the unit, stop everything not required by it |
| `flush` | Cancel all queued jobs first, then enqueue |
| `ignore-dependencies` | Ignore all requirement dependencies — almost always a mistake, but the hatch for a graph wedged by a broken unit |
| `ignore-requirements` | Keep ordering, skip only requirements |

The queue is visible with `list-jobs`:

```text
$ systemctl list-jobs
JOB UNIT                                     TYPE  STATE
4471 nginx.service                           start running
4472 network-online.target                   start waiting

2 jobs listed.
```

A `waiting` job is blocked behind ordering or an unfinished dependency; a
`running` job is actively starting something. When the transaction engine
finds an ordering cycle it breaks it and logs the line you must recognize:

```text
systemd[1]: Breaking ordering cycle by deleting job postgresql.service/start
```

That means your `After=`/`Before=` graph is circular; find the edge you added
(usually a drop-in) — the unit whose job was deleted will *not* start this
boot. Full graph mechanics are in
[dependency-management.md](./dependency-management.md).

## systemd-analyze — The Companion Toolkit

`systemd-analyze` is the profiling and validation sidekick: it queries the
same manager (or offline unit directories) and answers the questions
`systemctl` does not.

| Subcommand | What it gives you |
|---|---|
| `time` | Kernel/initrd/userspace split and when the default target was reached |
| `blame` | Every unit sorted by start duration — hides parallelism |
| `critical-chain [UNIT]` | The chain of ordering edges that bounded boot time; `@` = activated at, `+` = took |
| `plot` | Boot timeline SVG (`> boot.svg`) — blame with concurrency shown |
| `verify UNIT...` | Offline unit lint: directive typos, missing binaries, cycles |
| `security [UNIT]` | Exposure audit (0.0–10.0) of every sandboxing directive, with remediation text |
| `dump` | The manager's complete internal state as grep-able text |
| `calendar SPEC` | Normalize a calendar event and print the next elapses — test `OnCalendar=` before shipping |

```text
$ systemd-analyze time
Startup finished in 2.584s (kernel) + 4.851s (initrd) + 1min 3.452s (userspace) = 1min 10.888s
graphical.target reached after 1min 3.391s in userspace

$ systemd-analyze blame | head -3
  13.705s plymouth-quit-wait.service
   7.214s dev-sda1.device
   4.988s networkd-dispatcher.service

$ systemd-analyze critical-chain multi-user.target
The time when unit became active or started is printed after the "@" character.
The time the unit took to start is printed after the "+" character.

multi-user.target @1min 3.391s
└─getty.target @1min 3.390s
  └─getty@tty1.service @1min 3.390s +1ms

$ systemd-analyze calendar "Mon *-*-* 02:00:00"
Normalized: Mon *-*-* 02:00:00
    Next elapse: Mon 2025-06-09 02:00:00 CEST
       From now: 3 days left
```

The classic misreading: `blame` ranks a slow service top even when it ran in
parallel and cost the boot nothing — `critical-chain` answers "what delayed
*reaching* the default target" and `plot` settles the argument visually.
`security` ends with a per-unit exposure line (`Overall exposure level for
nginx.service: 8.5 EXPOSED`) — the drop-in below is what lowers that score.

## Debugging Recipes

### Failed Unit Triage Chain

The standard first minute of a failed-service investigation, in order:

```bash
systemctl --failed                            # 1. what is failed at all
systemctl status nginx.service -l --no-pager  # 2. state + last journal lines
journalctl -u nginx.service -b --no-pager     # 3. full boot-scoped log
systemctl show nginx.service -p Result,ExecMainStatus,NRestarts  # 4. failure record
systemctl cat nginx.service                   # 5. effective config (drop-ins included)
```

Reading step 4: `Result=exit-code` with `ExecMainStatus=1` is an application
exit; `Result=signal` with `ExecMainStatus=6` is SIGABRT; `Result=timeout`
means `TimeoutStartSec=`/`TimeoutStopSec=` expired; `Result=start-limit`
means `StartLimitBurst=` was hit and the unit is *refused* until
`systemctl reset-failed nginx.service` — the classic "I fixed the config but
it still won't start". `Result=watchdog` ties into the `sd_notify` watchdog
([apis-development.md](./apis-development.md)).

### Stuck Jobs

A `systemctl start` that hangs is a job stuck in `running` on some unit in
`activating` state:

```bash
systemctl list-jobs                    # which job, which unit
systemctl status <that-unit> -l        # "running (1m 10s / 1m 30s)" = elapsed/timeout
```

The `(elapsed / timeout)` pair in `status` is the deadline countdown. Common
blockers: a `Requires=`-pulled unit that never comes up, `network-online.target`
with `systemd-networkd-wait-online.service` enabled but no link up (2-minute
default timeout), and socket-activated units whose `.socket` is masked. To
unwind the whole transaction, `systemctl --job-mode=flush start rescue.target`
or a targeted `systemctl cancel <job-id>` clears the queue.

### The --user Manager and Linger

`systemctl --user` is a full parallel manager per UID. Its gotchas are
environment-shaped: it needs `$XDG_RUNTIME_DIR` (usually `/run/user/1000`),
which exists only while the user has a session — over SSH without a login
shell, export it manually. Units live in `~/.config/systemd/user/` and
`/usr/lib/systemd/user/`; triage is `systemctl --user --failed` plus
`journalctl --user -u myapp`. By default everything user-owned dies at logout
— `loginctl enable-linger alice` pins `user@1000.service` running so her
timers and daemons keep working headless, the supported no-root replacement
for cron-driven per-user daemons. The manager itself is the system unit
`user@1000.service`, diagnosable with `systemctl status user@1000`.

## A Complete Hardening Drop-In

End-to-end: harden a service without touching the vendor file. Write the
drop-in, apply it, verify:

```bash
systemctl edit myapp.service
```

```ini
### /etc/systemd/system/myapp.service.d/override.conf
[Service]
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/myapp /run/myapp
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
NoNewPrivileges=yes
CapabilityBoundingSet=
AmbientCapabilities=CAP_NET_BIND_SERVICE
RestrictSUIDSGID=yes
SystemCallFilter=@system-service
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
```

```bash
systemctl daemon-reload                 # drop-in is new configuration
systemctl restart myapp.service         # running process still has old config
systemd-analyze security myapp.service  # verify the exposure score dropped
systemctl show myapp.service -p ProtectSystem,PrivateDevices   # proof
```

The workflow is the point: `edit` creates the drop-in (never a vendor-file
copy), `daemon-reload` teaches the manager, `restart` applies it, `security`
scores the result, and `revert` undoes everything if the app breaks — the
error will be an `EPERM` in `journalctl -u myapp -b`. Loosen over-tight
filters (`SystemCallFilter=@system-service @network-io`,
`MemoryDenyWriteExecute=no` for JIT runtimes); the full `Protect*`/`Restrict*`
catalog lives in [service-units.md](./service-units.md) and `systemd.exec(5)`.

## Interview Questions

### Q: What does `systemctl enable --now foo` do, and why is it two operations?

It performs two orthogonal actions: `enable` writes the `[Install]`-derived
symlinks (typically `multi-user.target.wants/foo.service`) so the unit is
pulled in at every future boot, and `--now` queues an immediate start job so
it is running now. Without `--now`, enablement takes effect only after
reboot; conversely plain `start` evaporates at next boot. The halves even
fail independently — a unit can be enabled but failed, or active but
disabled — which is why `is-enabled` and `is-active` are separate probes.

### Q: How does `mask` differ from `disable`, and when is masking the right tool?

`disable` removes the enablement symlinks, but the unit remains loadable — it
can still be started by hand and still *pulled in* by any other unit that
`Wants=`/`Requires=` it. `mask` symlinks the unit name to `/dev/null` so the
manager refuses to load the unit at all, including as a dependency; even an
explicit `systemctl start` fails with "Unit is masked". Mask is the tool for
guarantees: killing a conflicting vendor service (chronyd vs
systemd-timesyncd), preventing a socket unit from respawning a service, or
holding a unit down across package upgrades. `--runtime` masks vanish at
reboot — the safer default for experiments.

### Q: Why is `systemctl isolate` dangerous?

`isolate` starts the named target and atomically stops every unit not in that
target's dependency tree. Isolating `rescue.target` from a multi-user system
tears down networking, your SSH daemon (with you attached) and every other
service in one transaction; isolating a custom target that does not `Want`
your services stops them silently. It also wall-messages all logged-in users
unless `--no-wall` is passed and requires `AllowIsolate=yes` on the target.
Safe pattern: treat isolate as a maintenance mode switch from a console, and
build custom targets deliberately — the design for that is in
[targets-runlevels.md](./targets-runlevels.md).

### Q: Why does systemd require `daemon-reload` after editing a unit file, and what exactly does it do?

Unit files are loaded into the manager's memory; the running process tree is
driven from that snapshot, not by re-reading disk. `daemon-reload` re-reads
all unit files and drop-ins from every search path and re-runs all generators
(including fstab translation) — but signals no process, so running units keep
their old `ExecStart` until the next (re)start. Forgetting it produces the
classic stale-config bug: `cat` shows your edit, behavior does not change,
then a restart applies it all at once. Contrast with `systemctl reload`,
which asks the *daemon* (via `ExecReload`) to re-read its own application
config without restarting.

### Q: You run `systemctl restart nginx` and it hangs, then fails with a timeout. Walk me through triage.

`systemctl status nginx.service -l` first: a state of `activating (start)`
with `(14s / 1min 30s)` shows the start deadline countdown, and
`Result=timeout` after expiry. `journalctl -u nginx -b` shows whether the
process started at all or is waiting on something (a config error, a port
held by another process visible in `list-sockets`, a blocking
`ExecStartPre`). `systemctl show -p Result,ExecMainStatus` names the failure
class exactly. If `Result=start-limit`, the unit is in refusal mode and
`systemctl reset-failed` is required before the next attempt. The chain —
status, journal, show properties, cat the effective unit — resolves nearly
every failed-start case in under a minute.

## References

- [systemctl(1) — the full verb and option reference](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [systemd-analyze(1) — profiling, verification and security subcommands](https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html)
- [systemd(1) — the manager itself: what the client talks to](https://www.freedesktop.org/software/systemd/man/latest/systemd.html)
- [systemd man page index (latest)](https://www.freedesktop.org/software/systemd/man/latest/)
- [systemctl(1) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemctl.1.en.html)
- [systemd-analyze(1) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd-analyze.1.en.html)

## Cross-References

- [Service units](./service-units.md) — the `[Service]` section, restart semantics and sandboxing directives the drop-in example used.
- [Unit files](./unit-files.md) — search paths, drop-in layering, generators and specifiers behind `cat` and `daemon-reload`.
- [Journal and journald](./journald.md) — the `journalctl -u` side of every debugging recipe here.
- [Targets and the runlevel compatibility layer](./targets-runlevels.md) — what `isolate`, `set-default` and the shutdown verbs actually switch.
- [Dependencies and ordering](./dependency-management.md) — the graph that `list-dependencies`, jobs and `--job-mode` operate on.
- [systemd hands-on (admin)](../../admin/systemd.md) — everyday command cookbook this page deepens.
- [SysVinit tooling](../sysvinit/tooling.md) — the `service`/`chkconfig`/`update-rc.d` world `systemctl` replaced.
- [Init system comparison](../comparison.md) — where each family's control tool stands feature by feature.
- [init-systems hub](../README.md) — section overview and reading order.
