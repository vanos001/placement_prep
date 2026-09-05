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

### Feed Ranking as a Two-Stage Retrieval Problem

The sketch above hides the most consequential constraint in feed design: **the ranker's input size is a design constant, not a consequence of graph size**. Production systems split retrieval from scoring — Covington et al. call it "the classic two-stage information retrieval dichotomy: first, we detail a deep candidate generation model and then describe a separate deep ranking model" [1]. (The [production case study](./real-world/news-feed.md) shows the same split as three stages, with a lightweight filter inserted between them.)

**Candidate generation is cheap by construction.** Candidates come from followed-entity channels (last-N posts per friend, page, and group membership — indexed reads) plus recommender recall channels (recommended accounts, trending, reshares). Every candidate pays only O(1) pre-filters: seen-set exclusion (a bloom filter per user), blocked/muted lookups, dedup across edges, visibility windows — no model touches this stage. Retrieval is deliberately recall-biased: the ranker can only choose among what retrieval surfaces, so over-recall-and-discard beats missing a post the user would have engaged with.

**The ranker only ever sees hundreds.** Against this page's < 500ms p95 target: ~750 candidates × ~1μs lightweight score is sub-millisecond, but the heavy model at ~5ms per (user, post) pair must be capped at ~100 pairs — that alone consumes the budget. Hand the heavy ranker 100,000 candidates and the same stage needs ~8 minutes. At this page's peak of 100K feed loads/sec, the 100-pair cap still means ~10M heavy inferences/sec fleet-wide (computed) — hence the cap, and why heavy scoring runs as batched GPU inference rather than per-pair calls.

