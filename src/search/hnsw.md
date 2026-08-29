# HNSW: Hierarchical Navigable Small World Graphs

HNSW (Malkov & Yashunin, arXiv 1603.09320; journal version in IEEE TPAMI vol. 42 no. 4) is a
fully graph-based approximate nearest-neighbor (ANN) index: no coarse quantizer, no trees, no
hash tables -- just a hierarchy of proximity graphs over the stored vectors. A query greedily
descends through increasingly dense layers, so distance computations grow logarithmically with
corpus size instead of linearly. HNSW is the default dense-vector index in pgvector, Qdrant,
Milvus, Weaviate, Elasticsearch, and faiss, and the paper positions it as a general
metric-space index: it needs only a distance function, never vector coordinates.

This page is the algorithm deep dive; tool-level coverage lives in
[faiss](../llm/advanced/faiss.md) and [pgvector](../llm/advanced/pgvector.md), the
retrieval-pipeline survey in [Vector Search](./vector-search.md), and the quantization-based
rival in [IVF-PQ](./ivf-pq-quantization.md).

## Why a graph, and why hierarchical

Greedy routing on a plain k-NN graph faces a **degree-vs-recall trap**. With short-range links
only, the greedy path walks nearly edge by edge across the corpus; with long-range links only,
nodes connect to unrelated regions and the walk never homes in. Navigable Small World (NSW)
theory -- going back to Kleinberg's lattice model, where each node adds long-range links with
probability proportional to r^(-alpha) over distance r -- says greedy routing is polylogarithmic
only when the long-link distribution matches the data dimension (alpha = d). Kleinberg's
construction needs the data distribution in advance, useless for an index that must accept
arbitrary insert streams.

HNSW lets long-range links **emerge** rather than be planned. Each element is assigned to
layers 0..l with an exponentially decaying distribution, so layer k holds roughly N/M^k
elements; a node on a high layer is connected to a sparse subset spanning the whole space, and
lower layers refine the same space at finer distance scales. The paper calls this **scale
separation** -- links organized by characteristic distance scale, exactly what Kleinberg's
navigability criterion requires, produced by coin flips instead of global knowledge. One
terminology note: the paper never says "MSC space"; its claims are that the structure is a
general metric-space search index, and that under the idealization of exact Delaunay layers
the expected greedy steps per layer are bounded by 1/(1-exp(-mL)) regardless of N -- giving
logarithmic search complexity overall.

## Structure: a skip list of proximity graphs

```text
      L2 (sparse)      E*------------------(x)                ~N/M^2 nodes
                       |      long-range hops, greedy, keep 1 candidate
                       v
      L1 (denser)      E*---------(y)                         ~N/M nodes
                       |     mid-range hops, still greedy
                       v
      L0 (all nodes)   E*--a--b-(q)--c--d--e--f--g            all N vectors
                            ^                 degree <= 2M here;
                            +--- beam search with ef candidates, return top K
```

- **Layer assignment** for a new element is l = floor(-ln(uniform(0,1)) * mL) with
  mL = 1/ln(M) -- the skip list construction with p = 1/M, giving an average single-element
  overlap between adjacent layers (the hnswlib source implements exactly this in
  `getRandomLevel`). Never derive the layer from the element id; the randomness keeps layers
  balanced under skewed insert orders.
- **Degree caps**: Mmax edges per node on upper layers, Mmax0 = 2*M on layer 0 -- the bottom
  layer carries the final beam, so it buys robustness with double degree (hnswlib hard-codes
  `maxM0_ = M_ * 2`).
- **One entry point** at the top layer; every insert and query starts there. Because layers
  are random, re-indexing the same data with a different seed yields a different graph with
  statistically similar performance -- HNSW is a randomized index, not a deterministic
  structure.

## Search: greedy descent plus a beam

The paper's K-NN-SEARCH (Algorithm 5) has two phases, and the demo below measures both:

```text
PHASE 1 -- descent (ef = 1): for lc = top .. 1
    walk layer lc greedily; enter layer lc-1 at the closest element found
PHASE 2 -- beam (layer 0 only): keep a best-ef list W
    expand the closest not-yet-expanded candidate in W, push its
    neighbors into W, keep only the ef closest; stop when the closest
    unexpanded candidate is farther than the ef-th element of W
```

The stop condition is the key implementation detail: expansion ends when no unexpanded
candidate can beat the current ef-th best, so the search prunes whole neighborhoods without a
fixed "distance computations" budget. That is why `ef` maps so cleanly onto a latency dial: it
bounds the working set, not the work.

## Insertion and the neighbor-diversity heuristic

