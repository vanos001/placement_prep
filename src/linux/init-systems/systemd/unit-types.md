# systemd Unit Types

## Overview

A *unit* is systemd's universal configuration object: a name with a type
suffix, a fragment file (or a programmatic origin), and a small state machine
the manager drives. Everything the service manager touches is a unit — the
daemons you care about (`.service`), the sockets they listen on
(`.socket`), the filesystems they need (`.mount`), the schedules that run
them (`.timer`), the hardware they need (`.device`), the cgroup
sub-hierarchies they live in (`.slice`), and the grouping nodes that tie a
boot together (`.target`).

This page is the catalogue: the state machine all units share, the full
twelve-type matrix, a per-type section with the directives that matter, and
the naming/escaping rules that bite everyone eventually. Unit *file* syntax,
drop-ins and templating get their own treatment in
[unit-files.md](./unit-files.md).

## The Unit State Machine

Every unit, regardless of type, moves through the same coarse states; the
manager exposes finer-grained *substates* (e.g. `dead`, `exited`, `running`,
`listening`, `plugged`, `mounted`, `waiting`) via `systemctl show -p ActiveState,SubState`:

```
inactive --> activating --> active --> deactivating --> inactive
                |                |
                v                v
             failed          failed   (on deactivation error / failed unit)
```

- `activating` — start job in flight: the process is starting (service), the
  socket is binding (socket), the device is appearing (device).
- `active` — the type-specific "ready" condition is met: process running,
  socket listening, mount mounted, device plugged.
- `deactivating` — stop job in flight (ExecStop running, processes being
  killed).
- `failed` — the unit terminated in error or a start-up condition failed.
  Clear with `systemctl reset-failed` (or automatically per `CollectMode=`).

What "active" means is entirely type-specific — that is the point of
`Type=notify` on services, `ListenStream=` on sockets, and so on. The
distinction between the coarse state and substates matters when scripting:
`systemctl is-active foo` returning `active` does not tell you whether a
oneshot exited (substate `exited`) or a daemon is running (substate `running`).

## The Unit Type Matrix

| Type | Wraps | Defined by | Activation trigger | Key directives |
|---|---|---|---|---|
| `.service` | A daemon or one-shot process | Unit file | Explicit, socket/bus/path/timer, dependency | `Type=`, `ExecStart=`, `Restart=` |
| `.socket` | A listening socket (or set of) | Unit file | Connection (if `Accept=`) or service start | `ListenStream=`, `Accept=`, `Service=` |
| `.target` | Grouping/synchronization point | Unit file | Explicit, dependencies, isolate | `Wants=`, `Requires=`, `AllowIsolate=` |
| `.device` | A kernel device | Generated from udev events | Device appearing (udev) | udev props `SYSTEMD_WANTS=`, `SYSTEMD_ALIAS=` |
| `.mount` | A mount point | Unit file or fstab generator | Explicit, dependencies, automount | `What=`, `Where=`, `Type=`, `Options=` |
| `.automount` | Autofs trigger for a mount | Unit file or fstab generator | First path access | `Where=`, `TimeoutIdleSec=` |
| `.timer` | A scheduled trigger | Unit file | Calendar/monotonic elapse | `OnCalendar=`, `OnBootSec=`, `Persistent=` |
| `.swap` | A swap device/file | Unit file or fstab generator | Explicit, boot | `What=`, `Priority=`, `Options=` |
| `.path` | A filesystem watcher | Unit file | Path condition satisfied | `PathExists=`, `PathChanged=`, `Unit=` |
| `.slice` | A cgroup hierarchy node | Unit file (mostly) | First contained unit starting | `Slice=`, resource limits |
| `.scope` | Externally created process group | Created via D-Bus/logind, no file | External call (`systemd-run --scope`, logind) | set at creation time |
| `.snapshot` | A saved unit state | Legacy | Legacy | removed from upstream releases |