**Feature freshness is tiered, not uniform.** Engagement counts mutate per minute; fetching exact counts for every (user, candidate) pair at rank time is a cache storm — and wasted precision, since the UI renders "1.2K". Production feeds serve approximate counts from probabilistic structures with bounded error; the math lives in [Probabilistic Data Structures](./probabilistic-data-structures.md). Offline features (affinity, creator historical engagement, embedding similarities) are precomputed on a schedule into a feature store keyed by user and post; online features (session context, time of day, unseen flags, the candidate's own engagement velocity) are computed per request. The deciding rule is staleness tolerance plus join cardinality: affinity over ~300 followed authors refreshes fine offline; "likes in the last 10 minutes on *this* post" must be online.

**One line on exploration and position bias:** a ranker trained only on what it already showed learns its own biases — top slots get engagement, so the model keeps promoting what it already promotes — which is why production rankers reserve a small exploration slice and correct for logged position; the multitask ranking system described by Zhao et al. is the canonical published account of this discipline [2].

### Feed Consistency: What Users Actually Notice

The fanout-on-write / fanout-on-read / hybrid trade is quantified in [Notifications](./notifications.md) — the feed and the notification system share that math, including the celebrity write-amplification numbers. This section covers what the trade *feels like to a user*, because consistency complaints are the top source of feed tickets.

**Ranked order makes pagination unstable.** In a chronological feed, "page 2" is well-defined: posts older than your cursor. In a ranked feed the order is a function of a model that changes between fetches — the user loads page 1, a burst of engagement promotes an unseen post, and page 2 either re-serves something from page 1 ("I already saw this") or skips a post entirely ("my friend's post vanished"). Timestamp cursors cannot fix this: ranking is not monotonic in time. Two production answers, usually combined: (1) **cursor-of-seen-ids** — the client echoes back a capped, bloom-filtered set of recently seen post ids and the server excludes them; stateless on the server and self-healing, but unable to prevent skips when a seen post legitimately belonged on the next page. (2) **stable snapshot id** — the first page request materializes the ranked list as a snapshot (an id plus a short TTL) and later pages read the frozen snapshot; new posts wait for the next session instead of splicing mid-scroll.

**Read-your-writes for your own posts.** Fanout-on-write means *followers* see your post only after the fanout workers land it — but the author must see it immediately (the inconsistency users screenshot). The fix is **merge-at-read**: the author's own last-N post ids are unioned from the post store with their fanout cache before ranking, and deduplicated by post id once the async copy arrives. The author's view never waits on the fanout pipeline.

**The delete cascade is lazy.** A post already fanned out into millions of per-user caches cannot be synchronously un-pushed — chasing them is the fanout storm in reverse. Instead, the post store and entity tier flip the post to a **tombstone**; feed caches hold only post ids, so hydration filters tombstones at read time; the stale id lingers in cached id-lists until trimmed or TTL-expired — lazy expiry, not proactive rewrite. The exception that cannot be lazy: legal and safety removals get a targeted async deletion queue with completion tracking, because "eventually" is not an acceptable answer for mandated takedowns. Mute and block reuse the trick — filter at hydration rather than rewriting caches.

### Feed Cache Tiering

"Add a cache" is the wrong granularity. A feed system runs **three cache tiers with different keys, payloads, and failure modes**:

| Tier | Key → payload | Sizing shape | Miss cost |
|---|---|---|---|
| Fanout cache | `feed:{user_id}` → ordered post *ids* (sorted set, top-K ≈ 50–500) | O(users × K × id size); 1.5B users × 50 ids × 8B ≈ **600 GB** of ids (computed) | Fall back to read-time merge — latency spike, not a rebuild |
| Entity cache | `post:{id}` → hydrated content, author, media URLs, counts | Working set = recently fanned-out posts, LRU | Post-store read per miss (hydration latency) |
| Graph cache | `followers:{user_id}`, affinity, celebrity-friend lists | Stationary, small keys, enormous read volume | Graph-DB hit; stalls fanout workers, not the read path |

Hit-rate expectations follow the payload: the fanout cache runs near-100% for normal users because it *is* the read path (a miss means the pull-model fallback); the entity cache runs 95%+ because its working set is exactly the recently fanned-out id universe; the graph cache runs 99%+ because follows change slowly while reads are constant. Facebook's graph store TAO exists to serve precisely this tier — it "can process a billion reads and millions of writes each second" and is "replacing memcache for many data types that fit its model" [3]; its data model and topology are covered in [Social Graph](./social-graph.md).

**Invalidation cascades one way, and only one way.** Post ids are immutable; content is mutable. That division is the payoff of the id-only fanout design: an edited post flips its entity-cache entry and *no fanout id-list needs touching*; a deleted post tombstones in the entity tier and id-lists self-heal at hydration (the lazy cascade above). The inverse design — caching hydrated post content inside fanout lists — turns every edit into a multi-million-key invalidation. The general TTL and invalidation primitives underneath (cache-aside, event-based, tag-based) are covered in [Caching Strategy](./hld/caching-strategy.md); what is feed-specific is *which tier holds truth*.

**A TTL ladder by content age.** Fresh posts (< 24h) live in fanout caches as ids, re-sorted as ranking signals refresh. Mid-age posts (days) are trimmed from most users' id-lists and re-enter the read path via entity-cache hydration when a deep scroll needs them. Old posts exist only in the post store plus the entity tier, fetched on demand. The ladder is what keeps the 600 GB id-cache bounded: without age-based expiry, feed caches grow with *lifetime* posts instead of the visible window.

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

## 📚 References

1. Covington, P.; Adams, J.; Sargin, E. "Deep Neural Networks for YouTube Recommendations." *Proc. 10th ACM Conf. on Recommender Systems (RecSys)*, 2016. DOI: [10.1145/2959100.2959190](https://doi.org/10.1145/2959100.2959190) — Crossref-verified (title/authors/venue) this session; the two-stage "information retrieval dichotomy" sentence quoted verbatim from the paper's abstract as fetched at <https://research.google/pubs/deep-neural-networks-for-youtube-recommendations/> (HTTP 200) this session.
2. Zhao, Z.; Hong, L.; Wei, L.; Chen, J.; Nath, A.; Andrews, S.; Kumthekar, A.; Sathiamoorthy, M.; Yi, X.; Chi, E. "Recommending what video to watch next: a multitask ranking system." *Proc. 13th ACM Conf. on Recommender Systems (RecSys)*, 2019. DOI: [10.1145/3298689.3346997](https://doi.org/10.1145/3298689.3346997) — Crossref-verified (full 10-author list/venue/date) via api.crossref.org this session; full text not fetchable this session (dl.acm.org returns 403 to automated fetch), so cited bibliographically only. (Note: a circulating attribution of this DOI to "Candille" could not be verified on Crossref and was dropped.)
3. Bronson, N.; et al. "TAO: Facebook's Distributed Data Store for the Social Graph." *USENIX ATC*, 2013 — publication page fetched this session at <https://research.facebook.com/publications/tao-facebooks-distributed-data-store-for-the-social-graph/> (HTTP 200); all quoted sentences verbatim from that page. (The usenix.org session page returned 403 to automated fetch this session, so the Meta Research page carries the citation.)

## 🔗 Cross-References

- [Notifications](./notifications.md) — the fanout-on-write / fanout-on-read / hybrid math this page's consistency section links to instead of re-deriving
- [Probabilistic Data Structures](./probabilistic-data-structures.md) — approximate engagement counters behind feature freshness
- [Social Graph](./social-graph.md) — TAO and the graph-cache tier
- [News Feed Case Study](./real-world/news-feed.md) — production-scale three-stage pipeline walk-through
- [Caching Strategy](./hld/caching-strategy.md) — general TTL/invalidation primitives the feed tiers build on
- [Chat System](./chat.md) — Real-time delivery patterns
- [Video Streaming](./video-streaming.md) — Media handling
- [Caching](../../cheatsheets/architecture.md) — Caching strategies
- [DBMS Questions](../dbms-questions.md) — Database selection
