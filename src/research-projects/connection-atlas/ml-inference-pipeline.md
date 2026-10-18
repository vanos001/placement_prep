# ML Inference as a Pipeline: The Model Is Never Just a Model

## Overview

Interviews and architecture diagrams compress "the model" into one box, as if a logistic regression or a transformer were a self-contained artifact you load and call. In production, the model is the *smallest* moving part of a serving pipeline: versioned artifacts are built by training jobs, feature values are fetched from an online store that mirrors an offline store, predictions are cached, weights are quantized to fit accelerators, requests are batched onto GPUs under latency budgets, and drift monitors watch input distributions for the slow rot that no exception or error code ever signals. The unit of deployment is the pipeline; the "model" is just where the parameters live.

The connection this page maps is that every stage of that pipeline instantiates machinery the rest of systems engineering already knows — the feature store is a two-level cache hierarchy with a consistency twist, serving is a queueing and batching problem, artifact management is content addressing, and drift monitoring is the observability pipeline pointed at distributions instead of latencies. What makes ML serving distinctive is the *silence* of its failures: a broken cache throws; a feature skew between training and serving degrades accuracy by fractions of a percent and throws nothing. Failure propagation here is slow, statistical, and invisible to the tools most teams have, which is why the design levers — canary models, shadow traffic, point-in-time correctness — are all mechanisms for making silent failures loud.

## The Systems, Independently

**Model artifacts and the registry.** A trained model is a versioned artifact — weights, architecture, preprocessing, training-data pointer, evaluation metrics — stored in a registry (content-addressed or semver-ish), from which serving pulls an immutable reference. The registry's job is reproducibility of a different kind than code deploys: model quality depends on data as well as code, so the artifact must pin the dataset hash, the feature definitions, and the training commit, or "model v7" means different things next quarter.

**Feature stores, quantization, and GPU serving.** The *feature store* keeps engineered features in two coordinated views: an **offline store** (columnar, history-complete, used for training) and an **online store** (low-latency KV, milliseconds, used at request time), populated by the same pipelines so the two views agree. *Quantization* compresses weights (FP32 → FP16/BF16 → INT8) so models fit accelerator memory and batch deeper, trading a small, measurable accuracy cost for capacity. *GPU serving* batches concurrent requests (dynamic batching), because a GPU is a throughput device whose per-invocation overhead is paid regardless of batch size — the batcher is where the queueing policy lives.

**Drift monitoring.** Drift monitoring tracks input feature distributions, prediction distributions, and delayed ground-truth accuracy against baselines, alerting when training-time assumptions rot. It comes in three layers with different detection speeds: input drift (fast, noisy — the world changed but maybe harmlessly), output drift (fast, cheap — the score distribution moved), and outcome drift (slow, definitive — actual accuracy on labels that took weeks to arrive). A serving stack without all three learns about decay from its business metrics, which is the most expensive possible detector.

**Prediction caching.** When inputs repeat — the same query, the same document, the same user-item pair — the inference result can be cached keyed by a hash of the feature vector, turning a GPU-bound path into a memory-bound one. The catch is the cache key's completeness: two requests that map to identical features must hash identically (feature normalization must precede hashing), and a stale entry after a model version bump is worse than a miss — so prediction caches are versioned by model artifact, exactly like build caches keyed by toolchain. The demand-filled, versioned, staleness-bounded structure is the same at every layer of this pipeline; only the latency budget changes.

## How the Chain Feeds Each Other

Request path: client → API → feature retrieval (online store, plus caches) → preprocessing → model (quantized, batched with concurrent requests) → postprocessing → response, with the prediction written to logs and (when labels arrive) to the training corpus. Build path: data sources → offline store → training → artifact → registry → canary/shadow deployment → full rollout. Monitor path: production logs → drift dashboards → retraining triggers → back to the build path. The three paths form one loop, and the loop's seams are where failures live: the seam between offline and online stores (skew), the seam between artifact and serving (quantization and version skew), and the seam between serving and monitoring (lag between behavior change and detection).

Shared invariants: **point-in-time correctness** — training features must be computed *as of the prediction moment*, never using data that did not exist yet (leakage); **train/serve parity** — the same feature definition, the same preprocessing, the same version, executed twice (once batch, once online) with identical results; **artifact immutability** — a serving process must resolve to exactly one artifact version for its whole lifetime, or a restart silently changes the model.

## The Shared Principle

