# BeeGFS Internals: Metadata Targets, Storage Targets, and the BeeGFS Protocol

The [parallel filesystems survey](./parallel-filesystems.md) compares BeeGFS with Lustre,
GlusterFS, JuiceFS, and GPFS, and [lustre-internals.md](./lustre-internals.md) walks the Lustre
equivalents. BeeGFS (formerly FhGFS, built at Fraunhofer ITWM and commercialized by the
late-2013 spin-off ThinkParQ) earns its own page because it answers the metadata bottleneck
differently than Lustre: instead of growing dedicated MDT servers, it lets every server host
the same services and pushes target selection into a free-space-aware chooser. Questions about
BeeGFS are almost always contrast questions, so this page keeps pointing back at the Lustre
twin. ([distributed-fs.md](./distributed-fs.md) keeps a shorter sketch;
[../../hpc/hpc-infra.md](../../hpc/hpc-infra.md) covers why such filesystems exist at all:
coordinated checkpoint/restart.)

## Four services, one kernel client

BeeGFS is user-space server daemons plus one in-kernel client. All three server daemons can
share a host (a "converged setup"), and each can run several instances per node ("Multi Mode").

| Service | Daemon | What it holds | HA unit |
|---------|--------|---------------|---------|
| Management | beegfs-mgmtd | Registry and watchdog for all nodes; never in the file-op path | Whole node |
| Metadata | beegfs-meta | The namespace: dentry/inode trees, stripe patterns, sessions | Whole metadata daemon |
| Storage | beegfs-storage | Chunk files of user data on storage targets | Target pair (buddy group) |
| Client | beegfs-client | Kernel module exposing a mount point; no FUSE, no patches | n/a |
| Monitoring | beegfs-mon | Optional; feeds InfluxDB/Grafana with performance data | n/a |

The asymmetry in that table is the headline fact: **storage nodes manage multiple storage
targets; metadata nodes do not have targets at all.** The mirroring documentation states that
"there are no metadata targets in BeeGFS" - metadata replication pairs whole daemons, which is
why metadata buddy mirroring needs an even number of metadata servers, while storage buddy
groups are built from individual targets (two targets on one server may even mirror each
other). The page title's "metadata targets" is colloquial shorthand; in interviews say
"metadata servers" when you mean the HA unit.

The management service deserves precision: it "serves as registry and watchdog", "essential for
the operation of the system, but ... not directly involved in file operations and thus not
critical for performance". Consequence: file operations survive mgmtd dying, but no buddy-group
failover can happen while it is down, so the docs recommend running mgmtd on a separate machine.
Each daemon also runs a UDP DatagramListener (64 KiB buffers in the client source) carrying
registration and heartbeat datagrams - that is the watchdog traffic.

## The request path

```text
       application on client (kernel module, e.g. mounted at /mnt/beegfs)
                        |
                        | 1. LookupIntentMsg: lookup | create | open | stat
                        |    combined into ONE round trip to metadata
                        v
            +-----------------------+
            | meta service          |  primary of the file's meta buddy group
            | dentries/, inodes/    |
            +-----------------------+
                        |
                        | 2. reply: stripe pattern, target IDs, chunk offsets
                        |    (target set was fixed at file creation)
          3. client talks to storage targets DIRECTLY, in parallel
                        |
      +-----------------+------------------+
      v                 v                  v
 target 101 @       target 201 @      target 301 @
 node_storage_1     node_storage_2    node_storage_3
 chunk files        chunk files       chunk files
      |
      +-- mirrored pattern only: primary synchronously forwards
          every chunk to its buddy secondary (buddymir/)

 mgmtd: registration/watchdog only - no file operation touches it
```

