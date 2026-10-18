# "The checksums match, so the file is intact/identical"

## Overview

"Compare the checksums" is the standard advice for verifying downloads,
copying archives, and replicating data, and it is usually excellent
advice. The claim audited here is the step further that engineers take
under pressure: that *matching* checksums prove the file is intact or
identical. What a checksum proves depends entirely on which checksum, who
could tamper, and how much data has been fingerprinted. CRC-32 — the
checksum in ZIP, PNG, gzip, and Ethernet — lives in a 32-bit space, sees
its first expected collision among ~65,536 files by the birthday bound,
and can be made to collide deliberately in seconds; cryptographic hashes
raise the bar astronomically for accidental and adversarial forgery but
still answer "do these bytes match?" rather than "did the right party
produce these bytes?", which requires a MAC or a signature. This page
separates the three properties, works the arithmetic, and shows the
historical wreckage (WEP, MD5) caused by reading a checksum as a proof.

## The Claim, Stated Fairly

The strongest common form is: "If the checksum of the copy matches the
checksum of the original, the file is intact — and if two files have the
same checksum, they are the same file." The claim deserves fairness
because the everyday version is overwhelmingly true in practice. Storage
and network errors at modern bit error rates are rare and, crucially,
*accidental*: when they strike, the probability that the damage preserves
a 32-bit CRC, let alone a 256-bit hash, is negligible. Billions of
downloads are verified daily with hashes and zillions of frames with
CRCs, and the cases where a matching check accompanied a corrupted or
forged file are so rare that most engineers will never see one. The audit
question is what, precisely, the equality of two checksum values licenses
you to conclude — and for whom that conclusion fails.

## Verdict

**Incomplete.** Checksum equality is strong *evidence* of identity against
accidental corruption and, for cryptographic hashes, against any forgery
an attacker can realistically compute — but it is a probability statement,
not a proof, and its strength varies by orders of magnitude across the
checksum hierarchy. CRC-32 equality is defeated trivially by an adversary
(malleable by construction: the CRC is a linear function, so collisions
are solved, not searched) and degrades to a coin flip by roughly 2^16
items by the birthday bound. A 256-bit cryptographic hash makes both
attacks computationally absurd, yet even hash equality does not
authenticate: it says the *bytes* match, not that the *party* is right —
authenticity requires a keyed MAC or a signature. The claim becomes true
only after three qualifiers: which digest, what adversary, and what
question is actually being asked.

## Why People Believe It

The kernel of truth is the arithmetic of accidental errors. A disk at a
bit error rate near 1e-14 to 1e-15, a flipped bit in transit, a bad
sector, a truncated download — all produce damage that a CRC-32 detects
with probability effectively 1 (it catches every burst error up to 32
bits, all odd numbers of bit errors, and the overwhelming majority of
longer bursts with a well-chosen polynomial). On top of that, the daily
workflow is built on the claim: `sha256sum` after download, `md5sum` in
package metadata, rsync's delta checks, S3's ETag, git's object hashes.
When a practice works ten thousand times in a row, it hardens into an
invariant.

Three props hold the belief up. First, the tool names blur the hierarchy:
`cksum`, `md5sum`, and `sha256sum` sit in the same manual section and
produce the same *shape* of output, so a 32-bit and a 256-bit digest feel
like the same instrument at different precisions. Second, the adversary
is absent from most engineers' threat model — corruption is random by
nature, and random damage cannot aim at a 32-bit value, so CRC "works"
every time it is tried against nature. Third, textbooks teach CRCs and
cryptographic hashes in different courses (coding theory versus
security), so the sentence "a checksum is a fingerprint" gets formed once
and applied to both.

What is lost is the adversary and the arithmetic. Random damage cannot
aim at a checksum; an adversary can. And the birthday paradox means
digest strength for *distinguishing many files* is half the digest width
— 32 bits of CRC is a 16-bit effective guarantee across a large corpus,
which is not a small number, it is 65,536.

## The Correct Formulation

| Tool class | Example | Digest space | Detects accidental damage | Resists deliberate forgery | Proves authenticity? |
|---|---|---|---|---|---|
| Error-detecting code | CRC-32 / CRC-32C | 32 bits | Effectively always (all bursts ≤ 32 bits, most longer) | No — linear over GF(2), collisions are constructed by algebra, not search | No |
| Broken legacy hash | MD5 | 128 bits | Yes | No — practical chosen-prefix collisions since 2004; rogue-CA forgery demonstrated 2008 | No |
| Cryptographic hash | SHA-256 | 256 bits | Yes | Yes for practical purposes (second preimage ≈ 2^256) | No — unkeyed |
| Keyed hash (MAC) | HMAC-SHA-256 | 256 bits | Yes | Yes (attacker lacks the key) | Shared-key authenticity only |
| Signature | Ed25519 over a hash | — | Yes | Yes | Yes, attributable to a key holder, with non-repudiation |

