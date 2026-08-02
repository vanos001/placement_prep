# AWS Lambda (Serverless Compute)

## Introduction

AWS Lambda is a serverless compute service that runs your code in response to events without provisioning or managing servers. You pay only for the compute time you consume—there is no charge when your code is not running.

## Serverless Computing

```mermaid
graph TB
    TRAD[Traditional] --> PROV[Provision Servers]
    PROV --> CONFIG[Configure OS & Runtime]
    CONFIG --> DEPLOY[Deploy Code]
    DEPLOY --> SCALE[Manage Scaling]
    SCALE --> PATCH[Patch & Maintain]
    PATCH --> PAY[Pay 24/7]

    SERVERLESS[Serverless] --> DEPLOY_SL[Deploy Code Only]
    DEPLOY_SL --> PAY_SL[Pay Per Execution]
```

**Serverless doesn't mean "no servers"**—it means you don't manage servers. AWS handles provisioning, scaling, patching, and availability.

## Lambda Architecture

```mermaid
graph TB
    subgraph "Event Sources"
        S3[S3 Bucket]
        APIGW[API Gateway]
        CW[CloudWatch Events]
        DDB[DynamoDB Streams]
        SQS[SQS Queue]
        SNS[SNS Topic]
        KINESIS[Kinesis Stream]
    end

    subgraph "Lambda Service"
        INVOC[Invocation]
        RUNTIME[Runtime - Node.js, Python, Java, Go, .NET, Ruby, Custom]
        EXEC[Execution Environment]
        LAYER[Layers - Shared Code]
    end

    subgraph "Destinations"
        RESP[Response to Caller]
        ASYNC_DEST[Async Destinations]
        DLQ[Dead Letter Queue]
    end

    S3 --> INVOC
    APIGW --> INVOC
    CW --> INVOC
    DDB --> INVOC
    SQS --> INVOC

    INVOC --> RUNTIME
    RUNTIME --> EXEC
    EXEC --> LAYER
    EXEC --> RESP
    EXEC --> ASYNC_DEST
    EXEC --> DLQ
```

### Lambda Function Components

| Component | Details |
|-----------|---------|
| **Function** | Your code + configuration |
| **Runtime** | Language runtime (Python 3.12, Node.js 20, Java 21, etc.) |
| **Handler** | Entry point function (e.g., `lambda_handler`) |
| **Layers** | Shared libraries and dependencies |
| **Environment Variables** | Configuration without code changes |
| **Execution Role** | IAM role Lambda assumes to access AWS services |
| **VPC Config** | Optional: run Lambda inside a VPC |

## Lambda Execution Model

```mermaid
sequenceDiagram
    participant Event as Event Source
    participant Lambda as Lambda Service
    participant Env as Execution Environment
    participant Code as Your Code

    Event->>Lambda: Invoke function
    Lambda->>Env: Reuse existing or create new environment
    Note over Env: If new: Init (download code, start runtime, run init code)
    Env->>Code: Call handler function
    Code->>Env: Return response
    Env->>Lambda: Response
    Lambda->>Event: Return result

    Note over Env: Environment kept warm for reuse
```

### Cold Starts vs Warm Starts

```mermaid
graph TB
    subgraph "Cold Start (First Request)"
        CS1[Download Function Code] --> CS2[Start Runtime/Container]
        CS2 --> CS3[Run Init Code (imports, connections)]
        CS3 --> CS4[Run Handler]
        CS4 --> CS5[Return Response]
    end

    subgraph "Warm Start (Subsequent Requests)"
        WS1[Reuse Existing Environment]
        WS1 --> WS2[Run Handler]
        WS2 --> WS3[Return Response]
    end
```

| Aspect | Cold Start | Warm Start |
|--------|-----------|------------|
| **Latency** | 100ms to 10s+ | 1-50ms |
| **Triggers** | First invocation, scaling, idle timeout (>15 min) | Reused environment |
| **What happens** | Download code, start runtime, run init | Just run handler |
| **Mitigation** | Provisioned concurrency, keep-warm patterns | Normal operation |

