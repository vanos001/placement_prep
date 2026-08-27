# Leases: Correctness From a Ticking Clock

A lock says "you may act until you release it." A lease says "you may act until time T."
That one substitution is what makes fault tolerance tractable: if the holder crashes,
you do not need to detect the crash - you need to wait. The lease is the workhorse
behind file-write arbitration in HDFS, chunk mutations in GFS, session management in
Chubby, leader election in Kubernetes, and every "cached data is good for N seconds"
story that actually promises consistency rather than hoping for it. The idea was
formalized by Cary Gray and David Cheriton at SOSP 1989, in the context of network file
server cache consistency, and their argument still holds: a lease turns fault recovery
from a message-exchange problem into a timeout problem.

## What a Lease Actually Buys

The grant is simple: the server records `(holder, expiry)`, the holder may act until the
deadline, and after the deadline the server may grant the same right to someone else.
The deep property is what Gray and Cheriton called out as the point of the design:

- **Silence is safe.** A crashed, partitioned, or paused holder needs to send nothing and
  receive nothing. The system converges to a consistent state by waiting out the clock.
- **Slow and dead become indistinguishable - and it stops mattering.** In an asynchronous
  system you cannot tell a crashed peer from a slow one; any scheme that needs to know
  is broken by construction. Leases sidestep the question: slow holders lose the right
  when the deadline passes, exactly like dead ones.
- **No cleanup protocol on crash.** Contrast heartbeat-validity schemes, where the server
  must notice missing heartbeats, garbage-collect the holder's state, and prove nobody
  is still acting - all before it can safely reassign the right.

The price: everyone must agree, within bounded error, on when the lease expires. A lease
is a quorum of one, plus a clock assumption.

## Where the Idea Came From: File Cache Consistency

In 1989 the concrete problem was NFS-style caching. A client caches file blocks and
attributes for performance; a fixed-time attribute cache (NFS defaults historically
allowed 3 to 60 seconds of staleness) gives you no soundness story at all - a writer on
another machine can change the file the instant after you cache it, and your reads are
simply wrong until your timer fires. Server-initiated callbacks fix that but require the
server to remember every client, page them, and recover from each client's crash before
acting - expensive, and it makes the server's correctness depend on crash detection.

The lease design: when a client reads cached data, the server grants a read lease; the
cached copy is valid while the lease is. A writer must wait for read leases to expire
(seconds, not minutes) or for clients to release them; its write then proceeds safely.
Client crashes require zero server action - the wait does the recovery.

```text
 server                                        client
   |--- GRANT(lease on block B, T = now + L) --->|
   |                                             | serves reads from cached B
   |                                             | ... client crashes / pauses ...
   |                (no messages: silence is safe)                    |
   |   T passes: cached copy may no longer be used               X
   |<-- (optional) client revalidates or refetches --------------|
   |--- GRANT to writer: safe, all old leases have expired ----->|
```

## The Timing Contract

Safety needs three quantities to fit inside the lease duration `L`:

- maximum clock skew `s` between server and holder,
- maximum one-way message delay `d`,
- maximum processing time `p` at the grantor.

A holder that receives its grant at server time `t0` must stop acting at its own local
time corresponding to `t0 + L - s`, conservatively shaving the skew off the deadline.
Conversely the server must not regrant before `t0 + L + s` (its clock may read late).
The requirement `L > 2d + p + s` is the whole engineering content of a lease: it is why
a lease can be a few seconds in a LAN (skew and delay are milliseconds) but must stretch
across WAN links.

Implementation guidance that avoids whole classes of bugs:

- Measure the remaining lease with a **monotonic clock** (`CLOCK_MONOTONIC`, not
  `CLOCK_REALTIME`), so NTP adjustments cannot extend or kill a lease locally.
- Wall-clock timestamps belong in the *recorded* lease (so other machines can inspect
  it), not in the *enforcement* loop.
