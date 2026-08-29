# Dataset Deduplication for LLM Training: MinHash, Exact Substring, and Semantic Filtering

Pretraining corpora contain far more redundancy than raw byte counts suggest. Lee et al. measured that over 1% of the unprompted output of models trained on C4 and LM1B is copied verbatim from training data, and that a single 61-word English sentence survives more than 60,000 repetitions inside C4 [1]. The downstream damage is well documented: a sequence present 10 times in training is generated roughly 1000x more often than one present once (memorization scales ~quadratically in duplicate count) [4], and train-test overlap contaminates over 4% of standard validation sets [1]. This page covers the dedup stack run before an LLM training job -- exact document hashing, MinHash + LSH near-duplicate detection, suffix-array substring excision, embedding-based semantic clustering -- with the estimator math, tuning knobs, and the economics of deleting data you should not delete.

For the storage-side cousin (block-level dedup in content-addressed systems), see [Storage-Level Deduplication](../../storage/advanced/dedup-cas.md); for Bloom filters and HyperLogLog, see [Probabilistic Data Structures](../../interview/system-design/probabilistic-data-structures.md). MinHash answers a different question than both: "how similar are these two sets?"

## The dedup ladder: cheapest test first

Each stage is more expensive per document but catches what the previous one missed; cheap O(1)-per-doc stages run before O(n^2)-shaped ones.

```text
   raw corpus (N docs)
        |  [1] exact doc hash: SHA-256 of normalized text; keep one per hash
        v
        |  [2] near-doc dedup: MinHash (k perms) + LSH bands -> verify J >= tau
        v
        |  [3] exact substring: suffix array over corpus; cut repeats >= 50 tok
        v
        |  [4] semantic dedup: embed + cluster; drop near-identical members
        v
        |  [5] contamination filter: same n-gram tools aimed at TEST sets
        v
   final training mix
```

## Shingles, Jaccard, and MinHash signatures

Reduce document similarity to **set** similarity: split each document into 5-gram (or 13-gram) shingles, then `J(A, B) = |A n B| / |A u B|`, the Jaccard coefficient (0 = disjoint, 1 = identical). One swapped word in a 48-word document destroys every 5-gram covering that position -- why near-dup detection runs on shingle sets, not file hashes. All-pairs Jaccard over 1B documents is ~5 x 10^17 set intersections, so stage 2 exists to avoid computing most of them.

Hash each shingle to a 64-bit integer; for permutation i, the MinHash of a set is `min_i h(shingle)`. For a uniformly random permutation, the probability two sets agree on their minimum is exactly J, so with k independent permutations:

```text
J_hat = (# agreeing signature rows) / k
Var(J_hat) = J(1 - J) / k   ->   std <= 1 / (2 * sqrt(k))
```

The error shrinks as ~1/sqrt(k) and near the extremes. Affine hashes `h(x) = (a*x + b) mod p` over a large prime p stand in for true random permutations -- what the demo implements. k = 64 caps the std at 0.063; k = 256 at 0.031.

| Permutations k | Max std = 1/(2*sqrt(k)) | Std at J=0.7 | Signature size (64-bit words) |
|---|---|---|---|
| 16 | 0.125 | 0.115 | 16 |
| 64 | 0.063 | 0.057 | 64 |
| 128 | 0.044 | 0.041 | 128 |
| 256 | 0.031 | 0.029 | 256 |

Scale check: MassiveText held ~2.35B documents and 10.5 TB of raw text [2]; 64-word signatures alone cost ~1.2 TB (2.35B x 512 bytes) before any shingle storage -- one reason banding and streaming variants matter.

## LSH banding: the S-curve you can tune

Split the k-row signature into b bands of r rows (b * r = k); two documents become **candidates** if any full band matches exactly. For a pair with true Jaccard J:

```text
P(band matches)       = J^r
P(pair is candidate)  = 1 - (1 - J^r)^b      ->  inflection ~ (1/b)^(1/r)
```

