# News Feed Case Study: Facebook-Style

## Overview

Facebook's news feed is one of the most complex systems in production — it must rank and deliver a personalized feed to 2B+ users by selecting from trillions of candidate posts generated daily. This case study focuses on the feed generation pipeline: candidate retrieval from social graph edges, multi-stage ranking (candidate generation → lightweight scoring → heavy ML ranking), real-time story injection, and the hybrid fan-out architecture that balances write amplification against read latency.

## Key Requirements

### Functional
- Personalized feed ranking based on affinity, engagement prediction, and content type
- Support multiple story types: posts, photos, videos, stories, live streams, ads
- Real-time injection: new posts appear in feed within seconds
- Pagination: infinite scroll with cursor-based navigation
- Feed types: top stories (ranked) vs most recent (chronological)
- Story unseen markers and content freshness indicators
- Support for ad insertion with guaranteed impression counting

### Non-Functional
| Requirement | Target |
|-------------|--------|
| Feed generation latency | < 500ms p95 |
| Time to inject new post | < 3 seconds |
| Candidate pool per request | ~500-1000 posts |
| Throughput | 500K feed loads/sec at peak |
| Availability | 99.99% |
| Ranking model freshness | Updated every 15 minutes |

### Capacity Estimation

```
Users: 3B total, 1.5B DAU
Posts per day: 1B
Average friends per user: 300
Average feed loads per user per day: 10
Total feed loads/day: 15B
Peak feed loads: 500K/sec

Candidate generation per feed load:
  From friends: 300 users × 2 posts/day = ~600 candidate posts
  From followed pages: ~50 candidate posts
  From groups: ~100 candidate posts
  Total candidates: ~750 per feed load

Ranking computation per feed load:
  750 candidates × lightweight score (~1μs) = ~0.75ms
  Top 100 × heavy ML score (~5ms) = ~500ms → needs batching/prediction service

Feed cache storage:
  1.5B users × 50 post_ids per cached feed × 8 bytes = ~600 GB
```

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client"
        App[Mobile App / Web]
    end

    subgraph "Edge"
        CDN[CDN]
        LB[Load Balancer]
        APIGW[API Gateway]
    end

    subgraph "Feed Services"
        FeedSvc[Feed Service<br/>Orchestration]
        CandidateSvc[Candidate Generation<br/>Service]
        RankSvc[Ranking Service<br/>Lightweight]
        MLRankSvc[ML Ranking<br/>Service]
        StorySvc[Real-Time Story<br/>Injection Service]
        AdSvc[Ad Service]
    end

    subgraph "Data Stores"
        SocialGraph[(Social Graph DB<br/>TAO / MySQL)]
        PostDB[(Post Store<br/>Cassandra)]
        FeedCache[(Feed Cache<br/>Redis Sorted Sets)]
        UserCache[(User Cache<br/>Redis)]
        RankCache[(Pre-computed<br/>Rank Features)]
    end

    subgraph "Fan-out"
        Kafka[Kafka Event Bus]
        FanoutWorker[Fan-out Workers<br/>Push Model]
    end

    subgraph "ML Infrastructure"
        FeatureStore[Feature Store]
        ModelServer[TF Serving<br/>Ranking Model]
    end

    App --> CDN
    App --> LB
    LB --> APIGW
    APIGW --> FeedSvc
    FeedSvc --> CandidateSvc
    FeedSvc --> StorySvc
    CandidateSvc --> SocialGraph
    CandidateSvc --> PostDB
    CandidateSvc --> RankSvc
    RankSvc -->|"Top 100"| MLRankSvc
    MLRankSvc --> FeatureStore
    MLRankSvc --> ModelServer
    StorySvc --> FeedCache
    StorySvc --> Kafka
    FanoutWorker --> FeedCache
    FanoutWorker --> Kafka
    FeedSvc --> FeedCache
    AdSvc --> FeedSvc
```

## Deep Dive: Feed Generation Pipeline

Feed generation follows a three-stage pipeline: candidate retrieval, lightweight scoring, and heavy ML ranking.

### Stage 1: Candidate Generation

```
For each feed load request:
1. Fetch user's social graph edges:
   - Friend connections (bidirectional)
   - Followed pages/public figures
   - Group memberships
   - Followed hashtags

2. Retrieve recent posts from each edge:
   - Friends: last 24h posts (cached in Redis, key: posts:{user_id})
   - Pages: last 48h posts
   - Groups: last 24h posts (for active groups only)

3. Deduplicate across edges (avoid showing same post twice)

4. Apply hard filters:
   - Remove posts already seen by user
   - Remove posts from blocked/muted users
   - Remove expired content (stories > 24h)

Result: ~500-1000 candidate posts
```

### Stage 2: Lightweight Scoring (Predictive Model)

Candidates are scored using a lightweight model (~10 features) to reduce the set for expensive ML inference:

```
Score = w1 × affinity(user, author)          # Friendship closeness
      + w2 × recency_hours(post_age)         # How recent is the post
      + w3 × author_post_frequency          # How often author posts
      + w4 × user_content_type_pref        # User's historical engagement with this type
      + w5 × early_engagement_signal       # Likes/comments in first 10 minutes
      + w6 × negative_feedback_prob         # Probability user will hide/report

Affinity calculation:
  affinity(A, B) = α × direct_interactions(A,B)
                 + β × mutual_friends(A,B)
                 + γ × co-tagged_photos(A,B)
                 + δ × message_frequency(A,B)

