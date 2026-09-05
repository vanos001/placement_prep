# Design a Video Streaming Platform

> **Difficulty:** ⭐⭐⭐⭐ | **Asked at:** Netflix, YouTube, Amazon | **Time:** 45 minutes

## 🎯 Problem Statement

Design a video streaming platform like YouTube or Netflix that:
- Allows users to upload, store, and stream videos
- Supports adaptive bitrate streaming
- Handles millions of concurrent viewers
- Provides recommendations and search

---

## Step 1: Requirements

### Functional Requirements
1. Users can upload videos
2. Users can stream videos (on-demand)
3. Adaptive bitrate streaming (adjust quality to bandwidth)
4. Video search and recommendations
5. Like, comment, subscribe
6. View count and analytics

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Video start time | < 2 seconds |
| Streaming quality | Adaptive 240p to 4K |
| Availability | 99.99% |
| Concurrent viewers | 10M+ |
| Upload processing | < 30 minutes for 1-hour video |

### Capacity Estimation

```
Uploads: 500 hours of video uploaded per minute (YouTube scale)
Storage: 500 hours/min × 60 min × 24hr = 720,000 hours/day
         × 5 GB/hour (raw) = 3.6 PB/day raw
         × 5 renditions = 18 PB/day encoded

Streaming: 2B daily views, average 5 minutes
          = 10B minutes/day = 167M hours/day
          Average bitrate: 5 Mbps
          Steady-state bandwidth: 167M hours/day ÷ 24 = 6.94M concurrent viewers × 5 Mbps ≈ 34.7 Tbps

CDN offload: 95% of traffic served from CDN edge
Origin bandwidth: 5% of total ≈ 1.7 Tbps
```

---

## Step 2: High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIDEO STREAMING PLATFORM                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  UPLOAD PATH:                                                   │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌───────┐ │
│  │  Client  │────→│  Upload  │────→│  Video   │────→│  CDN  │ │
│  │ (Upload) │     │  Service │     │  Encoder │     │ Origin│ │
│  └──────────┘     └──────────┘     └──────────┘     └───────┘ │
│                        │                │                       │
│                   ┌────▼────┐     ┌─────▼─────┐               │
│                   │  S3     │     │  Message  │               │
│                   │ (Raw)   │     │  Queue    │               │
│                   └─────────┘     └───────────┘               │
│                                                                 │
│  STREAMING PATH:                                                │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌───────┐ │
│  │  Client  │────→│  CDN     │────→│  Origin  │────→│ Video │ │
│  │(Watch)   │     │  Edge    │     │  Server  │     │ Store │ │
│  └──────────┘     └──────────┘     └──────────┘     └───────┘ │
│                                                                 │
│  METADATA PATH:                                                 │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│  │  Client  │────→│  API     │────→│ Metadata │               │
│  │          │     │  Gateway │     │  Service │               │
│  └──────────┘     └──────────┘     └──────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 3: Deep Dive

### Video Upload & Processing Pipeline

```
Upload Flow:
1. Client requests pre-signed S3 URL
2. Client uploads raw video directly to S3
3. S3 triggers Lambda → Notify encoding service via SQS

Encoding Pipeline:
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Raw     │────→│  Transcode│────→│  Quality │────→│  CDN     │
│  Video   │     │  Service  │     │  Check   │     │  Upload  │
│  (S3)    │     │ (FFmpeg)  │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘

Encoding Renditions (HLS/DASH):
├── 240p  (400 kbps)  — Mobile, slow connections
├── 360p  (800 kbps)  — Mobile standard
├── 480p  (1.5 Mbps)  — SD quality
├── 720p  (3 Mbps)    — HD quality
├── 1080p (6 Mbps)    — Full HD
├── 1440p (13 Mbps)   — 2K
└── 2160p (20 Mbps)   — 4K

Output Format: HLS (HTTP Live Streaming)
├── Master manifest (.m3u8) — Lists available qualities
├── Media manifests (.m3u8) — Lists segments for each quality
└── Video segments (.ts)    — 6-second chunks

Parallel Processing:
├── Split video into chunks (5-minute segments)
├── Encode each chunk in parallel across workers
├── Stitch chunks back together
└── Reduces encoding time from hours to minutes
```

