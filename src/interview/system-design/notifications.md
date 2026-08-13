# Design a Notification System

> **Difficulty:** ⭐⭐⭐ | **Asked at:** Amazon, Meta, Uber | **Time:** 40 minutes

## 🎯 Problem Statement

Design a notification system that:
- Sends notifications via multiple channels (push, SMS, email)
- Handles millions of notifications per day
- Supports prioritization and rate limiting
- Guarantees delivery with retries

---

## Step 1: Requirements

### Functional Requirements
1. Send notifications via Push (iOS/Android), SMS, Email
2. Support different notification types (transactional, marketing, alerts)
3. User preferences (opt-in/out per channel, quiet hours)
4. Template-based notifications
5. Delivery tracking and analytics
6. Rate limiting per user

### Non-Functional Requirements
| Requirement | Target |
|------------|--------|
| Throughput | 10M notifications/hour |
| Latency (high priority) | < 5 seconds |
| Delivery rate | > 99% |
| Availability | 99.99% |

---

## Step 2: High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐     ┌──────────────┐     ┌───────────────────┐   │
│  │ Event    │────→│ Notification │────→│   Message Queue   │   │
│  │ Sources  │     │   Service    │     │    (Kafka)        │   │
│  └──────────┘     └──────────────┘     └────────┬──────────┘   │
│                                                  │              │
│       ┌──────────────────┬───────────────────────┼──────┐       │
│       │                  │                       │      │       │
│  ┌────▼──────┐    ┌──────▼──────┐         ┌──────▼──────┐     │
│  │  Push     │    │   SMS       │         │  Email      │     │
│  │  Worker   │    │   Worker    │         │  Worker     │     │
│  └────┬──────┘    └──────┬──────┘         └──────┬──────┘     │
│       │                  │                       │             │
│  ┌────▼──────┐    ┌──────▼──────┐         ┌──────▼──────┐     │
│  │  APNs/   │    │  Twilio/    │         │  SendGrid/  │     │
│  │  FCM     │    │  SNS        │         │  SES        │     │
│  └──────────┘    └─────────────┘         └─────────────┘     │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │  Template    │  │  User Pref   │  │  Delivery        │     │
│  │  Service     │  │  Service     │  │  Tracker         │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 3: Deep Dive

### Notification Flow

```
Step 1: Event Trigger
  ┌─────────────────────────────────────────────────┐
  │  Order placed → Notification Service             │
  │  {                                              │
  │    "user_id": "123",                            │
  │    "type": "order_confirmation",                │
  │    "data": {"order_id": "ORD-456"},            │
  │    "priority": "high",                          │
  │    "channels": ["push", "email"]               │
  │  }                                              │
  └─────────────────────────────────────────────────┘

Step 2: Validate & Enrich
  ├── Check user preferences (has user opted in?)
  ├── Check quiet hours (is it 3am for this user?)
  ├── Load notification template
  ├── Render template with data
  └── Rate limit check (too many notifications today?)

Step 3: Route to Channel Queues
  ├── Push → kafka-topic-notifications-push
  ├── SMS  → kafka-topic-notifications-sms
  └── Email → kafka-topic-notifications-email

Step 4: Worker Processes
  ├── Fetch from queue
  ├── Format for provider API
  ├── Send via provider (APNs, Twilio, SendGrid)
  ├── Handle response (success/failure/retry)
  └── Update delivery status

Step 5: Delivery Tracking
  ├── Sent → Delivered → Opened → Clicked
  ├── Track failures and retries
  └── Generate analytics
```

### Message Queue Design

```
Kafka Topics:
├── notifications-high    (3 partitions, RF=3)
│   └── Transactional: order confirmation, password reset
├── notifications-medium  (6 partitions, RF=3)
│   └── Alerts: price drops, friend requests
├── notifications-low     (12 partitions, RF=3)
│   └── Marketing: newsletters, promotions

Consumer Groups:
├── push-worker-group     (10 consumers)
├── sms-worker-group      (5 consumers)
├── email-worker-group    (20 consumers)

Priority Processing:
├── High priority: Processed first, dedicated consumers
├── Medium priority: Normal processing
├── Low priority: Processed during off-peak, can be delayed
```

