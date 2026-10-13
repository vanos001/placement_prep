# OpenRC Runlevels and Service Management

## Overview

OpenRC groups services into runlevels, where a runlevel is nothing more exotic than a directory under `/etc/runlevels/` containing symlinks to service scripts. That file-tree definition is the whole idea: enabling a service means creating a symlink, disabling it means removing one, and inspecting a runlevel means listing a directory. On top of this flat model sits a dependency engine — services declare relations in `depend()`, and OpenRC computes start and stop order for the set of services involved — plus four user-facing tools: `rc-update` (edit membership), `rc-status` (report state), `rc-service` (control one service), and `rc-depend` (inspect and cache the dependency tree). The architectural picture — components, boot choreography, and how OpenRC relates to the PID 1 above it — is covered in [OpenRC — Overview and Architecture](./overview-architecture.md); this page stays at the operational layer.

Three special runlevels get automatic treatment: everything in `sysinit` and `boot` is implicitly included in every other runlevel, so a runlevel directory only ever lists the *delta* over that baseline. There is also no requirement that runlevels be numbered or predefined — `default` ships with the distribution, but any directory name you create becomes a valid runlevel. This is a sharper contrast with sysvinit than it first appears: sysvinit runlevels are fixed numbers wired into `inittab` (see [SysVinit — Runlevels](../sysvinit/runlevels.md)) with ordering encoded in `rcN.d` symlink prefixes (see [SysVinit — rc Symlinks](../sysvinit/rc-symlinks.md)), whereas OpenRC runlevels are user-extensible names and the ordering is solved from declared dependencies.