| True Jaccard J | P(candidate), b=16 r=4 |
|---|---|
| 0.2 | 0.025 |
| 0.4 | 0.340 |
| 0.5 | 0.644 |
| 0.6 | 0.891 |
| 0.8 | 1.000 |

The transition is steep: banding is a soft threshold at `(1/b)^(1/r)` and pairs near that value are a genuine gray zone (see d3-d5 below). To target threshold tau with chosen r, set `b = tau^(-r)`: tau = 0.7 with r = 6 gives b = 0.7^-6 = 8.5, so 8-9 bands.

| Bands b | Rows r | Threshold ~ (1/b)^(1/r) | Profile |
|---|---|---|---|
| 32 | 2 | 0.177 | recall-heavy; floods verification with candidates |
| 16 | 4 | 0.500 | balanced default |
| 10 | 6 | 0.681 | conservative; fewer wasted verifications |
| 8 | 8 | 0.771 | near-duplicate docs only |

False candidates cost one exact set-intersection check (cheap); false negatives silently leak duplicates into training (costly). That asymmetry argues for erring toward smaller r.

## Runnable demo: MinHash + LSH from scratch

Pure stdlib. Six documents: d1 = d0 with one word swapped, d2 = an exact copy of d1, d5 shares a 27-word span with d3, d4 is unrelated. Stage 1 collapses (d1, d2) before MinHash ever runs.

```python
# MinHash + LSH near-duplicate detection from scratch (stdlib only).
# Six docs: d1 = d0 with one word swapped, d2 = exact copy of d1,
# d5 shares a 27-word span with d3, d4 is unrelated. Three stages.
import hashlib
import random

P0 = ("the data pipeline ingests raw web text and applies quality filters "
      "before training document level hashing removes byte identical pages "
      "near duplicate detection then estimates pairwise overlap for every "
      "surviving document suffix arrays later excise long verbatim "
      "substrings semantic embeddings cluster the remaining corpus and "
      "expose redundant topics")
D = {"d0": P0,
     "d1": P0.replace("byte identical", "bit identical"),
     "d3": ("the web crawler fetches pages from a frontier queue respecting "
            "robots directives content extraction strips boilerplate navigation "
            "and scripts language identification drops pages outside the target "
            "locale the crawler stores responses with checksums and revisits "
            "popular hosts at a bounded crawl rate to stay polite"),
     "d4": ("quantization maps float32 weights to lower bit integers per channel "
            "scales are calibrated on activation statistics collected from a "
            "small held out set post training quantization needs no retraining "
            "but loses accuracy at four bits quantization aware training "
            "inserts fake quantize nodes so the model learns rounded weights")}
D["d2"] = D["d1"]                                    # exact duplicate of d1
D["d5"] = (" ".join(D["d3"].split()[:27]) +
           " the archive also records fetch timestamps provenance and host "
           "level politeness delays for audits")
IDS = sorted(D)
N, K, BANDS, ROWS = 5, 64, 16, 4                     # shingles, perms, banding
P = (1 << 61) - 1
rng = random.Random(123)
A = [rng.randrange(1, P) for _ in range(K)]
B = [rng.randrange(P) for _ in range(K)]

def shingles(text):
    w = text.split()
    return {int.from_bytes(hashlib.md5(" ".join(w[s:s + N]).encode()).digest()[:8],
                           "big") for s in range(len(w) - N + 1)}

SH = {i: shingles(D[i]) for i in IDS}
SIG = {i: [min((a * h + b) % P for h in SH[i]) for a, b in zip(A, B)] for i in IDS}

print("Stage 1 -- exact document hash (SHA-256 of normalized text)")
groups = {}
for i in IDS:
    groups.setdefault(hashlib.sha256(D[i].encode()).hexdigest(), []).append(i)
for h, g in sorted(groups.items(), key=lambda kv: kv[1]):
    print(f"  {g[0]}  sha256={h[:16]}...  docs={g}")

print("\nStage 2 -- MinHash (k=64 permutations, 5-gram shingles)")
print(f"  {'pair':<7}{'|A|':>4}{'|B|':>4}{'J true':>9}{'J est':>8}{'|err|':>8}")
worst = 0.0
for a in range(6):
    for b in range(a + 1, 6):
        i, j = IDS[a], IDS[b]
        jt = len(SH[i] & SH[j]) / len(SH[i] | SH[j])
        je = sum(x == y for x, y in zip(SIG[i], SIG[j])) / K
        worst = max(worst, abs(je - jt))
        print(f"  {i}-{j}  {len(SH[i]):>3} {len(SH[j]):>3}  {jt:8.3f} {je:8.3f}"
              f" {abs(je - jt):8.3f}{' <' if je >= 0.5 else ''}")
print(f"\n  max |J_est - J_true| over 15 pairs: {worst:.3f}"
      f"  (theory: ~0.5/sqrt(64)=0.062)")

buck = {}
for bi in range(BANDS):
    for i in IDS:
        buck.setdefault((bi, *SIG[i][bi * ROWS:(bi + 1) * ROWS]), []).append(i)
cand = {tuple(sorted((m1, m2))) for v in buck.values()
        for n, m1 in enumerate(v) for m2 in v[n + 1:]}
truth = {tuple(sorted((i, j))) for x, i in enumerate(IDS) for j in IDS[x + 1:]
         if len(SH[i] & SH[j]) / len(SH[i] | SH[j]) >= 0.5}
print("\nStage 3 -- LSH banding (b=16 bands, r=4 rows, threshold~(1/b)^(1/r)=%.3f)"
      % (1 / BANDS) ** (1 / ROWS))
print(f"  candidate pairs from shared bands: {sorted('-'.join(p) for p in cand)}")
print(f"  ground-truth pairs with J >= 0.5: {sorted('-'.join(p) for p in truth)}")
print(f"  missed by LSH: {sorted('-'.join(p) for p in truth - cand) or 'none'}")
print(f"  false-positive candidates: {sorted('-'.join(p) for p in cand - truth) or 'none'}")
```

