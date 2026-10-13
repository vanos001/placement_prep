# systemd — Overview and Architecture

## Overview

systemd is the Linux init system and service manager: the program that runs as
PID 1 after the kernel hands over userspace, the program that supervises every
service on the machine, and — increasingly — the name for a family of
background daemons and libraries that surround it. Written by Lennart
Poettering and Kay Sievers (both at Red Hat at the time), it had its first
public release in April 2010 and became the default init of Fedora 15 in May
2011. Today it is the default on Fedora, RHEL and clones, Debian, Ubuntu,
SUSE, Arch and most other mainstream distributions.

The design that made it win is not "it starts things fast" in isolation; it is
that systemd replaced a chain of ad-hoc shell scripts with a single
transactional engine that computes a dependency graph of *units*, starts as
much of it in parallel as the ordering allows, and tracks every process it
spawned in a kernel cgroup so nothing can escape supervision. Socket
activation, on-demand spawning, the binary journal, and per-user service
managers all fall out of that same model.

This page is the map of the territory: what systemd is, which daemons make up
the ecosystem, how the pieces are layered, and how it coexists with the
classic SysVinit world it replaced. The deep dives live in sibling pages —
the boot sequence in [boot-process.md](./boot-process.md), the unit model in
[unit-types.md](./unit-types.md), the operational toolkit in
[systemctl-cli.md](./systemctl-cli.md), and so on.

## Three Roles of One Binary

The `systemd` binary (installed at `/usr/lib/systemd/systemd` on merged-`/usr`
distros; `/lib/systemd/systemd` is a symlink to it or the pre-merge path)
wears several hats depending on how it is invoked and what it is asked to do:

| Role | Invocation context | What it does |
|---|---|---|
| System service manager (PID 1) | Started by the kernel as the default init (`/sbin/init` is a symlink to it) | Loads unit files, computes the boot transaction, supervises all system processes, reaps orphans, handles shutdown |
| Session manager | `systemd --user`, one instance per logged-in user as `user@UID.service` | Runs the user's services, timers, sockets and targets from `~/.config/systemd/user/` and `/usr/lib/systemd/user/` |
| Initrd manager | `systemd` inside the initramfs | Runs early userspace (`initrd.target`), then `switch_root`s into the real root and continues as PID 1 |

Being PID 1 is not incidental. The manager inherits kernel-specific duties
that used to be scattered: it is the default parent for re-parented orphans,
it handles the `SIGRTMIN+` signals that older systems reserved for init
(ctrl-alt-del handling, `kbrequest`), and it is the process whose cgroup
hierarchy anchors every other process on the system. `kill -9 1` is ignored —
with intent — because the manager is expected to keep state consistent even
when individual services misbehave.

The per-user instances matter for interviews: each login session gets a
`session-N.scope` cgroup managed by `systemd-logind`, and each *user* (not
session) gets a full `user@UID.service` manager that supports the same
`.service`, `.timer`, `.socket` and `.target` units as the system manager,
with `systemctl --user`. Users can run daemons, timers and socket-activated
services without root — provided `loginctl enable-linger` has been used, or
they are logged in.

## Design Goals

systemd's design goals explain most of its feature set. Each one addressed a
concrete failure mode of the SysVinit model, where `/etc/init.d/rc` ran
numbered shell scripts strictly sequentially (see
[overview-history.md](../sysvinit/overview-history.md) for that world).

- **Parallel startup driven by a dependency graph.** Instead of `S01foo`,
  `S02bar` ordering encoded in symlink names, each unit declares
  `Wants=`/`Requires=` and `Before=`/`After=`; the manager computes a
  transaction and starts everything not explicitly ordered against each other
  at the same time. Ordering is sparse and explicit; concurrency is the
  default.
- **Socket activation.** systemd creates listening sockets itself, before the
  service that will consume them exists. This decouples start order (a client
  can talk to the socket and be queued by the kernel while its server is still
  starting), enables on-demand activation, and allows privileged-port binding
  without the service holding root. See [socket-activation.md](./socket-activation.md).
