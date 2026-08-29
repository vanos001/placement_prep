# Fencing Tokens: Enforcing Expiry Where the Data Lives

A lock or a lease is a permission slip issued by a coordinator. Nothing in
the permission physically stops a client whose pause outlived it from
writing stale data. The missing piece is an invalidation mechanism: a
monotonically increasing token minted by the coordinator, carried on every
protected operation, and checked by the storage that receives the writes.
[Distributed locks](distributed-locks.md) catalogs lock designs and
[leases](../advanced/leases.md) derives the timing contract; this page
covers why permission alone cannot be safe, and how Chubby sequencers,
ZooKeeper zxids, etcd revisions, Kubernetes resourceVersions, GFS chunk
versions, and HDFS generation stamps enforce expiry where the data lives.

## Permission Decays; Acceptance Does Not

```text
t=0    C1 acquires a 10 s lease
t=1    C1 writes value=0          -> storage accepts
t=2    C1 stops: full GC, VM freeze, cgroup throttle, SIGSTOP (30 s)
t=10   lease expires; grantor regrants; C2 acquires and writes value=100
t=31   C1 resumes, writes value=1 -> storage accepts: C2's write destroyed
```

Two asymmetries make this fatal: the coordinator's grant decays with time
while the client's belief in it does not, and the storage's acceptance is
permanent - value=1 wins forever. A longer lease only shrinks the window;
in an asynchronous system the pause is unbounded. The lease budget
(`L > 2d + p + s`, derived on the [leases page](../advanced/leases.md))
narrows the two-actor window to clock error and scheduling; fencing tokens
are what close it.

## The Fencing Token Contract

Kleppmann's canonical statement: "provided that the lock service generates
strictly monotonically increasing tokens, this makes the lock safe." The
contract has five parts:

1. **Minted by the grantor, not the client.** The coordinator stamps each
   grant from a counter that survives its own failures (failover below).
2. **Strictly monotonic.** No two live grants share a value; values never go
   backwards. This rules out timestamps (skew) and resettable counters.
3. **Carried on every protected operation.** A token on the acquire RPC but
   not on the write is decoration; the delayed request is the dangerous one.
4. **Checked by the storage that takes the writes.** It records the highest
   token accepted and rejects lower ones; retries of the *same* operation
   carry the same token and must be accepted.
5. **Rejection is visible and handled.** Fencing trades silent corruption
   for an explicit failure; the stale client re-acquires, re-reads, redoes.

Point 4 is where most designs die: the check must live in a component the
stale client cannot fool - and the misbehaving party is the client.

## Lease Expiry Numbers Are a Budget, Not a Guarantee

A paused client spends this budget before anyone can take the right away.