### Cold Start Factors

| Factor | Impact | Mitigation |
|--------|--------|-----------|
| **Package size** | Larger = slower download | Minimize dependencies, use layers |
| **Runtime** | Java/C# slower than Python/Node.js | Use SnapStart (Java), choose lighter runtimes |
| **VPC attachment** | Adds ENI creation time | Use Hyperplane (improved), minimize VPC subnets |
| **Init code** | Heavy imports slow cold start | Lazy-load, minimize imports |
| **Memory** | More memory = more CPU = faster init | Right-size memory allocation |

## Lambda Pricing

```mermaid
graph TB
    COST[Lambda Cost] --> REQ[Request Charges]
    COST --> DUR[Duration Charges]
    COST --> PROV[Provisioned Concurrency]

    REQ --> |$0.20 per 1M requests| REQ_D[First 1M free/month]
    DUR --> |Per GB-second| DUR_D[$0.0000166667 per GB-sec]
    PROV --> |Provisioned concurrency pricing| PROV_D[Pay for always-warm instances]
```

**Example Cost Calculation:**
```
1 million requests/month
256 MB memory, 200ms average duration

Request cost: 1M × $0.20/1M = $0.20
Duration cost: 1M × 0.2s × 0.25GB × $0.0000166667 = $0.83
Total: ~$1.03/month
```

**Free Tier:** 1 million requests and 400,000 GB-seconds per month, always free.

## Lambda Concurrency

```mermaid
graph TB
    subgraph "Concurrency Model"
        SQS_C[SQS Queue] --> |Batch| INV[Lambda Invocations]
        INV --> ENV1[Environment 1]
        INV --> ENV2[Environment 2]
        INV --> ENV3[Environment 3]
        INV --> ENV_N[Environment N...]
    end

    subgraph "Concurrency Types"
        AC[Account Concurrency - 1000 default]
        FC[Function Concurrency - Shared pool]
        RC[Reserved Concurrency - Guaranteed max]
        PC[Provisioned Concurrency - Always warm]
    end
```

| Concurrency Type | Description | Use Case |
|-----------------|-------------|----------|
| **Account Limit** | 1,000 concurrent executions (default, can request increase) | Overall limit |
| **Unreserved** | Shared pool across all functions | Default behavior |
| **Reserved** | Guarantees max for a function, prevents noisy neighbor | Rate limiting |
| **Provisioned** | Pre-initialized environments, eliminates cold starts | Latency-critical |

### Provisioned Concurrency

```mermaid
graph LR
    PC[Provisioned Concurrency = 10] --> |Always warm| ENV10[10 Environments Ready]
    ENV10 --> |Handles first 10 concurrent requests| FAST[No Cold Start]
    FAST --> |Beyond 10| SCALING[Auto-scaling with regular concurrency]
    SCALING --> |May cold start| CS[Cold Start Possible]
```

## Lambda Event Sources

### Synchronous Invocations

```mermaid
sequenceDiagram
    participant Client
    participant APIGW as API Gateway
    participant Lambda
    participant DB as Database

    Client->>APIGW: HTTP Request
    APIGW->>Lambda: Invoke (synchronous)
    Lambda->>DB: Query data
    DB->>Lambda: Results
    Lambda->>APIGW: Response
    APIGW->>Client: HTTP Response
```

**Sync sources:** API Gateway, ALB, CloudFront, Cognito, Lex

### Asynchronous Invocations

```mermaid
sequenceDiagram
    participant S3
    participant Lambda
    participant DLQ as Dead Letter Queue
    participant Dest as Destination

    S3->>Lambda: Invoke (async, event)
    Note over Lambda: Returns 202 immediately
    Lambda->>Lambda: Process event

    alt Success
        Lambda->>Dest: OnSuccess destination
    else Failure (after 2 retries)
        Lambda->>DLQ: Failed event
    end
```

