# Dependencies and Ordering in systemd

## Overview

Every systemd boot is a *transaction*: the manager loads unit files, builds a
directed graph of dependencies and ordering constraints, verifies it, and
installs a set of jobs that runs as much of the graph in parallel as the
ordering allows. Two different kinds of edges make up that graph, and keeping
them mentally separate is the core skill this page teaches:

- **Requirement edges** (`Wants=`, `Requires=`, `Conflicts=`, ...) answer
  "*which units are involved*" — they pull units into the transaction.
- **Ordering edges** (`After=`, `Before=`) answer "*in what sequence*" — they
  constrain when jobs run, but pull in nothing.

The #1 practical error in the entire unit-file ecosystem is conflating the
two: writing `After=` alone and wondering why nothing got pulled in, or
writing `Requires=` alone and wondering why two units raced. The #2 error is
reaching for `network.target` when the unit actually needed the
`network-online.target` contract. Both are dissected below with worked
examples.

This page is the algebra reference; where the edges live on disk (`.wants`
symlink directories, drop-ins) is [unit-files.md](./unit-files.md), the
per-type lifecycle that requirements act on is
[service-units.md](./service-units.md), and the transaction engine's internals
as seen from the D-Bus API are in
[systemd-internals (admin)](../../admin/systemd-internals.md).

## The Cardinal Rule: Requirements Pull, Ordering Schedules

The two edge families are orthogonal by design. Consequences worth internalizing:

- `After=foo.service` with no requirement edge does nothing at start time if
  `foo.service` is inactive: ordering constrains jobs that exist, it does not
  create them. The unit starts immediately, alone.
- `Wants=foo.service` with no ordering edge pulls `foo.service` into the
  transaction and starts it *in parallel* with you — a race, not a sequence.
- Therefore the idiomatic pair is `Wants=foo.service` + `After=foo.service`
  (pull in, then wait), or `Requires=` + `After=` when failure of `foo` must
  also stop you.
- The only places ordering comes for free: `DefaultDependencies` (adds
  `After=sysinit.target`/`basic.target` and, for targets, complements every
  `Wants=`/`Requires=` with a matching `After=`), and `Requisite=`-style
  explicit checks.

```ini
# Race (bug): pulled in but started in parallel — may bind before network exists
[Unit]
Wants=network-online.target

# Correct: pulled in AND sequenced
[Unit]
Wants=network-online.target
After=network-online.target
```

The network case deserves its own paragraph because it is the canonical
interview question. `network.target` is a synchronization point that the
network *configuring* units order themselves against; it goes active early
and promises nothing about addresses. `network-online.target` is the "a
usable connection exists" promise — but it is passive: it only waits if a
wait-online implementation (`systemd-networkd-wait-online.service`,
`NetworkManager-wait-online.service`) is enabled on the system, and it only
covers the interfaces that daemon manages. A service that genuinely needs the
network declares `Wants=network-online.target` + `After=network-online.target`;
a service that merely needs the stack (a listener that binds fine on 0.0.0.0
before DHCP) should *not*, because wanting network-online needlessly delays
boot by the wait-online timeout whenever links are slow.

## Requirement Directives

Each requirement directive answers three questions differently: does it pull
the dependency into the transaction; what happens if the dependency fails to
activate; and what happens when the dependency stops (explicitly, or by
crashing) later. This table is the reference for the fine print:

| Directive | Pulls in? | Dependency fails to activate | Dependency explicitly stopped | Dependency crashes/is deactivated later | Notes |
|---|---|---|---|---|---|
| `Wants=` | Yes | Ignored — you still start | No effect on you | No effect on you | The default "group with me" edge |
| `Requires=` | Yes | You are not started (job fails) | You are stopped too | You are stopped (deactivated), not restarted | Failure propagates one way: stopping you does *not* stop the dependency |
| `Requisite=` | No | Start fails immediately if it is not already active | No effect on you (checked at start only) | No effect | The "fail fast, pull nothing" precondition |
| `BindsTo=` | Yes | You are not started | You are stopped too | You are stopped — on *any* deactivation, including crashes and device removal | Strongest lifecycle coupling; pair with `After=` |
| `Upholds=` (v248+) | Yes | Ignored at your start | Dependency is started again while you remain active | Dependency is restarted automatically | Continuous `Wants=`: keeps the dependency up as long as you are up |
| `PartOf=` | Yes (Wants-like) | Ignored | No effect | No effect | But: stop/restart *of the listed unit* propagates to you — the target-bound-service edge |
| `Conflicts=` | Negative pull | Starting it stops you (or refuses the job) | n/a | n/a | Mutual exclusion; both in one transaction is an error |
| `OnFailure=` | On your failure | Starts the listed unit when you enter `failed` | No effect | No effect | Pair with `After=` to the listed unit; the alerting hook |
| `OnSuccess=` (v250+) | On clean exit | Mirror of `OnFailure=` | No effect | No effect | Completion notifications |
| `PropagatesStopTo=` | No | n/a | n/a | n/a | When *you* stop, the listed units are stopped too — one-directional stop propagation |

