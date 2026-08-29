# GlusterFS Internals: Translators, Bricks, and the Sharding Problem

GlusterFS makes the most radical bet of any filesystem in the
[parallel filesystem survey](./parallel-filesystems.md): no metadata server at all. The
namespace is *computed*, on every client, from a hash of the pathname plus per-directory
layout metadata scattered across storage nodes. That decision explains both the best
property (no MDS to size or fail over - contrast
[Lustre internals](./lustre-internals.md)) and the worst (every namespace op is a small
distributed computation). This page goes inside the machine: the translator stack, DHT
hash-range layouts, AFR and split-brain, disperse erasure coding, and the sharding
translator. [distributed-fs.md](./distributed-fs.md) keeps the short sketch this page
replaces; [erasure-coding-deep.md](./erasure-coding-deep.md) carries the Reed-Solomon
math. All facts below were checked against docs.gluster.org and the glusterfs source
tree (fetches cited at the end, August 2026).

## Bricks and the translator stack

Three daemons make a deployment. **glusterd** runs once per node and owns cluster
membership and volume config. **glusterfsd** runs once per *brick* - a brick is just a
node plus an export directory (e.g. `node1:/data/brick1/gv0`) on a local filesystem such
as XFS. A **glusterfs** client process runs per mount, in userspace, over FUSE. Every one
of these processes executes a *graph of translators* (xlators) - objects implementing the
same file-operation interface, stacked so each can rewrite, fan out, or reject the fops
flowing through. A "volume type" is really "which cluster translators glusterd wires into
the graph":

```text
  client mount = one userspace glusterfs process per mount point
  +--------------------------------------------------+
  | FUSE kernel module  /mnt/gv0                     |
  |   |                                              |
  |   v  performance: write-behind, read-ahead,      |
  |      io-cache, quick-read                        |
  |   v  features: quota, shard, changelog           |
  |   v  cluster/replicate (AFR) or disperse (EC)    |
  |   v  cluster/distribute (DHT)                    |
  |   v  protocol/client -- RPC over TCP or RDMA     |
  +---------------------|----------------------------+
                        |  to the hashed / replicated brick
                        v
  +--------------------------------------------------+
  | glusterfsd on brick node1:/data/brick1/gv0       |
  |   protocol/server -> storage/posix (XFS)         |
  +--------------------------------------------------+
```

| Volume type | Cluster xlators | Placement rule | Usable capacity |
|---|---|---|---|
| Distribute | DHT | hash(name) range per brick | 100% |
| Replicated | AFR | identical copy on each brick of the set | 1/N |
| Distributed-Replicate | DHT above AFR | hash picks the replica set | 1/N |
| Dispersed | EC | one fragment per brick, k data + m parity | k/(k+m) |
| Distributed-Dispersed | DHT above EC | hash picks the disperse set | k/(k+m) |

Performance translators trade cache and latency behavior; cluster translators decide
*where data lives*. The rest of this page is about the cluster translators.

## DHT: the namespace is computed, not stored

The distribute translator picks a brick by hashing the entry name: `dht_hash_compute()`
calls `gf_dm_hashfn` (a Davies-Meyer hash) over the name
(`xlators/cluster/dht/src/dht-hashfn.c`). The 32-bit hash value lands in one of the
ranges partitioning the hash space, and each range belongs to one subvolume. Two
mechanisms make this viable as real metadata:

- **Layouts live on directories.** Each directory carries its layout as an array of
  (start, stop, subvolume) ranges in the `trusted.glusterfs.dht` xattr; the
  `trusted.glusterfs.dht.commithash` xattr lets clients detect stale layouts (both names
  confirmed in `xlators/cluster/dht/src/dht-common.c`).
- **Layouts can lag on purpose.** The admin guide on expansion: "Even after new bricks
  are added to the volume, newly created files in existing directories will still be
  distributed only among the original bricks" (docs.gluster.org, Managing Volumes). The
  new brick sits with a *null layout* - no hash range - and receives nothing.

