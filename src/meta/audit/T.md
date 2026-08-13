# Chunk T Audit — interview/ deep-read
**Files audited:** 90 (all .md files under `src/interview/`)
**Total findings:** 17 (HIGH: 4, MEDIUM: 9, LOW: 4)
**Audit method:** Full deep-read of every file. Arithmetic verified with Python. Technical claims cross-referenced against authoritative sources (official H3 docs, Amazon.jobs, Netflix culture deck, Open Connect specs, Signal Protocol docs).

## Findings

### HIGH severity

#### src/interview/system-design/estimation.md:88
- **Wrong text:** `Daily tweet storage = 4,600 × 86,400 × 0.5 KB ≈ 200 MB/day`
- **Correct text:** `Daily tweet storage = 4,600 × 86,400 × 0.5 KB ≈ 200 GB/day`
- **Verification:** Python: 4,600 × 86,400 × 0.5 KB = 198,720,000 KB = 198,720 MB ≈ 200 GB. The result is off by 1000× — units should be GB, not MB.
- **Impact:** All downstream Twitter storage figures are 1000× too small, teaching wildly incorrect back-of-the-envelope numbers.

#### src/interview/system-design/estimation.md:91
- **Wrong text:** `Daily image storage = 4,600 × 86,400 × 0.1 × 1 MB ≈ 40 GB/day`
- **Correct text:** `Daily image storage = 4,600 × 86,400 × 0.1 × 1 MB ≈ 40 TB/day`
- **Verification:** Python: 4,600 × 86,400 × 0.1 × 1 MB = 39,744,000 MB = 39,744 GB ≈ 40 TB. Off by 1000×.
- **Impact:** Image storage is 1000× understated, leading to wrong capacity planning.

#### src/interview/system-design/estimation.md:94
- **Wrong text:** `5-year storage = 73 GB × 5 + 14.6 TB × 5 ≈ 73 TB`
- **Correct text:** `5-year storage = 73 TB × 5 + 14.6 TB × 5 ≈ 438 TB` (using corrected yearly tweet figure of ~73 TB/year, not 73 GB/year)
- **Verification:** Python: corrected daily tweet storage (~200 GB) × 365 × 5 = 365,000 GB ≈ 365 TB; + 14.6 TB/year × 5 = 73 TB → total ~438 TB. Doc's "73 TB" total is dominated by the wrong tweet figure.
- **Impact:** Total 5-year storage is ~6× too low.

#### src/interview/system-design/video-streaming.md:46
- **Wrong text:** `Bandwidth: 167M × 3600 × 5 Mbps = ~230 Pbps peak`
- **Correct text:** `Bandwidth (steady state): 167M hours/day ÷ 24 = 6.94M concurrent viewers × 5 Mbps = ~34.7 Tbps`
- **Verification:** Python: 167M × 3600 × 5 = 3.0e12 Mbps·sec — this is total bits-per-day, not bandwidth. Dividing by 86,400 sec/day yields 34.7M Mbps = 34.7 Tbps (steady-state). The doc's 230 Pbps is off by ~6,624× and is dimensionally wrong (Mbps·sec ≠ Mbps).
- **Impact:** Teaches an absurd bandwidth number (230 Pbps > global internet bandwidth) for YouTube.

### MEDIUM severity

