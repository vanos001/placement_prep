# Reranking and Hybrid Fusion

A production retrieval path almost never returns stage-1 scores directly. A cheap,
recall-oriented candidate generator (an inverted index for lexical matching, an ANN
index for dense vectors, or both) feeds a costlier stage that **fuses the candidate
rankings into one list and re-scores its top with a better model**. This page is about
that stage: why heterogeneous scores cannot be added naively, how rank-based and
score-based fusion work, what cross-encoders cost, and the recall ceiling that caps all downstream improvement.

Scope note: reranking reorders *candidate lists*; it is not an index structure over
sorted keys. The "index as model" family (B-tree-as-regression, learned filters,
recursive model indexes) is a separate line of work, covered in
[Learned Indexes](../dbms/advanced/learned-indexes.md); the candidate generators are
covered in [Search Fundamentals](./fundamentals.md), [Vector Search](./vector-search.md),
[HNSW](./hnsw.md), and [IVF + PQ](./ivf-pq-quantization.md).

```text
                query
                  |
     +------------+-------------+
     |                          |
 lexical ranker             dense ranker
 (BM25, unbounded)          (ANN cosine, bounded)
     |                          |
 top-k1 by BM25 score      top-k2 by cosine
     |                          |
     +----------> FUSION <------+
                  |
   candidate list (top N) --> RERANK (cross-encoder) --> final top-10
```

## Why raw scores do not mix

The obvious hybrid, `w * bm25 + (1 - w) * cosine`, fails on scales:

- BM25 is unbounded and its range depends on the query: a rare-term query can produce
  scores in the 30s while a common-term query tops out near 2.
- Dense similarity is bounded (cosine in [-1, 1]; dot product is unbounded again if
  vectors are not normalized). Adding a 40 to a 0.9 is not a ranking, it is a lexical
  vote.
- Score distributions shift per query, so any *global* calibration learned once drifts
  as the corpus or query mix changes.

Shipped systems therefore either fuse **ranks** (scale-free) or **re-normalize scores
per query**; both are documented below with the parameters vendors actually ship.

## Reciprocal Rank Fusion

RRF (Cormack, Clarke, and Buettcher, SIGIR 2009) scores a document by the sum of
reciprocals of its ranks in each list, with a damping constant `k`:

```text
RRF(d) = sum over lists L of 1 / (k + rank_L(d))
```

The paper fixed `k = 60` "during a pilot investigation" and it became the de facto
default. Worked example with two lists and `k = 60`:

| doc | rank in list A | rank in list B | RRF score |
|-----|----------------|----------------|-----------|
| d1  | 1              | -              | 1/61 = 0.01639 |
| d2  | 3              | 2              | 1/63 + 1/62 = 0.03200 |
| d3  | 2              | 1              | 1/62 + 1/61 = 0.03252 |
| d4  | -              | 3              | 1/63 = 0.01587 |

Final order: d3, d2, d1, d4. A document ranked 2nd and 1st beats a document ranked 1st
and absent: RRF rewards broad agreement without either list's scores. Nothing needs
calibrating: the Elasticsearch reference states each child retriever "carries an equal
weight as part of the RRF formula" and that two or more child retrievers are required,
with the candidate window set by `rank_window_size` and the damping by `rank_constant`.
It is also outlier-proof: an exact-identifier hit with BM25 = 42 contributes the same
1/(k+1) as any other list leader. The costs: rank positions ignore magnitude, it cannot
express "trust lexical three times as much", and the 1/rank shape is top-heavy, which
matters when a reranker consumes the fused tail.

## Weighted score fusion with per-query normalization

When magnitude information and weights matter, each list must be normalized *within
the query*. OpenSearch's normalization processor is the documented example: it
normalizes each clause with `min_max` (the default; output [0.0, 1.0] with 0.0 replaced
by 0.001 so downstream formulas never multiply by zero), `l2` (when ratios between
scores carry information), or `z_score` (when outliers are a concern; it supports only
the `arithmetic_mean` combination), then combines clauses with `arithmetic_mean`
(default), `geometric_mean`, or `harmonic_mean`. Vespa rank profiles go further and are
plain expressions, e.g. `first-phase { expression: 0.7 * bm25(text) +
0.3 * attribute(popularity) }`, with weights tuned per application.

