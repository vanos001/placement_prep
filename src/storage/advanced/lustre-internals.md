# Lustre Internals: MDS, OSTs, and the Lustre Networking Layer

The [parallel filesystems survey](./parallel-filesystems.md) compares Lustre against BeeGFS,
GlusterFS, JuiceFS, and GPFS; [distributed-fs.md](./distributed-fs.md) keeps a shorter Lustre
sketch. Both stop where this page starts: at the level where an interviewer asks *which node
owns which structure, and what travels over which RPC*. Lustre splits into three planes -
metadata (MGS, MDTs), data (OSSs, OSTs), and the LNet network layer that carries both - held
together by FIDs, layout EAs, and a distributed lock manager. [HDFS
internals](./hdfs-internals.md) is the closest analog in this repo (a metadata tier that never
touches the data path); [hpc/README.md](../../hpc/README.md) gives the cluster context. Facts
are quoted or paraphrased from the Lustre Operations Manual (doc.lustre.org, fetched in full
for this page) and wiki.lustre.org; chapters are cited inline, and tags like "L 2.10" are the
manual's own "introduced in Lustre 2.10" markers.

## The request path: three planes, one mount

```text
  client node           metadata plane               data plane
  -----------------     -----------------------      --------------------
  app -> VFS -> llite    MGS (Management Service:
             |            startup/config logs)
             v           +----------------+
          LMV            | MDT0000 (MDT0) | FS root + quota tables
          |  \_pick MDT  +----------------+
          |              | MDT1 .. MDTn   | DNE secondary MDTs
          | LDLM intent  +----------------+
          | RPC open/unlink
          v
  MDT answers: attrs + layout EA (per-stripe OST object FIDs)
          |
          v
          LOV -- bulk data RPCs per stripe --> OSS nodes -> OST0..OSTn
                 over LNet; the MDS is not    (ldiskfs or ZFS objects)
                 in the data path
```

1. **The MDS never appears in the data path.** The open RPC returns a layout EA whose entries
   are OST object FIDs (manual ch. 1, figures "Layout EA on MDT" and "Lustre client requesting
   file data"); after that the client speaks bulk data RPC directly to OSS nodes.
2. **The MGS is not the MDS.** Glossary: the MGS "manages the startup configuration and
   changes to the configuration"; nodes read config logs from it at mount. MDS/MDT owns the
   namespace; MGS is how everyone learns the cluster shape.
3. **Locks ride with the targets.** Glossary: a lock server is "a service that is co-located
   with a storage target that manages locks on certain objects." Every MDT and OST manages
   locks for the objects it owns - no separate lock server node to fail.

## FIDs and the two metadata layers (LOV, LMV)

Every file, directory, and OST object is named by a **FID**, which the manual defines as a
128-bit identifier: a 64-bit sequence number (SEQ), a 32-bit object ID (OID), and a 32-bit
version. Clients get synthesized 64-bit inodes for POSIX compatibility, but 128-bit FIDs
cannot be uniquely mapped into 32-bit inodes. `lfs getdirstripe` shows the raw form:
`FID[seq:oid:ver] 0 [0x200000400:0x2:0x0]`. The two "logical volume" modules are the plumbing
- memorize **LOV : OSTs :: LMV : MDTs**:

| Layer | Glossary definition (abridged) | Abstracts |
|-------|-------------------------------|-----------|
| LOV | Logical Object Volume; "presents a collection of OSTs as a single device to the MDT and client file system drivers" | file -> OST objects via the layout EA |
| LMV | Logical Metadata Volume; a DNE client-side device that "forwards requests to the correct MDT based on name or directory striping information and merges replies" | namespace across MDT0 + secondaries |

## MDT0, DNE, and directory placement

The manual is blunt: "MDT0000 contains the root of the Lustre file system. If MDT0000 is
unavailable for any reason, the file system cannot be used" (the glossary adds quota tables
to its duties). DNE (Distributed Namespace Environment) is "a collection of metadata targets
serving a single file system namespace," in two forms - so metadata-heavy workloads hurt in
MDT tuning, not OST tuning:

- **Remote directories (DNE1)** - a subdirectory placed on one secondary MDT
  (`lfs mkdir -i <mdt_index>`).
- **Striped directories** - one large directory sharded across MDTs by a hash
  (`lfs mkdir -c <count>`; fields `lmv_stripe_count`, `lmv_hash_type: crush`). The manual
  warns against striping every directory: it targets directories with many output files (it
  cites >50k entries), because lookups now cost hash plus possibly a cross-MDT RPC.

## OSTs, pools, and the backing filesystem

