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

### Fanout Architectures and the Read-Path/Write-Path Trade

Every notification begins as one event ("order shipped", "Alice mentioned you") that must become *N* per-recipient deliveries. The defining decision is **who does the recipient-addressing work, and when**:

- **Fanout-on-write**: at event time, resolve every recipient and enqueue one durable per-recipient record per channel. Cost follows the *publisher's* audience. Run the numbers: one 200-byte notification to an account with 10M followers creates **10M queue messages ≈ 2 GB** in a single event; a busy account firing 100 such events a day produces **1B fanout writes/day and 200 GB/day of queue volume** — before retries. The payoff: every downstream stage (preference filtering, rendering, provider send, retry, tracking) operates on a small, independently retryable unit.
- **Fanout-on-read**: store the event once; each recipient's client merges it at fetch. Cost follows the *reader's* subscription count and session frequency — the same 10M followers pulling from ~50 celebrity sources at 10 opens/day do ~5B merge-fetches/day, but only for people actually online. The cost is merge latency at read time and per-source state kept queryable for every follower.
- **Hybrid**: write-path below a follower threshold, read-path above it. The [News Feed](./news-feed.md) chapter works through this hybrid (the "celebrity problem" originated there). Notifications twist it one way: delivery still needs *per-user* channel addressing (device tokens, opted-in channels, quiet hours), so systems usually hybridize on the **type axis** — transactional pushes (password reset) are always write-path, while "price drop on a watched item" pushes can be read-path or digested.

**Coalescing, dedup, and grouping** are the fanout pressure valves. Batching N notifications for one user into a digest is a windowing problem: collect events per `(user_id, grouping_key)` into a window (10 minutes, or "until the app next opens"), render one summary, and cap each window at K notifications so a burst cannot itself become spam. The **grouping key design** is the interview content: group by what the user perceives as one conversation — `user_id + thread_id` for messages, `user_id + repo_id` for CI results — never by `event_id`. The window must be per-priority: no digest window ever holds a password reset.

**Quiet hours and preferences are a filter stage, not a delivery afterthought.** Evaluate them *before* enqueueing per-recipient records: a notification filtered at send time has already paid the queue write, the render, and possibly a provider fee. Quiet-held notifications go to the digest window, not a midnight send queue. This is not just etiquette — interruption carries measurable productivity and stress cost, the empirical basis for digest batching [1].

### Push Channel Internals: APNs, FCM, and What Breaks

Push is not "one API" — it is two provider ecosystems with their own registries, limits, and failure semantics.

**Device-token registries.** A push token is an opaque per-device address, and it *rotates*. Apple is blunt: "**Never cache device tokens in local storage. APNs issues a new token when the user restores a device from a backup, when the user installs your app on a new device, and when the user reinstalls the operating system**" [2]. Clients therefore re-upload the token on every app launch, and the registry stores `user_id → set of device tokens` ("prepare your app to handle multiple device tokens" [2]). FCM adds a time dimension: it "considers a registration to be stale if its app instance hasn't connected for a month," and "when a registration has been inactive for 270 days, FCM considers it expired and garbage collects it" [3] — your registry needs its own staleness pruning, not just provider-driven cleanup.

**Why providers batch and throttle.** APNs is a shared best-effort service that "may reorder notifications you send to the same device token" and, when a device is offline, "**stores only one notification per bundle ID**" (mostly the latest) [4]. Apple's connection guidance: "reuse a connection as long as possible... many hours to days" and "avoid push bursts over selective connections" [4] — a pool of long-lived HTTP/2 connections, not connection-per-send. FCM publishes its numbers: "**The default quota of 600k messages per minute**" per project, with 429 RESOURCE_EXHAUSTED until refill; "up to 240 messages per minute and 5,000 messages per hour to a single device"; collapsible messages "limited to a burst of 20 messages per app per device, with a refill of 1 message every 3 minutes" [5]. These turn "we'd throttle" into "we'd shape a 1M/min fanout across a 600k/min per-project quota with connection pooling."

**Payload caps force an envelope design.** Apple's JSON payload "is limited to a maximum size of 4 KB (4096 bytes)" (5 KB for VoIP) [4]; FCM's is 4096 bytes for most messages, 2048 for topics [6]. Oversize sends fail with APNs 413 `PayloadTooLarge` [8] or FCM "message too big" [6]. Consequence: send **IDs, not content** — the push carries a notification ID and deep link; the client fetches the body. A template that grows past 4 KB in production is a self-inflicted outage.