Output (real run of the script above):

```text
Stage 1 -- exact document hash (SHA-256 of normalized text)
  d0  sha256=c11ef2e1b7feff70...  docs=['d0']
  d1  sha256=1ffc1494183909be...  docs=['d1', 'd2']
  d3  sha256=f13b9f81d32abfbf...  docs=['d3']
  d4  sha256=b902198d0896fb30...  docs=['d4']
  d5  sha256=57b620c2adca18ce...  docs=['d5']

Stage 2 -- MinHash (k=64 permutations, 5-gram shingles)
  pair    |A| |B|   J true   J est   |err|
  d0-d1   44  44     0.796    0.797    0.001 <
  d0-d2   44  44     0.796    0.797    0.001 <
  d0-d3   44  41     0.000    0.000    0.000
  d0-d4   44  44     0.000    0.000    0.000
  d0-d5   44  37     0.000    0.000    0.000
  d1-d2   44  44     1.000    1.000    0.000 <
  d1-d3   44  41     0.000    0.000    0.000
  d1-d4   44  44     0.000    0.000    0.000
  d1-d5   44  37     0.000    0.000    0.000
  d2-d3   44  41     0.000    0.000    0.000
  d2-d4   44  44     0.000    0.000    0.000
  d2-d5   44  37     0.000    0.000    0.000
  d3-d4   41  44     0.000    0.000    0.000
  d3-d5   41  37     0.444    0.484    0.040
  d4-d5   44  37     0.000    0.000    0.000

  max |J_est - J_true| over 15 pairs: 0.040  (theory: ~0.5/sqrt(64)=0.062)

Stage 3 -- LSH banding (b=16 bands, r=4 rows, threshold~(1/b)^(1/r)=0.500)
  candidate pairs from shared bands: ['d0-d1', 'd0-d2', 'd1-d2']
  ground-truth pairs with J >= 0.5: ['d0-d1', 'd0-d2', 'd1-d2']
  missed by LSH: none
  false-positive candidates: none
```