| Command | What it changes | What it costs |
|---|---|---|
| `gluster volume add-brick` | new subvolume, null layout | nothing moves; brick stays idle |
| `rebalance <vol> fix-layout start` | layout xattrs rewritten, commit hash bumped | metadata rewrite across every directory |
| `rebalance <vol> start` (migrate-data) | files copied to the brick their hash now owns | bulk data movement competing with client I/O |

After fix-layout, lookups for old files whose hashes moved hit a DHT **linkto** file on
the hashed brick and get redirected; rebalance removes the hops by migrating data.
Because the hash is over the name only, uniformity is asymptotic - the demo below lands
19 of 60 files on one brick. Two caveats to memorize: renaming a file can move it between
bricks (a rename is a copy), and readdir must visit every subvolume and merge, since no
global metadata index exists.

## AFR: pending xattrs, quorum, and three kinds of self-heal

The replicate translator (AFR, automatic file replication) fans each modifying operation
out to every member of the replica set. Bookkeeping is entirely in extended attributes:
per-member pending counters in `trusted.afr.<volname>-client-<N>` (name construction in
`glusterd-volgen.c`; `afr.h` documents the format as "trusted.afr.volume = [x y z]"),
plus a dirty marker (`trusted.afr.dirty`). Pending counters encode *which* member is
behind and *what kind* of divergence exists. Reads are served from one healthy member,
preferring a colocated brick; members with pending counts are avoided until healed.

Self-heal comes in exactly three flavors - the enumeration interviewers want:
**entry** self-heal (a file exists on one member only, e.g. a create that completed on
one brick during a fault), **metadata** self-heal (attribute divergence: owner, mode,
times), and **data** self-heal (content divergence). The self-heal daemon (`glustershd`,
one process per node with its own graph) crawls and repairs continuously; a lookup on an
inconsistent file also heals on access.

**Split-brain** means two members of a set each accepted divergent writes - classically a
two-node replica volume after a partition with quorum disabled - so both carry pending
counters and neither is authoritative. Prevention beats cure: client-side quorum
(`cluster.quorum-type`), odd-member replica sets, and **arbiter volumes** (a third,
metadata-only brick that votes and tracks pending state but stores no data). The
documented cures (docs.gluster.org, resolving-splitbrain) are: select the bigger file as
source, select the latest mtime, or force a source brick:

```text
gluster volume heal <VOLNAME> split-brain latest-mtime <FILE>
gluster volume heal <VOLNAME> split-brain source-brick <HOSTNAME:BRICKNAME> <FILE>
```

The same page ships `getfattr`/`setfattr` recipes for detecting data and metadata
split-brain on a specific file.

## Disperse: erasure coding inside the translator stack

The disperse translator (`xlators/cluster/ec`) replaces replica fan-out with
Reed-Solomon coding. From the source: `ec->fragments = ec->nodes - ec->redundancy` (k
data fragments of k+m members) and `ec->stripe_size = fragment_size * fragments`, where
the coding chunk `EC_METHOD_CHUNK_SIZE = EC_METHOD_WORD_SIZE * EC_GF_BITS` is 512 bytes
(`ec-method.h`), coalesced into larger brick I/Os, with `EC_METHOD_MAX_FRAGMENTS`
bounding the set. Consequences:

- Usable capacity is k/(k+m): a 4+2 volume gives 66.7% versus 50% for 3-way replication.
- Every file, however small, is spread as k+m fragments over k+m bricks - small-file
  workloads pay the full membership tax.
- Writes are full-stripe: a partial-stripe write must read missing data fragments to
  recompute parity, then rewrite the stripe. The demo shows a 64 KiB write costing 3 MiB
  read plus 3 MiB written on a 4+2 volume modeled with 512 KiB stripe units (the stripe
  unit there is a model parameter; the 512-byte coding chunk is source-verified).

