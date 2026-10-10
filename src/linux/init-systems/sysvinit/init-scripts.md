# /etc/init.d Scripts — Conventions and Patterns

## Overview

An init script is the unit of work of the whole SysV service model: a POSIX shell script that takes one action argument (`start`, `stop`, `status`, ...) and manages one service. Everything else in the stack — `rc`'s symlink walk, insserv's dependency computation, `invoke-rc.d`'s policy layer — exists to call these scripts in the right order with the right argument. A script that is merely *runnable* will boot; a script that is *compliant* will boot, stop cleanly, report status honestly, survive being run twice, and cooperate with every tool in the stack. This page is about that compliance layer: the LSB header (detailed on its own page), the action contract and exit codes, `start-stop-daemon` as the standard process-management engine, the `init-d-script` declarative shortcut, idempotency patterns, and the test matrix that separates a fragile script from a production one.

Two facts frame everything here. First, the contract is *by convention and by LSB specification*, not enforced by init: `rc` checks only the exit status, so a sloppy script boots fine and fails in production months later. Second, the same contract is what systemd's SysV compatibility reads — a well-formed script with a good LSB header translates to a generated unit almost mechanically, so writing it well is an investment that survives a migration.

## Anatomy of a Compliant Script

The skeleton below is the Debian-idiomatic form. Every element is load-bearing; the annotations explain why each exists:

```sh
#!/bin/sh
### BEGIN INIT INFO
# Provides:          myapp
# Required-Start:    $local_fs $remote_fs $network $syslog
# Required-Stop:     $local_fs $remote_fs $network $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Example application server
# Description:       Start the example Python application server that
#                    serves the internal dashboard.
### END INIT INFO

PATH=/sbin:/usr/sbin:/bin:/usr/bin
NAME=myapp
DESC="example application server"
DAEMON=/usr/local/bin/myapp
DAEMON_ARGS="--config /etc/myapp/myapp.conf"
PIDFILE=/run/myapp.pid
DAEMON_USER=www-data

[ -x "$DAEMON" ] || exit 5                  # 5 = "program is not installed" (LSB)

# Defaults file: administrator overrides, sourced if present.
[ -r /etc/default/myapp ] && . /etc/default/myapp

# LSB logging helpers: log_daemon_msg, log_end_msg, log_*_msg.
. /lib/lsb/init-functions

is_running() {
    [ -s "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

case "$1" in
  start)
    log_daemon_msg "Starting $DESC" "$NAME"
    if is_running; then
        log_end_msg 0                        # idempotent: already up = success
    else
        start-stop-daemon --start --quiet --background --make-pidfile \
            --pidfile "$PIDFILE" --chuid "$DAEMON_USER" \
            --exec "$DAEMON" -- $DAEMON_ARGS
        log_end_msg $?
    fi
    ;;
  stop)
    log_daemon_msg "Stopping $DESC" "$NAME"
    start-stop-daemon --stop --quiet --oknodo \
        --retry TERM/30/KILL/5 --remove-pidfile --pidfile "$PIDFILE"
    log_end_msg $?
    ;;
  restart|force-reload)
    $0 stop || true
    sleep 1
    $0 start
    ;;
  reload)
    log_warning_msg "Reload not supported - restarting instead" >&2
    $0 restart
    ;;
  status)
    if is_running; then
        echo "$NAME is running (pid $(cat "$PIDFILE"))"
        exit 0
    else
        echo "$NAME is not running"
        exit 3                               # 3 = "not running" (LSB status)
    fi
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|force-reload|reload|status}" >&2
    exit 2                                   # 2 = "invalid argument" (LSB)
    ;;
esac

exit 0
```

The structural checklist this skeleton satisfies — and that reviewers should enforce — is:

- `#!/bin/sh` (POSIX, not bash) for portability across /bin/sh implementations.
- A complete LSB header between the `### BEGIN/END INIT INFO` markers (field-by-field treatment in [lsb-headers.md](./lsb-headers.md)).
- An early `-x` test on the daemon with exit 5, so the script fails *honestly* when the package is half-installed.
- A sourced defaults file (`/etc/default/<name>`) so administrators can override variables without editing a package-owned file — the Debian counterpart of Red Hat's `/etc/sysconfig`.
- `case` dispatch over the LSB action set, with `force-reload` treated as an alias for "reload, or restart if reload is unsupported."
- LSB exit codes everywhere; `status` exits 0/3, the usage error exits 2.
- All daemon spawning delegated to `start-stop-daemon` rather than hand-rolled `nohup ... &` incantations (rationale below).

