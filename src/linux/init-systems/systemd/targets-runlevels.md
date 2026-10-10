# Targets and the Runlevel Compatibility Layer

## Overview

Targets are systemd's replacement for SysVinit runlevels — but the analogy is
only half true, and the half that is true explains most of systemd's boot
design. A target is a unit (`.target`) that groups other units and acts as a
*synchronization point*: reaching `multi-user.target` means, by definition,
that the whole dependency subtree hanging off it is active. A target runs no
process of its own; it is pure graph structure, a named milestone in the
transaction. That is the fundamental difference from runlevels, which were a
single global integer the init process stepped through sequentially.

Because targets are ordinary units, the machinery is uniform: you can
`isolate` into one, make one the boot default with a symlink, extend it with
drop-ins, and define your own. The runlevel *compatibility layer* — the
`runlevel*.target` aliases, `runlevel(8)` and `telinit(8)` — maps the old
integer interface onto this graph so legacy scripts and muscle memory keep
working. This page covers both: the native target model (boot chain, special
targets, isolation, custom targets) and the compatibility shim on top.
Companion reading: [boot-process.md](./boot-process.md) for the handover that
starts the manager, [dependency-management.md](./dependency-management.md)
for the algebra connecting targets to services, and
[systemctl-cli.md](./systemctl-cli.md) for the verbs used throughout.

## What a Target Is

A `.target` unit is the smallest unit type: typically just a `[Unit]` section
with `Description=`, `Wants=`/`Requires=` lists and `AllowIsolate=`. Three
properties define its role:

- **Grouping.** A target pulls in units via `Wants=`/`Requires=`. The
  on-disk mechanism is usually a directory of symlinks:
  `/etc/systemd/system/multi-user.target.wants/` containing one symlink per
  enabled service (created by `systemctl enable`). "Enabled" literally means
  "a symlink in some target's `.wants` directory exists".
- **Synchronization point.** Other units declare `After=multi-user.target`
  (or the target declares itself `Before=` something) to say "only when this
  whole milestone is reached". Targets make sparse ordering practical:
  instead of every service ordering against every other, services order
  against a handful of named milestones.
- **No process.** Unlike `init 3` — which *was* a program state in
  `/sbin/init` — a target has no PID, no process image, nothing to supervise.
  `systemctl status multi-user.target` shows "Loaded: loaded; Active:
  active" and a cgroup that is essentially empty. All the work is done by
  the services it gathered.

Two unit-file directives give targets their operational behavior:
`AllowIsolate=yes` marks a target safe to jump to with `systemctl isolate`,
and `DefaultDependencies=` gives every target `Requires=`/`After=sysinit.target`
plus `Conflicts=shutdown.target` + `Before=shutdown.target`, so targets
participate in boot and ordered shutdown by default. The full algebra,
including the rule that targets complement `Wants=`/`Requires=` with `After=`
edges, is dissected in [dependency-management.md](./dependency-management.md).

## The Boot Chain: sysinit, basic, default

The manager boots through three stacked milestones. Each is pulled in and
ordered after the previous one, and each absorbs one class of early work:

```mermaid
flowchart LR
    S["sysinit.target"] --> B["basic.target"]
    B --> M["multi-user.target"]
    M --> G["graphical.target"]
```

```text
systemd (PID 1)
  |
  v
sysinit.target     -- everything the OS needs before any real service:
  |                   local-fs.target + fsck, swap, systemd-journald,
  |                   systemd-udevd (+ udev-trigger), systemd-sysctl,
  |                   systemd-modules-load, systemd-random-seed,
  |                   systemd-tmpfiles-setup, cryptsetup, machine-id
  v
basic.target       -- "early userspace complete":
  |                   Requires/After sysinit.target; pulls in
  |                   sockets.target, timers.target, paths.target,
  |                   slices (cgroup hierarchy primed)
  v
default.target     -- /etc/systemd/system/default.target symlink
  |                   (usually -> multi-user.target or graphical.target)
  +--> multi-user.target  -- the full non-graphical system:
  |        |               getty.target (login ttys), sshd, dbus,
  |        |               cron, rc-local.service, logging/monitoring
  |        '-- graphical.target -- Wants=multi-user.target plus
  |                                display-manager.service (gdm/sddm)
  '-- (rescue / emergency are side exits, see below)
```