Reading the table by row reveals design intent. `Wants=` is soft grouping:
databases, optional helpers, things you want up but can live without.
`Requires=` is "I am not meaningful without this" — but note it protects you
only against the dependency's *deactivation*, it does not restart you or the
dependency. `BindsTo=` extends that to "if it goes away for any reason, so do
I" — the correct edge for services bound to a device, a mount, or a session
target. `PartOf=` exists precisely for the reverse of `BindsTo=`: services
that should follow a target's restart (that is how `user@.service`'s
per-user targets and desktop session targets propagate restarts to their
members). `Conflicts=` is the only negative dependency and the tool for
"never alongside" (display managers conflict with each other;
`rescue.service` conflicts with the normal gettys). Precise man-page wording
lives in `systemd.unit(5)`, linked in the References.

## Ordering Directives

`After=` and `Before=` are pure scheduling constraints between *jobs*: if A
is `After=` B and both appear in one transaction, B's job completes (B
reaches `active`, or its start job finishes) before A's start job begins.
Three subtleties that separate intermediate from expert answers:

- **Ordering is sparse and explicit.** There is no global sequence; two units
  with no path of `After=` edges between them start simultaneously. Parallelism
  is the default, ordering is opt-in — the exact inversion of SysVinit's
  numbered symlinks.
- **Ordering implies nothing about runtime coupling.** If B crashes five
  minutes later, A neither notices nor cares. Survival coupling is
  requirements' job; the two families never mix automatically.
- **Edges to nonexistent units are legal** and simply inert (the manager logs
  nothing at boot; `systemd-analyze verify` flags suspicious ones). This is
  what lets a unit file say `After=postgresql.service` on machines that will
  never run PostgreSQL.

Ordering also composes across the graph, not just pairwise: if A is `After=`
B and B is `After=` C, then A is effectively after C (transitively, through
the job graph). And ordering against *targets* is the idiomatic way to
position units in boot phases — `After=network-online.target`,
`After=postgresql.service` — rather than chaining every service to every
prerequisite by hand.

## DefaultDependencies

`DefaultDependencies=yes` (the default) injects an implicit edge set so that
ordinary units "just work" across boot and shutdown without declaring
anything:

- **Service units** gain `Requires=`/`After=sysinit.target`,
  `After=basic.target`, and `Conflicts=shutdown.target` +
  `Before=shutdown.target` — services start after early boot and are stopped,
  in order, by the shutdown transaction.
- **Target units** gain `Requires=`/`After=sysinit.target`,
  `Conflicts=shutdown.target` + `Before=shutdown.target`, plus the complement
  rule: every configured `Wants=`/`Requires=` on a target automatically gains
  a matching `After=` edge (unless the referenced unit itself opted out).
- Socket, timer, path, mount and other unit types carry their own documented
  default sets (see `systemd.unit(5)`); sockets, for instance, order before
  their services through `Before=` relationships the manager maintains.

Opting out (`DefaultDependencies=no`) is for units that live *outside* the
normal boot/shutdown window: units that must run during sysinit itself
(`systemd-journald.service`, fsck, mount units), units that run at the very
end of shutdown, and custom targets built as isolated worlds. When you opt
out, you take over the edge list by hand — at minimum re-declare the
shutdown pairing (`Conflicts=shutdown.target`, `Before=shutdown.target`)
and whatever early ordering you actually need. The full footgun walkthrough
(shutdown kills such units with SIGKILL and no `ExecStop` when the pairing
is forgotten) is in [targets-runlevels.md](./targets-runlevels.md). The
symptom checklist when debugging a `DefaultDependencies=no` unit: does it
start too early (races udev/journald), and does it die uncleanly at shutdown.

## Target Grouping: .wants Symlinks and add-wants

Requirement edges have an on-disk representation that predates most users'
interaction with it. `systemctl enable foo` reads `foo`'s `[Install]`
section (`WantedBy=multi-user.target`) and symlinks:

```text
/etc/systemd/system/multi-user.target.wants/foo.service
    -> /usr/lib/systemd/system/foo.service
```

