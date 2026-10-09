# lsns — list namespaces and the processes inside them

## Overview

`lsns` scans `/proc/<pid>/ns/*` and lists every unique Linux namespace on the system with the number of processes inside it, the lowest-PID (founder) process, and the procfs handle for entering it. It is the auditing tool for container-era debugging: which mount/net/user/pid namespaces exist, how many processes share each, and how they relate through parent and owner (user-namespace) links.

It ships in the `util-linux` package at `/usr/bin/lsns` and behaves like the other util-linux reporters (`-o`, `-J`, `-r`, `-n`, `-Q` filter, tree output). It is often confused with `ps` (shows processes, not namespace groupings), with `nsenter` (which *enters* a namespace using the PATH lsns prints), and with `unshare` (which creates namespaces).

| Field | Value |
| --- | --- |
| Package | util-linux (Debian bookworm) |
| Man section | 8 |
| Path | /usr/bin/lsns |
| First appeared | util-linux mid-2010s (2.24/2.25 era) |
| Standards | None — Linux namespaces are Linux-specific |

## Synopsis

```
lsns [options] [namespace]
```

Common one-line forms:

```
lsns                          # all namespaces, one row per unique NS
lsns -t net                   # only network namespaces
lsns -t mnt -o NS,NPROCS,PID,COMMAND
lsns -p 1234                  # namespaces of a given process
lsns -T                       # tree by parent/owner/process relation
```

## How It Works

### Scanning and deduplication

Every process carries a link for each namespace type in `/proc/<pid>/ns/<type>`, e.g. `/proc/1234/ns/net`, resolving to `net:[4026531994]` — the bracketed number is the nsfs inode, which is what lsns shows as `NS`. Processes sharing a namespace hold links to the *same* inode, so lsns walks `/proc`, groups descriptors by (type, inode), and emits one row per unique namespace:

```
/proc/<pid>/ns/{mnt,net,ipc,user,pid,uts,cgroup,time}
        │ for every live process, for every type
        ▼
 group by (type, nsfs inode)  ──▶  unique namespaces
        │
        ▼
 NS        TYPE NPROCS  PID COMMAND   PATH
 4026531994 net    3   25995 /bin/bash /proc/25995/ns/net
```

Real default output on a container host shows the eight namespace *types* — `mnt`, `net`, `ipc`, `user`, `pid`, `uts`, `cgroup`, `time` — with one row per unique instance:

```
$ lsns
        NS TYPE   NPROCS   PID USER COMMAND
4026531834 time        4 25575 z    /bin/bash --noprofile --norc
4026531835 cgroup      4 25575 z    /bin/bash --noprofile --norc
4026531837 user        4 25575 z    /bin/bash --noprofile --norc
4026531994 net         4 25575 z    /bin/bash --noprofile --norc
```

`PID` is the lowest PID in the namespace (its founder process) and `COMMAND` that process's command line; `USER`/`UID` identify the owner through the owning user namespace.

### Columns beyond the defaults

`--output-all` adds `PPID`, `PATH` (the `/proc/<pid>/ns/<type>` handle usable by `nsenter`), `UID`, `NETNSID` (kernel-assigned network namespace id, often `unassigned`), and `PNS`/`ONS` — the parent and owner namespace inodes that link a namespace into the user-namespace hierarchy.

### Tree views and persistence

`-T, --tree[=<rel>]` renders relationships: `parent` (default) chains child namespaces through `PNS`, `owner` arranges rows under their owning user namespace, `process` groups by process. Namespaces normally vanish when their last process exits — but an nsfs file that is still open (e.g. a bind mount in `/run/netns`) keeps one alive without any process. `-P, --persistent` includes those process-less namespaces, which is how you spot leaked `ip netns` handles.

### The [namespace] operand

Passing a namespace (the NS number or a path like `/proc/1234/ns/net`) filters the listing to that specific namespace instance.

### The eight types, one line each

| Type | Isolates | Everyday example |
| --- | --- | --- |
| `mnt` | mount table | a container's own `/` |
| `pid` | process IDs | container PIDs start at 1 |
| `net` | interfaces, routes, sockets | a VPN daemon's private stack |
| `ipc` | SysV IPC, POSIX queues | DB shared-memory segments hidden from host |
| `uts` | hostname, domainname | container hostname independent of host |
| `user` | UID/GID mappings, capabilities | root-inside-container maps to unprivileged host UID |
| `cgroup` | cgroup root view | container sees its own cgroup root |
| `time` | boottime/monotonic clocks | faking uptime for testing (Linux 5.6+) |

