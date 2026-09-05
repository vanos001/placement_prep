# Design a Chat System

> **Difficulty:** ⭐⭐⭐ | **Asked at:** Meta, Google, Amazon | **Time:** 45 minutes

## 🎯 Problem Statement

Design a real-time chat system like WhatsApp, Slack, or Facebook Messenger supporting:
- 1-on-1 and group messaging
- Online/offline presence
- Message delivery guarantees
- Media sharing (images, files)

---

## Step 1: Requirements

### Functional Requirements
1. 1-on-1 messaging with real-time delivery
2. Group messaging (up to 500 members)
3. Online/offline presence indicators
4. Message delivery receipts (sent, delivered, read)
5. Media sharing (images, videos, files up to 100MB)
6. Message history and search
7. Push notifications for offline users

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Message latency | < 200ms end-to-end |
| Availability | 99.99% |
| Message ordering | Guaranteed within a conversation |
| Durability | Messages never lost |
| Concurrent connections | 50M simultaneous |

### Capacity Estimation

```
Users: 500M total, 50M daily active
Messages: 50M users × 40 messages/day = 2B messages/day
Peak: ~25,000 messages/sec

Storage per message: ~100 bytes (metadata) + media
Daily storage: 2B × 100 bytes = ~200 GB text/day
Media storage: 2B × 10% × 500KB = ~100 TB/day (with CDN)

Connections: 50M concurrent WebSocket connections
Bandwidth: 25,000 msg/sec × 100 bytes = ~2.5 MB/s text
```

---

## Step 2: High-Level Design

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │ Client A │  │ Client B │  │ Client C │  │ Client D │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │            │            │            │                   │
│       └────────────┼────────────┼────────────┘                   │
│                    ▼            ▼                                 │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              WebSocket Gateway Layer                   │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐           │       │
│  │  │ Gateway 1│  │ Gateway 2│  │ Gateway 3│  ...       │       │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘           │       │
│  └───────┼──────────────┼──────────────┼────────────────┘       │
│          │              │              │                         │
│  ┌───────▼──────────────▼──────────────▼────────────────┐       │
│  │                   MESSAGE BUS (Kafka)                 │       │
│  └───────┬──────────────┬──────────────┬────────────────┘       │
│          │              │              │                         │
│  ┌───────▼─────┐ ┌──────▼──────┐ ┌────▼──────────┐             │
│  │ Message     │ │ Presence    │ │ Notification  │             │
│  │ Service     │ │ Service     │ │ Service       │             │
│  └──────┬──────┘ └─────────────┘ └───────────────┘             │
│         │                                                       │
│  ┌──────▼──────┐ ┌─────────────┐ ┌───────────────┐             │
│  │ Message DB  │ │ User DB     │ │ Media Storage │             │
│  │ (Cassandra) │ │ (PostgreSQL)│ │ (S3 + CDN)    │             │
│  └─────────────┘ └─────────────┘ └───────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

### API Design (WebSocket + REST)

```
WebSocket Events:
  // Send message
  → { "type": "send_message", "conversation_id": "conv_123",
      "content": "Hello!", "message_id": "msg_456" }

  // Receive message
  ← { "type": "new_message", "conversation_id": "conv_123",
      "sender": "user_789", "content": "Hello!",
      "timestamp": "2025-01-01T00:00:00Z", "message_id": "msg_456" }

  // Typing indicator
  → { "type": "typing", "conversation_id": "conv_123" }

  // Read receipt
  → { "type": "read_receipt", "conversation_id": "conv_123",
      "last_read_message_id": "msg_456" }

REST APIs:
  GET  /api/v1/conversations                    — List conversations
  POST /api/v1/conversations                    — Create conversation
  GET  /api/v1/conversations/{id}/messages      — Get message history
  POST /api/v1/media/upload                     — Upload media file
  GET  /api/v1/users/{id}/presence              — Get user presence
```

---

## Step 3: Deep Dive