Versus replication, disperse buys capacity at the price of write amplification and slower
rebuilds (reconstruction reads k fragments). Versus arbiter volumes, it is the
data-resilient-but-expensive pole: arbiter keeps full copies plus a metadata-only voter.

## The sharding problem

Large sequential files are hostile to everything above: one huge file is one DHT object
(one brick owns it), one self-heal unit, and one unbounded copy-on-write snapshot
liability. The `features/shard` translator splits files larger than `shard-block-size`
into independent block files in a hidden `.shard` directory on each brick, keyed off the
base file's GFID. The default block size is 64 MiB - confirmed in source,
`.default_value = "64MB"` for `shard-block-size` in
`xlators/features/shard/src/shard.c` (current docs builds have no sharding page; the
source is the authority).

The trade is object count against bounded units: a 1 TiB file becomes ~16,384 shards,
each an independent unit for rebalance, self-heal, and snapshots (the documented
motivation is keeping snapshot overhead bounded - see Managing Snapshots), but also
16,384 lookup targets, a partial-shard read-modify-write penalty on appends, and
compounding with disperse (double striping). When an interviewer says "the sharding
problem", the expected answer is the triangle: snapshot cost, metadata object count, and
migration granularity all scale with block size in opposite directions; 64 MiB is the
compromise.

## Quota and geo-replication, briefly

The **quota translator** keeps per-directory size accounting in xattrs (hooks on file
ops plus a crawler) and enforces soft/hard limits in the fop path (docs: Directory
Quota). **Geo-replication** is the async master-to-slave WAN story: the changelog xlator
journals modifications in xattrs, workers consume the journal and stream deltas (rsync or
tar over SSH) to the slave volume, and checkpoints mark consistent points (docs:
Geo-Replication). Both live in the same translator stack - features compose, but they
also serialize on one fop path.

## Why GlusterFS scales metadata poorly against a dedicated MDS

Three costs are structural, not bugs. First, listings fan out: readdir must query every
subvolume and merge, with no server-side index to answer "what is in this tree". Second,
namespace surgery is client-side: renames crossing hash ranges become copy-plus-delete,
and layout healing rewrites per-directory xattrs volume-wide. Third, added capacity does
not help existing trees until fix-layout and rebalance touch every directory. Lustre puts
the namespace on dedicated MDTs with server-side indexes (sharded by DNE); CephFS
partitions subtrees dynamically; GlusterFS computes placement instead of storing it -
winning on infrastructure simplicity, losing on metadata-heavy workloads (millions of
small files, deep trees, churn). That trade-off is why large HPC sites stayed with
Lustre-class designs.

## Status check (August 2026)

Red Hat ended the commercial product: Red Hat Gluster Storage 3.5 was the final release,
and the Red Hat life-cycle page states the product "has a defined support lifecycle
through to 31-Dec-24, after which the Red Hat Gluster Storage product will have reached
its EOL" (access.redhat.com, quoted from the page fetched for this write-up; Wikipedia
dates the 2022 announcement that 3.5 would be last). Upstream continues as a community
project: the newest tag on github.com/gluster/glusterfs/releases was **v11.2,
2025-07-02** at the August 2026 fetch, and issue #4298 ("Is the project still alive?",
January 2024) records maintainers confirming community development continues after the
Red Hat withdrawal. Hedge before quoting: release cadence has slowed markedly and
long-term stewardship is an open question worth re-verifying.

## Worked demo: DHT layout math and disperse write amplification

The simulator substitutes `zlib.crc32` for `gf_dm_hashfn` (any fixed 32-bit hash
reproduces the placement mechanics), models the documented add-brick / fix-layout /
rebalance sequence, then the disperse full-stripe write model:

