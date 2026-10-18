# Redundancy Arithmetic: Checksums, Parity, Erasure Coding, Hashes, ECC

## Overview

A TCP segment, a RAID stripe, an HDFS block group, a Git object, and a RAM DIMM all face the same adversary: bits flip. The responses look superficially similar — every one of them computes extra bits from the data — but they sit at different points on one design axis: how much redundancy you add, and what it converts a detected error into. A checksum converts silence into an alarm. A parity bit converts one loss into a reconstruction. An erasure code converts m losses into a reconstruction. Replication converts anything into "try another copy." Naming the axis turns five pieces of storage trivia into one trade-off table with numbers you can actually design with.

This page explains each mechanism independently, states the shared principle, works the storage-and-durability arithmetic for Reed-Solomon versus replication, and ends with the end-to-end argument — the reason checks at every layer can still let application-visible corruption through.

## The Concepts, Independently

**TCP/IP checksums.** The IPv4 header and TCP/UDP segments carry a 16-bit Internet checksum: ones'-complement addition of 16-bit words, complemented, stored in the header ([../../networks/tcp/header.md](../../networks/tcp/header.md), RFC 9293 §3.1). It detects every single-bit error and most bursts, but it is additive arithmetic: two errors in different words can cancel, so its residual miss rate for random multi-bit corruption is on the order of 1 in 2¹⁶. Ethernet goes further with a CRC-32 frame check sequence, which detects all burst errors up to 32 bits and all odd numbers of bit errors in practice. Neither corrects anything: detection means drop-or-retransmit, and the recovery loop lives elsewhere.

**RAID parity.** Striping across N disks plus one parity block per stripe, where parity is the XOR of the data blocks. Lose any one disk and every lost block is reconstructible: XOR the surviving blocks with the parity block. RAID-5 rotates parity across disks; RAID-6 adds a second, Reed-Solomon-style parity P+Q and survives two simultaneous failures ([../../os/filesystems/raid.md](../../os/filesystems/raid.md)). The catch is at rebuild time: to reconstruct the failed disk you must read *every surviving disk in full*, and any unreadable sector hit during that read is an unrecoverable error with no remaining redundancy to absorb it — the classic RAID-5 rebuild gamble.

**Erasure coding (Reed-Solomon).** Generalize parity: split data into k shards, compute m parity shards with Reed-Solomon coding; any k of the k+m shards reconstructs the whole object (the maximum-distance-separable property). HDFS default RS(6,3) and Ceph/RS-based object stores trade compute and network I/O for storage: 1.5× overhead instead of 3× replication ([../../networks/advanced/fec-networking.md](../../networks/advanced/fec-networking.md) covers the same math used for forward error correction on lossy links). The cost is repair: rebuilding one lost shard requires reading k shards and transferring them to the rebuilder — a k-fold network amplification versus replication's single-copy re-fetch.

**Git content hashes.** Every object is named by the SHA-1 (or SHA-256) of its content, and trees hash their children's hashes, so a commit root authenticates the entire graph ([../../git/internals.md](../../git/internals.md), [./git-cas.md](./git-cas.md)). This is *detection only* — a corrupted blob is caught at verification, but Git cannot heal it locally; recovery means fetching the object from another copy of the repository. Git is the purist's answer: zero data redundancy in the hash layer, all recovery delegated to replication of the whole repo (remotes, clones, mirrors).

**ECC RAM.** DRAM cells suffer soft errors (charge loss from particle strikes; quoted rates vary by orders of magnitude with altitude and process generation, but are always nonzero). Standard ECC DIMMs store 72 bits per 64-bit word — 8 overhead bits implementing a single-error-correct, double-error-detect (SECDED) code: the memory controller recomputes the syndrome on every read and fixes single-bit errors transparently ([../../arch/memory-tech/ddr.md](../../arch/memory-tech/ddr.md)). ECC is the one member of the family where correction is universal, per-word, and invisible to software — because the redundancy ratio (8/64 = 12.5%) and the failure model (sparse, independent bit flips) make per-word correction cheap.

## The Shared Principle

**Redundancy converts detection into recovery: add r bits (or r copies) derived from the data, and you can convert r units of loss from "detected failure" into "computed repair."** The design axis is a spectrum, ordered by how much loss each point absorbs per unit of overhead:

```text
  MECHANISM            OVERHEAD       DETECTS         CORRECTS
  -------------------  -------------  --------------  ----------------------------
  checksum (16-bit)    ~0% (digest)   most 1-2 bit    nothing (raise/drop/retransmit)
  CRC-32               ~0% (digest)   bursts <= 32    nothing
  SECDED ECC           12.5%          2-bit errors    1-bit errors, per word
  RAID-5 parity        1/N (e.g.17%)  2 disk losses   1 disk loss, per stripe
  Reed-Solomon k+m     m/k (1.2-1.5x)  m+1 shard loss m shard losses, per object
  replication n-way    (n-1)x         any corruption  any loss, per object (n>1)
```