### Adaptive Bitrate Streaming (ABR)

```
How ABR Works:
1. Client downloads master manifest
2. Starts with lowest quality (fast start)
3. Measures download bandwidth every segment
4. Switches quality based on bandwidth

Client Algorithm:
┌─────────────────────────────────────────────────┐
│  bandwidth = measure_download_speed()           │
│  buffer_level = get_buffer_duration()           │
│                                                 │
│  if buffer_level < 10 seconds:                  │
│      quality = select_lower_quality()           │
│  elif buffer_level > 30 seconds:                │
│      quality = select_higher_quality()          │
│  else:                                          │
│      quality = select_matching_quality(bandwidth)│
└─────────────────────────────────────────────────┘

Segment Sizes (6 seconds each):
  240p:  300 KB per segment
  720p:  2.25 MB per segment
  1080p: 4.5 MB per segment
```

### CDN Architecture

```
Multi-Tier CDN:
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client  │────→│  Edge    │────→│  Regional│────→│  Origin │
│          │     │  Server  │     │  Cache   │     │  Server │
└──────────┘     └──────────┘     └──────────┘     └──────────┘

Edge Server (thousands globally):
├── Caches popular videos (80% of traffic)
├── Serves from nearest geographic location
├── Cache hit ratio target: > 95%

Regional Cache (dozens per region):
├── Caches less popular videos
├── Reduces origin load
└── Cache hit ratio target: > 80%

Origin Server:
├── Stores all videos (S3)
├── Only serves cache misses (< 5% of traffic)
└── Multiple origin servers for redundancy

Cache Strategy:
├── Popular videos: Pre-push to edge servers
├── Long-tail videos: Pull on first request, cache
├── Live streams: Push to edge in real-time
```

### Video Metadata & Search

```sql
-- Video metadata
CREATE TABLE videos (
    video_id     UUID PRIMARY KEY,
    user_id      UUID NOT NULL,
    title        VARCHAR(500),
    description  TEXT,
    duration_ms  INT,
    upload_time  TIMESTAMP,
    view_count   BIGINT DEFAULT 0,
    like_count   INT DEFAULT 0,
    status       ENUM('processing', 'ready', 'failed'),
    thumbnail_url VARCHAR(500)
);

-- Video files (multiple renditions)
CREATE TABLE video_files (
    video_id     UUID REFERENCES videos(video_id),
    quality      VARCHAR(10),  -- '720p', '1080p'
    format       VARCHAR(10),  -- 'hls', 'dash'
    s3_key       VARCHAR(500),
    bitrate_kbps INT,
    file_size_bytes BIGINT,
    PRIMARY KEY (video_id, quality, format)
);
```

### Recommendation Engine

```
Recommendation Pipeline:
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  User    │────→│ Candidate│────→│  Ranking │────→│  Final   │
│  Signal  │     │  Gen     │     │  Model   │     │  List    │
└──────────┘     └──────────┘     └──────────┘     └──────────┘

Signals:
├── Watch history (what you watched)
├── Watch duration (how much you watched)
├── Likes/dislikes
├── Search queries
├── Subscription list
└── Similar users' behavior

Candidate Generation:
├── Collaborative filtering (users like you watched...)
├── Content-based (similar title/tags/channel)
├── Trending videos
└── Subscriptions new uploads

Ranking:
├── Click-through rate prediction
├── Watch time prediction
├── Engagement prediction (likes, comments)
└── Freshness boost
```

### Adaptive Bitrate: The Control Loop