Per bootup(7), the phases are strictly ordered: `sysinit.target` completes
before `basic.target` starts, and services with the default
`DefaultDependencies` all carry `After=basic.target`, so ordinary daemons
start after both milestones. The remaining well-known targets have narrower
contracts, and knowing where they legitimately fit is a recurring interview
theme:

| Target | Contract | Typical legitimate use | Classic abuse |
|---|---|---|---|
| `sockets.target` | All socket units are active before services start | Socket-activation parallelism: every `.socket` is bound early, services start on demand | Adding non-socket units to it, or reading it as "network is up" — sockets are bound, servers not started |
| `timers.target` | All timer units active | Timers tick from here regardless of which service target you boot to | Making timers depend on services; timers belong at this layer |
| `getty.target` | Login consoles exist | Pulls `getty@tty1` etc.; logind spawns more via `autovt@ttyN` on demand | Sprawling static `getty@` instances instead of letting logind allocate |
| `network.target` | Ordering point only: net-configuration units order around it | `After=network.target` means "after the network *stack* is being set up", not "after I have an address" | Using it as "network ready" — it makes no such promise |
| `network-online.target` | "A usable connection exists" — but only if something implements the wait | A unit that truly needs the network sets `Wants=network-online.target` + `After=network-online.target` | Wanting it everywhere (slows boot) or forgetting that the *wait-online service* must be enabled for it to mean anything |

The `network.target` versus `network-online.target` trap is the single most
cited dependency bug in systemd land; its full anatomy (the DHCP race, the
`systemd-networkd-wait-online.service` enablement requirement) has its own
worked example in [dependency-management.md](./dependency-management.md).

## Special Targets

systemd.special(7) catalogs the reserved names the manager treats specially.
The ones that matter operationally:

| Target | Role | Notes |
|---|---|---|
| `default.target` | What PID 1 starts at boot end | Always a symlink (`/etc/systemd/system/default.target` → a real target); this indirection is what `set-default` and the kernel cmdline override |
| `multi-user.target` | The complete text-mode system | The de-facto "server boot finished" milestone; `AllowIsolate=yes`; runlevel 2/3/4 alias |
| `graphical.target` | multi-user + display manager | `Wants=multi-user.target` (so it includes everything textual) + `display-manager.service`; runlevel 5 alias |
| `rescue.target` | Single-user repair mode after `sysinit.target` completed | Pulls `sysinit.target`; root shell via `sulogin` on the console; the `single`/runlevel-1 analog |
| `emergency.target` | Bare emergency shell, as early as possible | Pulled in on early-boot failures (fsck, mount, cryptsetup); only the emergency shell exists — no sysinit services guaranteed |
| `poweroff.target` | Ordered shutdown to machine off | Runlevel 0 alias; conflicts with everything else, isolated at shutdown |
| `reboot.target` | Ordered shutdown to reboot | Runlevel 6 alias; execs `systemctl reboot` logic via `systemd-reboot.service` |
| `halt.target` | Halt without powering off | Rarely used directly; embedded and debugging |
| `shutdown.target` | The stop-everything comsat | Every default-dependencies unit is `Conflicts=`/`Before=` it; user units should never want to reorder against it manually |
| `final.target` | Late shutdown sync point | After services are gone: unmount remaining filesystems, then the shutdown exec |

`shutdown.target` deserves one explicit sentence because it is invisible until
it bites: it is the *negative* sync point — starting it (which shutdown does)
stops everything that conflicts with it — and its ordering semantics are what
make `Before=shutdown.target` the mandatory self-declaration for units with
`DefaultDependencies=no`. The custom-target footgun in the section below is
precisely a violation of that contract.

## Runlevel Compatibility

The SysV world had seven well-known states selected by a single integer
(`/etc/inittab` → `telinit N`; see
[inittab.md](../sysvinit/inittab.md) and [runlevels.md](../sysvinit/runlevels.md)).
systemd keeps the interface and deletes the machinery: the integers map onto
alias symlinks, and the two legacy binaries are thin clients over `systemctl`
semantics.

| SysV runlevel | systemd target | Alias providing compat |
|---|---|---|
| 0 | `poweroff.target` | `runlevel0.target` |
| 1, s, S | `rescue.target` | `runlevel1.target` |
| 2, 3, 4 | `multi-user.target` | `runlevel2.target`, `runlevel3.target`, `runlevel4.target` |
| 5 | `graphical.target` | `runlevel5.target` |
| 6 | `reboot.target` | `runlevel6.target` |

