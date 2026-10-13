# OpenRC as a Supervisor — supervise-daemon, start-stop-daemon, and Restart Semantics

OpenRC is a dependency- and runlevel-based init system whose defining
property — from a process-lifecycle point of view — is that **supervision
is optional**. Out of the box it starts and stops service scripts and then
*goes away*: the official user guide states that "when all the service
scripts are started openrc terminates. There is no persistent daemon."
Whether a dead service gets restarted depends entirely on which
`supervisor=` a service script selects, and only one of the three choices
actually supervises.

The general OpenRC architecture, runlevels, and dependency graph are
covered in
[overview-architecture.md](../../init-systems/openrc/overview-architecture.md)
and [runlevels-services.md](../../init-systems/openrc/runlevels-services.md);
this page is strictly the exit-code / signal / restart angle. Compare with
[systemd.md](./systemd.md) (exit-status-conditioned restarts),
[runit.md](./runit.md) and [s6.md](./s6.md) (always-restart supervision)
and the [comparison](../../init-systems/comparison.md) page.

All claims below were verified against the official OpenRC sources —
`user-guide.md`, `supervise-daemon-guide.md`, and the roff man page sources
`openrc-run(8)`, `supervise-daemon(8)`, `start-stop-daemon(8)` in the
OpenRC GitHub repository (master, retrieved 2026-10) — plus the
`supervise-daemon.c` / `schedules.c` C sources for behavior the man pages
leave implicit.

## The openrc-run start/stop flow and exit-status handling (SM-006)

A service is a POSIX-shell script in `/etc/init.d/` interpreted by
`openrc-run(8)`. Per the man page, when a service runs a command,
openrc-run loads the service's `conf.d` file, the master configuration,
`/etc/rc.conf`, and the script itself, then runs the requested *command*,
which is a shell function. The default flow:

| Command | Documented behavior (openrc-run(8)) |
|---|---|
| `start` | first ensures dependencies are started — "if any needed services fail to start then we exit with a suitable error" — then calls the script's `start()` function if it exists |
| `stop` | first ensures dependents are stopped, then calls `stop()` |
| `restart` | stops and starts; cannot be overridden (`RC_CMD` tells the script it is a restart) |
| `status` | "shows the status of the service. The return code matches the status, with the exception of `started` returning 0" |
| `zap` | resets state to stopped, discarding saved data — the way to reset a crashed service *without* invoking a possibly broken `stop()` |

Success/failure is therefore **return-code based**: the script's
`start()`/`stop()` functions report via `eend`/return values (the bundled
scripts use `ebegin`/`eend` from libeinfo), and openrc-run marks the
service started/stopped/failed accordingly. There is no exit-code table,
no signal-name matching, and no `SuccessExitStatus=`-style vocabulary: a
service is "started" if its start path returned success, and its runtime
health is not modeled at all unless a supervisor is attached.

## Three supervisors, one variable (SM-006)