### Message Flow (1-on-1)

```
User A sends message to User B:

1. Client A → WebSocket Gateway 1
   { "type": "send_message", "to": "user_B", "content": "Hi!" }

2. Gateway 1 → Message Service
   Validate, persist, assign message_id

3. Message Service → Kafka (topic: messages)
   { "message_id": "msg_123", "from": "A", "to": "B",
     "content": "Hi!", "timestamp": "..." }

4. Message Service → Gateway 1 (ack to sender)
   { "type": "message_sent", "message_id": "msg_123",
     "status": "sent" }

5. Message Service → Check if User B is online
   ├── Online: Route to Gateway 2 (where B is connected)
   │   Gateway 2 → Client B: { "type": "new_message", ... }
   │   Client B → Gateway 2: { "type": "delivery_receipt", ... }
   │   Gateway 2 → Client A: { "type": "delivered", ... }
   │
   └── Offline: Push Notification Service
       → APNs / FCM → User B's device
```

### Message Ordering

```
Challenge: Messages may arrive out of order across gateways

Solution: Sequence Numbers per Conversation
├── Each conversation has a monotonically increasing sequence
├── Message Service assigns sequence number on persistence
├── Client uses sequence to sort messages
└── Gap detection: Client requests missing messages

Implementation:
  conversation_sequences {
      conversation_id VARCHAR,
      last_sequence   BIGINT,
      PRIMARY KEY (conversation_id)
  }

  -- Atomic increment
  UPDATE conversation_sequences
  SET last_sequence = last_sequence + 1
  WHERE conversation_id = 'conv_123'
  RETURNING last_sequence;
```

### Group Messaging

```
Group Message Flow:

1. User A sends to Group G (100 members)
2. Message Service persists message
3. Message Service → Kafka (topic: group_messages)

4. Fan-out Service consumes from Kafka:
   ├── Get group member list (from cache/DB)
   ├── For each online member:
   │   ├── Find their WebSocket gateway
   │   └── Push message to their gateway
   └── For offline members:
       └── Queue push notification

Optimization: Don't fan-out to all 100 members individually
├── Use Kafka consumer groups
├── Each gateway subscribes to relevant group topics
└── Gateway handles delivery to its connected clients
```

### Presence System

```
Architecture:
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Client  │────→│   Gateway    │────→│   Presence   │
│          │     │              │     │   Service    │
└──────────┘     └──────────────┘     └──────┬───────┘
                                             │
                                       ┌─────▼──────┐
                                       │   Redis    │
                                       │  (TTL-based│
                                       │   keys)    │
                                       └────────────┘

Implementation:
- Client sends heartbeat every 30 seconds
- Gateway updates Redis: SET presence:{user_id} "online" EX 60
- If no heartbeat for 60 seconds → mark offline
- Presence Service publishes changes to subscribers

Optimization:
- Don't broadcast every presence change to all contacts
- Only send presence updates to users currently viewing the chat
- Batch presence updates (send every 5 seconds)
```

### Delivery Guarantees

```
At-Least-Once Delivery:
1. Client sends message → Gateway ACKs
2. Gateway persists to Message Service
3. Message Service writes to Kafka (durable)
4. Consumer processes and ACKs Kafka offset
5. If consumer crashes → Kafka redelivers

Exactly-Once Semantics (simplified):
- Client generates unique message_id (UUID)
- Message Service checks for duplicate before processing
- Idempotency key prevents double-processing

Message States:
  SENDING → SENT (server received) → DELIVERED (recipient received) → READ
```

### Media Handling

```
Upload Flow:
1. Client → API Server: Request upload URL (pre-signed S3 URL)
2. Client → S3: Upload media directly (avoids API server bottleneck)
3. S3 → Lambda: Trigger thumbnail generation
4. Client → WebSocket: Send message with media_id
5. Recipient gets message → Fetch media from CDN

Storage:
├── S3 for original files
├── CDN for serving (CloudFront)
├── Thumbnails generated on upload (multiple sizes)
└── Virus scanning on upload (ClamAV via Lambda)
```