**Collapse keys, TTL, priority.** Both providers collapse: Apple's `apns-collapse-id` merges notifications and "must not exceed 64 bytes" [4], on top of the store-one-while-offline behavior; FCM's `collapse_key` — "when a device is not connected, only the last message with a given collapse key is queued for eventual delivery" [7]. Provider collapse is the last resort; your coalescing window is the first. TTL is Apple's `apns-expiration` ("If the value is 0, APNs attempts to deliver the notification only once and doesn't store it" [4]) and FCM's `ttl`, capped at "2,419,200 (4 weeks)" [6]. Priority: Apple's `apns-priority` 10/5/1 (immediate / power-conscious / never wake) [4], FCM's 5/10 [7] — and the pairing matters: Apple's `background` push type (silent push, below) must "**Always** use priority `5`. Using priority `10` is an error" [4].

**Feedback service and error-code-driven cleanup** keep the registry honest. APNs returns `410` — "the device token is no longer active for the topic" — with a `timestamp` "at which APNs confirmed the token was no longer valid" [8], plus an explicit never-retry list: `BadDeviceToken`, `DeviceTokenNotForTopic`, `Forbidden`, `ExpiredToken`, `Unregistered`, `PayloadTooLarge` [8]. FCM's mirror is `UNREGISTERED (HTTP 404)` — "the token used is no longer valid" — caused by uninstall ("if the APNs Feedback Service reported the APNs token as invalid"), token expiry, or app update; the doc's directive: "remove this registration token from the app server and stop using it to send messages" [6]. The operational pattern (used in the [real-world case study](./real-world/notification-system.md)): on 410/UNREGISTERED delete the token row synchronously; on 429 back off; on 5xx retry later. A registry that never processes feedback degenerates into permanently wasted sends.

### Delivery Guarantees Matrix and At-Least-One-Surface Semantics

The deepest trap is treating "a notification" as one deliverable. It is one logical event that fans into **channels × devices × providers**, and the honestly statable guarantee is *per (notification, channel, device)*:

| Surface | Transport guarantee | Realistic end-to-end guarantee |
|---|---|---|
| Push (APNs/FCM) | At-least-once to provider; store-and-forward per TTL/collapse rules [4] | At-least-once *handed to provider*; display best-effort |
| Email (SES/SendGrid) | At-least-once to provider | Provider-acked send; delivery webhooks best-effort |
| SMS (Twilio) | At-least-once to provider | Carrier status callbacks (sent/delivered) |
| In-app / WebSocket | At-least-once over the bus | At-least-once to connected client; client dedups |

Three semantics make the matrix honest. **At-least-once everywhere + client-side dedup by notification ID**: consumers, workers, and retries all duplicate, so each surface deliverable carries a stable `notification_id` (Apple even echoes your `apns-id` back on errors [8]); click tracking is idempotent the same way — unique key on `(notification_id, device_id, event_type)` (see [Idempotency](../../backend/patterns/idempotency.md)). **Read only committed state**: hooking sends off the transactional write path instead of a post-commit [CDC outbox](../../backend/patterns/cdc-outbox.md) is how users get "order confirmed" pushes for orders that rolled back. **Silent vs visible push are different products**: Apple's `background` type "deliver[s] content in the background, and don't trigger any user interactions" — priority 5 mandatory [4] — and is the transport for badge sync and pre-fetching; `alert` is the user-visible path. Conflating them burns user trust and provider goodwill simultaneously.

Two hard truths belong in every answer. **Delivery receipts are impossible for offline devices**: APNs is best-effort, reorderable, and stores one notification per bundle when offline [4] — even the provider cannot promise display, so define "delivered" precisely (handed to provider, or device ack while the app is alive) and never claim more in analytics. And **retry horizon must respect TTL**: the ladder above reaches its last attempt at 156 minutes (0 → 1 → 6 → 36 → 156 min); a 1-hour `apns-expiration`, or a quiet-hours hold ending at 8am, makes later attempts pure waste — the scheduler must expire instead of send, feeding the [dead-letter queue](./hld/messaging-systems.md) for structurally failing items (poison payloads, template regressions). Production observability mirrors the matrix: Slack models each notification as its own trace keyed by `notification_id` at 100% sampling, because one `@channel` push "would be potentially sent to hundreds of thousands of users across multiple devices, resulting in billions of spans for a single trace" [9] — telemetry is itself a fanout system, with a trigger → notify → sent → received funnel that is exactly the matrix above made measurable.

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

## 📚 References