ABR is not a server feature — it is a closed control loop on the client: the server publishes one playlist per quality rung; the client estimates bandwidth, picks a rung, downloads segments, and re-evaluates after every segment. Four things must be right: the manifest structure, the bandwidth estimator, the ladder, and the encoder-side invariants that make a switch safe.

**Master vs media playlists.** HLS defines exactly two playlist shapes [1]: "A Playlist is a Media Playlist if all URI lines in the Playlist identify Media Segments. A Playlist is a Master Playlist if all URI lines in the Playlist identify Media Playlists." The master playlist is the ladder's table of contents — each `EXT-X-STREAM-INF` entry declares one Variant Stream (a rung) with `BANDWIDTH`, the rung's "peak segment bit rate" [1] — and each rung's media playlist lists its segments, one URI per `EXTINF`, under `EXT-X-TARGETDURATION`, which "specifies the maximum Media Segment duration"; exceeding it "can trigger playback stalls or other errors" [1]. DASH (ISO/IEC 23009-1, profiled by DASH-IF IOP v5, constrained to CMAF ISO/IEC 23000-19 [2]) expresses the same split as MPD AdaptationSets/Representations; the loop is identical.

**Why segments are 2–10 seconds.** Segment length is the loop's control period, and it sits on a three-way trade-off. (1) *Startup latency*: a player fetches a few segments before starting, so 10-second segments mean multi-second joins. (2) *Switching granularity*: quality changes take effect only at segment boundaries — a 10s segment holds a stale decision for up to 10s, and a down-switch wastes up to a segment's worth of downloaded bytes. (3) *Encoding efficiency and request overhead*: every segment must start with a random-access point — "any Media Segment containing H.264 video SHOULD contain an Instantaneous Decoding Refresh (IDR)" [1] — so shorter segments mean more IDRs, smaller GOPs, worse compression at the same bitrate, plus more HTTP requests and bigger manifests. The 2–10s band is where these three curves flatten.

**The bandwidth estimator.** Two families dominate. *Throughput-window* estimators measure each segment's download rate, aggregate the last N segments (or T seconds) into a smoothed estimate, and pick the highest rung below it — fast to react, but misleading on tiny segments and CDN-fast paths where measured throughput overshoots the true bottleneck. *Buffer-occupancy* estimators ignore bandwidth entirely and switch on playback buffer level — the insight of the BOLA algorithm (SIGCOMM 2014 [4]): when throughput comfortably exceeds the chosen rung's bitrate, buffer level is the more stable signal, because it directly encodes the rebuffering headroom every rung choice spends. Production players blend both: throughput for coarse selection, buffer health as the guard on down-switches (the sketch in the ABR section above is this hybrid).

**Ladder design.** The ladder (240p@400 kbps → 4K@20 Mbps in Step 3) is a set of operating points on the rate-quality pareto curve — and each rung is a full copy of the library (storage math below), so rung count is a cost decision as much as a QoE one: too few rungs make adaptation coarse; too many, and a rung's marginal viewership never amortizes its storage, cache, and origin footprint. Per-title encoding attacks the fixed-ladder assumption: a title's rate-distortion curve is content-dependent (a static talking-head looks fine at a bitrate that ruins a soccer match), so the ladder is derived per asset — probe the source at a few bitrates, fit the curve, emit the title's own rungs. (Netflix originated this technique; its engineering blog was not fetchable this session, so the mechanism is stated without quotes rather than cited from memory.)

**Segment alignment across representations.** Switching is seamless only if all rungs agree on time, and RFC 8216 makes the invariants explicit — "Each Variant Stream MUST present the same content," "Matching content in Variant Streams MUST have matching timestamps," "Each Media Playlist in each Variant Stream MUST have the same target duration" — precisely "in order to allow clients to switch between them seamlessly" [1]. In practice every rung is encoded from one GOP clock: keyframes land on identical timestamps and segments cut on identical frame boundaries, so swapping rung A's segment for rung B's at a boundary swaps equivalent media. Alignment also enables byte-range addressing: "The EXT-X-BYTERANGE tag indicates that a Media Segment is a sub-range of the resource identified by its URI" [1] — one physical object per rung can back all its segments (fewer origin objects, friendlier caching). The classic bug is misaligned keyframes, which pop or glitch at every switch — the RFC adds that Variant Streams SHOULD contain the same encoded audio bitstream, so clients can "switch between Variant Streams without audible glitching" [1].

