# AWS SQS (Simple Queue Service)

Amazon SQS is a managed message queue service, launched in 2006 as one of AWS's first services. It provides durable, at-least-once message delivery between producers and consumers, decoupling them for scalability and fault tolerance. This page covers the architecture, the standard vs. FIFO queue types, the visibility timeout, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  SQS (fully managed, multi-tenant)                          │
│  - Distributed across multiple AZs                          │
│  - 11 nines durability (multiple copies + cross-AZ)        │
│  - No setup; queues created via API                          │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ Send message                │ Receive message
        │                              │ (long polling)
        ▼                              ▼
┌──────────────────────┐    ┌──────────────────────┐
│  Producer (lambda,    │    │  Consumer (lambda,   │
│  EC2, etc.)           │    │  EC2, etc.)          │
└──────────────────────┘    └──────────────────────┘
```

SQS is fully managed: no servers, no partitions to manage, no broker to maintain. Pricing is per-request and per-GB of data stored.

## Queue Types

### Standard Queues

- **Unlimited throughput**: no per-second cap on messages.
- **At-least-once delivery**: a message is delivered at least once, but may be delivered more than once (rare).
- **Best-effort ordering**: messages may be delivered out of order.

Standard queues are the default; use them when ordering and duplicates are tolerable.

### FIFO Queues

- **Throughput limit**: 300 messages/sec (or 3000 with batching) by default.
- **Exactly-once processing**: a message is delivered once and remains until the consumer acks.
- **First-in-first-out ordering**: messages are delivered in the order they were sent.

FIFO queues require a "Message Group ID" for ordering. Messages with the same group ID are processed in order; messages with different group IDs may be processed in parallel.

```bash
aws sqs create-queue --queue-name my-queue.fifo --attributes '{"FifoQueue":"true"}'
```

The `.fifo` suffix is required for FIFO queues.

## The Visibility Timeout

When a consumer receives a message, the message becomes "invisible" to other consumers for a configurable duration (the "visibility timeout", default 30 seconds). If the consumer doesn't delete the message before the timeout, the message becomes visible again and another consumer can receive it.

```text
Time 0: Producer sends M to queue.
Time 0: Consumer A receives M. M becomes invisible for 30s.
Time 5: Consumer A processes M.
Time 10: Consumer A deletes M. ← M is gone from the queue.

OR:

Time 0: Producer sends M to queue.
Time 0: Consumer A receives M. M becomes invisible for 30s.
Time 15: Consumer A crashes. M is not deleted.
Time 30: M becomes visible again. Consumer B receives M.
```

The visibility timeout must be longer than the expected processing time, otherwise another consumer will receive the same message (duplicate processing).

Set per-message:
```bash
aws sqs send-message --queue-url ... --message-body ... --visibility-timeout 60
```

Or per-queue:
```bash
aws sqs set-queue-attributes --queue-url ... --attributes '{"VisibilityTimeout":"60"}'
```

## Long Polling

By default, ReceiveMessage returns immediately (short polling), even if no messages are available. This wastes API calls and money.

Long polling: ReceiveMessage waits up to 20 seconds for a message:

```bash
aws sqs receive-message --queue-url ... --wait-time-seconds 20
```

If a message arrives within 20 seconds, it's returned immediately. If not, an empty response is returned at the end of the 20 seconds. Long polling reduces costs (fewer empty API calls) and improves user experience (faster response when messages arrive).

## Dead-Letter Queues (DLQ)

If a message can't be processed (e.g., the consumer keeps failing), it's moved to a DLQ for inspection:

```text
Main Queue: maxReceiveCount=5
After 5 receives without delete → message moves to DLQ.
```

```bash
aws sqs set-queue-attributes --queue-url ... --attributes '{
  "RedrivePolicy": "{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:123:my-dlq\",\"maxReceiveCount\":\"5\"}"
}'
```

The DLQ is just another SQS queue. The operator inspects the DLQ for messages that couldn't be processed (poison pills).

## Production Patterns

### Pattern 1: Worker Pool

```text
Producer (web app) → SQS → N consumer workers (Lambda or EC2)
```

The web app enqueues a task; workers receive and process. Scaling: as the queue grows, add more workers (auto-scaling on `ApproximateNumberOfMessagesVisible`).

### Pattern 2: Rate-Limited API Calls

```text
External API request → SQS (FIFO) → Consumer (1/sec) → External API
```

For an external API with rate limits, a FIFO queue with a single consumer processes one request at a time, respecting the rate limit.

### Pattern 3: Batch Processing

```text
User submits 10K records → SQS → 10 consumers process 1K each in parallel
```

A user submits a batch of work; SQS splits it across consumers. Each consumer processes its share and acks.

### Pattern 4: Lambda Trigger

Lambda functions can be triggered by SQS:

```python
# Lambda handler triggered by SQS
def handler(event, context):
    for record in event['Records']:
        body = json.loads(record['body'])
        process(body)
    # If the handler returns successfully, SQS auto-deletes the messages.
    # If the handler raises, the messages become visible again.
