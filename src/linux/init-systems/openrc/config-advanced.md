# rc.conf, cgroups, Containers and Advanced OpenRC

## Overview

OpenRC's core is small; its flexibility lives in configuration. `/etc/rc.conf` — documented in [rc.conf(5)](https://github.com/OpenRC/openrc/blob/master/man/rc.conf.5) and shipped as a heavily commented template — is the global knob panel: parallelism, logging, environment filtering, cgroup policy, and the `rc_sys` declaration that tells OpenRC what kind of environment it is running in. Per-service configuration then layers on through `/etc/conf.d/<service>`, which every script sources automatically, reusing the same variable vocabulary at service scope. This page tours those settings, then follows three threads that stretch them hardest: cgroup integration, OpenRC inside containers and chroots, and the companion components (networking stacks, elogind) that non-systemd systems must assemble themselves.

The unifying theme is composition. OpenRC deliberately does *not* bundle a journal, a timer system, a session manager, or a socket-activation framework — on a systemd distribution those are one project's problems; on an OpenRC distribution they are integration decisions, made once per distro and visible in files like `/etc/rc.conf`. That is also why the same rc engine fits a musl container base image and a full Gentoo desktop: the variables adapt it, and the missing pieces are chosen deliberately. The base architecture and component map are in [OpenRC — Overview and Architecture](./overview-architecture.md); the scripts that consume most of these variables are dissected in [OpenRC Service Scripts](./init-scripts.md); and the runlevel operations that turn settings into boot behavior are in [OpenRC Runlevels and Service Management](./runlevels-services.md).

