# IVF-PQ: Quantized Vector Search at Billion Scale

Billion-scale vector search has two hard budgets: **latency** (how many vectors a query may touch)
and **memory** (how many bytes each vector costs). IVF (inverted file) attacks latency by pruning
the corpus to a few cluster lists; PQ (product quantization) attacks memory by replacing every
float vector with a short code. Jegou, Douze and Schmid combined them in 2011 ("Product
Quantization for Nearest Neighbor Search", TPAMI) and IVF-ADC is still the default billion-scale
configuration shipped in vector engines. This page dissects the quantization machinery itself --
codebooks, ADC, the error it introduces, and the rescoring that fixes it -- with runnable arithmetic.

## The memory wall PQ exists to break

Exact search keeps every vector in full precision. For N = 1 billion vectors at d = 128 dims:

```text
fp32 vectors : 1e9 x 128 dims x 4 B   = 512 GB   (plus 8 B ids = 520 GB)
SQ8 (1 B/dim): 1e9 x 128 B            = 128 GB   (4x smaller)
PQ m=16, 8-bit: 1e9 x 16 B            =  16 GB   (32x smaller)
PQ m=16, 4-bit: 1e9 x 8 B             =   8 GB   (64x smaller)
```

All arithmetic above is exact (GB = 10^9 bytes). Codebook storage is negligible by comparison:
m x 2^nbits x (d/m) x 4 B, e.g. 16 x 256 x 8 x 4 B = 128 KB for the 8-bit scheme. Compression is
not free -- the next sections show exactly what accuracy it costs and how engines buy recall back.

## Product quantization: the codec

Split the d dims into m contiguous slices and quantize each slice against its own small codebook:

```text
d = 16, m = 4 slices, k* = 256 centroids per slice (nbits = 8, one byte per slice)

x   = [ x0  x1  x2  x3 | x4  x5  x6  x7 | x8  x9 x10 x11 | x12 x13 x14 x15 ]
      \____slice 0____/  \____slice 1____/  \____slice 2____/  \____slice 3____/
code  =    [   142   ][       7       ][      203      ][       51      ]   (4 bytes)
x'   =  c0[142] ++ c1[7] ++ c2[203] ++ c3[51]                    (reconstruction)
```

The key property is **combinatorial coverage from tiny codebooks**. The demo below (m = 8 slices,
k* = 16 centroids) stores 8 x 16 = 128 codebook vectors per subspace pool and represents
16^8 = 4.3 billion distinct reconstructions. One d-dimensional vector becomes m bytes.

Trade-offs of the product structure:

- **m must divide d**; each slice gets d/m dims. More slices mean finer quantization per slice but
  a longer code: m x nbits bits per vector.
- **Independent codebooks ignore correlation across slices.** Optimized Product Quantization (OPQ)
  adds a learned rotation before slicing -- the FAISS wiki calls it "a linear transformation of the
  vector space to make it more amenable for indexing with a product quantizer" (He et al., CVPR 2013).
- **Training is per-slice k-means**; a training sample small relative to k* degrades every codebook
  at once (FAISS emits a clustering warning in that case).

## ADC: asymmetric distance computation

The TPAMI paper's central trick: keep the **query** in full precision, quantize only the **database**
vectors. Per query, build one lookup table of squared distances from each query slice to all
centroids of that slice; then a database vector's approximate distance is m table lookups:

```text
LUT (per query)                        candidate x with code [142, 7, 203, 51]
slice 0: [d(q0,c00) .. d(q0,c0255)]    d'(q, x) = LUT[0][142]
slice 1: [d(q1,c10) .. d(q1,c1255)]           + LUT[1][7]
slice 2: [d(q2,c20) .. d(q2,c2255)]           + LUT[2][203]
slice 3: [d(q3,c30) .. d(q3,c3255)]           + LUT[3][51]
LUT build = m * k* distances           per candidate = m adds (vs d mults for exact)
```

At d = 128, m = 16 that is 8x fewer arithmetic ops per candidate, and candidates are 16-byte codes
that stay resident in cache instead of 512-byte vectors streaming from RAM. The alternative
**DCD** (decoded distance computation) reconstructs x' and computes a full distance -- O(d) again,
more accurate, rarely worth it for the scan stage.

The approximation is **biased**: d'(q, x) = d(q, x) plus both sides' quantization noise plus a cross
term -- errors are largest exactly where ranking matters most, the tight top ranks (measured below).

## IVF: the coarse partition

PQ scan over all N codes is still O(N*m). IVF -- the "inverted file" trick vector search inherited
from Video Google's visual-word index (ICCV 2003) -- cuts the scan with a coarse k-means quantizer
of nlist centroids; each vector lands on one inverted list, and a query probes only the nprobe
nearest lists. The FAISS wiki is explicit: "as a first approximation, this fraction is
nprobe/nlist, but this approximation is usually under-estimated because the inverted lists have not
equal lengths", with sizing rule of thumb "nlist = C * sqrt(n)" (C ~ 10) -- near 2^17 at N = 1e9.

## One IVF-ADC query, end to end

```text
query q (fp32, d=128)
  |
  | 1. coarse scan: q vs nlist centroids ......... nlist*d mults (16.8M at nlist=2^17)
  | 2. pick nprobe nearest lists
  | 3. build LUT: q slices vs PQ codebooks ....... m*k* distances (4096 at m=16, k*=256)
  | 4. walk inverted lists, ADC-add per code ..... visited * m adds
  | 5. keep top candidates by d'(q, x)
  | 6. rescore pool with exact fp32 distances .... pool * d mults
  v
top-k results
```

Steps 1-5 answer "which candidates are plausibly close" cheaply and approximately; step 6 answers
"exactly how close" for the few survivors. Memory reads follow the same split: codes and LUT stay
hot, fp32 vectors (if kept at all) are touched only for the rescore pool.

## Recall engineering

| Parameter | What it controls | Raise it for | You pay with |
|-----------|------------------|--------------|--------------|
| nlist | coarse partition granularity | short lists, more selective probes | centroid storage, coarse-scan cost |
| nprobe | lists visited per query | recall | latency, roughly linear in nprobe |
| m (slices) | quantization granularity | lower quantization error | longer codes, more LUT adds |
| nbits | centroids per slice (k* = 2^nbits) | finer codebooks | LUT build cost m*k*, code length |
| rescore pool | exact reranking depth | final recall | fp32 vector access, extra O(pool*d) |

The rescore stage is not optional folklore. FAISS wiki on 4-bit PQ (FastScan): "the 4-bit PQ has a
relatively low accuracy (PQ32x4 is significantly less accurate than PQ16x8 although they use the
same amount of memory), it is useful to perform a re-ranking stage with exact distance
computations". Both schemes spend 16 B per vector at d = 128, but 32 slices of 4 dims fit worse
than 16 slices of 8. Same-axis lineage from the wiki: IVFADC-R / IndexIVFPQR re-ranks with a
source-coded residual (Tavenard et al., ICASSP 2011); Polysemous codes pre-filter with binary codes.

## Model demo: PQ + ADC vs exact scan

Pure-stdlib, deterministic (fixed seeds): trains 8 four-bit codebooks by Lloyd k-means, encodes the
corpus, runs ADC-ranked search against exact brute force, and measures what rescoring buys:

```python
import math
import random

# Deterministic PQ + ADC demo: synthetic clustered vectors, per-subspace
# 4-bit k-means codebooks, asymmetric distance computation (ADC), recall
# vs exact brute force, and recall after a rescore pass.
N, D, M, KS, ITERS = 4000, 16, 8, 16, 8     # vectors, dims, subspaces, centroids, iters
SUB = D // M                                 # dims per subspace (M must divide D)
NQ, TOPK, RESCORE = 60, 10, 200              # queries, recall@K, rescore pool size

rng = random.Random(11)
centers = [[rng.uniform(-10, 10) for _ in range(D)] for _ in range(8)]
data = [[c[i] + rng.gauss(0, 1.0) for i in range(D)]
        for c in (centers[rng.randrange(8)] for _ in range(N))]
queries = [[c[i] + rng.gauss(0, 1.0) for i in range(D)]
           for c in (centers[rng.randrange(8)] for _ in range(NQ))]

def sq_l2(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b))

# One codebook per subspace: Lloyd k-means, seeded deterministic init
mrng = random.Random(7)
books = []
for si in range(M):
    sub = [v[si * SUB:(si + 1) * SUB] for v in data]
    cents = [list(sub[i]) for i in sorted(mrng.sample(range(N), KS))]
    for _ in range(ITERS):
        sums, cnt = [[0.0] * SUB for _ in range(KS)], [0] * KS
        for v in sub:
            j = min(range(KS), key=lambda k: sq_l2(v, cents[k]))
            cnt[j] += 1
            for t, x in enumerate(v):
                sums[j][t] += x
        cents = [[sums[j][t] / cnt[j] if cnt[j] else cents[j][t]
                  for t in range(SUB)] for j in range(KS)]
    books.append(cents)

codes = [[min(range(KS), key=lambda k: sq_l2(v[si * SUB:(si + 1) * SUB], books[si][k]))
          for si in range(M)] for v in data]
recon = [[books[si][codes[i][si]][t] for si in range(M) for t in range(SUB)] for i in range(N)]
err = sum(sq_l2(data[i], recon[i]) for i in range(N)) / N
var = sum(sq_l2(v, [0.0] * D) for v in data) / N
snr_db = 10 * math.log10(var / err)

hits = hits_rs = 0
true_d2 = adc_exc = 0.0
for q in queries:
    exact = sorted(range(N), key=lambda i: sq_l2(q, data[i]))[:TOPK]
    lut = [[sq_l2(q[si * SUB:(si + 1) * SUB], c) for c in books[si]] for si in range(M)]
    adc = sorted(range(N), key=lambda i: sum(lut[si][codes[i][si]] for si in range(M)))
    hits += len(set(adc[:TOPK]) & set(exact))
    rs = sorted(adc[:RESCORE], key=lambda i: sq_l2(q, data[i]))
    hits_rs += len(set(rs[:TOPK]) & set(exact))
    for i in exact:
        de = sq_l2(q, data[i])
        true_d2 += de
        adc_exc += sum(lut[si][codes[i][si]] for si in range(M)) - de
true_d2 /= NQ * TOPK
adc_exc /= NQ * TOPK

print("PQ + ADC demo: N=%d, D=%d dims, m=%d subspaces x k*=%d centroids (4-bit)" % (N, D, M, KS))
print("storage/vector : fp32 = %d B, PQ code = %d B (%dx), codebooks = %d KB" %
      (4 * D, M // 2, (4 * D) // (M // 2), (M * KS * SUB * 4 + 1023) // 1024))
print("quantization SNR: %.1f dB   true top-%d mean sq-dist: %.1f   mean ADC error: +%.1f" %
      (snr_db, TOPK, true_d2, adc_exc))
print("ops/query: exact = N*D = %d   ADC = m*k* + N*m = %d" % (N * D, M * KS + N * M))
print("recall@%d  ADC only: %.2f   ADC + rescore top-%d: %.2f" %
      (TOPK, hits / (NQ * TOPK), RESCORE, hits_rs / (NQ * TOPK)))
```

Real output (byte-identical across reruns):

```text
PQ + ADC demo: N=4000, D=16 dims, m=8 subspaces x k*=16 centroids (4-bit)
storage/vector : fp32 = 64 B, PQ code = 4 B (16x), codebooks = 1 KB
quantization SNR: 17.5 dB   true top-10 mean sq-dist: 13.7   mean ADC error: +4.9
ops/query: exact = N*D = 64000   ADC = m*k* + N*m = 32128
recall@10  ADC only: 0.17   ADC + rescore top-200: 0.89
```

Read the numbers as the whole IVF-PQ story in miniature: quantization noise (mean ADC error +4.9)
is about a third of the true top-10 distance scale (13.7), so ADC-only ranking garbles the top
ranks (recall@10 = 0.17), while a 5% rescore pool (top-200) restores 0.89 because exact distances
are computed only for a shortlist the cheap codes filtered. The op ratio is honest toy-scale (2x at
d = 16); at d = 128, m = 16 it is d/m = 8x per candidate, and the memory ratio changes architecture.

## Where IVF-PQ actually ships

| Engine | PQ support | Verified anchor |
|--------|------------|-----------------|
| FAISS | IndexIVFPQ(quantizer, d, nlist, M, nbits_per_idx) in the C++ API; IndexIVFPQFastScan 4-bit scan | faiss.ai API docs |
| Milvus | IVF_PQ index type; "each codebook contains 2^nbits centroids ... if nbits = 8, each codebook will contain 256 centroids" | Milvus IVF_PQ docs |
| OpenSearch | "Faiss product quantization" listed under vector-search storage optimization ("represent a vector using a configurable number of bits") | OpenSearch docs |
| DiskANN | PQ codes resident in RAM act as the distance oracle while the graph navigates SSD-resident full vectors | see [Vector Databases](../dbms/advanced/vector-databases.md) |
| pgvector | ivfflat and hnsw over fp32/half/binary representations -- **no product-quantized index type** (binary quantization only) | pgvector README |

Adjacent techniques: Google's **ScaNN** treats the quantizer as the search structure with an
anisotropic (rank-aware) objective; **RaBitQ** quantizes to 1-bit-per-dim codes with a provable
error bound. Both ship as encoders/rerankers inside engines rather than standalone indexes.

## Pitfalls

- **Chasing recall with nprobe only.** Past a point, ADC noise caps recall regardless of how many
  lists you visit; the fix is quantization quality (m, nbits) or a deeper rescore pool.
- **Ignoring the coarse-scan cost.** At 1B scale with nlist = 2^17, step 1 alone is ~16.8M
  multiply-accumulates per query -- the largest fixed term in the per-query accounting above. FAISS
  exposes a precomputed-centroid-table mode (nlist x m x k* table) to amortize it.
- **Forgetting id overhead.** Inverted lists store an 8 B id per entry next to each code: 1B ids =
  8 GB on top of 16 GB of codes.
- **Training sample too small for k*.** Every codebook degrades together; sample generously (the
  FAISS clustering warning threshold scales with k*).
- **Metric mismatch.** Codebooks trained on L2 reconstruction error do not rank inner-product
  queries correctly; train on the metric you query, or use an IP-aware variant.

## Cross-references

- [Vector Search](./vector-search.md) -- where IVF/PQ sit in the retrieval pipeline
- [FAISS](../llm/advanced/faiss.md) -- index-type tour and benchmark numbers (this page goes deeper on the codec)
- [Vector Databases](../dbms/advanced/vector-databases.md) -- HNSW/IVF/DiskANN comparison and DiskANN details
- [RAG Advanced](../llm/advanced/rag-advanced.md) -- DiskANN RAM math and rerank pipeline
- [k-NN Classification](../ml/classical/knn.md) -- the exact-search baseline PQ approximates
- [Learned Indexes](../dbms/advanced/learned-indexes.md) -- the "index as model" framing; PQ is the complementary "index as codec" framing

## References

- Jegou, Douze, Schmid, "Product Quantization for Nearest Neighbor Search", IEEE TPAMI 33(1), 2011 -- <https://doi.org/10.1109/TPAMI.2010.57> (crossref-verified; ADC/DCD defined here)
- Sivic, Zisserman, "Video Google: a text retrieval approach to object matching in videos", ICCV 2003 -- <https://doi.org/10.1109/ICCV.2003.1238663> (inverted-file lineage, crossref-verified)
- FAISS wiki, "Faiss indexes" -- <https://github.com/facebookresearch/faiss/wiki/Faiss-indexes> (nlist = C*sqrt(n) rule, IVFADC-R, OPQ, Polysemous)
- FAISS wiki, "Fast accumulation of PQ and AQ codes (FastScan)" -- <https://github.com/facebookresearch/faiss/wiki/FastScan> (4-bit PQ, rerank advice, ScaNN comparison)
- faiss.ai, IndexIVFPQ C++ API -- <https://faiss.ai/cpp_api/struct/structfaiss_1_1IndexIVFPQ.html> (constructor signature, precompute table)
- Milvus, "IVF_PQ" in-memory index docs -- <https://milvus.io/docs/ivf-pq.md>
- OpenSearch, "Faiss product quantization" -- <https://docs.opensearch.org/latest/vector-search/optimizing-storage/faiss-product-quantization/>
- Guo et al., "Accelerating Large-Scale Inference with Anisotropic Vector Quantization" (ScaNN) -- <https://arxiv.org/abs/1908.10396>
- Gao, Long, "RaBitQ: Quantizing High-Dimensional Vectors with a Theoretical Error Bound for Approximate Nearest Neighbor Search" -- <https://arxiv.org/abs/2405.12497>