- If you must compare times across machines, compare with the skew subtracted, and log
  the skew you assumed - the number is a safety argument, not a tuning knob.

## Renewal and Revocation

Renewal is a new grant, not a prolongation: the server extends only while no conflicting
grant waits. That single rule makes leases composable, and it makes revocation possible:

1. To revoke, the server stops renewing and marks the lease revoked.
2. It waits out the remaining lifetime (worst case: the full lease duration).
3. Only then may it grant the right elsewhere - guaranteed no ghost holder acts.

Kubernetes' leader-election settings make the trade-off arithmetic visible: with typical
client-go/controller-runtime defaults, the leader renews every 2 s (retry period), gives
up after 10 s without a successful renewal (renew deadline), and observers wait 15 s
(lease duration) before concluding the leadership is vacant. Renew deadline < lease
duration is deliberate: the holder stops acting *before* anyone else may start.

## Leases vs Quorums

| Aspect | Lease | Quorum (majority) |
| --- | --- | --- |
| Grantor contact | 1 node, 1 round trip | f + 1 nodes per operation |
| Availability of the right | survives f failures as long as grantor lives | needs a live majority |
| Clock assumption | bounded skew and delay required | none |
| Crash of holder | self-heals after the timeout | n/a (no holder state) |
| Failure mode if assumptions break | two actors during skew window | none (liveness only) |

Leases buy single-node latency and simplicity; quorums buy safety with no time
assumptions. Systems often mix: a lease for fast-path ordering, quorums underneath for
membership and recovery.

## Leases in Production

| System | Leased object | Duration | Renewal | What expiry triggers |
| --- | --- | --- | --- | --- |
| GFS | chunk mutation lease to a primary chunkserver | 60 s | extended via master heartbeats | master picks a new primary or re-leases |
| HDFS | file write lease from NameNode to writer client | soft 60 s, hard 1 h | client heartbeats keep it alive | lease recovery: close file, finalize blocks, bump generation stamp |
| Chubby | session lease (default 12 s) | 12 s | KeepAlive RPCs | session lost; master failover covered by a client grace period |
| Kubernetes | Lease object (coordination.k8s.io/v1) | 15 s leader elections; node leases renewed every 10 s | holder updates renewTime | another candidate takes over; node marked NotReady |

Notice that HDFS's generation stamp and GFS's chunk version numbers are fencing tokens:
each new grant bumps a monotonic counter, and the storage layer rejects writes carrying
stale tokens. Leases alone narrow the window of two-actor overlap to clock error;
fencing tokens close it. Chubby hands out sequence numbers for the same reason.

## The GC-Pause Trap

Now the failure every systems interviewer eventually asks about. A client acquires a
10-second lease, reads some state, computes an update - and then stops for a garbage
collection pause, a VM freeze, cgroup CPU throttling, or a stray SIGSTOP. The pause
outlives the lease. A second client acquires the lease and writes. The first client
wakes up, still believing its lease is valid, and applies its stale update. No network
partition, no clock problem - just scheduling. The simulation below reproduces it with a
deterministic fake clock, then shows fencing tokens rejecting the stale writer:

