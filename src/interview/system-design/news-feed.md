# Design a News Feed (Social Media Feed)

> **Difficulty:** ⭐⭐⭐ | **Asked at:** Meta, Twitter/X, Google | **Time:** 45 minutes

## 🎯 Problem Statement

Design a news feed system like Facebook, Twitter, or Instagram that:
- Shows posts from friends/followed accounts
- Ranks posts by relevance
- Supports real-time updates
- Handles billions of users

---

## Step 1: Requirements

### Functional Requirements
1. Users can create posts (text, images, videos)
2. Users see a feed of posts from friends/followed accounts
3. Feed is ranked by relevance (not just chronological)
4. Users can like, comment, share posts
5. Real-time feed updates when new posts are created
6. Support for hashtags, mentions, and media

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Feed load time | < 500ms |
| Post creation to feed appearance | < 5 seconds |
| Availability | 99.99% |
| Read:Write ratio | 1000:1 (feed reads dominate) |

### Capacity Estimation

```
Users: 2B total, 500M daily active
Posts: 500M users × 2 posts/day = 1B posts/day
Feed reads: 500M users × 10 feed loads/day = 5B feed reads/day
Peak feed reads: ~100,000 requests/sec

Storage per post: ~1 KB (text + metadata)
Daily storage: 1B × 1KB = ~1 TB/day
Media: 1B × 30% × 2MB = ~600 TB/day

Average friends per user: 500
Average posts visible per feed load: 20
```

---

## Step 2: High-Level Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌──────────┐     ┌──────────────┐     ┌───────────────────┐   │
│  │  Client  │────→│ Load Balancer│────→│    API Gateway    │   │
│  └──────────┘     └──────────────┘     └────────┬──────────┘   │
│                                                  │              │
│       ┌────────────────────┬─────────────────────┼──────┐      │
│       │                    │                     │      │      │
│  ┌────▼─────┐     ┌───────▼───────┐     ┌───────▼──────┐     │
│  │  Post    │     │    Feed       │     │  Engagement  │     │
│  │ Service  │     │   Service     │     │   Service    │     │
│  └────┬─────┘     └───────┬───────┘     └───────┬──────┘     │
│       │                   │                     │             │
│  ┌────▼─────┐     ┌───────▼───────┐     ┌───────▼──────┐     │
│  │ Post DB  │     │   Feed Cache  │     │ Engagement DB│     │
│  │(PostgreSQL)│   │   (Redis)     │     │ (Cassandra)  │     │
│  └──────────┘     └───────────────┘     └──────────────┘     │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │              Fan-out Service (Kafka Workers)          │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐               │
│  │ Graph DB │  │ Media CDN │  │ Ranker (ML)  │               │
│  │(Friends) │  │           │  │              │               │
│  └──────────┘  └───────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 3: Deep Dive

### Fan-out Strategies

This is the **core challenge** of news feed design.

#### Fan-out on Write (Push Model)

```
When User A creates a post:
1. Post Service saves post to Post DB
2. Fan-out Service gets User A's friend list (500 friends)
3. For each friend: Add post_id to their feed cache (Redis)
4. When friend opens app → Read from their pre-computed feed cache

┌──────┐    ┌──────────────┐    ┌─────────────────────────┐
│User A│───→│ Post Service │───→│ Fan-out Service         │
│posts │    └──────────────┘    │                         │
└──────┘                        │ For each of A's friends:│
                                │   Feed[friend].push(post)│
                                └─────────┬───────────────┘
                                          │
                              ┌───────────┼───────────┐
                              │           │           │
                         ┌────▼──┐   ┌────▼──┐   ┌────▼──┐
                         │Feed:B │   │Feed:C │   │Feed:D │
                         │(Redis)│   │(Redis)│   │(Redis)│
                         └───────┘   └───────┘   └───────┘

Pros: Fast feed reads (pre-computed), simple retrieval
Cons: Write amplification (celebrity with 10M followers = 10M writes)
      Storage cost (each user's feed stored separately)
      Slow for users with many followers
```

#### Fan-out on Read (Pull Model)

```
When User B opens their feed:
1. Get User B's friend list (500 friends)
2. Fetch recent posts from each friend
3. Merge and rank posts
4. Return top 20 posts

┌──────┐    ┌──────────────┐    ┌──────────────────────────┐
│User B│───→│ Feed Service │───→│ Get B's friend list      │
│opens │    └──────────────┘    │ For each friend:         │
│feed  │                        │   Fetch recent posts     │
└──────┘                        │ Merge + Rank + Return    │
                                └──────────────────────────┘

Pros: No write amplification, always fresh, less storage
Cons: Slow feed reads (real-time computation), high DB load
```