Glossary: an OST is an "Object Storage Target... associated with a unique OSD which, in turn
is associated with a formatted disk file system on the server containing the data objects";
the OSS is the "server OBD that provides network access between the client and local OSTs."
File data on an OST is a plain object in that filesystem, plus a `LAST_ID` allocator and the
`last_rcvd` recovery file (backups tar `last_rcvd`, `CONFIGS/`, `O/0/LAST_ID` together).
`mkfs.lustre --backfstype=ldiskfs` (the default) or `zfs` picks the backend; the manual gives
ZFS first-class treatment (ch. 31, Lustre ZFS snapshots), but ldiskfs remains the default.
OST pools (`lctl pool_new fsname.poolname`, `pool_add`; ASCII names, max 15 chars) restrict
striping to a named OST subset - pools predate PFL and still answer "keep tier-X files off
the archive OSTs."

## Striping defaults: the numbers interviews test

Manual ch. 10, Table "Default stripe pattern":

| Parameter | Default | Meaning |
|-----------|---------|---------|
| stripe_size | 1 MB | bytes written to one OST before rotating; must be a multiple of 64 KiB |
| stripe_count | 1 | OSTs per file - a brand-new file is NOT wide-striped |
| start_ost | -1 | first OST index; -1 lets the MDS choose by space/load balance (manual: do not change it) |

Corrections worth saying out loud: `stripe_count = 0` means "use the filesystem default" and
`-1` means "stripe over all available OSTs (full OSTs are skipped)" - so "Lustre stripes
everything across every OST by default" is wrong; the shipped default is a single stripe, and
wide striping is a per-directory/per-file choice (`lfs setstripe`). The wiki striping page's
`stripe_count 2 / 4 MB` example is a filesystem-level setting someone configured, not the
built-in default.

## Progressive file layouts (PFL)

PFL (ch. 19.5, L 2.10) gives one file multiple layout components with growing stripe counts:
small files waste no OSTs, large files still go wide. The manual's own examples:

```text
lfs setstripe -E 4M  -c 1  -E 64M -c 4  -E -1 -c -1  file
#              ^end  ^count    next component; -E -1 = to EOF (sentinel)
lfs setstripe -E 256M -c 1  -E 16G -c 4  -E -1 -S 4M -c -1  /mnt/testfs/pfldir
```

Components instantiate lazily as the file grows past each `-E` boundary; the same chapter
covers SEL (self-extending layouts, L 2.13), foreign layouts, and Data-on-MDT (ch. 20), which
puts small-file data on the MDT itself - the most citable reason "small-file Lustre" stopped
being an automatic no.

## LNet: NIDs, LNDs, multi-rail, router chains