**Every stage of ML serving is a demand-filled, versioned cache with a staleness budget, and every "silent" failure is a cache-consistency failure between two views that were supposed to be replicas of one definition.** The online feature store is the RAM layer and the offline store is the disk layer of one hierarchy (the atlas's caching lens in [virtual-memory-caching.md](./virtual-memory-caching.md)): same keying by identity, same demand filling, same stale-read hazards — but the *consistency contract between the two layers is stronger than a normal cache*, because the training consumer and the serving consumer must observe the *same values for the same entity*, or the model is evaluated on one distribution and deployed on another. Serving is queueing: dynamic batching is a delay-vs-throughput discipline exactly like Nagle's algorithm or group commit — wait a few milliseconds, fill a batch, amortize the fixed cost — and its tail-latency math is Little's Law arithmetic. Artifact management is content addressing: hash the inputs (code, data, config), get an immutable, deduplicable, verifiable object.

## Where the Analogy HOLDS and BREAKS

| Aspect | HOLDS | BREAKS |
|---|---|---|
| Feature store as cache | Two-level hierarchy, identity-keyed, latency cliff between layers | The two layers must agree *semantically*, not just eventually — an ordinary cache tolerates stale values, a feature store punishes even *correct-but-differently-computed* values (skew without staleness) |
| Serving as queueing | Batching, utilization cliffs, Little's Law all transfer verbatim | Batch quality couples to *content*: batching requests of mixed models or feature payloads changes compute per batch, so the "service time" is not independent of the arrival process |
| Model as deployable artifact | Immutable, versioned, promoted through environments like a binary | Quality is not preserved by immutability: the artifact's accuracy decays as the *world* drifts, with no code change at all — deployments rot in place |
| Monitoring as observability | Fan-in, sampling, dashboards, burn-rate alerts transfer | Labels arrive late or never (ground truth for a rejected loan takes months), so the "golden signal" is delayed, biased (you only learn outcomes for decisions you approved), and probabilistic |

The pattern also recurses, which is the strongest evidence it is a real pipeline rather than a diagram convention: a modern ranking system is itself a chain of models (candidate retrieval, then a heavier ranker, then a business-rules layer), each stage with its own artifact, cache, and latency budget — the request path of the outer pipeline is the serving path of an inner one. When an interviewer asks you to "add ML to this system," the strong answer decomposes the box the same way this page decomposed it: where do features come from, what is the freshness contract, what runs on the latency-critical path versus offline, and what watches the seams.

## Failure Propagation

**Feature skew between training and serving.** The canonical silent killer: training computes `avg_transaction_7d` from nightly batch over *completed* transactions; serving computes it on the fly over transactions visible at request time — different inclusion windows, different null handling, maybe a different time zone. Every request is served by a model whose input distribution is shifted from what it was trained on. Nothing errors: predictions look plausible, dashboards stay green, and the drift monitor (if it watches only *input* distributions) sees nothing abnormal, because the skewed feature is self-consistently wrong in production. Propagation: skew → miscalibration → business metric decay (fraud caught down 3%) → discovered weeks later by backtest, if ever. The family also includes staleness (online store last refreshed 6 hours ago during a pipeline outage — a cache expiry failure wearing ML clothes) and leakage (training features that could not exist at prediction time — the offline store violating point-in-time correctness, which inflates offline metrics and deflates production ones).

**Serving-path propagation.** Quantization converts a gradual accuracy/latency trade into a cliff: INT8 calibration on a skewed sample can collapse accuracy on rare classes — the tail the model existed for. Batching propagates load back in time: when traffic doubles and the batcher waits to fill batches, p50 is fine and p99 doubles — a pure queueing failure that page-owners blame on "the model being slow." Drift detection closes the loop too late by construction: label lag means detection follows impact by the label's own delay, so every drift alarm is an after-the-fact statement.

## A Concrete Worked Example

**The arithmetic of batching.** A GPU takes 3 ms to run one request and a fixed ~5 ms overhead per batch regardless of size; per-request cost is `5/B + 3` ms of GPU time. `B=1`: 8 ms, capacity 125 req/s. `B=16`: 5.3 ms per request, capacity ≈ 3,000 req/s — a 24× throughput gain for 2.3 ms added latency. Dynamic batching with a 5 ms wait window at 2,000 req/s arrival collects ≈ 10 requests per batch window; at 50 req/s it collects 0.25, so the wait window mostly *adds* latency for nothing — the batching parameter must be tuned to arrival rate, which is why a batcher tuned in load testing fails in production traffic shapes. Now the tail: with batch wait w and service time s, response latency ≈ w + s, but the *queueing* before batching follows M/M/c dynamics — at 80% utilization, expected queue delay is already ~4× the service time; at 90%, ~9×. A "model latency SLO" of p99 < 100 ms therefore buys capacity only up to ~70–80% utilization, and the canary that raises tokens-per-request by 20% raises service time 20% and pushes the fleet over the knee.

**Skew, with numbers.** A fraud model's offline feature uses 7 complete days (AUC 0.94 in training); the online implementation effectively sees 6.2 days of data. Retraining with the serving-side definition drops AUC to 0.92 — and closing the gap recovers 0.02 AUC *for free*, which on a 1M-transaction/day flow at $2 average fraud size is roughly $40,000/day of detection the skew was silently eating.

## Design Levers

- **Point-in-time-correct offline joins.** The feature store's core feature: training rows join feature history *as of the label timestamp*, eliminating leakage by construction and guaranteeing offline features are computable online — the structural fix for skew.
- **Canary models and shadow traffic.** Route 1% of live traffic to the candidate artifact with per-variant metrics (the flag-rollout playbook); *shadow* the candidate on 100% of traffic without serving its outputs, diffing predictions against the incumbent — the only cheap way to measure behavior on inputs the incumbent handles rarely.
- **Versioned, content-addressed artifacts.** Registry entries pin code commit, data hash, feature-definition version, and quantization recipe; serving resolves an immutable reference and restarts are bit-stable.
- **Batching as a tuned, monitored parameter.** Wait windows and max batch size set per model per traffic shape; utilization alarms at the queueing knee (~70–80%), not at CPU-style 90%.
- **Drift monitoring with layered signals.** Input-distribution drift (fast, noisy), prediction-distribution drift (fast, cheap), delayed label metrics (slow, definitive) — with explicit assumptions about label lag recorded next to each alarm.

## Interview Questions

1. "A model is a pipeline" — enumerate the stages and name one *silent* failure per stage that no exception handler would catch.
2. Explain feature skew to a systems engineer using only caching vocabulary. Why does eventual consistency not save you here, and what property of the offline/online pair replaces it?
3. Your GPU fleet's p50 is fine but p99 tripled after a traffic shift. Walk the queueing/batching arithmetic, and state which parameters move the utilization knee.
4. Design a shadow deployment for a new ranking model: what do you log, what do you compare, and what can shadow traffic *never* tell you?
5. Why does label delay make drift monitoring structurally different from latency monitoring, and what layered-signal design compensates?

## Key Takeaways

- The deployed unit is a pipeline — artifacts, feature stores, caches, quantized weights, batchers, monitors — and every stage has its own failure modes that compose multiplicatively.
- Feature stores are a two-level cache hierarchy with an unusually strict semantic-consistency contract; feature skew is the consistency failure of that hierarchy, and it is silent by construction.
- Serving is queueing with content-coupled batch costs: batching arithmetic (fixed overhead amortized over B) and utilization knees govern capacity, and they must be tuned to real traffic shapes.
- Models rot in place: drift makes "immutable artifact" a statement about identity, not quality, so monitoring and retraining loops are part of the deployment, not afterthoughts.
- Canary models and shadow traffic are the levers that make silent failures loud before users pay for them — reuse the flag-rollout and telemetry machinery rather than inventing ML-specific tools.

## Cross-References

- [./virtual-memory-caching.md](./virtual-memory-caching.md) — Virtual Memory and Caching — the offline/online feature store is one more two-level, demand-filled hierarchy with a latency cliff.
- [./observability-pipeline.md](./observability-pipeline.md) — The Observability Pipeline — drift monitoring is that fan-in pointed at distributions; label lag plays the role of sampling bias.
- [./backpressure.md](./backpressure.md) — Backpressure — bounded queues and demand propagation govern the batching layer under GPU saturation.
- [./load-balancing-partitioning.md](./load-balancing-partitioning.md) — Load Balancing and Partitioning — canary routing and per-model pools are placement decisions over a changing fleet.
- [../followup-tree/redis-caching.md](../followup-tree/redis-caching.md) — Redis Caching — the online-store lookups and prediction caches in their canonical implementation.
- [../../data-engineering/stream-processing.md](../../data-engineering/stream-processing.md) — Stream Processing — the computation that keeps online features fresh and bounded in staleness.
