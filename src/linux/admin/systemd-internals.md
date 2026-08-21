# systemd Internals — Units, the Dependency Graph, and Activation

systemd is more than a "faster init" — it is a generic transactional unit manager built around three primitives: **units** (declarative descriptions of resources), **dependencies** (a directed graph between units), and **activation** (the mechanism that brings a unit into being when needed). This page peels back the surface-level `systemctl` usage and looks at how the engine actually works: the parser, the dependency resolver, the transaction engine, and the activation primitives (socket, timer, path, device, and bus activation).

The reference implementation lives in `systemd`'s `src/core/` directory, in particular `unit.c`, `transaction.c`, `service.c`, `socket.c`, and `timer.c`. The man pages `systemd.unit(5)`, `systemd.service(5)`, `systemd.socket(5)`, and `systemd.timer(5)` are the canonical external documentation.

## 1. The unit abstraction

Every resource systemd manages is a **unit**. A unit has:

- a unique **name** (`postgresql.service`, `port-80.socket`, `daily-backup.timer`)
- a **type** (the suffix after the last `.`)
- a **load state** (`stub`, `loaded`, `not-found`, `bad-setting`, `masked`)
- an **active state** (`active`, `inactive`, `failed`, `activating`, `deactivating`, `reloading`)
- a **sub state** (e.g. `running` for services, `listening` for sockets, `waiting` for timers)
- a set of **dependencies** to other units
- a queue of pending **jobs**

Internally the unit graph lives in the `Manager` object's hash tables: `units_by_name`, `units_by_type`, and the per-type `name` tables. The `Unit` struct in `src/core/unit.c` is a base struct that per-type structs (`Service`, `Socket`, `Timer`, `Mount`, …) embed via C-style inheritance: each begins with `Unit meta;` so that pointers can be safely cast between the base and the derived type. This is the same trick the kernel uses for `struct device` vs `struct pci_dev`.

## 2. Unit types

| Type | Suffix | Manages | Defined in |
|------|--------|---------|-----------|
| Service | `.service` | Long-running daemons and one-shot commands | `service.c` |
| Socket | `.socket` | IPC, INET, file-system, FIFO, netlink sockets | `socket.c` |
| Timer | `.timer` | Calendar/monotonic timers, cron replacement | `timer.c` |
| Mount | `.mount` | Filesystem mount points (`/proc`, `/sys`, `/home`) | `mount.c` |
| Automount | `.automount` | Auto-mount-on-access mount points | `automount.c` |
| Swap | `.swap` | Swap files and swap partitions | `swap.c` |
| Target | `.target` | Sync points; grouping of units | `target.c` |
| Device | `.device` | Devices exposed by udev (`/dev` + sysfs) | `device.c` |
| Path | `.path` | Path-based activation (existence / modification) | `path.c` |
| Slice | `.slice` | Cgroup hierarchy node | `slice.c` |
| Scope | `.scope` | Externally-started process groups (e.g. user sessions) | `scope.c` |

Slices (`-.slice` = root, `system.slice`, `user.slice`, `machine.slice`) are the **structural** nodes of the cgroup tree; services and scopes are **leaf** units that contain processes. This dual structure — a declarative slice hierarchy plus leaf process containers — is what gives systemd its unified resource-control surface.

## 3. Unit file sections

A unit file is an INI-like file. systemd extends the format with `ConditionXxx=`, `AssertXxx=`, drop-in directories (`foo.service.d/*.conf`), and linter checks during `daemon-reload`.

```ini
# /etc/systemd/system/example.service
[Unit]
Description=Example daemon
Documentation=man:example(8) https://example.com/docs
Requires=network-online.target
After=network-online.target
Wants=postgresql.service
Conflicts=iptables.service
ConditionPathExists=/etc/example.conf

[Service]
Type=notify
User=example
Group=example
ExecStart=/usr/sbin/exampled --config /etc/example.conf
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=2
# Resource control (cgroup v2 delegation)
MemoryMax=2G
CPUQuota=200%
IOWeight=500
# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/example

[Install]
WantedBy=multi-user.target
```

- `[Unit]` — generic metadata and dependency declarations, common to all unit types.
- `[Service]` (or `[Socket]`, `[Timer]`, …) — type-specific configuration.
- `[Install]` — what `systemctl enable` should wire up. This section is *not* read at runtime; it is only consumed by `systemctl enable`/`preset`/`disable`.

## 4. The dependency graph

systemd distinguishes **strong** (`Requires=`, `Requisite=`, `BindsTo=`, `PartOf=`) from **weak** (`Wants=`) dependencies, plus **ordering** (`After=`, `Before=`) which is orthogonal to requirement. The combined effect is a directed graph with two kinds of edges.

