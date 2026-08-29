# File Descriptor Passing: SCM_RIGHTS and the Kernel Mechanics

[Unix Domain Sockets](../../../networks/sockets/unix.md) covers AF_UNIX addressing, socket types, and the basic `sendmsg()`/`recvmsg()` SCM_RIGHTS recipe at the API level. This page stays one layer down, inside the kernel: what actually crosses the socket is not an integer but a reference to a `struct file`, and the interview-relevant mechanics are refcounts, in-flight accounting, garbage collection of dead endpoint cycles, and the ways the transfer fails.

## An fd is a slot; a struct file is what gets shared

A file descriptor is an index into the per-process fdtable (`files_struct.fdt`; see [Virtual File System](./vfs.md)). Passing an fd installs a new slot in the receiver's table pointing at the *same* `struct file` (open file description), so both processes share the file offset and status flags; only `f_count` grows. unix(7) states the duplicate "refers to the same open file description" as the original.

```text
f_count ledger for one passed struct file
-----------------------------------------
1  open("/data/db.log")       p1 fd7              (sender slot)
2  sendmsg(SCM_RIGHTS [7])    skb queued on peer  (+1 in-flight ref)
1  p1 close(7)                skb keeps the ref   (in-flight hold)
1  recvmsg() -> p2 fd3        skb ref -> fd slot  (no net change)
0  p2 close(3)                fput -> release()   (file freed)
```

## What sendmsg() does before your bytes move

1. `__scm_send()` parses the cmsg. For `SCM_RIGHTS` it copies up to `SCM_MAX_FD` `struct file *` pointers into a `struct scm_fp_list` -- fields `fp[SCM_MAX_FD]`, `count`, `inflight`, `dead`, `edges` -- calling `get_file()` per descriptor: one atomic `f_count` bump per passed fd.
2. `unix_attach_fds()` duplicates the list into the skb (`scm_fp_dup()`) and calls `unix_inflight()` per fd, bumping the per-user counter `user->unix_inflight` under `unix_gc_lock`. In-flight fds are now accounted even though no process fdtable references them.
3. The skb parks on the receive queue holding `f_count` references that belong to nobody: the descriptors are in flight. The sender usually closes its own fd immediately (nginx-style handoff); the file survives only because the skb holds it.

If the sender's user has too many fds in flight, the send fails. Through Linux 5.15 the check was `user->unix_inflight > task_rlimit(RLIMIT_NOFILE)` returning `-ETOOMANYREFS` unless the sender held `CAP_SYS_RESOURCE`/`CAP_SYS_ADMIN` (`too_many_unix_fds()` in net/unix/scm.c). Current kernels keep the counter and use it mostly to decide when to schedule the garbage collector.

## What recvmsg() does: allocation, truncation, and 253

`scm_detach_fds()` (net/core/scm.c) computes `fdmax = min(cmsg buffer room, fp->count)` and, per descriptor, grabs the lowest free fd in the receiver's table and installs the skb's file there. Three facts interviewers probe:

- **SCM_MAX_FD is 253.** Verified in include/net/scm.h (`#define SCM_MAX_FD 253`); unix(7) confirms "SCM_MAX_FD has the value 253 (or 255 before Linux 2.6.38)". Exceeding it fails `sendmsg()` with `EINVAL`.
- **Receive-side limits close fds silently.** Per unix(7), if received fds would exceed the receiver's `RLIMIT_NOFILE`, "the excess file descriptors are automatically closed in the receiving process". A partially received batch is reported with `MSG_CTRUNC`.
- **`MSG_CMSG_CLOEXEC` (Linux 2.6.23+) maps to `O_CLOEXEC` at install time** (`o_flags` in `scm_detach_fds`), closing the race where a passed fd survives an unrelated `execve()`. Newer kernels add `SO_PASSRIGHTS`/`SO_RIGHTS_NOTRUNC` (uapi socket.h 83/85) to change truncation semantics.

## In-flight fds and the unix_gc cycle problem

