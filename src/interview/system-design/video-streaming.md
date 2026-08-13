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
          Bandwidth: 167M × 3600 × 5 Mbps = ~230 Pbps peak

CDN offload: 95% of traffic served from CDN edge
Origin bandwidth: 5% of total = ~11.5 Pbps
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

## 🔗 Cross-References

- [Search Engine](./search.md) — Video search implementation
- [Key-Value Store](./kv-store.md) — Metadata storage
- [Architecture Concepts](../../cheatsheets/architecture.md) — CDN, caching
- [Networking Questions](../network-questions.md) — Streaming protocols