```
                    Requires=           After=
      ┌─────────────────────┐  ┌─────────────────────┐
      │  strong requirement  │  │  ordering constraint  │
      │  (start target too)  │  │  (if both started,    │
      │                       │  │   do A before B)      │
      └──────────┬───────────┘  └──────────┬───────────┘
                 │                          │
                 ▼                          ▼
      A.service ──────────────────────► B.service
   ("unit A")                  ("unit B")
```

| Directive | Strength | Pulls in target? | Effect when target fails |
|-----------|----------|------------------|---------------------------|
| `Requires=` | strong | yes | start of A also fails |
| `Requisite=` | strong | no (checks current state only) | start of A fails immediately if B not already active |
| `Wants=` | weak | yes (best-effort) | A continues to start |
| `BindsTo=` | very strong | yes | if B goes down, A is also stopped |
| `PartOf=` | stop-propagation | no | stopping B stops A; starting unaffected |
| `Conflicts=` | negative | yes, in reverse | A and B cannot coexist |
| `After=`/`Before=` | ordering only | no | determines transaction job order |
| `Upholds=` | re-activate | yes | if target becomes inactive, restart it |

`Conflicts=` produces a **negative edge** in the graph. This is the only bidirectional-by-construction dependency; `Wants=` and `Requires=` are unilateral — the target unit is unaware unless it lists the inverse.

### A worked example: ordering without requirement

```ini
# A.service
[Unit]
After=B.service

[Service]
ExecStart=/bin/sleep 100
```

`After=` here means: "if both A and B are being started in the same transaction, start B first." It says **nothing** about whether B is started at all. So `systemctl start A` when B is inactive will start only A. This is a frequent source of confusion: `After=` does not imply `Requires=`.

### Why ordering is separate from requirement

Decoupling them lets you express "I want C up if it is up, but I don't care about starting it" (`Wants=` + `After=`) versus "I absolutely need C up" (`Requires=` + `After=`) versus "I need C up and I will be killed if it dies" (`BindsTo=`). systemd's own unit graph (the `basic.target`, `sysinit.target`, `multi-user.target` chain) is mostly `Wants=`+`After=` so that disabling one unit doesn't ripple uncontrollably.

## 5. The transaction engine

`systemctl start foo.service` does not just call `fork`. It builds a **transaction** — a set of **jobs**, one per unit affected, each in mode `start`/`stop`/`restart`/`reload`/`verify`. The transaction then goes through three phases:

```
   systemctl start web.service
              │
              ▼
   ┌──────────────────────────┐
   │  transaction_new()      │   collects anchor jobs
   │  ├─ web.service (start) │
   │  ├─ net.service (start) │   via After= requires
   │  └─ sock.socket (start) │   via Requires=
   └────────────┬────────────┘
                ▼
   ┌──────────────────────────┐
   │  cycle detection        │   uses Tarjan SCC
   │  conflict resolution    │
   └────────────┬────────────┘
                ▼
   ┌──────────────────────────┐
   │  topological sort        │   respects After=/Before=
   └────────────┬────────────┘
                ▼
   ┌──────────────────────────┐
   │  job_run()               │   each Job: unit_state_xxx()
   └──────────────────────────┘
```

1. **Generation** — the manager walks the dependency graph (DFS over `Requires`/`Wants`/`Conflicts`/`Requisite`/`BindsTo`) and computes the *anchor job set*. Each new unit gets a `Job` of the appropriate type.
2. **Verification** — `transaction_add_job_and_dependencies` in `transaction.c` checks for **cycles** and **conflicts**. If a cycle is found, systemd attempts to **break** it by dropping one of the `Wants=` edges (never `Requires=`). This is the famous `Job for foo.service failed... breaking start-up cycle` message.
3. **Application** — jobs are sorted topologically by `After=`/`Before=` and dispatched. Each job runs through the unit's **state machine** (see `service.c`'s `state_table[]`) until it reaches the target state.

Jobs are **idempotent**: if `web.service` is already `active` and another `systemctl start` arrives, no new job is queued. They are also **replaceable**: `JobMode=replace` (default) replaces conflicting queued jobs; `--fail` (`JobMode=fail`) refuses to queue if a job for the unit already exists; `--ignore-dependencies` runs the job without walking the graph. Use `systemctl list-jobs` to see what is currently queued.

## 6. Socket activation

Socket activation is systemd's most distinctive feature. A `.socket` unit creates and binds a socket **at boot** but does **not** start the associated service. The first connection to the socket triggers the service; systemd passes the pre-bound socket FDs to the service via `sd_listen_fds(3)` so the service can `accept()` without ever doing a `bind()` itself. This gives you:

