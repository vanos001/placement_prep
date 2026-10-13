# Init Systems Compared — systemd, sysvinit, OpenRC, runit, dinit

## Overview

The five init systems in this section implement the same job — be PID 1,
start and manage services — with five different core bets:

- **systemd** bets on a resident engine: a transactional dependency graph,
  cgroup-scoped supervision, and an ecosystem (journal, timers, resolved,
  networkd) that absorbs adjacent problems.
- **sysvinit** bets on shell scripts and static ordering: maximal
  transparency, zero magic, no supervision.
- **OpenRC** bets on the middle ground: dependency-aware *shell* services
  with a real solver, no daemon, supervision optional.
- **runit** bets on supervision: every service is a directory with a run
  script, watched by a tiny supervisor, forever.
- **dinit** bets on a modern minimal core: a systemd-style dependency graph
  with proper failure semantics and supervision, without the ecosystem.

This page lines the five up: feature matrix, architecture, command porting
map, and how to choose. The family pages hold the depth — each row below
links to the page that proves it.

## Feature matrix

Features are graded as: full support, partial/emulated, optional, or absent.

| Capability | systemd | sysvinit | OpenRC | runit | dinit |
|---|---|---|---|---|---|
| Dependency graph at boot | yes | via insserv headers | yes (computed per run) | no | yes |
| Dependency semantics at runtime | yes (transactional) | no | partial (stop ordering only) | no | yes (hard/milestone/soft) |
| Parallel startup | yes, graph-driven | partial (startpar batches) | yes (`rc_parallel`) | yes (all runsvs concurrent) | yes, graph-driven |
| Service supervision / auto-restart | yes (`Restart=`) | no | optional (`supervise-daemon`) | yes (always) | yes (`restart`, `smooth-recovery`) |
| Socket activation | yes | no | no | no | partial (socket listening) |
| On-demand activation (path/dbus) | yes | no | no | no | no |
| Timers / scheduling | yes (`.timer`) | no (use cron) | no (use cron) | no (use cron) | no (use cron) |
| Per-service cgroups | yes (v1/v2) | no | optional (v1/v2 integration) | no | partial (newer versions) |
| Structured logging | yes (journald) | no (syslog/bootlogd) | no (syslog, rc.log) | per-service files (svlogd) | optional per-service logs |
| Runlevels / states | targets + compat | runlevels 0-6,S | runlevels (dirs) | stages 1/2/3 + service sets | profiles (boot service + waits-for.d) |
| User session services | yes (`systemctl --user`) | no | no (pair with elogind) | yes (manual runsvdir) | yes (user manager) |
| SysV init script compat | yes (generator) | native | yes (scripts adapted) | no | no |
| Config language | declarative key=value units | POSIX shell | shell + keywords | shell run scripts | declarative key=value |
| Footprint | large (C, many binaries) | small | medium (shell-heavy) | very small (static C) | small (C++) |
| Live dependency evaluation | yes (daemon-reload) | no | yes (recomputed) | no | yes |
| Default distros | most mainstream | Devuan, Slackware, antiX | Gentoo, Alpine, Artix | Void | Chimera, eweOS |

Three structural observations the table hides:

1. **Supervision vs dependencies is the real axis.** sysvinit and OpenRC
   start services; runit supervises them; systemd and dinit do both. That is
   why "my daemon crashed" has five different answers, from "nothing happens"
   (sysvinit) to "restarted within a second" (runit).
2. **The journal gap is bigger than it looks.** Without journald you need
   syslog plus per-service conventions; runit is the only alternative that
   ships a real per-service logging story (svlogd) as part of its model.
3. **Compat layers matter for adoption.** systemd's sysv generator let
   distros switch while packages still shipped init scripts; OpenRC's script
   shape is close enough to sysvinit that porting is mostly `depend()`
   syntax. runit and dinit require real rewrites, which is part of why their
   ecosystems stay smaller.

## Architecture sketches

```
systemd (PID 1, resident manager)
  unit dependency graph ──> transaction engine ──> start units in parallel
        │                                              │
        │ ordering + requires                          │ every service in own cgroup
        ▼                                              ▼
  targets (multi-user, graphical)              supervise: Restart=, KillMode=

sysvinit (PID 1, stateless script runner)
  /etc/inittab ──> /etc/init.d/rc N ──> rcN.d/K* then S* in sequence
        │                                     (insserv .depend.* reorders,
        │ respawn entries only                 startpar runs batches parallel)
        ▼
  getty respawn; services = one-shot shell scripts

OpenRC (PID 1 = sysvinit/openrc-init; openrc-run = dependency engine)
  runlevel dirs (/etc/runlevels/default/*) ──> openrc-run solver
        │                                       │
        │ need/use/want/before/after            ▼
        ▼                                  shell scripts, optional supervise-daemon

runit (PID 1 = runit: stage 1/2/3 machine)
  stage 2: runsvdir /service ──> one runsv per dir ──> ./run (+ ./log/run)
                                     │ restarts forever, 1s backoff
                                     ▼
                               sv client sends control commands

dinit (PID 1 = dinit, resident manager)
  service descriptions (type=process/script/internal/triggered)
        │ depends-on / waits-for / milestone
        ▼
  dependency graph ──> start/stop with failure propagation ──> supervise
```

