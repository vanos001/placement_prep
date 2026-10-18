# "If data gets corrupted, something would crash or error"

## Overview

The belief that corruption announces itself rests on an image of broken
data as garbage: wrong magic bytes, unparseable structures, loud crashes.
Reality is quieter. Most bit-level damage that survives the hardware's own
error correction lands in bytes whose only special property is that they
are now wrong: an amount shifts from 100 to 102, a name gains a stray
character, a database page parses cleanly with one row pointing at the
wrong slot. Nothing crashes; nothing logs; the system answers, politely
and incorrectly. This page audits the claim, walks the standard silent
corruption classes — bit rot, lost writes, torn writes — explains the
checksumming that makes detection loud *when it exists*, and gives the
end-to-end argument its due: only the layer that understands the data can
fully validate it. The verdict is false, with one honest kernel: most
corruption *is* caught, by device-level engineering that the claim quietly
borrows credit for.

## The Claim, Stated Fairly

The strongest common form is: "Storage and networking stack everywhere
have integrity checks; if a byte were flipped on disk or in flight, a
checksum would fail, an I/O error would surface, and the process would
crash or at least log. Silent corruption is a scare story." This deserves
fairness, because the speaker has usually never seen silent corruption and
has seen many loud failures. Disk firmware really does check sectors,
filesystems really do verify metadata checksums on read in modern
defaults, and the majority of physical bit damage is corrected or flagged
before any application could observe it.

The claim fails on two boundaries. First, the layers that check are
checking specific hops, not the end-to-end path, and bytes that pass every
hop's local check can still be wrong at the end. Second, a wrong-but-
well-formed value is indistinguishable from valid data by any
structure-checking mechanism — detection requires semantic validation,
which by the end-to-end argument only the application can perform.

## Verdict

**False.** Silent corruption is an ordinary, documented phenomenon with
dedicated research literature and dedicated mitigations: lost writes
acknowledged but never persisted, torn writes applied across a power-loss
boundary, bit rot in media that is not read for years, and misdirected
I/O landing a valid block at the wrong address. Each class produces data
that is structurally plausible and semantically wrong, which is precisely
the condition under which no parser or structure checker raises anything.
The counterexamples do not require exotic hardware: they require only
years of operation at fleet scale, which is when the studies in this
page's references observed them.

## Why People Believe It

The kernel is layered defense that mostly works. Modern storage devices
store redundant bits per sector — error-correcting codes tuned so that the
common single-bit and burst errors are corrected invisibly or, when
uncorrectable, reported as read errors. Network frames carry CRCs, and
memory carries ECC in servers. The composite effect is real: the majority
of bit-level damage never reaches application code as silently wrong data,
because it is fixed at the device layer or surfaced as an I/O error. An
engineer who has run services for years and never seen silent corruption
is not imagining their evidence — they are observing the defenses working.

