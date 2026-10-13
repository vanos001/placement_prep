# Writing a Production init.d Script (End-to-End)

## Overview

Most documentation about init scripts shows a fragment — a header here, a `start-stop-daemon` line there. This page builds one complete, defensible service the way you would ship it: a daemon called `myapp`, packaged with a defaults file, a full `/etc/init.d/myapp` with every decision annotated, registration and verification commands, the declarative `init-d-script` alternative for comparison, a catalog of the bugs that actually bite, and a boot-time debugging playbook. The conventions layer (exit codes, idempotence, `start-stop-daemon` mechanics) is already covered field-by-field in [init-scripts.md](./init-scripts.md); here the goal is the whole artifact and the judgment calls inside it.

The worked example is deliberately a *forking background daemon* rather than a foreground process, because that is the hard case: process identity must be established and re-verified, startup readiness must be polled rather than assumed, and shutdown must be graceful-then-forced on a deadline. Every mechanism shown — `--background --make-pidfile`, the wait-for-ready loop, `--retry TERM/20/KILL/5`, the `/proc` cmdline status check — exists to make one of those three phases deterministic.

The page closes with a porting map to systemd, because a well-built init script is a transitory investment: each design decision (user, environment file, reload signal, stop schedule) has a direct systemd counterpart, and knowing the mapping turns "migrate my service" from a rewrite into a translation exercise.

## The Service We Are Shipping

Requirements for `myapp`, chosen so each line of the script has a reason:

- Binary `/usr/bin/myapp`, config `/etc/myapp/myapp.conf`, runs unprivileged as user `myapp`.
- Needs the network up and syslog running (hard dependencies); benefits from DNS and time sync (soft dependencies).
- Does **not** double-fork when started — it runs in the foreground until signaled, so the init script must background it. (This precondition matters; the annotations show what changes if it is false.)
- Understands `SIGHUP` as "reload configuration".
- Writes its own diagnostics to stderr; the script redirects them to `/var/log/myapp.log`.
- Should start in runlevels 2–5 and stop in 0, 1, and 6.

## /etc/default/myapp — Administrator Overrides

The defaults file separates operator intent from package-owned code. Package upgrades overwrite `/etc/init.d/myapp`; they never touch `/etc/default/myapp`:

```sh
# /etc/default/myapp - administrator overrides for the myapp service.
# All variables are optional; unset values fall back to the init script's.

DAEMON_ARGS="--config /etc/myapp/myapp.conf --workers 4"
DAEMON_USER=myapp
LOGFILE=/var/log/myapp.log
READY_TIMEOUT=30
# HEALTHCHECK="/usr/local/bin/myapp-health --url http://127.0.0.1:8080/ready"
```

Sourcing it is conditional (`[ -r ... ] && . ...`) so the service boots even if an admin deletes the file — a small habit that prevents a whole class of "missing defaults file breaks boot" incidents.

## The Complete /etc/init.d/myapp

The script below is POSIX `sh`, LSB-header compliant, idempotent, locked, readiness-polling, and graceful on stop. Annotations follow immediately after; the structural contract (why these actions, why these exit codes) is in [init-scripts.md](./init-scripts.md):

