# Approximate Query Processing, Privacy & Provenance

This chapter covers three related areas: (1) approximate query processing using probabilistic data structures, (2) privacy-preserving database techniques, and (3) data provenance and lineage.

## Approximate Query Processing

### When Approximation Is Acceptable

Many analytics queries don't need exact answers. "How many unique users visited today?" can tolerate a 1-2% error if it returns in milliseconds instead of minutes. Approximate query processing (AQP) trades accuracy for speed.

**Use cases**:
- Real-time dashboards (imprecise but fast)
- EXPLAIN plan cardinality estimation
- Network monitoring (distinct flow counting)
- A/B testing (statistical significance doesn't require exact counts)

## Sketches

A sketch is a compact, fixed-size summary of a (potentially infinite) data stream that supports approximate queries. Sketches are **mergeable**: two sketches of the same data can be combined to produce a sketch of the union.

### HyperLogLog (HLL)

HyperLogLog (Flajolet et al., 2007) estimates the **cardinality** (number of distinct elements) of a multiset using O(1) space (typically 1-16 KB) with a standard error of ~1.04/√m.

**Algorithm**:

1. Hash each element to a 64-bit value.
2. Examine the **position of the first 1-bit** (the "rank") in the hashed value.
3. Partition hashes into m = 2^b buckets (using the first b bits).
4. For each bucket, track the **maximum rank** seen.
5. The estimate is a harmonic mean of 2^max_rank across buckets, multiplied by a bias correction.

```python
import hashlib, math

class HyperLogLog:
    def __init__(self, precision=14):  # 2^14 = 16384 buckets
        self.precision = precision
        self.m = 1 << precision
        self.registers = [0] * self.m
        self.alpha_m = self._alpha(self.m)
    
    def add(self, value):
        h = int(hashlib.md5(str(value).encode()).hexdigest(), 16)
        idx = h & (self.m - 1)          # lower b bits → bucket
        w = h >> self.precision          # remaining bits
        rank = self._rho(w) + 1          # position of first 1-bit + 1
        self.registers[idx] = max(self.registers[idx], rank)
    
    def count(self):
        # Harmonic mean of 2^register[i]
        estimate = self.alpha_m * self.m * self.m / \
                   sum(2.0 ** (-r) for r in self.registers)
        # Small/large range corrections omitted for brevity
        return int(estimate)
    
    def _rho(self, w):
        if w == 0: return 64
        return 64 - w.bit_length() + 1
    
    @staticmethod
    def _alpha(m):
        if m == 16: return 0.673
        if m == 32: return 0.697
        if m == 64: return 0.709
        return 0.7213 / (1 + 1.079 / m)
```

**Accuracy**: With 16 KB (m=16384 registers), the standard error is ~0.8%. This is good enough for most cardinality estimation. Redis implements HLL natively (`PFADD`, `PFCOUNT`). BigQuery, PostgreSQL (via `hyperloglog` extension), and ClickHouse all support HLL.

### Count-Min Sketch (CMS)

Count-Min Sketch (Cormode & Muthukrishnan, 2005) estimates the **frequency** of items in a stream:

``n``

```
CMS parameters: width w, depth d
Each element is hashed by d independent hash functions into d rows.

Row 0: [0, 0, 3, 0, 1, 0, ...]  (w counters)
Row 1: [0, 1, 0, 0, 2, 0, ...]
Row 2: [2, 0, 0, 1, 0, 0, ...]
...
Row d-1: [0, 0, 2, 0, 0, 1, ...]

To estimate count(item): min(counter[0][h0(item)], counter[1][h1(item)], ...)

Guarantee: estimate >= true_count (never underestimates)
Error: at most ε × N with probability 1 - δ, where w = ⌈e/ε⌉, d = ⌈ln(1/δ)⌉
```

**Space**: O(w × d) = O(1/ε × ln(1/δ)). For ε=0.01 (1% error) and δ=0.01 (99% confidence): w=272, d=5 → 1360 counters (5.3 KB for 4-byte counters).

**Limitation**: CMS overestimates frequencies (never underestimates). For highly skewed distributions, the overestimate for rare items can be significant. **Count-Mean-Min Sketch** improves this by subtracting the expected noise.

### Reservoir Sampling

Reservoir sampling (Vitter, 1985) maintains a uniform random sample of size k from a stream of unknown length n:

```python
import random

def reservoir_sample(stream, k):
    reservoir = []
    for i, item in enumerate(stream):
        if i < k:
            reservoir.append(item)
        else:
            j = random.randint(0, i)  # inclusive
            if j < k:
                reservoir[j] = item
    return reservoir
```

**Property**: After processing n items, each item has probability k/n of being in the reservoir. O(n) time, O(k) space. Used in **approximate query processing** (sample a table, run the query on the sample, scale up) and **streaming algorithms**.

### Quantile Sketches

Quantile sketches estimate percentiles (median, p99, etc.) of a data stream:

| Sketch | Space | Error | Mergeable | Used In |
--------|-------|-------|-----------|----------|
| **GK (Greenwald-Khanna)** | O(1/ε log(εn)) | ε-rank error | Yes | Java streams, Apache Druid |
| **t-digest** (Ted Dunning) | O(k) centroids | Adaptive (better at tails) | Yes | Elasticsearch, Prometheus |
| **KLL** | O(1/ε × log(log(1/ε))) | ε-rank error | Yes | Apache DataSketches |

#### t-digest

t-digest clusters data into **centroids** (mean + weight). Near the extremes (tails), centroids are small for high precision. Near the median, centroids are larger. This gives **better accuracy at the tails** where it matters most (p99, p99.9):

```
Data: [1, 2, 3, ..., 1000]

Centroids (simplified):
  Near median (500):  [mean=450, weight=100]  [mean=550, weight=100]
  Near tail (p99=990):  [mean=985, weight=5]   [mean=993, weight=3]   [mean=998, weight=2]
```

The compression function ensures no single centroid has weight exceeding a threshold that depends on its quantile position: `max_weight(q) = (4 × k × q × (1-q)) / n`.

### Sampling Joins

Approximate join processing uses samples to estimate join sizes or approximate join results:

- **Join size estimation**: Sample from both tables, compute join on samples, scale by sampling fractions. Only accurate if the join predicate is uncorrelated with the sampling key.
- **Sample-and-resample**: (Chaudhuri et al., 2007) Samples from the smaller table, probes the larger table, and applies bias correction.
- **Iceberg queries**: "Find departments with > 1000 employees" — use HLL to estimate department sizes, only compute the exact count for departments that pass the threshold.

## Probabilistic Databases

A probabilistic database associates each tuple with a **probability** of being in the true database. Queries over probabilistic databases produce **probability distributions** over result tuples.

```
Tuples: (Alice, Engineering, p=0.8), (Alice, Sales, p=0.2)
Query: SELECT dept FROM employees WHERE name = 'Alice'
Result: (Engineering, p=0.8), (Sales, p=0.2)
```

**Semantics**: The two main semantics are **tuple-level independence** (tuples are independent random variables) and **possible worlds** (the database is one of 2^n possible worlds, each with a probability). Queries aggregate over possible worlds, which is #P-hard in general.

**MayBMS** (UC Berkeley) was a research system supporting probabilistic SQL with confidence intervals. In practice, most systems use **confidence intervals** via sampling (e.g., BigQuery's approximate aggregation functions).

## Privacy-Preserving Databases

### Differential Privacy

Differential privacy (Dwork et al., 2006) provides a mathematical guarantee: the output of a query is approximately the same whether or not any single individual's data is included. Formally, a mechanism M satisfies (ε, δ)-differential privacy if:

```
Pr[M(D) ∈ S] ≤ e^ε × Pr[M(D') ∈ S] + δ
```

for all datasets D and D' differing in one row, and all output sets S.

**Laplace mechanism**: Add Laplace noise calibrated to the sensitivity (maximum change in output from one row):

```python
import random, math

def laplace_mechanism(query_result, sensitivity, epsilon):
    noise = random.laplace(0, sensitivity / epsilon)
    return query_result + noise

# Example: COUNT query, sensitivity = 1 (one person changes count by at most 1)
true_count = SELECT COUNT(*) FROM medical_records WHERE disease = 'X'
private_count = laplace_mechanism(true_count, sensitivity=1, epsilon=0.1)
# Noise ~ Lap(0, 10), so result is noisy but provides ε=0.1 privacy
```

**Key insight**: ε (epsilon) controls the privacy-utility tradeoff. ε < 1 is strong privacy; ε > 10 provides weak privacy. δ is the probability of a catastrophic privacy breach (typically set to 1/n²).

**Composition**: Running k queries with (ε, δ)-DP each gives (kε, kδ)-DP. **Rényi DP** and **zCDP** provide tighter composition bounds for complex queries.

**Systems**: Google's **RAPPOR** collects Chrome usage statistics with local differential privacy. Apple uses local DP in iOS analytics. **PINQ** (McSherry, 2009) is a LINQ-like interface that automatically tracks privacy budget.

> **Interview Angle**: "Explain differential privacy in simple terms and give an example." — The key guarantee: adding or removing one person's data doesn't significantly change the query output. Implement by adding calibrated noise. The ε parameter controls how much privacy vs. accuracy you get.

## Secure Query Processing

### Encrypted Databases

The goal: query data that is **encrypted at rest and in transit**, without decrypting it on the server.

#### Searchable Encryption

| Scheme | What it supports | Security | Performance |
--------|-----------------|----------|-------------|
| **Deterministic encryption** | Exact equality (`WHERE name = 'Alice'`) | Reveals equality patterns | Fast (same as hash lookup) |
| **Order-preserving encryption (OPE)** | Range queries (`WHERE age > 30`) | Reveals order | Fast (B-tree on ciphertexts) |
| **Property-preserving encryption (PPE)** | Equality + order | Partial leakage | Fast |
| **Searchable symmetric encryption (SSE)** | Keyword search | Stronger (search tokens) | Moderate |
| **ORAM** | Full access pattern hiding | Strongest | Very slow (log n overheads) |

**CryptDB** (Popa et al., SOSP 2011) uses a layered approach: encrypt columns with the weakest encryption that supports the required operations. For `=`, use deterministic encryption. For `>`, use OPE. For `SUM`, use homomorphic encryption (Paillier). The server never sees plaintext.

### Homomorphic Query Processing

**Fully homomorphic encryption (FHE)** allows arbitrary computation on encrypted data. Gentry's 2009 breakthrough and subsequent improvements (BFV, CKKS, TFHE schemes) make FHE practical for some workloads:

```
Client encrypts: E(x) = encrypt(x)
Server computes: E(x + y) = E(x) ⊕ E(y)  (homomorphic addition)
                E(x × y) = E(x) ⊗ E(y)  (homomorphic multiplication)
Client decrypts: decrypt(E(x + y)) = x + y
```

**Practical limitations**: FHE operations are 10,000-100,000x slower than plaintext. Current use cases are limited to **aggregation** (sum, count) and **simple comparisons**. Microsoft's **SEAL** library and IBM's **HElib** provide open-source implementations. The **Concrete** library offers a compiler from Python to FHE.

**Partially homomorphic encryption (PHE)** is more practical:
- **Paillier**: Supports additive homomorphism (`E(a) × E(b) = E(a+b)`). Used for encrypted aggregation. Only ~10-100x slower.
- **ElGamal**: Supports multiplicative homomorphism. Used in encrypted voting.

### TEE for Databases (Trusted Execution Environments)

A TEE (Intel SGX, ARM TrustZone, AMD SEV) provides a hardware-isolated execution environment. Code and data inside the TEE are protected from the OS, hypervisor, and physical attackers.

```
┌───────────────────────────────┐
│          Untrusted OS        │
│  ┌─────────────────────────┐  │
│  │    Intel SGX Enclave    │  │
│  │  ┌───────────────────┐  │  │
│  │  │  DB Engine (code  │  │  │
│  │  │  + data)          │  │  │
│  │  │  Encrypted memory │  │  │
│  │  └───────────────────┘  │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘

- Data is encrypted in RAM (EPC - Enclave Page Cache)
- Attacker with OS/kernel access cannot read enclave data
- Remote attestation: client verifies the enclave's code hash
```

**Systems using TEEs**:

| System | TEE | Approach | Limitation |
--------|-----|----------|-----------|
| **Cipherbase** (Microsoft) | SGX | Runs SQL engine inside enclave | Limited EPC (128 MB) |
| **EnclaveDB** (Microsoft) | SGX | Encrypted DB with TEE processing | Side-channel attacks |
| **ObliDB** | SGX | ORAM-inspired access pattern hiding | High overhead |
| **VeilDB** | SGX | Encrypted analytics | Performance |
| **CockroachDB** | AWS Nitro Enclaves | Encrypted backup restore | AWS-specific |

**SGX limitations**: EPC (enclave memory) is limited (~128 MB on older CPUs, up to 256 MB on newer). Page faults between EPC and unencrypted memory are expensive. Side-channel attacks (Spectre, Cache-based timing attacks) have been demonstrated against SGX enclaves. AMD SEV encrypts VM memory but doesn't provide enclave-level isolation.

## Database Provenance & Data Lineage

### What is Provenance?

Data provenance (lineage) tracks **where data came from and how it was derived**. For each result tuple, provenance identifies the input tuples that contributed to it.

```
Table A: (1, 'Alice'), (2, 'Bob')
Table B: (1, 100), (2, 200)

Query: SELECT A.id, A.name, B.salary FROM A JOIN B ON A.id = B.id WHERE B.salary > 150

Result: (2, 'Bob', 200)
Provenance: {A: row (2, 'Bob'), B: row (2, 200)}
```

### Lineage Types

| Type | Question Answered | Granularity |
|------|-------------------|-------------|
| **Where-provenance** | Where did this data value originate? | Cell-level |
| **Why-provenance** | Which input tuples contributed to this output? | Tuple-level |
| **How-provenance** | What operations produced this output? | Operation-level |
| **Transformation provenance** | What query/ETL step produced this? | Pipeline-level |

### Lineage in Data Pipelines

In data warehousing and data lakehouse systems (e.g., **Delta Lake**, **Apache Iceberg**), lineage tracks the ETL pipeline:

```
Source: PostgreSQL (users table)
  ↓ Flink job: transform_users
  ↓ Write to: S3 / Delta Lake (dim_users)
  ↓ dbt model: aggregate_user_metrics
  ↓ Write to: BigQuery (user_metrics)

Lineage query: "Which upstream sources affect the user_metrics.daily_active_users column?"
Answer: PostgreSQL.users.id, PostgreSQL.users.last_active_at
```

**OpenLineage** is an open standard for lineage metadata, supported by dbt, Airflow, Spark, and Flink.

## Data Versioning

### Motivation

Data versioning extends Git-like versioning to datasets:

- **Reproducibility**: Re-run an ML model on the exact data version used for training.
- **Auditability**: Track who changed what and when.
- **Rollback**: Revert to a previous version of a dataset.
- **Branching**: Create experimental branches of a dataset.

### Approaches

| Approach | Mechanism | Storage Overhead | Used In |
----------|-----------|-----------------|----------|
| **Copy-on-write snapshots** | Full copy of changed blocks | O(changed data per version) | ZFS, Ceph RBD |
| **Copy-on-write metadata** | Track block pointers per version | O(metadata) | Delta Lake, Iceberg |
| **Append-only with versioning** | New versions are appended, old versions retained | O(total data × versions) | Some data lakes |
| **Delta encoding** | Store only changed rows per version | O(changed rows) | DVC (Data Version Control) |

**DVC (Data Version Control)**: Treats data files as Git-LFS-tracked objects. Metadata (`.dvc` files) tracks the hash and path of each dataset version. Combined with Git for code + DVC for data, it provides reproducible ML experiments.

**Delta Lake / Iceberg**: Store data as immutable Parquet files. Each new version is a new set of Parquet files + a metadata log (JSON/Avro). Time travel (`SELECT * FROM table VERSION AS OF timestamp`) reads the metadata log to reconstruct the table at a given version.

> **Interview Angle**: "How does Delta Lake implement time travel?" — Each write to a Delta table appends a new JSON commit file to the `_delta_log/` directory, listing the added/removed files. To read at a specific version, Delta reads the commit log from the beginning and reconstructs the file list up to that version. Removed files are still on storage (until VACUUM), enabling historical reads.

## Temporal Query Processing

Beyond the temporal databases covered in [temporal-streaming.md](temporal-streaming.md), temporal query processing refers to **querying historical states** of a database:

```sql
-- SQL:2011 temporal query
SELECT * FROM employees
FOR SYSTEM_TIME AS OF '2023-06-01 00:00:00'
WHERE department = 'Engineering';

-- This returns the state of the employees table as of June 1, 2023
```

**Implementation approaches**:

1. **Versioned tables**: Each row has validity period. Query filters on validity. Simple but slow for large tables.
2. **Append-only with current flag**: One row per version; `is_current` flag identifies the active version. Indexes on `(id, is_current)`.
3. **Event sourcing**: Store all changes as an immutable event log. Reconstruct state by replaying events. Used in Kafka-based systems.
4. **Snapshot-based**: Periodic full snapshots + change streams between snapshots. Like a backup strategy applied to query processing.

## References

- Flajolet, P. et al. "HyperLogLog: The Analysis of a Near-Optimal Cardinality Estimation Algorithm." DMTCS, 2007.
- Cormode, G. & Muthukrishnan, S. "An Improved Data Stream Summary: The Count-Min Sketch and Its Applications." JAL, 2005.
- Dwork, C. et al. "Calibrating Noise to Sensitivity in Private Data Analysis." TCC, 2006.
- Popa, R.A. et al. "CryptDB: Protecting Confidentiality with Encrypted Query Processing." SOSP, 2011.
- Dunning, T. & Ertl, O. "Computing Extremely Accurate Quantiles Using t-Digests." arXiv, 2019.
- Interlandi, M. & Shah, M. "Whereprovenance: A General Purpose Tracking System." CIDR, 2020.