| scheme | per query | keeps magnitude | outlier behavior |
|--------|-----------|-----------------|------------------|
| RRF (k=60) | yes (rank only) | no | immune by construction |
| min-max weighted | yes | yes | one extreme score reshapes the whole list |
| z-score weighted | yes | yes | resists extremes, assumes roughly normal spread |
| l2 normalized | yes | yes | preserves ratios within a clause |

Weights interact with normalization: switching min-max to z-score without re-tuning
silently changes the blend. Tune weights against a labeled set, not intuition.

## Cross-encoder rerankers

Stage-1 scoring never lets query tokens interact with document tokens: BM25 is term
matching, and bi-encoders embed query and document separately before comparing. A
cross-encoder feeds the concatenated `(query, document)` pair through the transformer,
so every query token attends to every document token. That joint attention is why
cross-encoders dominate bi-encoders on relevance quality, and why they cannot be
indexed: the cost is paid per pair at query time. The SBERT paper (Reimers and
Gurevych, 2019) quantifies the asymmetry: finding the most similar pair among 10,000
sentences requires about 50 million inference computations, roughly 65 hours, with
BERT; the reranker spends a bounded slice of that cost on a small candidate set.

```text
 bi-encoder (indexed)                 cross-encoder (query-time)
 ------------------------------       ------------------------------
 query  --> [encoder] --> q     \     (query, doc_i) --> [transformer,
 docs   --> [encoder] --> d_i ---+-->  shared attention] --> score
            cosine(q, d_i)        |
         precomputed, O(1)        cost O(doc_i) per candidate,
         per comparison           paid only for top N candidates
```

The affordable pattern: retrieve `k1` candidates cheaply; rerank the top `N`
(typically 50-1000) with the cross-encoder, batching pairs so GPU throughput amortizes;
return the top `k`. Cost is linear in `N`, so `N` is the quality/latency dial.

The verified lineage: monoBERT ("Passage Re-ranking with BERT", Nogueira and Cho, 2019)
established BERT reranking on MS MARCO; ColBERT (Khattab and Zaharia, 2020) sits
between bi- and cross-encoders with late interaction over token vectors (see
[RAG Advanced](../llm/advanced/rag-advanced.md) for MaxSim mechanics); RankGPT (Sun et
al., 2023) showed instructed generative LLMs can rank passages directly, competitive
with or better than supervised rerankers on standard IR benchmarks. Distilled
checkpoints like `cross-encoder/ms-marco-MiniLM-L-6-v2` trade a little accuracy for two
orders of magnitude fewer parameters than BERT-base.

## The recall ceiling

Reranking reorders candidates; it cannot conjure what the first stage missed. With `r`
relevant documents in the candidate pool and `k` results shown, a perfect reranker tops
out at `min(k, r)` relevant results. Two consequences:

- Buy recall before model capacity: raising `k1`/`k2` (more `num_candidates` in kNN,
  shallower filters, looser lexical cutoffs) raises the ceiling; a bigger reranker only
  spends the ceiling better.
- Vendors ship this insight as a product constraint: Azure AI Search's semantic ranker
  does L2 ranking, and its documentation states that even when results include more
  than 50 results, "only the top 50 results progress to semantic ranking". The rerank
  window is a deliberate cost/quality trade bounded by what feeds it.

Evaluate stages separately: stage-1 recall@N (the ceiling), nDCG@10 / MRR@10 of the
fused list *before* reranking, end-to-end nDCG@10 at the deployed window, and cost
(pairs scored per query, p99 rerank latency). BEIR (Thakur et al., 2021) is the
reference benchmark for zero-shot claims; its abstract concludes BM25 is "a robust
baseline" while "re-ranking and late-interaction-based models on average achieve the
best zero-shot performances, however, at high computational costs". MS MARCO (Bajaj et
al., 2016) is the standard supervised corpus behind the pointwise rerankers above.