In-flight refs outlive their sender: a process can pass an fd, close it, and die while the skb still pins the file. Worse, sockets themselves are files -- pass each end of a socket pair to the other and both endpoints die:

```text
p5 exits (its fds were closed). What remains in kernel memory:

  sock:A file rc=1 holders=[skb3]   skb3 parked on A's queue -> holds fd of B
  sock:B file rc=1 holders=[skb2]   skb2 parked on B's queue -> holds fd of A

  gc edges:  A -> B (skb3)      B -> A (skb2)
  SCC {A,B}: every reference comes from inside the cycle -> reclaim both
```

No `fput()` will ever arrive through normal channels, and naive mark-and-sweep deadlocks on the cycle. The garbage.c fix history is a systems-design lesson in itself: Al Viro's 1998 notes flag it directly ("Graph may have cycles. That is, we can send the descriptor of foo to bar and vice versa"), plus a subtler bug where fds sent to a connected-but-not-yet-accepted (embryo) socket were wrongly purged. Miklos Szeredi reimplemented it with a cycle-collecting algorithm in 2007; today's version builds `unix_vertex`/`unix_edge` graphs and reclaims strongly connected components (Tarjan-style `scc_index`).

## fdtable growth and the resize race

Receiving fds allocates slots in the receiver's table, so the receiver's `RLIMIT_NOFILE` (see getrlimit(2); the classic soft default is 1024) matters at recv time. When the table must grow, fs/file.c runs `expand_fdtable()` under `resize_in_progress` with a `resize_wait` queue: concurrent `fd_install()` callers sleep until the resize completes, and readers see a consistent table. Hitting the hard limit yields `EMFILE`.

## pidfd_getfd(2): the pull-based alternative

`pidfd_getfd()` (Linux 5.6+) duplicates a descriptor from another process given a pidfd. The man page notes the effect "is similar to the use of SCM_RIGHTS" but the direction is inverted: it is a *pull*, requiring `PTRACE_MODE_ATTACH_REALCREDS` permission (the ptrace access check), and needs `syscall(2)` on older glibc (no wrapper at introduction).

| Attribute | SCM_RIGHTS (push) | pidfd_getfd(2) (pull) |
|-----------|-------------------|-----------------------|
| Cooperation | Receiver must call recvmsg() | Target need not cooperate |
| Permission | Socket connectivity only | ptrace-level check |
| Auditability | Message flow is queued data | Supervisor-initiated, debug-oriented |
| Typical user | Service handoff | Supervisors, debuggers, system managers |

## Where fd migration ships

| Deployment | Pattern | What crosses |
|------------|---------|--------------|
| systemd socket activation | push, pre-exec | fds start at fd 3 (`SD_LISTEN_FDS_START`), announced via `LISTEN_PID`/`LISTEN_FDS`/`LISTEN_FDNAMES`; socket survives service restarts and enables zero-downtime upgrades |
| Sandbox broker (browser renderers; legacy NaCl) | push, on demand | Locked-down renderer asks an unsandboxed broker, which performs the sensitive `open()` and returns an fd |
| Pre-forked workers / connection pools | push, on demand | Accepted-connection fds migrate to workers instead of being inherited at fork |
| Supervisors and debuggers | pull, pidfd_getfd | fd extracted from a target process for inspection or handoff |

## Hazards

| Hazard | Mechanism | Defense |
|--------|-----------|---------|
| fd leak | skb queue never drained; sender already closed its copy | Drain or shut down queues; audit with lsof(8) |
| Double-close | Two owners both assume they own the number | fd numbers are per-process slots; close only your own |
| exec leak | Passed fd lacks O_CLOEXEC and survives execve() | `MSG_CMSG_CLOEXEC`, or fcntl F_SETFD right after recvmsg |
| MSG_CTRUNC | Receiver's cmsg buffer too small; leftovers closed | Size `msg_control` for the worst case |
| Shared-offset surprise | Same open file description means one shared offset | Reopen or use O_APPEND when isolation is needed |

## Refcount lifecycle simulator