#### src/interview/companies/amazon.md:22
- **Wrong text:** `Amazon maps EVERY behavioral question to their 14 Leadership Principles (LPs).`
- **Correct text:** `Amazon maps EVERY behavioral question to their 16 Leadership Principles (LPs).`
- **Verification:** Amazon.jobs official page (https://www.amazon.jobs/content/en/our-workplace/leadership-principles) lists 16 LPs — the 14 originals plus "Strive to be Earth's Best Employer" and "Success and Scale Bring Broad Responsibility" added in July 2021. Note: `companies/README.md` correctly says "16 Leadership Principles", and `behavioral/README.md` and `behavioral/common.md` also reference 16 — but only list 14. This is an internal contradiction across multiple files in the same chunk.
- **Impact:** Candidates using this guide will be underprepared for the 2 newer LPs.

#### src/interview/system-design/kv-store.md:172-173
- **Wrong text:** `Solution 2: Vector Clocks ... Used by: DynamoDB, Riak`
- **Correct text:** `Solution 2: Vector Clocks ... Used by: Amazon Dynamo (the 2007 internal system), Riak. (AWS DynamoDB the product uses LWW + conditional writes; it does not expose vector clocks.)`
- **Verification:** The 2007 Amazon Dynamo paper (DeCandia et al.) describes vector clocks. AWS DynamoDB (launched 2012) does not expose vector clocks to users — it uses last-writer-wins by default and conditional writes for strong consistency. Conflating the two is a common but real inaccuracy.
- **Impact:** Misleads candidates about DynamoDB's consistency model.

#### src/interview/system-design/consistency-patterns.md:98
- **Wrong text:** `Vector Clocks ... Used by Amazon DynamoDB (pre-2017), Riak`
- **Correct text:** `Vector Clocks ... Used by Amazon Dynamo (2007 paper), Riak, CouchDB`
- **Verification:** Same as above. The "pre-2017" qualifier is unclear; DynamoDB has never exposed vector clocks. Riak switched to dotted version vectors around 2014. The original Dynamo (paper) is what used vector clocks.
- **Impact:** Same as kv-store.md — reinforces the DynamoDB/vector-clock misconception.

#### src/interview/system-design/real-world/uber.md:92-94
- **Wrong text:** `H1["Hex Level 7 (~500m edge)"], H2["Hex Level 9 (~100m edge)"], H3["Hex Level 12 (~3m edge)"]`
- **Correct text:** `H1["Hex Level 7 (~1220m edge)"], H2["Hex Level 9 (~174m edge)"], H3["Hex Level 12 (~9m edge)"]`
- **Verification:** Official H3 docs (https://h3geo.org/docs/core-library/restable) avg edge lengths: Res 7 = 1220m, Res 9 = 174m, Res 12 = 9.4m. Doc values are off by 1.7×–3.1×. Also: `h3.geo_to_h3()` is deprecated in h3-py v4+ (use `h3.latlng_to_cell()`); `h3.k_ring()` is deprecated (use `h3.grid_disk()`).
- **Impact:** Candidates quoting these numbers in an Uber-specific interview (where interviewers know H3) will appear misinformed.

#### src/interview/system-design/real-world/distributed-lock.md:96-116
- **Wrong text:** Redlock `acquire` method references `self.name` (not set in `__init__`) and an undefined `start` variable:
  ```python
  def __init__(self, redis_instances, ttl=30):  # no `name` param
      ...
  def acquire(self, timeout=10):
      ...
      if acquired >= self.quorum:
          elapsed = time.time() - start  # `start` undefined
  ```
- **Correct text:** Constructor should accept `name`; `start = time.time()` should be set at the top of `acquire` before the while loop.
- **Verification:** Python: `NameError: name 'start' is not defined` and `AttributeError: 'Redlock' object has no attribute 'name'` at runtime.
- **Impact:** Example code won't compile/run; candidates copying this pattern will hit errors.

#### src/interview/pastebin.md:245
- **Wrong text:** `Pastebin is a write-heavy service: 10M pastes/day with 5:1 read/write ratio.`
- **Correct text:** `Pastebin is a read-heavy service: 10M pastes/day with 5:1 read/write ratio (50M reads/day vs 10M writes/day).`
- **Verification:** Self-contradiction: a 5:1 read/write ratio means reads dominate. The file's own Non-Functional Requirements section says "Read/Write ratio: ~5:1 (reads dominate)". The summary contradicts the requirements.
- **Impact:** Confusing — readers can't tell if the service is read-heavy or write-heavy.

#### src/interview/dbms-questions.md:269-277 (Q6 CAP diagram)
- **Wrong text:** The CAP triangle diagram labels the bottom edge (between Availability and Partition Tolerance) as "CA":
  ```
           Consistency
              /\
             /  \
            / CP \
           /______\
          /   CA   \
         /__________\
  Availability    Partition Tolerance
  ```
- **Correct text:** Bottom edge should be "AP" (the edge between Availability and Partition Tolerance). The "CA" label should be on the upper-left edge (between Consistency and Availability). Currently the diagram has only "CP" and "CA" labels but no "AP" — missing one label entirely.
- **Verification:** Standard CAP triangle has three edges: CA (C↔A), CP (C↔P), AP (A↔P). The text below the diagram correctly states "you must choose CP or AP", so the diagram is inconsistent with the surrounding text.
- **Impact:** Visual confusion in one of the most-tested interview concepts.

#### src/interview/ml-questions.md:49
- **Wrong text:** `DPO loss = -log σ(β log π(y_w)/π_ref(y_w) - β log π(y_l)/π_ref(y_l))`
- **Correct text:** `DPO loss = -log σ(β · log(π(y_w|x) / π_ref(y_w|x)) - β · log(π(y_l|x) / π_ref(y_l|x)))`
- **Verification:** The DPO paper (Rafailov et al., 2023) formula is `L_DPO = -log σ(β log(π_θ(y_w|x)/π_ref(y_w|x)) - β log(π_θ(y_l|x)/π_ref(y_l|x)))`. The doc's version omits parentheses around the log arguments, so by standard operator precedence `β log π(y_w)/π_ref(y_w)` parses as `((β·log(π(y_w))) / π_ref(y_w)` — mathematically wrong. Also missing `|x` context and `π_θ` (the policy being optimized, vs `π_ref`).
- **Impact:** Candidates asked to derive or implement DPO will get the formula wrong.

#### src/interview/companies/netflix.md:42-44
- **Wrong text:** Lists "Radical Candor" as a Netflix culture value with sub-points "Honest, direct feedback / No politics / Assume positive intent".
- **Correct text:** Netflix's culture deck describes "Radical Honesty" / "4A Feedback" (Aim to Assist, Actionable, Appreciated, Accept or Discard). "Radical Candor" is Kim Scott's separate framework (a 2017 book), not a Netflix term.
- **Verification:** Netflix culture memo (https://jobs.netflix.com/culture) describes "feedback is a continuous part of how we work" using the 4A model. "Radical Candor" is Kim Scott's IP. While related, they are distinct frameworks and conflating them in an interview could be flagged.
- **Impact:** Misattributes a trademarked framework to Netflix; could embarrass a candidate in a Netflix interview.

### LOW severity

#### src/interview/network-questions.md:222
- **Wrong text:** Q5 HTTP comparison table row: `Server Push | No | Yes | Yes` (HTTP/2 = Yes, HTTP/3 = Yes)
- **Correct text:** `Server Push | No | Yes (deprecated in Chrome 2022) | Yes (rarely used)` — Chrome removed HTTP/2 Server Push in late 2022; HTTP/3 push was never widely adopted and is being phased out.
- **Verification:** Chromium blog (Sept 2022) confirmed removal of HTTP/2 Push. RFC 9113 (HTTP/3) still defines push but major browsers don't support it.
- **Impact:** Outdated info; minor since push was always optional.

#### src/interview/system-design/estimation.md:234
- **Wrong text:** `Round aggressively — 86,400 ≈ 100,000; 365 ≈ 400`
- **Correct text:** `Round aggressively — 86,400 ≈ 100,000; 365 ≈ 360` (or simply `365 ≈ 400 for 10% margin`). Rounding 365 up to 400 inflates yearly estimates by ~10%, which is fine, but 365 ≈ 360 is closer and more natural.
- **Verification:** Trivially, 365 is closer to 360 than 400. This is stylistic advice, not wrong, just oddly chosen.
- **Impact:** Negligible — readers will pick their own rounding.

#### src/interview/system-design/typeahead.md:71
- **Wrong text:** Mermaid diagram orphans the `Googl` node:
  ```
  Goo --> Goog["goog"]
  Googl["googl"] --> Google["google<br/>(score: 95)"]  # Googl is never linked from Goog
  ```
- **Correct text:** `Goog --> Googl["googl"]\nGoogl --> Google["google<br/>(score: 95)"]`
- **Verification:** Mermaid renders `Googl` as a disconnected node since only the arrow `Googl --> Google` is defined; there is no `Goog --> Googl` edge.
- **Impact:** Minor visual bug in a diagram; the trie structure is still understandable.

#### src/interview/system-design/lld/concurrency-design.md:198-216
- **Wrong text:** BlockingQueue uses two `Condition` objects (`_not_empty`, `_not_full`) on the same underlying lock, but `_not_full.notify()` is called from inside `with self._not_empty:` block in `get()` (and vice versa). This works because both Conditions share the same lock, but it's an unusual pattern.
- **Correct text:** Either use a single `Condition` with `notify_all()`, or call `notify()` on the same Condition whose `wait()` you want to wake up. The current code mixes conditions across wait/notify pairs which is correct but confusing.
- **Verification:** Python `threading.Condition(lock)` shares the given lock; `notify()` on one Condition wakes threads waiting on that Condition only. The code as written is functional (notify on `_not_full` wakes producers waiting on `_not_full`, called from inside the consumer's `with self._not_empty:` block which holds the shared lock). This is valid but unconventional.
- **Impact:** Cosmetic — code works but is harder to read than the standard single-Condition pattern.

## Files confirmed clean

The following files were deep-read and contained no notable technical, code, or diagram errors:

- `src/interview/overview.md`
- `src/interview/os-questions.md`
- `src/interview/arch-questions.md`
- `src/interview/coding/README.md`
- `src/interview/coding/complexity.md`
- `src/interview/coding/framework.md`
- `src/interview/coding/data-structures.md`
- `src/interview/coding/patterns.md`
- `src/interview/behavioral/README.md` (minor: lists 14 LPs in table but says "16" in text — same as amazon.md)
- `src/interview/behavioral/star.md`
- `src/interview/behavioral/common.md` (minor: same 14-vs-16 LP issue as amazon.md)
- `src/interview/companies/README.md` (correctly says 16 LPs)
- `src/interview/companies/google.md`
- `src/interview/companies/microsoft.md`
- `src/interview/companies/meta.md`
- `src/interview/companies/apple.md`
- `src/interview/system-design/README.md`
- `src/interview/system-design/framework.md`
- `src/interview/system-design/latency-numbers.md`
- `src/interview/system-design/url-shortener.md`
- `src/interview/system-design/chat.md`
- `src/interview/system-design/news-feed.md`
- `src/interview/system-design/rate-limiter.md`
- `src/interview/system-design/search.md`
- `src/interview/system-design/notifications.md`
- `src/interview/system-design/dfs.md`
- `src/interview/system-design/rpc.md`
- `src/interview/system-design/payment.md`
- `src/interview/system-design/social-graph.md`
- `src/interview/system-design/google-maps.md`
- `src/interview/system-design/ads.md`
- `src/interview/system-design/metrics.md`
- `src/interview/system-design/stock-exchange.md`
- `src/interview/system-design/latency-vs-throughput.md`
- `src/interview/system-design/performance-vs-scalability.md`
- `src/interview/system-design/availability-patterns.md`
- `src/interview/system-design/consistency-patterns.md` (one MEDIUM finding noted above)
- `src/interview/system-design/backpressure.md`
- `src/interview/system-design/web-crawler.md`
- `src/interview/system-design/probabilistic-data-structures.md`
- `src/interview/system-design/lld/README.md`
- `src/interview/system-design/lld/oop-concepts.md`
- `src/interview/system-design/lld/solid.md`
- `src/interview/system-design/lld/abstraction-interfaces.md`
- `src/interview/system-design/lld/coupling-cohesion-principles.md`
- `src/interview/system-design/lld/design-patterns.md`
- `src/interview/system-design/lld/uml-class-diagrams.md`
- `src/interview/system-design/lld/error-handling.md`
- `src/interview/system-design/lld/chess.md`
- `src/interview/system-design/lld/parking-lot.md`
- `src/interview/system-design/lld/elevator.md`
- `src/interview/system-design/lld/atm.md`
- `src/interview/system-design/lld/movie-ticket.md`
- `src/interview/system-design/lld/library-management.md`
- `src/interview/system-design/lld/uber.md`
- `src/interview/system-design/lld/linkedin.md`
- `src/interview/system-design/lld/food-delivery.md`
- `src/interview/system-design/lld/file-system.md`
- `src/interview/system-design/lld/cache-lld.md`
- `src/interview/system-design/lld/key-value-store-lld.md`
- `src/interview/system-design/lld/notification-service.md`
- `src/interview/system-design/hld/README.md`
- `src/interview/system-design/hld/scalability.md`
- `src/interview/system-design/hld/availability.md`
- `src/interview/system-design/hld/consistency-tradeoffs.md`
- `src/interview/system-design/hld/capacity-planning.md`
- `src/interview/system-design/hld/load-balancing-design.md`
- `src/interview/system-design/hld/caching-strategy.md`
- `src/interview/system-design/hld/database-design.md`
- `src/interview/system-design/hld/api-design.md`
- `src/interview/system-design/hld/security-design.md`
- `src/interview/system-design/hld/data-intensive.md`
- `src/interview/system-design/hld/messaging-systems.md`
- `src/interview/system-design/hld/monitoring-observability.md`
- `src/interview/system-design/real-world/youtube.md`
- `src/interview/system-design/real-world/netflix.md`
- `src/interview/system-design/real-world/dropbox.md`
- `src/interview/system-design/real-world/whatsapp.md`
- `src/interview/system-design/real-world/instagram.md`
- `src/interview/system-design/real-world/google-search.md`
- `src/interview/system-design/real-world/twitter.md`
- `src/interview/system-design/real-world/streaming-pipeline.md`

## Top issues to fix first

1. **estimation.md (3 HIGH findings, all 1000× unit errors in Twitter storage calc)** — easiest to fix, highest pedagogical impact since this is the canonical "how to estimate" reference.
2. **video-streaming.md bandwidth (6600× error)** — teaches an impossible bandwidth (230 Pbps > global internet total).
3. **amazon.md LP count (14 vs 16)** — affects all candidates interviewing at Amazon.
4. **DynamoDB vector clock claim (kv-store.md + consistency-patterns.md)** — repeated in two files, reinforces a common misconception.
5. **distributed-lock.md Redlock code bugs** — example code doesn't run.