Top 100 candidates pass to Stage 3.
```

### Stage 3: Heavy ML Ranking

The top 100 candidates are ranked using a deep neural network (typically a DSSM or transformer-based model) with hundreds of features:

```
Features per (user, post) pair:
  Post features: text embeddings, image embeddings, video duration,
                 content freshness, engagement velocity
  User features: demographic embeddings, device type, session context,
                 content preference history
  Cross features: user-post affinity score, social context,
                  historical click-through rate for similar content
  Context features: time of day, day of week, session duration,
                    feed position bias

Batch inference: TF Serving with GPU, ~100 predictions in ~200ms
Top 20 posts returned to user with interleaved ads.
```

## Deep Dive: Hybrid Fan-out Architecture

The system uses a hybrid push/pull model to balance write amplification against read latency.

### Classification of Users

```mermaid
graph TB
    UserPosts["User creates post"] --> Classify{"Followers count?"}
    Classify -->|"< 100K"| PushFanout["Fan-out on Write<br/>(Push to followers' feed caches)"]
    Classify -->|"> 100K"| PullFanout["Fan-out on Read<br/>(Store post, merge at read time)"]

    PushFanout --> RedisCache["Redis Sorted Set<br/>feed:{follower_id}<br/>score=ranking_timestamp"]
    PullFanout --> PostStore["Post Store<br/>(Cassandra)"]

    RedisCache -->|"Pre-computed feed"| FeedRead["Feed Read:<br/>Read cache → Done"]
    PostStore -->|"Celebrity post"| FeedRead2["Feed Read:<br/>Read cache + Fetch celebrity posts<br/>→ Merge → Rank"]
```

**Write-path fan-out (push model):**
1. User posts → Post Service persists to Cassandra
2. Post Service publishes to Kafka topic `new-posts`
3. Fan-out workers consume and fetch poster's follower list
4. For each follower, add post_id to their Redis sorted set: `ZADD feed:{follower_id} {score} {post_id}`
5. Score combines posting timestamp + lightweight ranking signals

**Read-path merge (pull model):**
1. User opens feed → Feed Service reads pre-computed Redis sorted set (top 50)
2. Fetches recent posts from followed celebrities/pages (not in cache)
3. Merges both sets, runs ranking pipeline, returns top 20

**Why this works:**
- 99% of users have < 100K followers → push fan-out covers most of the graph
- The 1% celebrity tier generates < 5% of total posts but has > 50% of followers
- Write amplification: without hybrid, a celebrity with 100M followers generates 100M Redis writes per post

## Deep Dive: Pagination and Unseen Tracking

Pagination uses cursor-based navigation with seen/unseen watermarks:

```
GET /api/feed?cursor=eyJ0cyI6MTcwNDA2NzIwMH0&limit=20

Response:
{
  "stories": [...],
  "next_cursor": "eyJ0cyI6MTcwNDA2NzEwMH0",
  "unseen_count": 7,
  "new_stories_available": true
}

Unseen watermark:
  Redis key: feed_unseen_watermark:{user_id}
  Value: timestamp of last feed load

On feed load:
  1. Read watermark
  2. Fetch feed items (cached + real-time merge)
  3. Mark items with created_at > watermark as "unseen" (blue dot indicator)
  4. Update watermark to current time
  5. Client uses unseen_count for notification badge
```

## Scalability

| Component | Strategy |
|-----------|---------|
| Feed Service | Stateless, 200+ instances, partitioned by user_id |
| Candidate Generation | Parallel fetch from Redis + Cassandra |
| ML Ranking | GPU-backed TF Serving cluster, batch inference |
| Feed Cache | Redis cluster, 512 shards, ~600 GB total |
| Fan-out Workers | Kafka consumer group, 64 partitions, partitioned by poster_id |
| Social Graph | TAO (Facebook's graph API) or sharded MySQL with edge caching |
| Post Store | Cassandra, partitioned by post_id, time-series compaction |

## Trade-Offs

| Decision | Benefit | Cost |
|----------|---------|------|
| Three-stage ranking | Sub-500ms latency despite 1000 candidates | Pipeline complexity |
| Hybrid fan-out | No write amplification for celebrities | Two code paths for feed reads |
| Pre-computed lightweight scores | Fast candidate filtering | Scores become stale between refreshes |
| Cursor-based pagination | No offset drift, O(1) fetch | Clients must store cursor state |
| Redis sorted sets for feed cache | O(log N) insertion, O(log N + M) range query | Memory-intensive for large feeds |

## Interview Tips

1. **Lead with the ranking problem** — "The core challenge is selecting 20 posts from 1000 candidates in under 500ms"
2. **Explain three-stage ranking** — candidate generation → lightweight scoring → heavy ML ranking
3. **Discuss the hybrid fanout** — push for regular users, pull for celebrities
4. **Mention the unseen watermark** — how Facebook implements the "new posts" indicator
5. **Talk about ad interleaving** — ads are ranked separately and merged into the feed

## Key Takeaways

- Facebook's feed uses a three-stage ranking pipeline: candidate generation → lightweight scoring → ML ranking.
- Hybrid fan-out prevents write amplification from celebrities while keeping reads fast for regular users.
- Redis sorted sets store pre-computed feed caches; celebrity posts are merged at read time.
- Unseen watermarks track which posts are new since the user's last visit.
- GPU-backed ML inference ranks top 100 candidates in ~200ms for sub-500ms total feed latency.

## Cross-References

- [How Twitter Works](./twitter.md) — Twitter's hybrid fanout approach
- [News Feed Design](../news-feed.md) — Interview-format overview
- [Social Graph](../social-graph.md) — Graph traversal and storage
- [Caching Strategy](../hld/caching-strategy.md) — Cache warming and invalidation
