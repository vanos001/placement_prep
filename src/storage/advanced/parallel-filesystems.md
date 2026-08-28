# Parallel Filesystems: Lustre, BeeGFS, GlusterFS, JuiceFS, GPFS

One metadata bottleneck is the whole story of parallel filesystems. A
traditional NFS server serializes metadata through one host; HPC workloads
- a million files per checkpoint, bandwidth-hungry readers on thousands of
clients - need metadata and data paths that scale independently. Every
system in this page is a different answer to the same two questions: *where
does the metadata live*, and *how do stripes of file data map to storage
servers*. Knowing the answers by heart is the fastest way to reason about
new systems too, because the design space is genuinely small.

Related pages: [ceph](./ceph.md) and [ceph-crush](./ceph-crush.md) (the
commodity-cluster design that became the default cloud-native answer),
[hdfs-internals](./hdfs-internals.md) (the big-data cousin with its own
name-node trade-offs), and [nfs](../../linux/kernel/filesystems/nfs.md)
for the protocol baseline everything here replaces.

## The architectural matrix

```text
                 METADATA MODEL
                 centralized        distributed        metadata-in-RDBMS
                 one MDS            hash/mapped MDS    over KV/SQL
                +----------------+-------------------+--------------------
   DATA PATH    |  NFS (1 host)  |  (rare)           |  JuiceFS
   striped      |  Lustre (MDT)  |  BeeGFS           |  (Redis/TiKV meta)
   across       |  GPFS (NSD)    |                   |
   servers      |                |                   |
                +----------------+-------------------+--------------------
   DATA PATH    |  GlusterFS     |  CephFS           |
   volume/      |  (translator   |  (dynamic subtree |
   brick-wide   |   stacking)    |   partitioning)   |
                +----------------+-------------------+--------------------
```

- **Lustre** - the HPC flagship. Metadata servers (MDS/MDT) hold the
  namespace; object storage servers (OSS/OST) hold stripes. Files stripe
  across OSTs (count, size, index offsets); the layout is per-file and
  DNE (Distributed Namespace Environment) shards the namespace across
  MDTs. Decades of exascale-adjacent deployments; the operational tax is
  MDT tuning and the (shrinking) single-MDT bottleneck for metadata-heavy
  trees.
- **BeeGFS** - symmetric metadata: every server runs both metadata and
  storage services, targets are auto-mirrored at file or block level.
  Metadata ops scale with node count with no dedicated MDS tier - the
  simplest answer to "small files at scale", at the cost of the
  software-defined-tiering story Lustre/GPFS tell.
- **GlusterFS** - no metadata server at all: the namespace is *computed*
  by translator modules (hash-based distribute, replicate, stripe) stacked
  on bricks. Brilliant zero-metadata design and brutal performance
  ceiling at scale: every pathname lookup requires translators to
  interpret the namespace algorithmically; the project's decline in
  large deployments traces directly to that.
- **JuiceFS** - cloud-native: metadata in a transactional KV store
  (Redis, TiKV, Postgres), data as objects in S3-compatible storage.
  POSIX-compliant via FUSE (and S3 gateway). The metadata tier is the
  consistency and performance boundary - which makes it the only system
  here whose durability model is inherited, not invented.
- **GPFS / IBM Spectrum Scale** - the commercial veteran: NSD (network
  shared disk) servers, distributed lock manager, token-based
  consistency, bit-rot scrubs. Still the default in finance and
  media/film for a reason: its metadata scaling and snapshot machinery
  are the most battle-hardened in the industry.

## Stripe mechanics: where the bandwidth comes from

A striped file layout answers three numbers: stripe count (how many
OSTs), stripe size (bytes per OST before rotation), and stripe index
(start offset). A 10 GiB read with stripe count 10 and stripe size 1 MiB
pulls 10 concurrent 1 GiB streams - aggregate bandwidth scales with
stripe count until a bottleneck (client NIC, OSS saturation, lock
round-trips) binds. Small files flip the story: a 4 KiB file occupies one
stripe on one OST, and its cost is pure metadata - which is why the
systems above differ most in their metadata tier.