## Where reranking ships

| system | mechanism | verified detail |
|--------|-----------|-----------------|
| Elasticsearch | RRF retriever over child retrievers (term, knn, ELSER text expansion) | `rank_window_size`, `rank_constant`; equal child weights; score 1/(rank + constant) |
| OpenSearch | hybrid search pipeline with normalization/combination processors | `min_max` default plus `l2`, `z_score`; `arithmetic_mean` default plus geometric and harmonic; also an RRF option |
| Vespa | multi-phase rank profiles | `first-phase` over all matches, `second-phase` with `total-rerank-count: 1000`, `global-phase` ONNX cross-encoder with `rerank-count: 20` |
| Azure AI Search | semantic ranker (L2 ranking) | rerank window of the top 50 results from the default ranking algorithm |
| Weaviate | server-side rerank via modules | `rerank` query property delegates final ordering to a configured reranker model |
| Elasticsearch LTR plugin | learning-to-rank feature store and model rescorer | community plugin (o19s) implementing the `sltr` rescorer for feature-based models |

Dense-first systems add a sibling stage: rescoring PQ-compressed distances with
full-precision vectors ([IVF + PQ](./ivf-pq-quantization.md)) fixes *distance
approximation*; a cross-encoder fixes *relevance*.

## Workbench: fusion and the recall ceiling

The runnable model below (stdlib only, deterministic) shows both core effects: scale
distortion under weighted fusion versus rank-based RRF, and the pool ceiling.

```python
# MODEL: hybrid fusion + rerank recall-ceiling workbench (stdlib only, deterministic)
docs    = ["d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8"]
lexical = [12.4,  9.1, 18.2,  4.8,  7.3,  2.1, 42.0,  6.5]   # BM25-style: unbounded
dense   = [0.31, 0.77, 0.91, 0.55, 0.68, 0.44, 0.30, 0.02]   # cosine: bounded [-1, 1]
def order(xs): return [d for d, _ in sorted(zip(docs, xs), key=lambda t: -t[1])]
def min_max(xs): lo, hi = min(xs), max(xs); return [(x - lo) / (hi - lo) for x in xs]
def zscore(xs): mu = sum(xs) / len(xs); sd = (sum((x - mu) ** 2 for x in xs) / len(xs)) ** 0.5; return [(x - mu) / sd for x in xs]
W_LEX, W_DENSE, K = 0.6, 0.4, 60
mm  = [W_LEX * a + W_DENSE * b for a, b in zip(min_max(lexical), min_max(dense))]
zs  = [W_LEX * a + W_DENSE * b for a, b in zip(zscore(lexical), zscore(dense))]
rl  = {d: r for r, d in enumerate(order(lexical), 1)}
rd  = {d: r for r, d in enumerate(order(dense), 1)}
rrf = [1.0 / (K + rl[d]) + 1.0 / (K + rd[d]) for d in docs]
print("stage-1  lexical:", " ".join(order(lexical)))
print("stage-1  dense  :", " ".join(order(dense)))
print("fusion   minmax :", " ".join(order(mm)))
print("fusion   zscore :", " ".join(order(zs)))
print("fusion   rrf    :", " ".join(order(rrf)))
def tau(a, b):
    pa = {d: i for i, d in enumerate(a)}; pb = {d: i for i, d in enumerate(b)}
    s = [(pa[x] - pa[y]) * (pb[x] - pb[y]) for i, x in enumerate(a) for y in a[i + 1:]]
    return (sum(v > 0 for v in s) - sum(v < 0 for v in s)) / len(s)
print("tau vs rrf  minmax: %+.2f  zscore: %+.2f"
      % (tau(order(mm), order(rrf)), tau(order(zs), order(rrf))))
pool = ["d%d" % i for i in range(1, 101)]
gold = ["d17", "d3", "d88", "d5", "d204", "d11"]
inp  = [g for g in gold if g in pool]
print("recall ceiling  pool=%d gold=%d gold_in_pool=%d" % (len(pool), len(gold), len(inp)))
print("perfect reranker top-10: %d relevant (ceiling); unrecoverable: %d"
      % (min(10, len(inp)), len(gold) - len(inp)))
```

