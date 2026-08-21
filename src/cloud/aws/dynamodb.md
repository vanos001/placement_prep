# AWS DynamoDB

DynamoDB is Amazon's managed NoSQL database, launched in 2012. It provides single-digit-millisecond latency for key-value lookups at any scale, with automatic sharding, multi-AZ replication, and integrated TTL. DynamoDB is the successor to Amazon's internal Dynamo (2007), adapted for managed cloud deployment. This page covers the architecture, the partitioning model, the consistency options, and the production deployment patterns.

## The Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  DynamoDB Service (managed, multi-tenant)                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Request Router (distributes requests to partitions)    │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Partitions (auto-sharded)                              │ │
│  │  - Each partition holds data for a key range             │ │
│  │  - 3 replicas per partition (multi-AZ)                   │ │
│  │  - SSD-backed storage (B-tree)                          │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ▲                              ▲
        │ API call                     │ DynamoDB Streams (CDC)
        ▼                              ▼
    Application                    Kinesis/Lambda/Elasticsearch
```

DynamoDB is fully managed: the user doesn't see partitions or replicas. The service handles sharding, replication, and scaling.

## The Data Model

DynamoDB stores data in tables, each with a schema:

```python
import boto3
ddb = boto3.client('dynamodb')

# Create a table
ddb.create_table(
    TableName='users',
    KeySchema=[
        {'AttributeName': 'user_id', 'KeyType': 'HASH'},  # partition key
        {'AttributeName': 'created_at', 'KeyType': 'RANGE'},  # sort key
    ],
    AttributeDefinitions=[
        {'AttributeName': 'user_id', 'AttributeType': 'S'},
        {'AttributeName': 'created_at', 'AttributeType': 'N'},
    ],
    BillingMode='PAY_PER_REQUEST',  # or PROVISIONED
)
```

Each item (row) has:
- **Partition key** (HASH): determines which partition the item goes to.
- **Sort key** (RANGE, optional): determines the order within a partition.
- **Attributes**: any additional key-value pairs.

The partition key + sort key uniquely identifies an item.

## Partitioning

DynamoDB partitions data by hashing the partition key:

```text
hash(user_id) % N → partition P
Item with user_id="alice" → hash("alice") % N → partition 5
```

The number of partitions is determined by:
- The table's storage size (~10 GB per partition).
- The table's provisioned throughput (~1000 WCU / 3000 RCU per partition).

When a table grows (data or throughput), DynamoDB auto-splits partitions. This is transparent to the application.

## Consistency Options

### Eventually Consistent Reads (default)

```python
response = ddb.get_item(TableName='users', Key={'user_id': {'S': 'alice'}})
# May return slightly stale data (replication lag, <1 second).
# Half the read capacity cost of strongly consistent.
```

### Strongly Consistent Reads

```python
response = ddb.get_item(TableName='users', Key={'user_id': {'S': 'alice'}},
                        ConsistentRead=True)
# Returns the latest written value.
# Higher cost, may have slightly higher latency.
```

Strongly consistent reads hit the partition's primary replica; eventually consistent reads can hit any replica.

### Transactional Reads/Writes

DynamoDB supports ACID transactions across multiple items (since 2018):

```python
response = ddb.transact_write_items(
    TransactItems=[
        {'Put': {'TableName': 'users', 'Item': {'user_id': {'S': 'alice'}, ...}}},
        {'Update': {'TableName': 'accounts', 'Key': {...}, 
                    'UpdateExpression': 'SET balance = balance - :amt',
                    'ExpressionAttributeValues': {':amt': {'N': '100'}}}},
    ]
)
```

The transaction is atomic across items (within a single account, up to 100 items). Uses optimistic concurrency control internally.

## Global Secondary Indexes (GSI)

A GSI lets you query by a different key:

```python
ddb.create_table(
    TableName='users',
    KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
    AttributeDefinitions=[
        {'AttributeName': 'user_id', 'AttributeType': 'S'},
        {'AttributeName': 'email', 'AttributeType': 'S'},
    ],
    GlobalSecondaryIndexes=[
        {
            'IndexName': 'email-index',
            'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
            'Projection': {'ProjectionType': 'ALL'},
        }
    ],
    BillingMode='PAY_PER_REQUEST',
)

# Query by email
ddb.query(TableName='users', IndexName='email-index',
          KeyConditionExpression='email = :e',
          ExpressionAttributeValues={':e': {'S': 'alice@example.com'}})
```

GSI trade-offs:
- **Eventual consistency**: GSI updates lag the main table by ~1 second.
- **Cost**: GSI reads and writes are charged separately.
- **Storage**: GSI stores its own copy of the projected attributes.

## Local SecondaryIndexes (LSI)

LSI lets you query by a different sort key (same partition key):

```python
# LSI: query by user_id + created_at (the LSI's sort key)
ddb.query(TableName='users', IndexName='created-at-index',
          KeyConditionExpression='user_id = :u AND created_at > :t', ...)
```

LSI trade-offs:
- **Strongly consistent**: LSI reads can be strongly consistent.
- **Storage**: LSI shares the partition with the main table.
- **Limited**: only 5 LSI per table; must be created at table creation.

## DynamoDB Streams

DynamoDB Streams (since 2013) capture row-level changes (inserts, updates, deletes):

```python
# Enable streams on the table
ddb.update_table(TableName='users',
                 StreamSpecification={
                     'StreamEnabled': True,
                     'StreamViewType': 'NEW_AND_OLD_IMAGES',  # both before and after
                 })