Three structural facts to internalize: types are a *contract with the
manager*, not just a name (a `.socket` unit's whole purpose is to hold a
socket so the service doesn't have to); several types have no unit file at
all (`.device`, `.scope`); and all types share the `[Unit]` and `[Install]`
sections — the type-specific section (`[Service]`, `[Socket]`, ...) only
adds directives.

## Service Units

`.service` units wrap processes: long-running daemons (`Type=simple/exec/
notify/forking/dbus`), one-shot actions (`Type=oneshot`), and everything
between. The type's start-up semantics, `Exec*` command lines, restart
policies, watchdogs and the security sandbox are a full page of their own:
[service-units.md](./service-units.md). Minimal shape for orientation:

```ini
[Unit]
Description=Metrics exporter
After=network.target

[Service]
ExecStart=/usr/local/bin/exporter --port 9100
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Socket Units

`.socket` units let systemd bind listening sockets (AF_INET/6, UNIX, FIFOs,
and more) *before* the consuming service exists. Two payoff modes: service
start-up is no longer serialized behind socket availability, and — with
`Accept=yes` or on-demand activation — the service can be spawned only when
the first connection arrives. Every socket-activated service gains automatic
`Wants=`/`After=` on its socket, and the file descriptors arrive in the
service as fds 3+ (SD_LISTEN_FDS_START) with `LISTEN_FDS`/`LISTEN_PID` in the
environment. Full mechanics: [socket-activation.md](./socket-activation.md).

## Target Units

`.target` units are synchronization points and grouping nodes; they run no
process of their own. They are the runlevel replacement, the dependency
anchor points (`sysinit.target`, `multi-user.target`), and the packaging
mechanism for "start my whole stack" (`myapp.target` with
`Wants=myapp-api.service myapp-worker.service`). The boot chain, runlevel
compatibility and custom-target design are covered in
[targets-runlevels.md](./targets-runlevels.md).

## Timer Units

`.timer` units trigger other units on calendar times
(`OnCalendar=Fri 12:00`) or monotonic offsets (`OnBootSec=15min`), with
`Persistent=yes` to catch up missed runs after downtime (the cron
`anacron`-style behavior), `RandomizedDelaySec=` to spread load, and
`list-timers` for visibility. Calendar spec syntax, the `Persistent` catch-up
model and the cron comparison live in [timers.md](./timers.md).

## Mount, Automount and Swap Units

`.mount`, `.automount` and `.swap` units are systemd's take on what `/etc/fstab`
describes — and in fact you usually do not write them: the **fstab
generator** reads `/etc/fstab` at boot (and at `daemon-reload`) and creates
the units for you. You *can* write native fragments, but the unit name must
match the mount path (see the escaping section below), which is clunky; the
fstab route plus `x-systemd.*` options is the idiomatic path.

The `x-systemd.*` fstab options that matter (parsed by the generator and
documented in `systemd.mount(5)`):

| fstab option | Effect |
|---|---|
| `x-systemd.automount` | Create an `.automount` instead of mounting at boot — the mount happens on first access |
| `x-systemd.idle-timeout=60` | Unmount the automounted filesystem after 60 s idle |
| `x-systemd.mount-timeout=10` | Per-mount timeout instead of the default 90 s |
| `x-systemd.requires=units` | Add a `Requires=` to other units (e.g. a tunnel service) |
| `x-systemd.requires-mounts-for=/path` | Mount `/path` first (Requires+After for its mount unit) |
| `x-systemd.wants=` / `x-systemd.after=` | Weaker pull-in / pure ordering from fstab |
| `x-systemd.device-timeout=` | How long to wait for the backing device to appear |
| `noauto`, `nofail`, `_netdev` | Honored as usual; `noauto` skips `local-fs.target` pull-in; `nofail` downgrades failure |

The canonical network-filesystem recipe — do not let a dead NFS server
block boot, but keep it transparent:

```ini
# /etc/fstab
nas:/export/media  /mnt/media  nfs4  noauto,x-systemd.automount,x-systemd.idle-timeout=60,_netdev  0  0
```

Boot proceeds without touching the network mount; the first `ls /mnt/media`
triggers `mnt-media.automount` → `mnt-media.mount`. The same pattern is the
answer to "my box hangs 90 s at boot on a dead NFS server": `noauto,x-systemd.automount`
plus `x-systemd.mount-timeout=5` bounds the damage to the moment of first
access.

Native `.mount` fragments exist for when fstab is not the right home
(containers, initrd, generated systems):

```ini
# /etc/systemd/system/mnt-data.mount  (name MUST match the path)
[Mount]
What=/dev/disk/by-uuid/47d3-8f21
Where=/mnt/data
Type=ext4
Options=defaults,noatime
```

`.automount` pairs a `Where=` with the referenced mount unit; `.swap` units
mirror `[Swap] What=/Priority=/Options=`. `RequiresMountsFor=` (in any unit)
is the dependency shorthand for "this unit needs this path mounted" — it
adds Requires+After on the relevant mount units automatically.

## Device Units

`.device` units have **no unit files** — the manager creates them from udev
events as the kernel discovers hardware, so their lifecycle mirrors the
device's. You configure their *behavior* from udev rules, using the systemd
properties udev understands:

```
# /etc/udev/rules.d/99-backup-disk.rules
ACTION=="add", SUBSYSTEM=="block", ENV{ID_FS_LABEL}=="backup", \
  ENV{SYSTEMD_WANTS}="backup-sync.service", ENV{SYSTEMD_ALIAS}="/dev/disk/by-label/backup"
```

- `SYSTEMD_WANTS=` — pull in a unit when the device appears: the standard
  "react to hardware" hook (hotplug service start).
- `SYSTEMD_ALIAS=` — give the device unit a stable extra name (an alias
  symlink other units can reference).
- `TAG+="systemd"` — ensure the device is exposed to systemd at all for
  devices outside udev's default whitelist.

Mount units generated from fstab are automatically bound to their backing
device (a `BindsTo=` + `After=` relationship), so unplugging the device stops
and unmounts the mount — the mechanism behind "yanked USB disk" behaving
sanely. Devices also participate in `IgnoreOnIsolate=` (default true for
device units) so isolating targets does not rip devices out.

## Path Units

`.path` units are inotify-driven triggers for other units — the native
replacement for hand-rolled inotify scripts and cron-plus-timestamp hacks:

| Directive | Fires when |
|---|---|
| `PathExists=` | The path exists (checked on events and timer) |
| `PathExistsGlob=` | Any path matches the glob |
| `PathChanged=` | The path or a file inside was closed after writing (IN_CLOSE_WRITE) |
| `PathModified=` | Writes are observed (IN_MODIFY) — fires more often than `PathChanged` |
| `DirectoryNotEmpty=` | The directory has entries (spool-dir pattern) |

```ini
[Unit]
Description=Process inbound invoices

[Path]
DirectoryNotEmpty=/var/spool/invoices
Unit=invoice-worker.service
MakeDirectory=no
# TriggerLimitIntervalSec=, TriggerLimitBurst= throttle event storms

[Install]
WantedBy=multi-user.target
```

The triggered unit is `invoice-worker.service` (default: the unit file with
the same stem, `invoices.path` → `invoices.service`). The idiomatic pattern
is a **self-draining loop**: the service empties the directory, and the path
unit's condition simply stays true (or refires) until the spool is empty.
`PathChanged` vs `PathModified` in one line: use `PathModified` for "some
activity happened" and `PathChanged` for "a file reached its final state".

## Slice and Scope Units

`.slice` units name nodes of the cgroup tree. The implicit root is
`-.slice`; standard children are `system.slice` (normal system services),
`user.slice` (all user sessions and user managers), `machine.slice`
(containers/VMs registered with machined). A unit's placement is chosen with
`Slice=` (services default to `system.slice`); templated services get an
automatic per-template slice (`foo@.slice`) so instances can be limited as a
group. Because slices map directly onto cgroups, they are the carrier for
resource control — CPU/IO/memory limits, accounting, oomd pressure rules:
[cgroups-resource-control.md](./cgroups-resource-control.md).

`.scope` units are cgroups for processes systemd did **not** spawn: logind
puts each login session in `session-N.scope`, container runtimes register
their payloads as scopes, and `systemd-run --scope` wraps an arbitrary
command. Scopes have no unit file and no start/stop semantics of their own —
they exist so externally managed process trees get a supervised cgroup, a
name, and resource settings applied at creation.

## Unit Names, Aliases and Escaping

Rules worth knowing precisely:

- A unit's name must match its filename (minus directory); names are limited
  to 256 characters and may not contain `/`, shell glob characters (`*?`),
  or whitespace — hence escaping.
- **Aliases** are plain symlinks to the unit file: `[Install] Alias=foo.service`
  creates one at `systemctl enable` time; `systemctl` follows alias chains
  when you ask for a unit by any of its names.
- **Template units** end in `@.service` (etc.); instances are
  `template@instance.suffix` where the instance string is arbitrary and
  escaped — see [unit-files.md](./unit-files.md).
- Path-derived names (mounts, and unit names generated from paths) replace
  `/` with `-` and escape non-`[A-Za-z0-9._]` bytes as `\xNN`:

| Input | `systemd-escape` output | Context |
|---|---|---|
| `/home/user` | `home-user.mount` | mount unit for the path |
| `/mnt/My Disk` | `mnt-My\x20Disk.mount` | space escaped as `\x20` |
| `/data/backups 2024` | `data-backups\x202024` | plain path escaping (`-p`) |
| `hello world` | `notify@hello\x20world.service` | template instance via `--template=notify@.service` |

```
$ systemd-escape -p --suffix=mount "/mnt/My Disk"
mnt-My\x20Disk.mount
$ systemd-escape --template=notify@.service "hello world"
notify@hello\x20world.service
$ systemd-escape --unescape 'mnt-My\x20Disk'
/mnt/My Disk        # (--unescape with -p)
```

The classic interview trap: writing `etc-fstab.mount` style names by hand
without realizing the name *is* the path — a mount unit for `/etc/fstab`
would be `etc-fstab.mount`, and a typo in the name means a mount unit for a
path that does not exist. Always derive names with `systemd-escape`.

## Where Unit Files Live (Quick Map)

Load precedence, highest first for the main fragment: `/etc/systemd/system`
(admin) > `/run/systemd/system` (runtime) > `/usr/lib/systemd/system`
(vendor). Drop-ins from all of these merge. Generators inject units under
`/run/systemd/generator*`. The full ordered list, drop-in semantics and
template details are the subject of [unit-files.md](./unit-files.md); the
one-liner for the exam is *admin beats runtime beats vendor*.

## Interview Questions

### Q: What is the difference between a .service, a .socket and a .timer for the same daemon?

They are three contracts with the manager around one daemon. The `.socket`
holds the listening socket from boot (so connections queue in the kernel and
start order stops mattering), the `.service` holds the process lifecycle
(when it runs, how it restarts), and the `.timer` expresses when it should be
triggered. Socket-activated services additionally get automatic
Wants/After wiring between the pair, and `systemctl start` on the service
starts the whole trio where relevant. The pattern replaces inetd-style
super-servers with per-service units and no extra daemon.

### Q: Why would you choose a .path unit over a cron job that checks for files?

Latency and correctness. A `.path` unit reacts to inotify events the moment
the condition holds — no polling interval, no duplicate runs (the trigger
unit runs once per condition transition), and no timestamp race. Cron is the
right tool for wall-clock schedules; path units are the right tool for
"something appeared/changed". For spool directories, `DirectoryNotEmpty=` +
a service that drains the directory is the canonical loop, with
`TriggerLimitBurst=` guarding against event storms.

### Q: How do mount units get created if nobody writes them?

The fstab generator. At boot and at `daemon-reload`,
`systemd-fstab-generator` parses `/etc/fstab` and synthesizes `.mount`,
`.automount` and `.swap` units under `/run/systemd/generator`, translating
`x-systemd.*` options into native directives. A `noauto,x-systemd.automount`
entry becomes an automount unit instead of a boot-time mount. Native
fragments override generated ones, and hand-written `.mount` files must be
named after the escaped mount path (`/mnt/My Disk` → `mnt-My\x20Disk.mount`).

### Q: What is a .scope unit and who creates them?

A scope is a cgroup membership record for processes systemd did not start.
There is no unit file; scopes are created programmatically — logind wraps
every login session in `session-N.scope`, `systemd-run --scope` wraps an
arbitrary command, and container runtimes register their process trees as
scopes with machined. The scope gives those externally managed processes a
supervised cgroup so resource limits, accounting and clean kill-on-shutdown
apply uniformly to everything on the system.

### Q: A service must not start before /var/data is mounted. Write the dependency.

`RequiresMountsFor=/var/data` in the `[Unit]` section — it adds the
equivalent of `Requires=` + `After=` on every mount unit along the path. The
longer manual form is `Requires=var-data.mount` plus `After=var-data.mount`,
and forgetting the `After=` is the classic bug: requirement without ordering
starts both units concurrently. For fstab-managed filesystems, the
`x-systemd.requires-mounts-for=` option provides the same from fstab.

### Q: What is the difference between a target and the SysV runlevel it replaces?

A runlevel was a global integer state the whole machine was in, maintained by
init, with services attached via sequence-numbered symlinks. A target is just
a unit — a named synchronization point others can Want/Require and order
against — and many can be "active" simultaneously (multi-user, graphical,
getty, custom app targets). There is no global mode switch; `isolate` merely
starts one target and stops everything not pulled by it. The compatibility
layer (`runlevel(8)`, `runlevelN.target` aliases, telinit) maps the old
integers onto specific targets.

## References

- [systemd.unit(5) — unit grammar shared by all types, name rules, conditions](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [systemd.device(5) — device units and udev integration](https://www.freedesktop.org/software/systemd/man/latest/systemd.device.html)
- [systemd.mount(5) — mount units and the fstab generator](https://www.freedesktop.org/software/systemd/man/latest/systemd.mount.html)
- [systemd.automount(5) — automount units and idle timeouts](https://www.freedesktop.org/software/systemd/man/latest/systemd.automount.html)
- [systemd.path(5) — path units and inotify triggers](https://www.freedesktop.org/software/systemd/man/latest/systemd.path.html)
- [systemd.swap(5) — swap units](https://www.freedesktop.org/software/systemd/man/latest/systemd.swap.html)
- [systemd.directives(7) — alphabetical index of every directive](https://www.freedesktop.org/software/systemd/man/latest/systemd.directives.html)
- [systemd.unit(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.unit.5.en.html)
- [systemd.device(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.device.5.en.html)
- [systemd.mount(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.mount.5.en.html)
- [systemd.automount(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.automount.5.en.html)
- [systemd.path(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.path.5.en.html)
- [systemd.swap(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.swap.5.en.html)

## Cross-References

- [Unit files — syntax, loading, drop-ins and templating](./unit-files.md) — how fragments, drop-ins and templates are authored and resolved.
- [Service units in depth](./service-units.md) — the `.service` row of the matrix, expanded.
- [Socket activation](./socket-activation.md) — the `.socket` type as a startup-ordering tool.
- [Timers](./timers.md) — the `.timer` type, calendar specs and cron comparison.
- [Targets and runlevels](./targets-runlevels.md) — the `.target` type as grouping and boot structure.
- [cgroups and resource control](./cgroups-resource-control.md) — slices and scopes as the resource-control substrate.
- [Init system comparison](../comparison.md) — how the unit abstraction maps to other init families' concepts.
- [udev (admin)](../../admin/udev.md) — the rule engine behind `.device` units.
- [devtmpfs](../../kernel/filesystems/devtmpfs.md) — the kernel device-node filesystem udevd manages.