How to read it:

- **Stage 1 catches d2 for free.** The near-dup cluster (d0, d1) survives, but the byte-identical d2 never reaches MinHash. MassiveText ran this stage on every subset except Wikipedia and GitHub [2].
- **The estimator is tight.** d0-d1: true 0.796, estimated 0.797; worst error across 15 pairs is 0.040, inside the k=64 bound of 0.063.
- **The gray zone is visible, not hypothetical.** d3-d5 has true J = 0.444, just under the 0.5 inflection; the S-curve puts its detection probability at 0.470 -- a coin flip. This seed happened to leave it out. In production, tune (b, r) around the policy threshold or verify gray-zone candidates exactly.

## Exact substring dedup: suffix arrays over the concatenated corpus

Document-level dedup misses documents that share a paragraph but differ elsewhere. Lee et al.'s ExactSubstr concatenates the whole corpus into one giant string, builds a suffix array over it (linear-time construction), and uses the LCP structure to surface spans occurring verbatim more than once [1]. Any repeated span of at least **k = 50 tokens** is removed from one copy -- a deliberately conservative bound: the statistical "knee" of accidental repetition sits near 10 tokens, manual inspection found no false positives at length 25, and the authors doubled it for margin.

Verified scale numbers: ExactSubstr removes **7.18% of the tokens in C4** while deleting zero whole documents; MinHash-based NearDup finds 1.8M near-dup clusters that are single pairs in C4, but also 280 clusters with over 5,000 members, the largest holding 250,933 documents; 77% of examples NearDup removes also contain a verbatim length-50 match -- the two stages overlap but do not replace each other [1].

## Semantic dedup: clustering embeddings