```python
LEASE, GC_PAUSE = 10, 30            # seconds

def simulate(fencing):
    store = {"value": 0, "epoch": 0}  # epoch = fencing token: bumps on every grant
    log, holder, expires = [], None, -1

    def acquire(who, now):
        nonlocal holder, expires
        if holder is not None and now < expires:
            log.append(f"t={now:2d}  {who}: acquire REFUSED (held by {holder} until t={expires})")
            return
        holder, expires, reason = who, now + LEASE, ""
        store["epoch"] += 1
        log.append(f"t={now:2d}  {who}: acquired lease [{now},{expires}) epoch={store['epoch']}")

    def write(who, new_value, token, now):
        if fencing and token != store["epoch"]:
            log.append(f"t={now:2d}  {who}: write({new_value}) token={token} -> "
                       f"REJECTED (current epoch {store['epoch']})")
            return
        store["value"] = new_value
        log.append(f"t={now:2d}  {who}: write({new_value}) -> accepted (value={store['value']})")

    acquire("C1", 0)
    c1_token = store["epoch"]
    log.append("t= 1  C1: reads value=0, computes 0+1=1, then blocks in a 30 s GC pause")
    acquire("C2", 3)                              # refused: C1 still holds until t=10
    acquire("C2", 12)                             # C1's lease expired at t=10: safe to grant
    write("C2", 100, store["epoch"], 13)
    write("C1", 1, c1_token, 1 + GC_PAUSE)        # C1 resumes at t=31 and applies stale work
    log.append(f"t=31  final value = {store['value']}")
    return log

for fencing in (False, True):
    print(f"--- {'WITH' if fencing else 'WITHOUT'} fencing tokens ---")
    for line in simulate(fencing):
        print(line)
    print()
```

Real output:

```text
--- WITHOUT fencing tokens ---
t= 0  C1: acquired lease [0,10) epoch=1
t= 1  C1: reads value=0, computes 0+1=1, then blocks in a 30 s GC pause
t= 3  C2: acquire REFUSED (held by C1 until t=10)
t=12  C2: acquired lease [12,22) epoch=2
t=13  C2: write(100) -> accepted (value=100)
t=31  C1: write(1) -> accepted (value=1)
t=31  final value = 1

--- WITH fencing tokens ---
t= 0  C1: acquired lease [0,10) epoch=1
t= 1  C1: reads value=0, computes 0+1=1, then blocks in a 30 s GC pause
t= 3  C2: acquire REFUSED (held by C1 until t=10)
t=12  C2: acquired lease [12,22) epoch=2
t=13  C2: write(100) -> accepted (value=100)
t=31  C1: write(1) token=1 -> REJECTED (current epoch 2)
t=31  final value = 100
```

Without fencing, C2's write of 100 is silently destroyed - a lost update under a lease
that "never had two holders" if you trust the clock. With fencing, safety is restored
but the stale client's operation *fails*: fencing trades silent corruption for a visible
error that the client must handle by re-acquiring and redoing its work. That is the
correct trade. Martin Kleppmann's widely read analysis of distributed locking makes the
same argument: if you cannot fence, you must at minimum make operations idempotent and
verify preconditions at the storage layer, because the lease - any lease, with any
duration - cannot rule out the pause that outlives it.

## Sharp Edges for Interviews

- "Can't we just make the lease longer?" A longer lease shrinks the skew window
  (proportionally) but lengthens failover: revocation waits out the full duration.
  Duration is a liveness/safety trade, not a free fix.
- "Who renews - the worker or a watchdog?" If a background watchdog renews while the
  worker deadlocks, the lease never expires though the holder is useless. Chubby's
  KeepAlive renews the *session*; correctness of individual operations still needs
  version checks. Renewal proves liveness of the renewer, nothing more.
- "Why does HDFS have two limits?" The soft limit (60 s) is advisory - NameNode may
  recover the lease early; the hard limit (1 h) bounds how long a hung client can block
  everyone else. Two clocks, two purposes: liveness and worst-case wait.
- "Where does the fencing token come from?" The grantor's monotonic counter - ZooKeeper
  version numbers, HDFS generation stamps, Chubby sequence numbers, Kubernetes
  resourceVersions. It must be checked by whatever the holder writes to, not by the
  holder's own bookkeeping.

## References

- Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency - Gray and Cheriton (SOSP 1989): https://doi.org/10.1145/74850.74870
- Chubby: The Chubby lock service for loosely-coupled distributed systems - Burrows (OSDI 2006): https://research.google/pubs/pub27897/
- Kubernetes docs - Leases: https://kubernetes.io/docs/concepts/architecture/leases/
- HDFS Architecture Guide (leases and block recovery): https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HdfsDesign.html
- How to do distributed locking - Kleppmann (2016): https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