The open-path message name is real and instructive: `LookupIntentMsg` in the public source
defines intent flags REVALIDATE, CREATE, CREATEEXCLUSIVE, OPEN, and STAT, so create-plus-open is
one metadata RPC instead of four. The message also carries quota info, buddy-mirror flags, an
optional file-event record, and - on create - a `preferredTargets` list, which is how client
preferences reach the metadata server that fixes the stripe set. Data then flows as
`WriteLocalFileMsg` (or `WriteLocalFileRDMAMsg` on RDMA) straight between client and storage:
the same "metadata once, data everywhere" shape as Lustre's MDS/OST split.

## On-disk layout: metadata trees and chunk files

Metadata servers store two trees, `dentries/` and `inodes/` (mirrored copies under
`buddymir/dentries` and `buddymir/inodes`). Unless a file has multiple hard links its inode is
inlined into the dentry (`Inlined inode: yes` in the tools' output). Entries carry an entry ID
such as `1-6705972F-1`, and metadata is located by entry ID, not path, so renames never touch
chunk files.

A stripe pattern has exactly two knobs - number of storage targets and chunk size - set per
directory, inherited by new subdirectories, applied to files created inside; existing files keep
their pattern until migrated. In BeeGFS 8 the tool is `beegfs` (7.x used `beegfs-ctl`):

```text
beegfs entry info /mnt/beegfs/            # RAID0 (4x1M), storage pool 1
beegfs entry set --num-targets=4 --chunk-size=4MiB /mnt/beegfs/
beegfs entry set --num-targets=4 --chunk-size=1MiB --pattern=mirrored /mnt/beegfs/
```

Chunk files land under a `chunks/` tree on each target, fanned through two 128-entry
subdirectory levels (`CONFIG_CHUNK_LEVEL1_SUBDIR_NUM/2` in the source), a user-prefix directory,
the parent directory name, then the entry ID as file name:

```text
target root (/beegfs/storage on every storage node)
+-- chunks/
|   +-- u0/                     <- "u" + user-number prefix directory
|       +-- <fanout 0..127>/
|           +-- <fanout 0..127>/
|               +-- root/       <- parent directory name
|                   +-- 1-6705972F-1   <- entry ID = chunk file; the relative
+-- buddymir/                            chunk path is IDENTICAL on every
   (mirrored chunk copies)               striped target of that file
```

The deep-inspection documentation shows a real example: a file striped across targets
`101 @ node_storage_1` and `201 @ node_storage_2` keeps its chunks at
`/beegfs/storage/chunks/u0/0/r/root/1-6705972F-1` on both. Because chunk paths hang off entry
IDs, locating every chunk of a lost file is a reverse lookup - exactly what `beegfs entry info
--verbose --retro` and the deep-inspection recipe do.

## Free-space-aware targeting: capacity pools and storage pools

BeeGFS fixes a file's stripe target set at creation time, and the picker is free-space aware.
Targets are auto-bucketed into three capacity pools - Normal, Low, Emergency - with identical,
mgmtd-configured thresholds; the chooser prefers Normal-pool targets and falls back to Low or
Emergency only when the requested striping cannot be satisfied otherwise. On top of that,
storage pools group targets (and buddy groups) into classes - an SSD "fast" pool, a spinning
"bulk" pool - placeable per file or per directory, orthogonal to the tree structure.

If you expected an "affinity files" feature here: current BeeGFS documentation has no such page.
The real affinity levers are (a) storage pools, (b) capacity pools, and (c) the client options
`tunePreferredMetaFile` / `tunePreferredStorageFile`, which literally read a file listing
preferred servers (network-topology awareness); they only affect placement of new files. Flag
any "BeeGFS affinity files" claim as outdated terminology.

## Buddy mirroring

- A buddy group is a pair of targets (storage) or a pair of servers (metadata) with a primary
  and a secondary. Modifying operations always go to the primary first; it forwards.
- Mirroring is synchronous: the client operation completes only after both copies transferred -
  writes pay the amplification quantified in the demo below.
- Failover marks the primary offline and promotes the secondary after a deliberate delay,
  transparent to running applications - and it requires mgmtd to be alive.
- Mirroring is opt-in per file/dir (`--pattern=mirrored`, back to `raid0`), so both halves of a
  group can still hold unmirrored data alongside mirrored subsets.
- The docs warn bluntly: mirroring is not a backup - deleted files stay deleted.

## The protocol: messages, sockets, workers

Server daemons are ordinary user-space processes; the client is a Linux kernel module compiled
against your kernel. The wire protocol is a hierarchy of `NetMessage` classes serialized by a
dedicated toolkit (`common/toolkit/serialization` in the 8.x sources; before 8, releases were
squashed snapshots of a private repo, per the GitHub README). Verified families:
`LookupIntentMsg` + `MkDirMsg` (metadata), `WriteLocalFileMsg`/`WriteLocalFileRDMAMsg` (data),
`FLockEntryMsg`/`FLockRangeMsg` (flock/POSIX locks), and control messages `AuthenticateChannelMsg`,
`PeerInfoMsg`, `AckMsg`, `GenericResponseMsg`; connection authentication keys off a
`connAuthFile` shared secret. Discovery and heartbeats ride the UDP path; client sessions (the
"Client Sessions: Reading/Writing" fields in entry-info output) are why metadata nodes keep
state.

Transports are pluggable socket classes: `StandardSocket` (TCP) and `RDMASocket`, built on the
OpenFabrics ibverbs API for InfiniBand, RoCE, and Omni-Path. RDMA is on by default in the 8.x
client; servers need the `libbeegfs-ib` package; RDMA interfaces must still carry IP addresses
because connection initiation is IP-based. One correction for buzzword bingo: neither "buffer
messenger" nor "ring buffer" appears as a subsystem name in the current docs or public code - the
real model is a pool of parallel connections with pre-sized buffers feeding worker threads (the
client's `components/worker`, e.g. `RWPagesWork`, plus `Flusher`, `AckManager`, `InvalReader`,
`InternodeSyncer`, `DatagramListener`). That model is where the tuning questions live:

| Option | Effect | Docs guidance |
|--------|--------|---------------|
| connMaxInternodeNum | Parallel connections from one client to one server | About CPU-core count on compute nodes; watch server-side buffer RAM |
| connRDMABufSize x connRDMABufNum | RDMA buffer space per connection | Defaults 8192 x 70; buffer size a multiple of 4 KiB |
| chunk size vs buffers | Avoid splitting messages | Total buffer space >= chunk size; connRDMABufNum >= (chunkSize / connRDMABufSize) + 4 |
| tuneFileCacheBufSize | Client buffered-cache accumulation buffer | 512 KiB default; set to a multiple of the chunk size |
| tuneRemoteFSync | fsync() semantics | false = transfer to server cache only, cheaper for fsync-heavy apps |

The chunk size doubles as the maximum protocol message size, so a 1 MiB chunk makes 1 MiB the
largest single write message - the docs' own example computes `connRDMABufNum = (1048576 /
65536) + 4 = 20` to carry it unsplit.

## Quota

Quota covers two dimensions per user or group: used disk space and number of chunk files (a
striped file counts once per chunk). Tracking and enforcement are separate features; enforcement
works by mgmtd periodically collecting quota reports from all storage targets - which read the
quota facilities of the underlying local filesystem, so capabilities vary (old ZFS yields
space-only, ZFS >= 0.7.4 adds file counts). Limits are configured per storage pool, and exceeded
limits block writes until space is freed. In the BeeGFS 8 licensing model quotas are an
enterprise feature, which surprises people who met them on 7.x.

## BeeOND versus system services

BeeOND ("BeeGFS On Demand", pronounced "beyond") starts a throwaway BeeGFS instance across the
compute nodes of one job - typically aggregating internal SSDs as a burst buffer - with one
command start/stop designed for Slurm or Torque prologue/epilogue scripts, plus a parallel copy
tool for staging. It is the same daemons underneath, lifecycle-managed per job. Persistent
clusters instead run systemd services (`beegfs-mgmtd`, `beegfs-meta`, `beegfs-storage`,
`beegfs-client`); in 8.x their configuration moved to TOML files such as
`/etc/beegfs/beegfs-mgmtd.toml`, where `registration-disable` gates adding new targets.
Interview contrast: BeeOND optimizes for isolation and burst performance (job-local namespace),
system services for shared state and HA (buddy groups, quotas, monitoring).

## Naming and licensing, verified (August 2026)

| Era | Source model | Gated features |
|-----|--------------|----------------|
| FhGFS (Fraunhofer ITWM) | In-house research code; spun off late 2013/2014 as ThinkParQ; renamed BeeGFS in 2014 | none |
| BeeGFS 7.x | "Available Source" (public source, BeeGFS EULA; client module GPLv2); Community vs Enterprise editions | support, tooling |
| BeeGFS 8.x (current 8.4.0) | Same available-source repo plus a license-key system: "non-obtrusive with no remote verification or telemetry" | storage pools and quotas are enterprise-licensed; machine-count cap |

Corrections worth stating in an interview: calling BeeGFS "open source" is imprecise - the
license page says "Available Source development model" under a EULA, with only the client module
GPLv2. Version 8.2 (announced January 8, 2025) added full IPv6 support; the 8.4 release added
automatic file-change sync and stub-file restore via Remote Storage Targets. Documentation lives
at doc.beegfs.io (singular); the older `docs.beegfs.io` spelling does not resolve.

## Worked model: chunk placement, imbalance, and mirror amplification

```python
#!/usr/bin/env python3
"""BeeGFS-style chunk placement model (pure stdlib).

RAID0 striping: chunk i of a file lands on target (i % num_targets). A
free-space-aware chooser (capacity pools) picks each new file's stripe
target set weighted by target free space. Mirrored patterns double fabric
bytes: the primary synchronously forwards every chunk to its secondary.
"""
import math
import random

