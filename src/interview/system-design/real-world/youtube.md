# How YouTube Works

## Overview

YouTube is the world's largest video platform, serving 2+ billion monthly active users who watch over 1 billion hours of video daily. It handles massive video uploads (500+ hours of video uploaded every minute), transcoding, storage, and delivery — making it one of the most bandwidth-intensive applications on the internet.

## Key Requirements

### Functional
- Upload videos (any format, up to 256 GB or 12 hours)
- Stream videos on any device with adaptive bitrate
- Search and discover videos (recommendations, trending, subscriptions)
- Comments, likes, shares, playlists
- Live streaming
- Monetization (ads, Super Chat, memberships)
- Content moderation and copyright detection (Content ID)

### Non-Functional
- **Scale**: 2+ billion MAU, 1+ billion hours watched daily
- **Storage**: 800+ petabytes of video (growing ~500 hours/minute)
- **Bandwidth**: Peak of 25+ Tbps outbound
- **Latency**: Video start < 2 seconds
- **Availability**: 99.99%

## High-Level Architecture

```mermaid
graph TB
    subgraph "Creator"
        Upload[Video Upload]
    end

    subgraph "Viewer"
        Watch[Video Playback]
    end

    subgraph "Ingestion Pipeline"
        UploadSvc[Upload Service]
        Transcode[Transcoding Pipeline<br/>Bigtable/DAG]
        ThumbnailGen[Thumbnail Generator]
        ContentID[Content ID<br/>Copyright Check]
    end

    subgraph "Serving"
        CDN[YouTube CDN<br/>Google Global Cache]
        Origin[Origin Servers]
    end

    subgraph "Discovery"
        SearchSvc[Search Service]
        RecsSvc[Recommendation Service]
        Trending[Trending Service]
    end

    subgraph "Data Stores"
        VideoStore[(Video Storage<br/>Colossus/Blob)]
        MetaDB[(Metadata DB<br/>Bigtable)]
        SearchIdx[(Search Index<br/>Elasticsearch)]
        UserDB[(User DB<br/>Bigtable)]
    end

    Upload --> UploadSvc
    UploadSvc --> Transcode
    Transcode --> ThumbnailGen
    Transcode --> ContentID
    Transcode --> VideoStore
    ThumbnailGen --> VideoStore
    ContentID --> MetaDB

    Watch --> CDN
    CDN --> Origin
    Origin --> VideoStore

    Watch --> SearchSvc
    Watch --> RecsSvc
    SearchSvc --> SearchIdx
    RecsSvc --> MetaDB
    MetaDB --> UserDB
```

## Deep Dive: Video Upload & Processing

### Upload Flow

```mermaid
sequenceDiagram
    participant Creator
    participant UploadSvc
    participant Storage
    participant Transcode
    participant CDN

    Creator->>UploadSvc: Upload video (resumable)
    UploadSvc->>Storage: Store original (raw)
    UploadSvc->>Creator: Upload complete
    Transcode->>Storage: Fetch original
    Transcode->>Transcode: Encode to multiple formats
    Transcode->>Storage: Store encoded versions
    Transcode->>CDN: Push to edge
    Note over Transcode: Processing takes 1-60 min<br/>depending on length and queue
```

### Transcoding Pipeline

YouTube transcodes each video into **~30+ different versions**:

```mermaid
graph TB
    Original["Original Video<br/>(4K, 60fps, H.264)"] --> Split["Split into chunks<br/>(5-second segments)"]
    Split --> Encode1["144p H.264"]
    Split --> Encode2["360p H.264"]
    Split --> Encode3["720p H.264"]
    Split --> Encode4["1080p H.264"]
    Split --> Encode5["4K H.264"]
    Split --> Encode6["1080p VP9"]
    Split --> Encode7["4K VP9"]
    Split --> Encode8["1080p AV1"]
    Split --> Encode9["4K AV1"]
    Encode1 --> Mux["Mux + Package<br/>(DASH/HLS)"]
    Encode2 --> Mux
    Encode3 --> Mux
    Encode4 --> Mux
    Encode5 --> Mux
    Encode6 --> Mux
    Encode7 --> Mux
    Encode8 --> Mux
    Encode9 --> Mux
    Mux --> Storage["Blob Storage"]
```

**Why so many versions:**
- Different resolutions (144p to 8K) for different bandwidths
- Different codecs (H.264, VP9, AV1) for different device support
- Different bitrates within each resolution for adaptive streaming
- Segmented for DASH/HLS streaming

**YouTube's DAG-based transcoding:**
- Uses a **Directed Acyclic Graph (DAG)** to model the transcoding pipeline
- Each step (decode → filter → encode → package) is a node in the DAG
- Enables parallel processing and automatic retries
- Built on Google's internal infrastructure (Borg)

## Deep Dive: Video Delivery

### Adaptive Bitrate Streaming (DASH)

