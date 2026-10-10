# sysvinit — Overview and History

## Overview

sysvinit is the classical UNIX System V initialization system ported to Linux: a single small program, `/sbin/init`, runs as PID 1, reads `/etc/inittab`, and drives the system through a fixed set of runlevels by executing shell scripts. Every service start on a sysvinit machine is ultimately the invocation of a human-readable shell script under `/etc/init.d`, usually fronted by an LSB metadata header and sequenced by symlinks in `/etc/rc0.d` through `/etc/rc6.d` and `/etc/rcS.d`. The design dates back to AT&T UNIX and predates nearly every other component of a modern Linux distribution, which is precisely why it is still worth studying: it defined the vocabulary (runlevels, init scripts, single-user mode, respawn) that every later init system had to either adopt, emulate, or explicitly argue against.

Unlike systemd or runit, sysvinit's PID 1 is deliberately *stateless between events*. It does not supervise services, it does not maintain a dependency graph in memory, and it does not activate anything on demand. It does exactly four things well: run boot scripts in order, (re)start the processes listed in `inittab` as `respawn` entries (most importantly the gettys that give you login prompts), react to a handful of signals (SIGPWR from UPS monitoring, SIGINT from Ctrl-Alt-Del, SIGWINCH from special key combinations), and reap orphaned children forever. A daemon that crashes stays dead until a script or an administrator starts it again. This limitation is not an accident; it is the design, and understanding why it was acceptable for thirty years — and why it eventually stopped being acceptable — is the key to understanding the entire init-system landscape.

This page is the entry point of the sysvinit section of this knowledge base. It covers the historical lineage, the component inventory (which binary does what, and which Debian package ships it), the design philosophy and its trade-offs, and where sysvinit still runs today. The mechanics — the boot sequence, `inittab` grammar, runlevels, init script conventions, LSB headers, `rc*.d` symlink arithmetic, and the management tooling — each get their own dedicated page, cross-referenced throughout.

## Historical Lineage

### System III and System V: runlevels are born

The runlevel model comes from AT&T UNIX System III (released 1982–1983), which introduced `inittab` as the file a PID 1 init program would read at boot and on state changes. System V (1983 onward) carried this forward and standardized the runlevel machinery as it exists today: numbered system states 0–6, `S` for single user, an `/etc/inittab` grammar of `id:runlevels:action:process`, per-runlevel directories of start/kill scripts, and the convention that runlevel 0 halts the machine while runlevel 6 reboots it. Commercial System V derivatives — Solaris before SMF, AIX, HP-UX — all shipped recognizably the same machinery, which is why an administrator from 1992 can still read a Debian `inittab` in 2024 without a manual.

The core insight of System V init was that a machine has a small number of *coarse system states*, and that switching between them is a first-class operation: entering a state means starting a defined set of services and stopping everything not in it. This gave UNIX administrators a vocabulary — "boot to runlevel 3", "drop to single-user" — that persists verbatim in systemd's targets ("runlevel 3" maps to `multi-user.target`) and in OpenRC's runlevels.

### BSD-style init: the contrast