- **cgroup-based process tracking.** Every unit gets a cgroup; membership, not
  a PID file, defines "the service's processes". Daemons can no longer escape
  supervision by double-forking, and shutdown can reliably kill the whole
  group. See [cgroups-resource-control.md](./cgroups-resource-control.md).
- **On-demand activation.** Socket units, path units, timer units and bus
  activation mean services need not run until something actually needs them.
  Hardware events via udev similarly spawn `.device`-triggered services.
- **Transactionality.** A boot or an `isolate` is one atomic transaction with
  job deduplication and cycle detection — the engine either installs a
  consistent job set or fails loudly rather than half-starting a graph.
- **Unified logging.** `systemd-journald` captures stdout/stderr of every
  managed process plus kernel and syslog streams into a structured,
  indexed journal. See [journald.md](./journald.md).
- **Declarative configuration.** Unit files are small key=value files with a
  documented grammar, drop-in overrides, and specifiers — not shell code with
  implicit global state.

The SysV contrast worth memorizing: SysVinit ordered services with two-digit
sequence numbers and coordinated them through `start-stop-daemon` PID-file
guessing; systemd orders them with explicit `After=` edges and coordinates
them through sockets, D-Bus names, and cgroups. Both approaches "work", but
only the second one can start two independent subsystems simultaneously
without a human renumbering scripts.

## Component Map

The name "systemd" is attached to a family of daemons, each a separate
process shipped by the same project. Knowing one line about each is table
stakes for Linux roles:

