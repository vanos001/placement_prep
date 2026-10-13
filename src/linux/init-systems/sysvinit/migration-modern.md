# From sysvinit to systemd — Migration Paths and the Init Landscape

## Overview

Between roughly 2010 and 2015, nearly every major Linux distribution replaced sysvinit as PID 1. The replacement was not merely a faster boot: it was a change in what the init system is responsible for — from "run scripts in order" to a supervisory, resource-accounting, activation-driven core that also spans user sessions and containers. This page covers why the migration happened, the concrete mechanics on Debian (the `systemd-sysv` package and the `systemd-sysv-generator` compat layer), the supported paths for staying on sysvinit, and the wider landscape of alternatives that either predate systemd, forked against it, or grew up alongside it.

The landscape matters in practice, not just in history: sysvinit remains the default on Devuan and antiX, OpenRC runs Gentoo, Alpine, and Artix, runit runs Void, dinit runs Chimera Linux, and Slackware never left BSD-style init at all. Admins moving between these systems, candidates in interviews, and teams planning a fleet migration all need the same map: what each init actually does, what you gain and lose by switching, and what the migration checklists look like in both directions.

The baseline architecture and history of sysvinit itself are in [overview-history.md](./overview-history.md); this page starts where that one ends — at the point where its model stopped being enough.

## Why Distributions Migrated

The migration debate is easiest to follow as a capability comparison. The left column is what the sysvinit stack (scripts, insserv, startpar) can express; the right is what systemd was designed around:

| Capability | sysvinit (+ insserv/startpar) | systemd |
|---|---|---|
| Boot parallelism | batch rounds from a compiled dependency graph | continuous transactional graph; every satisfiable unit starts immediately |
| Process supervision | none — scripts exit after start; daemons die unwatched | per-unit supervision with `Restart=`, watchdogs, live state |
| On-demand activation | none — everything enabled starts at boot | socket, path, D-Bus, and timer activation; services start on first use |
| Resource control | none — no per-service attribution | cgroup attribution per unit; slices, limits, accounting |
| Logging | per-script stdout to console or logfile | journal with unit metadata, structured and indexed |
| User sessions | none — login managed by external tools | `systemd --user` managers, logind seat/session management |
| Containers | not designed for them | scope/slice integration, `systemd-nspawn`, per-container units |
| Time-based jobs | external cron | `.timer` units with calendar/monotonic triggers |
| Boot-time introspection | bootlogd timestamps, external charting | `systemd-analyze blame` / `critical-chain` built in |

The headline arguments for migration were operational: supervision (`Restart=` turns "cron checks and restarts" into a kernel-adjacent default), speed (socket activation removes ordering waits entirely — see [systemd — Socket Activation](../systemd/socket-activation.md)), and observability (per-unit cgroups make "what is this PID part of, and what did it use" answerable). The counterarguments — scope, complexity, and the coupling of optional features to PID 1 — are what produced every fork and alternative listed below. Both sides of that ledger are fair; the honest summary is that the capability table above was decisive for large fleets, while the coupling objection was decisive for the holdouts.

## The Debian Migration Mechanics

### The systemd-sysv package and the compat symlinks

Debian's switch is packaged as a decision, not an accident: installing `systemd-sysv` makes systemd PID 1. The package provides the `/sbin/init` symlink to systemd's binary and the legacy compatibility symlinks — `telinit`, `runlevel`, `shutdown`, `halt`, `poweroff`, `reboot` — pointing at `systemctl` (and friends), which behave as the historical tools when invoked under those names. The point of the layer is that twenty years of scripts and admin muscle memory keep working: `telinit 1`, `shutdown -r now`, and `runlevel` produce the expected behavior while PID 1 is actually systemd. Removing the package and installing `sysvinit-core` flips `/sbin/init` back — the two inits are co-installable as package sets, with exactly one owning the boot at a time.

### systemd-sysv-generator: what it does

