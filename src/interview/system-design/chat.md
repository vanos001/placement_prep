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

## 🔗 Cross-References

- [Notification System](./notifications.md) — Push notification deep dive
- [Key-Value Store](./kv-store.md) — Storage design for messages
- [Networking Questions](../network-questions.md) — WebSocket protocol details
- [OS Questions](../os-questions.md) — Connection handling, threading