KiB, MiB, GiB, TiB = 1024, 1024**2, 1024**3, 1024**4


def chunk_layout(file_bytes, chunk_size, num_targets):
    """Return (n_chunks, chunks_per_target) for a RAID0 stripe pattern."""
    n_chunks = math.ceil(file_bytes / chunk_size)
    base, rem = divmod(n_chunks, num_targets)
    return n_chunks, [base + 1 if t < rem else base for t in range(num_targets)]


def pick_stripe_set(rng, free, k):
    """Draw k distinct targets, probability weighted by free space (the
    capacity-pool chooser stand-in)."""
    pool, weights, chosen = list(range(len(free))), list(free), []
    for _ in range(k):
        i = rng.choices(range(len(pool)), weights=weights)[0]
        chosen.append(pool.pop(i)); weights.pop(i)
    return chosen


def chooser_sim(free, n_files, stripe_targets, chunks_per_file, seed):
    """Per-target chunk counts: capacity-aware vs uniform stripe sets."""
    rng, n = random.Random(seed), len(free)
    aware, uniform = [0] * n, [0] * n
    for _ in range(n_files):
        for counts, weighted in ((aware, True), (uniform, False)):
            targets = (pick_stripe_set(rng, free, stripe_targets) if weighted
                       else rng.sample(range(n), stripe_targets))
            for c in range(chunks_per_file):
                counts[targets[c % stripe_targets]] += 1
    return aware, uniform