INSERT (Algorithm 1) reuses the same machinery: descend greedily to the new element's top
layer, then run the beam search with `efConstruction` on each layer down to 0 and connect the
new element to the closest M results found (Mmax0 on layer 0). The naive version -- "keep the
M closest candidates" -- produces hub-dominated graphs: on clustered data a few central nodes
absorb every edge, outlying clusters get thin connectivity, and recall collapses exactly in
the high-recall regime. Algorithm 4 (SELECT-NEIGHBORS-HEURISTIC) fixes this with a diversity
filter:

```text
candidates sorted by distance to q: e1, e2, e3, ...
keep e1. For each next candidate e: keep e only if
    d(e, q) < d(e, s) for every already-kept neighbor s
    (otherwise e is redundant: a kept node covers its direction)
keepPrunedConnections = true: backfill free slots with pruned candidates
```

Two candidates on the same ray from q cannot both be kept, so the degree budget is spent on
different directions. The paper reports the largest gains at high recall and on highly
clustered data -- the regimes where hub collapse kills the naive graph. The demo below
implements the heuristic with backfill.

## Deletion and updates: marking, not unlinking

Graph indexes have no hole-punching operation like a B-tree delete:

- **faiss**: `IndexHNSW` does not support removing vectors -- the wiki states removal "would
  destroy the graph structure". The patterns are rebuild, or a removable id-filter on top.
- **hnswlib**: `mark_deleted(label)` flags the element; searches skip flagged nodes but the
  node and its edges stay, and `allow_replace_deleted` lets new inserts reuse deleted slots.
  Physical compaction means rebuild.
- **pgvector**: deleting a row leaves an index dead tuple, and updating the vector column
  behaves as delete-plus-insert; the docs steer hot-update workloads toward insert-only
  patterns for this reason.

Heavy vector churn therefore needs tombstone budgets plus periodic rebuilds, or an
architecture that treats HNSW as an append-only index behind a version map.

## Parameter effects: the recall / latency / memory triangle

| Parameter | Controls | Too low | Too high |
|---|---|---|---|
| M | edges per node per layer | disconnected clusters, recall ceiling | memory grows, build slows, no recall gain |
| efConstruction | beam width while inserting | brittle graph that no ef can repair | slow builds, diminishing returns |
| ef (query) | beam width at search time | recall starvation | linear latency growth, recall saturates |

Three rules from the primary sources tie the knobs together:

1. **ef must be >= k.** hnswlib documents that ef cannot be set below the number of requested
   neighbors; the demo below runs ef = 8 for a k = 10 query anyway, and the recall ceiling it
   shows is the reason hnswlib rejects that configuration.
2. **M times efConstruction is roughly a constant** for a target quality (hnswlib guidance):
   doubling M lets you halve efConstruction at similar graph quality. M = 12-48 covers most
   workloads; high-dimensional embeddings often want 48-64 at high recall.
3. **Memory is linear in M**: the hnswlib docs estimate link overhead at roughly M x 8-10
   bytes per stored element, and the faiss wiki quotes IndexHNSWFlat memory as 4*d payload
   bytes plus x * M * 2 * 4 bytes of graph links for a vector on x layers. From the hnswlib
   source, a layer-0 node costs 2M x 4 B of link ids plus a 4 B degree header -- 132 B at
   M = 16 -- plus an expected 1/(M-1) upper-layer blocks per element: a few percent of a
   768-dim fp32 vector, but over a third of a 384-dim SQ8 payload.

Latency is dominated by the layer-0 beam: the descent above it costs a nearly constant number
of hops, while beam work scales with ef. The demo makes this concrete -- raising ef from 16 to
64 multiplies beam hops by ~3.3 while adding 0.115 recall on this easy 2-D data set.

## Runnable demo: layers, hops, recall

Deterministic, stdlib-only. Builds HNSW over 2,000 uniform 2-D points with M = 4, prints
per-layer occupancy, splits average hops into descent vs layer-0 beam, and measures recall@10
against brute force for three ef values.

