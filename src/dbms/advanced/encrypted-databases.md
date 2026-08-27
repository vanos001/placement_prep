# Encrypted Databases & Secure Query Processing

"Is the database encrypted?" is a question with three different yes answers --
at rest, in transit, in use -- and only the first two are ever free. This page
maps the schemes that try to answer the third one (CryptDB's SQL-aware
encryption, SGX enclave execution, searchable encryption, homomorphic
encryption), what each one leaks, and what production systems actually deploy
in 2026.

Related pages: [Intel SGX](../../cryptography/intel-sgx.md) for the hardware
mechanics, [Confidential Computing](../../linux/security/confidential-computing.md)
for TDX/SEV-SNP virtualization, [Homomorphic Encryption](../../llm/advanced/homomorphic-encryption.md)
for the wider crypto landscape.

## Three threat models, three protections

```text
  protection      what stops it            who still sees plaintext
 --------------  -----------------------   -------------------------------
  in transit      network attacker,        endpoints (both sides)
  (TLS)           wire taps

  at rest         thief with the disk,     anyone who can query the running
  (TDE)           leaked backup volume     DB; the OS; the DBA

  in use          nobody, by default       the DBMS process itself (and
  (the gap)       ---                      via it: the DBA, dumps, memory)
```

The adversary for "in use" is the *curious operator*: a cloud admin, a
compromised host, an outsourced DBA, or a forensic image of a live machine.
Nothing in the classic stack protects data while the DBMS is evaluating a
query over it, because query execution needs plaintext (or something that
behaves like it). Every scheme below is a different answer to: **how little
plaintext does the server actually need?**

## TDE: page-level encryption and its blind spot

Transparent Data Encryption is the industry baseline (SQL Server and Oracle
for over a decade; MySQL InnoDB tablespace encryption via keyring plugins;
PostgreSQL has historically relied on volume encryption and the pg_tde
extension rather than a native feature). The mechanism is simple and coarse:

- Each database page is encrypted with a symmetric key; that key is wrapped by
  a KEK held in a KMS/HSM outside the database.
- The storage layer decrypts a page as it is read into the buffer pool and
  encrypts on write. Nothing above the storage layer ever sees ciphertext.

What TDE protects: a stolen SSD, a mislaid backup, a snapshot copied to
another account. What it does **not** protect: any SQL session, the buffer
pool, heap dumps, replication streams, or the DBA. It is binary (whole page,
whole database) -- no per-column, per-query, or per-user granularity -- and it
is unrelated to access control. In interviews the trap is claiming TDE
protects against a compromised application account: it does not, because the
DB happily hands that session decrypted rows.

## CryptDB: SQL-aware encryption with onion layers

CryptDB (Popa, Redfield, Zeldovich, Balakrishnan -- ACM CCS 2012) was the
first system to make "run most of SQL over ciphertext" practical, by encrypting
each column with a *stack* of increasingly weak-but-more-computable schemes
("onions") and adjusting per query:

```text
   onion chains for one column (outermost = strongest, runs fewest ops)

   ORD onion:   RND (randomized AES) -> DET (deterministic) -> OPE
                -> equality, then <, >, BETWEEN, ORDER BY, MIN/MAX
   ADD onion:   HOM (Paillier, additive) -> SUM, COUNT, AVG
                (a parallel chain, peeling does not weaken ORD)
```

- The server can always evaluate a query whose predicates the column's current
  outer layer supports; when a query needs more, the trusted proxy returns the
  layer key (keys chain from the user's password, so the server alone cannot
  peel), and the column is adjusted for all future queries.
- Adjustable privacy is also the leakage model: after a range query has run,
  that column is at OPE and the server learns order and frequency of values;
  DET columns leak which rows share a value (equality patterns).
- Follow-up cryptanalysis sharpened the point: OPE plus known input
  distributions leaks enough to recover much of a low-entropy column, so
  CryptDB's practical safety depends on columns having high min-entropy.

CryptDB itself stayed a research system, but its vocabulary (deterministic vs
order-preserving vs homomorphic layers, adjust-on-demand) is how the industry
still reasons about encrypted columns.

## TEEs: run the DBMS inside the enclave

The hardware answer inverts the problem: instead of making computation
crypto-compatible, hide the plaintext inside a CPU-protected memory region.
Intel SGX enclaves encrypt the enclave's memory pages and measure their
contents, so a hostile OS or hypervisor cannot read or tamper with them.