The precise statement, in three clauses. First, equality of digests is
evidence whose strength equals the cost of producing a second input with
the same digest: ~2^32 CRC-32 trials by brute force, an algebraic
solution for CRCs, ~2^128 birthday work for SHA-256, infeasible for
second preimages. Second, the *relevant* attack for "are these the same
file?" is second preimage (find a different file matching *this* digest),
which is exactly what cryptographic hashes make infeasible and what
CRC-32 does not. Third, no unkeyed digest — CRC or SHA — answers "is
this the file the *sender meant*?"; only a MAC (shared secret) or a
signature (key holder attribution) does, and conflating the two is how
integrity checks get shipped without authentication.

## Where It Breaks

**The birthday bound, computed.** The probability that at least two of N
files collide in a d-bit digest is approximately 1 − exp(−N²/2^(d+1)).
For CRC-32 (d = 32), N = 65,536 gives roughly a 50% chance that some two
files in the corpus share a checksum; a storage service deduplicating by
CRC-32 at 100,000 objects is *expecting* collisions, and if it treats
"same CRC" as "same object", it will serve wrong data. The same bound is
why git moved its collision resistance from SHA-1 (2^80 birthday,
demonstrated in 2017 by the SHAttered attack on crafted PDFs) toward
stronger hashing: the corpus is large, the adversary is patient.

**Adversarial CRC collisions are algebra, not luck.** The CRC is a
linear function of the message over GF(2): CRC(m XOR Δ) = CRC(m) XOR
CRC(Δ). An attacker who wants a modified message to keep the same
checksum does not search — they solve a linear system for a small set of
tweak bytes, typically four for CRC-32, then re-pad so file sizes and
container metadata also match. This is precisely the property Wi-Fi's
original WEP design ignored: it protected frames with RC4 encryption and
a linear CRC-32, so flipping ciphertext bits flipped plaintext *and* CRC
predictably — the "integrity check" authenticating nothing, a textbook
cause of WEP's collapse. Any protocol or format that lets an adversary
choose bytes and checks them with a bare CRC inherits this failure.

**Hashes, broken and unkeyed.** MD5's chosen-prefix collisions (Wang et
al., 2004; refined by fast PC tools) allowed two *deliberately different*
files to share a digest — and the 2008 rogue CA certificate demonstration
showed a collision forged between an honest and a malicious certificate.
Even with an unbroken hash, unkeyed digests still miss the authenticity
question: a length-extension attack on naive SHA-256 "key || message"
constructions lets an attacker append data to a message they cannot read,
defeating an integrity check that "matched" every time. The fix — HMAC —
exists precisely because hash equality was never authentication.

**When it accidentally works.** Against nature, the claim is effectively
true at every level: real bit error rates are so low, and damage so
structure-blind, that a matching CRC-32 after a copy is decision-grade
evidence for "no accidental corruption". The regimes where the claim
fails are exactly the regimes where an adversary or a massive corpus is
present: deduplication keys, package verification, protocol integrity,
multipart-upload consistency (where an attacker can supply their own
matching ETag-style metadata), and any comparison across ~2^16+ objects
with a 32-bit digest. Engineers who never leave the "download, verify,
install" loop will never meet the boundary — which is how the claim
survives in code review long after it would fail in a protocol design.

## Practical Implications

- Pick the digest by adversary: CRC (or CRC-32C) for hardware/transport
  error detection; SHA-256 or BLAKE3 for identity and deduplication;
  HMAC or signatures whenever a party could *benefit* from forging a
  match. Never let CRC stand in for a hash in an adversarial context.
- Do deduplication or equivalence claims only on cryptographic hashes —
  and mind the birthday math: a d-bit digest tolerates about 2^(d/2)
  items before collisions become expected.
- Verify downloads with signatures (or at minimum hashes from a
  *different* channel than the download), not with a checksum shipped by
  the same channel that could be tampering with both.
- Treat "hash matches" as the end of an integrity argument, not an
  authentication one: name the key that vouches for the bytes, or the
  check has an unguarded boundary.
- In systems with checksummed layers (database pages, WAL records,
  erasure-coded storage), keep CRCs at the layer that fixes errors and
  hashes at the layer that answers identity — the two layers coexist
  because they answer different questions.

## Interview Questions

### ZIP uses CRC-32 while package managers publish SHA-256 digests. Why the difference?

ZIP's CRC protects against the accidental corruption a file transfer or
disk produces — random damage has no way to aim at a 32-bit linear
code, so detection is effectively certain and the 4-byte field is
cheap. Package digests face an adversary who *chooses* bytes and can
compute: a linear CRC is solvable algebraically, while SHA-256
requires ~2^256 work for a second preimage. The design rule is that
digest strength must exceed the adversary's compute, and the CRC
family was never designed to buy that.