### The Storage/CDN Math of a Library

Do the catalog math once and the rest of the architecture becomes inevitable (all computations in this section were run with python3 this session). One hour of 1080p at 10 Mbps: 10 × 10⁶ bit/s × 3,600 s ÷ 8 = **4.5 GB**. A 100,000-title catalog at that rate is 100k × 4.5 GB = **450 PB** — of *1080p-only* video. You publish the whole ladder, not one rung: the ladder in Step 3 sums to 44.7 Mbps across rungs vs 6 Mbps for 1080p alone — **7.45×** — so the full-ladder library is ≈ **3,350 PB**. That multiplication decides where the money flows: object-store capacity is the *cheap* part (write-once, rarely egressed), while every byte the origin serves is paid at egress rates — the whole delivery design exists to push origin egress toward zero.

**Zipf skew.** Request popularity concentrates: the classical measurement is Breslau et al.'s "Web caching and Zipf-like distributions: evidence and implications" (INFOCOM '99 [5]), which established that web object popularity follows a Zipf-like distribution — video catalogs behave the same way. Under a Zipf model with exponent 1 over 100k titles (computed this session): the top 100 titles draw ≈ 43% of all requests, the top 1,000 ≈ 62%. The long tail is real but individually cold — which is exactly why a cache hierarchy works for video.

