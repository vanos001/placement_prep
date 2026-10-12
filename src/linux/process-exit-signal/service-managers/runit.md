# runit as a Supervisor — Unconditional Restarts, ./run and ./finish

runit is a three-stage init with a per-service supervisor (`runsv`) whose
restart model is the opposite of systemd's: **it always restarts a service
when it dies, regardless of exit code or killing signal, and it has no
restart limits.** The only levers are the service directory contents
(`./run`, `./finish`, `./down`), the control commands (`sv`, control
characters), and the `./finish` script, which receives the exit code and
signal number as arguments so *your script* can decide what a death meant.

Design philosophy and boot stages are covered in
[overview-philosophy.md](../../init-systems/runit/overview-philosophy.md)
and [stages-services.md](../../init-systems/runit/stages-services.md);
this page is the exit-code / signal / restart angle. Compare
[systemd.md](./systemd.md) (policy-driven restarts),
[openrc.md](./openrc.md), [s6.md](./s6.md) (the closest relative) and
[comparison.md](../../init-systems/comparison.md).

All claims below were verified against the official runit documentation
and sources at smarden.org — `runit(8)`, `runsv(8)`, `sv(8)`,
`runsvdir(8)`, `svlogd(8)` (retrieved 2026-10) — and, for behavior the
man pages summarize, the runit-2.2.0 source tarball distributed on the
same site (`src/sv.c`, `src/runsv.c`).

## The three-stage design and where supervision lives (SM-008)

runit must run as Unix process no 1 and performs boot, run, and shutdown
in three stages (runit(8)):

| Stage | Script | Exit-status contract |
|---|---|---|
| 1 — boot | `/etc/runit/1` | one-time initialization; "if /etc/runit/1 crashes, or exits 100, runit will skip stage 2 and enter stage 3" — exit 100 is the documented "boot failed" marker; it holds `/dev/console` to start an emergency shell |
| 2 — run | `/etc/runit/2` | "should not return until system shutdown; if it crashes, or exits 111, it will be restarted"; normally it just execs `runsvdir`, so the whole service supervision layer hangs off a stage-2 process that PID 1 itself restarts |
| 3 — halt | `/etc/runit/3` | shutdown tasks; after it returns, the system reboots if `/etc/runit/reboot` is executable, halts otherwise |

runit "only accepts signals in stage 2": `CONT` plus an executable
`/etc/runit/stopit` triggers shutdown, `INT` emulates ctrl-alt-del. The
supervision machinery itself is a tree: `runit` (PID 1) → `runsvdir` →
one `runsv` per service directory (up to 1000 per runsvdir, which
"restarts a runsv process if it terminates" — supervising the
supervisors, runsvdir(8)). runsvdir rescans the service directory every
five seconds when its mtime/inode/device changes, starting runsv for new
subdirectories and sending `TERM` to runsv whose directory disappeared.

## ./run lifecycle and unconditional restart (SM-008)

`runsv(8)` describes the complete service loop:

1. `runsv` switches into the service directory and starts `./run`.
2. **"If ./run exits and ./finish exists, runsv starts ./finish. If
   ./finish doesn't exist or ./finish exits, runsv restarts ./run."**
   There is no exit-code or signal check anywhere in this loop — an
   exit-0 death and a SIGSEGV death both lead to a restart. This is a
   *design property*, not configuration: runit has no
   `Restart=on-failure` equivalent (see [systemd.md](./systemd.md)) and
   no exit-status vocabulary at all.
3. Anti-busyloop guard only: "If ./run or ./finish exit immediately,
   runsv waits a second before starting ./finish or restarting ./run."
   That single fixed second is the entire restart-limit machinery —
   **runit has no restart-per-window limit and no give-up behavior**
   (also a design property; if you need backoff or circuit-breaking, it
   must live in your `./run`/`./finish` or an external watchdog).
4. If `runsv` cannot start `./run` at all, it reports exit code 111 with
   status 0 to the finish script (see below).

### ./finish — where exit codes and signals are handed to you (SM-008)

The finish script receives exactly two arguments (runsv(8), verbatim
semantics; verified identical in `runsv.c` `startservice()`):

| Argument | Value |
|---|---|
| `$1` | `./run`'s **exit code**, or **`-1` if ./run didn't exit normally** (i.e. it was killed by a signal) |
| `$2` | the **least significant byte of the raw wait status** as determined by `waitpid(2)`: `0` if `./run` exited normally, or the **signal number** if it was terminated by a signal |

Two edge cases are documented: if `runsv` cannot start `./run`, the
finish script gets `111` and `0`; and if `./run` or `./finish` exit
immediately, the 1-second delay applies. Crucially, **runsv itself never
inspects the finish script's exit code** — after `./finish` exits,
`./run` is restarted unconditionally (source-verified: `startservice()`
is called with no status test). A finish script that wants to prevent
the next restart cannot do it via its exit status; it must communicate
out of band (e.g. alert, log, or arrange for `sv down`/`x` externally).

