# Advanced Erasure Coding

> Builds on [../erasure-coding.md](../erasure-coding.md). This file covers the mathematics of Reed-Solomon over Galois fields, Local Reconstruction Codes, regenerating codes, fountain codes, and a thorough replication-vs-erasure-coding comparison.

## Reed-Solomon Over Galois Fields

### Why Galois Fields?

Erasure coding operates on finite fields where all arithmetic is exact — no floating-point rounding, no overflow. The most common choice is GF(2^w) where w ∈ {8, 16, 32, 64}. GF(2^8) uses a single byte per symbol and is fast with lookup tables. GF(2^16) and GF(2^128) are used when larger symbol sizes reduce per-symbol overhead.

In GF(2^w), addition is XOR and multiplication uses a generator polynomial. For GF(2^8), the standard polynomial is x^8 + x^4 + x^3 + x^2 + 1 (0x11D, used in AES and most EC libraries).

### Encoding Matrix

For a (k, m) Reed-Solomon code encoding k data symbols into k+m coded symbols:

```
Given k data vectors d_0, d_1, ..., d_{k-1}  (each is a vector of symbols)

Construct Vandermonde encoding matrix V of size (k+m) × k:

V = | 1    1    1   ...  1  |   (first k rows = identity, data is kept as-is)
    | 0    1    2   ... k-1|
    | 0    1    4   ... (k-1)^2|
    | ...                       |
    | 0    1  α^{k+m-2} ...    |

Coded: c = V · d
  c_0 = d_0                          (data)
  c_1 = d_1                          (data)
  ...
  c_{k-1} = d_{k-1}                  (data)
  c_k   = d_0 + d_1·α + ... + d_{k-1}·α^{k-1}  (parity)
  ...
```

Decoding: given any k of the k+m coded symbols, form a k×k submatrix of V, invert it in GF(2^w), and multiply to recover the original data. Matrix inversion in GF(2^w) uses Gaussian elimination (addition = XOR, division = multiplication by inverse via log/antilog tables).

### Performance Considerations

| Technique | Description | Speedup |
-----------|-------------|---------|
| **Cauchy Reed-Solomon** | Replace Vandermonde with Cauchy matrix; all ops become XOR | 2-4× over standard RS |
| **ISA-L (Intel)** | SIMD-optimized GF(2^8) multiplication using AVX2/AVX-512 | 10-50 GB/s per core |
| **Jerasure** | Popular C library with GF(2^8) and GF(2^16) support | Baseline |
| **liberasurecode** | Ceph's pluggable EC backend | Depends on backend |

Cauchy Reed-Solomon is preferred in production (Ceph, HDFS) because the encoding matrix can be constructed so that every element is 0 or 1, meaning the encoding operation is pure XOR — no finite-field multiplications needed at all for encoding. Decoding still requires inversion.

## Local Reconstruction Codes (LRC)

### Motivation

Standard (k, m) RS can reconstruct from *any* k of k+m fragments, but requires reading k fragments for *every* single failure. In a (10, 4) RS scheme, a single disk failure requires reading 10 fragments to reconstruct. LRC adds **local parity groups** so that a single failure can be recovered from a small subset.

### LRC Structure

```
(k, l, m) LRC:  k data + l local parities + m global parities

Example: (12, 2, 2) LRC (used by Azure)

  Group 0:  d0  d1  d2  d3  d4  d5  |  LP0 (local parity for group 0)
  Group 1:  d6  d7  d8  d9  d10 d11 |  LP1 (local parity for group 1)

  Global:   GP0  GP1  (parity across ALL 12 data blocks)

  Total: 12 + 2 + 2 = 16 fragments
  Fault tolerance: 2 failures (any combination)

  1-failure reconstruction cost:
    RS(12,4): read 12 fragments
    LRC(12,2,2): read 6 fragments (one local group)

  2-failure reconstruction cost:
    RS(12,4): read 12 fragments
    LRC: depends on failure pattern
      - 2 failures in same group: read 6 (local) + 1 (cross-group) = 7
      - 1 per group: use global parity, read 12
```