```mermaid
sequenceDiagram
    participant Client
    participant CDN
    participant Origin

    Client->>CDN: Request manifest (.mpd)
    CDN-->>Client: Manifest (available qualities)
    Client->>Client: Select quality based on bandwidth
    Client->>CDN: Request segment 1 (720p)
    CDN-->>Client: Segment data
    Client->>Client: Measure bandwidth
    Client->>CDN: Request segment 2 (1080p)
    CDN-->>Client: Segment data
    Note over Client: Continuously adapts quality
```

### CDN Architecture

YouTube uses **Google Global Cache (GGC)** — Google's CDN:

```mermaid
graph TB
    subgraph "ISP Network"
        GGC["Google Global Cache<br/>(inside ISP)"]
    end
    subgraph "Google Network"
        Origin["Origin Servers"]
        Storage["Colossus Storage"]
    end
    
    User --> GGC
    GGC -->|"Cache hit (~95%)"| User
    GGC -.->|"Cache miss"| Origin
    Origin --> Storage
```

- GGC servers are placed **inside ISPs** (like Netflix Open Connect)
- Serves ~95% of video traffic from ISP-local cache
- Reduces backbone bandwidth and improves start time

## Deep Dive: Recommendations

YouTube's recommendation system drives **70%+ of watch time**.

```mermaid
graph TB
    subgraph "Candidate Generation"
        Collab["Collaborative Filtering"]
        Content["Content-Based"]
        Search["Search-Based"]
    end

    subgraph "Ranking"
        DNN["Deep Neural Network"]
        Features["User features,<br/>video features,<br/>context features"]
    end

    subgraph "Serving"
        Homepage["Homepage Feed"]
        Sidebar["Up Next / Sidebar"]
        Search["Search Results"]
    end

    Collab --> DNN
    Content --> DNN
    Search --> DNN
    Features --> DNN
    DNN --> Homepage
    DNN --> Sidebar
    DNN --> Search
```

**Two-stage approach:**
1. **Candidate Generation**: Narrow millions of videos to hundreds using collaborative filtering
2. **Ranking**: Score candidates using a deep neural network with features like:
   - Watch history, search history, demographics
   - Video freshness, engagement metrics (likes, comments, watch time)
   - User context (device, time of day, location)

## Deep Dive: Search

```mermaid
graph LR
    Query["User Query"] --> QP["Query Processing"]
    QP --> Match["Title/Description<br/>Matching"]
    QP --> Semantic["Semantic Search<br/>(BERT)"]
    Match --> Rank["Ranking"]
    Semantic --> Rank
    Rank --> Results["Search Results"]
```

**Ranking factors:**
- Title and description match
- Watch time and engagement
- Channel authority
- Freshness
- User's watch history

## Scalability

| Component | Strategy |
|-----------|---------|
| Video storage | Colossus (Google's distributed file system), ~800+ PB |
| Transcoding | DAG-based parallel processing on Borg (thousands of machines) |
| CDN | Google Global Cache inside ISPs |
| Metadata | Bigtable (wide-column store) |
| Search | Inverted index on Bigtable |
| Recommendations | Pre-computed offline, served from cache |
| Live streaming | Low-latency DASH, origin push to CDN |

## Trade-Offs

| Decision | Benefit | Cost |
|----------|---------|------|
| Multiple codec versions | Optimal quality per device | 30x storage and encoding cost |
| DAG-based transcoding | Parallel, fault-tolerant | Complex pipeline management |
| GGC (ISP-local CDN) | Low latency, reduced backbone | Infrastructure investment |
| AV1 codec | 30% better compression than VP9 | Higher encoding cost, slower |
| Recommendation ML | 70%+ watch time from recs | Filter bubble, diversity concerns |

## Interview Tips

1. **Start with the numbers** — 2B MAU, 500 hours uploaded/minute, 1B hours watched/day
2. **Explain the transcoding pipeline** — DAG-based, parallel, 30+ versions per video
3. **Discuss adaptive bitrate streaming** — DASH/HLS, client-side quality switching
4. **Mention the CDN** — Google Global Cache inside ISPs for low-latency delivery
5. **Talk about recommendations** — 70% of watch time, two-stage (candidate gen + ranking)
6. **Don't forget Content ID** — copyright detection at upload time
7. **Mention codec evolution** — H.264 → VP9 → AV1 for better compression

## Key Takeaways

- YouTube processes 500+ hours of video uploaded every minute through a DAG-based transcoding pipeline.
- Each video is transcoded into 30+ versions (different resolutions, codecs, bitrates) for adaptive streaming.
- Google Global Cache (GGC) serves ~95% of video traffic from ISP-local servers.
- Recommendations drive 70%+ of watch time using collaborative filtering + deep learning.
- Video storage exceeds 800 PB, growing rapidly, stored on Google's Colossus distributed file system.
- Content ID automatically detects copyrighted material at upload time.
- The codec evolution (H.264 → VP9 → AV1) reduces bandwidth costs by 30% with each generation.

## Cross-References

- [Video Streaming](../video-streaming.md)
- [Search Engine](../search.md)
- [Recommendation](../../../ml/system-design/recommendation.md)
- [Object Storage](../../../storage/object-storage.md)
- [CDN & Caching](../hld/caching-strategy.md)