```sh
#!/bin/sh
# service/finish — classify the death of ./run
# $1 = exit code, or -1 if killed by a signal
# $2 = 0 if exited normally, else the signal number
if [ "$1" = "-1" ]; then
    echo "killed by signal $2" | logger -t mysvc
else
    echo "exited with code $1" | logger -t mysvc
fi
# cleanup work goes here; runsv will restart ./run afterwards regardless
```

> Precision note: the loop-level truth is "restart regardless of
> finish's exit code". The often-quoted "exit code 100–200 means stop"
> behavior is **s6's** (finish exit 125 ⇒ permanent failure, see
> [s6.md](./s6.md)), not runit's. runit's only documented exit-code
> conventions at the *stage* level are stage 1's `100` and stage 2's
> `111`.

### ./down — preventing autostart

If the file `service/down` exists, `runsv` does not start `./run`
immediately; the control interface starts the service on demand
(runsv(8)). Source-level precision (runsv.c): the file is checked **once,
when runsv starts** (`stat("down")` ⇒ want = down) — creating it later
does not stop an already-running service, and it also does not stop the
*next* restart inside a running runsv; use `sv down` for that. `down`
affects (a) the first start after runsv launches and (b) every start of
a fresh runsv, which is why it is the standard "installed but not
enabled here" marker. `sv` exposes it: `sv status` reports
`normally up`/`normally down` by statting `down` (sv.c), and s6's
equivalent `./down` semantics are documented in [s6.md](./s6.md).

## Control signals and sv (SM-008)

`runsv` reads one-character commands from the named pipe
`service/supervise/control` (normally written for you by `sv(8)`):

| Char | Command | Signal action |
|---|---|---|
| `u` | up | start if not running; restart when it stops |
| `d` | down | send `TERM` then `CONT`; run `./finish`; **do not restart** |
| `o` | once | start, do not restart on exit |
| `p` / `c` | pause / continue | `STOP` / `CONT` |
| `h`, `a`, `i`, `q`, `1`, `2` | — | `HUP`, `ALRM`, `INT`, `QUIT`, `USR1`, `USR2` |
| `t` | term | `TERM` (service keeps being restarted afterwards) |
| `k` | kill | `KILL` |
| `x` | exit | `TERM` + `CONT`, do not restart; when down, runsv exits (draining the log service first, if any) |

`sv(8)` maps these to subcommands (`sv up|down|once|pause|cont|hup|term|
kill|exit|status …`) plus LSB-compatible aliases (`start`, `stop`,
`restart`, `shutdown`, `force-stop`, `force-restart`, …). The waiting
variants (`-v`, `-w sec`, default **7 seconds**) poll until the command
took effect, and `sv` runs an optional `./check` program in the service
directory — exit 0 means "available" — to gate `start`/`restart`/`check`
success. `sv` exit codes: `0` success; **+1 per service that errored or
timed out, capped at 99**; `100` on error; in the LSB init-script
persona: `1` timeout, `2` usage, `3` down, `4` unknown status, `151`
error.

Custom stop hooks: for every control character `c` except `o`, `d`, `x`,
runsv first runs `service/control/c` if it exists and is executable; if
that program exits 0, runsv suppresses the built-in signal — the
documented way to implement graceful shutdowns (`control/t` receives the
service PID as its first argument).

### `sv status` output fields (SM-009)

`sv status` prints one line for the service and, if present, one for its
log service. Verified against `sv.c` (the `svstatus_print` function), the
line is:

```text
run: /service/sshd: (pid 1234) 5678s
run: /service/sshd/log: (pid 1301) 5678s
down: /service/backup: 12s, normally up
finish: /service/crashed: 3s, got TERM
```

| Field | Meaning |
|---|---|
| `run:` / `down:` / `finish:` | state word: process running, stopped, or finish script executing |
| directory | service directory path as given to sv |
| `(pid N)` | supervisor's record of the process PID (present when running) |
| `Ns` | seconds since the last state change |
| `, normally down` / `, normally up` | the `./down` file exists / does not exist |
| `, paused` | process is SIGSTOPped |
| `, want up` / `, want down` | desired vs. actual state diverge (e.g. `d` command in flight) |
| `, got TERM` | a TERM was sent and not yet acted upon |

The 20-byte binary status record lives in `service/supervise/status`
(daemontools-`supervise` compatible), with human-readable mirrors in
`supervise/stat` and the PID in `supervise/pid` (runsv(8)).

## Logging: the log/ subservice and svlogd (SM-009)