Glossary anchors: **LNet** is "Lustre networking. A message passing network protocol capable
of running and routing through various physical layers. LNet forms the underpinning of
LNETrpc"; an **LND** is the driver "over particular transports, such as TCP and various kinds
of InfiniBand networks"; a **NID** "encodes the type, network number, and network address" of
an interface, written `address@net` (`132.6.1.[1-8]@o2ib0` in the manual's route examples).
Manual table 8.3 lists TCP, OpenFabrics InfiniBand (`o2ib`), and Cray `gni` LNDs, noting only
TCP and o2ib are routinely release-tested.

- **Multi-rail (software MR, L 2.10)**: one node exposes several NIDs (`eth0@tcp` plus
  `ib0@o2ib1`); peers learn all of them, and traffic spreads or fails over across rails. The
  manual's example: `lnetctl net add --net tcp2 --if eth0 --peer_timeout 180 --peer_credits 8`;
  since 2.10 `--net` need not be unique per interface. LNet Health (L 2.12) tracks
  per-peer/per-NID health and fails traffic over; router health discovery follows in L 2.13.
- **Routing and router chains**: networks that cannot talk directly are bridged by LNet
  routers running `forwarding=enabled`, with `routes="tcp0 132.6.1.[1-8]@o2ib0"` style
  tables. The manual covers multi-hop configurations, router checkers, and an
  asymmetric-router-failure case study; each hop costs a full forwarding pass.

```text
  client rail A (tcp)   client rail B (o2ib1)     storage network (o2ib0)
  10.0.0.11@tcp         ib0:...@o2ib1
       |                      |                          |
       +--------+  +----------+                          |
                |  |                                     |
                v  v                                     |
             +-------------+ (second router for        +--------------------+
             | LNet router |  resiliency)              | MDT/OSS nodes      |
             | forwarding= |-------------------------->| target NIDs @o2ib0 |
             | enabled     |                           +--------------------+
             +-------------+
  multi-rail peer = one peer, several NIDs; LNet Health (2.12+) drops bad rails
```

## LDLM: intent-based locking

LDLM (the glossary's "Lustre Distributed Lock Manager") is distributed by construction: each
target runs a lock server for its own objects; clients run lock clients that "make lock RPCs
to a lock server and handle revocations from the server."

- **Intent locks** - glossary: an intent lock "combines a request for a lock with the full
  information to perform the operation," offering the server the option of performing the
  operation and returning the result *without granting a lock*, which "enables metadata
  operations (even complicated ones) to be implemented with a single RPC from the client to
  the server." One round trip instead of acquire + op + release.
- **Extent locks and eviction** - data locks are byte-range locks (PR/PW modes); a server
  needing a conflicting lock sends a blocking callback. The manual's eviction rule: a client
  that "fails to timely respond to a blocking lock callback from the Distributed Lock Manager
  (DLM) or fails to communicate with the server in a long period of time (i.e., no pings)" is
  forcibly evicted, freeing its locks for others.

## Recovery: last_rcvd, replay, orphans

Each target persists its last committed transaction number in the `last_rcvd` file on the
backing filesystem - hence the backup trio `last_rcvd`, `CONFIGS/`, `O/0/LAST_ID`. Clients
keep a per-server replay list of replies whose transaction numbers exceed the last committed
number the server reported; on target restart the server tells each reconnecting client the
last committed transaction number on disk, the client prunes already-committed requests and
"replays any newer requests to the server in transaction number order, one at a time" (ch.
36). Orphan cleanup is llog-driven: on unlink the MDT "atomically add[s] the OST objects into
a per-OST llog (in case a crash occurrs)" and destroys them after commit; a crash leaves "OST
objects to which no Lustre file points," removed by MDT-OST llog recovery - recovery is
transaction-number bookkeeping plus idempotent replay, not client-state journaling.

## HSM in one paragraph

The HSM stack (ch. 26) has three roles. A **coordinator** is enabled per MDT (`lctl set_param
mdt.$FSNAME-MDT0000.hsm_control=enabled`) and queues archive/release/restore requests.
**Agents** run copytools like `lhsmtool_posix --daemon --hsm-root $HSMPATH --archive=1
$LUSTREPATH` (stopped with SIGTERM). Users inspect state with `lfs hsm_state` and drive
actions with `lfs hsm_set`; copytools consume the MDT changelog (ch. 12), and PCC (ch. 27),
Lustre's persistent client cache, reuses the HSM mechanism for writeback sync.

## Demo: striping placement calculator

The calculator implements the manual's RAID-0 rule - stripe i lands on
`(start_ost + i) % stripe_count` - and computes the interview numbers: bytes per OST, active
OSTs vs declared stripe_count, aggregate read bandwidth vs the single-OST ceiling, and the
small-file pathology.

```python
#!/usr/bin/env python3
"""Lustre RAID-0 striping calculator (Operations Manual ch. 19 placement rule).

Stripe i lands on OST (start_ost + i) % stripe_count; start_ost = -1 means
the MDS picks the starting index. Aggregate read bandwidth = min(client
cap, active OSTs * per-OST BW), active = min(stripe_count, stripes)."""
import math

MIB = 1024 * 1024
BW_OST, BW_CLIENT = 500, 12288  # MiB/s per OST; client NIC + memory cap

def place(size, count, ssize, start=0):
    """One file's layout: {ost_index: bytes held on that OST}."""
    used = {}
    for i in range(math.ceil(size / ssize)):
        ost = (start + i) % count
        used[ost] = used.get(ost, 0) + min(ssize, size - i * ssize)
    return used

print("A. placement of a 1 GiB file, stripe_count=16, stripe_size=1 MiB")
for start in (0, 23):
    used = place(1 << 30, 16, MIB, start)
    span = "OST 0..15" if start == 0 else "wraps 31 -> 0"
    print(f"   start_ost={start:3d}: {len(used):2d} OSTs ({span}), {max(used.values()) // MIB} MiB each")
print("\nB. scenarios (per-OST 500 MiB/s, client cap 12288 MiB/s)")
print(f"   {'file':>10} {'count':>5} {'stripes':>7} {'OSTs used':>9} "
      f"{'max MiB/OST':>11} {'agg MiB/s':>9} {'read s':>7}")
for size_b, count, ssize_b in [(1 << 30, 16, MIB), (1 << 30, 1, MIB), (64 << 30, 64, MIB),
                               (512 * 1024, 16, MIB), (4 * 1024, 16, MIB), (4 * MIB, 16, MIB)]:
    used = place(size_b, count, ssize_b)
    bw = min(BW_CLIENT, len(used) * BW_OST)
    label = f"{size_b / (1 << 30):.2f} GiB" if size_b >= (1 << 30) else f"{size_b / MIB:.2f} MiB"
    print(f"   {label:>10} {count:>5} {math.ceil(size_b / ssize_b):>7} {len(used):>9} "
          f"{max(used.values()) / MIB:>11.3f} {bw:>9} {size_b / (bw * MIB):>7.3f}")
print("\nreading B: files below one stripe_size (512 KiB, 4 KiB) sit on a single OST and")
print("read at the single-OST ceiling - striping buys nothing below one stripe. 4 MiB with")
print("count=16 activates only 4 of 16 OSTs; wide layouts pay off once the file is many")
print("stripes deep.")
```

```text
A. placement of a 1 GiB file, stripe_count=16, stripe_size=1 MiB
   start_ost=  0: 16 OSTs (OST 0..15), 64 MiB each
   start_ost= 23: 16 OSTs (wraps 31 -> 0), 64 MiB each

B. scenarios (per-OST 500 MiB/s, client cap 12288 MiB/s)
         file count stripes OSTs used max MiB/OST agg MiB/s  read s
     1.00 GiB    16    1024        16      64.000      8000   0.128
     1.00 GiB     1    1024         1    1024.000       500   2.048
    64.00 GiB    64   65536        64    1024.000     12288   5.333
     0.50 MiB    16       1         1       0.500       500   0.001
     0.00 MiB    16       1         1       0.004       500   0.000
     4.00 MiB    16       4         4       1.000      2000   0.002

reading B: files below one stripe_size (512 KiB, 4 KiB) sit on a single OST and
read at the single-OST ceiling - striping buys nothing below one stripe. 4 MiB with
count=16 activates only 4 of 16 OSTs; wide layouts pay off once the file is many
stripes deep.
```

The 64 GiB row is the honest one: 64 OSTs x 500 MiB/s would be 32000 MiB/s, but the client cap
binds at 12288 - aggregate bandwidth is min(client, active x per-OST), and on real clusters
the client rail or OSS NIC usually binds before the OST array does.

## Interview probes

- A client is evicted mid-write: which two data structures decide which of its writes are
  replayed after reconnect, and what number prunes the replay list?
- Why can DNE striped directories hurt lookup latency even while spreading load?
- A 200 MiB file striped over 200 OSTs: given the defaults table, what did that buy, and what
  would an `-E`-based PFL layout have done instead?
- Where does `last_rcvd` live, why do backups tar it with `CONFIGS/` and `LAST_ID`, and what
  breaks on restore if it is stale?

## References

1. [Lustre Operations Manual](https://doc.lustre.org/lustre_manual.xhtml) (probed 200, fetched
   in full): default stripe pattern table (ch. 10), layouts/PFL (ch. 19), LNet (ch. 15-16),
   HSM (ch. 26), recovery (ch. 36), glossary quotes.
2. [wiki.lustre.org: Configuring Lustre File Striping](https://wiki.lustre.org/Configuring_Lustre_File_Striping)
   and [Multi-Rail LNet](https://wiki.lustre.org/Multi-Rail_LNet) (both probed 200 with a
   browser UA; plain scripted curls get 403 - noted): `lfs getstripe`/`setstripe` workflow,
   filesystem-level default layouts, multi-rail peer/NID policy.
3. [Wide-Area Lustre File System Using LNet Routers, OSTI/PNNL](https://www.osti.gov/servlets/purl/1468050)
   (probed 200): LNet router deployment across sites; and
   [A. Shehata, "LNet Multi-Rail Resiliency / LNet Health", OpenFabrics 2017](https://www.openfabrics.org/images/eventpresos/2017presentations/202_LNethealth_AShehata.pdf)
   (probed 200): the design talk behind LNet Health failover.
4. Qian, Li, Ihara, Dilger, Thomaz, "LPCC: Hierarchical Persistent Client Caching for Lustre,"
   SC '19, doi [10.1145/3295500.3356139](https://doi.org/10.1145/3295500.3356139) (dl.acm.org
   403s to curl; Crossref API confirms SC '19 proceedings, authors, Nov 2019).
5. George, Dilger, Brim, Mohr, Shehata, "Lustre Unveiled: Evolution, Design, Advancements, and
   Current Trends," ACM Transactions on Storage, doi
   [10.1145/3736583](https://doi.org/10.1145/3736583) (Crossref-verified 2025 survey by core
   Lustre developers).
6. [whamcloud.com](https://whamcloud.com/) and
   [lustre.org/documentation](https://www.lustre.org/documentation/) (both probed 200):
   maintainer hubs. DDN's EXAScaler page
   ([ddn.com/products/lustre-file-system-exascaler](https://www.ddn.com/products/lustre-file-system-exascaler))
   403s scripted probes; search-verified only.