- **Opaque** (Zheng et al., USENIX NSDI 2017) runs distributed analytics over
  encrypted data inside SGX and is the canonical citation for its main lesson:
  an enclave alone is not enough. "Controlled-channel" attacks observe *page
  fault patterns* and recover access patterns -- so Opaque adds **oblivious
  operators** (sorting and aggregation whose memory access sequence is
  data-independent), trading an extra log-factor of work for hiding the
  access pattern.
- **StealthDB** (Bajaj & Sion, PoPETs 2019) applied the same idea to full SQL
  over SQLite inside SGX, with sensitivity to the page-granular leakage that
  remains.
- **Always Encrypted with secure enclaves** (SQL Server 2019+, Azure SQL on
  SGX-capable DC-series VMs) is the production incarnation: columns stay
  encrypted (randomized AES) even at rest and in the buffer pool; pattern
  matching, range comparisons, and sorting are evaluated inside the enclave.
  This is the first mainstream DB feature in this family.

The caveats are permanent fixtures of the interview answer: enclave memory is
small and slow (EPC is tens of MB per socket on older SGX generations), so
working sets spill and slow down; side channels (timing, cache, page-fault)
are mitigated, not eliminated; and a TEE protects *processes*, not *people
with legitimate query access*.

## Searchable encryption: indexes over ciphertext, and what they leak

Searchable symmetric encryption (SSE) lets a server answer keyword queries
without seeing the documents: the client stores documents encrypted, plus an
index mapping `HMAC(term) -> encrypted posting list`; queries send the
trapdoor `HMAC(term)`; the server returns matching ids. The scheme can be
cryptographically strong and still leak, structurally:

- **search pattern**: identical queries are recognizable as identical;
- **access pattern**: which (encrypted) documents match each query;
- **volume pattern**: result-set sizes.

Leakage-abuse attacks turned these from theory into harm. IKK (Islam, Kuzu,
Kantarcioglu, NDSS 2012) recovered queried keywords from access patterns given
background knowledge about the corpus. Cash, Grubbs, Perry, Ristenpart (ACM
CCS 2015) coined the term "leakage-abuse attacks" and showed query recovery
with known data, and -- the striking result -- *plaintext recovery* of
encrypted emails using only leakage plus standard Apache access logs as
auxiliary data. The design lesson: leakage definitions, not just
indistinguishability claims, decide whether a deployed encrypted index is
safe.

## Homomorphic encryption: the asymptotic cost wall

- **Partially homomorphic (deployable):** Paillier supports addition over
  ciphertexts (`E(a) * E(b) = E(a+b)`), which is exactly SUM/COUNT/AVG. It is
  what CryptDB's HOM onion uses. Costs are real but bounded: a value an
  8-byte bigint would hold becomes a roughly 256-byte ciphertext at a 2048-bit
  modulus (about 32x expansion), and per-operation software cost is far above
  native arithmetic.
- **Fully homomorphic (qualitative gap):** BFV/BGV (exact) and CKKS
  (approximate) support arbitrary circuits, but each multiplication consumes a
  noise budget; surviving deep circuits needs bootstrapping, and end-to-end
  query evaluation remains orders of magnitude slower than plaintext. Vector
  batching recovers throughput, not latency. For databases this relegates FHE
  to narrow, high-value computations (a private aggregate or threshold over a
  small encrypted table), not OLTP. Microsoft's open-source SEAL library is
  the usual entry point; see also
  [Homomorphic Encryption](../../llm/advanced/homomorphic-encryption.md).

## Scheme comparison