Syntactic dedup cannot see that two differently-worded reviews say the same thing. SemDeDup embeds every item with a foundation model (CLIP for images, OPT for text), runs k-means (k = 50,000 clusters on a LAION subset; k = 11,000 on C4), then within each cluster drops pairs whose cosine similarity exceeds `1 - epsilon` [3]. Clustering tames the quadratic: naive all-pairs over 440M items is ~1.9 x 10^17 similarity computations, while per-cluster comparison costs O(n^2/k). Headline result: removing **50% of LAION-440M** left performance essentially intact and halved training time, and out-of-distribution performance improved [3]. `epsilon` is the aggressiveness dial; the kept-fraction-vs-epsilon curve is nearly linear, so tuning on 10% of clusters takes minutes. For practical embedding backends, sentence-transformers (https://www.sbert.net/) is the standard starting point, and the ANN indexes described in [RAG Advanced](./rag-advanced.md) serve the per-cluster neighbor search.

## What real pipelines shipped

| System | Exact stage | Near-dup stage | Substring stage | Test-set filter |
|---|---|---|---|---|
| MassiveText (Gopher) [2] | exact doc dedup | MinHash, 13-gram Jaccard > 0.8, whitespace-normalized, punctuation ignored; skipped for Wikipedia/GitHub | none documented | 13-gram Jaccard > 0.8 vs Wikitext103, C4, Curation Corpus, LAMBADA |
| C4 + Lee et al. tools [1] | none at corpus scale (61-word sentence survived 60,000+ repeats) | NearDup: MinHash, drop whole docs | ExactSubstr: suffix array, spans >= 50 tokens, 7.18% of C4 tokens | same tooling audited the >4% validation overlap |
| LAION + SemDeDup [3] | exact-duplicate search only | none | none | semantic stage replaces them: CLIP embed, k-means, cosine > 1 - eps |

Two details worth stealing: MassiveText *randomly* picks which of two near-duplicates to drop rather than guessing quality, and Gopher's authors note that test sets built *after* training (like The Pile) can still be leaked -- dedup is asymmetric against contamination you did not know about.

## False-positive economics: what dedup deletes

Every threshold has two failure directions, and they are not symmetric:

- **Under-dedup (keep duplicates).** Cost compounds across epochs and amplifies memorization quadratically [4]; cheap to fix later -- the waste is "only" compute.
- **Over-dedup (delete unique data).** A paraphrase, a corrected fact, or a second independent source can look like a near-duplicate at J = 0.6. Deleting it removes real signal, and you cannot recover it without re-crawling.

Two anchors keep over-dedup honest. First, dropping a document because its *estimated* Jaccard crossed the line acts on a noisy statistic: at k = 64 and true J = 0.7, a 3-sigma miss is ~0.17, so gray-zone pairs need exact verification -- precisely what LSH-then-verify does. Second, uniqueness has diminishing but real returns: Muennighoff et al. found up to **4 epochs of repeated data** costs almost nothing versus unique data, after which extra repetition adds zero value [5]. The optimal policy is not "dedup as hard as possible" but "dedup below the reuse level you intend to train at anyway."

## Train/test contamination: the same tools, opposite polarity

The stack doubles as a contamination auditor, and this is the angle interviewers probe. Gopher's pipeline removes any training document whose 13-gram Jaccard similarity with a test document exceeds 0.8, plus explicit removal of the Wikipedia pages used in Wikitext103 validation/test [2]. Lee et al. frame it as measurement: over 4% of standard validation sets have train overlap, and after dedup the remaining evaluation deltas are attributable to capability rather than recall [1]. The systems point: run contamination filtering *before* spending GPU-hours, and log exact thresholds -- "we deduplicated" is not an answer, "13-gram Jaccard > 0.8 against every eval set" is.

## Interview checks

- **Why LSH instead of comparing all MinHash signatures?** Brute force on signatures is still O(n^2); banding reduces candidates to pairs sharing a band, ~O(n) at low duplicate density, at the price of the S-curve's probabilistic misses.
- **Where does MinHash estimation error bite?** Near the policy threshold: std = sqrt(J(1-J)/k), so a pair at J = 0.55 with k = 64 can flip across a 0.5 boundary -- verify gray-zone candidates exactly, and remember 50-token substring thresholds are calibrated bounds, not guesses [1].
- **When is semantic dedup dangerous?** When diversity is the signal -- e.g., instruction-tuning data. SemDeDup's 50%-removal win on LAION does not transfer blindly to text [3].

Related pages: [Pretraining Data Pipeline](../llm-serving/pretraining.md) (survey-level view of the full crawl -> dedup -> filter -> mix) and [RAG Advanced](./rag-advanced.md) (embedding + ANN machinery reused by stage 4).

## References

1. Lee, Ippolito, Nystrom, Zhang, Eck, Callison-Burch, Carlini -- *Deduplicating Training Data Makes Language Models Better* (ACL 2022). https://arxiv.org/abs/2107.06499 ; https://aclanthology.org/2022.acl-long.577/
2. Rae et al. -- *Scaling Language Models: Methods, Analysis & Insights from Training Gopher* (MassiveText pipeline, Appendix A.1). https://arxiv.org/abs/2112.11446
3. Abbas, Tirumala, Simig, Ganguli, Morcos et al. -- *SemDeDup: Data-efficient learning at web-scale through semantic deduplication*. https://arxiv.org/abs/2303.09540
4. Kandpal, Wallace, Raffel -- *Deduplicating Training Data Mitigates Privacy Risks in Language Models* (ICML 2022). https://arxiv.org/abs/2202.06539
5. Muennighoff, Rush, Barak, Le Scao et al. -- *Scaling Data-Constrained Language Models*. https://arxiv.org/abs/2305.16264
6. Gao et al. -- *The Pile: An 800GB Dataset of Diverse Text for Language Modeling*. https://arxiv.org/abs/2101.00027
7. Raffel et al. -- *Exploring the Limits of Transfer Learning with a Unified Text-to-Text Transformer* (C4). https://arxiv.org/abs/2104.08758
8. google-research/deduplicate-text-datasets -- reference implementation of ExactSubstr and NearDup. https://github.com/google-research/deduplicate-text-datasets
9. sentence-transformers documentation -- embedding models for semantic deduplication. https://www.sbert.net/