## The demo: stripe placement and lock round-trips

The script below models read throughput for a striped file as a function
of file size, stripe parameters, and per-server bandwidth, then counts
lock round-trips for sequential vs random access - the two numbers that
decide "does my checkpoint finish in time".

```python
#!/usr/bin/env python3
"""Striped-file bandwidth and lock-round-trip model.

Model: n_osts object-storage targets, each capable of BW_OST MB/s;
client capped at BW_CLIENT. A file of size S with stripe size B and
stripe count C distributes ceil(S/B)/C stripes per OST.

Bandwidth: min(client cap, BW_OST * min(C, n_osts) * utilization) with
utilization degrading for tiny stripes (per-RPC overhead model).

Lock round-trips: sequential streaming needs O(1) extent locks; random
4 KiB access over N ops needs min(N, #stripes touched) lock acquisitions
per file, each costing RTT. Deterministic; no I/O performed."""

GIB = 1024  # MiB per GiB

def bandwidth(S_mib, stripe_mib, count, n_osts, bw_ost, bw_client):
    stripes = max(1, -(-S_mib // stripe_mib))
    active = min(count, n_osts, stripes)
    per_rpc_overhead = 0.10 if stripe_mib < 1 else 0.02
    util = max(0.2, 1.0 - per_rpc_overhead * (1 if stripe_mib >= 1 else 8))
    return min(bw_client, bw_ost * active * util)

def lock_rtts(n_ops, op_size, stripe_mib, count, rtt_us):
    """random ops over a striped file: one extent lock per stripe touched
    (worst case), amortized by op_size/stripe locality factor 0 otherwise"""
    stripes = max(1, -(-n_ops * op_size // stripe_mib))
    distinct = min(n_ops, stripes)
    # sequential: 1 lock; random: one per distinct stripe, pipelined partially
    return 1, distinct * rtt_us, distinct * rtt_us / 2   # seq_us, rnd_us, pipe_us

print("=== A. read bandwidth vs layout (10 GiB file, 20 OSTs, 500 MB/s each,")
print("    client 12 GB/s) ===")
S = 10 * GIB
for count, stripe in [(1, 1024), (4, 1024), (10, 1024), (20, 1024), (20, 128), (20, 16)]:
    bw = bandwidth(S, stripe, count, 20, 500, 12000)
    print(f"  stripe count={count:>2} stripe={stripe:>4} MiB -> {bw:>8.1f} MB/s "
          f"({S/1024/bw:6.2f} s per 10 GiB read)")

print()
print("=== B. lock round-trips: sequential vs random (RTT=80 us) ===")
for ops, opsz in [(100_000, 4), (1_000_000, 4)]:
    seq_us, rnd_us, rnd_pipe = lock_rtts(ops, opsz, 1024, 10, 80)
    print(f"  {ops:>9,} x {opsz} KiB random ops: {rnd_us/1e6:8.2f} s lock time "
          f"(pipelined ~{rnd_pipe/1e6:5.2f} s); sequential: {seq_us} lock")

print()
print("reading A: bandwidth scales with stripe count until the client cap -")
print("but only if the file HAS enough stripes: 1024 MiB stripes over a 10 GiB")
print("file produce 10 stripes, so half the 20-OST array idles (4900 not 9800).")
print("Sub-MiB stripes are where per-RPC overhead wrecks utilization. Reading")
print("B: metadata-op-heavy workloads are RTT-bound, not byte-bound - which")
print("is the entire architectural argument for distributed metadata tiers.")
```