## Command and concept porting map

| Task | systemd | sysvinit (Debian) | OpenRC | runit | dinit |
|---|---|---|---|---|---|
| Start service | `systemctl start nginx` | `/etc/init.d/nginx start` (or `service nginx start`) | `rc-service nginx start` | `sv up nginx` | `dinitctl start nginx` |
| Stop service | `systemctl stop nginx` | `/etc/init.d/nginx stop` | `rc-service nginx stop` | `sv down nginx` | `dinitctl stop nginx` |
| Restart | `systemctl restart nginx` | `/etc/init.d/nginx restart` | `rc-service nginx restart` | `sv restart nginx` | `dinitctl restart nginx` |
| Status | `systemctl status nginx` | `/etc/init.d/nginx status` | `rc-service nginx status` | `sv status nginx` | `dinitctl status nginx` |
| Enable at boot | `systemctl enable nginx` | `update-rc.d nginx defaults` | `rc-update add nginx default` | `ln -s /etc/sv/nginx /var/service/` | `dinitctl enable nginx` |
| Disable at boot | `systemctl disable nginx` | `update-rc.d nginx disable` | `rc-update del nginx default` | `rm /var/service/nginx` | `dinitctl disable nginx` |
| List services | `systemctl list-units --type=service` | `ls /etc/rc2.d/` | `rc-status --all` | `sv status /var/service/*` | `dinitctl list` |
| Mask/block | `systemctl mask nginx` | `chmod -x /etc/init.d/nginx` | `rc-update del` + remove script | remove symlink (+ `touch down`) | unload / remove description |
| Change system state | `systemctl isolate multi-user.target` | `telinit 3` | `openrc default` | runsvchdir (service sets) | switch boot profile |
| Reload config after edit | `systemctl daemon-reload` | nothing to reload | nothing to reload | rescan within 5s (or restart runsvdir) | `dinitctl reload` |
| Logs | `journalctl -u nginx` | `/var/log/syslog`, bootlogd | syslog + `/var/log/rc.log` | `/var/log/nginx/current` (svlogd) | per-service logfile |
| "What state is the system in?" | `systemctl get-default` / `is-system-running` | `runlevel` | `rc-status` | `sv status` set / stage | `dinitctl status boot` |

## History timeline

| Year | Event |
|---|---|
| 1983 | System V release defines runlevels and `/etc/inittab` |
| 1990s | Linux distros standardize on Miquel van Smoorenburg's sysvinit |
| 2001–2004 | daemontools lineage (DJB) inspires runit (Gerrit Pape) and eventually s6 |
| 2007–2008 | OpenRC extracted from Gentoo baselayout (Roy Marples) |
| 2010 | systemd first release (Poettering, Sievers) |
| 2011 | Fedora 15 ships systemd as default |
| 2011 | Debian squeeze makes insserv dependency-based boot default |
| 2012–2014 | Most major distros announce systemd defaults |
| 2014 | Devuan forks Debian over the init decision |
| 2014–2017 | Ubuntu returns from Upstart to systemd (16.04) |
| 2015+ | Artix, Void and friends consolidate the "init-choice" distro niche |
| 2017+ | dinit development; adopted by Chimera Linux and eweOS |
| 2023 | sysvinit 3.x line (Jesse Smith) keeps traditional init maintained |

## Decision guide

- **You are studying for interviews**: systemd + sysvinit deeply, one
  alternative shallowly. The boot-process, runlevels and service-management
  pages of those two families cover ~90% of questions asked.
- **You operate servers**: systemd is the default almost everywhere; learn
  its debugging path (`systemctl status` → `journalctl -u` → `show`
  properties) until it is muscle memory. Know sysvinit concepts to read
  older documentation and interview questions.
- **You build containers**: no init at all (one process + a zombie reaper
  like tini), or runit for multi-process images; OpenRC-in-container is an
  established pattern for chroot-heavy workflows.
- **You run embedded**: busybox init for the smallest footprints, runit
  where supervision matters and bytes are less scarce.
- **You want init freedom on a distro**: OpenRC is the most "mainstream
  compatible" choice (dependency-aware, script-based); runit the most
  minimal; dinit the most modern; sysvinit the most traditional.
