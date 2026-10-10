# Linux Init Systems — Field Guide

## Overview

Every Linux system runs exactly one first userspace process — **PID 1** — and
whatever that process is defines the shape of the whole machine: how services
start and stop, whether a crashed daemon comes back, how logs are captured,
how resources are accounted, how you boot into rescue mode, and even what
"the system is in state X" means. The init system is the least optional piece
of software on a Linux box: everything else can be replaced or removed, PID 1
cannot.

This section is a complete, implementation-level tour of the five init
systems that matter in practice: **systemd** (the default almost everywhere),
**sysvinit** (the traditional System V scheme that ran Linux for two decades
and still runs Devuan, Slackware and antiX), **OpenRC** (dependency-aware
shell scripts — Gentoo, Alpine, Artix), **runit** (supervision-first, minimal
— Void Linux), and **dinit** (a modern dependency graph with supervision —
Chimera Linux, eweOS, an Artix option).

Each family gets its own sub-section of deep pages covering inner workings,
usage, configuration, tooling, APIs, and operational patterns, with links to
upstream source, wikis, man pages, and API references. A single
[comparison page](./comparison.md) lines all five up feature-by-feature and
gives porting maps between their commands.

## What an init system actually does

Whatever the implementation, PID 1 has a small set of unavoidable jobs, and
each init system answers them differently:

1. **Boot the system** — mount filesystems, fsck, bring up device handling,
   and start the services that make the machine usable (network, logging,
   login prompts).
2. **Supervise services** — start them, track their processes, restart them
   when configured to, and stop them cleanly on shutdown. How much of this is
   real supervision vs "run a shell script and hope" is the biggest dividing
   line between the five systems.
3. **Express dependencies and ordering** — "start sshd only after the
   network is up" must be declarable somewhere, from sysvinit's static
   sequence numbers through LSB headers to systemd's and dinit's runtime
   dependency graphs.
4. **Manage system state** — runlevels (sysvinit, OpenRC), targets
   (systemd), or stages (runit): the named states a system moves between.
5. **Handle shutdown, rescue and reboot** — run stop scripts in reverse
   order, get you a sulogin prompt when boot fails, and turn the power off.

From these jobs, everything interview-relevant follows: why systemd can boot
in parallel while sysvinit mostly cannot, why `KillMode=` exists, why runit
has no dependency engine, and why OpenRC is not PID 1 on most systems that
run it.

## Distro defaults at a glance

| Distribution | Default init | Also available |
|---|---|---|
| Fedora, RHEL, SUSE, Arch, Debian, Ubuntu | systemd | — (Debian: others via remixing) |
| Devuan | sysvinit | OpenRC, runit |
| Slackware, antiX, PCLinuxOS | sysvinit | — |
| Gentoo | OpenRC | systemd |
| Alpine Linux | OpenRC | runit, (s6-based image) |
| Artix Linux | choice at install | OpenRC, runit, dinit, s6 |
| Void Linux | runit | — |
| Chimera Linux, eweOS | dinit | — |
| Most embedded firmware | busybox init or none | sysvinit-style scripts |

The pattern worth noticing: everything mainstream converged on systemd, and
the remaining diversity lives deliberately in distributions and embedded
projects that made init choice a design goal. That split is itself an
interview topic — see the [migration and landscape page](./sysvinit/migration-modern.md).

## Section map and reading order

If you are new, read the first two bullets of each row; the rest is
reference depth. Every page is self-contained and cross-linked.

### systemd — 15 pages

- [Overview and Architecture](./systemd/overview-architecture.md) — components, design, history, adoption
- [Boot Process (bootup(7))](./systemd/boot-process.md) — kernel → sysinit.target → default.target, analyze tools
- [Unit Types](./systemd/unit-types.md) — all 12 unit kinds, naming, escaping
- [Unit Files](./systemd/unit-files.md) — syntax, load paths, drop-ins, templating, [Install]
- [Service Units](./systemd/service-units.md) — Type=, Exec*, Restart=, watchdogs, sandboxing
- [systemctl CLI](./systemd/systemctl-cli.md) — every verb, job modes, systemd-analyze, debugging recipes
- [Targets and Runlevel Compat](./systemd/targets-runlevels.md) — target chain, rescue/emergency, isolation
- [Dependencies and Ordering](./systemd/dependency-management.md) — Wants/Requires/After semantics, transaction engine
- [Socket Activation](./systemd/socket-activation.md) — socket units, fd passing, on-demand services
- [Timer Units](./systemd/timers.md) — monotonic + calendar timers, Persistent=, vs cron
- [journald](./systemd/journald.md) — structured journal, journalctl mastery, forwarding, coredumps
- [cgroups and Resource Control](./systemd/cgroups-resource-control.md) — slices, scopes, CPUQuota/MemoryMax/TasksMax
- [systemd-udevd](./systemd/udevd.md) — uevents, rule grammar, predictable naming
- [networkd and resolved](./systemd/networkd-resolved.md) — network config files, DNS stub, split DNS
- [Programming APIs](./systemd/apis-development.md) — sd_notify, sd-bus, sd-journal, generators, transient units