Only `user` and `pid` are *hierarchical* (namespaces of these types nest in trees); the rest are flat. That distinction is exactly what the `-T owner` tree visualizes for user namespaces, and why a "parent" makes sense there.

### Direct kernel evidence for one process

lsns aggregates, but the underlying per-process truth is readable in one line per type — useful to double-check a row:

```
$ ls -l /proc/$$/ns/
lrwxrwxrwx ... net -> 'net:[4026531994]'
lrwxrwxrwx ... mnt -> 'mnt:[4026532250]'
```

The bracketed numbers are nsfs inodes — the same values lsns prints as `NS`. Two processes share a namespace iff these resolve to equal inodes, which is also why `NS` numbers are meaningless across reboots: they are filesystem inode numbers of the nsfs superblock, allocated fresh each boot.

## Options That Matter

| Option | Effect |
| --- | --- |
| `-t, --type <name>` | Filter by namespace type: mnt, net, ipc, user, pid, uts, cgroup, time |
| `-p, --task <pid>` | Show the namespaces of this process |
| `-T, --tree[=<rel>]` | Tree output: `parent`, `owner` or `process` relations |
| `-P, --persistent` | Include namespaces without any process (still referenced) |
| `-Q, --filter <expr>` | Display filter expression over columns |
| `-o, --output <list>` | Column selection |
| `--output-all` | All columns (adds PATH, PPID, UID, NETNSID, PNS, ONS) |
| `-J, --json` | JSON output |
| `-l, --list` | List-format output |
| `-r, --raw` | Raw unpadded output |
| `-n, --noheadings` | Omit header row |
| `-u, --notruncate` | Do not truncate wide columns |
| `-W, --nowrap` | Disable multi-line cell wrapping |

## Usage Patterns

```bash
# Inventory all namespaces on a container host
lsns
```

```bash
# List network namespaces with founder process and handle
lsns -t net -o NS,NPROCS,PID,PATH,COMMAND
```

```bash
# Which namespaces does PID 1234 live in?
lsns -p 1234 -o NS,TYPE,PATH
```

```bash
# Verify two shells share a mount namespace (same NS number)
lsns -p $$ -t mnt; lsns -p $OTHER_PID -t mnt
```

```bash
# Enter the net namespace lsns reported, using its PATH
nsenter --net=/proc/25995/ns/net ip addr
```

```bash
# Namespaces with more than one process, filtered
lsns -Q '(NPROCS > 1)' -o NS,TYPE,NPROCS,COMMAND
```

```bash
# Tree of user-namespace ownership
lsns -t user -T owner -o NS,TYPE,NPROCS,USER,COMMAND
```

```bash
# Find leaked persistent namespaces (bind-mounted but process-less)
lsns -P -o NS,TYPE,PATH,NPROCS
```

```bash
# JSON export for a container-audit script
lsns -J > /tmp/namespace-inventory.json
```

```bash
# Time namespaces exist since Linux 5.6 — confirm presence
lsns -t time
```

```bash
# Double-check one row against the kernel directly (same inode numbers)
ls -l /proc/$$/ns | head
```

```bash
# Do these two PIDs share a mount namespace? Compare NS values
lsns -p 4321 -t mnt -o NS; lsns -p 4322 -t mnt -o NS
```

```bash
# On a Docker host: find the netns founder PID for a container namespace
lsns -t net -o NS,NPROCS,PID,COMMAND
```

## Nuances and Gotchas

- **`NS` values are inode numbers, not stable IDs.** They change across reboots and image moves; never key configuration on them. For stability, match on `PATH` handles or re-resolve at runtime.
- **Unprivileged visibility limits.** lsns reads `/proc` — with `hidepid` mounts or restricted containers you see only processes you can inspect, so namespace inventories may be partial. Root sees the full scan.
- **A namespace exists only while referenced.** No process and no open nsfs handle means the namespace is gone. If you expected a container's netns to linger after its init died, that is the rule, not a bug; `-P` shows the lingering cases.
- **Namespaces are per-type.** A container typically owns a *set* of namespaces (mnt, pid, net, ...). `lsns -p <pid>` shows the whole set; single-type listings hide the rest.
- **PID column can be misleading across PID namespaces.** The founder PID is a host-/proc-view PID; inside a different PID namespace it may not exist. Care in scripts that forward PIDs to other tools.
- **Filter expressions are column-based.** `-Q` evaluates against output columns (e.g. `(NPROCS > 1)`); syntax errors fail the run rather than silently passing everything through.
- **User namespace ownership explains "weird" UIDs.** Rows in a user-namespace-mapped container show the *owner* user; combine `-t user -T owner` to understand which userns maps which UIDs.
- **`lsns` is a snapshot, not a subscription.** Between your invocation and your next action, a namespace can vanish (last process died). Scripts that act on a row must tolerate the namespace being gone by the time they use its PATH.
- **Type filters are exact words.** `-t` accepts exactly the eight type names; a typo is an immediate usage error — which is good, because a silent no-op here would look like "no namespaces" in a report.
- **Time and cgroup namespaces date differently.** `time` needs Linux 5.6+, `cgroup` namespaces 4.6+; older kernels (or minimal embedded ones) show fewer types. An inventory that expects all eight must tolerate their absence rather than treating "missing type" as an error.