---

### Presence: The Deceptively Simple Feature

Presence looks like a boolean and behaves like a distributed-systems problem. The state machine itself is easy — `OFFLINE → ONLINE → (idle) → OFFLINE`, with a `last_seen` timestamp — but every transition is ambiguous. **Connection liveness is not presence**: a phone locked in a pocket holds its TCP/WebSocket connection through NAT for minutes, and a laptop with a minimized browser keeps a perfectly healthy socket from a user who left for lunch. So production systems separate three signals: **WS ping/pong** (protocol-level liveness — detects dead sockets), the **app-level heartbeat** (every 30s the client renews a TTL key, so the *server* never trusts the socket alone), and the **client visibility API** (a foregrounded tab or screen-on app asserts the user is actually there). "Online" should mean *socket alive AND app visible within the heartbeat window* — anything less gives you the green dot that lies.

The cost problem is fanout, not storage. Each user's status is watched by K friends, so presence event volume = **users × K × transitions/day**. For 1M DAU, K = 200, and 50 transitions/day, that is 1M × 200 × 50 = **10B presence events/day ≈ 116K events/s average** — a broadcast storm where almost every event is irrelevant to its recipient (who may be offline, or in a different app screen). Four levers cut it, in descending order of impact:

1. **Notify only online watchers**: an event that matters only to connected sessions can skip all offline subscribers. At 10% of watchers online, 10B/day drops to **1B/day**.
2. **Debounce flapping**: subway Wi-Fi and NAT timeouts generate transition pairs within seconds. A grace window ("go offline" only after 60s of missed heartbeats, then re-notify) collapses 50 real transitions to ~10 meaningful ones: **2B/day**. The two levers compose: ~**200M/day** — a 50× reduction from the naive design, for zero product change.
3. **TTL-based liveness instead of explicit offline events**: store presence as `SET presence:{user_id} EX 60` refreshed by heartbeat and let expiry *be* the offline transition. Now the write rate is bounded by heartbeats (1M users / 30s ≈ 33K writes/s, sharded by user hash) and there is no offline fanout at all — watchers learn "offline" on their next fetch or from their own subscription layer.
4. **Subscribe by view, not by social graph**: Slack's presence servers keep presence "in-memory," hash "users... to individual PSs," and — the key line — "A Slack client receives presence notifications only for a subset of users that are visible in the app screen at any moment" [1]. Their follow-up edge-cache post quantifies the same idea applied at the client edge: "we've already moved user presence updates to the pub/sub model with great results: the number of presence events received by clients was reduced by a factor of 5" [2].

**Last-seen coarsening is simultaneously a privacy and a load feature.** Quantize `last_seen` to minute or 5-minute buckets ("last seen 14:05"): at most 288 distinct values per user per day, so writes can be skipped whenever the bucket hasn't changed, and the presence channel cannot be abused as a high-frequency covert signal of exactly when someone's phone unlocked. Privacy and throughput point at the same design — a rare alignment worth saying out loud in an interview.

### Typing Indicators and Read Receipts

Typing indicators and read receipts are **ephemeral signals: they must not touch durable storage**. Slack names the category directly: "Transient events... are a category of events that are not persisted in the database and are sent through a slightly different flow. User typing in a channel or a document is one such event" [1]. Fire-and-forget over the WebSocket, relay-only-to-current-viewers, never written to the message store, never replayed on reconnect — a stale "Alice is typing…" from three minutes ago is a bug, and persistence is how you get it. The flip side is deliberate lossiness: under load, the gateway drops transient events first (see [Graceful Degradation](../../backend/patterns/graceful-degradation.md)); chat correctness never depends on them.