```sh
#!/bin/sh
### BEGIN INIT INFO
# Provides:          myapp
# Required-Start:    $remote_fs $network $syslog
# Required-Stop:     $remote_fs $network $syslog
# Should-Start:      $named $time
# Should-Stop:       $named $time
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Production example application daemon
# Description:       Manage the myapp application daemon, the reference
#                    service built end to end on the custom-init-scripts page.
### END INIT INFO

PATH=/sbin:/usr/sbin:/bin:/usr/bin
DESC="myapp application daemon"
NAME=myapp
DAEMON=/usr/bin/myapp
DAEMON_ARGS="--config /etc/myapp/myapp.conf"
PIDFILE=/run/myapp.pid
DAEMON_USER=myapp
LOGFILE=/var/log/myapp.log
HEALTHCHECK="/usr/bin/myapp --health-check"
READY_TIMEOUT=30

[ -x "$DAEMON" ] || exit 5

# Administrator overrides (arguments, user, timeout, log destination).
[ -r /etc/default/myapp ] && . /etc/default/myapp

. /lib/lsb/init-functions

# Serialize concurrent invocations (rc batch, admin, invoke-rc.d).
exec 9>/run/lock/myapp.init.lock
flock -n 9 || { logger -t myapp "init script already active"; exit 0; }

is_running() {
    [ -s "$PIDFILE" ] || return 1
    pid=$(cat "$PIDFILE" 2>/dev/null)
    [ -n "$pid" ] && [ -d "/proc/$pid" ] \
        && tr '\0' ' ' < "/proc/$pid/cmdline" | grep -q "$NAME"
}

wait_ready() {
    i=0
    while [ "$i" -lt "$READY_TIMEOUT" ]; do
        is_running || return 1          # daemon died while starting: fail fast
        $HEALTHCHECK >/dev/null 2>&1 && return 0   # unquoted: word splitting intended
        sleep 1
        i=$((i + 1))
    done
    return 1
}

do_start() {
    is_running && return 0              # idempotent no-op is a success
    start-stop-daemon --start --quiet --background --make-pidfile \
        --pidfile "$PIDFILE" --chuid "$DAEMON_USER" --startas "$DAEMON" \
        -- $DAEMON_ARGS >>"$LOGFILE" 2>&1 || return 1
    wait_ready
}

do_stop() {
    is_running || { rm -f "$PIDFILE"; return 0; }   # stale pidfile: clean up
    start-stop-daemon --stop --quiet --oknodo --retry TERM/20/KILL/5 \
        --remove-pidfile --pidfile "$PIDFILE"
}

case "$1" in
  start)
    log_daemon_msg "Starting $DESC" "$NAME"
    do_start
    log_end_msg $?
    ;;
  stop)
    log_daemon_msg "Stopping $DESC" "$NAME"
    do_stop
    log_end_msg $?
    ;;
  restart)
    $0 stop || true
    $0 start
    ;;
  reload|force-reload)
    if is_running; then
        log_daemon_msg "Reloading $DESC" "$NAME"
        kill -HUP "$(cat "$PIDFILE")"
        log_end_msg 0
    else
        log_warning_msg "$NAME is not running - restarting instead"
        $0 restart
    fi
    ;;
  status)
    pid=$(pidof "$NAME" 2>/dev/null | cut -d' ' -f1)
    if [ -n "$pid" ] \
       && tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null | grep -q "$NAME"; then
        echo "$NAME is running (pid $pid)"
        exit 0
    fi
    echo "$NAME is not running"
    exit 3
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|reload|force-reload|status}" >&2
    exit 2
    ;;
esac

exit 0
```

## Decision-by-Decision Annotations

### Why --background and --make-pidfile

`--background` makes `start-stop-daemon` fork the daemon and return immediately, because a script that blocks on a foreground child stalls the rc walk — at boot, with parallel batches waiting, that is the cardinal sin. `--make-pidfile` tells s-s-d to record the backgrounded child's PID in `$PIDFILE`, giving start/stop/status an identity to work with. This pair is correct **only because `myapp` does not double-fork**: the PID s-s-d records is the first child it spawned, and if the daemon re-forked into a grandchild, that PID would be a dead end. If your daemon double-forks and writes its own pidfile, drop `--make-pidfile` and point `--pidfile` at the daemon's file; if it double-forks and writes nothing, you need a supervisor, not cleverness. Exactly one party may own the process identity.

### Why --chuid instead of su or sudo

`--chuid` performs setuid/setgid and execs the daemon in a single step: no intermediate shell, no PAM session overhead, no signal ambiguity about whether TERM went to the shell or the daemon. `su -c`/`sudo` insert a shell process into the identity chain — the pidfile then risks recording the shell, signals have two hops to traverse, and the environment diverges from boot context. Related rule: the daemon user must be able to create files in the pidfile's directory (here `/run`, root-owned but world-writable with sticky bit) and write the log — the script drops privileges *before* the daemon can fix anything itself.

### Why --startas and the /proc cmdline checks

