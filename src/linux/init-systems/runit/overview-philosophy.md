# runit — Overview and Design Philosophy

## Overview

runit is a UNIX init scheme with service supervision, written by Gerrit Pape. It occupies a specific niche in the init-system landscape: it is both a complete replacement for SysVinit (it can run as process 1 and manage boot and shutdown in three stages) and, at the same time, a general-purpose process supervision suite that can be used on a system that boots with some other init. This dual identity is the source of much of its design elegance — supervision is the core primitive, and everything else is layered on top of it.

Genealogically, runit is a direct descendant of Daniel J. Bernstein's [daemontools](http://cr.yp.to/daemontools.html) design. daemontools established the pattern: a long-running scanner process watches a services directory, spawns one lightweight supervisor per service directory, and each supervisor keeps its assigned daemon running forever, restarting it the instant it dies. runit took that pattern, added a proper three-stage init around it (boot, running, shutdown), added per-service log supervision with a real log daemon (svlogd), and rewrote everything as small, dependency-free C that builds statically. The s6 suite (a later, more elaborate evolution of the same ideas) is discussed on its [project page](https://skarnet.org/software/s6/).

The version history is a study in stability: runit 2.1.2 was released in 2014 and remained the shipping version for roughly a decade — Debian bookworm still packages 2.1.2, and Void Linux built its entire init on it. Upstream development resumed with 2.2.0 (now in Debian testing) and continues; 2.3.1 is the current release per upstream install instructions. A tool that changes this rarely is a tool you can learn once and rely on for the life of a career — a deliberate contrast with faster-moving systems like systemd.

This page covers the philosophy and the moving parts. The boot stages and service directory format are covered in detail in [runit — Boot Stages and Service Directories](./stages-services.md), and the day-two tooling (sv, svlogd, chpst) in [sv, svlogd, chpst — Operating Services and Logs](./sv-logging.md).

## Core Design Ideas

### Services are directories with a `run` script

A runit service is nothing but a directory containing an executable named `run`. The `run` script is expected to `exec` the daemon in the foreground — this is non-negotiable and drives the entire model. Because runit supervises the process it starts, daemons must not fork into the background; the well-known "daemon-off" invocation pattern (`nginx -g 'daemon off;'`, `sshd -D`) exists precisely for supervisors like this. There is no unit file grammar, no parser, no DSL: enabling a service means putting a symlink to its directory in a watched directory, and disabling means removing the symlink. Configuration state is the filesystem.

### Supervision is dedicated and unconditional

Every service directory gets its own `runsv` process — a supervisor that does exactly one job: start `./run`, wait for it to exit, optionally run `./finish`, then start `./run` again. There is no restart policy language, no backoff configuration, no threshold. If the process dies and no `down` file opted the service out of auto-start, it restarts — immediately (runsv inserts roughly one second of delay only when a `run` or `finish` exits immediately, to avoid a tight spin). The only opt-outs are explicit: a `down` file in the service directory prevents auto-start, and `sv down`/`sv once` express one-shot intent. This "restart is the default, opting out is explicit" inversion of SysVinit semantics is what makes runit-managed systems so resilient.

### Logging is a first-class paired service

If the service directory contains a `log/` subdirectory with its own `run` script, runsv creates a pipe: the service's stdout (and, by convention, its stderr after the `exec 2>&1` idiom) flows into the stdin of a second supervised process — almost always `svlogd`, runit's log daemon. The log service is itself supervised by the same runsv, so if svlogd dies it is restarted too, and log continuity survives service restarts. Every service gets its own log directory with size-based rotation and retention policy — no shared log file, no syslog dependency.

### Stages instead of runlevels

runit does not implement SysV-style runlevels with a symbolic state machine. It has three stages (1: one-time boot tasks, 2: the supervision loop, 3: shutdown tasks), and "runlevels" in runit are simply *different service directories* — you can switch the active set of services by swapping a symlink (`runsvchdir`) or boot a different set via the kernel command line. Ordering and grouping of services inside stage 2 are, by design, not runit's problem: all services in the directory start in parallel and stay supervised.

### Tiny, static, dependency-free