### Retry & Dead Letter Queue

```
Retry Strategy:
┌─────────────────────────────────────────────────┐
│  Attempt 1: Immediate                           │
│  Attempt 2: After 1 minute                      │
│  Attempt 3: After 5 minutes                     │
│  Attempt 4: After 30 minutes                    │
│  Attempt 5: After 2 hours                       │
│  → Dead Letter Queue (manual review)            │
└─────────────────────────────────────────────────┘

Dead Letter Queue (DLQ):
├── Stores permanently failed notifications
├── Dashboard for manual review
├── Alerting when DLQ grows (indicates systemic issue)
└── Periodic retry attempts for transient failures
```

### User Preferences

```json
{
  "user_id": "123",
  "preferences": {
    "push": {
      "enabled": true,
      "order_updates": true,
      "promotions": false,
      "quiet_hours": { "start": "22:00", "end": "08:00", "timezone": "IST" }
    },
    "email": {
      "enabled": true,
      "order_updates": true,
      "promotions": true,
      "frequency": "daily_digest"
    },
    "sms": {
      "enabled": false
    }
  }
}
```

### Rate Limiting

```
Per-User Limits:
├── Push: Max 10/hour, 50/day
├── SMS: Max 3/hour, 10/day
├── Email: Max 5/hour, 20/day
└── Override for critical (password reset, security alerts)

Global Limits:
├── Protect third-party provider rate limits
├── APNs: 1M notifications/minute
├── Twilio: 100 SMS/second
└── SendGrid: 10K emails/minute

Implementation:
  Redis key: rate_limit:{user_id}:{channel}:{window}
  Sliding window counter algorithm
```

### Template System

```yaml
templates:
  order_confirmation:
    push:
      title: "Order Confirmed! 🎉"
      body: "Your order #{{order_id}} has been confirmed. Expected delivery: {{delivery_date}}"
      action: "open_order_details"
    email:
      subject: "Order Confirmation - #{{order_id}}"
      body_template: "order_confirmation.html"
    sms:
      message: "Your order #{{order_id}} is confirmed. Track: {{tracking_url}}"

  password_reset:
    push:
      title: "Password Reset"
      body: "Your password was changed. If this wasn't you, tap here."
    email:
      subject: "Reset Your Password"
      body_template: "password_reset.html"
    # SMS disabled for this type (security)
```

---

## Step 4: Trade-offs

### Push vs Pull for Event Processing
| Approach | Pros | Cons |
|----------|------|------|
| Push (webhook) | Real-time | Coupling, retry complexity |
| Pull (queue) | Decoupled, reliable | Slight delay |

**Choice:** Push to queue, pull from queue (hybrid).

### At-Least-Once vs Exactly-Once Delivery
| Guarantee | Pros | Cons |
|-----------|------|------|
| At-least-once | Simpler, reliable | Possible duplicates |
| Exactly-once | No duplicates | Complex, slower |

**Choice:** At-least-once with idempotency keys (deduplicate on client side).

### Centralized vs Per-Channel Queues
| Approach | Pros | Cons |
|----------|------|------|
| Centralized queue | Simple management | Channel coupling |
| Per-channel queues | Independent scaling, isolation | More infrastructure |

**Choice:** Per-channel queues for independent scaling.

## 🔗 Cross-References

- [Chat System](./chat.md) — Real-time delivery patterns
- [Rate Limiter](./rate-limiter.md) — Rate limiting strategies
- [Architecture Concepts](../../cheatsheets/architecture.md) — Message queues, reliability
- [Networking Questions](../network-questions.md) — Webhooks, push protocols