- **You need one killer feature**: supervision with zero config → runit;
  timers/journal/socket activation → systemd; scripts with dependencies →
  OpenRC; small binary with real dependency semantics → dinit.

## Interview Questions

### Q: Why did systemd replace sysvinit despite the controversy?

Because its capability gap became operationally decisive: parallel boot from
a real dependency graph, reliable supervision via cgroups (no more pidfiles
lying about dead daemons), socket activation enabling both parallelism and
lazy start, unified structured logging, and resource control per service.
Distributions weigh maintenance cost too: one resident manager replacing
thousands of package-specific shell scripts reduces variant bugs. The
controversy (scope creep, binary logs) is real but did not outweigh the
capability case for mainstream distros.

### Q: Your daemon dies on a sysvinit system and on a runit system. What happens on each?

On sysvinit: nothing automatic. PID 1 has already handed control to a shell
script that exited; the service stays dead until a monitor (monit, cron,
human) notices. On runit: the per-service runsv supervisor notices within
moments and reruns ./run (with roughly a one-second pause between restarts),
and the crash lands in that service's svlogd log. This is the single most
concrete illustration of the supervision axis.

### Q: What does systemd's SysV compatibility layer do, and what are its limits?

systemd-sysv-generator synthesizes transient service units from
`/etc/init.d` scripts and their LSB headers at daemon-reload/boot, mapping
Required/Should-Start into ordering and runlevel links into enablement.
Limits follow from the model: the script still forks and daemonizes itself,
so systemd supervises only the wrapper — no true Restart= semantics, status
is what the script reports, and per-service cgroups only capture the script's
process tree imperfectly. It is a migration bridge, not a feature.

### Q: Compare how the five systems express "start sshd after the network is up".

sysvinit: static sequence numbers (S20sshd > S10network) or an LSB header
`Required-Start: $network` consumed by insserv. OpenRC: `depend() { need net;
}` (or `use net` for soft ordering). systemd: `After=network-online.target`
plus `Wants=network-online.target` when actual reachability matters —
ordering alone (After=network.target) does not wait for addresses. runit:
no engine — a polling loop in the run script (`sv check network || sleep 1; retry`).
dinit: `depends-on: network` (or milestone semantics for "network is up"
checkpoints). Same sentence, five encodings — and the differences in failure
semantics between them are exactly what interviewers probe.

### Q: When would you deliberately choose NOT systemd on a general-purpose server?

When fleet uniformity is already non-systemd (Devuan/Alpine/Gentoo estates),
when you need supervision more than ecosystem (runit on a minimal appliance
gives you that in a few hundred kilobytes), when auditability of every boot
step as plain shell is a requirement, or when the deployment is a container
where systemd's footprint buys nothing. The honest answer also lists what you
re-add: syslog, cron, a supervisor or monitoring for non-supervised systems,
and manual equivalents for socket activation and timers.

## Key Takeaways

- The five systems differ primarily on two axes: supervision (stateless
  scripts → resident managers) and dependency semantics (static numbers →
  live graphs); every other difference is downstream.
- Command porting between systems is mechanical — the table above covers the
  daily 90%; the concepts behind the commands are what interviews test.
- systemd's ecosystem and sysvinit's transparency are the two poles of the
  debate; OpenRC, runit and dinit each occupy a deliberate middle ground.

## Cross-References

- [Section hub](./README.md) — full page map and distro defaults
- [systemd overview](./systemd/overview-architecture.md) — the resident-engine design
- [sysvinit overview](./sysvinit/overview-history.md) — the traditional scheme
- [sysvinit migration page](./sysvinit/migration-modern.md) — how distros actually switched
- [OpenRC overview](./openrc/overview-architecture.md) — dependency-aware scripts
- [runit overview](./runit/overview-philosophy.md) — supervision-first design
- [dinit overview](./dinit/overview.md) — modern minimal graph manager
- [Boot Process overview](../../os/boot/README.md) — the stages before PID 1
- [Daemon Processes](../../os/processes/daemons.md) — the programs all of this manages

## References

- [systemd project](https://systemd.io/)
- [systemd man pages](https://www.freedesktop.org/software/systemd/man/latest/)
- [sysvinit source (Savannah cgit)](https://git.savannah.nongnu.org/cgit/sysvinit.git/)
- [OpenRC source and man pages](https://github.com/OpenRC/openrc)
- [Gentoo Wiki — OpenRC](https://wiki.gentoo.org/wiki/OpenRC)
- [runit official documentation](http://smarden.org/runit/)
- [Void handbook — runit services](https://docs.voidlinux.org/config/services/index.html)
- [dinit repository and docs](https://github.com/davmac314/dinit)
- [Devuan documentation](https://docs.devuan.org/)
- [s6 supervision suite](https://skarnet.org/software/s6/)
- [Upstart (historical)](http://upstart.ubuntu.com/)