The whole suite is a handful of small C programs with no external dependencies, built to be linked statically. There is no IPC framework: `sv` talks to `runsv` by writing single control characters into a named pipe (`supervise/control`), and supervisor state is exposed as small files (`supervise/stat`, `supervise/pid`) that any tool can read. Privilege dropping is done by `chpst` (change process state) rather than by setuid wrapper binaries or PAM integration. This is what makes runit trivially portable (Linux, the BSDs, macOS, Solaris) and attractive for embedded and container use, where it pairs naturally with a busybox-based userland.

## Design Lineage: daemontools, runit, s6

The comparison below frames runit against its closest relatives. All three descend from the supervise-and-restart school; they differ in scope and in how far they push the idea.

| Aspect | daemontools (DJB) | runit (G. Pape) | s6 (skarnet) |
|---|---|---|---|
| Scope | User-space supervision only; not an init | Full init (3 stages) + supervision suite | Supervision suite plus an optional init framework (s6-rc, s6-rc-oneshot-runner) |
| Supervision model | `supervise` per service, driven by `svscan`/`supervise` | `runsv` per service, driven by `runsvdir` | `s6-supervise` per service, driven by `s6-svscan` |
| Restart policy | Unconditional restart | Unconditional restart; `down` file opts out | Configurable via service definition; finish scripts with exit codes |
| Logging | `multilog` | `svlogd` (rotation, config file, pattern filtering) | `s6-log` (line-based scripting grammar) |
| Control CLI | `svc`, `svstat` | `sv` (single tool, LSB-compatible aliases) | `s6-svc`, `s6-svstat`, plus richer tooling |
| Service grouping | Directories scanned recursively | Flat directory; service sets via directory swap | Dependency graphs via s6-rc |
| Oneshot support | No | No (emulated patterns only) | Yes (oneshot service type) |

The recurring theme: daemontools proved the supervision pattern, runit productized it into a complete but minimal init, and s6 generalized it with dependency handling at the cost of a larger toolset. For interviews, the useful takeaway is that runit sits at the sweet spot: everything daemontools did, plus logging and boot/shutdown, with almost no configuration surface.

## Components at a Glance

| Component | Role |
|---|---|
| `runit` | The stage machine; must run as process 1; runs `/etc/runit/1`, `/etc/runit/2`, `/etc/runit/3` in order |
| `runit-init` | Tiny `/sbin/init` shim started by the kernel; immediately replaces itself with `runit`; also the `init 0` / `init 6` front end for shutdown/reboot requests |
| `runsvdir` | Scans a services directory (every five seconds), spawns and monitors one `runsv` per subdirectory or symlink |
| `runsv` | Per-service supervisor: runs `./run`, honors `down`, runs `./finish`, maintains the `supervise/` state and `control` pipe, and manages the optional `log/` service pair |
| `sv` | Control CLI for services: status, up, down, once, signals, plus LSB-style `start`/`stop`/`restart` aliases; exits nonzero per failing service |
| `svlogd` | Log daemon fed by the `log/run` pipe; size-based rotation, retention, per-directory `config`, pattern selection, optional processors |
| `chpst` | Change process state before exec: setuid/gid (`-u`), envdir (`-e`), chroot (`-/`), nice, rlimits — the non-PAM replacement for `su`/`setuidgid` |
| `runsvchdir` | Switch the active service set: repoints the `current` symlink used by `/service` |
| `utmpset` | Writes logout records into utmp/wtmp for getty services, since runit itself does not maintain those databases |

The process tree on a running system looks like this (Void-style paths):

```text
runit (PID 1)
└── runsvdir -P /run/runit/service
    ├── runsv agetty-tty1 ──── run (agetty)      supervise/ + control pipe
    ├── runsv agetty-tty2 ──── run (agetty)
    ├── runsv sshd ─────────── run (sshd -D)
    │                      └─── log/run (svlogd /var/log/sshd)
    ├── runsv udevd ────────── run (udevd)
    └── ...
```

## Where runit Is Used