## The LSB Exit-Code Contract

`rc` and every policy tool look at exit statuses; the LSB defines what they mean, and the table is worth memorizing because scripts in the wild violate it constantly (and their violations surface as mysterious "boot continues anyway" or "service reported stopped" behaviors):

| Exit | Meaning | Typical trigger |
|---|---|---|
| 0 | Success (or idempotent no-op: already started/stopped) | normal path |
| 1 | Generic or unspecified error | anything unclassified |
| 2 | Invalid or excess argument(s) | unknown action, extra args |
| 3 | Unimplemented feature ("reload" not supported) | `reload` on a daemon without SIGHUP semantics |
| 4 | Insufficient privilege | user lacks rights (not root) |
| 5 | Program is not installed | `[ -x "$DAEMON" ]` failed |
| 6 | Program is not configured | config file missing/unreadable |
| 7 | Program is not running | `stop`/`restart` with nothing to stop |
| 8–99 | Reserved for future LSB use | do not use |
| 100–149 | Reserved for distribution use | distro-specific extensions |
| 150–199 | Reserved for application use | your app's own codes |
| 200–254 | Reserved | do not use |

The `status` action has its own sub-contract: 0 = running, 1 = dead but a pidfile exists (the "stale pidfile" case — worth reporting distinctly), 3 = not running, 4 = unknown. `service <name> status` and monitoring hooks read these codes, so a script that always exits 0 from `status` breaks every consumer silently.

One subtle but important rule: **exit 0 for idempotent no-ops.** `start` on a running service and `stop` on a stopped service are successes, not errors. Boot-time reruns and race-prone transitions depend on it; a script that exits 7 from a no-op `stop` will produce spurious boot failures on systems where K links run against services that never started.

## start-stop-daemon: The Process-Management Engine

`start-stop-daemon(8)` (shipped with dpkg on Debian) is the standard tool for the only hard part of an init script: starting a daemon *exactly once* and stopping *exactly the right processes*. Its value is that it centralizes the race conditions — pidfile creation, double-start checks, PID reuse — that hand-rolled scripts get wrong.

### Start mode

```console
start-stop-daemon --start --exec /usr/sbin/nginx --pidfile /run/nginx.pid \
                  -- --conf /etc/nginx/nginx.conf     # '--' separates daemon args
```

Key options and the traps attached to them:

| Option | Effect | Trap |
|---|---|---|
| `--exec PATH` | Match/execute by binary path | If the binary is a wrapper script, exec-matching may miss the real process |
| `--startas PATH` | Path to execute (no exec-matching) | Prefer `--exec` when a pidfile exists, for the double-start check |
| `--pidfile FILE` | Pidfile used for the "already running" check | Missing/empty pidfile + `--exec` falls back to scanning — slower, rarer matches |
| `--make-pidfile` | s-s-d writes the pidfile itself | Only safe for daemons that do NOT double-fork; see below |
| `--background` | Fork and detach | With `--make-pidfile`, records the *first* child's pid |
| `--chuid user[:group]` | Drop privileges (also `-c`) | The directory holding the pidfile must be writable by that user |
| `--chdir DIR` / `--chroot DIR` | Working directory / chroot before exec | relative config paths resolve from here |
| `--nice N` | Nice level | applies at spawn |
| `--oknodo` (`-o`) | Exit 0 if nothing done (already running / nothing stopped) | The idempotence flag — use it in `stop` at minimum |
| `--test` (`-t`) | Print what would happen, do nothing | Use in packaging tests |

The `--make-pidfile` warning deserves its own sentence: it is **unsafe with double-forking daemons**, because the pid recorded belongs to the intermediate child that exits, not to the daemon that survives. If your daemon writes its own pidfile (most do — nginx, sshd, rsyslog), let it, and point `--pidfile` at the daemon's own file. If your daemon cannot write a pidfile and does not fork, `--background --make-pidfile` is correct. If it double-forks and cannot write a pidfile, neither tool helps; you need a supervisor or a wrapper.

### Stop mode

```console
start-stop-daemon --stop --pidfile /run/myapp.pid \
                  --retry TERM/30/KILL/5 --remove-pidfile --oknodo
```