```python
#!/usr/bin/env python3
# DHT hash-range simulator + disperse write-amplification model.
# Real DHT hashes names with gf_dm_hashfn (Davies-Meyer; dht-hashfn.c);
# crc32 stands in -- any fixed 32-bit hash gives the same mechanics.
import zlib

SPACE = 1 << 32
K, M, UNIT = 4, 2, 512 * 1024      # disperse model: k data, m parity, stripe unit


class Layout:
    def __init__(self, bricks, commit):
        w = SPACE // bricks
        self.commit, self.ranges = commit, []
        for i in range(bricks):
            start = i * w
            stop = SPACE - 1 if i == bricks - 1 else start + w - 1
            self.ranges.append((start, stop, "brick-%d" % i))

    def target(self, name):
        h = zlib.crc32(name.encode())
        return next(b for s, e, b in self.ranges if s <= h <= e)


def dump(l, title):
    print(title)
    for s, e, b in l.ranges:
        print("  %-8s [%08x-%08x] width=%5.1f%%" % (b, s, e, 100 * (e - s + 1) / SPACE))


old = ["file-%03d" % i for i in range(1, 49)]
new = ["file-%03d" % i for i in range(49, 61)]

v1 = Layout(4, 0x00000001)
dump(v1, "layout v1 (commit=0x00000001): 4 bricks, equal 32-bit ranges")
p_old = {f: v1.target(f) for f in old}
p_new = {f: v1.target(f) for f in new}
per = {}
for b in list(p_old.values()) + list(p_new.values()):
    per[b] = per.get(b, 0) + 1
print("  files per brick after create: %s" % dict(sorted(per.items())))
print()
print("phase 1: add-brick; new brick-4 gets a null layout (no hash range)")
print("  new files in existing dirs still spread over the ORIGINAL")
print("  bricks -> %d of 12 land on brick-4" % sum(1 for b in p_new.values() if b == "brick-4"))
print()
v2 = Layout(5, 0x00000002)
dump(v2, "phase 2: fix-layout (commit bumped to 0x00000002):")
t_old = {f: v2.target(f) for f in old}
t_new = {f: v2.target(f) for f in new}
skew = [f for f in old if p_old[f] != t_old[f]]
print("  %d of 12 new files now land on brick-4" % sum(1 for b in t_new.values() if b == "brick-4"))
print("  fix-layout alone: %d of %d old files sit behind linkto hops;"
      % (len(skew), len(old)))
print("  rebalance (migrate-data) moves %d, leaving %d untouched"
      % (len(skew), len(old) - len(skew)))
print()
frags = K + M
print("disperse: k=%d + m=%d, unit %d KiB, capacity %.1f%%, full-stripe amp %.2fx;"
      % (K, M, UNIT // 1024, 100 * K / frags, frags / K))
print("every file, however small, is %d fragments on %d bricks" % (frags, frags))
print()
print("  write KiB  stripes  read KiB  written KiB   amp")
for wkb in (64, 512, 1024, 4096):
    W = wkb * 1024
    d = -(-W // UNIT)               # data units touched (unit-aligned write)
    s = -(-d // K)                  # stripes touched
    rd = (s * K - d) * UNIT         # missing data units read back for parity
    wr = s * frags * UNIT           # every touched stripe rewritten whole
    print("  %9d  %7d  %8d  %11d  %4.2fx" % (wkb, s, rd // 1024, wr // 1024, wr / W))
```

Output (executed verbatim):