### LRC Trade-offs

| Metric | RS(12,4) | LRC(12,2,2) |
|--------|----------|-------------|
| Storage overhead | 1.33× (16/12) | 1.33× (16/12) |
| Single-failure repair bandwidth | 12 fragments | 6 fragments |
| Double-failure repair (worst) | 12 fragments | 12 fragments |
| Encoding CPU | O(k·(k+m)) | O(k·l + k·m) |
| Cross-rack repair traffic | High (any k nodes) | Lower (local group often on same rack) |

LRC is used in production by **Microsoft Azure Storage** (Huang et al., SIGMOD 2012) and **Facebook's f4** system. The key insight is that most failures are single-disk, and LRC dramatically reduces the *repair bandwidth* for the common case.

## Regenerating Codes

### Problem Statement

In distributed storage, **repair bandwidth** — the amount of data transferred during failure recovery — is often the bottleneck, not storage capacity. Regenerating codes (Dimakis et al., IEEE Trans. Info. Theory 2010) optimize specifically for minimum repair bandwidth.

### Trade-off: Storage vs Repair Bandwidth

For a system storing a file of size M across n nodes that can tolerate any n-k failures:

```
Optimal point               Storage per node      Repair bandwidth per node
Minimum storage regenerating (MSR)   M/k                  2·M/(k·(n-k))  [theoretical min]
Minimum bandwidth regenerating (MBR)  2·M/n                M/k

Actual (n=6, k=4, M=1):
  RS(4,2):  storage/node = 1/4,  repair = 4/4 = 1.0
  MSR:      storage/node = 1/4,  repair = 2/(4·2) = 0.25  (4× less)
  MBR:      storage/node = 2/6 = 0.33, repair = 1/4 = 0.25
```

MSR achieves the same storage efficiency as RS but reduces repair bandwidth by a factor of ~k/2 in the best case. MBR trades slightly more storage for the same repair bandwidth as MSR. In practice, regenerating codes have high encoding/decoding complexity and are not widely deployed in production storage systems (RS and LRC dominate), but they are active research.

### Practical Regenerating Codes

- **Product-matrix (PM) codes**: A specific construction that achieves the MBR point and has practical encoding. Used in some research prototypes.
- **Butterfly codes**: Another explicit construction for regenerating codes.
- **Why not in production?**: The algebraic complexity, lack of SIMD-optimized libraries (unlike ISA-L for RS), and the requirement that helper nodes transmit *different linear combinations* to each newcomer make deployment difficult. LRC is a practical middle ground.

## Fountain Codes

### Motivation

Unlike RS/LRC which have fixed (k, m) parameters, **fountain codes** generate an unlimited stream of encoded symbols from the source data. The decoder needs *any* k symbols to reconstruct, regardless of which symbols were received. This makes them ideal for unreliable channels where symbols may be lost at random (UDP multicast, satellite, mobile networks).

### LT Codes (Luby Transform)

```
Encoding:
  1. Pick degree d with probability ρ(d)  (Soliton distribution)
  2. Choose d random input symbols
  3. Output = XOR of those d symbols
  4. Repeat indefinitely (fountain)

Decoding:
  1. Find an encoded symbol with degree 1 → recover its input symbol
  2. XOR this value into all other encoded symbols containing it (degree reduction)
  3. Repeat until all input symbols recovered
  4. May need ~k·(1+ε) symbols to decode with high probability

Soliton distribution ρ(d):
  ρ(1) = 1/k
  ρ(d) = 1/(d·(d-1))  for d = 2, 3, ..., k
  (modified/robust soliton adjusts for practical decoding)
```

LT codes have O(k·log(k)) encoding/decoding complexity. With ~k + O(sqrt(k)·log²(k/δ)) received symbols, decoding succeeds with probability ≥ 1-δ.

### Raptor/RQ Codes