The `--retry` schedule is the elegant part: a slash-separated sequence of signal/seconds pairs, applied in order — send SIGTERM, wait up to 30s for exit, then SIGKILL, wait up to 5s. This single line implements the graceful-then-forced shutdown that hand-written scripts approximate with `sleep` and crossed fingers. Matching selectors for stop mode: `--pidfile`, `--pid PID`, `--ppid`, `--name` (process name), `--exec` (binary path), `--user`; `--name` matching is the weakest (name collisions) and `--pidfile`+`--exec` together is the strongest (the pid must match *and* its cmdline must be the expected binary — s-s-d verifies to avoid killing a recycled PID).

## The init-d-script Declarative Style

For the common case — "run one daemon with these arguments" — Debian's sysvinit-utils ships `/lib/init/init-d-script`, an interpreter that turns a short variable-driven script into a fully compliant one:

```sh
#!/lib/init/init-d-script
### BEGIN INIT INFO
# Provides:          secondapp
# Required-Start:    $remote_fs $network
# Required-Stop:     $remote_fs $network
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Demo of the init-d-script interpreter
### END INIT INFO
DAEMON=/usr/sbin/secondapp
NAME=secondapp
PIDFILE=/run/secondapp.pid
DAEMON_ARGS="--listen 0.0.0.0:8080 --workers 2"
```

That is the whole script: the interpreter provides `start`/`stop`/`restart`/`status` with correct LSB exit codes, sources `/lib/lsb/init-functions`, handles the pidfile, and honors overrides. Customization is via override functions — define `do_start_cmd_override()`, `do_stop_cmd_override()`, or supply `do_reload()` to replace individual behaviors while inheriting the rest. It is documented in `init-d-script(5)`, and it is the right default when your service fits the "one daemon, one pidfile" shape; reach for the full skeleton only when you need nonstandard verbs or multi-process logic. For a fully worked custom script with a real service, see [custom-init-scripts.md](./custom-init-scripts.md).

## Red Hat Heritage (for reading, not writing)

RHEL 5/6-era scripts differ cosmetically but contractually little: they source `/etc/rc.d/init.d/functions` and use its helpers — `daemon` (start with pidfile bookkeeping), `killproc` (signal by pidfile/name with TERM-then-KILL), `status` (with the same 0/3-ish status codes), `pidfileofproc` — and they read config from `/etc/sysconfig/<name>` instead of `/etc/default/<name>`. Registration is via a `# chkconfig: 2345 20 80` comment line rather than (or alongside) the LSB header; the equivalence mapping is covered on the LSB headers page. Nothing here transfers to Debian tooling, but half the scripts you will meet on the internet are written in this dialect, so recognizing it prevents misreading.

## Idempotency, Concurrency, and Common Bugs

### Preventing double starts

Beyond `start-stop-daemon`'s built-in check, two shell-level guards are standard. For whole-script serialization (two admins, or rc racing cron):

```sh
exec 9>/run/lock/myapp.init.lock
flock -n 9 || { logger -t myapp "init script already active"; exit 0; }
```

For a daemon-level check without s-s-d, validate the pidfile against `/proc` before trusting it:

```sh
if [ -s "$PIDFILE" ]; then
    pid=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$pid" ] && [ -d "/proc/$pid" ] \
       && tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q "$NAME"; then
        exit 0        # genuinely running
    fi
    rm -f "$PIDFILE"  # stale: dead PID or PID recycled to another program
fi
```

The `grep` on `/proc/$pid/cmdline` is the step that prevents the classic PID-reuse disaster: killing an unrelated process that inherited the recycled PID.

### Daemonization done by hand (and why each piece)

If you cannot use s-s-d, the canonical backgrounding line is:

```sh
nohup setsid "$DAEMON" $DAEMON_ARGS </dev/null >>/var/log/myapp.log 2>&1 &
```

- `</dev/null` — detach stdin so the daemon never blocks reading a terminal that no longer exists.
- `>>file 2>&1` — capture stderr (where daemons die loudly) rather than losing it to the console.
- `setsid` — new session: no controlling terminal, so terminal signals and hangups cannot reach the daemon; it also protects rc from SIGHUP side effects.
- `nohup` — belt-and-braces SIGHUP immunity for the interval before setsid takes effect.
- `&` — do not block rc; rc scripts must return or the boot stalls.

The full theory — why double-forking matters, what a session is, why daemons should not hold the controlling terminal — is in [daemons.md](../../../os/processes/daemons.md). In practice, prefer s-s-d or the daemon's own daemonization; hand-rolled recipes are for reading, not writing.