### sysvinit — 15 pages

- [Overview and History](./sysvinit/overview-history.md) — System V lineage, components, where it still runs
- [Boot Sequence](./sysvinit/boot-sequence.md) — inittab → rcS → rc N → gettys, initramfs handoff
- [inittab](./sysvinit/inittab.md) — every action explained, real distro files, serial consoles
- [Runlevels](./sysvinit/runlevels.md) — 0-6, S, ondemand; transition mechanics
- [/etc/init.d Scripts](./sysvinit/init-scripts.md) — conventions, start-stop-daemon, LSB exit codes
- [LSB Headers](./sysvinit/lsb-headers.md) — the metadata block, virtual facilities, chkconfig
- [rc.d Symlinks](./sysvinit/rc-symlinks.md) — S/K sequencing, .depend files, update-rc.d mechanics
- [Tooling](./sysvinit/tooling.md) — update-rc.d, invoke-rc.d, policy-rc.d, service, chkconfig
- [Shutdown Family](./sysvinit/shutdown-halt.md) — shutdown/halt/reboot/poweroff, runlevel 0/6 flow
- [Single-User and sulogin](./sysvinit/single-user-sulogin.md) — S runlevel, recovery recipes
- [getty and Terminals](./sysvinit/getty-terminals.md) — respawn chain, agetty, utmp/wtmp, serial consoles
- [Utilities](./sysvinit/utilities.md) — pidof, killall5, last, wall, mountpoint, bootlogd
- [Parallel Boot](./sysvinit/parallel-booting.md) — insserv dependency boot + startpar
- [Writing Production Scripts](./sysvinit/custom-init-scripts.md) — full worked example, testing, porting
- [Migration and the Landscape](./sysvinit/migration-modern.md) — why distros moved, Devuan, generators

### OpenRC — 4 pages

- [Overview and Architecture](./openrc/overview-architecture.md) — runlevel dirs, openrc-run, PID-1-vs-not clarification
- [Runlevels and Service Management](./openrc/runlevels-services.md) — rc-update/rc-status/rc-service/rc-depend
- [Service Scripts](./openrc/init-scripts.md) — depend() verbs, checkpath, supervise-daemon
- [rc.conf, cgroups, Containers](./openrc/config-advanced.md) — rc_parallel, rc_sys, elogind, Docker use

### runit — 3 pages

- [Overview and Philosophy](./runit/overview-philosophy.md) — daemontools lineage, supervision model
- [Stages and Service Directories](./runit/stages-services.md) — stage 1/2/3, runsvdir/runsv, service anatomy
- [sv, svlogd, chpst](./runit/sv-logging.md) — operating services, log rotation, recipes

### dinit — 3 pages

- [Overview](./dinit/overview.md) — design goals, users, architecture
- [Service Descriptions](./dinit/service-descriptions.md) — types, dependency kinds, full option grammar
- [Operations](./dinit/operations.md) — dinitctl, boot profiles, real systems

### Cross-cutting

- [Comparison](./comparison.md) — feature matrix, command porting map, decision guide

## How to choose what to study

For placement interviews, systemd and sysvinit dominate the question space —
systemd because it is what you will actually operate, sysvinit because its
concepts (runlevels, init scripts, rc ordering) remain the vocabulary of
every "describe the Linux boot process" question, and the contrast explains
*why* systemd is designed the way it is. OpenRC, runit and dinit questions
appear in infra-heavy and embedded shops, and knowing one alternative init
well is a strong differentiator because most candidates know only systemd.