**Async sources:** S3, SNS, CloudWatch Events, CodeCommit, IoT

### Event Source Mapping (Polling)

```mermaid
sequenceDiagram
    participant SQS as SQS / Kinesis / DynamoDB
    participant ESM as Event Source Mapping
    participant Lambda

    ESM->>SQS: Poll for records (long polling)
    ESM->>Lambda: Invoke with batch of records
    Lambda->>Lambda: Process batch

    alt Success
        ESM->>SQS: Delete/acknowledge records
    else Failure
        ESM->>SQS: Return to queue (visibility timeout)
    end
```

**Polling sources:** SQS, Kinesis, DynamoDB Streams, Kafka

## Lambda Best Practices

### Function Design

```mermaid
graph TB
    BEST[Lambda Best Practices] --> SINGLE[Single Responsibility]
    BEST --> STATELESS[Stateless Design]
    BEST --> SMALL[Minimal Package Size]
    BEST --> ENV[Environment Variables for Config]
    BEST --> LAYER[Layers for Shared Dependencies]
    BEST --> IDEMPOTENT[Idempotent Handlers]

    SINGLE --> |One function, one task| SR_D[Easier to debug, scale, monitor]
    STATELESS --> |No local state between invocations| SL_D[Reuse isn't guaranteed]
    SMALL --> |Minimize cold start| SM_D[Exclude dev dependencies]
    IDEMPOTENT --> |Safe to retry| ID_D[Async invocations may retry]
```

### Memory and CPU Relationship

```mermaid
graph LR
    MEM[Memory: 128MB - 10240MB] --> CPU[CPU scales proportionally]
    CPU --> NET[Network bandwidth scales too]

    MEM_LOW[128 MB = ~0.08 vCPU]
    MEM_MED[1769 MB = 1 vCPU]
    MEM_HIGH[10240 MB = ~6 vCPU]
```

| Memory | vCPU | Good For |
|--------|------|----------|
| 128 MB | ~0.08 | Simple transformations, routing |
| 512 MB | ~0.29 | API handlers, data processing |
| 1769 MB | 1.0 | CPU-intensive work |
| 3008 MB | 1.7 | Image processing, ML inference |
| 10240 MB | ~6 | Maximum CPU needs |

## Lambda Limits

| Limit | Default | Adjustable |
|-------|---------|-----------|
| **Memory** | 128 MB - 10,240 MB | Fixed range |
| **Timeout** | 3 seconds (default) | Up to 15 minutes |
| **Package size** | 50 MB (zipped) | Up to 250 MB (unzipped) |
| **Layers** | 5 layers | No |
| **Environment variables** | 4 KB | No |
| **Concurrency** | 1,000 per account | Yes (request increase) |
| **Payload** | 6 MB (sync), 256 KB (async) | No |
| **/tmp storage** | 512 MB - 10 GB | Via ephemeral storage config |
| **Execution** | No time limit on container reuse | Timeout per invocation |

## Lambda Destinations

```mermaid
graph TB
    ASYNC_INV[Async Invocation] --> RESULT{Result}
    RESULT --> |Success| ON_SUCCESS[OnSuccess Destination]
    RESULT --> |Failure| ON_FAILURE[OnFailure Destination]

    ON_SUCCESS --> SQS_S[SQS Queue]
    ON_SUCCESS --> SNS_S[SNS Topic]
    ON_SUCCESS --> LAMBDA_S[Lambda Function]
    ON_SUCCESS --> EB_S[EventBridge]

    ON_FAILURE --> SQS_F[SQS Queue]
    ON_FAILURE --> SNS_F[SNS Topic]
    ON_FAILURE --> LAMBDA_F[Lambda Function]
    ON_FAILURE --> EB_F[EventBridge]
```

## Interview Questions