### Quoting, limits, and other small sharp edges

- Quote `$DAEMON_ARGS` expansion deliberately: unquoted (`-- $DAEMON_ARGS`) gets word-splitting (usually intended for args); quoted passes one giant argument (usually not).
- Resource limits: apply `ulimit -n 65536` (fds) or `prlimit --nofile=...` before spawning; a daemon that opens more files than the inherited limit dies at load, not at install.
- `umask 022` before spawning if the daemon creates world-readable files; log directories pre-created with the right ownership, since `--chuid` drops privileges *before* the daemon can fix permissions itself.
- Never `cd` in an init script without a reason; relative paths then depend on who invoked the script — the source of many "works by hand" bugs.

## The Status Contract and Logging Conventions

`status` is the action external tools rely on most: `service <name> status` prints its output and propagates its exit code, monitoring scripts call it on a schedule, and on systemd systems the SysV-compat layer maps it onto unit state. The compliant implementation prints one human line (`name is running (pid N)` / `name is not running`) and exits 0/3 (with 1 for dead-but-pidfile). Avoid `grep -q`-style silent statuses — the human reading `service --status-all` output at 3 a.m. needs the line.

For progress output, always go through `/lib/lsb/init-functions`:

```sh
log_daemon_msg "Starting $DESC" "$NAME"    # "Starting example application server: myapp"
log_end_msg $?                             # appends [ OK ] / [FAIL] based on exit code
log_success_msg "migrated database"
log_warning_msg "skipping prune"
log_failure_msg "cache warm failed (non-fatal)"
```

These respect `VERBOSE`, handle coloring and the boot-console vs interactive-terminal distinction, and are what makes Debian boot output consistent. Bypassing them (raw `echo`) is the fastest way to make a script look amateur — and to lose its messages on the boot console where echo ordering matters.

## Test Matrix for a New Script

Run every row before shipping; each row corresponds to a real production failure mode:

| Test | Command | Pass condition |
|---|---|---|
| Syntax | `sh -n /etc/init.d/myapp`; `shellcheck` if available | no syntax/shell issues |
| Header sanity | insserv dry-run (`insserv -n`) | no header/ordering complaints |
| Cold start | `service myapp start` (twice) | second start exits 0, single daemon (`pidof`) |
| Status honesty | `service myapp status; echo $?` | 0 while running, 3 after stop |
| Graceful stop | `kill -STOP <pid>` then `service myapp stop` | honors `--retry` schedule, no hang |
| Stale pidfile | kill -9 the daemon, then `start` | recovers, new pidfile, no zombie kill |
| Restart | `service myapp restart` under load | no connection storm, no double daemon |
| Boot simulation | chroot + `policy-rc.d` deny, `update-rc.d -n` | links created, actions denied as expected |
| Reboot test | full VM reboot, twice | starts at boot, ordering correct, no race |
| Log presence | read `/var/log/boot` after reboot | messages visible via log_* helpers |

The reboot test is non-negotiable: boot-time context differs from hand-run context in environment, working directory, and console state, and roughly half of all init-script bugs reproduce only there.

## Interview Questions

### Q: What does exit code 7 from an init script mean, and why does the "already stopped" case exit 0 instead?

7 is "program is not running" — the LSB code for stop/restart finding nothing. But a `stop` on an already-stopped service should exit 0, because idempotent no-ops are successes: transitions rerun scripts against services whose state the caller could not know (a K link on a service that never started this boot, a rerun after a partial failure). Exit 7 is reserved for contexts where the *caller* genuinely needed the service and its absence is the report — and the `status` action's not-running code is 3, not 7. Knowing which code belongs to which verb is the difference between a script that cooperates with rc and one that generates false boot failures.

### Q: Why is `start-stop-daemon --make-pidfile` unsafe with double-forking daemons, and what are the alternatives?

Because the pidfile records the first child s-s-d created, while a double-forking daemon's surviving process is a grandchild with a different PID — the pidfile then points at a dead PID, and stop/status logic based on it fails or kills the wrong thing. Alternatives, in order of preference: let the daemon write its own pidfile and point `--pidfile` at it (nginx, sshd, rsyslog all do this); use `--background --make-pidfile` only when the daemon does not fork at all; or move the service to a real supervisor (runit/s6/systemd) where the supervisor owns the child and pidfiles become unnecessary. The general principle: exactly one party must own the process identity, and mixing owners is the root cause of most pidfile bugs.

