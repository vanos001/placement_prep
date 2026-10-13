# dinit Service Descriptions (dinit-service(5))

## Overview

A dinit service is described by a plain-text file whose name (minus any `@argument`) is the service name. There is no XML, no INI section headers, no shell execution at load time — just `property = value` lines interpreted by the daemon, with dependency relationships expressed as first-class properties. The authoritative grammar is the [dinit-service(5) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit-service.5.m4); every claim on this page traces to it.

Files live in the service description directories searched in order — for the system instance `/etc/dinit.d`, `/run/dinit.d`, `/usr/local/lib/dinit.d`, and `/lib/dinit.d`; for a user instance `$XDG_CONFIG_HOME/dinit.d`, `$HOME/.config/dinit.d`, `/etc/dinit.d/user`, `/usr/lib/dinit.d/user`, and `/usr/local/lib/dinit.d/user` (per the FILES section of [dinit(8)](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit.8.m4)). Loading is lazy: a description is read when its service is first needed, and once loaded it stays loaded until explicitly unloaded.

This page covers the file grammar, the five service types, the dependency properties and their exact failure semantics, the process-management options, logging and socket options, variable substitution, and worked examples ending in a boot-profile layout.

## File Grammar

Each line of a description file sets one property, in either of two forms:

```text
property = value
property: value
```

The man page is precise about the distinction: **there is currently no functional difference** between the two assignment forms, but some properties *override* any previous setting of the same property while others are *additive* (dependencies and `options` in particular) — the recommendation is to use `=` for overriding settings and `:` for additive ones, so the file itself signals intent. A small set of properties can also be appended to with `+=`.

Other grammar rules:

- Comments start with `#` and run to end of line; they must be separated from values by whitespace.
- Whitespace collapses to single spaces; leading/trailing whitespace is stripped.
- Double quotes group tokens: they prevent whitespace collapse and protect special characters (like `#`) inside them; the quotes themselves are not part of the value.
- A backslash escapes the next character (even inside quotes). An escaped newline continues the value onto the next line (the continuation line must start with whitespace); `\\` collapses to a single backslash.
- Lines beginning with `@` are **meta-commands** (see below), not properties.

**Service names** must be non-empty, must not begin with a dot, and consist of alphanumerics plus `.`, `-`, `_` (non-ASCII bytes are also permitted). **Service arguments** extend the model: `base-name@argument` identifies an independent instance, whose argument is substituted wherever `$1` appears in the description — one template file, many instances (a classic use is per-tty or per-interface services). All settings that name paths are best written as absolute paths; relative paths resolve against the description file's directory, and the `---.d` directory settings resolve against the containing *fragment* (relevant with `@include`).

**Meta-commands:** `@include path` inlines another file (error if missing), `@include-opt path` does the same but silently skips a missing file, and `@meta enable-via service-name` records which service `dinitctl enable` should attach this service to by default. `@include` is how distributions share a fragment across several descriptions without duplication.

## Service Types

Five types, from the SERVICE TYPES section:

| Type | Behavior | Typical use |
|---|---|---|
| `process` | One supervised process; service started/stopped state is linked to the process's life | Daemons with a foreground mode (`sshd -D`, `nginx -g 'daemon off;'`) |
| `bgprocess` | Like process, but for daemons that fork themselves: dinit waits for the original process to exit after forking, reads the new PID from `pid-file`, and supervises that process | Legacy daemons that insist on self-daemonizing |
| `scripted` | Started and stopped by executing a command to completion; successful exit means "started" (or "stopped") | Mounts, fsck, one-time setup — the oneshot equivalent |
| `internal` | No process at all; starts/stops purely as graph state | Grouping nodes, checkpoints, boot profiles (targets) |
| `triggered` | Like internal, but does not reach started state until an external trigger (`dinitctl trigger`) | Device-appearance or event-gated readiness |

The README adds the essential practical rule: for programs offering both modes, choose **foreground** and use `process` — supervision only works when the supervised process is the one dinit launched.