Raptor codes (Shokrollahi, 2006) add a **pre-coding** stage (typically a systematic code) before LT encoding. This eliminates the error floor problem of LT codes and guarantees constant decoding complexity.

```
Pre-code:  k input symbols → k intermediate symbols (systematic + some redundancy)
LT encode: intermediate symbols → unlimited fountain output

Result: O(k) decoding complexity (linear time), practical for k in millions
```

RaptorQ (RFC 6330) is the most advanced variant, used in:
- **3GPP multimedia broadcast/multicast services (MBMS)**
- **DVB-IPTV**
- **Google's QUIC** (loss recovery for FEC frames)
- **Filecoin** (encoding data for proofs of storage)

> **Interview Angle**: "Why doesn't S3 use fountain codes?" Fountain codes are rateless (good for lossy channels) but don't provide fixed redundancy ratios. S3 needs *exactly* 2-failure or 4-failure tolerance with known overhead. RS and LRC give exact (k, m) guarantees. Fountain codes are better for streaming over unreliable networks.

## Replication vs Erasure Coding: Comprehensive Comparison

### Operational Comparison

| Dimension | 3× Replication | RS(6,3) | LRC(12,2,2) |
-----------|---------------|---------|-------------|
| Storage overhead | 3.0× | 1.5× | 1.33× |
| Fault tolerance | 2 failures | 3 failures | 2 failures |
| Read latency (no failure) | 1 disk seek | 1 disk seek | 1 disk seek |
| Read latency (1 failure) | 1 disk seek (other replica) | Read 6, decode | Read 6 (local group) |
| Write latency | 2 round trips (sync) | Encode + write 9 | Encode + write 16 |
| Write CPU | Negligible | Moderate (GF mul) | Moderate |
| Full rebuild bandwidth | 1× data size | 6/9 data | 6/16 data (single failure) |
| Small-file suitability | Excellent | Poor (stripe overhead) | Poor |
| Random-read suitability | Excellent | Poor (read k fragments) | Poor |
| Degraded read perf | Excellent | Degrades significantly | Moderate |
| Complexity | Low | Medium | High |

### Decision Framework

```
Choose REPLICATION when:
  ✓ Small objects (< 1 MB)
  ✓ Random read / write workloads
  ✓ Low-latency reads required
  ✓ Write-heavy workload
  ✓ Simplicity and reliability are paramount

Choose ERASURE CODING when:
  ✓ Large objects (> 1 MB, ideally > 100 MB)
  ✓ Sequential read workload (analytics, backup, media)
  ✓ Storage cost is the primary concern
  ✓ Write-once, read-many pattern
  ✓ W-content is acceptable for degraded reads

Choose LRC specifically when:
  ✓ Network repair bandwidth is the bottleneck (cross-rack, cross-AZ)
  ✓ Single-disk failure is the dominant failure mode
  ✓ You need RS-level storage efficiency with better repair
```

### Production Deployments

| System | Default EC Scheme | Notes |
--------|-------------------|-------|
| Ceph (Reef) | 3× replication (hot), EC pool (cold) | Per-pool policy |
| HDFS 3.x | RS-6-3-1024k | Stripe-based, CPU-intensive |
| Azure Storage | LRC(12,2,2) | Original LRC paper system |
| S3 | RS + LRC variants | Per-storage-class policy |
| MinIO | RS(4+2) to RS(12+4) | Per-erasure-set, bitrot hash |
| Facebook f4 | LRC variants | Warm storage tier |
| GCS | RS-like | Not publicly documented |

> **Interview Angle**: "Design a storage tiering strategy for a photo-sharing app." Hot: 3× replication on NVMe for recent uploads (low-latency reads). Warm: 3× replication on HDD after 30 days. Cold: RS(6,3) or LRC after 90 days. Archive: RS(10,4) after 1 year. The transition is gradual, with a background tiering process that moves objects and updates the metadata store. Avoid EC for the hot tier because users browse recent photos randomly (degraded read penalty).