Two assumptions power every row, and both are where the systems break in practice. First, **errors must be independent**: XOR parity and RS codes are only as good as the claim that failures do not correlate — the claim that dies with a bad power supply, a firmware bug shipped to a whole batch of drives, or an entire rack losing power. Second, **verification must be end-to-end**: a check only certifies the layer that computes it.

## Where the Analogy HOLDS and BREAKS

| Property | HOLDS (all five) | BREAKS |
|---|---|---|
| Redundancy buys recovery | Same math family: parity = RS with m=1; SECDED = Hamming+parity; replication = RS with m=n−1 and maximal repair simplicity | Overhead is not comparable across the axis: 12.5% ECC overhead corrects 1 bit per 64; 50% RS overhead corrects whole shard losses — unit size matters more than percentage |
| Detection is cheap and universal | Hashes/checksums everywhere; all five verify independently of where data came from | Checksums *detect*, they never *repair* — Git and TCP must pair their detection with an external recovery loop (remote fetch, retransmit) |
| Repair vs storage trade-off | RS minimizes storage; replication minimizes repair I/O and latency; ECC fixes without software involvement | The trade flips with scale: at petabytes the 3× vs 1.4× storage difference dwarfs repair amplification; at cache-scale the reverse |
| Independence of failures | Every code's guarantee is conditional on uncorrelated losses | Correlated failures (power, firmware, rack, operator) dominate real data-loss postmortems; codes narrow the window but do not remove it |
| Layered checks compose | Each layer catches the corruption it can see | End-to-end argument: lower-layer checks are *necessary but insufficient* — a layer that recomputes its own checksum after corruption certifies garbage, and no lower layer can see application-meaning damage (swapped rows, wrong-field writes) |

The deepest break is the end-to-end one, and it deserves its own paragraph. Saltzer, Reed, and Clark's argument ("End-to-End Arguments in System Design," ACM TOCS 1984) is that functions placed at low layers can be *defeated* by intervening layers and cannot, by construction, know the application's correctness requirement. Applied here: a TCP checksum certifies the segment on the wire and the disk's CRC certifies the sector on the platter, but a controller bug, a misrouted DMA write, or an application writing the wrong value *correctly* produces data that passes every layer-level check while being wrong. This is why ZFS and btrfs checksum blocks in the filesystem, why object stores verify application-level digests on read, and why "we have ECC RAM" has never once excused anyone from hash-checking a backup restore.

## A Concrete Worked Example

**Storage: RS(10,4) vs 3-way replication for 10 TB of objects.**

- *Replication, 3×:* 30 TB of raw disk per 10 TB usable; each object readable from any of 3 copies.
- *Reed-Solomon RS(10,4):* 14 shard-slots per 10 data shards = 1.4× → 14 TB raw. Storage saved vs replication: 30/14 ≈ **2.14×** — on 1 PB of objects that is roughly 1.6 PB of raw disks not bought.
- *Repair cost, reversed:* lose 1 shard. Replication: re-copy 1 unit (~100 GB per 1 TB object) from a live replica — 1× read, 1× transfer. RS(10,4): read the 10 surviving shards, transfer them to a rebuilder, regenerate the lost shard — **10× the I/O for the same one lost shard**, plus a repair window of hours instead of minutes on a busy network.

**Durability, nominal arithmetic (independence assumed).** Take a per-disk annual failure rate of 2% → daily failure probability p ≈ 0.02/365 ≈ 5.5×10⁻⁵ per disk-day.

- *Replication, repair within 1 day:* an object is lost only if all 3 replicas fail before repair completes: p³ ≈ 1.7×10⁻¹³ per object-day. Tiny — *if* failures are independent.
- *RS(10,4), repair window 3 days:* loss needs 5 shard losses (of 14) within the window: C(14,5)·p⁵ ≈ 2002 × (1.6×10⁻⁴)⁵ ≈ 2×10⁻¹⁶ per object-day — nominally another ~1000× better.
- *The honest footnote:* those curves cross in the real world because the independence assumption is exactly what correlated failures violate. A batch-defective drive model, a rack power event, or a firmware bug pushes the joint failure probability far above the product of marginals; the RS repair window is *longer*, which widens exposure to precisely those events. Erasure coding wins the storage bill and usually wins the nominal durability math; replication wins repair speed, read amplification under degradation, and independence-robustness. Production systems buy both: EC for bulk, replication for hot or small objects.