### Q1: What is a cold start in Lambda and how do you mitigate it?
**Answer**: A cold start occurs when Lambda creates a new execution environment—downloading code, starting the runtime, and running initialization code. This adds 100ms to 10s+ of latency. Mitigations: (1) Provisioned Concurrency keeps environments pre-initialized, (2) Minimize package size and dependencies, (3) Use lighter runtimes (Python/Node.js over Java/C#), (4) Lazy-load heavy imports, (5) Use SnapStart for Java, (6) Avoid VPC attachment when possible, (7) Keep-warm patterns (scheduled pings—hacky but works).

### Q2: Explain Lambda's concurrency model.
**Answer**: Concurrency is the number of requests being processed simultaneously. Account limit defaults to 1,000. Functions share unreserved concurrency. Reserved Concurrency sets a guaranteed maximum for a function (prevents noisy neighbor). Provisioned Concurrency pre-initializes N environments, eliminating cold starts for up to N concurrent requests. Beyond provisioned concurrency, Lambda scales with regular concurrency (may cold start). Auto-scaling adjusts provisioned concurrency based on utilization.

### Q3: How does Lambda handle failures for different invocation types?
**Answer**: Synchronous (API Gateway, ALB): Returns error directly to caller—caller must retry. Asynchronous (S3, SNS): Lambda retries automatically twice (with backoff), then sends to Dead Letter Queue (DLQ) or OnFailure destination. Event Source Mapping (SQS, Kinesis): Returns messages to queue/stream for retry—use DLQ on the source for poison messages. Always configure DLQ/failure destinations to avoid losing events.

### Q4: When would you choose Lambda over EC2?
**Answer**: Choose Lambda for: event-driven workloads (S3 uploads, API requests), unpredictable traffic (auto-scales to zero), short-lived tasks (< 15 minutes), pay-per-execution cost model, zero operational overhead. Choose EC2 for: long-running processes, consistent traffic (cheaper than Lambda at scale), custom OS/kernel requirements, applications requiring persistent connections, workloads exceeding Lambda's limits (memory, timeout, package size).

### Q5: How do you connect Lambda to a VPC?
**Answer**: Configure the Lambda function with VPC subnets and security groups. Lambda creates ENIs in the specified subnets to access VPC resources (RDS, ElastiCache). This adds cold start latency (historically ~10s for ENI creation, now improved to ~1s with Hyperplane). Best practices: use private subnets with NAT Gateway for internet access, minimize subnet count, use VPC endpoints for AWS services (S3, DynamoDB) to avoid NAT costs.

## Common Mistakes

1. **Not handling timeouts**: Lambda silently kills your function at the timeout—handle graceful shutdown
2. **Storing state in global variables**: Environments may be reused, but don't rely on it for correctness
3. **Over-provisioning memory**: More memory = more CPU = faster execution, but costs more—optimize
4. **No DLQ for async functions**: Failed events are lost without a DLQ or destination
5. **Ignoring idempotency**: Async invocations may retry—handlers must be idempotent
6. **Large deployment packages**: Causes slow cold starts—minimize dependencies
7. **Not using environment variables**: Hard-coding config in code prevents reuse across environments
8. **VPC when not needed**: Adds cold start latency and requires NAT for internet access

## Summary

| Concept | Key Takeaway |
|---------|-------------|
| **Serverless** | No server management, pay per execution |
| **Cold Start** | Latency on first request, mitigated by provisioned concurrency |
| **Concurrency** | Account limit, reserved, provisioned concurrency |
| **Event Sources** | Synchronous, asynchronous, and polling (event source mapping) |
| **Pricing** | Per request + per GB-second, free tier available |
| **Best Practices** | Single responsibility, minimal size, idempotent, right-size memory |

## Cross-References

- **EC2**: [Instance Types](./ec2.md) — When Lambda isn't enough
- **S3**: [Event Notifications](./s3.md) — S3 triggers Lambda
- **API Gateway**: Front door for Lambda-based APIs
- **SQS**: Decoupling and async processing
- **Kubernetes**: [Pods](../kubernetes/pods.md) — Alternative: Knative serverless on K8s
- **Observability**: [Logging](../observability/logging.md) — CloudWatch Logs for Lambda
