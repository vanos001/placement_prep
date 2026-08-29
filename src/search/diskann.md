# DiskANN / Vamana: Billion-Scale ANN on a Single SSD Node

DiskANN is where approximate nearest-neighbor search leaves RAM. The NeurIPS 2019 paper (algorithm name Rand-NSG; DiskANN is the system) showed that one 64 GB workstation with an ordinary NVMe SSD can index and search a billion vectors at 95%+ 1-recall@1 in a few milliseconds -- territory in-memory graphs like [HNSW](./hnsw.md) cannot reach. This page covers the Vamana graph, the on-disk layout, beam search over SSD pages, FreshDiskANN streaming updates, and where the design ships. The quantization codec itself lives in [IVF-PQ](./ivf-pq-quantization.md).

## The memory wall at billion scale

Graph indexes keep vectors and adjacency lists in DRAM; both scale linearly with the corpus and neither shrinks when you buy a bigger disk.

| Component (N = 1B vectors, d = 96) | Bytes/vector | Total RAM | Verdict on a 64 GB node |
|---|---|---|---|
| Raw fp32 vectors | 384 | 384 GB | impossible |
| HNSW adjacency (M = 32, 4 B ids) | 128 | 128 GB | impossible |
| IVF-PQ codes (24 B) + cluster lists | ~28 | ~28 GB | fits, recall plateaus |
| DiskANN (PQ codes in DRAM, graph on SSD) | ~24 | ~24 GB | fits, recall holds |

Compression-only stacks (FAISS-quantized IVF, IVF-OADC+G+P) fit in RAM but lose precision: the DiskANN paper measured them plateauing near 50% 1-recall@1 on SIFT1B at comparable memory footprints, versus 95%+ for the SSD-resident graph. The DiskANN wager: keep the *navigation data* (compressed codes) in DRAM and stream the *bulky data* (graph edges, full vectors) from an SSD whose 4 KB random reads cost a few hundred microseconds.

## Vamana: a proximity graph shaped for disk reads

Vamana is a directed proximity graph like HNSW's base layer, with four deliberate differences (Section 2.4 of the paper):

| Design axis | HNSW / NSG | Vamana | Why it matters on SSD |
|---|---|---|---|
| Pruning threshold | implicitly alpha = 1 | tunable alpha > 1 | long-range edges cut hop counts |
| Candidate set for pruning | final L results only | every vertex visited during search | adds long-range edges cheaply |
| Initial graph | k-NN graph (NSG) or empty (HNSW) | random graph | no expensive prebuild |
| Passes over data | one | two | second pass adds reach, improves quality |

The quantified payoff: to reach 98% 5-recall@5, Vamana needs 2-3x fewer hops than HNSW and NSG. On disk a "hop" is a round of SSD reads on the critical path, so hop count *is* the latency budget.

### Robust pruning, spelled out

Neighbor selection is `RobustPrune(p, V, alpha, R)`: sort candidates V by distance to p, repeatedly pick the closest remaining `x` into p's out-neighbors, and delete every remaining `y` satisfying:

```text
alpha * d(x, y) <= d(p, y)      # y is "well covered" by x -- drop it
```

alpha = 1 is the classic RNG-style dominance rule: sparse, clean graphs. Raising alpha makes deletion *harder*, so more candidates survive -- including far-away points that overlap nothing. Those are exactly the long-range edges that let search cross a cluster boundary in one hop. The toy below is the paper's own motivating example (points on a line): alpha = 1 collapses the chain and never reaches the far point; alpha > 1 keeps an edge to it.