#### Hybrid Approach (Recommended) ✅

```
Normal users (< 5000 followers): Fan-out on Write
├── Pre-compute feed when they post
├── Fast feed reads for their followers
└── ~99% of users

Celebrity users (> 5000 followers): Fan-out on Read
├── Don't pre-compute (too expensive)
├── Fetch their posts at read time
├── Merge with pre-computed feed
└── ~1% of users (but high impact)

Feed Retrieval:
1. Read pre-computed feed from Redis (normal friends' posts)
2. Fetch recent posts from celebrity friends (read-time)
3. Merge both sets
4. Apply ranking model
5. Return top 20
```

### Feed Ranking

```
Ranking Pipeline:
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Candidate│───→│  Feature │───→│   ML     │───→│  Final   │
│  Gen     │    │  Extract │    │  Ranker  │    │  Sort    │
└──────────┘    └──────────┘    └──────────┘    └──────────┘

Features for Ranking:
├── Post features: age, type (text/image/video), engagement rate
├── User features: relationship closeness, past interactions
├── Context features: time of day, device, location
└── Engagement signals: likes, comments, shares from similar users

Scoring (simplified):
  score = w1 * affinity_score        # How close is the friendship
        + w2 * engagement_score       # How many likes/comments
        + w3 * recency_score          # How recent is the post
        + w4 * content_type_score     # User's preference for media type
        + w5 * creator_quality_score  # Creator's historical engagement
```

### Database Design

```sql
-- Posts
CREATE TABLE posts (
    post_id     BIGINT PRIMARY KEY,
    user_id     BIGINT NOT NULL,
    content     TEXT,
    media_urls  TEXT[],
    created_at  TIMESTAMP DEFAULT NOW(),
    like_count  INT DEFAULT 0,
    comment_count INT DEFAULT 0
);
CREATE INDEX idx_posts_user ON posts(user_id, created_at DESC);

-- Feed Cache (Redis)
-- Key: feed:{user_id}
-- Value: Sorted Set of post_ids (scored by timestamp or ranking)
-- ZADD feed:user_123 1704067200 post_456
-- ZREVRANGE feed:user_123 0 19  (get top 20 posts)

-- Friend Graph
CREATE TABLE friendships (
    user_id     BIGINT,
    friend_id   BIGINT,
    closeness   FLOAT DEFAULT 1.0,  -- Affinity score
    created_at  TIMESTAMP,
    PRIMARY KEY (user_id, friend_id)
);
```

### Handling Celebrity Problem

```
Celebrity with 10M followers posts:

Option 1: Full Fan-out (BAD)
├── 10M writes to Redis
├── Takes ~30 minutes with 5K writes/sec
└── Feed appears 30 min late for all followers

Option 2: Hybrid (GOOD)
├── Mark as celebrity (follower count > threshold)
├── Don't fan-out their posts
├── At read time: fetch celebrity posts separately
├── Merge with pre-computed feed
└── Feed appears in < 1 second

Implementation:
def get_feed(user_id):
    # 1. Pre-computed feed (normal friends)
    pre_computed = redis.zrevrange(f"feed:{user_id}", 0, 49)

    # 2. Celebrity friends' recent posts
    celebrity_friends = get_celebrity_friends(user_id)
    celebrity_posts = []
    for celeb in celebrity_friends:
        recent = db.query("SELECT * FROM posts WHERE user_id = %s
                          ORDER BY created_at DESC LIMIT 5", celeb)
        celebrity_posts.extend(recent)

    # 3. Merge and rank
    all_posts = merge(pre_computed, celebrity_posts)
    ranked = ranking_model.rank(all_posts, user_id)
    return ranked[:20]
```

---

## Step 4: Trade-offs

### Consistency vs Latency
| Approach | Consistency | Latency |
|----------|------------|---------|
| Fan-out on Write | Eventual | Low (pre-computed) |
| Fan-out on Read | Strong | High (real-time) |
| Hybrid | Eventual | Medium |

### Feed Freshness vs System Load
| Approach | Freshness | Load |
|----------|-----------|------|
| Pre-compute everything | Stale (seconds old) | High write load |
| Compute on read | Fresh | High read load |
| Hybrid | Good | Balanced |

## 🔗 Cross-References

- [Chat System](./chat.md) — Real-time delivery patterns
- [Video Streaming](./video-streaming.md) — Media handling
- [Caching](../../cheatsheets/architecture.md) — Caching strategies
- [DBMS Questions](../dbms-questions.md) — Database selection