```text
layout v1 (commit=0x00000001): 4 bricks, equal 32-bit ranges
  brick-0  [00000000-3fffffff] width= 25.0%
  brick-1  [40000000-7fffffff] width= 25.0%
  brick-2  [80000000-bfffffff] width= 25.0%
  brick-3  [c0000000-ffffffff] width= 25.0%
  files per brick after create: {'brick-0': 12, 'brick-1': 12, 'brick-2': 19, 'brick-3': 17}

phase 1: add-brick; new brick-4 gets a null layout (no hash range)
  new files in existing dirs still spread over the ORIGINAL
  bricks -> 0 of 12 land on brick-4

phase 2: fix-layout (commit bumped to 0x00000002):
  brick-0  [00000000-33333332] width= 20.0%
  brick-1  [33333333-66666665] width= 20.0%
  brick-2  [66666666-99999998] width= 20.0%
  brick-3  [99999999-cccccccb] width= 20.0%
  brick-4  [cccccccc-ffffffff] width= 20.0%
  1 of 12 new files now land on brick-4
  fix-layout alone: 27 of 48 old files sit behind linkto hops;
  rebalance (migrate-data) moves 27, leaving 21 untouched

disperse: k=4 + m=2, unit 512 KiB, capacity 66.7%, full-stripe amp 1.50x;
every file, however small, is 6 fragments on 6 bricks

  write KiB  stripes  read KiB  written KiB   amp
         64        1      1536         3072  48.00x
        512        1      1536         3072  6.00x
       1024        1      1024         3072  3.00x
       4096        2         0         6144  1.50x
```

Read the demo like an interviewer: the 19-on-brick-2 skew shows name-hash unevenness on
small populations; the null-layout phase reproduces the documented "new files still land
on the original bricks" behavior; fix-layout strands 27 of 48 old files behind linkto
hops until rebalance; and the disperse table is the argument that disperse wants large,
stripe-aligned writes, not 64 KiB random ones.

## Interview quick hits

- Brick = node + export directory + one glusterfsd; glusterd compiles each process's
  translator graph.
- DHT hashes the *name* (Davies-Meyer, 32-bit space); ranges stored per directory in
  `trusted.glusterfs.dht`; commit hash invalidates stale layouts; add-brick means
  fix-layout, then rebalance.
- AFR pending counters: `trusted.afr.<vol>-client-<N>`; self-heal flavors: entry,
  metadata, data; daemon: `glustershd`.
- Split-brain prevention: quorum, odd replicas, arbiter. Cures: bigger-file,
  latest-mtime, source-brick policies.
- Disperse: k data + m parity, capacity k/(k+m), full-stripe writes, RMW penalty on
  partial stripes, every file spans k+m bricks.
- Sharding default block size 64 MiB; object count vs snapshot cost vs migration
  granularity scale in opposite directions.

## References

1. GlusterFS docs, Quick Start Guide: Architecture - https://docs.gluster.org/en/latest/Quick-Start-Guide/Architecture/
2. GlusterFS docs, Administrator Guide: Automatic File Replication (AFR) - https://docs.gluster.org/en/latest/Administrator-Guide/Automatic-File-Replication/
3. GlusterFS docs, Troubleshooting: Resolving split-brain (heal CLI verified) - https://docs.gluster.org/en/latest/Troubleshooting/resolving-splitbrain/
4. GlusterFS docs, Administrator Guide: Managing Volumes (add-brick / fix-layout / rebalance, quoted) - https://docs.gluster.org/en/latest/Administrator-Guide/Managing-Volumes/
5. GlusterFS docs, Directory Quota (https://docs.gluster.org/en/latest/Administrator-Guide/Directory-Quota/) and Geo-Replication (https://docs.gluster.org/en/latest/Administrator-Guide/Geo-Replication/)
6. glusterfs source (devel branch; raw files fetched): xlators/cluster/dht/src (dht-hashfn.c, dht-layout.c, dht-common.c), xlators/features/shard/src/shard.c, xlators/cluster/ec/src (ec.c, ec-method.h), xlators/mgmt/glusterd/src/glusterd-volgen.c - https://github.com/gluster/glusterfs/tree/devel/xlators
7. GlusterFS releases page (newest tag v11.2, 2025-07-02, observed Aug 2026) - https://github.com/gluster/glusterfs/releases
8. Red Hat Gluster Storage life cycle page (EOL 31-Dec-24, quoted) - https://access.redhat.com/support/policy/updates/rhs
9. glusterfs issue #4298, "Is the project still alive?" (Jan 2024) - https://github.com/gluster/glusterfs/issues/4298