## Dependency Properties and Failure Semantics

The three relationship types have sharply different semantics; the table consolidates the man page's exact rules:

| Property | Start behavior | Failure of the dependency | Dependency stops later |
|---|---|---|---|
| `depends-on:` (hard/need) | Dependent waits for dependency to start; starting the dependent starts the dependency | Dependent does not start | Dependent is stopped |
| `prepared-by:` (hard variant) | Same as depends-on, but the named service is also restarted whenever this service restarts | Dependent does not start | Dependent is stopped |
| `depends-ms:` (milestone) | Dependent waits for dependency to *reach started*; starting the dependent starts the dependency | Dependent fails to start (returns to stopped) | **No effect** — the relationship is satisfied once started |
| `waits-for:` (soft) | Dependent waits for the dependency to finish starting *or fail*; starting the dependent still attempts to start it | Dependent starts anyway | No effect |
| `after:` | Pure ordering: wait only if the named service is also currently starting; does not load or start it | n/a | No effect |
| `before:` | Mirror of `after` from the other side | n/a | No effect |
| `chain-to =` | When this service terminates on its own after starting, start the named service | n/a (the chain target is not even loaded until then) | n/a |

Directory forms aggregate dependencies from directory contents: `depends-on.d:`, `depends-ms.d:`, and `waits-for.d:` each name a directory whose entries (by file name) become dependencies of the corresponding type; entry contents are ignored, symlinks are the expected but not required form, and unreadable entries are non-fatal. The `waits-for.d` directory on the `boot` service is the canonical enable/disable mechanism — `dinitctl enable` writes a symlink there (see [dinit in Operation](./operations.md)).

`chain-to` deserves a note: by default the chain fires only when the service terminated of its own accord with a success status — not after an explicit stop, a dependency-driven stop, an abnormal exit, or when the service will restart; the `always-chain` option removes those guards. The documented uses are recovery shells (exit the rescue shell, the normal service starts) and multi-stage boot where later descriptions live on a filesystem mounted during the first stage.

DINIT-AS-INIT adds the operational guidance: prefer `depends-on` for real requirements — using `waits-for` or especially `after` for a genuine requirement just means dinit will try to start the service without its prerequisite and produce failure noise. Use `after`/`before` only when the named service may not exist at all.

## Process-Management Options

The core options for `process`, `bgprocess`, and `scripted` services:

| Property | Meaning | Default |
|---|---|---|
| `command` | The command line to start the process (also `+=` appendable) | required for process types |
| `stop-command` | Executed to stop the service instead of signalling it | signal-based stop |
| `working-dir` | Working directory | directory of the description file |
| `run-as` | User (and, by name, primary group + supplementary groups) to run as | root/root's group |
| `env-file` | File of NAME=VALUE assignments read at load time; values usable in substitution | none |
| `restart` | `yes` / `no` / `on-failure` (restart only on nonzero exit or deadly signal); inhibited after a user-initiated stop | build-configurable |
| `smooth-recovery` | On unexpected process death: restart the process in place, without stopping dependents or changing state | false |
| `restart-delay` | Minimum seconds between automatic restarts | 0.2 |
| `restart-limit-interval` / `restart-limit-count` | Burst guard: at most count restarts per interval (0 disables) | 10 s / 3 |
| `start-timeout` | Seconds to start; on expiry SIGINT to the process group, then normal stopping; 0 = unlimited | build default (60 s in the example services) |
| `stop-timeout` | Seconds to stop; on expiry SIGKILL; 0 = unlimited | build default |
| `term-signal` | Signal used to request termination (`none` or a name without the `SIG` prefix) | TERM |
| `pid-file` | bgprocess only: file where the daemon writes its PID before detaching | required for bgprocess |
| `ready-notification` | `pipefd:N` or `pipevar:NAME` — wait for a write on the passed fd before "started"; pipefd form is s6-compatible | none (started when execution begins) |
| `rlimit-nofile` / `rlimit-core` / `rlimit-data` / `rlimit-addrspace` | Resource limits, `soft:hard` format (single value sets both) | unchanged |
| `nice` | CPU priority (also sets autogroup priority on Linux) | unchanged |
| `inittab-id` / `inittab-line` | Write/clear utmp entries for the process (needed for `who`-style output; doc recommends avoiding) | unset |

