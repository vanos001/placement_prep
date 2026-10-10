# sv, svlogd, chpst — Operating Services and Logs

## Overview

Three tools do most of the daily work on a runit system. `sv` is the control CLI: it talks to the per-service supervisors and reports state. `svlogd` is the log daemon that every well-formed service pipes its output into: it rotates, filters, timestamps, and optionally post-processes logs. `chpst` is the privilege-and-environment shim that `run` scripts use to drop privileges, import envdirs, and set rlimits — without PAM, without `su`, without a setuid wrapper.

All three follow the same design ethos as the rest of the suite: small, static, scriptable, with exit codes you can build on. This page is the operator's reference for them; the directory format they operate on is documented in [runit — Boot Stages and Service Directories](./stages-services.md).

## sv(8) — The Service Control CLI

### Command reference

`sv` reports status and controls services monitored by runsv. Its argument handling is simple: one command, one or more service directories (bare names are looked up in `/service/`, paths are used as-is; the `SVDIR` environment variable overrides the default). The table below is the full documented set ([sv(8) upstream](http://smarden.org/runit/sv.8.html), [Debian](https://manpages.debian.org/bookworm/runit/sv.8.en.html)):

| Command | Effect |
|---|---|
| `status` (alias `s`) | Report state of the service and, if present, its log service |
| `up` | Start if not running; if it stops, restart (cancels a previous `once`) |
| `down` | TERM then CONT; run `./finish` if present; do not restart afterwards |
| `once` | Start if not running; do **not** restart when it exits |
| `start` | LSB alias for `up`, but waits up to 7 seconds; runs `./check` if present (exit 0 = available) |
| `stop` | LSB alias for `down`, but waits up to 7 seconds for the service to go down |
| `restart` | Sends term, cont, up; waits up to 7 s; honors `./check` |
| `reload` | `hup` plus a status report |
| `shutdown` | Alias for `exit`, waiting up to 7 s for runsv to terminate |
| `force-stop` / `force-restart` / `force-reload` / `force-shutdown` | Like their plain forms, but on timeout send KILL |
| `try-restart` | Restart only if the service is currently running |
| `pause` / `cont` | Send STOP / CONT |
| `hup` / `alarm` / `interrupt` / `quit` / `1` / `2` / `term` / `kill` | Send HUP / ALRM / INT / QUIT / USR1 / USR2 / TERM / KILL |
| `exit` | Stop the service, then terminate runsv itself (removes the supervision — the last stop) |
| `check` | Wait up to 7 s for the service to reach the state requested by context; with `./check`, that script decides "up" |

Batching is a filter away: `sv status /var/service/*` reports every enabled service on a Void system, and `sv up /var/service/*` brings up everything that is down. Two options adjust waiting: `-v` makes `up`, `down`, `term`, `once`, `cont`, and `exit` wait (up to 7 seconds) for the command to take effect, and `-w sec` overrides the 7-second default (implying `-v`). The `SVWAIT` environment variable provides a persistent override.

### Exit codes — the scripting contract

`sv` has precise, documented exit behavior, and it matters because `sv check` is the dependency idiom (see [Boot Stages](./stages-services.md)):

- Exit **0** when the command was successfully sent to all services and, if waiting, took effect on all of them.
- For each service that caused an error (not controlled by a runsv, timeout while waiting), the exit code increases by one — up to a maximum of 99.
- Exit **100** on an internal error.
- When `sv` is invoked under a different base name (the LSB `/etc/init.d/` symlink mode), it follows LSB conventions instead: 1 on timeout or trouble sending the command; for `status`, 3 if the service is down and 4 if the status is unknown; 2 on wrong usage; 151 on error.

The LSB mode is a small but clever feature: symlinking `sv` into `/etc/init.d/` under a service's name provides a drop-in LSB init script interface for tooling that expects one — `service foo status` works against a supervised service.

### Reading `sv status` output

A typical pair of lines (service up, log service present):

```text
run: sshd: (pid 1234) 45s
run: sshd/log: (pid 1235) 45s
```

and the down case:

```text
down: sshd: 3s, normally up
```

Field anatomy: the leading word is the supervision state (`run`, `down`, or `finish`); the service name follows; for a running service, the PID and the number of seconds since the state last changed; for a down service, the seconds since it went down plus its *normally-up* disposition — a compact way of saying "this service wants to be up; something put it down". The same seconds-since-change counter is your restart-loop detector: a service whose reported age never grows past a second or two is thrashing. For a whole runsvdir, `sv status /var/service/*` gives the fleet view; anything not reporting `run:` is either downed, finishing, or flapping.

## svlogd — The Log Daemon

### How it is wired in

If a service directory has a `log/` subdirectory containing a `run` script, runsv creates a pipe, redirects the service's (and finish's) stdout to it, and starts `log/run` with its stdin connected to the pipe. The standard log service is four lines:

```sh
#!/bin/sh
exec svlogd -tt /var/log/sshd
```

svlogd reads stdin continuously, applies per-directory selection rules, and appends matching lines to `current` in the target directory. The Void Handbook's [logging page](https://docs.voidlinux.org/config/services/logging.html) documents this arrangement, including the recommended pattern of running the log service as an unprivileged user via `chpst`. Multiple log directories can be given in one invocation — the same stream can be written to several places at once.

### Log directory layout

Per [svlogd(8)](https://manpages.debian.org/bookworm/runit/svlogd.8.en.html), a log directory contains:

- `current` — the live log file; plain text, safe to `tail -F`.
- `@40000000…​.s` — rotated files, named with a precise timestamp marking the moment `current` was renamed. The `.s` suffix marks processed-and-final files.
- `lock` — ensures a single svlogd per directory.
- `config` — the configuration file, read at startup and on every SIGHUP.
- `state` / `newstate` — internal bookkeeping, created as needed.

### Rotation mechanics

When `current` reaches the configured maximum size, svlogd closes it, changes its permission to 0755, renames it to `@timestamp.s`, and starts a fresh `current`. If the number of old files exceeds the configured retention count, the oldest is deleted. Rotation can also be forced: an ALRM signal rotates every log with a non-empty `current`, and a maximum age can be configured so quiet services still rotate periodically. Because rotation is rename-based, readers holding `current` open simply continue on the new file — no lost lines, no truncation races.

### The config file — directives

`config` is read line by line; blank lines and lines starting with `#` are ignored. The well-documented directives:

| Line | Meaning |
|---|---|
| `s`*SIZE* | Max size of `current` before rotation, in bytes (default 1000000; 0 disables rotation) |
| `n`*NUM* | Number of old log files to keep (default 10; 0 keeps everything) |
| `N`*MIN* | Minimum number of old files to keep even when the filesystem is full (must be < n) |
| `t`*SECONDS* | Max age of `current` before forced rotation |
| `!`*PROCESSOR* | Feed each rotated file through this shell command (see below) |
| `u`*A.B.C.D*[:*PORT*] | Also send selected messages via UDP (default port 514) — private networks only |
| `U`*A.B.C.D*[:*PORT*] | Like `u`, but *only* UDP — nothing is written to the directory |
| `p`*PREFIX* | Prefix every emitted line with *PREFIX* |
| `+`*PATTERN* | Select matching lines (everything is selected initially) |
| `-`*PATTERN* | Deselect matching lines |
| `e`*PATTERN* / `E`*PATTERN* | Select / deselect lines for standard error as well |

Patterns are not regular expressions: `*` matches any string (or any string not containing the next pattern character when it is not at the end), and `+` matches one-or-more of the next character. The pattern applies to the first 1000 characters of the message by default (`-l` changes that), and timestamps added by svlogd are not part of the matched text. Selection rules are cumulative and order-sensitive — the classic use is `-`*everything* then `+`*errors only* to keep a small error-only log alongside the full one in a second log directory.

### Processors

The `!processor` line turns rotation into a pipeline: on rotation, `current` is saved as `@timestamp.u`, fed through `sh -c 'processor'`, and the output is written to `@timestamp.t`; on success that file is renamed to the final `.s` and the `.u` is deleted; on failure the `.t` is deleted and the processor is retried. Processors run in the background, and svlogd saves anything the processor writes to fd 5 and offers it back on fd 4 during the next rotation — a side channel for the processor to persist state. Compression (`gzip`), shipping (`curl`), or format conversion are the typical uses. Note the operational caveat: if a processor hangs, svlogd blocks on the next rotation for that log — keep processors simple and bounded.

### Timestamps: TAI64N vs human-readable

`-t` prefixes each line with a precise TAI64N timestamp (the daemontools convention — 24 characters, lexicographically sortable, timezone-proof); `-tt` uses a human-readable, sortable UTC form `YYYY-MM-DD_HH:MM:SS.xxxxx`; `-ttt` uses the ISO-like `YYYY-MM-DDTHH:MM:SS.xxxxx`. For new deployments prefer `-tt`: TAI64N exists for daemontools compatibility, and decoding it in your head requires the `tai64nlocal` tool from the [daemontools](http://cr.yp.to/daemontools.html) suite. If you inherit TAI64N logs, that is exactly what `tai64nlocal` is for: it converts them to local human-readable time on stdin/stdout.

### Signals

HUP closes and reopens all logs and re-reads every `config` — the way to apply selection-rule changes live. TERM (or end-of-file on stdin) makes svlogd flush its buffer, wait for running processors, and exit 0 — which is exactly what happens to the log service when its main service is stopped and the pipe closes. ALRM forces rotation.

## chpst — Changing Process State

### Option reference

`chpst` changes the process state of its argument according to the options and execs it ([chpst(8) upstream](http://smarden.org/runit/chpst.8.html), [Debian](https://manpages.debian.org/bookworm/runit/chpst.8.en.html)). The main options:

| Option | Effect |
|---|---|
| `-u [:]user[:group]` | Set uid/gid (setuidgid). A colon-list of groups sets all supplementary groups; a leading colon means numeric IDs, no name lookups |
| `-U [:]user[:group]` | Set `$UID`/`$GID` environment variables to the user's ids (envuidgid) without dropping privileges |
| `-e dir` | Import environment from an envdir: one file per variable, file name is variable name, first line is value; an empty file unsets the variable |
| `-/ root` | chroot to `root` before exec |
| `-C pwd` | chdir (after chroot if combined) |
| `-n inc` | Adjust nice value |
| `-l lock` / `-L lock` | Open and lock a file; `-l` waits, `-L` fails immediately if locked |
| `-m bytes` | Limit data segment, stack, locked pages, and total memory per process |
| `-d bytes` | Limit data segment size |
| `-o n` | Limit open file descriptors |
| `-p n` | Limit processes per uid |
| `-f bytes` / `-c bytes` | Limit output file size / core file size |
| `-t seconds` | Limit CPU time (SIGXCPU afterwards) |
| `-b argv0` | Run with a custom argv[0] |
| `-P` | Run the program in a new process group (pgrphack) |
| `-0` / `-1` / `-2` | Close stdin / stdout / stderr before exec |

Exit codes: 100 for wrong options, 111 for trouble changing process state, otherwise the exit code of the program itself — so a `run` script ending in `exec chpst ...` inherits the daemon's exit status, which is what `finish` scripts want to see.

### Why chpst instead of su or setuid wrappers

Three reasons. First, dependency footprint: `chpst` is part of the static runit binary set and does no PAM, NSS-session, or login-keyring work — `su` drags all of that in and fails strangely in minimal environments (containers, chroots without PAM configured). Second, composure: `chpst` is a pure prefix — `chpst -u app -e ./env -n 5 exec daemon` composes with the `run` script's other redirections, and its `EMULATION` modes (if invoked as `envdir`, `envuidgid`, `pgrphack`, `setlock`, `setuidgid`, or `softlimit`, it emulates the corresponding daemontools tool) make it a one-binary replacement for the whole DJB utility shelf. Third, auditability: what happens to the process state is exactly the option list, nothing implicit.

## utmpset — Session Accounting for getty Services

runit does not maintain the utmp/wtmp databases for its services — getty processes are supervised like everything else, so nothing records a logout when a getty's session ends. `utmpset` fills that gap: it modifies utmp (and, with `-w`, wtmp) to mark the user on a terminal line as logged out. The documented usage is in the getty's `finish` script:

```sh
#!/bin/sh
exec utmpset -w tty5
```

That keeps `who`, `last`, and friends correct on runit systems without runit itself growing accounting code. Exit codes follow suite convention: 111 on error, 1 on wrong usage, 0 otherwise. It is a small tool, but it is the canonical example of runit's "optional integrations live outside the supervisor" philosophy.

## Operations Cookbook

### Rolling restart of an application service

```sh
sv down myapp            # stops cleanly (TERM/CONT, runs finish), no restart
# ... deploy new code ...
sv up myapp              # supervisor starts it again; supervision state is untouched
```

Because the service directory and its state survive, this is a genuine drain-and-refill: nothing else in the runsvdir is affected, and the log service keeps running throughout (the pipe stays open — `sv down` on the main service does not stop the log service; the log service only exits when its stdin sees end-of-file, i.e., when runsv tears down the whole directory or `sv exit` is used).

### Draining before maintenance

`sv once myapp` followed by waiting for the reported state to go `down` gives a "no new work, finish current work" drain for services that exit when idle. For HTTP services the cleaner pattern is application-level: stop accepting connections (SIGHUP to a listener that supports it) and then `sv down` once drained. The supervision model cannot know your protocol, so draining logic belongs in the service.

### Inspecting supervisor state directly

Everything `sv` reports is readable from the filesystem: `cat /service/myapp/supervise/stat` (human-readable state), `cat /service/myapp/supervise/pid`, and the binary `status` file is daemontools-supervise-compatible for tooling that reads it. Writing single control characters to `supervise/control` is equivalent to `sv` commands (`printf t > ...` sends TERM) — handy in minimal environments where sv is not installed, though note that `printf` blocks if no runsv is running in that directory.

### Emergency: killing the supervisor itself

If you kill runsv, you create a supervision gap: runsvdir will restart it within its five-second scan (the directory entry still exists), but in the interim the service keeps running un-supervised, and when the new runsv starts it will start a *second* copy of the daemon unless the old one died with it. This is why the correct way to remove a service is always removing the directory entry (`rm /var/service/foo`) and letting runsvdir orchestrate the TERM — killing supervisors directly is for broken-supervisor emergencies only.

### runit as a container init

The common pattern uses runsvdir as the entrypoint:

```dockerfile
CMD ["/usr/bin/runsvdir", "-P", "/etc/service"]
```

Each `/etc/service/<name>/run` is a normal service directory. The benefits: multiple supervised processes, automatic restart, no cgroup or D-Bus requirements. The caveats, which come up in every interview about containers and PID 1: signals — `runsvdir` forwards nothing automatically, so graceful shutdown needs each service's `run`/`finish` to handle TERM, or a `finish`/wrapper that propagates; zombies — orphaned processes re-parent to PID 1 (runsvdir), which is not a reaping init, so services that spawn children that outlive them can accumulate zombies; and logging — without stage 1 there is no log ownership switch, so keep the `log/run` pattern with in-container directories. The underlying daemonization mechanics are covered in [Daemons and daemonization](../../../os/processes/daemons.md).

## Interview Questions

### Q: What is `sv check` and why is it the most important scripting verb in the suite?

`sv check` waits up to 7 seconds (configurable with `-w`) for the service to be in the requested state and, when checking "up", runs the service's optional `./check` script — the service is considered up only if that exits 0. It is the dependency idiom: since runit has no dependency engine, a dependent's `run` script loops on `sv check dependency || exit 1`, letting the supervisor's unconditional restart serve as the retry mechanism. The `./check` distinction matters: a process can be alive but not ready (database accepting connections), and `check` is where "ready" is defined.

### Q: How does svlogd rotation work, and what breaks if you rotate externally with logrotate?

svlogd owns `current` and does rename-based rotation: at the size threshold it closes the file, chmods 0755, renames to `@timestamp.s`, and starts a new `current`; retention (`n`) prunes the oldest. Running logrotate against the same directory fights the daemon — svlogd holds the open fd, so logrotate's create/copytruncate strategies either race the rename or duplicate data, and logrotate does not know about the `config`-driven selection rules. The correct answer: never mix; set size and retention in `log/config` and let svlogd handle it, adding a `!processor` line if you need compression or shipping.

### Q: You need per-service logs where errors also go to a separate small file. Design the svlogd setup.

Use two log directories in one svlogd invocation — `exec svlogd /var/log/app /var/log/app-errors` — with `config` files applying selection rules: the errors directory's config deselects everything then selects the error pattern (`-*` followed by `+*err*`-style rules on the program's tag), while the main directory keeps all lines. Selection is order-sensitive per directory, patterns are glob-like (not regex), and `-tt` timestamps are excluded from matching. This gives one full log and one filtered log from a single pipe with no duplicate daemon.

### Q: Why does the `run` script conventionally start with `exec 2>&1`, and what goes wrong without it?

runsv redirects only the service's stdout into the log pipe. Most daemons log to stderr (or to syslog, which may not be running). Without `exec 2>&1`, stderr goes to runsv's inherited stderr — typically the console — so error output bypasses the log service entirely. With it, everything the daemon writes lands in svlogd, timestamps and filters apply uniformly, and the log service becomes the single source of truth. This two-line detail is one of the most common runit mistakes in the wild.

### Q: What does `sv exit` do differently from `sv down`, and when does it matter?

`sv down` stops the service but leaves runsv alive and supervising (the directory is still managed; `sv up` restarts the service). `sv exit` stops the service and then instructs runsv itself to exit — if a log service exists, runsv closes its stdin and waits for it to terminate before exiting; runsvdir will *not* restart a runsv whose directory entry was removed, but for a still-linked directory it will, so `sv exit` matters when you want supervision to end cleanly and deterministically (e.g., tearing down a user services tree, or letting a container's per-service runsv wind down) rather than relying on the scanner's eventual behavior.

### Q: Compare svlogd's config grammar to journald or syslog configuration.

svlogd is per-service and file-driven: one small `config` per log directory, with rotation size (`s`), retention (`n`), age (`t`), selection patterns (`+`/`-`), a processor hook (`!`), and optional UDP mirroring. There is one grammar for all services and no global filter daemon — isolation is structural (one pipe, one directory, one config). journald, by contrast, is a system-wide structured journal with indexing, retention limits, and per-field queries; syslog is a networked central store with facility/priority routing. The runit answer trades query power for locality: to see what a service did, you read (and grep) its directory, and the rotation policy travels with the service definition itself. The journald contrast is developed further in the systemd pages.

## References

- [sv(8) — upstream](http://smarden.org/runit/sv.8.html) — command set, LSB aliases, waiting semantics, exit codes
- [sv(8) — Debian](https://manpages.debian.org/bookworm/runit/sv.8.en.html)
- [svlogd(8) — upstream](http://smarden.org/runit/svlogd.8.html) — log directory layout, rotation, config directives, processors, timestamps
- [svlogd(8) — Debian](https://manpages.debian.org/bookworm/runit/svlogd.8.en.html)
- [chpst(8) — upstream](http://smarden.org/runit/chpst.8.html) — full option reference and daemontools emulation modes
- [chpst(8) — Debian](https://manpages.debian.org/bookworm/runit/chpst.8.en.html)
- [utmpset(8) — upstream](http://smarden.org/runit/utmpset.8.html) — utmp/wtmp logout records for getty finish scripts
- [runsv(8) — upstream](http://smarden.org/runit/runsv.8.html) — the pipe and control wiring sv/svlogd operate through
- [Void Linux Handbook — Logging](https://docs.voidlinux.org/config/services/logging.html) — distribution conventions for svlogd usage
- [Void Linux Handbook — Per-User Services](https://docs.voidlinux.org/config/services/user-services.html) — user-space services and their logs
- [daemontools](http://cr.yp.to/daemontools.html) — origin of the envdir/setuidgid/tai64n conventions chpst and svlogd inherit

## Cross-References

- [runit — Boot Stages and Service Directories](./stages-services.md) — the directory anatomy these tools operate on.
- [runit — Overview and Design Philosophy](./overview-philosophy.md) — where sv/svlogd/chpst sit in the component map.
- [systemd — journald](../systemd/journald.md) — the structured-journal contrast to per-service text logs.
- [systemd — Service Units](../systemd/service-units.md) — Restart= and Type=notify vs unconditional supervision.
- [Init systems — comparison](../comparison.md) — logging and control-CLI columns across all init families.
- [init-systems README](../README.md) — section hub.