```python
import heapq, math, random  # compact HNSW demo: layers, hop split, recall@10

random.seed(7); M, N = 4, 2000; mL = 1.0 / math.log(M)
pts = [(random.uniform(0, 100), random.uniform(0, 100)) for _ in range(N)]
layer_of = [min(int(-math.log(random.random()) * mL), 8) for _ in range(N)]
dst = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
adj = [{} for _ in range(N)]            # node -> {level: [neighbours]}
entry, top = None, -1

def search_layer(q, eps, ef, level, hops):
    cand = sorted((dst(q, pts[e]), e) for e in eps)
    W = [(-dd, e) for dd, e in cand]; heapq.heapify(W); seen = set(eps)
    while cand:
        dc, c = heapq.heappop(cand)
        if dc > -W[0][0] and len(W) >= ef: break
        for e in adj[c].get(level, []):
            if e in seen: continue
            seen.add(e); hops[0] += 1
            de = dst(q, pts[e])
            if len(W) < ef or de < -W[0][0]:
                heapq.heappush(cand, (de, e)); heapq.heappush(W, (-de, e))
                if len(W) > ef: heapq.heappop(W)
    return sorted((-nd, e) for nd, e in W), hops[0]

def select_heur(q, cands, cap):         # paper Alg.4: diversity + keepPruned
    sel, pruned = [], []
    for dd, e in sorted(cands):
        (sel if all(dst(pts[e], pts[s]) > dd for s in sel) else pruned).append(e)
        if len(sel) == cap: break
    return (sel + pruned)[:cap]

def insert(i):
    global entry, top
    q, l = pts[i], layer_of[i]
    adj[i] = {lv: [] for lv in range(l + 1)}
    if entry is None: entry, top = i, l; return
    ep = [entry]
    for lv in range(top, l, -1):                       # greedy descent, ef=1
        ep = [search_layer(q, ep, 1, lv, [0])[0][0][1]]
    for lv in range(min(l, top), -1, -1):              # beam-connect per layer
        cands, _ = search_layer(q, ep, M, lv, [0])
        cap = 2 * M if lv == 0 else M
        adj[i][lv] = select_heur(q, cands, cap)
        for e in adj[i][lv]:
            adj[e][lv].append(i)
            if len(adj[e][lv]) > cap:                  # re-shrink full node
                adj[e][lv] = select_heur(pts[e],
                    [(dst(pts[e], pts[x]), x) for x in adj[e][lv]], cap)
        ep = [e for _, e in cands]
    if l > top: entry, top = i, l

for i in range(N): insert(i)
print("per-layer node counts:", {lv: sum(1 for x in range(N) if layer_of[x] >= lv) for lv in range(top + 1)})
print("M=%d  mL=1/ln(M)=%.3f" % (M, mL))
queries = list(range(0, N, 20))                        # 100 deterministic queries
brute = {q: sorted(range(N), key=lambda x: dst(pts[q], pts[x]))[1:11] for q in queries}
stat = {8: [0, 0], 16: [0, 0], 64: [0, 0]}             # ef -> [hits, beam hops]
desc = 0
for q in queries:
    ep, top_q = [entry], top
    while top_q > 0:                                   # greedy descent, ef = 1
        res, h = search_layer(pts[q], ep, 1, top_q, [0])
        ep, desc = [res[0][1]], desc + h; top_q -= 1
    for ef, acc in stat.items():                       # layer-0 beam
        res, h = search_layer(pts[q], ep, ef, 0, [0])
        got = [e for _, e in res if e != q][:10]
        acc[0] += len(set(got) & set(brute[q])); acc[1] += h
print("avg descent hops/query (top->L1): %.1f" % (desc / len(queries)))
for ef in (8, 16, 64):
    print("ef=%2d: recall@10=%.3f  avg beam hops=%.1f"
          % (ef, stat[ef][0] / (10 * len(queries)), stat[ef][1] / len(queries)))
```

Output (verified reproducible across runs):

```text
per-layer node counts: {0: 2000, 1: 530, 2: 107, 3: 33, 4: 8, 5: 2, 6: 1}
M=4  mL=1/ln(M)=0.721
avg descent hops/query (top->L1): 22.9
ef= 8: recall@10=0.631  avg beam hops=19.1
ef=16: recall@10=0.840  avg beam hops=29.6
ef=64: recall@10=0.955  avg beam hops=97.6
```

Reading the numbers: layer occupancy decays geometrically by M = 4 (2000, 530, 107, 33, 8, 2,
1), matching the skip-list prediction; descent through all upper layers costs ~23 hops per
query regardless of target quality, so all the recall you buy with ef is paid in beam width
(29.6 -> 97.6 hops for +0.115 recall). ef = 8 for k = 10 violates hnswlib's ef >= k rule -- the
beam cannot physically hold 10 results -- and the residual gap to 0.955 at ef = 64 is graph
quality (M = 4 is sparse): high recall needs both adequate M and adequate ef.

## HNSW vs IVF vs Annoy