- **Zero startup latency** on first request (no "warmup" race).
- **No lost connections** between socket creation and service start.
- **Stateless services**: a crashing service can be restarted with the same FDs.

```ini
# /etc/systemd/system/example.socket
[Socket]
ListenStream=80
ListenStream=443
# You can also bind unix sockets:
# ListenStream=/run/example.sock
# Or datagram:
# ListenDatagram=/run/example-dgram.sock
# Or sequential (FIFO):
# ListenFIFO=/run/example.fifo
# Or special:
# ListenSpecial=/dev/example
# Or netlink:
# ListenNetlink=kobject-uevent
# Or POSIX message queue:
# ListenMessageQueue=/example

SocketUser=www-data
SocketMode=0660
Accept=no
# Accept=yes would spawn a service instance per connection (like inetd)
Service=example.service

[Install]
WantedBy=sockets.target
```

The matching service:

```ini
# /etc/systemd/system/example.service
[Unit]
Requires=example.socket
After=example.socket

[Service]
Type=notify
ExecStart=/usr/sbin/exampled
# Receives socket FDs as fd 3, fd 4 via sd_listen_fds(3)
FileDescriptorName=web:80 web:443
Sockets=example.socket
```

When `Accept=no` (default for long-running daemons), the service is expected to call `accept()` itself; systemd passes the **listening** FD. When `Accept=yes`, systemd accepts the connection itself and runs a new instance of the service with the **accepted** connection FD as fd 3 (this is "inetd-style" activation). The `Sockets=` directive links the service to all sockets that should be passed to it during restart — so a service restart does not drop the listening socket.