1. Gloria Mark, Daniela Gudith, Ulrich Klocke. "The Cost of Interrupted Work: More Speed and Stress." *Proc. CHI 2008*. DOI: [10.1145/1357054.1357072](https://doi.org/10.1145/1357054.1357072) — Crossref-verified this session (title/authors/venue via api.crossref.org); the empirical basis for digest batching's claim that interruption carries real productivity cost.
2. Apple, "Registering your app with APNs" — <https://developer.apple.com/documentation/usernotifications/registering-your-app-with-apns> — fetched in full this session; the "Never cache device tokens in local storage" note and multi-device-token guidance quoted verbatim.
3. Google Firebase, "Manage FCM registration tokens" — <https://firebase.google.com/docs/cloud-messaging/manage-tokens> — fetched in full this session; one-month staleness default, 270-day Android expiry/garbage collection, stale-registration delivery warning, and delete-on-UNREGISTERED guidance quoted verbatim.
4. Apple, "Sending notification requests to APNs" — <https://developer.apple.com/documentation/usernotifications/sending-notification-requests-to-apns> — fetched in full this session (Markdown rendering); all quoted sentences verbatim: best-effort/reorder semantics, one-notification-per-bundle-ID store-and-forward, 4 KB / 5 KB payload caps, `apns-expiration`, `apns-priority`, `apns-collapse-id` (64-byte cap), `background` push type priority rule, and connection-reuse/burst best practices.
5. Google Firebase, "FCM Throttling and Quotas" — <https://firebase.google.com/docs/cloud-messaging/throttling-and-quotas> — fetched in full this session; 600k messages/minute default per-project quota, 429 RESOURCE_EXHAUSTED behavior, 240/min + 5,000/hour per-device limits, and the 20-burst / 1-per-3-minutes collapsible-message throttle quoted verbatim.
6. Google Firebase, "FCM Error Codes" — <https://firebase.google.com/docs/cloud-messaging/error-codes> — fetched in full this session; payload limits (4096/2048 bytes), TTL range (0–2,419,200 seconds), `UNREGISTERED` (404) causes including app uninstall and APNs feedback, and the remove-the-token directive quoted verbatim.
7. Google Firebase, "Understand message delivery" — <https://firebase.google.com/docs/cloud-messaging/understand-delivery> — fetched in full this session; `collapse_key` ("only the last message with a given collapse key is queued for eventual delivery"), `ttl` storage semantics, and priority values (5 normal / 10 high) quoted verbatim.
8. Apple, "Handling notification responses from APNs" — <https://developer.apple.com/documentation/usernotifications/handling-notification-responses-from-apns> — fetched in full this session; status-code table (200/400/403/404/405/410/413/429/500/503), `Unregistered`/`ExpiredToken` reasons, `timestamp` semantics on 410, the never-retry error list, and the 15-minute 5XX retry guidance quoted verbatim.
9. Slack Engineering, "Tracing Notifications" — <https://slack.engineering/tracing-notifications/> — fetched in full this session; `notification_id`-as-trace-id, 100% sampling rationale, billions-of-spans `@here`/`@channel` quote, and the trigger → notify → sent → received funnel quoted verbatim.

*Note:* engineering blogs this session could not fetch or verify (WhatsApp's blog returned HTTP 400 to every probe; Instagram Engineering was unreachable; Discord's Elixir scaling post renders only via JavaScript) are deliberately **not** cited here rather than cited from memory.

## 🔗 Cross-References

- [Chat System](./chat.md) — Real-time delivery patterns; presence and typing indicators as the free fanout that prevents push fanout
- [Rate Limiter](./rate-limiter.md) — Rate limiting strategies; the sliding-window counter behind the per-user limits above
- [News Feed](./news-feed.md) — The feed-native version of fanout-on-write vs fanout-on-read and the celebrity threshold
- [Messaging Systems (HLD)](./hld/messaging-systems.md) — Queue delivery guarantees, at-least-once semantics, and DLQ discipline the notification workers sit on
- [Notification System Case Study](./real-world/notification-system.md) — Production per-channel workers, provider circuit breakers, and stale-token cleanup
- [Notification Service (LLD)](./lld/notification-service.md) — The class-level design of the same system
- [CDC Outbox](../../backend/patterns/cdc-outbox.md) — Publishing notifications from committed state changes only
- [Graceful Degradation](../../backend/patterns/graceful-degradation.md) — Failing soft when a provider (APNs, Twilio, SendGrid) degrades
- [Idempotency](../../backend/patterns/idempotency.md) — The dedup discipline behind at-least-once surfaces and click tracking
- [Architecture Concepts](../../cheatsheets/architecture.md) — Message queues, reliability
- [Networking Questions](../network-questions.md) — Webhooks, push protocols