**The rebuild gamble, quantified.** RAID-5 rebuild must read all surviving disks: 8 × 2 TB = 16 TB = 1.28×10¹⁴ bits. With an unrecoverable-read-error rate around 1 per 10¹⁴–10¹⁵ bits (consumer spec sheets), the probability of hitting at least one URE mid-rebuild is roughly 1–10× — that is, RAID-5 rebuild on consumer drives is a genuine coin flip, which is the standard argument for RAID-6/mirror pairs at scale. The number is a probability statement from spec-sheet rates, not a measurement, but it explains an entire generation of storage folklore.

## When This Connection Is Useful

- **Storage design decisions.** "Why not replicate everything 3×?" and "why does S3/HDFS/Ceph bother with erasure coding?" are the same question with one answer: overhead vs repair-cost vs failure-correlation, chosen per data temperature. Small hot objects → replication; bulk cold objects → RS(6,3) or RS(10,4); caches → none (derivable data needs no redundancy, only its source does).
- **Interview: "how would you make a file store survive disk failures?"** The senior answer walks the spectrum in order: checksum for detection (and *where* the checksum lives — end-to-end, application-visible), then parity/EC for repair, then replication for latency-of-recovery, then the independence caveat (placement policy: disks, nodes, racks, power domains) — and closes with "checksums detect, only redundancy repairs," which is the sentence that separates mechanism knowledge from keyword matching.
- **Engineering judgment.** Trust no layer's integrity claim alone: verify application-level digests on restore (backups), on read (object stores), and on graph traversal (Git). The cost of a hash is nanoseconds; the cost of a silent restore-time corruption is the company.

## Interview Questions

1. Compute a 4-data-disk XOR parity example: given blocks A=1011, B=0110, C=1110, what is P, and how do you rebuild B after its disk dies? Why does the same trick not survive two disk losses?
2. For RS(10,4) vs 3-way replication: state the storage overhead of each, the I/O to repair one lost shard of each, and name the workload where each wins.
3. What does the end-to-end argument say about putting integrity checks in TCP, the disk, and the application simultaneously — and give a concrete corruption scenario that passes all three layer checks yet delivers wrong data to the user.
4. Why is Git's SHA-1 object hash *not* a data-protection mechanism? What pairs with it to make corrupted repositories recoverable, and where does that redundancy live?
5. SECDED ECC corrects 1 bit per 64 with 8 overhead bits. Estimate why the same per-bit-correction approach cannot scale to correcting a whole failed disk, and what the storage world does instead.

## Key Takeaways

- Redundancy is a dial from detection to recovery: checksum → parity → erasure code → replication; every mechanism is the same math family at different unit sizes and overhead ratios.
- Erasure coding trades repair I/O for storage: RS(10,4) costs 1.4× instead of 3× but repairs a lost shard with 10× the I/O; replication trades storage for repair speed and independence-robustness.
- All redundancy guarantees are conditional on failure independence — correlated failures (power, firmware, operator) are the dominant real-world break, handled by placement policy, not codes.
- Checksums detect; only redundancy repairs. Git's hashes and TCP's checksums are both detection-only and must be paired with an external recovery loop.
- The end-to-end argument (Saltzer/Reed/Clark, ACM TOCS 1984) explains why layered checks still miss app-level corruption: verify at the layer where correctness is defined.

## Cross-References

- [./git-cas.md](./git-cas.md) — Git as Content-Addressable Storage — hashes as names, and the Merkle property as end-to-end graph verification.
- [../../git/internals.md](../../git/internals.md) — Git Internals — object hashing and packfile integrity in detail.
- [../../networks/tcp/header.md](../../networks/tcp/header.md) — TCP Header — the Internet checksum field and its computation.
- [../../networks/advanced/fec-networking.md](../../networks/advanced/fec-networking.md) — Forward Error Correction — Reed-Solomon math applied to lossy links.
- [../../os/filesystems/raid.md](../../os/filesystems/raid.md) — RAID — parity layouts, rebuild behavior, and RAID-6 double parity.
- [../../arch/memory-tech/ddr.md](../../arch/memory-tech/ddr.md) — DRAM and DDR — soft errors and ECC signaling.
- [../assumptions-hunt/storage-durability.md](../assumptions-hunt/storage-durability.md) — Storage Durability Assumptions — adversarial audit of "the data is safe" claims.
- RFC 9293, "Transmission Control Protocol (TCP)," §3.1 — <https://datatracker.ietf.org/doc/html/rfc9293>.
- Saltzer, J., Reed, D., & Clark, D., "End-to-End Arguments in System Design," ACM Transactions on Computer Systems 2(4), 1984.
- HDFS Erasure Coding documentation, <https://hadoop.apache.org/docs/stable/hadoop-project-dist/hadoop-hdfs/HDFSErasureCoding.html>.
- Backblaze, "Reed-Solomon Explained," <https://www.backblaze.com/blog/reed-solomon/>.
- Harris, R., "Why RAID 5 Stops Working" (StorageMojo, 2007) — the rebuild-URE argument, cited by name.