Pure-stdlib simulation of the ledger above: send/receive/close events against a table of `struct file` objects, with leak detection (`rc > 0` at exit), double-close detection, and a Tarjan-SCC garbage-collection pass for the dead-endpoint cycle.

```python
class Sim:
    def __init__(self):
        self.files = {}   # fid -> [kind, holders]; rc = len(holders)
        self.fdt = {}     # pid -> {fd: fid} process fd tables
        self.skbs = {}    # n -> [queue_sock_fid, [held fids]]
        self.trace, self.flags, self.collected = [], [], set()
        self.nfid = 0
    def log(self, s): self.trace.append(s)
    def rc(self, fid): return len(self.files[fid][1])
    def alloc_fd(self, pid):
        tab = self.fdt.setdefault(pid, {})
        fd = 0
        while fd in tab: fd += 1
        return fd
    def install(self, fid, pid, fd):
        self.fdt[pid][fd] = fid
        self.files[fid][1].append(("p", pid, fd))
    def open(self, pid, kind):
        fid = "f%d" % self.nfid
        self.nfid += 1
        self.files[fid] = [kind, []]
        self.install(fid, pid, self.alloc_fd(pid))
        self.log("open   %-4s %-13s rc=1" % (fid, kind))
        return fid
    def dup(self, pid, fd):
        fid = self.fdt[pid][fd]
        nfd = self.alloc_fd(pid)
        self.install(fid, pid, nfd)
        self.log("dup    %-4s p%d fd%d->fd%d rc=%d" % (fid, pid, fd, nfd, self.rc(fid)))
    def sendmsg(self, qsock, fds, n):
        for fid in fds: self.files[fid][1].append(("skb", n))
        self.skbs[n] = [qsock, list(fds)]
        self.log("send   skb%d q=%-4s fds=%-5s rc=%d (get_file x%d)"
                 % (n, qsock, ",".join(fds), self.rc(fds[0]), len(fds)))
    def recvmsg(self, pid, n, cloexec=False):
        qsock, fds = self.skbs.pop(n)
        got = []
        for fid in fds:
            self.files[fid][1].remove(("skb", n))
            nfd = self.alloc_fd(pid)
            self.install(fid, pid, nfd)
            got.append("%s->p%d:fd%d" % (fid, pid, nfd))
        self.log("recv   skb%d %s rc=%d%s" % (n, ",".join(got), self.rc(fds[0]),
                 " [+MSG_CMSG_CLOEXEC]" if cloexec else ""))
    def close(self, pid, fd):
        fid = self.fdt[pid].pop(fd, None)
        if fid is None or ("p", pid, fd) not in self.files[fid][1]:
            self.log("close  p%d fd%d DOUBLE-CLOSE: no holder, flag!" % (pid, fd))
            self.flags.append("double-close p%d fd%d" % (pid, fd))
            return
        self.files[fid][1].remove(("p", pid, fd))
        self.log("close  %-4s p%d fd%d rc=%d%s" % (fid, pid, fd, self.rc(fid),
                 " freed" if self.rc(fid) == 0 else ""))
    def die(self, pid):
        for fd in sorted(self.fdt.get(pid, {})):
            self.files[self.fdt[pid][fd]][1].remove(("p", pid, fd))
        self.fdt[pid] = {}
        self.log("die    p%d exits; skb holders survive in the kernel" % pid)
    def gc(self):  # Tarjan SCC over edges: queue socket -> held file
        nodes, edges = set(), {}
        for q, fds in self.skbs.values():
            nodes.update([q] + fds)
            edges.setdefault(q, []).extend(fds)
        low, num, stack, on, sccs, ctr = {}, {}, [], set(), [], [0]
        def strong(v):
            num[v] = low[v] = ctr[0]; ctr[0] += 1
            stack.append(v); on.add(v)
            for w in edges.get(v, []):
                if w not in num:
                    strong(w); low[v] = min(low[v], low[w])
                elif w in on:
                    low[v] = min(low[v], num[w])
            if low[v] == num[v]:
                grp = []
                while True:
                    w = stack.pop(); on.discard(w); grp.append(w)
                    if w == v: break
                if len(grp) > 1: sccs.append(sorted(grp))
        for v in sorted(nodes):
            if v not in num: strong(v)
        for grp in sccs:
            m = set(grp)
            rooted = any(h[0] == "p" or self.skbs[h[1]][0] not in m
                         for fid in grp for h in self.files[fid][1])
            if rooted:
                self.log("gc     scc %s still rooted, skip" % "+".join(grp))
            else:
                for fid in grp:
                    self.files[fid][1] = []
                    self.collected.add(fid)
                self.log("gc     collect cycle %s (dead endpoints)" % "+".join(grp))
    def report(self):
        print("\n== final struct file table ==")
        print("%-5s %-14s %3s  %s" % ("fid", "kind", "rc", "status"))
        for fid in sorted(self.files):
            kind, hs = self.files[fid]
            r = len(hs)
            if fid in self.collected: st = "freed (GC cycle)"
            elif r == 0: st = "freed"
            elif all(h[0] == "skb" for h in hs):
                st = "LEAK: in-flight skb on " + self.skbs[hs[0][1]][0]
            else:
                st = "alive: " + ",".join("p%d:fd%d" % (h[1], h[2]) for h in hs)
            print("%-5s %-14s %3d  %s" % (fid, kind, r, st))
        print()
        print("flags:", self.flags if self.flags else "none")

s = Sim()
print("== scenario 1: clean handoff p1 -> p2 ==")
s.open(1, "sock:P")            # f0: p1's end of the pair
q = s.open(2, "sock:Q")        # f1: skb will park on this queue
f = s.open(1, "file:db.log")   # f2: the payload
s.sendmsg(q, [f], 0)           # kernel: get_file() per passed fd
s.close(1, 1)                  # sender drops its fd at once
s.recvmsg(2, 0, cloexec=True)  # rc unchanged: ref transfers
s.close(2, 1)                  # receiver done -> freed
print("\n== scenario 2: leaked in-flight fd ==")
s.sendmsg(q, [s.open(3, "file:db.dump")], 1)  # p3 pushes to sock:Q ...
s.close(3, 0)                  # ... drops its fd; queue never drains: LEAK
print("\n== scenario 3: double-close detection ==")
s.open(4, "file:key.pem")      # f4: p4 fd0
s.dup(4, 0)                    # fd1 now shares the struct file
s.close(4, 0)                  # rc 2 -> 1
s.close(4, 0)                  # fd0 already gone: flag
s.close(4, 1)                  # last holder -> freed
print("\n== scenario 4: unix_gc cycle (each end passed to the other) ==")
a = s.open(5, "sock:A")        # f5
b = s.open(5, "sock:B")        # f6
s.sendmsg(b, [a], 2)           # skb2 on B's queue holds A
s.sendmsg(a, [b], 3)           # skb3 on A's queue holds B
s.close(5, 0)
s.close(5, 1)
s.die(5)                       # p5 exits; its skb holders survive in kernel
s.gc()                         # Tarjan SCC -> collect {A, B}
print()
print("\n".join(s.trace))
s.report()
```