Implementation notes that make the compat honest rather than cosmetic:

- The aliases are real symlinks in `/usr/lib/systemd/system/`, so anything
  referencing `runlevel3.target` by name works.
- `telinit N` still exists (`telinit(8)`): 0/6 translate to poweroff/reboot,
  1/s/S to rescue, and 2–5 isolate the corresponding runlevel target — SysV
  syntax on top of target isolation.
- `runlevel(8)` still prints the classic `N 3` pair — but reads it from
  *utmp*, where `systemd-update-utmp` records target changes. On a system
  whose utmp was never updated (or a container without utmp), `runlevel`
  output can be empty even though targets are fine — a favorite gotcha.
- The 2/3/4 collapse onto `multi-user.target` follows the modern Debian
  reading: distributions historically disagreed about what 2 vs 3 vs 4 meant,
  and systemd ends that argument by not distinguishing them.
- `/etc/inittab` is ignored (bar a few generator-honored settings); real
  configuration moved to `default.target` and unit files.

## Rescue vs Emergency

Both targets give you a root shell via `sulogin` on the console, and both are
reached either deliberately (`systemctl isolate`, kernel cmdline) or
automatically by the manager when boot fails. The difference is *how much
system exists around the shell*:

| Property | `rescue.target` | `emergency.target` |
|---|---|---|
| Position in boot | After `sysinit.target` completed | As early as possible — jumped to from inside a failing sysinit |
| Pulls in sysinit? | Yes (`Requires=`/`After=sysinit.target`) | No — does not pull services beyond the emergency shell machinery |
| Local filesystems | Mounted (fsck passed) | Not guaranteed — may be unmounted or read-only |
| udev / journal / network stack | Up | Not guaranteed |
| Typical triggers | Admin: `systemctl isolate rescue.target`, `systemd.unit=rescue.target` | Automatic: fsck failure, missing/failing mount, cryptsetup failure; admin: `systemd.unit=emergency.target` |
| Exit path | `systemctl daemon-reload; systemctl isolate default.target` (or reboot) | Fix the blocker, `systemctl daemon-reload`, then continue boot — often a reboot is cleanest |
| Analog | SysV single-user mode (runlevel 1) | "Give me a shell before anything else can break" |

The practical triage rule: if the failure is *below* the filesystem layer
(bad `fstab` entry, corrupt fs, wrong LUKS passphrase), you land in
emergency — fix the cause before expecting mounts. If you *chose* a
maintenance mode, rescue gives you a working minimal system with disks
mounted. The `sulogin` shell itself, root's password requirement, and
locked-root handling are treated in [rescue (admin)](../../admin/rescue.md).

## Default Target Selection

Which tree boots is resolved in three steps, most specific wins:

1. **Kernel cmdline.** `systemd.unit=graphical.target` (or `rescue.target`,
   `emergency.target`, `multi-user.target`) forces the choice for this boot
   only; `systemd.mask=foo.service` / `systemd.wants=bar.service` additionally
   mask or add units for one boot. This is the standard trick for one-off
   recovery boots without touching persistent config.
2. **`/etc/systemd/system/default.target`.** The persistent setting: a
   symlink, normally to `/usr/lib/systemd/system/graphical.target` (desktop)
   or `multi-user.target` (server). `systemctl set-default multi-user.target`
   rewrites it and prints the link it created; `get-default` reads it.
3. **Fallback.** If nothing is set, the manager uses `default.target` shipped
   by the distribution preset logic, ultimately defaulting toward
   `multi-user.target`.

Note the direction of the symlink: `default.target` in `/etc` is the pointer;
the real targets in `/usr/lib` never move. The symlink *is* the
configuration — no two-digit script symlinks to renumber — so scripted
provisioning is a one-liner and the boot-time override is revertible by
definition, since the kernel cmdline never persists.

## Runtime Switching with isolate