Everything below is anchored to the verified man sources: [openrc(8)](https://manpages.debian.org/bookworm/openrc/openrc.8.en.html), [openrc-run(8)](https://manpages.debian.org/bookworm/openrc/openrc-run.8.en.html), and [supervise-daemon(8)](https://manpages.debian.org/bookworm/openrc/supervise-daemon.8.en.html), plus the distribution wikis for distro-specific defaults.

## rc.conf(5) — the Global Configuration File

`/etc/rc.conf` is shell syntax: commented-out lines show defaults, and uncommenting an assignment overrides them. The settings that matter day to day, per [rc.conf(5)](https://github.com/OpenRC/openrc/blob/master/man/rc.conf.5) and the shipped template:

| Variable | Default | Effect |
|---|---|---|
| `rc_parallel` | `NO` | Start services concurrently where the graph allows. Output is interleaved and prefixed per service. Upstream's own comment warns it can still lock the boot process — "don't file bugs unless you can supply patches." |
| `rc_interactive` | `YES` | Press `I` during boot to step services individually. Automatically disabled when `rc_parallel` is on. |
| `rc_depend_strict` | `YES` | Virtual dependencies (`provide`) satisfied by *all* enabled providers (`YES`) or *any* started one (`NO`). |
| `rc_logger` | `NO` | Capture the whole rc process into a log; the boot-debugging artifact. On Linux the sysinit runlevel cannot be logged (devfs must come first). |
| `rc_log_path` | `/var/log/rc.log` | Alternate log location. |
| `rc_shell` | `$SHELL`/`/bin/sh` | Shell dropped to on hard failure; Linux boxes typically set `/sbin/sulogin` so the rescue prompt authenticates. |
| `rc_sys` | unset = autodetect | Declares the environment: `docker`, `podman`, `lxc`, `openvz`, `systemd-nspawn`, `vserver`, `uml`, `xen0`/`xenU`, `jail`, `prefix`, `subhurd`, `rkt`. Matches `keyword` masks in service scripts. |
| `rc_hotplug` | empty = disabled | Wildcard patterns deciding which services may be hotplug-started, e.g. `rc_hotplug="net.wlan !net.*"`. |
| `rc_verbose` | `no` | Verbose script output, globally or per service via its conf.d file. |
| `rc_env_allow` | empty | Environment-filter allowlist; `*` passes everything through to scripts. |
| `rc_start_wait` | `0` | Milliseconds start-stop-daemon waits after start to confirm the daemon is still alive — catches daemons that fork and then die on config errors. |
| `rc_nostop` | empty | Services never stopped by runlevel transitions (a direct `rc-service stop` still works). |
| `rc_crashed_stop` / `rc_crashed_start` | `NO` / `YES` | On transitions, rc never implicitly stops crashed services but does try to restart them. |
| `rc_nocolor` | `NO` | Disable color output (logs, serial consoles). |
| `rc_default_runlevel` | `default` | Used by `openrc-init` when choosing the post-boot runlevel. |
| `rc_tty_number` | `12` | TTY count consumed by `consolefont`, `keymaps`, `numlock`, `termencoding`. |
| `unicode`, `extra_net_fs_list`, `rc_fuser_timeout` | varies | Shared misc settings: console unicode, extra network filesystem types, fuser remote-response timeout. |

Three of these deserve emphasis for interviews and operations alike. `rc_parallel` is the only performance switch and the only one with an upstream caveat baked into its own documentation — treat it as a measured decision, not a default (Boot Performance section below). `rc_logger` is the difference between debugging a failed boot from evidence and from memory, since the log timestamps every service start and failure. And `rc_sys` is the linchpin of container behavior: it is what makes hundreds of stock scripts either run or gracefully no-op via their `keyword` masks.

### Per-Service Overrides Without Editing Scripts

The same file documents a naming convention that turns it (and each `/etc/conf.d/<svc>`) into a dependency-override mechanism: `rc_<service>_<verb>` variables. For a service named `foo`, `rc_foo_need="openvpn"`, `rc_foo_use="net.eth0"`, `rc_foo_after="clock"`, `rc_foo_before="local"`, `rc_foo_provide="!net"`, and `rc_foo_config="/etc/foo"` inject or remove dependency edges — the dashes in hyphenated service names become underscores (`rc_foo_bar_need` for `foo-bar`). This is how an administrator patches a dependency graph without touching a package-owned script: say, forcing a service to `after firewall`, or stripping a wrong `provide net` from a tap interface (`rc_net_tap0_provide="!net"`). Process-quality knobs are also service-scoped through exports: `SSD_NICELEVEL`, `SSD_IONICELEVEL`, `SSD_OOM_SCORE_ADJ`, and `rc_ulimit` (e.g. `rc_ulimit="-u 30"` caps process count via `ulimit -u`).

### Resolution Order: rc.conf, conf.d, and Script Defaults

The layering rule is simple and worth stating precisely, because it is the answer to half of all "why is my setting ignored" questions. openrc-run sources, in order: the script itself supplies in-code defaults; then `/etc/rc.conf` supplies global policy; then `/etc/conf.d/<service>` is sourced last, so service-scoped files always win. Consequences: a setting in the service's conf.d overrides the same-named global; putting what is really a per-service setting (a memory budget, a listen address, an override dependency) into rc.conf silently applies it to *every* service — the rc.conf template's own comments warn that service-configuration variables "should be configured in /etc/conf.d/foo ... and NOT enabled here unless you really want them to work on a global basis." For hyphenated service names, the mapping to variable names replaces `-` with `_`, and the same per-service prefix mechanism is how the virtual-provider exception `rc_net_tap0_provide="!net"` works.

## cgroups Integration

OpenRC puts each service's processes into a dedicated cgroup so that resource policy and cleanup have a handle that survives double-forking daemons. The layout is governed by `rc_cgroup_mode`:

| Variable | Values / default | Meaning |
|---|---|---|
| `rc_cgroup_mode` | `unified` (current default; older releases `hybrid`/`legacy`) | `unified`: cgroup v2 mounted at `/sys/fs/cgroup`. `legacy`: v1 at `/sys/fs/cgroup`. `hybrid`: v2 at `/sys/fs/cgroup/unified` plus v1 at `/sys/fs/cgroup`. |
| `rc_cgroup_controllers` | empty | Which v2 controllers to enable (mostly relevant under hybrid, where v2-claimed controllers are unavailable to v1). |
| `rc_cgroup_settings` | empty | v2 control-file writes, newline-separated, e.g. `memory.max 10485760` and `pids.max max`. Global in rc.conf or per service in `/etc/conf.d/<svc>`. |
| `rc_controller_cgroups` | `YES` | Legacy/hybrid: mount each v1 controller individually. |
| `rc_cgroup_<controller>` | empty | v1 per-controller settings (`rc_cgroup_cpu="cpu.shares 512"`, plus blkio/cpuset/devices/memory/pids/...). |
| `rc_cgroup_cleanup` | `NO` | Kill everything in the service's cgroup on stop/restart. |
| `rc_send_sighup`, `rc_timeout_stopsec`, `rc_send_sigkill` | `NO`, `90`, `YES` | The cleanup escalation chain: after the stop signal, optionally SIGHUP, wait (default 90 s), then SIGKILL unless suppressed. |

On a unified-mode system the tree is easy to inspect and verify:

```text
/sys/fs/cgroup/
  openrc/
    sshd/
      cgroup.procs
      memory.max
      pids.max
    nginx/
      ...
```

Verification is then ordinary filesystem reading: `cat /sys/fs/cgroup/openrc/sshd/cgroup.procs` shows the PIDs OpenRC considers part of the service; `cat /sys/fs/cgroup/openrc/sshd/memory.max` shows the applied limit. To give one service a memory and PID budget, drop settings into its conf.d file rather than rc.conf:

```text
# /etc/conf.d/myapp
rc_cgroup_settings="
memory.max 536870912
pids.max 64
"
```

The cleanup chain is the part worth understanding deeply because it is OpenRC's answer to "the daemon spawned children that survived the stop script." With `rc_cgroup_cleanup="YES"` (globally or per service), stopping a service moves through: send the stop signal (SIGTERM unless overridden) followed by SIGCONT to everything left in the cgroup; optionally SIGHUP (`rc_send_sighup`); wait `rc_timeout_stopsec` (default 90 seconds); then SIGKILL the remainder unless `rc_send_sigkill="NO"`. On kernels with cgroup v2's `cgroup.kill`, that primitive is used for a reliable single-syscall teardown. The same teardown is available on demand without changing config: `rc-service <svc> cgroup_cleanup`.

### Verifying and Testing cgroup Policy

A short verification sequence, runnable on any booted OpenRC system:

```text
# which mode am I in? (unified = plain v2 tree)
$ mount | rg cgroup
$ ls /sys/fs/cgroup/openrc/           # one dir per service
$ cat /sys/fs/cgroup/openrc/sshd/cgroup.procs
$ cat /sys/fs/cgroup/openrc/sshd/memory.max
# prove containment: memory budget then stress the daemon
$ rc-service myapp restart
$ cat /sys/fs/cgroup/openrc/myapp/memory.max
```

If `openrc` directories are absent, check the mode first (`rc_cgroup_mode`), then whether the mounted cgroup filesystem was delegated writable — the same prerequisite containers trip over below. And if limits appear unset, remember the resolution order from the previous section: a typo in a conf.d variable name loses silently, while `rc-service -v <svc> restart` echoes the cgroup setup as it happens. For the control theory behind these files, see [systemd — cgroups and Resource Control](../systemd/cgroups-resource-control.md) and the kernel-side picture in [cgroups](../../../os/containers/cgroups.md) — OpenRC uses the same kernel interface with a much thinner policy layer.

## OpenRC in Containers

OpenRC runs happily inside Docker, Podman, LXC, and chroots — and `rc_sys` is the switch that makes it *behave* there. Unset, OpenRC autodetects the environment; set explicitly (`rc_sys="docker"` or `rc_sys="lxc"`), it drives three consequences: `keyword` masks in stock scripts make no-op services (gettys, module loading, fsck) exit cleanly instead of failing; runlevel conventions trim to what a container needs; and the boot flow skips host-only work. The result is a service manager for the use case where one *wants* several processes in a container without taking on systemd: development images, appliances, musl-based labs, migrated init scripts.

Prerequisites, in order of how often they bite:

1. **A writable cgroup subtree.** OpenRC wants to create `/sys/fs/cgroup/openrc/<svc>`; the runtime must delegate that. LXC provides cgroup namespaces by default and is the natural host; Docker/Podman need a delegated, writable cgroup path (in throwaway lab images people often simply run privileged; production setups delegate a proper subpath).
2. **Writable `/run`** — the state tmpfs under `/run/openrc` must exist before rc commands work.
3. **Trimmed runlevels.** The sysinit/boot sets that make sense on a host (udev, fsck, gettys) are removed or keyword-masked; container images typically enable only their real services plus `local`.

The mechanism behind point three is visible in the scripts themselves. A stock getty service ships a dependency block like:

```text
depend() {
    after local
    keyword -docker -lxc -openvz -prefix -systemd-nspawn -uml -vserver -xen0
}
```

Match that against the `rc_sys` value list in the settings table above and the behavior falls out: inside a container the keyword test fails, the service is skipped, and the boot proceeds without gettys rather than dying on "no controlling tty." This is why the same unmodified distribution script set boots a laptop and a Docker image — the environment declaration plus masks do the adaption that systemd does with condition units (`ConditionPathExists=`, virtualization detection) in its unit files.

A minimal Alpine-style sketch (lab image, not a production pattern):

```text
FROM alpine:3.20
RUN apk add --no-cache openrc openssh \
 && rc-update add sshd default \
 && rc-update add local default
# bootstrap state dirs that do not exist in a bare image
RUN mkdir -p /run/openrc && touch /run/openrc/softlevel
# PID 1: openrc-init drives sysinit -> boot -> default
CMD ["/sbin/openrc-init"]
```

Run it with the cgroup delegation arranged (`--privileged` is the honest lab shortcut), and the container boots its `default` runlevel like a small machine; `docker exec <c> rc-status` reports it. Two alternative CMD patterns exist: running the runtime's default command and driving rc from an entrypoint (`openrc default && tail -f /dev/null`-style keep-alives) — common in older images — or invoking single services ad hoc after a `touch /run/openrc/softlevel`, which is the trick that makes `rc-service` usable inside an already-running container:

```text
# ad-hoc service management inside a running container
$ docker exec -it mybox touch /run/openrc/softlevel
$ docker exec -it mybox rc-service sshd start
$ docker exec -it mybox rc-status
```

For LXC, `lxc-create -t alpine` yields a full OpenRC guest with inittab and trimmed runlevels out of the box, which is why LXC is the smoother environment when the goal is "a small OpenRC machine" rather than "one app plus its dependencies." The guest's `/etc/rc.conf` usually needs nothing — autodetection handles `rc_sys="lxc"` — while the host's container configuration provides the cgroup and device delegation. For Artix and Devuan, OpenRC is a native boot option for full systems ([artixlinux.org](https://artixlinux.org/), [docs.devuan.org](https://docs.devuan.org/)); the container case above is the same engine one level down.

## Networking Stacks: netifrc and ifupdown-ng

OpenRC itself only understands the virtual `net` token; the actual network configuration is a distribution-layer service, and the two big OpenRC distros made different choices.

Gentoo's **netifrc** gives each interface a service: `/etc/init.d/net.eth0` is a symlink of `net.lo` (so instances are enabled per interface with `rc-update add net.eth0 default`), configured from `/etc/conf.d/net`:

```text
config_eth0="192.168.1.10/24"
routes_eth0="default via 192.168.1.1"
dns_servers_eth0="192.168.1.1"
modules_wlan0="wpa_supplicant"     # wireless module selection per interface
```

Alpine's stack is **ifupdown-ng** behind a single `networking` service reading the classic `/etc/network/interfaces`:

```text
auto eth0
iface eth0 inet static
    address 192.168.1.10/24
    gateway 192.168.1.1

auto wlan0
iface wlan0 inet dhcp
```

Wireless pairs with either stack as ordinary services: Gentoo selects `wpa_supplicant` or iwd per interface via the `modules_` setting above; Alpine installs the `wpa_supplicant` or `iwd` package, whose service is added to `boot`/`default` and whose daemon ifupdown-ng invokes for the wireless stanza. The design point worth carrying into interviews: because consumers declare `use net`/`need net` against the *virtual* provider, an entire distribution can swap networking stacks without touching any other service script — the portability payoff of `provide` described in [OpenRC Service Scripts](./init-scripts.md).

Debugging either stack starts the same place — which service provides `net`, and is it started:

```text
$ rc-status                       # is networking (or net.eth0) started?
$ rc-service networking status    # Alpine: which interfaces came up?
$ ifquery --list                  # ifupdown-ng: parse /etc/network/interfaces
$ rc-service -v networking restart   # verbose: per-interface actions
```

Gentoo adds `/etc/init.d/net.<iface> restart` and the netifrc-specific `iwconfig`-era diagnostics to that vocabulary, but the shape is identical: the stack is a service, so the service tooling — status, restart, verbose, rc.log — is the diagnostic interface. Failures here are also the number-one cause of delayed boots elsewhere, which is the loop back to the performance section: a `need net` consumer waiting on DHCP is measured in rc.log timestamps.

## Session Management Without systemd: elogind and seatd

A desktop Linux without systemd still needs the *logind API*: seat and session tracking, VT switching, device-access arbitration, and the power-action D-Bus endpoints (`org.freedesktop.login1`). On OpenRC systems that role is filled by **elogind**, the systemd-logind codebase extracted to run standalone — it exposes the same D-Bus interface, which is why polkit, desktop environments, and Wayland compositors work unmodified: polkit authenticates power/suspend actions against it, and wlroots-based compositors request DRM/input device access through it when starting a session. Without it, a non-systemd desktop loses graceful shutdown from the session, suspend integration, and (for most Wayland stacks) sane device handoff. Gentoo ships elogind as the standard pairing; Devuan documents it among its systemd-free desktop components ([docs.devuan.org](https://docs.devuan.org/)); Artix similar.

**seatd** is the lighter alternative: a small seat-management daemon and library serving the same arbitration role, popular with minimal wlroots setups where the full logind API (and polkit) is not otherwise needed. The operational rule of thumb: DE-heavy desktops want elogind for compatibility breadth; bespoke minimal compositors can run seatd and skip the rest. Neither is part of OpenRC — they are the visible price of OpenRC's composition philosophy, which the systemd world gets "for free" inside PID 1.

Verification on a running desktop is quick: the session-aware `loginctl` shipped with elogind should list seats and sessions (`loginctl list-sessions`, `loginctl show-session <id>`), and the D-Bus name `org.freedesktop.login1` should be owned on the system bus. A compositor that hangs at startup asking for the DRM master, or a DE whose shutdown entry is greyed out, is the classic symptom that neither elogind nor seatd is running — a configuration omission, not an OpenRC failure.

## Boot Performance

- **`rc_parallel="YES"`** is the headline switch: services start concurrently wherever the dependency graph permits, typically shaving a noticeable fraction of boot time on service-dense boxes. The costs are upstream-documented: interleaved, prefix-tagged output is harder to read (and `rc_interactive` stepping is disabled), and the rc.conf comment explicitly warns parallel boot "can still potentially lock the boot process" — with the request that bug reports come with patches. Enable it deliberately, verify a full boot cycle, and keep it off on boxes where boot-time debuggability matters more than seconds.
- **Measure with `rc.log`.** With `rc_logger="YES"`, `/var/log/rc.log` records each service start and completion with timestamps — the evidence base for any optimization. A slice of a real-looking log:

```text
rc boot logging started
 * Starting fsck ...                       [ ok ]
 * Mounting local filesystems ...          [ ok ]
 * Starting networking ...                 [ ok ]
 * Starting syslog ...                     [ ok ]
 * Starting sshd ...                       [ ok ]
boot process complete
```

Sort the deltas; the slow entries are usually network waits (`netmount`, DHCP) and fsck, not rc overhead. On Linux the sysinit runlevel is not captured (devfs must initialize first), so measure within `boot`/`default`.
- **Keep the dependency cache warm.** The solved tree under `/run/openrc` makes transitions cheap; `rc-update -u` after script or membership changes prevents re-solve surprises from appearing as boot slowness.
- **Slim the runlevels.** `rc-update show -v` exposes services enabled by habit rather than need; every disabled service is a graph node the solver never has to start. Combine with per-service dependency overrides (`rc_<svc>_need`/`rc_<svc>_use`) to cut edges that pull in heavyweight chains — the override mechanism above exists precisely for tuning without forking scripts.

## Failure Handling

OpenRC's failure posture is *degrade and continue*. A service that fails to start does not abort the boot: the runlevel transition proceeds, and only the failed service's dependents (things that `need` it) are skipped — `use`-dependent services still start, consistent with the soft-edge semantics in [OpenRC Service Scripts](./init-scripts.md). The failure is recorded (`failed`/`crashed` states, visible in `rc-status` and `rc-status -c`), and the transition defaults give recovery a chance: `rc_crashed_start="YES"` retries crashed services on the next transition, while `rc_crashed_stop="NO"` guarantees rc never silently stops a crashed service on the way down (stopping it could cascade through dependents).

For hard failures there is the rescue shell. `rc_shell` (set it to `/sbin/sulogin` on Linux) is what OpenRC drops to when sysinit-level work fails badly enough that continuing is meaningless — an authenticated single-user prompt instead of a hung boot. At the ordinary service level the equivalent manual flow is: fix the cause, `rc-service <svc> zap` if bookkeeping desynced (crashed-but-actually-dead, or marked-started-but-actually-exited), then re-run `openrc` to converge the runlevel without rebooting — the operational details live in the cookbook section of [OpenRC Runlevels and Service Management](./runlevels-services.md).

Two quieter states round out the model. `inactive` marks services that ran and released (inetd-style); they are eligible to be started again on demand, and `scheduled` marks services queued waiting for one of those to become inactive. Neither is an error; both show up in `rc-status` output and are the states most often mistaken for failures by admins reading a boot log for the first time.

A note on failure *output* versus failure *handling*: with `rc_parallel` off, a failed service's red line sits visibly in sequence in the console and in rc.log; with `rc_parallel` on, failures surface interleaved and prefixed, which is why post-mortem reading of rc.log — not console recall — should be the habit on parallel-boot machines. Either way the recovery sequence is identical: evidence, fix, `zap` if needed, converge.

## What OpenRC Does Not Do

The feature list OpenRC deliberately omits defines its integration surface, and each omission has a conventional answer:

| Missing capability | The OpenRC-world answer |
|---|---|
| Structured journal | A syslog daemon (`syslog-ng`, `rsyslogd`, busybox `syslogd`) plus `rc_logger`'s `/var/log/rc.log` for the boot itself — compare the [systemd journal](../systemd/journald.md) |
| Timers | cron/fcron — see [cron administration](../../admin/cron.md); package cron jobs land in the usual spool directories |
| Socket activation | None; services start on dependency and boot, not connection. The systemd mechanism is described in [systemd — Socket Activation](../systemd/socket-activation.md) |
| Per-process resource policy | Present but thin: per-service cgroup directories with the settings/cleanup knobs above, versus systemd's full slice/scope model in [systemd — cgroups and Resource Control](../systemd/cgroups-resource-control.md) |
| Device management | Delegated to udev (Gentoo) or mdev (Alpine) as sysinit services |
| Session/seat management | elogind or seatd, as described above |

The interview framing: these are not gaps by accident. OpenRC keeps the unit of work a shell script and the rc layer stateless across boots, pushing stateful policy (journals, timers, sessions) to dedicated daemons — the same composition philosophy that lets it fit a 10 MB container image and a full desktop alike.

The corollary for capacity planning: every one of those companion daemons is itself an OpenRC service with a conf.d file, dependency edges, and possibly a cgroup budget — so "adopting OpenRC" on a desktop-grade system is really adopting a *stack* (OpenRC + elogind + syslog + cron + NetworkManager-or-equivalent), each piece independently auditable. Teams coming from systemd should budget integration time for exactly these seams, not for the service manager itself.

## Interview Questions

### Q: Is rc_parallel safe to enable everywhere?

No — treat it as a tested decision. The upstream documentation itself warns parallel boot can still lock the boot process and asks that bug reports come with patches. Concrete trade-offs: output interleaves (prefixed per service, harder to read live), `rc_interactive` stepping is disabled, and a failure that was previously cleanly serialized now surfaces mid-tangle. Best practice: enable it on service-dense machines after a verified full-boot cycle with `rc_logger` on, keep it off for boxes where boot-time debuggability dominates, and remember the dependency solve still serializes anything genuinely ordered — parallelism only exploits the slack the graph allows.

### Q: What is rc_sys, which values does it take, and what actually changes when it is set?

`rc_sys` declares the environment class OpenRC is running in: `docker`, `podman`, `lxc`, `openvz`, `systemd-nspawn`, `vserver`, `uml`, `xen0`/`xenU`, `jail` (BSD), `prefix` (Gentoo Prefix), `subhurd`, `rkt` — or unset for autodetection. Its effect is mediated through the `keyword` masks in service scripts: a script with `keyword -docker -lxc` simply no-ops when `rc_sys` matches, so gettys, module loading, and fsck never fail inside containers. It also trims behavior like hotplugging and shapes which boot steps apply. The subtle rule from rc.conf: set the value representing the environment you are *presently* in, not what the platform is capable of.

### Q: How does OpenRC use cgroups, concretely?

Per service: OpenRC creates a dedicated cgroup per service (unified mode: `/sys/fs/cgroup/openrc/<service>`), governed by `rc_cgroup_mode` (unified/legacy/hybrid) with v2 controllers enabled via `rc_cgroup_controllers` and limits written from `rc_cgroup_settings` (`memory.max`, `pids.max`, ...), settable globally or per service in `/etc/conf.d/<svc>`. The second use is cleanup: `rc_cgroup_cleanup="YES"` walks the escalation chain — stop signal + SIGCONT, optional SIGHUP, `rc_timeout_stopsec` (default 90 s) wait, then SIGKILL unless `rc_send_sigkill="NO"` — using cgroup v2's `cgroup.kill` where the kernel offers it, so orphaned daemon children cannot survive a service stop. Verification is reading `/sys/fs/cgroup/openrc/<svc>/cgroup.procs`.

### Q: Why do non-systemd desktops need elogind, and what runs instead of it if you go minimal?

Because a large slice of the desktop stack is written against the logind D-Bus API (`org.freedesktop.login1`): polkit authorizes power actions through it, desktop environments call it for session lifecycle and shutdown, and Wayland compositors (wlroots and friends) obtain DRM/input device access via a logind session. elogind is the extracted, standalone build of that API, which is what makes Gentoo/Devuan/Artix desktops work unmodified. The minimal alternative is seatd — a small seat-management daemon covering device arbitration for compositors that only need that layer — at the cost of losing the wider logind API surface (and polkit integration) that full DEs expect.

### Q: A service fails during boot. Walk through what happens next on an OpenRC system.

The transition continues — OpenRC's model is degrade, not abort. Dependents that `need` the failed service are skipped; `use`-dependent services still start. The state is recorded (`failed`, or `crashed` if the process died after being tracked), visible via `rc-status`/`rc-status -c`. On the next transition, `rc_crashed_start="YES"` retries crashed services. Operationally: read the reason from the console or `/var/log/rc.log` (enable `rc_logger` beforehand — timestamps are the point), fix the cause, `zap` the service if recorded state disagrees with reality, and converge with a bare `openrc`. Only a hard sysinit-stage failure escalates to the `rc_shell` rescue prompt (`/sbin/sulogin`), because without plumbing there is nothing left to degrade into.

### Q: Where does boot logging come from on OpenRC, and what are its limits compared with a journal?

From `rc_logger="YES"`: a logging helper captures the rc process's output to `rc_log_path` (default `/var/log/rc.log`) — plain text, timestamped per service start/completion, the primary boot-debugging artifact. Limits: it captures rc's own output only, not daemons' ongoing logs (those go to syslog — you assemble the journal replacement yourself); on Linux the sysinit runlevel cannot be captured (devfs must run first); and there is no querying, persistence policy, or structured metadata like journald provides (see [systemd — journald](../systemd/journald.md)). Practical setup: `rc_logger` for boot evidence, syslog for runtime evidence, and `rc_nocolor` if the log is consumed by tooling.

## References

- [rc.conf.5 blob — OpenRC GitHub](https://github.com/OpenRC/openrc/blob/master/man/rc.conf.5) — authoritative variable documentation
- [openrc(8) — Debian](https://manpages.debian.org/bookworm/openrc/openrc.8.en.html) — runlevel mechanics referenced throughout
- [openrc-run(8) — Debian](https://manpages.debian.org/bookworm/openrc/openrc-run.8.en.html) — script interpreter and cgroup handling
- [supervise-daemon(8) — Debian](https://manpages.debian.org/bookworm/openrc/supervise-daemon.8.en.html) — supervision used by service scripts
- [Gentoo wiki — OpenRC](https://wiki.gentoo.org/wiki/OpenRC) — Gentoo defaults, netifrc conventions
- [Alpine wiki — OpenRC](https://wiki.alpinelinux.org/wiki/OpenRC) — Alpine defaults, ifupdown-ng conventions
- [Devuan docs](https://docs.devuan.org/) — systemd-free integration including elogind-era desktop components

## Cross-References

- [OpenRC — Overview and Architecture](./overview-architecture.md) — the component map these settings tune.
- [OpenRC Runlevels and Service Management](./runlevels-services.md) — the operational layer rc.conf knobs act on.
- [OpenRC Service Scripts](./init-scripts.md) — the scripts that source rc.conf and conf.d files.
- [SysVinit — Parallel Booting](../sysvinit/parallel-booting.md) — startpar-era parallelism, the conservative ancestor of rc_parallel.
- [systemd — cgroups and Resource Control](../systemd/cgroups-resource-control.md) — the deep version of the cgroup policy OpenRC exposes thinly.
- [systemd — journald](../systemd/journald.md) — what replaces rc.log-style logging in the systemd world.
- [cron administration](../../admin/cron.md) — the timer substitute on OpenRC systems.
- [cgroups](../../../os/containers/cgroups.md) — kernel-side background for the cgroup sections.
- [init-systems README](../README.md) — section hub.
- [Init systems — comparison](../comparison.md) — where OpenRC's composition model sits across the families.