def fabric_bytes(file_bytes, chunk_size, mirrored):
    """Fabric bytes per write: mirrored sends every chunk twice (primary
    ingress + forwarding egress); primary NIC load is 1x vs 2x."""
    n_chunks = math.ceil(file_bytes / chunk_size)
    return min(file_bytes, n_chunks * chunk_size) * (2 if mirrored else 1)


def main():
    print("== Scenario table: RAID0 chunk layout ==")
    print(f"{'file':>9} {'chunk':>7} {'tgts':>4} {'chunks':>6}  chunks per target (max-min delta)")
    for size, chunk, nt in [(10 * MiB, 512 * KiB, 4), (10 * MiB, 1 * MiB, 4),
                            (1 * GiB, 1 * MiB, 8), (5 * GiB, 4 * MiB, 4),
                            (7 * MiB, 2 * MiB, 3)]:
        n_chunks, per = chunk_layout(size, chunk, nt)
        print(f"{size // MiB:>7}MiB {chunk // KiB:>5}KiB {nt:>4} {n_chunks:>6}  "
              f"{'/'.join(str(p) for p in per)} (delta {max(per) - min(per)})")
    print()
    print("== Stripe-set choice: 12 targets, 2000 files x 8 chunks, stripe 4 ==")
    free = [60 * TiB, 25 * TiB, 15 * TiB, 8 * TiB, 5 * TiB, 4 * TiB,
            3 * TiB, 2 * TiB, 2 * TiB, 1 * TiB, 1 * TiB, 1 * TiB]
    aware, uniform = chooser_sim(free, 2000, 4, 8, seed=49)
    total = sum(aware)
    print(f"{'tgt':>3} {'free %':>7} {'aware %':>8} {'uniform %':>10}   overfill vs capacity (pp)")
    for t in sorted(range(len(free)), key=lambda i: -free[i]):
        a, u = 100.0 * aware[t] / total, 100.0 * uniform[t] / total
        s = 100.0 * free[t] / sum(free)
        print(f"{t:>3} {s:>7.2f} {a:>8.2f} {u:>10.2f}   "
              f"aware {a - s:+6.2f}  uniform {u - s:+6.2f}")
    print()
    print("== Buddy-mirroring write amplification (per 1 GiB file, 1 MiB chunks) ==")
    for mirrored in (False, True):
        fb = fabric_bytes(1 * GiB, 1 * MiB, mirrored)
        tail = (" -> primary target NIC load 2.0x (1.0 GiB in + 1.0 GiB out)"
                if mirrored else " -> primary target NIC load 1.0x (1.0 GiB in)")
        print(f"mirrored={mirrored!s:<5} fabric={fb / GiB:.1f} GiB{tail}")