**Typing is a client-throttled event stream**: send `typing_start` on first keystroke, at most one repeat every ~3 seconds while typing continues, and `typing_stop` on send or idle. The throttle matters at scale — 50M DAU typing 40 messages/day at ~5 keystrokes/s for 5s each is 50B keystroke-level events/day; with the 3-second window it is ~3 events per message, **6B/day**, an 8× cut the user cannot perceive.

**Read receipts are a per-message delivery state machine — `SENT → DELIVERED → READ` — that must not be fanned out per message in groups.** In a 500-member group, one member's read of one message must reach 499 others; per-message receipts make event volume O(users × messages), which is quadratic in the worst case. The fix is the **watermark**: track *max read offset per user per conversation*, not per message. Each client emits one `read_up_to: {conversation_id, user_id, seq}` transition per reading session; the server stores the watermark and publishes transitions (O(1) per user), and clients render "seen by" from watermarks. A member opening the group after a week reads current state — who has read up to what — instead of replaying a week of receipt events. This is the same event-sourcing insight as the [delivery-guarantees matrix](./notifications.md): state is the aggregate, events are the noise.

### Websocket Scale-Out

50M concurrent connections cannot share a process, so the moment you add a second gateway you inherit three distributed problems.

**Connection state and the registry.** The WebSocket handshake is HTTP; after `101 Switching Protocols` the connection lives on exactly one gateway node, so load balancers need sticky sessions — but stickiness is an *optimization*, not correctness. Any component that wants to push to user U needs the answer to "which gateway holds U?", and that is a **connection registry**: `user_id → gateway_id` (plus connection metadata) in Redis, written on connect, TTL-refreshed on every heartbeat, cleared on disconnect. A stale registry entry after a gateway crash routes to a dead node — the sender falls back to the offline path (push notification, see [Notification System](./notifications.md)) while the reconnecting client repairs the registry itself. Stickiness without a registry works only while nothing in the system ever needs to *find* a user — which excludes group chat, presence, and typing, i.e., the product.

**Channel ownership and fanout.** The scalable shape is pub/sub: gateways subscribe to the channels their connected users are viewing, and the message service publishes once per conversation. Who aggregates? A consistent-hash channel owner. Slack runs exactly this: "Every CS is mapped to a subset of channels based on consistent hashing. At peak times, about 16 million channels are served per host" [1], with gateways deployed "across multiple geographical regions" and "a draining mechanism for region failures that seamlessly switches the users in a bad region to the nearest good region" [1] — delivering "messages across the world in 500ms" [1]. Discord formalized the other half — route *storage* traffic by the same key: their data-service routing uses "a channel ID, so all requests for the same channel go to the same instance of the service" [3], which also enables request coalescing ("If multiple users are requesting the same row at the same time, we'll only query the database once" [3]) when a big announcement makes everyone read the same partition at once.

**Reconnect storms after deploys.** Rolling 100 gateway nodes × 500K connections each = 50M clients re-dialing at once; unthrottled, every client with naive retry hammers the new node in a synchronized burst. The defenses are client-side **jittered exponential backoff** (spreading 50M reconnects over a minute is ~833K/s — trivially absorbable, and per-connection admission still obeys the [rate limiter](./rate-limiter.md)), and server-side state that survives reconnection: Slack reports that "when new or recently disconnected users connect, they are served directly from the Flannel cache, which reduces impact of reconnect storms to the Slack backend servers" [2] — an edge tier serving "4 million simultaneous connections at peak" [2]. The deep principle: a reconnecting client is a *cold cache*, not a database client — hand it snapshot state from an edge tier and let it catch up via the sequence numbers below.

**Ordering across gateways.** Gateways are stateless for messages: whoever owns the conversation partition assigns the monotonic per-conversation sequence at persistence (see Message Ordering above), and every consumer — gateway, offline sync, search indexer — orders by that sequence, never by arrival time or gateway-local clocks. Discord's storage schema shows the same discipline at trillion scale: "Every ID we use is a Snowflake, making it chronologically sortable," with messages partitioned "by the channel they're sent in, along with a bucket, which is a static time window" [3] — one owner per partition key, one sortable sequence per conversation, clients detect gaps and pull by sequence. The gateway a message *arrives at* must never influence the order a conversation *reads in*.