**Cache-fill vs steady-state egress.** VOD segments are immutable once published, so caching them is trivially *correct* — no invalidation problem (the general case is [Caching Strategy](./hld/caching-strategy.md)'s subject). Two regimes matter:

- *Cache-fill*: the first request for an (edge, title, rung, segment) tuple misses to origin. Zipf skew bounds this: only a small active set is ever requested anywhere, so total fill traffic is a small multiple of the *active* catalog, not of the full 3.35 EB — and each object is fetched once per cache location, then absorbed.
- *Steady state*: origin egress ∝ (1 − hit ratio) × demand. With 10M concurrent viewers at 10 Mbps, aggregate demand is 100 Tbps (computed); at 95% CDN offload the origin serves 5 Tbps, at 98% it serves 2 Tbps, at 99% it serves 1 Tbps. One percentage point of offload is worth tens of Tbps — which is why the hit-ratio target ("> 95%" in the CDN section above) is the whole game for hot catalogs.

**Multi-CDN strategy.** No single CDN is uniformly best across regions and weeks, so large operators run two or three and steer by measurement: per (region, CDN) **rebuffer ratio**, **join time**, and **average delivered bitrate** collected from player SDK telemetry. Switching is measurement-driven — DNS weights, manifest base-URL selection, or per-region rules — and the metrics are ordered by user impact: a CDN with a better join time but worse rebuffer ratio loses.

**Origin-shield tier.** Without a mid-tier, a miss at every edge node fans out to origin concurrently — a new popular title's first hour can stampede the origin with many identical fetches of the same segment. The shield tier collapses that fan-out. CloudFront's Origin Shield doc: "all requests from all of CloudFront's caching layers to your origin go through Origin Shield, increasing the likelihood of a cache hit," and "Requests for content that is not in Origin Shield's cache are consolidated with other requests for the same object, resulting in as few as one request going to your origin" [6] — a tier AWS explicitly recommends for "Workloads that use multiple content delivery networks (CDNs)" [6], since each provider's miss fan-out then converges on the shield instead of multiplying at the origin.

### Transcoding at Scale: A Massive Async Batch Problem

The upload pipeline sketched in Step 3 is, at catalog scale, a giant asynchronous batch problem wearing a media costume. Write the flow as a DAG: **upload → probe → segment → encode ladder → package → publish**.

- *Probe* reads the source (duration, resolution, codec, scene complexity) and decides the title's ladder (per-title encoding above) — everything downstream depends on it.
- *Segment* cuts the source into chunks on GOP boundaries.
- *Encode* is one job per (chunk, rung) — embarrassingly parallel.
- *Package* stitches per-chunk segments, writes manifests, applies DRM packaging.
- *Publish* flips the metadata row from `processing` to `ready` (the state machine already in the schema above).

The DAG framing matters because nodes have dependencies, heterogeneous costs, and retry semantics — the same scheduling problems as any batch pipeline ([Batch Processing](../../data-engineering/batch-processing.md): DAG orchestration, idempotent partitioned jobs, backfill). The publish step is what makes this a platform rather than a script: `ready` flips atomically, and only then does the CDN fill.

**Fleet sizing** (computed this session with python3): at 100k uploads/day × 8 ladder rungs × 0.5–2 core-hours per rung (content length and codec complexity vary it; hardware encoders shift it down, quality presets up):

| Per-rung cost | Core-hours/day | Cores busy 24/7 |
|---|---|---|
| 0.5 h | 400,000 | 16,667 |
| 1.0 h | 800,000 | 33,333 |
| 2.0 h | 1,600,000 | 66,667 |

That is a fleet, not a queue consumer. **Content-chunk parallelism** makes the *latency* tractable inside it: a 1-hour title cut into 12 × 5-minute chunks × 8 rungs = 96 independent unit jobs; with 96 busy workers the title encodes in ≈ 1 wall-clock hour (computed). The trade-off is the same pareto as segment sizing: chunk boundaries force extra IDRs (worse compression) and demand exact GOP alignment to re-stitch.

**Spot/preemptible workers with checkpointing.** Encoding is restartable, stateless per unit, and enormous — the canonical spot workload ([Spot and Preemptible Instances](../../cloud/spot-preemptible.md) has the interruption math). The queue *is* the checkpoint: each (chunk, rung) job is small and idempotent, so an eviction loses at most the in-flight unit — a few minutes of re-encode, not a movie. The mid-case fleet at $0.014/vCPU-h computes to ≈ $11,200/day on-demand vs ≈ $3,360/day at a 70% spot discount — a 3.3× saving that survives nontrivial eviction rates precisely *because* rework is bounded to one unit job.

**Failure isolation: one bad segment ≠ one bad movie.** Encoders crash on malformed input; uploads are corrupt in creative ways. The unit of failure must be the unit job: per-segment retries with attempt caps, then poison-job quarantine (dead-letter + human review) so a pathological chunk blocks only itself; validation gates between stages (probe sanity, per-segment decode-verify before packaging); the title publishes only when all its unit jobs pass.

**Nightly re-encode campaigns vs incremental.** Publish-on-upload is the steady state; the catalog is a batch dataset that periodically needs bulk rewrites — new codec, redesigned ladder, DRM re-packaging, caption fixes. A full-catalog re-encode at the mid-case 1 core-hour/rung is 100k × 8 = **800,000 core-hours** (computed) — weeks of fleet time, so campaigns are planned like backfills: top of the Zipf curve first (the CDN keeps serving the old ladder for the long tail), rate-limited against production capacity, every (title, rung) job idempotent so the campaign pauses, resumes, and backfills like any other batch job.

---

## Step 4: Trade-offs

### Upload: Sync vs Async Processing
| Approach | Pros | Cons |
|----------|------|------|
| Sync (wait for encoding) | Immediate availability | Long wait, timeout risk |
| Async (queue + notify) | Fast upload response | Delayed availability |

**Choice:** Async — upload returns immediately, notify when processed.

### Storage: Object Store vs Block Storage
| Storage | Pros | Cons |
|---------|------|------|
| S3 (object) | Scalable, cheap, durable | No random access |
| EBS (block) | Random access | Limited size, expensive |

**Choice:** S3 for video files, EBS for temporary encoding workspace.

### Manifest: HLS vs DASH
| Format | Pros | Cons |
|--------|------|------|
| HLS | Apple ecosystem native, wider support | Apple-controlled |
| DASH | Open standard, more flexible | Less Apple integration |

**Recommendation:** Support both via transcoding pipeline.

## 📚 References

1. Pantos, R. (Ed.); May, W. "HTTP Live Streaming" (HLS), RFC 8216, August 2017 — <https://www.rfc-editor.org/rfc/rfc8216.txt> — fetched in full this session; all quoted sentences (master/media playlist definitions, EXT-X-STREAM-INF BANDWIDTH, EXT-X-TARGETDURATION, IDR requirement, Variant Stream alignment constraints, EXT-X-BYTERANGE, audio bitstream guidance) are verbatim from the fetched text.
2. DASH Industry Forum, "DASH-IF Interoperability Points, V5.0 (IOP V5)" — <https://dash-industry-forum.github.io/guidelines/iop-v5/> — fetched this session; used for the IOP v5 framing (defined for MPEG DASH ISO/IEC 23009-1, constrained to CMAF ISO/IEC 23000-19; includes Part 4 "Live and low-latency services"). No quotes.
3. Apple HLS documentation — <https://developer.apple.com/streaming/> — fetched this session (HTTP 200), but the page renders as a navigation shell with no quotable body; Apple's deeper authoring-spec pages returned 404 to fetchers this session. Kept as a pointer only; no claims cited to it.
4. Huang, T.-Y.; Johari, R.; McKeown, N.; Trunnell, M.; Watson, M. "A buffer-based approach to rate adaptation." *Proc. ACM SIGCOMM 2014*. DOI: [10.1145/2619239.2626296](https://doi.org/10.1145/2619239.2626296) — Crossref-verified this session (title + authors + venue + year).
5. Breslau, L.; Cao, P.; Fan, L.; Phillips, G.; Shenker, S. "Web caching and Zipf-like distributions: evidence and implications." *Proc. IEEE INFOCOM '99*. DOI: [10.1109/INFCOM.1999.749260](https://doi.org/10.1109/INFCOM.1999.749260) — Crossref-verified this session (title + authors + venue + year).
6. Amazon Web Services, "Use Amazon CloudFront Origin Shield" (CloudFront Developer Guide) — <https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/origin-shield.md> — fetched in full this session (markdown source); all quoted sentences verbatim.

*Note:* the Netflix Tech Blog (e.g., the per-title encoding post) returned HTTP 403 to automated fetchers this session; per this book's verification policy it is **not** quoted or cited — the per-title mechanism above is described generically.

## 🔗 Cross-References

- [Search Engine](./search.md) — Video search implementation
- [Key-Value Store](./kv-store.md) — Metadata storage
- [Architecture Concepts](../../cheatsheets/architecture.md) — CDN, caching
- [Networking Questions](../network-questions.md) — Streaming protocols
- [Caching Strategy Design](./hld/caching-strategy.md) — CDN caching layers, invalidation, and the general cache-stampede machinery invoked by origin shields
- [Batch Processing](../../data-engineering/batch-processing.md) — DAG orchestration, idempotent partitioned jobs, and backfill patterns the transcode pipeline reuses
- [Spot and Preemptible Instances](../../cloud/spot-preemptible.md) — eviction math and queue-based checkpointing behind the encode farm
- [How Netflix Works](./real-world/netflix.md) — Netflix-specific case study (Open Connect CDN, pipeline)
- [Video Streaming (Real-World)](./real-world/video-streaming.md) — live-vs-VOD machines and the reliability tour (rebuffer, flash crowds, DRM outages)