```

Lambda's SQS integration is fully managed: AWS polls SQS for you, invokes Lambda with batches of messages, and auto-deletes successful messages.

## Production Performance

SQS performance on a standard queue:
- Throughput: unlimited (scales with the queue's traffic).
- Latency (send): ~10 ms.
- Latency (receive, long polling): ~10-20 ms.
- Max message size: 256 KB (or 2 GB with S3 extension).
- Storage: 14 days (max retention).

For high-throughput workloads (1M+ messages/sec), use Kinesis or Kafka instead.

## Common Pitfalls

1. **Forgetting that standard queues can deliver duplicates.** A consumer that doesn't handle duplicates may double-process. Make consumers idempotent.

2. **Forgetting that the visibility timeout must exceed processing time.** If the consumer takes 60s but the timeout is 30s, the message is re-delivered mid-processing.

3. **Forgetting that FIFO queues have a throughput limit.** 300 msgs/sec is the default; 3000 with batch send/receive. For higher throughput, use parallel FIFO queues (one per group ID).

4. **Forgetting that SQS messages are limited to 256 KB.** For larger payloads, store in S3 and pass the S3 pointer in the SQS message (the "extended client library" handles this).

5. **Forgetting to set up DLQs.** Without a DLQ, poison pill messages stay in the queue forever (each receive makes them visible again, but they're never deleted).

6. **Forgetting that Lambda's SQS trigger may batch messages.** A Lambda invocation may receive up to 10 messages (configurable). If one fails, all are re-queued (or partially acked with `ReportBatchItemFailures`).

## Comparison to Other Message Queues

| Aspect | SQS | RabbitMQ | Kafka | SNS+SQS |
|--------|-----|----------|-------|----------|
| Model | Pull-based (consumer polls) | Push (consumer subscribes) | Pull (consumer pulls) | Push (fan-out) |
| Throughput | Unlimited (standard) | 50K/sec | 1M+/sec | Limited |
| Ordering | No (standard), Yes (FIFO) | Yes (FIFO queues) | Yes (per-partition) | No |
| Persistence | Yes | Yes (with config) | Yes | Yes |
| Best for | AWS-native decoupling | Self-hosted complex routing | High-throughput logs | Fan-out |

SQS is the standard for AWS-native decoupling. Kafka for high-throughput. RabbitMQ for complex routing in non-AWS environments.

## References

- [AWS SQS documentation](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html)
- [SQS Standard vs FIFO](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-standard-fifo-queues.html)
- [SQS visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [SQS + Lambda (trigger configuration)](https://docs.aws.amazon.com/lambda/latest/dg/with-sqs.html)
- [SQS extended client library (S3 storage)](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-s3-messages.html)
- [SQS vs Kafka vs RabbitMQ (Confluent blog)](https://www.confluent.io/kafka-vs-sqs-vs-rabbitmq/)
- [LWN: SQS overview (2020)](https://lwn.net/Articles/820133/)