## Step 4: Trade-offs

### WebSocket vs Long Polling vs SSE
| Technology | Pros | Cons |
|-----------|------|------|
| WebSocket | Full duplex, low latency | Complex, stateful servers |
| Long Polling | Simple, works everywhere | Higher latency, more overhead |
| SSE | Simple, server→client only | Unidirectional |

**Choice:** WebSocket — required for real-time bidirectional chat.

### Cassandra vs PostgreSQL for Messages
| Database | Pros | Cons |
|----------|------|------|
| Cassandra | Write-heavy optimized, linearly scalable | No JOINs, eventual consistency |
| PostgreSQL | ACID, complex queries | Harder to scale writes |

**Choice:** Cassandra for messages (append-heavy, time-series), PostgreSQL for user data.

### Push vs Pull for New Messages
| Approach | Pros | Cons |
|----------|------|------|
| Push (WebSocket) | Real-time, low latency | Connection management |
| Pull (polling) | Simple | Wasted requests, latency |

**Choice:** Push for online users, pull as fallback for reconnecting clients.

## 📚 References

1. Slack Engineering, "Real-time Messaging" — <https://slack.engineering/real-time-messaging/> — fetched in full this session; all quoted sentences verbatim: Presence Servers ("in-memory... keep track of which users are online", users hashed to PSs, on-screen-only presence notifications), Transient events ("not persisted in the database"), consistent-hash Channel Servers ("about 16 million channels are served per host"), multi-region Gateways with the draining mechanism, and the 500ms worldwide delivery figure.
2. Slack Engineering, "Flannel: An Application-Level Edge Cache to Make Slack Scale" — <https://slack.engineering/flannel-an-application-level-edge-cache-to-make-slack-scale/> — fetched in full this session; the presence-events-reduced-by-a-factor-of-5 pub/sub result, the reconnect-storm absorption quote, and the 4M-connection / 600K-queries-per-second figures quoted verbatim.
3. Discord Engineering (Bo Ingram), "How Discord Stores Trillions of Messages" — <https://discord.com/blog/how-discord-stores-trillions-of-messages> — fetched in full this session; Snowflake-ID chronological sortability, channel+bucket partitioning, channel-ID consistent-hash routing, and request coalescing quoted verbatim.

*Note:* sources this session could not fetch or verify — WhatsApp's blog (HTTP 400 on every probe), Instagram Engineering (connection failure), and Discord's "How Discord Scaled Elixir to 5,000,000 Concurrent Users" (JavaScript-rendered; content not retrievable) — are deliberately **not** cited here rather than cited from memory.

## 🔗 Cross-References

- [Notification System](./notifications.md) — Push notification deep dive; the offline-user fallback when the connection registry says "not here", and the at-least-once semantics this page's receipts rely on
- [Key-Value Store](./kv-store.md) — Storage design for messages
- [Real-World Chat System](./real-world/chat-system.md) — Slack-style team chat at 50M concurrent WebSocket connections
- [Messaging Systems (HLD)](./hld/messaging-systems.md) — Queue delivery guarantees and DLQ behind the gateways
- [Notification Service (LLD)](./lld/notification-service.md) — Client-side notification class design
- [Rate Limiter](./rate-limiter.md) — Admission control for reconnect bursts and per-connection quotas
- [Graceful Degradation](../../backend/patterns/graceful-degradation.md) — Dropping transient events first under load
- [Slack Case Study](./real-world/slack.md) — The architecture this page's Slack quotes come from
- [WhatsApp](./real-world/whatsapp.md) / [Telegram](./real-world/telegram.md) — Consumer-messaging variants of the same design
- [Networking Questions](../network-questions.md) — WebSocket protocol details
- [OS Questions](../os-questions.md) — Connection handling, threading