## Exit Status

- `0` — success.
- `1` — failure: `/proc` inaccessible, invalid option/filter/column, or unknown namespace operand.

## Related Commands

- [`util-linux collection hub`](./overview.md) — all pages in this collection.
- [`process management`](../../admin/process-management.md) — the /proc model lsns walks.
- [`lslocks`](./lslocks.md) — sibling procfs-scanning reporter with the same output conventions.
- [`internals`](../../internals.md) — what namespaces isolate and how nsfs inodes work.

## Interview Questions

### Q: How would you check whether two processes share a network namespace?

Compare their `/proc/<pid>/ns/net` handles — same `NS` inode means shared. With lsns: run it filtered to `-t net` and see whether both PIDs appear under one row, or compare `lsns -p PID1 -t net` and `lsns -p PID2 -t net` NS numbers. The kernel answer is identical to `readlink /proc/PID/ns/net`.

### Q: What does the NPROCS column actually count, and when can it mislead?

It counts live processes visible in `/proc` that hold that namespace's inode. It can mislead under `hidepid` (invisible processes are not counted), across PID namespaces (the founder PID may be unresolvable elsewhere), and for persistent namespaces created via bind mounts (NPROCS 0 is legitimate).

### Q: Explain the difference between PNS and ONS columns.

`PNS` is the parent namespace — the one in effect when this namespace was created (hierarchic types like pid/user/net nest through it). `ONS` is the owner user namespace, which holds the capability and UID-mapping authority. Tree mode `-T owner` arranges namespaces under their owning user namespace, which is the structure you reason about when auditing container privilege boundaries.

### Q: A debugging session needs to enter the mount namespace of PID 1234. How do lsns and nsenter cooperate?

`lsns -p 1234 -t mnt -o PATH` prints the namespace handle (`/proc/1234/ns/mnt`); `nsenter --mount=<path>` (or `-t 1234`) enters it. The PATH column is designed as a drop-in argument for nsenter — that pairing is the standard "inspect then enter" workflow.

### Q: Why can lsns show a network namespace with zero processes, and why does that matter?

Because something still holds a reference to the nsfs file — classically a bind mount under `/run/netns` created by `ip netns add`, or an open fd in another process. `-P` includes these persistent namespaces. They matter because such "empty" namespaces still own network state (interfaces, routes) and leak resources until the reference is released.

### Q: Which namespace types are hierarchical, and why does lsns care?

`user` and `pid` nest hierarchically — a new user namespace is created as a child of an existing one, and PID namespaces chain parent→child. That is why the tree mode makes sense for them (`-T owner` for user namespaces, parent chains via PNS for pid), while net/mnt/ipc/uts are flat instances with no parent relation. Knowing which types nest is what makes the PNS/ONS columns interpretable rather than decorative.

### Q: How do you use lsns output with nsenter to debug a running container from the host?

Find the container's namespace row (`lsns -t net` and match by NPROCS/COMMAND, or start from a PID with `lsns -p <pid>`), take the PATH handle (e.g. `/proc/1234/ns/net`), and pass it to `nsenter --net=<path>` (or `nsenter -t <pid>` for the whole set). The container's own tools then run in its namespace: `ip addr`, `ss -tlnp`, `cat /etc/resolv.conf`. lsns provides the discovery layer; nsenter executes the entry — the standard host-side container debug loop.

### Q: Why is the NS column not suitable as a persistent identifier in configs?

It is the inode number of the namespace's nsfs file, allocated fresh at every boot and different per machine. Two reboots of the same container get different NS values. Persistent references should use stable names (`ip netns` names, container IDs) and resolve to handles at runtime — with lsns used for discovery, not identity.

## References

- [Man page(8) — manpages.debian.org](https://manpages.debian.org/bookworm/util-linux/lsns.8.en.html)
- [Source — GitHub](https://github.com/util-linux/util-linux)
- [Source — Debian sources](https://sources.debian.org/src/util-linux/)
