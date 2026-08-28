# Watching the Filesystem: dnotify, inotify, fanotify and the fsnotify Backend

A surprising fraction of distributed-systems failures start as "the local file changed and nobody noticed." Linux has shipped three different notification mechanisms — dnotify, inotify, fanotify — and a shared kernel backend (`fsnotify`) that all of them now hang off. This page explains what each generation actually does at the kernel level, why each one replaced its predecessor, and how to reason about the failure modes that show up in file-sync engines, antivirus/EDR, and audit tooling. For the *consumption* side — putting an event source into a poll loop — see [epoll](../../sysprog/epoll.md); for a real design that leans on these events, see the [Dropbox case study](../../../interview/system-design/real-world/dropbox.md).

## Generation zero: dnotify, and why it lost

dnotify (Linux 2.4) is not a syscall of its own: you `fcntl(fd, F_NOTIFY, DN_CREATE | DN_DELETE | ...)`, and the kernel delivers the news by *signal* — `SIGIO` with a `si_fd` ([fcntl(2)](https://man7.org/linux/man-pages/man2/fcntl.2.html)). Three properties made it unusable at scale:

1. **It pins directories.** A watch is keyed to an open directory fd, so a daemon watching 50,000 directories holds 50,000 open fds — and those directories can no longer be unmounted, because they are in use.
2. **Delivery is asynchronous signal.** Every event funnels through one signal handler; there is no queue, no coalescing policy, no ordering guarantee, and the [async-signal-safety problem](../../sysprog/signals.md) applies to every observation.
3. **Directories only, no per-file events, no recursion.** Watching a tree means walking it and fcntl-ing every directory yourself.

The signal-delivery design was the original sin: it duplicated the delivery machinery the signal page covers (frame builds, restart codes) and gained nothing from it.

## Generation one: inotify (2.6.13) — events as an fd

inotify inverts the model: `inotify_init1()` returns an fd; `inotify_add_watch(fd, path, mask)` registers interest in an inode (in practice, a directory); events come back as fixed-size `struct inotify_event` records from `read(2)`. Because the event stream is an fd, readiness integrates with `poll`/`epoll` — [event loops](../../sysprog/epoll.md) treat it like any other socket — and because delivery is a read, there is no signal handler in the path.

The events worth memorizing for debugging: `IN_CREATE`/`IN_DELETE`/`IN_MOVED_FROM`/`IN_MOVED_TO` (the last two carry a shared `cookie` so a daemon can pair a rename), `IN_MODIFY`/`IN_CLOSE_WRITE` (write-then-close is the only sane "content complete" signal for sync engines), `IN_UNMOUNT` and `IN_IGNORED` (watch torn down), and `IN_Q_OVERFLOW`.

The limits are exposed as sysctls, documented in [inotify(7)](https://man7.org/linux/man-pages/man7/inotify.7.html):

| Knob | Unit | What it bounds |
|---|---|---|
| `/proc/sys/fs/inotify/max_user_instances` | inotify fds per real user | runaway daemons |
| `/proc/sys/fs/inotify/max_user_watches` | watches per real user | recursive tree monitoring |
| `/proc/sys/fs/inotify/max_queued_events` | events queued per instance | event burst absorption |

The two structural problems inotify never solved: **no permission events** — it can only observe after the fact, never veto — and **no whole-tree or whole-mount scope** — you buy watches one directory at a time, with the accounting consequences in section 5.

## Generation two: fanotify (2.6.37) — blocking decisions and whole-mount scopes

fanotify is a different bargain. Groups are created with `fanotify_init()` and require privilege (`CAP_SYS_ADMIN` in the initial user namespace, or the marked filesystem's namespace for some setups) — by design, since the API can intercept other users' I/O. Marks attach with `fanotify_mark()` at three scopes: an inode, an entire **mount** (`FAN_MARK_MOUNT`), or an entire **filesystem** (`FAN_MARK_FILESYSTEM`) — one mark replaces thousands of inotify watches. [fanotify(7)](https://man7.org/linux/man-pages/man7/fanotify.7.html) documents the event set; the additions that matter:

- **Permission events** (`FAN_OPEN_PERM`, `FAN_ACCESS_PERM`, and `FAN_OPEN_EXEC_PERM` for exec) turn notification into *arbitration*: the kernel stops the triggering process until the daemon reads the event and writes back an allow/deny response. This is the mechanism under on-access scanning — and the danger in section 6.
- **`FAN_OPEN_EXEC`** reports a file opened with intent to execute, the hook EDR products need to see a binary before it runs.
- **`FAN_REPORT_FID`** makes events carry nameless file handles instead of path strings, which shrinks the [event-vs-path race](#failure-modes-that-bite-in-production) window: the handle stays valid when the path is renamed mid-report.
- **`FAN_FS_ERROR`** (with `FAN_REPORT_FID`) is a filesystem *health* channel: the kernel reports the first error since the last notification and merely counts the rest, so one corrupted-IO event is not buried under its 200 cascading siblings. [The kernel's filesystem-monitoring admin guide](https://docs.kernel.org/admin-guide/filesystem-monitoring.html) documents it (initially emitted by ext4).
- **`FAN_UNLIMITED_QUEUE`** (at init) removes the queue cap for daemons that must never lose an event.

The trade: no file names for mount/filesystem-scope marks unless `FAN_REPORT_FID` is used (events identify the watched mount, not each file), and fanotify still cannot tell you *what content* changed — it tells you *that* something happened, same as inotify.

## The fsnotify backend: one hook, three consumers

All three generations are now frontends over one backend. VFS operations that mutate state call `fsnotify_*()` hooks; the backend fans each event out to the groups that care:

```text
        VFS (fs/*.c)                    fsnotify backend (fs/notify/)
   open/write/rename/...          +------------------------------+
        |                         |  event mask & flags built    |
        v                         |  from the hook               |
  fsnotify_move(), ... ---------> |  connector marks consulted   |
                                  |    inode marks  <- inotify   |
   inotify group <- wd table <--  |    mount marks  <- fanotify  |
   fanotify group <- policy    <- |    fs marks     <- fanotify  |
        |                         |  no interested group =>      |
        v                         |    zero work (fast path)     |
   per-group queue -> read(2)     +------------------------------+
```

A **mark** is (group, object, mask): the object can be an inode, a vfsmount, or a superblock. Each inode carries a connector with the marks attached to it; an event fires only where the hook's implicit mask intersects a mark's mask, so an unwatched filesystem pays a couple of bit tests and nothing more. The three frontends are then just bookkeeping over marks:

- an **inotify watch** = an inode mark + a `wd` integer mapped into the group's table (so userspace events can reference the watch);
- a **fanotify mount mark** = a vfsmount mark with the group configured for permission or notification responses;
- **dnotify** survives as a legacy inode-mark client, still signal-based.

## How an inotify watch maps onto marks

`inotify_add_watch()` resolves the path to an inode, allocates an `inotify_inode_mark`, attaches it to the connector with the user's event mask, and records `wd -> mark` in the group's idr table. Removal is asymmetric: `IN_IGNORED` is generated when the kernel kills a watch — inode deleted, filesystem unmounted, or the watch explicitly removed — so a daemon must treat `IN_IGNORED` as "your wd is dead, re-register if still relevant," not as an event about a file. Because watches pin the watched inode in memory, the watch count is also a pinned-inode count; that is exactly why `max_user_watches` exists.

## Choosing a mechanism

| Capability | dnotify | inotify | fanotify |
|---|---|---|---|
| Delivery | `SIGIO` signal | `read(2)` on fd | `read(2)` on fd |
| Scope | per directory | per inode (dir) | inode / mount / whole filesystem |
| Recursive trees | manual | manual (1 watch/dir) | one mark |
| Blocking decisions (veto open/exec) | no | no | yes (permission events) |
| Event payload | signal number | event + file name | metadata (+ file handle w/ `FAN_REPORT_FID`) |
| Privilege needed | none | none | yes |
| Queue overflow semantics | none (no queue) | `IN_Q_OVERFLOW` (`wd == -1`) | queue cap; `FAN_UNLIMITED_QUEUE` opt-out |
| Who uses it | nobody (legacy) | sync engines, build tools, editors | AV/EDR, audit, fs-health monitors |

| Use case | Pick | Why |
|---|---|---|
| File-sync engine (watch a working tree) | inotify | unprivileged, per-file names, epoll-friendly; accept the re-scan cost of overflows |
| On-access malware scanning / EDR | fanotify permission events | needs to block opens/execs system-wide; privilege is inherent |
| Detect binary tampering, config reload | inotify on the specific dirs | cheap, no privilege, event names enough |
| Filesystem health monitoring | fanotify `FAN_FS_ERROR` | kernel-side first-error aggregation survives error storms |
| CI cache invalidation on a huge tree | fanotify mount mark | thousands of dirs but one mark and no watch budget to manage |

## Failure modes that bite in production

- **The add-watch race.** Between `mkdir(2)` and `inotify_add_watch()` on the new directory, events inside it go to nobody. Watch-then-create (register `IN_CREATE` on the parent, add the child watch before writing into it) shrinks but does not eliminate the window; sync engines keep a rescan fallback.
- **Overflow is invisible until you look.** `max_queued_events` is finite; a 10,000-file checkout drops nearly everything when the reader cannot keep up, and the only notice is one `IN_Q_OVERFLOW` with `wd == -1`. The correct recovery is a full re-scan and state re-derivation, not event replay — because the events are gone.
- **Event-vs-`stat` races.** An `IN_MODIFY` names a file; by the time you `open()`/`stat()` it, it may be renamed or gone. Either read the content in one open, or use `IN_MOVED_TO`/cookies for pairing, or switch to `FAN_REPORT_FID` handles.
- **Permission-event deadlock.** With fanotify permission events, a process performing I/O is stopped until your daemon answers. If the daemon dies, or deadlocks on the very filesystem it arbitrates (its own logs!), the machine wedges. Production daemons write responses from a dedicated thread with no filesystem dependencies and watchdog their response latency.
- **Recursive watch cost is quadratic in user surprise.** Deep trees multiply watches *and* pinned inodes *and* per-event fan-out work; a shared host where many users sync big trees hits `max_user_watches` per *user*, with errors that surface as mysterious `ENOSPC` from `inotify_add_watch`.

## Production tuning checklist

```bash
# inotify budgets (per real user)
cat /proc/sys/fs/inotify/max_user_instances   # default distro-dependent
cat /proc/sys/fs/inotify/max_user_watches     # raise for sync daemons on big trees
cat /proc/sys/fs/inotify/max_queued_events    # raise if bursts exceed reader drain rate
# size max_user_watches: one per directory watched; budget pinned-inode memory

# who is holding the budget (walk /proc/*/fd counting inotify fds)
for p in /proc/[0-9]*; do n=$(ls -l $p/fd 2>/dev/null | grep -c inotify); \
  [ "$n" -gt 0 ] && echo "$n $p"; done | sort -rn | head
```

The demo below is the sizing math a sync daemon should run before shipping: how many watches a recursive tree needs, what a burst looks like against `max_queued_events`, and the same tree under one fanotify mark.

```python
#!/usr/bin/env python3
"""inotify watch-accounting + event-queue overflow calculator.
Given a directory tree, count what a recursive inotify watch costs against
max_user_watches / max_queued_events, and compare with one fanotify mount
mark. Pure stdlib, deterministic."""

TREE = {          # path: (files, subdirs)  -- one fictional build checkout
    "/srv/build":            (3, ["src", "tests", "docs"]),
    "/srv/build/src":        (120, ["core", "net"]),
    "/srv/build/src/core":   (310, []),
    "/srv/build/src/net":    (96, []),
    "/srv/build/tests":      (58, ["fixtures"]),
    "/srv/build/tests/fixtures": (2200, []),
    "/srv/build/docs":       (14, []),
}

def account_recursive(root, max_user_watches, max_queued_events):
    watches = events_storm = overflow_events = 0
    for path, (files, _) in TREE.items():
        if path.startswith(root):
            watches += 1                    # one watch per directory
            events_storm += files * 2       # IN_CREATE + IN_CLOSE_WRITE per file
    lost = max(0, events_storm - max_queued_events)
    overflow_events = 1 if lost else 0      # kernel injects exactly one IN_Q_OVERFLOW
    fits = watches <= max_user_watches
    return watches, events_storm, lost, overflow_events, fits

def account_fanotify_mount_mark():
    return 1, None                          # one mark on the mount, no per-dir cost

print("recursive inotify accounting (1 watch per directory):")
for mw, mq in ((8192, 16), (8192, 16384)):
    w, ev, lost, ovf, fits = account_recursive("/srv/build", mw, mq)
    print(f"  max_user_watches={mw:5d} max_queued_events={mq:5d} -> "
          f"watches={w} fits={fits}  burst={ev} events, lost={lost}, "
          f"IN_Q_OVERFLOW={ovf}")

w, _ = account_fanotify_mount_mark()
print(f"fanotify FAN_MARK_FILESYSTEM equivalent: {w} mark, same events, "
      f"no IN_Q_OVERFLOW loss if reader keeps up (FAN_UNLIMITED_QUEUE)")

# verdicts a file-sync daemon must reason about
print("\nverdicts:")
print("  - 7 dirs -> 7 watches; each new subdir needs inotify_add_watch before")
print("    its first write lands, or those events go to nobody (classic race)")
print("  - max_queued_events=16 loses all but 16 of a 5,602-event checkout burst")
print("  - loss is invisible: inotify reports overflow only via IN_Q_OVERFLOW")
print("    (wd=-1); the daemon must then re-scan the tree and re-derive state")
```

Real output:

```text
recursive inotify accounting (1 watch per directory):
  max_user_watches= 8192 max_queued_events=   16 -> watches=7 fits=True  burst=5602 events, lost=5586, IN_Q_OVERFLOW=1
  max_user_watches= 8192 max_queued_events=16384 -> watches=7 fits=True  burst=5602 events, lost=0, IN_Q_OVERFLOW=0
fanotify FAN_MARK_FILESYSTEM equivalent: 1 mark, same events, no IN_Q_OVERFLOW loss if reader keeps up (FAN_UNLIMITED_QUEUE)

verdicts:
  - 7 dirs -> 7 watches; each new subdir needs inotify_add_watch before
    its first write lands, or those events go to nobody (classic race)
  - max_queued_events=16 loses all but 16 of a 5,602-event checkout burst
  - loss is invisible: inotify reports overflow only via IN_Q_OVERFLOW
    (wd=-1); the daemon must then re-scan the tree and re-derive state
```

The numbers compress the whole design argument: watch budget is a directory-count problem (fine here, fatal on monorepos), while the event queue is a *burst* problem that no watch count fixes — and fanotify converts the first problem entirely into one mark while leaving the second to the reader's drain rate.

## References

- [inotify(7) — events, limits, IN_Q_OVERFLOW semantics](https://man7.org/linux/man-pages/man7/inotify.7.html)
- [fanotify(7) — permission events, marks, FAN_REPORT_FID, FAN_OPEN_EXEC](https://man7.org/linux/man-pages/man7/fanotify.7.html)
- [fanotify_mark(2) — mark scopes: inode, mount, filesystem](https://man7.org/linux/man-pages/man2/fanotify_mark.2.html)
- [fcntl(2) — dnotify's F_NOTIFY interface](https://man7.org/linux/man-pages/man2/fcntl.2.html)
- [Kernel admin guide: File system Monitoring with fanotify — FAN_FS_ERROR](https://docs.kernel.org/admin-guide/filesystem-monitoring.html)

## Related Topics

- [VFS](vfs.md) — where the fsnotify hooks sit in file operations
- [dentry](dentry.md) — path resolution, renames, and why path strings in events race
- [epoll](../../sysprog/epoll.md) — consuming inotify/fanotify fds in event loops
- [Signals (API level)](../../sysprog/signals.md) — the async-signal problem dnotify bequeathed
- [audit](../../security/audit.md) — kernel audit as the other "who touched what" channel
- [Dropbox design case](../../../interview/system-design/real-world/dropbox.md) — a sync engine built on these events
- [overlayfs](overlayfs.md) — the filesystem containers actually mount, watched by the same marks
