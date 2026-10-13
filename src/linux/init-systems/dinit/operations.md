# dinit in Operation — dinitctl, Boot, and Real Systems

## Overview

Descriptions define services; *operation* is everything that happens around them: the control client, the boot sequence when dinit is PID 1, shutdown, logging, user-mode management, and the debugging loops that real systems demand. This page walks the operational surface of dinit using, as primary sources, the [dinitctl(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinitctl.8.m4), the [dinit(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit.8.m4), the [Getting started guide](https://github.com/davmac314/dinit/blob/master/doc/getting_started.md), and the [Dinit-as-init guide](https://github.com/davmac314/dinit/blob/master/doc/linux/DINIT-AS-INIT.md) from the project repository.

## dinitctl — Verb Reference

`dinitctl` is the only supported way to command a running dinit (besides signals). It connects over the control socket; as root it talks to the system instance by default, otherwise to your user instance, overridable with `-s`/`-u` or `--socket-path`/`-p` (the `DINIT_SOCKET_PATH` environment variable is honored too). General options worth knowing: `--no-wait` (return without waiting for the command to complete), `--quiet`, `--offline`/`-o` (work without a daemon — only valid for enable/disable), and `--use-passed-cfd` (use a pre-passed connection fd from `DINIT_CS_FD` — the counterpart of the `pass-cs-fd` service option).

| Verb | Effect |
|---|---|
| `start` | Start the service; marks it **explicitly activated** (it will not be auto-stopped when its dependents stop). Options: `--no-wait`, `--pin` |
| `stop` | Stop the service and remove explicit activation; refuses (with a warning and no action) if non-soft dependents would also stop, unless `--force`; inhibits automatic restart for it and any dependents stopped alongside |
| `restart` | Stop then start, preserving explicit activation status; `--force` restarts dependents too |
| `wake` | Start the service *without* marking it active — it stops again when its active dependents stop |
| `release` | Remove the explicit activation mark; the service stops if nothing else needs it |
| `status` | Full report: current state (and target state if transitioning), activation, PID, and the reason for an abnormal stop |
| `is-started` / `is-failed` | Scripting predicates; `is-failed` reports stopped due to startup failure, timeout, or dependency failure |
| `list` | List all loaded services with their state indicators (anatomy below) |
| `pin` states | `start --pin` / `stop --pin` / `unpin` — freeze a service against state changes from dependencies or commands; maintenance tooling |
| `add-dep` / `rm-dep` | Add/remove a dependency (`need`, `milestone`, or `waits-for`) between running services at runtime; no cycles allowed |
| `enable` / `disable` | Persistently enable/disable: add/remove a waits-for dependency *and* write/remove the symlink in the target's `waits-for.d` directory; `--from` names the dependent (default: the `@meta enable-via` service, else `boot`) |
| `trigger` / `untrigger` | Set/clear the external trigger of a `triggered` service |
| `setenv` / `unsetenv` | Modify the activation environment; subsequently started/restarted services see the change |
| `catlog` | Dump a service's log buffer (requires `log-type = buffer`); `--clear` empties it after showing |
| `signal` | Send a signal to a service's process (`TERM`, `HUP`, `KILL`, ...; `--list` shows the supported set) |
| `unload` / `reload` | Drop a stopped, dependency-free description from memory / re-read a description in place (with documented limits: type, pid-file, console flags cannot change while running) |
| `shutdown` | Stop all services (no restarts) and terminate dinit; against the system instance this shuts the machine down |

The start/stop semantics encode dinit's activation model. `start` pins the service as active; `release` un-pins it; plain `stop` is a release that also forces a stop. A consequence worth internalizing: the *opposite* of `start` is not `stop` but `release` — `stop` additionally forces the state, and its refusal-without-`--force` protects you from cascading stops (force-stopping `boot` can take down every service and all user sessions).

### Reading `dinitctl list` output

From the README's example:

```text
[[+]     ] boot
[{+}     ] tty1 (pid: 300)
[{+}     ] loginready (has console)
[{+}     ] udevd (pid: 4)
[     {-}] mysql
[   <<{ }] webapp
```

Anatomy: the brackets are the *target* state (square `[+]` = explicitly active; curly `{+}` = running only as a dependency), the inner `+`/`-` is started/stopped, and `<<`/`>>` are transitions (starting/stopping). A service showing `<<` is starting — possibly waiting for its dependencies — and `[   <<{ }]` means "starting, but will stop after starting" (a queued stop). An `X` in place of `-` means the service failed to start or died abnormally; an `s` means a skippable service was skipped. Extra annotations show console ownership, PID, or the exit status/signal that terminated the process.

## The Control Socket

The system instance listens on `/dev/dinitctl` by default (build-time configurable); user instances on `$XDG_RUNTIME_DIR/dinitctl` or `$HOME/.dinitctl` (per the dinit(8) `-p` option documentation). The socket is created at daemon start — or, on a cold boot where the root filesystem is read-only, as soon as a service with the `starts-rwfs` option makes the filesystem writable; the same option also re-creates the socket if it vanished. Dinit refuses to start when an active socket already exists (a non-atomic check, per the man page — do not rely on it as a singleton lock). There is no remote protocol: control is local UNIX-socket only, and regular users are expected to be unable to talk to the system instance — the permission model is the filesystem's. For boot scripts that must talk to dinit before the socket exists (fsck/reboot helpers), the `pass-cs-fd` option passes a socket connection into the service process via `DINIT_CS_FD`.

## Boot: Dinit as PID 1

The [DINIT-AS-INIT guide](https://github.com/davmac314/dinit/blob/master/doc/linux/DINIT-AS-INIT.md) describes the production layout. The kernel starts dinit via `init=/sbin/dinit` (or after a symlink swap of `/sbin/init`); dinit, running as system manager, starts the `boot` service by default. The recommended division of labor: an initramfs handles the earliest work (mount `/proc`, `/sys`, `/dev` (devtmpfs), `/run` as tmpfs, find and mount root read-only, switch root, exec dinit) — a writable `/run` matters because it lets the control socket exist from the first moment, which is exactly what makes boot *recovery* possible.

The example service set in the repository's `doc/linux/services` directory (explained service-by-service in the guide) boots like this:

1. `early-filesystems` — mounts sysfs, devtmpfs, procfs (scripted; no dependencies, so among the first).
2. `udevd` — device node manager (eudev; supports dinit-compatible readiness notification since 3.2.15), then `udev-trigger` and `udev-settle` (scripted).
3. `hwclock` — sets system time from the RTC (depends on udevd for the device node).
4. `modules` — loads modules from `/etc/modules` (depends on early-filesystems).
5. `rootfscheck` — fsck the root filesystem, on-console, interruptible, skippable, no start timeout.
6. `rootrw` — remount root read-write; carries the `starts-rwfs` option, so this is the moment dinit creates its control socket and logs the boot to wtmp.
7. `auxfscheck` → `filesystems` — check and mount auxiliary filesystems.
8. `rcboot` — cleanup of `/tmp`, `/var/run`, `/var/lock`, random seeding (seedrng), loopback up, hostname (scripted; its stop action re-seeds entropy at shutdown).
9. After `rcboot`, the system is functional: `syslogd` (with `starts-log`, so dinit's own buffered output flows into syslog), `dbusd`, `dhcpcd`, `sshd`.
10. `loginready` — internal consolidation point (depends on `rcboot`, `dbusd`, `udevd`, `syslogd`; runs-on-console to quiet the console once logins are possible).
11. `tty1`–`tty6` — getty services, each depending on `loginready`.

The guide's dependency-writing advice is worth quoting as doctrine: any service needing a writable filesystem, pseudo-filesystems, syslog, dbus, or the network must depend (directly or transitively) on the service providing it — missing dependencies cause *sporadic* failures because parallel startup sometimes wins the race. Wrap the common prerequisites in one internal service and depend on that; prefer `depends-on` over `waits-for`/`after` for real requirements.

### Single-user mode and recovery

Two special descriptions complete the picture. `single` runs a maintenance shell; an unprivileged user cannot start it — it is reached by putting `single` on the kernel command line, which dinit (as PID 1, per the COMMAND LINE FROM KERNEL section) interprets as the name of the service to start. When the shell exits, `chain-to = boot` resumes normal startup. `recovery` (root-password-gated shell) is what dinit offers when boot appears to fail — that is, when all services stop without a shutdown command; the console prompt offers restart or recovery, and `--auto-recovery` (`-r`) selects recovery automatically for headless machines. If boot instead *hangs* (services neither stopping nor finishing), the timeouts in the descriptions (`start-timeout`, `stop-timeout`) are the mechanism that converts hangs into failures you can see.

### Shutdown

`dinitctl shutdown` against the system instance stops all services — in reverse dependency order, with restarts suppressed — and then dinit, as system manager, executes the external shutdown program (the `-m` system-mgr behavior). Scripted shutdown tasks are ordinary services with `kill-all-on-stop`: the option makes dinit TERM-then-KILL every other process on the system before running the script, so unmounting cannot fail from stragglers holding files open (the man page's own warning: with that broadcast active, keep strict ordering — every service should be a dependency or dependent of the kill-all service). The signal fallbacks from PID 1: SIGINT reboots (ctrl-alt-del), SIGTERM halts, SIGQUIT performs an immediate shutdown with no service rollback.

## Logging in Operation

Dinit itself logs through two channels simultaneously: the console (standard output) and the main log facility (syslog by default, or a file via `-l path`; `--console-level` and `--log-level` set per-channel minimums from `debug`/`notice`/`warn`/`error`, with `none` silencing a channel — service state-change messages survive even `none` unless `--quiet` was used). Two service options tie the daemon's logging into the system's: `starts-log` marks the service that brings up the system logger (dinit flushes its buffer through `/dev/log` from that point), and `starts-rwfs` marks the service that makes the filesystem writable (control socket + wtmp boot record). Early-boot services that must log before the root filesystem is writable are advised (in the DINIT-AS-INIT caveats) to log under `/run`, use `shares-console`, or use `log-type = buffer` — `dinitctl catlog` then reads the ring buffer over the control socket.

For *service* output, `log-type = pipe` plus a logger service (`consumer-of = logger`) reproduces the supervision-suite pattern: the logger is itself a process service, supervised, restartable, and the only component that needs to know about log rotation. This keeps dinit's own footprint minimal — there is no built-in rotation — which is why Chimera pairs dinit with a dedicated logging daemon for this role (see [chimera-linux.org](https://chimera-linux.org/); the project is separate from dinit proper).

## User-Mode Manager

The [Getting started guide](https://github.com/davmac314/dinit/blob/master/doc/getting_started.md) is a complete user-mode walkthrough, condensed here:

```sh
mkdir -p ~/.config/dinit.d/boot.d
cat > ~/.config/dinit.d/boot <<'EOF'
type = internal
waits-for.d: boot.d
EOF
cat > ~/.config/dinit.d/mpd <<'EOF'
type = process
command = /usr/bin/mpd --no-daemon
restart = true
EOF
dinit -q &                # user instance; default socket $XDG_RUNTIME_DIR/dinitctl
dinitctl start mpd        # explicitly activate and start
dinitctl enable mpd       # start now AND persist: symlink written into boot.d/
dinitctl list
```

Three lessons from the guide: (1) dinit always starts `boot` unless told otherwise, so the internal `boot` profile with a `boot.d` directory is the user-mode equivalent of the system layout; (2) `enable` both starts the service and creates the symlink in `waits-for.d` — the persisted form of activation, surviving restarts of the user manager; (3) `kill -9`-ing a service shows the `[STOPPD]`/`[ OK ]` pair in dinit's output — the crash and the supervised recovery, visible in two lines. User services see the login session's environment plus anything set with `dinitctl setenv`, which is how session information (DISPLAY, SSH_AUTH_SOCK) reaches them.

## Debugging Recipes

- **Service won't start.** `dinitctl status <svc>` gives state plus *why* it stopped (the status subcommand reports the reason for any non-normal stop). Check the type and command first (a `process` service whose binary is missing fails immediately), then dependencies — a service waiting on a dependency shows as transitioning in `dinitctl list`. `dinit-check` statically validates descriptions before you reboot into them.
- **Service starts but dependents misbehave.** The classic dinit trap, straight from the DINIT-AS-INIT guide: a missing dependency can work "by luck" on some boots (parallelism wins the race) and fail on others. Declare the dependency; do not replace it with sleeps.
- **Never reaches STARTED.** Almost always a readiness-notification mismatch (process service with `ready-notification` but a daemon that never writes the fd) — it waits the full `start-timeout`, then SIGINT/stopping. Audit the notification setting against the daemon's actual capabilities.
- **Service fails at start with a log path error.** `logfile` semantics: the *directory* must exist and be writable when the service starts, or the service fails to start. Early-boot services must depend on the service that makes the filesystem writable (or log to `/run` / buffer).
- **Stop cascades further than expected.** Read the brackets in `dinitctl list`: stopping a service stops its dependents. `dinitctl stop --force` bypasses the refusal — prefer stopping dependents individually first; the man page's warning about force-stopping `boot` ending user sessions is not rhetorical.
- **Runtime graph changes.** `add-dep`/`rm-dep` let you rewire dependencies live (no cycles), and `setenv` injects environment for subsequently started services — useful for maintenance without editing files.

## How dinit Maps to systemctl

| systemd world | dinit world |
|---|---|
| `systemctl start/stop/restart <unit>` | `dinitctl start/stop/restart <service>` |
| `systemctl status` | `dinitctl status <service>` / `dinitctl list` |
| `systemctl enable/disable` (symlinks in target `.wants/` dirs) | `dinitctl enable/disable` (symlinks in `waits-for.d`) |
| Targets (`.target` units) | `internal` services (e.g., `boot`, `loginready`) |
| `Type=notify` (sd_notify) | `ready-notification = pipefd:N` / `pipevar:NAME` |
| `Restart=always` + `StartLimitBurst` | `restart = yes` + `restart-limit-count`/`restart-limit-interval` |
| Unit directories (`/etc/systemd/system`, `/usr/lib/systemd/system`) | `/etc/dinit.d`, `/usr/lib/dinit.d`, `/lib/dinit.d`, `/run/dinit.d` (search order) |
| `systemctl --user` + logind sessions | `dinit -u` with `$XDG_CONFIG_HOME/dinit.d` |
| `systemctl isolate rescue.target` | boot with `single` on the kernel command line; `recovery` service |
| `systemctl set-environment` | `dinitctl setenv` / `unsetenv` |

The structural similarity is the point — dinit is the closest small-system analog to systemd's core model — and the deltas (no journal, no socket activation, no timers, no D-Bus API) are exactly the features [dinit — A Modern Dependency-Aware Init](./overview.md) enumerates as out of scope.

## Interview Questions

### Q: What does `dinitctl stop` do that `dinitctl release` does not, and why does the distinction exist?

`stop` removes the explicit activation *and forces the service to stop* (refusing without `--force` if that would cascade into dependents, and suppressing automatic restarts for everything it stops). `release` only clears the activation mark — the service stops *if and only if* nothing else needs it. The distinction exists because dinit tracks two orthogonal facts: whether a service is running and whether anyone wants it running. `start` sets both; `release` un-sets the want; `stop` un-sets both forcibly. Maintenance workflows use `release` to let dependency-driven state reclaim memory cleanly, and `stop` when you truly want the process gone.

### Q: Walk through the boot-failure path: an essential service with a hard dependency on `boot` fails to start.

If the failing service is (transitively) a hard dependency of `boot`, `boot` fails, and as services stop without a shutdown command dinit recognizes an apparent boot failure. As system manager it prompts on the console with recovery options — prominently starting the `recovery` service (a root-password shell in the example set) or restarting the machine; `--auto-recovery` takes the prompt away for headless systems. The design requirement from DINIT-AS-INIT is that essential services hang off `boot` via `depends-on`/`depends-ms` so their failure *propagates* into this state machine instead of leaving a half-booted system that looks alive.

### Q: Why is a writable `/run` in the initramfs considered so important for dinit systems?

Because the control socket lives there, and every recovery and inspection path runs through it. With `/run` mounted as tmpfs before root is writable, dinit creates `/dev/dinitctl`-class control immediately: `dinitctl` works from the earliest moment for diagnostics, and boot-critical scripts can use `pass-cs-fd` to command dinit (e.g., to reboot after a failed fsck) even while the root filesystem is still read-only. The `starts-rwfs` option is the fallback that creates the socket later — but the DINIT-AS-INIT guide treats that as the degraded case, not the design target.

### Q: How does `dinitctl enable` differ from editing `waits-for.d` by hand, and what does `@meta enable-via` contribute?

They converge on the same artifact — a symlink in the service's profile directory — but `enable` does it atomically against a running daemon: it adds the runtime waits-for dependency (starting the dependency immediately if the dependent is running, without explicit activation), then writes the symlink so the relationship persists across sessions. By default the dependency attaches to `boot`; `@meta enable-via <service>` in the description redirects that default (e.g., attaching a `dbus` session service to a `session` profile instead), and `enable --from <svc>` overrides at the command line. `disable` is the exact complement, with the caveat that "disabled" only severs that one dependency — the service may still start as someone else's dependency.

### Q: You inherit a dinit box where a service is `[   <<{ }]` and has been for minutes. What does the display mean and what do you check?

The brackets decode as: starting (`<<`), target state stopped (`{ }`) — the service is in its startup path but a stop is already queued, so it will stop the moment it finishes starting (or it is wedged mid-start). First check `dinitctl status` for the reason field and the PID; then `dinitctl list` for its dependencies' states — a dependency stuck starting (frequently another ready-notification mismatch or a start-timeout about to fire) is the usual cause. If it is genuinely hung, the description's `start-timeout` will eventually SIGINT it; if the timeout is 0 (unlimited), that is the configuration bug to fix.

## References

- [dinitctl(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinitctl.8.m4) — PRIMARY: verbs, options, pin semantics, list indicators
- [dinit(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit.8.m4) — daemon options, socket paths, activation model, signals, kernel command line
- [Dinit as init (Linux)](https://github.com/davmac314/dinit/blob/master/doc/linux/DINIT-AS-INIT.md) — PID-1 boot layout, example services, dependency doctrine, caveats
- [Getting started with dinit](https://github.com/davmac314/dinit/blob/master/doc/getting_started.md) — user-mode walkthrough behind this page's examples
- [dinit README](https://github.com/davmac314/dinit/blob/master/README.md) — control examples, list output anatomy
- [dinit-service(5) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit-service.5.m4) — the description options referenced throughout
- [dinit GitHub repository](https://github.com/davmac314/dinit) — source, doc tree, [wiki](https://github.com/davmac314/dinit/wiki)
- [Chimera Linux](https://chimera-linux.org/) — production system built on dinit
- [Artix Linux](https://artixlinux.org/) — dinit as an init option

## Cross-References

- [dinit — A Modern Dependency-Aware Init](./overview.md) — architecture and feature inventory this page operates.
- [dinit Service Descriptions (dinit-service(5))](./service-descriptions.md) — the grammar being loaded, enabled, and debugged.
- [systemd — systemctl CLI](../systemd/systemctl-cli.md) — the mapped verbs in their native habitat.
- [runit — sv, svlogd, chpst](../runit/sv-logging.md) — the control-CLI contrast: policy-driven vs supervision-only.
- [Init systems — comparison](../comparison.md) — where dinit lands across the families.
- [init-systems README](../README.md) — section hub.