```text
=== A. read bandwidth vs layout (10 GiB file, 20 OSTs, 500 MB/s each,
    client 12 GB/s) ===
  stripe count= 1 stripe=1024 MiB ->    490.0 MB/s (  0.02 s per 10 GiB read)
  stripe count= 4 stripe=1024 MiB ->   1960.0 MB/s (  0.01 s per 10 GiB read)
  stripe count=10 stripe=1024 MiB ->   4900.0 MB/s (  0.00 s per 10 GiB read)
  stripe count=20 stripe=1024 MiB ->   4900.0 MB/s (  0.00 s per 10 GiB read)
  stripe count=20 stripe= 128 MiB ->   9800.0 MB/s (  0.00 s per 10 GiB read)
  stripe count=20 stripe=  16 MiB ->   9800.0 MB/s (  0.00 s per 10 GiB read)

=== B. lock round-trips: sequential vs random (RTT=80 us) ===
    100,000 x 4 KiB random ops:     0.03 s lock time (pipelined ~ 0.02 s); sequential: 1 lock
  1,000,000 x 4 KiB random ops:     0.31 s lock time (pipelined ~ 0.16 s); sequential: 1 lock

reading A: bandwidth scales with stripe count until the client cap -
but only if the file HAS enough stripes: 1024 MiB stripes over a 10 GiB
file produce 10 stripes, so half the 20-OST array idles (4900 not 9800).
Sub-MiB stripes are where per-RPC overhead wrecks utilization. Reading
B: metadata-op-heavy workloads are RTT-bound, not byte-bound - which
is the entire architectural argument for distributed metadata tiers.
```

## Choosing, honestly

| workload                          | first choice   | why                                        |
|-----------------------------------|----------------|---------------------------------------------|
| HPC checkpoint/restart, TB-scale files | Lustre / GPFS | deep stripe tooling, decades of tuning   |
| many-small-file analytics on bare metal | BeeGFS     | symmetric metadata scales without MDT pain |
| cloud-native POSIX over object storage | JuiceFS    | durability inherited from S3/KV, cheap ops |
| legacy scale-up, petabyte NAS replacement | GPFS/Spectrum Scale | DLM maturity, snapshots, geo-DR     |
| hyperconverged storage on app hosts | GlusterFS (declining) | zero-metadata simplicity, but perf ceiling |
| cloud-native k8s workloads        | CephFS         | commodity clusters, dynamic subtrees        |

The meta-lesson for interviews: parallel filesystems differ mainly in
where they put the *consistency and naming* authority. Everything else -
striping, failover, scrubbing - is engineering around that choice.

## Interview probes

- A 1 MiB-stripe, 100-OST file is read by 50 clients concurrently: what
  limits aggregate throughput first, and which counter on the OSS proves
  it?
- Why does GlusterFS's no-metadata design hurt random small-file lookups,
  while CephFS's dynamic subtree partitioning handles them?
- JuiceFS can serve POSIX with linearizable metadata: what consistency
  guarantees does its KV backend need to provide, and what breaks if it
  lags?
- Checkpoint-restart wants maximum write bandwidth; an ML dataset loader
  wants max IOPS on millions of files. Which two systems in this page
  fit each, and which single knob differs most between the deployments?

## References

1. [GlusterFS documentation](https://gluster.readthedocs.io/en/latest/)
   - the translator/brick architecture (distribute/replicate/EC
   volumes) from the project's own docs.
2. [JuiceFS documentation](https://juicefs.com/docs/community/introduction/)
   - the metadata-engine + object-store architecture and its POSIX
   compliance notes.
3. Lustre operations manual,
   [doc.lustre.org](https://doc.lustre.org/lustre_manual.xhtml) (403s to
   scripted probes; canonical and search-verified) - MDT/OSS layout,
   DNE, and stripe parameters.
4. BeeGFS documentation,
   [docs.beegfs.io](https://docs.beegfs.io/latest/) (bot-blocked to
   scripted probes; canonical and search-verified) - the symmetric
   metadata architecture.
5. [Ceph CRUSH (this repo)](./ceph-crush.md) and
   [Ceph architecture (this repo)](./ceph.md) - the commodity-cluster
   alternative and its placement math.