The BSD side of the UNIX family took a much simpler route: `init` performed a single pass through `/etc/rc`, which sourced a handful of other shell files (`/etc/rc.local` being the classic site-administrator hook), and then spawned gettys from a hard-coded table. There were no runlevels in early BSD — no way to say "start networking but not NFS" without editing `rc.local` — and no standardized way for packages to register services. The historical fix for package integration was convention and discipline; the modern fix (FreeBSD's `rc.d` framework with `rcorder` computing a dependency order at boot time) addresses ordering but still has no runlevel concept.

This distinction matters historically because the two models collided on Linux and the System V model won the early war: Slackware is the famous exception, running the sysvinit *program* with a BSD-style *script layout* (see below), while every major 1990s distribution — Debian, Red Hat, SUSE, Caldera, Mandrake — standardized on System V runlevels and `/etc/init.d`. The full taxonomy of init systems, including where the BSD approach survives, is covered in the section hub and in [os/boot/init-systems.md](../../../os/boot/init-systems.md).

### The Linux sysvinit line: 1991 to today

The sysvinit used on Linux is not a port of AT&T source code; it is a clean-room reimplementation in C, started around 1991 by **Miquel van Smoorenburg**. His implementation (`init`, `telinit`, `shutdown`, `halt`, `runlevel`, `pidof`, `killall5`, `sulogin` and friends) became *the* sysvinit — the one shipped by every Linux distribution for two decades. Miquel maintained it from version 1.x in the early 1990s through 2.86 (2004), after which development slowed sharply. The 2.88dsf line (2009–2014) was maintained largely by the Debian team while upstream was dormant, which is why those version strings carry the `dsf` suffix.

Since roughly 2014 the project has been maintained by **Jesse Smith**, who resumed regular releases (2.89, 2.90, ...) and moved the code to a git repository on Savannah. Version numbering jumped to the 3.x line in late 2021; **3.09 shipped in late 2023**, including accumulated bug fixes and security hardening. The project is alive in the sense of being maintained and released — it is simply *feature-stable*: its scope is what it was in 1995, and its maintainer explicitly keeps it small. Current release tarballs and the source browser live at `git.savannah.nongnu.org/cgit/sysvinit.git/`.

| Era | Version(s) | Maintainer | Notes |
|---|---|---|---|
| 1991–2004 | 1.x – 2.86 | Miquel van Smoorenburg | Definitive implementation; 2.86 was the long-stable release shipped by Debian sarge/etch |
| 2009–2014 | 2.88dsf | Debian team (P. Reinholdtsen et al.) | Upstream dormant; `dsf` suffix marks the Debian-maintained fork line |
| 2014–2021 | 2.89 – 2.97 | Jesse Smith | Development resumed; hardening and cleanup releases |
| 2021–present | 3.00 – 3.09+ | Jesse Smith | 3.x line; 3.09 released late 2023; git on Savannah |

## Design Model: a stateless PID 1

`/sbin/init` under sysvinit is best understood as an *event-driven script runner*, not a service manager. The events are: boot, `telinit` requests, child exits, and a small set of signals. For each event it consults `/etc/inittab` and does exactly what the matching entries say, then forgets about the service again:

- **Boot and runlevel changes** are handled by running `/etc/init.d/rc <N>`, which walks `/etc/rcN.d` (and `/etc/rcS.d` at boot) in symlink-name order, calling each init script once with `start` or `stop`. There is no runtime dependency engine: ordering is purely the lexical order of symlink names (or, on Debian since squeeze, a precomputed dependency order that *insserv* derives from LSB headers and stores in static `.depend.*` files — still not runtime, still static).
- **Respawn entries** (gettys above all) are the only supervision sysvinit does: if the process for a `respawn` entry exits, init starts it again. Even here it is primitive — a respawn loop is throttled (init delays if a process respawns too fast) rather than understood.
- **Everything else is the kernel's problem.** A crashed `sshd` is simply gone. `cron` does not notice. PID 1 does not notice. Nothing notices until a monitoring system or a user does. This is the single most important behavioral difference from systemd (unit supervision with restart policies), runit/s6 (per-service supervisors), and Dinit (dependency-aware supervision).

The consequences of statelessness, spelled out:

1. **No service state tracking.** "Is the service running?" is answered by running the init script's `status` action (or by `pidof`), not by asking PID 1. There is no runtime database equivalent to systemd's unit state.
2. **No dependency maintenance at runtime.** If the database you depend on dies, nothing stops or restarts your application. Dependencies exist only as *boot-time ordering* encoded in symlink numbers or LSB headers.
3. **No on-demand activation.** A service must be started to be used. There is no socket-activation equivalent (systemd's answer), no bus activation, nothing listening on behalf of a stopped service.
4. **No aggregation of output.** A service's stdout/stderr goes wherever its init script redirects it — usually a log file via syslog — and boot output goes to the console unless `bootlogd` captures it.

These four absences, repeated across thousands of production incidents, are exactly what the successor designs set out to fix — each in a different direction: systemd added supervision *and* dependency graphs *and* activation; OpenRC kept the shell-script model but added a real dependency engine; runit and s6 kept everything minimal but made supervision the whole point. The trade-offs are compared in detail on the hub and comparison pages linked below.

## The sysvinit Program versus the SysV Conventions

A recurring source of confusion in interviews and in distribution documentation is that "sysvinit" names two separable things. The **program** is Miquel van Smoorenburg's `/sbin/init` — a generic runlevel engine that reads `inittab` and knows nothing about directories of symlinks. The **conventions** are the distribution-era layers built on top: `/etc/init.d` scripts, LSB headers, `/etc/rc0.d`–`/etc/rc6.d` symlink farms, `update-rc.d`/`chkconfig` management tools. Only the conventions are standardized across distributions; the program is identical everywhere, but what it is *told to run* differs enormously.

| Dimension | BSD-style init | System V init model |
|---|---|---|
| State model | No runlevels; one boot sequence | Runlevels 0–6, S, plus ondemand a/b/c |
| Configuration | `rc` shell files, hard-coded table | `inittab` grammar: `id:runlevels:action:process` |
| Service integration | Edit `rc.local` / hook files | Drop a script in `/etc/init.d`, add `rc*.d` links |
| Ordering | Single pass; later `rcorder` (FreeBSD) | Symlink sequence numbers; later LSB headers + insserv |
| Shutdown | `reboot`/`halt` run rc stop files; historically ad hoc | Runlevels 0 and 6 are states like any other; K scripts stop services |
| Package story | Weak historically (convention-driven) | Strong (update-rc.d / chkconfig / policy layers) |
| Where it survives | FreeBSD/NetBSD rc.d, Slackware layout, some embedded | Debian/Devuan/RHEL≤6 (archived), most textbooks |

The practical consequence: when someone says "this distro uses sysvinit," you should ask *which layer*. Debian (with `sysvinit-core`) and Devuan use both layers — the program plus full SysV conventions. Slackware uses only the program, mapping runlevels onto monolithic BSD-style scripts. And conversely, systems like OpenRC keep *conventions* resembling the SysV ones (runlevels, `/etc/init.d` scripts) while completely replacing the program. Every comparison in the rest of this section should be read with this layer split in mind.

## Component Inventory

sysvinit is not one binary but a small family of cooperating utilities, spread across several packages on Debian. Knowing which package owns which tool matters when you build a minimal system or debug a container where "half of sysvinit" is missing. The table reflects Debian bookworm packaging (see the verified man page inventory for the source of the package attributions):

| Component | Role | Debian package |
|---|---|---|
| `/sbin/init` | PID 1: reads `inittab`, runs `rc`, spawns gettys, handles signals | sysvinit-core |
| `/sbin/telinit` | Symlink to `init`; the runtime control interface (`telinit q`, `telinit 3`) | sysvinit-core |
| `/sbin/runlevel` | Prints current and previous runlevel from utmp | sysvinit-core |
| `/sbin/shutdown` | Scheduled shutdown/reboot with wall notifications and `/run/nologin` | sysvinit-core |
| `/sbin/halt` / `reboot` / `poweroff` | One multiplexed binary; `reboot`/`poweroff` call `halt` with different flags | sysvinit-core |
| `/sbin/sulogin` | Single-user shell login (prompts for root password) | util-linux |
| `/sbin/agetty` (aka `getty`) | Terminal login prompt spawner, driven by `inittab` respawn entries | util-linux |
| `/sbin/bootlogd` | Copies console output to `/var/log/boot` during boot | bootlogd |
| `/bin/pidof` | Find PIDs of running programs by name | sysvinit-utils |
| `/sbin/killall5` | Signal every process except those in the caller's session (used by rc scripts) | sysvinit-utils |
| `/bin/last` / `/bin/lastb` | Read login history from wtmp / failed logins from btmp | util-linux |
| `/usr/bin/mesg` | Control write access to your terminal | util-linux |
| `/usr/bin/wall` | Broadcast a message to all terminals (used by shutdown) | bsdutils |
| `/sbin/fstab-decode` | Decode fstab-encoded arguments (used by fsck/mount glue in rc scripts) | sysvinit-utils |
| `/lib/init/init-d-script` | `/bin/sh` interpreter for declarative init scripts | sysvinit-utils |
| `/lib/lsb/init-functions` | Shell library providing `log_daemon_msg`, `log_end_msg`, etc. | sysvinit-utils |
| `/usr/bin/login` | The login program getty execs | login |
| `startpar` | Runs rc scripts in parallel batches (optional, used by `rc` when configured) | startpar |
| `update-rc.d`, `invoke-rc.d`, `service` | Link management, policy-checked dispatch, portable wrapper | init-system-helpers |
| `insserv` | Dependency-based boot sequencing from LSB headers | insserv |

Note the deliberate layering: `sysvinit-core` is the init system proper, `sysvinit-utils` is the toolbox that stays useful even under systemd (Debian's systemd systems still ship `pidof` and `killall5` because other scripts call them), and `init-system-helpers` is the init-system-agnostic policy layer. On a systemd-based Debian, installing `sysvinit-core` and removing `systemd-sysv` switches PID 1 while keeping every one of these tools in place — the swap is designed to be that surgical.

## A First Tour of the Tools

The fastest way to internalize the component inventory is to run it. On a sysvinit-based Debian (or a chroot with `sysvinit-core` installed), the following session exercises the main actors; each command is annotated with the layer it belongs to:

```console
$ cat /etc/debian_version            # context: this is a bookworm system
12.5

$ ps -p 1 -o pid,comm,args           # who is PID 1?
  PID COMMAND         ARGS
    1 init            /sbin/init

$ runlevel                           # state query: previous and current
N 2                                  # N = no previous (fresh boot), now level 2

$ telinit q                          # control: re-read /etc/inittab (no state change)

$ ls -l /sbin/halt /sbin/reboot /sbin/poweroff | awk '{print $9, $10, $11}'
halt  ->
reboot -> halt                       # one binary, different names select the action
poweroff -> halt

$ ls /etc/rc2.d/ | head -5           # conventions: per-runlevel start/stop links
S01bootlogs
S01cron
S01dbus
S01rsyslog
S02ssh

$ invoke-rc.d cron status            # policy-checked dispatch into /etc/init.d
cron is running.

$ pidof cron                         # sysvinit-utils toolbox, init-independent
612

$ last -x -n 3 reboot                # boot accounting from wtmp
reboot   system boot  5.10.0-21-amd64  Tue Mar 12 09:14   still running
```

Two things to notice. First, the state queries (`runlevel`, `pidof`, `last`) never talk to PID 1 — they read utmp/wtmp files or scan `/proc`, which is the statelessness of the design made visible at the command line. Second, the dispatch layer (`invoke-rc.d`, `service`) exists *between* the user and the scripts precisely so that policy (a `policy-rc.d` file, a chroot guard) can intercept; calling `/etc/init.d/cron` directly bypasses that policy, which is sometimes exactly what you want and sometimes a mistake — the tooling page covers the difference.

## Where sysvinit still runs

- **Devuan** — the Debian fork created specifically to drop systemd; sysvinit is its default init, with OpenRC and runit offered as options. Its administration documentation lives at `docs.devuan.org`.
- **Debian** — systemd is the default, but bookworm still ships `sysvinit-core` as a fully supported alternative init: install it, make sure `systemd-sysv` is not installed, and the system boots with sysvinit. This is documented in the Debian policy and release notes rather than being a fringe hack.
- **Slackware** — the longest-standing holdout. Slackware runs the sysvinit *program* but organizes scripts BSD-style: `inittab` maps each runlevel to a single monolithic script (`rc.S` for setup, `rc.M` for multiuser, `rc.K` for single user, `rc.4` for X), and packages drop hook files into `rc.d`. A cautionary example that the *program* and the *philosophy* are separable.
- **antiX, PCLinuxOS** — long-standing desktop distributions built on the no-systemd / traditional-script path respectively.
- **Embedded and minimal Linux** — where you cannot afford the full toolbox, BusyBox provides its own tiny `init` that speaks a simplified `inittab` dialect; see [busybox.md](../../binaries/busybox.md) for that variant.

The upstream project itself is maintained but conservative: bug fixes, portability, and security hardening; no new architecture. That stability is a feature for the distributions that depend on it — they get CVE fixes without behavioral surprises.

## Philosophy and Trade-offs

The case *for* sysvinit is the case for shell scripts, and it is stronger than younger engineers assume:

- **Auditability.** Every boot-time action is a plain script you can `cat`. There is no declarative unit file semantics to learn, no generator layer, no compiled-in defaults. What you read is what runs.
- **Predictability.** Boot order is a total order defined by symlink names. Two sysvinit machines with the same `/etc/rc2.d` boot in the same order, every time. Debugging "what happened at boot" is reading a sequence you can replay by hand (`/etc/init.d/foo start`).
- **Zero coupling.** PID 1 has no state to corrupt, no database to fsck, no daemon to restart. If init itself misbehaves, it is 4,000 lines of C, not a service bus. A sysvinit system has no "PID 1 problem" to debug.
- **Shell-script composability.** An administrator's whole customization is one file (`/etc/rc.local` or a hand-written `/etc/init.d` script) with no new format to learn.

### The shell script as the unit of work

Everything above follows from one design decision: the unit of work is a POSIX shell script, not a process model. That choice has a long tail of consequences worth enumerating explicitly, because every successor init system is, in a sense, an answer to one or more of them:

| Consequence | Where it hurts | How successors respond |
|---|---|---|
| A script can do anything | Parallelization is unsafe: two scripts may race on the same resource | systemd: units declare capabilities; OpenRC: dependency graph gates execution |
| A script's cost is unknown | One hanging mount blocks the whole boot | systemd: per-unit timeouts; OpenRC: `rc_parallel` plus per-service knobs |
| No process identity | "Is cron running?" means pattern-matching `ps` output, with classic false positives | systemd: cgroup membership is authoritative; runit: supervisor owns the child |
| No output contract | Boot logs vanish into console scrollback unless bootlogd runs | systemd: journal captures everything; journald indexes it |
| State lives outside PID 1 | Tools reconstruct state from utmp, pidfiles, and `ps` at every query | systemd: unit state is a first-class in-memory object |

The costs are equally concrete:

- **Serial boot.** Scripts run one at a time in name order; a slow script (a hanging NFS mount, an fsck) delays everything after it. Dependency-based sequencing (insserv) and parallel batch execution (startpar) mitigate but never solve this, because the *unit of work* is still a script that can do anything.
- **No supervision.** As discussed above, a dead service stays dead. Long-running production systems need an external watchdog or a human.
- **Dependency encoding is manual and static.** Someone must write `Required-Start: $remote_fs $network` and keep it truthful, and that metadata is only consulted when regenerating boot order — never at runtime.
- **Coarse state model.** Runlevels are global: a service is in a runlevel or it is not. You cannot express "web and database, but not mail" without inventing a custom runlevel, and you cannot change one service's state without potentially touching dozens (a full `rc` transition stops and starts whole sets).

These trade-offs are not strawmen to knock down — for a single-user workstation or a small server in 1995, the sysvinit bargain was excellent. The pages that follow treat its machinery with the respect it deserves, while the comparison material shows, line by line, how systemd's units, OpenRC's dependency engine, and runit's supervisors each attack a specific limitation identified here.

The boot-time data flow, end to end:

```
kernel
  |
  v
/sbin/init (PID 1)  -- opens /dev/console, installs signal handlers
  |
  +-- reads /etc/inittab
  |
  +-- si::sysinit  --> /etc/init.d/rcS  --> /etc/rcS.d/S*   (one-shot setup:
  |                                                     fsck, mounts, udev, lo)
  |
  +-- initdefault --> runlevel 2 (Debian default)
  |
  +-- l2:2:wait   --> /etc/init.d/rc 2 --> /etc/rc2.d/
  |                       K*  (stop links: run on transitions out)
  |                       S*  (start links: run in NN order)
  |                              each link -> /etc/init.d/<service>
  |
  +-- respawn entries --> getty tty1..tty6 (restarted whenever they exit)
  |
  +-- waits forever: reaps orphans, reacts to SIGPWR / SIGINT / SIGWINCH
```

## Vocabulary sysvinit Gave the Industry

A final reason the history matters: the vocabulary. An entire generation of Linux operational language was coined by this subsystem, and the words survive even where the implementation does not. "Runlevel" survives as systemd targets (`multi-user.target` answers to runlevel 3, with `systemctl isolate` as `telinit`). "Init script" survives as a compatibility layer — `service`, `/etc/init.d` scripts, and systemd's sysv-generator on distributions that kept them. "Single-user mode" survives as `rescue.target`. "Respawn" survives as `Restart=always`. "getty" survives unchanged, name and job. "The system is at runlevel 1" is still how a 2024 on-call engineer describes a 1991 concept.

When you read the remaining pages of this section, you are reading the original definitions of these terms. When you read the systemd, OpenRC, runit, and Dinit sections, you will repeatedly find yourself recognizing the same concepts with new plumbing. That continuity — not nostalgia — is why sysvinit remains mandatory knowledge for a Linux systems interview, and why this section treats the 1991 design as living documentation rather than archaeology.

## Interview Questions

### Q: Is sysvinit still maintained? What should you know about its release history?

Yes. After Miquel van Smoorenburg's long tenure ended around 2.86 (2004), the Debian team maintained the 2.88dsf line until Jesse Smith took over upstream around 2014 and resumed regular releases. The current line is 3.x (3.00 in late 2021; 3.09 in late 2023), developed in a git repository on Savannah. It is maintained in the stability sense: fixes and hardening, no architectural change. Interviewers ask this to check that you know "unmaintained" is wrong — the accurate statement is "actively maintained, deliberately feature-stable."

### Q: Explain what "sysvinit is stateless between events" means and give one operational consequence.

PID 1 keeps no runtime model of services. It runs scripts at boot or runlevel change, restarts `respawn` entries when they exit, and handles a few signals — nothing else. Consequence: if a daemon crashes, nothing restarts it and nothing even notices; "is it running?" must be answered by running the script's `status` action or `pidof`, not by querying init. This is why systems that need availability under sysvinit bolt on monitoring, cron-based checks, or a separate supervisor.

### Q: Slackware "uses sysvinit" — in what sense, and what does that tell you?

Slackware runs the sysvinit *program* (`/sbin/init` from the same codebase, reading a conventional `inittab`) but organizes boot scripts BSD-style: runlevels in `inittab` point at monolithic scripts (`rc.S`, `rc.M`, `rc.K`, `rc.4`) rather than directories of numbered symlinks, and packages integrate via hook files. The lesson: the runlevel engine and the SysV-style `/etc/init.d` + `rc*.d` conventions are separable layers. The program is generic; the layout is a distribution convention.

### Q: Why did sysvinit lose to systemd? Give three concrete technical reasons tied to its design.

(1) No supervision: dead services stay dead, and nothing tracks service state at runtime, so systemd's unit state plus restart policies fix a real operational gap. (2) Static, coarse-grained dependencies: ordering is symlink numbers or boot-time-only header metadata, and runlevels are global states, so partial service sets and runtime dependency changes are inexpressible. (3) Serial, script-based startup: the unit of execution is a shell script that can do anything, so true parallelism and per-service resource control (cgroups) are impossible. Each of these is a specific, demonstrable limitation rather than an aesthetic complaint.

### Q: On Debian, which packages do `init`, `pidof`, and `update-rc.d` come from, and why does the split matter?

`init` (and `telinit`, `runlevel`, `shutdown`, `halt`) come from `sysvinit-core`; `pidof` (and `killall5`, `fstab-decode`, the `init-d-script` interpreter and `/lib/lsb/init-functions`) from `sysvinit-utils`; `update-rc.d` (with `invoke-rc.d` and `service`) from `init-system-helpers`. The split matters because the layers are independent: `sysvinit-utils` is useful under systemd too (many legacy scripts call `pidof`/`killall5`), `init-system-helpers` works with multiple init systems, and switching Debian's PID 1 is just swapping `sysvinit-core` against `systemd-sysv` without disturbing the rest.

### Q: Name the signals sysvinit's PID 1 reacts to and what each does by default.

SIGPWR (power failure from UPS monitoring) triggers the `powerwait`/`powerfail`/`powerokwait`/`powerfailnow` inittab actions; SIGINT from the console Ctrl-Alt-Del key sequence triggers the `ctrlaltdel` action (usually `shutdown -r now`); SIGWINCH from a special console key combination triggers the `kbrequest` action; SIGCHLD is not a "feature" but the obligation behind PID 1's orphan-reaping duty; and `telinit` communicates with init through `/run/initctl` rather than a signal. A system that answers "init listens on SIGPWR, SIGINT, SIGWINCH and telinit commands" has the right mental model.

## References

- [init(8) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/init.8.en.html) — authoritative description of PID 1 behavior, signals, and environment.
- [inittab(5) — sysvinit-core man page, Debian bookworm](https://manpages.debian.org/bookworm/sysvinit-core/inittab.5.en.html) — the grammar and action set this page summarizes.
- [sysvinit git repository (Savannah)](https://git.savannah.nongnu.org/cgit/sysvinit.git/) — upstream source and release history.
- [Devuan documentation](https://docs.devuan.org/) — distribution documentation for the leading sysvinit-default distro.
- [Debian Policy Manual, ch-opersys](https://www.debian.org/doc/debian-policy/ch-opersys.html) — how Debian packages integrate with init systems, including the alternate-init rules.
- [LSB Core, Init Script Actions](https://refspecs.linuxfoundation.org/LSB_5.0.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html) — the standardized action/exit-code contract inherited by all `/etc/init.d` scripts.

## Cross-References

- [The sysvinit Boot Sequence](./boot-sequence.md) — firmware to gettys, step by step, with Debian script names.
- [Runlevels in Depth](./runlevels.md) — the state model introduced here, examined mechanically.
- [systemd — Overview and Architecture](../systemd/overview-architecture.md) — the successor design and how each sysvinit gap was addressed.
- [OpenRC — Overview and Architecture](../openrc/overview-architecture.md) — keeps the shell-script model, adds a runtime dependency engine.
- [runit — Overview and Philosophy](../runit/overview-philosophy.md) — supervision-first minimalism as the opposite trade-off.
- [Dinit — Overview](../dinit/overview.md) — a modern init that combines dependencies with supervision.
- [Init Systems Hub](../README.md) — section map and reading order for all init-system families.
- [Init System Comparison](../comparison.md) — feature matrix across sysvinit, systemd, OpenRC, runit, and Dinit.