| Property | HNSW | IVF (+PQ) | Annoy |
|---|---|---|---|
| Structure | layered proximity graph | k-means clusters + lists | random projection forest |
| Training | none (incremental inserts) | k-means pass required | forest built up front |
| Build order | online; inserts any time | batch retrain to add lists | static; no appends |
| Memory | high (graph links, ~M x 8-10 B/element) | tunable down via PQ codes | low; memory-mapped file |
| Query dial | ef | nprobe | search_k |
| Filtering | graph traversal; engine-specific support | post-filter on probed lists | post-filter on returned leaves |
| Deletions | mark/tombstone or rebuild | rebuild lists | rebuild |
| Sweet spot | low-latency in-RAM recall 0.95+ | billion scale, tight memory | read-only on-disk corpora |

IVF prunes by **partition** (see [IVF-PQ](./ivf-pq-quantization.md) for the quantization
machinery), Annoy by **tree path**, HNSW by **graph reachability** -- the most flexible and the
most memory-hungry pruning rule, which is why HNSW wins recall-per-latency in RAM while IVF-PQ
wins cost-per-billion-vectors.

## Production tuning: faiss, pgvector, Qdrant

| System | Build knobs | Query knob | Defaults |
|---|---|---|---|
| faiss | M (constructor arg), efConstruction | HNSW.efSearch | efConstruction = 40, efSearch = 16 |
| pgvector | m, ef_construction | hnsw.ef_search | m = 16, ef_construction = 64, ef_search = 40 |
| Qdrant | m, ef_construct | hnsw_ef | m = 16, ef_construct = 100 |
| hnswlib | M, ef_construction | ef | M = 16, ef_construction = 200 |

- **faiss** composes HNSW with compression: `IndexHNSWSQ`, `IndexHNSWPQ`, and `IndexHNSW2Level`
  put quantized payloads under the same graph; HNSW also works as an IVF coarse quantizer.
- **pgvector** warns when the graph no longer fits in `maintenance_work_mem` -- a spilling
  build slows down dramatically, so size it before loading. Filtering is applied *after* the
  index scan, so a predicate matching 10 percent of rows with the default ef_search = 40
  yields ~4 rows on average; iterative scans (capped by `hnsw.max_scan_tuples`, 20,000 by
  default) re-visit more of the index when the filtered result set is starved.
- **Qdrant** prefers a full scan over HNSW for tiny segments (`full_scan_threshold`, 10,000 KB
  of vectors by default, where 1 KB is defined as one 256-dim vector) and ships a filterable
  HNSW variant with filter-aware edges, which requires building HNSW after payload indexes.
- **hnswlib's calibration recipe**: after building, measure recall for an M-NN query with
  ef = efConstruction; below 0.9, raise efConstruction (or M) rather than fixing a bad graph
  at query time.

## Interview checkpoints

- Derive the layer-assignment formula from the skip list analogy; why mL = 1/ln(M)?
- Why does the neighbor-diversity heuristic matter most on clustered data?
- What do ef, M, and efConstruction each buy, and why is M*efConstruction treated as constant?
- A filtered query matches 10 percent of rows on pgvector defaults: how many rows return, and
  which knob do you raise?

## Cross-references

- [Vector Search](./vector-search.md) -- retrieval-pipeline survey around the index
- [IVF-PQ: Quantized Vector Search](./ivf-pq-quantization.md) -- the partition/quantization rival
- [Search Fundamentals](./fundamentals.md) -- the lexical side of hybrid retrieval
- [faiss](../llm/advanced/faiss.md) / [pgvector](../llm/advanced/pgvector.md) -- tool-level pages
- [Vector Databases](../llm/llm-serving/vector-databases.md) -- system-level comparisons

## References

- Malkov & Yashunin, "Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs," arXiv:1603.09320 -- https://arxiv.org/abs/1603.09320
- Journal version, IEEE TPAMI vol. 42 no. 4, pp. 824-836 -- https://doi.org/10.1109/TPAMI.2018.2889473
- hnswlib reference implementation, README and ALGO_PARAMS.md -- https://github.com/nmslib/hnswlib and https://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md
- pgvector README, HNSW index and query options -- https://github.com/pgvector/pgvector/blob/master/README.md
- faiss wiki, "Faiss-indexes" (IndexHNSW variants, memory formula, removal restriction) -- https://github.com/facebookresearch/faiss/wiki/Faiss-indexes
- Qdrant documentation, "Indexing" (HNSW configuration, filterable HNSW) -- https://qdrant.tech/documentation/concepts/indexing/
- J. Kleinberg, "The Small-World Phenomenon: An Algorithmic Perspective," Cornell TR -- https://www.cs.cornell.edu/home/kleinber/swn.pdf
- Spotify Annoy (random projection forest baseline) -- https://github.com/spotify/annoy