| Grantor | Grant and renewal figures (source) | Pause budget without fencing |
| --- | --- | --- |
| Chubby session | KeepAlive-extended; default lease extension 12 s (OSDI'06 paper) | under 12 s |
| GFS chunk primary lease | initial timeout 60 s, extended while mutating (SOSP'03 paper) | under 60 s |
| Kubernetes leader election | lease 15 s, renew deadline 10 s, retry 2 s (kube-controller-manager defaults) | holder gives up at 10 s |
| HDFS write lease | NameNode auto lease recovery; `dfs.namenode.lease-hard-limit-sec` default 1200 s (hdfs-default.xml) | under 1200 s |

The Kubernetes row shows the trade: the holder stops at 10 s so observers
waiting 15 s never see two leaders - but a 12 s GC pause in the leader
creates two actors anyway unless the leader's downstream writes are fenced.
Budgets are liveness knobs; fencing is the safety mechanism.

## Where the Token Lives in Real Systems

| System | Token | Minted by | Checked at | Rejection signal |
| --- | --- | --- | --- | --- |
| Chubby | lock sequencer: name, mode, generation | Chubby master | resource server via `CheckSequencer()` | sequencer invalid -> reject |
| ZooKeeper | zxid / czxid / znode version | ensemble, leader-ordered proposals | guarded store in the app | stale zxid/version -> reject |
| etcd | key `mod_revision`, store-wide revision | raft-applied MVCC store | `txn` compare on `mod_revision` | compare fails -> else branch |
| Kubernetes | `metadata.resourceVersion` | etcd revision via kube-apiserver | API server on update/delete | 409 Conflict |
| GFS | chunk version number | master, bumped per new lease | chunkservers on mutations | stale replica -> GC'd |
| HDFS | per-block generation stamp | NameNode, advanced at lease recovery | DataNodes in the pipeline | stale-stamp op fails |
| Redis | none built in | - | you must add it | - |

### Chubby: sequencers and the lock-delay fallback

Per the OSDI'06 paper, "a lock holder may request a sequencer, an opaque
byte-string... It contains the name of the lock, the mode in which it was
acquired (exclusive or shared), and the lock generation number." The
recipient server tests it "against the most recent sequencer that the server
has observed" and rejects otherwise. For servers that never adopt
sequencers, Burrows added an "imperfect but easier mechanism": on a
failure-driven release the service blocks re-grants for a lock-delay,
"currently one minute" - it widens the pause budget but does not close the
window. Chubby's client epoch numbers keep this safe across master failover.

### ZooKeeper: zxid as the token source

The internals doc fixes the layout: "The zxid has two parts: the epoch and a
counter... We use the high order 32-bits for the epoch and the low order
32-bits for the counter. The epoch number represents a change in
leadership." The stat structure exposes `czxid` and `version`, and sequence
nodes append "a monotonically increasing counter" to paths. The zxid is
assigned by consensus, exactly the strictly monotonic counter fencing needs
- Kleppmann: "if you are using ZooKeeper as lock service, you can use the
zxid or the znode version number as fencing token." Ephemeral nodes vanish
with the session, but a vanished node is invisible to a delayed write: the
guarded resource still needs the zxid check. See [ZooKeeper](zookeeper.md).

### etcd: revisions and transactional gates

Every key carries `create_revision` and `mod_revision`; every response
header carries the store-wide `revision` ("the revision of the key-value
store when generating the response"), applied through raft and therefore
monotonic across leader changes. The gate is a `txn`: compare `mod_revision`
to the value you read, write in the success branch, report the conflict in
the else branch. etcd's mutex is advisory only - a resource outside etcd
must be handed the revision and validate it itself (see the
[etcd page](../../cloud/etcd.md)).

### Kubernetes: resourceVersion is a fencing token

The API concepts doc defines the field as "representing the version of that
resource as stored in the underlying persistence layer," orderable as
"monotonically increasing integers within the same resource type." The gate
is optimistic concurrency: a stale resourceVersion makes "the API server
return... a 409 Conflict error response." Leader election builds on it: the
`Lease` object (coordination.k8s.io/v1) carries `holderIdentity`,
`leaseDurationSeconds`, and `renewTime`; a candidate takes over only via a
successful update against the recorded resourceVersion - a fenced CAS
executed by the API server.

### GFS and HDFS: versioned chunks and blocks

The GFS paper: "the master maintains a chunk version number to distinguish
between up-to-date and stale replicas. Whenever the master grants a new
lease on a chunk, it increases the chunk version number... The client or
the chunkserver verifies the version number when it performs the
operation." HDFS does the same for file write leases: a stalled writer's
lease is recovered by the NameNode (bounded by
`dfs.namenode.lease-hard-limit-sec`, 1200 s default), the block's
generation stamp advances, and DataNodes reject pipeline writes carrying
the old stamp. Kleppmann's motivating example - read a file, pause, write
it back - is exactly this bug shape on HDFS or S3.

### Redis: no token facility, by design

Kleppmann's Redlock critique: "it does not have any facility for generating
fencing tokens." The Redis docs now instruct: "You should implement fencing
tokens. This is especially important for processes that can take significant
time and applies to any distributed locking system" - noting Redis does not
even use a monotonic clock for TTLs. The `SET NX PX` unique value is a
release guard (do not delete someone else's lock), not a fencing token: it
has no ordering, so storage cannot compare it. Antirez's rebuttal defends
the timing model for efficiency locks; for correctness locks, take a token
from a consensus service and check it at the resource. See
[Redis advanced patterns](../../redis/advanced-patterns.md) and the
[interview walkthrough](../../interview/system-design/real-world/distributed-lock.md).

## Monotonicity Across Failover

The hardest contract point is the first: the minting counter must never go
backwards, including across the grantor's own restart:

```text
ZooKeeper:  zxid = (epoch << 32) | counter
            leader change bumps epoch; counter continues from the log
Chubby:     "a new client epoch number, which clients are required to
            present on every call. The master rejects calls from clients
            using older epoch numbers"
etcd:       one raft-ordered revision stream; a new leader cannot renumber
            history because commands apply through the log
```

If minting resets, old tokens are reissued; the storage gate below only
saves you by accident of remembering the high-water mark. Monotonic minting
needs a replicated log (ZooKeeper, etcd), an epoch-carrying failover
protocol (Chubby), or a durable counter - not an in-memory variable.

## Demo: Token Allocator and Storage Gate

```python
# MODEL: monotonic fencing-token allocator plus a storage-side gate.
# Tokens are (epoch, counter) pairs; the storage accepts a token >= the
# highest token seen, so retries succeed and regressions fail.

class Grantor:
    def __init__(self, durable):
        self.durable, self.epoch, self.counter = durable, 0, 0
    def mint(self):
        self.counter += 1
        return (self.epoch, self.counter)
    def failover(self):
        if self.durable:
            self.epoch += 1                  # zxid-style epoch bump
        else:
            self.epoch, self.counter = 0, 0  # restart loses history

class Storage:
    def __init__(self):
        self.value, self.max_seen = None, None
    def write(self, client, token, value):
        if self.max_seen is not None and token < self.max_seen:
            return f"{client} token={token} REJECTED (max_seen={self.max_seen})"
        self.value, self.max_seen = value, token
        return f"{client} token={token} accepted (value={self.value})"

for durable in (True, False):
    g, s = Grantor(durable), Storage()
    print(f"--- {'DURABLE' if durable else 'VOLATILE'} grantor "
          f"({'epoch bumps across failover' if durable else 'restart forgets the counter'})")
    t1 = g.mint()
    print(s.write("A", t1, "A1"))
    print(s.write("A", t1, "A1"))            # retry: same token, allowed
    print(s.write("B", g.mint(), "B1"))
    print(s.write("A", t1, "A1"))            # reordered duplicate: stale
    t3 = g.mint()
    print(f"A pauses (GC) holding token {t3}; wakes after B writes")
    print(s.write("B", g.mint(), "B2"))
    print(s.write("A", t3, "A2"))            # paused writer: stale
    g.failover()
    print(s.write("C", g.mint(), "C1"))      # post-failover write
    print()
```

Real output:

```text
--- DURABLE grantor (epoch bumps across failover) ---
A token=(0, 1) accepted (value=A1)
A token=(0, 1) accepted (value=A1)
B token=(0, 2) accepted (value=B1)
A token=(0, 1) REJECTED (max_seen=(0, 2))
A pauses (GC) holding token (0, 3); wakes after B writes
B token=(0, 4) accepted (value=B2)
A token=(0, 3) REJECTED (max_seen=(0, 4))
C token=(1, 5) accepted (value=C1)

--- VOLATILE grantor (restart forgets the counter) ---
A token=(0, 1) accepted (value=A1)
A token=(0, 1) accepted (value=A1)
B token=(0, 2) accepted (value=B1)
A token=(0, 1) REJECTED (max_seen=(0, 2))
A pauses (GC) holding token (0, 3); wakes after B writes
B token=(0, 4) accepted (value=B2)
A token=(0, 3) REJECTED (max_seen=(0, 4))
C token=(0, 1) REJECTED (max_seen=(0, 4))
```

The durable run rejects every regressed token and lets C continue at
(1, 5); the volatile run got *lucky* - C's reissued (0, 1) was rejected only
because this storage remembered (0, 4). That is why Kubernetes stores the
resourceVersion inside the object itself, GFS records chunk versions in
persistent state, and ZooKeeper orders the token through the same log that
orders the data.

## Client, Proxy, or Storage: Who Checks?

| Enforcement point | What it can do | What it cannot do |
| --- | --- | --- |
| Client-side | fail fast on its own stale token | stop the buggy client; it grades its own homework |
| Proxy/gateway | validate tokens for a service behind it | cover bypassing paths; survive its own restart cleanly |
| Storage-native | reject stale writes with the data's own CAS/version | nothing - this is the correct place |

Storage-native enforcement usually needs no new machinery: a conditional
update (`UPDATE ... WHERE version = ?`), an etcd `txn` compare, or a 409 on
a stale resourceVersion. Kleppmann's closing instruction: "please enforce
use of fencing tokens on all resource accesses under the lock." When the
resource cannot compare tokens at all (an append-only sink, a third-party
API), fall back to Chubby's lock-delay plus idempotency keys and admit the
guarantee is probabilistic. Fencing and idempotency compose: fencing stops
*stale* writers; idempotency keys make *retries* of a live writer harmless.
The same shape appears where participants reject old coordinator epochs in
[two-phase commit](../../dbms/transactions/two-phase-commit.md), and
[Jepsen-style testing](../testing/jepsen.md) is how fencing gaps get found.

## Failure Modes Checklist

- Equality checks (`token != expected`) instead of a stored high-water mark
  break under reordering and reject valid retries.
- Token validated at acquire time only; the delayed write bypasses it.
- Either side of the pair (minting counter, storage high-water mark) loses
  state on restart: the demo's volatile case generalizes.
- Timestamps as tokens: skew mints backwards or duplicated values.
- Trusting renewal: a renewed lease proves the renewer is alive (Chubby's
  KeepAlive renews the session, not your write's validity); the token, not
  the lease, is the write credential.
- Rejections swallowed: a fenced client must stop, re-acquire, re-read,
  redo; log-and-continue reintroduces the lost update. Read paths that skip
  the token can still observe torn decisions.

## Cross-References

- [Leases: Correctness From a Ticking Clock](../advanced/leases.md)
- [Distributed Locks and Fencing Tokens](distributed-locks.md)
- [Time and Clocks](time.md)
- [ZooKeeper](zookeeper.md)
- [Token-Based Mutual Exclusion](token-based-mutex.md) - a different "token"
- [Redis Advanced Patterns](../../redis/advanced-patterns.md)

## References

- Martin Kleppmann, "How to do distributed locking" (2016): https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html
- Mike Burrows, "The Chubby lock service for loosely-coupled distributed systems," OSDI 2006: https://research.google/pubs/pub27897/
- Apache ZooKeeper, "ZooKeeper Internals" (zxid epoch/counter layout): https://zookeeper.apache.org/doc/current/zookeeperInternals.html
- Apache ZooKeeper, "ZooKeeper Programmer's Guide" (czxid, version, sequence nodes): https://zookeeper.apache.org/doc/current/zookeeperProgrammers.html
- etcd v3.5 API reference (KeyValue revisions, response-header revision): https://etcd.io/docs/v3.5/learning/api/
- Kubernetes API Concepts (resourceVersion semantics, 409 Conflict): https://kubernetes.io/docs/reference/using-api/api-concepts/
- kube-controller-manager reference (leader-elect lease/renew defaults): https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/
- Ghemawat, Gobioff, Leung, "The Google File System," SOSP 2003: https://research.google/pubs/the-google-file-system/
- Apache Hadoop hdfs-default.xml (`dfs.namenode.lease-hard-limit-sec`): https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/hdfs-default.xml
- Redis, "Distributed locks with Redis" (fencing-token guidance): https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/
- Salvatore Sanfilippo, "Is Redlock safe?" (antirez's rebuttal): http://antirez.com/news/101