`systemctl isolate NAME.target` (needs `AllowIsolate=yes` on the target) is a
transaction: start everything the new target wants, stop everything the
running system has that the new target does not. `systemctl isolate
multi-user.target` on a desktop therefore kills `display-manager.service` and
your X session; `systemctl isolate graphical.target` on a server starts a
display manager (and complains if none is installed/enabled); `systemctl
isolate rescue.target` drops to single-user and stops sshd — including the
session you typed it on, so do it from a console or expect the disconnect.

Operational rules that keep isolate from hurting:

- `--no-wall` is a choice, not a reflex: isolate and shutdown verbs
  wall-message logged-in users by default, which is *correct* for
  multi-user maintenance and annoying in scripts.
- Check what will die first: `systemctl list-dependencies --reverse <unit>`
  shows which targets pull it in; anything not reachable from the new
  target's tree stops.
- `isolate` is not `restart`: isolating the target you are already in still
  reconciles the tree (stops strays), but does not restart satisfied units.
- For "refresh the service stack" you usually want targeted `restart`s or
  `daemon-reload` — full isolation is a mode switch, not a refresh.

## Custom Targets and the shutdown Footgun

Custom targets are the supported way to define a service group you can
start/stop/isolate as one unit (a kiosk stack, a lab environment, an
application tier). The naive version works — until shutdown, because of
`DefaultDependencies`:

```ini
# /etc/systemd/system/kiosk.target
[Unit]
Description=Kiosk station stack
Wants=kiosk-app.service kiosk-browser.service
After=network-online.target
AllowIsolate=yes
```

With defaults in place this is correct: the target gets
`Conflicts=shutdown.target` + `Before=shutdown.target` implicitly, and the
services pulled in carry their own default shutdown ordering. The footgun is
`DefaultDependencies=no` — which you *must* set on units that live outside
the normal boot/shutdown window (early-boot units, emergency tooling, units
ordered directly against `sysinit.target`). The moment you opt out, every
implicit edge disappears and the manager will not guess for you:

```ini
# /etc/systemd/system/earlydata.target  (BAD example — missing shutdown edges)
[Unit]
Description=Early data plane
DefaultDependencies=no
Wants=earlydata.service
After=earlydata.service
# FORGOTTEN: Conflicts=shutdown.target
# FORGOTTEN: Before=shutdown.target
```

The consequence: at shutdown, `shutdown.target` starts and stops everything
conflicting with it — but units that neither conflict with nor order before
it have no *ordered* stop path left. They are killed only by the final
SIGTERM/SIGKILL sweep, with no `ExecStop` and logs that look like a crash.
The fixed version re-declares both edges (and, for units this early, ordering
against `sysinit.target` itself):

```ini
[Unit]
Description=Early data plane
DefaultDependencies=no
Wants=earlydata.service
After=earlydata.service
Conflicts=shutdown.target
Before=shutdown.target
After=sysinit.target
```

The general rule worth memorizing: `DefaultDependencies=no` is an
"assume manual responsibility" flag — the manager will happily build a unit
that boots fine and shuts down badly, and only bootup(7)'s documented
contracts tell you what to re-declare. The dependency semantics behind these
edges are expanded in [dependency-management.md](./dependency-management.md).

## Interview Questions

### Q: What actually is a target, given that it runs no process?

A target is a graph node with a name: a unit that groups other units through
`Wants=`/`Requires=` (materialized as `.wants` directory symlinks) and serves
as a synchronization point for `After=`/`Before=` ordering. "Reached" means
"everything hanging off it is active", which is why boot progress is measured
in targets (`sysinit` → `basic` → `default`) rather than in service counts —
and why a target has a state but no PID. It is the direct generalization of a
runlevel, minus the global integer: instead of one machine-wide state, you
have composable named milestones, several of which (sockets, timers, paths)
activate in parallel layers rather than sequence.

### Q: How do SysV runlevels map to systemd targets, and what remains of the old interface?

Runlevel 0 maps to `poweroff.target`, 1/s/S to `rescue.target`, 2/3/4 to
`multi-user.target`, 5 to `graphical.target`, 6 to `reboot.target`, each via
a `runlevelN.target` alias symlink. `telinit N` still works and translates to
isolate/poweroff/reboot operations; `runlevel(8)` still prints the classic
pair but sources it from utmp records written by `systemd-update-utmp`. What
is gone is the mechanism: no `/etc/inittab` respawn logic, no sequential
S/K symlinks, no single global integer — runlevels are now a compatibility
view over the target graph, and 2/3/4 collapse because no target exists for
their historical per-distribution distinctions.

