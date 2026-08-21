# AWS SNS (Simple Notification Service)

Amazon SNS is a managed pub/sub messaging service, launched in 2010. It provides push-based fan-out: a publisher sends one message to an SNS topic; SNS delivers the message to all subscribers (SQS queues, Lambda functions, HTTP endpoints, mobile devices, email addresses). This page covers the architecture, the subscriber types, the message filtering, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  SNS Topic (multi-tenant, multi-AZ, managed)               │
│  - Receives messages from publishers                        │
│  - Delivers to all subscribers                              │
│  - 11 nines durability (cross-AZ replication)              │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲                              ▲
        │                              │                              │
        ▼                              ▼                              ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Subscriber 1:    │    │  Subscriber 2:    │    │  Subscriber 3:    │
│  SQS queue       │    │  Lambda function  │    │  HTTP endpoint   │
└──────────────────┘    └──────────────────┘    └──────────────────┘
        ▲                              ▲                              ▲
        │                              │                              │
        ▼                              ▼                              ▼
    Publisher sends one message → SNS fans out to all subscribers
```

SNS is a push-based system. Publishers send to a topic; SNS pushes to subscribers. The publisher doesn't know the subscribers; the subscribers don't know the publisher.

## Topic Types

### Standard Topics

- **Unlimited throughput**: no per-second cap.
- **At-least-once delivery**: a message is delivered at least once, but may be delivered more than once.
- **No ordering**: messages may be delivered out of order.

### FIFO Topics

- **Throughput limit**: 300 messages/sec (or 3000 with batching).
- **Exactly-once delivery**: messages are delivered once and remain until acked.
- **FIFO ordering**: messages delivered in order.

FIFO topics require FIFO SQS subscribers (not Lambda or HTTP).

## Subscriber Types

SNS can deliver to:

### SQS Queue

The most common subscriber type. SNS enqueues a message in the SQS queue; the consumer of the SQS queue processes it.

```bash
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:123:my-topic \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:123:my-queue
```

SNS delivers via the SQS queue's API. This decouples SNS from the consumer's processing speed.

### Lambda Function

SNS invokes the Lambda function directly, passing the message as the event payload:

```python
def handler(event, context):
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        process(message)
```

Lambda's SNS trigger is fully managed; SNS retries on failure (3 retries by default).

### HTTP/HTTPS Endpoint

SNS sends an HTTP POST to a URL:

```http
POST / HTTP/1.1
Host: example.com
x-amz-sns-message-type: Notification
x-amz-sns-message-id: abc-123
Content-Type: application/json

{
  "Type": "Notification",
  "MessageId": "abc-123",
  "TopicArn": "arn:aws:sns:us-east-1:123:my-topic",
  "Subject": "Order placed",
  "Message": "{\"order_id\": 123}",
  "Timestamp": "2024-01-15T12:34:56.789Z",
  "SignatureVersion": "1",
  "Signature": "...",
  "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-...",
  "UnsubscribeURL": "..."
}
```

The endpoint must respond with 2xx; otherwise, SNS retries (with exponential backoff). The endpoint should verify the message signature (to prevent spoofing).

### Email

SNS can send emails (text-only) to subscribers. Useful for alerts and notifications.

### Mobile Push (APNS, FCM, ADM, Baidu)

SNS sends push notifications to mobile devices via the device's push service (Apple APNS, Google FCM).

### SMS

SNS can send SMS messages to phone numbers. Useful for critical alerts.

## Message Filtering

Subscribers can filter the messages they receive:

```json
{
  "order_type": ["premium"],
  "customer_country": ["US", "CA"]
}
```

A subscriber with this filter only receives messages where `order_type=premium` AND `customer_country` is US or CA. Other subscribers get other messages.

```bash
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:123:my-topic \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:123:premium-orders \
  --attributes '{"FilterPolicy":"{\"order_type\":[\"premium\"]}"}'
```

Filtering at the SNS layer saves the consumer from receiving irrelevant messages.

## The Fan-Out Pattern

The classic SNS use case: a single publisher fans out to many consumers via SQS:

```text
Publisher → SNS topic → SQS queue 1 (analytics consumer)
                      → SQS queue 2 (audit consumer)
                      → SQS queue 3 (notification consumer)