A practical path: the two boot-process pages, both runlevel pages, one
service-management page per family, then the
[comparison](./comparison.md). From there, follow the cross-references from
whatever your current role touches most — logging ([journald](./systemd/journald.md)),
scheduling ([timers](./systemd/timers.md)), or devices ([udevd](./systemd/udevd.md)).

## Interview Questions

### Q: What does an init system do, and what is the deepest architectural difference between systemd and sysvinit?

It is PID 1: it bootstraps userspace, starts and supervises services, resolves
startup dependencies, manages system states, and handles shutdown. The deepest
difference is the supervision model: sysvinit executes shell scripts once per
runlevel and has no daemon after that — a service that dies stays dead until
something reruns the script — while systemd keeps every service in its own
cgroup, tracks its main process, and applies Restart= policies continuously.
Almost every other difference (parallel boot, socket activation, journal,
resource control) follows from systemd turning service management into a
resident, stateful engine rather than a boot-time script runner.

### Q: Why is OpenRC usually not PID 1 even on systems that "use OpenRC"?

Because OpenRC is a runlevel and dependency engine, not a process supervisor
by default. Classically, sysvinit stays PID 1 and its inittab invokes
`openrc sysinit`, `openrc boot`, and `openrc default` at the right points;
OpenRC then computes the dependency order and runs the service scripts.
openrc-init exists as an optional PID 1 replacement, but most deployments
keep the classic split. This is a common interview trap: "Gentoo's init
system" is really a two-piece arrangement.

### Q: Which init would you pick for a container, and why is the answer often "none"?

Containers usually run one application, so a full init buys little; the real
question is zombie reaping and signal forwarding, since PID 1 in a container
inherits those duties. A tiny supervisor like tini or dumb-init — or runit's
runsvdir for multi-process images — covers that without systemd's footprint.
If you genuinely need multiple supervised services, runit or OpenRC inside
the container are established patterns, while systemd in containers is
possible but heavy. See the migration page's container section.

### Q: What is one capability each init system has that the others lack?

sysvinit: none of them beats its auditability — every service start is a
shell script you can read with no daemon magic. systemd: socket activation
and cgroup-scoped kill/restart, which no other init in this section matches
in maturity. OpenRC: dependency-aware *scripts* — you keep plain shell
services but get a real dependency solver. runit: rock-solid minimal
supervision with per-service logging out of the box. dinit: a systemd-like
dependency graph (with proper failure semantics) in a tiny, dependency-light
binary.

## Key Takeaways

- PID 1 defines the machine: supervision, dependency resolution, state
  management, shutdown — every other behavior follows from how the init
  system answers those four jobs.
- systemd won by turning init into a resident transactional engine; sysvinit
  remains the conceptual baseline (runlevels, rc scripts) everyone is tested
  on; OpenRC, runit and dinit are the maintained alternatives, each with a
  different core bet (scripts+deps, supervision, graph+supervision).
- The comparison page's porting map is the fastest way to translate habits
  between systems; each family's pages link upstream source, wikis, man
  pages and API docs for ground truth.

## Cross-References

- [Boot Process overview](../../os/boot/README.md) — firmware and bootloader stages before init
- [Init Systems (overview)](../../os/boot/init-systems.md) — original short treatment this section supersedes in depth
- [Linux Kernel Boot](../kernel/core/kernel-boot.md) — the kernel side of the handoff to PID 1
- [Daemon Processes](../../os/processes/daemons.md) — what init supervises: daemonization, PID files
- [systemd (admin guide)](../admin/systemd.md) — existing hands-on admin page
- [BusyBox](../binaries/busybox.md) — busybox init and the embedded end of the spectrum

## References

- [systemd source repository](https://github.com/systemd/systemd)
- [systemd project home and docs index](https://systemd.io/)
- [systemd man pages (freedesktop.org)](https://www.freedesktop.org/software/systemd/man/latest/)
- [sysvinit source repository (Savannah)](https://git.savannah.nongnu.org/cgit/sysvinit.git/)
- [OpenRC source repository](https://github.com/OpenRC/openrc)
- [Gentoo Wiki — OpenRC](https://wiki.gentoo.org/wiki/OpenRC)
- [runit — official pages](http://smarden.org/runit/)
- [Void Linux handbook — services](https://docs.voidlinux.org/config/services/index.html)
- [dinit source repository](https://github.com/davmac314/dinit)
- [Devuan documentation](https://docs.devuan.org/)