Output (verbatim run):

```text
== scenario 1: clean handoff p1 -> p2 ==

== scenario 2: leaked in-flight fd ==

== scenario 3: double-close detection ==

== scenario 4: unix_gc cycle (each end passed to the other) ==

open   f0   sock:P        rc=1
open   f1   sock:Q        rc=1
open   f2   file:db.log   rc=1
send   skb0 q=f1   fds=f2    rc=2 (get_file x1)
close  f2   p1 fd1 rc=1
recv   skb0 f2->p2:fd1 rc=1 [+MSG_CMSG_CLOEXEC]
close  f2   p2 fd1 rc=0 freed
open   f3   file:db.dump  rc=1
send   skb1 q=f1   fds=f3    rc=2 (get_file x1)
close  f3   p3 fd0 rc=1
open   f4   file:key.pem  rc=1
dup    f4   p4 fd0->fd1 rc=2
close  f4   p4 fd0 rc=1
close  p4 fd0 DOUBLE-CLOSE: no holder, flag!
close  f4   p4 fd1 rc=0 freed
open   f5   sock:A        rc=1
open   f6   sock:B        rc=1
send   skb2 q=f6   fds=f5    rc=2 (get_file x1)
send   skb3 q=f5   fds=f6    rc=2 (get_file x1)
close  f5   p5 fd0 rc=1
close  f6   p5 fd1 rc=1
die    p5 exits; skb holders survive in the kernel
gc     collect cycle f5+f6 (dead endpoints)

== final struct file table ==
fid   kind            rc  status
f0    sock:P           1  alive: p1:fd0
f1    sock:Q           1  alive: p2:fd0
f2    file:db.log      0  freed
f3    file:db.dump     1  LEAK: in-flight skb on f1
f4    file:key.pem     0  freed
f5    sock:A           0  freed (GC cycle)
f6    sock:B           0  freed (GC cycle)

flags: ['double-close p4 fd0']
```

