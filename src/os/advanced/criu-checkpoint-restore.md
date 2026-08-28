# CRIU Internals: Checkpointing a Running Process

CRIU (Checkpoint/Restore In Userspace) freezes a process tree, serializes its
complete observable state into image files, and rebuilds it later on the same
host or another one -- preserving PIDs, open file descriptors, and even TCP
sockets in mid-conversation. Born in the Virtuozzo/OpenVZ live-migration world,
it now powers `podman container checkpoint`. The CLI cookbook lives
in [the containers CRIU page](../../linux/containers/criu.md); this page is the
machinery: what gets captured, how code gets into a frozen process, and what
TCP_REPAIR must serialize. Current upstream release: v4.2.1
([criu.org/Download](https://criu.org/Download)).

## The state vector a dump must capture

A process is a fan-out across procfs, ptrace, and kernel structures that CRIU
must read **consistently** (hence: seize everything first, read after):

| Object                 | Source of truth at dump time                | Image artifact        | Restore-time hazard                     |
|------------------------|---------------------------------------------|-----------------------|-----------------------------------------|
| Thread registers + IP  | ptrace `PTRACE_GETREGSET` on seized tasks   | core-<pid>.img        | IP must land in a rebuilt mapping        |
| Address space          | `/proc/pid/maps` + parasite page reads      | vma-*.img, pages-*.img| Map at identical addresses, incl. gaps   |
| File descriptors       | `/proc/pid/fd` + fstat via parasite         | fdinfo-*.img          | Rebuild the dup table, same fd numbers   |
| Established sockets    | `TCP_REPAIR` mode                           | fdinfo-*.img (sock)   | Seq/window continuity, options           |
| PIDs and process tree  | procfs + pstree walk                        | pstree.img            | Re-create historical PIDs (new PID ns)   |
| Creds, rlimits, sigact | procfs + parasite prctl calls               | pstree.img / core     | Order of setting vs. dropping caps       |
| SysV shm, pipes, epoll | procfs + parasite                           | ipc*, fifo, eventfd   | Refcount peers living outside the tree   |
| Namespaces             | nsfs handles                                | netns, ids in images  | netns/time-ns must exist before sockets  |

Two entries deserve emphasis. **PIDs**: the restored tree must get its original
PIDs back, only possible by forking the tree inside a freshly created PID
namespace (children there get predictable sequential PIDs) and adjusting
`ns_last_pid` -- gated by `CAP_SYS_ADMIN` or, since Linux 5.9,
`CAP_CHECKPOINT_RESTORE` (see [capabilities](../../linux/security/capabilities.md)).
**Time namespaces** (Linux 5.6+) exist largely for CRIU: after migration the new
host's `CLOCK_MONOTONIC`/`CLOCK_BOOTTIME` differ, and per-namespace offsets
restore the illusion of an unbroken clock
([namespaces: processes](../../linux/kernel/processes/namespaces.md)).

## Freezing a task: seize, inject, command

Reading most of that state must happen *in the target's context* (`map_files`,
page reads through its address space, fd polling). A frozen task cannot run
([criu.org/Parasite](https://criu.org/Parasite)).

```text
parasite infection (parasite-syscall.c, parasite_infect_seized)

  1. PTRACE_SEIZE each task        -> stopped, but "seized" (no visible stop)
  2. ptrace-driven syscall: mmap   -> shared RW area in the target
  3. CRIU opens the same area      -> via /proc/<pid>/map_files (its "hole")
  4. copy PIE parasite blob + asm  -> bootstrap is per-arch (x86, arm, arm64)
  5. redirect instruction pointer  -> parasite runs inside the dumpee

     CRIU process                      frozen dumpee process
     ------------                      ---------------------
     unix socket  <------------------  parasite daemon
     (PARASITE_CMD_* packets)          (reads pages, dumps fds, polls)
```

The parasite runs in two modes: **trap mode** executes one command and traps
back to CRIU; **daemon mode** opens a unix socket and serves `PARASITE_CMD_*`
requests in a loop -- the difference between poking a process one instruction at
a time and batch-processing its memory at memcpy speed. Dumping done, CRIU
"cures" the process: original code bytes are restored, the hole unmapped. The
same trick powers restore, where a **restorer blob** performs final
self-assembly: mmap the saved VMAs at their original addresses, populate pages
from image files, rebuild the fd table -- all before the final `sigreturn`
hands control back to the original instruction pointer. The restored process
never runs `execve`; it *becomes* the target by modifying itself.

The dump side writes one protobuf-encoded image file per object type per task
(`pstree.img`, `core-<pid>.img`, `pages-*.img`, ...); restore consumes them in
dependency order: namespaces first, then process tree, then fds, then sockets.

## TCP_REPAIR: re-animating a socket mid-stream

Network state is hardest because the peer is a distributed witness that keeps
ACKing against your old sequence numbers. Kernel 3.5 added `TCP_REPAIR` for
this: while set, syscalls take on nonstandard meanings -- `connect()` merely
flips state to ESTABLISHED with the peer address you name, `bind()` binds
forcibly ignoring conflicts, nothing transmits
([criu.org/TCP_connection](https://criu.org/TCP_connection)). Queued data becomes
visible as bytes: you can drain the *outgoing* queue with `recv()` and re-inject
bytes into the *incoming* queue with `send()`. `TCP_QUEUE_SEQ` gets/sets each
queue's sequence anchor (only while CLOSED), and `TCP_REPAIR_OPTIONS` re-arms
the four negotiated options: `mss_clamp`, `snd_scale`, `sack`, `tstamp`.

The model below accounts, for one toy socket, exactly which bytes must be
serialized, where in-flight bytes live, and why the stream stays gapless:

```python
# TCP_REPAIR state-capture model: what bytes a CRIU dump must serialize
# for one established socket, and why the restored stream stays continuous.

ISN_OUT = 1000          # our initial send seq
ISN_IN  = 500000        # peer's initial seq
MSS     = 1400
write_tail = ISN_OUT + 47000   # 48000: app wrote 14000 + 22000 + 11000 bytes
snd_una    = ISN_OUT + 25000   # 26000: peer acked everything below
snd_nxt    = ISN_OUT + 43000   # 44000: everything below was sent once
# The 18000 sent-but-unacked bytes split three ways:
wire_fwd, peer_hold, rto_wait = 8000, 6000, 4000
assert wire_fwd + peer_hold + rto_wait == snd_nxt - snd_una
rcv_nxt = ISN_IN + 26000            # 526000: in-order edge at a 2000 B hole
ooo     = [(ISN_IN + 28000, 3000)]  # (start_seq, len) buffered out-of-order
lost_in = 2000                      # the hole: peer's RTO will re-cover it
in_order_unread = (rcv_nxt - ISN_IN) - 6000   # queued, app has not read it
# TCP_REPAIR_OPTIONS re-arms the four negotiated options:
opts = {"mss_clamp": MSS, "snd_scale": 7, "sack": 1, "tstamp": 1}

send_q = write_tail - snd_una                 # drained via recv() in repair mode
recv_q = in_order_unread + sum(n for _, n in ooo)  # re-injected via send()
meta   = 4 + 4 + 4 + 4 + len(opts) + 2 * len(ooo)  # seqs+wnd+opts+ranges (words)

print("TCP_REPAIR dump for one established socket")
print("  seq state      : SND.UNA=%d SND.NXT=%d write_tail=%d RCV.NXT=%d"
      % (snd_una, snd_nxt, write_tail, rcv_nxt))
print("  wire map       : in-flight=%d peer-held=%d rto-wait=%d (all inside send queue)"
      % (wire_fwd, peer_hold, rto_wait))
print("  hole (peer covers via its own RTO): %d bytes at %d" % (lost_in, rcv_nxt))
print("  serialize      : send_q=%d B  recv_q=%d B (in-order %d + OOO %d)"
      % (send_q, recv_q, in_order_unread, sum(n for _, n in ooo)))
print("  OOO ranges     : %s" % ooo)
print("  options bitmap : %s" % opts)
print("  checkpoint cost: %d B payload + ~%d B metadata = %d B"
      % (send_q + recv_q, meta * 4, send_q + recv_q + meta * 4))

# Restore order: socket(CLOSED) -> TCP_REPAIR=1 -> TCP_QUEUE_SEQ x2 -> bind
# (forced) -> connect (flips to ESTABLISHED) -> TCP_REPAIR_QUEUE + send() to
# refill both queues -> TCP_REPAIR_OPTIONS -> TCP_REPAIR=0 -> retransmit.
new_una       = snd_una                                # restored anchor
peer_expected = ISN_OUT + 25000 + 6000 + 8000 + 4000   # what peer saw sent
stream_ok = new_una <= peer_expected <= snd_nxt  # first retransmit = old una;
# old in-flight segments arrive as duplicates; TCP drops them by seq match.
app_pending = recv_q + lost_in          # bytes the app is still owed
print("  restore check  : una-continuity=%s  stream-gapless=%s  app-owed=%d B"
      % (new_una == ISN_OUT + 25000, stream_ok, app_pending))
print("  freeze->resume : retransmit of %d B from restored queue; 8000 B of old"
      % (snd_nxt - snd_una))
print("                   in-flight duplicates are dropped by seq match, not reordered")
```

Output (real run of the script above):

```text
TCP_REPAIR dump for one established socket
  seq state      : SND.UNA=26000 SND.NXT=44000 write_tail=48000 RCV.NXT=526000
  wire map       : in-flight=8000 peer-held=6000 rto-wait=4000 (all inside send queue)
  hole (peer covers via its own RTO): 2000 bytes at 526000
  serialize      : send_q=22000 B  recv_q=23000 B (in-order 20000 + OOO 3000)
  OOO ranges     : [(528000, 3000)]
  options bitmap : {'mss_clamp': 1400, 'snd_scale': 7, 'sack': 1, 'tstamp': 1}
  checkpoint cost: 45000 B payload + ~88 B metadata = 45088 B
  restore check  : una-continuity=True  stream-gapless=True  app-owed=25000 B
  freeze->resume : retransmit of 18000 B from restored queue; 8000 B of old
                   in-flight duplicates are dropped by seq match, not reordered
```

Three observations fall out of the arithmetic. First, the send queue is a
*superset* of "in flight": unacked, peer-held, and never-transmitted bytes all
live in the same socket queues and all get serialized. Second, data lost
*toward* us (the 2000 B hole) is deliberately **not** in the checkpoint; the
peer's own RTO re-covers it, and the restored socket preserves `RCV.NXT` plus
the OOO ranges so the retransmission still fits. Third, sequence-anchor
continuity makes migration invisible: bytes the old host had on the wire arrive
at the peer as duplicates and are discarded by seq match. The dangerous
direction is traffic *toward the source* -- migration must take over the IP
path (ARP/route move, or a drain window). TCP timestamps use the kernel jiffies
clock, one more reason migrated sockets care about clock continuity.

## Migration strategies: pre-copy, post-copy, page server

Dumping a multi-GB address space in one shot means one long freeze. CRIU splits it:

| Strategy        | Memory moved before resume        | Downtime driven by            | Failure cost                        |
|-----------------|-----------------------------------|-------------------------------|-------------------------------------|
| Stop-and-copy   | all of it, during the freeze      | RAM size + transfer + restore | long frozen window                  |
| Pre-copy        | iterative pre-dumps while running | final dirty set + restore     | wasted rounds if write rate is high |
| Post-copy/lazy  | only minimal state                | first-fault latency           | source must stay alive per page     |

`criu pre-dump` captures memory only and leaves the task running ("later
operations supersede prior dumps", as Podman's `--pre-checkpoint` describes it);
repeating it shrinks the set of pages changed since the last pass, so downtime
converges toward dirty rate, not memory size -- the same convergence fight KSM
has with footprint, except KSM cuts resident size, not write rate
([KSM internals](ksm-page-merging.md)). Post-copy inverts it: `criu dump
--lazy-pages` transfers only minimal state, the task resumes on the destination
almost immediately, and the **lazy-pages daemon** intercepts its page faults and
pulls each needed page from the source node on demand (built on userfaultfd --
see [userfaultfd](../../linux/kernel/memory/userfaultfd.md)). The **page server**
streams images to a remote host instead of staging them on local disk
([criu.org/Page_server](https://criu.org/Page_server)). Fast-failover designs
combine both: cheap periodic pre-dumps keep a warm copy; on failure, restore
runs lazy so the process serves again in milliseconds while cold pages stream in.

## Container integration status

- **Podman**: `podman container checkpoint` / `restore` wrap CRIU through the
  container runtime (crun/runc). An `--export` archive can be imported on
  another host, which Podman's docs describe as enabling container live
  migration; checkpoint *images* can be pushed to a registry like any layer and
  carry annotations such as the CRIU and runtime versions used. Flags mirror
  kernel fidelity choices: `--tcp-established`, `--file-locks`, `--pre-checkpoint`.
- **Kubernetes**: no in-tree pod live migration. What exists is the kubelet
  **Checkpoint API** (`POST /checkpoint/{namespace}/{pod}/{container}`),
  beta in v1.30 and enabled by default -- a *forensic* checkpointing facility
  (KEP-2003) returning a tar of CRIU images via the CRI; the docs warn the
  archive contains all memory pages and is therefore sensitive
  ([kubelet checkpoint API](https://kubernetes.io/docs/reference/node/kubelet-checkpoint-api/)).
- **Heritage**: OpenVZ/Virtuozzo run production CRIU live migration; CRI-O
  implements the CRI checkpoint calls the kubelet API drives.

Honest summary: single-container checkpoint/migrate is solid; live-migrating a
*pod* (shared netns, volumes, cluster IP, sidecars) is an open systems problem,
and most Kubernetes users get resilience from rescheduling instead.

## Limitations ledger

| Limitation                | Why it bites                                                                 |
|---------------------------|------------------------------------------------------------------------------|
| External resources        | fds to device nodes, host-local sockets, or paths outside the tree fail reattachment |
| GPU state                 | CUDA contexts, cuFile/GPUDirect registrations are not captured -> GPU failover needs app-level checkpoints |
| Timers and clocks         | interval timers/timerfds are captured, but monotonic continuity rides on time namespaces |
| Kernel-version coupling   | images encode kernel object layouts; dump and restore across mismatched kernels is fragile |
| Newer kernel objects lag  | exotic fds (io_uring rings, seccomp notifications, pidfd features) gain support late |
| Secrets in images         | a checkpoint archive is a full memory dump; anyone holding it can read the process |

## CRIU versus the alternatives

| Approach                 | Captures                          | Strength                     | Weakness                              |
|--------------------------|-----------------------------------|------------------------------|---------------------------------------|
| VM snapshot / migration  | whole machine incl. kernel        | mature pre/post-copy (QEMU)  | migrates everything; guest kernel too |
| CRIU                     | process tree + kernel objects     | container granularity, TCP   | root, kernel coupling, external fds   |
| DMTCP                    | userland wrapper (LD_PRELOAD)     | no kernel requirements       | misses raw syscalls/plugins; weaker sockets |
| App-level checkpoints    | semantic state (e.g., training)   | handles GPUs, resumable jobs | needs cooperation; not transparent    |

## Interview angles

1. Why inject a parasite instead of doing everything through ptrace? (One
   syscall per stop vs. a command loop; some operations only work in the
   target's context, e.g., `map_files` access.)
2. Walk the wire when migrating an established TCP connection: what is
   serialized, what covers in-flight bytes, what happens to duplicates?
3. Why did Kubernetes settle for forensic checkpointing instead of pod live
   migration? (Image secrecy, cluster IP/volume state, scheduler assumptions,
   node kernel coupling.)

## Where this connects

- CLI usage, flags, worked examples: [CRIU cookbook](../../linux/containers/criu.md)
- PID/time namespaces and restore-time clock fixes: [process namespaces](../../linux/kernel/processes/namespaces.md);
  network side of migrating sockets: [network namespaces](../../linux/kernel/networking/namespaces.md)
- Demand paging underpinning lazy migration: [userfaultfd](../../linux/kernel/memory/userfaultfd.md)

## References

1. CRIU project -- Download (release v4.2.1): https://criu.org/Download
2. CRIU wiki -- Parasite (injection, trap/daemon modes): https://criu.org/Parasite
3. CRIU wiki -- TCP connection (TCP_REPAIR mechanics): https://criu.org/TCP_connection
4. CRIU wiki -- Lazy migration (post-copy with lazy-pages daemon): https://criu.org/Lazy_migration
5. LWN.net, "TCP connection repair" (kernel-side TCP_REPAIR overview): https://lwn.net/Articles/495304/