```

Each consumer has its own queue, processes at its own pace, and can be independently scaled. The publisher doesn't know about the consumers.

This is the basis for event-driven architectures: a single source of truth (the publisher) and many independent consumers.

## The SNS+SQS DLQ Pattern

For reliable delivery:

```text
SNS → SQS (with DLQ)
       │
       ├── On success: SQS deletes the message.
       └── On failure (after maxReceiveCount): message moves to DLQ.
```

This gives at-least-once delivery with retry. The DLQ holds poison pill messages.

## Production Use Cases

### Event-Driven Microservices

```text
Order Service → SNS topic "order-events" →
  ├── Inventory Service (Lambda) — adjust stock
  ├── Shipping Service (SQS+worker) — schedule shipping
  └── Notification Service (Lambda) — email customer
```

The Order Service publishes an event; downstream services react independently. Adding a new consumer (e.g., a new "Fraud Detection Service") is just subscribing a new SQS queue.

### Alerting

```text
Monitoring (CloudWatch) → SNS topic "alerts" →
  ├── PagerDuty HTTP endpoint (for paging)
  ├── Email subscriber (for archive)
  └── Lambda (for auto-remediation)
```

CloudWatch alarms publish to SNS; SNS fans out to multiple alerting channels.

### Mobile Push Notifications

```text
Backend → SNS topic (platform application = APNS) → device token
```

SNS handles the APNS/FCM API; the backend just sends a JSON to SNS.

## Production Performance

SNS performance:
- Throughput (standard): unlimited.
- Throughput (FIFO): 300 msgs/sec.
- Latency (push to SQS): ~10 ms.
- Latency (push to HTTP): variable (depends on endpoint).
- Max message size: 256 KB (or larger with S3 extension).

For very high throughput, partition the topic by a hash key (multiple topics).

## Common Pitfalls

1. **Forgetting that SNS delivery is async.** A successful `Publish` API call doesn't mean the message was delivered to subscribers; SNS attempts delivery async. For synchronous delivery, use SNS+SQS with synchronous receive.

2. **Forgetting that HTTP endpoints must verify signatures.** Without verification, an attacker can POST fake SNS messages to the endpoint. Always verify the `Signature` field against SNS's signing certificate.

3. **Forgetting that SNS may retry HTTP delivery many times.** The default retry policy retries for up to 24 hours. If the endpoint is consistently failing, SNS keeps retrying. Consider unsubscribing on persistent failure.

4. **Forgetting that filtering happens at delivery time.** A subscriber with a filter policy only receives matching messages, but the policy is applied after the SNS topic routes — there's some overhead.

5. **Forgetting that FIFO topics require FIFO subscribers.** Lambda and HTTP subscribers don't support FIFO; only SQS FIFO queues can subscribe.

6. **Forgetting that SNS messages are limited to 256 KB.** For larger payloads, store in S3 and pass the S3 pointer (use the S3 message attribute with the S3 URL).

## Comparison to Other Pub/Sub Systems

| Aspect | SNS | Kafka | Redis Pub/Sub | Pulsar |
|--------|-----|-------|---------------|--------|
| Delivery | Push | Pull | Push | Pull |
| Persistence | Yes (SQS subscriber) | Yes (log) | No | Yes (log) |
| Fan-out | Yes | Via consumer groups | Yes | Yes |
| Filtering | Yes (policy) | No | No | Yes |
| Best for | AWS-native fan-out | High-throughput logs | Real-time push | Multi-tenant pub/sub |

SNS is the AWS-native fan-out choice. Kafka for high-throughput pull-based. Redis Pub/Sub for ephemeral broadcasts.

## References

- [AWS SNS documentation](https://docs.aws.amazon.com/sns/latest/dg/welcome.html)
- [SNS subscriber types](https://docs.aws.amazon.com/sns/latest/dg/sns-event-destinations.html)
- [SNS message filtering](https://docs.aws.amazon.com/sns/latest/dg/sns-message-filtering.html)
- [SNS + SQS fan-out pattern](https://docs.aws.amazon.com/sns/latest/dg/sns-common-scenarios.html)
- [SNS mobile push notifications](https://docs.aws.amazon.com/sns/latest/dg/sns-mobile-notifications.html)
- [SNS HTTP/HTTPS endpoint verification](https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature.html)
- [SNS vs Kafka (Confluent blog)](https://www.confluent.io/blog/sns-vs-kafka/)
- [LWN: SNS overview (2020)](https://lwn.net/Articles/820133/)