Loading `multi-user.target` therefore pulls in everything in its `.wants`
directory — which is what "enabled" means mechanically. Two verbs extend this
grouping mechanism without touching `[Install]`:

```bash
systemctl add-wants multi-user.target my-monitoring.service   # WantedBy-style, admin-owned
systemctl add-requires multi-user.target my-critical.service  # Requires-style, stronger
```

`add-wants`/`add-requires` are the admin's tool for attaching *existing*
units to a target from the outside — no unit-file edit, no `[Install]`
section needed, works on units you do not ship (e.g. attaching a vendor
service to a custom target). Symlinks land in `/etc` (persistent) or `/run`
(with `--runtime`), and `disable` removes `[Install]`-derived links while
`revert` removes admin overrides — so a `add-wants`-created link survives
`disable` but is cleaned by `revert`, a distinction that occasionally shows
up in real post-mortems.

## The Transaction Engine, from the CLI

When you submit a lifecycle verb, the manager does not act immediately; it
computes a *transaction*: the closure of requirement edges from the requested
unit, converted to jobs (`start`/`stop`/`restart` per unit), deduplicated
(two paths requiring the same unit produce one job), checked against ordering
cycles, and reconciled with already-queued jobs according to `--job-mode` (see
[systemctl-cli.md](./systemctl-cli.md) for the mode table). Only then are
jobs run, each as soon as its `After=` predecessors allow — which is where
boot parallelism physically comes from.

From the command line you can watch all of this:

```bash
systemctl list-jobs                 # the queue: JOB UNIT TYPE STATE (waiting/running)
systemctl list-dependencies nginx.service              # what pulls in with it
systemctl list-dependencies --reverse nginx.service    # who depends on it
journalctl -b -u <unit> | grep -i "cycle\|deleted"     # cycle forensics
```

When the closure contains an ordering cycle, the transaction cannot be
totally ordered, so the manager breaks it: it picks a job to delete, logs
`Breaking ordering cycle by deleting job X/start`, and X simply does not
start this boot (or fails the request outright for interactive transactions).
The fix is always in the unit files — an `After=` edge added by a drop-in is
the usual culprit, which is why `systemctl cat` (merged view) is the first
triage step, followed by `systemd-analyze verify` for an offline check.

## Stop Propagation and Reverse Dependencies

Start-time coupling is intuitive; stop-time coupling is where
misunderstandings live. The rule: **stopping a unit stops nothing that
depends on it**, unless an explicit propagation edge exists (`Requires=`
stops dependents on *explicit* stop of the dependency; `BindsTo=` on any
deactivation; `PartOf=`/`PropagatesStopTo=` in their one-directional ways).
Plain `Wants=`/`After=` propagate nothing — by design, because shutting down
one subsystem should not cascade through the graph like dominoes.

```bash
$ systemctl stop postgresql.service     # app.service keeps running (Wants=, not Requires=)
$ systemctl list-dependencies --reverse app.service
app.service
● └─nginx.service                       # nginx pulls app: stopping app does NOT stop nginx
```