If `service/log` is a directory, runsv creates a pipe, points
`service/run`'s and `service/finish`'s stdout at it, and starts
`log/run` with stdin from the pipe (runsv(8)) — the classic
service/logger pair, supervised as two runsv children. The usual logger
is `svlogd(8)`: it "continuously reads log data from its standard input,
optionally filters log messages, and writes the data to one or more
automatically rotated logs", writing the current file `current` and
rotated files named `@<tai64n-timestamp>`; per-directory `config` files
control size/line counts/filtering, and a `processor` script can post-
process rotated logs. Failure of the logger is visible as its own
`sv status` line; the `x` command's drain-before-exit behavior exists to
avoid cutting the log pipe mid-write.

## A complete service directory (SM-008 / SM-009)

```sh
/service/mydaemon/
├── run         # exec's the daemon in the foreground (no self-daemonizing)
├── finish      # optional crash classifier ($1 exit code, $2 signal/0)
├── log/run     # svlogd pipeline; receives ./run + ./finish stdout
├── down        # optional: present = do not autostart this runsv
└── control/t   # optional custom stop hook (exit 0 suppresses the TERM)
```

```sh
#!/bin/sh
# run
exec 2>&1
exec chpst -umydaemon mydaemon --foreground
```

```sh
#!/bin/sh
# log/run — svlogd keeps ./current plus rotated @<tai64n> files
exec svlogd -tt /var/log/mydaemon
```

Operate it with `sv`:

```console
$ sv status mydaemon
run: /service/mydaemon: (pid 4321) 187s
run: log: (pid 4320) 187s
$ sv restart mydaemon      # term, cont, up, then wait (./check consulted)
$ sv down mydaemon         # TERM + CONT, run ./finish, no restart
```

Reading the status line: both producer and logger are `run:`-state with
their PIDs and uptime; after a `sv down` completes the first field flips
to `down:` and, if the service directory has no `./down` file, the line
gains `, normally up` — exactly the fields enumerated in the table
above. The 7-second default wait (overridable with `-w`) is the only
patience `sv` offers; runit has no timeout escalation, so a daemon that
ignores `TERM` must be killed with `sv kill` or shut down gracefully by
a `control/t` hook.

## Zombie reaping and failure reporting

`runsv` is the direct parent of `./run` and `./finish` and reaps their
statuses itself (that is where `$1`/`$2` come from); the logger is
reaped likewise. Daemons that fork their own children are responsible
for reaping them; processes orphaned inside the service tree are
re-parented by the kernel to process 1 (runit), whose init loop reaps
them — the usual Unix re-parenting contract, a design property of any
PID 1 rather than a documented runit feature (background in
[process-control.md](../../sysprog/process-control.md)).

Failure reporting is deliberately minimal: there is no persistent
"failed" state to query — a dead service is just momentarily `down` for
the second before the restart. What you have is `sv status` (state word,
PID, uptime, `want`/`got TERM` flags), the `sv` exit codes above,
`./finish` as your classification hook (write it to `logger`/`svlogd` on
crash), and the 1-second restart cadence as the tell-tale crash loop in
`ps`/logs.

## Related Topics

- [overview-philosophy.md](../../init-systems/runit/overview-philosophy.md) —
  why the supervision tree looks like this.
- [stages-services.md](../../init-systems/runit/stages-services.md) —
  stage scripts and service directory conventions.
- [sv-logging.md](../../init-systems/runit/sv-logging.md) — svlogd
  configuration in depth.
- [comparison.md](../../init-systems/comparison.md) — runit vs. the rest.
- [systemd.md](./systemd.md) — the policy-driven counterpart;
  [s6.md](./s6.md) — same philosophy with finish-exit-code semantics and
  timeouts; [openrc.md](./openrc.md) — supervision as an option;
  [index.md](./index.md) — comparison table.
- [signals.md](../../sysprog/signals.md),
  [wait4.md](../../syscalls/process/wait4.md) — the `$2` byte is the
  low byte of the wait status described there.

## References

- runit(8) — a UNIX process no 1; three stages and their exit-code
  contracts: <http://smarden.org/runit/runit.8.html>
- runsv(8) — starts and monitors a service (./run, ./finish arguments,
  down file, control characters, customization, exit codes):
  <http://smarden.org/runit/runsv.8.html>
- sv(8) — control and manage services monitored by runsv (commands,
  7-second waits, `./check`, exit codes): <http://smarden.org/runit/sv.8.html>
- runsvdir(8) — starts and monitors runsv processes (1000 services,
  5-second rescan): <http://smarden.org/runit/runsvdir.8.html>
- svlogd(8) — runit's service logging daemon:
  <http://smarden.org/runit/svlogd.8.html>
- runit-2.2.0 source (official tarball, smarden.org) — `src/sv.c`
  status-line fields, `src/runsv.c` finish-argument construction and
  one-time `down` check, retrieved 2026-10:
  <http://smarden.org/runit/>