| Scheme | Ops computed server-side | Leakage | Overhead | Maturity |
|---|---|---|---|---|
| TDE (page cipher) | everything (data decrypted at I/O) | none vs attacker w/o keys; everything vs DBA/host | near-native (AES-NI) | universal baseline |
| Deterministic columns (DET) | equality, GROUP BY, JOIN | equality + frequency patterns | near-native | shipping (Always Encrypted DET mode) |
| Order-preserving (OPE) | range predicates, ORDER BY | order + frequency (exploitable on low-entropy data) | near-native, indexable | research caution |
| CryptDB onion stack | SQL subset per current layer | adjusts upward per query (DET/OPE leakage once peeled) | single-digit to tens of percent on TPC-ish work | research system |
| SSE (searchable index) | keyword match via trapdoors | search/access/volume patterns | index size + one hash per term | shipping in niche products |
| TEE enclave DBMS (Opaque/StealthDB/AE-SGX) | full SQL/analytics in enclave | explicit leakage fn; side channels remain | oblivious ops add log factor; EPC pressure | production (Azure SQL enclaves) |
| Paillier (additive HE) | SUM, COUNT, AVG on ciphertext | value-independent, but query metadata | large expansion + slow adds | specialized aggregation |
| FHE (BFV/CKKS) | arbitrary circuits in principle | ciphertext only | orders of magnitude slowdown | pilots only |

## What industry actually does

Layered, pragmatic, and mostly *not* exotic:

1. **Baseline**: TLS everywhere; TDE or volume encryption for data at rest,
   with the KEK in a cloud KMS/HSM and rotation policies. This handles the
   compliance checkbox and the stolen-backup threat, and it is where most
   shops stop.
2. **Field-level application encryption** for the crown-jewel columns
   (AES-GCM in the app, or tokenization for PANs under PCI). The database
   never sees plaintext for those columns -- and correspondingly cannot
   index or filter them usefully; that is the accepted trade.
3. **Always Encrypted** (deterministic mode for equality, enclave-backed
   randomized mode for richer predicates) on SQL Server/Azure SQL when the
   DBA must be excluded from specific columns.
4. **Confidential computing VMs** (AMD SEV-SNP, Intel TDX, AWS Nitro
   Enclaves) running *unmodified* engines: memory is encrypted/hardware-
   attested against the host. In 2026 this is the default practical answer
   to the in-use gap for BYO-DB cloud deployments, because it needs no query
   rewrite -- see
   [Confidential Computing](../../linux/security/confidential-computing.md).

## Failure modes worth quoting in interviews

- "We enabled TDE" answering "can a compromised app account read rows?" --
  no relation; TDE is below SQL, not around it.
- Deterministic encryption on a low-cardinality column (status, zip code) is
  effectively a codebook: an attacker with a handful of known pairs inverts
  the whole column.
- Enclave deployed without oblivious operators re-introduces controlled-
  channel leakage -- the exact lesson of the Opaque paper.
- Keys and data in the same trust domain (KMS IAM role assumable by the same
  host) reconstructs the original threat model with extra steps.
- Searchable-encryption deployments judged by their crypto, not their
  leakage -- the CCS 2015 attacks need no key, only logs.

## Interview questions

- Contrast at-rest, in-transit, and in-use protection with one concrete
  attacker defeated by each and one attacker defeated by none of them.
- Your CTO proposes encrypting all columns with OPE so range queries keep
  working. What do you say? (Frequency leakage; low-entropy columns;
  prefer enclave-backed randomized encryption or accept app-side filtering.)
- Why does Opaque need *oblivious* sort inside SGX? (Controlled-channel
  page-fault attacks recover access patterns; obliviousness makes the access
  sequence data-independent.)
- Which of these schemes let the server compute SUM without seeing values?
  (Paillier/HOM; FHE; TEE if the enclave is trusted as "not the server".)

## References

1. Popa, Redfield, Zeldovich, Balakrishnan - CryptDB: Protecting Confidentiality with Encrypted Query Processing (ACM CCS 2012): <https://doi.org/10.1145/2382196.2382224>
2. Zheng, Dave, Beekman, Popa, Gonzalez, Stoica - Opaque: An Oblivious and Encrypted Distributed Analytics Platform (USENIX NSDI 2017): <https://www.usenix.org/conference/nsdi17/technical-sessions/presentation/zheng>
3. Cash, Grubbs, Perry, Ristenpart - Leakage-Abuse Attacks Against Searchable Encryption (ACM CCS 2015): <https://doi.org/10.1145/2810103.2813700>
4. Islam, Kuzu, Kantarcioglu - Access Pattern Disclosure on Searchable Encryption (NDSS 2012): <https://www.ndss-symposium.org/ndss2012/access-pattern-disclosure-searchable-encryption-ramification-attack-and-mitigation>
5. Microsoft - Always Encrypted (Database Engine) documentation: <https://learn.microsoft.com/en-us/sql/relational-databases/security/encryption/always-encrypted-database-engine>