```python
# RobustPrune(p, V, alpha, R) from the DiskANN paper: y is dropped from the
# candidate list when alpha * d(x, y) <= d(p, y) for an already-selected x.
# Toy 1-D points: p = 0, a dense chain 1..5, and one far outlier at 100.

def d(a, b):
    return abs(a - b)

def robust_prune(p, V, alpha, R):
    W = sorted(V, key=lambda y: d(p, y))   # nearest-first candidate list
    kept = []
    while W and len(kept) < R:
        x = W.pop(0)                       # closest remaining candidate
        kept.append(x)
        W = [y for y in W if not (alpha * d(x, y) <= d(p, y))]
    return kept

P, V = 0, [1, 2, 3, 4, 5, 100]
for alpha in (1.0, 1.2, 2.0):
    print(f"alpha={alpha:.1f}: out-neighbors {robust_prune(P, V, alpha, R=10)}")
```

Output:

```text
alpha=1.0: out-neighbors [1]
alpha=1.2: out-neighbors [1, 100]
alpha=2.0: out-neighbors [1, 3, 100]
```

### Two-phase build, and the merged path

Vamana builds in two passes: pass one with alpha = 1 (fast, clean pruning), pass two with alpha > 1 (alpha = 2 in the billion-point builds) to upgrade out-neighbor lists with long-range edges. A one-shot 1B-point index (L = 125, R = 128) took ~2 days on a 1.8 TB-RAM VM with ~1100 GB peak -- which defeats the purpose -- so the scalable recipe is:

1. Partition the corpus into k = 40 shards with k-means.
2. Assign each point to its l = 2 *closest* shards (overlapping, not disjoint).
3. Build a Vamana index per shard in RAM (L = 125, R = 64, alpha = 2).
4. Merge by taking the union of all edge sets.

The merged SIFT1B index is 348 GB, average degree 92.1, built in ~5 days on the 64 GB workstation without ever exceeding RAM (assignment and merge stream from disk). Overlap (l = 2) keeps the merged graph connected when a query's true neighbors straddle shards; the cost is at most ~20% extra latency versus the one-shot index at a target recall.

## On-disk layout

The original layout puts PQ codes in DRAM and both the graph and the full-precision vectors on SSD, packed so no offset table is needed: node i's record sits at a fixed stride; short neighbor lists are zero-padded.

```text
One 4 KB sector per node visit (original DiskANN layout)

+-----------------------------------------------------------------------+
| full-precision vector_i      | neighbor ids of node i (<= R x 4 B)    |
| (d x 4 B = 384 B at d = 96)  | zero-padded to the fixed stride        |
+------------------------------+----------------------------------------+
     ^ free re-ranking payload        ^ the next hop's frontier
  DRAM: PQ codes (~24-32 B/vector), the PQ codebook (~100 KB),
  the start node, and a cache of the first C = 3-4 BFS levels from it
```

- **Implicit re-ranking.** A 4 KB-aligned read costs no more than a 512 B read, so the full-precision vector rides along with the adjacency list in the same sector. The beam navigates on PQ distances; the final top-k is re-ranked on exact distances with *zero extra SSD reads*. Rivals like Zoom paid hundreds of separate random reads to fetch full vectors.
- **The library layout generalizes this.** microsoft/DiskANN (and FreshDiskANN) also support the inverse split -- PQ code + adjacency in the node sector, full vectors hoisted to a separate region. The invariant holds either way: each hop touches O(1) sectors, and sectors-per-query is the IO budget.

## Search: beam width L, W-way reads, hop count