`--startas` executes the binary without s-s-d's exec-path matching on the "already running" check; this script does its own, more precise verification instead. `is_running()` does not trust the pidfile: it requires the file to be non-empty, the PID to exist in `/proc`, *and* the recorded process's cmdline to actually contain `myapp`. That last test is what prevents the classic PID-reuse disaster — a stale pidfile whose number was recycled to an unrelated process — from ever turning into a wrong kill or a false "running" report. The `status` action applies the same idea from the other direction: `pidof` provides the live PID, and the `/proc/$pid/cmdline` grep confirms identity before claiming the service is up. Two independent probes (our pidfile, the system's view) that must agree is the difference between an honest status and a guessed one.

### The wait-for-ready loop

`start-stop-daemon` returning does not mean the service works; it means a process exists. `wait_ready` polls, once per second and bounded by `READY_TIMEOUT`, that (a) the daemon is still alive and (b) the health probe passes — a real readiness check (an HTTP ping, a port probe), not merely "the process has not exited yet". Failing fast when the daemon dies mid-startup converts a 30-second silent boot hang into an immediate logged failure. The bounded loop also protects the boot itself: a service that never becomes ready delays rc by at most `READY_TIMEOUT` seconds instead of forever.

### Log redirection and the flock guard

The `>>"$LOGFILE" 2>&1` on the s-s-d line captures both output streams — daemon stderr is where startup failures announce themselves, and without redirection they vanish into the boot console. The `flock` guard on descriptor 9 serializes whole invocations: rc's batch, an admin's shell, and `invoke-rc.d` from a package postinst can otherwise interleave, and under parallel boot (see [parallel-booting.md](./parallel-booting.md)) "invoked twice within a second" is normal life, not an anomaly. The guard exits 0 when another invocation holds the lock — the second caller's work is either already done or in progress, and erroring would produce a spurious failure.

## Registration and Verification

### update-rc.d and the resulting links

Registering creates the rc?.d symlink sets; `defaults` means start in 2–5, stop in 0/1/6, per the header's `Default-Start`/`Default-Stop` (see [update-rc.d(8)](https://manpages.debian.org/bookworm/init-system-helpers/update-rc.d.8.en.html)):

```console
$ sudo update-rc.d myapp defaults
$ ls -l /etc/rc{0,1,2,6}.d/ | grep myapp
/etc/rc0.d/:
lrwxrwxrwx 1 root root 15 Jul 12 08:40 K01myapp -> ../init.d/myapp
/etc/rc1.d/:
lrwxrwxrwx 1 root root 15 Jul 12 08:40 K01myapp -> ../init.d/myapp
/etc/rc2.d/:
lrwxrwxrwx 1 root root 15 Jul 12 08:40 S01myapp -> ../init.d/myapp
/etc/rc6.d/:
lrwxrwxrwx 1 root root 15 Jul 12 08:40 K01myapp -> ../init.d/myapp
```

On systems running insserv's dependency-based boot (see [parallel-booting.md](./parallel-booting.md)), `update-rc.d` delegates to insserv, which also recomputes the `.depend.*` graph from your fresh header and assigns meaningful sequence numbers; on modern Debian without it, numbers collapse to a conservative `01` and ordering falls to lexical order or to whatever init consumes the header metadata. Either way, `update-rc.d -n myapp defaults` is the safe preview, and `insserv -n` dry-runs the header against the dependency graph before it is installed for real.

### Syntax and header checks

Before any reboot test: `sh -n /etc/init.d/myapp` parses without executing; `shellcheck` (if installed) catches quoting and word-splitting bugs that `-n` cannot; `insserv -n` validates that the header parses and introduces no cycles. Run all three from packaging CI — they are the cheap 90% of init-script regression testing.

### Chroot boot simulation with policy-rc.d

Package builds and container images install services into chroots where nothing should actually start. The policy layer does this: `invoke-rc.d` (the tool dpkg postinsts call) consults `/usr/sbin/policy-rc.d` before invoking any script, and its exit code decides the action ([invoke-rc.d(8)](https://manpages.debian.org/bookworm/init-system-helpers/invoke-rc.d.8.en.html)):

```console
# Inside a build chroot: deny all service starts during package configuration.
chroot /srv/build-chroot sh -c \
  'printf "#!/bin/sh\nexit 101\n" > /usr/sbin/policy-rc.d; chmod +x /usr/sbin/policy-rc.d'
# Exit 101 tells invoke-rc.d to deny the action; services get registered, not started.
```

`invoke-rc.d --query myapp start` asks the same policy layer what it *would* decide without executing anything — useful both in chroots and for verifying your own script's registration.

### The real boot test

No simulation replaces rebooting. Boot a VM twice and read `bootlogd`'s record in `/var/log/boot`: the `log_daemon_msg`/`log_end_msg` lines must appear (proof the init-functions plumbing works on the console), the service must start without blocking the batch, and ordering relative to `$network`/`$syslog` must hold. Roughly half of all init-script bugs reproduce only in boot context — different PATH, no controlling terminal, parallel siblings — which is why the reboot rows in the test matrix ([init-scripts.md](./init-scripts.md)) are non-negotiable.

## The init-d-script Alternative

For the common "one daemon, one pidfile" shape, `sysvinit-utils` ships `/lib/init/init-d-script`, an interpreter documented in [init-d-script(5)](https://manpages.debian.org/bookworm/sysvinit-utils/init-d-script.5.en.html) that expands a variable-driven script into a fully compliant one — the same service in roughly 25 lines:

```sh
#!/lib/init/init-d-script
### BEGIN INIT INFO
# Provides:          myapp
# Required-Start:    $remote_fs $network $syslog
# Should-Start:      $named $time
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: myapp via the init-d-script interpreter
### END INIT INFO
DAEMON=/usr/bin/myapp
NAME=myapp
PIDFILE=/run/myapp.pid
DAEMON_ARGS="--config /etc/myapp/myapp.conf"

do_start_cmd_override() {
    start-stop-daemon --start --quiet --background --make-pidfile \
        --pidfile "$PIDFILE" --chuid myapp --startas "$DAEMON" \
        -- $DAEMON_ARGS >>/var/log/myapp.log 2>&1
}
```

The interpreter supplies `start`/`stop`/`restart`/`status` with correct LSB exit codes, sources the defaults file and `/lib/lsb/init-functions`, and honors overrides: `do_start_cmd_override` replaces only the start command while inherited stop/status/restart logic stays. The tradeoffs are the mirror of the long form: far less code to get wrong and consistent behavior for free, but less control — custom readiness polling, exotic verbs, and multi-process logic must be forced through the override functions, and the interpreter's exact defaults have drifted slightly between sysvinit releases. Rule of thumb: start with `init-d-script`; escalate to the full script when the first override function starts contorting.

## Common Bugs Catalog

Each row is a real production incident pattern, with the symptom that surfaces and the fix:

| Bug | Symptom | Fix |
|---|---|---|
| Stale pidfile double-start | second `start` spawns a duplicate daemon, or `stop` kills an innocent recycled PID | `/proc/$pid/cmdline` identity check before trusting the pidfile; `rm -f` stale file; flock guard |
| reload/restart confusion | config change "reloaded" by killing and restarting; dropped connections; or `reload` silently does nothing on a daemon without HUP semantics | implement `reload` as a real signal path, `force-reload` as reload-else-restart, exit 3 for unsupported reload |
| Wrong exit codes breaking invoke-rc.d chains | dpkg configure step fails because `stop` exited 7 on an already-stopped service | exit 0 on idempotent no-ops; LSB codes everywhere; `status` exits 0/3 |
| Missing `$remote_fs` | boots break when `/usr` is a separate filesystem — script runs before its binary exists | `$remote_fs` in Required-Start whenever anything under `/usr` is used |
| Minimal boot PATH | works from admin shell, fails at boot: `/usr/local/bin` not on rc's PATH | set `PATH=/sbin:/usr/sbin:/bin:/usr/bin` explicitly; use absolute daemon paths |
| Locale assumptions | parsing `date`/`sort` output breaks under the boot locale | `LC_ALL=C` around parsing; never parse localized output |
| No pidfile on forking daemon | `stop` and `status` are blind; s-s-d falls back to name scanning with weak matching | let the daemon write its pidfile and point `--pidfile` at it; `Type`-style identity is not optional |
| Foreground start stalls boot | rc hangs on this script until timeout; parallel batches wait | `--background` (or the daemon's own daemonization); never block the rc walk |

## Debugging at Boot

Boot context differs from shell context in PATH, environment, console state, and concurrency — so debug there deliberately:

- **Trace the script**: `sh -x /etc/init.d/myapp start` from a shell shows variable expansion and each command; for the boot itself, temporarily add `set -x` near the top and read the trace via `bootlogd` in `/var/log/boot` (remove it afterwards).
- **Ask the policy layer**: `invoke-rc.d --query myapp start` reveals whether the registration/policy stack would allow and invoke the script — isolating "script is broken" from "script is never called".
- **Read the boot log**: `/var/log/boot` shows what actually ran, in what order, with what output — the ground truth that a successful interactive test cannot provide.
- **Test the K path explicitly**: the K01myapp stop link only executes on a runlevel *transition*, never via `service myapp restart`. Exercise it with `telinit 1` (watch the stop fire in `/var/log/boot`), then `telinit 2` to come back. A green `restart` proves nothing about shutdown ordering; only a transition does. Shutdown itself (`telinit 0`/`6`) is the same mechanism at runlevels 0/6, as covered in [shutdown-halt.md](./shutdown-halt.md).

## Porting Map: init.d Script to systemd Unit

Every decision in the worked example has a systemd counterpart — the migration is a translation, not a rewrite (unit syntax in [systemd — Service Units](../systemd/service-units.md), migration strategy in [migration-modern.md](./migration-modern.md)):

| init.d mechanism | systemd counterpart |
|---|---|
| `Required-Start`/`Should-Start` header fields | `After=`/`Wants=` (order + preference) or `Requires=` (hard) |
| `--background --make-pidfile` | gone: `Type=exec`/`simple` — systemd supervises the foreground process, no pidfile needed |
| Daemon's own pidfile (double-forking case) | `Type=forking` + `PIDFile=` |
| `--chuid "$DAEMON_USER"` | `User=`/`Group=` |
| `--retry TERM/20/KILL/5` | `KillSignal=SIGTERM`, `TimeoutStopSec=25`, `KillMode=mixed` |
| `/etc/default/myapp` sourcing | `EnvironmentFile=/etc/default/myapp` (same file, reused as-is) |
| `kill -HUP` reload | `ExecReload=/bin/kill -HUP $MAINPID` |
| `>>"$LOGFILE" 2>&1` | journal by default (`StandardOutput=journal`); log rotation handled for you |
| pidfile-based `status` | unit state itself (`systemctl is-active`) |
| `update-rc.d` symlinks | `systemctl enable` + presets |
| flock double-start guard | unnecessary — systemd never starts the unit twice |

The structural win of the port: process identity, readiness (`Type=` semantics with `sd_notify`), and supervision move from your shell code into the init system, which is why the `wait_ready` loop, the pidfile checks, and the flock guard all disappear rather than translate.

## Interview Questions

### Q: Why --background together with --make-pidfile, and when is that pair wrong?

`--background` exists because an init script must never block the rc walk on a foreground child; `--make-pidfile` records the PID of the child s-s-d spawned so start/stop/status have an identity to operate on. The pair is wrong exactly when the daemon double-forks: s-s-d records the first child, but the surviving daemon is a grandchild, so the pidfile points at a dead PID and stop/status quietly break. Correct responses, in order of preference: let a double-forking daemon write its own pidfile and point `--pidfile` at it; use `--background --make-pidfile` only for daemons that stay in the foreground; and if the daemon both double-forks and writes nothing, add a real supervisor rather than hacking around it. The invariant: exactly one party owns process identity.

### Q: Why --chuid rather than su -c or sudo, and what operational detail does it force you to handle?

`--chuid` does setuid/setgid plus exec in one step — no intermediate shell in the process chain, no PAM session overhead, no ambiguity about which process a signal or pidfile refers to, and a predictable boot-like environment. `su -c`/`sudo` insert a shell whose exit, signals, and environment all differ from the daemon's, which is how "works under su, dies at boot" bugs are born. The forced detail: privileges drop before the daemon runs, so the daemon user needs write access to whatever it must touch from birth — the pidfile directory and log path — rather than being able to chown them into shape afterwards.

### Q: What does the /proc cmdline check in is_running and status actually prevent?

PID reuse. A pidfile is a claim, not a fact: if the daemon died and the kernel recycled its PID to an unrelated process, a naive `[ -d /proc/$pid ]` (or worse, `kill $pid`) reports a healthy service or kills a bystander. Checking that the recorded PID's cmdline actually contains the expected program name converts "some process has this number" into "this process is our daemon" — in `is_running` before a stop, and in `status` (via the independent `pidof` probe) before reporting up. It is also why the catalog lists stale-pidfile handling as its first row: unrecovered stale pidfiles are the most common real-world init-script defect after missing idempotence.

### Q: Why must the stop path use a bounded --retry schedule, and what does TERM/20/KILL/5 mean concretely?

K scripts run synchronously inside rc's runlevel transition, and on shutdown that transition is on the way to poweroff — any unbounded wait in a stop path stalls the entire boot or shutdown. `--retry TERM/20/KILL/5` is a schedule of signal/wait pairs: send SIGTERM, wait up to 20 seconds for exit, then SIGKILL, wait up to 5 more. It turns "however long a wedged daemon ignores TERM" into a known worst-case constant, and `--oknodo` keeps the already-stopped case a success (exit 0). Hand-rolled `kill; sleep 5; kill -9` approximates the schedule but neither waits adaptively for exit nor reports — which is why the s-s-d form is the standard.

### Q: What does /usr/sbin/policy-rc.d do, and why does every chroot build need one?

It is the policy hook that `invoke-rc.d` consults before invoking any init script: the hook's exit code allows or denies the action. In a chroot (package build, container image), packages configure themselves and their postinsts try to start services that cannot possibly run there; a policy-rc.d that exits 101 denies those starts while leaving the scripts properly registered. The same hook answers "would this service start?" via `invoke-rc.d --query`, which makes it both a build-hygiene tool and a registration debugger. Without it, chroot builds either spew boot-attempt errors or, worse, actually spawn daemons inside the build environment.

### Q: If you ported this exact service to systemd, what translates, and what disappears entirely?

Translates nearly one-to-one: Required/Should-Start to `After=`/`Wants=`, `--chuid` to `User=`, `/etc/default/myapp` to `EnvironmentFile=` (reused verbatim), the TERM-then-KILL schedule to `KillSignal=`/`TimeoutStopSec=`, the HUP reload to `ExecReload=/bin/kill -HUP $MAINPID`. Disappears rather than translates: the pidfile and all its checks (systemd supervises the real process and knows its identity), the `--background` fork (systemd wants the foreground process), the wait-ready poll (readiness becomes `Type=` semantics or an `sd_notify` callback), and the flock guard (units cannot be double-started). The pattern to internalize: everything in the script that existed to manage *process identity and lifecycle* is the systemd init system's job now; what remains is only the service's actual configuration.

## References

- [init-d-script(5) — sysvinit-utils man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-utils/init-d-script.5.en.html) — the declarative interpreter: variables, override functions, and defaults.
- [invoke-rc.d(8) — init-system-helpers man page, Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/invoke-rc.d.8.en.html) — the policy layer: `policy-rc.d` semantics, `--query`, and denial codes.
- [update-rc.d(8) — init-system-helpers man page, Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/update-rc.d.8.en.html) — registration: `defaults`, explicit sequence numbers, dry-run mode.
- [service(8) — init-system-helpers man page, Debian bookworm](https://manpages.debian.org/bookworm/init-system-helpers/service.8.en.html) — the portable front end your script's `status` contract serves.
- [LSB Core — Init Script Actions](https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html) — the normative action set and exit-code table the script implements.
- [Debian Policy Manual — Operating System Files](https://www.debian.org/doc/debian-policy/ch-opersys.html) — the distribution-level rules for init scripts, defaults files, and registration.

## Cross-References

- [/etc/init.d Scripts — Conventions and Patterns](./init-scripts.md) — the contract layer: exit codes, s-s-d options, idempotence patterns.
- [LSB Init Script Headers and Dependency Metadata](./lsb-headers.md) — the header block this script depends on, field by field.
- [rc0.d–rc6.d, rcS.d — Symlink Sequencing Mechanics](./rc-symlinks.md) — what registration actually creates and how rc consumes it.
- [SysVinit Service Management Tooling](./tooling.md) — update-rc.d, invoke-rc.d, and service in daily use.
- [From sysvinit to systemd — Migration Paths](./migration-modern.md) — where this service goes when the distro moves on.
- [systemd — Service Units](../systemd/service-units.md) — the declarative target of the porting map.
- [Init Systems Hub](../README.md) — section map and reading order.
- [Init System Comparison](../comparison.md) — where this script's lifecycle responsibilities land in each init system.