# Lambda function triggered by stream events
def handler(event, context):
    for record in event['Records']:
        if record['eventName'] == 'INSERT':
            new_item = record['dynamodb']['NewImage']
            # Process the new item
```

The stream is consumed by Kinesis or Lambda; this is the CDC (Change Data Capture) for DynamoDB. Used for:
- Replication to Elasticsearch (search index).
- Replication to Redshift (analytics warehouse).
- Real-time alerts on data changes.

## TTL (Time-to-Live)

Items can auto-expire:

```python
ddb.update_time_to_live(TableName='users',
    TimeToLiveSpecification={'AttributeName': 'expires_at', 'Enabled': True})

# When writing:
ddb.put_item(TableName='users', Item={
    'user_id': {'S': 'alice'},
    'expires_at': {'N': str(int(time.time()) + 3600)},  # expire in 1 hour
})
```

Items past their TTL are deleted in the background (~48 hours lag). Used for session storage, cache, rate-limit counters.

## Global Tables (Multi-Region)

DynamoDB Global Tables (since 2017) replicate a table across regions:

```python
ddb.create_global_table(
    GlobalTableName='users',
    ReplicationGroup=[
        {'RegionName': 'us-east-1'},
        {'RegionName': 'eu-west-1'},
        {'RegionName': 'ap-south-1'},
    ]
)
```

Writes to any region propagate to others within seconds. Reads are local to each region (low latency). Conflicts are resolved by last-writer-wins.

## Production Performance

DynamoDB performance:
- Single-digit-ms latency for point lookups (P99 ~10 ms).
- Throughput: limited by provisioned capacity or on-demand pricing.
- Storage: per-table, ~10 TB+ per partition.
- Per-item size: 400 KB.

DynamoDB's strength is consistent latency regardless of table size — a 1 TB table and a 1 GB table have the same lookup latency.

## Production Use Cases

### Session Storage

```python
# Write a session (with TTL)
ddb.put_item(TableName='sessions', Item={
    'session_id': {'S': 'abc-123'},
    'user_id': {'S': 'alice'},
    'expires_at': {'N': str(int(time.time()) + 3600)},
})

# Read a session
session = ddb.get_item(TableName='sessions', Key={'session_id': {'S': 'abc-123'}})
```

Sessions auto-expire via TTL; reads are sub-10 ms.

### Shopping Cart

```python
# Add to cart
ddb.update_item(TableName='carts', Key={'user_id': {'S': 'alice'}},
                UpdateExpression='SET items.#i = :q',
                ExpressionAttributeNames={'#i': 'product-123'},
                ExpressionAttributeValues={':q': {'N': '2'}})
```

Per-user carts; consistent reads ensure users see their latest cart.

### High-Throughput Logging

For 100K events/sec:
- Partition key: event type (low cardinality).
- Sort key: timestamp (high cardinality).
- On-demand pricing.

```python
ddb.put_item(TableName='events', Item={
    'event_type': {'S': 'login'},
    'timestamp': {'N': str(int(time.time() * 1000))},
    'user_id': {'S': 'alice'},
})
```

Per-event cost: ~$0.001 on-demand.

## Common Pitfalls

1. **Choosing a partition key with hot shards.** A partition key with one dominant value (e.g., all events have type="login") overloads one partition. Add a "shard" suffix: `login-0`, `login-1`, etc.

2. **Forgetting that GSIs are eventually consistent.** A GSI query may return stale data; if you need strong consistency, query the main table.

3. **Forgetting that DynamoDB's per-item size is 400 KB.** For larger items, store in S3 and put the S3 pointer in DynamoDB.

4. **Forgetting that provisioned capacity auto-scales slowly.** If traffic spikes, the auto-scaler takes ~5 minutes to add capacity. Pre-warm for known spikes.

5. **Forgetting that global tables have write conflicts.** Two regions writing the same key simultaneously may overwrite each other (last-writer-wins). Use a single-writer pattern or conflict resolution.

6. **Forgetting that scans are slow and expensive.** A "scan" reads the whole table; for >1 GB tables, this is slow and costly. Use queries with partition keys, or export to S3 + Athena for full-table analysis.

## Comparison to Other NoSQL DBs

| Aspect | DynamoDB | Cassandra | MongoDB |
|--------|----------|-----------|---------|
| Deployment | Fully managed (AWS) | Self-managed | Self or Atlas |
| Sharding | Automatic | Consistent hashing | mongos router |
| Consistency | Tunable (per read) | Tunable (per read) | Strong (default) |
| Throughput | Provisioned or on-demand | Very high (~1M/sec) | Medium (~100K/sec) |
| Best for | AWS-native, low-ops | Self-hosted, multi-DC | Flexible queries |

DynamoDB is the AWS-native choice; Cassandra for self-hosted; MongoDB for flexible queries.

## References

- [AWS DynamoDB documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Welcome.html)
- DeCandia et al., "[Dynamo: Amazon's Highly Available Key-Value Store](https://www.cs.ucsb.edu/~suri/psdir/SOSP07-Dynamo.pdf)" (SOSP 2007) — the original paper
- [DynamoDB Streams documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html)
- [DynamoDB Global Tables](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html)
- [DynamoDB best practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [DynamoDB vs Cassandra (AWS blog)](https://aws.amazon.com/blogs/database/dynamodb-vs-cassandra/)
- [LWN: DynamoDB overview (2020)](https://lwn.net/Articles/820133/)