`list-dependencies --reverse` is the tool for asking "who will notice if this
dies" — and conversely `systemctl stop` on a *target* demonstrates the one
case where propagation feels automatic: stopping a target stops its members
only through their own default `Conflicts=`/`PartOf=` relationships, not
because targets push. When you *want* cascade-down behavior ("stop the app
tier when its database vanishes"), the explicit tools are `BindsTo=` +
`After=` (device/mount-bound services) or `PropagatesStopTo=` (one-way
shutdown of companions) — never `Conflicts=`, which is mutual exclusion, not
lifecycle following.

## Worked Example: A Web Application Graph

A three-tier deployment with real constraints: the app needs the network and
the database; nginx needs the app. Unit fragments first:

```ini
# /etc/systemd/system/myapp.service   [Unit] section
[Unit]
Description=Application server
Wants=network-online.target
After=network-online.target
Requires=postgresql.service
After=postgresql.service

# /etc/systemd/system/nginx.service.d/dep.conf
[Unit]
Wants=myapp.service
After=myapp.service
```

The resulting graph, with edge types annotated:

```text
                 network-online.target
                        ^  (Wants + After)
                        |
   postgresql.service <-+-- myapp.service
        ^  (Requires + After)     ^  (Wants + After)
        |                         |
        +-------- myapp ----------+           nginx.service
                                             ^  (Wants + After)
                                             |
                                        (client traffic)
```

What the manager does with `systemctl start nginx.service`: the transaction
closure is {nginx, myapp, network-online.target, postgresql}; ordering gives
two independent front edges — `network-online.target` (waiting on
wait-online) and `postgresql.service` — which start **in parallel**, then
`myapp.service`, then `nginx.service`. Two observations to state in an
interview: first, database start and network wait overlap, so total latency
is max of the two, not the sum; second, `Requires=` on the database means a
*stopped* database stops `myapp` (propagation), but a *crashed* one leaves
`myapp` deactivating too — neither edge restarts anything, which is what
`Restart=` inside `postgresql.service` (and `Upholds=` if you want the
manager to keep pulling it) is for. Stop order is the exact reverse of start
order per the same edges.

## Classic Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `After=` without `Wants=`/`Requires=` | "The dependency never starts" — ordering with nothing pulled | Add `Wants=` (soft) or `Requires=` (hard) |
| `Wants=` without `After=` | Two units race; "sometimes it works" | Add the matching `After=` |
| `Requires=` used as ordering | Units still start in parallel | `Requires=` pulls, never sequences — pair with `After=` |
| `After=network.target` as "network ready" | Bind/connect failures on slow DHCP | `Wants=network-online.target` + `After=` + wait-online unit enabled |
| Expecting `Requires=` to restart on crash | Dependency crashes; dependents stop but nothing comes back | `Restart=` on the dependency, or `Upholds=` from the dependent |
| `Conflicts=` used to express "stop when X stops" | Mutual exclusion chaos at start | `BindsTo=`/`PartOf=`/`PropagatesStopTo=` for lifecycle following |
| Circular `After=` via accumulated drop-ins | `Breaking ordering cycle by deleting job ...` in the journal | `systemctl cat` both ends, remove the redundant edge, `systemd-analyze verify` |
| Sprinkling `Requires=` everywhere | One failure fails a huge subtree | Prefer `Wants=`; reserve `Requires=`/`BindsTo=` for true hard coupling |
| Editing units without `daemon-reload` | Manager executes stale config at next restart | `systemctl daemon-reload` (see [systemctl-cli.md](./systemctl-cli.md)) |

## Runtime Versus Persistent Edits

Every mechanism on this page has a persistent form (under `/etc`) and a
runtime form (under `/run`, gone at reboot) — choosing deliberately is an
operational skill:

| Operation | Persistent | Runtime-only |
|---|---|---|
| Override a unit's dependencies | `systemctl edit` → `/etc/systemd/system/X.service.d/override.conf` | `systemctl edit --runtime` → same under `/run` |
| Attach a unit to a target | `systemctl add-wants TARGET UNIT` (writes `/etc`) | `systemctl add-wants --runtime TARGET UNIT` |
| Enable for boot | `systemctl enable UNIT` | `systemctl enable --runtime UNIT` |
| Property change (resource limits) | `systemctl set-property X CPUWeight=50` | `systemctl set-property --runtime ...` |
| Mask a unit | `systemctl mask UNIT` | `systemctl mask --runtime UNIT` |

The runtime forms are how you test a dependency theory without committing it:
`edit --runtime` + `daemon-reload` + restart, verify with
`list-dependencies`, then either promote to a persistent edit or `revert`.
Note the failure asymmetry: a runtime edit silently vanishes at reboot (by
design), while a persistent edit you forgot to `daemon-reload` lingers
invisibly until the next restart applies it — the two classic "it behaved
differently after reboot / didn't change until reboot" bugs, both rooted in
the same persistent/runtime split.

## Interview Questions

### Q: Explain the difference between requirement and ordering dependencies, and why systemd separates them.

Requirement directives (`Wants=`, `Requires=`, `Conflicts=`, ...) decide the
*membership* of a transaction — which units are pulled in — while ordering
directives (`After=`, `Before=`) decide the *sequence* of jobs within it.
They are orthogonal: ordering without a requirement edge is inert (nothing
pulled), and a requirement edge without ordering starts both units in
parallel. The separation is what makes sparse parallel boot possible: you
declare only the sequencing you actually care about, and everything without
an explicit ordering path runs concurrently. SysVinit had no such split —
sequence numbers implied both membership and order — which is exactly why its
graphs were serial.

### Q: What is the deal with network.target versus network-online.target?

`network.target` is an early ordering synchronization point around which
network-configuring units arrange themselves; it says nothing about
addresses being available. `network-online.target` carries the "usable
connection exists" contract, but it is passive: it only blocks if a
wait-online implementation (e.g. `systemd-networkd-wait-online.service`) is
enabled. The correct idiom for a genuinely network-dependent service is
`Wants=network-online.target` plus `After=network-online.target` plus the
wait-online unit enabled on the host; using `After=network.target` for that
purpose produces the classic race where the service starts before DHCP
completes. Conversely, demanding network-online for services that do not
need it slows every boot by the wait timeout.

### Q: A service `Wants=database.service After=database.service`. The database crashes. What happens? How do the answers differ with `Requires=` and `BindsTo=`?

With `Wants=`: nothing — the app keeps running and must handle its own
reconnection; `Wants=` propagates neither start failure nor later
deactivation. With `Requires=`: the app is *stopped* when the database is
deactivated (including crash), but nothing restarts either side — recovery
is the database's own `Restart=` policy. With `BindsTo=`: same stop-on-any-
deactivation behavior, which is the point for device- or mount-bound
services; if you additionally want the manager to keep the dependency alive
while you are up, `Upholds=` (v248+) restarts it automatically. The nuanced
answer distinguishes *start failure* (Requires prevents your start),
*explicit stop* (Requires stops you), and *later crash* (Requires/BindsTo
deactivate you; nothing restarts you).

### Q: You see `Breaking ordering cycle by deleting job foo.service/start` in the journal. What does it mean and how do you fix it?

The transaction engine found a cycle in the `After=`/`Before=` graph — the
job set cannot be totally ordered — so it salvaged the transaction by
deleting one job, which means `foo.service` (the named victim) will not
start this boot. Cycles almost always come from accumulated configuration:
a drop-in adding `Before=` to a unit that already orders back, or two
custom units ordering against each other. Triage: `systemctl cat` the
involved units to see the *merged* edges (drop-ins included), remove the
offending or redundant edge, run `systemd-analyze verify` for an offline
check, then `daemon-reload`. It is a configuration bug, never a runtime
fluke — it will repeat every boot until an edge is removed.

### Q: Why does `systemctl stop postgresql` leave myapp running, and what edge would change that?

Because stop propagation only travels along explicit lifecycle edges, and
`Wants=`/`After=` carry none — they are start-time grouping and sequencing
only. Stopping the dependency activates dependents only under `Requires=`
(explicit stop) or `BindsTo=` (any deactivation); `PartOf=` and
`PropagatesStopTo=` give one-directional stop/restart following for target-
bound service groups. The design rationale: cascading stops through a
sparse graph would make every maintenance stop a potential outage, so
systemd requires you to opt into each propagation direction explicitly.
`list-dependencies --reverse` is how you audit who would be affected before
stopping anything.

### Q: What do DefaultDependencies give a service and a target, and when would you disable them?

A service gains `Requires=`/`After=sysinit.target`, `After=basic.target`
(start after early boot) and `Conflicts=shutdown.target` +
`Before=shutdown.target` (stopped in order at shutdown). A target gains the
sysinit pairing, the shutdown pairing, and the complement rule that turns
every `Wants=`/`Requires=` into a matching `After=` edge. You opt out with
`DefaultDependencies=no` only for units outside the normal boot/shutdown
window — units that run during sysinit itself, final-shutdown units, and
hermetic custom targets — and then you must re-declare the edges by hand,
most critically the shutdown pairing: forgetting it means the unit is
killed by the final SIGKILL sweep with no `ExecStop`, a classic
"shuts down dirty" bug.

## References

- [systemd.unit(5) — the [Unit] section: every requirement and ordering directive](https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html)
- [systemd.service(5) — service lifecycle the edges act on (Restart, ExecStop)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html)
- [systemd.target(5) — target default dependencies and the complement rule](https://www.freedesktop.org/software/systemd/man/latest/systemd.target.html)
- [systemd.directives(7) — alphabetical index of every directive to its man page](https://www.freedesktop.org/software/systemd/man/latest/systemd.directives.html)
- [systemd.unit(5) — Debian bookworm mirror](https://manpages.debian.org/bookworm/systemd/systemd.unit.5.en.html)

## Cross-References

- [Unit files](./unit-files.md) — where dependency edges live on disk: fragments, drop-ins, .wants symlink directories.
- [Service units](./service-units.md) — the [Service] lifecycle (Restart, ExecStop, timeouts) that requirements propagate through.
- [Targets and the runlevel compatibility layer](./targets-runlevels.md) — the sync points this graph hangs from, and the DefaultDependencies=no shutdown footgun.
- [systemd internals (admin)](../../admin/systemd-internals.md) — the transaction and job engine beneath the CLI view given here.
- [LSB init script headers](../sysvinit/lsb-headers.md) — the `# Required-Start:` dependency encoding systemd's directives replaced.
- [Init system comparison](../comparison.md) — dependency models of all five families side by side.
- [init-systems hub](../README.md) — section overview and reading order.