if __name__ == "__main__":
    main()
```

Output (executed; the model is a stylized stand-in for the documented chooser, not its code):

```text
== Scenario table: RAID0 chunk layout ==
     file   chunk tgts chunks  chunks per target (max-min delta)
     10MiB   512KiB    4     20  5/5/5/5 (delta 0)
     10MiB  1024KiB    4     10  3/3/2/2 (delta 1)
   1024MiB  1024KiB    8   1024  128/128/128/128/128/128/128/128 (delta 0)
   5120MiB  4096KiB    4   1280  320/320/320/320 (delta 0)
      7MiB  2048KiB    3      4  2/1/1 (delta 1)

== Stripe-set choice: 12 targets, 2000 files x 8 chunks, stripe 4 ==
tgt  free %  aware %  uniform %   overfill vs capacity (pp)
  0   47.24    24.09       8.61   aware -23.16  uniform -38.63
  1   19.69    20.62       8.24   aware  +0.94  uniform -11.45
  2   11.81    16.34       8.26   aware  +4.53  uniform  -3.55
  3    6.30    11.05       8.28   aware  +4.75  uniform  +1.98
  4    3.94     7.04       8.32   aware  +3.10  uniform  +4.39
  5    3.15     5.85       8.10   aware  +2.70  uniform  +4.95
  6    2.36     4.21       8.44   aware  +1.85  uniform  +6.08
  7    1.57     2.98       8.14   aware  +1.40  uniform  +6.56
  8    1.57     2.99       8.49   aware  +1.41  uniform  +6.91
  9    0.79     1.64       8.18   aware  +0.85  uniform  +7.39
 10    0.79     1.74       8.72   aware  +0.95  uniform  +7.94
 11    0.79     1.46       8.22   aware  +0.68  uniform  +7.44