| Component | One-line role |
|---|---|
| `systemd` (PID 1) | System and service manager: unit loading, transactions, supervision, shutdown |
| `systemd-journald` | Receives logs (kmsg, `/dev/log`, stdout/stderr of units) and stores the structured journal |
| `systemd-udevd` | Applies udev rules to kernel `uevent`s, manages device nodes in devtmpfs, emits `.device` units |
| `systemd-logind` | Tracks logins, seats and sessions; creates `session-N.scope` and `user@UID.service`; powers off on lid close |
| `systemd-networkd` | Configures network interfaces (addresses, routes, DHCP, links) from `systemd.network` files |
| `systemd-resolved` | Local DNS stub resolver (127.0.0.53): per-link DNS, LLMNR, mDNS, DNSSEC option |
| `systemd-timesyncd` | Minimal SNTP client keeping the system clock synced |
| `systemd-tmpfiles` | Applies `tmpfiles.d` rules to create/clean volatile and temporary files |
| `systemd-sysusers` | Provisions system users and groups from `sysusers.d` at boot, no shell scripts |
| `systemd-machined` | Registers and tracks VMs and containers ("machines") with their cgroups |
| `systemd-hostnamed` / `systemd-timedated` / `systemd-localed` | D-Bus gateways for hostname, time/NTP and locale settings (backends of `hostnamectl`, `timedatectl`, `localectl`) |
| `systemd-coredump` | Captures and compresses process cores, indexes them for `coredumpctl` |
| `systemd-oomd` | Userspace OOM killer driven by PSI pressure metrics, kills overloaded cgroups before the kernel must |
| `systemd-homed` | Manages portable, LUKS-backed home directories (still optional/experimental) |
| `systemd-userdbd` | Multiplexes user/group lookups over JSON user records and NSS |
| `systemd-fsck` (`systemd-fsck@.service`, `systemd-fsck-root.service`) | Runs filesystem checks at boot, parallelized per filesystem; Debian/Ubuntu add a `systemd-fsckd` progress multiplexer |
| `systemd-sysctl`, `systemd-modules-load` | Apply `sysctl.d` and `modules-load.d` settings during `sysinit.target` |
| `systemd-shutdown` (PID 1's final exec) | Last-stage binary: unmounts, detaches loop/DM devices, disables swaps, then calls `reboot(2)` |

A few of these deserve their own page in this book: journald, udev, resolved
and networkd each have dedicated chapters (see the Cross-References at the
bottom of this page).

## Architecture Layers

The components layer roughly like this. The manager sits on the kernel
(cgroups, namespaces, epoll, udev events), talks to long-lived daemons over
D-Bus (and private sockets for journald), exposes the stable
`org.freedesktop.systemd1` API, and ships client libraries (`libsystemd`'s
`sd-*` family, plus `libudev`) so third-party daemons can integrate instead of
reimplementing supervision, logging and activation.

```
+-------------------------------------------------------------------------+
|  CLI tools:  systemctl  journalctl  udevadm  resolvectl  loginctl       |
|              networkctl  timedatectl  hostnamectl  coredumpctl busctl   |
+-----------------------+-------------------------------------------------+
                        | D-Bus / private sockets
+-----------------------v-------------------------------------------------+
|  PID 1: systemd (system service manager)                                |
|    - unit loader (fragments, drop-ins, generators)                      |
|    - transaction engine (job queue, cycle detection)                    |
|    - per-unit state machines + supervision (Exec*, Restart, Kill*)      |
|    - cgroup tree: -.slice -> system.slice / user.slice / machine.slice  |
+----+-------------+--------------+--------------+------------------------+
     |             |              |              |
     v             v              v              v
 journald       udevd          logind        networkd / resolved /
 (logs)      (devices)     (sessions)      timesyncd / oomd / ...
     ^                                                          ^
     | sd_journal, sd_bus, sd_notify, sd_listen_fds             |
+----+----------------------------------------------------------+--------+
|  libsystemd (sd-*), libudev  -> used by sshd, nginx, containers, ...    |
+-------------------------------------------------------------------------+
|  kernel: cgroups v1/v2, namespaces, devtmpfs, kmsg, netlink uevents     |
+-------------------------------------------------------------------------+

  Parallel session managers: user@1000.service (systemd --user)
    - same engine, user bus, units from /usr/lib/systemd/user +
      ~/.config/systemd/user, session scopes from logind
```

Two details that trips people up in interviews: the user manager is *not* a
child of the user's shell — it is started by logind as a system service — and
the daemons in the map are peers, not children of the unit tree that matters;
`systemd-journald.service` is itself a unit supervised by the same manager.

## The Unit Abstraction

Everything the manager controls is a *unit*: a named configuration object with
a small state machine (`inactive`, `activating`, `active`, `deactivating`,
`failed`) and a type suffix. Services are `.service`, but so are listening
sockets (`.socket`), mount points (`.mount`), timers (`.timer`), device
appearances (`.device`), slices of the cgroup tree (`.slice`), and grouping
nodes (`.target`). The full matrix — twelve types, their backings and their
key directives — is the subject of [unit-types.md](./unit-types.md).

"Everything is a unit" is also what lets systemd absorb the older ecosystems
without dropping them:

- **SysV init scripts.** A generator (`systemd-sysv-generator`) wraps
  `/etc/init.d/*` scripts into transient-looking `.service` units, translating
  LSB header dependencies into native ones, so `systemctl start foo` works
  even for legacy scripts. See [init-scripts.md](../sysvinit/init-scripts.md)
  for what those scripts look like on the other side.
- **`/etc/rc.local`.** The classic "run my stuff at the end of boot" hook is
  available as `rc-local.service`, which is ordered after `multi-user.target`
  and executes `/etc/rc.local` if it exists and is executable.
- **runlevels.** `runlevel(8)`, `telinit(8)` and the `runlevel*.target`
  aliases keep old muscle memory (and old monitoring scripts) working; the
  mapping is covered in [targets-runlevels.md](./targets-runlevels.md).
- **cron.** Not absorbed, but `systemd.timer` units cover most scheduled-job
  use cases with calendar events and persistent catch-up semantics; the
  trade-offs are discussed in [timers.md](./timers.md) and
  [cron.md](../../admin/cron.md).
- **fstab.** `systemd-fstab-generator` turns `/etc/fstab` entries into native
  `.mount`/`.automount`/`.swap` units, so mount configuration has one source
  of truth and one set of timeouts and dependencies.

## Distro Adoption

| Distribution | First default systemd release | Notes |
|---|---|---|
| Fedora | 15 (May 2011) | First distribution to ship it as default; upstream's home turf |
| openSUSE | 12.1 (November 2011) | Early co-designer; both Poettering and Sievers had SuSE history |
| Arch Linux | 2012 (October) | Move replaced the initscripts package wholesale |
| RHEL / CentOS | 7 (June 2014) | Enterprise consolidation point; SLES 12 followed in late 2014 |
| Debian | 8 "Jessie" (April 2015) | Adopted after the 2013-2014 Technical Committee vote |
| Ubuntu | 15.04 "Vivid" (April 2015) | Replaced Upstart, which had been default since 11.04/12.04 |

The common thread: adoption followed a functional decision — the dependency
graph, socket activation and cgroup tracking solved real boot and supervision
problems — not a marketing push. Debian's Technical Committee vote and the
resulting Devuan fork (below) are the canonical case study for "architecture
arguments that split communities".

## The Init-Freedom Controversy

systemd has been the most contested piece of Linux plumbing of its era. The
criticisms, in roughly decreasing order of technical content:

- **Scope creep.** The project absorbed DNS, NTP, login sessions, network
  configuration, home directories. Critics saw an ecosystem monoculture; the
  project's position is that these daemons are independently enabled and
  replaceable (Debian runs NetworkManager instead of networkd; sssd or
  unbound can front resolved), and that "systemd the project" is not "systemd
  the PID 1 binary".
- **Binary journal.** `journald`'s indexed binary format replaced plain text
  files; critics disliked losing `grep`-ability until they learned
  `journalctl` exposes structured queries and the `forward-to-syslog` switch
  preserves classic files. See [journald.md](./journald.md).
- **Coupling with GNOME/udev/D-Bus.** Real but historically overstated; udev
  remains a separate repository and logind has been run against non-systemd
  init in limited setups.
- **Governance and tone.** The 2014 flamewars were as much about process as
  engineering, and the Debian vote plus the **Devuan** fork (Debian without
  systemd, first stable release 2017) are the institutional outcomes. Devuan
  ships sysvinit or OpenRC by default — see
  [migration-modern.md](../sysvinit/migration-modern.md) for what moving away
  from systemd actually costs, and [../openrc/overview-architecture.md](../openrc/overview-architecture.md)
  for the main open alternative.

A balanced interview answer: systemd the *service manager* is a clear
engineering win that effectively every serious deployment runs; systemd the
*ecosystem* is a set of optional, individually replaceable daemons; the
controversy mostly reduced to distro-level default choices, which are
reversible per-daemon and per-config.

## Release Cadence and Versioning

Version numbers are simple integers incremented per release: v245 (2020),
v250 (2021), v252 (2022), v255 (December 2023), v256 (June 2024), v257
(November 2024), v258 during 2025. The historical cadence of a release every
~3 months (2016-2019 era) has settled to roughly two major releases a year.
Debian 12 ships 252, Debian 13 ships 257; RHEL 9 is based on 250-ish; the
exact version per distro is worth checking with `systemd --version` before
quoting feature availability.

What stays stable — deliberately — is the command-line and API surface:
`systemctl` and `journalctl` verbs, unit file directives, the
`org.freedesktop.systemd1` D-Bus API, and `sd_notify`/`sd_listen_fds`
protocols. Features are deprecated with log warnings (and `NEWS` entries)
long before removal; unit files written for v219-era systems generally load
unmodified on v257. Newer additions to know about: `Type=notify-reload`
(v253), `systemctl freeze`/`thaw`, soft-reboot (`systemctl soft-reboot`),
`Upholds=` dependencies, and the `systemd-oomd`/`systemd-homed` daemons.

## Interview Questions

### Q: Why did systemd replace SysVinit — what specific technical problems did it solve?

Sequential boot was the visible symptom; the deeper issues were supervision
and ordering. SysVinit started scripts one at a time using sequence-number
symlinks, could not express "start these two independently", tracked daemons
by guessing PID files, and offered no on-demand activation. systemd models the
boot as a transaction over an explicit dependency graph (parallelism where
ordering permits), tracks processes by cgroup membership so daemons cannot
escape, and uses socket/bus/path activation to defer starting things until
they are needed. Those three mechanisms — graph, cgroups, activation — are the
answer, not "it boots faster", which is a consequence rather than a cause.

### Q: What is the difference between systemd as PID 1 and the surrounding daemons?

The PID 1 binary is the service manager: it loads unit files, builds
transactions, supervises processes and drives shutdown. Everything else in
the family — journald, udevd, logind, networkd, resolved, timesyncd, oomd and
friends — is an ordinary daemon supervised *by* that manager, communicating
over D-Bus or local sockets. They are individually disableable and replaceable
(you can run unbound instead of resolved, NetworkManager instead of networkd),
which is the standard rebuttal to "systemd does everything" objections.

### Q: What is user@.service and how does a user get their own systemd instance?

`user@UID.service` is a system-level unit that runs a full `systemd --user`
manager for that UID. `systemd-logind` starts it on the user's first login
(and `pam_systemd` sets up the session scope), and it manages units from
`/usr/lib/systemd/user/` and `~/.config/systemd/user/` on the user's private
D-Bus. Users control it with `systemctl --user`. Without an active session the
manager is normally stopped; `loginctl enable-linger <user>` pins it so
user services and timers run even when logged out — the standard trick for
running user-owned daemons on servers.

### Q: How does systemd stay compatible with SysVinit scripts and old habits?

Three mechanisms. First, `systemd-sysv-generator` exposes every `/etc/init.d`
script as a `.service` unit, honoring its LSB header dependencies, so
`systemctl start foo` and boot-time ordering work for legacy scripts. Second,
`runlevel(8)`/`telinit(8)` and the `runlevel*.target` aliases preserve the
runlevel interface, with runlevel data maintained in utmp. Third, well-known
hooks like `/etc/rc.local` survive as `rc-local.service`. The unit-file layer
itself is the long-term replacement, but the compat layer means nothing breaks
overnight.

### Q: What are the stable interfaces of systemd that third-party software should rely on?

The `systemctl`/`journalctl` command surfaces, the unit file grammar and its
directives, the `org.freedesktop.systemd1` D-Bus API, and the library
protocols: `sd_notify` readiness/watchdog messages, `sd_listen_fds` socket
passing, and the journal's native API. These are documented as supported
interfaces and kept backward compatible across releases; anything else
(internal state files, cgroup layout details) can change between releases.

### Q: Is systemd monolithic because it ships DNS, NTP and logind?

No — it is a suite of separate daemons under one project. The PID 1 manager
needs none of them to run: you can boot a system where networkd, resolved,
timesyncd and even logind components are masked or replaced, and distributions
do exactly that per their defaults. The honest criticism is bundling and
governance (one upstream shipping many default-ish components concentrates
influence), not technical coupling; each daemon is a distinct process with a
distinct configuration format and lifecycle.

## References

- [systemd(1) index — all manager and daemon man pages](https://www.freedesktop.org/software/systemd/man/latest/)
- [systemd.unit(5) — the unit file grammar everything else hangs off](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [bootup(7) — the boot and shutdown phases the manager drives](https://www.freedesktop.org/software/systemd/man/latest/bootup.html)
- [systemctl(1) — the primary client tool](https://www.freedesktop.org/software/systemd/man/latest/systemctl.html)
- [daemon(7) — systemd's daemon-writing conventions (sd_notify, socket activation)](https://www.freedesktop.org/software/systemd/man/latest/daemon.html)
- [systemd.unit(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.unit.5.en.html)
- [systemctl(1) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemctl.1.en.html)
- [daemon(7) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/daemon.7.en.html)
- [github.com/systemd/systemd — source, NEWS files per release](https://github.com/systemd/systemd)
- [systemd.io — project homepage and design write-ups](https://systemd.io/)

## Cross-References

- [init-systems hub](../README.md) — section overview and reading order for all init families.
- [Init system comparison](../comparison.md) — side-by-side feature matrix: systemd vs sysvinit vs openrc vs runit vs dinit.
- [systemd hands-on (admin)](../../admin/systemd.md) — practical everyday management; this section goes deeper per topic.
- [systemd internals (admin)](../../admin/systemd-internals.md) — the unit/transaction engine internals this page only maps.
- [Init systems overview (os/boot)](../../../os/boot/init-systems.md) — where the init choice sits in the boot pipeline.
- [SysVinit overview and history](../sysvinit/overview-history.md) — the sequential-script model systemd replaced.
- [The systemd boot process](./boot-process.md) — kernel-to-PID-1 handover and the target timeline.
- [Unit types](./unit-types.md) — the twelve unit types this page introduced by name.