### Q: Why does `After=network.target` not guarantee the network is usable, and what is the correct idiom?

`network.target` is an ordering synchronization point around which
network-configuring units order; it promises nothing about addresses. The
"usable network" promise is `network-online.target`, and it is passive: it
only waits if a wait-online implementation is enabled (e.g.
`systemd-networkd-wait-online.service` or `NetworkManager-wait-online.service`)
and only covers interfaces that daemon knows about. The correct idiom for a
genuinely network-dependent service is `Wants=network-online.target` plus
`After=network-online.target` in the unit, plus the wait-online unit enabled
on the system — otherwise the ordering edge points at a target that goes
active immediately and you get the classic DHCP race.

### Q: Compare rescue.target and emergency.target.

Both end at a `sulogin` root shell, but rescue runs *after* `sysinit.target`
(which it requires): filesystems checked and mounted, udev, journal and the
basic plumbing are up — it is the analog of SysV single-user mode and the
right place for deliberate maintenance. Emergency is the manager's panic
exit: it does not pull in sysinit services and is typically reached
automatically when early boot fails (fsck, mounts, crypto), so you may have
no mounts and no devices — the right place to fix the thing that broke boot.
Invocations differ too: rescue via `systemctl isolate rescue.target` or
`systemd.unit=rescue.target`; emergency mostly via `systemd.unit=emergency.target`
or an automatic failure path.

### Q: What are the dangers of `systemctl isolate`?

It atomically starts the chosen target and stops every unit not in its
dependency tree — so on a multi-user system, isolating rescue or a custom
target tears down sshd, networking and unrelated services in one step,
including your own session. It requires `AllowIsolate=yes` on the target,
broadcasts a wall message unless `--no-wall` is given, and silently stops
anything the new tree does not want (the reverse-dependency check is
`list-dependencies --reverse`). Safe practice: use it for genuine mode
switches from a console, verify what hangs off the target first, and build
custom targets explicitly with `Wants=` lists and, when `DefaultDependencies=no`
is involved, hand-declared shutdown edges.

### Q: You set `DefaultDependencies=no` on a custom target and its services. What must you re-declare and why?

Everything the defaults used to provide. For boot: ordering that places the
unit after the plumbing it needs (typically `After=sysinit.target`, or
`After=basic.target` for normal services). For shutdown: `Conflicts=shutdown.target`
plus `Before=shutdown.target`, so the unit is *stopped, in order, by the
shutdown transaction* rather than reaped by the final SIGKILL sweep with no
`ExecStop` run. Defaults also give targets the complement rule (`Wants=`
gains matching `After=` edges) and services their sysinit anchoring — skip
them only for early-boot or shutdown-time units, and only when you can name
each edge you are now responsible for.

## References

- [systemd.target(5) — target unit files, default dependencies, AllowIsolate](https://www.freedesktop.org/software/systemd/man/latest/systemd.target.html)
- [bootup(7) — the canonical sysinit/basic/default phase narrative](https://www.freedesktop.org/software/systemd/man/latest/bootup.html)
- [systemd.special(7) — every reserved target and its contract](https://www.freedesktop.org/software/systemd/man/latest/systemd.special.html)
- [systemd.target(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.target.5.en.html)
- [bootup(7) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/bootup.7.en.html)
- [systemd.special(7) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.special.7.en.html)

## Cross-References

- [The systemd boot process](./boot-process.md) — the kernel-to-PID-1 handover and per-phase timeline this page's chain sits inside.
- [Dependencies and ordering](./dependency-management.md) — the Wants/Requires/After algebra targets are built from, including network-online anatomy.
- [systemctl — command reference](./systemctl-cli.md) — the verbs used here: isolate, set-default, get-default, rescue.
- [SysVinit runlevels](../sysvinit/runlevels.md) — the integer model the compatibility table maps from.
- [SysVinit inittab](../sysvinit/inittab.md) — the respawn and default-runlevel logic systemd replaced.
- [Rescue and recovery (admin)](../../admin/rescue.md) — hands-on rescue/emergency workflows, sulogin and locked-root handling.
- [init-systems hub](../README.md) — section overview and reading order.
- [Init system comparison](../comparison.md) — how each family models "system state" side by side.