Build-gated additions (present when dinit is compiled with support, as Chimera does): `run-in-cgroup = path` (place the process in an existing cgroup; relative paths resolve against dinit's own cgroup — with cgroups v2 a relative path typically begins with `..` because of the no-internal-process rule; dinit does not create the cgroup), `capabilities`/`securebits` (Linux IAB capability syntax; `^CAP_NET_BIND_SERVICE` in the Ambient set grants port-binding to unprivileged processes), `ioprio`, and `oom-score-adj`.

**Variable substitution** applies to command lines and most path values: `$NAME` or `${NAME}`, with shell-like defaulting (`${NAME:-word}`, `${NAME-word}`, `${NAME:+word}`, `${NAME+word}`), `$$` for a literal `$`, and `$1` for the service argument. Substitution happens at load time from the effective environment (service `env-file` > load-option exports > dinit's process environment), so `dinitctl setenv` does not retroactively change already-loaded descriptions. `$/NAME` additionally splits the expanded value into multiple arguments. Dependency names undergo *pre-load* substitution (service argument and dinit environment only).

## Logging, Sockets, and Console Options

**Logging** is configured with two properties. `log-type = file | buffer | pipe | none` selects the destination for the service's stdout/stderr: append to `logfile` (created if absent; `logfile-permissions` default 600, with `logfile-uid`/`logfile-gid` for ownership — and note the failure mode: if the logfile's directory does not exist or is not writable when the service starts, *the service fails to start*), keep an in-memory ring buffer (`log-buffer-size` caps it; read it with `dinitctl catlog`), or pipe it to another service (`consumer-of = logger`, where the logger is a process service with `log-type = pipe` whose stdin receives the stream). Specifying `logfile` alone flips the type to `file`. The `pipe` form is dinit's answer to the supervision-world logger pattern, with the caveat that an un-consumed full pipe can stall the service.

**Sockets:** `socket-listen = path` makes dinit pre-open a UNIX socket and pass it to the service using the systemd activation protocol; `socket-permissions` (default 666), `socket-uid`, `socket-gid` control the socket node. The man page is explicit that this is *not* socket activation — no first-connection-triggered start — it only guarantees the socket exists and accepts connections (into a queue) from the moment the service starts.

**Console options** (set via the additive `options` property): `runs-on-console` gives the service exclusive console I/O (only one service may hold it; others queue), `starts-on-console` the same during startup only, `shares-console` non-exclusive access without delaying console-exclusive services, `unmask-intr` enables Ctrl-C delivery, `start-interruptible` allows SIGINT to cancel startup, and `skippable` makes an interrupt during a scripted startup count as success — the combination that makes an fsck script skippable at boot. Other `options`: `starts-rwfs` (this service makes the root filesystem writable — prompts dinit to create its control socket and log the boot to wtmp), `starts-log` (this service starts the syslog daemon — dinit flushes its buffered log through /dev/log from then on), `pass-cs-fd` (pass the control socket fd to the process — with a security warning: the service must close it before spawning untrusted processes), `signal-process-only` (signal the process, not its process group), `kill-all-on-stop` (scripted/internal only; before stopping, TERM-then-KILL every other process on the system — for shutdown scripts), `no-new-privs`, and `always-chain`.

**Load options:** `load-options: export-passwd-vars` exports `USER`, `LOGNAME`, `HOME`, `SHELL`, `UID`, `GID` into the service environment; `load-options: export-service-name` exports `DINIT_SERVICE`.

## Worked Examples

### A supervised daemon with readiness notification

```text
# /etc/dinit.d/webapp
type = process
command = /usr/bin/webapp --listen :8080
run-as = webapp
smooth-recovery = true
restart = on-failure
ready-notification = pipefd:3
depends-on: rcboot
waits-for: syslogd
logfile = /var/log/webapp.log
```

Reading it: the process runs as `webapp`; if it dies unexpectedly it is restarted in place (dependents keep running); a crash-loop is bounded by the default 3-restarts/10-seconds limit; dinit does not report the service started until the app writes to fd 3; startup is ordered after `syslogd` (softly) and requires `rcboot` (hard).

### A oneshot with dependencies and a chained rescue path

```text
# /etc/dinit.d/rootfscheck  (adapted from the man page's example)
type = scripted
command = /etc/dinit.d/scripts/rootfscheck.sh
restart = false
options: starts-on-console pass-cs-fd
options: start-interruptible skippable
depends-on: early-filesystems
depends-on: device-node-daemon
```

A scripted service runs the command and is "started" when it exits 0. Because fsck can take arbitrarily long, the real example disables `start-timeout` (setting it to 0); because it must be interruptible, it holds the console and is marked skippable — Ctrl-C skips the check without failing the boot. `pass-cs-fd` lets the script's `reboot` helper talk to dinit even though the control socket may not exist yet (the root filesystem is still read-only).

### The boot profile pattern

```text
# /etc/dinit.d/boot
type = internal
depends-ms: filesystems
depends-ms: loginready
waits-for.d: boot.d
```

The `boot` service is `internal` — pure graph state. Its hard *milestone* dependencies encode "boot has failed if these did not come up" (milestone rather than hard because, once the system is up, `filesystems` stopping should not tear the boot node down), and `waits-for.d: boot.d` points at a directory of symlinks: every entry is a service that boot waits for (softly) at startup. This is exactly the getting-started example extended to production shape, and it is the mechanism `dinitctl enable/disable` manipulates. The tty services then hang off `loginready`, an internal node that collects the services users need before login.

## Boot and Shutdown Ordering — How the Graph Executes

On startup, dinit starts the named service(s) (default `boot`) and computes start order from the dependency graph: a service's process is launched only after all its hard dependencies have started; dependencies themselves start (in parallel where possible) because starting a dependent implies starting what it needs. `waits-for` orders without coupling success; milestone dependencies order with success coupling until reached; `after` orders only co-starting services.

On shutdown, the order inverts through the same graph: a service is not signalled to stop until all of its dependents have completely stopped, and stopping a service stops its dependents first. The activation model ties this to runtime state: `dinitctl start` marks a service explicitly active; `release` clears the mark; a service that is neither explicitly active nor a dependency of an active service stops — so starting a service and then stopping it returns the system to its prior state, dependencies included. Failure propagation summarizes to the table above: hard dependencies stop their dependents; milestones do not (once reached); waits-for never propagates in either direction.

## Interview Questions

### Q: When would you use `depends-ms` (milestone) instead of `depends-on` (hard)?

When the dependency only needs to *have happened*, not to *keep running*. `filesystems` is the canonical example: mounting must complete (successfully) before services start, and it must have succeeded — a hard dependency would tear dependents down if the mount service ever stopped, but a milestone relationship is satisfied permanently once the milestone is reached. Conversely, a database is a `depends-on` dependency: if it stops, dependents must stop. The man page's precise wording: with milestone, once the dependency reaches started state, it may stop without affecting the dependent — but failure to start, or cancelled startup, fails the dependent.

### Q: What is the exact difference between `waits-for` and `after`?

`waits-for` creates a relationship: starting the dependent also starts the named service and delays the dependent's start until that service finishes starting *or fails*. `after` creates no relationship: it only says "if the named service happens to be starting at the same time, let it finish first" — it neither loads nor starts it, and it does not even require the service to exist. DINIT-AS-INIT's guidance follows: use `depends-on` for requirements, `waits-for` for best-effort ordering of things you are starting anyway, and reserve `after` for services whose existence you cannot guarantee (where a `waits-for` on a missing service would be a load failure).

### Q: A process service with `ready-notification = pipefd:3` never reaches STARTED state. What are the likely causes?

First, verify the daemon actually supports the protocol — writing a readiness byte to fd 3 must be implemented by the program (or s6-compatible behavior); a daemon that ignores fd 3 hangs the startup until `start-timeout` expires, whereupon dinit SIGINTs it and it enters stopping state. Second, check the fd number: if the service itself opens files, fd 3 could be consumed by the child; `pipevar:NAME` avoids the guessing by passing the fd number in an environment variable. Third, look at the transition markers in `dinitctl list` — the `<<` indicator with no state change over the timeout window is the signature of a notification mismatch. This "waits the full start-timeout then fails" pattern is the classic dinit debugging scenario.

### Q: How do dinit's dependency directory forms (`waits-for.d` etc.) work, and why do they use file names instead of file contents?

`waits-for.d: boot.d` declares that every non-dot entry in the directory `boot.d` adds a waits-for dependency named after the entry. Contents are irrelevant by design — the *presence* of a name is the datum — which makes the directory a natural target for symlinks (a package manager links a service description into the profile directory to enable it) and for `dinitctl enable`/`disable`, which create and remove exactly such symlinks. Failure to read the directory or find a named service is explicitly non-fatal, so a stale symlink degrades gracefully instead of failing the boot.

### Q: Where does `run-as` differ from OpenRC's `command_user` or runit's `chpst -u`?

In supplementary-group and lookup semantics, per the man page: `run-as` specified *by name* sets the primary group to the user's primary group and initializes supplementary groups from the system group database; specified *numerically*, it keeps dinit's own group and drops all supplementary groups. OpenRC's `command_user` (evaluated by openrc-run before launching) and runit's `chpst -u` behave similarly in the name form (`chpst -u user:group` can set an explicit group or colon-separated group list), but they run inside a shell script context, whereas dinit performs the switch in the daemon itself before exec — there is no script stage to inherit environment or umask from. For privilege *dropping with capability trimming*, dinit additionally offers `capabilities`/`securebits`/`no-new-privs`, which the shell-based systems approximate poorly.

## References

- [dinit-service(5) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit-service.5.m4) — PRIMARY: grammar, all properties, options, substitution, meta-commands
- [dinit(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinit.8.m4) — service description directories, activation model, environment file
- [dinitctl(8) man source](https://github.com/davmac314/dinit/blob/master/doc/manpages/dinitctl.8.m4) — runtime manipulation of these descriptions
- [Getting started with dinit](https://github.com/davmac314/dinit/blob/master/doc/getting_started.md) — the `boot` + `waits-for.d` example this page extends
- [Dinit as init (Linux)](https://github.com/davmac314/dinit/blob/master/doc/linux/DINIT-AS-INIT.md) — dependency-writing guidance and example service explanations
- [dinit README](https://github.com/davmac314/dinit/blob/master/README.md) — service type overview and introductory examples
- [dinit GitHub repository](https://github.com/davmac314/dinit) — source and doc/manpages tree
- [dinit wiki](https://github.com/davmac314/dinit/wiki) — community docs
- [Chimera Linux](https://chimera-linux.org/) — production dinit.d layout in practice

## Cross-References

- [dinit — A Modern Dependency-Aware Init](./overview.md) — architecture, features, and positioning context.
- [dinit in Operation — dinitctl, Boot, and Real Systems](./operations.md) — loading, enabling, debugging these descriptions at runtime.
- [systemd — Unit Files](../systemd/unit-files.md) — the INI unit grammar dinit's key-value format contrasts with.
- [systemd — Dependency Management](../systemd/dependency-management.md) — Requires/Wants/BindsTo vs depends-on/milestone/waits-for.
- [runit — Boot Stages and Service Directories](../runit/stages-services.md) — the no-dependency alternative's directory format.
- [init-systems README](../README.md) — section hub.