### Your storage service deduplicates objects by CRC-32 and has 1 million objects. Estimate the collision risk and state the fix.

The birthday approximation gives an expected number of colliding pairs
near N²/2^(d+1) = 10^12/2^33 ≈ 116 pairs — deduplication will routinely
collapse distinct objects and serve wrong data. The fix is
deduplicating on a cryptographic digest (256-bit: expected collisions
across a billion objects remain astronomically small) and treating
"CRC equal" only as a fast pre-filter confirmed by the strong hash.
Mentioning the 2^(d/2) birthday scaling is the key follow-up.

### WEP used CRC-32 for integrity. Why was that fatal even before the key recovery attacks?

CRC is linear: flipping ciphertext bits flips the decrypted plaintext
and the CRC in a predictable way, so an attacker can modify frames and
patch the integrity field to match without knowing the key. Integrity
checks must be keyed and non-linear with respect to attacker-controlled
change — the exact property MACs and AEAD tags provide and bare CRCs
cannot. WEP is the canonical example that error detection and message
authentication are different properties, not different sizes of the
same property.

### Two files have the same SHA-256. Are they the same file — and what is the honest answer in an interview?

For every practical purpose, yes: finding any second preimage costs
~2^256 hash evaluations, far beyond any foreseeable compute. The
honest answer adds two qualifiers: equality is evidence with
astronomically high probability, not logical identity (a 256-bit
space means collisions *exist*, and the birthday cost ~2^128 governs
many-vs-many comparisons); and if the question is "did the expected
sender produce this file?", the hash must be covered by a MAC or
signature, because an unkeyed hash authenticates no one.

## Key Takeaways

- "Checksums match" is evidence whose strength depends on the digest:
  CRC-32 ≈ trivial for an adversary, SHA-256 ≈ unforgeable, and neither
  authenticates anyone without a key.
- Birthday math rules many-vs-many comparisons: a d-bit digest shows
  expected collisions around 2^(d/2) items — CRC-32's floor is ~65,536
  objects, not "never".
- CRCs are linear codes: adversarial collisions are solved by algebra
  (four tweak bytes), and protocols that paired bare CRCs with
  attacker-chosen bytes (WEP) failed for exactly that reason.
- Broken hashes (MD5) and unkeyed hashes (naive SHA-256 keying) fail in
  different ways: chosen-prefix collision versus length extension —
  HMAC and AEAD exist to close both gaps.
- The claim accidentally works against nature because accidental
  corruption cannot aim at any digest; it fails the moment the corpus
  is large or the adversary is real.

## Cross-References

- [Misconception: It's Encrypted, So It Can't Be Tampered With](./encryption-means-authenticated.md)
  — the cipher-mode sibling: malleability, AEAD, and the
  integrity-versus-authentication split
- [Assumptions Hunt: Security & Crypto](../assumptions-hunt/security-crypto.md)
  — the hidden assumptions in "we verify with hashes" claims
- [Assumptions Hunt: Storage Durability](../assumptions-hunt/storage-durability.md)
  — where checksums sit in the durability stack
- [Connection Atlas: Checksums & Erasure Coding](../connection-atlas/checksums-erasure-coding.md)
  — how checksums, parity, and repair cooperate across a storage path
- [Cryptography](../../security/cryptography.md) — hashes, MACs, and
  signatures in their native habitat
- [WAL Internals](../../dbms/internals/wal.md) — checksummed pages and
  records inside a production database
- [DSA: Hashing](../../dsa/chapters/ch07-hashing.md) — the general
  hashing mechanics behind digest-based reasoning

## References

- W. W. Peterson and D. T. Brown. *Cyclic Codes for Error Detection*.
  Proceedings of the IRE, January 1961, cited by title (the classical
  CRC detection-property analysis).
- P. Koopman and T. Chakravarty. *Cyclic Redundancy Code (CRC)
  Polynomial Selection for Embedded Networks*. DSN 2004, cited by title
  (Hamming-distance properties of CRC polynomials, including CRC-32C).
- X. Wang, D. Feng, X. Lai, and H. Yu. *Collisions for Hash Functions
  MD4, MD5, HAVAL-128 and RIPEMD*. CRYPTO 2004, cited by title.
- M. Stevens et al. *Short Chosen-Prefix Collisions for MD5 and the
  Creation of a Rogue CA Certificate*. CRYPTO 2009, cited by title;
  see also the SHAttered SHA-1 collision announcement (2017), cited by
  name.
- NIST. *Secure Hash Standard (SHS)*. FIPS 180-4, August 2015, cited by
  standard name.
- iSCSI CRC-32C (Castagnoli polynomial) usage: RFC 7143 *Internet Small
  Computer System Interface (iSCSI) Protocol*, April 2014.
  <https://www.rfc-editor.org/rfc/rfc7143.html>