Search is GreedySearch with a result list of size L. Per iteration the W closest *unexpanded* candidates issue their sector reads in parallel (the paper's BeamSearch); their neighborhoods merge into the list, the list is truncated to the L closest, and the search ends when every candidate in L has been expanded.

```text
query xq ---> DRAM: PQ codebook -> ADC distances (no SSD touch)
  |
  | frontier = W closest unexpanded candidates
  |        \______ W parallel 4 KB reads ______/
  v
 SSD: adjacency of those nodes -> new candidate ids + PQ codes
  |
  | merge into list, keep closest L, repeat while L \ V is non-empty
  v
 top-k re-ranked on the full vectors that rode along in each sector
```

Operating points from the paper: W in {2, 4, 8} keeps the SSD at a 30-40% load factor (queuing at peak IOPS would push reads past a millisecond), each thread spends 40-50% of query time in IO, and caching the first 3-4 BFS levels around the start node removes the hottest reads. Beam width L is the recall knob -- doubling it roughly doubles sectors-read per query.

## Demo: an SSD-read-limited cost model

The model reproduces the paper's accounting for a 64 GB node serving 1B x 96-dim fp32 vectors: hops = ceil(L/W) rounds of parallel reads, one 4 KB sector read per expanded node, 90 us per random read, a 200K-IOPS budget (500K peak x 40% load). It also sizes the alternatives. Distances are not modeled -- this is the IO arithmetic only.

```python
# DiskANN-style SSD-read cost model vs in-memory and brute-force baselines.
# Workload: 1B vectors, d = 96 (fp32). Parameters follow the DiskANN paper
# (NeurIPS 2019): 4 KB sectors, out-degree R, PQ codes in DRAM, consumer
# NVMe SSD: ~90 us random 4KB read, ~500K IOPS peak, ~7 GB/s sequential.

D, N = 96, 1_000_000_000
SECTOR = 4096
R = 32                                   # graph out-degree bound (on SSD)
M_PQ = 24                                # PQ code bytes per vector (in DRAM)
READ_LAT = 90e-6                         # seconds per random 4KB read
IOPS_PEAK, LOAD = 500_000, 0.40          # paper: run SSD at 30-40% load
SEQ_BW = 7.0e9                           # sequential-scan bytes/second
W = 4                                    # reads issued in parallel per hop

raw = N * D * 4                          # raw vectors: 1B x 96 x fp32
hnsw_ram = raw + N * R * 4               # vectors + adjacency in DRAM
diskann_ram = N * M_PQ                   # PQ codes only; graph on SSD
bf_scan = raw / SEQ_BW                   # one brute-force query = full scan

print(f"raw vectors 1B x {D}-d fp32        : {raw/1e9:.0f} GB")
print(f"in-memory HNSW RAM (vec + links)  : {hnsw_ram/1e9:.0f} GB  (> 64 GB node)")
print(f"DiskANN DRAM (PQ codes, {M_PQ} B/vec) : {diskann_ram/1e9:.0f} GB  (fits 64 GB)")
print(f"brute force = full NVMe scan/query: {bf_scan:.1f} s")
print()
print("  L  hops(L/W)  sectors-read  SSD bytes/q  latency(hops x 90us)  QPS @ 200K IOPS")
for L in (16, 32, 64, 128):
    hops = -(-L // W)                    # ceil(L / W)
    lat = hops * READ_LAT
    qps = IOPS_PEAK * LOAD / L
    print(f"{L:4d} {hops:8d} {L:12d} {L*SECTOR/1024:12.0f}KB {lat*1000:14.2f} ms {qps:16.0f}")
```

Output:

```text
raw vectors 1B x 96-d fp32        : 384 GB
in-memory HNSW RAM (vec + links)  : 512 GB  (> 64 GB node)
DiskANN DRAM (PQ codes, 24 B/vec) : 24 GB  (fits 64 GB)
brute force = full NVMe scan/query: 54.9 s

  L  hops(L/W)  sectors-read  SSD bytes/q  latency(hops x 90us)  QPS @ 200K IOPS
  16        4           16           64KB           0.36 ms            12500
  32        8           32          128KB           0.72 ms             6250
  64       16           64          256KB           1.44 ms             3125
 128       32          128          512KB           2.88 ms             1562
```

The table lands in the paper's envelope: >5000 QPS with <3 ms mean latency at 95%+ 1-recall@1 on SIFT1B sits between the L = 32 and L = 64 rows. Treat the columns as a budgeting model, not a benchmark -- the real system buys latency back with caching and multi-query batching, and pays it out on larger L.

## FreshDiskANN: billion-scale with live updates

The original index is static: a changed corpus meant a rebuild, measured in days at billion scale. FreshDiskANN (ICML 2021) turns Vamana into a streaming index:

- **Insert eagerly, prune lazily.** A new point is connected to its searched neighbors immediately; when a touched node's out-degree exceeds R, RobustPrune with alpha > 1 restores the bound. Running alpha > 1 keeps recall *stable* across update streams instead of degrading.
- **Deletes go to a DeleteList.** Unlinking a deleted node means re-pruning every in-neighbor, so deletions are marked and skipped at query time; once they reach 1-10% of the index, a batched consolidation pass repairs neighborhoods, parallelized with prefix sums.
- **Two tiers + StreamingMerge.** A long-term SSD-resident index holds the bulk; a short-term in-memory index absorbs recent updates; background StreamingMerge consolidates the latter into the former to bound DRAM.

Headline result: over a billion points on one SSD workstation, thousands of concurrent inserts, deletes, and searches per second each, retaining >95% 5-recall@5 -- a 5-10x reduction in the cost of freshness versus rebuilds. Follow-ups attack the remaining corners: OOD-DiskANN (arXiv 2211.12850) for out-of-distribution queries, DiskANN++ (arXiv 2310.00402) for page-level placement and query-sensitive entry vertices, DistributedANN (arXiv 2509.06046) for one DiskANN graph across thousands of machines.

## What the papers measured

| Claim | Number | Source |
|---|---|---|
| SIFT1B, 1-recall@1 > 95% | mean latency < 3.5 ms, same RAM as IVF-OADC+G+P-32 | DiskANN, NeurIPS 2019 |
| SIFT1B, best recall | 98.68% 1-recall@1 under 5 ms | DiskANN, NeurIPS 2019 |
| Throughput on one node | > 5000 QPS, < 3 ms mean, 95%+ 1-recall@1 | DiskANN, NeurIPS 2019 |
| Compression-only rivals | IVF-OADC+G+P-16/-32 plateau at 37.04% / 62.74% 1-recall@1 | DiskANN, NeurIPS 2019 |
| Merged SIFT1B index | 348 GB, avg degree 92.1, ~5 days under 64 GB RAM | DiskANN, NeurIPS 2019 |
| Hop advantage over HNSW/NSG | 2-3x fewer hops at 98% 5-recall@5 | DiskANN, NeurIPS 2019 |
| Freshness | > 95% 5-recall@5 with 1000s of inserts + deletes + searches/s | FreshDiskANN, ICML 2021 |

## Where DiskANN ships

| System | DiskANN form | Notes |
|---|---|---|
| Azure Database for PostgreSQL Flexible Server | DiskANN index type via the pgdiskann extension | upstream pgvector offers HNSW/IVFFlat only |
| Azure DocumentDB (MongoDB vCore lineage) | integrated vector store listing DiskANN | positioned for low-RAM, large-scale semantic search |
| Milvus | DISKANN on-disk index, based on Vamana graphs | disabled by default; enabled for SSD-resident deployments |
| microsoft/DiskANN | reference library (now the composable DiskANN3 engine) | powers the database integrations above |

Two cautions for system-design answers. First, "on-disk ANN" is not the default anywhere: Milvus ships DiskANN disabled, and Azure AI Search's vector ranking is HNSW and exhaustive KNN, not DiskANN -- the technology belongs where RAM is the binding constraint. Second, don't reach for it below a few hundred million vectors: an in-memory [HNSW](./hnsw.md) or a quantized [IVF-PQ](./ivf-pq-quantization.md) beats a graph that pays SSD latency per hop.

## Interview checkpoints

- Why can't HNSW just "use an SSD"? -- Its hierarchy and adjacency live in DRAM; a hop is ~100 ns there versus ~90 us on SSD, so a naive port is ~1000x slower per hop. DiskANN redesigns the graph (alpha edges, fewer hops) and the layout (one sector per node) around that latency.
- What does alpha trade? -- Recall per hop vs degree: alpha > 1 densifies the graph with long-range edges, cutting hop count (each hop is an SSD round trip) at the price of build time.
- Where do full-precision vectors go? -- Next to the adjacency in the same 4 KB sector (2019 layout, free re-ranking), or in a separate region (library layout); either way PQ distances only *steer* the beam.
- How do deletes work? -- Lazy: DeleteList plus skip-at-query-time, with batched neighborhood repair once deletions hit 1-10% (FreshDiskANN).

## Cross-references

- [HNSW](./hnsw.md) -- the in-memory graph this design is measured against; search/beam mechanics are shared, the storage tier is not
- [IVF-PQ: Quantized Vector Search](./ivf-pq-quantization.md) -- the PQ/ADC codec DiskANN borrows; that page owns quantization mechanics
- [Vector Search](./vector-search.md) -- retrieval-pipeline survey placing all three index families side by side
- [Vector Databases](../dbms/advanced/vector-databases.md) -- HNSW/IVF/DiskANN comparison and index-maintenance survey
- [Milvus](../llm/advanced/milvus.md) -- the DISKANN index in a real engine
- [pgvector](../llm/advanced/pgvector.md) -- the upstream PostgreSQL extension DiskANN complements (not replaces) in Azure Postgres

## References

- Jayaram Subramanya, Devvrit, Simhadri, Krishnaswamy, Kadekodi, "Rand-NSG: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node" (the DiskANN system paper), NeurIPS 2019 -- <https://proceedings.neurips.cc/paper/2019/hash/09853c7fb1d3f8ee67a61b6bf4a7f8e6-Abstract.html> (abstract fetched live; Vamana, RobustPrune, sector layout, SIFT1B numbers)
- Singh, Jayaram Subramanya, Krishnaswamy, Simhadri, "FreshDiskANN: A Fast and Accurate Graph-Based ANN Index for Streaming Similarity Search," ICML 2021 -- <https://arxiv.org/abs/2105.09613> (DeleteList, StreamingMerge, freshness numbers)
- Jaiswal et al., "OOD-DiskANN: Efficient and Scalable Graph ANNS for Out-of-Distribution Queries" -- <https://arxiv.org/abs/2211.12850>
- Ni et al., "DiskANN++: Efficient Page-based Search over Isomorphic Mapped Graph Index using Query-sensitivity Entry Vertex" -- <https://arxiv.org/abs/2310.00402>
- Adams et al., "DISTRIBUTEDANN: Efficient Scaling of a Single DISKANN Graph Across Thousands of Computers" -- <https://arxiv.org/abs/2509.06046>
- microsoft/DiskANN -- reference library and project wiki (DiskANN3 engine; research overview 2018-present) -- <https://github.com/microsoft/DiskANN> and <https://github.com/microsoft/DiskANN/wiki/DiskANN-Project-and-Research-Overview-(2018%E2%80%90present)>
- The DiskANN library: Graph-Based Indices for Fast, Fresh and Filtered Vector Search, IEEE Data Eng. Bull. 47(3), 2024 -- <http://sites.computer.org/debull/A24sept/p20.pdf>
- Microsoft Learn, "Enable and Use DiskANN in Azure Database for PostgreSQL Flexible Server" -- <https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-use-pgdiskann>
- Microsoft Learn, Azure DocumentDB integrated vector store (DiskANN index kind) -- <https://learn.microsoft.com/en-us/azure/documentdb/vector-search>
- Milvus docs, "On-disk Index" (DiskANN, Vamana-based, disabled by default) -- <https://milvus.io/docs/disk_index.md>
- pgvector README (HNSW and IVFFlat index types only) -- <https://github.com/pgvector/pgvector/blob/master/README.md> 