Output (verbatim):

```text
stage-1  lexical: d7 d3 d1 d2 d5 d8 d4 d6
stage-1  dense  : d3 d2 d5 d4 d6 d1 d7 d8
fusion   minmax : d7 d3 d2 d5 d1 d4 d6 d8
fusion   zscore : d7 d3 d2 d5 d1 d4 d6 d8
fusion   rrf    : d3 d2 d7 d5 d1 d4 d6 d8
tau vs rrf  minmax: +0.86  zscore: +0.86
recall ceiling  pool=100 gold=6 gold_in_pool=5
perfect reranker top-10: 5 relevant (ceiling); unrecoverable: 1
```

Reading the output: the outlier d7 (lexical 42.0) tops both weighted fusions because it
stretches the min-max and z-score scales; RRF demotes it to third because the dense
ranker put it 7th of 8, while d3, near the top of both lists, wins under RRF, the
behavior you want when two weak-evidence systems agree. The perfect reranker recovers
5 of 6 relevant documents: d204 never entered the pool, so doubling rerank depth doubles
compute and buys nothing.

## Pitfalls

1. **Globally normalized scores.** Per-query normalization is the point; offline
   calibration goes stale with the corpus.
2. **k=60 as sacred.** It was a pilot-investigation constant in one 2009 paper; sweep it.
3. **Deep synchronous reranking.** Pair cost is linear in window size; cap it, batch it,
   and budget the hop at p99, not just p50.
4. **Judging fusion on reranked output only.** A strong reranker masks a bad blend.

## Cross-references

- [Search Fundamentals](./fundamentals.md) -- candidate/rerank stage split and BM25 scoring
- [Vector Search](./vector-search.md) -- ANN candidate generation and hybrid retrieval options
- [HNSW](./hnsw.md) -- the graph index most dense candidate lists come from
- [IVF + PQ Quantization](./ivf-pq-quantization.md) -- full-precision rescoring vs relevance reranking
- [Elasticsearch](./elasticsearch.md) -- where RRF and rescorers live in the engine
- [RAG Advanced](../llm/advanced/rag-advanced.md) -- bi- vs cross-encoder tables and ColBERT MaxSim
- [Learned Indexes](../dbms/advanced/learned-indexes.md) -- model-as-index over sorted keys, a different family

## References

- G. V. Cormack, C. L. A. Clarke, S. Buettcher, "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods", SIGIR 2009 -- <https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf>
- Elasticsearch Reference, "Reciprocal rank fusion" -- <https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion>
- OpenSearch Docs, "Normalization processor" -- <https://opensearch.org/docs/latest/search-plugins/search-pipelines/normalization-processor/>
- Vespa Documentation, "Ranking" -- <https://docs.vespa.ai/en/ranking.html>
- Microsoft Learn, "Semantic ranking in Azure AI Search" -- <https://learn.microsoft.com/en-us/azure/search/semantic-ranking>
- R. Nogueira, K. Cho, "Passage Re-ranking with BERT" (monoBERT), arXiv:1901.04085 -- <https://arxiv.org/abs/1901.04085>
- W. Sun et al., "Is ChatGPT Good at Search? Investigating Large Language Models as Re-Ranking Agents", arXiv:2304.09542 -- <https://arxiv.org/abs/2304.09542>
- N. Reimers, I. Gurevych, "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks", arXiv:1908.10084 -- <https://arxiv.org/abs/1908.10084>
- O. Khattab, M. Zaharia, "ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT", arXiv:2004.12832 -- <https://arxiv.org/abs/2004.12832>
- N. Thakur et al., "BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models", arXiv:2104.08663 -- <https://arxiv.org/abs/2104.08663>
- P. Bajaj et al., "MS MARCO: A Human Generated MAchine Reading COmprehension Dataset", arXiv:1611.09268 -- <https://arxiv.org/abs/1611.09268>
- Weaviate Docs, "Reranking results" -- <https://weaviate.io/developers/weaviate/search/rerank>