A migration needs bridge traffic in both directions, and the bridge is a generator — a small program systemd runs at boot and at `daemon-reload` time to synthesize unit files dynamically (the generator contract is specified in [systemd.generator(7)](https://manpages.debian.org/bookworm/systemd/systemd.generator.7.en.html)). `systemd-sysv-generator` scans `/etc/init.d/`, parses each script's LSB header, and creates a transient service unit for every script with runlevel links. An abridged, illustrative example of what it produces (exact fields vary by release; the shape is what matters):

```text
# /run/systemd/generator.late/myapp.service  (generated - inspect, do not edit)
[Unit]
SourcePath=/etc/init.d/myapp
Description=LSB: myapp application daemon
After=network.target syslog.target
[Service]
Type=forking
ExecStart=/etc/init.d/myapp start
ExecStop=/etc/init.d/myapp stop
RemainAfterExit=yes
```

The generated units are written to the late generator directory so that native unit files in `/etc/systemd/system` take precedence — a hand-written `myapp.service` instantly overrides the generated one. Header fields map mechanically: `Required-Start` becomes `After=` ordering, `Default-Start` selects the runlevel targets to hook, `Short-Description` becomes the unit description, and start/stop are implemented by calling the script itself. The practical effect: on a migrated Debian system, every legacy service keeps working under `systemctl status myapp` on day zero, before anyone writes a native unit.

### What the generator cannot do

The generator is a compatibility layer, not a translation. Its limits define why hand-porting is always the second step (a worked script and its port are in [custom-init-scripts.md](./custom-init-scripts.md)):

- **No real supervision.** The unit runs the *script*, which starts the daemon and exits; systemd's `Type=forking` tracking plus `RemainAfterExit` approximates state, but `Restart=` cannot resurrect a daemon whose death systemd never observes. The service still dies unwatched.
- **The script still forks.** Process identity lives in the same pidfile machinery as before, including all of its stale-PID hazards — nothing moves into systemd's own model.
- **Coarse attribution.** The script's whole process subtree lands in the unit's cgroup, but resource control semantics designed for supervised units are approximate here.
- **No new capabilities.** Socket activation, timers, path units, and journal-native logging require native units; the generator bridges behavior, not features.

The rule of thumb: treat generated units as a working scaffold — `systemctl cat myapp.service` to inspect, then write a native unit in `/etc/systemd/system` when you touch the service.

## Staying on sysvinit

### Debian: sysvinit-core caveats

Debian never removed the old init: selecting `sysvinit-core` keeps `/sbin/init` as sysvinit and preserves the script model described across this section. What a modern Debian on sysvinit-core needs, and what surprises people:

- **A syslog daemon.** There is no journal without systemd, and Debian's logging expectations shifted during the migration years; install rsyslog (or equivalent) explicitly or logs exist only where individual scripts send them.
- **elogind for desktops.** Components built against logind's interface (seat management, polkit agents, desktop environments) need `elogind` — the standalone extraction of logind for non-systemd systems — or the session layer breaks while services still run fine.
- **Some packages assume systemd.** Anything shipped only as a unit, or relying on socket/timer activation, needs a script substitute; cron remains the timer substitute (see [Cron — Scheduled Jobs](../../admin/cron.md) for that side of the trade).
- **Boot ordering expectations.** With dependency tooling absent, ordering reverts toward static numbers and lexical order — the header metadata discussed in [parallel-booting.md](./parallel-booting.md) is what keeps dependency semantics alive on such systems.

### Devuan: the init-freedom fork

Devuan is the Debian fork created in 2014 after Debian's technical committee decided systemd would be the default init for jessie and the ecosystem began assuming logind. Its stated principle — "init freedom", in the project's own terminology — is that the distribution should not mandate a particular init; functionally, Devuan maintains Debian's package base with sysvinit as the default PID 1 and OpenRC and runit offered as supported options. The first stable release (Devuan 1.0 "Jessie", 2017) tracked Debian jessie's package base minus the systemd dependency chain; the project has tracked every Debian release since, and its documentation at [docs.devuan.org](https://docs.devuan.org/) is the primary reference for its packaging decisions. Whatever one's position on the underlying controversy, the engineering result is a maintained, up-to-date Debian derivative where the sysvinit paths above are the supported default rather than the alternative.

### antiX, Slackware, and the holdouts

antiX, a Debian-based distribution, ships sysvinit by default (with runit available in recent releases), and Slackware never adopted systemd at all — it runs the sysvinit binaries with BSD-style `rc.*` scripts and no runlevel-based service management, a model predating the LSB conventions entirely. The pattern across holdouts is consistent: they are not museums. They are maintained distributions whose maintainers judged the capability table above not worth the coupling, and they demonstrate that the script model remains fully viable at scale in the right hands.

## The Alternatives Landscape

sysvinit versus systemd is the headline, but the actual landscape is wider. The main contenders:

| Init system | Used by | Model | Supervision | Notes |
|---|---|---|---|---|
| sysvinit | Devuan (default), antiX, Slackware (variant) | runlevel-driven shell scripts | none (external tools) | the model this whole section documents |
| systemd | Debian, RHEL/Fedora, SUSE, Ubuntu, Arch | transactional unit graph | native, per-unit | the migration target; see [systemd — Overview](../systemd/overview-architecture.md) |
| OpenRC | Gentoo, Alpine, Artix, Devuan option | dependency-ordered scripts | optional (`supervise-daemon`) | closest "modern sysvinit"; see [OpenRC — Overview](../openrc/overview-architecture.md) |
| runit | Void (default), Devuan option, antiX option | three-stage boot + per-service dir | native, per-service | tiny, supervision-first; see [runit — Overview and Philosophy](../runit/overview-philosophy.md) |
| s6 / s6-rc | embedded and enthusiast setups | supervision suite with dependency management | native, per-service | Laurent Bercot's [s6](https://skarnet.org/software/s6/); rigorous, composable, steep learning curve |
| dinit | Chimera Linux (default), eweOS; Artix/antiX option | dependency-aware service manager | native, per-service | modern C++ design; see [dinit — Overview](../dinit/overview.md) |
| busybox init | embedded systems, initramfs | minimal inittab-driven | none | tiny; covered with BusyBox in [BusyBox](../../binaries/busybox.md) |
| Upstart | Ubuntu 9.10–14.10 (removed 16.04) | event-driven jobs | native (limited) | the lost competitor; [upstart.ubuntu.com](http://upstart.ubuntu.com/) preserves its docs |

Upstart deserves its own sentence of history because it shaped the debate: it replaced sysvinit as Ubuntu's default in 9.10 (2009), pioneered event-driven boot (jobs reacting to events rather than following numbers), and lost the ecosystem contest after Canonical moved Ubuntu to systemd with 15.04 (2015); its packages were removed in 16.04. Its design questions — how to order services without runlevels — are the same ones systemd, OpenRC, and dinit each answered differently.

## A Decision Matrix

No init wins every context; the honest matrix is by workload:

| Context | Good fit | Why |
|---|---|---|
| Large uniform server fleet | systemd | one model for supervision, logging, resource limits; fleet-wide uniformity pays |
| Multi-distro administration | OpenRC | portable across Gentoo/Alpine/Artix/Devuan; script model you can read anywhere |
| Containers (one app each) | no init, or tini/dumb-init | PID 1 duties reduced to signal forwarding and zombie reaping — see below |
| Embedded / small RAM | busybox init or runit | footprint; runit adds supervision at negligible cost |
| Workstation | systemd | logind seat/session integration is load-bearing for desktop stacks |
| Minimal server | OpenRC, runit, or s6 | full service model without systemd's scope |

The container row is the modern interview favorite, and the reasoning matters. A container is one namespace around one application; a full init solves problems (boot ordering, multi-service dependency graphs) that do not exist there. But PID 1 has two unavoidable duties regardless: it receives the container's signals (and must forward SIGTERM to the app — a process with default signal dispositions will simply not shut down gracefully), and it inherits orphaned processes and must reap them (a PID 1 that does not `wait()` accumulates zombies). That is exactly what `tini`/`dumb-init` implement, and why the full theory of daemons, sessions, and reaping — in [daemons.md](../../../os/processes/daemons.md) — is the knowledge that generalizes across every init choice.

## Checklist: Migrating sysvinit Services to systemd

1. **Inventory and scaffold.** List every enabled script and its LSB header. On the migrated system, the generator has already built first-pass units — inspect each with `systemctl cat <name>` (the `SourcePath=` line identifies generated-from-script units).
2. **Hand-port the header.** Write a native unit in `/etc/systemd/system`: `Required-Start` to `After=`/`Wants=` (unit syntax in [systemd — Unit Files](../systemd/unit-files.md)); the script's hard dependencies become ordering, the soft ones become wants.
3. **Port process identity.** Replace pidfile management with `Type=` semantics: foreground daemon `Type=exec`; double-forking daemon `Type=forking` + `PIDFile=`; best of all, a daemon that integrates `sd_notify` and `Type=notify`.
4. **Port the environment.** `/etc/default/<name>` maps to `EnvironmentFile=` — the file itself can be reused unchanged.
5. **Port the lifecycle.** `--chuid` to `User=`; `--retry TERM/20/KILL/5` to `KillSignal=`/`TimeoutStopSec=`; `kill -HUP` reload to `ExecReload=/bin/kill -HUP $MAINPID`.
6. **Convert scheduled jobs.** Cron entries that existed to work around init limitations (restart-on-failure, periodic reload) become `.timer` units ([systemd — Timers](../systemd/timers.md)); plain cron stays cron (and its mechanics remain in [cron.md](../../admin/cron.md)).
7. **Move logging.** Logfile redirection becomes the journal by default; retention and queries via [journald](../systemd/journald.md) — keep an export path if compliance requires files.
8. **Reconsider socket services.** Anything waiting on a port is a candidate for socket activation, which removes its boot-order edges entirely (see [systemd — Socket Activation](../systemd/socket-activation.md)).
9. **Validate.** `systemd-analyze verify` on each unit, then a real boot with `systemd-analyze blame`/`critical-chain` against your old bootlogd timings.
10. **Retire the script last.** Keep the init script installed through the transition (the generator defers to your native unit); remove registration only after a full success cycle.

## Checklist: Migrating Back (systemd to sysvinit)

The reverse direction — consolidating on a Debian-family system that stays sysvinit, or standardizing a fleet on Devuan/antiX — is mostly an exercise in re-adding what systemd was doing for you:

- **Supervision.** `Restart=` is gone: re-add a supervisor — runit services, s6, OpenRC's `supervise-daemon`, or monit — for every daemon whose death previously triggered a restart.
- **Timers.** `.timer` units become cron entries (or fcron); calendar syntax does not translate automatically — rewrite each schedule.
- **Logging.** The journal becomes syslog: install rsyslog, and add logrotate configuration for every logfile your scripts now create, since nothing rotates them implicitly.
- **Socket activation.** No equivalent in the script model: either accept boot-order dependency on the listener, or front the service with an inetd-style wrapper.
- **Resource control and attribution.** cgroup slices disappear; accounting needs external tooling, and "which service owns this PID" reverts to process-tree reading.
- **Boot parallelism and ordering.** The boot is scripts again: keep LSB headers correct and dependency tooling (insserv/startpar, [parallel-booting.md](./parallel-booting.md)) installed if you want compiled ordering rather than numbers.
- **The scripts themselves.** Services that had native units but no init script need one — the full worked example in [custom-init-scripts.md](./custom-init-scripts.md) is the template, and the porting map table there runs in reverse.

The realistic assessment: everything on this list is solvable with mature tools, which is precisely why the holdout distributions are viable — but it is maintenance you now own, item by item.

## Interview Questions

### Q: What exactly does systemd-sysv-generator do, and what does it not do?

It is a generator — a program systemd invokes at boot and at `daemon-reload` — that scans `/etc/init.d/`, parses LSB headers, and synthesizes transient service units (in the late generator directory, so native units in `/etc` override them). `Required-Start` becomes `After=` ordering, `Default-Start` hooks the runlevel targets, and start/stop are implemented by executing the script itself, which is why legacy services keep working under `systemctl` on a migrated system with zero migration work. What it does *not* do is translate the model: the unit runs the script, the script forks the daemon, so there is no real supervision (`Restart=` cannot see a daemon's death through the script), no socket/timer/path activation, no native journal integration, and pidfile hazards survive intact. It is a bridge, and the second step of any migration is replacing its output with hand-written native units.

### Q: Why do most containers skip a full init system, and what breaks without one?

A container packages one application, so the problems a full init solves — boot ordering across dozens of services, dependency graphs, user sessions — do not exist. But PID 1 has two duties that never go away: signal handling (the container's SIGTERM arrives at PID 1, and a process with default dispositions ignores or mishandles it, producing ungraceful shutdowns) and orphan reaping (dead children reparent to PID 1 and become zombies if nobody waits on them). Hence the standard pattern: no init at all for simple, well-behaved single processes; a minimal reaper like `tini` or `dumb-init` when those PID 1 duties need an owner; a real init only for containers that genuinely run multiple services. The underlying theory — why daemons fork, what sessions are, who reaps — is init-system-independent and covered in [daemons.md](../../../os/processes/daemons.md).

### Q: Can sysvinit scripts and systemd coexist on the same host?

Yes, at two levels. At the package level, both init systems can be installed as package sets (systemd-sysv versus sysvinit-core), but exactly one owns `/sbin/init` and thus the boot — the "coexistence" there is a switch, not a mixture. At the runtime level, the coexistence is real and routine: a systemd PID 1 happily runs legacy scripts through the SysV generator while native units run beside them, which is precisely how distributions staged the migration — every service keeps booting during the transition, script-based or native. What does not exist is the reverse runtime mixture: a sysvinit PID 1 ignores unit files entirely (no generator runs), so on a sysvinit boot, everything must be script-backed.

### Q: Why did Devuan fork, and what did the fork trade away?

The proximate cause was Debian's 2014 technical-committee decision making systemd the default init for jessie, followed by ecosystem components (logind consumers in particular) becoming hard-wired to it — which Devuan's founders read as the distribution no longer supporting a choice of init. Their project preserves Debian's package base with sysvinit as default and OpenRC/runit as supported alternatives, under the project's "init freedom" principle; the first stable release shipped in 2017 and it has tracked every Debian release since, with its own documentation at docs.devuan.org. The trade: Devuan maintains the integration work Debian offloaded to systemd (desktop session handling via elogind, logging via classic syslog, init-script coverage for packages that dropped theirs) — ongoing effort, paid for a policy outcome they consider worth it. It is the clearest long-running experiment in whether the script model remains viable with full-time maintenance behind it; so far, demonstrably yes.

### Q: You are moving a systemd fleet to OpenRC/runit/sysvinit. What must you re-add, item by item?

Supervision first: `Restart=` has no script-model equivalent, so every critical daemon needs an external supervisor (runit services, s6, `supervise-daemon`, or monit). Timers become cron entries with rewritten schedules. The journal becomes rsyslog plus logrotate, since nothing rotates script output implicitly. Socket activation has no equivalent — either accept ordering dependencies on listeners or wrap them inetd-style. cgroup-based accounting and per-service attribution revert to external tooling. Boot parallelism/ordering revert to the header-plus-insserv machinery. And every service that had only a native unit needs an init script written. None of this is exotic — it is the standard toolkit of the pre-systemd decade — but it is all now explicit maintenance, which is the honest cost of the move.

### Q: Why did Ubuntu replace Upstart with systemd, given Upstart worked and shipped for years?

Upstart solved the ordering problem elegantly — event-driven jobs instead of sequence numbers — and served as Ubuntu's default from 9.10 through 14.10. What it could not match was the ecosystem consolidation around systemd's *scope*: the capability set that actually decided migrations (socket activation, cgroup-integrated resource control, per-unit supervision with journal metadata, user managers) arrived faster and more completely on the systemd side, and cross-distro convergence on one init meant one set of unit files worked everywhere — a decisive property for a distribution shipping both servers and derivatives. Canonical switched the default with 15.04 and removed Upstart packages in 16.04. The lesson worth keeping from Upstart is its design insight — runlevels are the wrong abstraction, events and dependencies are right — which the surviving alternatives (systemd most thoroughly) all share.

## References

- [sysvinit source repository (Savannah)](https://git.savannah.nongnu.org/cgit/sysvinit.git/) — the sysvinit/startpar/insserv-adjacent suite whose migration paths this page maps.
- [Devuan documentation](https://docs.devuan.org/) — the fork's official docs: init options (sysvinit, OpenRC, runit) and release-level differences from Debian.
- [Debian Wiki — LSBInitScripts](https://wiki.debian.org/LSBInitScripts) — the header conventions the generator parses when converting scripts to units.
- [LSB Core — Init Script Actions](https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html) — the normative script contract both inits must honor during a transition.
- [Debian Policy Manual — Operating System Files](https://www.debian.org/doc/debian-policy/ch-opersys.html) — Debian's rules for init scripts and registration, which outlive any particular init.
- [systemd.generator(7) — systemd man page, Debian bookworm](https://manpages.debian.org/bookworm/systemd/systemd.generator.7.en.html) — the generator contract `systemd-sysv-generator` implements.
- [Upstart](http://upstart.ubuntu.com/) — the event-driven init that held Ubuntu's default slot 9.10–14.10; preserved documentation.
- [s6 — skarnet.org](https://skarnet.org/software/s6/) — the supervision suite (with s6-rc for dependency management) referenced in the alternatives landscape.

## Cross-References

- [SysVinit — Overview and History](./overview-history.md) — the model being migrated away from, and how it got here.
- [SysVinit Service Management Tooling](./tooling.md) — update-rc.d, invoke-rc.d, and service: the tooling whose behavior changes under systemd.
- [Writing a Production init.d Script (End-to-End)](./custom-init-scripts.md) — the worked script and its one-to-one systemd porting map.
- [systemd — Overview and Architecture](../systemd/overview-architecture.md) — the migration target's design.
- [systemd — Unit Files](../systemd/unit-files.md) — the syntax LSB headers translate into.
- [systemd — Timers](../systemd/timers.md) — the destination of cron-driven workarounds.
- [systemd — journald](../systemd/journald.md) — where script logfile redirection lands.
- [systemd — Socket Activation](../systemd/socket-activation.md) — the capability with no script-model equivalent.
- [OpenRC — Overview and Architecture](../openrc/overview-architecture.md) — the closest modern descendant of the script model.
- [runit — Overview and Philosophy](../runit/overview-philosophy.md) — supervision-first minimalism; the reaper of choice in reverse migrations.
- [dinit — Overview](../dinit/overview.md) — the modern dependency-aware alternative running Chimera Linux.
- [Init System Comparison](../comparison.md) — the feature matrix behind every decision in this page.
- [Init Systems Hub](../README.md) — section map and reading order.
- [Daemons](../../../os/processes/daemons.md) — the fork/session/reaping theory that explains the container-PID-1 question.