== Buddy-mirroring write amplification (per 1 GiB file, 1 MiB chunks) ==
mirrored=False fabric=1.0 GiB -> primary target NIC load 1.0x (1.0 GiB in)
mirrored=True  fabric=2.0 GiB -> primary target NIC load 2.0x (1.0 GiB in + 1.0 GiB out)
```

How to read it. With stripe 4 over only 4 targets, round-robin equalizes chunk counts no matter
how the chooser weighs free space - the scenario table's delta is 0 whenever the chunk count is
a multiple of the target count. Real clusters have far more targets than the stripe count, and
there the chooser matters: with 12 targets and stripe 4, the free-space-weighted chooser puts
1.46-1.74 percent of chunks on the 0.79-percent-free targets versus 8.2-8.7 percent under
uniform choice - a fivefold overfill. Weighting alone still underfills the biggest target
(-23.16pp), which is exactly why BeeGFS layers hard capacity-pool thresholds on top of
free-space preference. Mirroring doubles fabric bytes per write and puts twice the NIC load on
primaries (ingress plus forwarding egress) - the tax accepted for transparent failover.

## References

1. BeeGFS 8.4 documentation - Architecture (services, converged setups, capacity pools,
   mirroring): <https://doc.beegfs.io/latest/architecture/overview.html> (probed 200)
2. BeeGFS 8.4 - Striping (patterns, mirrored mode, chunk-size/message coupling):
   <https://doc.beegfs.io/latest/advanced_topics/striping.html> (probed 200)
3. BeeGFS 8.4 - Client Node Tuning (connMaxInternodeNum, connRDMABufSize/Num rule of thumb):
   <https://doc.beegfs.io/latest/advanced_topics/client_tuning.html> (probed 200)
4. BeeGFS 8.4 - RDMA Support (ibverbs/OFED, InfiniBand/RoCE/Omni-Path, libbeegfs-ib):
   <https://doc.beegfs.io/latest/advanced_topics/rdma_support.html> (probed 200)
5. BeeGFS 8.4 - Deep Inspection (chunk paths, dentries/inodes, buddymir layout):
   <https://doc.beegfs.io/latest/advanced_topics/deep_inspection.html> (probed 200)
6. BeeGFS 8.4 - Quota (tracking vs enforcement, chunk-file counts, per-pool limits):
   <https://doc.beegfs.io/latest/advanced_topics/quota.html> (probed 200)
7. BeeGFS 8.4 - Licensing and 7.4.7 License (Available Source, EULA, client GPLv2):
   <https://doc.beegfs.io/latest/advanced_topics/licensing.html>,
   <https://doc.beegfs.io/7.4.7/license.html> (both probed 200)
8. BeeGFS 8.4 - BeeOND: BeeGFS On Demand:
   <https://doc.beegfs.io/latest/advanced_topics/beeond.html> (probed 200)
9. ThinkParQ/beegfs public repository (message and socket classes cited in text):
   <https://github.com/ThinkParQ/beegfs> (probed 200)
10. ThinkParQ press release, BeeGFS 8.2 with full IPv6 support, January 8, 2025:
    <https://thinkparq.com/2025/01/08/beegfs8-2> (probed 200)
11. F.-J. Pfreundt et al., "A parallel file system - made in Germany", MSST 2012 (FhGFS design
    goals: distributed metadata, no kernel patches, native IB and Ethernet):
    <https://msstconference.org/MSST-history/2012/Presentations/M08.Pfreundt.pdf> (probed 200)
12. ThinkParQ whitepaper, "Picking the right number of targets per server for BeeGFS":
    <https://www.beegfs.io/docs/whitepapers/Picking_the_right_Number_of_Targets_per_Server_for_BeeGFS_by_ThinkParQ.pdf>
    (probed 200); BeeGFS EULA: <https://www.beegfs.io/docs/BeeGFS_EULA.txt> (probed 200)
13. NetApp, "BeeGFS for Beginners" (403 to scripted probes; existence search-verified):
    <https://www.netapp.com/blog/beegfs-for-beginners>