### Q: Your stop path must not hang the boot. What mechanism enforces graceful-then-forced termination, and what does the schedule look like?

`start-stop-daemon --stop --retry TERM/30/KILL/5 --pidfile ...`: a schedule of signal/wait pairs applied in order — SIGTERM, up to 30 seconds for the process to exit, then SIGKILL, up to 5 more. This matters because K scripts run synchronously inside a `wait` entry of init: any hang in a stop path stalls the whole runlevel transition (and on shutdown, stalls levels 0/6). The schedule makes worst-case stop time a known constant instead of "however long a wedged daemon ignores SIGTERM." Hand-rolled `kill; sleep 5; kill -9` approximates it badly — it neither waits adaptively nor reports.

### Q: Why do Debian init scripts source /etc/default/<name> and /lib/lsb/init-functions, and what breaks if you skip them?

The defaults file separates administrator intent (port, flags, limits) from package-owned code, so package upgrades never clobber local configuration — skip it and every upgrade becomes a merge conflict or a regression. The init-functions library provides `log_daemon_msg`/`log_end_msg`/`log_*_msg`, which honor VERBOSE and render boot-console output correctly — skip it and your messages either vanish from the boot console or appear as unformatted noise, and your script no longer looks or behaves like the rest of the system. Both are conventions, not enforcement — which is exactly why interviewers ask whether you understand *why* they exist rather than that they exist.

### Q: What does a compliant `status` action need to do, and who consumes it?

Print one honest human line ("myapp is running (pid 1234)" or "myapp is not running") and exit per the LSB status contract: 0 running, 1 dead-but-pidfile-exists, 3 not running, 4 unknown. Consumers: `service <name> status` (propagates the exit code), `service --status-all` (renders the summary), monitoring scripts and health checks (read the exit code), and on systemd systems the SysV compatibility layer, which maps init-script state onto generated unit state. A status that always exits 0 or prints nothing breaks every one of those consumers silently — which is why it is the most common real-world init-script defect after missing idempotence.

### Q: Walk through making a hand-written daemonization line safe: `nohup mydaemon &`. What is missing?

Everything that matters. Missing stdin detach (`</dev/null`) — the daemon can block reading a terminal that dies; missing output capture (`>>log 2>&1`) — its stderr, where startup failures appear, goes to a console nobody watches; missing session detachment (`setsid`) — it stays in rc's session and can receive terminal signals; missing identity management — no pidfile, so start/stop/status have nothing to hang correctness on. The corrected form is `start-stop-daemon --start --background [--make-pidfile] ...` or, at minimum, `nohup setsid mydaemon </dev/null >>log 2>&1 &` plus a pidfile written by the daemon. The point of the question is that "it works when I run it" and "it works as a service" differ by exactly these pieces.

## References

- [init-d-script(5) — sysvinit-utils man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-utils/init-d-script.5.en.html) — the declarative interpreter, its variables and override points.
- [invoke-rc.d(8) — init-system-helpers man page, Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/invoke-rc.d.8.en.html) — how the policy layer calls your script.
- [service(8) — init-system-helpers man page, Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/service.8.en.html) — the portable wrapper and its status propagation.
- [insserv(8) — insserv man page, Debian bookworm](https://manpages.debian.org/bookworm/insserv/insserv.8.en.html) — how headers (including yours) get compiled into boot order.
- [LSB Core, Init Script Actions](https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html) — the normative action set and exit-code table.
- `start-stop-daemon(8)` — inline citation only (Debian's s-s-d is a dpkg tool; the OpenRC variant shares the name but differs in flags — do not confuse their man pages).

## Cross-References

- [LSB Init Script Headers and Dependency Metadata](./lsb-headers.md) — the `### BEGIN INIT INFO` block in full depth.
- [rc0.d–rc6.d, rcS.d — Symlink Sequencing Mechanics](./rc-symlinks.md) — how these scripts get sequenced and invoked.
- [SysVinit Service Management Tooling](./tooling.md) — update-rc.d, invoke-rc.d, service, and friends.
- [Custom Init Scripts — Worked Example](./custom-init-scripts.md) — a complete, tested script built end to end.
- [systemd — Service Units](../systemd/service-units.md) — the declarative successor; your header maps almost directly.
- [Daemons](../../../os/processes/daemons.md) — the fork/session/setsid theory behind the daemonization rules.
- [Init Systems Hub](../README.md) — section map and reading order.