The compression error is attributing the defenses to nature rather than
engineering, and assuming the defenses are universal. Each protective
layer has documented gaps: device ECC covers a sector but not the case
where the drive acknowledges a write and the data never reaches stable
media (lost write); a filesystem journal protects metadata but not
necessarily data blocks; a parity RAID volume protects against a lost
device but a lost *write* corrupts parity silently, because parity is
recomputed from what arrived. None of these failures are exotic — storage
research at fleet scale (the FAST '08 study in the references) found
checksum mismatches and lost or corrupt blocks occurring at measurable
rates across hundreds of thousands of systems.

The third reason the belief persists is that its failure mode is
invisible by definition. A crash produces an investigation; silent
corruption produces a slightly wrong report that nobody opens for
quarters. Absence of observed corruption is therefore not evidence of
absence — it is exactly what the phenomenon predicts.

A fourth reason is the asymmetry of remembered failures. When storage
misbehaves in ways the stack does detect, the engineer sees the crash,
the I/O error, the kernel log line — vivid, attributable events that
anchor the intuition "corruption is loud". The silent cases, by
construction, leave no such memory: they surface as a reconciliation
discrepancy months later, an invoice that is merely wrong, or never at
all. The evidence set an individual accumulates is therefore
systematically biased toward the loud half of the distribution, which is
the half the defenses already caught.

## The Correct Formulation

| Claim component | Correct form |
|---|---|
| "Corruption crashes or errors" | Structure-plausible corruption parses fine; detection needs semantic checks, not parsers |
| "The device checks sectors" | Device ECC corrects common bit damage but cannot catch lost writes or misdirected I/O |
| "The network checks frames" | Link CRCs protect each hop; end-to-end integrity needs verification at the endpoints |
| "The filesystem journal protects data" | Journals typically protect metadata; data blocks often ride outside the guarantee |
| "Checksums exist" | Only where explicitly enabled: ZFS/Btrfs block checksums, dm-integrity, PostgreSQL page checksums (opt-in per cluster), application digests |
| "Most corruption is caught" | True — by device ECC and journaling engineering, not by nature; the claim borrows their credit |

The corrected sentence: "Absence of an error signal means only that no
layer you enabled was designed to check this. Detection is a property you
purchase per layer — device ECC, filesystem checksums, database page
checksums, application-level digests — and the only layer that can check
*meaning* is the application that produced the data."

The end-to-end argument (Saltzer, Reed, and Clark, 1984) is the formal
version: lower layers can legitimately omit guarantees they cannot
provide cheaply, because only the endpoints know what correctness means.
Applied to integrity, it says checksums at every intermediate hop are
necessary engineering but never sufficient, and the application-level
digest — hash the record, store it, verify on read — is the only check
that spans the whole path. This is the same architectural lesson the TCP
audit in this collection teaches for delivery: the guarantee you feel is
the one at *your* layer, not the ones below it.

## Where It Breaks

**The lost write.** A storage array with a failed battery-backed cache
acknowledges writes that it has not actually committed to platters; power
fails; the drive's write cache is empty. The filesystem believes block B
holds the new value; the platter holds the old one. Two nodes now read
different "current" balances; an application that reads old-modifies-writes
computes from a stale base, and every subsequent operation succeeds
loudly. Nothing errored at write time — the write was acknowledged — and
nothing errors at read time, because the old value is a perfectly valid
value. Detection requires either end-to-end verification (checksum every
recorded value at the application layer) or explicit write-hole
protection at the array, both of which are purchases, not defaults.

**The torn write without page checksums.** A database writes a 8 KB page;
power is lost after the storage device commits only part of the
multi-sector write. With page checksums enabled, the recovery process
detects the mixed page and fails loudly into recovery tooling — the
designed experience. Without checksums (the historically default-off case
for PostgreSQL clusters), the page may parse: a row pointer lands within
bounds, a transaction ID looks plausible, and queries return rows that
were never committed together. The corruption surfaces as inexplicable
reporting drift weeks later, if ever. The feature that would have made
the failure loud was a per-cluster opt-in the team never enabled.

**Bit rot in cold data.** An archive object is unread for three years;
its sector accumulates uncorrectable damage; the medium, read again,
returns wrong bytes with no error signal (or the redundancy itself has
decayed). If the object store verifies digests on scrub, the failure is
caught at the next scrub and repaired from parity or replica — this is
the designed experience, and the reason scrubbing exists. If the archive
is a plain directory tree on a volume without background verification,
the wrongness is discovered by a human comparing against a source that
may no longer exist. The "loud" outcome in the claim depends on somebody
having scheduled the checking.

**The single-bit semantic flip.** The price field stored as ASCII
`100` (`0x64`) suffers one flipped bit and becomes `0x66` — `102`.
Invoices accept it; reports sum it; nothing crashes, because `102` is a
valid price. This class needs no hardware pathology at all — it is just
what a flipped bit *is*: a different valid value. Detection is only
possible through redundancy that encodes meaning (a digest, a second
copy, a reconciliation), which is an application-layer design decision.
When it accidentally works: device ECC, frame CRCs, journaling, and
enabled page checksums do catch most of what occurs — the claim survives
as a statement about fleets whose engineers bought detection at every
layer, which is the opposite of a reason to skip buying it.

## Practical Implications

- Enable checksumming where the layer offers it: database page checksums
  per cluster, filesystem block checksums (ZFS/Btrfs) or dm-integrity
  where supported, and scrub schedules for parity volumes.
- Add application-level digests for data whose meaning you own: hash
  records at write, verify at read or on scheduled audit; this is the
  only end-to-end check.
- Reconcile independently: export-and-compare jobs between service and
  ledger, source and replica, catch silent divergence that no checksum
  layer can.
- Treat write-path durability as part of integrity: battery/flash
  protection on write caches, fsync discipline, and fencing on storage
  failover reduce the lost-write class at its source.
- In design reviews, ask "how would we *notice*?" for every durability
  claim — an integrity mechanism without a detection story is a hope.

## Interview Questions

### Give an example of corruption that produces no error anywhere in the stack.

A lost write: storage acknowledges the write, power or cache failure
prevents it reaching stable media, and both the old and new values are
valid — reads of the stale value succeed silently. Or a single flipped
bit in an ASCII digit, which yields another valid digit. Both are
undetectable by parsers and structure checks; detection requires
redundancy that encodes meaning, such as digests or reconciliation.

### Why is device-level ECC not enough?

ECC covers a sector's bits against decay between write and read, but it
cannot know whether the drive ever received or retained a write
(lost write), whether the write went to the correct address (misdirected
I/O), or whether a multi-sector write completed (torn write). Those
classes need coordination above the device — journaling, checksummed
pages, or end-to-end digests.

### What does the end-to-end argument imply for data integrity?

That intermediate layers should provide the checks they can do cheaply,
but correctness of the data's meaning can only be verified by the
endpoints that understand it. Practically: hop-level CRCs and ECC remain
worth having, and the application adds write-time digests and read-time
verification so the check spans every layer, including the ones nobody
remembers are there.

### How do databases make torn-page corruption loud?

By storing a per-page checksum in the page header: recovery validates
every page and fails loudly on mismatch, converting silent wrong answers
into a detected, actionable failure. The tradeoff is a small write cost
and, historically, an opt-in decision per cluster — which is why the
audit question "are page checksums on?" belongs in every database
design review.

### You inherit a system with no checksums anywhere. Where do you add detection first?

At the application layer for the highest-value records (digests,
reconciliation jobs), because that check is end-to-end and catches every
upstream gap. Then enable the cheap layer-level options — database page
checksums, filesystem checksumming or scrubbing — since they localize
damage. The ordering matters: semantic detection finds wrong answers even
when every hardware layer checks out.

## Key Takeaways

- Corruption is silent by default: wrong-but-well-formed data parses,
  answers, and invoices without complaint.
- The standard classes — bit rot, lost writes, torn writes, misdirected
  I/O — are documented at fleet scale, not hypothetical.
- Loudness is purchased per layer: device ECC, frame CRCs, journals,
  page checksums, scrubs. Most corruption *is* caught — by engineering
  the claim forgot to credit.
- Only the application can check meaning; the end-to-end argument makes
  digests and reconciliation the only full-path detection.
- For every durability guarantee in a design, ask how its failure would
  be noticed, and by which layer.

## Cross-References

- [Connection Atlas: Checksums & Erasure Coding](../connection-atlas/checksums-erasure-coding.md)
  — how checksums and coding detect and repair damage mechanically
- [Assumptions Hunt: Storage Durability](../assumptions-hunt/storage-durability.md)
  — the hidden assumptions behind "the data is safe on disk"
- [Misconceptions: tcp-guarantees-delivery](./tcp-guarantees-delivery.md)
  — the same end-to-end lesson for delivery: layer guarantees stop at
  their own boundary
- [Misconceptions: crc-equality-means-file-equality](./crc-equality-means-file-equality.md)
  — the adjacent audit: that page asks whether a *matching checksum*
  proves a file's identity; this page asks whether corruption
  announces itself when no check is watching
- [Misconceptions: backups-mean-recovery](./backups-mean-recovery.md) —
  backups faithfully preserve silent corruption; verification belongs at
  write time, restoration at recovery time
- [Linux Storage: RAID Explained](../../linux/storage/raid-explained.md)
  — parity, scrubbing, and the write hole in practice
- [Misconceptions index](./index.md) — the taxonomy used for this verdict

## References

- L. N. Bairavasundaram et al. *An Analysis of Data Corruption in the
  Storage Stack*, FAST '08 — fleet-scale incidence of checksum
  mismatches, lost writes, and torn writes, cited by title.
- J. H. Saltzer, D. P. Reed, D. D. Clark. *End-to-End Arguments in System
  Design*, ACM TOCS, 1984 — cited by title.
- PostgreSQL documentation, *Data Page Checksums* — the per-cluster
  opt-in mechanism discussed above, cited by title.