Scenario 2 is the operational read of the ledger: an fd "held by a queue" is invisible to every process yet keeps the file alive -- the classic leak shape in daemons that pass fds to slow consumers. Scenario 4 is why unix_gc must do SCC collection rather than simple refcount-zero checks.

## Cross-references

- [Unix Domain Sockets](../../../networks/sockets/unix.md) -- API-level SCM_RIGHTS recipe and UDS applications
- [Virtual File System](./vfs.md) -- `struct file`, `f_count`, and the fd-to-file lookup path
- [File Operations](./file-ops.md) -- open/read/close and the syscall layer above this page
- [The New Mount API](./mount-api.md) -- fs_context lifecycle and other fd-centric kernel interfaces

## References

1. unix(7) man page, man7.org -- SCM_MAX_FD value and history, RLIMIT_NOFILE auto-close semantics: <https://man7.org/linux/man-pages/man7/unix.7.html>
2. recvmsg(2) -- MSG_CMSG_CLOEXEC (since Linux 2.6.23), MSG_CTRUNC: <https://man7.org/linux/man-pages/man2/recvmsg.2.html>
3. sendmsg(2) -- ancillary data send path: <https://man7.org/linux/man-pages/man2/sendmsg.2.html>
4. pidfd_getfd(2) -- Linux 5.6, PTRACE_MODE_ATTACH_REALCREDS, comparison to SCM_RIGHTS: <https://man7.org/linux/man-pages/man2/pidfd_getfd.2.html>
5. Kernel source include/net/scm.h -- `#define SCM_MAX_FD 253`, `struct scm_fp_list`: <https://raw.githubusercontent.com/torvalds/linux/master/include/net/scm.h>
6. Kernel source net/unix/garbage.c -- unix_inflight accounting, GC history comments, SCC machinery: <https://raw.githubusercontent.com/torvalds/linux/master/net/unix/garbage.c>
7. Kernel source net/core/scm.c -- `scm_detach_fds()`, MSG_CMSG_CLOEXEC to O_CLOEXEC mapping: <https://raw.githubusercontent.com/torvalds/linux/master/net/core/scm.c>
8. Kernel source fs/file.c -- `expand_fdtable()`, `resize_in_progress`, `resize_wait`: <https://raw.githubusercontent.com/torvalds/linux/master/fs/file.c>
9. v5.15 net/unix/scm.c -- historical `too_many_unix_fds()` / `-ETOOMANYREFS` behavior: <https://raw.githubusercontent.com/torvalds/linux/v5.15/net/unix/scm.c>
10. sd_listen_fds(3) (Ubuntu mirror; freedesktop.org returns 403 to curl) -- LISTEN_PID/LISTEN_FDS/LISTEN_FDNAMES, SD_LISTEN_FDS_START: <https://manpages.ubuntu.com/manpages/noble/man3/sd_listen_fds.3.html>
11. L. Poettering, "Socket Activation" -- motivation and mechanics of fd handoff to services: <https://0pointer.de/blog/projects/socket-activation.html>