The four tool families map cleanly onto daily questions: "should this service start at boot?" (`rc-update`), "what is running right now?" (`rc-status`), "start/stop/fix this one service" (`rc-service`), and "why did it start in this order?" (`rc-depend`). Each tool has its own man page — the command tables below follow [rc-update(8)](https://manpages.debian.org/bookworm/openrc/rc-update.8.en.html), [rc-status(8)](https://manpages.debian.org/bookworm/openrc/rc-status.8.en.html), and [rc-service(8)](https://manpages.debian.org/bookworm/openrc/rc-service.8.en.html) — and `openrc(8)` itself acts as the runlevel switcher.

## A Runlevel Is a Directory of Symlinks

Concretely, the runlevel tree looks like this on a freshly installed Alpine system (Gentoo differs only in which entries appear):

```text
/etc/runlevels/
  sysinit/    devfs -> /etc/init.d/devfs
              dmesg -> /etc/init.d/dmesg
              mdev  -> /etc/init.d/mdev
              ...
  boot/       bootmisc  -> /etc/init.d/bootmisc
              hostname  -> /etc/init.d/hostname
              swap      -> /etc/init.d/swap
              ...
  default/    networking -> /etc/init.d/networking
              sshd       -> /etc/init.d/sshd
              crond      -> /etc/init.d/crond
              local      -> /etc/init.d/local
  shutdown/   killprocs -> /etc/init.d/killprocs
              mount-ro  -> /etc/init.d/mount-ro
              savecache -> /etc/init.d/savecache
  single/     (usually empty)
```

Every symlink points into `/etc/init.d/` (scripts themselves are dissected in [OpenRC Service Scripts](./init-scripts.md)). The special runlevel semantics, per [openrc(8)](https://manpages.debian.org/bookworm/openrc/openrc.8.en.html):

| Runlevel | Semantics |
|---|---|
| `sysinit` | One-shot system plumbing at host start: `/dev`, `/proc`, `/sys`, and mounts `/run/openrc` as the state tmpfs. Runs once; not meant to be re-entered. |
| `boot` | Filesystems, swap, hostname, clock, kernel tuning, basic logging. Members of `sysinit` and `boot` are automatically included in all other runlevels. |
| `default` | The ordinary multi-user service set. This is what a bare `openrc` invocation with no argument operates on when booting normally. |
| `single` | Stops everything except `sysinit` services — the rescue level, equivalent in spirit to sysvinit runlevel 1. |
| `shutdown` | Services *started* during shutdown, after the normal set has been stopped: killing stragglers (`killprocs`), remounting root read-only (`mount-ro`), caching rc state (`savecache` on Alpine). You do not invoke it yourself; `openrc-shutdown` or the resident init drives it. |
| `nonetwork` | Gentoo's historical example of an *ordinary* runlevel: `default` minus networking services, for maintenance with local tools only. |

The `nonetwork` entry is worth internalizing because it reveals the model: a runlevel is any directory, so distributions and admins can add or subtract service sets freely. Two dynamic runlevels also exist at runtime and show up in `rc-status -a` output — `hotplugged` (services started by a device manager when matching hardware appears, gated by `rc_hotplug`) and virtual groups like `needed` (services pulled in by dependencies, not explicitly enabled). They have no directory under `/etc/runlevels/`; they are state groupings, not configuration.

## What Runs Where: Default Sets and Distro Variation

The membership of the special runlevels is chosen by each distribution's base packages, so treat the following as representative rather than normative. What is stable is the *shape*: sysinit is tiny and plumbing-only, boot makes the machine bootable, default makes it useful.

| Runlevel | Gentoo (representative) | Alpine (representative) |
|---|---|---|
| `sysinit` | `devfs`, `dmesg`, `sysfs`, `udev` (+ trigger/settle historically) | `devfs`, `dmesg`, `mdev` (or `udev`), `hwdrivers`, `modloop` |
| `boot` | `fsck`, `root`, `localmount`, `swap`, `sysctl`, `hostname`, `hwclock`, `keymaps`, `modules`, `net.lo`, `bootmisc`, `urandom`/`seedrng` | `bootmisc`, `hostname`, `hwclock`, `keymaps`, `modules`, `swap`, `sysctl`, `sysfixtime`, `syslog`, `seedrng`, `machine-id` |
| `default` | `sshd`, `cronie`, `dbus`, `acpid`, `net.eth0` (netifrc), `local` | `acpid`, `crond`, `sshd`, `local` |
| `shutdown` | usually empty; `killprocs`/`mount-ro` on many setups | `killprocs`, `mount-ro`, `savecache` |

Two cross-distro differences deserve attention. First, networking: Gentoo puts `net.lo` (loopback) in `boot` and adds per-interface `net.eth0`-style services to `default`, while Alpine runs a single `networking` service — typically placed in `boot` by `setup-alpine` — driving `/etc/network/interfaces` (details in the distro-flavor section below). Second, the `local` service always sits in `default` on both: it is a catch-all that runs `/etc/local.d/*.start` and `*.stop` snippets last, and it is a common escape hatch for site-specific one-shots that do not merit a real service script.

## Selecting the Initial Runlevel

Who decides that the machine ends up in `default` (or in something else)? Three mechanisms, in practice stacked:

1. **sysvinit as PID 1** — the classic arrangement. `/etc/inittab` carries lines that run `openrc sysinit`, then `openrc boot`, then `openrc default` in sequence; later lines respawn gettys. The *choice* of final runlevel is literally which argument inittab passes (see [SysVinit — inittab choreography around rc calls](../sysvinit/boot-sequence.md) for the surrounding stage sequence).
2. **openrc-init as PID 1** — since OpenRC 0.25 this native init can drive the same three runlevels internally, taking the default runlevel from `rc_default_runlevel` in `/etc/rc.conf`, the kernel command line, or the built-in `default`. It does not manage gettys — see the architecture page for that caveat.
3. **The `softlevel=` kernel parameter** — appending `softlevel=<name>` to the kernel command line boots into that runlevel instead of the default. `softlevel=single` is the canonical use: a rescue boot without editing inittab or anything else. The current runlevel is recorded at runtime in `/run/openrc/softlevel`, which is how tools like `rc-status` know where "here" is.

At runtime, switching levels is `openrc <runlevel>` — covered in [Switching Runlevels at Runtime](#switching-runlevels-at-runtime) below.

## rc-update — Enabling and Disabling Services

`rc-update` is the only sanctioned way to edit runlevel membership. A session, annotated:

```text
# rc-update add sshd default        # enable sshd in the default runlevel
 * service sshd added to runlevel default
# rc-update add crond default       # enable cron
 * service crond added to runlevel default
# rc-update show                    # list: service | runlevels
            acpid |      default
            crond |      default
            local |      default
            sshd  |      default
# rc-update show -v                 # -v also lists services in NO runlevel
# rc-update del crond default       # disable (delete accepts a runlevel;
                                    # with none given the service is
                                    # removed from every runlevel)
# rc-update -u                      # rebuild the dependency cache after
                                    # touching symlinks by hand
```

What `rc-update add sshd default` actually writes is exactly one filesystem object: the symlink `/etc/runlevels/default/sshd` pointing to `/etc/init.d/sshd`. Nothing is started, no state is touched, and no daemon configuration is read — membership takes effect at the next runlevel transition (`openrc default`, reboot) or when you start the service manually. The `-u`/`update` operation exists because OpenRC caches the solved dependency tree under `/run/openrc`; if you create or remove symlinks with `ln`/`rm` directly (scriptable, but not recommended), the cache is stale until you force a rebuild — the same remedy applies after clock skew, as documented for [rc-update(8)](https://manpages.debian.org/bookworm/openrc/rc-update.8.en.html).

Two further behaviors are handy: `rc-update add` accepts any runlevel name (custom runlevels, next section), and stacked runlevels are supported — a runlevel can be listed inside another, so its members start before the target runlevel's own services. Note also what `rc-update` deliberately does *not* do: it never reads or validates the service script itself. A typo in the runlevel argument creates a runlevel directory you did not intend; `rc-update show` afterward is the cheap sanity check.

## rc-status — Reading Service State

`rc-status` with no arguments reports the current runlevel's services and their recorded states; the interesting flags are `-a`/`--all` (every runlevel, including the dynamic ones) and `-c`/`--crashed` (only services whose recorded state says crashed):

```text
# rc-status -a
Runlevel: boot
 bootmisc                                                       [  started  ]
 hostname                                                       [  started  ]
 swap                                                           [  started  ]
Runlevel: default
 acpid                                                          [  started  ]
 sshd                                                           [  started  ]
 crond                                                          [  stopped  ]
 local                                                          [  started  ]
Dynamic Runlevel: hotplugged
Dynamic Runlevel: needed
 udev                                                           [  started  ]
Dynamic Runlevel: manual
```

Reading the output: each line is a service name, right-aligned state in brackets, color-coded when not piped. States come from the service state machine tracked under `/run/openrc`, and each state has a distinct operational meaning:

| State | Meaning | How it typically arises |
|---|---|---|
| `started` | Bookkeeping says running; verified for supervised services | Normal successful start |
| `stopped` | Not running, not enabled in any active sense | Normal stop, or after `zap` |
| `starting` / `stopping` | Transition in progress (hook still running) | Observed during slow starts or hangs |
| `inactive` | Ran and released; will restart on demand | inetd-style and queue-style services |
| `scheduled` | Waiting for another service to become inactive | Something declared interest via an inactive-capable dependency |
| `crashed` | Tracked process is gone but state was not refreshed | OOM-kill, daemon exiting behind the script's back |
| `failed` | Start did not complete successfully | Non-zero `eend`, missing dependency |

The `Dynamic Runlevel:` sections are runtime groupings rather than directories: `hotplugged` holds device-triggered services (gated globally by the `rc_hotplug` setting), `needed` holds services started only because something enabled depends on them, and `manual` holds services started by hand. A service that was OOM-killed or died under the manager's feet shows as `crashed` — the detection and recovery flow is in the cookbook below.

`rc-status` also integrates with supervision: services running under `supervise-daemon` are reported as such (see [rc-status(8)](https://manpages.debian.org/bookworm/openrc/rc-status.8.en.html) and the supervision section of [OpenRC Service Scripts](./init-scripts.md)).

## rc-service — The Direct Service Control Tool

`rc-service <service> <command>` locates a service script (wherever it lives) and runs a command against it through `openrc-run`. It is the distro-agnostic entry point — equivalent to calling `/etc/init.d/sshd start` directly, but it also finds scripts outside `/etc/init.d` and normalizes option handling:

| Command | Effect |
|---|---|
| `start` | Satisfy dependencies, then run the service's start path |
| `stop` | Run stop logic (reverse dependencies that *need* this service are stopped first) |
| `restart` | Stop then start, honoring dependency order |
| `status` | Print the recorded state; exit code reflects it |
| `zap` | Reset recorded state to `stopped` *without running any stop logic* |
| `describe` | Print the script's `description=` plus any extra commands it defines |
| `<custom>` | Any command the script registered via `extra_commands` / `extra_started_commands` (e.g. `reload`) |
| `cgroup_cleanup` | Present when cgroups are active: kill everything left in the service's cgroup |

Useful `rc-service` options: `-C` disables color for capture into logs or tickets, `-d` and `-v` raise debug/verbose output from the script itself, `--ifexists` suppresses the error when a service is missing (handy in loops over many machines), and `-l`/`--list` enumerates available services. Exit codes are meaningful for scripting: `status` in particular exits non-zero when the service is not running, which is the basis for monitoring wrappers.

`zap` deserves its own paragraph because it is the recovery tool for bookkeeping desync. OpenRC records state; it does not continuously measure it (except under `supervise-daemon`). If a daemon was OOM-killed, or a buggy script marked the service started while the process actually exited, reality and the recorded state disagree — `rc-status` shows `crashed` or `started` for a process that is not there. `zap` throws the bookkeeping away (resets to `stopped`) without invoking `stop()`, which is exactly right when there is nothing real to stop; then a `start` re-establishes consistent state. If the process *is* alive and healthy, zap-and-start is still the fix — the alternative, editing state files under `/run/openrc` by hand, is not sanctioned.

## rc-depend — Inspecting and Caching the Dependency Tree

`rc-depend` exposes the solver's output. Two flags cover the operational needs: `-t`/`--tree` prints the dependency tree (who pulls in whom, in solve order — invaluable when a boot sequence surprises you), and `-u`/`--update` rebuilds the cached tree under `/run/openrc`. The cache is what makes repeated transitions cheap: `openrc-run` shells every script's `depend()` once, stores the solved graph, and subsequent runs reuse it. After editing `depend()` functions, changing rc scripts via packages, or hand-manipulating `/etc/runlevels/`, a forced rebuild (`rc-update -u` or `rc-depend -u`) guarantees the next transition sees the new graph. The cache is also sensitive to the `config` dependency verb — services that declare `config /etc/foo.conf` re-resolve when that file's timestamp changes.

## Switching Runlevels at Runtime

`openrc <runlevel>` is the closest analogue to `telinit` in this world: `openrc default` stops services not present in the target runlevel (unless `--no-stop`) and starts the missing ones in dependency order, effectively converging the machine onto the runlevel's defined state. With no argument it operates on the current runlevel — which makes bare `openrc` the "repair my boot" idiom: after fixing a failed service, re-running `openrc` brings the level to its intended membership without a reboot. Because `sysinit` and `boot` members are always included, transitioning between ordinary runlevels never tears down filesystem plumbing.

Shutdown and reboot are driven differently depending on who is PID 1. Under sysvinit, `shutdown(8)`/`telinit 0` remain the request path and inittab invokes `openrc shutdown`. Under `openrc-init`, `openrc-shutdown` is the counterpart (`-p` poweroff, `-r` reboot, `-H` halt, `-s` single-user, plus cancel/re-exec options) — it switches to the `shutdown` runlevel, letting `killprocs`/`mount-ro`-style services finish the machine. The flags and the PID 1 pairing are tabulated in [OpenRC — Overview and Architecture](./overview-architecture.md), so only the runlevel mechanics are repeated here.

One property of transitions is worth internalizing: they are convergent and repeatable. Because the target state is "exactly the services in this directory, running," running the same `openrc default` twice is harmless, and the same mechanism serves boot, repair, and scheduled reconfiguration alike. The cost of a transition is bounded by the dependency solve, which is served from the `/run/openrc` cache — so a no-op convergence on a cached tree is fast, which is why configuration management systems safely invoke `openrc default` after every change.

## Custom Runlevels

Creating a runlevel is creating a directory. The explicit, portable recipe:

```text
# mkdir -p /etc/runlevels/maintenance
# rc-update add sshd maintenance
# rc-update show | rg maintenance
         sshd |      default maintenance
# openrc maintenance
```

Two properties make this more useful than it looks. First, because `sysinit`+`boot` are auto-included, `maintenance` only needs the delta (here, sshd for remote access) — localmount, syslog, and friends are already implied. Second, services can belong to multiple runlevels simultaneously (`sshd` above is in both `default` and `maintenance`), so custom levels are selections, not partitions. Typical uses: a `workstation` vs `server` split on one machine, a `games` level that starts an X stack, or per-environment levels in appliances where the "product mode" and "factory mode" service sets differ. Per-runlevel service differences are then just different directory contents; remember that a service being merely *enabled* in a level does not start it until a transition into that level happens — or until something `need`s it dynamically.

## Distro Flavor: Gentoo netifrc vs Alpine ifupdown-ng

The runlevel model is identical across OpenRC distributions; what differs is the *packaged services* layered on top, and networking is the loudest example.

Gentoo's netifrc gives every interface its own service: `/etc/init.d/net.eth0` is a symlink to `net.lo`, enabled per interface, configured from `/etc/conf.d/net`:

```text
# Gentoo: one service per interface
# ln -s net.lo /etc/init.d/net.eth0  (package usually does this)
# rc-update add net.lo boot
# rc-update add net.eth0 default
# /etc/conf.d/net:
config_eth0="192.168.1.10/24"
routes_eth0="default via 192.168.1.1"
dns_servers_eth0="192.168.1.1"
```

Alpine instead ships one `networking` service backed by ifupdown-ng reading `/etc/network/interfaces`, enabled once (usually in `boot`):

```text
# Alpine: one service, declarative interfaces file
# rc-update add networking boot
# /etc/network/interfaces:
auto eth0
iface eth0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1
```

Wireless follows each distro's convention: on Gentoo, `net.wlan0` plus `modules="wpa_supplicant"` (or iwd) in `/etc/conf.d/net`; on Alpine, the `wpa_supplicant` or `iwd` package installs a service you add to `boot` or `default`. The transferable lesson for interviews: OpenRC itself is network-agnostic — `need net` dependencies resolve against *whatever* provides the virtual `net` service, which is why swapping netifrc for ifupdown-ng (or even a custom provider) leaves all other service scripts untouched.

## Operations Cookbook

- **Which runlevels contain service X?** `rc-update show | grep X` — or `rc-update show -v` to also see disabled services. Remember `show` reads the directories, not runtime state.
- **Crashed-service cleanup.** `rc-status -c` lists candidates; verify reality with `pidof`/`ps`; then either `rc-service <svc> restart` (if the process should run) or `rc-service <svc> zap` followed by `start` to rebuild consistent bookkeeping. Defaults from `/etc/rc.conf` also matter here: `rc_crashed_start="YES"` makes rc retry crashed services on the next transition, while `rc_crashed_stop="NO"` deliberately never stops them implicitly.
- **Dependency cache refresh.** After hand-editing symlinks, upgrading packages, or editing `depend()` functions: `rc-update -u` (or `rc-depend -u`). Symptom of a stale cache: ordering that no longer matches your declarations.
- **Converge without rebooting.** `openrc` (current level) or `openrc default` — stops non-members, starts absentees. Combine with `rc-service <svc> zap` for the desync cases above.
- **Fast rescue boot.** `softlevel=single` on the kernel command line, or from a running system `openrc single` (stops everything except sysinit).
- **Boot debugging.** Enable `rc_logger="YES"` in `/etc/rc.conf` and read `/var/log/rc.log` — every service start/failure with timestamps; knobs and caveats in [rc.conf, cgroups, Containers and Advanced OpenRC](./config-advanced.md).
- **Audit a transition before you make it.** `rc-update show <level>` for membership, `rc-depend -t` for the solve order, and `rc-status` for the current baseline — together these predict exactly what the next `openrc <level>` will start and stop.
- **Interactive boot triage.** With `rc_interactive="YES"` pressing `I` during boot lets you choose services individually — note this is automatically disabled when `rc_parallel` is enabled, a frequent reason lab and production boot configurations drift apart.
- **Find a service's script when it is not in `/etc/init.d`.** `rc-service <svc> describe` works wherever the script lives (some packages ship scripts elsewhere), and prints the custom commands it supports — cheaper than grepping the filesystem.

## Mapping: Runlevels, systemd Targets, sysvinit Runlevels

| OpenRC | systemd | sysvinit | Notes |
|---|---|---|---|
| `sysinit` | `sysinit.target` | early rcS-style plumbing | `/dev`, `/proc`, `/sys`, state mounts |
| `boot` | spread across early targets (`local-fs`, `swap`, udev...) | Debian `S`/boot scripts | auto-included everywhere |
| `default` | `multi-user.target` / `graphical.target` | runlevel 2 or 3 (Debian: 2) | the useful machine |
| `single` | `rescue.target` | runlevel 1 / `S` | stops non-sysinit services |
| `nonetwork` | no direct equivalent (a reduced target set) | custom numeric level | maintenance without net |
| `shutdown` | `shutdown.target` + `final.target` | transition into 0/6 | services *started* while shutting down |
| dynamic (`hotplugged`, `needed`) | device/_path-based activation | none | runtime groupings, not directories |

The structural difference worth stating precisely: a systemd system can have several targets active simultaneously (they compose via Wants/Requires into one dependency graph — see [systemd — Targets and Runlevels](../systemd/targets-runlevels.md)), while OpenRC has exactly one *current* runlevel whose directory contents define the desired set, layered over the always-included sysinit/boot baseline. sysvinit sits at the other extreme: fixed numeric levels, no dependency solving, order by symlink name.

## Interview Questions

### Q: How are OpenRC runlevels different from systemd targets?

Mechanically: an OpenRC runlevel is a directory of symlinks to shell scripts, and exactly one runlevel is current at a time, layered over the always-included `sysinit` and `boot` members. systemd targets are units in one global dependency graph, and multiple targets can be active simultaneously (multi-user plus graphical plus device-triggered wants). Practically: OpenRC transitions by diffing directory membership (stop non-members, start absentees); systemd reaches a target by pulling its dependency closure. OpenRC's dynamic groupings (`hotplugged`, `needed`) approximate target-like layering but remain runtime state, not configuration. See the mapping table above and [systemd — Targets and Runlevels](../systemd/targets-runlevels.md).

### Q: What does `rc-update add foo default` actually write, and when does foo start?

Exactly one symlink: `/etc/runlevels/default/foo` pointing to the service script. Nothing starts at that moment — membership takes effect at the next transition into that runlevel (`openrc default`, reboot) or when the service is pulled in dynamically by a dependency. If you bypass rc-update and create symlinks by hand, follow with `rc-update -u` so the cached dependency tree is rebuilt; `rc-status`/`rc-update show` read the directories themselves, so they will reflect the change immediately.

### Q: When would you use `rc-service foo zap`?

When recorded state and reality disagree: the daemon was OOM-killed, a buggy start path marked the service started while the process exited, or a service is marked crashed but the underlying process is gone (or verifiably fine). `zap` resets the state to `stopped` without running any stop logic — appropriate because there is nothing real to stop — after which a normal `start` re-establishes consistent bookkeeping. It is the sanctioned alternative to editing state files under `/run/openrc` by hand. Under `supervise-daemon` the need mostly disappears, because the supervisor continuously measures the child.

### Q: What is the `nonetwork` runlevel and what does it illustrate?

Gentoo historically shipped it as an ordinary runlevel equal to `default` minus the networking services — a maintenance level with local tools only. Its pedagogical value is that it demonstrates the model: a runlevel is any directory under `/etc/runlevels/`, so "default without X" is just a directory listing, not a mode compiled into the rc system. You can create equivalent levels freely (`mkdir /etc/runlevels/maintenance; rc-update add sshd maintenance`), and services may be members of several levels at once.

### Q: I created a symlink in `/etc/runlevels/default/` by hand and my service starts in the wrong order. Why, and what is the fix?

The solved dependency tree is cached under `/run/openrc`. Hand-made symlinks (or freshly edited `depend()` functions, or a skewed clock) can leave that cache out of sync with what the scripts declare, so the next transition solves against stale data. Run `rc-update -u` or `rc-depend -u` to force a rebuild, verify with `rc-depend -t`, and prefer `rc-update` for membership changes so this class of problem does not arise.

### Q: How does the system decide which runlevel to enter at boot?

Three mechanisms depending on deployment. With sysvinit as PID 1, `/etc/inittab` literally encodes the answer — its lines invoke `openrc sysinit`, `openrc boot`, and `openrc default` in sequence. With the optional `openrc-init` as PID 1, the default runlevel comes from `rc_default_runlevel` in `/etc/rc.conf`, the kernel command line, or the built-in `default`. Independently of both, the `softlevel=<name>` kernel parameter overrides the target — the standard way to request a `single` rescue boot. At runtime the current level is recorded in `/run/openrc/softlevel`.

## References

- [openrc(8) — Debian](https://manpages.debian.org/bookworm/openrc/openrc.8.en.html) — runlevel semantics, special runlevels, switching behavior
- [rc-update(8) — Debian](https://manpages.debian.org/bookworm/openrc/rc-update.8.en.html) — add/show/delete and dependency cache update
- [rc-status(8) — Debian](https://manpages.debian.org/bookworm/openrc/rc-status.8.en.html) — states list, -a/--all, -c/--crashed
- [rc-service(8) — Debian](https://manpages.debian.org/bookworm/openrc/rc-service.8.en.html) — direct service commands including zap
- [openrc.8 blob — OpenRC GitHub](https://github.com/OpenRC/openrc/blob/master/man/openrc.8) — man source for runlevel rules
- [Gentoo wiki — OpenRC](https://wiki.gentoo.org/wiki/OpenRC) — usage overview and Gentoo conventions
- [Alpine wiki — OpenRC](https://wiki.alpinelinux.org/wiki/OpenRC) — Alpine service conventions and examples

## Cross-References

- [OpenRC — Overview and Architecture](./overview-architecture.md) — components, boot choreography, and execution model behind these commands.
- [OpenRC Service Scripts](./init-scripts.md) — the scripts that runlevel symlinks point to; depend() verbs and supervision.
- [rc.conf, cgroups, Containers and Advanced OpenRC](./config-advanced.md) — rc.conf knobs (rc_default_runlevel, rc_logger, rc_hotplug) used above.
- [SysVinit — Runlevels](../sysvinit/runlevels.md) — the numeric-runlevel model OpenRC generalizes.
- [SysVinit — rc Symlinks](../sysvinit/rc-symlinks.md) — rcN.d ordering symlinks vs dependency-solved ordering.
- [systemd — Targets and Runlevels](../systemd/targets-runlevels.md) — the graph-based counter-model.
- [init-systems README](../README.md) — section hub.
- [Init systems — comparison](../comparison.md) — runlevel/target semantics across all families.