The `supervisor` variable selects how the *default* start/stop functions
launch the daemon (openrc-run(8): "This defaults to start-stop-daemon for
historical reasons"):

| `supervisor=` | Supervises? | Restart behavior |
|---|---|---|
| `start-stop-daemon` (default) | **no** | none — start/stop only |
| `supervise-daemon` | yes | respawns the daemon whenever it exits, unconditionally (bounded by respawn limits) |
| `s6` | yes (delegates) | OpenRC drives an external s6 tree; see [s6.md](./s6.md) |

If you write your own `start()`/`stop()` functions, none of the supervisor
machinery applies — the official supervise-daemon guide is explicit: "If
you write your own start, stop and status functions in your service
script, none of this will work. You must allow OpenRC to use the default
functions."

### start-stop-daemon services do NOT restart

With the default `start-stop-daemon` supervisor (OpenRC's own
re-implementation of Debian's s-s-d), OpenRC backgrounds the daemon
(`command_background=yes` forces `--make-pidfile`/`--pidfile`), writes a
pidfile, and exits. Nothing watches the resulting process:

- If the daemon dies at runtime, **no restart happens** — this is the
  classic difference from systemd/runit/s6. The only recovery is
  administrative: re-running `openrc` "will try to reset all services so
  that the current runlevel is satisfied; if … squid died but is in the
  current runlevel it'll be restarted" (user guide) — a runlevel
  re-synchronization, not continuous supervision.
- Stop signaling uses `stopsig` (default **SIGTERM**) targeted via the
  pidfile, `procname`, or `name` matching. The `retry` variable
  (`-R, --retry`) accepts a timeout or `signal/timeout` pairs; per the
  man pages the default schedule is `SIGTERM/5` — send SIGTERM, wait up
  to 5 seconds. Source-level note (schedules.c): a bare `signal/timeout`
  schedule does **not** auto-append SIGKILL; escalation to `SIGKILL`
  happens only if the schedule explicitly includes it (e.g.
  `retry="SIGTERM/10/SIGKILL/5"`). This differs from the common
  "SIGTERM then KILL" folklore.
- **Pidfile considerations are the weak point**: pidfiles are racy and
  can point at recycled PIDs; s-s-d additionally matches by executable
  name (`procname=`), which is why the user guide has a whole section on
  "Dealing with Orphaned Processes" and adds a `cgroup_cleanup` command
  (Linux, cgroups enabled; make it automatic with
  `rc_cgroup_cleanup=yes`) to sweep up orphans left behind when, e.g., a
  supervise-daemon itself dies.

### supervise-daemon — OpenRC's built-in supervisor

`supervise-daemon(8)` "starts a daemon and restarts it if it crashes".
Per the project's own guide it exists "beginning with OpenRC-0.21"
(verified from `supervise-daemon-guide.md` in the official repo). Its
model is runit/s6-like:

- The daemon **must not fork**: "Any daemon that you would like to have
  monitored by supervise-daemon must not fork. Instead, it must stay in
  the foreground" (guide); the man page adds that supervise-daemon "only
  works with daemons which do not fork". Foreground flags go into
  `command_args_foreground=`.
- supervise-daemon forks/execs the daemon and is its parent, so it
  **reaps** the daemon's exit status directly; the man page's
  `respawn` machinery then applies. Its observations are logged via
  syslog with the exact wait(2) decomposition — "exited with return code
  %d" vs. "terminated by signal %d" (verified in supervise-daemon.c) —
  which is OpenRC's only recorded exit-code/signal distinction.
- **Restart policy**: respawn is unconditional. There is no equivalent of
  systemd's `Restart=on-failure` / exit-code conditions — any death
  (exit code 0 included, e.g. a health-check-triggered restart) is
  followed by a respawn. This is a design property, not a configurable
  one.

Respawn bounding (all verified against supervise-daemon(8) and the
defaults in supervise-daemon.c):

| Option / variable | Default | Meaning |
|---|---|---|
| `respawn_delay` (`-D`) | `0` | wait before restarting after a crash; accepts `ms`/`sec`/`min`/`hour` |
| `respawn-delay-step` | `128ms` | linear delay growth per retry within the period |
| `respawn-delay-cap` | `30sec` | cap on the stepped delay |
| `respawn_max` (`-m`) | `10` (`0` = unlimited) | give up after this many respawns |
| `respawn_period` (`-P`) | `12sec` | window for `respawn_max`; more than `respawn_max` crashes inside the window ⇒ give up |

When the limit trips, supervise-daemon logs
`respawned "<daemon>" too many times, exiting` via syslog and stops
supervising (source-verified). The man page carries an explicit warning
that mis-set combinations can cause infinite respawning (e.g. a respawn
period shorter than the delay × max), so verify your numbers. Note a
documentation discrepancy worth knowing: the man page states
`respawn-period` defaults to `12sec` (as does the current source), while
the guide text still says "by default … unset and respawn_max applies to
the entire lifetime of the service" — treat 12s as the operative default
on current versions.

**Health checks** add a second restart trigger: define a `healthcheck()`
function (and optionally `unhealthy()`) plus `healthcheck_timer=` /
`healthcheck_delay=`; when `healthcheck()` returns non-zero,
`unhealthy()` runs for cleanup and "the service is restarted" by the
supervisor (guide). The check runs every N seconds inside supervise-daemon
(the C source shows it reaps the check, runs `unhealthy`, then kills the
child through the same retry schedule).

**Stop signaling and escalation**: to stop the supervised child,
supervise-daemon runs the same retry-schedule engine
(`run_stop_schedule`) with `retry` (default `SIGTERM/5`); as with s-s-d,
SIGKILL only happens if your schedule includes it. `stopsig=` is the
signal used by the default stop function, but for supervise-daemon the
man page notes "using retry is preferred". `stopgroup=yes` signals the
whole process group instead of just the child.

**Readiness notification**: `notify=fd:N` makes supervise-daemon wait
until the daemon writes a newline to descriptor N; `notify=socket:ready`
exports `$NOTIFY_SOCKET` and waits for a `READY=1` datagram — the same
wire protocol systemd's `sd_notify` uses (see [systemd.md](./systemd.md)),
so sd_notify-aware daemons can announce readiness without linking
libsystemd. This is readiness reporting only; it does not gate restarts.

**Failure reporting**: there is no `failed` unit state like systemd's.
State is visible through `rc-service <svc> status` / `rc-status`, the
supervisor's syslog messages (crashes, health-check failures, respawn
give-ups), and its own pidfile (`-p, --pidfile` is the *supervisor's*
pidfile, "not the pid file of the process that is being supervised").

### A supervise-daemon service script

```sh
#!/sbin/openrc-run
# /etc/init.d/myworker

description="Foreground worker, supervised"
supervisor=supervise-daemon
command=/usr/libexec/myworker
command_args_foreground="--foreground"   # must NOT daemonize
command_user="myworker:myworker"

# respawn bounding (defaults: delay 0 / max 10 / period 12sec)
respawn_delay=2
respawn_max=5
respawn_period=60

# stop schedule: SIGTERM, wait up to 10s, then SIGKILL, wait up to 5s
retry="SIGTERM/10/SIGKILL/5"

# readiness (optional): sd_notify-style or fd handshake
# notify="socket:ready"

# log the daemon's output through a logger process instead of a file
output_logger="logger -t myworker"

depend() {
    need net
}
```

With `supervisor=s6` instead, openrc-run delegates to an s6 tree:
`s6_service_path` (default `/var/svc.d/${RC_SVCNAME}`),
`s6_service_timeout_stop` (default 60000 ms),
`s6_force_kill`, and `s6_svwait_options_start` are the documented knobs
(openrc-run(8)); the supervision semantics are then s6's — see
[s6.md](./s6.md).

## What OpenRC does not have (SM-007 summary)

Compared with the other managers on this shelf:

- **No exit-status-based restart conditions** — no
  `SuccessExitStatus=`/`RestartPreventExitStatus=` equivalents; a
  supervised daemon restarts regardless of how it exited.
- **No signal-name-based success classification** — the four
  "clean signals" of systemd have no OpenRC counterpart; stop signaling
  is a schedule, restart detection is binary.
- **No cgroup-enforced teardown by default** — Linux cgroups are used for
  accounting and optionally cleanup (`rc_cgroup_mode`, `cgroup_cleanup`),
  not as the kill scope; `stopgroup` is the coarse group-kill option.
- **No persistent manager at runlevel rest** — unless a service opts into
  supervise-daemon/s6, a dead service stays dead until something runs
  openrc again.

## Related Topics

- [overview-architecture.md](../../init-systems/openrc/overview-architecture.md) —
  where openrc-run and the supervisor fit in the boot flow.
- [init-scripts.md](../../init-systems/openrc/init-scripts.md) — writing
  the service scripts this page supervises.
- [comparison.md](../../init-systems/comparison.md) — feature matrix
  across init systems.
- [systemd.md](./systemd.md) — the exit-code-conditioned alternative;
  [runit.md](./runit.md), [s6.md](./s6.md) — always-restart alternatives;
  [index.md](./index.md) — side-by-side comparison.
- [signals.md](../../sysprog/signals.md) — SIGTERM/SIGKILL semantics
  behind the retry schedules.

## References

- OpenRC Users Guide (`user-guide.md`) — no persistent daemon; runlevel
  re-sync restart; orphan/cgroup_cleanup:
  <https://github.com/OpenRC/openrc/blob/master/user-guide.md>
- Using supervise-daemon (`supervise-daemon-guide.md`) — "Beginning with
  OpenRC-0.21"; must-not-fork; health checks; respawn variables:
  <https://github.com/OpenRC/openrc/blob/master/supervise-daemon-guide.md>
- supervise-daemon(8) man source — respawn defaults (`-D` 0, `-m` 10,
  `-P` 12sec, step 128ms, cap 30sec), `retry` default `SIGTERM/5`,
  `notify` fd/socket:ready:
  <https://github.com/OpenRC/openrc/blob/master/man/supervise-daemon.8>
- openrc-run(8) man source — start/stop/status/zap flow, `supervisor=`
  values, default start/stop variable table (stopsig, retry, respawn_*,
  notify, s6_*):
  <https://github.com/OpenRC/openrc/blob/master/man/openrc-run.8>
- start-stop-daemon(8) man source — backgrounding, pidfiles, retry
  schedule: <https://github.com/OpenRC/openrc/blob/master/man/start-stop-daemon.8>
- Source verification (defaults and SIGKILL-escalation behavior):
  `src/supervise-daemon/supervise-daemon.c`, `src/shared/schedules.c`,
  <https://github.com/OpenRC/openrc> (master, retrieved 2026-10)