- **Void Linux** uses runit as its default and only init — its service definitions, per-user services, and logging conventions are documented in the Void Handbook's [services section](https://docs.voidlinux.org/config/services/index.html). Void is the flagship runit distribution and the best reference for production service directory layouts.
- **antiX** ships with runit available and uses it in default installs of recent releases.
- **Artix Linux** offers runit as one of its init choices alongside OpenRC, dinit, and s6 (see [artixlinux.org](https://artixlinux.org/)).
- **Alpine Linux** defaults to OpenRC but packages runit for those who prefer supervision-style service management.
- **Devuan** (systemd-free Debian) allows runit as an init option; see [docs.devuan.org](https://docs.devuan.org/).
- **Debian** ships a `runit` package that provides the full supervision suite for use *without* replacing sysvinit — commonly used to supervise individual daemons or, with `runit-init`, as a full init. The suite's man pages are published for [runit(8)](https://manpages.debian.org/bookworm/runit/runit.8.en.html), [runsv(8)](https://manpages.debian.org/bookworm/runit/runsv.8.en.html), [sv(8)](https://manpages.debian.org/bookworm/runit/sv.8.en.html), and the rest of the toolset.

The container story deserves special mention: because the suite is small and static, `runsvdir -P /etc/service` is a common container entrypoint pattern — it gives a PID 1 that supervises real processes instead of a shell. The tradeoffs (zombie reaping, signal handling) are discussed in [sv, svlogd, chpst — Operating Services and Logs](./sv-logging.md) and in the daemon fundamentals page [Daemons and daemonization](../../../os/processes/daemons.md).

## Tradeoffs: What You Give Up and What You Gain

### What you give up

- **No dependency engine.** runit has no concept of "start postgres before the app". Ordering workarounds are application-level: `sv check` loops in `run` scripts, wait-for-file loops, or distro layers (Void runs ordered one-time setup in stage 1's `core-services`). The runit FAQ itself points users who need dependencies toward other tools.
- **No timers.** Scheduled work belongs to a cron daemon, not to runit.
- **No cgroups integration.** No per-service control groups, no resource isolation between services beyond classic rlimits (which `chpst` can set).
- **No socket activation.** A service that is down simply is not listening; there is no mechanism to hold a socket open and start the service on first connection.
- **No oneshot semantics.** There is no service type that runs a command to completion and is then "done". The common emulations are fragile and are discussed honestly in [Boot Stages and Service Directories](./stages-services.md).
- **No session/seat management, no journal.** Logging is per-service text files; login session accounting needs `utmpset` and cooperative getty scripts.

### What you gain

- **Simplicity and auditability.** The entire supervision path is a few thousand lines of C; a service definition is a shell script you can read in ten seconds.
- **Robustness by default.** Unconditional restart with no policy to misconfigure; a crashing service is kept running (or rather, kept being restarted) through exactly the failures that would kill a SysVinit system silently.
- **Per-service logs by default.** Every supervised service can have isolated, rotated, filtered logs with no syslog involvement.
- **Trivial portability.** Static binaries, no libc coupling beyond POSIX, runs identically on Linux, BSDs, and macOS.
- **Deterministic environment.** Each (re)start of a service gets the same file descriptors, environment, and controlling terminal — a property the Void Handbook explicitly calls out as a benefit of the suite.
- **Container friendliness.** Small static PID 1, simple signal behavior, no D-Bus or cgroup requirements.

For a side-by-side with systemd, OpenRC, and the other families in this section, see the comparison hub [Init systems — comparison](../comparison.md) and the section overview [init-systems README](../README.md).

## Interview Questions

### Q: Why does runit insist that the `run` script `exec` the daemon in the foreground?

Because supervision works by watching a child process it knows. If `run` starts a daemon that forks and exits, runsv would see "run exited" and either restart it in a loop or, with `finish` logic, get confused — while the actual daemon runs unsupervised. `exec` makes the daemon *be* the supervised process: its PID is recorded in `supervise/pid`, its death is immediately observable, and signals sent by `sv` reach the daemon directly. That is why nearly every service you encounter uses patterns like `nginx -g 'daemon off;'` or `sshd -D`.

### Q: runit has no dependency handling. How do real deployments ensure a service starts only after, say, the database is reachable?

The idiomatic answer is a readiness loop in the service's own `run` script: `sv check database >/dev/null || { sleep 2; exit 1; }` repeated with backoff — exiting nonzero forces runsv to restart `run`, effectively turning the supervisor into a retry engine. Other patterns are waiting for a socket or file to appear, or pushing the problem up into stage 1 (Void's `core-services` runs ordered setup before stage 2). The design stance is that dependencies are the service's concern; the supervisor's only job is keeping processes alive.

### Q: Compare the restart model of runit with systemd's `Restart=always`.

Both end up restarting a crashed process, but the semantics differ. runit restarts unconditionally from the moment runsv starts the service, with no rate limiting, no exponential backoff, and no exit-code policy — opting out requires a `down` file or an explicit `sv down`. systemd makes restart a policy knob (`Restart=`, `RestartSec=`, `StartLimitBurst=`) with failure classification. The runit approach is simpler and has fewer misconfiguration modes; the systemd approach prevents tight restart loops and can express "restart on failure but not on clean exit". Follow up with the fact that runit does at least avoid a tight spin: runsv sleeps about one second when a process exits instantly.

### Q: What actually happens when you remove a service symlink from a runsvdir?

runsvdir re-scans the directory when it detects a change (it checks the directory's mtime/inode/device at least every five seconds). On seeing the entry gone, it sends TERM to the corresponding runsv — which acts as if the `x` (exit) control command was written — stops monitoring it, and does not restart it. runsv first brings the service down (TERM then CONT, runs `finish`), closes the log pipe if present, and exits. Net effect: unlinking is both "disable" and "stop".

### Q: Why would a distribution like Void choose runit over OpenRC or systemd?

Three reasons recur in practice: auditability (a service is a shell script, the supervisor is tiny C), reliability (unconditional supervision means a crashed service is always restarted, and each service gets a clean, reproducible environment on every start), and per-service logging without syslog. Void also values the simplicity of the enable model — symlinks in `/var/service` — over a dependency-solver engine. The cost is that Void maintains its own ordering conventions in stage 1 and its packages must ship well-behaved foreground daemons.

### Q: Where does runit fit in a container, and what is the classic pitfall?

`runsvdir -P /etc/service` as the container entrypoint gives you a PID 1 that supervises multiple processes, restarts crashed ones, and does not require cgroups or D-Bus — a common pattern for multi-process images. The pitfall: orphans re-parent to PID 1, and runsvdir (a plain scanner) does not reap arbitrary zombies the way a purpose-built init would; a `run` script that spawns children that outlive it can accumulate zombie entries until the service's runsv exits. Containers also need `-P` (new session per runsv) to avoid terminal signal leakage, and they must handle TERM semantics themselves since there is no stage 3 to clean up.

## References

- [runit — a UNIX init scheme with service supervision](http://smarden.org/runit/) — upstream home page and documentation index
- [runit — how to install](http://smarden.org/runit/install.html) — build/install instructions; current release (2.3.1) referenced here
- [runit(8) — upstream](http://smarden.org/runit/runit.8.html) — the three stages, ctrl-alt-del, and signal behavior
- [runit(8) — Debian man page](https://manpages.debian.org/bookworm/runit/runit.8.en.html) — shows bookworm ships 2.1.2
- [sv(8) — upstream](http://smarden.org/runit/sv.8.html) — control CLI and exit codes
- [runsv(8) — upstream](http://smarden.org/runit/runsv.8.html) — per-service supervisor semantics
- [runsvdir(8) — upstream](http://smarden.org/runit/runsvdir.8.html) — directory scanning and the 5-second rescan
- [daemontools](http://cr.yp.to/daemontools.html) — the supervision design runit descends from
- [s6](https://skarnet.org/software/s6/) — the later, more elaborate evolution of the same design
- [Void Linux Handbook — Services and Daemons (runit)](https://docs.voidlinux.org/config/services/index.html) — production usage, advantages of the suite
- [svlogd(8) — Debian](https://manpages.debian.org/bookworm/runit/svlogd.8.en.html) — runit's logging daemon
- [chpst(8) — Debian](https://manpages.debian.org/bookworm/runit/chpst.8.en.html) — process-state changes without PAM

## Cross-References

- [init-systems README](../README.md) — hub page for the whole init-systems section.
- [Init systems — comparison](../comparison.md) — runit vs systemd vs OpenRC vs SysVinit in one matrix.
- [SysVinit — Overview and History](../sysvinit/overview-history.md) — the init tradition runit deliberately breaks from.
- [systemd — Overview and Architecture](../systemd/overview-architecture.md) — the dependency-driven counterpoint to runit's supervision-first design.
- [dinit — A Modern Dependency-Aware Init](../dinit/overview.md) — a middle path: supervision plus dependencies.
- [Daemons and daemonization](../../../os/processes/daemons.md) — the forking behavior that makes foreground `run` scripts necessary.