The `LISTEN_FDS` / `LISTEN_PID` environment variables implement this protocol; see `sd_listen_fds(3)` and the [socket activation porting guide](https://systemd.io/PORTING_TO_RECEIVING_SD_LISTEN_FDS/).

## 7. Timer activation

A `.timer` unit schedules a `.service` of the same root name. There are two clock families: **monotonic** (`OnBootSec=`, `OnStartupSec=`, `OnUnitActiveSec=`, `OnUnitInactiveSec=`) and **realtime/calendar** (`OnCalendar=`).

```ini
# /etc/systemd/system/example-backup.timer
[Unit]
Description=Run example-backup.service every night

[Timer]
OnCalendar=*-*-* 02:00:00          # 02:00 every day
Persistent=true                     # catch up if missed while powered off
AccuracySec=1min                    # coalesce wakeups within 1 minute

# Alternative: every 5 minutes after service was last activated:
# OnUnitActiveSec=5min

# Alternative: 30 seconds after boot:
# OnBootSec=30s

Unit=example-backup.service

[Install]
WantedBy=timers.target
```

`OnCalendar=` uses a systemd-specific grammar (similar to cron but richer; see `systemd.time(7)`). Examples:

```
OnCalendar=*:0/15                  # every 15 minutes
OnCalendar=Mon..Fri 09:00          # 9am on weekdays
OnCalendar=*-*-01 03:00:00         # 1st of every month, 3am
OnCalendar=Sun *-*-* 04:00:00      # every Sunday at 4am
OnCalendar=monthly                 # built-in macros: hourly, daily, weekly, monthly, yearly
```

`Persistent=true` causes systemd to "catch up" missed runs by recording the last trigger time in `/var/lib/systemd/timers/stamp-example-backup.timer` — this is what differentiates systemd timers from cron for laptops that may be powered off at the scheduled time.

`AccuracySec=` lets timers in the system coalesce: instead of waking every second, all timers within a 1-minute (default) window fire together.

To inspect timers:

```bash
$ systemctl list-timers --all
NEXT                        LEFT       LAST                       PASSED  UNIT               ACTIVATES
Mon 2024-06-10 02:00:00 UTC 5h 12min   Sun 2024-06-09 02:00:00 UTC 18h ago example-backup.timer example-backup.service
```

## 8. Path and device activation

**Path** activation watches a path in the filesystem and triggers a service when the watched condition fires. Watch conditions are backed by inotify (`PathExists=`, `PathExistsGlob=`, `PathChanged=`, `PathModified=`).

```ini
# /etc/systemd/system/print-spool.path
[Path]
PathChanged=/var/spool/lp

[Install]
WantedBy=paths.target
```

**Device** units are created dynamically by `systemd-udevd` and reflect `udev` events. They typically appear in `WantedBy=` of udev rules:

```
# /usr/lib/udev/rules.d/99-foo.rules
SUBSYSTEM=="block", KERNEL=="sda1", ACTION=="add", \
  ENV{SYSTEMD_WANTS}="mount-sda1.service"
```

## 9. Journal integration

systemd does not call `syslog(3)`. By default, services inherit a **log stream socket** from `systemd`; stdout/stderr is captured by `systemd-journald` and stored in the structured journal (`/var/log/journal/` for persistent or `/run/log/journal/` for volatile). The journal is **binary**, **indexed** (by `_PID`, `_UID`, `_SYSTEMD_UNIT`, `MESSAGE_ID`, …), and supports **structured fields** via the [native protocol](https://systemd.io/JOURNAL_NATIVE_PROTOCOL/):

```bash
$ printf '<27>example: hello\nSYSLOG_IDENTIFIER=exampled\nCUSTOM_FIELD=42\n' \
  | systemd-cat -t exampled
```

Each field is a `KEY=VALUE\n` line; the priority is taken from the `syslog`-style prefix `<27>` (facility 3 + severity 3 = err).

Querying the structured journal:

```bash
$ journalctl _SYSTEMD_UNIT=example.service --since "1 hour ago"
$ journalctl MESSAGE_ID=7d4958e842f74c0f9d04f8e5b6f8a9e3   # boot message id
$ journalctl -o json-pretty | head
```

The journal exposes **namespaces** via `journalctl --namespace=foo`, allowing containerised services to write to their own journal files. This is used by `systemd-nspawn` containers and by service units with `LogNamespace=foo`.

## 10. Cgroup delegation

systemd is the **single writer** of the cgroup v2 hierarchy under `/sys/fs/cgroup/`. Each unit gets a cgroup at `/sys/fs/cgroup/<slice>/<subslice>/<unit-name>.unit/`. Resource controls (`MemoryMax=`, `CPUQuota=`, `IOWeight=`, `TasksMax=`) translate to writes to the corresponding cgroup v2 control files.

For nested management — a service that wants to manage its own children's resources — systemd supports **delegation**:

```ini
# /etc/systemd/system/kubelet.service
[Service]
Delegate=yes
ExecStart=/usr/bin/kubelet
```

With `Delegate=yes`, systemd permits the unit to create sub-cgroups inside its own cgroup and writes the `cgroup.subtree_control` file to enable controllers for the unit's subtree. This is what allows Kubernetes' `kubelet`, `containerd`, `podman`, and `systemd-nspawn` to nest under systemd without conflicting writes.

Without delegation, systemd would consider any cgroup writes by the unit as "outside state" and could wipe them on the next `daemon-reload`.

## 11. Putting it together: a boot transaction

When you boot a Linux system, systemd (as PID 1) does roughly:

1. `manager_new()` — initialise the `Manager` object, parse kernel cmdline (`/proc/cmdline`), pick up `systemd.unit=` overrides.
2. `manager_coldplug()` — restore state from `/run/systemd/transient/*`, re-attach to sockets and service processes left over from initramfs.
3. Activate `default.target` (usually a symlink to `graphical.target` → `multi-user.target`).
4. The target pulls in its `Wants=` and `Requires=` set, recursively; this is the **root transaction**.
5. Topologically sort; dispatch jobs; for each `.service` job: `service_start()` walks the state machine (`dead → start-pre → start → start-post → running`).
6. `sockets.target`, `timers.target`, `paths.target`, `local-fs.target` all converge on `basic.target` → `sysinit.target` → `default.target`.

`systemctl list-jobs` shows the current job queue; on a healthy boot this is empty by the time you log in.

## References

- systemd documentation index, https://systemd.io/
- man systemd.unit(5), https://www.freedesktop.org/software/systemd/man/systemd.unit.html
- man systemd.service(5), https://www.freedesktop.org/software/systemd/man/systemd.service.html
- man systemd.socket(5), https://www.freedesktop.org/software/systemd/man/systemd.socket.html
- man systemd.timer(5), https://www.freedesktop.org/software/systemd/man/systemd.timer.html
- "Socket Activation" by Lennart Poettering, https://systemd.io/SOCKET_ACTIVATION/
- "Receiving socket activation FDs" porting guide, https://systemd.io/PORTING_TO_RECEIVING_SD_LISTEN_FDS/
- LWN: "Systemd and parallel booting" — Jonathan Corbet, https://lwn.net/Articles/567997/
- LWN: "A closer look at systemd" — Sean Robinson, https://lwn.net/Articles/567732/
- sd_listen_fds(3) and the journal native protocol, https://systemd.io/JOURNAL_NATIVE_PROTOCOL/
- Lennart Poettering, "systemd for Administrators, Part IX" (cgroup delegation), https://0pointer.de/blog/projects/resources.html
