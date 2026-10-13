# dinit — A Modern Dependency-Aware Init

## Overview

Dinit is a service supervisor with dependency support that can also act as the system init — the first process the kernel starts. It was created by Davin McCall with the explicit goal of providing a portable init system with dependency management that is functionally superior to many extant inits; the project's stated development goals are clean design, robustness, portability, usability, and avoiding feature bloat while still handling common — and some less common — use cases. Where systemd subsumes (journal, logind, udev, networkd, timers), dinit's README is explicit about the opposite stance: dinit is designed to *integrate with* rather than replace other system software.

The gap dinit fills is easy to state. runit and the daemontools lineage give you supervision but no dependency engine; OpenRC gives you dependencies but, by default, no supervision; systemd gives you both plus an ecosystem you may not want. Dinit gives you dependency-ordered, parallel, supervised services — plus a control CLI — in a single C++ daemon (built on the bundled Dasynq event library), usable both as PID 1 and as a per-user service manager. It is released under the Apache License, version 2.0.

The version line is 0.x (the current README reports v0.23.0pre) — pre-1.0, but production-proven: it is the default init of [Chimera Linux](https://chimera-linux.org/) and eweOS, and an install option on Artix Linux and antiX. Full documentation ships as man pages — dinit(8) for the daemon, dinit-service(5) for the service description format, dinitctl(8) for the control tool, plus dinit-check(8) (description linting) and dinit-monitor(8) — with the authoritative sources in the repository's [doc/manpages directory](https://github.com/davmac314/dinit/tree/master/doc/manpages).

## Who Uses It

| System | Role of dinit |
|---|---|
| Chimera Linux | Default init; the distribution is built around it (see [chimera-linux.org](https://chimera-linux.org/)) |
| eweOS | Default init |
| Artix Linux | Init option alongside OpenRC, runit, and s6 ([artixlinux.org](https://artixlinux.org/)) |
| antiX | Init option |
| Other distros | Packaged as a *user service manager* on many systems — run under your own account to supervise personal services |

The last row matters architecturally: the same binary, the same description format, and the same control tool serve both the system instance (root, system paths) and a user instance (your account, XDG paths). This is dinit's equivalent of systemd's system/user manager split, minus the D-Bus machinery.

## Architecture

The system has three moving parts: the `dinit` daemon, the service description files it loads, and the `dinitctl` client.

```text
┌───────────────────────────── system instance (PID 1 or root daemon) ─────────────────────────────┐
│  dinit                                                                                           │
│   ├── loads service descriptions from /etc/dinit.d, /run/dinit.d,                                │
│   │                     /usr/local/lib/dinit.d, /lib/dinit.d   (searched in this order)          │
│   ├── starts "boot" service by default (or services named on the command line)                   │
│   ├── supervises process services; rolls back dependents on failure                              │
│   ├── control socket: /dev/dinitctl (system; build-time configurable)                            │
│   └── as system manager (-m): executes shutdown program after all services stop                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
              ▲ control socket commands                    ┌── user instance ──────────────────┐
              │                                            │ dinit -u                          │
        ┌─────┴─────┐                                      │  dirs: $XDG_CONFIG_HOME/dinit.d,  │
        │ dinitctl  │                                      │  $HOME/.config/dinit.d,           │
        └───────────┘                                      │  socket: $XDG_RUNTIME_DIR/dinitctl│
                                                           └───────────────────────────────────┘
```

Key behaviors, per [dinit(8)](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit.8.m4):

- **Lazy loading.** Service descriptions are read as needed — a service's description is typically loaded the first time something starts or references it. Once loaded, a description is never automatically unloaded; `dinitctl unload`/`reload` exist for explicit cases (a stopped service with no loaded dependents can be unloaded; `reload` re-reads a description with documented limitations — the service type, for example, cannot change while running).
- **The `boot` service.** With no command-line service names, dinit starts the service named `boot`, whose dependencies pull up everything else. This convention (mirrored by the `recovery` service, offered when boot appears to fail) is the backbone of every dinit-based distribution's layout.
- **Control socket.** Created at startup, or as soon as the filesystem becomes writable if it was not (the `starts-rwfs` option in a service description is the hook that triggers this). Dinit refuses to start if an active socket already exists, though the check is not atomic. `SIGUSR1` re-opens the socket if it was deleted.
- **System manager vs system service manager.** `-s`/`--system` selects the root service manager role (system paths); `-m`/`--system-mgr` adds the machine-management duties (running the external shutdown program after services stop, recovery handling) and is the default when dinit is PID 1; `-o`/`--container` disables system management entirely for container use, making dinit exit rather than execute a shutdown program.

## Feature Inventory (from the Project's Own Documentation)

From the README's feature description and the dinit-service(5) option list:

- **Parallel startup with dependency management.** Services whose dependencies are satisfied start simultaneously; the graph is computed from the description files, not from static ordering.
- **Supervision with intelligent recovery.** A process service's death stops the service — and dinit can restart it, first "rolling back" dependent services and restarting them once their dependencies are satisfied again. `smooth-recovery` goes further: the process is restarted *in place*, without stopping dependents or changing service state.
- **Rate-limited restarts.** `restart-delay` (default 0.2 s), and a limit of `restart-limit-count` (default 3) restarts within `restart-limit-interval` (default 10 s) — a burst guard runit deliberately lacks.
- **Five service types.** `process` (supervised external program), `bgprocess` (daemon that forks itself and writes a pid file — dinit reads the pid file and supervises the real process), `scripted` (started/stopped by running a command to completion — the oneshot equivalent), `internal` (no process; a grouping/checkpoint node — the target analog), `triggered` (needs an external `dinitctl trigger` to reach started state — e.g., representing a device appearing).
- **Three dependency relationship types** plus ordering hints: hard (`depends-on`, `prepared-by`), milestone (`depends-ms`), soft (`waits-for`), and `after`/`before`. Full semantics in [dinit Service Descriptions](./service-descriptions.md).
- **Readiness notification.** `ready-notification = pipefd:N` or `pipevar:NAME` — dinit hands the process a pipe fd and waits for a message before considering the service started. This is dinit's `Type=notify` analog, and the `pipefd` form is explicitly documented as compatible with the s6 protocol.
- **Per-service logging built in.** `log-type = file | buffer | pipe | none`: append to a log file (with ownership/permissions knobs), keep a ring buffer inspectable via `dinitctl catlog`, or feed output to another *service* via `consumer-of` — the logger-service pattern from the supervision world, expressed as a dependency.
- **Prelaid socket support.** `socket-listen` pre-opens a socket and passes it to the service using the systemd activation protocol (including `LISTEN_FDS`-style hand-off). Note the man page's precision: this by itself is *not* socket activation (nothing starts the service on first connection) — it just guarantees the socket exists and is connectable the moment the service starts.
- **Environment control.** `/etc/dinit/environment` for the system instance (with `!clear`/`!unset`/`!import` directives), per-service `env-file`, `dinitctl setenv`/`unsetenv` at runtime, and variable substitution (`$NAME`, `${NAME:-default}`, `$1` for service arguments) in most setting values.
- **Build-gated hardening and isolation.** Where compiled in (as Chimera does): cgroups (`run-in-cgroup`), Linux capabilities (`capabilities` IAB syntax, `securebits`, `no-new-privs` option), I/O priority, and OOM score adjustment. Resource limits (`rlimit-nofile`, `rlimit-core`, `rlimit-data`, `rlimit-addrspace`, `nice`) are always available in soft:hard form.
- **Console discipline.** One service at a time can own the console (`runs-on-console`); others can share it (`shares-console`) or use it only during startup (`starts-on-console`); fsck-style scripts can be made `skippable` and `start-interruptible` so Ctrl-C skips them without failing the boot.
- **Tooling.** `dinitctl` (control), `dinit-check` (static validation of service descriptions), `dinit-monitor` (run a command on service state change).

## Signals and Lifecycle

Because dinit is frequently PID 1, its signal handling is part of the contract (from the SIGNALS section of dinit(8)):

| Signal | System manager (PID 1) | User instance / system service manager |
|---|---|---|
| SIGINT | Stop all services, then **reboot** (this is what ctrl-alt-del maps to) | Stop services and exit |
| SIGTERM | Stop all services, then **halt** | Stop services and exit |
| SIGQUIT | **Immediate** shutdown — no service rollback | Exit immediately |
| SIGUSR1 | Re-open the control socket (any mode) | Re-open the control socket |

When running as a non-PID-1 service manager, system shutdown is not dinit's job: the primary init starts dinit, and before shutting down signals it and waits (typically via `dinitctl shutdown`). When running *as* system manager and all services stop without a shutdown command, dinit does not die silently — it prompts on the console with recovery options, including starting the special `recovery` service; `-r`/`--auto-recovery` automates that choice for headless machines. The full PID-1 walk-through is in [dinit in Operation](./operations.md).

## Positioning Against the Other Families

| Capability | dinit | systemd | OpenRC | runit |
|---|---|---|---|---|
| Dependency graph, parallel start | Yes (3 relationship types + after/before) | Yes (richer: Requires/Wants/Requisite/BindsTo/...) | Yes (need/use/want/before/after via shell scripts) | No |
| Process supervision | Yes (with rollback, smooth-recovery, restart limits) | Yes (cgroup-tracked, per-unit policy) | Optional (`supervise-daemon` or s6 per service) | Yes (unconditional, per-service) |
| Oneshot service type | Yes (`scripted`) | Yes (`Type=oneshot`) | Yes (scripts are oneshots by default) | No (emulated) |
| Readiness notification | Yes (`ready-notification` pipefd/pipevar, s6-compatible) | Yes (sd_notify) | Partial (`notify` fd/socket option in openrc-run) | No |
| Socket activation | No (pre-opened socket hand-off only) | Yes (full) | No | No |
| Timers | No (cron/external) | Yes | No | No |
| Journal / logging ecosystem | Per-service file/buffer/pipe | journald | syslog + rc.log | svlogd |
| User manager | Yes (same binary, user paths) | Yes (systemd --user + logind) | User-mode openrc (-U) | runsvdir per user |
| Configuration format | Key-value service descriptions | Unit files (INI) | POSIX shell scripts | Directory + `run` script |
| PID 1 role | Linux-supported, production-used (Chimera) | Yes | Optional (`openrc-init`) | Yes (the `runit` binary) |
| Code footprint | Single C++ daemon, small feature set | Very large integrated project | Moderate (C + shell) | Very small C suite |

The honest summary: dinit is "systemd's dependency-and-supervision core" extracted from the ecosystem — no journal, no socket activation, no timers, no logind — with a configuration surface an order of magnitude smaller. Against runit it adds the dependency engine, oneshots, readiness notification, and restart rate-limiting; against OpenRC it adds supervision as a native property rather than an optional add-on. The full-family matrix is in [Init systems — comparison](../comparison.md).

## Interview Questions

### Q: What problem was dinit designed to solve that runit and OpenRC each leave open?

runit supervises but cannot express "start the web server only after the database is ready, and if the database dies, stop the web server first". OpenRC can express ordering and requirements but does not watch processes — a crashed daemon stays crashed until the next boot or a manual restart. Dinit unifies both: a dependency graph computed from description files drives parallel startup, and every `process` service is supervised, with failure propagation through the graph (dependents stopped first, then restarted when dependencies are re-satisfied). It is the smallest system that answers "dependencies and supervision" simultaneously.

### Q: Explain the difference between dinit's `bgprocess` type and a regular `process` service.

A `process` service *is* the process dinit forks and watches. A `bgprocess` service is for daemons that insist on daemonizing: dinit runs the original command, the daemon forks, writes its new PID to `pid-file`, and the original process exits; only then does dinit consider the service started — after reading the pid file and adopting the real process for supervision (it can then signal and monitor it, provided the pid file's permissions are trustworthy). This is the migration path for legacy daemons that lack a foreground mode; the README's advice is still to prefer foreground mode (`process`) so dinit watches the process it launched directly.

### Q: How does dinit's `ready-notification` relate to systemd's `Type=notify`?

Both solve the same problem: distinguishing "process was forked" from "service is actually ready". With `ready-notification = pipefd:3`, dinit sets up a pipe, passes the write end as fd 3, and does not mark the service started until the process writes to it — and the `pipefd` protocol is documented as compatible with s6, so s6-ready daemons work unmodified (`pipevar:NAME` instead names an environment variable through which the fd is passed). The consequence of *not* using it is the classic failure mode: a process service is considered started as soon as it begins execution, so dependents may start against an unready dependency; with a notification configured, startup ordering becomes readiness ordering. Debugging notes are in [dinit in Operation](./operations.md).

### Q: Why does dinit distinguish a system service manager (`-s`) from a system manager (`-m`)?

They are different responsibility sets over the same daemon. `-s` (the default for root) means "manage services with system paths" — service directories, control socket, logging. `-m` adds the machine duties that only PID 1 should exercise: performing the final shutdown/reboot by executing the external shutdown program after all services stop, and driving boot-failure recovery (the console prompt, the `recovery` service, `-r` auto-recovery). A root dinit managing services on a system booted with some other init runs `-s`; the process occupying PID 1 runs `-m` (by default). `-o` container mode is the third combination: services only, no machine duties at all.

### Q: What happens if the `boot` service fails on a dinit system, and how is this designed to be observable?

If all services stop without a shutdown command having been issued, dinit treats it as an apparent boot failure. Running as system manager, it prompts on the console offering several options, prominently starting the `recovery` service (a root-password-gated shell in the example service set); `--auto-recovery` runs recovery without prompting. The design intent documented in DINIT-AS-INIT is that essential services should be *hard* dependencies of `boot` (`depends-on`/`depends-ms`), so their failure propagates into a proper boot failure instead of a system that "mostly" came up — which also makes `dinitctl status`/`list` output the first debugging stop, covered in the operations page.

## References

- [dinit — GitHub repository](https://github.com/davmac314/dinit) — source, releases, issue tracker
- [dinit README](https://github.com/davmac314/dinit/blob/master/README.md) — version (v0.23.0pre), license, supported platforms, users, introductory guide
- [dinit wiki](https://github.com/davmac314/dinit/wiki) — community documentation
- [doc/manpages directory](https://github.com/davmac314/dinit/tree/master/doc/manpages) — authoritative man page sources
- [dinit(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit.8.m4) — daemon options, paths, activation model, signals
- [dinit-service(5) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit-service.5.m4) — service description grammar (primary reference)
- [dinitctl(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinitctl.8.m4) — control CLI
- [Getting started with dinit](https://github.com/davmac314/dinit/blob/master/doc/getting_started.md) — user-mode walkthrough
- [Dinit as init (Linux)](https://github.com/davmac314/dinit/blob/master/doc/linux/DINIT-AS-INIT.md) — PID-1 setup and example service explanations
- [doc directory](https://github.com/davmac314/dinit/tree/master/doc) — design notes and the linux/ services examples
- [Chimera Linux](https://chimera-linux.org/) — flagship production user of dinit

## Cross-References

- [Init systems — comparison](../comparison.md) — dinit against systemd, OpenRC, runit, and sysvinit.
- [systemd — Overview and Architecture](../systemd/overview-architecture.md) — the heavyweight dinit's design converses with.
- [runit — Overview and Design Philosophy](../runit/overview-philosophy.md) — supervision-first alternative that dinit extends with dependencies.
- [OpenRC — Overview and Architecture](../openrc/overview-architecture.md) — the dependency-without-supervision alternative.
- [init-systems README](../README.md) — section hub.
